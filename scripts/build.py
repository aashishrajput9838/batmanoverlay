"""Build script for packaging batmanoverlay into a portable Windows executable."""

import contextlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
SRC_DIR = ROOT_DIR / "src"
RESOURCES_DIR = ROOT_DIR / "resources"


def get_executable_path() -> Path:
    """Return absolute, resolved path to compiled portable executable."""
    return (DIST_DIR / "batmanoverlay" / "batmanoverlay.exe").resolve()


def verify_executable(exe_path: Path | str | None = None, timeout_sec: float = 10.0) -> Path:
    """Centralized verification that the executable exists, is non-empty, and fully written.

    Args:
        exe_path: Path to executable. Defaults to get_executable_path().
        timeout_sec: Maximum seconds to wait for file writing to complete.

    Returns:
        Absolute resolved Path object.

    Raises:
        FileNotFoundError: If executable does not exist or remains 0 bytes after timeout.
    """
    target = Path(exe_path).resolve() if exe_path else get_executable_path()
    start_time = time.perf_counter()

    while time.perf_counter() - start_time < timeout_sec:
        if target.exists() and target.is_file() and target.stat().st_size > 0:
            file_size = target.stat().st_size
            print(f"[BUILD VERIFY] Executable verified at: {target} ({file_size:,} bytes)")
            return target
        time.sleep(0.1)

    raise FileNotFoundError(
        f"[BUILD VERIFY ERROR] Executable missing or incomplete after {timeout_sec}s:\n{target}"
    )


def verify_build_execution(timeout_sec: float = 10.0) -> int:
    """Verify built executable runs successfully in deterministic environment."""
    exe = verify_executable(timeout_sec=timeout_sec)
    print(f"[BUILD VERIFY] Testing execution of: {exe}")

    result = subprocess.run(
        [str(exe), "--version"],
        cwd=str(exe.parent),
        capture_output=True,
        text=True,
    )
    print(f"[BUILD VERIFY] Executable STDOUT: {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"[BUILD VERIFY] Executable STDERR: {result.stderr.strip()}")
        raise RuntimeError(
            f"[BUILD VERIFY ERROR] Verification failed with exit code {result.returncode}"
        )
    return result.returncode


def clean() -> None:
    """Clean build and dist directories."""
    print("Cleaning build directories...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    spec_file = ROOT_DIR / "batmanoverlay.spec"
    if spec_file.exists():
        with contextlib.suppress(Exception):
            spec_file.unlink()


def run_pyinstaller() -> None:
    """Execute PyInstaller to compile the executable."""
    print(f"Executing PyInstaller build (distpath={DIST_DIR})...")
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

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    print("PyInstaller Return Code:", result.returncode)
    print("PyInstaller STDOUT (last 500 chars):", result.stdout[-500:])
    print("PyInstaller STDERR (last 500 chars):", result.stderr[-500:])
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller failed with code {result.returncode}")
    print("PyInstaller finished successfully.")


def assemble_portable_package() -> None:
    """Assemble portable zero-install package directory structure."""
    print("Assembling portable package...")
    target_dir = DIST_DIR / "batmanoverlay"
    source_dir = BUILD_DIR / "batmanoverlay"

    if not target_dir.exists() and source_dir.exists():
        shutil.copytree(source_dir, target_dir)
    elif (
        not (target_dir / "batmanoverlay.exe").exists()
        and (source_dir / "batmanoverlay.exe").exists()
    ):
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

    # Create portable data structure
    (target_dir / "data" / "config").mkdir(parents=True, exist_ok=True)
    (target_dir / "data" / "logs").mkdir(parents=True, exist_ok=True)
    (target_dir / "data" / "sessions").mkdir(parents=True, exist_ok=True)

    # Copy License and Readme
    if (ROOT_DIR / "README.md").exists():
        shutil.copy2(ROOT_DIR / "README.md", target_dir / "README.md")
    if (ROOT_DIR / "LICENSE").exists():
        shutil.copy2(ROOT_DIR / "LICENSE", target_dir / "LICENSE")

    print(f"Portable build complete: {target_dir}")


def main() -> None:
    clean()
    run_pyinstaller()
    assemble_portable_package()
    verify_build_execution()


if __name__ == "__main__":
    main()
