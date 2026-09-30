"""Deterministic post-run verification for the local DuckDB warehouse."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def _one(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[object] | None = None) -> object:
    return connection.execute(sql, parameters or []).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expect-period", required=True)
    parser.add_argument("--expect-reference-date", required=True)
    parser.add_argument("--expect-sample-size", type=int, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        raise SystemExit(f"warehouse does not exist: {args.database}")

    with duckdb.connect(str(args.database), read_only=True) as connection:
        manifests = _one(
            connection,
            "select count(*) from ops.sample_manifests where source_period = ?",
            [args.expect_period],
        )
        distinct_companies = _one(
            connection,
            """
            select count(distinct cnpj_basico)
            from bronze.raw_companies
            where source_period = ?
            """,
            [args.expect_period],
        )
        fact_rows = _one(
            connection,
            "select count(*) from gold.fct_company_activity_daily where reference_date = cast(? as date)",
            [args.expect_reference_date],
        )
        invalid_facts = _one(
            connection,
            """
            select count(*)
            from gold.fct_company_activity_daily
            where reference_date = cast(? as date)
              and active_establishment_count <= 0
            """,
            [args.expect_reference_date],
        )
    errors: list[str] = []
    if manifests < 1:
        errors.append(f"no manifest for source period {args.expect_period}")
    if distinct_companies != args.expect_sample_size:
        errors.append(f"expected {args.expect_sample_size} companies; found {distinct_companies}")
    if fact_rows < 1:
        errors.append("Gold fact has no active-company rows")
    if invalid_facts:
        errors.append(f"Gold fact contains {invalid_facts} invalid active-company rows")
    if errors:
        raise SystemExit("Warehouse verification failed: " + "; ".join(errors))
    print(
        "Warehouse verified: "
        f"period={args.expect_period}, companies={distinct_companies}, active_fact_rows={fact_rows}"
    )


if __name__ == "__main__":
    main()
