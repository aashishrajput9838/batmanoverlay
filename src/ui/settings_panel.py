"""Settings Form Panel Widget for batmanoverlay."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.constants import ThemeName
from src.core.config_manager import ConfigManager


class SettingsPanel(QWidget):
    """Settings Panel form interface."""

    def __init__(self, config_manager: ConfigManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsPanel")
        self._config_manager = config_manager

        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Title Header
        header_label = QLabel("<h2>Application Settings</h2>", self)
        main_layout.addWidget(header_label)

        # Scroll area for form
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)

        # ── Appearance Group ──
        grp_appearance = QGroupBox("Appearance & Theme", container)
        form_app = QFormLayout(grp_appearance)

        self._combo_theme = QComboBox(grp_appearance)
        self._combo_theme.addItems([ThemeName.DARK, ThemeName.LIGHT, ThemeName.SYSTEM])
        self._combo_theme.currentTextChanged.connect(
            lambda val: self._config_manager.set("appearance.theme", val)
        )
        form_app.addRow("Theme:", self._combo_theme)

        self._spin_font_scale = QDoubleSpinBox(grp_appearance)
        self._spin_font_scale.setRange(0.8, 2.0)
        self._spin_font_scale.setSingleStep(0.1)
        self._spin_font_scale.valueChanged.connect(
            lambda val: self._config_manager.set("appearance.font_scale", val)
        )
        form_app.addRow("Font Scale:", self._spin_font_scale)

        container_layout.addWidget(grp_appearance)

        # ── General Group ──
        grp_general = QGroupBox("General Options", container)
        form_gen = QFormLayout(grp_general)

        self._chk_updates = QCheckBox("Check for updates automatically", grp_general)
        self._chk_updates.toggled.connect(
            lambda checked: self._config_manager.set("general.check_updates", checked)
        )
        form_gen.addRow(self._chk_updates)

        self._chk_restore = QCheckBox("Restore previous session on startup", grp_general)
        self._chk_restore.toggled.connect(
            lambda checked: self._config_manager.set("general.restore_session", checked)
        )
        form_gen.addRow(self._chk_restore)

        container_layout.addWidget(grp_general)

        # ── Typing Group ──
        grp_typing = QGroupBox("Typing Engine Settings", container)
        form_type = QFormLayout(grp_typing)

        self._spin_speed = QSpinBox(grp_typing)
        self._spin_speed.setRange(1, 10)
        self._spin_speed.valueChanged.connect(
            lambda val: self._config_manager.set("typing.default_speed", val)
        )
        form_type.addRow("Default Speed Level (1-10):", self._spin_speed)

        self._spin_pre_delay = QSpinBox(grp_typing)
        self._spin_pre_delay.setRange(1, 10)
        self._spin_pre_delay.valueChanged.connect(
            lambda val: self._config_manager.set("typing.pre_typing_delay", val)
        )
        form_type.addRow("Pre-typing Delay (sec):", self._spin_pre_delay)

        self._chk_jitter = QCheckBox("Enable typing jitter simulation", grp_typing)
        self._chk_jitter.toggled.connect(
            lambda checked: self._config_manager.set("typing.jitter_enabled", checked)
        )
        form_type.addRow(self._chk_jitter)

        container_layout.addWidget(grp_typing)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _load_values(self) -> None:
        """Load current values from ConfigManager into controls."""
        settings = self._config_manager.settings()

        self._combo_theme.setCurrentText(settings.appearance.theme)
        self._spin_font_scale.setValue(settings.appearance.font_scale)

        self._chk_updates.setChecked(settings.general.check_updates)
        self._chk_restore.setChecked(settings.general.restore_session)

        self._spin_speed.setValue(settings.typing.default_speed)
        self._spin_pre_delay.setValue(settings.typing.pre_typing_delay)
        self._chk_jitter.setChecked(settings.typing.jitter_enabled)
