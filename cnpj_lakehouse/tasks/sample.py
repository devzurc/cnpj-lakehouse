"""Relationship-preserving deterministic sampling for CNPJ source archives."""

from __future__ import annotations

import csv
import gzip
import hashlib
import heapq
import io
import json
import os
import re
import shutil
import uuid
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path

from cnpj_lakehouse.contracts import CNAE, COMPANIES, CONTRACTS, ESTABLISHMENTS, SourceContract
from cnpj_lakehouse.privacy import ensure_private_directory, ensure_private_file
from cnpj_lakehouse.settings import validate_ingestion_workers
from cnpj_lakehouse.tasks.archive import iter_contract_rows
from cnpj_lakehouse.tasks.download import DownloadedFile

SAMPLE_METADATA_FIELDS = (
    "source_file",
    "source_member",
    "source_row_number",
    "source_url",
    "source_file_sha256",
)
SAMPLE_ALGORITHM = "sha256-lowest-cnpj-v4-invalid-observability"
LOCAL_PROCESS_CONTEXT = get_context("spawn")


@dataclass(frozen=True, slots=True)
class SampleResult:
    sample_id: str
    selected_companies: tuple[str, ...]
    sample_files: dict[str, Path]
    row_counts: dict[str, int]


def normalize_base_cnpj(value: str) -> str | None:
    digits = value.strip()
    if not re.fullmatch(r"\d{8}", digits):
        return None
    return digits


def _score(source_period: str, cnpj_basico: str) -> int:
    return int(hashlib.sha256(f"{source_period}:{cnpj_basico}".encode()).hexdigest(), 16)


def select_company_cnpjs(
    establishment_files: Iterable[Path], source_period: str, sample_size: int, *, require_size: bool = True
) -> tuple[str, ...]:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    heap: list[tuple[int, str]] = []
    selected: set[str] = set()
    for path in establishment_files:
        for _, _, row in iter_contract_rows(path, ESTABLISHMENTS):
            cnpj_basico = normalize_base_cnpj(row["cnpj_basico"])
            if cnpj_basico is None or cnpj_basico in selected:
                continue
            score = _score(source_period, cnpj_basico)
            if len(heap) < sample_size:
                heapq.heappush(heap, (-score, cnpj_basico))
                selected.add(cnpj_basico)
                continue
            largest_score = -heap[0][0]
            if score < largest_score:
                _, evicted = heapq.heapreplace(heap, (-score, cnpj_basico))
                selected.remove(evicted)
                selected.add(cnpj_basico)
    if require_size and len(selected) < sample_size:
        raise ValueError(f"source contains only {len(selected)} valid distinct companies; need {sample_size}")
    return tuple(sorted(selected))


def _select_from_archive(path: Path, source_period: str, sample_size: int) -> tuple[str, ...]:
    """Return the local lowest candidates from one independently readable shard."""
    return select_company_cnpjs((path,), source_period, sample_size, require_size=False)


def select_company_cnpjs_parallel(
    establishment_files: Iterable[Path], source_period: str, sample_size: int, workers: int
) -> tuple[str, ...]:
    """Merge local shard rankings into the same global deterministic lowest-N cohort."""
    workers = validate_ingestion_workers(workers)
    paths = tuple(establishment_files)
    if workers <= 1 or len(paths) <= 1:
        return select_company_cnpjs(paths, source_period, sample_size)
    with ProcessPoolExecutor(max_workers=workers, mp_context=LOCAL_PROCESS_CONTEXT) as pool:
        local = pool.map(_select_from_archive, paths, (source_period,) * len(paths), (sample_size,) * len(paths))
        candidates = {cnpj for shard in local for cnpj in shard}
    ranked = sorted(candidates, key=lambda cnpj: (_score(source_period, cnpj), cnpj))
    if len(ranked) < sample_size:
        raise ValueError(f"source contains only {len(ranked)} valid distinct companies; need {sample_size}")
    return tuple(sorted(ranked[:sample_size]))


def _open_deterministic_gzip(path: Path) -> io.TextIOWrapper:
    """Create byte-reproducible sample output for content-addressed manifests."""
    raw = ensure_private_file(path).open("wb")
    compressed = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
    return io.TextIOWrapper(compressed, encoding="utf-8", newline="")


def sample_id_for_sources(
    source_period: str,
    sample_size: int,
    downloaded: Iterable[DownloadedFile],
    *,
    parallel_jobs: int = 1,
) -> str:
    manifest: dict[str, object] = {
        "algorithm": SAMPLE_ALGORITHM,
        "source_period": source_period,
        "sample_size": sample_size,
        "files": sorted(
            (
                {"dataset": item.source.dataset, "filename": item.source.filename, "sha256": item.sha256}
                for item in downloaded
            ),
            key=lambda item: (item["dataset"], item["filename"]),
        ),
    }
    if parallel_jobs != 1:
        manifest["parallel_jobs"] = parallel_jobs
        manifest["total_companies"] = sample_size * parallel_jobs
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]


