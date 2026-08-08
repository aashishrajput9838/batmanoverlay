"""Overlay Visibility / Transparency Control Panel widget for batmanoverlay."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def _format_transparency_str(value: float) -> str:
    """Format transparency float into clean percentage string without trailing zeros."""
    rounded = round(value, 2)
    if rounded == int(rounded):
        return f"{int(rounded)}%"
    return f"{rounded:.2f}%"


class OverlayVisibilityPanel(QWidget):
    """Panel providing overlay transparency control slider, endpoint labels, and reset button."""

    # Emits transparency percentage as float (0.0 to 99.99)
    transparency_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("OverlayVisibilityPanel")
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 6, 16, 6)
        main_layout.setSpacing(4)

        # Header row: Title + Description on left; Value + Reset on right
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        title_label = QLabel("Overlay Visibility", self)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #CDD6F4;")

        desc_label = QLabel("Adjust the transparency of the overlay", self)
        desc_label.setStyleSheet("font-size: 11px; color: #A6ADC8;")

        shortcut_hint_label = QLabel(
            "Shortcuts: Ctrl+Q decrease opacity · Ctrl+W increase opacity · Ctrl+Alt+E focus",
            self,
        )
        shortcut_hint_label.setStyleSheet("font-size: 10px; color: #6C7086; font-style: italic;")

        title_box.addWidget(title_label)
        title_box.addWidget(desc_label)
        title_box.addWidget(shortcut_hint_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Current value label
        self._value_label = QLabel("0%", self)
        self._value_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #5B8DEF;")
        header_layout.addWidget(self._value_label)

        # Reset button
        self._reset_btn = QPushButton("Reset", self)
        self._reset_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._reset_btn.setToolTip("Reset transparency to 0% (Fully Visible)")
        self._reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475A;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #585B70;
            }
        """)
        self._reset_btn.clicked.connect(self.reset_transparency)
        header_layout.addWidget(self._reset_btn)

        main_layout.addLayout(header_layout)

        # Slider row with endpoint labels (0 to 9999 represents 0.00% to 99.99%)
        slider_row = QHBoxLayout()
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.setSpacing(10)

        left_endpoint = QLabel("0% (Fully Visible)", self)
        left_endpoint.setStyleSheet("font-size: 10px; color: #9399B2;")
        slider_row.addWidget(left_endpoint)

        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.setRange(0, 9999)
        self._slider.setValue(0)
        self._slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._slider.setToolTip("Overlay Transparency (0% = Opaque, 99.99% = Max Transparency)")
        self._slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #45475A;
                height: 6px;
                background: #1E1E2E;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #5B8DEF;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #89B4FA;
                border: 1px solid #5B8DEF;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #B4BEFE;
            }
        """)
        self._slider.valueChanged.connect(self._on_slider_value_changed)
        slider_row.addWidget(self._slider, stretch=1)

        right_endpoint = QLabel("99.99% (Max Transparency)", self)
        right_endpoint.setStyleSheet("font-size: 10px; color: #9399B2;")
        slider_row.addWidget(right_endpoint)

        main_layout.addLayout(slider_row)

        self.setStyleSheet("""
            #OverlayVisibilityPanel {
                background-color: #181825;
                border-top: 1px solid #313244;
                border-bottom: 1px solid #313244;
            }
        """)

    def _on_slider_value_changed(self, value: int) -> None:
        t_val = round(value / 100.0, 2)
        self._value_label.setText(_format_transparency_str(t_val))
        self.transparency_changed.emit(t_val)

    def get_transparency(self) -> float:
        """Return current transparency percentage float (0.0 to 99.99)."""
        return round(self._slider.value() / 100.0, 2)

    def set_transparency(self, value: float) -> None:
        """Set transparency percentage float (0.0 to 99.99) and update UI controls."""
        clamped = max(0.0, min(99.99, float(value)))
        slider_val = round(clamped * 100)
        self._slider.blockSignals(True)
        self._slider.setValue(slider_val)
        self._slider.blockSignals(False)
        self._value_label.setText(_format_transparency_str(clamped))

    def reset_transparency(self) -> None:
        """Reset transparency to 0% (Fully Visible)."""
        self.set_transparency(0.0)
        self.transparency_changed.emit(0.0)
