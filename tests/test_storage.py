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


def test_normalize_dock_shortcut_defaults_label_from_filename() -> None:
    from stickynotes.models import normalize_dock_shortcut

    shortcut = normalize_dock_shortcut(
        {"path": "/tmp/Q1 Report.docx", "added_at": "2026-06-13T10:00:00"},
        "shortcut-1",
    )
    assert shortcut is not None
    assert shortcut["id"] == "shortcut-1"
    assert shortcut["path"].endswith("Q1 Report.docx")
    assert shortcut["label"] == "Q1 Report"
    assert shortcut["added_at"] == "2026-06-13T10:00:00"


def test_normalize_dock_shortcut_rejects_empty_path() -> None:
    from stickynotes.models import normalize_dock_shortcut

    assert normalize_dock_shortcut({"path": ""}, "shortcut-1") is None
    assert normalize_dock_shortcut({"path": "   "}, "shortcut-1") is None


def test_dock_file_badge_maps_extensions() -> None:
    from stickynotes.models import dock_file_badge

    assert dock_file_badge("/tmp/report.docx") == "DOC"
    assert dock_file_badge("/tmp/data.xlsx") == "XLS"
    assert dock_file_badge("/tmp/sheet.pdf") == "PDF"


def test_load_persists_dock_shortcuts(temp_paths: FakePaths) -> None:
    _write_json(
        temp_paths.data_file,
        {
            "notes": {},
            "settings": {"dock_position": "top", "dark_mode": False},
            "dock_shortcuts": [
                {
                    "id": "s1",
                    "path": "/tmp/report.docx",
                    "label": "Q1 Report",
                    "added_at": "2026-06-13T10:00:00",
                }
            ],
        },
    )
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    shortcuts = storage.get_dock_shortcuts()
    assert len(shortcuts) == 1
    assert shortcuts[0]["id"] == "s1"
    assert shortcuts[0]["label"] == "Q1 Report"


def test_load_skips_invalid_dock_shortcuts(temp_paths: FakePaths) -> None:
    _write_json(
        temp_paths.data_file,
        {
            "notes": {},
            "settings": {"dock_position": "top", "dark_mode": False},
            "dock_shortcuts": [
                {
                    "id": "good",
                    "path": "/tmp/valid.pdf",
                    "label": "Valid",
                    "added_at": "2026-06-13T10:00:00",
                },
                {"id": "bad", "path": ""},
                "not a dict",
            ],
        },
    )
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    shortcuts = storage.get_dock_shortcuts()
    assert len(shortcuts) == 1
    assert shortcuts[0]["id"] == "good"


def test_add_and_remove_dock_shortcut(temp_paths: FakePaths, tmp_path: Path) -> None:
    doc = tmp_path / "budget.xlsx"
    doc.write_text("data", encoding="utf-8")
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)

    added = storage.add_dock_shortcut(str(doc))
    assert added["path"] == str(doc.resolve())
    assert added["label"] == "budget"
    assert len(storage.get_dock_shortcuts()) == 1

    loaded = json.loads(temp_paths.data_file.read_text(encoding="utf-8"))
    assert len(loaded["dock_shortcuts"]) == 1
    assert loaded["dock_shortcuts"][0]["label"] == "budget"

    storage.remove_dock_shortcut(added["id"])
    assert storage.get_dock_shortcuts() == []
    reloaded = json.loads(temp_paths.data_file.read_text(encoding="utf-8"))
    assert reloaded.get("dock_shortcuts", []) == []


def test_save_includes_empty_dock_shortcuts_array(temp_paths: FakePaths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Hello"
    storage.set_note(note["id"], note)

    data = json.loads(temp_paths.data_file.read_text(encoding="utf-8"))
    assert data.get("dock_shortcuts") == []


def test_dock_pin_extensions_and_dialog_filter() -> None:
    from stickynotes.models import DOCK_PIN_EXTENSIONS, dock_pin_dialog_filters

    assert ".docx" in DOCK_PIN_EXTENSIONS
    assert ".pdf" in DOCK_PIN_EXTENSIONS
    assert ".csv" in DOCK_PIN_EXTENSIONS
    filters = dock_pin_dialog_filters()
    assert "*.docx" in filters
    assert "All files (*)" in filters


def test_is_dock_pinnable_file(tmp_path: Path) -> None:
    from stickynotes.models import is_dock_pinnable_file

    doc = tmp_path / "notes.txt"
    doc.write_text("hello", encoding="utf-8")
    assert is_dock_pinnable_file(str(doc)) is True
    assert is_dock_pinnable_file(str(tmp_path / "missing.pdf")) is False
    assert is_dock_pinnable_file("") is False


def test_filter_new_dock_paths_skips_duplicates(
    temp_paths: FakePaths, tmp_path: Path
) -> None:
    from stickynotes.app_manager import AppManager

    doc_a = tmp_path / "a.pdf"
    doc_b = tmp_path / "b.csv"
    doc_a.write_text("a", encoding="utf-8")
    doc_b.write_text("b", encoding="utf-8")
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    storage.add_dock_shortcut(str(doc_a))

    new_paths = AppManager.filter_new_dock_paths(
        [str(doc_a), str(doc_b), str(doc_a)],
        storage.get_dock_shortcuts(),
    )
    assert new_paths == [str(doc_b.resolve())]
