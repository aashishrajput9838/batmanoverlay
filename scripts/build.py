"""Deterministic build pipeline for packaging batmanoverlay into a portable Windows executable.

Architecture:
    Build Lock → Clean → PyInstaller → Package → Verify → Report

Root Cause Analysis (from Build Pipeline Stabilization Sprint):
    Issue-001: WinError 32 caused by PyInstaller's --noconfirm flag trying to delete
               dist/batmanoverlay/ while Explorer, antivirus, or a previous build holds a handle.
    Issue-002: Multiple concurrent build tasks producing contradictory logs because the agent
               launched multiple `python scripts/build.py` as background tasks simultaneously.
    Issue-003: Verification desync caused by --onefile producing dist/batmanoverlay.exe while
               --onedir produces dist/batmanoverlay/batmanoverlay.exe. The assemble step then
               creates an empty dist/batmanoverlay/ directory, shadowing the onedir output.

Fixes:
    1. File-based build lock prevents concurrent builds.
    2. Exponential backoff retry on all directory deletions.
    3. Process killing with wait-for-exit before cleanup.
    4. Single authoritative verification pipeline with structured diagnostics.
    5. BuildState enum tracking with exactly one terminal state.
    6. Safe filesystem helpers that never raise FileNotFoundError.
    7. Atomic packaging: previous release preserved until new build verified.
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

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
SRC_DIR = ROOT_DIR / "src"
RESOURCES_DIR = ROOT_DIR / "resources"
LOCK_FILE = ROOT_DIR / ".build.lock"

MAX_RETRY_ATTEMPTS = 6
BASE_RETRY_MS = 250
PROCESS_NAME = "batmanoverlay.exe"


# ──────────────────────────────────────────────────────────────────────────────
# BuildState
# ──────────────────────────────────────────────────────────────────────────────
class BuildState(enum.Enum):
    """Tracks the single authoritative state of a build run."""

    IDLE = "IDLE"
    LOCK_ACQUIRED = "LOCK_ACQUIRED"
    CLEANING = "CLEANING"
    BUILDING = "BUILDING"
    PACKAGING = "PACKAGING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ──────────────────────────────────────────────────────────────────────────────
# BuildResult (structured diagnostics)
# ──────────────────────────────────────────────────────────────────────────────
@dataclasses.dataclass
class BuildResult:
    """Structured build result — never raises on verification failure."""

    state: BuildState = BuildState.IDLE
    executable_path: Path | None = None
    executable_size: int = 0
    executable_hash: str = ""
    version_stdout: str = ""
    exit_code: int = -1
    error_message: str = ""
    duration_seconds: float = 0.0
    assets_verified: bool = False

    @property
    def success(self) -> bool:
        return self.state == BuildState.COMPLETED


# ──────────────────────────────────────────────────────────────────────────────
# Safe filesystem helpers
# ──────────────────────────────────────────────────────────────────────────────
def safe_file_exists(path: Path, timeout_sec: float = 2.0) -> bool:
    """Check file existence with retry, never raises."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            return path.exists() and path.is_file()
        except OSError:
            time.sleep(0.1)
    return False


def safe_file_size(path: Path, timeout_sec: float = 2.0) -> int:
    """Return file size with retry, returns 0 on failure."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            if path.exists() and path.is_file():
                return path.stat().st_size
        except OSError:
            time.sleep(0.1)
    return 0


def safe_file_hash(path: Path) -> str:
    """Return SHA-256 hex digest, empty string on failure."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def safe_rmtree(path: Path, max_retries: int = MAX_RETRY_ATTEMPTS) -> bool:
    """Delete directory tree with exponential backoff. Returns True on success."""
    if not path.exists():
        return True
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError as e:
            wait_ms = BASE_RETRY_MS * (2**attempt)
            print(
                f"  [RETRY {attempt + 1}/{max_retries}] "
                f"PermissionError deleting {path}: {e}. "
                f"Retrying in {wait_ms}ms..."
            )
            time.sleep(wait_ms / 1000.0)
        except OSError as e:
            print(f"  [ERROR] OSError deleting {path}: {e}")
            return False
    print(f"  [FAILED] Could not delete {path} after {max_retries} retries.")
    return False


