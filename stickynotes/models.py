"""Data models and helpers."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
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
        "private": False,
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
    "private": False,
    "user_resized": False,
}


def is_private(note: dict) -> bool:
    return bool(note.get("private"))


def private_preview_text() -> str:
    return "Private note — click to reveal"


def dock_popup_preview_text() -> str:
    return "Private note — hover copy still works"


def dock_indicator_text(note: dict) -> str:
    if is_private(note):
        return "\U0001F512"
    content = note.get("content", "").strip()
    return content[:4] or "\u2026"


DOCK_PIN_EXTENSIONS = frozenset(
    {".doc", ".docx", ".xls", ".xlsx", ".pdf", ".txt", ".csv"}
)

FILE_BADGE_MAP = {
    ".doc": "DOC",
    ".docx": "DOC",
    ".xls": "XLS",
    ".xlsx": "XLS",
    ".pdf": "PDF",
    ".txt": "TXT",
    ".csv": "CSV",
    ".ppt": "PPT",
    ".pptx": "PPT",
    ".rtf": "RTF",
    ".md": "MD",
}


def dock_pin_dialog_filters() -> str:
    """QFileDialog filter string for pinning files to the dock."""
    doc_exts = " ".join(f"*{ext}" for ext in sorted(DOCK_PIN_EXTENSIONS))
    return (
        f"Documents ({doc_exts});;"
        "Word (*.doc *.docx);;"
        "Excel (*.xls *.xlsx);;"
        "PDF (*.pdf);;"
        "All files (*)"
    )


def is_dock_pinnable_file(path: str) -> bool:
    """Return True if path is a local file that may be pinned (matches pin dialog)."""
    if not path or not path.strip():
        return False
    return os.path.isfile(os.path.abspath(path))


def local_paths_from_mime_urls(urls: list) -> list[str]:
    """Extract absolute local file paths from QUrl list; skips non-files."""
    paths: list[str] = []
    for url in urls:
        if not url.isLocalFile():
            continue
        local = url.toLocalFile()
        if not local:
            continue
        resolved = os.path.abspath(local)
        if os.path.isfile(resolved):
            paths.append(resolved)
    return paths


def dock_file_badge(path: str) -> str:
    """Return a short file-type badge for dock indicators."""
    ext = Path(path).suffix.lower()
    return FILE_BADGE_MAP.get(ext, ext.lstrip(".").upper()[:3] or "FILE")


def dock_file_label(path: str, label: str | None = None) -> str:
    """Return display label; default to filename without extension."""
    if label and label.strip():
        return label.strip()
    return Path(path).stem or Path(path).name or "File"


def default_dock_shortcut(
    shortcut_id: str | None = None,
    path: str = "",
    label: str | None = None,
) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    resolved = os.path.abspath(path) if path else ""
    return {
        "id": shortcut_id or str(uuid.uuid4()),
        "path": resolved,
        "label": dock_file_label(resolved, label) if resolved else (label or ""),
        "added_at": now,
    }


def normalize_dock_shortcut(
    raw: dict[str, Any], shortcut_id: str
) -> dict[str, Any] | None:
    """Validate and normalize a dock shortcut dict; return None if unusable."""
    if not isinstance(raw, dict):
        return None
    path = str(raw.get("path", "")).strip()
    if not path:
        return None
    resolved = os.path.abspath(path)
    label = dock_file_label(resolved, str(raw.get("label", "")))
    added_at = raw.get("added_at")
    if not added_at:
        added_at = datetime.now().isoformat(timespec="seconds")
    return {
        "id": shortcut_id,
        "path": resolved,
        "label": label,
        "added_at": str(added_at),
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
    for key in ("always_on_top", "visible", "compact", "private", "user_resized"):
        note[key] = bool(note.get(key, NOTE_DEFAULTS[key]))
    note["content"] = str(note.get("content", ""))
    for ts in ("created_at", "modified_at"):
        if not note.get(ts):
            note[ts] = datetime.now().isoformat(timespec="seconds")
    return note
