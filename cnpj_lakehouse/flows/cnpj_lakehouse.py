"""The reproducible local CNPJ-to-DuckDB Lakehouse Prefect flow."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import get_context
from pathlib import Path

from prefect import flow, task
from prefect.context import FlowRunContext, TaskRunContext, get_run_context
from prefect.exceptions import MissingContextError

from cnpj_lakehouse.contracts import CONTRACT_BY_DATASET
from cnpj_lakehouse.inventory import plan_local_ingestion
from cnpj_lakehouse.metrics import stage_timer
from cnpj_lakehouse.names import (
    FLOW_DESCRIPTION,
    FLOW_NAME,
    dbt_task_run_name,
    lakehouse_flow_run_name,
)
from cnpj_lakehouse.privacy import ensure_private_directory, ensure_private_file
from cnpj_lakehouse.settings import (
    apply_batch_environment,
    assert_linux_native_path,
    output_layout,
    period_end,
    resolve_ingestion_workers,
    resolve_sampling_plan,
    resolve_source_period,
    validate_ingestion_workers,
    validate_source_period,
)
from cnpj_lakehouse.tasks.archive import ArchiveValidation, validate_archive
from cnpj_lakehouse.tasks.dbt import run_dbt, warehouse_run_lock
from cnpj_lakehouse.tasks.download import DownloadedFile, download_file
from cnpj_lakehouse.tasks.load_duckdb import (
    BronzeLoadResult,
    completed_bronze,
    load_bronze,
    reusable_bronze_for_cohort,
)
from cnpj_lakehouse.tasks.sample import SampleResult, build_sample, sample_id_for_sources
from cnpj_lakehouse.tasks.source_resolution import (
    DEFAULT_ARCHIVE_INDEX,
    SourceFile,
    resolve_local_sources,
    resolve_remote_sources,
)

MIN_REMOTE_FREE_BYTES = 15 * 1024**3
LOCAL_PROCESS_CONTEXT = get_context("spawn")


def _load_verify_analytics_contract() -> Callable[[Path, str], dict[str, int]]:
    script = Path(__file__).resolve().parents[2] / "scripts" / "verify_analytics_contract.py"
    spec = importlib.util.spec_from_file_location("verify_analytics_contract", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load analytics contract verifier: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_analytics_contract


verify_analytics_contract = _load_verify_analytics_contract()


def _invoke(task: object, *args: object, **kwargs: object) -> object:
    """Create Prefect task runs only inside an existing flow or task context."""
    if FlowRunContext.get() is not None or TaskRunContext.get() is not None:
        return task(*args, **kwargs)  # type: ignore[operator]
    return task.fn(*args, **kwargs)  # type: ignore[attr-defined]


def ensure_remote_download_capacity(output_path: Path, minimum_bytes: int = MIN_REMOTE_FREE_BYTES) -> None:
    """Fail before source resolution/download when the target filesystem is too small."""
    ensure_private_directory(output_path)
    free_bytes = shutil.disk_usage(output_path).free
    if free_bytes < minimum_bytes:
        required_gib = minimum_bytes / 1024**3
        free_gib = free_bytes / 1024**3
        raise RuntimeError(
            f"remote source download requires at least {required_gib:.0f} GiB free; "
            f"{output_path} has {free_gib:.1f} GiB"
        )


@task(
    name="inventariar-lote",
    description=(
        "Compara os 32 ZIPs contratados no disco com os sample_id já gravados na Bronze. "
        "Não lê CNPJ nem linhas restritas."
    ),
)
def inventory_source_batch(
    output_path: str, source_period: str, expected_companies: int
) -> dict[str, object]:
    plan = plan_local_ingestion(Path(output_path), source_period, expected_companies)
    if plan["conflict"]:
        raise RuntimeError(str(plan["conflict"]))
    return plan


@task(
    name="resolver-fontes-do-lote",
    description=(
        "Descobre o diretório YYYY-MM-DD do mês no espelho público (ou lê source_dir) "
        "e devolve a lista contratada de ZIPs Empresas, Estabelecimentos, Sócios, Simples e CNAE."
    ),
)
def resolve_sources(source_period: str, source_dir: str | None, base_url: str) -> tuple[SourceFile, ...]:
    validate_source_period(source_period)
    return resolve_local_sources(Path(source_dir)) if source_dir else resolve_remote_sources(source_period, base_url)


@task(
    name="baixar-zips-do-lote",
    description=(
        "Baixa os ZIPs do lote com até 3 streams em paralelo, grava SHA-256 e o manifesto de download. "
        "A política de retry está em download_file."
    ),
    retries=0,
)
def download_source_files(sources: tuple[SourceFile, ...], destination: str) -> tuple[DownloadedFile, ...]:
    destination_path = Path(destination)
    with ThreadPoolExecutor(max_workers=3) as executor:
        downloaded = tuple(executor.map(lambda item: download_file(item, destination_path), sources))
    downloaded = tuple(sorted(downloaded, key=lambda item: (item.source.dataset, item.source.filename)))
    manifest = {
        "official_dataset": "https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica-cnpj",
        "files": [
            item.source.as_dict()
            | {
                "sha256": item.sha256,
                "bytes_downloaded": item.bytes_downloaded,
                "reused": item.reused,
            }
            for item in downloaded
        ],
    }
    ensure_private_file(destination_path / "download_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return downloaded


@task(
    name="validar-integridade-dos-arquivos",
    description=(
        "Confere membros ZIP, encoding e contagem de campos. Reusa o manifesto imutável quando "
        "todos os SHA-256 coincidem; senão valida de novo e persiste a linhagem."
    ),
)
def validate_archives(
    downloaded: tuple[DownloadedFile, ...], source_period: str, manifest_directory: str, ingestion_workers: int = 1
) -> dict[str, int]:
    ingestion_workers = validate_ingestion_workers(ingestion_workers)
    reusable = reusable_source_manifest(downloaded, source_period, Path(manifest_directory))
    if reusable is not None:
        return {item["filename"]: item["row_count"] for item in reusable["files"]}
    row_counts: dict[str, int] = {}
    validations: dict[str, ArchiveValidation] = {}
    if ingestion_workers <= 1:
        results = tuple(_validate_downloaded_archive(item) for item in downloaded)
    else:
        with ProcessPoolExecutor(
            max_workers=ingestion_workers, mp_context=LOCAL_PROCESS_CONTEXT
        ) as executor:
            results = tuple(executor.map(_validate_downloaded_archive, downloaded))
    for item, validation in results:
        row_counts[item.source.filename] = validation.row_count
        validations[item.source.filename] = validation
    persist_source_manifest(downloaded, validations, source_period, Path(manifest_directory))
    return row_counts


def _validate_downloaded_archive(item: DownloadedFile) -> tuple[DownloadedFile, ArchiveValidation]:
    return item, validate_archive(item.path, CONTRACT_BY_DATASET[item.source.dataset])


def reusable_source_manifest(
    downloaded: tuple[DownloadedFile, ...], source_period: str, manifest_directory: Path
) -> dict[str, object] | None:
    """Reuse prior full archive validation only when every content identity matches."""
    expected = {
        (item.source.dataset, item.source.filename): (item.sha256, item.bytes_downloaded)
        for item in downloaded
    }
    for path in sorted(manifest_directory.glob("manifest_id=*/source_manifest.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if document.get("source_period") != source_period:
            continue
        manifest_id = document.get("manifest_id")
        payload = {key: value for key, value in document.items() if key != "manifest_id"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if (
            not isinstance(manifest_id, str)
            or manifest_id != hashlib.sha256(canonical.encode()).hexdigest()
            or path.parent.name != f"manifest_id={manifest_id}"
        ):
            continue
        received = {
            (item["dataset"], item["filename"]): (item["sha256"], item["bytes_downloaded"])
            for item in document.get("files", [])
        }
        if received == expected and len(document.get("files", [])) == len(expected):
            return document
    return None


def persist_source_manifest(
    downloaded: tuple[DownloadedFile, ...],
    validations: dict[str, ArchiveValidation],
    source_period: str,
    manifest_directory: Path,
) -> Path:
    """Persist one immutable, content-addressed source manifest after validation."""
    files: list[dict[str, object]] = []
    for item in downloaded:
        validation = validations[item.source.filename]
        files.append(
            item.source.as_dict()
            | {
                "sha256": item.sha256,
                "bytes_downloaded": item.bytes_downloaded,
                "members": list(validation.members),
                "row_count": validation.row_count,
            }
        )
    payload = {
        "algorithm": "sha256-source-manifest-v1",
        "official_dataset": "https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica-cnpj",
        "source_period": source_period,
        "files": files,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    manifest_id = hashlib.sha256(canonical.encode()).hexdigest()
    document = payload | {"manifest_id": manifest_id}
    manifest_path = manifest_directory / f"manifest_id={manifest_id}" / "source_manifest.json"
    ensure_private_directory(manifest_path.parent)
    rendered = json.dumps(document, sort_keys=True, indent=2) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != rendered:
        raise RuntimeError(f"immutable source manifest differs from existing file: {manifest_path}")
    ensure_private_file(manifest_path).write_text(rendered, encoding="utf-8")
    return manifest_path


@task(
    name="amostrar-empresas-relacionadas",
    description=(
        "Seleciona empresas por ranking SHA-256 de {source_period}:{cnpj_basico} e inclui "
        "estabelecimentos, sócios e Simples ligados a essa coorte."
    ),
)
def build_relationship_preserving_sample(
    downloaded: tuple[DownloadedFile, ...],
    source_period: str,
    sample_size: int,
    sample_directory: str,
    parallel_jobs: int = 1,
    ingestion_workers: int = 1,
) -> SampleResult:
    return build_sample(
        downloaded,
        source_period,
        sample_size,
        Path(sample_directory),
        parallel_jobs=parallel_jobs,
        ingestion_workers=ingestion_workers,
    )


@task(
    name="carregar-bronze",
    description=(
        "Carrega a amostra no DuckDB em transação append-only. CNPJ e códigos ficam como string. "
        "O mesmo sample_id não duplica linhas."
    ),
)
def load_bronze_task(database_path: str, sample: SampleResult, source_period: str) -> BronzeLoadResult:
    return load_bronze(Path(database_path), sample, source_period)


@task(
    name="reutilizar-bronze-existente",
    description="Se o sample_id já está completo na Bronze, devolve o resultado e pula amostragem e carga.",
)
def lookup_completed_bronze(
    database_path: str, sample_id: str
) -> BronzeLoadResult | None:
    return completed_bronze(Path(database_path), sample_id)


@task(
    name="executar-dbt",
    task_run_name=dbt_task_run_name,
    description=(
        "Roda um comando dbt (Silver, snapshot de Capital Social, Gold ou testes) no warehouse, "
        "com lote ativo CNPJ_LAKEHOUSE_* e artefatos agrupados pelo flow_run_id."
    ),
)
def run_dbt_task(
    project_directory: str,
    artifact_directory: str,
    database_path: str,
    source_period: str,
    sample_id: str,
    reference_date: str,
    command: list[str],
    artifact_label: str,
) -> None:
    environment = apply_batch_environment(
        os.environ.copy(),
        database_path=database_path,
        source_period=source_period,
        sample_id=sample_id,
        reference_date=reference_date,
    )
    project = Path(project_directory)
    try:
        flow_run_id = str(get_run_context().task_run.flow_run_id)
        if not flow_run_id or flow_run_id == "None":
            flow_run_id = "local"
    except (MissingContextError, AttributeError):
        flow_run_id = "local"
    flow_artifacts = Path(artifact_directory) / f"flow_run_id={flow_run_id}"
    run_dbt(project, project, flow_artifacts, command, environment, artifact_label)


@task(
    name="validar-contrato-analitico",
    description="Confere o contrato Gold (dimensões e fato) antes de marcar o run Prefect como Completed.",
)
def validate_analytics_contract_task(database_path: str, reference_date: str) -> None:
    verify_analytics_contract(Path(database_path), reference_date)


def run_local_pipeline(
    source_period: str | None,
    sample_size: int | None,
    output_path: str,
    reference_date: str | None,
    full_refresh: bool,
    source_dir: str | None,
    base_url: str,
    run_dbt_steps: bool,
    parallel_jobs: int | None = None,
    ingestion_workers: int | None = None,
) -> BronzeLoadResult:
    """Use the decorated canonical flow for every local execution path."""
    return cnpj_lakehouse_flow.fn(
        source_period=source_period,
        sample_size=sample_size,
        output_path=output_path,
        reference_date=reference_date,
        full_refresh=full_refresh,
        source_dir=source_dir,
        base_url=base_url,
        run_dbt_steps=run_dbt_steps,
        parallel_jobs=parallel_jobs,
        ingestion_workers=ingestion_workers,
    )


@flow(name=FLOW_NAME, description=FLOW_DESCRIPTION, flow_run_name=lakehouse_flow_run_name)
def cnpj_lakehouse_flow(
    source_period: str | None = None,
    sample_size: int | None = None,
    output_path: str | None = None,
    reference_date: str | None = None,
    full_refresh: bool = False,
    source_dir: str | None = None,
    base_url: str = DEFAULT_ARCHIVE_INDEX,
    run_dbt_steps: bool = True,
    parallel_jobs: int | None = None,
    ingestion_workers: int | None = None,
) -> BronzeLoadResult:
    """Ingere o lote mensal do CNPJ aberto até Gold no DuckDB local.

    Args:
        source_period: Mês do lote no formato YYYYMM. Vazio usa o mês calendário anterior
            em America/Sao_Paulo.
        sample_size: Empresas por job de amostra. Vazio usa env, `config/sampling.toml` ou 10.000.
        output_path: Diretório Linux nativo da execução (`$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run`).
        reference_date: Data da partição Gold (YYYY-MM-DD). Vazio = último dia civil do mês.
        full_refresh: Reconstrói modelos incrementais dbt sem reescrever a Bronze.
        source_dir: Pasta local com os ZIPs já baixados. Vazio baixa do espelho público.
        base_url: Índice HTML do espelho. Padrão: arquivo público Casa dos Dados.
        run_dbt_steps: Se falso, para após a Bronze (uso em testes).
        parallel_jobs: Jobs disjuntos em paralelo. Vazio usa env, arquivo ou 1 (desafio).
    """
    source_period = resolve_source_period(source_period)
    plan = resolve_sampling_plan(sample_size, parallel_jobs)
    sample_size = plan.sample_size
    parallel_jobs = plan.parallel_jobs
    ingestion_workers = resolve_ingestion_workers(ingestion_workers)
    if output_path is None:
        from cnpj_lakehouse.settings import default_pipeline_output_path

        output_path = str(default_pipeline_output_path())
    output_root = assert_linux_native_path(output_path, label="output_path")
    ensure_private_directory(output_root)
    layout = output_layout(output_root, source_period)
    actual_reference_date = reference_date or period_end(source_period).isoformat()
    expected_companies = sample_size * parallel_jobs

    with warehouse_run_lock(str(layout["warehouse"])):
        with stage_timer("source_inventory", source_period=source_period) as metrics:
            inventory = _invoke(
                inventory_source_batch, str(output_root), source_period, expected_companies
            )
            if not isinstance(inventory, dict):
                raise TypeError("source inventory did not return a plan")
            archives = inventory.get("archives")
            if not isinstance(archives, dict):
                raise TypeError("source inventory archives are invalid")
            present = archives.get("present") or ()
            missing = archives.get("missing") or ()
            metrics["present"] = len(present)
            metrics["missing"] = len(missing)
            metrics["action"] = inventory["action"]
        reused_bronze = reusable_bronze_for_cohort(
            layout["warehouse"], source_period, expected_companies
        )
        if reused_bronze is None:
            needs_download = bool(archives.get("needs_download"))
            if source_dir is None and needs_download:
                ensure_remote_download_capacity(output_root)
            resolved_source_dir = source_dir
            if resolved_source_dir is None and not needs_download:
                resolved_source_dir = str(layout["downloads"])
            with stage_timer("source_resolution", source_period=source_period) as metrics:
                sources = _invoke(resolve_sources, source_period, resolved_source_dir, base_url)
                metrics["files"] = len(sources)
            with stage_timer("download", source_period=source_period, files=len(sources)) as metrics:
                downloaded = _invoke(download_source_files, sources, str(layout["downloads"]))
                metrics["bytes"] = sum(
                    0 if item.reused else item.bytes_downloaded for item in downloaded
                )
                metrics["reused_files"] = sum(1 for item in downloaded if item.reused)
            with stage_timer(
                "archive_validation",
                source_period=source_period,
                files=len(downloaded),
                workers=ingestion_workers,
            ) as metrics:
                row_counts = _invoke(
                    validate_archives,
                    downloaded,
                    source_period,
                    str(layout["manifests"]),
                    ingestion_workers,
                )
                metrics["rows"] = sum(row_counts.values())
            expected_sample_id = sample_id_for_sources(
                source_period, sample_size, downloaded, parallel_jobs=parallel_jobs
            )
            result = _invoke(lookup_completed_bronze, str(layout["warehouse"]), expected_sample_id)
            if result is None:
                with stage_timer(
                    "sample_filtering", source_period=source_period, workers=ingestion_workers
                ) as metrics:
                    sample = _invoke(
                        build_relationship_preserving_sample,
                        downloaded,
                        source_period,
                        sample_size,
                        str(layout["samples"]),
                        parallel_jobs,
                        ingestion_workers,
                    )
                    metrics["rows"] = sum(sample.row_counts.values())
                with stage_timer("bronze_load", source_period=source_period) as metrics:
                    result = _invoke(load_bronze_task, str(layout["warehouse"]), sample, source_period)
                    metrics["rows"] = sum(result.row_counts.values())
        else:
            result = reused_bronze

        if not run_dbt_steps:
            return result
        project_directory = str(Path(__file__).resolve().parents[2] / "dbt")
        dbt_run_args = ["run"] + (["--full-refresh"] if full_refresh else [])
        dbt_stages = (
            ("dbt_core", dbt_run_args + ["--select", "path:models/staging path:models/intermediate"], "01-dbt-run-core"),
            ("dbt_snapshot", ["snapshot"], "02-dbt-snapshot"),
            ("dbt_marts", dbt_run_args + ["--select", "path:models/marts"], "03-dbt-run-marts"),
            ("dbt_test", ["test"], "04-dbt-test"),
        )
        for stage, command, artifact_label in dbt_stages:
            with stage_timer(stage, source_period=source_period):
                _invoke(
                    run_dbt_task,
                    project_directory,
                    str(layout["artifacts"]),
                    str(layout["warehouse"]),
                    source_period,
                    result.sample_id,
                    actual_reference_date,
                    command,
                    artifact_label,
                )
        with stage_timer("analytics_contract_validation", source_period=source_period):
            _invoke(validate_analytics_contract_task, str(layout["warehouse"]), actual_reference_date)
    return result
