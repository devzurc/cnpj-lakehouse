"""Runtime configuration for the local-first pipeline."""

from __future__ import annotations

import calendar
import os
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SAO_PAULO_TIMEZONE = "America/Sao_Paulo"
OPERATOR_RUNTIME_ROOT = Path.home() / ".local" / "share" / "cnpj-lakehouse"
DEMO_RUNTIME_ROOT = OPERATOR_RUNTIME_ROOT
OFFICIAL_RUNTIME_ROOT = Path.home() / ".local" / "share" / "cnpj-lakehouse-official"
SERVE_DEFAULT_RUNTIME_ROOT = "/var/lib/cnpj-lakehouse"
RUNTIME_ROOT_ENV = "CNPJ_LAKEHOUSE_RUNTIME_ROOT"
DUCKDB_PATH_ENV = "CNPJ_LAKEHOUSE_DUCKDB_PATH"
WAREHOUSE_FILENAME = "cnpj_lakehouse.duckdb"
SAMPLE_SIZE_ENV = "CNPJ_LAKEHOUSE_SAMPLE_SIZE"
PARALLEL_JOBS_ENV = "CNPJ_LAKEHOUSE_PARALLEL_JOBS"
INGESTION_WORKERS_ENV = "CNPJ_LAKEHOUSE_INGESTION_WORKERS"
SAMPLING_CONFIG_ENV = "CNPJ_LAKEHOUSE_SAMPLING_CONFIG"
DEFAULT_SAMPLE_SIZE = 10_000
DEFAULT_PARALLEL_JOBS = 1
MAX_PARALLEL_JOBS = 16
DEFAULT_INGESTION_WORKERS = 2
MAX_INGESTION_WORKERS = 4
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLING_CONFIG = REPOSITORY_ROOT / "config" / "sampling.toml"


