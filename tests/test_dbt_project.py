from __future__ import annotations

import hashlib
import os
from pathlib import Path

import duckdb
import pytest
from dbt.cli.main import dbtRunner

from cnpj_lakehouse.tasks.download import DownloadedFile
from cnpj_lakehouse.tasks.load_duckdb import load_bronze
from cnpj_lakehouse.tasks.sample import build_sample
from cnpj_lakehouse.tasks.source_resolution import resolve_local_sources
from tests.test_bronze_pipeline import _create_required_archives

ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT = ROOT / "dbt"


def _run_dbt(arguments: list[str], environment: dict[str, str], target_path: Path) -> None:
    prior_values = {key: os.environ.get(key) for key in environment}
    os.environ.update(environment)
    try:
        result = dbtRunner().invoke(
            arguments
            + [
                "--project-dir",
                str(DBT_PROJECT),
                "--profiles-dir",
                str(DBT_PROJECT),
                "--target-path",
                str(target_path),
            ]
        )
    finally:
        for key, value in prior_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    assert result.success, result.exception


def test_dbt_models_snapshot_and_quality_gates(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    database = tmp_path / "cnpj_lakehouse.duckdb"
    load_bronze(database, sample, "202601")
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            update bronze.raw_partners
            set cnpj_cpf_socio = '12345678901', representante_legal = '10987654321'
            where cnpj_basico = '00000001'
            """
        )
    environment = os.environ | {
        "CNPJ_LAKEHOUSE_DUCKDB_PATH": str(database),
        "CNPJ_LAKEHOUSE_REFERENCE_DATE": "2026-01-31",
        "CNPJ_LAKEHOUSE_SOURCE_PERIOD": "202601",
        "CNPJ_LAKEHOUSE_SAMPLE_ID": sample.sample_id,
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    target_path = tmp_path / "dbt-target"
    _run_dbt(
        ["run", "--select", "path:models/staging path:models/intermediate"],
        environment,
        target_path,
    )
    _run_dbt(["snapshot"], environment, target_path)
    _run_dbt(["run", "--select", "path:models/marts"], environment, target_path)
    _run_dbt(["test"], environment, target_path)

    with duckdb.connect(str(database)) as connection:
        partner_documents = connection.execute(
            """
            select partner_document_pseudonym, legal_representative_document_pseudonym
            from silver.stg_partners
            where cnpj_basico = '00000001'
            """
        ).fetchone()
        silver_columns = {
            row[0]
            for row in connection.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'silver' and table_name = 'stg_partners'
                """
            ).fetchall()
        }
        representatives = connection.execute(
            """
            select cnpj_basico, principal_cnae, uf
            from silver.int_company_rollup
            order by cnpj_basico
            """
        ).fetchall()
    assert partner_documents == (
        "v1:" + hashlib.sha256(b"partner-document:12345678901").hexdigest(),
        "v1:" + hashlib.sha256(b"legal-representative-document:10987654321").hexdigest(),
    )
    assert "partner_document_raw" not in silver_columns
    assert "legal_representative_document_raw" not in silver_columns
    assert representatives == [
        ("00000001", "6201501", "SC"),
        ("00000002", "6201501", "SP"),
    ]

    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            insert into bronze.raw_companies
            select * replace (
                '2.000,00' as capital_social_raw,
                ? as sample_id,
                'batch-v2' as ingestion_batch_id,
                ingested_at + interval '1 second' as ingested_at,
                'record-v2' as record_hash
            )
            from bronze.raw_companies
            where cnpj_basico = '00000001'
            limit 1
            """,
            [sample.sample_id],
        )

    _run_dbt(
        ["run", "--select", "path:models/staging path:models/intermediate"],
        environment,
        target_path,
    )
    _run_dbt(["snapshot"], environment, target_path)
    _run_dbt(["run", "--select", "path:models/marts"], environment, target_path)
    with duckdb.connect(str(database)) as connection:
        history = connection.execute(
            """
            select count(*), count(*) filter (where dbt_valid_to is null)
            from snapshots.company_capital_social_snapshot
            where cnpj_basico = '00000001'
            """
        ).fetchone()
        first_fact_count = connection.execute(
            "select count(*) from gold.fct_company_activity_daily"
        ).fetchone()[0]
    assert history == (2, 1)

    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            insert into bronze.raw_establishments
            select * replace (
                '08' as situacao_cadastral,
                ? as sample_id,
                'batch-v3' as ingestion_batch_id,
                ingested_at + interval '2 seconds' as ingested_at,
                'record-v3' as record_hash
            )
            from bronze.raw_establishments
            where cnpj_basico = '00000002'
            """,
            [sample.sample_id],
        )

    _run_dbt(
        ["run", "--select", "path:models/staging path:models/intermediate"],
        environment,
        target_path,
    )
    _run_dbt(["run", "--select", "path:models/marts"], environment, target_path)

    _run_dbt(["run", "--select", "fct_company_activity_daily"], environment, target_path)
    with duckdb.connect(str(database)) as connection:
        second_fact_count = connection.execute(
            "select count(*) from gold.fct_company_activity_daily"
        ).fetchone()[0]
        duplicate_fact_keys = connection.execute(
            """
            select count(*)
            from (
                select reference_date, cnpj_basico
                from gold.fct_company_activity_daily
                group by 1, 2
                having count(*) > 1
            )
            """
        ).fetchone()[0]
    assert first_fact_count == 2
    assert second_fact_count == 1
    assert duplicate_fact_keys == 0


