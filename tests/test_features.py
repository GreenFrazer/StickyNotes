"""Tests for export/import, checklist, tags, search, and reminders."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from stickynotes.models import (
    checklist_progress,
    content_has_checklist_items,
    dock_indicator_text,
    normalize_note,
    normalize_tags,
    parse_checklist,
)
from stickynotes.reminders import ReminderService
from stickynotes.storage import StorageManager
from stickynotes.ui.search_dialog import SearchDialog


def test_normalize_tags_lowercase_deduped() -> None:
    assert normalize_tags(["Work", "work", " Personal "]) == ["work", "personal"]


def test_normalize_note_adds_tags_checklist_reminder_defaults() -> None:
    note = normalize_note({"content": "hello"}, "id-1")
    assert note is not None
    assert note["tags"] == []
    assert note["checklist"] is False
    assert note["reminder_at"] is None


def test_normalize_note_auto_detects_checklist() -> None:
    note = normalize_note({"content": "- [ ] one\n- [x] two"}, "id-2")
    assert note is not None
    assert note["checklist"] is True


def test_parse_checklist_and_progress() -> None:
    content = "- [ ] milk\n- [x] eggs\n- [ ] bread"
    items = parse_checklist(content)
    assert items == [(False, "milk"), (True, "eggs"), (False, "bread")]
    assert checklist_progress(content) == (1, 3)
    assert content_has_checklist_items(content)


def test_dock_indicator_checklist_and_reminder() -> None:
    note = {
        "content": "- [ ] a\n- [x] b",
        "checklist": True,
        "private": False,
        "reminder_at": "2099-01-01T09:00:00",
    }
    assert dock_indicator_text(note) == "\u23F01/2"


def test_export_import_json_round_trip(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Exported note"
    note["tags"] = ["work"]
    storage.set_note(note["id"], note)

    export_path = temp_paths.data_dir / "export.json"
    storage.export_archive(export_path)
    assert export_path.exists()

    other = StorageManager(temp_paths, restore_prompt=lambda: False)
    other.delete_note(note["id"])
    assert note["id"] not in other.get_all_notes()

    stats = other.import_data(export_path, merge=False)
    assert stats["mode"] == "replace"
    loaded = other.get_all_notes()[note["id"]]
    assert loaded["content"] == "Exported note"
    assert loaded["tags"] == ["work"]


def test_export_import_zip_round_trip(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Zip note"
    storage.set_note(note["id"], note)

    zip_path = temp_paths.data_dir / "backup.stickynotes"
    storage.export_archive(zip_path)
    assert zipfile.is_zipfile(zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert "data.json" in zf.namelist()
        assert "metadata.json" in zf.namelist()

    other = StorageManager(temp_paths, restore_prompt=lambda: False)
    other.import_data(zip_path, merge=True)
    assert other.get_all_notes()[note["id"]]["content"] == "Zip note"


def test_import_merge_prefers_newer_modified_at(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Local newer"
    note["modified_at"] = "2026-06-15T12:00:00"
    storage.set_note(note["id"], note)

    incoming = {
        "notes": {
            note["id"]: {
                **note,
                "content": "Incoming older",
                "modified_at": "2026-06-14T12:00:00",
            }
        },
        "settings": storage.get_settings(),
        "dock_shortcuts": [],
    }
    path = temp_paths.data_dir / "incoming.json"
    path.write_text(json.dumps(incoming), encoding="utf-8")

    stats = storage.import_data(path, merge=True)
    assert stats["kept"] == 1
    assert storage.get_all_notes()[note["id"]]["content"] == "Local newer"


def test_import_merge_takes_incoming_when_newer(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Local older"
    note["modified_at"] = "2026-06-14T12:00:00"
    storage.set_note(note["id"], note)

    incoming = {
        "notes": {
            note["id"]: {
                **note,
                "content": "Incoming newer",
                "modified_at": "2026-06-15T12:00:00",
            }
        },
        "settings": storage.get_settings(),
        "dock_shortcuts": [],
    }
    path = temp_paths.data_dir / "incoming.json"
    path.write_text(json.dumps(incoming), encoding="utf-8")

    stats = storage.import_data(path, merge=True)
    assert stats["merged"] == 1
    assert storage.get_all_notes()[note["id"]]["content"] == "Incoming newer"


def test_list_backups_and_restore(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    note = StorageManager.default_note()
    note["content"] = "Original"
    storage.set_note(note["id"], note)
    note["content"] = "Updated"
    storage.set_note(note["id"], note)

    backups = storage.list_backups()
    assert len(backups) == 1
    assert backups[0]["name"] == "data.json.bak"

    storage.delete_note(note["id"])
    assert storage.restore_from_backup()
    assert storage.get_all_notes()[note["id"]]["content"] == "Original"


def test_import_rejects_invalid_archive(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    bad = temp_paths.data_dir / "bad.stickynotes"
    bad.write_bytes(b"not a zip")
    with pytest.raises(Exception):
        storage.import_data(bad, merge=True)


def test_reminder_service_detects_overdue() -> None:
    past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    future = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
    assert ReminderService.is_overdue(past) is True
    assert ReminderService.is_overdue(future) is False


def test_reminder_service_poll_emits_due(qapp, qtbot) -> None:
    fired: list[str] = []
    notes = {
        "n1": {
            "content": "Due task",
            "reminder_at": (datetime.now() - timedelta(seconds=1)).isoformat(
                timespec="seconds"
            ),
        }
    }
    svc = ReminderService(lambda: notes)
    svc.reminder_due.connect(lambda nid, _nd: fired.append(nid))
    svc._poll()
    assert fired == ["n1"]


def test_reminder_presets_minute_offsets() -> None:
    presets = ReminderService.reminder_presets()
    assert [label for label, _ in presets] == [
        "In 5 minutes",
        "In 10 minutes",
        "In 15 minutes",
        "In 30 minutes",
        "In 60 minutes",
    ]
    assert [minutes for _, minutes in presets] == [5, 10, 15, 30, 60]


def test_reminder_at_offset_from_now() -> None:
    before = datetime.now()
    due = ReminderService.reminder_at_offset(10)
    after = datetime.now()
    assert before + timedelta(minutes=10) <= due <= after + timedelta(minutes=10)


def test_reminder_service_refires_after_new_future_reminder(qapp, qtbot) -> None:
    fired: list[str] = []
    notes: dict[str, dict] = {
        "n1": {
            "content": "Task",
            "reminder_at": (datetime.now() - timedelta(seconds=1)).isoformat(
                timespec="seconds"
            ),
        }
    }
    svc = ReminderService(lambda: notes)
    svc.reminder_due.connect(lambda nid, _nd: fired.append(nid))
    svc._poll()
    assert fired == ["n1"]
    svc._poll()
    assert fired == ["n1"]
    notes["n1"]["reminder_at"] = (
        datetime.now() + timedelta(minutes=5)
    ).isoformat(timespec="seconds")
    svc._poll()
    assert fired == ["n1"]
    notes["n1"]["reminder_at"] = (
        datetime.now() - timedelta(seconds=1)
    ).isoformat(timespec="seconds")
    svc._poll()
    assert fired == ["n1", "n1"]


def test_search_dialog_finds_content(qapp, qtbot) -> None:
    note = StorageManager.default_note()
    note["content"] = "Find me alpha beta"
    notes = {note["id"]: note}

    dlg = SearchDialog(notes, lambda nid: notes[nid]["content"])
    qtbot.addWidget(dlg)
    dlg._input.setText("alpha")
    qtbot.wait(400)
    assert dlg._results.count() == 1


def test_search_dialog_finds_tags(qapp, qtbot) -> None:
    note = StorageManager.default_note()
    note["content"] = "Unrelated body text"
    note["tags"] = ["work", "urgent"]
    notes = {note["id"]: note}

    dlg = SearchDialog(notes, lambda nid: notes[nid]["content"])
    qtbot.addWidget(dlg)
    dlg._input.setText("urgent")
    qtbot.wait(400)
    assert dlg._results.count() == 1
    assert "Tags: #urgent" in dlg._results.item(0).text()


def test_search_dialog_masks_private_until_selected(qapp, qtbot) -> None:
    note = StorageManager.default_note()
    note["content"] = "Secret keyword"
    note["private"] = True
    notes = {note["id"]: note}

    dlg = SearchDialog(notes, lambda nid: notes[nid]["content"])
    qtbot.addWidget(dlg)
    dlg._input.setText("keyword")
    qtbot.wait(400)
    assert dlg._results.count() == 1
    item = dlg._results.item(0)
    assert "Private" in item.text()


def test_search_dialog_tolerates_invalid_tags_and_content(qapp, qtbot) -> None:
    note = StorageManager.default_note()
    note["content"] = "Find me alpha"
    note["tags"] = [123, "work"]
    notes = {note["id"]: note}

    dlg = SearchDialog(notes, lambda nid: notes[nid].get("content"))
    qtbot.addWidget(dlg)
    dlg._input.setText("alpha")
    qtbot.wait(400)
    assert dlg._results.count() == 1

    dlg._input.setText("work")
    qtbot.wait(400)
    assert dlg._results.count() == 1


def test_search_dialog_show_and_focus_reentrant(qapp, qtbot) -> None:
    note = StorageManager.default_note()
    note["content"] = "Find me alpha beta"
    notes = {note["id"]: note}

    dlg = SearchDialog(notes, lambda nid: notes[nid]["content"])
    qtbot.addWidget(dlg)
    for _ in range(5):
        dlg.show_and_focus()
        qtbot.wait(10)
    assert dlg.isVisible()
    assert dlg._input.text() == ""
