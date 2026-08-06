"""Unit tests for TitleBar."""

import pytest
from PySide6.QtWidgets import QWidget

from src.ui.title_bar import TitleBar


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_title_bar_toggles() -> None:
    parent = QWidget()
    title_bar = TitleBar(parent)

    collapsed_events: list[bool] = []
    pinned_events: list[bool] = []

    title_bar.collapse_toggled.connect(collapsed_events.append)
    title_bar.pin_toggled.connect(pinned_events.append)

    title_bar._toggle_collapse()
    assert len(collapsed_events) == 1
    assert collapsed_events[0] is True

    title_bar._btn_pin.setChecked(False)
    title_bar._toggle_pin()
    assert len(pinned_events) == 1
    assert pinned_events[0] is False