def test_staging_models_are_scoped_to_the_requested_bronze_batch(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    database = tmp_path / "cnpj_lakehouse.duckdb"
    load_bronze(database, sample, "202601")
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            insert into bronze.raw_companies
            select * replace (
                '9.000,00' as capital_social_raw,
                '202602' as source_period,
                'sample-202602' as sample_id,
                'batch-202602' as ingestion_batch_id,
                ingested_at + interval '1 day' as ingested_at,
                'record-202602' as record_hash
            ) from bronze.raw_companies where cnpj_basico = '00000001' limit 1
            """
        )
    environment = os.environ | {
        "CNPJ_LAKEHOUSE_DUCKDB_PATH": str(database),
        "CNPJ_LAKEHOUSE_REFERENCE_DATE": "2026-02-28",
        "CNPJ_LAKEHOUSE_SOURCE_PERIOD": "202602",
        "CNPJ_LAKEHOUSE_SAMPLE_ID": "sample-202602",
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    _run_dbt(["run", "--select", "stg_companies stg_simples"], environment, tmp_path / "dbt-target")
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("select capital_social from silver.stg_companies").fetchall() == [(9000,)]
        assert connection.execute("select count(*) from silver.stg_simples").fetchone() == (0,)


def test_invalid_non_empty_capital_social_fails_the_staging_quality_gate(tmp_path: Path) -> None:
    _create_required_archives(tmp_path)
    sources = resolve_local_sources(tmp_path)
    downloaded = tuple(
        DownloadedFile(source, Path(source.location), "fixture-checksum", Path(source.location).stat().st_size)
        for source in sources
    )
    sample = build_sample(downloaded, "202601", 2, tmp_path / "samples")
    database = tmp_path / "cnpj_lakehouse.duckdb"
    load_bronze(database, sample, "202601")
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            update bronze.raw_companies
            set capital_social_raw = '12x,00'
            where cnpj_basico = '00000001'
            """
        )
    environment = os.environ | {
        "CNPJ_LAKEHOUSE_DUCKDB_PATH": str(database),
        "CNPJ_LAKEHOUSE_REFERENCE_DATE": "2026-01-31",
        "CNPJ_LAKEHOUSE_SOURCE_PERIOD": "202601",
        "CNPJ_LAKEHOUSE_SAMPLE_ID": sample.sample_id,
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    target_path = tmp_path / "dbt-target"
    _run_dbt(["run", "--select", "stg_companies"], environment, target_path)
    with pytest.raises(AssertionError):
        _run_dbt(["test", "--select", "stg_companies"], environment, target_path)


@pytest.mark.parametrize(
    ("missing_name", "environment_name"),
    [
        ("source_period", "CNPJ_LAKEHOUSE_SOURCE_PERIOD"),
        ("sample_id", "CNPJ_LAKEHOUSE_SAMPLE_ID"),
        ("reference_date", "CNPJ_LAKEHOUSE_REFERENCE_DATE"),
    ],
)
def test_dbt_requires_every_active_batch_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing_name: str, environment_name: str
) -> None:
    environment = {
        "CNPJ_LAKEHOUSE_DUCKDB_PATH": str(tmp_path / "cnpj_lakehouse.duckdb"),
        "CNPJ_LAKEHOUSE_SOURCE_PERIOD": "202601",
        "CNPJ_LAKEHOUSE_SAMPLE_ID": "sample-fixture",
        "CNPJ_LAKEHOUSE_REFERENCE_DATE": "2026-01-31",
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    environment.pop(environment_name)
    for name in (
        "CNPJ_LAKEHOUSE_SOURCE_PERIOD",
        "CNPJ_LAKEHOUSE_SAMPLE_ID",
        "CNPJ_LAKEHOUSE_REFERENCE_DATE",
    ):
        monkeypatch.delenv(name, raising=False)
    prior_values = {key: os.environ.get(key) for key in environment}
    os.environ.update(environment)
    try:
        result = dbtRunner().invoke(
            [
                "compile",
                "--select",
                "stg_companies",
                "--project-dir",
                str(DBT_PROJECT),
                "--profiles-dir",
                str(DBT_PROJECT),
                "--target-path",
                str(tmp_path / "dbt-target"),
            ]
        )
    finally:
        for key, value in prior_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    assert not result.success
    assert f"Required active-batch input is blank: {missing_name}" in str(result.exception)
