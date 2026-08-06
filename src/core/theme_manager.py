"""Theme management subsystem for loading and applying QSS stylesheets."""

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from src.constants import ThemeName
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals


class ThemeManager(QObject):
    """Manages application stylesheets, accent colors, and dark/light mode switching."""

    def __init__(
        self,
        app: QApplication,
        config_manager: ConfigManager,
        signals: AppSignals,
        resources_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self._app = app
        self._config_manager = config_manager
        self._signals = signals

        if resources_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            self._resources_dir = base_dir / "resources"
        else:
            self._resources_dir = resources_dir

        self._themes_dir = self._resources_dir / "themes"
        self._current_theme: str = "system"

        # Listen to config changes
        self._config_manager.config_changed.connect(self._on_config_changed)

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def apply_theme(self, theme_name: str | None = None) -> None:
        """Apply the specified theme ('dark', 'light', or 'system')."""
        if theme_name is None:
            theme_name = str(self._config_manager.get("appearance.theme", "system"))

        target_theme = theme_name.lower()
        if target_theme == ThemeName.SYSTEM:
            target_theme = self._detect_system_theme()

        qss_filename = "dark.qss" if target_theme == ThemeName.DARK else "light.qss"
        qss_path = self._themes_dir / qss_filename

        if not qss_path.exists():
            logger.warning(f"Theme file {qss_path} not found. Applying fallback dark theme.")
            qss_content = self._get_fallback_dark_qss()
        else:
            qss_content = qss_path.read_text(encoding="utf-8")

        self._app.setStyleSheet(qss_content)
        self._current_theme = target_theme
        self._signals.theme_changed.emit(target_theme)
        logger.info(f"Applied theme: {target_theme}")

    def _detect_system_theme(self) -> str:
        """Detect system palette preference."""
        palette = self._app.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        # Darkness check
        if bg_color.lightness() < 128:
            return ThemeName.DARK
        return ThemeName.LIGHT

    def _on_config_changed(self, key_path: str, new_value: object) -> None:
        if key_path == "appearance.theme" and isinstance(new_value, str):
            self.apply_theme(new_value)

    def _get_fallback_dark_qss(self) -> str:
        return """
        QMainWindow { background-color: #1E1E2E; color: #CDD6F4; }
        QWidget { color: #CDD6F4; }
        """
