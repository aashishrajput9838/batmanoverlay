"""
Build script to compile native C++ Z-Order Watchdog DLL for BatmanOverlay.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
CPP_SRC = ROOT_DIR / "src" / "platform" / "native" / "batmanoverlay_zorder.cpp"
OUT_DLL = ROOT_DIR / "src" / "platform" / "native" / "batmanoverlay_zorder.dll"


def build_dll() -> bool:
    if not CPP_SRC.exists():
        print(f"Error: Source file {CPP_SRC} does not exist.")
        return False

    OUT_DLL.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try MSVC cl.exe
    cl_path = shutil.which("cl.exe")
    if cl_path:
        print("Compiling with MSVC cl.exe...")
        cmd = [
            cl_path,
            "/LD",
            "/O2",
            "/EHsc",
            str(CPP_SRC),
            f"/Fe{OUT_DLL}",
            "user32.lib",
            "kernel32.lib",
        ]
        res = subprocess.run(cmd, cwd=str(OUT_DLL.parent), capture_output=True, text=True)
        if res.returncode == 0 and OUT_DLL.exists():
            print(f"Successfully compiled DLL: {OUT_DLL}")
            return True
        print(f"MSVC compilation failed: {res.stderr or res.stdout}")

    # 2. Try MinGW g++ or gcc
    gcc_path = shutil.which("g++") or shutil.which("gcc")
    if gcc_path:
        print(f"Compiling with {gcc_path}...")
        cmd = [
            gcc_path,
            "-shared",
            "-O2",
            str(CPP_SRC),
            "-o",
            str(OUT_DLL),
            "-luser32",
            "-lkernel32",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and OUT_DLL.exists():
            print(f"Successfully compiled DLL: {OUT_DLL}")
            return True
        print(f"GCC compilation failed: {res.stderr or res.stdout}")

    # 3. Try clang / clang++
    clang_path = shutil.which("clang++") or shutil.which("clang")
    if clang_path:
        print(f"Compiling with {clang_path}...")
        cmd = [
            clang_path,
            "-shared",
            "-O2",
            str(CPP_SRC),
            "-o",
            str(OUT_DLL),
            "-luser32",
            "-lkernel32",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and OUT_DLL.exists():
            print(f"Successfully compiled DLL: {OUT_DLL}")
            return True
        print(f"Clang compilation failed: {res.stderr or res.stdout}")

    print("Warning: No native C++ compiler (cl, gcc, clang) found on system PATH.")
    print("batmanoverlay_zorder.dll was not created. Python ctypes fallback will be used.")
    return False


if __name__ == "__main__":
    success = build_dll()
    sys.exit(0 if success else 1)
