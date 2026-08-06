"""Presentation layer package for batmanoverlay."""

from src.ui.browser_panel import BrowserPanel
from src.ui.clipboard_card import ClipboardItemCard
from src.ui.clipboard_panel import ClipboardPanel
from src.ui.components.empty_state import EmptyStateWidget
from src.ui.dialogs import ConfirmDialog, ErrorDialog, RecoveryDialog
from src.ui.icons import IconManager
from src.ui.main_window import MainWindow
from src.ui.settings_panel import SettingsPanel
from src.ui.sidebar import Sidebar
from src.ui.splash_screen import SplashScreen
from src.ui.status_bar import StatusBar
from src.ui.title_bar import TitleBar
from src.ui.toast import ToastManager, ToastWidget

__all__ = [
    "BrowserPanel",
    "ClipboardItemCard",
    "ClipboardPanel",
    "ConfirmDialog",
    "EmptyStateWidget",
    "ErrorDialog",
    "IconManager",
    "MainWindow",
    "RecoveryDialog",
    "SettingsPanel",
    "Sidebar",
    "SplashScreen",
    "StatusBar",
    "TitleBar",
    "ToastManager",
    "ToastWidget",
]
