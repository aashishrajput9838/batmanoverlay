"""Unit tests for Browser Foundation engine (models, profile, session, service)."""

from pathlib import Path

import pytest
from PySide6.QtWebEngineCore import QWebEngineProfile

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
    assert profile.sessions_dir.exists()
    # Hotfix-005: Verify cookies directory is NOT pre-created as a directory
    assert not (profile.data_dir / "cookies").is_dir()
    assert not (profile.data_dir / "Cookies").is_dir()


@pytest.mark.unit
def test_cookies_directory_is_never_created_and_legacy_migrated(tmp_path: Path) -> None:
    """Hotfix-005 Regression Test: Verify cookies directory is never pre-created

    and any legacy directory named 'cookies' or 'Cookies' is safely removed
    without affecting History, Local Storage, or Session Storage.
    """
    profile_dir = tmp_path / "browser" / "profiles" / "default"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Pre-create legacy directory named 'cookies' and dummy user data
    legacy_cookies_dir = profile_dir / "cookies"
    legacy_cookies_dir.mkdir()
    (legacy_cookies_dir / "old_stale_data.txt").write_text("old")

    history_dir = profile_dir / "history"
    history_dir.mkdir()
    (history_dir / "history.db").write_text("dummy history")

    profile_mgr = BrowserProfileManager(tmp_path)

    # 1. Verify legacy directory was deleted to prevent collision
    assert not legacy_cookies_dir.exists()

    # 2. Verify other user data was NOT deleted
    assert history_dir.exists()
    assert (history_dir / "history.db").exists()

    # 3. Verify cookies_dir in model points to Cookies file location
    profile = profile_mgr.get_profile("default")
    assert profile.cookies_dir == profile_dir / "Cookies"
    assert not profile.cookies_dir.is_dir()


@pytest.mark.unit
def test_browser_profile_qwebengine_persistence(tmp_path: Path) -> None:
    """Hotfix-004/005 Verification: Ensure QWebEngineProfile is persistent,

    uses workspace storage/cache paths, enforces ForcePersistentCookies,
    re-uses profile instances, and flushes cookies cleanly.
    """
    profile_mgr = BrowserProfileManager(tmp_path)

    qt_profile = profile_mgr.get_or_create_qt_profile("default")
    assert qt_profile.isOffTheRecord() is False

    # 1. Storage Path Verification
    expected_storage = (tmp_path / "browser" / "profiles" / "default").resolve()
    assert Path(qt_profile.persistentStoragePath()).resolve() == expected_storage

    # 2. Cache Path Verification
    expected_cache = (tmp_path / "browser" / "profiles" / "default" / "cache").resolve()
    assert Path(qt_profile.cachePath()).resolve() == expected_cache

    # 3. Persistent Cookies Policy Verification
    assert (
        qt_profile.persistentCookiesPolicy()
        == QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )

    # 4. Same Profile Instance Returned (no redundant profiles)
    again = profile_mgr.get_or_create_qt_profile("default")
    assert again is qt_profile

    # 5. Cookie Flush Verification
    profile_mgr.flush_cookies()


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

    # Test service level persistent profile & cookie flush
    qt_prof = service.get_qt_profile("default")
    assert qt_prof.isOffTheRecord() is False
    service.flush_cookies()
