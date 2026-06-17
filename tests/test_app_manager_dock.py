"""Tests for AppManager dock refresh scheduling and private display content."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QPoint, QPointF, QTimer, QRect, Qt
from PyQt6.QtGui import QMouseEvent

from stickynotes.app_manager import AppManager
from stickynotes.models import private_preview_text
from stickynotes.storage import StorageManager
from stickynotes.ui.dock import DockWidget
from stickynotes.ui.note_window import NoteWindow


def _mouse_event(
    event_type,
    global_pos: QPoint,
    *,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        QPointF(0, 0),
        QPointF(global_pos),
        button,
        button,
        Qt.KeyboardModifier.NoModifier,
    )


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


def test_rapid_resize_persist_and_sync_once(qapp, temp_paths) -> None:
    """Many drag moves must not write settings or sync sibling docks."""
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    geo = QRect(0, 0, 1920, 1080)
    dock_a = DockWidget(
        position="right",
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=100,
    )
    dock_b = DockWidget(
        position="left",
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=100,
    )
    for dock in (dock_a, dock_b):
        dock._hide_tmr.stop()
        dock._shown = True
        dock._set_shown_size_constraints()
        dock.setGeometry(dock._shown_geo())

    mgr = AppManager.__new__(AppManager)
    mgr.storage = storage
    mgr.docks = [dock_a, dock_b]
    mgr._dock_width = 100
    set_settings_calls: list[dict] = []
    original_set_settings = storage.set_settings

    def track_set_settings(settings: dict) -> None:
        set_settings_calls.append(dict(settings))
        original_set_settings(settings)

    storage.set_settings = track_set_settings  # type: ignore[method-assign]
    sync_calls: list[int] = []
    original_set_dock_width = dock_b.set_dock_width

    def track_sibling_sync(width: int, *, persist: bool = True) -> None:
        if not persist:
            sync_calls.append(width)
        original_set_dock_width(width, persist=persist)

    dock_b.set_dock_width = track_sibling_sync  # type: ignore[method-assign]
    mgr._on_dock_width_changed = AppManager._on_dock_width_changed.__get__(mgr)
    dock_a.sig_dock_width_changed.connect(
        lambda w: mgr._on_dock_width_changed(w, dock_a)
    )

    handle = dock_a._resize_handle
    try:
        start = QPoint(geo.right() - 50, 540)
        handle.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
        for x in range(geo.right() - 60, geo.right() - 200, -5):
            handle.mouseMoveEvent(
                _mouse_event(QMouseEvent.Type.MouseMove, QPoint(x, 540))
            )
        assert set_settings_calls == []
        assert sync_calls == []
        handle.mouseReleaseEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonRelease,
                QPoint(geo.right() - 200, 540),
            )
        )
        assert len(set_settings_calls) == 1
        assert set_settings_calls[0]["dock_width"] == dock_a._thick
        assert sync_calls == [dock_a._thick]
    finally:
        dock_a.destroy_dock()
        dock_b.destroy_dock()
