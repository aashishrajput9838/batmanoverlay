"""Left panel navigation sidebar for batmanoverlay."""

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from src.constants import SIDEBAR_COLLAPSED_WIDTH, PanelName
from src.ui.icons import IconManager


class SidebarButton(QToolButton):
    """Custom sidebar button with active state styling."""

    def __init__(self, panel_name: str, label: str, icon_name: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarButton")
        self.panel_name = panel_name
        self.setIcon(IconManager.get_icon(icon_name))
        self.setIconSize(QSize(20, 20))
        self.setText(label)
        self.setToolTip(f"{label} Panel")
        self.setAccessibleName(f"Navigate to {label}")
        self.setMinimumSize(40, 40)
        self.setCheckable(True)


class Sidebar(QWidget):
    """Left navigation sidebar."""

    panel_selected = Signal(str)  # panel_name

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)
        self._buttons: dict[str, SidebarButton] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(8)

        items = [
            (PanelName.BROWSER, "Browser", "browser"),
            (PanelName.CLIPBOARD, "Clipboard", "clipboard"),
            (PanelName.TYPING, "Typing", "typing"),
            (PanelName.BOOKMARKS, "Bookmarks", "bookmarks"),
            (PanelName.SETTINGS, "Settings", "settings"),
        ]

        for panel_name, label, icon_name in items:
            btn = SidebarButton(panel_name, label, icon_name, self)
            btn.clicked.connect(lambda _, name=panel_name: self._on_button_clicked(name))
            layout.addWidget(btn)
            self._buttons[panel_name] = btn

        layout.addStretch()

    def _on_button_clicked(self, panel_name: str) -> None:
        self.set_active_panel(panel_name)
        self.panel_selected.emit(panel_name)

    def set_active_panel(self, panel_name: str) -> None:
        """Update active button state."""
        for name, btn in self._buttons.items():
            is_active = name == panel_name
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
