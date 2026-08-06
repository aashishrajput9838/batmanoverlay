"""Integration tests for Browser Foundation engine."""

from pathlib import Path

import pytest

from src.browser.models import BrowserSession
from src.browser.profile_manager import BrowserProfileManager
from src.browser.service import BrowserService
from src.browser.session_manager import BrowserSessionManager


@pytest.mark.integration
def test_browser_foundation_integration_lifecycle(tmp_path: Path) -> None:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)
    service = BrowserService(profile_mgr, session_mgr)

    # Verify initial tab state
    assert len(service.current_session.open_tabs) >= 1

    # Create new tabs
    tab1 = service.create_tab("google.com")
    assert tab1.url == "https://google.com"

    tab2 = service.create_tab("python pyside6 tutorial")
    assert tab2.url.startswith("https://duckduckgo.com/?q=")

    # Verify session save and reload
    reloaded_session = session_mgr.load_session("default")
    assert len(reloaded_session.open_tabs) == 3


@pytest.mark.integration
def test_browser_crash_recovery_integration(tmp_path: Path) -> None:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)

    # Corrupt session file
    profile = profile_mgr.get_profile("corrupted_space")
    session_file = profile.sessions_dir / "session.json"
    session_file.write_text("INVALID_JSON_CORRUPTED_PAYLOAD", encoding="utf-8")

    # Attempt to load session -> must recover cleanly
    recovered = session_mgr.load_session("corrupted_space")
    assert isinstance(recovered, BrowserSession)
    assert len(recovered.open_tabs) == 1
    assert recovered.open_tabs[0].url == "about:blank"
