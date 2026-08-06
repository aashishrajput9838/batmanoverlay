"""Clipboard Import and Export format contracts for batmanoverlay."""

import csv
import io
import json

from loguru import logger

from src.clipboard.exceptions import ClipboardExportError
from src.models.clipboard import ClipboardBatch, ClipboardItem


class ClipboardExporter:
    """Formatter for exporting and importing clipboard collections
    across JSON, CSV, and TXT formats.
    """

    @staticmethod
    def export_json(items: list[ClipboardItem]) -> str:
        """Export clipboard items into formatted JSON payload."""
        try:
            batch = ClipboardBatch(count=len(items), items=items)
            return batch.model_dump_json(indent=2)
        except Exception as e:
            logger.error(f"JSON export error: {e}")
            raise ClipboardExportError(f"JSON export failed: {e}") from e

    @staticmethod
    def import_json(json_str: str) -> list[ClipboardItem]:
        """Import clipboard items from JSON payload."""
        try:
            raw = json.loads(json_str)
            if isinstance(raw, dict) and "items" in raw:
                batch = ClipboardBatch.model_validate(raw)
                return batch.items
            if isinstance(raw, list):
                return [ClipboardItem.model_validate(item) for item in raw]
            raise ValueError("Invalid JSON clipboard payload structure")
        except Exception as e:
            logger.error(f"JSON import error: {e}")
            raise ClipboardExportError(f"JSON import failed: {e}") from e

    @staticmethod
    def export_csv(items: list[ClipboardItem]) -> str:
        """Export clipboard items into CSV string format."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "id",
                    "content",
                    "content_type",
                    "char_count",
                    "word_count",
                    "line_count",
                    "timestamp",
                    "is_pinned",
                    "is_favorite",
                ]
            )
            for item in items:
                writer.writerow(
                    [
                        item.id,
                        item.content,
                        str(item.content_type),
                        item.char_count,
                        item.word_count,
                        item.line_count,
                        item.timestamp.isoformat(),
                        item.is_pinned,
                        item.is_favorite,
                    ]
                )
            return output.getvalue()
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            raise ClipboardExportError(f"CSV export failed: {e}") from e

    @staticmethod
    def export_txt(items: list[ClipboardItem]) -> str:
        """Export clipboard item text contents separated by double newlines."""
        return "\n\n---\n\n".join(item.content for item in items if item.content)
