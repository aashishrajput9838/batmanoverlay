"""Reusable EmptyStateWidget for batmanoverlay presentation layer."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.icons import IconManager


class EmptyStateWidget(QWidget):
    """Centered empty state placeholder with icon, headline, description, and action button."""

    def __init__(
        self,
        icon_name: str,
        title: str,
        description: str,
        hint: str | None = None,
        action_text: str | None = None,
        action_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._title = title
        self._description = description
        self._hint = hint
        self._action_text = action_text
        self._action_callback = action_callback

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon Label
        icon_label = QLabel(self)
        icon_label.setPixmap(IconManager.get_icon(self._icon_name).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title Label
        title_label = QLabel(f"<h3>{self._title}</h3>", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #CDD6F4; font-weight: bold;")
        layout.addWidget(title_label)

        # Description Label
        desc_label = QLabel(self._description, self)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #A6ADC8; font-size: 13px;")
        layout.addWidget(desc_label)

        # Optional Hint Label
        if self._hint:
            hint_label = QLabel(f"<font color='#6C7086'><i>{self._hint}</i></font>", self)
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint_label)

        # Optional Action Button
        if self._action_text and self._action_callback:
            btn_action = QPushButton(self._action_text, self)
            btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_action.clicked.connect(self._action_callback)
            layout.addWidget(btn_action, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_content(self, title: str, description: str, hint: str | None = None) -> None:
        """Dynamically update empty state text."""
        self._title = title
        self._description = description
        self._hint = hint
        # Re-setup UI
        lay = self.layout()
        if lay is not None:
            while lay.count():
                child = lay.takeAt(0)
                if child is not None:
                    widget = child.widget()
                    if widget is not None:
                        widget.deleteLater()
        self._setup_ui()
