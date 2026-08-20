import hashlib
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


class ClipboardMonitor(QObject):
    """Monitors system QClipboard change events and emits captured text & images."""

    text_captured = Signal(str)  # raw text content
    image_captured = Signal(str)  # image file path

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._last_captured_text: str = ""
        self._last_captured_image_hash: str = ""

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

        # Check for Image content first
        mime = clipboard.mimeData()
        if mime and mime.hasImage():
            img = clipboard.image()
            if not img.isNull():
                try:
                    bits = img.constBits()
                    if bits:
                        img_hash = hashlib.md5(bytes(bits)).hexdigest()
                        if img_hash != self._last_captured_image_hash:
                            self._last_captured_image_hash = img_hash
                            save_dir = Path("data/screenshots")
                            save_dir.mkdir(parents=True, exist_ok=True)
                            file_path = save_dir / f"system_clip_{img_hash[:8]}.png"
                            if not file_path.exists():
                                img.save(str(file_path), "PNG")
                            logger.debug(f"Captured new system clipboard image: {file_path}")
                            self.image_captured.emit(str(file_path.resolve()))
                            return
                except Exception as e:
                    logger.warning(f"Error capturing system clipboard image: {e}")

        # Check for Text content
        text = clipboard.text()
        if not text or text == self._last_captured_text:
            return

        self._last_captured_text = text
        logger.debug(f"Captured new clipboard text length={len(text)}")
        self.text_captured.emit(text)
