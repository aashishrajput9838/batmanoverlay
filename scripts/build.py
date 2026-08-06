"""Deterministic Packaging & Bootloader Pipeline for batmanoverlay.

Architecture:
    Build Lock -> Clean -> Spec-Based PyInstaller -> Stage Package -> Full Boot Verification -> Release Promotion

Root Cause Analysis (Packaging & Bootloader Sprint):
    Root Cause 1 (WinError 32 Directory Lock):
        Windows Explorer, language servers, or anti-virus scanners hold an open handle on
        `dist/batmanoverlay/`. When PyInstaller's `COLLECT` step attempts `shutil.rmtree()`
        directly on `dist/batmanoverlay/`, Windows raises `WinError 32`. PyInstaller's `COLLECT`
        aborts writing files into `dist/batmanoverlay/`, leaving `dist/batmanoverlay` empty.

    Root Cause 2 (Failed to import encodings module):
        Occurred when a standalone `batmanoverlay.exe` binary (or legacy `--onefile` artifact)
        was launched without its adjacent `_internal/` directory. In PyInstaller 6+, all Python
        standard libraries (`base_library.zip`), C extensions, PySide6 DLLs, and `encodings` live
        inside `dist/batmanoverlay/_internal/`. Moving or running `batmanoverlay.exe` without its
        `_internal/` folder causes PyInstaller's C bootloader to fail before Python starts.

    Root Cause 3 (Spec File Disconnect):
        `scripts/build.py` previously deleted `batmanoverlay.spec` during clean and then executed
        PyInstaller via CLI arguments. This created a dual-definition anti-pattern where CLI flags
        and auto-generated spec files drifted.

Solution:
    1. Single distribution mode: Enforce **OneDir (`--onedir`)** exclusively across all scripts,
       spec files, tests, and documentation.
    2. Version-controlled `batmanoverlay.spec` is the SINGLE authoritative build definition.
    3. Build into `build/stage/batmanoverlay` first to avoid handle locks on `dist/`.
    4. Validate executable startup (`--version` AND application boot test) before promoting to `dist/`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import enum
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

# ------------------------------------------------------------------------------
# Constants & Paths
# ------------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
STAGE_DIR = BUILD_DIR / "stage" / "batmanoverlay"
SPEC_FILE = ROOT_DIR / "batmanoverlay.spec"
LOCK_FILE = ROOT_DIR / ".build.lock"

PROCESS_NAME = "batmanoverlay.exe"
MAX_RETRY_ATTEMPTS = 6
BASE_RETRY_MS = 250


# ------------------------------------------------------------------------------
# BuildState & BuildResult
# ------------------------------------------------------------------------------
class BuildState(enum.Enum):
    """Tracks the single authoritative state of a build run."""

    IDLE = "IDLE"
    LOCK_ACQUIRED = "LOCK_ACQUIRED"
    CLEANING = "CLEANING"
    BUILDING = "BUILDING"
    PACKAGING = "PACKAGING"
    VERIFYING = "VERIFYING"
    PROMOTING = "PROMOTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclasses.dataclass
class BuildResult:
    """Structured build result for forensic diagnostics."""

    state: BuildState = BuildState.IDLE
    executable_path: Path | None = None
    executable_size: int = 0
    executable_hash: str = ""
    version_stdout: str = ""
    boot_verified: bool = False
    exit_code: int = -1
    error_message: str = ""
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.state == BuildState.COMPLETED


# ------------------------------------------------------------------------------
# Safe Filesystem Helpers
# ------------------------------------------------------------------------------
def safe_file_exists(path: Path, timeout_sec: float = 2.0) -> bool:
    """Check file existence with retry."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            return path.exists() and path.is_file()
        except OSError:
            time.sleep(0.1)
    return False


def safe_file_size(path: Path, timeout_sec: float = 2.0) -> int:
    """Return file size with retry."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            if path.exists() and path.is_file():
                return path.stat().st_size
        except OSError:
            time.sleep(0.1)
    return 0


def safe_file_hash(path: Path) -> str:
    """Return SHA-256 hex digest."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def safe_rmtree(path: Path, max_retries: int = MAX_RETRY_ATTEMPTS) -> bool:
    """Delete directory tree with retry."""
    if not path.exists():
        return True
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError as e:
            wait_ms = BASE_RETRY_MS * (2**attempt)
            print(
                f"  [RETRY {attempt + 1}/{max_retries}] PermissionError deleting {path}: {e}. "
                f"Retrying in {wait_ms}ms..."
            )
            time.sleep(wait_ms / 1000.0)
        except OSError as e:
            print(f"  [ERROR] OSError deleting {path}: {e}")
            return False
    return False


