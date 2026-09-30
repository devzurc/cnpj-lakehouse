"""Verify the read-only Gold contract used by a future local visualization."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ANALYTICS_CONTRACT: dict[str, frozenset[str]] = {
    "dim_company_current": frozenset(
        {
            "cnpj_basico",
            "natureza_juridica",
            "porte_empresa",
            "capital_social",
            "principal_cnae",
            "uf",
            "is_simples_nacional",
            "is_mei",
            "source_period",
            "sample_id",
        }
    ),
    "dim_cnae": frozenset({"cnae_code", "cnae_description", "source_period"}),
    "dim_cnae_hierarchy": frozenset(
        {
            "cnae_code",
            "division_code",
            "group_code",
            "class_code",
            "subclass_description",
            "source_period",
        }
    ),
    "fct_company_activity_daily": frozenset(
        {
            "reference_date",
            "cnpj_basico",
            "active_establishment_count",
            "partner_count",
            "capital_social",
            "principal_cnae",
            "uf",
            "is_simples_nacional",
            "is_mei",
            "source_period",
            "sample_id",
        }
    ),
}
BLOCKED_ANALYTICS_COLUMNS = frozenset(
    {
        "razao_social",
        "cnpj_cpf_socio",
        "nome_socio",
        "correio_eletronico",
        "telefone_1",
        "telefone_2",
        "logradouro",
        "cep",
        "dbt_invocation_id",
        "dbt_updated_at",
    }
)


def _count(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[object]) -> int:
    return int(connection.execute(sql, parameters).fetchone()[0])


def verify_analytics_contract(database: Path, reference_date: str) -> dict[str, int]:
    """Validate Gold contract shape and the selected fact partition in read-only mode."""
    if not database.is_file():
        raise ValueError(f"warehouse does not exist: {database}")
    if any(columns & BLOCKED_ANALYTICS_COLUMNS for columns in ANALYTICS_CONTRACT.values()):
        raise ValueError("analytics contract exposes a blocked column")

    with duckdb.connect(str(database), read_only=True) as connection:
        columns_by_table: dict[str, set[str]] = {}
        for table_name, column_name in connection.execute(
            """
            select table_name, column_name
            from information_schema.columns
            where table_schema = 'gold'
            """
        ).fetchall():
            columns_by_table.setdefault(table_name, set()).add(column_name)
        for table_name, required_columns in ANALYTICS_CONTRACT.items():
            missing = required_columns - columns_by_table.get(table_name, set())
            if missing:
                raise ValueError(f"gold.{table_name} is missing contract columns: {sorted(missing)}")

        duplicate_company_keys = _count(
            connection,
            """
            select count(*) from (
                select cnpj_basico from gold.dim_company_current group by 1 having count(*) > 1
            )
            """,
            [],
        )
        duplicate_cnae_keys = _count(
            connection,
            """
            select count(*) from (
                select cnae_code from gold.dim_cnae group by 1 having count(*) > 1
            )
            """,
            [],
        )
        duplicate_fact_keys = _count(
            connection,
            """
            select count(*) from (
                select reference_date, cnpj_basico
                from gold.fct_company_activity_daily
                where reference_date = cast(? as date)
                group by 1, 2 having count(*) > 1
            )
            """,
            [reference_date],
        )
        missing_cnae = _count(
            connection,
            """
            select count(*)
            from gold.fct_company_activity_daily as fact
            left join gold.dim_cnae as cnae on fact.principal_cnae = cnae.cnae_code
            where fact.reference_date = cast(? as date)
              and fact.principal_cnae is not null
              and cnae.cnae_code is null
            """,
            [reference_date],
        )
        missing_hierarchy = _count(
            connection,
            """
            select count(*)
            from gold.dim_cnae_hierarchy as hierarchy
            left join gold.dim_cnae as cnae on hierarchy.cnae_code = cnae.cnae_code
            where cnae.cnae_code is null
            """,
            [],
        )
        fact_rows = _count(
            connection,
            "select count(*) from gold.fct_company_activity_daily where reference_date = cast(? as date)",
            [reference_date],
        )

    violations = {
        "duplicate_company_keys": duplicate_company_keys,
        "duplicate_cnae_keys": duplicate_cnae_keys,
        "duplicate_fact_keys": duplicate_fact_keys,
        "missing_cnae": missing_cnae,
        "missing_hierarchy": missing_hierarchy,
    }
    failed = {name: count for name, count in violations.items() if count}
    if fact_rows == 0:
        failed["fact_rows"] = 0
    if failed:
        raise ValueError(f"analytics contract verification failed: {failed}")
    return {"fact_rows": fact_rows, **violations}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expect-reference-date", required=True)
    args = parser.parse_args()
    try:
        result = verify_analytics_contract(args.database, args.expect_reference_date)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"Analytics contract verified: reference_date={args.expect_reference_date}, {result}")


if __name__ == "__main__":
    main()
