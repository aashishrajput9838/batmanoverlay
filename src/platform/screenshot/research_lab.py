"""SAFE Windows Screenshot Capture Research Lab.

Implements controlled test window using official Microsoft APIs (SetWindowDisplayAffinity).
STRICT SECURITY & ETHICAL BOUNDARY: This is strictly for learning and security research on
our OWN test windows. Does NOT modify, bypass, hook, or inject into any third-party software.
"""

import ctypes
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

# Microsoft Windows Documented Display Affinity Constants
WDA_NONE: int = 0x00000000
WDA_MONITOR: int = 0x00000001
WDA_EXCLUDEFROMCAPTURE: int = 0x00000011


class FrameCategory(Enum):
    """Classification of captured screenshot frame content."""

    ACTUAL_WINDOW_PIXELS = "ACTUAL_WINDOW_PIXELS"
    MASKED_PIXELS = "MASKED_PIXELS"
    BACKGROUND_PIXELS = "BACKGROUND_PIXELS"
    UNIFORM_FRAME = "UNIFORM_FRAME"
    NO_FRAME = "NO_FRAME"
    CAPTURE_ERROR = "CAPTURE_ERROR"


@dataclass
class FrameAnalysisReport:
    """Detailed pixel-level analysis report for a captured screenshot frame."""

    width: int = 0
    height: int = 0
    total_pixels: int = 0
    unique_colors: int = 0
    std_dev: float = 0.0
    avg_rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)
    edge_density: float = 0.0
    color_percentages: dict[str, float] = field(default_factory=dict)
    category: FrameCategory = FrameCategory.NO_FRAME
    summary_msg: str = "No frame provided"


