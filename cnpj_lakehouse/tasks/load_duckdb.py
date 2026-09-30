"""Append-only, idempotent loading of sampled source records into DuckDB Bronze."""

from __future__ import annotations

import csv
import gzip
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from cnpj_lakehouse.contracts import CONTRACTS, SourceContract
from cnpj_lakehouse.privacy import ensure_private_directory
from cnpj_lakehouse.tasks.dbt import warehouse_writer_lock
from cnpj_lakehouse.tasks.sample import SAMPLE_METADATA_FIELDS, SampleResult

RUNTIME_FIELDS = (
    "source_period",
    "sample_id",
    "ingestion_batch_id",
    "ingested_at",
    "record_hash",
)


@dataclass(frozen=True, slots=True)
class BronzeLoadResult:
    sample_id: str
    ingestion_batch_id: str | None
    row_counts: dict[str, int]
    skipped: bool


def completed_bronze(database_path: Path, sample_id: str) -> BronzeLoadResult | None:
    """Return a completed sample without opening a write transaction."""
    if not database_path.is_file():
        return None
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        table_exists = connection.execute(
            """
            select count(*)
            from information_schema.tables
            where table_schema = 'ops' and table_name = 'sample_manifests'
            """
        ).fetchone()[0]
        if not table_exists:
            return None
        existing = connection.execute(
            "SELECT row_counts_json FROM ops.sample_manifests WHERE sample_id = ?", [sample_id]
        ).fetchone()
        if existing is None:
            return None
        return BronzeLoadResult(sample_id, None, json.loads(existing[0]), skipped=True)
    finally:
        connection.close()


@dataclass(frozen=True, slots=True)
class PeriodSample:
    sample_id: str
    source_period: str
    row_counts: dict[str, int]
    distinct_companies: int


