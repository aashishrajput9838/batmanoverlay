"""UI unit tests for ClipboardPanel, ClipboardItemCard, and ClipboardDialogs."""

from pathlib import Path

import pytest

from src.clipboard.service import ClipboardService
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.storage.clipboard_repository import ClipboardRepository
from src.storage.sqlite_store import SQLiteStore
from src.ui.clipboard_card import ClipboardItemCard
from src.ui.clipboard_panel import ClipboardPanel
from src.ui.dialogs import ClipboardClearConfirmDialog, ClipboardPreviewDialog


@pytest.fixture
def clipboard_service(tmp_path: Path) -> ClipboardService:
    db_file = tmp_path / "test_ui_clipboard.db"
    store = SQLiteStore(db_file)
    repo = ClipboardRepository(store)
    signals = AppSignals()
    config_mgr = ConfigManager(tmp_path)
    return ClipboardService(repo, signals, config_mgr)


@pytest.mark.ui
def test_clipboard_panel_initialization_and_refresh(
    qtbot: pytest.PyTest, clipboard_service: ClipboardService
) -> None:
    panel = ClipboardPanel(clipboard_service, clipboard_service._signals)
    qtbot.addWidget(panel)
    panel.show()

    # Empty state initial check
    assert panel.empty_state.isVisible()
    assert panel.count_badge.text() == "0 items"

    # Add item to service
    item1 = clipboard_service.add_text("First Clipboard Item")
    assert item1 is not None

    assert panel.list_widget.count() == 1
    assert panel.count_badge.text() == "1 items"
    assert not panel.empty_state.isVisible()


@pytest.mark.ui
def test_clipboard_panel_search_filtering(
    qtbot: pytest.PyTest, clipboard_service: ClipboardService
) -> None:
    clipboard_service.add_text("Python Code Snippet")
    clipboard_service.add_text("Qt Desktop Design")
    clipboard_service.add_text("Database Schema DDL")

    panel = ClipboardPanel(clipboard_service, clipboard_service._signals)
    qtbot.addWidget(panel)

    assert panel.list_widget.count() == 3

    # Type into search input
    panel.search_input.setText("Python")
    assert panel.list_widget.count() == 1

    # Clear search
    panel.search_input.clear()
    assert panel.list_widget.count() == 3


@pytest.mark.ui
def test_clipboard_panel_tab_filtering(
    qtbot: pytest.PyTest, clipboard_service: ClipboardService
) -> None:
    item1 = clipboard_service.add_text("Normal item")
    item2 = clipboard_service.add_text("Pinned item")
    assert item1 is not None
    assert item2 is not None
    clipboard_service.toggle_pin(item2.id)

    panel = ClipboardPanel(clipboard_service, clipboard_service._signals)
    qtbot.addWidget(panel)

    # All filter
    assert panel.list_widget.count() == 2

    # Pinned filter
    panel._set_filter("pinned")
    assert panel.list_widget.count() == 1


@pytest.mark.ui
def test_clipboard_card_and_dialog_instantiation(
    qtbot: pytest.PyTest, clipboard_service: ClipboardService
) -> None:
    item = clipboard_service.add_text("Preview Item Content")
    assert item is not None

    card = ClipboardItemCard(item)
    qtbot.addWidget(card)
    assert card.text_label.text() == "Preview Item Content"

    dlg = ClipboardPreviewDialog(item)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Clipboard Item Detail"

    confirm_dlg = ClipboardClearConfirmDialog()
    qtbot.addWidget(confirm_dlg)
    assert confirm_dlg.keep_pinned() is True


@pytest.mark.ui
def test_image_clipboard_card_and_dialog_instantiation(
    qtbot: pytest.PyTest, clipboard_service: ClipboardService, tmp_path: Path
) -> None:
    from PySide6.QtGui import QImage, QPixmap

    # Create dummy screenshot file
    img_file = tmp_path / "test_screenshot.png"
    img = QImage(100, 100, QImage.Format.Format_RGB32)
    img.fill(0xFF0000)
    img.save(str(img_file), "PNG")

    from src.models.clipboard import ClipboardItemType

    item = clipboard_service.add_item(str(img_file), content_type=ClipboardItemType.IMAGE)
    assert item is not None

    card = ClipboardItemCard(item)
    qtbot.addWidget(card)
    assert hasattr(card, "img_label")
    assert card.sizeHint().height() >= 220

    dlg = ClipboardPreviewDialog(item)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Clipboard Item Detail"
