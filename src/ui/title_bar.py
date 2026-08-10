"""Custom title bar for frameless overlay window."""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QToolButton,
    QWidget,
)

from src.constants import APP_DISPLAY_NAME, TITLE_BAR_HEIGHT
from src.ui.icons import IconManager


class TitleBar(QWidget):
    """Custom title bar widget providing window controls and dragging."""

    collapse_toggled = Signal(bool)  # is_collapsed
    screenshot_requested = Signal()  # full-screen screenshot trigger

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(TITLE_BAR_HEIGHT)

        self._drag_position = QPoint()
        self._is_collapsed = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(4)

        # App Logo & Title
        from pathlib import Path

        _logo_path = Path(__file__).parent.parent.parent / "resources" / "icons" / "app.png"
        if _logo_path.exists():
            from PySide6.QtGui import QPixmap

            self._logo_label = QLabel(self)
            pix = QPixmap(str(_logo_path)).scaled(
                20,
                20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._logo_label.setPixmap(pix)
            layout.addWidget(self._logo_label)

        self._title_label = QLabel(APP_DISPLAY_NAME, self)
        layout.addWidget(self._title_label)

        layout.addStretch()

        # Screenshot Button (Positioned immediately to the LEFT of Collapse)
        self._btn_screenshot = QToolButton(self)
        self._btn_screenshot.setObjectName("ScreenshotButton")
        self._btn_screenshot.setIcon(IconManager.get_icon("screenshot"))
        self._btn_screenshot.setToolTip("Take Full-Screen Screenshot")
        self._btn_screenshot.clicked.connect(self.screenshot_requested.emit)
        layout.addWidget(self._btn_screenshot)

        # Collapse / Expand Toggle
        self._btn_collapse = QToolButton(self)
        self._btn_collapse.setIcon(IconManager.get_icon("collapse"))
        self._btn_collapse.setToolTip("Collapse / Expand Overlay")
        self._btn_collapse.clicked.connect(self._toggle_collapse)
        layout.addWidget(self._btn_collapse)

        # Minimize Button
        self._btn_minimize = QToolButton(self)
        self._btn_minimize.setIcon(IconManager.get_icon("minimize"))
        self._btn_minimize.setToolTip("Minimize")
        self._btn_minimize.clicked.connect(self.window().showMinimized)
        layout.addWidget(self._btn_minimize)

        # Close Button
        self._btn_close = QToolButton(self)
        self._btn_close.setObjectName("CloseButton")
        self._btn_close.setIcon(IconManager.get_icon("close"))
        self._btn_close.setToolTip("Close Application")
        self._btn_close.clicked.connect(self.window().close)
        layout.addWidget(self._btn_close)

    def _toggle_collapse(self) -> None:
        self._is_collapsed = not self._is_collapsed
        icon_name = "expand" if self._is_collapsed else "collapse"
        self._btn_collapse.setIcon(IconManager.get_icon(icon_name))
        self.collapse_toggled.emit(self._is_collapsed)

    def set_collapsed(self, is_collapsed: bool) -> None:
        self._is_collapsed = is_collapsed
        icon_name = "expand" if is_collapsed else "collapse"
        self._btn_collapse.setIcon(IconManager.get_icon(icon_name))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_position.isNull():
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
