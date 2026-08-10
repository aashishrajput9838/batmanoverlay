"""Windows desktop capture engine supporting multi-monitor and virtual desktop topology."""

import ctypes
import time

from loguru import logger
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap

from src.platform.screenshot.backend_interface import CaptureStatus, RawFrameData
from src.platform.screenshot.dxgi_desktop_duplication import DXGIDesktopDuplicationBackend
from src.platform.screenshot.windows_graphics_capture import WindowsGraphicsCaptureBackend


class _BITMAPINFOHEADER(ctypes.Structure):
    """Win32 BITMAPINFOHEADER structure."""

    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class WindowsCapture:
    """Multi-tiered virtual desktop capture engine.

    Orchestrates capture backends in strict priority order:
    1. Tier 1: Windows Graphics Capture (WGC / D3D11)
    2. Tier 2: DXGI Desktop Duplication (D3D11 / DXGI 1.2+)
    3. Tier 3: Win32 BitBlt GDI Virtual Screen Capture
    4. Tier 4: Qt QScreen Composite Screen Grab
    """

    _wgc_backend = WindowsGraphicsCaptureBackend()
    _dxgi_backend = DXGIDesktopDuplicationBackend()

    @classmethod
    def get_foreground_window_diagnostics(cls) -> tuple[int, str, bool]:
        """Return diagnostic tuple: (hwnd, window_title, is_cloaked)."""
        if not hasattr(ctypes, "windll"):
            return 0, "", False

        user32 = getattr(ctypes.windll, "user32", None)
        dwmapi = getattr(ctypes.windll, "dwmapi", None)
        if not user32:
            return 0, "", False

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0, "", False

        title = ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            title_buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buf, length + 1)
            title = title_buf.value

        is_cloaked = False
        if dwmapi:
            cloaked = ctypes.c_uint32(0)
            hr = dwmapi.DwmGetWindowAttribute(
                hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            )
            if hr == 0 and cloaked.value != 0:
                is_cloaked = True

        return hwnd, title, is_cloaked

    @classmethod
    def capture_full_desktop(cls) -> tuple[CaptureStatus, QPixmap | None, str]:
        """Capture the visible Windows virtual desktop using tiered backends."""
        start_ts = time.monotonic()
        hwnd_fg, title_fg, cloaked_fg = cls.get_foreground_window_diagnostics()
        logger.debug(
            f"Capture start - Foreground HWND: {hwnd_fg:#x}, Title: '{title_fg}', "
            f"Cloaked: {cloaked_fg}"
        )

        wgc_res = cls._try_wgc()
        if wgc_res:
            logger.info(f"Capture outcome ({wgc_res[2]}): {wgc_res[0]}")
            return wgc_res

        dxgi_res = cls._try_dxgi()
        if dxgi_res:
            logger.info(f"Capture outcome ({dxgi_res[2]}): {dxgi_res[0]}")
            return dxgi_res

        bitblt_res = cls._try_bitblt()
        if bitblt_res:
            logger.info(f"Capture outcome ({bitblt_res[2]}): {bitblt_res[0]}")
            return bitblt_res

        qt_res = cls._try_qt()
        if qt_res:
            logger.info(f"Capture outcome ({qt_res[2]}): {qt_res[0]}")
            return qt_res

        duration = round(time.monotonic() - start_ts, 3)
        logger.warning(f"All capture tiers unavailable (duration: {duration}s)")
        return CaptureStatus.CAPTURE_UNAVAILABLE, None, "None"

    @classmethod
    def _try_wgc(cls) -> tuple[CaptureStatus, QPixmap | None, str] | None:
        try:
            status, raw_data, _ = cls._wgc_backend.capture_virtual_desktop()
            if status == CaptureStatus.SUCCESS and raw_data is not None:
                pixmap = cls._raw_frame_to_pixmap(raw_data)
                if pixmap and not pixmap.isNull() and pixmap.width() > 0:
                    return CaptureStatus.SUCCESS, pixmap, "WindowsGraphicsCapture"
            elif status in (
                CaptureStatus.PROTECTED_CONTENT,
                CaptureStatus.CAPTURE_NOT_REPRESENTATIVE,
            ):
                logger.warning(f"WGC reported {status}. Halting capture fallback.")
                return status, None, "WindowsGraphicsCapture"
        except Exception as err:
            logger.debug(f"Tier 1 WGC backend error: {err}")
        return None

    @classmethod
    def _try_dxgi(cls) -> tuple[CaptureStatus, QPixmap | None, str] | None:
        try:
            status, raw_data, _ = cls._dxgi_backend.capture_virtual_desktop()
            if status == CaptureStatus.SUCCESS and raw_data is not None:
                pixmap = cls._raw_frame_to_pixmap(raw_data)
                if pixmap and not pixmap.isNull() and pixmap.width() > 0:
                    return CaptureStatus.SUCCESS, pixmap, "DXGIDesktopDuplication"
            elif status in (
                CaptureStatus.PROTECTED_CONTENT,
                CaptureStatus.CAPTURE_NOT_REPRESENTATIVE,
            ):
                logger.warning(f"DXGI reported {status}. Halting capture fallback.")
                return status, None, "DXGIDesktopDuplication"
        except Exception as err:
            logger.debug(f"Tier 2 DXGI backend error: {err}")
        return None

    @classmethod
    def _try_bitblt(cls) -> tuple[CaptureStatus, QPixmap | None, str] | None:
        try:
            pixmap = cls._capture_via_win32_bitblt()
            if pixmap and not pixmap.isNull() and pixmap.width() > 0 and pixmap.height() > 0:
                return CaptureStatus.SUCCESS, pixmap, "Win32BitBlt"
        except Exception as err:
            logger.debug(f"Tier 3 Win32 BitBlt backend error: {err}")
        return None

    @classmethod
    def _try_qt(cls) -> tuple[CaptureStatus, QPixmap | None, str] | None:
        try:
            pixmap = cls._capture_via_qt_screens()
            if pixmap and not pixmap.isNull() and pixmap.width() > 0 and pixmap.height() > 0:
                return CaptureStatus.SUCCESS, pixmap, "QtQScreen"
        except Exception as err:
            logger.debug(f"Tier 4 Qt QScreen backend error: {err}")
        return None

    @classmethod
    def _raw_frame_to_pixmap(cls, raw_data: RawFrameData) -> QPixmap | None:
        """Convert RawFrameData buffer to QPixmap."""
        try:
            qimg = QImage(
                raw_data.bytes_data,
                raw_data.width,
                raw_data.height,
                raw_data.bytes_per_line,
                QImage.Format.Format_ARGB32_Premultiplied,
            )
            return QPixmap.fromImage(qimg)
        except Exception as err:
            logger.error(f"Failed to convert raw frame to QPixmap: {err}")
            return None

    @classmethod
    def _capture_via_qt_screens(cls) -> QPixmap | None:
        """Capture and composite all active screens using Qt QScreen APIs."""
        screens = QGuiApplication.screens()
        if not screens:
            return None

        min_x = min(s.geometry().x() for s in screens)
        min_y = min(s.geometry().y() for s in screens)
        max_x = max(s.geometry().x() + s.geometry().width() for s in screens)
        max_y = max(s.geometry().y() + s.geometry().height() for s in screens)

        virt_width = max_x - min_x
        virt_height = max_y - min_y

        if virt_width <= 0 or virt_height <= 0:
            return None

        composite = QPixmap(virt_width, virt_height)
        composite.fill()

        painter = QPainter(composite)
        try:
            captured_any = False
            for s in screens:
                screen_pix = s.grabWindow(0)
                if not screen_pix.isNull() and screen_pix.width() > 0:
                    geo = s.geometry()
                    dest_x = geo.x() - min_x
                    dest_y = geo.y() - min_y
                    painter.drawPixmap(dest_x, dest_y, geo.width(), geo.height(), screen_pix)
                    captured_any = True

            return composite if captured_any else None
        finally:
            painter.end()

    @classmethod
    def _capture_via_win32_bitblt(cls) -> QPixmap | None:
        """Fallback Win32 BitBlt capture of SM_XVIRTUALSCREEN / SM_YVIRTUALSCREEN."""
        if not hasattr(ctypes, "windll"):
            return None

        user32 = getattr(ctypes.windll, "user32", None)
        gdi32 = getattr(ctypes.windll, "gdi32", None)
        if not user32 or not gdi32:
            return None

        try:
            sm_xvirtualscreen = 76
            sm_yvirtualscreen = 77
            sm_cxvirtualscreen = 78
            sm_cyvirtualscreen = 79
            srccopy = 0x00CC0020

            x = user32.GetSystemMetrics(sm_xvirtualscreen)
            y = user32.GetSystemMetrics(sm_yvirtualscreen)
            width = user32.GetSystemMetrics(sm_cxvirtualscreen)
            height = user32.GetSystemMetrics(sm_cyvirtualscreen)

            if width <= 0 or height <= 0:
                x, y = 0, 0
                width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = user32.GetSystemMetrics(1)  # SM_CYSCREEN

            if width <= 0 or height <= 0:
                return None

            hdc_screen = user32.GetDC(0)
            if not hdc_screen:
                return None

            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
            old_bmp = gdi32.SelectObject(hdc_mem, hbmp)

            success = gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, x, y, srccopy)

            if not success:
                gdi32.SelectObject(hdc_mem, old_bmp)
                gdi32.DeleteDC(hdc_mem)
                gdi32.DeleteObject(hbmp)
                user32.ReleaseDC(0, hdc_screen)
                return None

            bmi = _BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # top-down DIB
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            buffer_size = width * height * 4
            buffer = ctypes.create_string_buffer(buffer_size)

            copied = gdi32.GetDIBits(
                hdc_mem,
                hbmp,
                0,
                height,
                buffer,
                ctypes.byref(bmi),
                0,  # DIB_RGB_COLORS
            )
            gdi32.SelectObject(hdc_mem, old_bmp)
            gdi32.DeleteDC(hdc_mem)
            gdi32.DeleteObject(hbmp)
            user32.ReleaseDC(0, hdc_screen)

            if not copied:
                return None

            qimg = QImage(
                buffer.raw,
                width,
                height,
                width * 4,
                QImage.Format.Format_ARGB32_Premultiplied,
            )
            return QPixmap.fromImage(qimg)
        except Exception as err:
            logger.error(f"Win32 BitBlt capture exception: {err}")
            return None
