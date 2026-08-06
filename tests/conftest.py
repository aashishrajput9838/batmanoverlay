"""Global pytest fixtures for batmanoverlay."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.models.settings import AppSettings


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide QApplication instance for Qt unit tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Provide temporary data directory structure."""
    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "workspaces" / "default").mkdir(parents=True)
    (data_dir / "sessions").mkdir(parents=True)
    (data_dir / "logs").mkdir(parents=True)
    return data_dir


@pytest.fixture
def default_settings() -> AppSettings:
    """Provide default AppSettings instance."""
    return AppSettings()
