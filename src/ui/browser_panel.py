"""Production Browser Panel UI widget for batmanoverlay."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QKeyEvent
from PySide6.QtWebEngineCore import QWebEnginePage
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
        self.btn_reload.setIcon(IconManager.get_icon("reload"))
        self.btn_reload.setToolTip("Reload (F5)")
        self.btn_reload.setAccessibleName("Reload Page")
        self.btn_reload.setMinimumSize(32, 32)
        self.btn_reload.clicked.connect(self._on_reload_clicked)
        toolbar_layout.addWidget(self.btn_reload)

        # 4. Home Button
        self.btn_home = QToolButton(self)
        self.btn_home.setIcon(IconManager.get_icon("home"))
        self.btn_home.setToolTip("Home")
        self.btn_home.setAccessibleName("Navigate Home")
        self.btn_home.setMinimumSize(32, 32)
        self.btn_home.clicked.connect(self._on_home_clicked)
        toolbar_layout.addWidget(self.btn_home)

        # 5. Security Indicator Badge
        self.lbl_security = QLabel(self)
        self.lbl_security.setPixmap(IconManager.get_icon("shield").pixmap(16, 16))
        self.lbl_security.setToolTip("Security Status: Safe Connection")
        self.lbl_security.setAccessibleName("Security Status Indicator")
        toolbar_layout.addWidget(self.lbl_security)

        # 6. Address Bar (QLineEdit)
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

        # QWebEngineView Web View Container with Persistent QWebEngineProfile
        self.web_view = QWebEngineView(self)
        qt_profile = self.service.get_qt_profile("default")
        self.web_page = QWebEnginePage(qt_profile, self.web_view)
        self.web_view.setPage(self.web_page)
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

    def _on_home_clicked(self) -> None:
        self.navigate("about:blank")

    def _on_url_changed(self, url: QUrl) -> None:
        url_str = url.toString()
        display_url = clean_display_url(url_str)

        if not self.url_input.hasFocus():
            self.url_input.setText(display_url)

        self.btn_back.setEnabled(self.web_view.history().canGoBack())
        self.btn_forward.setEnabled(self.web_view.history().canGoForward())

        # Update Security Indicator Badge
        if display_url.startswith("https://"):
            self.lbl_security.setPixmap(IconManager.get_icon("shield", "#A6E3A1").pixmap(16, 16))
            self.lbl_security.setToolTip("Secure HTTPS Connection")
        else:
            self.lbl_security.setPixmap(IconManager.get_icon("info", "#F9E2AF").pixmap(16, 16))
            self.lbl_security.setToolTip("Non-HTTPS or Local Address")

    def _on_title_changed(self, title: str) -> None:
        display_url = clean_display_url(self.url_input.text())
        self.service.update_navigation_state(display_url, title=title)

    def _on_load_started(self) -> None:
        self._is_loading = True
        self.progress_bar.setValue(10)
        self.progress_bar.show()
        self.btn_reload.setIcon(IconManager.get_icon("stop"))
        self.btn_reload.setToolTip("Stop Loading (Esc)")
        self.btn_reload.setAccessibleName("Stop Loading")

    def _on_load_progress(self, progress: int) -> None:
        self.progress_bar.setValue(progress)

    def _on_load_finished(self, success: bool) -> None:
        self._is_loading = False
        self.progress_bar.hide()
        self.btn_reload.setIcon(IconManager.get_icon("reload"))
        self.btn_reload.setToolTip("Reload (F5)")
        self.btn_reload.setAccessibleName("Reload Page")
        self.btn_back.setEnabled(self.web_view.history().canGoBack())
        self.btn_forward.setEnabled(self.web_view.history().canGoForward())

        display_url = clean_display_url(self.url_input.text())
        if not success and display_url not in ("about:blank", ""):
            self.web_view.setHtml(self._render_error_page(display_url))

    def _render_blank_page(self) -> str:
        return (
            "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>New Tab</title><style>"
            "* { box-sizing: border-box; margin: 0; padding: 0; }"
            "body { background-color: #232d36; color: #e8eaed; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; "
            "height: 100vh; display: flex; flex-direction: column; justify-content: space-between; user-select: none; overflow: hidden; }"
            ".top-bar { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; font-size: 13px; }"
            ".bookmarks-bar { display: flex; align-items: center; gap: 12px; overflow-x: auto; }"
            ".bm-item { display: flex; align-items: center; gap: 6px; color: #bdc1c6; text-decoration: none; font-size: 12px; padding: 4px 8px; border-radius: 12px; transition: background 0.15s, color 0.15s; white-space: nowrap; }"
            ".bm-item:hover { background: rgba(255, 255, 255, 0.1); color: #ffffff; }"
            ".top-right { display: flex; align-items: center; gap: 14px; }"
            ".top-link { color: #e8eaed; text-decoration: none; font-size: 13px; opacity: 0.85; }"
            ".top-link:hover { opacity: 1; text-decoration: underline; }"
            ".profile-avatar { width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #1e88e5, #1565c0); color: #ffffff; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; cursor: pointer; }"
            ".main-content { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: -20px; }"
            ".google-logo { font-size: 76px; font-weight: 500; letter-spacing: -2.5px; margin-bottom: 24px; }"
            ".google-logo .g1 { color: #4285F4; } .google-logo .o1 { color: #EA4335; } .google-logo .o2 { color: #FBBC05; } .google-logo .g2 { color: #4285F4; } .google-logo .l { color: #34A853; } .google-logo .e { color: #EA4335; }"
            ".search-form { width: 100%; max-width: 580px; }"
            ".search-box { display: flex; align-items: center; background: #2b3843; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 24px; padding: 8px 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.25); transition: background 0.2s, box-shadow 0.2s; }"
            ".search-box:hover, .search-box:focus-within { background: #32414e; box-shadow: 0 4px 12px rgba(0,0,0,0.35); border-color: rgba(255, 255, 255, 0.22); }"
            ".search-box svg { fill: #9aa0a6; }"
            ".search-input { flex: 1; background: transparent; border: none; outline: none; color: #e8eaed; font-size: 15px; padding: 4px 10px; }"
            ".search-input::placeholder { color: #9aa0a6; }"
            ".search-actions { display: flex; align-items: center; gap: 8px; }"
            ".ai-mode-btn { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #e8eaed; border-radius: 14px; padding: 4px 10px; font-size: 12px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 4px; }"
            ".ai-mode-btn:hover { background: rgba(255, 255, 255, 0.15); }"
            ".shortcuts-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 16px; margin-top: 28px; max-width: 620px; }"
            ".shortcut-item { display: flex; flex-direction: column; align-items: center; width: 80px; text-decoration: none; color: #e8eaed; padding: 8px 4px; border-radius: 10px; transition: background 0.15s; }"
            ".shortcut-item:hover { background: rgba(255, 255, 255, 0.08); }"
            ".shortcut-icon { width: 48px; height: 48px; border-radius: 50%; background: #2b3843; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); border: 1px solid rgba(255, 255, 255, 0.08); }"
            ".shortcut-label { font-size: 11px; text-align: center; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #bdc1c6; }"
            ".bottom-bar { display: flex; justify-content: flex-end; padding: 16px 20px; }"
            ".customize-btn { background: #2b3843; border: 1px solid rgba(255, 255, 255, 0.15); color: #8ab4f8; padding: 6px 14px; border-radius: 16px; font-size: 12px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px; }"
            ".customize-btn:hover { background: #32414e; }"
            "</style></head><body>"
            "<div class='top-bar'>"
            "<div class='bookmarks-bar'>"
            "<a href='https://mail.google.com' class='bm-item'>✉️ Gmail</a>"
            "<a href='https://www.youtube.com' class='bm-item'>▶️ YouTube</a>"
            "<a href='https://maps.google.com' class='bm-item'>📍 Maps</a>"
            "<a href='https://news.google.com' class='bm-item'>📰 News</a>"
            "<a href='https://translate.google.com' class='bm-item'>🌐 Translate</a>"
            "</div>"
            "<div class='top-right'>"
            "<a href='https://mail.google.com' class='top-link'>Gmail</a>"
            "<a href='https://images.google.com' class='top-link'>Images</a>"
            "<div class='profile-avatar' title='Google Account'>A</div>"
            "</div></div>"
            "<div class='main-content'>"
            "<div class='google-logo'><span class='g1'>G</span><span class='o1'>o</span><span class='o2'>o</span><span class='g2'>g</span><span class='l'>l</span><span class='e'>e</span></div>"
            "<form id='searchForm' class='search-form'>"
            "<div class='search-box'>"
            "<svg width='18' height='18' viewBox='0 0 24 24'><path d='M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z'/></svg>"
            "<input type='text' id='searchInput' class='search-input' placeholder='Ask Google or type a URL...' autofocus />"
            "<div class='search-actions'><div class='ai-mode-btn'>✨ AI Mode</div></div>"
            "</div></form>"
            "<div class='shortcuts-grid'>"
            "<a href='https://web.whatsapp.com' class='shortcut-item'><div class='shortcut-icon' style='background:#25D366;'><svg viewBox='0 0 24 24' width='26' height='26' fill='#fff'><path d='M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.81 9.81 0 0 0 12.04 2z'/></svg></div><div class='shortcut-label'>whatsApp</div></a>"
            "<a href='https://chatgpt.com' class='shortcut-item'><div class='shortcut-icon' style='background:#10a37f;'><svg viewBox='0 0 24 24' width='24' height='24' fill='#fff'><path d='M22.28 9.82a5.98 5.98 0 0 0-.52-4.91 6.04 6.04 0 0 0-6.51-2.9 6.06 6.06 0 0 0-4.63-2.07 6.06 6.06 0 0 0-5.77 4.14 6.05 6.05 0 0 0-4.14 2.92 6.02 6.02 0 0 0 .74 7.1 5.98 5.98 0 0 0 .51 4.91 6.05 6.05 0 0 0 6.52 2.9 6.03 6.03 0 0 0 4.63 2.07 6.06 6.06 0 0 0 5.77-4.15 6.05 6.05 0 0 0 4.14-2.91 6.02 6.02 0 0 0-.74-7.1z'/></svg></div><div class='shortcut-label'>chat GPT3.5</div></a>"
            "<a href='https://www.google.com' class='shortcut-item'><div class='shortcut-icon' style='background:#303134;'><svg viewBox='0 0 24 24' width='24' height='24'><path fill='#4285F4' d='M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z'/><path fill='#34A853' d='M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z'/><path fill='#FBBC05' d='M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z'/><path fill='#EA4335' d='M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z'/></svg></div><div class='shortcut-label'>viola The World...</div></a>"
            "<a href='https://www.wallpaperflare.com' class='shortcut-item'><div class='shortcut-icon' style='background:#2ea44f;'><span style='font-weight:bold; font-size:22px; color:#fff;'>W</span></div><div class='shortcut-label'>wallpaperflare</div></a>"
            "<a href='https://www.onlinegdb.com' class='shortcut-item'><div class='shortcut-icon' style='background:#7c3aed;'><span style='font-size:22px;'>⚡</span></div><div class='shortcut-label'>onlinegdb</div></a>"
            "<a href='https://photos.google.com' class='shortcut-item'><div class='shortcut-icon' style='background:#ea4335;'><span style='font-size:22px;'>🖼️</span></div><div class='shortcut-label'>photos.google</div></a>"
            "<a href='#' id='addShortcutBtn' class='shortcut-item'><div class='shortcut-icon' style='background:#303134;'><span style='font-size:20px; color:#bdc1c6;'>+</span></div><div class='shortcut-label'>Show more</div></a>"
            "</div></div>"
            "<div class='bottom-bar'><div class='customize-btn'>✏️ Customize Chrome</div></div>"
            "<script>"
            "document.getElementById('searchForm').addEventListener('submit', function(e) { e.preventDefault(); var query = document.getElementById('searchInput').value.trim(); if (!query) return; if (/^(https?:\\/\\/)?([a-zA-Z0-9-]+\\.)+[a-zA-Z]{2,}(\\/.*)?$/.test(query)) { if (!query.startsWith('http://') && !query.startsWith('https://')) { query = 'https://' + query; } window.location.href = query; } else { window.location.href = 'https://www.google.com/search?q=' + encodeURIComponent(query); } });"
            "document.getElementById('addShortcutBtn').addEventListener('click', function(e) { e.preventDefault(); var url = prompt('Enter Website URL (e.g. https://github.com):'); if (url) { if (!url.startsWith('http://') && !url.startsWith('https://')) { url = 'https://' + url; } window.location.href = url; } });"
            "</script></body></html>"
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
