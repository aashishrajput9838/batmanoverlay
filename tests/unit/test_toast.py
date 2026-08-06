"""Unit tests for Toast notifications."""

import pytest
from PySide6.QtWidgets import QWidget

from src.ui.toast import ToastManager


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_toast_creation_and_manager() -> None:
    parent = QWidget()
    parent.resize(800, 600)
    toast_mgr = ToastManager(parent)

    toast_mgr.show_toast("info", "Information toast")
    toast_mgr.show_toast("warning", "Warning toast")

    assert len(toast_mgr._active_toasts) == 2
