"""Custom list item widget representing a clipboard item card."""

from datetime import UTC, datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.clipboard import ClipboardItem
from src.ui.icons import IconManager


def format_relative_time(dt: datetime) -> str:
    """Format datetime into relative human string (e.g. 'Just now', '5m ago', '2h ago')."""
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return dt.strftime("%b %d, %H:%M")


class ClipboardItemCard(QWidget):
    """Card widget for displaying a single clipboard item with action controls."""

    pin_toggled = Signal(str)
    favorite_toggled = Signal(str)
    copy_requested = Signal(str)
    delete_requested = Signal(str)
    preview_requested = Signal(object)

    def __init__(self, item: ClipboardItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Snippet text label
        self.text_label = QLabel(self.item.content, self)
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumHeight(60)
        main_layout.addWidget(self.text_label)

        # Meta & Actions row
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)

        # Badges
        rel_time = format_relative_time(self.item.timestamp)
        meta_str = (
            f"<font color='#A6ADC8'>{rel_time}</font> &bull; "
            f"<font color='#89B4FA'>{self.item.char_count} chars</font>"
        )
        self.meta_label = QLabel(meta_str, self)
        meta_row.addWidget(self.meta_label)

        meta_row.addStretch()

        # Action Buttons
        self.btn_pin = QPushButton(self)
        self.btn_pin.setIcon(IconManager.get_icon("pin"))
        self.btn_pin.setToolTip("Unpin Item" if self.item.is_pinned else "Pin Item")
        self.btn_pin.setFlat(True)
        self.btn_pin.clicked.connect(lambda: self.pin_toggled.emit(self.item.id))
        meta_row.addWidget(self.btn_pin)

        self.btn_fav = QPushButton(self)
        self.btn_fav.setIcon(IconManager.get_icon("star"))
        self.btn_fav.setToolTip("Remove Favorite" if self.item.is_favorite else "Add to Favorites")
        self.btn_fav.setFlat(True)
        self.btn_fav.clicked.connect(lambda: self.favorite_toggled.emit(self.item.id))
        meta_row.addWidget(self.btn_fav)

        self.btn_copy = QPushButton(self)
        self.btn_copy.setIcon(IconManager.get_icon("copy"))
        self.btn_copy.setToolTip("Copy to Clipboard")
        self.btn_copy.setFlat(True)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        meta_row.addWidget(self.btn_copy)

        self.btn_delete = QPushButton(self)
        self.btn_delete.setIcon(IconManager.get_icon("delete"))
        self.btn_delete.setToolTip("Delete Item")
        self.btn_delete.setFlat(True)
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.item.id))
        meta_row.addWidget(self.btn_delete)

        main_layout.addLayout(meta_row)

    def _on_copy_clicked(self) -> None:
        QApplication.clipboard().setText(self.item.content)
        self.copy_requested.emit(self.item.id)

    def mouseDoubleClickEvent(self, event: object) -> None:
        """Double clicking card opens preview dialog."""
        self.preview_requested.emit(self.item)
        super().mouseDoubleClickEvent(event)  # type: ignore[arg-type]
