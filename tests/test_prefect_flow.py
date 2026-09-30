from __future__ import annotations

import json
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from cnpj_lakehouse.flows.cnpj_lakehouse import (
    build_relationship_preserving_sample,
    cnpj_lakehouse_flow,
    download_source_files,
    ensure_remote_download_capacity,
    load_bronze_task,
    resolve_sources,
    reusable_source_manifest,
    run_dbt_task,
    run_local_pipeline,
    validate_analytics_contract_task,
    validate_archives,
)
from cnpj_lakehouse.names import DBT_TASK_RUN_NAMES
from cnpj_lakehouse.serve import MONTHLY_CRON, deployment_parameters, serve
from cnpj_lakehouse.tasks.dbt import run_dbt, warehouse_writer_lock
from tests.test_bronze_pipeline import _create_required_archives


def test_prefect_tasks_load_a_local_fixture_without_dbt(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)

    output = tmp_path / "output"
    resolved = resolve_sources.fn("202601", str(sources), "unused")
    downloaded = download_source_files.fn(resolved, str(output / "downloads"))
    validation = validate_archives.fn(downloaded, "202601", str(output / "manifests"))
    sample = build_relationship_preserving_sample.fn(downloaded, "202601", 2, str(output / "samples"))
    result = load_bronze_task.fn(str(output / "warehouse" / "cnpj_lakehouse.duckdb"), sample, "202601")

    assert result.skipped is False
    assert result.row_counts["companies"] == 20
    assert validation["Empresas0.zip"] == 2
    manifest = json.loads((output / "downloads" / "download_manifest.json").read_text())
    assert manifest["official_dataset"].startswith("https://dados.gov.br/")
    source_manifests = list(output.glob("manifests/manifest_id=*/source_manifest.json"))
    assert len(source_manifests) == 1
    source_manifest = json.loads(source_manifests[0].read_text(encoding="utf-8"))
    assert source_manifest["source_period"] == "202601"
    assert len(source_manifest["files"]) == 32
    assert all(item["sha256"] and item["members"] for item in source_manifest["files"])

    validate_archives.fn(downloaded, "202601", str(output / "manifests"))
    assert list(output.glob("manifests/manifest_id=*/source_manifest.json")) == source_manifests

    source_manifest["files"][0]["row_count"] = 0
    source_manifests[0].write_text(json.dumps(source_manifest), encoding="utf-8")
    assert reusable_source_manifest(downloaded, "202601", output / "manifests") is None


