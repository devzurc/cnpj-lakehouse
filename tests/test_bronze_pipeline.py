from __future__ import annotations

import csv
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

import duckdb
import httpx
import pytest

from cnpj_lakehouse.contracts import (
    CNAE,
    COMPANIES,
    ESTABLISHMENTS,
    PARTNERS,
    SIMPLES,
    SourceContract,
)
from cnpj_lakehouse.demo_sources import DEMO_NOTICE, create_demo_sources
from cnpj_lakehouse.tasks.archive import (
    SourceSchemaError,
    iter_contract_rows,
    validate_archive,
)
from cnpj_lakehouse.tasks.download import DownloadedFile, TransientDownloadError, download_file
from cnpj_lakehouse.tasks.load_duckdb import load_bronze
from cnpj_lakehouse.tasks.sample import build_sample, normalize_base_cnpj
from cnpj_lakehouse.tasks.source_resolution import (
    SourceFile,
    resolve_local_sources,
    resolve_remote_sources,
)


def _row(contract: SourceContract, **values: str) -> list[str]:
    return [values.get(field, "") for field in contract.expected_fields]


def _write_archive(directory: Path, contract: SourceContract, filename: str, rows: list[list[str]]) -> None:
    archive = directory / filename
    member = f"{filename.removesuffix('.zip')}.csv"
    content = "\n".join(";".join(row) for row in rows) + "\n"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr(member, content.encode("cp1252"))


def _create_required_archives(directory: Path) -> None:
    company_rows = [
        _row(COMPANIES, cnpj_basico="00000001", razao_social="Empresa Um", capital_social_raw="1.234,50"),
        _row(COMPANIES, cnpj_basico="00000002", razao_social="Empresa Dois", capital_social_raw="0,00"),
    ]
    establishment_rows = [
        _row(
            ESTABLISHMENTS,
            cnpj_basico="00000001",
            cnpj_ordem="0001",
            cnpj_dv="95",
            identificador_matriz_filial="1",
            situacao_cadastral="02",
            cnae_fiscal_principal="6201501",
            uf="SC",
        ),
        _row(
            ESTABLISHMENTS,
            cnpj_basico="00000001",
            cnpj_ordem="0002",
            cnpj_dv="96",
            identificador_matriz_filial="2",
            situacao_cadastral="02",
            cnae_fiscal_principal="6311900",
            uf="RJ",
        ),
        _row(
            ESTABLISHMENTS,
            cnpj_basico="00000002",
            cnpj_ordem="0002",
            cnpj_dv="00",
            identificador_matriz_filial="2",
            situacao_cadastral="02",
            cnae_fiscal_principal="6201501",
            uf="SP",
        ),
        _row(
            ESTABLISHMENTS,
            cnpj_basico="00000002",
            cnpj_ordem="0003",
            cnpj_dv="01",
            identificador_matriz_filial="2",
            situacao_cadastral="02",
            cnae_fiscal_principal="6311900",
            uf="RJ",
        ),
    ]
    partner_rows = [_row(PARTNERS, cnpj_basico="00000001", nome_socio="Ana")]
    simples_rows = [_row(SIMPLES, cnpj_basico="00000001", opcao_simples="S", opcao_mei="N")]
    cnae_rows = [
        _row(CNAE, cnae_code="6201501", cnae_description="Desenvolvimento de programas"),
        _row(CNAE, cnae_code="6311900", cnae_description="Tratamento de dados"),
    ]

    for index in range(10):
        _write_archive(directory, COMPANIES, f"Empresas{index}.zip", company_rows)
        _write_archive(directory, ESTABLISHMENTS, f"Estabelecimentos{index}.zip", establishment_rows)
        _write_archive(directory, PARTNERS, f"Socios{index}.zip", partner_rows)
    _write_archive(directory, SIMPLES, "Simples.zip", simples_rows)
    _write_archive(directory, CNAE, "Cnaes.zip", cnae_rows)


def _remote_directory_html(*, include_all: bool = True) -> str:
    names = [
        *(f"Empresas{index}.zip" for index in range(10)),
        *(f"Estabelecimentos{index}.zip" for index in range(10)),
        *(f"Socios{index}.zip" for index in range(10)),
        "Simples.zip",
        "Cnaes.zip",
    ]
    if not include_all:
        names.remove("Socios9.zip")
    return "\n".join(f'<a href="{name}">{name}</a>' for name in names)


