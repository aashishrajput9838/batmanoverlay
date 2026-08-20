"""Unit tests for src.platform.security module."""

import sys
from pathlib import Path

import pytest

from src.platform.security import apply_uipi_message_filter, harden_process_security


@pytest.mark.unit
def test_harden_process_security_execution() -> None:
    """Verify harden_process_security runs cleanly without exception."""
    res = harden_process_security()
    if sys.platform == "win32":
        assert res is True
    else:
        assert res is False


@pytest.mark.unit
def test_apply_uipi_message_filter_invalid_hwnd() -> None:
    """Verify apply_uipi_message_filter handles invalid HWND gracefully."""
    res = apply_uipi_message_filter(0)
    assert res is False


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_apply_uipi_message_filter_valid_widget_hwnd() -> None:
    """Verify apply_uipi_message_filter on QWidget winId."""
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    widget.show()
    hwnd = int(widget.winId()) if widget.winId() else 0
    res = apply_uipi_message_filter(hwnd)

    if sys.platform == "win32" and hwnd:
        assert res is True
    else:
        assert res is False

    widget.close()
