"""Exception hierarchy for batmanoverlay."""

from src.storage.exceptions import (
    BatmanOverlayError,
    ClipboardStorageError,
    DatabaseConnectionError,
    DatabaseMigrationError,
    JsonFileError,
    SessionCorruptionError,
    StorageError,
)

__all__ = [
    "BatmanOverlayError",
    "BrowserError",
    "ClipboardStorageError",
    "ConfigurationError",
    "DatabaseConnectionError",
    "DatabaseMigrationError",
    "DeadlockPreventionError",
    "HotkeyConflictError",
    "HotkeyError",
    "JsonFileError",
    "SendInputFailureError",
    "SessionCorruptionError",
    "StorageError",
    "TabCrashError",
    "TargetWindowLostError",
    "TypingError",
    "UndoExpiredError",
    "WorkspaceError",
    "WorkspaceImportError",
    "WorkspaceNameConflictError",
]


class BrowserError(BatmanOverlayError):
    error_code = "E200"


class TabCrashError(BrowserError):
    error_code = "E201"
    user_message = "A browser tab crashed unexpectedly."


class TypingError(BatmanOverlayError):
    error_code = "E300"


class TargetWindowLostError(TypingError):
    error_code = "E301"
    user_message = "Typing was paused because the target window is no longer focused."


class SendInputFailureError(TypingError):
    error_code = "E302"
    user_message = "Could not send keystrokes. The target application may not accept input."


class HotkeyError(BatmanOverlayError):
    error_code = "E400"


class HotkeyConflictError(HotkeyError):
    error_code = "E401"
    user_message = "This keyboard shortcut is already used by another application."


class ConfigurationError(BatmanOverlayError):
    error_code = "E500"
    user_message = "A settings value is invalid and has been reset to default."


class WorkspaceError(BatmanOverlayError):
    error_code = "E600"


class WorkspaceNameConflictError(WorkspaceError):
    error_code = "E601"
    user_message = "A workspace with this name already exists."


class WorkspaceImportError(WorkspaceError):
    error_code = "E602"
    user_message = "The workspace file could not be imported."


class DeadlockPreventionError(BatmanOverlayError):
    error_code = "E700"
    user_message = "An internal timeout occurred. Please restart the application."


class UndoExpiredError(BatmanOverlayError):
    error_code = "E800"
    user_message = "The undo window has expired."
