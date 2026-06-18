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


MIN_DOCK_WIDTH = 56
MAX_DOCK_WIDTH = 280


def clamp_dock_width(width: int | float) -> int:
    try:
        w = int(width)
    except (TypeError, ValueError):
        w = MIN_DOCK_WIDTH
    return max(MIN_DOCK_WIDTH, min(MAX_DOCK_WIDTH, w))


def default_settings() -> dict[str, Any]:
    return {
        "dock_position": "top",
        "dark_mode": False,
        "default_tag": "",
        "dock_width": MIN_DOCK_WIDTH,
        "dock_order": [],
    }


def normalize_dock_order(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    order: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        item_id = item.strip()
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        order.append(item_id)
    return order


def default_dock_item_order(
    shortcut_ids: list[str],
    note_ids: list[str],
    shortcuts_by_id: dict[str, dict[str, Any]],
    notes_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Legacy dock order: pinned files first, then notes by most recently modified."""
    sorted_shortcuts = sorted(
        shortcut_ids,
        key=lambda sid: shortcuts_by_id.get(sid, {}).get("added_at", ""),
    )
    sorted_notes = sorted(
        note_ids,
        key=lambda nid: notes_by_id.get(nid, {}).get("modified_at", ""),
        reverse=True,
    )
    return sorted_shortcuts + sorted_notes


def ordered_dock_item_ids(
    order: list[str],
    shortcut_ids: list[str],
    note_ids: list[str],
    shortcuts_by_id: dict[str, dict[str, Any]],
    notes_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Merge saved dock order with visible items; append new items in default order."""
    visible = set(shortcut_ids) | set(note_ids)
    normalized = normalize_dock_order(order)
    result: list[str] = []
    seen: set[str] = set()
    for item_id in normalized:
        if item_id in visible and item_id not in seen:
            result.append(item_id)
            seen.add(item_id)
    default_remaining = default_dock_item_order(
        [sid for sid in shortcut_ids if sid not in seen],
        [nid for nid in note_ids if nid not in seen],
        shortcuts_by_id,
        notes_by_id,
    )
    result.extend(default_remaining)
    return result


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
        "grip_resized": False,
        "tags": [],
        "checklist": False,
        "reminder_at": None,
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
    "grip_resized": False,
    "tags": [],
    "checklist": False,
    "reminder_at": None,
}


def is_private(note: dict) -> bool:
    return bool(note.get("private"))


def private_preview_text() -> str:
    return "Private note — hold to reveal"


def dock_popup_preview_text() -> str:
    return "Private note — hover copy still works"


def normalize_tags(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    tags: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        tag = item.strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def parse_checklist(content: str) -> list[tuple[bool, str]]:
    """Parse markdown-style checklist lines: '- [ ] item' / '- [x] item'."""
    items: list[tuple[bool, str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if len(stripped) < 6:
            continue
        if stripped.startswith("- [ ] "):
            items.append((False, stripped[6:]))
        elif stripped.startswith("- [x] ") or stripped.startswith("- [X] "):
            items.append((True, stripped[6:]))
    return items


def checklist_progress(content: str) -> tuple[int, int]:
    items = parse_checklist(content)
    if not items:
        return 0, 0
    done = sum(1 for checked, _ in items if checked)
    return done, len(items)


def content_has_checklist_items(content: str) -> bool:
    return bool(parse_checklist(content))


def note_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:80]
    return ""


def dock_indicator_text(note: dict) -> str:
    if is_private(note):
        return "\U0001F512"
    content = note.get("content", "").strip()
    if note.get("checklist") or content_has_checklist_items(content):
        done, total = checklist_progress(content)
        if total:
            clock = "\u23F0" if note.get("reminder_at") else ""
            return f"{clock}{done}/{total}" if clock else f"{done}/{total}"
    if note.get("reminder_at"):
        return "\u23F0"
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
    for key in ("always_on_top", "visible", "compact", "private", "user_resized", "grip_resized"):
        note[key] = bool(note.get(key, NOTE_DEFAULTS[key]))
    note["content"] = str(note.get("content", ""))
    note["tags"] = normalize_tags(note.get("tags", []))
    note["checklist"] = bool(note.get("checklist", NOTE_DEFAULTS["checklist"]))
    if not note["checklist"] and content_has_checklist_items(note["content"]):
        note["checklist"] = True
    reminder = note.get("reminder_at")
    if reminder in (None, "", "null"):
        note["reminder_at"] = None
    else:
        note["reminder_at"] = str(reminder)
    for ts in ("created_at", "modified_at"):
        if not note.get(ts):
            note[ts] = datetime.now().isoformat(timespec="seconds")
    return note