def test_archive_rows_are_streamed_and_contract_validated(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    rows = list(iter_contract_rows(tmp_path / "Empresas0.zip", COMPANIES))
    assert rows[0][2]["cnpj_basico"] == "00000001"


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("", "found none"),
        (
            '<a href="2026-01-11/">one</a><a href="2026-01-31/">two</a>',
            "2026-01-11",
        ),
    ],
)
def test_remote_resolution_rejects_zero_or_multiple_period_directories(
    payload: str, expected: str
) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=payload))
    with pytest.raises(ValueError, match=expected):
        resolve_remote_sources("202601", "https://example.test/archives/", transport=transport)


def test_remote_resolution_rejects_missing_required_shard() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/archives/":
            return httpx.Response(200, text='<a href="2026-01-11/">month</a>')
        return httpx.Response(200, text=_remote_directory_html(include_all=False))

    with pytest.raises(ValueError, match="Socios9.zip"):
        resolve_remote_sources(
            "202601",
            "https://example.test/archives/",
            transport=httpx.MockTransport(handler),
        )


def test_remote_resolution_propagates_http_404() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        resolve_remote_sources("202601", "https://example.test/archives/", transport=transport)


def test_download_retries_transient_failures_then_promotes_complete_file(tmp_path: Path) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500 if attempts < 3 else 200, content=b"complete")

    source = SourceFile("companies", "Empresas0.zip", "https://example.test/Empresas0.zip", "https://example.test/Empresas0.zip")
    result = download_file(
        source,
        tmp_path,
        transport=httpx.MockTransport(handler),
    )
    assert attempts == 3
    assert result.path.read_bytes() == b"complete"
    assert not (tmp_path / "Empresas0.zip.part").exists()


@pytest.mark.parametrize("status", [404, 500])
def test_failed_download_never_promotes_partial_file(tmp_path: Path, status: int) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status)

    source = SourceFile("companies", "Empresas0.zip", "https://example.test/Empresas0.zip", "https://example.test/Empresas0.zip")
    expected_error = httpx.HTTPStatusError if status == 404 else TransientDownloadError
    with pytest.raises(expected_error):
        download_file(source, tmp_path, transport=httpx.MockTransport(handler))
    assert attempts == (1 if status == 404 else 3)
    assert not (tmp_path / "Empresas0.zip").exists()
    assert not (tmp_path / "Empresas0.zip.part").exists()


