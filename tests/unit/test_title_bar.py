"""Unit tests for TitleBar."""

import pytest
from PySide6.QtWidgets import QWidget

from src.ui.title_bar import TitleBar


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_title_bar_collapse_toggle() -> None:
    parent = QWidget()
    title_bar = TitleBar(parent)

    collapsed_events: list[bool] = []
    title_bar.collapse_toggled.connect(collapsed_events.append)

    title_bar._toggle_collapse()
    assert len(collapsed_events) == 1
    assert collapsed_events[0] is True

    title_bar._toggle_collapse()
    assert len(collapsed_events) == 2
    assert collapsed_events[1] is False


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_title_bar_set_collapsed() -> None:
    parent = QWidget()
    title_bar = TitleBar(parent)

    title_bar.set_collapsed(True)
    assert title_bar._is_collapsed is True

    title_bar.set_collapsed(False)
    assert title_bar._is_collapsed is False
