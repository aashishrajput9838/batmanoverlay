"""
Production Main Window overlay shell for batmanoverlay.
"""

import contextlib
import ctypes
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import (
    QCloseEvent,
    QIcon,
    QKeySequence,
    QMoveEvent,
    QResizeEvent,
    QShortcut,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.browser.protocols import IBrowserService
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
from src.platform.global_hotkey import (
    HOTKEY_ID_CTRL_ALT_E,
    MOD_ALT,
    MOD_CONTROL,
    MSG,
    VK_E,
    WM_HOTKEY,
    WindowsGlobalHotkeyManager,
)
from src.platform.screenshot import CaptureStatus, ScreenshotService
from src.platform.zorder_manager import ZOrderWatchdogManager
from src.storage.json_store import JsonStore
from src.ui.browser_panel import BrowserPanel
from src.ui.clipboard_panel import ClipboardPanel
from src.ui.overlay_visibility_panel import OverlayVisibilityPanel
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
        browser_service: IBrowserService | None = None,
        typing_engine: Any | None = None,
        screenshot_service: ScreenshotService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MainWindow")
        self._config_manager = config_manager
        self._signals = signals
        self._data_dir = data_dir
        self._clipboard_service = clipboard_service
        self._browser_service = browser_service
        self._typing_engine = typing_engine
        self._screenshot_service = screenshot_service
        self._json_store = JsonStore()
        self._geometry_file = data_dir / "sessions" / "geometry.json"

        self._is_collapsed = False
        self._is_pinned = True
        self._expanded_height = 768
        self._hotkey_manager = WindowsGlobalHotkeyManager()
        self._hotkey_registered = False
        self._zorder_manager = ZOrderWatchdogManager()

        # Setup Debounced Geometry Save Timer
        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.setInterval(GEOMETRY_SAVE_DEBOUNCE_MS)
        self._geometry_timer.timeout.connect(self._save_geometry_now)

        # Frameless Window Flags (Tool window suppresses Windows Taskbar button)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # App icon — used in Alt+Tab switcher and tray fallback
        _icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / "app.png"
        if _icon_path.exists():
            from PySide6.QtGui import QPixmap

            self.setWindowIcon(QIcon(QPixmap(str(_icon_path))))

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

        browser_widget: QWidget
        if self._browser_service:
            browser_widget = BrowserPanel(
                self._browser_service,
                self._signals,
                parent=self.stack,
            )
        else:
            browser_widget = _PlaceholderWidget(PanelName.BROWSER, self.stack)

        typing_widget: QWidget
        if self._typing_engine:
            from src.ui.typing_panel import TypingPanel

            typing_widget = TypingPanel(
                self._typing_engine,
                self._signals,
                parent=self.stack,
            )
        else:
            typing_widget = _PlaceholderWidget(PanelName.TYPING, self.stack)

        self._panel_widgets: dict[str, QWidget] = {
            PanelName.BROWSER: browser_widget,
            PanelName.CLIPBOARD: clipboard_widget,
            PanelName.TYPING: typing_widget,
            PanelName.BOOKMARKS: _PlaceholderWidget(PanelName.BOOKMARKS, self.stack),
            PanelName.SETTINGS: SettingsPanel(self._config_manager, self.stack),
        }

        for _panel_name, widget in self._panel_widgets.items():
            self.stack.addWidget(widget)

        content_layout.addWidget(self.stack)
        root_layout.addWidget(self._content_widget, stretch=1)

        # 3. Overlay Visibility Panel
        self.overlay_visibility_panel = OverlayVisibilityPanel(central)
        root_layout.addWidget(self.overlay_visibility_panel)

        # 4. StatusBar
        self.status_bar = StatusBar(self._signals, central)
        root_layout.addWidget(self.status_bar)

        self.setCentralWidget(central)

        # 5. Toast Manager Overlay
        self.toast_manager = ToastManager(self)

        # 6. System Tray Icon Setup
        self._setup_tray_icon()

    def _connect_signals(self) -> None:
        # TitleBar signals
        self.title_bar.collapse_toggled.connect(self.set_collapsed)
        self.title_bar.screenshot_requested.connect(self.take_screenshot)

        # Overlay Visibility Panel signals
        self.overlay_visibility_panel.transparency_changed.connect(self._on_transparency_changed)

        # Sidebar signals
        self.sidebar.panel_selected.connect(self.switch_panel)

        # AppSignals
        self._signals.panel_changed.connect(self.switch_panel)
        self._signals.toast_requested.connect(self.toast_manager.show_toast)

        # Global Opacity Control Shortcuts (Ctrl+Q & Ctrl+W)
        self._shortcut_decrease_opacity = QShortcut(QKeySequence("Ctrl+Q"), self)
        self._shortcut_decrease_opacity.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut_decrease_opacity.activated.connect(self.decrease_opacity)

        self._shortcut_increase_opacity = QShortcut(QKeySequence("Ctrl+W"), self)
        self._shortcut_increase_opacity.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut_increase_opacity.activated.connect(self.increase_opacity)

        # Full-Screen Screenshot Shortcut (Ctrl+Shift+S)
        self._shortcut_screenshot = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._shortcut_screenshot.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut_screenshot.activated.connect(self.take_screenshot)

    def decrease_opacity(self) -> None:
        """Decrease window opacity by 5% step (increase UI transparency, max 99.99%)."""
        current_t = self.overlay_visibility_panel.get_transparency()
        new_t = round(min(99.99, current_t + 5.0), 2)
        self.overlay_visibility_panel.set_transparency(new_t)
        self._on_transparency_changed(new_t)

    def increase_opacity(self) -> None:
        """Increase window opacity by 5% step (decrease UI transparency, min 0%)."""
        current_t = self.overlay_visibility_panel.get_transparency()
        new_t = round(max(0.0, current_t - 5.0), 2)
        self.overlay_visibility_panel.set_transparency(new_t)
        self._on_transparency_changed(new_t)

    def take_screenshot(self) -> None:
        """Execute full-screen desktop screenshot with temporary window exclusion."""
        service = self._screenshot_service or ScreenshotService()

        was_visible = self.isVisible()
        if was_visible:
            self.hide()
            QApplication.processEvents()

        result = service.take_screenshot()

        if was_visible:
            self.show()
            self._apply_native_taskbar_suppression()
            self.activateWindow()

        if result.success and result.file_path:
            msg = f"Screenshot saved: {result.file_path.name}"
            self._signals.toast_requested.emit("info", msg)
            self._signals.status_message.emit(f"Screenshot saved to {result.file_path}")
        elif result.is_protected_content or result.status == CaptureStatus.PROTECTED_CONTENT:
            prot_app = result.protected_app_name or "Unknown application"
            safe_prot_app = prot_app[:40]
            toast_msg = (
                f"Screenshot unavailable\n"
                f"Protected application: {safe_prot_app}\n"
                f"Windows prevented this application from being captured."
            )
            self._signals.toast_requested.emit("warning", toast_msg)
            self._signals.status_message.emit(f"Protected application: {safe_prot_app}")
        elif result.status == CaptureStatus.CAPTURE_NOT_REPRESENTATIVE:
            err_msg = (
                result.error_message
                or "Screenshot unavailable: the requested content could not be "
                "accurately captured by Windows."
            )
            self._signals.toast_requested.emit("warning", err_msg)
            self._signals.status_message.emit("Screenshot unavailable: non-representative frame")
        else:
            err_msg = result.error_message or "Screenshot failed."
            self._signals.toast_requested.emit("warning", err_msg)
            self._signals.status_message.emit("Screenshot failed")

    def _on_transparency_changed(self, transparency_percent: float) -> None:
        """Handle transparency slider changes and apply Qt window opacity."""
        clamped_t = round(max(0.0, min(99.99, float(transparency_percent))), 2)
        opacity = 1.0 - (clamped_t / 100.0)
        self.set_window_opacity(opacity)
        self._config_manager.set("appearance.overlay_transparency", clamped_t)

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
        clamped = max(0.004, min(1.0, opacity))
        self.setWindowOpacity(clamped)
        t_val = round(max(0.0, min(99.99, (1.0 - opacity) * 100.0)), 2)
        if hasattr(self, "overlay_visibility_panel"):
            self.overlay_visibility_panel.set_transparency(t_val)
        self._schedule_geometry_save()

    def set_always_on_top(self, is_pinned: bool) -> None:
        """Toggle WindowStaysOnTopHint window flag and native Z-Order Watchdog."""
        self._is_pinned = is_pinned

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.show()  # Re-show required after window flags mutation on Windows
        self._apply_native_taskbar_suppression()

        hwnd = int(self.winId()) if self.winId() else 0
        if hwnd:
            self._zorder_manager.set_hwnd(hwnd)
            if is_pinned:
                self._zorder_manager.start_watchdog(hwnd)
            else:
                self._zorder_manager.stop_watchdog()

        self._schedule_geometry_save()

    def set_collapsed(self, is_collapsed: bool) -> None:
        """Toggle collapsed mode (showing title bar only vs full window)."""
        self._is_collapsed = is_collapsed
        self.title_bar.set_collapsed(is_collapsed)

        if is_collapsed:
            self._expanded_height = self.height()
            self._content_widget.hide()
            self.overlay_visibility_panel.hide()
            self.status_bar.hide()
            self.setFixedHeight(TITLE_BAR_HEIGHT)
        else:
            self.setFixedHeight(max(MIN_WINDOW_HEIGHT, self._expanded_height))
            self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            self.setMaximumSize(16777215, 16777215)
            self._content_widget.show()
            self.overlay_visibility_panel.show()
            self.status_bar.show()

        self._schedule_geometry_save()

    def _register_global_hotkeys(self) -> None:
        """Register Ctrl+Alt+E global hotkey for focus restoration."""
        hwnd = int(self.winId()) if self.winId() else 0
        if hwnd:
            self._hotkey_registered = self._hotkey_manager.register_hotkey(
                hwnd, HOTKEY_ID_CTRL_ALT_E, MOD_CONTROL | MOD_ALT, VK_E
            )

    def _unregister_global_hotkeys(self) -> None:
        """Unregister global hotkeys on window destruction."""
        if self._hotkey_registered:
            hwnd = int(self.winId()) if self.winId() else 0
            self._hotkey_manager.unregister_hotkey(hwnd, HOTKEY_ID_CTRL_ALT_E)
            self._hotkey_registered = False

    def _apply_native_taskbar_suppression(self) -> None:
        """Enforce native Win32 HWND extended style (WS_EX_TOOLWINDOW set)."""
        with contextlib.suppress(Exception):
            hwnd = int(self.winId()) if self.winId() else 0
            if hwnd and hasattr(ctypes, "windll"):
                user32 = getattr(ctypes.windll, "user32", None)
                if user32:
                    gwl_exstyle = -20
                    ws_ex_toolwindow = 0x00000080
                    ws_ex_appwindow = 0x00040000

                    get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
                    set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
                    get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
                    get_style.restype = ctypes.c_ssize_t
                    set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
                    set_style.restype = ctypes.c_ssize_t

                    hwnd_ptr = ctypes.c_void_p(hwnd)
                    old_style = get_style(hwnd_ptr, gwl_exstyle)
                    new_style = (old_style | ws_ex_toolwindow) & ~ws_ex_appwindow
                    if old_style != new_style:
                        set_style(hwnd_ptr, gwl_exstyle, new_style)

    def restore_and_focus(self) -> None:
        """Restore window from minimized state and force focus without altering transparency."""
        if self.isMinimized():
            self.showNormal()

        if self._is_collapsed:
            self.set_collapsed(False)

        self.show()
        self._apply_native_taskbar_suppression()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        # Native Win32 foreground activation if on Windows
        with contextlib.suppress(Exception):
            hwnd = int(self.winId()) if self.winId() else 0
            if hwnd:
                user32 = getattr(ctypes.windll, "user32", None)
                if user32:
                    user32.ShowWindow(ctypes.c_void_p(hwnd), 9)  # SW_RESTORE = 9
                    user32.SetForegroundWindow(ctypes.c_void_p(hwnd))

    def nativeEvent(self, event_type: Any, message: Any) -> tuple[bool, int]:
        """Intercept native Windows WM_HOTKEY events for Ctrl+Alt+E."""
        if message:
            with contextlib.suppress(Exception):
                msg_ptr = int(message)
                if msg_ptr:
                    msg = MSG.from_address(msg_ptr)
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID_CTRL_ALT_E:
                        self.restore_and_focus()
                        return True, 0
        result = super().nativeEvent(event_type, message)
        if isinstance(result, tuple) and len(result) == 2:
            return bool(result[0]), int(result[1])
        return False, 0

    def _setup_tray_icon(self) -> None:
        """Initialize QSystemTrayIcon and context menu for background/minimized execution."""
        from src.constants import APP_DISPLAY_NAME

        _icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / "app.png"
        if _icon_path.exists():
            from PySide6.QtGui import QPixmap

            tray_qicon = QIcon(QPixmap(str(_icon_path)))
        else:
            from src.ui.icons import IconManager

            tray_qicon = IconManager.get_icon("shield")

        self._tray_icon = QSystemTrayIcon(tray_qicon, self)
        self._tray_icon.setToolTip(APP_DISPLAY_NAME)

        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("Show BatmanOverlay")
        show_action.triggered.connect(self.restore_and_focus)

        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_icon_activated)
        self._tray_icon.show()

    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle system tray icon click and double-click actions."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_and_focus()

    def changeEvent(self, event: QEvent) -> None:
        """Intercept window minimize event to hide MainWindow to system tray."""
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            event.ignore()
            QTimer.singleShot(0, self._minimize_to_tray)
            return
        super().changeEvent(event)

    def _minimize_to_tray(self) -> None:
        """Hide window to system tray without quitting background process."""
        self.hide()
        self.setWindowState(Qt.WindowState.WindowNoState)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_native_taskbar_suppression()
        if not self._hotkey_registered:
            self._register_global_hotkeys()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle real application termination on Close (X) button."""
        self._zorder_manager.stop_watchdog()
        self._save_geometry_now()
        if hasattr(self, "_tray_icon") and self._tray_icon:
            self._tray_icon.hide()
        self._unregister_global_hotkeys()
        super().closeEvent(event)
        QApplication.quit()

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
        raw_t = float(self._config_manager.get("appearance.overlay_transparency", 0.0))
        saved_transparency = round(min(99.99, max(0.0, raw_t)), 2)

        if not self._geometry_file.exists():
            self.set_window_opacity(1.0 - (saved_transparency / 100.0))
            self.switch_panel(PanelName.SETTINGS)
            return

        try:
            raw = self._json_store.read(self._geometry_file)
            geo = WindowGeometry.model_validate(raw)

            self.move(geo.x, geo.y)
            self.resize(geo.width, geo.height)
            self._expanded_height = geo.height
            self.set_window_opacity(max(0.004, min(1.0, geo.opacity)))
            self.set_always_on_top(geo.is_pinned)

            if geo.is_collapsed:
                self.set_collapsed(True)

            self.switch_panel(geo.active_panel or PanelName.SETTINGS)
        except Exception:
            self.set_window_opacity(1.0 - (saved_transparency / 100.0))
            self.switch_panel(PanelName.SETTINGS)
