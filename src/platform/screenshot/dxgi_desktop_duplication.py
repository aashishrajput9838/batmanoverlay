"""Tier 2: DXGI Desktop Duplication (D3D11 / DXGI 1.2+) backend implementation."""

import ctypes
import sys
from typing import Any

from loguru import logger

from src.platform.screenshot.backend_interface import (
    CaptureStatus,
    IScreenshotBackend,
    RawFrameData,
)

DXGI_ERROR_ACCESS_LOST = 0x887A0026
DXGI_ERROR_WAIT_TIMEOUT = 0x887A0027


class GUID(ctypes.Structure):
    """Win32 GUID structure for COM interface queries."""

    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(
        self,
        data1: int,
        w1: int,
        w2: int,
        b1: int,
        b2: int,
        b3: int,
        b4: int,
        b5: int,
        b6: int,
        b7: int,
        b8: int,
    ) -> None:
        super().__init__()
        self.Data1 = data1
        self.Data2 = w1
        self.Data3 = w2
        self.Data4 = (ctypes.c_ubyte * 8)(b1, b2, b3, b4, b5, b6, b7, b8)


# DirectX / DXGI Interface GUIDs
IID_IDXGIDevice = GUID(0x54EC77FA, 0x1377, 0x44E6, 0x8C, 0x32, 0x88, 0xFD, 0x5F, 0x44, 0xC8, 0x4C)
IID_IDXGIAdapter = GUID(0x2411E7E1, 0x12AC, 0x4CCF, 0xBD, 0x14, 0x97, 0x98, 0xE8, 0x53, 0x4D, 0x00)
IID_IDXGIOutput1 = GUID(0x00CD1F67, 0x630B, 0x4B18, 0x86, 0xAE, 0x73, 0xE9, 0x2E, 0x47, 0xAC, 0x77)
IID_ID3D11Texture2D = GUID(
    0x6F15FACB, 0x6108, 0x478E, 0x9A, 0x2E, 0x00, 0x02, 0x66, 0x92, 0x2C, 0xDD
)


class DXGI_OUTDUPL_FRAME_INFO(ctypes.Structure):  # noqa: N801
    """DXGI Output Duplication frame information."""

    _fields_ = [
        ("LastPresentTime", ctypes.c_int64),
        ("LastMouseUpdateTime", ctypes.c_int64),
        ("AccumulatedFrames", ctypes.c_uint32),
        ("RectsCoalesced", ctypes.c_int32),
        ("ProtectedContentMasked", ctypes.c_int32),
        ("PointerPosition", ctypes.c_ubyte * 16),
        ("TotalMetadataBufferSize", ctypes.c_uint32),
        ("PointerShapeBufferSize", ctypes.c_uint32),
    ]


class D3D11_TEXTURE2D_DESC(ctypes.Structure):  # noqa: N801
    """Direct3D 11 Texture 2D Description."""

    _fields_ = [
        ("Width", ctypes.c_uint32),
        ("Height", ctypes.c_uint32),
        ("MipLevels", ctypes.c_uint32),
        ("ArraySize", ctypes.c_uint32),
        ("Format", ctypes.c_uint32),
        ("SampleDesc_Count", ctypes.c_uint32),
        ("SampleDesc_Quality", ctypes.c_uint32),
        ("Usage", ctypes.c_uint32),
        ("BindFlags", ctypes.c_uint32),
        ("CPUAccessFlags", ctypes.c_uint32),
        ("MiscFlags", ctypes.c_uint32),
    ]


class D3D11_MAPPED_SUBRESOURCE(ctypes.Structure):  # noqa: N801
    """Direct3D 11 Mapped Subresource CPU pointer & stride."""

    _fields_ = [
        ("pData", ctypes.c_void_p),
        ("RowPitch", ctypes.c_uint32),
        ("DepthPitch", ctypes.c_uint32),
    ]


