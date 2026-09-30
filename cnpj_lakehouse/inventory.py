"""Operator inventory of contracted archives versus completed Bronze cohorts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cnpj_lakehouse.settings import output_layout, validate_source_period
from cnpj_lakehouse.tasks.load_duckdb import list_period_samples, reusable_bronze_for_cohort
from cnpj_lakehouse.tasks.source_resolution import expected_source_filenames


def classify_download_dir(download_dir: Path) -> dict[str, Any]:
    """Compare the 32 contracted ZIP names against files already on disk."""
    expected = expected_source_filenames()
    present = [
        name
        for name in expected
        if (download_dir / name).is_file() and (download_dir / name).stat().st_size > 0
    ]
    present_set = set(present)
    missing = [name for name in expected if name not in present_set]
    return {
        "required": len(expected),
        "present": present,
        "missing": missing,
        "needs_download": bool(missing),
    }


def archive_inventory_from_run(run_dir: Path) -> list[dict[str, Any]]:
    """Scan `bronze/downloads/source_period=*` without reading restricted rows."""
    root = run_dir / "bronze" / "downloads"
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("source_period=*")):
        if not path.is_dir():
            continue
        period = path.name.removeprefix("source_period=")
        rows.append({"source_period": period, **classify_download_dir(path)})
    return rows


def plan_local_ingestion(
    output_path: Path,
    source_period: str,
    expected_companies: int,
) -> dict[str, Any]:
    """Report present archives, missing archives, Bronze samples, and the next action."""
    source_period = validate_source_period(source_period)
    layout = output_layout(output_path, source_period)
    archives = classify_download_dir(layout["downloads"])
    samples = [
        {
            "sample_id": sample.sample_id,
            "companies": sample.row_counts.get("companies"),
            "distinct_companies": sample.distinct_companies,
            "row_counts": sample.row_counts,
        }
        for sample in list_period_samples(layout["warehouse"], source_period)
    ]
    conflict: str | None = None
    reuse_bronze = False
    try:
        reused = reusable_bronze_for_cohort(
            layout["warehouse"], source_period, expected_companies
        )
        reuse_bronze = reused is not None
    except RuntimeError as error:
        conflict = str(error)
    if conflict:
        action = "conflict"
    elif reuse_bronze:
        action = "reuse_bronze"
    elif archives["needs_download"]:
        action = "download_missing"
    else:
        action = "ingest_present_archives"
    return {
        "action": action,
        "archives": archives,
        "bronze_samples": samples,
        "conflict": conflict,
        "expected_companies": expected_companies,
        "reuse_bronze": reuse_bronze,
        "source_period": source_period,
    }
