"""Unit tests for WindowDetector top-level application detection and name sanitization."""

import pytest

from src.platform.screenshot.window_detector import WindowDetector, WindowInfo


@pytest.mark.unit
def test_sanitize_app_name() -> None:
    assert WindowDetector.sanitize_app_name("Google Chrome") == "GoogleChrome"
    assert WindowDetector.sanitize_app_name("VS Code : Project") == "VSCodeProject"
    assert WindowDetector.sanitize_app_name("File / Explorer *") == "FileExplorer"
    assert WindowDetector.sanitize_app_name("???") == "App"


@pytest.mark.unit
def test_get_app_name_from_title() -> None:
    assert WindowDetector.get_app_name_from_title("Google Chrome - New Tab") == "Chrome"
    title_vscode = "main.py - BatmanOverlay - Visual Studio Code"
    assert WindowDetector.get_app_name_from_title(title_vscode) == "VSCode"
    assert WindowDetector.get_app_name_from_title("File Explorer") == "FileExplorer"
    assert WindowDetector.get_app_name_from_title("CodeTantra - Online Test") == "CodeTantra"
    assert WindowDetector.get_app_name_from_title("Microsoft Edge") == "Edge"


@pytest.mark.unit
def test_is_window_protected() -> None:
    assert WindowDetector.is_window_protected("CodeTantra Secure Browser", 123) is True
    assert WindowDetector.is_window_protected("Google Chrome", 456) is False
    assert WindowDetector.is_window_protected("Visual Studio Code", 789) is False


@pytest.mark.unit
def test_build_screenshot_filename_prefix() -> None:
    assert WindowDetector.build_screenshot_filename_prefix([]) == "Desktop"

    w1 = WindowInfo(1, "Google Chrome", "Chrome", False, 0, 0, 800, 600)
    assert WindowDetector.build_screenshot_filename_prefix([w1]) == "Chrome"

    w2 = WindowInfo(2, "VS Code", "VSCode", False, 100, 100, 800, 600)
    assert WindowDetector.build_screenshot_filename_prefix([w1, w2]) == "Chrome+VSCode"

    w3 = WindowInfo(3, "File Explorer", "FileExplorer", False, 200, 200, 800, 600)
    prefix_3 = WindowDetector.build_screenshot_filename_prefix([w1, w2, w3])
    assert prefix_3 == "Chrome+VSCode+FileExplorer"
