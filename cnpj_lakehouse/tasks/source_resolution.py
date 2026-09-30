"""Resolve the required monthly archive manifest from a mirror or local directory."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import httpx

from cnpj_lakehouse.contracts import CONTRACTS, SourceContract
from cnpj_lakehouse.settings import validate_source_period

DEFAULT_ARCHIVE_INDEX = "https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/"
DATE_DIRECTORY_RE = re.compile(r'href="(\d{4}-\d{2}-\d{2})/"')


@dataclass(frozen=True, slots=True)
class SourceFile:
    dataset: str
    filename: str
    location: str
    source_url: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def expected_filenames(contract: SourceContract) -> tuple[str, ...]:
    if contract.sharded:
        return tuple(contract.filename_pattern.format(index=index) for index in range(10))
    return (contract.filename_pattern,)


def expected_source_filenames() -> tuple[str, ...]:
    """Return the contracted 32 archive names in canonical contract order."""
    return tuple(
        filename for contract in CONTRACTS for filename in expected_filenames(contract)
    )


def _validate_manifest(files: list[SourceFile]) -> tuple[SourceFile, ...]:
    expected = {(contract.dataset, filename) for contract in CONTRACTS for filename in expected_filenames(contract)}
    received = {(file.dataset, file.filename) for file in files}
    if missing := expected - received:
        raise ValueError(f"source manifest is missing required files: {sorted(missing)}")
    if extra := received - expected:
        raise ValueError(f"source manifest has unexpected files: {sorted(extra)}")
    return tuple(sorted(files, key=lambda file: (file.dataset, file.filename)))


def resolve_local_sources(source_dir: Path) -> tuple[SourceFile, ...]:
    if not source_dir.is_dir():
        raise ValueError(f"source_dir does not exist or is not a directory: {source_dir}")
    files: list[SourceFile] = []
    for contract in CONTRACTS:
        for filename in expected_filenames(contract):
            path = source_dir / filename
            if path.is_file():
                files.append(
                    SourceFile(
                        dataset=contract.dataset,
                        filename=filename,
                        location=str(path.resolve()),
                        source_url=path.as_uri(),
                    )
                )
    return _validate_manifest(files)


def _matching_period_directories(index_html: str, source_period: str) -> list[str]:
    year, month = int(source_period[:4]), int(source_period[4:])
    matches: list[str] = []
    for value in DATE_DIRECTORY_RE.findall(index_html):
        parsed = date.fromisoformat(value)
        if parsed.year == year and parsed.month == month:
            matches.append(value)
    return sorted(set(matches))


def list_source_periods(
    year: int,
    base_url: str = DEFAULT_ARCHIVE_INDEX,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, ...]:
    """Return YYYYMM periods that have exactly one dated directory on the index."""
    if not 2000 <= year <= 2100:
        raise ValueError("year must be between 2000 and 2100")
    base_url = base_url.rstrip("/") + "/"
    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=60.0),
        transport=transport,
    ) as client:
        index_response = client.get(base_url)
        index_response.raise_for_status()
        html = index_response.text
    periods: list[str] = []
    for month in range(1, 13):
        source_period = f"{year:04d}{month:02d}"
        directories = _matching_period_directories(html, source_period)
        if len(directories) == 1:
            periods.append(source_period)
    return tuple(periods)


def resolve_remote_sources(
    source_period: str,
    base_url: str = DEFAULT_ARCHIVE_INDEX,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple[SourceFile, ...]:
    validate_source_period(source_period)
    base_url = base_url.rstrip("/") + "/"
    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=60.0),
        transport=transport,
    ) as client:
        index_response = client.get(base_url)
        index_response.raise_for_status()
        directories = _matching_period_directories(index_response.text, source_period)
        if len(directories) != 1:
            raise ValueError(
                f"expected exactly one source directory for {source_period}; found {directories or 'none'}"
            )
        monthly_url = urljoin(base_url, directories[0] + "/")
        monthly_response = client.get(monthly_url)
        monthly_response.raise_for_status()
        monthly_html = monthly_response.text

    files: list[SourceFile] = []
    for contract in CONTRACTS:
        for filename in expected_filenames(contract):
            if f'href="{filename}"' not in monthly_html:
                continue
            files.append(
                SourceFile(
                    dataset=contract.dataset,
                    filename=filename,
                    location=urljoin(monthly_url, filename),
                    source_url=urljoin(monthly_url, filename),
                )
            )
    return _validate_manifest(files)
