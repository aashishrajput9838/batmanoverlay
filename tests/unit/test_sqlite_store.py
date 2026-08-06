"""Unit tests for SQLiteStore connection, migrations, and schema validation."""

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


@pytest.mark.unit
def test_sqlite_store_schema_validation_and_fallback_ddl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify schema validation applies fallback DDL if migrations dir is missing."""
    db_file = tmp_path / "test_fallback_clipboard.db"

    # Mock _get_migrations_dir to point to non-existent directory
    monkeypatch.setattr(
        SQLiteStore, "_get_migrations_dir", lambda _self: tmp_path / "non_existent_dir"
    )

    store = SQLiteStore(db_file)
    assert db_file.exists()

    with store.connect() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clipboard_items'"
        )
        assert cursor.fetchone() is not None
