"""Unit tests for DockWidget card management."""

from __future__ import annotations

from PyQt6.QtCore import QRect

import pytest

from stickynotes.storage import StorageManager
from stickynotes.ui.dock import DockNoteIndicator, DockWidget


def _make_note(content: str, *, modified_at: str = "2026-06-14T10:00:00") -> dict:
    nd = StorageManager.default_note()
    nd["content"] = content
    nd["modified_at"] = modified_at
    return nd


@pytest.fixture
def dock(qapp, qtbot) -> DockWidget:
    d = DockWidget(
        position="top",
        dark_mode=False,
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    qtbot.addWidget(d)
    yield d
    d.destroy_dock()


def test_refresh_cards_ordering(dock: DockWidget) -> None:
    n1 = _make_note("First", modified_at="2026-06-14T09:00:00")
    n2 = _make_note("Second", modified_at="2026-06-14T11:00:00")
    n3 = _make_note("Third", modified_at="2026-06-14T10:00:00")
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2, n3["id"]: n3}, [])
    ids = [ind.note_id for ind in dock._indicators]
    assert ids == [n2["id"], n3["id"], n1["id"]]


def test_update_note_card_updates_label(dock: DockWidget) -> None:
    nd = _make_note("Original")
    dock.refresh_cards({nd["id"]: nd}, [])
    ind = dock._indicator_map[nd["id"]]
    old_count = len(dock._indicators)
    nd2 = dict(nd)
    nd2["content"] = "Updated text here"
    dock.update_note_card(nd["id"], nd2)
    assert len(dock._indicators) == old_count
    assert ind.lbl_preview.text() == "Upda"


def test_update_note_card_inserts_new_note(dock: DockWidget) -> None:
    nd1 = _make_note("One")
    dock.refresh_cards({nd1["id"]: nd1}, [])
    nd2 = _make_note("Two", modified_at="2026-06-14T12:00:00")
    dock.update_note_card(nd2["id"], nd2)
    assert nd2["id"] in dock._indicator_map
    assert len(dock._indicators) == 2


def test_remove_note_card(dock: DockWidget) -> None:
    n1 = _make_note("Keep")
    n2 = _make_note("Remove")
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2}, [])
    dock.remove_note_card(n2["id"])
    assert n2["id"] not in dock._indicator_map
    assert len(dock._indicators) == 1
    assert all(isinstance(i, DockNoteIndicator) for i in dock._indicators)
