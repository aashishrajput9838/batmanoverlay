"""Unit tests for ThemeManager."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.constants import ThemeName
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.core.theme_manager import ThemeManager


@pytest.mark.unit
def test_theme_manager_apply_dark(qapp: QApplication, tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    signals = AppSignals()
    theme_mgr = ThemeManager(qapp, config_mgr, signals)

    theme_mgr.apply_theme(ThemeName.DARK)
    assert theme_mgr.current_theme == ThemeName.DARK


@pytest.mark.unit
def test_theme_manager_apply_light(qapp: QApplication, tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    signals = AppSignals()
    theme_mgr = ThemeManager(qapp, config_mgr, signals)

    theme_mgr.apply_theme(ThemeName.LIGHT)
    assert theme_mgr.current_theme == ThemeName.LIGHT


@pytest.mark.unit
def test_theme_manager_config_reactive(qapp: QApplication, tmp_data_dir: Path) -> None:
    config_mgr = ConfigManager(tmp_data_dir)
    signals = AppSignals()
    theme_mgr = ThemeManager(qapp, config_mgr, signals)

    config_mgr.set("appearance.theme", ThemeName.LIGHT)
    assert theme_mgr.current_theme == ThemeName.LIGHT
