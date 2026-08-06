"""Unit tests for StatusBar."""

import pytest
from PySide6.QtWidgets import QWidget

from src.core.events import AppSignals
from src.ui.status_bar import StatusBar


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_status_bar_updates() -> None:
    signals = AppSignals()
    parent = QWidget()
    bar = StatusBar(signals, parent)

    signals.status_message.emit("Test status message")
    assert bar._status_label.text() == "Test status message"
