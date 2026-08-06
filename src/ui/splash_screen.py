"""Base application splash screen."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSplashScreen

from src.constants import APP_DISPLAY_NAME
from src.version import __version__


class SplashScreen(QSplashScreen):
    """Initial splash screen displayed during application startup."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(400, 250)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)

    def paintEvent(self, _event: object) -> None:
        """Render splash screen content."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#1E1E2E"))

        # Title
        painter.setPen(QColor("#5B8DEF"))
        painter.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        painter.drawText(20, 80, APP_DISPLAY_NAME)

        # Subtitle / Version
        painter.setPen(QColor("#A6ADC8"))
        painter.setFont(QFont("Inter", 10))
        painter.drawText(20, 110, f"Version {__version__}")

        # Loading Indicator Text
        painter.drawText(20, 200, "Initializing engineering foundation...")
