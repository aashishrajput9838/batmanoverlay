"""Unit tests for SQLiteStore connection and migrations."""

from pathlib import Path

import pytest

from src.storage.sqlite_store import SQLiteStore


@pytest.mark.unit
def test_sqlite_store_initialization(tmp_path: Path) -> None:
    db_file = tmp_path / "test_clipboard.db"
    store = SQLiteStore(db_file)

    assert db_file.exists()

    with store.connect() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clipboard_items'"
        )
        assert cursor.fetchone() is not None
