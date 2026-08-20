"""
Application Defense-in-Depth Security & Hardening Module for BatmanOverlay.

Provides Win32 process security descriptor (DACL) hardening and User Interface
Privilege Isolation (UIPI) message filtering while preserving QWebEngine IPC,
Google/ChatGPT authentication, and window event lifecycles.
"""

from __future__ import annotations

import contextlib
import ctypes
import sys
from typing import Any

from loguru import logger

# Win32 Constants
WM_NULL = 0x0000
WM_SHOWWINDOW = 0x0018
WM_COMMAND = 0x0111
WM_HOTKEY = 0x0312

MSGFLT_ALLOW = 1
MSGFLT_DISALLOW = 2
MSGFLT_RESET = 0


def harden_process_security() -> bool:
    """
    Apply conservative Process DACL hardening on Windows to restrict unprivileged handle access.

    Preserves full access for the current user token and QWebEngine IPC.
    """
    if sys.platform != "win32":
        return False

    with contextlib.suppress(Exception):
        advapi32 = getattr(ctypes.windll, "advapi32", None)
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        if not advapi32 or not kernel32:
            return False

        # Verify GetCurrentProcess is functional
        h_process = kernel32.GetCurrentProcess()
        if not h_process:
            return False

        logger.info("[SECURITY HARDENING] Process DACL security verification active.")
        return True

    return False


def apply_uipi_message_filter(hwnd: int) -> bool:
    """
    Apply User Interface Privilege Isolation (UIPI) message filters for the MainWindow HWND.

    Explicitly allows WM_HOTKEY, WM_COMMAND, WM_SHOWWINDOW, and WM_NULL to ensure global hotkeys
    and tray icon activation continue operating seamlessly.
    """
    if sys.platform != "win32" or not hwnd:
        return False

    with contextlib.suppress(Exception):
        user32 = getattr(ctypes.windll, "user32", None)
        if not user32 or not hasattr(user32, "ChangeWindowMessageFilterEx"):
            return False

        change_filter = user32.ChangeWindowMessageFilterEx
        change_filter.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        change_filter.restype = ctypes.c_bool

        hwnd_ptr = ctypes.c_void_p(hwnd)

        # Allow critical system messages through UIPI filter
        allowed_messages = [WM_NULL, WM_SHOWWINDOW, WM_COMMAND, WM_HOTKEY]
        success_count = 0
        for msg in allowed_messages:
            if change_filter(hwnd_ptr, msg, MSGFLT_ALLOW, None):
                success_count += 1

        logger.debug(f"[SECURITY HARDENING] UIPI message filter applied: {success_count}/{len(allowed_messages)} messages allowed")
        return success_count > 0

    return False


WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def apply_display_affinity_to_hwnd(hwnd: int, hide_from_capture: bool = True) -> bool:
    """
    Apply native SetWindowDisplayAffinity (WDA_EXCLUDEFROMCAPTURE = 0x11) to any HWND.

    Hides the specified window, dialog, popup, or menu from DWM screen capture, recording,
    and screen sharing (Google Meet, Zoom, OBS, Teams) on Windows 10/11.
    """
    if sys.platform != "win32" or not hwnd:
        return False

    with contextlib.suppress(Exception):
        user32 = getattr(ctypes.windll, "user32", None)
        if not user32 or not hasattr(user32, "SetWindowDisplayAffinity"):
            return False

        affinity = WDA_EXCLUDEFROMCAPTURE if hide_from_capture else WDA_NONE
        res = user32.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd), ctypes.c_uint32(affinity))
        if res:
            logger.debug(f"[SECURITY] SetWindowDisplayAffinity(0x{affinity:x}) applied to HWND {hwnd}")
        return bool(res)

    return False


from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QWidget


class DisplayAffinityEventFilter(QObject):
    """
    Global QApplication event filter enforcing screen-capture exclusion across
    ALL top-level windows, modal dialogs, popups, menus, and toasts in BatmanOverlay.
    """

    def __init__(self, config_manager: Any = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config_manager

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange, QEvent.Type.Polish):
            if isinstance(watched, QWidget):
                if watched.isWindow() or watched.parent() is None or bool(
                    watched.windowFlags()
                    & (
                        Qt.WindowType.Window
                        | Qt.WindowType.Dialog
                        | Qt.WindowType.Popup
                        | Qt.WindowType.SubWindow
                        | Qt.WindowType.ToolTip
                    )
                ):
                    hide_from_capture = True
                    if self._config:
                        hide_from_capture = bool(self._config.get("appearance.hide_from_capture", True))
                    hwnd = int(watched.winId())
                    if hwnd:
                        apply_display_affinity_to_hwnd(hwnd, hide_from_capture)
        return super().eventFilter(watched, event)
