"""Tests for AppManager dock refresh scheduling and private display content."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QTimer, QRect

from stickynotes.app_manager import AppManager
from stickynotes.models import private_preview_text
from stickynotes.storage import StorageManager
from stickynotes.ui.dock import DockWidget
from stickynotes.ui.note_window import NoteWindow


def _minimal_manager(
    qapp,
    storage: StorageManager,
    note: NoteWindow,
    dock: DockWidget,
) -> AppManager:
    mgr = AppManager.__new__(AppManager)
    mgr.app = qapp
    mgr.storage = storage
    mgr.notes = {note.note_id: note}
    mgr.docks = [dock]
    mgr._pending_note_updates = set()
    mgr._last_dock_tags = ()
    mgr._last_dock_shortcuts_signature = ()
    mgr._last_dock_filter = ""
    mgr._notes_with_content = set()
    mgr._active_tag_filter = ""
    mgr._dark = False
    mgr._dock_refresh_timer = QTimer()
    mgr._dock_refresh_timer.setSingleShot(True)
    mgr._dock_refresh_timer.setInterval(AppManager.DOCK_REFRESH_MS)
    mgr._dock_refresh_timer.timeout.connect(mgr._refresh_all_docks)

    def _all_known_tags() -> list[str]:
        return []

    mgr._all_known_tags = _all_known_tags
    return mgr


@pytest.fixture
def manager_setup(qapp, qtbot, temp_paths):
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "Test note"
    note = NoteWindow(nd, storage)
    qtbot.addWidget(note)
    dock = DockWidget(
        position="top",
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda nid: note.editor.toPlainText(),
    )
    qtbot.addWidget(dock)
    mgr = _minimal_manager(qapp, storage, note, dock)
    yield mgr, note, dock
    mgr._dock_refresh_timer.stop()
    dock._poll.stop()


def test_schedule_dock_refresh_debounced_only(manager_setup) -> None:
    mgr, note, dock = manager_setup
    nid = note.note_id
    mgr.storage.set_note(nid, note.note_data)
    nd = dict(note.note_data)
    nd["content"] = note.editor.toPlainText()
    dock.refresh_cards({nid: nd}, [])
    mgr._last_dock_shortcuts_signature = ()
    update_spy = MagicMock(wraps=dock.update_note_card)
    refresh_spy = MagicMock(wraps=dock.refresh_cards)
    dock.update_note_card = update_spy
    dock.refresh_cards = refresh_spy

    mgr._schedule_dock_refresh(nid)
    update_spy.assert_not_called()
    assert nid in mgr._pending_note_updates

    mgr._dock_refresh_timer.stop()
    mgr._refresh_all_docks()
    update_spy.assert_called_once()
    refresh_spy.assert_not_called()


def test_private_note_display_content(manager_setup) -> None:
    mgr, note, _dock = manager_setup
    nid = note.note_id
    note.note_data["private"] = True
    note._revealed = False
    assert mgr.get_display_content(nid) == private_preview_text()
    note._revealed = True
    assert mgr.get_display_content(nid) == mgr.get_live_content(nid)
