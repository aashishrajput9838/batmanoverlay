"""Minimal Settings Form Panel Widget for batmanoverlay."""

from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import ConfigManager
from src.ui.overlay_visibility_panel import OverlayVisibilityPanel


class SettingsPanel(QWidget):
    """Minimal Settings Panel form interface featuring Overlay Visibility control."""

    def __init__(self, config_manager: ConfigManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsPanel")
        self._config_manager = config_manager

        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Title Header
        header_label = QLabel("<h2>Application Settings</h2>", self)
        header_label.setStyleSheet("color: #CDD6F4; margin-bottom: 2px;")
        main_layout.addWidget(header_label)

        sub_label = QLabel(
            "Manage BatmanOverlay application preferences and window transparency controls.", self
        )
        sub_label.setStyleSheet("color: #A6ADC8; font-size: 12px; margin-bottom: 8px;")
        main_layout.addWidget(sub_label)

        # Scroll area for form
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        # Embedded Overlay Visibility Panel
        self.overlay_visibility_panel = OverlayVisibilityPanel(container)
        self.overlay_visibility_panel.transparency_changed.connect(self._on_transparency_changed)
        container_layout.addWidget(self.overlay_visibility_panel)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

    def _on_transparency_changed(self, value: float) -> None:
        """Handle transparency changes from the panel."""
        self._config_manager.set("appearance.overlay_transparency", value)

    def _load_values(self) -> None:
        """Load current values from ConfigManager into controls."""
        settings = self._config_manager.settings()
        self.overlay_visibility_panel.set_transparency(settings.appearance.overlay_transparency)