def _write_rows(
    contract: SourceContract,
    files: Iterable[DownloadedFile],
    selected: set[str] | None,
    output_file: Path,
    *,
    allow_empty: bool = False,
) -> int:
    ensure_private_directory(output_file.parent)
    count = 0
    with _open_deterministic_gzip(output_file) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=contract.expected_fields + SAMPLE_METADATA_FIELDS,
            extrasaction="raise",
        )
        writer.writeheader()
        for downloaded_file in files:
            for member_name, row_number, row in iter_contract_rows(downloaded_file.path, contract):
                if selected is not None:
                    cnpj_basico = normalize_base_cnpj(row["cnpj_basico"])
                    if cnpj_basico not in selected:
                        continue
                writer.writerow(
                    row
                    | {
                        "source_file": downloaded_file.source.filename,
                        "source_member": member_name,
                        "source_row_number": str(row_number),
                        "source_url": downloaded_file.source.source_url,
                        "source_file_sha256": downloaded_file.sha256,
                    }
                )
                count += 1
    if not allow_empty and count == 0 and contract in (ESTABLISHMENTS, COMPANIES, CNAE):
        raise ValueError(f"sample has no required {contract.dataset} rows")
    return count


def _merge_gzip_csv(sources: Iterable[Path], destination: Path) -> int:
    """Concatenate shard CSVs that share one header into a single gzip file."""
    ensure_private_directory(destination.parent)
    count = 0
    header: list[str] | None = None
    with _open_deterministic_gzip(destination) as handle:
        writer: csv.DictWriter | None = None
        for source in sources:
            with gzip.open(source, "rt", encoding="utf-8", newline="") as incoming:
                reader = csv.DictReader(incoming)
                fields = list(reader.fieldnames or ())
                if header is None:
                    header = fields
                    writer = csv.DictWriter(handle, fieldnames=header, extrasaction="raise")
                    writer.writeheader()
                elif fields != header:
                    raise ValueError(f"shard CSV header mismatch: {source}")
                assert writer is not None
                for row in reader:
                    writer.writerow(row)
                    count += 1
    return count


def _write_archive_fragment(
    contract: SourceContract,
    downloaded_file: DownloadedFile,
    selected: set[str] | None,
    output_file: Path,
) -> Path:
    _write_rows(contract, (downloaded_file,), selected, output_file, allow_empty=True)
    return output_file


def _write_partitioned_rows(
    contract: SourceContract,
    files: list[DownloadedFile],
    selected: set[str] | None,
    output_file: Path,
    fragment_directory: Path,
    workers: int,
) -> int:
    """Filter independent archives in processes, then merge in canonical filename order."""
    if workers <= 1 or len(files) <= 1:
        return _write_rows(contract, files, selected, output_file)
    ensure_private_directory(fragment_directory)
    fragments = [fragment_directory / f"{item.source.filename}.csv.gz" for item in files]
    with ProcessPoolExecutor(max_workers=workers, mp_context=LOCAL_PROCESS_CONTEXT) as pool:
        futures = [
            pool.submit(_write_archive_fragment, contract, item, selected, fragment)
            for item, fragment in zip(files, fragments, strict=True)
        ]
        for future in futures:
            future.result()
    try:
        return _merge_gzip_csv(fragments, output_file)
    finally:
        for fragment in fragments:
            fragment.unlink(missing_ok=True)
        fragment_directory.rmdir()


