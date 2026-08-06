"""Clipboard Domain Data Models for batmanoverlay."""

import hashlib
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ClipboardItemType(StrEnum):
    """Enumeration of supported clipboard content types."""

    TEXT = "text"
    CODE = "code"
    URL = "url"
    HTML = "html"
    IMAGE = "image"
    FILE = "file"


class ClipboardItem(BaseModel):
    """Domain model representing a single clipboard entry."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    content_type: ClipboardItemType = ClipboardItemType.TEXT
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_pinned: bool = False
    is_favorite: bool = False
    source_app: str | None = None
    content_hash: str = ""

    def model_post_init(self, __context: object) -> None:
        """Compute metadata and content hash after model initialization."""
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()

        if self.content_type == ClipboardItemType.TEXT:
            self.char_count = len(self.content)
            self.word_count = len(self.content.split())
            self.line_count = len(self.content.splitlines()) or (1 if self.content else 0)


class ClipboardBatch(BaseModel):
    """Batch collection of clipboard items for import/export."""

    exported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    count: int = 0
    items: list[ClipboardItem] = Field(default_factory=list)
