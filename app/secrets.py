from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


_CRYPTPROTECT_UI_FORBIDDEN = 0x1


def _blob(value: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(value)
    return _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def protect_secret(value: str) -> str:
    """Encrypt a value with Windows DPAPI for the current Windows user only."""
    if not value:
        return ""
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
    except AttributeError as error:
        raise RuntimeError("本版本只能在 Windows 上保存本机加密密钥。") from error
    input_blob, input_buffer = _blob(value.encode("utf-8"))
    output_blob = _DataBlob()
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob), "邮箱代理", None, None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(output_blob)
    ):
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        kernel32.LocalFree(output_blob.pbData)


def reveal_secret(value: str) -> str:
    if not value:
        return ""
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
    except AttributeError as error:
        raise RuntimeError("本版本只能在 Windows 上读取本机加密密钥。") from error
    input_blob, input_buffer = _blob(base64.b64decode(value.encode("ascii")))
    output_blob = _DataBlob()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob), None, None, None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(output_blob)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(output_blob.pbData)
