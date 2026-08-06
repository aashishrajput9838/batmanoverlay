"""Clipboard history panel widget for batmanoverlay."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.clipboard.exporters import ClipboardExporter
from src.clipboard.protocols import IClipboardService
from src.core.events import AppSignals
from src.models.clipboard import ClipboardItem
from src.ui.clipboard_card import ClipboardItemCard
from src.ui.dialogs import ClipboardClearConfirmDialog, ClipboardPreviewDialog
from src.ui.icons import IconManager


class ClipboardPanel(QWidget):
    """Main panel displaying full clipboard history, filtering, preview, and controls."""

    def __init__(
        self,
        clipboard_service: IClipboardService,
        signals: AppSignals,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = clipboard_service
        self.signals = signals

        self._active_filter = "all"  # "all" | "pinned" | "favorites"
        self._search_query = ""

        self._setup_ui()
        self._connect_signals()
        self.refresh_items()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_label = QLabel("<b>Clipboard History</b>", self)
        header_layout.addWidget(title_label)

        self.count_badge = QLabel("0 items", self)
        self.count_badge.setStyleSheet("color: #A6ADC8; font-size: 11px;")
        header_layout.addWidget(self.count_badge)

        header_layout.addStretch()

        self.btn_export = QToolButton(self)
        self.btn_export.setIcon(IconManager.get_icon("settings"))
        self.btn_export.setToolTip("Export History (JSON / CSV / TXT)")
        self.btn_export.clicked.connect(self._on_export_clicked)
        header_layout.addWidget(self.btn_export)

        self.btn_clear = QToolButton(self)
        self.btn_clear.setIcon(IconManager.get_icon("delete"))
        self.btn_clear.setToolTip("Clear Clipboard History")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        header_layout.addWidget(self.btn_clear)

        main_layout.addLayout(header_layout)

        # Search Bar & Filter Tabs Row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search clipboard (Ctrl+F)...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_row.addWidget(self.search_input, stretch=1)

        # Filter buttons
        self.btn_filter_all = QPushButton("All", self)
        self.btn_filter_all.setCheckable(True)
        self.btn_filter_all.setChecked(True)
        self.btn_filter_all.clicked.connect(lambda: self._set_filter("all"))
        filter_row.addWidget(self.btn_filter_all)

        self.btn_filter_pinned = QPushButton("Pinned", self)
        self.btn_filter_pinned.setCheckable(True)
        self.btn_filter_pinned.clicked.connect(lambda: self._set_filter("pinned"))
        filter_row.addWidget(self.btn_filter_pinned)

        self.btn_filter_fav = QPushButton("Favorites", self)
        self.btn_filter_fav.setCheckable(True)
        self.btn_filter_fav.clicked.connect(lambda: self._set_filter("favorites"))
        filter_row.addWidget(self.btn_filter_fav)

        main_layout.addLayout(filter_row)

        # Main List Widget
        self.list_widget = QListWidget(self)
        self.list_widget.setSpacing(4)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.list_widget, stretch=1)

        # Empty State Label
        self.empty_label = QLabel("No clipboard items captured yet.", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #6C7086; font-size: 13px;")
        main_layout.addWidget(self.empty_label)

    def _connect_signals(self) -> None:
        self.signals.clipboard_item_added.connect(lambda _: self.refresh_items())
        self.signals.clipboard_item_deleted.connect(lambda _: self.refresh_items())
        self.signals.clipboard_cleared.connect(self.refresh_items)

    def _set_filter(self, filter_type: str) -> None:
        self._active_filter = filter_type
        self.btn_filter_all.setChecked(filter_type == "all")
        self.btn_filter_pinned.setChecked(filter_type == "pinned")
        self.btn_filter_fav.setChecked(filter_type == "favorites")
        self.refresh_items()

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip()
        self.refresh_items()

    def refresh_items(self) -> None:
        """Fetch items matching current filter/search and rebuild list widget."""
        if self._search_query:
            items = self.service.search_history(self._search_query)
        else:
            items = self.service.get_history()

        # Apply active tab filter
        if self._active_filter == "pinned":
            items = [i for i in items if i.is_pinned]
        elif self._active_filter == "favorites":
            items = [i for i in items if i.is_favorite]

        self.list_widget.clear()
        self.count_badge.setText(f"{len(items)} items")

        if not items:
            self.list_widget.hide()
            if self._search_query:
                self.empty_label.setText(f"No clipboard items match '{self._search_query}'.")
            else:
                self.empty_label.setText("No clipboard items captured yet.")
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.list_widget.show()

        for item in items:
            list_item = QListWidgetItem(self.list_widget)
            card = ClipboardItemCard(item, self.list_widget)

            # Connect card signals
            card.pin_toggled.connect(self._on_pin_toggled)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            card.copy_requested.connect(self._on_copy_requested)
            card.delete_requested.connect(self._on_delete_requested)
            card.preview_requested.connect(self._open_preview)

            list_item.setSizeHint(card.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, card)

    def _on_pin_toggled(self, item_id: str) -> None:
        self.service.toggle_pin(item_id)
        self.refresh_items()

    def _on_favorite_toggled(self, item_id: str) -> None:
        self.service.toggle_favorite(item_id)
        self.refresh_items()

    def _on_copy_requested(self, _item_id: str) -> None:
        self.signals.toast_requested.emit("info", "Copied to clipboard!")

    def _on_delete_requested(self, item_id: str) -> None:
        self.service.delete_item(item_id)
        self.refresh_items()

    def _open_preview(self, item: ClipboardItem) -> None:
        dlg = ClipboardPreviewDialog(item, self)
        dlg.exec()

    def _on_item_double_clicked(self, list_item: QListWidgetItem) -> None:
        widget = self.list_widget.itemWidget(list_item)
        if isinstance(widget, ClipboardItemCard):
            self._open_preview(widget.item)

    def _on_clear_clicked(self) -> None:
        dlg = ClipboardClearConfirmDialog(self)
        if dlg.exec():
            keep_pinned = dlg.keep_pinned()
            count = self.service.clear_all(keep_pinned=keep_pinned)
            self.signals.toast_requested.emit(
                "info", f"Cleared {count} clipboard items from history."
            )
            self.refresh_items()

    def _on_export_clicked(self) -> None:
        items = self.service.get_history()
        if not items:
            self.signals.toast_requested.emit("warning", "No items available to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Clipboard History",
            "clipboard_export.json",
            "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt)",
        )
        if not file_path:
            return

        if file_path.endswith(".csv"):
            data = ClipboardExporter.export_csv(items)
        elif file_path.endswith(".txt"):
            data = ClipboardExporter.export_txt(items)
        else:
            data = ClipboardExporter.export_json(items)

        Path(file_path).write_text(data, encoding="utf-8")

        self.signals.toast_requested.emit("info", f"Exported {len(items)} items to {file_path}.")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle panel key bindings: Ctrl+F, Delete, Enter, Esc."""
        if event.key() == Qt.Key.Key_F and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.search_input.setFocus()
            self.search_input.selectAll()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Escape and (
            self.search_input.hasFocus() or self._search_query
        ):
            self.search_input.clear()
            self.list_widget.setFocus()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Delete:
            curr_item = self.list_widget.currentItem()
            if curr_item:
                widget = self.list_widget.itemWidget(curr_item)
                if isinstance(widget, ClipboardItemCard):
                    self.service.delete_item(widget.item.id)
                    self.refresh_items()
                    event.accept()
                    return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            curr_item = self.list_widget.currentItem()
            if curr_item:
                widget = self.list_widget.itemWidget(curr_item)
                if isinstance(widget, ClipboardItemCard):
                    QApplication.clipboard().setText(widget.item.content)
                    self.signals.toast_requested.emit("info", "Copied to clipboard!")
                    event.accept()
                    return

        super().keyPressEvent(event)
