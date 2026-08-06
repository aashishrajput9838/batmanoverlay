"""UI unit tests for BrowserPanel component."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from src.browser.profile_manager import BrowserProfileManager
from src.browser.service import BrowserService
from src.browser.session_manager import BrowserSessionManager
from src.core.events import AppSignals
from src.ui.browser_panel import BrowserPanel


@pytest.fixture
def browser_service(tmp_path: Path) -> BrowserService:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)
    return BrowserService(profile_mgr, session_mgr)


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
