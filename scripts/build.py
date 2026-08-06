"""Build script for packaging batmanoverlay into a portable Windows executable."""

import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
SRC_DIR = ROOT_DIR / "src"
RESOURCES_DIR = ROOT_DIR / "resources"


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
    result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
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
    elif not (target_dir / "batmanoverlay.exe").exists() and (source_dir / "batmanoverlay.exe").exists():
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


if __name__ == "__main__":
    main()
