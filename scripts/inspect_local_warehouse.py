"""Print safe operational metadata for a local CNPJ DuckDB warehouse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

from cnpj_lakehouse.inventory import archive_inventory_from_run


def _counts(connection: duckdb.DuckDBPyConnection, schema: str, tables: tuple[str, ...]) -> dict[str, int]:
    return {
        table: int(connection.execute(f"select count(*) from {schema}.{table}").fetchone()[0])
        for table in tables
    }


def inspect_warehouse(database: Path) -> dict[str, Any]:
    """Read only safe counts, grains and partition metadata; never read entity rows."""
    if not database.is_file():
        raise ValueError(f"warehouse does not exist: {database}")
    with duckdb.connect(str(database), read_only=True) as connection:
        manifests = connection.execute(
            "select source_period, sample_id, row_counts_json from ops.sample_manifests order by ingested_at"
        ).fetchall()
        active_batch = connection.execute(
            "select source_period, sample_id, count(*) as company_count from silver.int_company_rollup group by 1, 2"
        ).fetchall()
        snapshot = connection.execute(
            """
            select count(*) as version_count,
                   sum(case when dbt_valid_to is null then 1 else 0 end) as current_version_count
            from snapshots.company_capital_social_snapshot
            """
        ).fetchone()
        partitions = connection.execute(
            """
            select reference_date, source_period, sample_id, count(*) as fact_rows
            from gold.fct_company_activity_daily group by 1, 2, 3
            order by reference_date desc, source_period desc, sample_id desc
            """
        ).fetchall()
        return {
            "bronze_row_counts": _counts(
                connection,
                "bronze",
                ("raw_cnae", "raw_companies", "raw_establishments", "raw_partners", "raw_simples"),
            ),
            "silver_row_counts": _counts(
                connection,
                "silver",
                ("stg_companies", "stg_establishments", "stg_partners", "stg_simples", "stg_cnae", "int_company_rollup"),
            ),
            "gold_row_counts": _counts(
                connection,
                "gold",
                ("dim_company_current", "dim_cnae", "dim_cnae_hierarchy", "fct_company_activity_daily"),
            ),
            "sample_manifests": [
                {"source_period": period, "sample_id": sample_id, "row_counts": json.loads(row_counts)}
                for period, sample_id, row_counts in manifests
            ],
            "active_batches": [
                {"source_period": period, "sample_id": sample_id, "company_count": count}
                for period, sample_id, count in active_batch
            ],
            "snapshot": {"version_count": snapshot[0], "current_version_count": snapshot[1]},
            "gold_partitions": [
                {"reference_date": str(date), "source_period": period, "sample_id": sample_id, "fact_rows": count}
                for date, period, sample_id, count in partitions
            ],
            "source_archives": archive_inventory_from_run(database.parent.parent),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_warehouse(args.database), indent=2, sort_keys=True))
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
