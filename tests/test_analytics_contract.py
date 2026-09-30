from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from scripts.verify_analytics_contract import verify_analytics_contract


def _create_contract_warehouse(database: Path, *, include_fact_uf: bool = True) -> None:
    fact_uf = ", uf varchar" if include_fact_uf else ""
    with duckdb.connect(str(database)) as connection:
        connection.execute("create schema gold")
        connection.execute(
            """
            create table gold.dim_company_current (
                cnpj_basico varchar, natureza_juridica varchar, porte_empresa varchar,
                capital_social decimal(18, 2), principal_cnae varchar, uf varchar,
                is_simples_nacional boolean, is_mei boolean, source_period varchar, sample_id varchar
            )
            """
        )
        connection.execute(
            "create table gold.dim_cnae (cnae_code varchar, cnae_description varchar, source_period varchar)"
        )
        connection.execute(
            """
            create table gold.dim_cnae_hierarchy (
                cnae_code varchar, division_code varchar, group_code varchar, class_code varchar,
                subclass_description varchar, source_period varchar
            )
            """
        )
        connection.execute(
            f"""
            create table gold.fct_company_activity_daily (
                reference_date date, cnpj_basico varchar, active_establishment_count integer,
                partner_count integer, capital_social decimal(18, 2), principal_cnae varchar{fact_uf},
                is_simples_nacional boolean, is_mei boolean, source_period varchar, sample_id varchar
            )
            """
        )
        connection.execute("insert into gold.dim_company_current values ('00000001', '2062', '01', 1, '6201501', 'SC', true, false, '202601', 'sample')")
        connection.execute("insert into gold.dim_cnae values ('6201501', 'Desenvolvimento', '202601')")
        connection.execute("insert into gold.dim_cnae_hierarchy values ('6201501', '62', '620', '62015', 'Desenvolvimento', '202601')")
        columns = "reference_date, cnpj_basico, active_establishment_count, partner_count, capital_social, principal_cnae"
        values = "date '2026-01-31', '00000001', 1, 0, 1, '6201501'"
        if include_fact_uf:
            columns += ", uf"
            values += ", 'SC'"
        connection.execute(
            f"insert into gold.fct_company_activity_daily ({columns}, is_simples_nacional, is_mei, source_period, sample_id) values ({values}, true, false, '202601', 'sample')"
        )


def test_analytics_contract_verifies_authorized_gold_shape(tmp_path: Path) -> None:
    database = tmp_path / "warehouse.duckdb"
    _create_contract_warehouse(database)
    assert verify_analytics_contract(database, "2026-01-31") == {
        "fact_rows": 1,
        "duplicate_company_keys": 0,
        "duplicate_cnae_keys": 0,
        "duplicate_fact_keys": 0,
        "missing_cnae": 0,
        "missing_hierarchy": 0,
    }


def test_analytics_contract_rejects_missing_published_column(tmp_path: Path) -> None:
    database = tmp_path / "warehouse.duckdb"
    _create_contract_warehouse(database, include_fact_uf=False)
    with pytest.raises(ValueError, match="fct_company_activity_daily is missing contract columns"):
        verify_analytics_contract(database, "2026-01-31")


def test_analytics_contract_rejects_bronze_only_warehouse(tmp_path: Path) -> None:
    database = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(database)):
        pass
    with pytest.raises(ValueError, match="dim_company_current is missing contract columns"):
        verify_analytics_contract(database, "2026-01-31")
