"""Platform abstractions for target acquisition and input synthesis."""

import sys

from src.platform.global_hotkey import (
    HOTKEY_ID_CTRL_ALT_E,
    MOD_ALT,
    MOD_CONTROL,
    MSG,
    VK_E,
    WM_HOTKEY,
    WindowsGlobalHotkeyManager,
)
from src.platform.mock_target import MockKeyInputSender, MockTargetAcquirer
from src.platform.models import TargetInfo, ValidationResult
from src.platform.protocols import IKeyInputSender, ITargetAcquirer
from src.platform.security import apply_uipi_message_filter, harden_process_security
from src.platform.windows_target import WindowsKeyInputSender, WindowsTargetAcquirer


def get_platform_target_acquirer() -> ITargetAcquirer:
    """Return OS-appropriate target acquirer."""
    if sys.platform == "win32":
        return WindowsTargetAcquirer()
    return MockTargetAcquirer()  # type: ignore[unreachable]


def get_platform_input_sender() -> IKeyInputSender:
    """Return OS-appropriate key input sender."""
    if sys.platform == "win32":
        return WindowsKeyInputSender()
    return MockKeyInputSender()  # type: ignore[unreachable]


__all__ = [
    "HOTKEY_ID_CTRL_ALT_E",
    "MOD_ALT",
    "MOD_CONTROL",
    "MSG",
    "VK_E",
    "WM_HOTKEY",
    "IKeyInputSender",
    "ITargetAcquirer",
    "MockKeyInputSender",
    "MockTargetAcquirer",
    "TargetInfo",
    "ValidationResult",
    "WindowsGlobalHotkeyManager",
    "WindowsKeyInputSender",
    "WindowsTargetAcquirer",
    "apply_uipi_message_filter",
    "get_platform_input_sender",
    "get_platform_target_acquirer",
    "harden_process_security",
]
