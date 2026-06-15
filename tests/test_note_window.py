"""Unit tests for NoteWindow behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest

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


def test_private_hold_to_reveal(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    w.note_data["private"] = True
    w._revealed = False
    w._apply_private_state()
    QTest.mousePress(w._private_overlay, Qt.MouseButton.LeftButton)
    assert not w._private_overlay.isVisible()
    assert w._revealed
    assert w.editor.isReadOnly()
    QTest.mouseRelease(w._private_overlay, Qt.MouseButton.LeftButton)
    assert w._private_overlay.isVisible()
    assert not w._revealed


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


def test_private_toggle_persists_from_storage_dict(
    qapp, qtbot, temp_paths
) -> None:
    """Loaded notes share storage dicts; private must still save to disk."""
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "Secret plans"
    storage.set_note(nd["id"], nd)

    loaded = storage.get_all_notes()[nd["id"]]
    w = NoteWindow(loaded, storage)
    qtbot.addWidget(w)
    w.show()

    w._set_private(True)

    reloaded = StorageManager(temp_paths, restore_prompt=lambda: False)
    assert reloaded.get_all_notes()[nd["id"]]["private"] is True


def test_tags_edit_persists_from_storage_dict(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "Tagged note"
    storage.set_note(nd["id"], nd)

    loaded = storage.get_all_notes()[nd["id"]]
    w = NoteWindow(loaded, storage)
    qtbot.addWidget(w)
    w.show()

    w.note_data["tags"] = ["work", "urgent"]
    w._update_tag_chip()
    w._persist()

    reloaded = StorageManager(temp_paths, restore_prompt=lambda: False)
    assert reloaded.get_all_notes()[nd["id"]]["tags"] == ["work", "urgent"]


def test_close_short_click_hides(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    w.editor.setPlainText("Keep me")
    deleted: list[str] = []
    w.request_delete.connect(deleted.append)

    QTest.mousePress(w.btn_close, Qt.MouseButton.LeftButton)
    QTest.mouseRelease(w.btn_close, Qt.MouseButton.LeftButton)
    qtbot.wait(100)

    assert not w.isVisible()
    assert w.note_data["visible"] is False
    assert deleted == []
    assert w.note_id in w.storage.get_all_notes()


def test_close_long_press_deletes(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    w.editor.setPlainText("Delete me")

    with qtbot.waitSignal(w.request_delete, timeout=1000) as blocker:
        QTest.mousePress(w.btn_close, Qt.MouseButton.LeftButton)
        qtbot.wait(650)
        QTest.mouseRelease(w.btn_close, Qt.MouseButton.LeftButton)

    assert blocker.args == [w.note_id]


def test_close_long_press_cancelled(note_window: NoteWindow, qtbot) -> None:
    w = note_window
    w.editor.setPlainText("Stay visible")
    deleted: list[str] = []
    w.request_delete.connect(deleted.append)

    QTest.mousePress(w.btn_close, Qt.MouseButton.LeftButton)
    qtbot.wait(650)
    assert w._close_delete_armed
    QTest.mouseRelease(
        w.btn_close,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(-5, -5),
    )
    qtbot.wait(100)

    assert deleted == []
    assert w.isVisible()
    assert w.note_data.get("visible", True) is not False


def test_colour_change_persists_from_storage_dict(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "Colour me"
    storage.set_note(nd["id"], nd)

    loaded = storage.get_all_notes()[nd["id"]]
    w = NoteWindow(loaded, storage)
    qtbot.addWidget(w)
    w.show()

    w._change_colour("blue")

    reloaded = StorageManager(temp_paths, restore_prompt=lambda: False)
    assert reloaded.get_all_notes()[nd["id"]]["colour"] == "blue"

