"""Application-wide constants for batmanoverlay."""

from enum import StrEnum

# Application Information
APP_NAME: str = "batmanoverlay"
APP_ORGANIZATION: str = "batmanoverlay"
APP_DISPLAY_NAME: str = "batmanoverlay"

# Schema Versioning
SETTINGS_SCHEMA_VERSION: int = 1
HOTKEYS_SCHEMA_VERSION: int = 1
SESSION_SCHEMA_VERSION: int = 1
DB_SCHEMA_VERSION_CLIPBOARD: int = 1
DB_SCHEMA_VERSION_BOOKMARKS: int = 1
DB_SCHEMA_VERSION_HISTORY: int = 2

# Directory & File Constants (Relative to data_dir)
CONFIG_DIR: str = "config"
WORKSPACES_DIR: str = "workspaces"
LOGS_DIR: str = "logs"
SESSIONS_DIR: str = "sessions"
SETTINGS_FILE: str = "settings.json"
HOTKEYS_FILE: str = "hotkeys.json"
SESSION_FILE: str = "session.json"
SESSION_LOCK_FILE: str = "session.lock"
LOG_FILE: str = "batmanoverlay.log"
WORKSPACE_META_FILE: str = "meta.json"
BROWSER_SESSION_FILE: str = "session.json"
GEOMETRY_FILE: str = "geometry.json"

# Limits & Thresholds
MAX_WORKSPACE_NAME_LENGTH: int = 64
MAX_ENTRY_TEXT_LENGTH: int = 1_000_000
DEFAULT_WORKSPACE_NAME: str = "default"

# Timing Constants (ms)
AUTO_SAVE_INTERVAL_DEFAULT_MS: int = 60_000
CONFIG_SAVE_DEBOUNCE_MS: int = 500
GEOMETRY_SAVE_DEBOUNCE_MS: int = 200

# UI Dimensions
TITLE_BAR_HEIGHT: int = 36
STATUS_BAR_HEIGHT: int = 24
SIDEBAR_COLLAPSED_WIDTH: int = 48
MIN_WINDOW_WIDTH: int = 400
MIN_WINDOW_HEIGHT: int = 300

# Log Configuration
LOG_MAX_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_RETENTION_COUNT: int = 5
LOG_FORMAT: str = (
    "{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level:<8} | {module}:{function}:{line} | {message}"
)


class NotificationLevel(StrEnum):
    """Notification level enumeration."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PanelName(StrEnum):
    """Panel identifier enumeration."""

    BROWSER = "browser"
    CLIPBOARD = "clipboard"
    TYPING = "typing"
    BOOKMARKS = "bookmarks"
    SETTINGS = "settings"


class ThemeName(StrEnum):
    """Theme identifier enumeration."""

    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"
