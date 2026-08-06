# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for batmanoverlay.

Canonical build definition for producing the portable OneDir Windows package.
"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve()
SRC_DIR = ROOT / "src"
RESOURCES_DIR = ROOT / "resources"

a = Analysis(
    [str(SRC_DIR / "main.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        (str(RESOURCES_DIR), "resources"),
        (str(SRC_DIR / "storage" / "migrations"), "src/storage/migrations"),
    ],
    hiddenimports=[
        "encodings",
        "encodings.utf_8",
        "encodings.ascii",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebChannel",
        "PySide6.QtPrintSupport",
        "pydantic",
        "loguru",
        "psutil",
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="batmanoverlay",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="batmanoverlay",
)
