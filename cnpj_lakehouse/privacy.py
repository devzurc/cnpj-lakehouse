"""Owner-only filesystem helpers for restricted local runtime state."""

from __future__ import annotations

from pathlib import Path

PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def ensure_private_directory(path: Path) -> Path:
    """Create or normalize one runtime directory to owner-only access."""
    missing: list[Path] = []
    ancestor = path
    while not ancestor.exists():
        missing.append(ancestor)
        ancestor = ancestor.parent
    path.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIRECTORY_MODE)
    for directory in reversed(missing):
        directory.chmod(PRIVATE_DIRECTORY_MODE)
    path.chmod(PRIVATE_DIRECTORY_MODE)
    return path


def ensure_private_file(path: Path) -> Path:
    """Create or normalize one runtime file to owner-only access."""
    ensure_private_directory(path.parent)
    path.touch(exist_ok=True)
    path.chmod(PRIVATE_FILE_MODE)
    return path
