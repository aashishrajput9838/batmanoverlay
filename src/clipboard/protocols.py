"""Clipboard Engine Interface Protocols for batmanoverlay."""

from typing import Protocol, runtime_checkable

from src.models.clipboard import ClipboardItem


@runtime_checkable
class IClipboardRepository(Protocol):
    """Abstract protocol contract for clipboard persistence repositories."""

    def save_item(self, item: ClipboardItem) -> ClipboardItem: ...

    def get_item_by_id(self, item_id: str) -> ClipboardItem | None: ...

    def get_items(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_pinned: bool = False,
        filter_favorite: bool = False,
    ) -> list[ClipboardItem]: ...

    def search_items(self, query_str: str, limit: int = 50) -> list[ClipboardItem]: ...

    def update_item(self, item: ClipboardItem) -> None: ...

    def delete_item(self, item_id: str) -> bool: ...

    def clear_history(self, keep_pinned: bool = True) -> int: ...

    def get_count(self) -> int: ...


@runtime_checkable
class IClipboardService(Protocol):
    """Abstract protocol contract for clipboard management services."""

    def add_text(self, text: str, source_app: str | None = None) -> ClipboardItem | None: ...

    def get_history(self, limit: int = 100, offset: int = 0) -> list[ClipboardItem]: ...

    def toggle_pin(self, item_id: str) -> bool: ...

    def toggle_favorite(self, item_id: str) -> bool: ...

    def remove_item(self, item_id: str) -> bool: ...

    def clear_all(self, keep_pinned: bool = True) -> int: ...