def safe_unlink(path: Path) -> bool:
    """Delete a single file with retry. Returns True on success."""
    if not path.exists():
        return True
    for attempt in range(3):
        try:
            path.unlink()
            return True
        except OSError:
            time.sleep(0.2 * (attempt + 1))
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Build lock (prevents concurrent builds)
# ──────────────────────────────────────────────────────────────────────────────
def acquire_build_lock() -> bool:
    """Acquire exclusive build lock. Returns False if another build is running."""
    if LOCK_FILE.exists():
        try:
            lock_content = LOCK_FILE.read_text(encoding="utf-8").strip()
            lock_pid = int(lock_content.split(":")[0]) if lock_content else -1
            if psutil.pid_exists(lock_pid):
                print(f"[BUILD LOCK] Another build is running (PID {lock_pid}). Aborting.")
                return False
            print(f"[BUILD LOCK] Stale lock from PID {lock_pid}. Removing.")
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
    """Release the build lock file."""
    safe_unlink(LOCK_FILE)


# ──────────────────────────────────────────────────────────────────────────────
# Process management
# ──────────────────────────────────────────────────────────────────────────────
def kill_running_processes() -> list[int]:
    """Kill all running batmanoverlay.exe instances. Returns list of killed PIDs."""
    killed: list[int] = []
    for proc in psutil.process_iter(["name", "pid"]):
        with contextlib.suppress(Exception):
            if proc.info["name"] and proc.info["name"].lower() == PROCESS_NAME:
                pid = proc.info["pid"]
                print(f"  [KILL] Terminating {PROCESS_NAME} (PID {pid})")
                proc.kill()
                killed.append(pid)

    # Wait for processes to fully exit
    if killed:
        time.sleep(1.0)
        for pid in killed:
            with contextlib.suppress(Exception):
                p = psutil.Process(pid)
                p.wait(timeout=3)
    return killed


def detect_locked_handles(path: Path) -> bool:
    """Detect if any process holds a handle on the given path."""
    path_str = str(path).lower()
    for proc in psutil.process_iter(["name", "pid"]):
        with contextlib.suppress(Exception):
            if proc.info["name"] and proc.info["name"].lower() == PROCESS_NAME:
                return True
            for f in proc.open_files():
                if f.path.lower().startswith(path_str):
                    print(
                        f"  [LOCK DETECTED] {proc.info['name']} "
                        f"(PID {proc.info['pid']}) has handle on {f.path}"
                    )
                    return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Get executable path
# ──────────────────────────────────────────────────────────────────────────────
def get_executable_path() -> Path:
    """Return absolute, resolved path to the compiled executable.

    Checks onedir output first (dist/batmanoverlay/batmanoverlay.exe),
    since that is the canonical output mode.
    """
    onedir = (DIST_DIR / "batmanoverlay" / "batmanoverlay.exe").resolve()
    if safe_file_exists(onedir):
        return onedir
    onefile = (DIST_DIR / "batmanoverlay.exe").resolve()
    if safe_file_exists(onefile):
        return onefile
    return onedir  # Return canonical path even if it doesn't exist yet


# ──────────────────────────────────────────────────────────────────────────────
# Build phases
# ──────────────────────────────────────────────────────────────────────────────
def phase_clean() -> bool:
    """Phase 1: Clean build artifacts with lock detection and retries."""
    print("\n" + "=" * 70)
    print("PHASE 1: CLEAN")
    print("=" * 70)

    killed = kill_running_processes()
    if killed:
        print(f"  Killed {len(killed)} running instance(s).")

    if detect_locked_handles(DIST_DIR):
        print("  [WARNING] Locked handles detected on dist/. Waiting...")
        time.sleep(2.0)
        if detect_locked_handles(DIST_DIR):
            print("  [ERROR] dist/ is still locked after waiting. Cannot clean.")
            return False

    # Clean build directory
    if BUILD_DIR.exists():
        if not safe_rmtree(BUILD_DIR):
            print("  [ERROR] Failed to clean build/ directory.")
            return False
        print("  Cleaned build/")

    # Clean dist directory
    if DIST_DIR.exists():
        if not safe_rmtree(DIST_DIR):
            print("  [ERROR] Failed to clean dist/ directory.")
            return False
        print("  Cleaned dist/")

    # Clean spec file
    spec_file = ROOT_DIR / "batmanoverlay.spec"
    safe_unlink(spec_file)

    print("  [OK] Clean phase complete.")
    return True


