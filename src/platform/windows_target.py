"""Zero-dependency Windows ctypes target acquirer and SendInput keystroke engine."""

import ctypes
import sys
from pathlib import Path
from typing import Any, ClassVar

from src.platform.models import TargetInfo, ValidationResult

# Windows API Constants & Structures
HWND = ctypes.c_void_p
DWORD = ctypes.c_ulong
LONG = ctypes.c_long
UINT = ctypes.c_uint
WORD = ctypes.c_ushort

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_BACK = 0x08
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_V = 0x56


class MOUSEINPUT(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("dx", LONG),
        ("dy", LONG),
        ("mouseData", DWORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("uMsg", DWORD),
        ("wParamL", WORD),
        ("wParamH", WORD),
    ]


class InputUnion(ctypes.Union):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("type", DWORD),
        ("union", InputUnion),
    ]


class RECT(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("left", LONG),
        ("top", LONG),
        ("right", LONG),
        ("bottom", LONG),
    ]


class GUITHREADINFO(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("cbSize", DWORD),
        ("flags", DWORD),
        ("hwndActive", HWND),
        ("hwndFocus", HWND),
        ("hwndCapture", HWND),
        ("hwndMenuOwner", HWND),
        ("hwndMoveSize", HWND),
        ("hwndCaret", HWND),
        ("rcCaret", RECT),
    ]


class WindowsTargetAcquirer:
    """Acquires and validates Windows active foreground window and focused control."""

    BLOCKED_CLASSES: ClassVar[set[str]] = {
        "progman",
        "workerw",
        "shell_traywnd",
        "shell_secondarytraywnd",
        "syslistview32",
    }

    def __init__(self) -> None:
        self._user32: Any = None
        self._kernel32: Any = None

        if sys.platform == "win32":
            import ctypes.wintypes

            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32

    def get_foreground_target(self) -> TargetInfo | None:
        """Query Windows OS for the current foreground window and focused control."""
        if not self._user32:
            return None

        hwnd_fg = self._user32.GetForegroundWindow()
        if not hwnd_fg:
            return None

        # Get Window Title
        length = self._user32.GetWindowTextLengthW(hwnd_fg)
        buf = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd_fg, buf, length + 1)
        window_title = buf.value.strip() or "Untitled Window"

        # Get Process Name
        pid = DWORD()
        thread_id = self._user32.GetWindowThreadProcessId(hwnd_fg, ctypes.byref(pid))
        process_name = self._get_process_name(pid.value)

        # Get Focused Control HWND using GetGUIThreadInfo
        hwnd_focus = self._get_focused_hwnd(thread_id, hwnd_fg)

        # Get Control Class Name
        buf_cls = ctypes.create_unicode_buffer(256)
        self._user32.GetClassNameW(hwnd_focus or hwnd_fg, buf_cls, 256)
        control_type = buf_cls.value.strip() or "UnknownControl"

        return TargetInfo(
            window_title=window_title,
            process_name=process_name,
            control_type=control_type,
            hwnd_window=int(hwnd_fg or 0),
            hwnd_control=int(hwnd_focus or hwnd_fg or 0),
            is_editable=True,
        )

    def _get_focused_hwnd(self, thread_id: int, hwnd_fg: Any) -> Any:
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(GUITHREADINFO)

        if self._user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)) and info.hwndFocus:
            return info.hwndFocus
        return hwnd_fg

    def _get_process_name(self, pid: int) -> str:
        if not pid or not self._kernel32:
            return "unknown.exe"

        query_flags = 0x1000
        h_process = self._kernel32.OpenProcess(query_flags, False, pid)
        if not h_process:
            return "unknown.exe"

        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = DWORD(1024)
            if self._kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                return Path(buf.value).name
        finally:
            self._kernel32.CloseHandle(h_process)
        return "unknown.exe"

    def validate_target(self, target_info: TargetInfo | None) -> ValidationResult:
        """Validate whether the target window/control is suitable for keyboard input."""
        if target_info is None:
            return ValidationResult.failure("No active window is currently focused.")

        if not target_info.hwnd_window:
            return ValidationResult.failure("Foreground window handle is invalid.")

        control_class = target_info.control_type.lower()
        if control_class in self.BLOCKED_CLASSES:
            return ValidationResult.failure(
                f"Target control '{target_info.control_type}' is Desktop or System Shell."
            )

        if "desktop" in target_info.window_title.lower() and control_class in (
            "progman",
            "workerw",
        ):
            return ValidationResult.failure("Target is Windows Desktop background.")

        return ValidationResult.success(target_info)

    def acquire_and_validate_target(self) -> ValidationResult:
        """Acquire target immediately and return validation result."""
        target = self.get_foreground_target()
        return self.validate_target(target)


class WindowsKeyInputSender:
    """Synthesizes OS-level keyboard events using user32.SendInput."""

    def __init__(self) -> None:
        self._user32: Any = None
        if sys.platform == "win32":
            self._user32 = ctypes.windll.user32

    def send_char(self, char: str, _target: TargetInfo) -> bool:
        """Send a single character or surrogate pair to the OS focused window."""
        if not self._user32:
            return False

        if char in ("\n", "\r"):
            return self._send_vk(VK_RETURN)

        utf16_bytes = char.encode("utf-16-le")
        for i in range(0, len(utf16_bytes), 2):
            code_unit = utf16_bytes[i] | (utf16_bytes[i + 1] << 8)
            inputs = (INPUT * 2)()

            # Key Down
            inputs[0].type = INPUT_KEYBOARD
            inputs[0].union.ki.wScan = code_unit
            inputs[0].union.ki.dwFlags = KEYEVENTF_UNICODE

            # Key Up
            inputs[1].type = INPUT_KEYBOARD
            inputs[1].union.ki.wScan = code_unit
            inputs[1].union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

            self._user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        return True

    def send_backspace(self, _target: TargetInfo) -> bool:
        """Send backspace key press."""
        return self._send_vk(VK_BACK)

    def send_paste_chunk(self, _chunk: str, _target: TargetInfo) -> bool:
        """Send Ctrl+V paste shortcut or character chunk."""
        inputs = (INPUT * 4)()

        # Ctrl Down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = VK_CONTROL

        # V Down
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = VK_V

        # V Up
        inputs[2].type = INPUT_KEYBOARD
        inputs[2].union.ki.wVk = VK_V
        inputs[2].union.ki.dwFlags = KEYEVENTF_KEYUP

        # Ctrl Up
        inputs[3].type = INPUT_KEYBOARD
        inputs[3].union.ki.wVk = VK_CONTROL
        inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP

        if self._user32:
            self._user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
            return True
        return False

    def _send_vk(self, vk: int) -> bool:
        if not self._user32:
            return False

        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = vk

        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = vk
        inputs[1].union.ki.dwFlags = KEYEVENTF_KEYUP

        self._user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        return True
