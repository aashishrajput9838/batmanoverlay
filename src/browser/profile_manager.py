"""Browser Profile Manager for workspace-isolated storage profiles."""

import contextlib
import shutil
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject
from PySide6.QtWebEngineCore import QWebEngineProfile

from src.browser.models import BrowserProfile


class BrowserProfileManager:
    """Manages workspace-specific browser profile directory structures and isolation."""

    def __init__(self, base_data_dir: Path, parent: QObject | None = None) -> None:
        self._base_dir = base_data_dir / "browser" / "profiles"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._parent = parent

        self._profiles: dict[str, BrowserProfile] = {}
        self._qt_profiles: dict[str, QWebEngineProfile] = {}

        # Ensure default profile exists
        self.get_or_create_profile("default")

    def get_or_create_profile(self, profile_id: str = "default") -> BrowserProfile:
        """Get or initialize a workspace profile with isolated directory structure."""
        if profile_id in self._profiles:
            return self._profiles[profile_id]

        profile_dir = self._base_dir / profile_id
        cache_dir = profile_dir / "cache"
        history_dir = profile_dir / "history"
        downloads_dir = profile_dir / "downloads"
        sessions_dir = profile_dir / "sessions"

        # Hotfix-005: Clean up any legacy directory named 'cookies' or 'Cookies'
        # to prevent file vs directory collision with Chromium's SQLite database file.
        for legacy_name in ("cookies", "Cookies"):
            legacy_target = profile_dir / legacy_name
            if legacy_target.exists() and legacy_target.is_dir():
                try:
                    shutil.rmtree(legacy_target)
                    logger.warning(
                        f"Removed legacy directory '{legacy_target}' to allow "
                        f"Chromium SQLite Cookies database file creation"
                    )
                except OSError as e:
                    logger.error(
                        f"Failed to remove legacy cookies directory '{legacy_target}': {e}"
                    )

        # Note: Do NOT mkdir cookies_dir!
        # Chromium manages the SQLite file named Cookies in profile_dir.
        for p in (profile_dir, cache_dir, history_dir, downloads_dir, sessions_dir):
            p.mkdir(parents=True, exist_ok=True)

        cookies_file = profile_dir / "Cookies"

        profile = BrowserProfile(
            profile_id=profile_id,
            name=f"Profile-{profile_id}",
            data_dir=profile_dir,
            cache_dir=cache_dir,
            cookies_dir=cookies_file,
            history_dir=history_dir,
            downloads_dir=downloads_dir,
            sessions_dir=sessions_dir,
        )

        self._profiles[profile_id] = profile
        logger.info(f"Initialized browser profile '{profile_id}' at {profile_dir}")
        return profile

    def get_or_create_qt_profile(self, profile_id: str = "default") -> QWebEngineProfile:
        """Get or initialize a persistent QWebEngineProfile instance for a workspace profile."""
        if profile_id in self._qt_profiles:
            return self._qt_profiles[profile_id]

        bp = self.get_or_create_profile(profile_id)
        qt_profile = QWebEngineProfile(f"batmanoverlay_{profile_id}", self._parent)

        # Configure persistent storage and cache paths
        qt_profile.setPersistentStoragePath(str(bp.data_dir))
        qt_profile.setCachePath(str(bp.cache_dir))

        # Explicitly enforce ForcePersistentCookies policy for session persistence
        qt_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self._qt_profiles[profile_id] = qt_profile

        # Determine Cookies storage status for startup logging
        cookies_target = bp.data_dir / "Cookies"
        if not cookies_target.exists():
            cookies_target_lower = bp.data_dir / "cookies"
            if cookies_target_lower.exists():
                cookies_target = cookies_target_lower

        if cookies_target.is_file():
            cookies_status = f"FILE ({cookies_target.stat().st_size:,} bytes)"
        elif cookies_target.is_dir():
            cookies_status = "DIRECTORY (COLLISION ERROR)"
        else:
            cookies_status = "NOT_YET_CREATED (Will be created by Chromium on navigation)"

        logger.info(
            f"Configured persistent QWebEngineProfile '{profile_id}': "
            f"storageName={qt_profile.storageName()}, "
            f"persistentStoragePath={bp.data_dir}, "
            f"cachePath={bp.cache_dir}, "
            f"cookies_policy=ForcePersistentCookies, "
            f"cookies_status={cookies_status}"
        )
        return qt_profile

    def get_profile(self, profile_id: str = "default") -> BrowserProfile:
        """Retrieve existing profile or create if missing."""
        return self.get_or_create_profile(profile_id)

    def flush_cookies(self) -> None:
        """Ensure all browser profile cookie stores load and flush to disk on exit."""
        for _pid, qt_profile in self._qt_profiles.items():
            with contextlib.suppress(Exception):
                qt_profile.cookieStore().loadAllCookies()
        logger.info("Flushed all browser profile cookie stores to disk")

    @property
    def profile_id(self) -> str:
        return "default"

    @property
    def data_dir(self) -> Path:
        return self.get_profile("default").data_dir

    @property
    def cache_dir(self) -> Path:
        return self.get_profile("default").cache_dir

    @property
    def cookies_dir(self) -> Path:
        return self.get_profile("default").cookies_dir

    @property
    def downloads_dir(self) -> Path:
        return self.get_profile("default").downloads_dir