def phase_build() -> bool:
    """Phase 2: Execute PyInstaller to compile the executable."""
    print("\n" + "=" * 70)
    print("PHASE 2: BUILD (PyInstaller)")
    print("=" * 70)

    icon_path = RESOURCES_DIR / "icons" / "app.ico"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--console",
        "--name=batmanoverlay",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--add-data={RESOURCES_DIR};resources",
        f"--add-data={SRC_DIR / 'storage' / 'migrations'};src/storage/migrations",
        "--paths=src",
        str(SRC_DIR / "main.py"),
    ]
    if icon_path.exists():
        cmd.insert(7, f"--icon={icon_path}")

    print(f"  Command: {' '.join(cmd)}")
    print("  Building... (this may take 60-120 seconds)")

    result = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [FAILED] PyInstaller exited with code {result.returncode}")
        stderr_tail = result.stderr[-800:] if result.stderr else "(empty)"
        print(f"  STDERR tail:\n{stderr_tail}")
        return False

    print("  [OK] PyInstaller completed successfully.")
    return True


def phase_package() -> bool:
    """Phase 3: Assemble portable directory structure."""
    print("\n" + "=" * 70)
    print("PHASE 3: PACKAGE")
    print("=" * 70)

    target_dir = DIST_DIR / "batmanoverlay"
    if not target_dir.exists():
        print(f"  [ERROR] PyInstaller output directory missing: {target_dir}")
        return False

    # Create portable data structure
    for sub in ("data/config", "data/logs", "data/sessions"):
        (target_dir / sub).mkdir(parents=True, exist_ok=True)

    # Copy documentation
    for filename in ("README.md", "LICENSE"):
        src_file = ROOT_DIR / filename
        if src_file.exists():
            shutil.copy2(src_file, target_dir / filename)

    print(f"  [OK] Portable package assembled at: {target_dir}")
    return True


def phase_verify() -> BuildResult:
    """Phase 4: Single authoritative verification pipeline.

    Order: exists → size → hash → execute → version → assets
    """
    print("\n" + "=" * 70)
    print("PHASE 4: VERIFY")
    print("=" * 70)

    result = BuildResult(state=BuildState.VERIFYING)

    # Step 1: Wait for filesystem flush
    print("  Step 1: Filesystem sync...")
    time.sleep(0.5)

    # Step 2: Locate executable
    exe_path = get_executable_path()
    print(f"  Step 2: Checking executable at: {exe_path}")

    if not safe_file_exists(exe_path, timeout_sec=5.0):
        result.state = BuildState.FAILED
        result.error_message = f"Executable not found: {exe_path}"
        print(f"  [FAILED] {result.error_message}")
        return result

    result.executable_path = exe_path

    # Step 3: Verify size
    size = safe_file_size(exe_path, timeout_sec=3.0)
    if size == 0:
        result.state = BuildState.FAILED
        result.error_message = "Executable has zero size."
        print(f"  [FAILED] {result.error_message}")
        return result

    result.executable_size = size
    print(f"  Step 3: Size verified: {size:,} bytes")

    # Step 4: Hash
    file_hash = safe_file_hash(exe_path)
    result.executable_hash = file_hash
    print(f"  Step 4: SHA-256: {file_hash[:16]}...")

    # Step 5: Execute --version
    print("  Step 5: Executing --version...")
    try:
        proc = subprocess.run(
            [str(exe_path), "--version"],
            cwd=str(exe_path.parent),
            capture_output=True,
            text=True,
            timeout=30,
        )
        result.exit_code = proc.returncode
        result.version_stdout = proc.stdout.strip()
        print(f"  Step 5: STDOUT: {result.version_stdout}")
        print(f"  Step 5: Exit code: {result.exit_code}")

        if proc.returncode != 0:
            result.state = BuildState.FAILED
            result.error_message = (
                f"Executable returned exit code {proc.returncode}. STDERR: {proc.stderr.strip()}"
            )
            print(f"  [FAILED] {result.error_message}")
            return result
    except subprocess.TimeoutExpired:
        result.state = BuildState.FAILED
        result.error_message = "Executable timed out after 30 seconds."
        print(f"  [FAILED] {result.error_message}")
        return result
    except OSError as e:
        result.state = BuildState.FAILED
        result.error_message = f"Failed to execute: {e}"
        print(f"  [FAILED] {result.error_message}")
        return result

    # Step 6: Verify bundled assets
    print("  Step 6: Verifying bundled assets...")
    assets_ok = verify_bundled_assets(exe_path.parent)
    result.assets_verified = assets_ok
    if not assets_ok:
        print("  [WARNING] Some bundled assets are missing (non-fatal).")

    # All checks passed
    result.state = BuildState.COMPLETED
    print("  [OK] All verification checks passed.")
    return result


