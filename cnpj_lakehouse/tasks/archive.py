"""Streaming ZIP validation and CSV row iteration."""

from __future__ import annotations

import codecs
import csv
import io
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from cnpj_lakehouse.contracts import SourceContract


class SourceSchemaError(ValueError):
    """A source archive or row does not match its documented contract."""


def _preserve_undefined_cp1252(error: UnicodeDecodeError) -> tuple[str, int]:
    """Preserve undefined CP1252 bytes as reversible C1 code points."""
    offending_bytes = error.object[error.start : error.end]
    return offending_bytes.decode("latin-1"), error.end


codecs.register_error("cnpj_lakehouse_cp1252_preserve", _preserve_undefined_cp1252)


@dataclass(frozen=True, slots=True)
class ArchiveValidation:
    archive_path: Path
    members: tuple[str, ...]
    row_count: int


def archive_members(path: Path) -> tuple[str, ...]:
    if not zipfile.is_zipfile(path):
        raise SourceSchemaError(f"not a ZIP archive: {path}")
    with zipfile.ZipFile(path) as archive:
        members = tuple(info.filename for info in archive.infolist() if not info.is_dir())
        if not members:
            raise SourceSchemaError(f"archive has no file members: {path.name}")
        encrypted = [info.filename for info in archive.infolist() if info.flag_bits & 0x1]
        if encrypted:
            raise SourceSchemaError(f"archive has encrypted members: {encrypted}")
        return members


def iter_contract_rows(path: Path, contract: SourceContract) -> Iterator[tuple[str, int, dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        for member_name in archive_members(path):
            with archive.open(member_name) as binary_handle:
                text_handle = io.TextIOWrapper(
                    binary_handle,
                    encoding="cp1252",
                    errors="cnpj_lakehouse_cp1252_preserve",
                    newline="",
                )
                reader = csv.reader(text_handle, delimiter=";", quotechar='"')
                row_count = 0
                for row_number, row in enumerate(reader, start=1):
                    if len(row) != len(contract.expected_fields):
                        raise SourceSchemaError(
                            f"{path.name}:{member_name}:{row_number} expected "
                            f"{len(contract.expected_fields)} fields, received {len(row)}"
                        )
                    row_count += 1
                    yield member_name, row_number, dict(zip(contract.expected_fields, row, strict=True))
                if row_count == 0:
                    raise SourceSchemaError(f"{path.name}:{member_name} has no rows")


def validate_archive(path: Path, contract: SourceContract) -> ArchiveValidation:
    """Read every row once to validate schema and capture an auditable source row count."""
    members = archive_members(path)
    row_count = sum(1 for _ in iter_contract_rows(path, contract))
    if row_count == 0:
        raise SourceSchemaError(f"archive has no data rows: {path.name}")
    return ArchiveValidation(path, members, row_count)