class PixelAnalyzer:
    """Pixel-level color classifier and frame category evaluation engine."""

    TARGET_COLORS: ClassVar[dict[str, tuple[int, int, int]]] = {
        "RED": (255, 0, 0),
        "GREEN": (0, 255, 0),
        "BLUE": (0, 0, 255),
        "YELLOW": (255, 255, 0),
        "MAGENTA": (255, 0, 255),
        "CYAN": (0, 255, 255),
    }

    @classmethod
    def analyze_frame(cls, pixmap: QPixmap | None) -> FrameAnalysisReport:
        """Sample pixmap and evaluate test color presence and frame category."""
        if pixmap is None or pixmap.isNull():
            return FrameAnalysisReport(
                category=FrameCategory.NO_FRAME, summary_msg="Pixmap is null or zero size"
            )

        w, h = pixmap.width(), pixmap.height()
        if w <= 0 or h <= 0:
            return FrameAnalysisReport(
                category=FrameCategory.NO_FRAME, summary_msg=f"Invalid dimensions: {w}x{h}"
            )

        qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)
        step_x, step_y = max(1, w // 80), max(1, h // 80)

        sampled_colors: set[tuple[int, int, int]] = set()
        color_counts: dict[str, int] = dict.fromkeys(cls.TARGET_COLORS, 0)
        sum_r, sum_g, sum_b, total_samples = 0, 0, 0, 0

        for y in range(0, h, step_y):
            for x in range(0, w, step_x):
                px = qimg.pixelColor(x, y)
                r, g, b = px.red(), px.green(), px.blue()
                sampled_colors.add((r, g, b))
                sum_r += r
                sum_g += g
                sum_b += b
                total_samples += 1

                for name, (tr, tg, tb) in cls.TARGET_COLORS.items():
                    if abs(r - tr) <= 30 and abs(g - tg) <= 30 and abs(b - tb) <= 30:
                        color_counts[name] += 1

        if total_samples == 0:
            return FrameAnalysisReport(
                width=w, height=h, category=FrameCategory.NO_FRAME, summary_msg="Zero samples"
            )

        avg_r, avg_g, avg_b = (
            sum_r / total_samples,
            sum_g / total_samples,
            sum_b / total_samples,
        )
        var_sum = sum(
            (c[0] - avg_r) ** 2 + (c[1] - avg_g) ** 2 + (c[2] - avg_b) ** 2 for c in sampled_colors
        )
        std_dev = (var_sum / len(sampled_colors)) ** 0.5 if sampled_colors else 0.0
        percentages = {
            name: (count / total_samples) * 100.0 for name, count in color_counts.items()
        }
        match_ratio = sum(percentages.values())

        cat, msg = cls._classify_category(
            len(sampled_colors), avg_r, avg_g, avg_b, std_dev, match_ratio
        )
        return FrameAnalysisReport(
            width=w,
            height=h,
            total_pixels=w * h,
            unique_colors=len(sampled_colors),
            std_dev=round(std_dev, 2),
            avg_rgb=(round(avg_r, 1), round(avg_g, 1), round(avg_b, 1)),
            edge_density=round(len(sampled_colors) / (w * h) * 1000, 3),
            color_percentages={k: round(v, 2) for k, v in percentages.items()},
            category=cat,
            summary_msg=msg,
        )

    @staticmethod
    def _classify_category(
        color_count: int,
        avg_r: float,
        avg_g: float,
        avg_b: float,
        std_dev: float,
        match_ratio: float,
    ) -> tuple[FrameCategory, str]:
        """Determine FrameCategory based on color count, averages, and test block match."""
        if color_count <= 2:
            if avg_r < 20 and avg_g < 20 and avg_b < 20:
                return (
                    FrameCategory.MASKED_PIXELS,
                    "Masked black pixels rendered by DWM capture exclusion",
                )
            return (
                FrameCategory.UNIFORM_FRAME,
                f"Uniform single-color frame (avg RGB: {avg_r:.1f},{avg_g:.1f},{avg_b:.1f})",
            )
        if match_ratio >= 1.5:
            return (
                FrameCategory.ACTUAL_WINDOW_PIXELS,
                f"Actual ResearchTestWindow pixels detected ({match_ratio:.1f}% test block match)",
            )
        bg_msg = f"Background desktop pixels (std dev: {std_dev:.1f})"
        return FrameCategory.BACKGROUND_PIXELS, bg_msg


class ResearchTestWindow(QWidget):
    """Controlled research test window for evaluating Windows capture-exclusion APIs."""

    AFFINITY_NAMES: ClassVar[dict[int, str]] = {
        WDA_NONE: "WDA_NONE (0x00 - Fully Capturable)",
        WDA_MONITOR: "WDA_MONITOR (0x01 - Legacy Display Affinity)",
        WDA_EXCLUDEFROMCAPTURE: "WDA_EXCLUDEFROMCAPTURE (0x11 - Capture Excluded)",
    }

    def __init__(self, title: str = "Research Test Window - Capture Exclusion Lab") -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.resize(750, 480)
        self.setMinimumSize(640, 400)

        self._current_affinity: int = WDA_NONE
        self._init_ui()
        self.show()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("BATMANOVERLAY RESEARCH LAB — WINDOWS CAPTURE EXCLUSION TEST")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header.setStyleSheet(
            "color: #FFFFFF; background-color: #1E1E1E; padding: 10px; border-radius: 4px;"
        )
        layout.addWidget(header)

        blocks_layout = QHBoxLayout()
        blocks_def = [
            ("RED", "#FF0000", "white"),
            ("GREEN", "#00FF00", "black"),
            ("BLUE", "#0000FF", "white"),
            ("YELLOW", "#FFFF00", "black"),
            ("MAGENTA", "#FF00FF", "white"),
            ("CYAN", "#00FFFF", "black"),
        ]

        for label_text, bg_color, text_color in blocks_def:
            block = QLabel(f"{label_text}\nBLOCK")
            block.setAlignment(Qt.AlignmentFlag.AlignCenter)
            block.setStyleSheet(
                f"background-color: {bg_color}; color: {text_color}; "
                "font-weight: bold; padding: 10px;"
            )
            blocks_layout.addWidget(block)

        layout.addLayout(blocks_layout)

        self._info_label = QLabel()
        self._info_label.setFont(QFont("Consolas", 10))
        self._info_label.setStyleSheet(
            "background-color: #2D2D2D; color: #00FF66; padding: 10px; border-radius: 4px;"
        )
        layout.addWidget(self._info_label)

        controls_layout = QHBoxLayout()
        btn_none = QPushButton("Set WDA_NONE (0x00)")
        btn_none.clicked.connect(lambda: self.set_display_affinity(WDA_NONE))

        btn_exclude = QPushButton("Set WDA_EXCLUDEFROMCAPTURE (0x11)")
        btn_exclude.clicked.connect(lambda: self.set_display_affinity(WDA_EXCLUDEFROMCAPTURE))

        controls_layout.addWidget(btn_none)
        controls_layout.addWidget(btn_exclude)
        layout.addLayout(controls_layout)

        self.update_info_display()

    def set_display_affinity(self, affinity_flag: int) -> bool:
        """Apply Windows SetWindowDisplayAffinity API to this window handle."""
        if sys.platform != "win32":
            logger.warning("SetWindowDisplayAffinity is Windows-only.")
            return False

        hwnd = int(self.winId())
        if not hwnd:
            logger.error("Invalid window handle for display affinity.")
            return False

        try:
            user32 = getattr(ctypes.windll, "user32", None)
            if not user32 or not hasattr(user32, "SetWindowDisplayAffinity"):
                logger.error("SetWindowDisplayAffinity API unavailable.")
                return False

            success = bool(user32.SetWindowDisplayAffinity(hwnd, affinity_flag))
            if success:
                self._current_affinity = affinity_flag
                logger.info(
                    f"SetWindowDisplayAffinity(HWND={hwnd:#x}, "
                    f"Affinity={affinity_flag:#x}) -> SUCCESS"
                )
            else:
                last_err = getattr(ctypes.windll.kernel32, "GetLastError", lambda: 0)()
                logger.error(
                    f"SetWindowDisplayAffinity(HWND={hwnd:#x}, "
                    f"Affinity={affinity_flag:#x}) -> FAILED (Win32 Error: {last_err})"
                )

            self.update_info_display()
            return success
        except Exception as err:
            logger.error(f"set_display_affinity exception: {err}")
            return False

    def get_display_affinity(self) -> int:
        """Query current display affinity via Windows GetWindowDisplayAffinity API."""
        if sys.platform != "win32":
            return self._current_affinity

        hwnd = int(self.winId())
        if not hwnd:
            return self._current_affinity

        try:
            user32 = getattr(ctypes.windll, "user32", None)
            if user32 and hasattr(user32, "GetWindowDisplayAffinity"):
                aff = ctypes.c_uint32(0)
                if user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(aff)):
                    self._current_affinity = aff.value
                    return aff.value
        except Exception as err:
            logger.debug(f"GetWindowDisplayAffinity exception: {err}")

        return self._current_affinity

    def update_info_display(self) -> None:
        """Refresh window identity and display affinity details label."""
        hwnd = int(self.winId())
        pid = os.getpid()
        aff_val = self.get_display_affinity()
        aff_str = self.AFFINITY_NAMES.get(aff_val, f"Custom (0x{aff_val:02X})")

        info_text = (
            f"HWND: {hwnd:#x} ({hwnd})\n"
            f"PID:  {pid}\n"
            f"Process: {sys.executable}\n"
            f"Display Affinity: {aff_str}"
        )
        self._info_label.setText(info_text)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint custom visual identification background."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#121212"))
        painter.end()
