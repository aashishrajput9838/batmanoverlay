"""Clipboard Monitor listener component for batmanoverlay."""

from loguru import logger
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


class ClipboardMonitor(QObject):
    """Monitors system QClipboard change events and emits captured text."""

    text_captured = Signal(str)  # raw text content

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._last_captured_text: str = ""

        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            clipboard = app.clipboard()
            clipboard.dataChanged.connect(self._on_data_changed)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        """Enable system clipboard monitoring."""
        self._enabled = True
        logger.info("Clipboard monitoring enabled.")

    def disable(self) -> None:
        """Disable system clipboard monitoring."""
        self._enabled = False
        logger.info("Clipboard monitoring disabled.")

    def _on_data_changed(self) -> None:
        """Callback invoked when system clipboard content changes."""
        if not self._enabled:
            return

        app = QApplication.instance()
        if not app or not isinstance(app, QApplication):
            return

        clipboard = app.clipboard()
        text = clipboard.text()

        if not text or text == self._last_captured_text:
            return

        self._last_captured_text = text
        logger.debug(f"Captured new clipboard text length={len(text)}")
        self.text_captured.emit(text)