def assert_linux_native_path(path: Path | str, *, label: str = "path") -> Path:
    """Require an absolute Linux-native path outside the repository."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise ValueError(f"{label} must be an absolute Linux-native path")
    resolved = candidate.resolve()
    text = str(resolved)
    if text.startswith("/mnt/"):
        raise ValueError(f"{label} must use Linux-native storage, not /mnt: {resolved}")
    repository = Path(__file__).resolve().parents[1]
    if resolved == repository or repository in resolved.parents:
        raise ValueError(f"{label} must live outside the repository: {resolved}")
    return resolved


def _configured_runtime_root() -> str | None:
    return os.environ.get(RUNTIME_ROOT_ENV)


def resolve_runtime_root(runtime_root: str | Path | None = None) -> Path:
    """Return the operator or service runtime root, never a Windows mount."""
    if runtime_root is not None:
        return assert_linux_native_path(runtime_root, label=RUNTIME_ROOT_ENV)
    configured = _configured_runtime_root()
    if configured:
        return assert_linux_native_path(configured, label=RUNTIME_ROOT_ENV)
    return assert_linux_native_path(OPERATOR_RUNTIME_ROOT, label=RUNTIME_ROOT_ENV)


def resolve_official_runtime_root(runtime_root: str | Path | None = None) -> Path:
    """Return the isolated backfill runtime; never the synthetic demo share by default."""
    if runtime_root is not None:
        path = assert_linux_native_path(runtime_root, label=RUNTIME_ROOT_ENV)
    else:
        configured = _configured_runtime_root()
        path = assert_linux_native_path(
            configured if configured else OFFICIAL_RUNTIME_ROOT,
            label=RUNTIME_ROOT_ENV,
        )
    if path == DEMO_RUNTIME_ROOT.expanduser().resolve():
        raise ValueError(f"backfill must not use the synthetic demo runtime: {path}")
    return path


def pipeline_run_dir(runtime_root: Path | str) -> Path:
    """Warehouse, Bronze and dbt artifacts live under `<runtime>/run`."""
    return assert_linux_native_path(Path(runtime_root) / "run", label="output_path")


def default_pipeline_output_path() -> Path:
    """CLI default: `$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run` or `~/.local/share/cnpj-lakehouse/run`."""
    return pipeline_run_dir(resolve_runtime_root())


def apply_batch_environment(
    environment: dict[str, str],
    *,
    database_path: str,
    source_period: str,
    sample_id: str,
    reference_date: str,
) -> dict[str, str]:
    """Export the active-batch variables consumed by dbt and the dashboard."""
    environment["CNPJ_LAKEHOUSE_DUCKDB_PATH"] = database_path
    environment["CNPJ_LAKEHOUSE_SOURCE_PERIOD"] = source_period
    environment["CNPJ_LAKEHOUSE_SAMPLE_ID"] = sample_id
    environment["CNPJ_LAKEHOUSE_REFERENCE_DATE"] = reference_date
    return environment


def duckdb_path_from_environment(environment: dict[str, str], *, default: str) -> str:
    """Read the warehouse path from the CNPJ_LAKEHOUSE environment."""
    return environment.get(DUCKDB_PATH_ENV) or default


def warehouse_database_path(output_path: Path | str) -> Path:
    """Return the canonical warehouse, or one unambiguous legacy local database.

    A runtime rename must not silently create a second warehouse beside one
    completed historical database. Multiple candidates require an operator to
    select or migrate a runtime explicitly.
    """
    warehouse = Path(output_path) / "warehouse"
    canonical = warehouse / WAREHOUSE_FILENAME
    if not warehouse.is_dir():
        return canonical
    candidates = sorted(path for path in warehouse.glob("*.duckdb") if path.is_file())
    if len(candidates) == 1:
        candidate = candidates[0]
        if candidate == canonical:
            return canonical
        if _is_compatible_legacy_warehouse(candidate):
            return candidate
        raise RuntimeError(
            "runtime legacy DuckDB warehouse is incompatible; migrate it explicitly or select a clean runtime"
        )
    if len(candidates) > 1:
        raise RuntimeError(
            "runtime contains multiple DuckDB warehouses; migrate explicitly or select a clean runtime"
        )
    return canonical


def _is_compatible_legacy_warehouse(database_path: Path) -> bool:
    """Prove a renamed runtime has the minimum immutable Bronze contract before reuse."""
    import duckdb

    expected_tables = {
        ("ops", "sample_manifests"),
        ("bronze", "companies"),
        ("bronze", "establishments"),
        ("bronze", "partners"),
        ("bronze", "simples"),
        ("bronze", "cnae"),
    }
    try:
        with duckdb.connect(str(database_path), read_only=True) as connection:
            rows = connection.execute(
                "SELECT table_schema, table_name FROM information_schema.tables"
            ).fetchall()
    except duckdb.Error:
        return False
    return expected_tables <= {(str(schema), str(table)) for schema, table in rows}


@dataclass(frozen=True, slots=True)
class SamplingPlan:
    """Per-job sample size and how many disjoint ranking jobs to run."""

    sample_size: int
    parallel_jobs: int

    @property
    def total_companies(self) -> int:
        return self.sample_size * self.parallel_jobs


def _positive_int(value: object, *, label: str, maximum: int | None = None) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a positive integer") from error
    if number < 1:
        raise ValueError(f"{label} must be a positive integer")
    if maximum is not None and number > maximum:
        raise ValueError(f"{label} must be at most {maximum}")
    return number


def _load_sampling_file() -> dict[str, object]:
    configured = os.environ.get(SAMPLING_CONFIG_ENV)
    if configured == "":
        return {}
    path = Path(configured) if configured else DEFAULT_SAMPLING_CONFIG
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def resolve_sampling_plan(
    sample_size: int | None = None,
    parallel_jobs: int | None = None,
) -> SamplingPlan:
    """CLI/flow args override env, which overrides config/sampling.toml, then defaults."""
    file_cfg = _load_sampling_file()
    size: object = (
        sample_size
        if sample_size is not None
        else os.environ.get(SAMPLE_SIZE_ENV) or file_cfg.get("sample_size") or DEFAULT_SAMPLE_SIZE
    )
    jobs: object = (
        parallel_jobs
        if parallel_jobs is not None
        else os.environ.get(PARALLEL_JOBS_ENV) or file_cfg.get("parallel_jobs") or DEFAULT_PARALLEL_JOBS
    )
    return SamplingPlan(
        sample_size=_positive_int(size, label=SAMPLE_SIZE_ENV),
        parallel_jobs=_positive_int(jobs, label=PARALLEL_JOBS_ENV, maximum=MAX_PARALLEL_JOBS),
    )


def validate_ingestion_workers(workers: object) -> int:
    """Reject direct callers that would bypass the local worker safety limit."""
    return _positive_int(workers, label=INGESTION_WORKERS_ENV, maximum=MAX_INGESTION_WORKERS)


def resolve_ingestion_workers(workers: int | None = None) -> int:
    """Resolve bounded local process concurrency for archive CPU work."""
    file_cfg = _load_sampling_file()
    value: object = (
        workers
        if workers is not None
        else os.environ.get(INGESTION_WORKERS_ENV)
        or file_cfg.get("ingestion_workers")
        or DEFAULT_INGESTION_WORKERS
    )
    return validate_ingestion_workers(value)


def validate_source_period(source_period: str) -> str:
    if len(source_period) != 6 or not source_period.isdigit():
        raise ValueError("source_period must use YYYYMM format")
    year, month = int(source_period[:4]), int(source_period[4:])
    if not 2000 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError("source_period must contain a valid year and month")
    return source_period


def period_end(source_period: str) -> date:
    validate_source_period(source_period)
    year, month = int(source_period[:4]), int(source_period[4:])
    return date(year, month, calendar.monthrange(year, month)[1])


def resolve_source_period(source_period: str | None, *, now: datetime | None = None) -> str:
    """Use an explicit source period or the prior calendar month in São Paulo."""
    if source_period is not None:
        return validate_source_period(source_period)
    local_now = (now or datetime.now(ZoneInfo(SAO_PAULO_TIMEZONE))).astimezone(
        ZoneInfo(SAO_PAULO_TIMEZONE)
    )
    year, month = local_now.year, local_now.month
    if month == 1:
        year, month = year - 1, 12
    else:
        month -= 1
    return f"{year:04d}{month:02d}"


def output_layout(output_path: Path, source_period: str) -> dict[str, Path]:
    return {
        "downloads": output_path / "bronze" / "downloads" / f"source_period={source_period}",
        "samples": output_path / "bronze" / "samples" / f"source_period={source_period}",
        "manifests": output_path / "bronze" / "manifests" / f"source_period={source_period}",
        "warehouse": warehouse_database_path(output_path),
        "artifacts": output_path / "artifacts",
    }
