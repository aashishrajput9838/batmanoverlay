"""Browser Service backend implementation for batmanoverlay."""

import re
from urllib.parse import quote_plus, urlparse

from loguru import logger
from PySide6.QtWebEngineCore import QWebEngineProfile

from src.browser.models import (
    BrowserSecurityLevel,
    BrowserSession,
    BrowserTabModel,
    NavigationState,
)
from src.browser.profile_manager import BrowserProfileManager
from src.browser.session_manager import BrowserSessionManager


class BrowserService:
    """Core backend service for URL normalization, profile isolation, and session lifecycle."""

    DOMAIN_REGEX = re.compile(
        r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/.*)?$|" r"^localhost(?::\d+)?(?:/.*)?$"
    )
    IP_REGEX = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?(?:/.*)?$")

    def __init__(
        self,
        profile_manager: BrowserProfileManager,
        session_manager: BrowserSessionManager,
        search_engine_url: str = "https://duckduckgo.com/?q=",
    ) -> None:
        self._profile_mgr = profile_manager
        self._session_mgr = session_manager
        self._search_engine_url = search_engine_url
        self._current_session: BrowserSession = self._session_mgr.load_session("default")
        self._active_nav_state = NavigationState(url="about:blank")

        logger.info("Initialized BrowserService backend")

    @property
    def current_session(self) -> BrowserSession:
        return self._current_session

    def get_qt_profile(self, profile_id: str = "default") -> QWebEngineProfile:
        """Get or initialize persistent QWebEngineProfile for a given workspace profile."""
        return self._profile_mgr.get_or_create_qt_profile(profile_id)

    def is_search_query(self, raw_input: str) -> bool:
        """Determine if raw user input is a web search query versus a URL."""
        cleaned = raw_input.strip()
        if not cleaned:
            return False

        if cleaned.startswith(("http://", "https://", "about:", "file://", "chrome://")):
            return False

        if " " in cleaned:
            return True

        return not (self.DOMAIN_REGEX.match(cleaned) or self.IP_REGEX.match(cleaned))

    def normalize_url(self, raw_input: str) -> str:
        """Normalize raw user input into a valid HTTP/HTTPS URL or search query URL."""
        cleaned = raw_input.strip()
        if not cleaned:
            return "about:blank"

        if cleaned.startswith(("http://", "https://", "about:", "file://")):
            return cleaned

        if self.is_search_query(cleaned):
            return f"{self._search_engine_url}{quote_plus(cleaned)}"

        # Prepend https:// for valid domains and IPs
        return f"https://{cleaned}"

    def create_tab(
        self,
        url: str = "about:blank",
        security_level: BrowserSecurityLevel = BrowserSecurityLevel.STANDARD,
    ) -> BrowserTabModel:
        """Create a new browser tab model and append to session."""
        normalized_url = self.normalize_url(url)
        tab = BrowserTabModel(
            url=normalized_url,
            title="New Tab" if normalized_url == "about:blank" else normalized_url,
            security_level=security_level,
        )
        self._current_session.open_tabs.append(tab)
        self._session_mgr.save_session(self._current_session)
        logger.info(f"Created browser tab {tab.id} for URL: {normalized_url}")
        return tab

    def close_tab(self, tab_id: str) -> bool:
        """Remove a tab from the active session."""
        original_count = len(self._current_session.open_tabs)
        self._current_session.open_tabs = [
            t for t in self._current_session.open_tabs if t.id != tab_id
        ]
        if len(self._current_session.open_tabs) < original_count:
            self._session_mgr.save_session(self._current_session)
            logger.info(f"Closed browser tab: {tab_id}")
            return True
        return False

    def get_active_navigation_state(self) -> NavigationState:
        """Return current navigation state."""
        return self._active_nav_state

    def update_navigation_state(self, url: str, title: str = "") -> None:
        """Update active navigation state model."""
        parsed = urlparse(url)
        is_secure = parsed.scheme == "https" or url == "about:blank"
        self._active_nav_state = NavigationState(url=url, title=title or url, is_secure=is_secure)

    def clear_cache(self) -> bool:
        """Clear cache directory for current profile."""
        try:
            cache_dir = self._profile_mgr.cache_dir
            for f in cache_dir.glob("*"):
                if f.is_file():
                    f.unlink()
            logger.info("Cleared browser profile cache")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    def clear_cookies(self) -> bool:
        """Clear cookies directory for current profile."""
        try:
            cookies_dir = self._profile_mgr.cookies_dir
            for f in cookies_dir.glob("*"):
                if f.is_file():
                    f.unlink()
            logger.info("Cleared browser profile cookies")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            return False

    def flush_cookies(self) -> None:
        """Flush all browser profile cookie stores on shutdown."""
        self._profile_mgr.flush_cookies()
