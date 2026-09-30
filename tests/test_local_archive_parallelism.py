from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Self

import pytest

import cnpj_lakehouse.flows.cnpj_lakehouse as lakehouse_flow
import cnpj_lakehouse.tasks.sample as sample_task
from cnpj_lakehouse.demo_sources import create_demo_sources
from cnpj_lakehouse.flows.cnpj_lakehouse import (
    download_source_files,
    resolve_sources,
    validate_archives,
)
from cnpj_lakehouse.tasks.load_duckdb import load_bronze
from cnpj_lakehouse.tasks.sample import build_sample
from tests.test_sampling_plan import _four_company_archives


class _InlineFuture:
    def __init__(self, value: object) -> None:
        self.value = value

    def result(self) -> object:
        return self.value


class _InlineProcessPool:
    """Exercise the parallel branch without WSL /mnt process-startup latency."""

    def __init__(self, *, max_workers: int, **_kwargs: object) -> None:
        self.max_workers = max_workers

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def map(self, function: object, *iterables: object) -> list[object]:
        return [function(*values) for values in zip(*iterables, strict=True)]  # type: ignore[operator,arg-type]

    def submit(self, function: object, *args: object) -> _InlineFuture:
        return _InlineFuture(function(*args))  # type: ignore[operator]


def test_archive_workers_preserve_the_sample_and_validation_counts(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(lakehouse_flow, "ProcessPoolExecutor", _InlineProcessPool)  # type: ignore[union-attr]
    monkeypatch.setattr(sample_task, "ProcessPoolExecutor", _InlineProcessPool)  # type: ignore[union-attr]
    sources = tmp_path / "sources"
    sources.mkdir()
    _four_company_archives(sources)
    downloaded = download_source_files.fn(
        resolve_sources.fn("202601", str(sources), "unused"), str(tmp_path / "downloads")
    )
    serial_validation = validate_archives.fn(downloaded, "202601", str(tmp_path / "serial-manifests"), 1)
    parallel_validation = validate_archives.fn(downloaded, "202601", str(tmp_path / "parallel-manifests"), 2)
    assert parallel_validation == serial_validation

    serial = build_sample(downloaded, "202601", 4, tmp_path / "serial-samples", ingestion_workers=1)
    parallel = build_sample(downloaded, "202601", 4, tmp_path / "parallel-samples", ingestion_workers=2)
    assert parallel.sample_id == serial.sample_id
    assert parallel.selected_companies == serial.selected_companies
    assert parallel.row_counts == serial.row_counts


def test_parallel_ranking_merges_partial_candidates_from_demo_shards(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(sample_task, "ProcessPoolExecutor", _InlineProcessPool)  # type: ignore[union-attr]
    sources = tmp_path / "sources"
    create_demo_sources(sources)
    downloaded = download_source_files.fn(
        resolve_sources.fn("202601", str(sources), "unused"), str(tmp_path / "downloads")
    )
    sample = build_sample(downloaded, "202601", 3, tmp_path / "samples", ingestion_workers=2)
    assert len(sample.selected_companies) == 3


def test_real_process_workers_preserve_sample_file_hashes(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _four_company_archives(sources)
    downloaded = download_source_files.fn(
        resolve_sources.fn("202601", str(sources), "unused"), str(tmp_path / "downloads")
    )
    serial = build_sample(downloaded, "202601", 4, tmp_path / "serial-samples", ingestion_workers=1)
    parallel = build_sample(downloaded, "202601", 4, tmp_path / "parallel-samples", ingestion_workers=2)
    serial_manifest = json.loads(
        (serial.sample_files["companies"].parent / "sample_manifest.json").read_text(encoding="utf-8")
    )
    parallel_manifest = json.loads(
        (parallel.sample_files["companies"].parent / "sample_manifest.json").read_text(encoding="utf-8")
    )
    assert parallel.selected_companies == serial.selected_companies
    assert parallel.row_counts == serial.row_counts
    assert parallel_manifest["sample_files"] == serial_manifest["sample_files"]
    serial_database = tmp_path / "serial.duckdb"
    parallel_database = tmp_path / "parallel.duckdb"
    assert load_bronze(serial_database, serial, "202601").row_counts == load_bronze(
        parallel_database, parallel, "202601"
    ).row_counts
    verifier = Path(__file__).resolve().parents[1] / "scripts" / "verify_bronze.py"
    for database in (serial_database, parallel_database):
        subprocess.run(
            [
                sys.executable,
                str(verifier),
                "--database",
                str(database),
                "--expect-period",
                "202601",
                "--expect-sample-size",
                "4",
            ],
            check=True,
            capture_output=True,
            text=True,
        )


def test_parallel_worker_failure_does_not_promote_partial_sample(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _four_company_archives(sources)
    with zipfile.ZipFile(sources / "Empresas0.zip", "w") as archive:
        archive.writestr("broken.csv", "only;two\n")
    downloaded = download_source_files.fn(
        resolve_sources.fn("202601", str(sources), "unused"), str(tmp_path / "downloads")
    )
    sample_directory = tmp_path / "samples"
    with pytest.raises(ValueError, match="expected 7"):
        build_sample(downloaded, "202601", 4, sample_directory, ingestion_workers=2)
    assert not list(sample_directory.glob("sample_id=*"))
    assert not list(sample_directory.glob(".sample_id=*.part"))
