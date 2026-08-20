"""UI unit tests for BrowserPanel component."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QUrl

from src.browser.profile_manager import BrowserProfileManager
from src.browser.service import BrowserService
from src.browser.session_manager import BrowserSessionManager
from src.core.events import AppSignals
from src.ui.browser_panel import BrowserPanel, clean_display_url


@pytest.fixture
def browser_service(tmp_path: Path) -> BrowserService:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)
    return BrowserService(profile_mgr, session_mgr)


@pytest.mark.ui
def test_clean_display_url_sanitization() -> None:
    assert clean_display_url("") == "about:blank"
    assert clean_display_url("data:text/html,<h1>Test</h1>") == "about:blank"
    assert clean_display_url("about:srcdoc") == "about:blank"
    assert clean_display_url("chrome://settings") == "about:blank"
    assert clean_display_url("javascript:alert(1)") == "about:blank"
    assert clean_display_url("https://github.com") == "https://github.com"
    assert clean_display_url("http://localhost:8000") == "http://localhost:8000"


@pytest.mark.ui
def test_browser_panel_instantiation_and_navigation(
    qtbot: pytest.PyTest, browser_service: BrowserService
) -> None:
    signals = AppSignals()
    panel = BrowserPanel(browser_service, signals)
    qtbot.addWidget(panel)
    panel.show()

    assert panel.url_input.text() == "about:blank"
    assert panel.btn_back.isEnabled() is False
    assert panel.btn_forward.isEnabled() is False

    # Test navigate call
    panel.navigate("example.com")
    assert panel.url_input.text() == "https://example.com"

    # Simulate internal data URL signal emission
    panel._on_url_changed(QUrl("data:text/html;charset=utf-8,<h2>Internal</h2>"))
    assert panel.url_input.text() == "about:blank"


@pytest.mark.ui
def test_browser_panel_toolbar_icon_rendering(
    qtbot: pytest.PyTest, browser_service: BrowserService
) -> None:
    """Hotfix-003 Verification: Ensure every browser toolbar button has non-null QIcon,

    proper accessibility attributes, minimum sizes, and dynamic reload/stop icon switching.
    """
    signals = AppSignals()
    panel = BrowserPanel(browser_service, signals)
    qtbot.addWidget(panel)
    panel.show()

    # 1. Back button
    assert panel.btn_back.icon().isNull() is False
    assert panel.btn_back.accessibleName() == "Navigate Back"
    assert "Back" in panel.btn_back.toolTip()
    assert panel.btn_back.minimumWidth() >= 32
    assert panel.btn_back.minimumHeight() >= 32

    # 2. Forward button
    assert panel.btn_forward.icon().isNull() is False
    assert panel.btn_forward.accessibleName() == "Navigate Forward"
    assert "Forward" in panel.btn_forward.toolTip()
    assert panel.btn_forward.minimumWidth() >= 32
    assert panel.btn_forward.minimumHeight() >= 32

    # 3. Reload button
    assert panel.btn_reload.icon().isNull() is False
    assert panel.btn_reload.accessibleName() == "Reload Page"
    assert "Reload" in panel.btn_reload.toolTip()
    assert panel.btn_reload.minimumWidth() >= 32
    assert panel.btn_reload.minimumHeight() >= 32

    # 4. Home button
    assert panel.btn_home.icon().isNull() is False
    assert panel.btn_home.accessibleName() == "Navigate Home"
    assert "Home" in panel.btn_home.toolTip()

    # 5. Security Indicator
    assert panel.lbl_security.pixmap() is not None
    assert panel.lbl_security.pixmap().isNull() is False
    assert panel.lbl_security.accessibleName() == "Security Status Indicator"

    # Test load state transition: reload -> stop
    panel._on_load_started()
    assert panel.btn_reload.icon().isNull() is False
    assert panel.btn_reload.accessibleName() == "Stop Loading"
    assert "Stop" in panel.btn_reload.toolTip()

    # Test load finished transition: stop -> reload
    panel._on_load_finished(True)
    assert panel.btn_reload.icon().isNull() is False
    assert panel.btn_reload.accessibleName() == "Reload Page"
    assert "Reload" in panel.btn_reload.toolTip()


@pytest.mark.ui
def test_browser_panel_keyboard_shortcuts(
    qtbot: pytest.PyTest, browser_service: BrowserService
) -> None:
    signals = AppSignals()
    panel = BrowserPanel(browser_service, signals)
    qtbot.addWidget(panel)
    panel.show()

    # Address bar focus
    panel.url_input.setText("https://test.org")
    qtbot.keyClick(panel.url_input, Qt.Key.Key_Return)
    assert panel.url_input.text() == "https://test.org"


@pytest.mark.ui
def test_browser_panel_multi_tab_operations(
    qtbot: pytest.PyTest, browser_service: BrowserService
) -> None:
    signals = AppSignals()
    panel = BrowserPanel(browser_service, signals)
    qtbot.addWidget(panel)
    panel.show()

    assert panel.tab_bar.count() == 1

    # Add new tab
    new_idx = panel.add_new_tab("https://github.com", "GitHub")
    assert panel.tab_bar.count() == 2
    assert panel.tab_bar.currentIndex() == new_idx

    # Close active tab
    panel.close_tab(new_idx)
    assert panel.tab_bar.count() == 1
