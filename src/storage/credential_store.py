"""Windows-native Secure Credential Storage for OAuth Tokens via Windows DPAPI."""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.wintypes
import json
import sys
from pathlib import Path

from loguru import logger


class DATA_BLOB(ctypes.Structure):  # noqa: N801
    """Win32 DATA_BLOB structure for CryptProtectData / CryptUnprotectData."""

    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _win32_encrypt(data: bytes) -> bytes:
    """Encrypt bytes using Windows DPAPI (CryptProtectData)."""
    if sys.platform != "win32":
        return data

    buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    in_blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()

    crypt32 = getattr(ctypes.windll, "crypt32")  # noqa: B009
    res = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "batmanoverlay_oauth_tokens",
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not res:
        raise OSError("Windows DPAPI CryptProtectData failed.")

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32 = getattr(ctypes.windll, "kernel32")  # noqa: B009
        kernel32.LocalFree(out_blob.pbData)


def _win32_decrypt(encrypted_data: bytes) -> bytes:
    """Decrypt bytes using Windows DPAPI (CryptUnprotectData)."""
    if sys.platform != "win32":
        return encrypted_data

    buffer = (ctypes.c_byte * len(encrypted_data)).from_buffer_copy(encrypted_data)
    in_blob = DATA_BLOB(len(encrypted_data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()

    crypt32 = getattr(ctypes.windll, "crypt32")  # noqa: B009
    res = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not res:
        raise OSError("Windows DPAPI CryptUnprotectData failed.")

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32 = getattr(ctypes.windll, "kernel32")  # noqa: B009
        kernel32.LocalFree(out_blob.pbData)


class SecureCredentialStore:
    """Manages Windows-native secure storage for OAuth access and refresh tokens."""

    def __init__(self, storage_dir: Path) -> None:
        self._target_file = storage_dir / "tokens.dat"
        self._target_file.parent.mkdir(parents=True, exist_ok=True)

    def save_tokens(self, access_token: str | None, refresh_token: str | None) -> None:
        """Securely encrypt and write access_token and refresh_token to OS credential storage."""
        if not access_token and not refresh_token:
            self.clear_tokens()
            return

        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
        json_bytes = json.dumps(payload).encode("utf-8")

        try:
            encrypted_blob = _win32_encrypt(json_bytes)
            self._target_file.write_bytes(encrypted_blob)
            logger.debug("Successfully saved encrypted OAuth tokens to OS credential storage.")
        except Exception as err:
            logger.error(f"Failed to encrypt and save OAuth tokens: {err}")
            raise

    def load_tokens(self) -> tuple[str | None, str | None]:
        """Decrypt and read access_token and refresh_token from OS credential storage."""
        if not self._target_file.exists():
            return None, None

        try:
            encrypted_blob = self._target_file.read_bytes()
            if not encrypted_blob:
                return None, None

            decrypted_bytes = _win32_decrypt(encrypted_blob)
            payload = json.loads(decrypted_bytes.decode("utf-8"))
            access_token = payload.get("access_token")
            refresh_token = payload.get("refresh_token")
            return access_token, refresh_token
        except Exception as err:
            logger.warning(f"Failed to decrypt OAuth tokens from OS credential storage: {err}")
            return None, None

    def clear_tokens(self) -> None:
        """Securely remove encrypted token storage file."""
        if self._target_file.exists():
            with contextlib.suppress(Exception):
                self._target_file.unlink()
            logger.debug("Cleared OAuth tokens from OS credential storage.")
