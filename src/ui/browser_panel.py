"""Production Browser Panel UI widget for batmanoverlay."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QKeyEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.browser.protocols import IBrowserService
from src.core.events import AppSignals
from src.ui.icons import IconManager


def clean_display_url(url_str: str) -> str:
    """Sanitize raw URL for user-facing address bar display, hiding internal data/srcdoc URLs."""
    cleaned = url_str.strip()
    if not cleaned or cleaned.startswith(("data:", "about:srcdoc", "chrome:", "javascript:")):
        return "about:blank"
    return cleaned


class BrowserPanel(QWidget):
    """Single-tab web browser panel with navigation toolbar and SSL security status."""

    def __init__(
        self,
        browser_service: IBrowserService,
        signals: AppSignals,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = browser_service
        self.signals = signals

        self._is_loading = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Navigation Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        # 1. Back Button
        self.btn_back = QToolButton(self)
        self.btn_back.setIcon(IconManager.get_icon("chevron_left"))
        self.btn_back.setToolTip("Back (Alt+Left)")
        self.btn_back.setAccessibleName("Navigate Back")
        self.btn_back.setMinimumSize(32, 32)
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._on_back_clicked)
        toolbar_layout.addWidget(self.btn_back)

        # 2. Forward Button
        self.btn_forward = QToolButton(self)
        self.btn_forward.setIcon(IconManager.get_icon("chevron_right"))
        self.btn_forward.setToolTip("Forward (Alt+Right)")
        self.btn_forward.setAccessibleName("Navigate Forward")
        self.btn_forward.setMinimumSize(32, 32)
        self.btn_forward.setEnabled(False)
        self.btn_forward.clicked.connect(self._on_forward_clicked)
        toolbar_layout.addWidget(self.btn_forward)

        # 3. Reload / Stop Button
        self.btn_reload = QToolButton(self)
        self.btn_reload.setIcon(IconManager.get_icon("settings"))
        self.btn_reload.setToolTip("Reload (F5)")
        self.btn_reload.setAccessibleName("Reload Page")
        self.btn_reload.setMinimumSize(32, 32)
        self.btn_reload.clicked.connect(self._on_reload_clicked)
        toolbar_layout.addWidget(self.btn_reload)

        # 4. Security Indicator Badge
        self.lbl_security = QLabel(self)
        self.lbl_security.setPixmap(IconManager.get_icon("shield").pixmap(16, 16))
        self.lbl_security.setToolTip("Security Status: Safe Connection")
        self.lbl_security.setAccessibleName("Security Status Indicator")
        toolbar_layout.addWidget(self.lbl_security)

        # 5. Address Bar (QLineEdit)
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Search or enter web address (Ctrl+L)...")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.setAccessibleName("Address Bar")
        self.url_input.returnPressed.connect(self._on_navigate_requested)
        toolbar_layout.addWidget(self.url_input, stretch=1)

        main_layout.addLayout(toolbar_layout)

        # Loading Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: transparent; border: none; } "
            "QProgressBar::chunk { background-color: #89B4FA; border-radius: 1px; }"
        )
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # QWebEngineView Web View Container
        self.web_view = QWebEngineView(self)
        self.web_view.setAccessibleName("Web Page Content View")
        main_layout.addWidget(self.web_view, stretch=1)

        # Load default starting page
        self.navigate("about:blank")

    def _connect_signals(self) -> None:
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.titleChanged.connect(self._on_title_changed)
        self.web_view.loadStarted.connect(self._on_load_started)
        self.web_view.loadProgress.connect(self._on_load_progress)
        self.web_view.loadFinished.connect(self._on_load_finished)

    def navigate(self, raw_url: str) -> None:
        """Normalize URL via BrowserService and navigate QWebEngineView."""
        normalized_url = self.service.normalize_url(raw_url)
        display_url = clean_display_url(normalized_url)
        self.url_input.setText(display_url)
        if normalized_url == "about:blank":
            self.web_view.setHtml(self._render_blank_page())
        else:
            self.web_view.setUrl(QUrl(normalized_url))

    def _on_navigate_requested(self) -> None:
        raw_text = self.url_input.text().strip()
        if raw_text:
            self.navigate(raw_text)

    def _on_back_clicked(self) -> None:
        if self.web_view.history().canGoBack():
            self.web_view.back()

    def _on_forward_clicked(self) -> None:
        if self.web_view.history().canGoForward():
            self.web_view.forward()

    def _on_reload_clicked(self) -> None:
        if self._is_loading:
            self.web_view.stop()
        else:
            self.web_view.reload()

    def _on_url_changed(self, url: QUrl) -> None:
        url_str = url.toString()
        display_url = clean_display_url(url_str)

        if not self.url_input.hasFocus():
            self.url_input.setText(display_url)

        self.btn_back.setEnabled(self.web_view.history().canGoBack())
        self.btn_forward.setEnabled(self.web_view.history().canGoForward())

        # Update Security Indicator Badge
        if display_url.startswith("https://"):
            self.lbl_security.setPixmap(IconManager.get_icon("shield").pixmap(16, 16))
            self.lbl_security.setToolTip("Secure HTTPS Connection")
        else:
            self.lbl_security.setPixmap(IconManager.get_icon("info").pixmap(16, 16))
            self.lbl_security.setToolTip("Non-HTTPS or Local Address")

    def _on_title_changed(self, title: str) -> None:
        display_url = clean_display_url(self.url_input.text())
        self.service.update_navigation_state(display_url, title=title)

    def _on_load_started(self) -> None:
        self._is_loading = True
        self.progress_bar.setValue(10)
        self.progress_bar.show()
        self.btn_reload.setToolTip("Stop Loading (Esc)")

    def _on_load_progress(self, progress: int) -> None:
        self.progress_bar.setValue(progress)

    def _on_load_finished(self, success: bool) -> None:
        self._is_loading = False
        self.progress_bar.hide()
        self.btn_reload.setToolTip("Reload (F5)")
        self.btn_back.setEnabled(self.web_view.history().canGoBack())
        self.btn_forward.setEnabled(self.web_view.history().canGoForward())

        display_url = clean_display_url(self.url_input.text())
        if not success and display_url not in ("about:blank", ""):
            self.web_view.setHtml(self._render_error_page(display_url))

    def _render_blank_page(self) -> str:
        return (
            "<!DOCTYPE html><html><head><style>"
            "body { background-color: #1E1E2E; color: #CDD6F4; font-family: sans-serif; "
            "display: flex; flex-direction: column; align-items: center; justify-content: center; "
            "height: 90vh; margin: 0; }"
            "h2 { color: #89B4FA; margin-bottom: 8px; }"
            "p { color: #A6ADC8; font-size: 14px; }"
            "</style></head><body>"
            "<h2>batmanoverlay Browser Engine</h2>"
            "<p>Enter a URL or search query in the address bar above (Ctrl+L).</p>"
            "</body></html>"
        )

    def _render_error_page(self, failed_url: str) -> str:
        return (
            f"<!DOCTYPE html><html><head><style>"
            f"body {{ background-color: #1E1E2E; color: #CDD6F4; font-family: sans-serif; "
            f"display: flex; flex-direction: column; align-items: center; "
            f"justify-content: center; height: 90vh; margin: 0; }}"
            f".card {{ background: #181825; border: 1px solid #313244; padding: 32px; "
            f"border-radius: 12px; text-align: center; max-width: 480px; }}"
            f"h2 {{ color: #F38BA8; margin-top: 0; }}"
            f"p {{ color: #A6ADC8; font-size: 13px; margin-bottom: 20px; word-break: break-all; }}"
            f"</style></head><body><div class='card'>"
            f"<h2>Unable to Load Web Page</h2>"
            f"<p>Could not connect to <b>{failed_url}</b>. Check network or URL spelling.</p>"
            f"</div></body></html>"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle browser panel keyboard navigation shortcuts."""
        if event.key() == Qt.Key.Key_L and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.url_input.setFocus()
            self.url_input.selectAll()
            event.accept()
            return

        if event.key() in (Qt.Key.Key_F5, Qt.Key.Key_R) and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier or event.key() == Qt.Key.Key_F5
        ):
            self._on_reload_clicked()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Left and (
            event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            self._on_back_clicked()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Right and (
            event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            self._on_forward_clicked()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Escape and self._is_loading:
            self.web_view.stop()
            event.accept()
            return

        super().keyPressEvent(event)
