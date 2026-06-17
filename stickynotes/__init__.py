"""Sticky Notes desktop application."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

__version__ = "3.5"
__build_date__ = ""

try:
    from stickynotes import _build_info

    if _build_info.__build_date__:
        __build_date__ = _build_info.__build_date__
except ImportError:
    pass


def build_date_display() -> str:
    """Return build timestamp; falls back to package mtime for dev runs."""
    if __build_date__:
        return __build_date__
    stamp = datetime.fromtimestamp(Path(__file__).stat().st_mtime)
    return stamp.strftime("%Y-%m-%d %H:%M")
