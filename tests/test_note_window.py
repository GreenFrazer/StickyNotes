"""Unit tests for NoteWindow behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from stickynotes.models import private_preview_text
from stickynotes.storage import StorageManager
from stickynotes.ui.note_window import NoteWindow


@pytest.fixture
def note_window(qapp, qtbot, temp_paths) -> NoteWindow:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "Hello"
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()
    return w


def test_persist_debounce_fires(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    storage = w.storage
    w.editor.setPlainText("Updated content")
    qtbot.wait(600)
    notes = storage.get_all_notes()
    assert w.note_id in notes
    assert notes[w.note_id]["content"] == "Updated content"


def test_private_masking(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    w.note_data["private"] = True
    w._revealed = False
    w._apply_private_state()
    assert w._private_overlay.isVisible()
    assert w.editor.isReadOnly()
    assert private_preview_text() in w._overlay_lbl.text()


def test_compact_mode_hides_editor(note_window: NoteWindow) -> None:
    w = note_window
    w._set_compact(True)
    assert not w.editor.isVisible()
    assert w.height() <= w.TB + 10


def test_on_text_long_content_no_crash(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    w._editing = True
    long_text = "Word " * 5000 + "\n" * 200
    w.editor.setPlainText(long_text)
    w._on_text()
    qtbot.wait(50)
    assert w.height() > 0
