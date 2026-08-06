"""Central Configuration Manager for batmanoverlay."""

from pathlib import Path
from typing import Any

from loguru import logger
from PySide6.QtCore import QObject, Signal

from src.constants import CONFIG_DIR, SETTINGS_FILE
from src.models.settings import AppSettings
from src.storage.json_store import JsonStore


class ConfigManager(QObject):
    """Manages application settings loading, persistence, and change notification."""

    config_changed = Signal(str, object)  # (key_path, new_value)

    def __init__(self, data_dir: Path) -> None:
        super().__init__()
        self._config_dir = data_dir / CONFIG_DIR
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._settings_path = self._config_dir / SETTINGS_FILE
        self._json_store = JsonStore()
        self._settings = self._load_settings()

    def _load_settings(self) -> AppSettings:
        if not self._settings_path.exists():
            default_settings = AppSettings()
            self._json_store.write_atomic(self._settings_path, default_settings)
            logger.info(f"Created default settings at {self._settings_path}")
            return default_settings

        try:
            raw_data = self._json_store.read(self._settings_path)
            settings = AppSettings.model_validate(raw_data)
            logger.debug(f"Loaded settings from {self._settings_path}")
            return settings
        except Exception as err:
            logger.warning(
                f"Failed to parse settings from {self._settings_path}: {err}. "
                "Regenerating defaults."
            )
            backup_path = self._settings_path.with_suffix(".json.bak")
            if self._settings_path.exists():
                self._settings_path.rename(backup_path)
            default_settings = AppSettings()
            self._json_store.write_atomic(self._settings_path, default_settings)
            return default_settings

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get setting value using dot-notation (e.g. 'general.language')."""
        parts = key_path.split(".")
        curr: Any = self._settings
        for part in parts:
            if hasattr(curr, part):
                curr = getattr(curr, part)
            elif isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return default
        return curr

    def set(self, key_path: str, value: Any) -> None:
        """Set a setting value using dot-notation and emit change signal."""
        parts = key_path.split(".")
        if len(parts) == 2:
            section_name, attr_name = parts
            if hasattr(self._settings, section_name):
                section = getattr(self._settings, section_name)
                if hasattr(section, attr_name):
                    setattr(section, attr_name, value)
                    self._json_store.write_atomic(self._settings_path, self._settings)
                    self.config_changed.emit(key_path, value)
                    logger.debug(f"Updated setting {key_path} = {value}")

    def settings(self) -> AppSettings:
        """Return full AppSettings model."""
        return self._settings
