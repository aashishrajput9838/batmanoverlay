"""Unit tests for WindowsGlobalHotkeyManager and Ctrl+Alt+E focus restoration hotkey."""

import ctypes
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QByteArray, Qt

from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.platform.global_hotkey import (
    HOTKEY_ID_CTRL_ALT_E,
    MOD_ALT,
    MOD_CONTROL,
    MSG,
    VK_E,
    WM_HOTKEY,
    WindowsGlobalHotkeyManager,
)
from src.ui.main_window import MainWindow


@pytest.mark.unit
def test_win64_msg_struct_alignment():
    """Verify MSG structure has correct sizeof and wParam byte offset (16) on Win64 ABI."""
    assert ctypes.sizeof(MSG) == 48
    assert MSG.wParam.offset == 16


@pytest.mark.unit
def test_global_hotkey_manager_registration_and_unregistration():
    """Verify WindowsGlobalHotkeyManager handles registration success and failure cleanly."""
    mgr = WindowsGlobalHotkeyManager()
    mgr._user32 = MagicMock()

    # Success case
    mgr._user32.RegisterHotKey.return_value = 1
    assert mgr.register_hotkey(12345, HOTKEY_ID_CTRL_ALT_E, MOD_CONTROL | MOD_ALT, VK_E) is True
    assert mgr._user32.RegisterHotKey.call_count == 1
    args = mgr._user32.RegisterHotKey.call_args[0]
    assert args[1] == HOTKEY_ID_CTRL_ALT_E
    assert args[2] == MOD_CONTROL | MOD_ALT
    assert args[3] == VK_E

    mgr._user32.UnregisterHotKey.return_value = 1
    assert mgr.unregister_hotkey(12345, HOTKEY_ID_CTRL_ALT_E) is True
    assert mgr._user32.UnregisterHotKey.call_count == 1
    un_args = mgr._user32.UnregisterHotKey.call_args[0]
    assert un_args[1] == HOTKEY_ID_CTRL_ALT_E

    # Failure case (e.g. shortcut collision)
    mgr._user32.RegisterHotKey.return_value = 0
    assert mgr.register_hotkey(12345, HOTKEY_ID_CTRL_ALT_E, MOD_CONTROL | MOD_ALT, VK_E) is False


@pytest.mark.unit
@pytest.mark.ui
def test_main_window_restore_and_focus_preserves_transparency(tmp_path, qtbot):
    """Verify restore_and_focus restores window focus without mutating transparency or settings."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    # Set non-zero transparency (75%)
    win.overlay_visibility_panel.set_transparency(75)
    win._on_transparency_changed(75)
    assert win.overlay_visibility_panel.get_transparency() == 75
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 0.25

    # Minimize window
    win.showMinimized()

    # Execute restore_and_focus
    win.restore_and_focus()

    # Verify window is restored and transparency remains unchanged at 75%
    assert not win.isMinimized()
    assert win.overlay_visibility_panel.get_transparency() == 75
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 0.25
    assert config_mgr.get("appearance.overlay_transparency") == 75


@pytest.mark.unit
@pytest.mark.ui
def test_main_window_native_event_hotkey_handling(tmp_path, qtbot):
    """Verify WM_HOTKEY native event triggers restore_and_focus."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    restore_mock = MagicMock()
    win.restore_and_focus = restore_mock

    # Create dummy MSG structure for WM_HOTKEY Ctrl+Alt+E
    msg = MSG()
    msg.message = WM_HOTKEY
    msg.wParam = HOTKEY_ID_CTRL_ALT_E
    msg_addr = ctypes.addressof(msg)

    q_evt = QByteArray(b"windows_generic_MSG")
    handled, _res = win.nativeEvent(q_evt, msg_addr)
    assert handled is True
    restore_mock.assert_called_once()


@pytest.mark.unit
@pytest.mark.ui
def test_main_window_close_unregisters_hotkeys(tmp_path, qtbot):
    """Verify MainWindow unregisters global hotkeys when closed."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    win._hotkey_manager = MagicMock()
    win._hotkey_registered = True

    qtbot.mouseClick(win.title_bar._btn_close, Qt.MouseButton.LeftButton)
    assert win._hotkey_registered is False
    win._hotkey_manager.unregister_hotkey.assert_called_once()
