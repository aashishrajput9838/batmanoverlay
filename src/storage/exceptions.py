"""Storage domain exceptions for batmanoverlay."""


class BatmanOverlayError(Exception):
    """Base exception for batmanoverlay."""

    def __init__(
        self,
        message: str | None = None,
        error_code: str = "E000",
        user_message: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.user_message = user_message or message or "An unexpected error occurred."
        self.message = message or self.user_message
        super().__init__(self.message)


class StorageError(BatmanOverlayError):
    """Base for storage-related errors."""

    error_code = "E100"


class DatabaseConnectionError(StorageError):
    error_code = "E101"
    user_message = "Could not connect to the database."


class DatabaseMigrationError(StorageError):
    error_code = "E102"
    user_message = "Database upgrade failed. Your data may need to be restored from backup."


class ClipboardStorageError(StorageError):
    error_code = "E110"
    user_message = "Could not save to clipboard. The data file may be in use."


class SessionCorruptionError(StorageError):
    error_code = "E120"
    user_message = "Your session file is corrupted. A fresh session will be started."


class JsonFileError(StorageError):
    error_code = "E130"
    user_message = "A configuration file could not be read."
