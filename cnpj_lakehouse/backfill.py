"""Sequential monthly backfill against the remote CNPJ archive index."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

from cnpj_lakehouse.settings import (
    DEMO_RUNTIME_ROOT,
    RUNTIME_ROOT_ENV,
    assert_linux_native_path,
    period_end,
    pipeline_run_dir,
    validate_source_period,
    warehouse_database_path,
)
from cnpj_lakehouse.tasks.source_resolution import DEFAULT_ARCHIVE_INDEX, list_source_periods

REPO_ROOT = Path(__file__).resolve().parents[1]


def assert_isolated_runtime(runtime_root: Path | str) -> Path:
    """Reject Windows mounts and the synthetic demo share directory."""
    path = assert_linux_native_path(runtime_root, label=RUNTIME_ROOT_ENV)
    demo = DEMO_RUNTIME_ROOT.expanduser().resolve()
    if path.expanduser().resolve() == demo:
        raise ValueError(f"backfill must not use the synthetic demo runtime: {demo}")
    return path


def periods_for_year(
    year: int,
    *,
    from_period: str | None = None,
    base_url: str = DEFAULT_ARCHIVE_INDEX,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, ...]:
    periods = list_source_periods(year, base_url, transport=transport)
    if from_period is not None:
        start = validate_source_period(from_period)
        periods = tuple(period for period in periods if period >= start)
    return periods


def verify_period(database: Path, source_period: str, sample_size: int) -> None:
    """Run the tracked verifiers for one month-end Gold partition."""
    reference_date = period_end(source_period).isoformat()
    commands = (
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "verify_bronze.py"),
            "--database",
            str(database),
            "--expect-period",
            source_period,
            "--expect-sample-size",
            str(sample_size),
        ],
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "verify_warehouse.py"),
            "--database",
            str(database),
            "--expect-period",
            source_period,
            "--expect-reference-date",
            reference_date,
            "--expect-sample-size",
            str(sample_size),
        ],
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "verify_analytics_contract.py"),
            "--database",
            str(database),
            "--expect-reference-date",
            reference_date,
        ],
    )
    for command in commands:
        subprocess.run(command, check=True)


def run_year_backfill(
    year: int,
    *,
    runtime_root: Path | str,
    sample_size: int = 10_000,
    ingestion_workers: int | None = None,
    from_period: str | None = None,
    base_url: str = DEFAULT_ARCHIVE_INDEX,
    transport: httpx.BaseTransport | None = None,
    run_pipeline: Callable[..., object] | None = None,
    verify_period_fn: Callable[[Path, str, int], None] | None = None,
    skip_verify: bool = False,
) -> tuple[str, ...]:
    """Download, sample, transform and verify each unambiguous month in `year`."""
    root = assert_isolated_runtime(runtime_root)
    output_path = pipeline_run_dir(root)
    periods = periods_for_year(
        year, from_period=from_period, base_url=base_url, transport=transport
    )
    if not periods:
        raise ValueError(f"no unambiguous source periods found for {year}")
    if run_pipeline is None:
        from cnpj_lakehouse.flows.cnpj_lakehouse import run_local_pipeline

        run_pipeline = run_local_pipeline
    verifier = verify_period if verify_period_fn is None else verify_period_fn
    for period in periods:
        run_pipeline(
            source_period=period,
            sample_size=sample_size,
            parallel_jobs=1,
            ingestion_workers=ingestion_workers,
            output_path=str(output_path),
            reference_date=None,
            full_refresh=False,
            source_dir=None,
            base_url=base_url,
            run_dbt_steps=True,
        )
        if not skip_verify:
            verifier(warehouse_database_path(output_path), period, sample_size)
    return periods
