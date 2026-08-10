"""Domain service managing full-screen capture, detection, and application-aware persistence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from src.platform.screenshot.backend_interface import CaptureStatus
from src.platform.screenshot.frame_analyzer import FrameAnalyzer
from src.platform.screenshot.window_detector import WindowDetector, WindowInfo
from src.platform.screenshot.windows_capture import WindowsCapture


@dataclass
class ScreenshotResult:
    """Structured response container for screenshot operations."""

    status: CaptureStatus
    success: bool
    file_path: Path | None = None
    backend_used: str | None = None
    error_message: str | None = None
    is_protected_content: bool = False
    detected_apps: list[str] | None = None
    protected_app_name: str | None = None
    protected_hwnd: int | None = None
    protected_pid: int | None = None
    protected_process_name: str | None = None


class ScreenshotService:
    """High-level service orchestrating desktop capture, validation, and output."""

    @staticmethod
    def get_default_screenshots_dir() -> Path:
        """Return the default Pictures/BatmanOverlay/Screenshots directory path."""
        return Path.home() / "Pictures" / "BatmanOverlay" / "Screenshots"

    @classmethod
    def generate_filename(
        cls,
        base_dir: Path,
        visible_windows: list[WindowInfo] | None = None,
        timestamp: datetime | None = None,
    ) -> Path:
        """Generate unique application-aware PNG path with incrementing collision suffix."""
        dt = timestamp or datetime.now(UTC).astimezone()
        time_str = dt.strftime("%Y-%m-%d_%H-%M-%S")

        prefix = WindowDetector.build_screenshot_filename_prefix(visible_windows or [])
        base_name = f"BatmanOverlay_{prefix}_{time_str}"

        candidate = base_dir / f"{base_name}.png"
        if not candidate.exists():
            return candidate

        counter = 1
        while True:
            candidate = base_dir / f"{base_name}_{counter}.png"
            if not candidate.exists():
                return candidate
            counter += 1

    @classmethod
    def _create_protected_content_result(
        cls,
        visible_windows: list[WindowInfo],
        backend_used: str | None = None,
    ) -> ScreenshotResult:
        """Construct ScreenshotResult for protected content with diagnostic capture trace."""
        prot_win = WindowDetector.find_responsible_protected_window(visible_windows)

        app_name = prot_win.app_name if prot_win else "Unknown application"
        hwnd = prot_win.hwnd if prot_win else None
        pid = prot_win.process_id if prot_win else None
        proc_name = prot_win.process_name if prot_win else None
        title = prot_win.title if prot_win else "Unknown"

        logger.warning(
            f"\n[CAPTURE TRACE]\n"
            f"Status: PROTECTED_CONTENT\n"
            f"Responsible application: {app_name}\n"
            f"Window handle: {f'{hwnd:#x}' if hwnd else 'None'}\n"
            f"Process ID: {pid if pid else 'Unknown'}\n"
            f"Process name: {proc_name if proc_name else 'Unknown'}\n"
            f"Window title: {title}\n"
            f"Persistence: BLOCKED\n"
        )

        msg = (
            "Screenshot unavailable\n"
            f"Protected application: {app_name}\n"
            "Windows prevented this application from being captured."
        )

        return ScreenshotResult(
            status=CaptureStatus.PROTECTED_CONTENT,
            success=False,
            backend_used=backend_used,
            error_message=msg,
            is_protected_content=True,
            detected_apps=[w.app_name for w in visible_windows],
            protected_app_name=app_name,
            protected_hwnd=hwnd,
            protected_pid=pid,
            protected_process_name=proc_name,
        )

    def take_screenshot(self, output_dir: Path | None = None) -> ScreenshotResult:
        """Capture virtual desktop with application-aware filename generation and validation."""
        try:
            target_dir = output_dir or self.get_default_screenshots_dir()

            # 1. Enumerate visible top-level windows
            visible_windows = WindowDetector.get_visible_windows()
            detected_app_names = [w.app_name for w in visible_windows]

            # Priority 1: Check for protected/secure application windows (e.g. CodeTantra)
            protected_apps = [w for w in visible_windows if w.is_protected]
            if protected_apps:
                return self._create_protected_content_result(visible_windows)

            # 2. Execute tiered desktop capture
            status, pixmap, backend_used = WindowsCapture.capture_full_desktop()

            # Priority 2: Check for backend protection signals
            if status == CaptureStatus.PROTECTED_CONTENT:
                return self._create_protected_content_result(visible_windows, backend_used)

            # Priority 3: Check for non-representative frame signals
            if status == CaptureStatus.CAPTURE_NOT_REPRESENTATIVE:
                logger.warning(
                    f"Screenshot capture halted: CAPTURE_NOT_REPRESENTATIVE ({backend_used})."
                )
                return ScreenshotResult(
                    status=CaptureStatus.CAPTURE_NOT_REPRESENTATIVE,
                    success=False,
                    backend_used=backend_used,
                    error_message="Screenshot unavailable: non-representative capture frame.",
                    detected_apps=detected_app_names,
                )

            if status != CaptureStatus.SUCCESS or pixmap is None or pixmap.isNull():
                logger.warning(
                    f"Desktop capture unavailable (status={status}, backend={backend_used})."
                )
                return ScreenshotResult(
                    status=CaptureStatus.CAPTURE_UNAVAILABLE,
                    success=False,
                    backend_used=backend_used,
                    error_message="Screenshot capture unavailable.",
                    detected_apps=detected_app_names,
                )

            # 3. Representative capture analysis
            is_rep, rep_reason = FrameAnalyzer.analyze_frame(pixmap, visible_windows)
            if not is_rep:
                logger.warning(f"Frame validation failed: {rep_reason}")
                return ScreenshotResult(
                    status=CaptureStatus.CAPTURE_NOT_REPRESENTATIVE,
                    success=False,
                    backend_used=backend_used,
                    error_message="Screenshot unavailable: non-representative capture frame.",
                    detected_apps=detected_app_names,
                )

            # 4. Generate application-aware filename and save PNG
            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.generate_filename(target_dir, visible_windows)

            saved = pixmap.save(str(file_path), "PNG")
            if not saved:
                logger.error(f"Failed to save pixmap to file: {file_path}")
                return ScreenshotResult(
                    status=CaptureStatus.CAPTURE_ERROR,
                    success=False,
                    backend_used=backend_used,
                    error_message="Failed to save screenshot image file.",
                    detected_apps=detected_app_names,
                )

            logger.info(
                f"Screenshot successfully captured via {backend_used} and saved to: {file_path}"
            )
            return ScreenshotResult(
                status=CaptureStatus.SUCCESS,
                success=True,
                file_path=file_path,
                backend_used=backend_used,
                detected_apps=detected_app_names,
            )
        except Exception as err:
            logger.error(f"ScreenshotService.take_screenshot error: {err}")
            return ScreenshotResult(
                status=CaptureStatus.CAPTURE_ERROR,
                success=False,
                error_message=f"Screenshot failed: {err}",
            )
