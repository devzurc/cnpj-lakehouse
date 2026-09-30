from __future__ import annotations

import json
from pathlib import Path

import duckdb

from cnpj_lakehouse.dashboard import (
    DASHBOARD_CATALOG,
    activity_by_uf,
    available_partitions,
    capital_buckets,
    cnae_concentration,
    overview,
    regime_share,
)
from scripts.inspect_local_warehouse import inspect_warehouse
from tests.test_analytics_contract import _create_contract_warehouse


def test_dashboard_queries_gold_read_only_without_company_keys(tmp_path: Path) -> None:
    database = tmp_path / "warehouse.duckdb"
    _create_contract_warehouse(database)
    partitions = available_partitions(database)
    assert partitions == [{"reference_date": partitions[0]["reference_date"], "source_period": "202601", "sample_id": "sample"}]
    assert overview(database, "2026-01-31", "sample")["active_companies"] == 1
    assert activity_by_uf(database, "2026-01-31", "sample") == [
        {"uf": "SC", "active_companies": 1, "active_establishments": 1}
    ]
    assert all("cnpj_basico" not in columns for columns in DASHBOARD_CATALOG.values())
    assert regime_share(database, "2026-01-31", "sample") == {
        "active_companies": 1,
        "simples_companies": 1,
        "mei_companies": 0,
        "simples_unknown": 0,
        "mei_unknown": 0,
    }
    assert capital_buckets(database, "2026-01-31", "sample") == [
        {"bucket": "Até 1 mil", "active_companies": 1}
    ]
    concentration = cnae_concentration(database, "2026-01-31", "sample")
    assert concentration["top_cnae_share"] == 1.0
    assert concentration["top_cnae"][0]["cnae_code"] == "6201501"
    rendered = json.dumps(concentration)
    assert "cnpj_basico" not in rendered
    assert "00000001" not in rendered


def _create_inspection_warehouse(database: Path) -> None:
    with duckdb.connect(str(database)) as connection:
        for schema in ("bronze", "silver", "gold", "snapshots", "ops"):
            connection.execute(f"create schema {schema}")
        for table in ("raw_cnae", "raw_companies", "raw_establishments", "raw_partners", "raw_simples"):
            connection.execute(f"create table bronze.{table} (restricted_value varchar)")
            connection.execute(f"insert into bronze.{table} values ('00000001')")
        for table in ("stg_companies", "stg_establishments", "stg_partners", "stg_simples", "stg_cnae"):
            connection.execute(f"create table silver.{table} (restricted_value varchar)")
            connection.execute(f"insert into silver.{table} values ('00000001')")
        connection.execute("create table silver.int_company_rollup (source_period varchar, sample_id varchar)")
        connection.execute("insert into silver.int_company_rollup values ('202601', 'sample')")
        for table in ("dim_company_current", "dim_cnae", "dim_cnae_hierarchy"):
            connection.execute(f"create table gold.{table} (value varchar)")
            connection.execute(f"insert into gold.{table} values ('safe')")
        connection.execute("create table gold.fct_company_activity_daily (reference_date date, source_period varchar, sample_id varchar)")
        connection.execute("insert into gold.fct_company_activity_daily values (date '2026-01-31', '202601', 'sample')")
        connection.execute("create table snapshots.company_capital_social_snapshot (dbt_valid_to timestamp)")
        connection.execute("insert into snapshots.company_capital_social_snapshot values (null)")
        connection.execute("create table ops.sample_manifests (source_period varchar, sample_id varchar, row_counts_json varchar, ingested_at timestamp)")
        connection.execute("insert into ops.sample_manifests values ('202601', 'sample', ?, current_timestamp)", [json.dumps({"companies": 1})])


def test_inspector_reports_metadata_without_restricted_rows(tmp_path: Path) -> None:
    database = tmp_path / "inspection.duckdb"
    _create_inspection_warehouse(database)
    rendered = json.dumps(inspect_warehouse(database))
    assert "00000001" not in rendered
    assert '"raw_companies": 1' in rendered
    assert '"sample_id": "sample"' in rendered
    assert '"source_archives": []' in rendered
