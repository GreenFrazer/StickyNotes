"""Checklist mode tests for NoteWindow."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt

from stickynotes.storage import StorageManager
from stickynotes.theme import NOTE_COLOURS
from stickynotes.ui.note_window import NoteWindow


@pytest.fixture
def checklist_note(qapp, qtbot, temp_paths) -> NoteWindow:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "- [ ] one\n- [x] two"
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()
    return w


def test_checklist_mode_persists(checklist_note: NoteWindow, qtbot) -> None:
    w = checklist_note
    item = w.checklist_widget.item(1)
    assert item is not None
    item.setCheckState(Qt.CheckState.Unchecked)
    qtbot.wait(600)
    stored = w.storage.get_all_notes()[w.note_id]
    assert "- [ ] two" in stored["content"]


def test_clear_completed_removes_checked_items(checklist_note: NoteWindow, qtbot) -> None:
    w = checklist_note
    w._clear_completed_checklist()
    qtbot.wait(600)
    stored = w.storage.get_all_notes()[w.note_id]
    assert "[x]" not in stored["content"]
    assert "- [ ] one" in stored["content"]


def test_empty_checklist_seeds_editable_item(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    w._set_checklist_mode(True)

    assert w.checklist_widget.isVisible()
    assert not w.editor.isVisible()
    assert w.checklist_widget.count() == 1
    item = w.checklist_widget.item(0)
    assert item is not None
    assert item.checkState() == Qt.CheckState.Unchecked
    assert item.flags() & Qt.ItemFlag.ItemIsEditable


def test_checklist_widget_uses_note_background(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["colour"] = "blue"
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    expected_bg = NOTE_COLOURS["blue"]
    stylesheet = w.styleSheet()
    assert expected_bg in stylesheet
    assert "#checklistWidget" in stylesheet
