"""Windows shell icon extraction via SHGetFileInfo (no pywin32)."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

SHGFI_ICON = 0x000000100
SHGFI_LARGEICON = 0x000000000
SHGFI_SMALLICON = 0x000000001
SHGFI_USEFILEATTRIBUTES = 0x000000010
FILE_ATTRIBUTE_NORMAL = 0x00000080
DIB_RGB_COLORS = 0
BI_RGB = 0


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def _hicon_to_pixmap(hicon: int, size: int) -> QPixmap | None:
    if not hicon:
        return None
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    icon_info = ctypes.create_string_buffer(32)
    if not user32.GetIconInfo(hicon, icon_info):
        user32.DestroyIcon(hicon)
        return None

    # ICONINFO: BOOL fIcon; DWORD xHotspot; DWORD yHotspot; HBITMAP hbmMask; HBITMAP hbmColor
    hbm_color = ctypes.c_uint32.from_buffer(icon_info, 12).value
    if not hbm_color:
        user32.DestroyIcon(hicon)
        return None

    bmp = wintypes.BITMAP()
    if gdi32.GetObjectW(hbm_color, ctypes.sizeof(bmp), ctypes.byref(bmp)) == 0:
        user32.DestroyIcon(hicon)
        return None

    width = bmp.bmWidth
    height = abs(bmp.bmHeight)
    if width <= 0 or height <= 0:
        user32.DestroyIcon(hicon)
        return None

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = BI_RGB

    buffer_size = width * height * 4
    buffer = (ctypes.c_ubyte * buffer_size)()
    hdc = user32.GetDC(0)
    try:
        if (
            gdi32.GetDIBits(
                hdc,
                hbm_color,
                0,
                height,
                ctypes.byref(buffer),
                ctypes.byref(bmi),
                DIB_RGB_COLORS,
            )
            == 0
        ):
            return None
    finally:
        user32.ReleaseDC(0, hdc)
        user32.DestroyIcon(hicon)

    image = QImage(bytes(buffer), width, height, QImage.Format.Format_ARGB32)
    pixmap = QPixmap.fromImage(image)
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def shell_file_icon_pixmap(path: str, size: int = 28) -> QPixmap | None:
    """Extract a shell icon for path using SHGetFileInfoW."""
    resolved = os.path.abspath(path)
    if not os.path.isfile(resolved):
        return None

    shell32 = ctypes.windll.shell32
    shfi = SHFILEINFOW()
    flags = SHGFI_ICON | (SHGFI_SMALLICON if size <= 24 else SHGFI_LARGEICON)
    result = shell32.SHGetFileInfoW(
        resolved,
        FILE_ATTRIBUTE_NORMAL,
        ctypes.byref(shfi),
        ctypes.sizeof(shfi),
        flags,
    )
    if result == 0:
        return None
    return _hicon_to_pixmap(int(shfi.hIcon), size)
