from __future__ import annotations

import json
import logging

import pytest

from cnpj_lakehouse.metrics import stage_timer


def test_stage_timer_logs_aggregate_rates(caplog: object) -> None:
    with caplog.at_level(logging.INFO, logger="cnpj_lakehouse.performance"), stage_timer(
        "sample", files=2
    ) as metric:  # type: ignore[union-attr]
        metric["bytes"] = 100
        metric["rows"] = 10
    message = next(record.message for record in caplog.records if "stage_metric=" in record.message)  # type: ignore[union-attr]
    details = json.loads(message.removeprefix("stage_metric="))
    assert details["stage"] == "sample"
    assert details["files"] == 2
    assert details["bytes_per_second"] > 0
    assert details["rows_per_second"] > 0
    assert details["status"] == "completed"
    assert details["started_at"] <= details["ended_at"]


def test_stage_timer_records_failure_without_suppressing_it(caplog: object) -> None:
    with pytest.raises(RuntimeError, match="expected"), caplog.at_level(
        logging.INFO, logger="cnpj_lakehouse.performance"
    ), stage_timer("sample"):
        raise RuntimeError("expected")
    message = next(record.message for record in caplog.records if "stage_metric=" in record.message)  # type: ignore[union-attr]
    assert json.loads(message.removeprefix("stage_metric="))["status"] == "failed"
