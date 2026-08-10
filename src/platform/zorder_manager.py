"""
Z-Order Watchdog and CBT Hook Manager for BatmanOverlay.

Integrates native C++ batmanoverlay_zorder.dll (when compiled) with
in-process Win32 ctypes fallback for non-stop HWND_TOPMOST enforcement.
"""

from __future__ import annotations

import contextlib
import ctypes
import sys
import threading
import time
from pathlib import Path
from typing import Any

from loguru import logger

DLL_PATH = Path(__file__).parent / "native" / "batmanoverlay_zorder.dll"


class ZOrderWatchdogManager:
    """
    Manages continuous HWND_TOPMOST Z-order watchdog thread and WH_CBT window hooks.
    """

    def __init__(self, hwnd: int = 0) -> None:
        self._hwnd = hwnd
        self._dll: Any = None
        self._is_dll_loaded = False
        self._python_thread: threading.Thread | None = None
        self._python_running = False
        self._user32: Any = None

        if sys.platform == "win32":
            self._user32 = getattr(ctypes.windll, "user32", None)
            self._load_native_dll()

    def set_hwnd(self, hwnd: int) -> None:
        """Update target window handle."""
        self._hwnd = hwnd

    def _load_native_dll(self) -> None:
        """Attempt to load native batmanoverlay_zorder.dll."""
        if DLL_PATH.exists():
            try:
                self._dll = ctypes.CDLL(str(DLL_PATH))
                self._dll.StartZOrderWatchdog.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
                self._dll.StartZOrderWatchdog.restype = ctypes.c_bool
                self._dll.StopZOrderWatchdog.restype = ctypes.c_bool
                self._dll.InstallCBTHook.argtypes = [ctypes.c_void_p]
                self._dll.InstallCBTHook.restype = ctypes.c_bool
                self._dll.RemoveCBTHook.restype = ctypes.c_bool
                self._dll.IsWatchdogActive.restype = ctypes.c_bool
                self._is_dll_loaded = True
                logger.info(f"[ZORDER MANAGER] Loaded native C++ DLL from '{DLL_PATH}'")
            except Exception as err:
                logger.warning(
                    f"[ZORDER MANAGER] Native DLL load failed: {err}; fallback to Python ctypes"
                )

    def start_watchdog(self, hwnd: int | None = None, interval_ms: int = 16) -> bool:
        """Start continuous topmost Z-order watchdog thread and CBT hook."""
        if hwnd:
            self._hwnd = hwnd

        if not self._hwnd:
            logger.warning("[ZORDER MANAGER] Cannot start watchdog: invalid HWND")
            return False

        if self._is_dll_loaded and self._dll:
            try:
                res_w = self._dll.StartZOrderWatchdog(ctypes.c_void_p(self._hwnd), interval_ms)
                res_h = self._dll.InstallCBTHook(ctypes.c_void_p(self._hwnd))
                logger.info(
                    f"[ZORDER MANAGER] Native C++ Watchdog started: hwnd={self._hwnd} | "
                    f"watchdog={res_w} | cbt_hook={res_h}"
                )
                return bool(res_w)
            except Exception as err:
                logger.error(f"[ZORDER MANAGER] Native DLL call error: {err}")

        # Python ctypes Fallback Watchdog
        if self._python_running:
            return True

        self._python_running = True
        self._python_thread = threading.Thread(
            target=self._python_watchdog_loop,
            args=(interval_ms,),
            daemon=True,
            name="ZOrderWatchdogThread",
        )
        self._python_thread.start()
        logger.info(f"[ZORDER MANAGER] Python ctypes Watchdog started for HWND={self._hwnd}")
        return True

    def stop_watchdog(self) -> bool:
        """Stop watchdog thread and uninstall CBT hooks."""
        if self._is_dll_loaded and self._dll:
            with contextlib.suppress(Exception):
                self._dll.StopZOrderWatchdog()
                self._dll.RemoveCBTHook()

        if self._python_running:
            self._python_running = False
            if self._python_thread and self._python_thread.is_alive():
                self._python_thread.join(timeout=0.5)
            self._python_thread = None

        logger.info("[ZORDER MANAGER] Z-Order Watchdog stopped.")
        return True

    def _python_watchdog_loop(self, interval_ms: int) -> None:
        """Fallback thread maintaining HWND_TOPMOST via user32.SetWindowPos."""
        if not self._user32:
            return

        hwnd_ptr = ctypes.c_void_p(self._hwnd)
        hwnd_topmost = ctypes.c_void_p(-1)  # HWND_TOPMOST
        swp_flags = (
            0x0001 | 0x0002 | 0x0010 | 0x0040
        )  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        interval_sec = max(0.01, interval_ms / 1000.0)

        while self._python_running and self._hwnd:
            try:
                if self._user32.IsWindow(hwnd_ptr):
                    self._user32.SetWindowPos(hwnd_ptr, hwnd_topmost, 0, 0, 0, 0, swp_flags)
            except Exception:
                pass
            time.sleep(interval_sec)
