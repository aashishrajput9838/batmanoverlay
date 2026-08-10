"""Screenshot package exposing interfaces, backends, and domain services."""

from src.platform.screenshot.backend_interface import CaptureStatus, RawFrameData
from src.platform.screenshot.frame_analyzer import FrameAnalyzer
from src.platform.screenshot.screenshot_service import ScreenshotResult, ScreenshotService
from src.platform.screenshot.window_detector import WindowDetector, WindowInfo
from src.platform.screenshot.windows_capture import WindowsCapture

__all__ = [
    "CaptureStatus",
    "FrameAnalyzer",
    "RawFrameData",
    "ScreenshotResult",
    "ScreenshotService",
    "WindowDetector",
    "WindowInfo",
    "WindowsCapture",
]
