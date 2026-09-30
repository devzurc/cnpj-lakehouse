"""Safe dbt subprocess execution and artifact retention."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from cnpj_lakehouse.privacy import ensure_private_directory, ensure_private_file
from cnpj_lakehouse.settings import duckdb_path_from_environment

DBT_ARTIFACTS = ("manifest.json", "run_results.json")


@contextmanager
def warehouse_writer_lock(database_path: str):
    """Serialize local dbt writers for one DuckDB warehouse."""
    import fcntl

    lock_path = Path(f"{database_path}.lock")
    ensure_private_directory(lock_path.parent)
    with ensure_private_file(lock_path).open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def warehouse_run_lock(database_path: str):
    """Serialize a complete Bronze-to-Gold run, including active-batch views."""
    import fcntl

    lock_path = Path(f"{database_path}.run.lock")
    ensure_private_directory(lock_path.parent)
    with ensure_private_file(lock_path).open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def run_dbt(
    project_directory: Path,
    profiles_directory: Path,
    artifact_directory: Path,
    command: list[str],
    environment: dict[str, str],
    artifact_label: str,
) -> None:
    """Run dbt in a private target and promote only attributable artifacts."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_{artifact_label}_{uuid.uuid4().hex[:8]}"
    workspace = artifact_directory / ".work" / run_id
    target_path = workspace / "target"
    ensure_private_directory(artifact_directory)
    workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    workspace.chmod(0o700)
    with warehouse_writer_lock(
        duckdb_path_from_environment(environment, default=str(artifact_directory / "warehouse"))
    ):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dbt.cli.main",
                *command,
                "--project-dir",
                str(project_directory),
                "--profiles-dir",
                str(profiles_directory),
                "--target-path",
                str(target_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
    artifact_sources = {name: target_path / name for name in DBT_ARTIFACTS}
    artifact_documents: dict[str, dict[str, object]] = {}
    for name, source in artifact_sources.items():
        if source.is_file():
            try:
                artifact_documents[name] = json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise RuntimeError(f"dbt produced malformed {name}: {source}") from error
    if completed.returncode == 0 and set(artifact_documents) != set(DBT_ARTIFACTS):
        raise RuntimeError("dbt completed without both manifest.json and run_results.json")
    invocation_ids = {
        str(document.get("metadata", {}).get("invocation_id"))
        for document in artifact_documents.values()
        if document.get("metadata", {}).get("invocation_id")
    }
    if completed.returncode == 0 and len(invocation_ids) != 1:
        raise RuntimeError("dbt artifacts require one matching nonempty invocation ID")
    promotion = artifact_directory / f".{run_id}.part"
    ensure_private_directory(promotion)
    ensure_private_file(promotion / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    ensure_private_file(promotion / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    for name, source in artifact_sources.items():
        if source.is_file():
            shutil.copyfile(source, promotion / name)
            (promotion / name).chmod(0o600)
    destination = artifact_directory / run_id
    promotion.replace(destination)
    shutil.rmtree(workspace, ignore_errors=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"dbt {' '.join(command)} failed with exit code {completed.returncode}; "
            f"inspect {destination}"
        )
