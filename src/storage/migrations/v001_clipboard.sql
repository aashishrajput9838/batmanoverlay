-- Migration v001: Initial Clipboard Schema

CREATE TABLE IF NOT EXISTS clipboard_items (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text',
    char_count INTEGER NOT NULL DEFAULT 0,
    word_count INTEGER NOT NULL DEFAULT 0,
    line_count INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    source_app TEXT,
    content_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clipboard_hash ON clipboard_items(content_hash);
CREATE INDEX IF NOT EXISTS idx_clipboard_timestamp ON clipboard_items(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_clipboard_pinned ON clipboard_items(is_pinned);
CREATE INDEX IF NOT EXISTS idx_clipboard_favorite ON clipboard_items(is_favorite);
