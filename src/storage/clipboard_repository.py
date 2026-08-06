"""Clipboard SQLite Repository for batmanoverlay."""

from datetime import UTC, datetime

from loguru import logger

from src.models.clipboard import ClipboardItem, ClipboardItemType
from src.storage.exceptions import StorageError
from src.storage.sqlite_store import SQLiteStore


class ClipboardRepository:
    """Data Access Object handling SQLite persistence for clipboard entries."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def save_item(self, item: ClipboardItem) -> ClipboardItem:
        """Save a new clipboard item or bump timestamp if deduplicated."""
        try:
            with self._store.connect() as conn:
                # Check deduplication by hash
                cursor = conn.execute(
                    "SELECT id, is_pinned, is_favorite FROM clipboard_items "
                    "WHERE content_hash = ?",
                    (item.content_hash,),
                )
                row = cursor.fetchone()
                if row:
                    existing_id = str(row["id"])
                    now_str = datetime.now(UTC).isoformat()
                    conn.execute(
                        "UPDATE clipboard_items SET timestamp = ? WHERE id = ?",
                        (now_str, existing_id),
                    )
                    logger.debug(f"Deduplicated clipboard item hash {item.content_hash[:8]}")
                    saved_item = self.get_item_by_id(existing_id)
                    if saved_item:
                        return saved_item

                # Insert new item
                conn.execute(
                    """
                    INSERT INTO clipboard_items (
                        id, content, content_type, char_count, word_count, line_count,
                        timestamp, is_pinned, is_favorite, source_app, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        item.content,
                        str(item.content_type),
                        item.char_count,
                        item.word_count,
                        item.line_count,
                        item.timestamp.isoformat(),
                        1 if item.is_pinned else 0,
                        1 if item.is_favorite else 0,
                        item.source_app,
                        item.content_hash,
                    ),
                )
                logger.debug(f"Persisted clipboard item {item.id}")
                return item
        except Exception as e:
            logger.error(f"Failed to save clipboard item: {e}")
            raise StorageError(f"Save failed: {e}") from e

    def get_item_by_id(self, item_id: str) -> ClipboardItem | None:
        """Retrieve a single item by UUID."""
        with self._store.connect() as conn:
            cursor = conn.execute("SELECT * FROM clipboard_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_item(row)
        return None

    def get_items(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_pinned: bool = False,
        filter_favorite: bool = False,
    ) -> list[ClipboardItem]:
        """Query paginated clipboard items ordered by timestamp descending."""
        query = "SELECT * FROM clipboard_items WHERE 1=1"
        params: list[object] = []

        if filter_pinned:
            query += " AND is_pinned = 1"
        if filter_favorite:
            query += " AND is_favorite = 1"

        query += " ORDER BY is_pinned DESC, timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._store.connect() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_item(row) for row in rows]

    def search_items(self, query_str: str, limit: int = 50) -> list[ClipboardItem]:
        """Search clipboard items by substring match."""
        pattern = f"%{query_str}%"
        with self._store.connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM clipboard_items WHERE content LIKE ? "
                "ORDER BY is_pinned DESC, timestamp DESC LIMIT ?",
                (pattern, limit),
            )
            rows = cursor.fetchall()
            return [self._row_to_item(row) for row in rows]

    def update_item(self, item: ClipboardItem) -> None:
        """Update pinned or favorite flags of an existing item."""
        with self._store.connect() as conn:
            conn.execute(
                "UPDATE clipboard_items SET is_pinned = ?, is_favorite = ? WHERE id = ?",
                (1 if item.is_pinned else 0, 1 if item.is_favorite else 0, item.id),
            )

    def delete_item(self, item_id: str) -> bool:
        """Delete an item by ID."""
        with self._store.connect() as conn:
            cursor = conn.execute("DELETE FROM clipboard_items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def clear_history(self, keep_pinned: bool = True) -> int:
        """Clear unpinned clipboard history."""
        query = "DELETE FROM clipboard_items"
        if keep_pinned:
            query += " WHERE is_pinned = 0"

        with self._store.connect() as conn:
            cursor = conn.execute(query)
            deleted_count = cursor.rowcount
            logger.info(f"Cleared {deleted_count} items from clipboard history.")
            return deleted_count

    def get_count(self) -> int:
        """Get total number of stored clipboard items."""
        with self._store.connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM clipboard_items")
            return int(cursor.fetchone()[0])

    def enforce_max_capacity(self, max_items: int = 500) -> int:
        """Purge unpinned oldest entries exceeding capacity limit."""
        with self._store.connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM clipboard_items
                WHERE id IN (
                    SELECT id FROM clipboard_items
                    WHERE is_pinned = 0
                    ORDER BY timestamp DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (max_items,),
            )
            return cursor.rowcount

    def _row_to_item(self, row: dict[str, object]) -> ClipboardItem:
        raw_ts = str(row["timestamp"])
        ts = datetime.fromisoformat(raw_ts)
        return ClipboardItem(
            id=str(row["id"]),
            content=str(row["content"]),
            content_type=ClipboardItemType(str(row["content_type"])),
            char_count=int(str(row["char_count"])),
            word_count=int(str(row["word_count"])),
            line_count=int(str(row["line_count"])),
            timestamp=ts,
            is_pinned=bool(row["is_pinned"]),
            is_favorite=bool(row["is_favorite"]),
            source_app=str(row["source_app"]) if row["source_app"] else None,
            content_hash=str(row["content_hash"]),
        )
