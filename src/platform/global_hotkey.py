"""Zero-dependency Windows native global hotkey registration manager."""

import ctypes
from typing import Any, ClassVar

from loguru import logger

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_E = 0x45
WM_HOTKEY = 0x0312
HOTKEY_ID_CTRL_ALT_E = 0x011C


class MSG(ctypes.Structure):
    """Win32 MSG structure layout for 64-bit Windows native event processing."""

    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_ulonglong),
        ("lParam", ctypes.c_longlong),
        ("time", ctypes.c_ulong),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]


class WindowsGlobalHotkeyManager:
    """Manages native RegisterHotKey and UnregisterHotKey lifecycle on Windows."""

    def __init__(self) -> None:
        self._user32: Any = getattr(ctypes.windll, "user32", None)

    def register_hotkey(self, hwnd: int, hotkey_id: int, modifiers: int, vk: int) -> bool:
        """Register a global hotkey with Windows OS.

        Returns True on success, False if registration failed (e.g. key collision).
        """
        if not self._user32:
            logger.warning("user32 library not available; global hotkey registration skipped.")
            return False

        try:
            res = self._user32.RegisterHotKey(
                ctypes.c_void_p(hwnd) if hwnd else None,
                hotkey_id,
                modifiers,
                vk,
            )
            if res:
                logger.info(f"Registered global hotkey ID {hotkey_id} (hwnd={hwnd})")
                return True

            err = ctypes.GetLastError()
            logger.warning(
                f"Failed to register global hotkey ID {hotkey_id} (WinError: {err}). "
                "The shortcut may be in use by another application."
            )
            return False
        except Exception as err:
            logger.warning(f"Unexpected error registering hotkey ID {hotkey_id}: {err}")
            return False

    def unregister_hotkey(self, hwnd: int, hotkey_id: int) -> bool:
        """Unregister a previously registered global hotkey."""
        if not self._user32:
            return False

        try:
            res = self._user32.UnregisterHotKey(
                ctypes.c_void_p(hwnd) if hwnd else None,
                hotkey_id,
            )
            if res:
                logger.info(f"Unregistered global hotkey ID {hotkey_id}")
                return True
            return False
        except Exception as err:
            logger.warning(f"Unexpected error unregistering hotkey ID {hotkey_id}: {err}")
            return False
