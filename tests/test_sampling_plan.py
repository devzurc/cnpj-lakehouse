from __future__ import annotations

import json
from pathlib import Path

import pytest

from cnpj_lakehouse.contracts import CNAE, COMPANIES, ESTABLISHMENTS, PARTNERS, SIMPLES
from cnpj_lakehouse.flows.cnpj_lakehouse import download_source_files, resolve_sources
from cnpj_lakehouse.settings import resolve_sampling_plan
from cnpj_lakehouse.tasks.download import DownloadedFile
from cnpj_lakehouse.tasks.sample import (
    build_sample,
    sample_id_for_sources,
    select_company_cnpjs,
)
from cnpj_lakehouse.tasks.source_resolution import SourceFile
from tests.test_bronze_pipeline import _row, _write_archive


def _four_company_archives(directory: Path) -> None:
    companies = [
        _row(COMPANIES, cnpj_basico=f"{index:08d}", razao_social=f"Empresa {index}", capital_social_raw="1,00")
        for index in range(1, 5)
    ]
    establishments = [
        _row(
            ESTABLISHMENTS,
            cnpj_basico=f"{index:08d}",
            cnpj_ordem="0001",
            cnpj_dv="00",
            identificador_matriz_filial="1",
            situacao_cadastral="02",
            cnae_fiscal_principal="6201501",
            uf="SC",
        )
        for index in range(1, 5)
    ]
    partners = [_row(PARTNERS, cnpj_basico="00000001", nome_socio="Ana")]
    simples = [_row(SIMPLES, cnpj_basico="00000001", opcao_simples="S", opcao_mei="N")]
    cnae = [_row(CNAE, cnae_code="6201501", cnae_description="Desenvolvimento")]
    for shard in range(10):
        _write_archive(directory, COMPANIES, f"Empresas{shard}.zip", companies)
        _write_archive(directory, ESTABLISHMENTS, f"Estabelecimentos{shard}.zip", establishments)
        _write_archive(directory, PARTNERS, f"Socios{shard}.zip", partners)
    _write_archive(directory, SIMPLES, "Simples.zip", simples)
    _write_archive(directory, CNAE, "Cnaes.zip", cnae)


def test_sampling_plan_defaults_to_challenge_size() -> None:
    plan = resolve_sampling_plan()
    assert plan.sample_size == 10_000
    assert plan.parallel_jobs == 1
    assert plan.total_companies == 10_000


def test_sampling_plan_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CNPJ_LAKEHOUSE_SAMPLE_SIZE", "5000")
    monkeypatch.setenv("CNPJ_LAKEHOUSE_PARALLEL_JOBS", "4")
    plan = resolve_sampling_plan()
    assert plan.sample_size == 5_000
    assert plan.parallel_jobs == 4
    assert plan.total_companies == 20_000


def test_sampling_plan_file_then_cli_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "sampling.toml"
    config.write_text("sample_size = 2000\nparallel_jobs = 2\n", encoding="utf-8")
    monkeypatch.setenv("CNPJ_LAKEHOUSE_SAMPLING_CONFIG", str(config))
    assert resolve_sampling_plan().total_companies == 4_000
    monkeypatch.setenv("CNPJ_LAKEHOUSE_SAMPLE_SIZE", "5000")
    monkeypatch.setenv("CNPJ_LAKEHOUSE_PARALLEL_JOBS", "4")
    assert resolve_sampling_plan().total_companies == 20_000
    assert resolve_sampling_plan(sample_size=3, parallel_jobs=2).total_companies == 6


def test_sample_id_unchanged_for_single_job() -> None:
    item = DownloadedFile(
        SourceFile("companies", "Empresas0.zip", "https://example.test/a", "https://example.test/a"),
        Path("Empresas0.zip"),
        "abc",
        1,
    )
    assert sample_id_for_sources("202601", 10_000, [item]) == sample_id_for_sources(
        "202601", 10_000, [item], parallel_jobs=1
    )
    assert sample_id_for_sources("202601", 5_000, [item], parallel_jobs=4) != sample_id_for_sources(
        "202601", 20_000, [item], parallel_jobs=1
    )


def test_two_parallel_jobs_cover_same_companies_as_one_double_sample(tmp_path: Path) -> None:
    sources = tmp_path / "zips"
    sources.mkdir()
    _four_company_archives(sources)
    downloaded = download_source_files.fn(
        resolve_sources.fn("202601", str(sources), "unused"), str(tmp_path / "dl")
    )
    sequential = select_company_cnpjs(
        [item.path for item in downloaded if item.source.dataset == "establishments"],
        "202601",
        4,
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples", parallel_jobs=2)
    assert len(sample.selected_companies) == 4
    assert set(sample.selected_companies) == set(sequential)
    assert sample.row_counts["companies"] >= 4
    sample_root = sample.sample_files["companies"].parent
    assert not any(sample_root.glob("shard=*"))
    manifest = json.loads((sample_root / "sample_manifest.json").read_text(encoding="utf-8"))
    assert manifest["sample_size"] == 2
    assert manifest["parallel_jobs"] == 2
    assert manifest["total_companies"] == 4
    assert len(manifest["selection_observability"]) == 10
    assert {
        "source_file",
        "invalid_cnpj_basico",
        "valid_cnpj_basico",
        "selected_cnpj_basico",
    } == set(manifest["selection_observability"][0])


def test_sample_manifest_records_invalid_cnpj_only_as_aggregate_metrics(tmp_path: Path) -> None:
    sources = tmp_path / "zips"
    sources.mkdir()
    _four_company_archives(sources)
    invalid_value = "not-a-cnpj"
    _write_archive(
        sources,
        ESTABLISHMENTS,
        "Estabelecimentos0.zip",
        [
            _row(
                ESTABLISHMENTS,
                cnpj_basico=invalid_value,
                cnpj_ordem="0001",
                cnpj_dv="00",
                identificador_matriz_filial="1",
                situacao_cadastral="02",
                cnae_fiscal_principal="6201501",
                uf="SC",
            )
        ],
    )
    downloaded = download_source_files.fn(
        resolve_sources.fn("202601", str(sources), "unused"), str(tmp_path / "dl")
    )
    sample = build_sample(downloaded, "202601", 4, tmp_path / "samples")
    manifest_text = (sample.sample_files["companies"].parent / "sample_manifest.json").read_text(
        encoding="utf-8"
    )
    manifest = json.loads(manifest_text)
    first_shard = next(
        item for item in manifest["selection_observability"] if item["source_file"] == "Estabelecimentos0.zip"
    )
    assert first_shard == {
        "source_file": "Estabelecimentos0.zip",
        "invalid_cnpj_basico": 1,
        "valid_cnpj_basico": 0,
        "selected_cnpj_basico": 0,
    }
    assert invalid_value not in manifest_text


def test_sampling_plan_rejects_too_many_jobs() -> None:
    with pytest.raises(ValueError, match="at most"):
        resolve_sampling_plan(sample_size=1, parallel_jobs=17)
