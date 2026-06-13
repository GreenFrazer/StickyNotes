"""Unit tests for StorageManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stickynotes.storage import StorageManager


class FakePaths:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def data_file(self) -> Path:
        return self._data_dir / "data.json"

    @property
    def backup_file(self) -> Path:
        return self._data_dir / "data.json.bak"

    @property
    def lock_file(self) -> Path:
        return self._data_dir / "app.lock"


@pytest.fixture
def temp_paths(tmp_path: Path) -> FakePaths:
    return FakePaths(tmp_path / "StickyNotesApp")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_save_creates_atomic_backup(temp_paths: FakePaths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Hello"
    storage.set_note(note["id"], note)
    note["content"] = "Hello updated"
    storage.set_note(note["id"], note)

    assert temp_paths.data_file.exists()
    assert temp_paths.backup_file.exists()

    loaded = json.loads(temp_paths.data_file.read_text(encoding="utf-8"))
    assert loaded["notes"][note["id"]]["content"] == "Hello updated"


def test_empty_note_not_persisted(temp_paths: FakePaths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "   "
    storage.set_note(note["id"], note)

    assert storage.get_all_notes() == {}
    if temp_paths.data_file.exists():
        data = json.loads(temp_paths.data_file.read_text(encoding="utf-8"))
        assert data.get("notes", {}) == {}


def test_load_migrates_left_right_dock_position(temp_paths: FakePaths) -> None:
    _write_json(
        temp_paths.data_file,
        {"notes": {}, "settings": {"dock_position": "left", "dark_mode": False}},
    )
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    assert storage.get_settings()["dock_position"] == "side"


def test_load_recovers_from_backup_when_main_corrupt(temp_paths: FakePaths) -> None:
    note = StorageManager.default_note()
    note["content"] = "Recovered"
    good = {
        "notes": {note["id"]: note},
        "settings": {"dock_position": "top", "dark_mode": False},
    }
    _write_json(temp_paths.backup_file, good)
    temp_paths.data_file.write_text("{not valid json", encoding="utf-8")

    storage = StorageManager(temp_paths, restore_prompt=lambda: True)
    assert note["id"] in storage.get_all_notes()
    assert storage.get_all_notes()[note["id"]]["content"] == "Recovered"


def test_load_skips_invalid_note_entries(temp_paths: FakePaths) -> None:
    valid = StorageManager.default_note()
    valid["content"] = "OK"
    _write_json(
        temp_paths.data_file,
        {
            "notes": {
                valid["id"]: valid,
                "bad": "not a dict",
            },
            "settings": {"dock_position": "top", "dark_mode": False},
        },
    )
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    notes = storage.get_all_notes()
    assert len(notes) == 1
    assert valid["id"] in notes
    assert "bad" not in notes


def test_atomic_write_uses_tmp_file(temp_paths: FakePaths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Atomic"
    storage.set_note(note["id"], note)

    assert not (temp_paths.data_dir / "data.json.tmp").exists()
    data = json.loads(temp_paths.data_file.read_text(encoding="utf-8"))
    assert data["notes"][note["id"]]["content"] == "Atomic"


def test_delete_note_removes_from_storage(temp_paths: FakePaths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Delete me"
    storage.set_note(note["id"], note)
    storage.delete_note(note["id"])
    assert storage.get_all_notes() == {}


def test_private_field_round_trips(temp_paths: FakePaths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Secret text"
    note["private"] = True
    storage.set_note(note["id"], note)

    loaded = StorageManager(temp_paths, restore_prompt=lambda: False)
    notes = loaded.get_all_notes()
    assert note["id"] in notes
    assert notes[note["id"]]["private"] is True
    assert notes[note["id"]]["content"] == "Secret text"


def test_normalize_note_defaults_private_false() -> None:
    from stickynotes.models import normalize_note

    note = normalize_note({"content": "x"}, "test-id")
    assert note is not None
    assert note["private"] is False
