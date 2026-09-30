"""Small, aggregate-only runtime metrics for local pipeline stages."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from time import perf_counter

LOGGER = logging.getLogger("cnpj_lakehouse.performance")


@contextmanager
def stage_timer(stage: str, **dimensions: object) -> Iterator[dict[str, object]]:
    """Log a structured duration without exposing source rows or runtime paths."""
    details: dict[str, object] = {"stage": stage, "status": "completed", **dimensions}
    details["started_at"] = datetime.now(UTC).isoformat()
    started = perf_counter()
    try:
        yield details
    except Exception:
        # Keep the failure aggregate-only; the caller retains the actionable exception.
        details["status"] = "failed"
        raise
    finally:
        elapsed = perf_counter() - started
        duration = round(elapsed, 3)
        details["ended_at"] = datetime.now(UTC).isoformat()
        details["duration_seconds"] = duration
        if elapsed > 0:
            if isinstance(details.get("bytes"), int):
                details["bytes_per_second"] = round(details["bytes"] / elapsed, 3)
            if isinstance(details.get("rows"), int):
                details["rows_per_second"] = round(details["rows"] / elapsed, 3)
        LOGGER.info("stage_metric=%s", json.dumps(details, sort_keys=True))
