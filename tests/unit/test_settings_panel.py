"""Unit tests for minimal SettingsPanel."""

from pathlib import Path

import pytest

from src.core.config_manager import ConfigManager
from src.ui.overlay_visibility_panel import OverlayVisibilityPanel
from src.ui.settings_panel import SettingsPanel


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_settings_panel_minimal_layout_and_binding(tmp_data_dir: Path) -> None:
    """Verify SettingsPanel renders minimal layout with OverlayVisibilityPanel."""
    config_mgr = ConfigManager(tmp_data_dir)
    panel = SettingsPanel(config_mgr)

    # Removed section widgets must not exist on SettingsPanel
    assert not hasattr(panel, "_combo_theme")
    assert not hasattr(panel, "_spin_font_scale")
    assert not hasattr(panel, "_chk_updates")
    assert not hasattr(panel, "_chk_restore")
    assert not hasattr(panel, "_spin_speed")
    assert not hasattr(panel, "_spin_pre_delay")
    assert not hasattr(panel, "_chk_jitter")

    # Embedded OverlayVisibilityPanel must exist and function
    assert hasattr(panel, "overlay_visibility_panel")
    assert isinstance(panel.overlay_visibility_panel, OverlayVisibilityPanel)

    panel.overlay_visibility_panel.set_transparency(50.0)
    panel.overlay_visibility_panel.transparency_changed.emit(50.0)
    assert config_mgr.get("appearance.overlay_transparency") == 50.0


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_settings_panel_legacy_config_backward_compatibility(tmp_data_dir: Path) -> None:
    """Verify legacy settings file with obsolete fields loads cleanly without error."""
    config_mgr = ConfigManager(tmp_data_dir)
    config_mgr.set("appearance.theme", "dark")
    config_mgr.set("appearance.font_scale", 1.2)
    config_mgr.set("general.check_updates", False)
    config_mgr.set("general.restore_session", True)
    config_mgr.set("typing.default_speed", 8)
    config_mgr.set("typing.pre_typing_delay", 5)
    config_mgr.set("typing.jitter_enabled", False)
    config_mgr.set("appearance.overlay_transparency", 75.0)

    panel = SettingsPanel(config_mgr)
    assert panel.overlay_visibility_panel.get_transparency() == 75.0
