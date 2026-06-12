"""Data models and helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from stickynotes.theme import DEFAULT_NOTE_H, DEFAULT_NOTE_W, DATE_FMT


def fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime(DATE_FMT)
    except (ValueError, TypeError):
        return iso or ""


def auto_size(content: str) -> tuple[int, int]:
    n = len(content.strip())
    lines = content.count("\n") + 1
    if n == 0:
        return 220, 150
    if n < 30:
        return 220, 160
    if n < 100 and lines < 5:
        return 240, 180
    if n < 300:
        return 260, 220
    return 280, 280


def default_settings() -> dict[str, Any]:
    return {"dock_position": "top", "dark_mode": False}


def default_note(note_id: str | None = None) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": note_id or str(uuid.uuid4()),
        "content": "",
        "x": 200,
        "y": 200,
        "width": DEFAULT_NOTE_W,
        "height": DEFAULT_NOTE_H,
        "colour": "yellow",
        "opacity": 1.0,
        "always_on_top": False,
        "visible": True,
        "compact": False,
        "user_resized": False,
        "created_at": now,
        "modified_at": now,
    }


VALID_COLOURS = frozenset(
    {"yellow", "blue", "green", "pink", "purple", "orange", "white"}
)

NOTE_DEFAULTS = {
    "content": "",
    "x": 200,
    "y": 200,
    "width": DEFAULT_NOTE_W,
    "height": DEFAULT_NOTE_H,
    "colour": "yellow",
    "opacity": 1.0,
    "always_on_top": False,
    "visible": True,
    "compact": False,
    "user_resized": False,
}


def normalize_note(raw: dict[str, Any], note_id: str) -> dict[str, Any] | None:
    """Validate and normalize a note dict; return None if unusable."""
    if not isinstance(raw, dict):
        return None
    note = dict(default_note(note_id))
    note.update(raw)
    note["id"] = note_id
    if note.get("colour") not in VALID_COLOURS:
        note["colour"] = "yellow"
    try:
        note["opacity"] = float(note.get("opacity", 1.0))
    except (TypeError, ValueError):
        note["opacity"] = 1.0
    for key in ("x", "y", "width", "height"):
        try:
            note[key] = int(note.get(key, NOTE_DEFAULTS[key]))
        except (TypeError, ValueError):
            note[key] = NOTE_DEFAULTS[key]
    for key in ("always_on_top", "visible", "compact", "user_resized"):
        note[key] = bool(note.get(key, NOTE_DEFAULTS[key]))
    note["content"] = str(note.get("content", ""))
    for ts in ("created_at", "modified_at"):
        if not note.get(ts):
            note[ts] = datetime.now().isoformat(timespec="seconds")
    return note