def _table_exists(connection: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    found = connection.execute(
        """
        select count(*)
        from information_schema.tables
        where table_schema = ? and table_name = ?
        """,
        [schema, table],
    ).fetchone()
    return bool(found and found[0])


def _distinct_companies(connection: duckdb.DuckDBPyConnection, source_period: str) -> int:
    """Count distinct CNPJ básicos without returning entity values."""
    if not _table_exists(connection, "bronze", "raw_companies"):
        return 0
    count = connection.execute(
        """
        select count(distinct cnpj_basico)
        from bronze.raw_companies
        where source_period = ?
        """,
        [source_period],
    ).fetchone()
    return int(count[0]) if count else 0


def list_period_samples(database_path: Path, source_period: str) -> tuple[PeriodSample, ...]:
    """Return Bronze manifests for one source period; never reads entity rows."""
    if not database_path.is_file():
        return ()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        if not _table_exists(connection, "ops", "sample_manifests"):
            return ()
        distinct_companies = _distinct_companies(connection, source_period)
        rows = connection.execute(
            """
            SELECT sample_id, source_period, row_counts_json
            FROM ops.sample_manifests
            WHERE source_period = ?
            ORDER BY sample_id
            """,
            [source_period],
        ).fetchall()
        return tuple(
            PeriodSample(sample_id, period, json.loads(row_counts), distinct_companies)
            for sample_id, period, row_counts in rows
        )
    finally:
        connection.close()


def reusable_bronze_for_cohort(
    database_path: Path, source_period: str, expected_companies: int
) -> BronzeLoadResult | None:
    """Reuse Bronze when this period already holds exactly the requested cohort.

    Matching uses distinct `cnpj_basico` (the sample size), not ZIP row counts.
    A different company count for the same period is a second sample (for example
    synthetic 3 vs official 10.000) and is refused so the warehouse is never mixed.
    """
    samples = list_period_samples(database_path, source_period)
    if not samples:
        return None
    if len(samples) == 1 and samples[0].distinct_companies == expected_companies:
        sample = samples[0]
        return BronzeLoadResult(sample.sample_id, None, sample.row_counts, skipped=True)
    loaded = ", ".join(
        (
            f"{sample.sample_id} (distinct_companies={sample.distinct_companies}, "
            f"company_rows={sample.row_counts.get('companies')})"
        )
        for sample in samples
    )
    raise RuntimeError(
        f"source_period {source_period} already has Bronze sample(s) {loaded}; "
        f"refusing a second cohort of {expected_companies} companies. "
        "Rerun with the same sample_size or reset the warehouse volumes."
    )


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_columns(contract: SourceContract) -> tuple[str, ...]:
    return contract.expected_fields + SAMPLE_METADATA_FIELDS + RUNTIME_FIELDS


def _create_objects(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    connection.execute("CREATE SCHEMA IF NOT EXISTS ops")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.sample_manifests (
            sample_id VARCHAR PRIMARY KEY,
            source_period VARCHAR NOT NULL,
            ingestion_batch_id VARCHAR NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL,
            row_counts_json VARCHAR NOT NULL
        )
        """
    )
    for contract in CONTRACTS:
        declarations: list[str] = [f"{_quote(field)} VARCHAR" for field in contract.expected_fields]
        declarations.extend(
            (
                '"source_file" VARCHAR NOT NULL',
                '"source_member" VARCHAR NOT NULL',
                '"source_row_number" BIGINT NOT NULL',
                '"source_url" VARCHAR NOT NULL',
                '"source_file_sha256" VARCHAR NOT NULL',
                '"source_period" VARCHAR NOT NULL',
                '"sample_id" VARCHAR NOT NULL',
                '"ingestion_batch_id" VARCHAR NOT NULL',
                '"ingested_at" TIMESTAMPTZ NOT NULL',
                '"record_hash" VARCHAR NOT NULL',
            )
        )
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS bronze.{_quote(contract.table_name)} ({', '.join(declarations)})"
        )


def _validate_sample_header(sample_file: Path, contract: SourceContract) -> None:
    expected_columns = contract.expected_fields + SAMPLE_METADATA_FIELDS
    with gzip.open(sample_file, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_columns:
            raise ValueError(f"sample CSV header does not match {contract.dataset} contract")


def _insert_rows(
    connection: duckdb.DuckDBPyConnection,
    contract: SourceContract,
    sample_file: Path,
    source_period: str,
    sample_id: str,
    ingestion_batch_id: str,
    ingested_at: datetime,
) -> int:
    _validate_sample_header(sample_file, contract)
    columns = _table_columns(contract)
    column_sql = ", ".join(_quote(column) for column in columns)
    source_columns = contract.expected_fields + SAMPLE_METADATA_FIELDS
    source_column_sql = ", ".join(_quote(column) for column in source_columns)
    raw_value_sql = ", ".join(_quote(column) for column in contract.expected_fields)
    connection.execute("DROP TABLE IF EXISTS temp.sample_import")
    connection.execute(
        """
        CREATE TEMP TABLE sample_import AS
        SELECT *
        FROM read_csv(?, header = true, all_varchar = true, compression = 'gzip', nullstr = '\\0')
        """,
        [str(sample_file)],
    )
    count = connection.execute("SELECT count(*) FROM temp.sample_import").fetchone()[0]
    connection.execute(
        f"""
        INSERT INTO bronze.{_quote(contract.table_name)} ({column_sql})
        SELECT
            {source_column_sql},
            ?, ?, ?, ?,
            sha256(to_json(list_value({raw_value_sql})))
        FROM temp.sample_import
        """,
        [source_period, sample_id, ingestion_batch_id, ingested_at],
    )
    connection.execute("DROP TABLE temp.sample_import")
    return count


def load_bronze(
    database_path: Path,
    sample: SampleResult,
    source_period: str,
) -> BronzeLoadResult:
    """Load one sample atomically, returning a no-op result if it already completed."""
    ensure_private_directory(database_path.parent)
    with warehouse_writer_lock(str(database_path)):
        connection = duckdb.connect(str(database_path))
        try:
            _create_objects(connection)
            existing = connection.execute(
            "SELECT row_counts_json FROM ops.sample_manifests WHERE sample_id = ?", [sample.sample_id]
            ).fetchone()
            if existing is not None:
                return BronzeLoadResult(
                sample_id=sample.sample_id,
                ingestion_batch_id=None,
                row_counts=json.loads(existing[0]),
                skipped=True,
                )

            ingestion_batch_id = str(uuid.uuid4())
            ingested_at = datetime.now(UTC)
            row_counts: dict[str, int] = {}
            connection.execute("BEGIN TRANSACTION")
            try:
                for contract in CONTRACTS:
                    row_counts[contract.dataset] = _insert_rows(
                        connection,
                        contract,
                        sample.sample_files[contract.dataset],
                        source_period,
                        sample.sample_id,
                        ingestion_batch_id,
                        ingested_at,
                    )
                if row_counts != sample.row_counts:
                    raise ValueError(f"Bronze row counts differ from sample manifest: {row_counts}")
                connection.execute(
                    """
                    INSERT INTO ops.sample_manifests
                    (sample_id, source_period, ingestion_batch_id, ingested_at, row_counts_json)
                VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        sample.sample_id,
                        source_period,
                        ingestion_batch_id,
                        ingested_at,
                        json.dumps(row_counts, sort_keys=True),
                    ],
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
            return BronzeLoadResult(sample.sample_id, ingestion_batch_id, row_counts, skipped=False)
        finally:
            connection.close()
            if database_path.exists():
                database_path.chmod(0o600)
