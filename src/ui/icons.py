"""High-DPI vector icon generator and resource loader for batmanoverlay."""

from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESOURCES_ICONS_DIR = ROOT_DIR / "resources" / "icons"


class IconManager:
    """Manages icon retrieval with resource fallback and vector rendering."""

    _cache: ClassVar[dict[str, QIcon]] = {}

    @classmethod
    def get_icon(cls, name: str, color: str = "#CDD6F4") -> QIcon:
        """Get or generate a QIcon by name."""
        cache_key = f"{name}_{color}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # 1. Try loading external SVG/PNG asset if present
        icon = cls._try_load_file_icon(name)
        if icon is None:
            # 2. Render crisp anti-aliased high-DPI vector icon
            icon = cls._create_vector_icon(name, color)

        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def _try_load_file_icon(cls, name: str) -> QIcon | None:
        """Attempt to load icon from SVG or PNG asset directory."""
        for ext in (".svg", ".png"):
            file_path = RESOURCES_ICONS_DIR / f"{name}{ext}"
            if file_path.exists() and file_path.is_file():
                icon = QIcon(str(file_path))
                if not icon.isNull():
                    return icon
        return None

    @classmethod
    def _create_vector_icon(cls, name: str, color_hex: str) -> QIcon:  # noqa: C901
        """Render high-DPI anti-aliased vector icon pixmap."""
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_color = QColor(color_hex)

        # Scale pen width for high DPI (48x48 canvas mapped to 24x24 coordinates)
        pen = painter.pen()
        pen.setColor(pen_color)
        pen.setWidthF(2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Use 48x48 scaling coordinates (scaled up 2x from 24x24 grid for crisp rendering)
        painter.scale(2.0, 2.0)

        match name:
            case "chevron_left":
                path = QPainterPath()
                path.moveTo(15, 5)
                path.lineTo(9, 12)
                path.lineTo(15, 19)
                painter.drawPath(path)

            case "chevron_right":
                path = QPainterPath()
                path.moveTo(9, 5)
                path.lineTo(15, 12)
                path.lineTo(9, 19)
                painter.drawPath(path)

            case "reload":
                rect_arc = QRectF(5, 5, 14, 14)
                painter.drawArc(rect_arc, 45 * 16, 270 * 16)
                arrow = QPainterPath()
                arrow.moveTo(13, 3)
                arrow.lineTo(19, 5)
                arrow.lineTo(16, 10)
                painter.drawPath(arrow)

            case "stop":
                painter.drawLine(7, 7, 17, 17)
                painter.drawLine(17, 7, 7, 17)

            case "shield" | "lock":
                path = QPainterPath()
                path.moveTo(12, 4)
                path.lineTo(19, 7)
                path.lineTo(19, 12)
                path.quadTo(19, 18, 12, 20)
                path.quadTo(5, 18, 5, 12)
                path.lineTo(5, 7)
                path.closeSubpath()
                painter.drawPath(path)

            case "home":
                path = QPainterPath()
                path.moveTo(4, 11)
                path.lineTo(12, 4)
                path.lineTo(20, 11)
                path.lineTo(18, 11)
                path.lineTo(18, 20)
                path.lineTo(6, 20)
                path.lineTo(6, 11)
                path.closeSubpath()
                painter.drawPath(path)

            case "close":
                painter.drawLine(6, 6, 18, 18)
                painter.drawLine(18, 6, 6, 18)

            case "minimize":
                painter.drawLine(5, 18, 19, 18)

            case "maximize":
                painter.drawRect(QRectF(5, 5, 14, 14))

            case "restore":
                painter.drawRect(QRectF(8, 5, 11, 11))
                painter.drawRect(QRectF(5, 8, 11, 11))

            case "pin":
                painter.drawEllipse(QPointF(12, 9), 4, 4)
                painter.drawLine(12, 13, 12, 19)
                painter.drawLine(8, 9, 16, 9)

            case "pin_filled":
                painter.setBrush(pen_color)
                painter.drawEllipse(QPointF(12, 9), 5, 5)
                painter.drawLine(12, 14, 12, 20)

            case "collapse":
                path = QPainterPath()
                path.moveTo(6, 15)
                path.lineTo(12, 9)
                path.lineTo(18, 15)
                painter.drawPath(path)

            case "expand":
                path = QPainterPath()
                path.moveTo(6, 9)
                path.lineTo(12, 15)
                path.lineTo(18, 9)
                painter.drawPath(path)

            case "settings":
                painter.drawEllipse(QPointF(12, 12), 4, 4)
                for _i in range(8):
                    painter.drawLine(12, 4, 12, 6)
                    painter.translate(12, 12)
                    painter.rotate(45)
                    painter.translate(-12, -12)

            case "browser":
                painter.drawEllipse(QPointF(12, 12), 8, 8)
                painter.drawLine(4, 12, 20, 12)
                painter.drawEllipse(QPointF(12, 12), 4, 8)

            case "clipboard":
                painter.drawRoundedRect(QRectF(6, 7, 12, 14), 2, 2)
                painter.drawRect(QRectF(9, 3, 6, 4))

            case "typing":
                painter.drawRoundedRect(QRectF(4, 7, 16, 10), 2, 2)
                painter.drawRect(QRectF(7, 13, 10, 2))

            case "bookmarks":
                path = QPainterPath()
                path.moveTo(6, 4)
                path.lineTo(18, 4)
                path.lineTo(18, 20)
                path.lineTo(12, 15)
                path.lineTo(6, 20)
                path.closeSubpath()
                painter.drawPath(path)

            case "search":
                painter.drawEllipse(QPointF(10, 10), 6, 6)
                painter.drawLine(14, 14, 19, 19)

            case "delete":
                painter.drawLine(6, 7, 18, 7)
                painter.drawLine(9, 5, 15, 5)
                painter.drawRoundedRect(QRectF(7, 8, 10, 11), 1, 1)
                painter.drawLine(10, 11, 10, 16)
                painter.drawLine(14, 11, 14, 16)

            case "copy":
                painter.drawRoundedRect(QRectF(8, 8, 11, 12), 2, 2)
                path = QPainterPath()
                path.moveTo(6, 16)
                path.lineTo(5, 16)
                path.lineTo(5, 5)
                path.lineTo(16, 5)
                path.lineTo(16, 6)
                painter.drawPath(path)

            case "star":
                path = QPainterPath()
                path.moveTo(12, 4)
                path.lineTo(14.5, 9.5)
                path.lineTo(20, 10)
                path.lineTo(16, 14)
                path.lineTo(17.5, 19.5)
                path.lineTo(12, 16.5)
                path.lineTo(6.5, 19.5)
                path.lineTo(8, 14)
                path.lineTo(4, 10)
                path.lineTo(9.5, 9.5)
                path.closeSubpath()
                painter.drawPath(path)

            case "star_filled":
                painter.setBrush(pen_color)
                path = QPainterPath()
                path.moveTo(12, 4)
                path.lineTo(14.5, 9.5)
                path.lineTo(20, 10)
                path.lineTo(16, 14)
                path.lineTo(17.5, 19.5)
                path.lineTo(12, 16.5)
                path.lineTo(6.5, 19.5)
                path.lineTo(8, 14)
                path.lineTo(4, 10)
                path.lineTo(9.5, 9.5)
                path.closeSubpath()
                painter.drawPath(path)

            case "info":
                painter.drawEllipse(QPointF(12, 12), 8, 8)
                painter.drawPoint(QPointF(12, 8))
                painter.drawLine(12, 11, 12, 16)

            case "warning":
                path = QPainterPath()
                path.moveTo(12, 4)
                path.lineTo(21, 19)
                path.lineTo(3, 19)
                path.closeSubpath()
                painter.drawPath(path)
                painter.drawPoint(QPointF(12, 16))
                painter.drawLine(12, 10, 12, 14)

            case "error":
                painter.drawEllipse(QPointF(12, 12), 8, 8)
                painter.drawLine(8, 8, 16, 16)
                painter.drawLine(16, 8, 8, 16)

            case _:
                # Generic fallback icon: circle dot
                painter.drawEllipse(QPointF(12, 12), 6, 6)

        painter.end()

        # Create QIcon with High DPI support and Disabled state opacity rendering
        icon = QIcon()
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)

        # Create semi-transparent pixmap for disabled state
        disabled_pixmap = QPixmap(pixmap.size())
        disabled_pixmap.fill(Qt.GlobalColor.transparent)
        dp_painter = QPainter(disabled_pixmap)
        dp_painter.setOpacity(0.35)
        dp_painter.drawPixmap(0, 0, pixmap)
        dp_painter.end()
        icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)

        return icon
