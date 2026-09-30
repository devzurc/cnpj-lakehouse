"""Loopback-only Gold dashboard for the local analytical warehouse."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import duckdb

DATABASE_ENV = "CNPJ_LAKEHOUSE_DUCKDB_PATH"

# The UI intentionally omits technical company keys even though some are valid
# join keys in the broader analytics contract.
DASHBOARD_CATALOG: dict[str, tuple[str, ...]] = {
    "gold.dim_company_current": (
        "natureza_juridica",
        "porte_empresa",
        "capital_social",
        "principal_cnae",
        "uf",
        "is_simples_nacional",
        "is_mei",
        "source_period",
        "sample_id",
    ),
    "gold.dim_cnae": ("cnae_code", "cnae_description", "source_period"),
    "gold.dim_cnae_hierarchy": (
        "cnae_code",
        "division_code",
        "group_code",
        "class_code",
        "subclass_description",
        "source_period",
    ),
    "gold.fct_company_activity_daily": (
        "reference_date",
        "active_establishment_count",
        "partner_count",
        "capital_social",
        "principal_cnae",
        "uf",
        "is_simples_nacional",
        "is_mei",
        "source_period",
        "sample_id",
    ),
}


def configured_database() -> Path:
    """Return an existing local warehouse selected by environment variable."""
    value = os.environ.get("CNPJ_LAKEHOUSE_DUCKDB_PATH") or os.environ.get("CNPJ_LAKEHOUSE_DUCKDB_PATH")
    if not value:
        raise ValueError("set CNPJ_LAKEHOUSE_DUCKDB_PATH to the local warehouse path")
    database = Path(value).expanduser().resolve()
    if not database.is_file():
        raise ValueError(f"warehouse does not exist: {database}")
    return database


def _rows(database: Path, sql: str, parameters: list[object] | None = None) -> list[dict[str, Any]]:
    with duckdb.connect(str(database), read_only=True) as connection:
        cursor = connection.execute(sql, parameters or [])
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def available_partitions(database: Path) -> list[dict[str, Any]]:
    return _rows(
        database,
        """
        select distinct reference_date, source_period, sample_id
        from gold.fct_company_activity_daily
        order by reference_date desc, source_period desc, sample_id desc
        """,
    )


def overview(database: Path, reference_date: str, sample_id: str) -> dict[str, Any]:
    rows = _rows(
        database,
        """
        select count(*) as active_companies,
               coalesce(sum(active_establishment_count), 0) as active_establishments,
               coalesce(sum(partner_count), 0) as partners,
               coalesce(sum(capital_social), 0) as total_capital_social
        from gold.fct_company_activity_daily
        where reference_date = cast(? as date) and sample_id = ?
        """,
        [reference_date, sample_id],
    )
    return rows[0]


def activity_by_uf(database: Path, reference_date: str, sample_id: str) -> list[dict[str, Any]]:
    return _rows(
        database,
        """
        select coalesce(uf, 'Não informado') as uf,
               count(*) as active_companies,
               sum(active_establishment_count) as active_establishments
        from gold.fct_company_activity_daily
        where reference_date = cast(? as date) and sample_id = ?
        group by 1 order by active_companies desc, uf
        """,
        [reference_date, sample_id],
    )


def activity_by_cnae(database: Path, reference_date: str, sample_id: str) -> list[dict[str, Any]]:
    return _rows(
        database,
        """
        select fact.principal_cnae as cnae_code,
               hierarchy.subclass_description,
               count(*) as active_companies
        from gold.fct_company_activity_daily as fact
        left join gold.dim_cnae_hierarchy as hierarchy
          on fact.principal_cnae = hierarchy.cnae_code
        where fact.reference_date = cast(? as date) and fact.sample_id = ?
        group by 1, 2 order by active_companies desc, cnae_code
        """,
        [reference_date, sample_id],
    )


def regime_share(database: Path, reference_date: str, sample_id: str) -> dict[str, Any]:
    rows = _rows(
        database,
        """
        select count(*) as active_companies,
               count(*) filter (where is_simples_nacional) as simples_companies,
               count(*) filter (where is_mei) as mei_companies,
               count(*) filter (where is_simples_nacional is null) as simples_unknown,
               count(*) filter (where is_mei is null) as mei_unknown
        from gold.fct_company_activity_daily
        where reference_date = cast(? as date) and sample_id = ?
        """,
        [reference_date, sample_id],
    )
    return rows[0]


def capital_buckets(database: Path, reference_date: str, sample_id: str) -> list[dict[str, Any]]:
    return _rows(
        database,
        """
        select case
                 when capital_social is null then 'Não informado'
                 when capital_social < 1000 then 'Até 1 mil'
                 when capital_social < 10000 then '1 mil a 10 mil'
                 when capital_social < 100000 then '10 mil a 100 mil'
                 when capital_social < 1000000 then '100 mil a 1 milhão'
                 else '1 milhão ou mais'
               end as bucket,
               count(*) as active_companies
        from gold.fct_company_activity_daily
        where reference_date = cast(? as date) and sample_id = ?
        group by 1
        order by active_companies desc, bucket
        """,
        [reference_date, sample_id],
    )


def cnae_concentration(database: Path, reference_date: str, sample_id: str) -> dict[str, Any]:
    ranked = activity_by_cnae(database, reference_date, sample_id)
    total = sum(int(row["active_companies"]) for row in ranked)
    top = ranked[:5]
    top_companies = sum(int(row["active_companies"]) for row in top)
    return {
        "active_companies": total,
        "top_cnae_companies": top_companies,
        "top_cnae_share": (top_companies / total) if total else 0.0,
        "top_cnae": top,
    }


def cnae_catalog(database: Path, source_period: str) -> list[dict[str, Any]]:
    return _rows(
        database,
        """
        select cnae_code, cnae_description, source_period
        from gold.dim_cnae
        where source_period = ?
        order by cnae_code
        """,
        [source_period],
    )


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="CNPJ Lakehouse", layout="wide")
    st.title("CNPJ Lakehouse")
    st.caption(
        "Leitura local em Gold; Bronze, Silver, snapshots e ops não são exibidos. "
        "Este lote já está materializado: um rerun com o mesmo período e o mesmo tamanho de amostra "
        "reutiliza a Bronze e os ZIPs locais e não duplica linhas. "
        "Quick run de monthly-ingest sem source_period resolve o mês calendário anterior "
        "(não o lote desta tela) e só baixa arquivos ainda ausentes."
    )
    try:
        database = configured_database()
        partitions = available_partitions(database)
    except (ValueError, duckdb.Error) as error:
        st.error(str(error))
        st.stop()
    if not partitions:
        st.warning("Não há partições Gold disponíveis neste warehouse.")
        st.stop()

    labels = [f"{item['reference_date']} · {item['source_period']} · {item['sample_id']}" for item in partitions]
    selected = partitions[st.selectbox("Partição Gold", range(len(partitions)), format_func=labels.__getitem__)]
    reference_date = str(selected["reference_date"])
    sample_id = str(selected["sample_id"])
    source_period = str(selected["source_period"])
    st.caption(f"Período {source_period} · amostra {sample_id} · referência {reference_date}")
    summary = overview(database, reference_date, sample_id)
    regime = regime_share(database, reference_date, sample_id)
    companies = int(summary["active_companies"] or 0)
    metrics = st.columns(4)
    metrics[0].metric("Empresas ativas", summary["active_companies"])
    metrics[1].metric("Estabelecimentos ativos", summary["active_establishments"])
    metrics[2].metric("Sócios", summary["partners"])
    metrics[3].metric("Capital social total", summary["total_capital_social"])
    share = st.columns(2)
    simples = int(regime["simples_companies"] or 0)
    mei = int(regime["mei_companies"] or 0)
    share[0].metric("Simples Nacional", f"{(simples / companies):.0%}" if companies else "—")
    share[1].metric("MEI", f"{(mei / companies):.0%}" if companies else "—")

    left, right = st.columns(2)
    with left:
        st.subheader("Atividade por UF")
        st.bar_chart(activity_by_uf(database, reference_date, sample_id), x="uf", y="active_companies")
    with right:
        st.subheader("Capital social")
        st.bar_chart(capital_buckets(database, reference_date, sample_id), x="bucket", y="active_companies")
    concentration = cnae_concentration(database, reference_date, sample_id)
    st.subheader("Atividade por CNAE")
    if companies:
        st.caption(
            f"Os cinco CNAEs principais concentram {concentration['top_cnae_share']:.0%} "
            "das empresas ativas desta partição."
        )
    st.dataframe(activity_by_cnae(database, reference_date, sample_id), width="stretch")
    st.subheader("Domínio CNAE")
    st.dataframe(cnae_catalog(database, str(selected["source_period"])), width="stretch")
    st.subheader("Catálogo de consumo")
    st.dataframe(
        [{"relation": relation, "columns": ", ".join(columns)} for relation, columns in DASHBOARD_CATALOG.items()],
        width="stretch",
    )


def serve() -> None:
    """Start Streamlit bound to loopback only."""
    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).resolve()),
        f"--server.address={os.environ.get('CNPJ_LAKEHOUSE_DASHBOARD_ADDRESS', os.environ.get('CNPJ_LAKEHOUSE_DASHBOARD_ADDRESS', '127.0.0.1'))}",
        f"--server.port={os.environ.get('CNPJ_LAKEHOUSE_DASHBOARD_PORT', os.environ.get('CNPJ_LAKEHOUSE_DASHBOARD_PORT', '8501'))}",
        "--server.headless=true",
    ]
    streamlit_cli.main()


if __name__ == "__main__":
    main()
