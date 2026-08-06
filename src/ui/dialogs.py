"""Reusable modal dialogs for batmanoverlay."""

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.clipboard import ClipboardItem
from src.ui.icons import IconManager


class ConfirmDialog(QDialog):
    """Generic modal confirmation dialog."""

    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        msg_label = QLabel(message, self)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton("Confirm", self)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)


class ErrorDialog(QDialog):
    """Modal error dialog displaying structured error information and stack trace details."""

    def __init__(
        self,
        title: str,
        error_code: str,
        user_message: str,
        details: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header with icon and error code
        header_layout = QHBoxLayout()
        icon_label = QLabel(self)
        icon_label.setPixmap(IconManager.get_icon("error").pixmap(24, 24))
        header_layout.addWidget(icon_label)

        title_label = QLabel(f"<b>{user_message}</b>", self)
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, stretch=1)
        layout.addLayout(header_layout)

        code_label = QLabel(f"<font color='#F38BA8'>Error Code: {error_code}</font>", self)
        layout.addWidget(code_label)

        if details:
            details_box = QTextEdit(self)
            details_box.setReadOnly(True)
            details_box.setPlainText(details)
            details_box.setFixedHeight(120)
            layout.addWidget(details_box)

        btn_layout = QHBoxLayout()

        if details:
            btn_copy = QPushButton("Copy Details", self)
            btn_copy.clicked.connect(
                lambda: QApplication.clipboard().setText(
                    f"Error Code: {error_code}\nMessage: {user_message}\nDetails:\n{details}"
                )
            )
            btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()
        btn_close = QPushButton("Close", self)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)


class RecoveryDialog(QDialog):
    """Modal dialog presented when a session crash is detected."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Session Recovery")
        self.setFixedWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title_label = QLabel("<b>A previous crash was detected.</b>", self)
        layout.addWidget(title_label)

        msg_label = QLabel(
            "Would you like to restore your previous tabs and session state, "
            "or start with a fresh session?",
            self,
        )
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        btn_layout = QHBoxLayout()
        btn_fresh = QPushButton("Start Fresh", self)
        btn_fresh.clicked.connect(lambda: self.done(0))
        btn_layout.addWidget(btn_fresh)

        btn_restore = QPushButton("Restore Session", self)
        btn_restore.clicked.connect(lambda: self.done(1))
        btn_layout.addWidget(btn_restore)

        layout.addLayout(btn_layout)


class ClipboardClearConfirmDialog(QDialog):
    """Confirmation dialog for clearing clipboard history with pinned items option."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clear Clipboard History")
        self.setFixedWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        msg_label = QLabel(
            "Are you sure you want to clear your clipboard history?\n"
            "This action cannot be undone.",
            self,
        )
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        self.keep_pinned_cb = QCheckBox("Keep pinned items", self)
        self.keep_pinned_cb.setChecked(True)
        layout.addWidget(self.keep_pinned_cb)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_clear = QPushButton("Clear History", self)
        btn_clear.clicked.connect(self.accept)
        btn_layout.addWidget(btn_clear)

        layout.addLayout(btn_layout)

    def keep_pinned(self) -> bool:
        """Return True if keep pinned items checkbox is checked."""
        return self.keep_pinned_cb.isChecked()


class ClipboardPreviewDialog(QDialog):
    """Modal dialog displaying full un-truncated text and metadata for a clipboard item."""

    def __init__(self, item: ClipboardItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clipboard Item Detail")
        self.setMinimumSize(540, 420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Meta summary line
        meta_str = (
            f"Type: <b>{item.content_type.value.upper()}</b> | "
            f"Chars: <b>{item.char_count}</b> | "
            f"Words: <b>{item.word_count}</b> | "
            f"Lines: <b>{item.line_count}</b>"
        )
        meta_label = QLabel(meta_str, self)
        layout.addWidget(meta_label)

        # Text display area
        text_box = QTextEdit(self)
        text_box.setReadOnly(True)
        text_box.setPlainText(item.content)
        layout.addWidget(text_box, stretch=1)

        # Bottom info & action bar
        info_label = QLabel(
            f"<font color='#89B4FA'>Hash: {item.content_hash[:16]}...</font>", self
        )
        layout.addWidget(info_label)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("Copy to Clipboard", self)
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(item.content))
        btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()

        btn_close = QPushButton("Close", self)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)
