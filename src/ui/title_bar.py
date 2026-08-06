"""Custom title bar for frameless overlay window."""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QSlider,
    QToolButton,
    QWidget,
)

from src.constants import APP_DISPLAY_NAME, TITLE_BAR_HEIGHT, PanelName
from src.ui.icons import IconManager


class TitleBar(QWidget):
    """Custom title bar widget providing window controls, overlay toggles, and dragging."""

    collapse_toggled = Signal(bool)  # is_collapsed
    pin_toggled = Signal(bool)  # is_pinned
    opacity_changed = Signal(float)  # opacity (0.1 to 1.0)
    panel_requested = Signal(str)  # panel_name
    search_requested = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(TITLE_BAR_HEIGHT)

        self._drag_position = QPoint()
        self._is_collapsed = False
        self._is_pinned = True
        self._opacity = 1.0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(4)

        # App Icon & Title
        self._title_label = QLabel(APP_DISPLAY_NAME, self)
        layout.addWidget(self._title_label)

        layout.addStretch()

        # Search Button
        self._btn_search = QToolButton(self)
        self._btn_search.setIcon(IconManager.get_icon("search"))
        self._btn_search.setToolTip("Global Search (Ctrl+Shift+F)")
        self._btn_search.clicked.connect(self.search_requested.emit)
        layout.addWidget(self._btn_search)

        # Opacity Control Button + Popup Menu
        self._btn_opacity = QToolButton(self)
        self._btn_opacity.setIcon(IconManager.get_icon("settings"))
        self._btn_opacity.setToolTip("Window Opacity")
        self._setup_opacity_menu()
        layout.addWidget(self._btn_opacity)

        # Pin / Always-On-Top Toggle
        self._btn_pin = QToolButton(self)
        self._btn_pin.setIcon(IconManager.get_icon("pin_filled"))
        self._btn_pin.setToolTip("Toggle Always-On-Top")
        self._btn_pin.setCheckable(True)
        self._btn_pin.setChecked(True)
        self._btn_pin.clicked.connect(self._toggle_pin)
        layout.addWidget(self._btn_pin)

        # Collapse / Expand Toggle
        self._btn_collapse = QToolButton(self)
        self._btn_collapse.setIcon(IconManager.get_icon("collapse"))
        self._btn_collapse.setToolTip("Collapse / Expand Overlay")
        self._btn_collapse.clicked.connect(self._toggle_collapse)
        layout.addWidget(self._btn_collapse)

        # Settings Panel Button
        self._btn_settings = QToolButton(self)
        self._btn_settings.setIcon(IconManager.get_icon("settings"))
        self._btn_settings.setToolTip("Settings")
        self._btn_settings.clicked.connect(lambda: self.panel_requested.emit(PanelName.SETTINGS))
        layout.addWidget(self._btn_settings)

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

    def _setup_opacity_menu(self) -> None:
        menu = QMenu(self)
        slider_widget = QWidget(menu)
        slider_layout = QHBoxLayout(slider_widget)
        slider_layout.setContentsMargins(12, 8, 12, 8)

        slider = QSlider(Qt.Orientation.Horizontal, slider_widget)
        slider.setRange(20, 100)
        slider.setValue(100)
        slider.setFixedWidth(120)
        slider.valueChanged.connect(self._on_slider_opacity_changed)

        slider_layout.addWidget(QLabel("Opacity:", slider_widget))
        slider_layout.addWidget(slider)

        menu.addAction("100% (Opaque)").triggered.connect(lambda: self._set_opacity(1.0))
        menu.addAction("80%").triggered.connect(lambda: self._set_opacity(0.8))
        menu.addAction("50% (Semi)").triggered.connect(lambda: self._set_opacity(0.5))

        self._btn_opacity.setMenu(menu)
        self._btn_opacity.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def _on_slider_opacity_changed(self, val: int) -> None:
        opacity = val / 100.0
        self._set_opacity(opacity)

    def _set_opacity(self, opacity: float) -> None:
        self._opacity = opacity
        self.opacity_changed.emit(opacity)

    def _toggle_pin(self) -> None:
        self._is_pinned = self._btn_pin.isChecked()
        icon_name = "pin_filled" if self._is_pinned else "pin"
        self._btn_pin.setIcon(IconManager.get_icon(icon_name))
        self.pin_toggled.emit(self._is_pinned)

    def _toggle_collapse(self) -> None:
        self._is_collapsed = not self._is_collapsed
        icon_name = "expand" if self._is_collapsed else "collapse"
        self._btn_collapse.setIcon(IconManager.get_icon(icon_name))
        self.collapse_toggled.emit(self._is_collapsed)

    def set_pinned(self, is_pinned: bool) -> None:
        self._is_pinned = is_pinned
        self._btn_pin.setChecked(is_pinned)
        icon_name = "pin_filled" if is_pinned else "pin"
        self._btn_pin.setIcon(IconManager.get_icon(icon_name))

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
