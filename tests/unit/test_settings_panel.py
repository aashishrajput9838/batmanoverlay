"""Unit tests for SettingsPanel."""

from pathlib import Path

import pytest

from src.core.config_manager import ConfigManager
from src.ui.settings_panel import SettingsPanel


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_settings_panel_binding(tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    panel = SettingsPanel(config_mgr)

    assert panel._combo_theme.currentText() == "system"
    assert panel._spin_speed.value() == 5

    panel._spin_speed.setValue(9)
    assert config_mgr.get("typing.default_speed") == 9