class DXGIDesktopDuplicationBackend(IScreenshotBackend):
    """Tier 2 DXGI Desktop Duplication capture backend utilizing DirectX 11."""

    def __init__(self) -> None:
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Return True if DXGI Desktop Duplication is supported on this system."""
        if self._available is not None:
            return self._available

        if sys.platform != "win32":
            self._available = False
            return False

        try:
            d3d11 = getattr(ctypes.windll, "d3d11", None)
            dxgi = getattr(ctypes.windll, "dxgi", None)
            if not d3d11 or not dxgi:
                self._available = False
                return False

            self._available = True
            return True
        except Exception as err:
            logger.debug(f"DXGI Desktop Duplication availability error: {err}")
            self._available = False
            return False

    @staticmethod
    def _get_vtable(ptr: ctypes.c_void_p) -> Any:
        """Retrieve COM object vtable pointer array."""
        return ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]

    def _check_foreground_protection(self) -> bool:
        """Check for active cloaked or protected foreground window."""
        if not hasattr(ctypes, "windll"):
            return False
        user32 = getattr(ctypes.windll, "user32", None)
        dwmapi = getattr(ctypes.windll, "dwmapi", None)
        if not user32 or not dwmapi:
            return False

        hwnd = user32.GetForegroundWindow()
        if hwnd:
            cloaked = ctypes.c_uint32(0)
            hr = dwmapi.DwmGetWindowAttribute(
                hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            )
            if hr == 0 and cloaked.value != 0:
                return True
        return False

    def capture_virtual_desktop(self) -> tuple[CaptureStatus, RawFrameData | None, str | None]:
        """Attempt GPU-accelerated DXGI desktop capture across all monitors."""
        if not self.is_available():
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "DXGI unavailable on this platform"

        if self._check_foreground_protection():
            logger.warning("DXGI detected protected/cloaked window surface.")
            msg = "Screenshot unavailable: content is protected or cloaked by Windows."
            return CaptureStatus.PROTECTED_CONTENT, None, msg

        d3d11 = getattr(ctypes.windll, "d3d11", None)
        if not d3d11:
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "d3d11 DLL missing"

        # DirectX 11 Device Creation
        p_device = ctypes.c_void_p()
        p_context = ctypes.c_void_p()
        feature_level = ctypes.c_uint32()

        hr_dev = d3d11.D3D11CreateDevice(
            None,
            1,  # D3D_DRIVER_TYPE_HARDWARE
            None,
            0x20,  # D3D11_CREATE_DEVICE_BGRA_SUPPORT
            None,
            0,
            7,  # D3D11_SDK_VERSION
            ctypes.byref(p_device),
            ctypes.byref(feature_level),
            ctypes.byref(p_context),
        )

        if hr_dev != 0 or not p_device.value:
            return (
                CaptureStatus.CAPTURE_UNAVAILABLE,
                None,
                f"D3D11CreateDevice failed: {hr_dev:#x}",
            )

        try:
            return self._execute_dxgi_pipeline(p_device, p_context)
        except Exception as err:
            logger.error(f"DXGI Desktop Duplication capture exception: {err}")
            return CaptureStatus.CAPTURE_ERROR, None, str(err)

    def _create_duplication(self, p_device: ctypes.c_void_p) -> tuple[ctypes.c_void_p, str | None]:
        p_dxgi_device = ctypes.c_void_p()
        p_adapter = ctypes.c_void_p()
        p_output = ctypes.c_void_p()
        p_output1 = ctypes.c_void_p()
        p_dup = ctypes.c_void_p()

        vtbl_device = self._get_vtable(p_device)
        qi = ctypes.WINFUNCTYPE(
            ctypes.c_int32,
            ctypes.c_void_p,
            ctypes.POINTER(GUID),
            ctypes.POINTER(ctypes.c_void_p),
        )(vtbl_device[0])
        if qi(p_device, ctypes.byref(IID_IDXGIDevice), ctypes.byref(p_dxgi_device)) != 0:
            return p_dup, "IDXGIDevice query failed"

        vtbl_dxgi = self._get_vtable(p_dxgi_device)
        get_adapter = ctypes.WINFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )(vtbl_dxgi[7])
        if get_adapter(p_dxgi_device, ctypes.byref(p_adapter)) != 0:
            return p_dup, "GetAdapter failed"

        vtbl_adapter = self._get_vtable(p_adapter)
        enum_outputs = ctypes.WINFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)
        )(vtbl_adapter[7])
        if enum_outputs(p_adapter, 0, ctypes.byref(p_output)) != 0:
            return p_dup, "EnumOutputs failed"

        vtbl_output = self._get_vtable(p_output)
        qi_out = ctypes.WINFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
        )(vtbl_output[0])
        hr_out1 = qi_out(p_output, ctypes.byref(IID_IDXGIOutput1), ctypes.byref(p_output1))

        target_out = p_output1 if (hr_out1 == 0 and p_output1.value) else p_output
        vtbl_target = self._get_vtable(target_out)

        dup_output = ctypes.WINFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )(vtbl_target[22])
        hr_dup = dup_output(target_out, p_device, ctypes.byref(p_dup))
        if hr_dup != 0:
            return p_dup, f"DuplicateOutput unsupported: {hr_dup:#x}"

        return p_dup, None

    def _execute_dxgi_pipeline(
        self, p_device: ctypes.c_void_p, p_context: ctypes.c_void_p
    ) -> tuple[CaptureStatus, RawFrameData | None, str | None]:
        """Execute DXGI duplication frame acquisition and staging texture extraction."""
        p_dup, err_msg = self._create_duplication(p_device)
        if err_msg or not p_dup.value:
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, err_msg or "DuplicateOutput failed"

        frame_info = DXGI_OUTDUPL_FRAME_INFO()
        p_resource = ctypes.c_void_p()
        vtbl_dup = self._get_vtable(p_dup)
        acquire = ctypes.WINFUNCTYPE(
            ctypes.c_int32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(DXGI_OUTDUPL_FRAME_INFO),
            ctypes.POINTER(ctypes.c_void_p),
        )(vtbl_dup[8])
        release_frame = ctypes.WINFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)(vtbl_dup[14])

        hr_acq = acquire(p_dup, 250, ctypes.byref(frame_info), ctypes.byref(p_resource))
        if frame_info.ProtectedContentMasked != 0:
            release_frame(p_dup)
            logger.warning("DXGI reported ProtectedContentMasked frame.")
            msg = "Screenshot unavailable: content is protected or cloaked by Windows."
            return CaptureStatus.PROTECTED_CONTENT, None, msg

        if hr_acq != 0 or not p_resource.value:
            return (
                CaptureStatus.CAPTURE_UNAVAILABLE,
                None,
                f"DXGI AcquireNextFrame timeout/error: {hr_acq:#x}",
            )

        try:
            return self._extract_staging_pixels(p_device, p_context, p_resource)
        finally:
            release_frame(p_dup)

    def _extract_staging_pixels(
        self, p_device: ctypes.c_void_p, p_context: ctypes.c_void_p, p_resource: ctypes.c_void_p
    ) -> tuple[CaptureStatus, RawFrameData | None, str | None]:
        p_texture = ctypes.c_void_p()
        p_staging = ctypes.c_void_p()

        vtbl_res = self._get_vtable(p_resource)
        qi_res = ctypes.WINFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
        )(vtbl_res[0])
        if qi_res(p_resource, ctypes.byref(IID_ID3D11Texture2D), ctypes.byref(p_texture)) != 0:
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "ID3D11Texture2D query failed"

        tex_desc = D3D11_TEXTURE2D_DESC()
        vtbl_tex = self._get_vtable(p_texture)
        get_desc = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(D3D11_TEXTURE2D_DESC))(
            vtbl_tex[10]
        )
        get_desc(p_texture, ctypes.byref(tex_desc))

        if tex_desc.Width <= 0 or tex_desc.Height <= 0:
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "DXGI frame had 0 dimensions"

        staging_desc = D3D11_TEXTURE2D_DESC()
        staging_desc.Width = tex_desc.Width
        staging_desc.Height = tex_desc.Height
        staging_desc.MipLevels = 1
        staging_desc.ArraySize = 1
        staging_desc.Format = tex_desc.Format
        staging_desc.SampleDesc_Count = 1
        staging_desc.SampleDesc_Quality = 0
        staging_desc.Usage = 3  # D3D11_USAGE_STAGING
        staging_desc.BindFlags = 0
        staging_desc.CPUAccessFlags = 0x20000  # D3D11_CPU_ACCESS_READ
        staging_desc.MiscFlags = 0

        vtbl_dev = self._get_vtable(p_device)
        create_tex2d = ctypes.WINFUNCTYPE(
            ctypes.c_int32,
            ctypes.c_void_p,
            ctypes.POINTER(D3D11_TEXTURE2D_DESC),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        )(vtbl_dev[5])
        if create_tex2d(p_device, ctypes.byref(staging_desc), None, ctypes.byref(p_staging)) != 0:
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "CreateTexture2D staging failed"

        vtbl_ctx = self._get_vtable(p_context)
        copy_resource = ctypes.WINFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(vtbl_ctx[47])
        copy_resource(p_context, p_staging, p_texture)

        mapped = D3D11_MAPPED_SUBRESOURCE()
        map_sub = ctypes.WINFUNCTYPE(
            ctypes.c_int32,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(D3D11_MAPPED_SUBRESOURCE),
        )(vtbl_ctx[14])
        unmap_sub = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32)(
            vtbl_ctx[15]
        )

        if map_sub(p_context, p_staging, 0, 1, 0, ctypes.byref(mapped)) != 0 or not mapped.pData:
            return CaptureStatus.CAPTURE_UNAVAILABLE, None, "Map staging texture failed"

        try:
            img_size = mapped.RowPitch * tex_desc.Height
            raw_bytes = ctypes.string_at(mapped.pData, img_size)

            raw_frame = RawFrameData(
                width=tex_desc.Width,
                height=tex_desc.Height,
                bytes_data=raw_bytes,
                bytes_per_line=mapped.RowPitch,
                format_name="ARGB32",
                backend_name="DXGIDesktopDuplication",
            )
            return CaptureStatus.SUCCESS, raw_frame, None
        finally:
            unmap_sub(p_context, p_staging, 0)
