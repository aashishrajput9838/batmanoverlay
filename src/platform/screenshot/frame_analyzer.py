"""Representative capture frame validation engine."""

from PySide6.QtGui import QImage, QPixmap

from src.platform.screenshot.window_detector import WindowInfo


class FrameAnalyzer:
    """Analyzes captured screenshot pixmap to ensure it represents visible desktop UI."""

    @classmethod
    def analyze_frame(
        cls, pixmap: QPixmap | None, visible_windows: list[WindowInfo]
    ) -> tuple[bool, str]:
        """Verify captured frame pixel contents against visible desktop windows.

        Returns:
            Tuple of (is_representative: bool, reason: str).
        """
        if pixmap is None or pixmap.isNull():
            return False, "Null pixmap frame"

        width, height = pixmap.width(), pixmap.height()
        if width <= 0 or height <= 0:
            return False, f"Invalid dimensions {width}x{height}"

        # If no top-level application windows are open, desktop wallpaper is valid
        if not visible_windows:
            return True, "Desktop capture validated (no top-level apps present)"

        qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)

        # Fast sample grid analysis (step size across width and height)
        step_x = max(1, width // 50)
        step_y = max(1, height // 50)

        sampled_colors: set[tuple[int, int, int]] = set()
        total_samples = 0
        sum_r, sum_g, sum_b = 0, 0, 0

        for y in range(0, height, step_y):
            for x in range(0, width, step_x):
                pixel = qimg.pixelColor(x, y)
                rgb = (pixel.red(), pixel.green(), pixel.blue())
                sampled_colors.add(rgb)
                sum_r += rgb[0]
                sum_g += rgb[1]
                sum_b += rgb[2]
                total_samples += 1

        if total_samples <= 0:
            return False, "Zero sample pixels"

        unique_ratio = len(sampled_colors) / total_samples

        # Compute RGB standard deviation / variance
        avg_r = sum_r / total_samples
        avg_g = sum_g / total_samples
        avg_b = sum_b / total_samples

        var_sum = 0.0
        for rgb in sampled_colors:
            var_sum += (rgb[0] - avg_r) ** 2 + (rgb[1] - avg_g) ** 2 + (rgb[2] - avg_b) ** 2
        std_dev = (var_sum / len(sampled_colors)) ** 0.5 if sampled_colors else 0.0

        # Non-representative rule: visible apps present but extremely low pixel variance
        if len(visible_windows) >= 1 and unique_ratio < 0.02 and std_dev < 10.0:
            app_names = [w.app_name for w in visible_windows]
            msg = (
                f"Frame is non-representative: captured uniform background pixels "
                f"({len(visible_windows)} visible apps present: {app_names})"
            )
            return False, msg

        return True, "Frame validated as representative desktop capture"
