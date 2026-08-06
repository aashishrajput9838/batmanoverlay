"""FileSystem utilities for atomic writes and path safety."""

import os
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating parents if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text content to a file via a temporary file replacement.

    Guarantees that partial writes will never overwrite existing valid files.
    """
    ensure_dir(path.parent)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding=encoding) as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    # Atomic replace on NTFS / POSIX
    tmp_path.replace(path)
