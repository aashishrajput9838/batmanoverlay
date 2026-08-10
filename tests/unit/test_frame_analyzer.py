"""Unit tests for FrameAnalyzer representative capture validation."""

import pytest
from PySide6.QtGui import QColor, QImage, QPixmap

from src.platform.screenshot.frame_analyzer import FrameAnalyzer
from src.platform.screenshot.window_detector import WindowInfo


@pytest.mark.unit
def test_analyze_frame_null_pixmap() -> None:
    is_rep, reason = FrameAnalyzer.analyze_frame(None, [])
    assert is_rep is False
    assert "Null pixmap" in reason


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_analyze_frame_desktop_only() -> None:
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(0, 0, 0))
    is_rep, reason = FrameAnalyzer.analyze_frame(pixmap, [])
    assert is_rep is True
    assert "Desktop capture validated" in reason


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_analyze_frame_uniform_pixels_with_visible_apps() -> None:
    # Create a uniform single-color image (wallpaper signature)
    qimg = QImage(200, 200, QImage.Format.Format_RGB32)
    qimg.fill(QColor(50, 50, 50))
    pixmap = QPixmap.fromImage(qimg)

    w1 = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)
    is_rep, reason = FrameAnalyzer.analyze_frame(pixmap, [w1])

    assert is_rep is False
    assert "non-representative" in reason.lower()
