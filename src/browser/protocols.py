"""Protocol interfaces for batmanoverlay Browser Engine."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.browser.models import (
    BrowserProfile,
    BrowserSecurityLevel,
    BrowserSession,
    BrowserTabModel,
    NavigationState,
)


@runtime_checkable
class IBrowserProfile(Protocol):
    """Interface for managing browser profiles and storage paths."""

    @property
    def profile_id(self) -> str: ...

    @property
    def data_dir(self) -> Path: ...

    @property
    def cache_dir(self) -> Path: ...

    @property
    def cookies_dir(self) -> Path: ...

    @property
    def downloads_dir(self) -> Path: ...

    def get_profile(self, profile_id: str) -> BrowserProfile: ...


@runtime_checkable
class IBrowserSessionManager(Protocol):
    """Interface for managing browser sessions across workspaces."""

    def save_session(self, session: BrowserSession) -> bool: ...

    def load_session(self, workspace_id: str = "default") -> BrowserSession | None: ...

    def close_session(self, session_id: str) -> bool: ...


@runtime_checkable
class IBrowserHistory(Protocol):
    """Interface for tracking browser navigation history."""

    def add_entry(self, url: str, title: str) -> None: ...

    def get_recent(self, limit: int = 50) -> Sequence[tuple[str, str, str]]: ...

    def clear_history(self) -> int: ...


@runtime_checkable
class IBrowserSecurityPolicy(Protocol):
    """Interface for browser security permissions and content policy rules."""

    @property
    def camera_allowed(self) -> bool: ...

    @property
    def microphone_allowed(self) -> bool: ...

    @property
    def notifications_allowed(self) -> bool: ...

    @property
    def geolocation_allowed(self) -> bool: ...

    @property
    def popups_allowed(self) -> bool: ...

    @property
    def javascript_enabled(self) -> bool: ...

    def is_url_safe(self, url: str) -> bool: ...


@runtime_checkable
class IBrowserService(Protocol):
    """Primary service interface for browser operations, navigation, and state."""

    def normalize_url(self, raw_input: str) -> str: ...

    def is_search_query(self, raw_input: str) -> bool: ...

    def create_tab(
        self, url: str = "about:blank", security_level: BrowserSecurityLevel = ...
    ) -> BrowserTabModel: ...

    def close_tab(self, tab_id: str) -> bool: ...

    def get_active_navigation_state(self) -> NavigationState: ...

    def update_navigation_state(self, url: str, title: str = "") -> None: ...

    def clear_cache(self) -> bool: ...

    def clear_cookies(self) -> bool: ...
