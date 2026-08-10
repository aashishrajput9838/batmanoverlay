"""Interfaces and data models for screenshot capture backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class CaptureStatus(StrEnum):
    """Strongly typed status outcome for screenshot capture operations."""

    SUCCESS = "SUCCESS"
    PROTECTED_CONTENT = "PROTECTED_CONTENT"
    CAPTURE_NOT_REPRESENTATIVE = "CAPTURE_NOT_REPRESENTATIVE"
    CAPTURE_UNAVAILABLE = "CAPTURE_UNAVAILABLE"
    CAPTURE_ERROR = "CAPTURE_ERROR"


@dataclass(frozen=True)
class RawFrameData:
    """Structured pixel container returned by native capture backends."""

    width: int
    height: int
    bytes_data: bytes
    bytes_per_line: int
    format_name: str
    backend_name: str


class IScreenshotBackend(ABC):
    """Abstract interface for desktop screenshot capture implementations."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the backend is supported on the current system."""

    @abstractmethod
    def capture_virtual_desktop(self) -> tuple[CaptureStatus, RawFrameData | None, str | None]:
        """Attempt desktop capture.

        Returns:
            Tuple of (CaptureStatus, RawFrameData | None, error_message | None).
        """
