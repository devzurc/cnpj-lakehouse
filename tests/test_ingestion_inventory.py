from __future__ import annotations

import shutil
from pathlib import Path

import httpx
import pytest

from cnpj_lakehouse.flows.cnpj_lakehouse import run_local_pipeline
from cnpj_lakehouse.inventory import archive_inventory_from_run, plan_local_ingestion
from cnpj_lakehouse.settings import output_layout
from cnpj_lakehouse.tasks.download import download_file
from cnpj_lakehouse.tasks.load_duckdb import reusable_bronze_for_cohort
from cnpj_lakehouse.tasks.source_resolution import SourceFile, expected_source_filenames
from tests.test_bronze_pipeline import _create_required_archives


def test_expected_source_filenames_cover_the_contract() -> None:
    names = expected_source_filenames()
    assert len(names) == 32
    assert "Empresas0.zip" in names
    assert "Cnaes.zip" in names


def test_download_reuses_existing_file_without_http(tmp_path: Path) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, content=b"complete-archive")

    source = SourceFile(
        "companies",
        "Empresas0.zip",
        "https://example.test/Empresas0.zip",
        "https://example.test/Empresas0.zip",
    )
    first = download_file(source, tmp_path, transport=httpx.MockTransport(handler))
    second = download_file(source, tmp_path, transport=httpx.MockTransport(handler))
    assert attempts == 1
    assert first.reused is False
    assert second.reused is True
    assert second.sha256 == first.sha256
    assert second.path.read_bytes() == b"complete-archive"


def test_archive_inventory_lists_present_and_missing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    downloads = run_dir / "bronze" / "downloads" / "source_period=202601"
    downloads.mkdir(parents=True)
    (downloads / "Empresas0.zip").write_bytes(b"x")
    rows = archive_inventory_from_run(run_dir)
    assert rows[0]["source_period"] == "202601"
    assert "Empresas0.zip" in rows[0]["present"]
    assert "Cnaes.zip" in rows[0]["missing"]
    assert rows[0]["required"] == 32
    assert len(rows[0]["missing"]) == 31
    assert rows[0]["needs_download"] is True


def test_plan_lists_missing_archives_before_ingest(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    plan = plan_local_ingestion(output, "202601", 3)
    assert plan["action"] == "download_missing"
    assert plan["archives"]["required"] == 32
    assert len(plan["archives"]["missing"]) == 32
    assert plan["bronze_samples"] == []
    assert plan["reuse_bronze"] is False


def test_second_pipeline_run_skips_bronze_for_the_same_cohort(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    output = tmp_path / "output"
    first = run_local_pipeline(
        source_period="202601",
        sample_size=2,
        output_path=str(output),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=False,
        ingestion_workers=1,
    )
    second = run_local_pipeline(
        source_period="202601",
        sample_size=2,
        output_path=str(output),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=False,
        ingestion_workers=1,
    )
    assert first.skipped is False
    assert second.skipped is True
    assert second.sample_id == first.sample_id
    plan = plan_local_ingestion(output, "202601", 2)
    assert plan["action"] == "reuse_bronze"
    assert plan["archives"]["needs_download"] is False
    assert plan["bronze_samples"][0]["distinct_companies"] == 2
    conflict = plan_local_ingestion(output, "202601", 3)
    assert conflict["action"] == "conflict"
    assert conflict["reuse_bronze"] is False


def test_present_archives_ingest_without_remote_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    output = tmp_path / "output"
    downloads = output_layout(output, "202601")["downloads"]
    downloads.mkdir(parents=True)
    for archive in sources.iterdir():
        if archive.is_file():
            shutil.copy2(archive, downloads / archive.name)
    plan = plan_local_ingestion(output, "202601", 2)
    assert plan["action"] == "ingest_present_archives"
    assert plan["archives"]["needs_download"] is False

    def fail_remote(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("remote source resolution must not run")

    monkeypatch.setattr(
        "cnpj_lakehouse.flows.cnpj_lakehouse.resolve_remote_sources",
        fail_remote,
    )
    result = run_local_pipeline(
        source_period="202601",
        sample_size=2,
        output_path=str(output),
        reference_date=None,
        full_refresh=False,
        source_dir=None,
        base_url="https://example.invalid/",
        run_dbt_steps=False,
        ingestion_workers=1,
    )
    assert result.skipped is False
    assert result.row_counts["companies"] >= 2
    assert plan_local_ingestion(output, "202601", 2)["action"] == "reuse_bronze"


def test_second_cohort_for_the_same_period_is_refused(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    output = tmp_path / "output"
    run_local_pipeline(
        source_period="202601",
        sample_size=2,
        output_path=str(output),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=False,
        ingestion_workers=1,
    )
    with pytest.raises(RuntimeError, match="refusing a second cohort of 3 companies"):
        run_local_pipeline(
            source_period="202601",
            sample_size=3,
            output_path=str(output),
            reference_date=None,
            full_refresh=False,
            source_dir=str(sources),
            base_url="unused",
            run_dbt_steps=False,
            ingestion_workers=1,
        )
    warehouse = output / "warehouse" / "cnpj_lakehouse.duckdb"
    with pytest.raises(RuntimeError, match="already has Bronze"):
        reusable_bronze_for_cohort(warehouse, "202601", 10_000)
