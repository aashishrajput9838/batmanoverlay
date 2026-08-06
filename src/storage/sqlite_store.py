"""SQLite database connection and schema migration manager for batmanoverlay."""

import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from loguru import logger

from src.storage.exceptions import StorageError

DEFAULT_DDL_V001 = """
CREATE TABLE IF NOT EXISTS clipboard_items (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text',
    char_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    source_app TEXT,
    content_hash TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clipboard_hash ON clipboard_items(content_hash);
CREATE INDEX IF NOT EXISTS idx_clipboard_timestamp ON clipboard_items(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_clipboard_pinned ON clipboard_items(is_pinned);
CREATE INDEX IF NOT EXISTS idx_clipboard_favorite ON clipboard_items(is_favorite);
"""


class SQLiteStore:
    """Manages thread-safe SQLite connection, migrations, and schema validation."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _get_migrations_dir(self) -> Path:
        """Resolve migrations directory supporting PyInstaller frozen mode and dev mode."""
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidate = Path(meipass) / "src" / "storage" / "migrations"
                if candidate.exists():
                    return candidate
            exe_candidate = Path(sys.executable).parent / "src" / "storage" / "migrations"
            if exe_candidate.exists():
                return exe_candidate
        return Path(__file__).parent / "migrations"

    def _validate_schema(self, conn: sqlite3.Connection) -> None:
        """Verify required tables exist. Automatically apply fallback DDL if missing."""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clipboard_items';"
        )
        if cursor.fetchone() is None:
            logger.warning(
                f"Table 'clipboard_items' missing in {self._db_path}. Applying fallback DDL..."
            )
            conn.executescript(DEFAULT_DDL_V001)
            conn.commit()

            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='clipboard_items';"
            )
            if cursor.fetchone() is None:
                raise StorageError(
                    message="Database schema validation failed: 'clipboard_items' table missing.",
                    error_code="E102",
                    user_message=(
                        "Database initialization error. Could not create database tables."
                    ),
                )

    def _initialize_db(self) -> None:
        """Apply WAL mode, execute migrations, and validate database schema."""
        conn = None
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")

            migrations_dir = self._get_migrations_dir()
            if migrations_dir.exists():
                for sql_file in sorted(migrations_dir.glob("*.sql")):
                    sql_script = sql_file.read_text(encoding="utf-8")
                    conn.executescript(sql_script)

            self._validate_schema(conn)
            logger.info(f"Initialized & validated SQLite database at {self._db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize SQLite database at {self._db_path}: {e}")
            raise StorageError(
                message=f"Database initialization failed: {e}",
                error_code="E101",
                user_message="Database connection error. Could not initialize storage.",
            ) from e
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
            raise StorageError(
                message=f"Database operation failed: {e}",
                error_code="E100",
                user_message="Database storage error.",
            ) from e
        finally:
            if conn:
                conn.close()
