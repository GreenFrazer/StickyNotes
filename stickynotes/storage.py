"""JSON persistence with atomic writes and backup recovery."""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtWidgets import QMessageBox

from stickynotes.models import (
    default_dock_shortcut,
    default_note,
    default_settings,
    normalize_dock_shortcut,
    normalize_note,
)
from stickynotes.platform import get_paths
from stickynotes.platform.base import PlatformPaths

logger = logging.getLogger(__name__)

ARCHIVE_FORMAT = "stickynotes"
ARCHIVE_VERSION = "1"


class StorageManager:
    def __init__(
        self,
        paths: PlatformPaths | None = None,
        *,
        restore_prompt: Callable[[], bool] | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self.filepath = self._paths.data_file
        self.backup_path = self._paths.backup_file
        self._restore_prompt = restore_prompt
        self._data: dict[str, Any] = {
            "notes": {},
            "settings": default_settings(),
            "dock_shortcuts": [],
        }
        self._saves_since_backup = 0
        self._last_serialized: str | None = None
        self._dirty = False
        self.load()

    @staticmethod
    def default_note(note_id: str | None = None) -> dict[str, Any]:
        return default_note(note_id)

    def _empty_data(self) -> dict[str, Any]:
        return {
            "notes": {},
            "settings": default_settings(),
            "dock_shortcuts": [],
        }

    def _read_json_file(self, path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise json.JSONDecodeError("root must be object", "", 0)
        return raw

    def _normalize_loaded(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = self._empty_data()
        settings = raw.get("settings")
        if isinstance(settings, dict):
            data["settings"].update(settings)
        for key, val in default_settings().items():
            data["settings"].setdefault(key, val)
        dp = data["settings"].get("dock_position", "top")
        if dp in ("left", "right"):
            data["settings"]["dock_position"] = "side"
        notes_in = raw.get("notes", {})
        if not isinstance(notes_in, dict):
            notes_in = {}
        for nid, nd in notes_in.items():
            if not isinstance(nid, str):
                continue
            normalized = normalize_note(nd if isinstance(nd, dict) else {}, nid)
            if normalized:
                data["notes"][nid] = normalized
            else:
                logger.warning("Skipping invalid note entry: %s", nid)
        shortcuts_in = raw.get("dock_shortcuts", [])
        if not isinstance(shortcuts_in, list):
            shortcuts_in = []
        for entry in shortcuts_in:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("id")
            if not isinstance(sid, str) or not sid:
                continue
            normalized = normalize_dock_shortcut(entry, sid)
            if normalized:
                data["dock_shortcuts"].append(normalized)
            else:
                logger.warning("Skipping invalid dock shortcut entry: %s", sid)
        return data

    def _try_restore_backup(self) -> bool:
        if not self.backup_path.exists():
            return False
        try:
            raw = self._read_json_file(self.backup_path)
            self._data = self._normalize_loaded(raw)
            self.save()
            return True
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Backup restore failed: %s", exc)
            return False

    def _offer_backup_restore(self) -> bool:
        if self._restore_prompt is not None:
            if self._restore_prompt():
                return self._try_restore_backup()
            return False
        reply = QMessageBox.question(
            None,
            "Sticky Notes — Data Error",
            "Your notes file could not be read. Restore from the last backup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            return self._try_restore_backup()
        return False

    def _serialize(self) -> str:
        return json.dumps(self._data, indent=2, ensure_ascii=False)

    def _mark_clean(self) -> None:
        self._last_serialized = None
        self._dirty = False

    def load(self) -> None:
        if not self.filepath.exists():
            self._data = self._empty_data()
            self._mark_clean()
            return
        try:
            raw = self._read_json_file(self.filepath)
            self._data = self._normalize_loaded(raw)
            self._mark_clean()
        except json.JSONDecodeError as exc:
            logger.error("Corrupt data.json: %s", exc)
            if self._offer_backup_restore():
                return
            self._data = self._empty_data()
            self._mark_clean()
        except OSError as exc:
            logger.error("Cannot read data.json: %s", exc)
            self._data = self._empty_data()
            self._mark_clean()

    def save(self) -> None:
        if not self._dirty:
            return
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        serialized = self._serialize()
        if serialized == self._last_serialized:
            self._dirty = False
            return
        tmp = self.filepath.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(serialized)
                f.flush()
                os.fsync(f.fileno())
            self._saves_since_backup += 1
            if self.filepath.exists() and (
                not self.backup_path.exists() or self._saves_since_backup >= 5
            ):
                shutil.copy2(self.filepath, self.backup_path)
                self._saves_since_backup = 0
            os.replace(tmp, self.filepath)
            self._last_serialized = serialized
            self._dirty = False
        except OSError:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

    def get_all_notes(self) -> dict[str, dict[str, Any]]:
        return {
            nid: nd
            for nid, nd in self._data.get("notes", {}).items()
            if nd.get("content", "").strip()
        }

    def set_note(self, nid: str, data: dict[str, Any]) -> None:
        if not data.get("content", "").strip():
            self.delete_note(nid)
            return
        stored = dict(data)
        existing = self._data.get("notes", {}).get(nid)
        if existing == stored:
            return
        self._data.setdefault("notes", {})[nid] = stored
        self._dirty = True
        self.save()

    def delete_note(self, nid: str) -> None:
        if nid not in self._data.get("notes", {}):
            return
        self._data.get("notes", {}).pop(nid, None)
        self._dirty = True
        self.save()

    def get_settings(self) -> dict[str, Any]:
        return dict(self._data.get("settings", default_settings()))

    def set_settings(self, settings: dict[str, Any]) -> None:
        if self._data.get("settings") == settings:
            return
        self._data["settings"] = settings
        self._dirty = True
        self.save()

    def get_dock_shortcuts(self) -> list[dict[str, Any]]:
        shortcuts = self._data.get("dock_shortcuts", [])
        if not isinstance(shortcuts, list):
            return []
        return [dict(s) for s in shortcuts if isinstance(s, dict)]

    def add_dock_shortcut(
        self, path: str, label: str | None = None
    ) -> dict[str, Any]:
        shortcut = default_dock_shortcut(path=path, label=label)
        self._data.setdefault("dock_shortcuts", []).append(shortcut)
        self._dirty = True
        self.save()
        return dict(shortcut)

    def remove_dock_shortcut(self, shortcut_id: str) -> None:
        shortcuts = self._data.get("dock_shortcuts", [])
        if not isinstance(shortcuts, list):
            return
        self._data["dock_shortcuts"] = [
            s for s in shortcuts if isinstance(s, dict) and s.get("id") != shortcut_id
        ]
        self._dirty = True
        self.save()

    def get_all_stored_notes(self) -> dict[str, dict[str, Any]]:
        """All notes with non-empty content (includes hidden notes)."""
        return self.get_all_notes()

    def export_data_json(self) -> str:
        return self._serialize()

    def export_archive(self, dest: Path) -> None:
        """Write data.json or a .stickynotes zip archive."""
        dest = Path(dest)
        serialized = self._serialize()
        if dest.suffix.lower() == ".stickynotes":
            metadata = {
                "format": ARCHIVE_FORMAT,
                "version": ARCHIVE_VERSION,
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "note_count": len(self._data.get("notes", {})),
            }
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("data.json", serialized)
                zf.writestr(
                    "metadata.json",
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                )
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(serialized, encoding="utf-8")

    @staticmethod
    def _read_import_payload(path: Path) -> dict[str, Any]:
        path = Path(path)
        if path.suffix.lower() == ".stickynotes" or zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, "r") as zf:
                if "data.json" not in zf.namelist():
                    raise ValueError("Invalid archive: missing data.json")
                raw = zf.read("data.json").decode("utf-8")
                return json.loads(raw)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("Import file must contain a JSON object")
        return raw

    def preview_import(self, path: Path) -> dict[str, Any]:
        """Return note counts for import preview."""
        incoming = self._normalize_loaded(self._read_import_payload(path))
        incoming_ids = set(incoming.get("notes", {}))
        existing_ids = set(self._data.get("notes", {}))
        overlap = incoming_ids & existing_ids
        conflicts = 0
        for nid in overlap:
            ex = self._data["notes"][nid]
            inc = incoming["notes"][nid]
            if ex.get("modified_at", "") != inc.get("modified_at", ""):
                conflicts += 1
        return {
            "incoming_count": len(incoming_ids),
            "existing_count": len(existing_ids),
            "overlap_count": len(overlap),
            "conflict_count": conflicts,
        }

    def _merge_notes(self, incoming: dict[str, Any]) -> dict[str, int]:
        added = merged = kept = 0
        for nid, nd in incoming.get("notes", {}).items():
            existing = self._data.get("notes", {}).get(nid)
            if existing:
                if nd.get("modified_at", "") > existing.get("modified_at", ""):
                    self._data["notes"][nid] = nd
                    merged += 1
                else:
                    kept += 1
            else:
                self._data.setdefault("notes", {})[nid] = nd
                added += 1
        incoming_shortcuts = incoming.get("dock_shortcuts", [])
        if isinstance(incoming_shortcuts, list) and incoming_shortcuts:
            seen = {
                s.get("path")
                for s in self._data.get("dock_shortcuts", [])
                if isinstance(s, dict)
            }
            for entry in incoming_shortcuts:
                if not isinstance(entry, dict):
                    continue
                path = entry.get("path")
                if path and path not in seen:
                    self._data.setdefault("dock_shortcuts", []).append(entry)
                    seen.add(path)
        return {"added": added, "merged": merged, "kept": kept}

    def import_data(self, path: Path, *, merge: bool = True) -> dict[str, Any]:
        """Import JSON or .stickynotes zip; merge prefers newer modified_at."""
        incoming = self._normalize_loaded(self._read_import_payload(path))
        if merge:
            stats = self._merge_notes(incoming)
            stats["mode"] = "merge"
            stats["note_count"] = len(self._data.get("notes", {}))
        else:
            self._data = incoming
            stats = {
                "mode": "replace",
                "note_count": len(incoming.get("notes", {})),
            }
        self._dirty = True
        self.save()
        return stats

    def list_backups(self) -> list[dict[str, Any]]:
        backups: list[dict[str, Any]] = []
        if self.backup_path.exists():
            stat = self.backup_path.stat()
            backups.append(
                {
                    "path": str(self.backup_path),
                    "name": self.backup_path.name,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(
                        timespec="seconds"
                    ),
                    "size": stat.st_size,
                }
            )
        return backups

    def restore_from_backup(self, backup_path: Path | None = None) -> bool:
        path = Path(backup_path) if backup_path else self.backup_path
        if not path.is_file():
            return False
        try:
            raw = self._read_json_file(path)
            self._data = self._normalize_loaded(raw)
            self._dirty = True
            self.save()
            return True
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Backup restore failed: %s", exc)
            return False
