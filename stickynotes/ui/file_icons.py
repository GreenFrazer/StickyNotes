"""OS shell file icons for dock shortcuts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QFileInfo, QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QFileIconProvider

_ICON_PROVIDER: QFileIconProvider | None = None
_PIXMAP_CACHE: dict[tuple[str, int, float], QPixmap] = {}


def _provider() -> QFileIconProvider:
    global _ICON_PROVIDER
    if _ICON_PROVIDER is None:
        _ICON_PROVIDER = QFileIconProvider()
    return _ICON_PROVIDER


def _path_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _scale_pixmap(pixmap: QPixmap, size: int) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _icon_from_qt(path: str, size: int) -> QPixmap | None:
    if sys.platform == "win32" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return None
    info = QFileInfo(path)
    icon = _provider().icon(info)
    if icon.isNull():
        return None
    pixmap = icon.pixmap(QSize(size, size), QIcon.Mode.Normal, QIcon.State.Off)
    if pixmap.isNull():
        return None
    return _scale_pixmap(pixmap, size)


def _icon_from_platform(path: str, size: int) -> QPixmap | None:
    if sys.platform != "win32":
        return None
    ext = Path(path).suffix.lower()
    if ext != ".lnk":
        return None
    from stickynotes.platform.windows.shell_icons import shell_file_icon_pixmap

    return shell_file_icon_pixmap(path, size)


def file_icon_pixmap(path: str, size: int = 28) -> QPixmap | None:
    """Return a scaled OS file icon for path, or None if unavailable."""
    if not path or not path.strip():
        return None
    resolved = os.path.abspath(path)
    mtime = _path_mtime(resolved)
    cache_key = (resolved, size, mtime)
    cached = _PIXMAP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    pixmap = _icon_from_qt(resolved, size)
    if pixmap is None or pixmap.isNull():
        pixmap = _icon_from_platform(resolved, size)

    if pixmap is None or pixmap.isNull():
        return None

    _PIXMAP_CACHE[cache_key] = pixmap
    return pixmap


def has_file_icon(path: str, *, size: int = 28) -> bool:
    """Return True if a shell icon can be resolved for path."""
    pixmap = file_icon_pixmap(path, size=size)
    return pixmap is not None and not pixmap.isNull()


def clear_file_icon_cache() -> None:
    """Clear cached pixmaps (for tests)."""
    _PIXMAP_CACHE.clear()
