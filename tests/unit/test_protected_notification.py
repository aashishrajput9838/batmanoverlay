"""Unit tests for Application-Aware Protected Screenshot Failure Notification."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtGui import QColor, QImage, QPixmap

from src.platform.screenshot.backend_interface import CaptureStatus
from src.platform.screenshot.screenshot_service import ScreenshotService
from src.platform.screenshot.window_detector import WindowDetector, WindowInfo
from src.platform.screenshot.windows_capture import WindowsCapture


@pytest.mark.unit
def test_find_responsible_protected_window_codetantra() -> None:
    w_chrome = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)
    w_prot = WindowInfo(2, "CodeTantra Secure Browser", "CodeTantra", True, 0, 0, 800, 600)

    found = WindowDetector.find_responsible_protected_window([w_chrome, w_prot])
    assert found is not None
    assert found.app_name == "CodeTantra"


@pytest.mark.unit
def test_find_responsible_protected_window_none() -> None:
    w_chrome = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)
    w_vscode = WindowInfo(2, "VS Code", "VSCode", False, 100, 100, 800, 600)

    found = WindowDetector.find_responsible_protected_window([w_chrome, w_vscode])
    assert found is None


@pytest.mark.unit
def test_protected_capture_codetantra_notification(tmp_path: Path) -> None:
    service = ScreenshotService()
    w_prot = WindowInfo(1, "CodeTantra Secure Browser", "CodeTantra", True, 0, 0, 800, 600)

    with patch.object(WindowDetector, "get_visible_windows", return_value=[w_prot]):
        result = service.take_screenshot(output_dir=tmp_path)
        assert result.status == CaptureStatus.PROTECTED_CONTENT
        assert result.success is False
        assert result.is_protected_content is True
        assert result.protected_app_name == "CodeTantra"
        assert result.file_path is None
        assert "Protected application: CodeTantra" in (result.error_message or "")

        # Verify NO files created in directory
        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) == 0


@pytest.mark.unit
def test_protected_capture_unknown_app_notification(tmp_path: Path) -> None:
    service = ScreenshotService()

    with (
        patch.object(WindowDetector, "get_visible_windows", return_value=[]),
        patch.object(
            WindowsCapture,
            "capture_full_desktop",
            return_value=(CaptureStatus.PROTECTED_CONTENT, None, "WGC"),
        ),
    ):
        result = service.take_screenshot(output_dir=tmp_path)
        assert result.status == CaptureStatus.PROTECTED_CONTENT
        assert result.success is False
        assert result.is_protected_content is True
        assert result.protected_app_name == "Unknown application"
        assert result.file_path is None
        assert "Protected application: Unknown application" in (result.error_message or "")

        # Verify NO files created in directory
        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) == 0


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_normal_chrome_capture_succeeds(tmp_path: Path) -> None:
    service = ScreenshotService()
    w_chrome = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)

    qimg = QImage(100, 100, QImage.Format.Format_RGB32)
    for y in range(100):
        for x in range(100):
            qimg.setPixelColor(x, y, QColor(x * 2, y * 2, (x + y) % 255))
    dummy_pixmap = QPixmap.fromImage(qimg)

    with (
        patch.object(WindowDetector, "get_visible_windows", return_value=[w_chrome]),
        patch.object(
            WindowsCapture,
            "capture_full_desktop",
            return_value=(CaptureStatus.SUCCESS, dummy_pixmap, "DXGIDesktopDuplication"),
        ),
    ):
        result = service.take_screenshot(output_dir=tmp_path)
        assert result.status == CaptureStatus.SUCCESS
        assert result.success is True
        assert result.file_path is not None
        assert result.file_path.exists()
        assert "Chrome" in result.file_path.name
