"""Custom list item widget representing a clipboard item card."""

from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.clipboard import ClipboardItem, ClipboardItemType
from src.ui.icons import IconManager


def format_relative_time(dt: datetime) -> str:
    """Format datetime into dynamic relative human string."""
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 5:
        return "Just now"
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = seconds // 60
    if minutes == 1:
        return "1 minute ago"
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours == 1:
        return "1 hour ago"
    if hours < 24:
        return f"{hours} hours ago"
    days = diff.days
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return dt.strftime("%b %d, %Y")


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

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"Clipboard item: {item.content[:30]}")

        self._setup_ui()

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self.item.content_type == ClipboardItemType.IMAGE:
            return QSize(hint.width(), max(hint.height(), 220))
        return hint

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # Header Row (Type Icon, Badges, Relative Timestamp)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        # Type Icon
        self.type_icon = QLabel(self)
        if self.item.content_type == ClipboardItemType.CODE:
            icon_name = "code"
        elif self.item.content_type == ClipboardItemType.IMAGE:
            icon_name = "search"
        else:
            icon_name = "clipboard"

        self.type_icon.setPixmap(IconManager.get_icon(icon_name).pixmap(16, 16))
        header_row.addWidget(self.type_icon)

        # Content Type Pill Badge
        badge_color = "#89B4FA"
        if self.item.content_type == ClipboardItemType.CODE:
            badge_color = "#A6E3A1"
        elif self.item.content_type == ClipboardItemType.URL:
            badge_color = "#CBA6F7"
        elif self.item.content_type == ClipboardItemType.IMAGE:
            badge_color = "#FAB387"

        type_str = (
            f"<font color='{badge_color}'><b>{self.item.content_type.value.upper()}</b></font>"
        )
        self.type_badge = QLabel(type_str, self)
        header_row.addWidget(self.type_badge)

        header_row.addStretch()

        # Relative Timestamp Label
        self.time_label = QLabel(format_relative_time(self.item.timestamp), self)
        self.time_label.setStyleSheet("color: #A6ADC8; font-size: 11px;")
        header_row.addWidget(self.time_label)

        main_layout.addLayout(header_row)

        # Snippet text label
        display_text = self.item.content
        if self.item.content_type == ClipboardItemType.IMAGE:
            p = Path(self.item.content)
            display_text = f"📸 Screenshot: {p.name}"

        self.text_label = QLabel(display_text, self)
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumHeight(36)
        self.text_label.setStyleSheet("color: #CDD6F4; font-size: 12px; font-weight: bold;")
        main_layout.addWidget(self.text_label)

        # Image Thumbnail Preview Widget
        if self.item.content_type == ClipboardItemType.IMAGE:
            p = Path(self.item.content)
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    scaled_pix = pix.scaled(
                        280, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                    )
                    self.img_label = QLabel(self)
                    self.img_label.setPixmap(scaled_pix)
                    self.img_label.setStyleSheet(
                        "border: 1px solid #313244; border-radius: 6px; background-color: #11111b; padding: 4px;"
                    )
                    self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    main_layout.addWidget(self.img_label)

        # Meta & Action Controls Row
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)

        # Character/Word Metrics Badge
        if self.item.content_type == ClipboardItemType.IMAGE:
            meta_str = "<font color='#6C7086'>Image / Screenshot File</font>"
        else:
            meta_str = (
                f"<font color='#6C7086'>{self.item.char_count} chars &bull; "
                f"{self.item.word_count} words</font>"
            )
        self.meta_label = QLabel(meta_str, self)
        meta_row.addWidget(self.meta_label)

        meta_row.addStretch()

        # Distinct Action Buttons with High Affordance & Contrast
        # 1. Pin Button
        self.btn_pin = QPushButton(self)
        self.btn_pin.setIcon(IconManager.get_icon("pin"))
        self.btn_pin.setToolTip("Unpin Item" if self.item.is_pinned else "Pin Item")
        self.btn_pin.setAccessibleName("Pin Item" if not self.item.is_pinned else "Unpin Item")
        self.btn_pin.setMinimumSize(32, 32)
        self.btn_pin.setFlat(True)
        if self.item.is_pinned:
            self.btn_pin.setStyleSheet(
                "background-color: rgba(249, 226, 175, 0.2); border-radius: 4px;"
            )
        self.btn_pin.clicked.connect(lambda: self.pin_toggled.emit(self.item.id))
        meta_row.addWidget(self.btn_pin)

        # 2. Favorite Button
        self.btn_fav = QPushButton(self)
        self.btn_fav.setIcon(IconManager.get_icon("star"))
        self.btn_fav.setToolTip("Remove Favorite" if self.item.is_favorite else "Add to Favorites")
        self.btn_fav.setAccessibleName(
            "Add to Favorites" if not self.item.is_favorite else "Remove Favorite"
        )
        self.btn_fav.setMinimumSize(32, 32)
        self.btn_fav.setFlat(True)
        if self.item.is_favorite:
            self.btn_fav.setStyleSheet(
                "background-color: rgba(245, 194, 231, 0.2); border-radius: 4px;"
            )
        self.btn_fav.clicked.connect(lambda: self.favorite_toggled.emit(self.item.id))
        meta_row.addWidget(self.btn_fav)

        # 3. Copy Button
        self.btn_copy = QPushButton(self)
        self.btn_copy.setIcon(IconManager.get_icon("copy"))
        self.btn_copy.setToolTip("Copy Again")
        self.btn_copy.setAccessibleName("Copy Again")
        self.btn_copy.setMinimumSize(32, 32)
        self.btn_copy.setFlat(True)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        meta_row.addWidget(self.btn_copy)

        # 4. Delete Button
        self.btn_delete = QPushButton(self)
        self.btn_delete.setIcon(IconManager.get_icon("delete"))
        self.btn_delete.setToolTip("Delete Item")
        self.btn_delete.setAccessibleName("Delete Item")
        self.btn_delete.setMinimumSize(32, 32)
        self.btn_delete.setFlat(True)
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.item.id))
        meta_row.addWidget(self.btn_delete)

        main_layout.addLayout(meta_row)

    def update_relative_time(self) -> None:
        """Update visible relative timestamp string."""
        self.time_label.setText(format_relative_time(self.item.timestamp))

    def _on_copy_clicked(self) -> None:
        if self.item.content_type == ClipboardItemType.IMAGE:
            p = Path(self.item.content)
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    QApplication.clipboard().setImage(pix.toImage())
                else:
                    QApplication.clipboard().setText(self.item.content)
            else:
                QApplication.clipboard().setText(self.item.content)
        else:
            QApplication.clipboard().setText(self.item.content)
        self.copy_requested.emit(self.item.id)

    def mouseDoubleClickEvent(self, event: object) -> None:
        """Double clicking card opens preview dialog."""
        self.preview_requested.emit(self.item)
        super().mouseDoubleClickEvent(event)  # type: ignore[arg-type]
