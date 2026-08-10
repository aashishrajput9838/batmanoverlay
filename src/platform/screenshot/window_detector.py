"""Top-level window enumeration, application-aware name detection, and process identification."""

import ctypes
import re
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class WindowInfo:
    """Container for top-level window information."""

    hwnd: int
    title: str
    app_name: str
    is_protected: bool
    left: int
    top: int
    width: int
    height: int
    process_id: int = 0
    process_name: str = ""


class WindowDetector:
    """Enumerates visible top-level application windows for screenshot naming and protection."""

    KNOWN_PROTECTED_TITLES: ClassVar[set[str]] = {
        "codetantra",
        "lockapp",
        "screenclippingHost",
        "windows default lock screen",
    }

    @classmethod
    def sanitize_app_name(cls, name: str) -> str:
        """Sanitize an application name for use in Windows filenames or UI toasts."""
        clean = re.sub(r'[\\/:*?"<>|]', "", name)
        clean = re.sub(r"\s+", "", clean.strip())
        return clean or "App"

    @classmethod
    def get_app_name_from_title(cls, title: str) -> str:
        """Extract user-facing application name from window title."""
        if not title:
            return "Application"

        lower = title.lower()
        mapping = [
            ("chrome", "Chrome"),
            ("visual studio code", "VSCode"),
            ("vs code", "VSCode"),
            ("vscode", "VSCode"),
            ("file explorer", "FileExplorer"),
            ("explorer", "FileExplorer"),
            ("codetantra", "CodeTantra"),
            ("edge", "Edge"),
            ("notepad", "Notepad"),
            ("word", "Word"),
            ("excel", "Excel"),
            ("powerpoint", "PowerPoint"),
        ]

        for keyword, name in mapping:
            if keyword in lower:
                return name

        # Fall back to first meaningful segment of window title
        parts = title.split(" - ")
        candidate = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
        return cls.sanitize_app_name(candidate)

    @classmethod
    def is_window_protected(cls, title: str, hwnd: int = 0) -> bool:
        """Return True if the window is flagged as protected/secure."""
        if title:
            lower = title.lower()
            if any(protected_title in lower for protected_title in cls.KNOWN_PROTECTED_TITLES):
                return True

        if hwnd and hasattr(ctypes, "windll"):
            try:
                user32 = getattr(ctypes.windll, "user32", None)
                if user32 and hasattr(user32, "GetWindowDisplayAffinity"):
                    aff = ctypes.c_uint32(0)
                    if user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(aff)) and aff.value in (
                        0x11,
                        0x01,
                    ):
                        return True
            except Exception:
                pass

        return False

    @classmethod
    def get_process_info_for_hwnd(cls, hwnd: int) -> tuple[int, str]:
        """Safely retrieve process ID and executable process name for a window handle."""
        if not hasattr(ctypes, "windll") or not hwnd:
            return 0, ""

        user32 = getattr(ctypes.windll, "user32", None)
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        psapi = getattr(ctypes.windll, "psapi", None)
        if not user32 or not kernel32:
            return 0, ""

        pid = ctypes.c_uint32(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return 0, ""

        process_name = ""
        # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_VM_READ (0x0010)
        h_process = kernel32.OpenProcess(0x0410, False, pid.value)
        if h_process:
            try:
                buf = ctypes.create_unicode_buffer(1024)
                if (
                    psapi
                    and hasattr(psapi, "GetModuleFileNameExW")
                    and psapi.GetModuleFileNameExW(h_process, None, buf, 1024) > 0
                ) or (
                    hasattr(kernel32, "GetProcessImageFileNameW")
                    and kernel32.GetProcessImageFileNameW(h_process, buf, 1024) > 0
                ):
                    process_name = Path(buf.value).name
            except Exception:
                process_name = ""
            finally:
                kernel32.CloseHandle(h_process)

        return pid.value, process_name

    @classmethod
    def get_visible_windows(cls) -> list[WindowInfo]:
        """Enumerate all visible, non-minimized top-level application windows."""
        if not hasattr(ctypes, "windll"):
            return []

        user32 = getattr(ctypes.windll, "user32", None)
        dwmapi = getattr(ctypes.windll, "dwmapi", None)
        if not user32:
            return []

        visible_windows: list[WindowInfo] = []

        def enum_windows_proc(hwnd: int, _lparam: int) -> bool:
            info = cls._inspect_window(hwnd, user32, dwmapi)
            if info is not None:
                visible_windows.append(info)
            return True

        wnd_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(wnd_proc(enum_windows_proc), 0)

        return visible_windows

    @classmethod
    def find_responsible_protected_window(
        cls, visible_windows: list[WindowInfo] | None = None
    ) -> WindowInfo | None:
        """Find the top-level visible window responsible for a protected capture failure."""
        if not hasattr(ctypes, "windll"):
            return None

        user32 = getattr(ctypes.windll, "user32", None)
        if not user32:
            return None

        # 1. Check active foreground window first
        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd:
            length = user32.GetWindowTextLengthW(fg_hwnd)
            if length > 0:
                title_buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(fg_hwnd, title_buf, length + 1)
                fg_title = title_buf.value.strip()
                if cls.is_window_protected(fg_title, fg_hwnd):
                    pid, proc_name = cls.get_process_info_for_hwnd(fg_hwnd)
                    return WindowInfo(
                        hwnd=fg_hwnd,
                        title=fg_title,
                        app_name=cls.get_app_name_from_title(fg_title),
                        is_protected=True,
                        left=0,
                        top=0,
                        width=100,
                        height=100,
                        process_id=pid,
                        process_name=proc_name,
                    )

        # 2. Search visible windows list for protected window
        windows = visible_windows if visible_windows is not None else cls.get_visible_windows()
        for w in windows:
            if w.is_protected:
                return w

        return None

    @classmethod
    def _inspect_window(
        cls, hwnd: int, user32: ctypes.WinDLL, dwmapi: ctypes.WinDLL | None
    ) -> WindowInfo | None:
        """Inspect a single window handle and return WindowInfo if valid top-level app."""
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return None

        ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        if ex_style & 0x00000080:  # WS_EX_TOOLWINDOW
            return None

        if dwmapi:
            cloaked = ctypes.c_uint32(0)
            hr = dwmapi.DwmGetWindowAttribute(
                hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            )
            if hr == 0 and cloaked.value != 0:
                return None

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return None

        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value.strip()

        if not title:
            return None

        ignore_list = ("Program Manager", "Default IME", "MSCTFIME UI", "BatmanOverlay")
        if any(title.startswith(prefix) for prefix in ignore_list):
            return None

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 10 or height <= 10:
            return None

        app_name = cls.get_app_name_from_title(title)
        is_prot = cls.is_window_protected(title, hwnd)
        pid, proc_name = cls.get_process_info_for_hwnd(hwnd)

        return WindowInfo(
            hwnd=hwnd,
            title=title,
            app_name=app_name,
            is_protected=is_prot,
            left=rect.left,
            top=rect.top,
            width=width,
            height=height,
            process_id=pid,
            process_name=proc_name,
        )

    @classmethod
    def build_screenshot_filename_prefix(cls, windows: list[WindowInfo]) -> str:
        """Generate application-aware filename prefix."""
        if not windows:
            return "Desktop"

        seen: set[str] = set()
        app_names: list[str] = []

        for w in windows:
            clean_name = cls.sanitize_app_name(w.app_name)
            if clean_name and clean_name not in seen:
                seen.add(clean_name)
                app_names.append(clean_name)

        if not app_names:
            return "Desktop"

        prefix = "+".join(app_names[:3])
        return prefix[:60]
