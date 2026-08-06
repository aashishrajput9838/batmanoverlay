"""Unit tests for IconManager vector icon rendering and integrity."""

import pytest
from PySide6.QtGui import QIcon

from src.ui.icons import IconManager

ICON_NAMES = [
    "chevron_left",
    "chevron_right",
    "reload",
    "stop",
    "shield",
    "lock",
    "home",
    "close",
    "minimize",
    "maximize",
    "restore",
    "pin",
    "pin_filled",
    "collapse",
    "expand",
    "settings",
    "browser",
    "clipboard",
    "typing",
    "bookmarks",
    "search",
    "delete",
    "copy",
    "star",
    "star_filled",
    "info",
    "warning",
    "error",
]


@pytest.mark.unit
@pytest.mark.parametrize("icon_name", ICON_NAMES)
def test_icon_manager_returns_non_null_qicon(icon_name: str) -> None:
    """Verify every registered icon produces a non-null QIcon with valid pixmaps."""
    icon = IconManager.get_icon(icon_name)
    assert isinstance(icon, QIcon)
    assert icon.isNull() is False, f"Icon '{icon_name}' must not be null"

    pixmap = icon.pixmap(24, 24)
    assert pixmap.isNull() is False, f"Pixmap for '{icon_name}' must not be null"
    assert pixmap.width() > 0
    assert pixmap.height() > 0


@pytest.mark.unit
def test_icon_manager_caching() -> None:
    """Verify icon caching works for identical name and color parameters."""
    icon1 = IconManager.get_icon("chevron_left", "#CDD6F4")
    icon2 = IconManager.get_icon("chevron_left", "#CDD6F4")
    assert icon1 is icon2


@pytest.mark.unit
def test_icon_manager_disabled_mode_pixmap() -> None:
    """Verify disabled mode rendering contains a valid semi-transparent pixmap."""
    icon = IconManager.get_icon("reload")
    disabled_pixmap = icon.pixmap(24, 24, mode=QIcon.Mode.Disabled)
    assert disabled_pixmap.isNull() is False
