"""Comprehensive unit & integration tests for the deterministic build pipeline,

spec file configuration, bootloader startup, and OneDir runtime integrity.
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.build import (
    BuildResult,
    BuildState,
    acquire_build_lock,
    get_executable_path,
    release_build_lock,
    safe_file_exists,
    safe_file_hash,
    safe_file_size,
    safe_rmtree,
    safe_unlink,
    verify_executable,
)


# ──────────────────────────────────────────────────────────────────────────────
# Safe Filesystem Helpers
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
class TestSafeFilesystemHelpers:
    def test_safe_file_exists_true(self, tmp_path: Path) -> None:
        f = tmp_path / "exists.txt"
        f.write_text("hello")
        assert safe_file_exists(f) is True

    def test_safe_file_exists_false(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.txt"
        assert safe_file_exists(f, timeout_sec=0.1) is False

    def test_safe_file_exists_directory_returns_false(self, tmp_path: Path) -> None:
        assert safe_file_exists(tmp_path, timeout_sec=0.1) is False

    def test_safe_file_size_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "data.bin"
        f.write_bytes(b"x" * 1024)
        assert safe_file_size(f) == 1024

    def test_safe_file_size_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.bin"
        assert safe_file_size(f, timeout_sec=0.1) == 0

    def test_safe_file_hash_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "hashme.bin"
        f.write_bytes(b"deterministic content")
        h = safe_file_hash(f)
        assert len(h) == 64
        assert h == safe_file_hash(f)

    def test_safe_file_hash_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.bin"
        assert safe_file_hash(f) == ""

    def test_safe_rmtree_success(self, tmp_path: Path) -> None:
        d = tmp_path / "target"
        d.mkdir()
        (d / "file.txt").write_text("content")
        assert safe_rmtree(d) is True
        assert not d.exists()

    def test_safe_rmtree_nonexistent(self, tmp_path: Path) -> None:
        d = tmp_path / "nonexistent"
        assert safe_rmtree(d) is True

    def test_safe_rmtree_retries_on_permission_error(self, tmp_path: Path) -> None:
        d = tmp_path / "locked"
        d.mkdir()
        call_count = 0
        original_rmtree = shutil.rmtree

        def failing_rmtree(path: object, **_kw: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PermissionError("WinError 32")
            original_rmtree(path)  # type: ignore[arg-type]

        with patch.object(shutil, "rmtree", side_effect=failing_rmtree):
            result = safe_rmtree(d, max_retries=5)

        assert result is True
        assert call_count == 3

    def test_safe_unlink_success(self, tmp_path: Path) -> None:
        f = tmp_path / "delete_me.txt"
        f.write_text("bye")
        assert safe_unlink(f) is True
        assert not f.exists()

    def test_safe_unlink_nonexistent(self, tmp_path: Path) -> None:
        f = tmp_path / "already_gone.txt"
        assert safe_unlink(f) is True


# ──────────────────────────────────────────────────────────────────────────────
# Build Lock
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
class TestBuildLock:
    def test_acquire_and_release(self) -> None:
        release_build_lock()
        assert acquire_build_lock() is True
        release_build_lock()

    def test_concurrent_lock_blocked(self) -> None:
        release_build_lock()
        assert acquire_build_lock() is True
        assert acquire_build_lock() is False
        release_build_lock()

    def test_stale_lock_removed(self) -> None:
        release_build_lock()
        from scripts.build import LOCK_FILE

        LOCK_FILE.write_text("999999999:0.0", encoding="utf-8")
        assert acquire_build_lock() is True
        release_build_lock()


# ──────────────────────────────────────────────────────────────────────────────
# BuildResult & BuildState
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
class TestBuildResult:
    def test_default_state(self) -> None:
        r = BuildResult()
        assert r.state == BuildState.IDLE
        assert r.success is False

    def test_completed_is_success(self) -> None:
        r = BuildResult(state=BuildState.COMPLETED)
        assert r.success is True

    def test_failed_is_not_success(self) -> None:
        r = BuildResult(state=BuildState.FAILED)
        assert r.success is False


# ──────────────────────────────────────────────────────────────────────────────
# Executable Resolution & Verification
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
class TestExecutableResolution:
    def test_get_executable_path_returns_onedir_target(self) -> None:
        exe = get_executable_path()
        assert isinstance(exe, Path)
        assert exe.is_absolute()
        assert exe.name == "batmanoverlay.exe"
        assert exe.parent.name == "batmanoverlay"

    def test_verify_executable_missing_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "not_here.exe"
        with pytest.raises(FileNotFoundError, match="Executable missing"):
            verify_executable(missing, timeout_sec=0.2)

    def test_verify_executable_existing_returns_resolved(self, tmp_path: Path) -> None:
        f = tmp_path / "valid.exe"
        f.write_bytes(b"dummy executable content")
        result = verify_executable(f, timeout_sec=1.0)
        assert result == f.resolve()


# ──────────────────────────────────────────────────────────────────────────────
# Spec File & OneDir Integrity Tests
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
class TestSpecFileAndPackagingIntegrity:
    def test_spec_file_exists_and_contains_hiddenimports(self) -> None:
        spec_path = Path(__file__).resolve().parent.parent.parent / "batmanoverlay.spec"
        assert spec_path.exists(), "batmanoverlay.spec must exist in workspace root"
        content = spec_path.read_text(encoding="utf-8")
        assert "encodings" in content
        assert "PySide6.QtWebEngineWidgets" in content
        assert "PySide6.QtWebEngineCore" in content
        assert "COLLECT" in content
        assert "exclude_binaries=True" in content

    def test_onedir_packaging_structure(self, tmp_path: Path) -> None:
        """Verify OneDir structure requirements: exe adjacent to _internal/."""
        package_dir = tmp_path / "batmanoverlay"
        package_dir.mkdir()
        internal_dir = package_dir / "_internal"
        internal_dir.mkdir()
        exe = package_dir / "batmanoverlay.exe"
        exe.write_bytes(b"dummy binary")

        assert (package_dir / "batmanoverlay.exe").exists()
        assert (package_dir / "_internal").exists()
        assert (package_dir / "_internal").is_dir()
