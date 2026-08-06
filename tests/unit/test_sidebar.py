"""Unit tests for Sidebar."""

import pytest
from PySide6.QtWidgets import QWidget

from src.constants import PanelName
from src.ui.sidebar import Sidebar


@pytest.mark.unit
@pytest.mark.usefixtures("qapp")
def test_sidebar_panel_selection() -> None:
    parent = QWidget()
    sidebar = Sidebar(parent)
    selected_panels: list[str] = []

    sidebar.panel_selected.connect(selected_panels.append)

    sidebar.set_active_panel(PanelName.SETTINGS)
    assert len(selected_panels) == 0

    sidebar._on_button_clicked(PanelName.CLIPBOARD)
    assert len(selected_panels) == 1
    assert selected_panels[0] == PanelName.CLIPBOARD
