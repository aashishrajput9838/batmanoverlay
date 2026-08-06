"""Unit tests for Application Shell and main window creation."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.app import BatmanOverlayApp, get_portable_data_dir
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.core.logger import setup_logging
from src.ui.main_window import MainWindow


@pytest.mark.unit
def test_portable_data_dir() -> None:
    data_dir = get_portable_data_dir()
    assert isinstance(data_dir, Path)
    assert data_dir.name == "data"
    assert data_dir.exists()


@pytest.mark.unit
def test_app_boot_and_shutdown() -> None:
    data_dir = get_portable_data_dir()
    existing_app = QApplication.instance()
    if existing_app is None:
        app = BatmanOverlayApp(["batmanoverlay_test"])
        app.boot(debug=True)
        assert app.config_manager is not None
        assert app.main_window is not None
        assert app.splash_screen is not None
        app.shutdown()
    else:
        # Exercise components when QApplication singleton already exists in test runner
        setup_logging(data_dir, debug=True)
        config_mgr = ConfigManager(data_dir)
        signals = AppSignals()
        window = MainWindow(config_mgr, signals, data_dir)
        assert config_mgr.get("general.language") == "en"
        assert window.windowTitle() is not None
        window.close()
