"""Application lifecycle and dependency injection container for batmanoverlay."""

import sys
import traceback
from pathlib import Path
from typing import Any

from loguru import logger
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.clipboard.monitor import ClipboardMonitor
from src.clipboard.service import ClipboardService
from src.constants import APP_NAME, APP_ORGANIZATION
from src.core.config_manager import ConfigManager
from src.core.events import AppSignals
from src.core.logger import setup_logging
from src.core.notification_manager import NotificationManager
from src.core.theme_manager import ThemeManager
from src.storage.clipboard_repository import ClipboardRepository
from src.storage.sqlite_store import SQLiteStore
from src.ui.dialogs import ErrorDialog
from src.ui.main_window import MainWindow
from src.ui.splash_screen import SplashScreen


def get_portable_data_dir() -> Path:
    """Determine the portable data directory relative to executable or root."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent

    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class BatmanOverlayApp(QApplication):
    """Main Application instance managing boot, lifecycle, theme, and shutdown."""

    def __init__(self, argv: list[str]) -> None:
        if QApplication.instance() is None:
            super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setOrganizationName(APP_ORGANIZATION)

        self.data_dir = get_portable_data_dir()
        self.config_manager: ConfigManager | None = None
        self.theme_manager: ThemeManager | None = None
        self.notification_manager: NotificationManager | None = None
        self.signals: AppSignals | None = None
        self.main_window: MainWindow | None = None
        self.splash_screen: SplashScreen | None = None

        self._setup_exception_hook()

    def _setup_exception_hook(self) -> None:
        """Install global exception hook for uncaught exceptions."""

        def global_excepthook(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_tb: Any,
        ) -> None:
            error_msg = str(exc_value) or "An unhandled exception occurred."
            error_code = getattr(exc_value, "error_code", "E000")
            user_msg = getattr(exc_value, "user_message", error_msg)
            tb_details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

            logger.critical(
                f"Unhandled Exception [{error_code}]: {exc_type.__name__}: {error_msg}\n"
                f"{tb_details}"
            )

            if self.main_window and self.main_window.isVisible():
                dlg = ErrorDialog(
                    title="Application Error",
                    error_code=error_code,
                    user_message=user_msg,
                    details=tb_details,
                    parent=self.main_window,
                )
                dlg.exec()

            sys.__excepthook__(exc_type, exc_value, exc_tb)

        sys.excepthook = global_excepthook

    def boot(self, debug: bool = False) -> None:
        """Execute application boot sequence."""
        # 1. Logger
        setup_logging(self.data_dir, debug=debug)
        logger.info("Booting batmanoverlay application shell...")

        # 2. ConfigManager
        self.config_manager = ConfigManager(self.data_dir)

        # 2.5 Global Display Affinity Security Filter
        from src.platform.security import DisplayAffinityEventFilter

        self.affinity_event_filter = DisplayAffinityEventFilter(self.config_manager, self)
        self.installEventFilter(self.affinity_event_filter)

        # 3. Signals & Notifications
        self.signals = AppSignals()
        self.notification_manager = NotificationManager(self.signals)

        # 4. ThemeManager
        self.theme_manager = ThemeManager(self, self.config_manager, self.signals)
        self.theme_manager.apply_theme()

        # 5. Clipboard Engine Container
        self.sqlite_store = SQLiteStore(self.data_dir / "sessions" / "clipboard.db")
        self.clipboard_repository = ClipboardRepository(self.sqlite_store)
        self.clipboard_monitor = ClipboardMonitor(self)
        self.clipboard_service = ClipboardService(
            repository=self.clipboard_repository,
            signals=self.signals,
            config_manager=self.config_manager,
            monitor=self.clipboard_monitor,
            parent=self,
        )

        # 5.5 Browser Engine Container
        from src.browser.profile_manager import BrowserProfileManager
        from src.browser.service import BrowserService
        from src.browser.session_manager import BrowserSessionManager

        self.browser_profile_manager = BrowserProfileManager(self.data_dir)
        self.browser_session_manager = BrowserSessionManager(self.browser_profile_manager)
        self.browser_service = BrowserService(
            profile_manager=self.browser_profile_manager,
            session_manager=self.browser_session_manager,
        )

        # 5.6 Typing Engine Container
        from src.typing.engine import HumanTypingEngine

        self.typing_engine = HumanTypingEngine(parent=self)

        # 6. Splash Screen
        self.splash_screen = SplashScreen()
        self.splash_screen.show()
        self.processEvents()

        # 7. Main Window Construction
        self.main_window = MainWindow(
            self.config_manager,
            self.signals,
            self.data_dir,
            clipboard_service=self.clipboard_service,
            browser_service=self.browser_service,
            typing_engine=self.typing_engine,
        )

        # 8. Schedule Splash Transition
        QTimer.singleShot(600, self._finish_boot)

    def _finish_boot(self) -> None:
        """Finalize boot transition from splash to main window."""
        if self.main_window:
            if self.splash_screen:
                self.splash_screen.finish(self.main_window)
            self.main_window.show()
        logger.info("Application shell booted successfully.")

    def shutdown(self) -> None:
        """Perform graceful application shutdown."""
        logger.info("Shutting down batmanoverlay application shell...")
        if hasattr(self, "browser_service") and self.browser_service:
            self.browser_service.flush_cookies()
        if self.main_window:
            self.main_window._save_geometry_now()
            self.main_window.hide()
        logger.info("Graceful shutdown completed.")