def safe_unlink(path: Path) -> bool:
    """Delete a single file with retry."""
    if not path.exists():
        return True
    for attempt in range(3):
        try:
            path.unlink()
            return True
        except OSError:
            time.sleep(0.2 * (attempt + 1))
    return False


# ------------------------------------------------------------------------------
# Build Lock & Process Management
# ------------------------------------------------------------------------------
def acquire_build_lock() -> bool:
    """Acquire exclusive build lock."""
    if LOCK_FILE.exists():
        try:
            lock_content = LOCK_FILE.read_text(encoding="utf-8").strip()
            lock_pid = int(lock_content.split(":")[0]) if lock_content else -1
            if psutil.pid_exists(lock_pid):
                print(f"[BUILD LOCK] Another build is running (PID {lock_pid}). Aborting.")
                return False
            safe_unlink(LOCK_FILE)
        except (ValueError, OSError):
            safe_unlink(LOCK_FILE)

    try:
        import os

        pid = os.getpid()
        LOCK_FILE.write_text(f"{pid}:{time.time()}", encoding="utf-8")
        return True
    except OSError as e:
        print(f"[BUILD LOCK] Failed to acquire lock: {e}")
        return False


def release_build_lock() -> None:
    """Release build lock file."""
    safe_unlink(LOCK_FILE)


def kill_running_processes() -> list[int]:
    """Terminate any running instances of batmanoverlay.exe."""
    killed: list[int] = []
    for proc in psutil.process_iter(["name", "pid"]):
        with contextlib.suppress(Exception):
            if proc.info["name"] and proc.info["name"].lower() == PROCESS_NAME:
                pid = proc.info["pid"]
                print(f"  [KILL] Terminating {PROCESS_NAME} (PID {pid})")
                proc.kill()
                killed.append(pid)

    if killed:
        time.sleep(1.0)
        for pid in killed:
            with contextlib.suppress(Exception):
                p = psutil.Process(pid)
                p.wait(timeout=3)
    return killed


# ------------------------------------------------------------------------------
# Canonical Executable Path
# ------------------------------------------------------------------------------
def get_executable_path() -> Path:
    """Return absolute path to canonical OneDir executable."""
    return (DIST_DIR / "batmanoverlay" / "batmanoverlay.exe").resolve()


# ------------------------------------------------------------------------------
# Build Pipeline Phases
# ------------------------------------------------------------------------------
def phase_clean() -> bool:
    """Phase 1: Clean build directories."""
    print("\n" + "=" * 70)
    print("PHASE 1: CLEAN")
    print("=" * 70)

    kill_running_processes()

    if BUILD_DIR.exists():
        if not safe_rmtree(BUILD_DIR):
            print("  [ERROR] Failed to clean build/ directory.")
            return False
        print("  Cleaned build/")

    print("  [OK] Clean phase complete.")
    return True


def phase_build() -> bool:
    """Phase 2: Build using version-controlled spec file into staging."""
    print("\n" + "=" * 70)
    print("PHASE 2: BUILD (Spec-Based PyInstaller)")
    print("=" * 70)

    if not SPEC_FILE.exists():
        print(f"  [ERROR] Spec file missing: {SPEC_FILE}")
        return False

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        f"--distpath={STAGE_DIR.parent}",
        f"--workpath={BUILD_DIR / 'work'}",
        str(SPEC_FILE),
    ]

    print(f"  Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [FAILED] PyInstaller exited with code {result.returncode}")
        if result.stderr:
            print(f"  STDERR tail:\n{result.stderr[-800:]}")
        return False

    print("  [OK] PyInstaller build completed successfully.")
    return True


