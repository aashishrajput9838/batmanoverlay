"""Browser Profile Manager for workspace-isolated storage profiles."""

from pathlib import Path

from loguru import logger

from src.browser.models import BrowserProfile


class BrowserProfileManager:
    """Manages workspace-specific browser profile directory structures and isolation."""

    def __init__(self, base_data_dir: Path) -> None:
        self._base_dir = base_data_dir / "browser" / "profiles"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, BrowserProfile] = {}

        # Ensure default profile exists
        self.get_or_create_profile("default")

    def get_or_create_profile(self, profile_id: str = "default") -> BrowserProfile:
        """Get or initialize a workspace profile with isolated directory structure."""
        if profile_id in self._profiles:
            return self._profiles[profile_id]

        profile_dir = self._base_dir / profile_id
        cache_dir = profile_dir / "cache"
        cookies_dir = profile_dir / "cookies"
        history_dir = profile_dir / "history"
        downloads_dir = profile_dir / "downloads"
        sessions_dir = profile_dir / "sessions"

        for p in (profile_dir, cache_dir, cookies_dir, history_dir, downloads_dir, sessions_dir):
            p.mkdir(parents=True, exist_ok=True)

        profile = BrowserProfile(
            profile_id=profile_id,
            name=f"Profile-{profile_id}",
            data_dir=profile_dir,
            cache_dir=cache_dir,
            cookies_dir=cookies_dir,
            history_dir=history_dir,
            downloads_dir=downloads_dir,
            sessions_dir=sessions_dir,
        )

        self._profiles[profile_id] = profile
        logger.info(f"Initialized browser profile '{profile_id}' at {profile_dir}")
        return profile

    def get_profile(self, profile_id: str = "default") -> BrowserProfile:
        """Retrieve existing profile or create if missing."""
        return self.get_or_create_profile(profile_id)

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
