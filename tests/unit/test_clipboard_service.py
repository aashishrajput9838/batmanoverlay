"""Unit tests for ClipboardService."""

from pathlib import Path

import pytest

from src.clipboard.service import ClipboardService
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.storage.clipboard_repository import ClipboardRepository
from src.storage.sqlite_store import SQLiteStore


@pytest.fixture
def service(tmp_path: Path) -> ClipboardService:
    db_file = tmp_path / "clipboard_service_test.db"
    store = SQLiteStore(db_file)
    repo = ClipboardRepository(store)
    signals = AppSignals()
    config_mgr = ConfigManager(tmp_path)
    return ClipboardService(repo, signals, config_mgr)


@pytest.mark.unit
def test_service_add_and_clear(service: ClipboardService) -> None:
    added_signals: list[str] = []
    service._signals.clipboard_item_added.connect(added_signals.append)

    item = service.add_text("Hello World Clipboard Service")
    assert item is not None
    assert len(added_signals) == 1
    assert added_signals[0] == item.id

    history = service.get_history()
    assert len(history) == 1

    cleared_count = service.clear_all()
    assert cleared_count == 1
    assert len(service.get_history()) == 0


@pytest.mark.unit
def test_service_toggle_pin_and_favorite(service: ClipboardService) -> None:
    item = service.add_text("Pinned Entry")
    assert item is not None

    pinned = service.toggle_pin(item.id)
    assert pinned is True

    fav = service.toggle_favorite(item.id)
    assert fav is True
