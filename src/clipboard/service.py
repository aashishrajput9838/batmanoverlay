"""Clipboard Domain Service for batmanoverlay."""

from loguru import logger
from PySide6.QtCore import QObject

from src.clipboard.monitor import ClipboardMonitor
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.models.clipboard import ClipboardItem, ClipboardItemType
from src.storage.clipboard_repository import ClipboardRepository


class ClipboardService(QObject):
    """Core domain service orchestrating clipboard ingestion, persistence, and signaling."""

    def __init__(
        self,
        repository: ClipboardRepository,
        signals: AppSignals,
        config_manager: ConfigManager,
        monitor: ClipboardMonitor | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._signals = signals
        self._config_manager = config_manager
        self._monitor = monitor

        if self._monitor:
            self._monitor.text_captured.connect(self._on_text_captured)

    def _on_text_captured(self, text: str) -> None:
        """Process text captured from system clipboard monitor."""
        self.add_text(text)

    def add_item(
        self,
        content: str,
        content_type: ClipboardItemType = ClipboardItemType.TEXT,
        source_app: str | None = None,
    ) -> ClipboardItem | None:
        """Validate, persist, and emit signal for a new clipboard entry (text, code, image, file)."""
        if not content or not content.strip():
            return None

        try:
            item = ClipboardItem(
                content=content,
                content_type=content_type,
                source_app=source_app,
            )
            saved_item = self._repository.save_item(item)

            # Enforce max history capacity limit
            max_capacity = int(self._config_manager.get("clipboard.max_history_items", 500))
            self._repository.enforce_max_capacity(max_capacity)

            # Notify application subscribers
            self._signals.clipboard_item_added.emit(saved_item.id)
            self._signals.status_message.emit("Clipboard entry recorded")
            logger.info(f"Clipboard entry added ({content_type}): {saved_item.id}")
            return saved_item
        except Exception as e:
            logger.error(f"Failed to add clipboard item: {e}")
            return None

    def add_text(self, text: str, source_app: str | None = None) -> ClipboardItem | None:
        """Validate, persist, and emit signal for new text clipboard entry."""
        return self.add_item(content=text, content_type=ClipboardItemType.TEXT, source_app=source_app)

    def get_history(self, limit: int = 100, offset: int = 0) -> list[ClipboardItem]:
        """Fetch history entries."""
        return self._repository.get_items(limit=limit, offset=offset)

    def search(self, query_str: str, limit: int = 50) -> list[ClipboardItem]:
        """Search entries matching query."""
        if not query_str:
            return self.get_history(limit=limit)
        return self._repository.search_items(query_str, limit=limit)

    def toggle_pin(self, item_id: str) -> bool:
        """Toggle pinned status of a item."""
        item = self._repository.get_item_by_id(item_id)
        if not item:
            return False

        item.is_pinned = not item.is_pinned
        self._repository.update_item(item)
        logger.info(f"Toggled pin for {item_id}: {item.is_pinned}")
        return item.is_pinned

    def toggle_favorite(self, item_id: str) -> bool:
        """Toggle favorite status of an item."""
        item = self._repository.get_item_by_id(item_id)
        if not item:
            return False

        item.is_favorite = not item.is_favorite
        self._repository.update_item(item)
        logger.info(f"Toggled favorite for {item_id}: {item.is_favorite}")
        return item.is_favorite

    def remove_item(self, item_id: str) -> bool:
        """Delete an item by ID."""
        success = self._repository.delete_item(item_id)
        if success:
            self._signals.clipboard_item_deleted.emit(item_id)
            logger.info(f"Deleted clipboard item {item_id}")
        return success

    def delete_item(self, item_id: str) -> bool:
        """Alias for remove_item."""
        return self.remove_item(item_id)

    def search_history(self, query_str: str, limit: int = 50) -> list[ClipboardItem]:
        """Alias for search."""
        return self.search(query_str, limit=limit)

    def clear_all(self, keep_pinned: bool = True) -> int:
        """Clear history entries."""
        count = self._repository.clear_history(keep_pinned=keep_pinned)
        self._signals.clipboard_cleared.emit()
        self._signals.status_message.emit("Clipboard history cleared")
        return count
