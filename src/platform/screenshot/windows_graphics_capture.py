"""Tier 1: Windows Graphics Capture (WGC / D3D11) backend implementation."""

import ctypes
import sys

from loguru import logger

from src.platform.screenshot.backend_interface import (
    CaptureStatus,
    IScreenshotBackend,
    RawFrameData,
)


class WindowsGraphicsCaptureBackend(IScreenshotBackend):
    """Tier 1 Windows Graphics Capture backend using native D3D11 and Win32 interop."""

    def __init__(self) -> None:
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if Windows Graphics Capture and D3D11 are available on this system."""
        if self._available is not None:
            return self._available

        if sys.platform != "win32":
            self._available = False
            return False

        try:
            d3d11 = getattr(ctypes.windll, "d3d11", None)
            user32 = getattr(ctypes.windll, "user32", None)
            if not d3d11 or not user32:
                self._available = False
                return False

            # Test D3D11 device creation availability
            p_device = ctypes.c_void_p()
            p_context = ctypes.c_void_p()
            feature_level = ctypes.c_uint32()

            hr = d3d11.D3D11CreateDevice(
                None,  # pAdapter
                1,  # D3D_DRIVER_TYPE_HARDWARE
                None,  # Software
                0x20,  # D3D11_CREATE_DEVICE_BGRA_SUPPORT
                None,
                0,
                7,  # D3D11_SDK_VERSION
                ctypes.byref(p_device),
                ctypes.byref(feature_level),
                ctypes.byref(p_context),
            )

            if hr == 0 and p_device.value:
                # Release COM pointers if created
                if p_context.value:
                    vtbl_ctx = ctypes.cast(p_context, ctypes.POINTER(ctypes.c_void_p))[0]
                    release_ctx = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(
                        ctypes.cast(vtbl_ctx, ctypes.POINTER(ctypes.c_void_p))[2]
                    )
                    release_ctx(p_context)

                vtbl_dev = ctypes.cast(p_device, ctypes.POINTER(ctypes.c_void_p))[0]
                release_dev = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(
                    ctypes.cast(vtbl_dev, ctypes.POINTER(ctypes.c_void_p))[2]
                )
                release_dev(p_device)

                self._available = True
                return True

            self._available = False
            return False
        except Exception as err:
            logger.debug(f"WGC availability check exception: {err}")
            self._available = False
            return False

    def _check_foreground_protection(self) -> bool:
        """Check if active foreground window is protected or cloaked by shell/UAC."""
        if not hasattr(ctypes, "windll"):
            return False

        user32 = getattr(ctypes.windll, "user32", None)
        dwmapi = getattr(ctypes.windll, "dwmapi", None)
        if not user32 or not dwmapi:
            return False

        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return False

            cloaked = ctypes.c_uint32(0)
            hr = dwmapi.DwmGetWindowAttribute(
                hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            )
            if hr == 0 and cloaked.value != 0:
                return True
        except Exception as err:
            logger.debug(f"WGC protection check error: {err}")

        return False

    def capture_virtual_desktop(self) -> tuple[CaptureStatus, RawFrameData | None, str | None]:
        """Execute Tier 1 WGC desktop capture."""
        if not self.is_available():
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "WGC unavailable on this platform"

        # 1. Strictly verify content protection status before attempting capture
        if self._check_foreground_protection():
            logger.warning("WGC detected protected/cloaked window on foreground desktop.")
            msg = "Screenshot unavailable: content is protected or cloaked by Windows."
            return CaptureStatus.PROTECTED_CONTENT, None, msg

        # 2. WGC frame acquisition delegated to DXGI pipeline if unhandled
        msg = "WGC frame acquisition delegated to DXGI pipeline"
        return CaptureStatus.CAPTURE_UNAVAILABLE, None, msg
