"""UI chrome glyphs and app branding icons."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from stickynotes.theme import INK, NOTE_COLOURS, ON_DARK, TITLE_BAR_COLOURS

# Recognisable emoji / Unicode glyphs for small toolbar buttons.
GLYPHS: dict[str, str] = {
    "copy": "\U0001F4CB",
    "lock": "\U0001F512",
    "unlock": "\U0001F513",
    "compact": "\u25AC",
    "expand": "\u25BC",
    "pin": "\U0001F4CC",
    "unpin": "\U0001F4CD",
    "close": "\u2715",
    "check": "\u2713",
    "pin_file": "\U0001F4CE",
    "plus": "\u2795",
    "show_all": "\U0001F4CB",
    "hide_all": "\U0001F648",
    "settings": "\u2699",
    "search": "\U0001F50D",
    "exit": "\u274C",
}


def _glyph_font_size(size: int) -> int:
    return max(11, min(20, int(size * 0.72)))


def icon(name: str, size: int = 20, *, light: bool = False) -> QIcon:
    """Return an empty icon; chrome buttons use text glyphs via set_button_icon."""
    return QIcon()


def set_button_icon(btn, name: str, size: int = 20, *, light: bool = False) -> None:
    """Apply a recognisable glyph to a chrome button."""
    btn.setIcon(QIcon())
    btn.setText(GLYPHS.get(name, "?"))
    btn.setIconSize(QSize(size, size))
    px = _glyph_font_size(size)
    btn.setProperty("glyphSize", px)


def render_app_icon(size: int = 64) -> QPixmap:
    """Squircle sticky-note icon for tray and packaging."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pad = max(2, size // 16)
    r = max(8, size // 7)
    bg = QColor(NOTE_COLOURS["yellow"])
    border = QColor(TITLE_BAR_COLOURS["yellow"])
    p.setBrush(bg)
    p.setPen(QPen(border, max(1, size // 32)))
    p.drawRoundedRect(pad, pad, size - pad * 2, size - pad * 2, r, r)
    line_pen = QPen(QColor(INK), max(1, size // 32))
    line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(line_pen)
    x1 = int(size * 0.22)
    x2 = int(size * 0.78)
    for yf in (0.32, 0.5, 0.68):
        y = int(size * yf)
        p.drawLine(x1, y, x2, y)
    p.end()
    return px


def app_icon() -> QIcon:
    ic = QIcon()
    for sz in (16, 32, 64, 128, 256):
        ic.addPixmap(render_app_icon(sz))
    return ic