def build_sample(
    downloaded: Iterable[DownloadedFile],
    source_period: str,
    sample_size: int,
    sample_directory: Path,
    *,
    parallel_jobs: int = 1,
    ingestion_workers: int = 1,
) -> SampleResult:
    if parallel_jobs < 1:
        raise ValueError("parallel_jobs must be positive")
    ingestion_workers = validate_ingestion_workers(ingestion_workers)
    downloaded_tuple = tuple(downloaded)
    by_dataset: dict[str, list[DownloadedFile]] = {}
    for item in downloaded_tuple:
        by_dataset.setdefault(item.source.dataset, []).append(item)
    for values in by_dataset.values():
        values.sort(key=lambda item: item.source.filename)

    expected_count = sample_size * parallel_jobs
    sample_id = sample_id_for_sources(
        source_period, sample_size, downloaded_tuple, parallel_jobs=parallel_jobs
    )
    target = sample_directory / f"sample_id={sample_id}"

    if completed := _load_completed_sample(target, sample_id, expected_count, downloaded_tuple):
        return completed

    temporary = sample_directory / f".sample_id={sample_id}.{uuid.uuid4().hex}.part"
    ensure_private_directory(sample_directory)
    temporary.mkdir(parents=True, exist_ok=False, mode=0o700)
    temporary.chmod(0o700)
    try:
        return _build_and_promote_sample(
            temporary,
            target,
            sample_id,
            downloaded_tuple,
            by_dataset,
            source_period,
            sample_size,
            parallel_jobs,
            ingestion_workers,
        )
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _build_and_promote_sample(
    temporary: Path,
    target: Path,
    sample_id: str,
    downloaded_tuple: tuple[DownloadedFile, ...],
    by_dataset: dict[str, list[DownloadedFile]],
    source_period: str,
    sample_size: int,
    parallel_jobs: int = 1,
    ingestion_workers: int = 1,
) -> SampleResult:
    total = sample_size * parallel_jobs
    selected_companies = select_company_cnpjs_parallel(
        (item.path for item in by_dataset[ESTABLISHMENTS.dataset]), source_period, total, ingestion_workers
    )
    selected_set = set(selected_companies)
    selection_observability = _selection_observability(
        by_dataset[ESTABLISHMENTS.dataset], selected_set
    )
    sample_files: dict[str, Path] = {}
    row_counts: dict[str, int] = {}
    child_contracts = tuple(contract for contract in CONTRACTS if contract is not CNAE)

    if parallel_jobs == 1:
        for contract in CONTRACTS:
            output_file = temporary / f"{contract.dataset}.csv.gz"
            selected = None if contract is CNAE else selected_set
            row_counts[contract.dataset] = _write_partitioned_rows(
                contract,
                by_dataset[contract.dataset],
                selected,
                output_file,
                temporary / ".fragments" / contract.dataset,
                ingestion_workers,
            )
            sample_files[contract.dataset] = output_file
        shutil.rmtree(temporary / ".fragments", ignore_errors=True)
    else:
        ordered = sorted(selected_companies, key=lambda cnpj: (_score(source_period, cnpj), cnpj))
        shards = [
            set(ordered[index * sample_size : (index + 1) * sample_size])
            for index in range(parallel_jobs)
        ]

        def write_shard(item: tuple[int, set[str]]) -> Path:
            index, companies = item
            shard_dir = temporary / f"shard={index}"
            shard_dir.mkdir(mode=0o700)
            for contract in child_contracts:
                _write_rows(
                    contract,
                    by_dataset[contract.dataset],
                    companies,
                    shard_dir / f"{contract.dataset}.csv.gz",
                )
            return shard_dir

        with ThreadPoolExecutor(max_workers=parallel_jobs) as pool:
            list(pool.map(write_shard, enumerate(shards)))
        for contract in child_contracts:
            output_file = temporary / f"{contract.dataset}.csv.gz"
            row_counts[contract.dataset] = _merge_gzip_csv(
                (temporary / f"shard={index}" / f"{contract.dataset}.csv.gz" for index in range(parallel_jobs)),
                output_file,
            )
            sample_files[contract.dataset] = output_file
        cnae_file = temporary / f"{CNAE.dataset}.csv.gz"
        row_counts[CNAE.dataset] = _write_rows(CNAE, by_dataset[CNAE.dataset], None, cnae_file)
        sample_files[CNAE.dataset] = cnae_file
        for index in range(parallel_jobs):
            shutil.rmtree(temporary / f"shard={index}", ignore_errors=True)

    company_cnpjs = {
        normalize_base_cnpj(row["cnpj_basico"])
        for _, _, row in _iter_sample_csv(sample_files[COMPANIES.dataset], COMPANIES)
    }
    missing = selected_set - company_cnpjs
    if missing:
        raise ValueError(f"selected companies missing from companies sample: {sorted(missing)[:10]}")
    _validate_sample_contents(sample_files, selected_companies, row_counts)
    _write_sample_manifest(
        temporary,
        sample_id,
        selected_companies,
        row_counts,
        downloaded_tuple,
        sample_size,
        parallel_jobs,
        selection_observability,
    )
    if target.exists():
        quarantine = target.with_name(f"{target.name}.invalid-{uuid.uuid4().hex}")
        os.replace(target, quarantine)
    os.replace(temporary, target)
    promoted_files = {dataset: target / path.name for dataset, path in sample_files.items()}
    return SampleResult(sample_id, selected_companies, promoted_files, row_counts)