def test_direct_local_runner_avoids_ephemeral_prefect_api(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    result = run_local_pipeline(
        source_period="202601",
        sample_size=2,
        output_path=str(tmp_path / "output"),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=False,
        ingestion_workers=1,
    )
    assert result.skipped is False
    assert (tmp_path / "output" / "warehouse" / "cnpj_lakehouse.duckdb").is_file()


def test_direct_local_runner_resolves_automatic_period_before_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    monkeypatch.setattr("cnpj_lakehouse.flows.cnpj_lakehouse.resolve_source_period", lambda _: "202512")
    result = run_local_pipeline(
        source_period=None,
        sample_size=2,
        output_path=str(tmp_path / "output"),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=False,
        ingestion_workers=1,
    )
    assert result.skipped is False
    assert (tmp_path / "output" / "bronze" / "samples" / "source_period=202512").is_dir()


def test_direct_local_runner_rejects_windows_mount(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Linux-native"):
        run_local_pipeline(
            source_period="202601",
            sample_size=2,
            output_path="/mnt/c/cnpj-output",
            reference_date=None,
            full_refresh=False,
            source_dir=str(tmp_path),
            base_url="unused",
            run_dbt_steps=False,
        )


def test_local_pipeline_two_jobs_select_two_companies(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    result = run_local_pipeline(
        source_period="202601",
        sample_size=1,
        output_path=str(tmp_path / "output"),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=False,
        parallel_jobs=2,
        ingestion_workers=1,
    )
    assert result.skipped is False
    assert result.row_counts["companies"] >= 2


def test_remote_download_capacity_fails_before_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    usage = type("Usage", (), {"free": 1024})()
    monkeypatch.setattr("cnpj_lakehouse.flows.cnpj_lakehouse.shutil.disk_usage", lambda _: usage)
    with pytest.raises(RuntimeError, match="at least 15 GiB"):
        ensure_remote_download_capacity(tmp_path)


def test_monthly_deployment_uses_schedule_and_automatic_period(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    class FakeFlow:
        def serve(self, **kwargs: object) -> None:
            received.update(kwargs)

    monkeypatch.setattr("cnpj_lakehouse.serve.cnpj_lakehouse_flow", FakeFlow())
    monkeypatch.delenv("CNPJ_LAKEHOUSE_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("CNPJ_LAKEHOUSE_RUNTIME_ROOT", "/var/lib/cnpj-lakehouse-test")
    serve()
    schedule = received["schedules"][0]
    assert schedule.cron == MONTHLY_CRON
    assert schedule.timezone == "America/Sao_Paulo"
    assert received["name"] == "monthly-ingest"
    assert "dia 7" in str(received["description"])
    assert received["parameters"] == {
        "source_period": None,
        "sample_size": None,
        "parallel_jobs": None,
        "output_path": "/var/lib/cnpj-lakehouse-test/run",
        "full_refresh": False,
        "source_dir": None,
    }


def test_monthly_deployment_rejects_windows_mount() -> None:
    with pytest.raises(ValueError, match="Linux-native"):
        deployment_parameters("/mnt/c/cnpj-output")


def test_prefect_launcher_declares_bounded_sqlite_timeouts() -> None:
    launcher = Path(__file__).resolve().parents[1] / "scripts" / "prefect_local.sh"
    content = launcher.read_text(encoding="utf-8")
    assert 'PREFECT_API_DATABASE_TIMEOUT="${PREFECT_API_DATABASE_TIMEOUT:-60}"' in content
    assert 'PREFECT_API_DATABASE_CONNECTION_TIMEOUT="${PREFECT_API_DATABASE_CONNECTION_TIMEOUT:-60}"' in content


def test_dbt_artifacts_are_retained_per_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "dbt"
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        command = args[0]
        target = Path(command[command.index("--target-path") + 1])
        target.mkdir(parents=True)
        (target / "manifest.json").write_text(
            '{"metadata": {"invocation_id": "inv-1"}}', encoding="utf-8"
        )
        (target / "run_results.json").write_text(
            '{"metadata": {"invocation_id": "inv-1"}, "results": []}', encoding="utf-8"
        )
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    artifacts = tmp_path / "artifacts"
    run_dbt(project, project, artifacts, ["run"], {}, "dbt-run")
    destination = next(artifacts.iterdir())
    assert (destination / "manifest.json").is_file()
    assert (destination / "run_results.json").is_file()
    assert (destination / "stdout.log").read_text(encoding="utf-8") == "ok"


def test_dbt_does_not_misattribute_stale_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "dbt"
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="deps", stderr=""
        ),
    )

    artifacts = tmp_path / "artifacts"
    with pytest.raises(RuntimeError, match="without both manifest"):
        run_dbt(project, project, artifacts, ["deps"], {}, "dbt-deps")
    destination = next(artifacts.iterdir())
    assert not (destination / "manifest.json").exists()
    assert not (destination / "run_results.json").exists()


def test_dbt_failure_retains_logs_and_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "dbt"
    project.mkdir()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=[], returncode=2, stdout="partial output", stderr="compiler error"
        ),
    )

    artifacts = tmp_path / "artifacts"
    with pytest.raises(RuntimeError, match="exit code 2"):
        run_dbt(project, project, artifacts, ["run"], {}, "dbt-run")
    destination = next(artifacts.iterdir())
    assert (destination / "stdout.log").read_text(encoding="utf-8") == "partial output"
    assert (destination / "stderr.log").read_text(encoding="utf-8") == "compiler error"


def test_warehouse_writer_lock_serializes_concurrent_writers(tmp_path: Path) -> None:
    acquired = threading.Event()

    def contender() -> None:
        with warehouse_writer_lock(str(tmp_path / "warehouse.duckdb")):
            acquired.set()

    with warehouse_writer_lock(str(tmp_path / "warehouse.duckdb")):
        thread = threading.Thread(target=contender)
        thread.start()
        assert not acquired.wait(0.1)
    thread.join(timeout=1)
    assert acquired.is_set()


def test_validate_analytics_contract_task_raises_missing_gold(tmp_path: Path) -> None:
    database = tmp_path / "cnpj_lakehouse.duckdb"
    with duckdb.connect(str(database)):
        pass
    with pytest.raises(ValueError, match="dim_company_current is missing contract columns"):
        validate_analytics_contract_task.fn(str(database), "2026-01-31")


def test_dbt_task_run_names_map_artifact_labels() -> None:
    assert run_dbt_task.task_run_name(parameters={"artifact_label": "01-dbt-run-core"}) == (
        "executar-dbt-silver"
    )
    assert [DBT_TASK_RUN_NAMES[label] for label in (
        "01-dbt-run-core",
        "02-dbt-snapshot",
        "03-dbt-run-marts",
        "04-dbt-test",
    )] == [
        "executar-dbt-silver",
        "executar-dbt-snapshot",
        "executar-dbt-gold",
        "executar-dbt-testes",
    ]


def test_run_dbt_task_uses_local_flow_run_id_without_prefect_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[Path] = []

    def fake_run_dbt(
        project_directory: Path,
        profiles_directory: Path,
        artifact_directory: Path,
        command: list[str],
        environment: dict[str, str],
        artifact_label: str,
    ) -> None:
        captured.append(artifact_directory)

    monkeypatch.setattr("cnpj_lakehouse.flows.cnpj_lakehouse.run_dbt", fake_run_dbt)
    run_dbt_task.fn(
        str(tmp_path / "dbt"),
        str(tmp_path / "artifacts"),
        str(tmp_path / "cnpj_lakehouse.duckdb"),
        "202601",
        "sample",
        "2026-01-31",
        ["run"],
        "01-dbt-run-core",
    )
    assert captured
    assert captured[0].name == "flow_run_id=local"


def test_decorated_flow_orders_dbt_and_groups_artifacts_by_flow_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    _create_required_archives(sources)
    calls: list[tuple[list[str], Path, str]] = []
    contract_calls: list[tuple[str, str]] = []
    lock_held = {"value": False}

    @contextmanager
    def fake_run_lock(_database_path: str):
        lock_held["value"] = True
        try:
            yield
        finally:
            lock_held["value"] = False

    def fake_run_dbt(
        project_directory: Path,
        profiles_directory: Path,
        artifact_directory: Path,
        command: list[str],
        environment: dict[str, str],
        artifact_label: str,
    ) -> None:
        assert project_directory == profiles_directory
        assert environment["CNPJ_LAKEHOUSE_REFERENCE_DATE"] == "2026-01-31"
        assert environment["CNPJ_LAKEHOUSE_SOURCE_PERIOD"] == "202601"
        assert environment["CNPJ_LAKEHOUSE_SAMPLE_ID"]
        assert lock_held["value"]
        calls.append((command, artifact_directory, artifact_label))

    def fake_verify(database: Path, reference_date: str) -> dict[str, int]:
        assert lock_held["value"]
        contract_calls.append((str(database), reference_date))
        return {"fact_rows": 1}

    monkeypatch.setattr(
        "cnpj_lakehouse.flows.cnpj_lakehouse.warehouse_run_lock", fake_run_lock
    )
    monkeypatch.setattr("cnpj_lakehouse.flows.cnpj_lakehouse.run_dbt", fake_run_dbt)
    monkeypatch.setattr(
        "cnpj_lakehouse.flows.cnpj_lakehouse.verify_analytics_contract", fake_verify
    )
    flow_run_id = "11111111-2222-3333-4444-555555555555"
    monkeypatch.setattr(
        "cnpj_lakehouse.flows.cnpj_lakehouse.get_run_context",
        lambda: SimpleNamespace(task_run=SimpleNamespace(flow_run_id=flow_run_id)),
    )
    result = cnpj_lakehouse_flow.fn(
        source_period="202601",
        sample_size=2,
        output_path=str(tmp_path / "output"),
        reference_date=None,
        full_refresh=False,
        source_dir=str(sources),
        base_url="unused",
        run_dbt_steps=True,
        ingestion_workers=1,
    )

    warehouse = tmp_path / "output" / "warehouse" / "cnpj_lakehouse.duckdb"
    assert result.skipped is False
    assert contract_calls == [(str(warehouse), "2026-01-31")]
    assert [command for command, _, _ in calls] == [
        ["run", "--select", "path:models/staging path:models/intermediate"],
        ["snapshot"],
        ["run", "--select", "path:models/marts"],
        ["test"],
    ]
    labels = [label for _, _, label in calls]
    assert labels == [
        "01-dbt-run-core",
        "02-dbt-snapshot",
        "03-dbt-run-marts",
        "04-dbt-test",
    ]
    assert [DBT_TASK_RUN_NAMES[label] for label in labels] == [
        "executar-dbt-silver",
        "executar-dbt-snapshot",
        "executar-dbt-gold",
        "executar-dbt-testes",
    ]
    flow_directories = {path.name for _, path, _ in calls}
    assert flow_directories == {f"flow_run_id={flow_run_id}"}
    assert lock_held["value"] is False
