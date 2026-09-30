"""Long-running local Prefect deployment process."""

from __future__ import annotations

from prefect.client.schemas.schedules import CronSchedule

from cnpj_lakehouse.flows.cnpj_lakehouse import cnpj_lakehouse_flow
from cnpj_lakehouse.names import DEPLOYMENT_DESCRIPTION, DEPLOYMENT_NAME, FLOW_TAGS
from cnpj_lakehouse.settings import (
    SAO_PAULO_TIMEZONE,
    pipeline_run_dir,
    resolve_runtime_root,
)

MONTHLY_CRON = "0 9 7 * *"


def deployment_parameters(runtime_root: str | None = None) -> dict[str, object]:
    """Return monthly defaults. Sample size is resolved per run from env/file/defaults."""
    root = resolve_runtime_root(runtime_root)
    return {
        "source_period": None,
        "sample_size": None,
        "parallel_jobs": None,
        "output_path": str(pipeline_run_dir(root)),
        "full_refresh": False,
        "source_dir": None,
    }


def serve() -> None:
    """Register the monthly ingest deployment and serve runs until interrupted."""
    cnpj_lakehouse_flow.serve(
        name=DEPLOYMENT_NAME,
        description=DEPLOYMENT_DESCRIPTION,
        tags=list(FLOW_TAGS),
        schedules=[CronSchedule(cron=MONTHLY_CRON, timezone=SAO_PAULO_TIMEZONE)],
        parameters=deployment_parameters(),
    )
