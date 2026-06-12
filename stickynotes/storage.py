"""JSON persistence with atomic writes and backup recovery."""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtWidgets import QMessageBox

from stickynotes.models import default_note, default_settings, normalize_note
from stickynotes.platform import get_paths
from stickynotes.platform.base import PlatformPaths

logger = logging.getLogger(__name__)


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
        self._data: dict[str, Any] = {"notes": {}, "settings": default_settings()}
        self.load()

    @staticmethod
    def default_note(note_id: str | None = None) -> dict[str, Any]:
        return default_note(note_id)

    def _empty_data(self) -> dict[str, Any]:
        return {"notes": {}, "settings": default_settings()}

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

    def load(self) -> None:
        if not self.filepath.exists():
            self._data = self._empty_data()
            return
        try:
            raw = self._read_json_file(self.filepath)
            self._data = self._normalize_loaded(raw)
        except json.JSONDecodeError as exc:
            logger.error("Corrupt data.json: %s", exc)
            if self._offer_backup_restore():
                return
            self._data = self._empty_data()
        except OSError as exc:
            logger.error("Cannot read data.json: %s", exc)
            self._data = self._empty_data()

    def save(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.filepath.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if self.filepath.exists():
                shutil.copy2(self.filepath, self.backup_path)
            os.replace(tmp, self.filepath)
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
        self._data.setdefault("notes", {})[nid] = data
        self.save()

    def delete_note(self, nid: str) -> None:
        self._data.get("notes", {}).pop(nid, None)
        self.save()

    def get_settings(self) -> dict[str, Any]:
        return dict(self._data.get("settings", default_settings()))

    def set_settings(self, settings: dict[str, Any]) -> None:
        self._data["settings"] = settings
        self.save()
