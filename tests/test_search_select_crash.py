"""Regression tests for search result selection crashes."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from stickynotes.app_manager import AppManager
from stickynotes.storage import StorageManager
from stickynotes.ui.search_dialog import SearchDialog


def test_search_private_note_opens_after_reveal_click(qapp, qtbot) -> None:
    note = StorageManager.default_note()
    note["content"] = "Secret body"
    note["tags"] = ["t1-fgreen"]
    note["private"] = True
    notes = {note["id"]: note}

    dlg = SearchDialog(notes, lambda nid: notes[nid]["content"])
    qtbot.addWidget(dlg)
    dlg.show()
    dlg._input.setText("t1")
    qtbot.wait(400)
    assert dlg._results.count() == 1

    item = dlg._results.item(0)
    assert item.data(Qt.ItemDataRole.UserRole + 1) is True

    opened: list[str] = []
    dlg.note_selected.connect(opened.append)

    dlg._results.setCurrentItem(item)
    dlg._on_activated(item)
    qtbot.wait(10)

    item = dlg._results.item(0)
    assert item is not None
    assert item.data(Qt.ItemDataRole.UserRole + 1) is False

    dlg._on_activated(item)
    qtbot.wait(10)

    assert opened == [note["id"]]


def test_search_select_private_note_via_app_manager(qapp, qtbot) -> None:
    mgr = AppManager(qapp)

    nid = None
    for note_id, nd in mgr.storage.get_all_notes().items():
        if any("t1" in t for t in nd.get("tags", [])):
            nid = note_id
            break

    if nid is None:
        note = StorageManager.default_note()
        note["content"] = "Tagged secret"
        note["tags"] = ["t1-fgreen"]
        note["private"] = True
        note["visible"] = False
        mgr.storage.set_note(note["id"], note)
        mgr._spawn(note)
        mgr.notes[note["id"]].hide()
        nid = note["id"]

    mgr.open_search()
    dlg = mgr._search_dialog
    assert dlg is not None
    qtbot.addWidget(dlg)

    dlg._input.setText("t1")
    qtbot.wait(400)
    assert dlg._results.count() >= 1

    item = dlg._results.item(0)
    qtbot.mouseClick(
        dlg._results.viewport(),
        Qt.MouseButton.LeftButton,
        pos=dlg._results.visualItemRect(item).center(),
    )
    qtbot.wait(50)

    item = dlg._results.item(0)
    qtbot.wait(50)
    qtbot.mouseClick(
        dlg._results.viewport(),
        Qt.MouseButton.LeftButton,
        pos=dlg._results.visualItemRect(item).center(),
    )
    qtbot.wait(100)

    assert mgr.notes[nid].isVisible()
