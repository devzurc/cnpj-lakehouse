from datetime import UTC, datetime
from pathlib import Path

import pytest

from cnpj_lakehouse.settings import (
    DEMO_RUNTIME_ROOT,
    OFFICIAL_RUNTIME_ROOT,
    OPERATOR_RUNTIME_ROOT,
    assert_linux_native_path,
    default_pipeline_output_path,
    period_end,
    pipeline_run_dir,
    resolve_official_runtime_root,
    resolve_runtime_root,
    resolve_source_period,
    validate_ingestion_workers,
    warehouse_database_path,
)


def test_resolve_source_period_preserves_explicit_value() -> None:
    assert resolve_source_period("202601", now=datetime(2026, 3, 1, tzinfo=UTC)) == "202601"


def test_resolve_source_period_uses_prior_month_in_sao_paulo() -> None:
    # 02:30 UTC is still 23:30 of the prior local day in São Paulo.
    assert resolve_source_period(None, now=datetime(2026, 2, 1, 2, 30, tzinfo=UTC)) == "202512"


def test_resolve_source_period_handles_new_year_in_sao_paulo() -> None:
    assert resolve_source_period(None, now=datetime(2026, 1, 7, 12, tzinfo=UTC)) == "202512"


def test_reference_date_derives_from_resolved_period() -> None:
    assert period_end(resolve_source_period(None, now=datetime(2026, 3, 1, 3, 1, tzinfo=UTC))).isoformat() == "2026-02-28"


def test_assert_linux_native_path_rejects_windows_mount() -> None:
    with pytest.raises(ValueError, match="Linux-native"):
        assert_linux_native_path("/mnt/c/cnpj-output", label="output_path")


def test_operator_runtime_is_isolated_from_official_backfill_share() -> None:
    assert OPERATOR_RUNTIME_ROOT == DEMO_RUNTIME_ROOT
    assert OPERATOR_RUNTIME_ROOT.name == "cnpj-lakehouse"
    assert OFFICIAL_RUNTIME_ROOT.name == "cnpj-lakehouse-official"
    assert OFFICIAL_RUNTIME_ROOT != OPERATOR_RUNTIME_ROOT


def test_pipeline_run_dir_lives_under_runtime_run() -> None:
    assert pipeline_run_dir("/var/lib/cnpj-lakehouse") == Path("/var/lib/cnpj-lakehouse/run")


def test_default_pipeline_output_uses_runtime_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CNPJ_LAKEHOUSE_RUNTIME_ROOT", "/var/lib/cnpj-lakehouse-test")
    assert resolve_runtime_root() == Path("/var/lib/cnpj-lakehouse-test")
    assert default_pipeline_output_path() == Path("/var/lib/cnpj-lakehouse-test/run")


def test_official_runtime_defaults_to_isolated_share(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CNPJ_LAKEHOUSE_RUNTIME_ROOT", raising=False)
    assert resolve_official_runtime_root() == OFFICIAL_RUNTIME_ROOT.expanduser().resolve()


def test_official_runtime_rejects_demo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CNPJ_LAKEHOUSE_RUNTIME_ROOT", str(DEMO_RUNTIME_ROOT))
    with pytest.raises(ValueError, match="synthetic demo"):
        resolve_official_runtime_root()


def test_warehouse_path_is_canonical(tmp_path: Path) -> None:
    output = tmp_path / "run"
    expected = output / "warehouse" / "cnpj_lakehouse.duckdb"
    assert warehouse_database_path(output) == expected


def test_ingestion_worker_limit_rejects_direct_callers() -> None:
    with pytest.raises(ValueError, match="at most 4"):
        validate_ingestion_workers(5)
