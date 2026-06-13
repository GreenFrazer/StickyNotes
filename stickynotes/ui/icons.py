"""Programmatic monochrome icons for dock and note chrome."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from stickynotes.theme import INK, NOTE_COLOURS, ON_DARK, TITLE_BAR_COLOURS

_ICON_CACHE: dict[tuple[str, int, str], QIcon] = {}


def _col(name: str) -> QColor:
    return QColor(name)


def _draw(name: str, size: int, color: QColor) -> QPixmap:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    s = size
    m = max(2, s // 8)
    thin = max(1.0, s / 16)
    med = max(1.5, s / 11)
    pen.setWidthF(thin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    cx, cy = s / 2, s / 2

    if name == "pin_file":
        pen.setWidthF(med)
        p.setPen(pen)
        p.drawLine(int(cx - s * 0.18), int(cy + s * 0.22), int(cx + s * 0.18), int(cy - s * 0.22))
        p.drawEllipse(int(cx + s * 0.08), int(cy - s * 0.32), int(s * 0.14), int(s * 0.14))
    elif name == "plus":
        p.drawLine(int(cx), int(m * 2), int(cx), int(s - m * 2))
        p.drawLine(int(m * 2), int(cy), int(s - m * 2), int(cy))
    elif name == "show_all":
        p.drawRect(int(m * 1.5), int(m * 2), int(s - m * 3), int(s - m * 3.5))
        p.drawLine(int(m * 3), int(m * 3.5), int(s - m * 3), int(m * 3.5))
        p.drawLine(int(m * 3), int(m * 5), int(s - m * 5), int(m * 5))
    elif name == "hide_all":
        p.drawLine(int(m * 2), int(cy), int(s - m * 2), int(cy))
        p.drawLine(int(m * 2.5), int(cy - s * 0.12), int(s - m * 2.5), int(cy + s * 0.12))
    elif name == "settings":
        p.drawEllipse(int(m * 2), int(m * 2), int(s - m * 4), int(s - m * 4))
        for i in range(8):
            ang = i * 45
            from math import cos, sin, radians

            r1 = s * 0.22
            r2 = s * 0.34
            a = radians(ang)
            p.drawLine(
                int(cx + cos(a) * r1),
                int(cy + sin(a) * r1),
                int(cx + cos(a) * r2),
                int(cy + sin(a) * r2),
            )
    elif name == "exit":
        pen.setWidthF(med)
        p.setPen(pen)
        p.drawLine(int(m * 2), int(m * 2), int(s - m * 2), int(s - m * 2))
        p.drawLine(int(s - m * 2), int(m * 2), int(m * 2), int(s - m * 2))
    elif name == "copy":
        p.drawRect(int(m * 2), int(m * 3), int(s * 0.52), int(s * 0.52))
        p.drawRect(int(s * 0.34), int(m * 1.5), int(s * 0.52), int(s * 0.52))
    elif name == "lock":
        p.drawRect(int(m * 2.5), int(cy), int(s - m * 5), int(s * 0.34))
        p.drawArc(int(m * 3), int(m * 2), int(s - m * 6), int(s * 0.42), 0, 180 * 16)
    elif name == "unlock":
        p.drawRect(int(m * 2.5), int(cy), int(s - m * 5), int(s * 0.34))
        p.drawArc(int(m * 3), int(m * 2), int(s - m * 6), int(s * 0.42), 30 * 16, 150 * 16)
    elif name == "compact":
        p.drawLine(int(m * 2), int(cy), int(s - m * 2), int(cy))
    elif name == "expand":
        p.drawLine(int(cx), int(m * 2), int(cx), int(s - m * 2))
        p.drawLine(int(m * 2.5), int(cy + s * 0.08), int(cx), int(s - m * 2.5))
        p.drawLine(int(s - m * 2.5), int(cy + s * 0.08), int(cx), int(s - m * 2.5))
    elif name == "pin":
        pen.setWidthF(med)
        p.setPen(pen)
        p.drawLine(int(cx), int(m * 1.5), int(cx), int(s - m * 2.5))
        p.drawLine(int(cx - s * 0.16), int(s - m * 2.5), int(cx + s * 0.16), int(s - m * 2.5))
        p.drawEllipse(int(cx - s * 0.12), int(m * 1.2), int(s * 0.24), int(s * 0.24))
    elif name == "unpin":
        pen.setWidthF(med)
        p.setPen(pen)
        p.drawLine(int(cx), int(m * 2.5), int(cx), int(s - m * 2))
        p.drawLine(int(cx - s * 0.14), int(s - m * 2), int(cx + s * 0.14), int(s - m * 2))
    elif name == "close":
        pen.setWidthF(med)
        p.setPen(pen)
        p.drawLine(int(m * 2), int(m * 2), int(s - m * 2), int(s - m * 2))
        p.drawLine(int(s - m * 2), int(m * 2), int(m * 2), int(s - m * 2))
    elif name == "check":
        pen.setWidthF(med)
        p.setPen(pen)
        p.drawLine(int(m * 2), int(cy), int(cx - m * 0.5), int(s - m * 2.5))
        p.drawLine(int(cx - m * 0.5), int(s - m * 2.5), int(s - m * 2), int(m * 2))
    else:
        p.drawEllipse(int(m * 2), int(m * 2), int(s - m * 4), int(s - m * 4))

    p.end()
    return px


def icon(name: str, size: int = 20, *, light: bool = False) -> QIcon:
    """Return a cached monochrome icon. ``light=True`` for dark dock backgrounds."""
    key = (name, size, "light" if light else "dark")
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    color = _col(ON_DARK if light else INK)
    ic = QIcon(_draw(name, size, color))
    _ICON_CACHE[key] = ic
    return ic


def set_button_icon(btn, name: str, size: int = 20, *, light: bool = False) -> None:
    btn.setIcon(icon(name, size, light=light))
    btn.setIconSize(QSize(size, size))
    btn.setText("")


def render_app_icon(size: int = 64) -> QPixmap:
    """Squircle sticky-note icon for tray and packaging."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pad = max(2, size // 16)
    r = max(8, size // 7)
    bg = _col(NOTE_COLOURS["yellow"])
    border = _col(TITLE_BAR_COLOURS["yellow"])
    p.setBrush(bg)
    p.setPen(QPen(border, max(1, size // 32)))
    p.drawRoundedRect(pad, pad, size - pad * 2, size - pad * 2, r, r)
    line_pen = QPen(_col(INK), max(1, size // 32))
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
