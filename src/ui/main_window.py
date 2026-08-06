"""
Production Main Window overlay shell for batmanoverlay.
"""

import contextlib
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMoveEvent, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.clipboard.protocols import IClipboardService
from src.constants import (
    GEOMETRY_SAVE_DEBOUNCE_MS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    TITLE_BAR_HEIGHT,
    PanelName,
)
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.models.session import WindowGeometry
from src.storage.json_store import JsonStore
from src.ui.clipboard_panel import ClipboardPanel
from src.ui.settings_panel import SettingsPanel
from src.ui.sidebar import Sidebar
from src.ui.status_bar import StatusBar
from src.ui.title_bar import TitleBar
from src.ui.toast import ToastManager


class _PlaceholderWidget(QWidget):
    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        label = QLabel(
            f"<h3>{name.capitalize()} Panel Shell</h3>"
            f"<p>Module will be implemented in Sprint-00{self._get_sprint_num(name)}.</p>",
            self,
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def _get_sprint_num(self, name: str) -> int:
        match name:
            case PanelName.CLIPBOARD:
                return 2
            case PanelName.TYPING:
                return 3
            case PanelName.BROWSER:
                return 4
            case PanelName.BOOKMARKS:
                return 5
            case _:
                return 1


class MainWindow(QMainWindow):
    """Main Application Window shell providing overlay controls and geometry persistence."""

    def __init__(
        self,
        config_manager: ConfigManager,
        signals: AppSignals,
        data_dir: Path,
        clipboard_service: IClipboardService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MainWindow")
        self._config_manager = config_manager
        self._signals = signals
        self._data_dir = data_dir
        self._clipboard_service = clipboard_service
        self._json_store = JsonStore()
        self._geometry_file = data_dir / "sessions" / "geometry.json"

        self._is_collapsed = False
        self._is_pinned = True
        self._expanded_height = 768

        # Setup Debounced Geometry Save Timer
        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.setInterval(GEOMETRY_SAVE_DEBOUNCE_MS)
        self._geometry_timer.timeout.connect(self._save_geometry_now)

        # Frameless Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )

        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(1024, 768)

        self._setup_ui()
        self._restore_geometry()
        self._connect_signals()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom TitleBar
        self.title_bar = TitleBar(central)
        root_layout.addWidget(self.title_bar)

        # 2. Main Content Split Area (Sidebar + Panel Stack)
        self._content_widget = QWidget(central)
        content_layout = QHBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = Sidebar(self._content_widget)
        content_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget(self._content_widget)

        # Instantiate Panels
        clipboard_widget: QWidget
        if self._clipboard_service:
            clipboard_widget = ClipboardPanel(self._clipboard_service, self._signals, self.stack)
        else:
            clipboard_widget = _PlaceholderWidget(PanelName.CLIPBOARD, self.stack)

        self._panel_widgets: dict[str, QWidget] = {
            PanelName.BROWSER: _PlaceholderWidget(PanelName.BROWSER, self.stack),
            PanelName.CLIPBOARD: clipboard_widget,
            PanelName.TYPING: _PlaceholderWidget(PanelName.TYPING, self.stack),
            PanelName.BOOKMARKS: _PlaceholderWidget(PanelName.BOOKMARKS, self.stack),
            PanelName.SETTINGS: SettingsPanel(self._config_manager, self.stack),
        }

        for _panel_name, widget in self._panel_widgets.items():
            self.stack.addWidget(widget)

        content_layout.addWidget(self.stack)
        root_layout.addWidget(self._content_widget, stretch=1)

        # 3. StatusBar
        self.status_bar = StatusBar(self._signals, central)
        root_layout.addWidget(self.status_bar)

        self.setCentralWidget(central)

        # 4. Toast Manager Overlay
        self.toast_manager = ToastManager(self)

    def _connect_signals(self) -> None:
        # TitleBar signals
        self.title_bar.collapse_toggled.connect(self.set_collapsed)
        self.title_bar.pin_toggled.connect(self.set_always_on_top)
        self.title_bar.opacity_changed.connect(self.set_window_opacity)
        self.title_bar.panel_requested.connect(self.switch_panel)

        # Sidebar signals
        self.sidebar.panel_selected.connect(self.switch_panel)

        # AppSignals
        self._signals.panel_changed.connect(self.switch_panel)
        self._signals.toast_requested.connect(self.toast_manager.show_toast)

    def switch_panel(self, panel_name: str) -> None:
        """Switch active panel stack view."""
        if panel_name in self._panel_widgets:
            widget = self._panel_widgets[panel_name]
            self.stack.setCurrentWidget(widget)
            self.sidebar.set_active_panel(panel_name)
            self._signals.status_message.emit(f"Switched to {panel_name.capitalize()}")
            self._schedule_geometry_save()

    def set_window_opacity(self, opacity: float) -> None:
        """Set window transparency level."""
        clamped = max(0.1, min(1.0, opacity))
        self.setWindowOpacity(clamped)
        self._schedule_geometry_save()

    def set_always_on_top(self, is_pinned: bool) -> None:
        """Toggle WindowStaysOnTopHint window flag."""
        self._is_pinned = is_pinned
        self.title_bar.set_pinned(is_pinned)

        flags = self.windowFlags()
        if is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.show()  # Re-show required after window flags mutation on Windows
        self._schedule_geometry_save()

    def set_collapsed(self, is_collapsed: bool) -> None:
        """Toggle collapsed mode (showing title bar only vs full window)."""
        self._is_collapsed = is_collapsed
        self.title_bar.set_collapsed(is_collapsed)

        if is_collapsed:
            self._expanded_height = self.height()
            self._content_widget.hide()
            self.status_bar.hide()
            self.setFixedHeight(TITLE_BAR_HEIGHT)
        else:
            self.setFixedHeight(max(MIN_WINDOW_HEIGHT, self._expanded_height))
            self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            self.setMaximumSize(16777215, 16777215)
            self._content_widget.show()
            self.status_bar.show()

        self._schedule_geometry_save()

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._schedule_geometry_save()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._schedule_geometry_save()

    def _schedule_geometry_save(self) -> None:
        self._geometry_timer.start()

    def _save_geometry_now(self) -> None:
        geo = WindowGeometry(
            x=self.x(),
            y=self.y(),
            width=self.width(),
            height=self._expanded_height if self._is_collapsed else self.height(),
            opacity=self.windowOpacity(),
            is_collapsed=self._is_collapsed,
            is_pinned=self._is_pinned,
            is_always_on_top=bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint),
            active_panel=self.sidebar._buttons[PanelName.SETTINGS].panel_name,
        )
        with contextlib.suppress(Exception):
            self._json_store.write_atomic(self._geometry_file, geo)

    def _restore_geometry(self) -> None:
        if not self._geometry_file.exists():
            self.switch_panel(PanelName.SETTINGS)
            return

        try:
            raw = self._json_store.read(self._geometry_file)
            geo = WindowGeometry.model_validate(raw)

            self.move(geo.x, geo.y)
            self.resize(geo.width, geo.height)
            self._expanded_height = geo.height
            self.set_window_opacity(geo.opacity)
            self.set_always_on_top(geo.is_pinned)

            if geo.is_collapsed:
                self.set_collapsed(True)

            self.switch_panel(geo.active_panel or PanelName.SETTINGS)
        except Exception:
            self.switch_panel(PanelName.SETTINGS)
