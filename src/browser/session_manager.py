"""Browser Session Manager for saving and restoring browser session state."""

from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from src.browser.models import BrowserSession, BrowserTabModel
from src.browser.profile_manager import BrowserProfileManager
from src.storage.json_store import JsonStore


class BrowserSessionManager:
    """Manages persistence, restoration, and lifecycle of browser sessions across workspaces."""

    def __init__(self, profile_manager: BrowserProfileManager) -> None:
        self._profile_mgr = profile_manager
        self._json_store = JsonStore()

    def _get_session_path(self, workspace_id: str) -> Path:
        profile = self._profile_mgr.get_profile(workspace_id)
        return profile.sessions_dir / "session.json"

    def save_session(self, session: BrowserSession) -> bool:
        """Save a browser session to persistent storage."""
        try:
            session.updated_at = datetime.now(UTC)
            session_file = self._get_session_path(session.workspace_id)
            self._json_store.write_atomic(session_file, session)
            tab_cnt = len(session.open_tabs)
            logger.debug(
                f"Saved browser session for workspace '{session.workspace_id}' ({tab_cnt} tabs)."
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save browser session for '{session.workspace_id}': {e}")
            return False

    def load_session(self, workspace_id: str = "default") -> BrowserSession:
        """Load browser session for workspace. Returns fresh session if unreadable/missing."""
        session_file = self._get_session_path(workspace_id)
        if session_file.exists():
            try:
                data = self._json_store.read(session_file)
                session = BrowserSession.model_validate(data)
                tab_cnt = len(session.open_tabs)
                logger.info(f"Restored browser session for '{workspace_id}' ({tab_cnt} tabs).")
                return session
            except Exception as e:
                logger.warning(
                    f"Corrupted session file for '{workspace_id}': {e}. Creating new session."
                )

        logger.info(f"No existing session found for '{workspace_id}'. Creating new session.")
        new_session = BrowserSession(
            workspace_id=workspace_id, open_tabs=[BrowserTabModel(url="about:blank")]
        )
        self.save_session(new_session)
        return new_session

    def close_session(self, session_id: str) -> bool:
        """Close session resources."""
        logger.info(f"Closed browser session '{session_id}'")
        return True
