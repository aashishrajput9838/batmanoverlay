"""Unit tests for build script executable verification functions."""

from pathlib import Path

import pytest
from scripts.build import get_executable_path, verify_executable


@pytest.mark.unit
def test_get_executable_path() -> None:
    exe_path = get_executable_path()
    assert isinstance(exe_path, Path)
    assert exe_path.is_absolute()
    assert exe_path.name == "batmanoverlay.exe"


@pytest.mark.unit
def test_verify_executable_missing(tmp_path: Path) -> None:
    missing_file = tmp_path / "non_existent.exe"
    with pytest.raises(FileNotFoundError, match="Executable missing or incomplete"):
        verify_executable(missing_file, timeout_sec=0.2)


@pytest.mark.unit
def test_verify_executable_existing(tmp_path: Path) -> None:
    valid_file = tmp_path / "valid.exe"
    valid_file.write_bytes(b"dummy executable content")

    verified = verify_executable(valid_file, timeout_sec=1.0)
    assert verified == valid_file.resolve()
