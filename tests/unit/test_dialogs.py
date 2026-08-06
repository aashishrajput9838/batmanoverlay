"""Unit tests for Modal Dialogs."""

import pytest

from src.ui.dialogs import ConfirmDialog, ErrorDialog, RecoveryDialog


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_dialogs_instantiation() -> None:
    confirm = ConfirmDialog("Test Title", "Test Message")
    assert confirm.windowTitle() == "Test Title"

    error = ErrorDialog("Error Title", "E101", "Database Error", "Details trace")
    assert error.windowTitle() == "Error Title"

    recovery = RecoveryDialog()
    assert recovery.windowTitle() == "Session Recovery"