def test_archive_validation_rejects_corrupt_empty_and_wrong_width_files(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(b"not-a-zip")
    with pytest.raises(SourceSchemaError, match="not a ZIP"):
        validate_archive(corrupt, COMPANIES)

    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Empresas.csv", b"")
    with pytest.raises(SourceSchemaError, match="has no rows"):
        validate_archive(empty, COMPANIES)

    wrong_width = tmp_path / "wrong-width.zip"
    with zipfile.ZipFile(wrong_width, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Empresas.csv", b"one;two\n")
    with pytest.raises(SourceSchemaError, match="expected 7 fields"):
        validate_archive(wrong_width, COMPANIES)


def test_undefined_cp1252_byte_is_preserved_losslessly(tmp_path: Path) -> None:
    path = tmp_path / "Empresas0.zip"
    values = _row(COMPANIES, cnpj_basico="00000001", razao_social="placeholder")
    encoded = ";".join(values).encode("cp1252").replace(b"placeholder", b"A\x8fB") + b"\n"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Empresas0.csv", encoded)

    row = next(iter_contract_rows(path, COMPANIES))[2]
    assert row["razao_social"] == "A\x8fB"
    assert row["razao_social"].encode("latin-1") == b"A\x8fB"


def test_sample_and_bronze_load_are_relationship_preserving_and_idempotent(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    assert sample.row_counts == {
        "establishments": 40,
        "companies": 20,
        "partners": 10,
        "simples": 1,
        "cnae": 2,
    }
    mtimes = {dataset: path.stat().st_mtime_ns for dataset, path in sample.sample_files.items()}
    reused = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    assert reused.sample_id == sample.sample_id
    assert reused.row_counts == sample.row_counts
    assert {dataset: path.stat().st_mtime_ns for dataset, path in reused.sample_files.items()} == mtimes
    assert (next(iter(reused.sample_files.values())).parent / "sample_manifest.json").is_file()

    database = tmp_path / "cnpj_lakehouse.duckdb"
    first = load_bronze(database, sample, "202601")
    second = load_bronze(database, sample, "202601")
    assert first.skipped is False
    assert second.skipped is True
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("select count(*) from bronze.raw_companies").fetchone()[0] == 20
        assert connection.execute("select count(*) from ops.sample_manifests").fetchone()[0] == 1
        cnpj = connection.execute(
            "select distinct cnpj_basico from bronze.raw_companies order by 1"
        ).fetchall()
        assert cnpj == [("00000001",), ("00000002",)]
        raw_values = connection.execute(
            """
            select cnpj_basico, razao_social, natureza_juridica, qualificacao_responsavel,
                   capital_social_raw, porte_empresa, ente_federativo_responsavel, record_hash
            from bronze.raw_companies
            where cnpj_basico = '00000001'
            limit 1
            """
        ).fetchone()
        expected_hash = hashlib.sha256(
            json.dumps(raw_values[:-1], ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        assert raw_values[-1] == expected_hash


def test_optional_child_samples_can_be_header_only_and_load_as_empty(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    unrelated_partner = [_row(PARTNERS, cnpj_basico="99999999", nome_socio="Fora da amostra")]
    unrelated_simples = [_row(SIMPLES, cnpj_basico="99999999", opcao_simples="S")]
    for index in range(10):
        _write_archive(tmp_path, PARTNERS, f"Socios{index}.zip", unrelated_partner)
    _write_archive(tmp_path, SIMPLES, "Simples.zip", unrelated_simples)

    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    assert sample.row_counts[PARTNERS.dataset] == 0
    assert sample.row_counts[SIMPLES.dataset] == 0

    database = tmp_path / "cnpj_lakehouse.duckdb"
    result = load_bronze(database, sample, "202601")
    assert result.row_counts[PARTNERS.dataset] == 0
    assert result.row_counts[SIMPLES.dataset] == 0
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("select count(*) from bronze.raw_partners").fetchone()[0] == 0
        assert connection.execute("select count(*) from bronze.raw_simples").fetchone()[0] == 0


def test_sample_contains_raw_lineage_columns(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    with gzip.open(sample.sample_files[COMPANIES.dataset], "rt", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["source_file"] == "Empresas0.zip"
    assert row["source_url"].startswith("file:")


@pytest.mark.parametrize("value", ["1", "1234567", "ABC12345", "12-345-678", "123456789"])
def test_base_cnpj_never_manufactures_invalid_values(value: str) -> None:
    assert normalize_base_cnpj(value) is None


def test_tampered_completed_sample_is_quarantined_and_rebuilt(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    sample.sample_files[COMPANIES.dataset].write_bytes(b"tampered")
    rebuilt = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    assert rebuilt.sample_id == sample.sample_id
    assert rebuilt.sample_files[COMPANIES.dataset].read_bytes() != b"tampered"
    assert list((tmp_path / "samples").glob("sample_id=*.invalid-*"))


def test_demo_generator_creates_every_contract_valid_archive(tmp_path: Path) -> None:
    source_dir = tmp_path / "demo-source"
    archives = create_demo_sources(source_dir)

    assert len(archives) == 32
    assert DEMO_NOTICE in (source_dir / "DEMO_ONLY.json").read_text(encoding="utf-8")
    for source in resolve_local_sources(source_dir):
        contract = next(item for item in (ESTABLISHMENTS, COMPANIES, PARTNERS, SIMPLES, CNAE) if item.dataset == source.dataset)
        rows = list(iter_contract_rows(Path(source.location), contract))
        assert rows

    with pytest.raises(ValueError, match="must be empty"):
        create_demo_sources(source_dir)


def test_runtime_outputs_are_owner_only(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    download_directory = tmp_path / "runtime" / "downloads"
    downloaded = tuple(download_file(source, download_directory) for source in sources)
    sample = build_sample(downloaded, "202601", 2, tmp_path / "runtime" / "samples")
    database = tmp_path / "runtime" / "warehouse" / "cnpj_lakehouse.duckdb"
    load_bronze(database, sample, "202601")

    assert download_directory.stat().st_mode & 0o777 == 0o700
    assert all(item.path.stat().st_mode & 0o777 == 0o600 for item in downloaded)
    sample_directory = next(iter(sample.sample_files.values())).parent
    assert sample_directory.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in sample.sample_files.values())
    assert (sample_directory / "sample_manifest.json").stat().st_mode & 0o777 == 0o600
    assert database.parent.stat().st_mode & 0o777 == 0o700
    assert database.stat().st_mode & 0o777 == 0o600
