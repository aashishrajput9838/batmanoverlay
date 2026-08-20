from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QScreen, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.clipboard import ClipboardItem
from src.platform.models import TargetInfo
from src.platform.security import apply_display_affinity_to_hwnd
from src.ui.icons import IconManager


class SecureDialog(QDialog):
    """Base modal dialog enforcing display capture exclusion (WDA_EXCLUDEFROMCAPTURE = 0x11) on Windows."""

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        if hwnd:
            apply_display_affinity_to_hwnd(hwnd, True)


class ConfirmDialog(SecureDialog):
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


class ErrorDialog(SecureDialog):
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


class ClearHistoryDialog(SecureDialog):
    """Confirmation modal for clearing clipboard repository history."""

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


ClipboardClearConfirmDialog = ClearHistoryDialog


class RecoveryDialog(SecureDialog):
    """Modal dialog for session recovery options."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Session Recovery")
        self.setFixedWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        msg_label = QLabel(
            "An unexpected shutdown was detected. "
            "Would you like to recover your previous session?",
            self,
        )
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_discard = QPushButton("Discard", self)
        btn_discard.clicked.connect(self.reject)
        btn_layout.addWidget(btn_discard)

        btn_recover = QPushButton("Recover Session", self)
        btn_recover.setDefault(True)
        btn_recover.clicked.connect(self.accept)
        btn_layout.addWidget(btn_recover)

        layout.addLayout(btn_layout)


class ClipboardPreviewDialog(SecureDialog):
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


class TargetPreviewDialog(SecureDialog):
    """Modal target acquisition preview dialog displayed before typing starts."""

    def __init__(
        self,
        target_info: TargetInfo,
        char_count: int,
        est_seconds: float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Typing Target Preview")
        self.setFixedWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_label = QLabel("<h3>Target Acquisition Preview</h3>", self)
        layout.addWidget(title_label)

        form_group = QGroupBox("Target Window & Control Details", self)
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        form_layout.addRow("Target Window:", QLabel(f"<b>{target_info.window_title}</b>", self))
        form_layout.addRow(
            "Target Process:", QLabel(f"<code>{target_info.process_name}</code>", self)
        )
        form_layout.addRow(
            "Target Control:", QLabel(f"<code>{target_info.control_type}</code>", self)
        )
        form_layout.addRow("Character Count:", QLabel(f"<b>{char_count:,} characters</b>", self))

        mins = int(est_seconds // 60)
        secs = int(est_seconds % 60)
        dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        form_layout.addRow("Estimated Duration:", QLabel(f"<b>{dur_str}</b>", self))

        layout.addWidget(form_group)

        self.dont_show_cb = QCheckBox("Do not show preview confirmation dialog again", self)
        layout.addWidget(self.dont_show_cb)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_start = QPushButton("Start Typing", self)
        btn_start.setDefault(True)
        btn_start.clicked.connect(self.accept)
        btn_layout.addWidget(btn_start)

        layout.addLayout(btn_layout)

    def dont_show_again(self) -> bool:
        """Return True if user requested disabling preview mode."""
        return self.dont_show_cb.isChecked()


class ScreenSelectionDialog(SecureDialog):
    """Modal dialog asking user which screen/monitor (or full desktop) to capture."""

    def __init__(
        self,
        screens: list[QScreen],
        primary_screen: QScreen | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Screen to Capture")
        self.setMinimumWidth(480)
        self.setModal(True)

        self._screens = screens
        self._primary_screen = primary_screen or (screens[0] if screens else None)
        self._selected_index: int | None = 0
        self._radio_buttons: list[QRadioButton] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_icon = QLabel(self)
        header_icon.setPixmap(IconManager.get_icon("screenshot").pixmap(28, 28))
        header_layout.addWidget(header_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_label = QLabel("<b>Select Target Display to Capture</b>", self)
        title_label.setStyleSheet("font-size: 14px; color: #CDD6F4;")
        desc_label = QLabel(
            f"Detected {len(self._screens)} monitors. "
            "Select display to capture or press number key.",
            self,
        )
        desc_label.setStyleSheet("font-size: 11px; color: #A6ADC8;")
        desc_label.setWordWrap(True)
        title_box.addWidget(title_label)
        title_box.addWidget(desc_label)

        header_layout.addLayout(title_box, stretch=1)
        layout.addLayout(header_layout)

        options_group = QGroupBox("Available Displays", self)
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setSpacing(10)

        self._button_group = QButtonGroup(self)

        for idx, s in enumerate(self._screens):
            geo = s.geometry()
            is_prim = (self._primary_screen is not None) and (
                s == self._primary_screen or s.name() == self._primary_screen.name()
            )
            prim_tag = " ★ Primary" if is_prim else ""
            shortcut_hint = f" [Press {idx + 1}]"
            label_text = (
                f"Display {idx + 1}: {geo.width()}x{geo.height()} "
                f"({s.name()}){prim_tag}{shortcut_hint}"
            )

            rb = QRadioButton(label_text, self)
            rb.setStyleSheet("font-weight: bold; color: #CDD6F4;")
            if idx == 0:
                rb.setChecked(True)

            options_layout.addWidget(rb)
            self._button_group.addButton(rb, idx)
            self._radio_buttons.append(rb)

        if self._screens:
            min_x = min(s.geometry().x() for s in self._screens)
            min_y = min(s.geometry().y() for s in self._screens)
            max_x = max(s.geometry().x() + s.geometry().width() for s in self._screens)
            max_y = max(s.geometry().y() + s.geometry().height() for s in self._screens)
            virt_w = max_x - min_x
            virt_h = max_y - min_y

            all_label = f"All Displays (Full Desktop): {virt_w}x{virt_h} [Press A or 0]"
            rb_all = QRadioButton(all_label, self)
            rb_all.setStyleSheet("font-weight: bold; color: #89B4FA;")
            options_layout.addWidget(rb_all)
            self._button_group.addButton(rb_all, -1)

        layout.addWidget(options_group)

        self.remember_cb = QCheckBox("Remember choice for future screenshots", self)
        self.remember_cb.setStyleSheet("color: #BAC2DE; font-size: 11px;")
        layout.addWidget(self.remember_cb)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_capture = QPushButton("Capture Selected", self)
        btn_capture.setDefault(True)
        btn_capture.clicked.connect(self._on_capture_clicked)
        btn_layout.addWidget(btn_capture)

        layout.addLayout(btn_layout)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Allow number keys (1..9) or 'A' / '0' to fast-select screen."""
        key = event.key()
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            idx = key - Qt.Key.Key_1
            if 0 <= idx < len(self._screens):
                btn = self._button_group.button(idx)
                if btn:
                    btn.setChecked(True)
                    self._on_capture_clicked()
                    return
        elif key in (Qt.Key.Key_0, Qt.Key.Key_A):
            btn_all = self._button_group.button(-1)
            if btn_all:
                btn_all.setChecked(True)
                self._on_capture_clicked()
                return
        super().keyPressEvent(event)

    def _on_capture_clicked(self) -> None:
        checked_id = self._button_group.checkedId()
        self._selected_index = checked_id if checked_id != -2 else 0
        self.accept()

    def get_selected_screen_index(self) -> int | None:
        """Return screen index (0..N-1), -1 for All Displays, or None if cancelled."""
        if self.result() == QDialog.DialogCode.Accepted:
            return self._selected_index
        return None

    def get_remember_choice(self) -> bool:
        """Return True if user checked remember choice checkbox."""
        return self.remember_cb.isChecked() if self.remember_cb else False
