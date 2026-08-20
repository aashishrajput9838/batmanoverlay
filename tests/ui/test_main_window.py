"""UI tests for MainWindow shell and controls."""

from pathlib import Path

import pytest

from src.constants import PanelName
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.ui.main_window import MainWindow


@pytest.mark.ui
@pytest.mark.usefixtures("qapp")
def test_main_window_controls_and_panels(tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    signals = AppSignals()
    window = MainWindow(config_mgr, signals, tmp_data_dir)

    assert window.windowTitle() is not None
    assert window.title_bar is not None
    assert window.sidebar is not None
    assert window.status_bar is not None

    # Test Panel Switch
    window.switch_panel(PanelName.SETTINGS)
    assert window.sidebar._buttons[PanelName.SETTINGS].isChecked() is True

    # Test Window Collapse
    window.set_collapsed(True)
    assert window._is_collapsed is True
    assert window.height() == 36

    window.set_collapsed(False)
    assert window._is_collapsed is False

    # Test Window Opacity
    window.set_window_opacity(0.8)
    assert window.windowOpacity() == 0.8

    window.close()


@pytest.mark.ui
@pytest.mark.usefixtures("qapp")
def test_main_window_display_affinity_and_capture_exclusion(tmp_data_dir: Path) -> None:
    """Verify MainWindow invokes _apply_native_display_affinity on config change."""
    config_mgr = ConfigManager(tmp_data_dir)
    signals = AppSignals()
    window = MainWindow(config_mgr, signals, tmp_data_dir)

    called = []
    window._apply_native_display_affinity = lambda: called.append(True)

    config_mgr.set("appearance.hide_from_capture", False)
    assert len(called) == 1

    config_mgr.set("appearance.hide_from_capture", True)
    assert len(called) == 2

    window.close()
