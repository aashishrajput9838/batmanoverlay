"""Unit tests for ClipboardRepository persistence operations."""

from pathlib import Path

import pytest

from src.models.clipboard import ClipboardItem, ClipboardItemType
from src.storage.clipboard_repository import ClipboardRepository
from src.storage.sqlite_store import SQLiteStore


@pytest.fixture
def repo(tmp_path: Path) -> ClipboardRepository:
    db_file = tmp_path / "clipboard_repo_test.db"
    store = SQLiteStore(db_file)
    return ClipboardRepository(store)


@pytest.mark.unit
def test_save_and_retrieve_item(repo: ClipboardRepository) -> None:
    item = ClipboardItem(content="Test Clipboard Content", content_type=ClipboardItemType.TEXT)
    saved = repo.save_item(item)

    assert saved.id == item.id
    fetched = repo.get_item_by_id(item.id)
    assert fetched is not None
    assert fetched.content == "Test Clipboard Content"
    assert fetched.char_count == len("Test Clipboard Content")


@pytest.mark.unit
def test_deduplication_updates_timestamp(repo: ClipboardRepository) -> None:
    item1 = ClipboardItem(content="Duplicate Content")
    saved1 = repo.save_item(item1)

    item2 = ClipboardItem(content="Duplicate Content")
    saved2 = repo.save_item(item2)

    assert saved2.id == saved1.id
    assert repo.get_count() == 1


@pytest.mark.unit
def test_search_and_filter(repo: ClipboardRepository) -> None:
    repo.save_item(ClipboardItem(content="Python Code Snippet"))
    repo.save_item(ClipboardItem(content="Qt Desktop App"))

    results = repo.search_items("Python")
    assert len(results) == 1
    assert "Python" in results[0].content


@pytest.mark.unit
def test_clear_history(repo: ClipboardRepository) -> None:
    repo.save_item(ClipboardItem(content="Normal Entry 1"))
    repo.save_item(ClipboardItem(content="Pinned Entry", is_pinned=True))

    deleted = repo.clear_history(keep_pinned=True)
    assert deleted == 1
    assert repo.get_count() == 1
