from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest

from cnpj_lakehouse.backfill import (
    assert_isolated_runtime,
    periods_for_year,
    run_year_backfill,
)
from cnpj_lakehouse.settings import DEMO_RUNTIME_ROOT
from cnpj_lakehouse.tasks.source_resolution import list_source_periods

INDEX_HTML = """
<a href="2026-01-11/">jan</a>
<a href="2026-02-20/">feb</a>
<a href="2026-03-01/">mar1</a>
<a href="2026-03-16/">mar2</a>
<a href="2025-12-14/">prev</a>
"""


def test_list_source_periods_keeps_unique_months_and_skips_ambiguous() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=INDEX_HTML))
    assert list_source_periods(2026, "https://example.test/archives/", transport=transport) == (
        "202601",
        "202602",
    )


def test_list_source_periods_rejects_invalid_year() -> None:
    with pytest.raises(ValueError, match="2000"):
        list_source_periods(1999, "https://example.test/archives/")


def test_list_source_periods_propagates_http_404() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        list_source_periods(2026, "https://example.test/archives/", transport=transport)


def test_periods_for_year_honors_from_period() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=INDEX_HTML))
    assert periods_for_year(
        2026, from_period="202602", base_url="https://example.test/archives/", transport=transport
    ) == ("202602",)


def test_backfill_refuses_demo_runtime() -> None:
    with pytest.raises(ValueError, match="synthetic demo"):
        assert_isolated_runtime(DEMO_RUNTIME_ROOT)


def test_backfill_refuses_mnt_runtime() -> None:
    with pytest.raises(ValueError, match="/mnt"):
        assert_isolated_runtime("/mnt/c/cnpj-output")


def test_run_year_backfill_is_sequential(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "cnpj_lakehouse.backfill.list_source_periods",
        lambda year, base_url, transport=None: ("202601", "202602", "202603"),
    )

    def fake_run(**kwargs: object) -> None:
        calls.append(("run", str(kwargs["source_period"])))
        assert kwargs["sample_size"] == 10_000
        assert kwargs["parallel_jobs"] == 1
        assert kwargs["ingestion_workers"] == 2

    def fake_verify(_database: Path, period: str, sample_size: int) -> None:
        calls.append(("verify", period))
        assert sample_size == 10_000

    monkeypatch.setenv("CNPJ_LAKEHOUSE_PARALLEL_JOBS", "4")
    monkeypatch.setenv("CNPJ_LAKEHOUSE_SAMPLE_SIZE", "5000")

    periods = run_year_backfill(
        2026,
        runtime_root=tmp_path / "lakehouse",
        from_period="202602",
        ingestion_workers=2,
        run_pipeline=fake_run,
        verify_period_fn=fake_verify,
    )
    assert periods == ("202602", "202603")
    assert calls == [
        ("run", "202602"),
        ("verify", "202602"),
        ("run", "202603"),
        ("verify", "202603"),
    ]


def test_run_year_backfill_requires_at_least_one_period(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cnpj_lakehouse.backfill.list_source_periods",
        lambda year, base_url, transport=None: (),
    )
    with pytest.raises(ValueError, match="no unambiguous source periods"):
        run_year_backfill(2026, runtime_root=tmp_path / "lakehouse", skip_verify=True)


def test_backfill_script_is_executable_and_isolated() -> None:
    script = Path("scripts/backfill.sh")
    assert script.is_file()
    assert script.stat().st_mode & 0o111
    subprocess.run(["bash", "-n", str(script)], check=True)
    text = script.read_text(encoding="utf-8")
    runtime_lib = Path("scripts/lib/runtime.sh").read_text(encoding="utf-8")
    assert "/mnt/*" in text
    assert 'source "$script_dir/lib/runtime.sh"' in text
    assert 'cnpj_official_runtime_root' in runtime_lib
    assert 'runtime_root="$(cnpj_official_runtime_root)"' in text
    assert "cnpj_default_runtime_root" not in text
    assert 'demo_root="$HOME/.local/share/cnpj-lakehouse"' in text
    assert "cnpj-lakehouse-official" in runtime_lib
    assert "synthetic demo runtime" in text
    assert "backfill-year" in text
    assert "local.sh wait" in text
    assert "inspect_local_warehouse.py" in text
    assert "uv run cnpj-lakehouse" in text