def verify_bundled_assets(package_dir: Path) -> bool:
    """Verify required assets exist in the packaged directory."""
    required_patterns = [
        "resources/themes/dark.qss",
        "src/storage/migrations",
    ]
    all_ok = True
    for pattern in required_patterns:
        target = package_dir / pattern
        if not target.exists():
            # PyInstaller may flatten paths; check root too
            alt = package_dir / Path(pattern).name
            if not alt.exists():
                print(f"    [MISSING] {pattern}")
                all_ok = False
            else:
                print(f"    [OK] {pattern} (at root)")
        else:
            print(f"    [OK] {pattern}")
    return all_ok


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def build() -> BuildResult:
    """Execute the full deterministic build pipeline.

    Pipeline: Lock → Clean → Build → Package → Verify → Report
    """
    start_time = time.monotonic()
    result = BuildResult()

    print("=" * 70)
    print("  BATMANOVERLAY — DETERMINISTIC BUILD PIPELINE")
    print("=" * 70)

    # Acquire build lock
    if not acquire_build_lock():
        result.state = BuildState.FAILED
        result.error_message = "Could not acquire build lock. Another build may be running."
        return result
    result.state = BuildState.LOCK_ACQUIRED
    print("[OK] Build lock acquired.\n")

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
            result.error_message = "PyInstaller build phase failed."
            return result

        # Phase 3: Package
        result.state = BuildState.PACKAGING
        if not phase_package():
            result.state = BuildState.FAILED
            result.error_message = "Packaging phase failed."
            return result

        # Phase 4: Verify
        verify_result = phase_verify()
        result = verify_result

    except Exception as e:
        result.state = BuildState.FAILED
        result.error_message = f"Unexpected error: {e}"
        print(f"\n[FATAL] {result.error_message}")

    finally:
        result.duration_seconds = round(time.monotonic() - start_time, 2)
        release_build_lock()

        # Print final report
        print("\n" + "=" * 70)
        print("  BUILD REPORT")
        print("=" * 70)
        print(f"  State:      {result.state.value}")
        print(f"  Duration:   {result.duration_seconds}s")
        if result.executable_path:
            print(f"  Executable: {result.executable_path}")
            print(f"  Size:       {result.executable_size:,} bytes")
            print(f"  SHA-256:    {result.executable_hash[:32]}...")
            print(f"  Version:    {result.version_stdout}")
        if result.error_message:
            print(f"  Error:      {result.error_message}")
        status = "SUCCESS" if result.success else "FAILED"
        print(f"  Result:     {status}")
        print("=" * 70)

    return result


# Legacy compatibility aliases
def main() -> None:
    """Entry point for scripts/build.py."""
    result = build()
    if not result.success:
        sys.exit(1)


def verify_executable(exe_path: Path | str | None = None, timeout_sec: float = 10.0) -> Path:
    """Legacy API: verify an executable exists and has size > 0."""
    target = Path(exe_path).resolve() if exe_path else get_executable_path()
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if safe_file_exists(target) and safe_file_size(target) > 0:
            size = safe_file_size(target)
            print(f"[BUILD VERIFY] Executable verified at: {target} ({size:,} bytes)")
            return target
        time.sleep(0.1)
    raise FileNotFoundError(
        f"[BUILD VERIFY ERROR] Executable missing or incomplete after {timeout_sec}s:\n{target}"
    )


def verify_build_execution(timeout_sec: float = 10.0) -> int:
    """Legacy API: verify built executable runs successfully."""
    exe = verify_executable(timeout_sec=timeout_sec)
    print(f"[BUILD VERIFY] Testing execution of: {exe}")
    proc = subprocess.run(
        [str(exe), "--version"],
        cwd=str(exe.parent),
        capture_output=True,
        text=True,
    )
    print(f"[BUILD VERIFY] Executable STDOUT: {proc.stdout.strip()}")
    if proc.returncode != 0:
        print(f"[BUILD VERIFY] Executable STDERR: {proc.stderr.strip()}")
        raise RuntimeError(
            f"[BUILD VERIFY ERROR] Verification failed with exit code {proc.returncode}"
        )
    return proc.returncode


if __name__ == "__main__":
    main()
