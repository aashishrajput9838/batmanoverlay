"""SQLite database connection and schema migration manager for batmanoverlay."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from loguru import logger

from src.storage.exceptions import StorageError


class SQLiteStore:
    """Manages thread-safe SQLite connection and migration lifecycle."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _initialize_db(self) -> None:
        """Apply WAL mode and run database schema migrations."""
        conn = None
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")

            migrations_dir = Path(__file__).parent / "migrations"
            if migrations_dir.exists():
                for sql_file in sorted(migrations_dir.glob("*.sql")):
                    sql_script = sql_file.read_text(encoding="utf-8")
                    conn.executescript(sql_script)
            logger.info(f"Initialized SQLite database at {self._db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize SQLite database at {self._db_path}: {e}")
            raise StorageError(f"Database initialization failed: {e}") from e
        finally:
            if conn:
                conn.close()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Provide a managed connection context with automatic row factory."""
        conn = None
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"SQLite transaction error: {e}")
            raise StorageError(f"Database operation failed: {e}") from e
        finally:
            if conn:
                conn.close()
