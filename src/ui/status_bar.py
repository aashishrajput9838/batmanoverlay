"""Bottom status bar widget for batmanoverlay."""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.constants import STATUS_BAR_HEIGHT
from src.core.events import AppSignals
from src.version import __version__


class StatusBar(QWidget):
    """Bottom status bar displaying messages, memory usage, and version."""

    def __init__(self, signals: AppSignals, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(STATUS_BAR_HEIGHT)
        self._signals = signals

        self._setup_ui()
        self._signals.status_message.connect(self.set_status)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)

        # Status Indicator Dot
        self._dot_label = QLabel("●", self)
        self._dot_label.setStyleSheet("color: #A6E3A1; font-size: 10px;")
        layout.addWidget(self._dot_label)

        # Main Status Message
        self._status_label = QLabel("Ready", self)
        layout.addWidget(self._status_label)

        layout.addStretch()

        # Version Info Label
        self._version_label = QLabel(f"v{__version__}", self)
        self._version_label.setStyleSheet("color: #6C7086;")
        layout.addWidget(self._version_label)

    def set_status(self, message: str) -> None:
        """Set current status message."""
        self._status_label.setText(message)

    def set_indicator_color(self, color_hex: str) -> None:
        """Set status indicator dot color."""
        self._dot_label.setStyleSheet(f"color: {color_hex}; font-size: 10px;")
