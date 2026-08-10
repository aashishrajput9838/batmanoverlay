"""Unit tests for System Tray lifecycle, minimize to tray, and taskbar suppression."""

import ctypes

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSystemTrayIcon

from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.ui.main_window import MainWindow


@pytest.mark.unit
@pytest.mark.ui
def test_system_tray_icon_initialization(tmp_path, qtbot):
    """Verify MainWindow initializes persistent QSystemTrayIcon."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    assert hasattr(win, "_tray_icon")
    assert isinstance(win._tray_icon, QSystemTrayIcon)
    assert win._tray_icon.contextMenu() is not None


@pytest.mark.unit
@pytest.mark.ui
def test_taskbar_button_suppression_flags_and_hwnd_style(tmp_path, qtbot):
    """Verify MainWindow has Qt.WindowType.Tool flag and native WS_EX_TOOLWINDOW extended style."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)
    win.show()

    assert bool(win.windowFlags() & Qt.WindowType.Tool)

    hwnd = int(win.winId()) if win.winId() else 0
    if hwnd and hasattr(ctypes, "windll"):
        user32 = getattr(ctypes.windll, "user32", None)
        if user32:
            get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
            get_style.restype = ctypes.c_ssize_t

            style = get_style(ctypes.c_void_p(hwnd), -20)
            assert bool(style & 0x00000080) is True  # WS_EX_TOOLWINDOW
            assert bool(style & 0x00040000) is False  # WS_EX_APPWINDOW


@pytest.mark.unit
@pytest.mark.ui
def test_minimize_hides_main_window_to_tray(tmp_path, qtbot):
    """Verify minimize action hides MainWindow without terminating application."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)
    win.show()
    assert win.isVisible()

    win._minimize_to_tray()
    assert not win.isVisible()


@pytest.mark.unit
@pytest.mark.ui
def test_restore_from_tray_preserves_transparency_and_geometry(tmp_path, qtbot):
    """Verify restore from system tray brings MainWindow to foreground with transparency."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    # Set transparency to 99.99%
    win.overlay_visibility_panel.set_transparency(99.99)
    win._on_transparency_changed(99.99)
    assert win.windowOpacity() > 0.0

    # Minimize to tray
    win._minimize_to_tray()
    assert not win.isVisible()

    # Restore from tray
    win.restore_and_focus()
    assert win.isVisible()
    assert win.windowOpacity() > 0.0
    assert win.overlay_visibility_panel.get_transparency() == 99.99
    assert bool(win.windowFlags() & Qt.WindowType.Tool)


@pytest.mark.unit
@pytest.mark.ui
def test_tray_activation_triggers_restore(tmp_path, qtbot):
    """Verify tray icon click/double-click triggers restore_and_focus."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)
    win._minimize_to_tray()
    assert not win.isVisible()

    win._on_tray_icon_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert win.isVisible()