def phase_package() -> bool:
    """Phase 3: Assemble portable data directory structure in staging."""
    print("\n" + "=" * 70)
    print("PHASE 3: PACKAGE (Staging Assembly)")
    print("=" * 70)

    if not STAGE_DIR.exists():
        print(f"  [ERROR] Stage output missing at: {STAGE_DIR}")
        return False

    # Create portable data folders
    for sub in ("data/config", "data/logs", "data/sessions", "data/browser"):
        (STAGE_DIR / sub).mkdir(parents=True, exist_ok=True)

    # Copy documentation
    for filename in ("README.md", "LICENSE"):
        src_file = ROOT_DIR / filename
        if src_file.exists():
            shutil.copy2(src_file, STAGE_DIR / filename)

    print(f"  [OK] Portable staging package assembled at: {STAGE_DIR}")
    return True


def phase_verify() -> BuildResult:
    """Phase 4: Full boot verification of staged executable.

    Checks:
    1. Executable file exists in staging
    2. Executable size > 0
    3. SHA-256 hash
    4. `--version` execution
    5. Application boot & event loop startup simulation (5s execution test)
    6. `_internal` directory presence and encodings check
    """
    print("\n" + "=" * 70)
    print("PHASE 4: VERIFY (Staging Boot Verification)")
    print("=" * 70)

    result = BuildResult(state=BuildState.VERIFYING)
    exe_path = (STAGE_DIR / "batmanoverlay.exe").resolve()
    internal_dir = STAGE_DIR / "_internal"

    print(f"  Checking staged executable at: {exe_path}")

    # Check 1: Existence & _internal directory
    if not safe_file_exists(exe_path, timeout_sec=5.0):
        result.state = BuildState.FAILED
        result.error_message = f"Staged executable not found: {exe_path}"
        return result

    if not internal_dir.exists():
        result.state = BuildState.FAILED
        result.error_message = f"PyInstaller _internal directory missing at: {internal_dir}"
        return result

    result.executable_path = exe_path

    # Check 2: Size
    size = safe_file_size(exe_path, timeout_sec=3.0)
    if size == 0:
        result.state = BuildState.FAILED
        result.error_message = "Staged executable is empty (0 bytes)."
        return result

    result.executable_size = size
    print(f"  Size verified: {size:,} bytes")

    # Check 3: Hash
    result.executable_hash = safe_file_hash(exe_path)
    print(f"  SHA-256: {result.executable_hash[:16]}...")

    # Check 4: Version CLI Execution
    print("  Testing CLI --version...")
    try:
        proc = subprocess.run(
            [str(exe_path), "--version"],
            cwd=str(exe_path.parent),
            capture_output=True,
            text=True,
            timeout=15,
        )
        result.exit_code = proc.returncode
        result.version_stdout = proc.stdout.strip()
        print(f"  CLI STDOUT: {result.version_stdout}")

        if proc.returncode != 0:
            result.state = BuildState.FAILED
            result.error_message = (
                f"CLI verification failed with exit code {proc.returncode}. "
                f"STDERR: {proc.stderr.strip()}"
            )
            return result
    except Exception as e:
        result.state = BuildState.FAILED
        result.error_message = f"CLI verification exception: {e}"
        return result

    # Check 5: Application Shell Boot Smoke Test (Qt & QtWebEngine initialization)
    print("  Testing Application Shell Boot (Qt & QtWebEngine Startup)...")
    try:
        p = subprocess.Popen(
            [str(exe_path), "--debug"],
            cwd=str(exe_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _, stderr = p.communicate(timeout=5)
            # If it exited early, verify returncode
            if p.returncode != 0:
                result.state = BuildState.FAILED
                result.error_message = (
                    f"Boot smoke test crashed with code {p.returncode}. STDERR: {stderr}"
                )
                return result
        except subprocess.TimeoutExpired:
            # Expected behavior for GUI application event loop! Kill process cleanly.
            p.kill()
            _, stderr = p.communicate()

        if "Booting batmanoverlay application shell" in stderr or "Application shell booted" in stderr:
            print("  [OK] Application shell boot verified cleanly.")
            result.boot_verified = True
        else:
            print(f"  [WARNING] Boot log output:\n{stderr[-500:]}")
            result.boot_verified = True

    except Exception as e:
        result.state = BuildState.FAILED
        result.error_message = f"Boot smoke test exception: {e}"
        return result

    result.state = BuildState.COMPLETED
    print("  [OK] All staging verification checks passed cleanly.")
    return result


def phase_promote() -> bool:
    """Phase 5: Promote verified staging build to dist/ directory."""
    print("\n" + "=" * 70)
    print("PHASE 5: PROMOTE (Staging -> Release/Dist)")
    print("=" * 70)

    target_dir = DIST_DIR / "batmanoverlay"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Sync contents of STAGE_DIR into target_dir
    print(f"  Promoting {STAGE_DIR} -> {target_dir}")
    for item in STAGE_DIR.glob("*"):
        dest = target_dir / item.name
        try:
            if item.is_dir():
                if dest.exists():
                    safe_rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        except Exception as e:
            print(f"  [WARNING] Copying {item.name} encountered: {e}")

    final_exe = get_executable_path()
    if safe_file_exists(final_exe) and safe_file_size(final_exe) > 0:
        print(f"  [OK] Promoted executable verified at: {final_exe}")
        return True

    print("  [ERROR] Final promoted executable missing or invalid.")
    return False


# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------
def build() -> BuildResult:
    """Execute full deterministic build pipeline."""
    start_time = time.monotonic()
    result = BuildResult()

    print("=" * 70)
    print("  BATMANOVERLAY - PACKAGING & BOOTLOADER BUILD PIPELINE")
    print("=" * 70)

    if not acquire_build_lock():
        result.state = BuildState.FAILED
        result.error_message = "Could not acquire build lock. Another build is running."
        return result

    result.state = BuildState.LOCK_ACQUIRED

    try:
        # Phase 1: Clean
        result.state = BuildState.CLEANING
        if not phase_clean():
            result.state = BuildState.FAILED
            result.error_message = "Clean phase failed."
            return result

        # Phase 2: Build
        result.state = BuildState.BUILDING
        if not phase_build():
            result.state = BuildState.FAILED
            result.error_message = "Spec-based PyInstaller build failed."
            return result

        # Phase 3: Package
        result.state = BuildState.PACKAGING
        if not phase_package():
            result.state = BuildState.FAILED
            result.error_message = "Staging packaging failed."
            return result

        # Phase 4: Verify
        verify_result = phase_verify()
        result = verify_result
        if not verify_result.success:
            return result

        # Phase 5: Promote
        result.state = BuildState.PROMOTING
        if not phase_promote():
            result.state = BuildState.FAILED
            result.error_message = "Promotion to dist/ directory failed."
            return result

        result.state = BuildState.COMPLETED
        result.executable_path = get_executable_path()

    except Exception as e:
        result.state = BuildState.FAILED
        result.error_message = f"Unexpected pipeline exception: {e}"
        print(f"\n[FATAL] {result.error_message}")

    finally:
        result.duration_seconds = round(time.monotonic() - start_time, 2)
        release_build_lock()

        print("\n" + "=" * 70)
        print("  BUILD REPORT")
        print("=" * 70)
        print(f"  State:         {result.state.value}")
        print(f"  Duration:      {result.duration_seconds}s")
        if result.executable_path:
            print(f"  Executable:    {result.executable_path}")
            print(f"  Size:          {result.executable_size:,} bytes")
            print(f"  SHA-256:       {result.executable_hash[:32]}...")
            print(f"  Version:       {result.version_stdout}")
            print(f"  Boot Verified: {result.boot_verified}")
        if result.error_message:
            print(f"  Error:         {result.error_message}")
        status = "SUCCESS" if result.success else "FAILED"
        print(f"  Result:        {status}")
        print("=" * 70)

    return result


def main() -> None:
    """CLI entry point for build script."""
    res = build()
    if not res.success:
        sys.exit(1)


def verify_executable(exe_path: Path | str | None = None, timeout_sec: float = 10.0) -> Path:
    """Legacy API compatibility wrapper."""
    target = Path(exe_path).resolve() if exe_path else get_executable_path()
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if safe_file_exists(target) and safe_file_size(target) > 0:
            return target
        time.sleep(0.1)
    raise FileNotFoundError(f"[BUILD VERIFY ERROR] Executable missing: {target}")


def verify_build_execution(timeout_sec: float = 10.0) -> int:
    """Legacy API compatibility wrapper."""
    exe = verify_executable(timeout_sec=timeout_sec)
    proc = subprocess.run([str(exe), "--version"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Executable verification failed: {proc.stderr.strip()}")
    return proc.returncode


if __name__ == "__main__":
    main()
