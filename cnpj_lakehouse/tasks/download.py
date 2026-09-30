"""Streaming archive download with checksum and bounded transient retries."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from cnpj_lakehouse.privacy import ensure_private_directory, ensure_private_file
from cnpj_lakehouse.tasks.source_resolution import SourceFile


class TransientDownloadError(RuntimeError):
    """A download error eligible for bounded retry."""


@dataclass(frozen=True, slots=True)
class DownloadedFile:
    source: SourceFile
    path: Path
    sha256: str
    bytes_downloaded: int
    reused: bool = False


def _is_transient(response: httpx.Response) -> bool:
    return response.status_code == 429 or response.status_code >= 500


def _sha256_file(path: Path) -> str:
    """Calculate a checksum without reading a potentially large archive into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_local_file(source: SourceFile, destination: Path, partial: Path) -> DownloadedFile:
    """Copy a test/local archive with the same bounded-memory and atomic-write contract."""
    source_path = Path(source.location)
    if not source_path.is_file():
        raise FileNotFoundError(f"local source archive not found: {source_path}")
    digest = hashlib.sha256()
    bytes_downloaded = 0
    try:
        with source_path.open("rb") as input_handle, ensure_private_file(partial).open("wb") as output_handle:
            for chunk in iter(lambda: input_handle.read(1024 * 1024), b""):
                output_handle.write(chunk)
                digest.update(chunk)
                bytes_downloaded += len(chunk)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return DownloadedFile(source, destination, digest.hexdigest(), bytes_downloaded, reused=False)


def download_file(
    source: SourceFile,
    destination_directory: Path,
    attempts: int = 3,
    *,
    transport: httpx.BaseTransport | None = None,
) -> DownloadedFile:
    ensure_private_directory(destination_directory)
    destination = destination_directory / source.filename
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.is_file() and destination.stat().st_size > 0:
        digest = _sha256_file(destination)
        return DownloadedFile(source, destination, digest, destination.stat().st_size, reused=True)
    if Path(source.location).is_file():
        return _copy_local_file(source, destination, partial)

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        digest = hashlib.sha256()
        bytes_downloaded = 0
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, read=120.0),
                transport=transport,
            ) as client, client.stream("GET", source.location) as response:
                if _is_transient(response):
                    raise TransientDownloadError(
                        f"transient HTTP {response.status_code} for {source.filename}"
                    )
                response.raise_for_status()
                with ensure_private_file(partial).open("wb") as handle:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        handle.write(chunk)
                        digest.update(chunk)
                        bytes_downloaded += len(chunk)
            partial.replace(destination)
            return DownloadedFile(source, destination, digest.hexdigest(), bytes_downloaded, reused=False)
        except (httpx.TimeoutException, httpx.NetworkError, TransientDownloadError) as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2**attempt)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
    raise TransientDownloadError(f"download failed after {attempts} attempts: {source.filename}") from last_error
