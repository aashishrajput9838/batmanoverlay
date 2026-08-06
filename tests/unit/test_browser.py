"""Unit tests for Browser Foundation engine (models, profile, session, service)."""

from pathlib import Path

import pytest

from src.browser.models import (
    BrowserSecurityLevel,
    BrowserSession,
    BrowserTabModel,
    NavigationState,
)
from src.browser.profile_manager import BrowserProfileManager
from src.browser.service import BrowserService
from src.browser.session_manager import BrowserSessionManager


@pytest.mark.unit
def test_browser_models() -> None:
    nav = NavigationState(url="https://example.com", title="Example", is_secure=True)
    assert nav.url == "https://example.com"
    assert nav.is_secure is True

    tab = BrowserTabModel(url="https://python.org", title="Python")
    assert tab.url == "https://python.org"
    assert tab.security_level == BrowserSecurityLevel.STANDARD

    session = BrowserSession(workspace_id="test_space", open_tabs=[tab])
    assert session.workspace_id == "test_space"
    assert len(session.open_tabs) == 1


@pytest.mark.unit
def test_browser_profile_manager(tmp_path: Path) -> None:
    profile_mgr = BrowserProfileManager(tmp_path)
    profile = profile_mgr.get_or_create_profile("work_workspace")

    assert profile.profile_id == "work_workspace"
    assert profile.cache_dir.exists()
    assert profile.cookies_dir.exists()
    assert profile.sessions_dir.exists()


@pytest.mark.unit
def test_browser_session_manager(tmp_path: Path) -> None:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)

    session = session_mgr.load_session("default")
    assert session.workspace_id == "default"
    assert len(session.open_tabs) >= 1

    tab2 = BrowserTabModel(url="https://pyside.org")
    session.open_tabs.append(tab2)
    assert session_mgr.save_session(session) is True

    restored = session_mgr.load_session("default")
    assert restored is not None
    assert len(restored.open_tabs) == 2


@pytest.mark.unit
def test_browser_service_url_normalization(tmp_path: Path) -> None:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)
    service = BrowserService(profile_mgr, session_mgr)

    # Valid URLs
    assert service.normalize_url("https://github.com") == "https://github.com"
    assert service.normalize_url("http://localhost:8000") == "http://localhost:8000"

    # Domain names needing https:// prefix
    assert service.normalize_url("google.com") == "https://google.com"
    assert service.normalize_url("sub.domain.org/path") == "https://sub.domain.org/path"
    assert service.normalize_url("192.168.1.1:8080") == "https://192.168.1.1:8080"

    # Search queries
    assert service.is_search_query("python tutorial pyside6") is True
    assert service.normalize_url("python tutorial pyside6").startswith(
        "https://duckduckgo.com/?q="
    )


@pytest.mark.unit
def test_browser_service_tab_and_clearing(tmp_path: Path) -> None:
    profile_mgr = BrowserProfileManager(tmp_path)
    session_mgr = BrowserSessionManager(profile_mgr)
    service = BrowserService(profile_mgr, session_mgr)

    tab = service.create_tab("https://pytest.org")
    assert tab.url == "https://pytest.org"

    assert service.close_tab(tab.id) is True
    assert service.clear_cache() is True
    assert service.clear_cookies() is True
