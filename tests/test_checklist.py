"""Checklist mode tests for NoteWindow."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit

from stickynotes.storage import StorageManager
from stickynotes.theme import NOTE_COLOURS
from stickynotes.ui.note_window import NoteWindow


def _checklist_editor(w: NoteWindow) -> QLineEdit | None:
    for editor in w.checklist_widget.findChildren(QLineEdit):
        if editor.isVisible():
            return editor
    return None


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
    assert "#checklistBody" in stylesheet
    assert "#checklistWidget" in stylesheet
    assert "#checklistWidget::viewport" in stylesheet
    assert "#addChecklistItemBtn" in stylesheet
    assert "background:transparent" not in stylesheet.split("#addChecklistItemBtn")[1].split("}")[0]


def test_checklist_surfaces_are_opaque(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["colour"] = "yellow"
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    expected_bg = NOTE_COLOURS["yellow"]
    assert w.checklist_body.isVisible()
    assert expected_bg in w.checklist_body.styleSheet() or expected_bg in w.styleSheet()
    assert w.checklist_widget.autoFillBackground()
    assert w.checklist_widget.viewport().autoFillBackground()
    assert w.btn_add_checklist_item.isFlat()
    btn_style = w.styleSheet().split("#addChecklistItemBtn")[1]
    assert f"background:{expected_bg}" in btn_style


def test_checklist_height_tracks_item_count(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "- [ ] one\n- [ ] two"
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    h2 = w._checklist_content_height()
    w._add_checklist_item()
    qtbot.wait(50)
    h3 = w._checklist_content_height()
    assert w.checklist_widget.count() == 3
    assert h3 > h2


def test_checklist_window_grows_with_items(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    nd["height"] = 180
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()
    qtbot.wait(50)

    h0 = w.height()
    for _ in range(5):
        w._add_checklist_item()
        qtbot.wait(50)

    chrome = w._chrome_height()
    body = w.height() - chrome
    content = w.checklist_widget.height() + w.btn_add_checklist_item.height()
    assert w.height() > h0, "checklist note should grow as items are added"
    assert body >= content, "checklist body should fit all items without clipping"


def test_checklist_five_items_fit_on_init(qapp, qtbot, temp_paths) -> None:
    """Loaded checklist notes must expand on show without clipping rows or footer."""
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    nd["content"] = "\n".join(f"- [ ] item{i}" for i in range(5))
    nd["height"] = 180
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()
    qtbot.wait(50)

    assert w.checklist_widget.count() == 5
    assert w.checklist_widget.height() >= w._checklist_content_height()
    body = w.height() - w._chrome_height()
    content = w.checklist_widget.height() + w.btn_add_checklist_item.height()
    assert body >= content, "checklist body should fit all items and add button"
    assert w.height() >= w._checklist_window_height(), (
        "window should be tall enough for all checklist chrome"
    )
    assert w.lbl_ts.height() <= w.meta_row.height(), "footer meta row should not clip label"


def test_user_resized_checklist_still_grows(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    nd["height"] = 180
    nd["user_resized"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()
    qtbot.wait(50)

    h0 = w.height()
    for _ in range(4):
        w._add_checklist_item()
        qtbot.wait(50)
    assert w.height() > h0, "user-resized checklist should still grow with items"


def test_add_item_button_adds_row(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    assert w.checklist_widget.count() == 1
    qtbot.mouseClick(w.btn_add_checklist_item, Qt.MouseButton.LeftButton)
    qtbot.wait(50)

    assert w.checklist_widget.count() == 2
    assert _checklist_editor(w) is not None


def test_enter_while_editing_adds_row_below(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    item0 = w.checklist_widget.item(0)
    assert item0 is not None
    w.checklist_widget.editItem(item0)
    qtbot.wait(50)
    editor = _checklist_editor(w)
    assert editor is not None

    qtbot.keyClicks(editor, "First task")
    qtbot.keyPress(editor, Qt.Key.Key_Return)
    qtbot.wait(50)

    assert w.checklist_widget.count() == 2
    assert w.checklist_widget.item(0) is not None
    assert w.checklist_widget.item(0).text() == "First task"
    editor2 = _checklist_editor(w)
    assert editor2 is not None
    assert editor2.text() == ""


def test_backspace_on_empty_item_removes_row(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "- [ ] one\n- [ ] two\n- [ ] three"
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    item = w.checklist_widget.item(1)
    assert item is not None
    w.checklist_widget.setCurrentItem(item)
    w.checklist_widget.editItem(item)
    qtbot.wait(50)
    editor = _checklist_editor(w)
    assert editor is not None

    editor.clear()
    qtbot.keyPress(editor, Qt.Key.Key_Backspace)
    qtbot.wait(50)

    assert w.checklist_widget.count() == 2
    texts = [w.checklist_widget.item(i).text() for i in range(w.checklist_widget.count())]
    assert texts == ["one", "three"]


def test_backspace_on_last_empty_item_keeps_one_row(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    item = w.checklist_widget.item(0)
    assert item is not None
    w.checklist_widget.editItem(item)
    qtbot.wait(50)
    editor = _checklist_editor(w)
    assert editor is not None

    editor.clear()
    qtbot.keyPress(editor, Qt.Key.Key_Backspace)
    qtbot.wait(50)

    assert w.checklist_widget.count() == 1
    assert w.checklist_widget.item(0) is not None
    assert w.checklist_widget.item(0).text() == ""
    assert _checklist_editor(w) is not None


def test_checklist_layout_matches_text_mode_structure(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    main_lo = w.layout()
    assert main_lo is not None
    widgets = [main_lo.itemAt(i).widget() for i in range(main_lo.count())]
    assert widgets[0] is w.title_bar
    assert widgets[1] is w.checklist_body
    assert widgets[2] is w.editor
    assert widgets[3] is w.colour_row
    assert widgets[4] is w.meta_row

    assert w.checklist_body.isVisible()
    assert w.checklist_widget.isVisible()
    assert w.btn_add_checklist_item.isVisible()
    assert not w.editor.isVisible()
    assert w.colour_row.isVisible()
    assert w.meta_row.isVisible()


def test_checklist_editor_uses_note_background(qapp, qtbot, temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["colour"] = "green"
    nd["checklist"] = True
    w = NoteWindow(nd, storage)
    qtbot.addWidget(w)
    w.show()

    item = w.checklist_widget.item(0)
    assert item is not None
    w.checklist_widget.editItem(item)
    qtbot.wait(50)
    editor = _checklist_editor(w)
    assert editor is not None
    assert NOTE_COLOURS["green"] in editor.styleSheet()


def test_context_menu_add_checklist_item_still_works(checklist_note: NoteWindow, qtbot) -> None:
    w = checklist_note
    start = w.checklist_widget.count()
    w._add_checklist_item()
    qtbot.wait(50)

    assert w.checklist_widget.count() == start + 1
    assert _checklist_editor(w) is not None