def _write_sample_manifest(
    target: Path,
    sample_id: str,
    selected_companies: tuple[str, ...],
    row_counts: dict[str, int],
    downloaded: tuple[DownloadedFile, ...],
    sample_size: int,
    parallel_jobs: int,
    selection_observability: list[dict[str, int | str]],
) -> None:
    sample_files = {contract.dataset: target / f"{contract.dataset}.csv.gz" for contract in CONTRACTS}
    ensure_private_file(target / "sample_manifest.json").write_text(
        json.dumps(
            {
                "algorithm": SAMPLE_ALGORITHM,
                "sample_id": sample_id,
                "sample_size": sample_size,
                "parallel_jobs": parallel_jobs,
                "total_companies": sample_size * parallel_jobs,
                "selected_companies": selected_companies,
                "selection_observability": selection_observability,
                "row_counts": row_counts,
                "source_files": [
                    {
                        "dataset": item.source.dataset,
                        "filename": item.source.filename,
                        "sha256": item.sha256,
                        "bytes_downloaded": item.bytes_downloaded,
                    }
                    for item in sorted(downloaded, key=lambda item: (item.source.dataset, item.source.filename))
                ],
                "sample_files": {dataset: _file_sha256(path) for dataset, path in sample_files.items()},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _selection_observability(
    establishment_files: Iterable[DownloadedFile], selected_companies: set[str]
) -> list[dict[str, int | str]]:
    """Return per-archive aggregate selection counters without retaining CNPJ values."""
    metrics: list[dict[str, int | str]] = []
    for item in sorted(establishment_files, key=lambda value: value.source.filename):
        invalid = valid = selected = 0
        for _, _, row in iter_contract_rows(item.path, ESTABLISHMENTS):
            cnpj_basico = normalize_base_cnpj(row["cnpj_basico"])
            if cnpj_basico is None:
                invalid += 1
                continue
            valid += 1
            if cnpj_basico in selected_companies:
                selected += 1
        metrics.append(
            {
                "source_file": item.source.filename,
                "invalid_cnpj_basico": invalid,
                "valid_cnpj_basico": valid,
                "selected_cnpj_basico": selected,
            }
        )
    return metrics


def _load_completed_sample(
    target: Path, sample_id: str, sample_size: int, downloaded: tuple[DownloadedFile, ...]
) -> SampleResult | None:
    """Reuse only a completed, immutable sample that matches current source content."""
    sample_files = {contract.dataset: target / f"{contract.dataset}.csv.gz" for contract in CONTRACTS}
    manifest_path = target / "sample_manifest.json"
    if not manifest_path.is_file() or not all(path.is_file() for path in sample_files.values()):
        return None

    row_counts: dict[str, int] = {}
    selected_companies: set[str] = set()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_sources = [
            {
                "dataset": item.source.dataset,
                "filename": item.source.filename,
                "sha256": item.sha256,
                "bytes_downloaded": item.bytes_downloaded,
            }
            for item in sorted(downloaded, key=lambda item: (item.source.dataset, item.source.filename))
        ]
        if (
            manifest.get("algorithm") != SAMPLE_ALGORITHM
            or manifest.get("sample_id") != sample_id
            or manifest.get("source_files") != expected_sources
            or not isinstance(manifest.get("sample_files"), dict)
            or manifest.get("total_companies") not in (None, sample_size)
        ):
            return None
        for contract in CONTRACTS:
            if manifest["sample_files"].get(contract.dataset) != _file_sha256(
                sample_files[contract.dataset]
            ):
                return None
            count = 0
            for _, _, row in _iter_sample_csv(sample_files[contract.dataset], contract):
                count += 1
                if contract is COMPANIES:
                    cnpj = normalize_base_cnpj(row["cnpj_basico"])
                    if cnpj is not None:
                        selected_companies.add(cnpj)
            row_counts[contract.dataset] = count
    except (OSError, EOFError, ValueError, json.JSONDecodeError):
        return None
    if len(selected_companies) != sample_size or tuple(sorted(selected_companies)) != tuple(manifest.get("selected_companies", ())):
        return None

    selected_tuple = tuple(sorted(selected_companies))
    if row_counts != manifest.get("row_counts"):
        return None
    _validate_sample_contents(sample_files, selected_tuple, row_counts)
    return SampleResult(sample_id, selected_tuple, sample_files, row_counts)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sample_contents(
    sample_files: dict[str, Path], selected_companies: tuple[str, ...], row_counts: dict[str, int]
) -> None:
    selected = set(selected_companies)
    for contract in CONTRACTS:
        observed_count = 0
        for _, _, row in _iter_sample_csv(sample_files[contract.dataset], contract):
            observed_count += 1
            if contract is CNAE:
                continue
            cnpj = normalize_base_cnpj(row["cnpj_basico"])
            if cnpj not in selected:
                raise ValueError(f"sample {contract.dataset} contains a child outside selected companies")
        if observed_count != row_counts[contract.dataset]:
            raise ValueError(f"sample count differs for {contract.dataset}")
        if contract is CNAE and observed_count == 0:
            raise ValueError("sample CNAE domain is empty")


def _iter_sample_csv(path: Path, contract: SourceContract):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != contract.expected_fields + SAMPLE_METADATA_FIELDS:
            raise ValueError(f"sample CSV header does not match {contract.dataset} contract")
        for row_number, row in enumerate(reader, start=2):
            yield path.name, row_number, row
