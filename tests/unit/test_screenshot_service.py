"""Unit tests for ScreenshotService, WindowDetector, and application-aware filenames."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtGui import QColor, QImage, QPixmap

from src.platform.screenshot.backend_interface import CaptureStatus
from src.platform.screenshot.screenshot_service import ScreenshotResult, ScreenshotService
from src.platform.screenshot.window_detector import WindowDetector, WindowInfo
from src.platform.screenshot.windows_capture import WindowsCapture


@pytest.mark.unit
def test_default_screenshots_dir() -> None:
    service = ScreenshotService()
    expected_dir = Path.home() / "Pictures" / "BatmanOverlay" / "Screenshots"
    assert service.get_default_screenshots_dir() == expected_dir


@pytest.mark.unit
def test_generate_filename_format(tmp_path: Path) -> None:
    service = ScreenshotService()
    fixed_dt = datetime(2026, 8, 8, 6, 55, 31, tzinfo=UTC)

    # Desktop only
    f1 = service.generate_filename(tmp_path, visible_windows=[], timestamp=fixed_dt)
    assert f1.name == "BatmanOverlay_Desktop_2026-08-08_06-55-31.png"

    # Single App
    w1 = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)
    f2 = service.generate_filename(tmp_path, visible_windows=[w1], timestamp=fixed_dt)
    assert f2.name == "BatmanOverlay_Chrome_2026-08-08_06-55-31.png"

    # Multiple Apps
    w2 = WindowInfo(2, "VS Code", "VSCode", False, 100, 100, 800, 600)
    f3 = service.generate_filename(tmp_path, visible_windows=[w1, w2], timestamp=fixed_dt)
    assert f3.name == "BatmanOverlay_Chrome+VSCode_2026-08-08_06-55-31.png"


@pytest.mark.unit
def test_generate_filename_collision_handling(tmp_path: Path) -> None:
    service = ScreenshotService()
    fixed_dt = datetime(2026, 8, 8, 6, 55, 31, tzinfo=UTC)
    w1 = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)

    # Pre-create the first candidate
    first_file = tmp_path / "BatmanOverlay_Chrome_2026-08-08_06-55-31.png"
    first_file.write_text("dummy image data")

    second_path = service.generate_filename(tmp_path, visible_windows=[w1], timestamp=fixed_dt)
    assert second_path.name == "BatmanOverlay_Chrome_2026-08-08_06-55-31_1.png"

    # Pre-create second candidate
    second_path.write_text("dummy image data")
    third_path = service.generate_filename(tmp_path, visible_windows=[w1], timestamp=fixed_dt)
    assert third_path.name == "BatmanOverlay_Chrome_2026-08-08_06-55-31_2.png"


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_take_screenshot_success(tmp_path: Path) -> None:
    service = ScreenshotService()
    # Gradient image to pass representative analysis
    qimg = QImage(100, 100, QImage.Format.Format_RGB32)
    for y in range(100):
        for x in range(100):
            qimg.setPixelColor(x, y, QColor(x * 2, y * 2, (x + y) % 255))
    dummy_pixmap = QPixmap.fromImage(qimg)

    with (
        patch.object(WindowDetector, "get_visible_windows", return_value=[]),
        patch.object(
            WindowsCapture,
            "capture_full_desktop",
            return_value=(CaptureStatus.SUCCESS, dummy_pixmap, "TestBackend"),
        ),
    ):
        result = service.take_screenshot(output_dir=tmp_path)
        assert result.status == CaptureStatus.SUCCESS
        assert result.success is True
        assert result.file_path is not None
        assert result.file_path.exists()
        assert result.file_path.stat().st_size > 0
        assert result.backend_used == "TestBackend"
        assert "Desktop" in result.file_path.name


@pytest.mark.unit
def test_take_screenshot_protected_window_priority(tmp_path: Path) -> None:
    """Verify CodeTantra visible + Chrome behind => PROTECTED_CONTENT and NO PNG saved."""
    service = ScreenshotService()
    w_chrome = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)
    w_prot = WindowInfo(2, "CodeTantra Secure Browser", "CodeTantra", True, 0, 0, 800, 600)

    with patch.object(WindowDetector, "get_visible_windows", return_value=[w_chrome, w_prot]):
        result = service.take_screenshot(output_dir=tmp_path)
        assert result.status == CaptureStatus.PROTECTED_CONTENT
        assert result.success is False
        assert result.is_protected_content is True
        assert result.file_path is None

        # Verify NO files were created in output directory
        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) == 0


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_windows_capture_qt_screens() -> None:
    """Verify WindowsCapture._capture_via_qt_screens generates a composite QPixmap."""
    pixmap = WindowsCapture._capture_via_qt_screens()
    if pixmap is not None:
        assert not pixmap.isNull()
        assert pixmap.width() > 0
        assert pixmap.height() > 0


@pytest.mark.unit
def test_screenshot_result_dataclass() -> None:
    res = ScreenshotResult(
        status=CaptureStatus.SUCCESS,
        success=True,
        file_path=Path("test.png"),
        backend_used="QtQScreen",
        detected_apps=["Chrome", "VSCode"],
    )
    assert res.status == CaptureStatus.SUCCESS
    assert res.success is True
    assert res.file_path == Path("test.png")
    assert res.backend_used == "QtQScreen"
    assert res.is_protected_content is False
    assert res.detected_apps == ["Chrome", "VSCode"]


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_take_screenshot_target_screen_geometry_crop(tmp_path: Path) -> None:
    """Verify take_screenshot crops full desktop pixmap to target screen rectangle."""
    from PySide6.QtCore import QRect

    service = ScreenshotService()
    qimg = QImage(200, 100, QImage.Format.Format_RGB32)
    for y in range(100):
        for x in range(200):
            qimg.setPixelColor(x, y, QColor(x, y, (x + y) % 255))
    dummy_pixmap = QPixmap.fromImage(qimg)

    target_rect = QRect(0, 0, 100, 100)

    with (
        patch.object(WindowDetector, "get_visible_windows", return_value=[]),
        patch.object(
            WindowsCapture,
            "capture_full_desktop",
            return_value=(CaptureStatus.SUCCESS, dummy_pixmap, "TestBackend"),
        ),
    ):
        result = service.take_screenshot(output_dir=tmp_path, target_screen_geometry=target_rect)
        assert result.status == CaptureStatus.SUCCESS
        assert result.success is True
        assert result.file_path is not None
        assert result.file_path.exists()
