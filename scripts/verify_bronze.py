"""Verify a completed deterministic Bronze sample before dbt transformation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from cnpj_lakehouse.contracts import CONTRACTS

CHILD_TABLES = ("raw_establishments", "raw_partners", "raw_simples")
BRONZE_TABLES = ("raw_companies", *CHILD_TABLES, "raw_cnae")
LINEAGE_COLUMNS = (
    "source_file",
    "source_member",
    "source_url",
    "source_file_sha256",
    "source_row_number",
    "sample_id",
    "ingestion_batch_id",
    "ingested_at",
    "record_hash",
)


def _scalar(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[object]) -> int:
    return int(connection.execute(sql, parameters).fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expect-period", required=True)
    parser.add_argument("--expect-sample-size", type=int, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        raise SystemExit(f"warehouse does not exist: {args.database}")

    errors: list[str] = []
    counts: dict[str, int] = {}
    with duckdb.connect(str(args.database), read_only=True) as connection:
        manifest_rows = connection.execute(
            """
            select sample_id, row_counts_json
            from ops.sample_manifests
            where source_period = ?
            """,
            [args.expect_period],
        ).fetchall()
        if len(manifest_rows) != 1:
            errors.append(f"expected one completed manifest; found {len(manifest_rows)}")
        sample_id = manifest_rows[0][0] if len(manifest_rows) == 1 else None
        manifest_counts = json.loads(manifest_rows[0][1]) if len(manifest_rows) == 1 else {}

        distinct_companies = _scalar(
            connection,
            """
            select count(distinct cnpj_basico)
            from bronze.raw_companies
            where source_period = ? and sample_id = ?
            """,
            [args.expect_period, sample_id],
        )
        if distinct_companies != args.expect_sample_size:
            errors.append(
                f"expected {args.expect_sample_size} distinct companies; found {distinct_companies}"
            )

        for table in BRONZE_TABLES:
            counts[table] = _scalar(
                connection,
                f"select count(*) from bronze.{table} where source_period = ? and sample_id = ?",
                [args.expect_period, sample_id],
            )
            dataset = table.removeprefix("raw_")
            if manifest_counts.get(dataset) != counts[table]:
                errors.append(
                    f"{table} count {counts[table]} differs from manifest "
                    f"{manifest_counts.get(dataset)}"
                )
            null_predicate = " or ".join(f'"{column}" is null' for column in LINEAGE_COLUMNS)
            missing_lineage = _scalar(
                connection,
                f"""
                select count(*) from bronze.{table}
                where source_period = ? and sample_id = ? and ({null_predicate})
                """,
                [args.expect_period, sample_id],
            )
            if missing_lineage:
                errors.append(f"{table} has {missing_lineage} rows with incomplete lineage")
            duplicate_lineage = _scalar(
                connection,
                f"""
                select count(*) - count(distinct (source_file_sha256, source_member, source_row_number))
                from bronze.{table}
                where source_period = ? and sample_id = ?
                """,
                [args.expect_period, sample_id],
            )
            if duplicate_lineage:
                errors.append(f"{table} has {duplicate_lineage} duplicate physical-lineage rows")
            contract = next(item for item in CONTRACTS if item.table_name == table)
            raw_values = ", ".join(f'"{field}"' for field in contract.expected_fields)
            bad_hashes = _scalar(
                connection,
                f"""
                select count(*) from bronze.{table}
                where source_period = ? and sample_id = ?
                  and record_hash != sha256(to_json(list_value({raw_values})))
                """,
                [args.expect_period, sample_id],
            )
            if bad_hashes:
                errors.append(f"{table} has {bad_hashes} record hashes inconsistent with raw values")

        if counts["raw_cnae"] == 0:
            errors.append("raw_cnae is empty")
        for table in CHILD_TABLES:
            orphans = _scalar(
                connection,
                f"""
                select count(*)
                from bronze.{table} as child
                where child.source_period = ? and child.sample_id = ?
                  and not exists (
                    select 1
                    from bronze.raw_companies as company
                    where company.source_period = child.source_period
                      and company.sample_id = child.sample_id
                      and company.cnpj_basico = child.cnpj_basico
                  )
                """,
                [args.expect_period, sample_id],
            )
            if orphans:
                errors.append(f"{table} has {orphans} company-orphan rows")

    if errors:
        raise SystemExit("Bronze verification failed: " + "; ".join(errors))
    print(
        "Bronze verified: "
        f"period={args.expect_period}, sample_id={sample_id}, "
        f"companies={distinct_companies}, rows={json.dumps(counts, sort_keys=True)}"
    )


if __name__ == "__main__":
    main()
