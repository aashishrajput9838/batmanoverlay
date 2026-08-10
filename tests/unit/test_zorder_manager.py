"""
Unit tests for ZOrderWatchdogManager.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from src.platform.zorder_manager import ZOrderWatchdogManager


def test_zorder_watchdog_manager_initialization() -> None:
    """Verify ZOrderWatchdogManager initialization defaults."""
    mgr = ZOrderWatchdogManager(hwnd=12345)
    assert mgr._hwnd == 12345
    assert mgr._python_running is False


def test_zorder_watchdog_manager_start_stop_fallback() -> None:
    """Verify start_watchdog and stop_watchdog lifecycle in fallback mode."""
    mgr = ZOrderWatchdogManager(hwnd=12345)
    mgr._is_dll_loaded = False  # Force fallback testing

    start_res = mgr.start_watchdog(hwnd=12345, interval_ms=20)
    assert start_res is True
    assert mgr._python_running is True
    assert mgr._python_thread is not None
    assert mgr._python_thread.is_alive()

    time.sleep(0.05)

    stop_res = mgr.stop_watchdog()
    assert stop_res is True
    assert mgr._python_running is False
    assert mgr._python_thread is None


def test_zorder_watchdog_manager_invalid_hwnd() -> None:
    """Verify starting watchdog with invalid HWND returns False."""
    mgr = ZOrderWatchdogManager(hwnd=0)
    res = mgr.start_watchdog(hwnd=0)
    assert res is False
    assert mgr._python_running is False


def test_zorder_watchdog_manager_native_dll_mock() -> None:
    """Verify native C++ DLL interface calls when loaded."""
    mgr = ZOrderWatchdogManager(hwnd=54321)
    mock_dll = MagicMock()
    mock_dll.StartZOrderWatchdog.return_value = True
    mock_dll.InstallCBTHook.return_value = True
    mock_dll.StopZOrderWatchdog.return_value = True
    mock_dll.RemoveCBTHook.return_value = True

    mgr._dll = mock_dll
    mgr._is_dll_loaded = True

    assert mgr.start_watchdog(hwnd=54321, interval_ms=16) is True
    mock_dll.StartZOrderWatchdog.assert_called_once()
    mock_dll.InstallCBTHook.assert_called_once()

    assert mgr.stop_watchdog() is True
    mock_dll.StopZOrderWatchdog.assert_called_once()
    mock_dll.RemoveCBTHook.assert_called_once()
