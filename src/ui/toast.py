"""Toast notification overlay widget for batmanoverlay."""

from PySide6.QtCore import QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget

from src.constants import NotificationLevel
from src.ui.icons import IconManager


class ToastWidget(QWidget):
    """Individual floating toast notification card."""

    def __init__(self, level: str, message: str, parent: QWidget, duration_ms: int = 5000) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)

        bg_color, border_color, icon_name = self._get_level_style(level)

        self.setStyleSheet(
            f"ToastWidget {{ background-color: {bg_color}; border: 1px solid {border_color}; "
            f"border-radius: 8px; }}"
            f"QLabel {{ color: #CDD6F4; font-size: 12px; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(8)

        # Icon
        icon_label = QLabel(self)
        icon_label.setPixmap(IconManager.get_icon(icon_name).pixmap(18, 18))
        layout.addWidget(icon_label)

        # Text
        msg_label = QLabel(message, self)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # Dismiss Button
        btn_close = QToolButton(self)
        btn_close.setIcon(IconManager.get_icon("close"))
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet(
            "QToolButton { border: none; background: transparent; } "
            "QToolButton:hover { background-color: rgba(255, 255, 255, 0.2); border-radius: 4px; }"
        )
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.setFixedWidth(280)
        self.adjustSize()

        # Timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(duration_ms)

    def _get_level_style(self, level: str) -> tuple[str, str, str]:
        match level.lower():
            case NotificationLevel.WARNING:
                return ("#2E2A1B", "#F9E2AF", "warning")
            case NotificationLevel.ERROR | NotificationLevel.CRITICAL:
                return ("#311B22", "#F38BA8", "error")
            case _:
                return ("#182438", "#89B4FA", "info")


class ToastManager(QObject):
    """Manages floating toast notifications on the main window."""

    def __init__(self, parent_window: QWidget) -> None:
        super().__init__()
        self._parent_window = parent_window
        self._active_toasts: list[ToastWidget] = []

    def show_toast(self, level: str, message: str, duration_ms: int = 5000) -> None:
        """Display a toast notification."""
        toast = ToastWidget(level, message, self._parent_window, duration_ms)
        toast.destroyed.connect(lambda: self._remove_toast(toast))
        self._active_toasts.append(toast)
        self._reposition_toasts()
        toast.show()

    def _remove_toast(self, toast: ToastWidget) -> None:
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
            self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        if not self._parent_window:
            return

        try:
            parent_rect = self._parent_window.rect()
        except Exception:
            return

        margin = 16
        spacing = 8
        current_y = parent_rect.height() - 40

        for toast in reversed(self._active_toasts):
            current_y -= toast.height()
            x = parent_rect.width() - toast.width() - margin
            toast.move(QPoint(x, max(40, current_y)))
            current_y -= spacing
