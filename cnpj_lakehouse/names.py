"""Operator-facing names for the CNPJ Lakehouse."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

SAO_PAULO_TIMEZONE = "America/Sao_Paulo"

FLOW_NAME = "cnpj-lakehouse"
FLOW_DESCRIPTION = (
    "Ingere um lote mensal do CNPJ aberto (dados.gov.br): descobre o diretório YYYY-MM-DD "
    "no espelho, baixa os ZIPs, valida integridade, seleciona a amostra configurável "
    "(padrão 10.000 empresas em 1 job) com estabelecimentos/sócios/Simples, carrega "
    "Bronze e executa dbt Silver, snapshot de Capital Social, Gold e testes. Destino: DuckDB local."
)

DEPLOYMENT_NAME = "monthly-ingest"
DEPLOYMENT_DESCRIPTION = (
    "Automação mensal (dia 7 às 09:00 America/Sao_Paulo). Processa o mês calendário "
    "anterior, amostra configurável (padrão 10.000 em 1 job), sem fonte sintética. Falha "
    "visível se o lote ainda não existir no espelho. Rerun com o mesmo sample_id não duplica Bronze."
)

DEPLOYMENT_REF = f"{FLOW_NAME}/{DEPLOYMENT_NAME}"
FLOW_TAGS = ("cnpj", "lakehouse", "mensal")
DBT_TASK_RUN_NAMES = {
    "01-dbt-run-core": "executar-dbt-silver",
    "02-dbt-snapshot": "executar-dbt-snapshot",
    "03-dbt-run-marts": "executar-dbt-gold",
    "04-dbt-test": "executar-dbt-testes",
}


def dbt_task_run_name(*, parameters: dict[str, object]) -> str:
    """Operator-facing Prefect run name for one dbt stage."""
    label = str(parameters.get("artifact_label") or "")
    return DBT_TASK_RUN_NAMES.get(label, f"executar-dbt-{label}")


def lakehouse_flow_run_name(*_args: object, **_kwargs: object) -> str:
    """Stable, unique run name without vendor or random animal labels."""
    stamp = datetime.now(ZoneInfo(SAO_PAULO_TIMEZONE)).strftime("%Y%m%d-%H%M")
    return f"lakehouse-{stamp}"
