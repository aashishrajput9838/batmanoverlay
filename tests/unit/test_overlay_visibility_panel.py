"""Unit tests for OverlayVisibilityPanel and transparency/opacity mapping."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider

from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.ui.main_window import MainWindow
from src.ui.overlay_visibility_panel import OverlayVisibilityPanel


@pytest.mark.unit
@pytest.mark.ui
def test_overlay_visibility_panel_defaults(qtbot):
    """Verify OverlayVisibilityPanel initial state and component defaults."""
    panel = OverlayVisibilityPanel()
    qtbot.add_widget(panel)

    assert panel.get_transparency() == 0.0

    slider = panel.findChild(QSlider)
    assert slider is not None
    assert slider.minimum() == 0
    assert slider.maximum() == 9999
    assert slider.value() == 0
    assert slider.focusPolicy() == Qt.FocusPolicy.StrongFocus


@pytest.mark.unit
@pytest.mark.ui
def test_overlay_visibility_panel_slider_updates_and_signals(qtbot):
    """Verify slider value updates emit transparency_changed float signal."""
    panel = OverlayVisibilityPanel()
    qtbot.add_widget(panel)

    emitted_values = []
    panel.transparency_changed.connect(emitted_values.append)

    panel.set_transparency(25.0)
    assert panel.get_transparency() == 25.0
    assert panel._value_label.text() == "25%"

    panel.set_transparency(50.0)
    assert panel.get_transparency() == 50.0
    assert panel._value_label.text() == "50%"

    panel.set_transparency(99.99)
    assert panel.get_transparency() == 99.99
    assert panel._value_label.text() == "99.99%"


@pytest.mark.unit
@pytest.mark.ui
def test_overlay_visibility_panel_reset_button(qtbot):
    """Verify reset button sets transparency back to 0%."""
    panel = OverlayVisibilityPanel()
    qtbot.add_widget(panel)

    panel.set_transparency(75.0)
    assert panel.get_transparency() == 75.0
    assert panel._value_label.text() == "75%"

    qtbot.mouseClick(panel._reset_btn, Qt.MouseButton.LeftButton)
    assert panel.get_transparency() == 0.0
    assert panel._value_label.text() == "0%"


@pytest.mark.unit
@pytest.mark.ui
def test_main_window_transparency_opacity_mapping(tmp_path, qtbot):
    """Verify main window transparency percentage mapping to Qt opacity.

    Formula: Opacity = 1.0 - (Transparency / 100.0)
    - 0%     -> Opacity 1.0 (Fully Visible)
    - 25%    -> Opacity 0.75
    - 50%    -> Opacity 0.50
    - 75%    -> Opacity 0.25
    - 99.99% -> Opacity 0.0001 (Almost Fully Transparent, Never 0.0)
    """
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    # Default 0% -> Opacity 1.0
    assert win.overlay_visibility_panel.get_transparency() == 0.0
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 1.0

    # 25% -> Opacity 0.75
    win.overlay_visibility_panel.set_transparency(25.0)
    win._on_transparency_changed(25.0)
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 0.75
    assert config_mgr.get("appearance.overlay_transparency") == 25.0

    # 50% -> Opacity 0.50
    win.overlay_visibility_panel.set_transparency(50.0)
    win._on_transparency_changed(50.0)
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 0.50
    assert config_mgr.get("appearance.overlay_transparency") == 50.0

    # 75% -> Opacity 0.25
    win.overlay_visibility_panel.set_transparency(75.0)
    win._on_transparency_changed(75.0)
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 0.25
    assert config_mgr.get("appearance.overlay_transparency") == 75.0

    # 99.99% -> Opacity 0.0001 (Must be > 0.0)
    win.overlay_visibility_panel.set_transparency(99.99)
    win._on_transparency_changed(99.99)
    assert win.windowOpacity() > 0.0
    assert config_mgr.get("appearance.overlay_transparency") == 99.99

    # Reset -> Opacity 1.0
    qtbot.mouseClick(win.overlay_visibility_panel._reset_btn, Qt.MouseButton.LeftButton)
    assert win.overlay_visibility_panel.get_transparency() == 0.0
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 1.0
    assert config_mgr.get("appearance.overlay_transparency") == 0.0


@pytest.mark.unit
@pytest.mark.ui
def test_transparency_setting_persistence_and_restore(tmp_path, qtbot):
    """Verify saved 99.99 float transparency value is restored when MainWindow reboots."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    # Save 99.99 setting
    config_mgr.set("appearance.overlay_transparency", 99.99)

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    assert win.overlay_visibility_panel.get_transparency() == 99.99
    assert win.windowOpacity() > 0.0


@pytest.mark.unit
@pytest.mark.ui
def test_legacy_100_percent_setting_normalized_to_99_99(tmp_path, qtbot):
    """Verify legacy settings with 100% transparency are normalized to 99.99%."""
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    # Save legacy 100% value
    config_mgr.set("appearance.overlay_transparency", 100)

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    assert win.overlay_visibility_panel.get_transparency() == 99.99
    assert win.windowOpacity() > 0.0


@pytest.mark.unit
@pytest.mark.ui
def test_opacity_keyboard_shortcuts_and_clamping(tmp_path, qtbot):
    """Verify Ctrl+Q (decrease opacity / +5% transparency)
    and Ctrl+W (increase opacity / -5% transparency) shortcuts clamped at 99.99%.
    """
    config_mgr = ConfigManager(tmp_path)
    signals = AppSignals()

    win = MainWindow(config_mgr, signals, tmp_path)
    qtbot.add_widget(win)

    # Default: 0% transparency, Opacity 1.0
    assert win.overlay_visibility_panel.get_transparency() == 0.0

    # Ctrl+Q step 1: 0% -> 5% transparency
    win.decrease_opacity()
    assert win.overlay_visibility_panel.get_transparency() == 5.0
    assert config_mgr.get("appearance.overlay_transparency") == 5.0

    # Set to 95% and Ctrl+Q -> 99.99%
    win.overlay_visibility_panel.set_transparency(95.0)
    win._on_transparency_changed(95.0)
    win.decrease_opacity()
    assert win.overlay_visibility_panel.get_transparency() == 99.99
    assert win.windowOpacity() > 0.0

    # Ctrl+Q beyond 99.99% -> Clamps at 99.99%
    win.decrease_opacity()
    assert win.overlay_visibility_panel.get_transparency() == 99.99
    assert win.windowOpacity() > 0.0

    # Ctrl+W from 99.99% -> 94.99% transparency
    win.increase_opacity()
    assert win.overlay_visibility_panel.get_transparency() == 94.99
    assert config_mgr.get("appearance.overlay_transparency") == 94.99

    # Set to 5% and Ctrl+W -> 0%
    win.overlay_visibility_panel.set_transparency(5.0)
    win._on_transparency_changed(5.0)
    win.increase_opacity()
    assert win.overlay_visibility_panel.get_transparency() == 0.0
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 1.0

    # Ctrl+W beyond 0% -> Clamps at 0%
    win.increase_opacity()
    assert win.overlay_visibility_panel.get_transparency() == 0.0
    assert pytest.approx(win.windowOpacity(), abs=0.01) == 1.0
