"""Clipboard Domain Exceptions for batmanoverlay."""

from src.core.exceptions import BatmanOverlayError


class ClipboardError(BatmanOverlayError):
    """Base exception for clipboard engine domain errors."""

    def __init__(self, message: str, error_code: str = "CB_001") -> None:
        super().__init__(message=message, error_code=error_code, user_message=message)


class ClipboardStorageError(ClipboardError):
    """Exception raised when clipboard SQLite storage operations fail."""

    def __init__(self, message: str) -> None:
        super().__init__(message=f"Clipboard storage error: {message}", error_code="CB_101")


class ClipboardExportError(ClipboardError):
    """Exception raised when clipboard export or import operations fail."""

    def __init__(self, message: str) -> None:
        super().__init__(message=f"Clipboard export error: {message}", error_code="CB_201")
