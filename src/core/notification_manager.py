"""Central Notification Routing Service for batmanoverlay."""

from PySide6.QtCore import QObject

from src.core.events import AppSignals


class NotificationManager(QObject):
    """Routes application events to UI toasts and status messages."""

    def __init__(self, signals: AppSignals) -> None:
        super().__init__()
        self._signals = signals

    def notify_info(self, message: str) -> None:
        """Post an informative toast and status bar message."""
        self._signals.status_message.emit(message)
        self._signals.toast_requested.emit("info", message)

    def notify_warning(self, message: str) -> None:
        """Post a warning toast and status bar message."""
        self._signals.status_message.emit(f"Warning: {message}")
        self._signals.toast_requested.emit("warning", message)

    def notify_error(self, message: str) -> None:
        """Post an error toast and status bar message."""
        self._signals.status_message.emit(f"Error: {message}")
        self._signals.toast_requested.emit("error", message)
