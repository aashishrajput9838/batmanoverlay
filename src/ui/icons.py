"""Icon loading and fallback vector icon generator for batmanoverlay."""

from typing import ClassVar

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap


class IconManager:
    """Manages icon retrieval with automatic vector fallback generation."""

    _cache: ClassVar[dict[str, QIcon]] = {}

    @classmethod
    def get_icon(cls, name: str, color: str = "#CDD6F4") -> QIcon:
        """Get or generate a QIcon by name."""
        cache_key = f"{name}_{color}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        icon = cls._create_vector_icon(name, color)
        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def _create_vector_icon(cls, name: str, color_hex: str) -> QIcon:  # noqa: C901
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_color = QColor(color_hex)
        painter.setPen(pen_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        rect = QRectF(3, 3, 18, 18)

        match name:
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
                painter.drawEllipse(QPointF(12, 12), 5, 5)
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
            case "info":
                painter.drawEllipse(QPointF(12, 12), 8, 8)
                painter.drawPoint(12, 8)
                painter.drawLine(12, 11, 12, 16)
            case "warning":
                path = QPainterPath()
                path.moveTo(12, 4)
                path.lineTo(21, 19)
                path.lineTo(3, 19)
                path.closeSubpath()
                painter.drawPath(path)
                painter.drawPoint(12, 16)
                painter.drawLine(12, 10, 12, 14)
            case "error":
                painter.drawEllipse(QPointF(12, 12), 8, 8)
                painter.drawLine(8, 8, 16, 16)
                painter.drawLine(16, 8, 8, 16)
            case _:
                painter.drawRect(rect)

        painter.end()
        return QIcon(pixmap)
