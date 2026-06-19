"""Unit tests for DockWidget card management."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt
from PyQt6.QtGui import QCursor, QMouseEvent

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

import pytest

from stickynotes import __version__
from stickynotes.models import MAX_DOCK_WIDTH, MIN_DOCK_WIDTH, clamp_dock_width
from stickynotes.storage import StorageManager
from stickynotes.ui.dock import DockNoteIndicator, DockNotePopup, DockWidget


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
    d._poll.stop()
    d._hide_tmr.stop()
    yield d
    d.destroy_dock()


def test_refresh_cards_ordering(dock: DockWidget) -> None:
    n1 = _make_note("First", modified_at="2026-06-14T09:00:00")
    n2 = _make_note("Second", modified_at="2026-06-14T11:00:00")
    n3 = _make_note("Third", modified_at="2026-06-14T10:00:00")
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2, n3["id"]: n3}, [])
    ids = [ind.note_id for ind in dock._indicators]
    assert ids == [n2["id"], n3["id"], n1["id"]]


def test_refresh_cards_respects_saved_dock_order(dock: DockWidget) -> None:
    n1 = _make_note("First", modified_at="2026-06-14T09:00:00")
    n2 = _make_note("Second", modified_at="2026-06-14T11:00:00")
    n3 = _make_note("Third", modified_at="2026-06-14T10:00:00")
    custom_order = [n1["id"], n3["id"], n2["id"]]
    dock.refresh_cards(
        {n1["id"]: n1, n2["id"]: n2, n3["id"]: n3},
        [],
        dock_order=custom_order,
    )
    assert dock._ordered_ids == custom_order
    assert [ind.note_id for ind in dock._indicators] == custom_order


def test_move_item_to_index_reorders_notes_and_files(dock: DockWidget) -> None:
    n1 = _make_note("One")
    n2 = _make_note("Two", modified_at="2026-06-14T12:00:00")
    shortcut = {
        "id": "shortcut-1",
        "path": "C:/docs/report.pdf",
        "label": "report",
        "added_at": "2026-06-14T08:00:00",
    }
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2}, [shortcut])
    assert dock._ordered_ids == [shortcut["id"], n2["id"], n1["id"]]
    dock._move_item_to_index(n1["id"], 0)
    assert dock._ordered_ids == [n1["id"], shortcut["id"], n2["id"]]


def test_apply_dock_order_updates_layout(dock: DockWidget) -> None:
    n1 = _make_note("One")
    n2 = _make_note("Two", modified_at="2026-06-14T12:00:00")
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2}, [])
    dock.apply_dock_order([n1["id"], n2["id"]])
    assert dock._ordered_ids == [n1["id"], n2["id"]]


def test_finish_manual_reorder_moves_note(dock: DockWidget) -> None:
    n1 = _make_note("One")
    n2 = _make_note("Two", modified_at="2026-06-14T12:00:00")
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2}, [])
    ind = dock._indicator_map[n1["id"]]
    dock._start_manual_reorder(n1["id"], ind)
    try:
        drop_x = ind.geometry().center().x()
        global_pos = dock.ind_container.mapToGlobal(QPoint(drop_x, ind.geometry().center().y()))
        dock._finish_manual_reorder(global_pos)
    finally:
        if dock._reorder_item_id:
            dock._finish_manual_reorder(QCursor.pos())
    assert dock._reorder_item_id is None
    assert not dock._item_drag_active


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


def test_incremental_inserts_do_not_stack_indicators(qapp, qtbot) -> None:
    dock = DockWidget(
        position="right",
        dark_mode=False,
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    qtbot.addWidget(dock)
    dock.show()
    dock._shown = True
    dock.setGeometry(dock._shown_geo())
    dock.refresh_cards({}, [], [])
    for i in range(6):
        nd = _make_note(f"Note {i}", modified_at=f"2026-06-17T10:0{i}:00")
        dock.update_note_card(nd["id"], nd)
    qtbot.wait(20)
    ys = [ind.geometry().y() for ind in dock._indicators]
    assert len(ys) == len(set(ys))
    dock.destroy_dock()


def test_hidden_dock_relayouts_notes_on_expand(qapp, qtbot) -> None:
    dock = DockWidget(
        position="right",
        dark_mode=False,
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    qtbot.addWidget(dock)
    dock._place_hidden()
    dock.refresh_cards({}, [], [])
    for i in range(4):
        nd = _make_note(f"Note {i}", modified_at=f"2026-06-17T10:0{i}:00")
        dock.update_note_card(nd["id"], nd)
    dock._slide_in()
    qtbot.wait(250)
    ys = [ind.geometry().y() for ind in dock._indicators]
    assert len(ys) == len(set(ys))
    dock.destroy_dock()


def test_refresh_cards_skips_empty_non_private_notes(dock: DockWidget) -> None:
    empty = _make_note("")
    private = _make_note("")
    private["private"] = True
    dock.refresh_cards({empty["id"]: empty, private["id"]: private}, [], [])
    assert len(dock._indicators) == 1
    assert dock._indicators[0].note_id == private["id"]


def test_poll_mouse_same_cursor_skips_interval_reset(
    dock: DockWidget, monkeypatch: pytest.MonkeyPatch
) -> None:
    dock._poll.stop()
    dock._shown = False
    dock._last_poll_cursor = None
    dock._last_poll_shown = False

    pos = QPoint(960, 500)
    monkeypatch.setattr("stickynotes.ui.dock.QCursor.pos", lambda: pos)

    set_interval_calls: list[int] = []
    original_set_interval = dock._poll.setInterval

    def track_set_interval(ms: int) -> None:
        set_interval_calls.append(ms)
        original_set_interval(ms)

    monkeypatch.setattr(dock._poll, "setInterval", track_set_interval)

    dock._poll_mouse()
    count_after_first = len(set_interval_calls)
    assert count_after_first >= 1

    dock._poll_mouse()
    assert len(set_interval_calls) == count_after_first


def test_left_dock_hidden_geometry_collapses_at_screen_edge(qapp) -> None:
    geo = QRect(-1920, 0, 1920, 1080)
    dock = DockWidget(
        position="left",
        dark_mode=False,
        screen_geo=geo,
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        dock._place_hidden()
        hidden = dock.geometry()
        assert hidden.x() == geo.left()
        assert hidden.width() <= dock.TRIGGER
        assert hidden.height() == geo.height()
    finally:
        dock.destroy_dock()


def test_top_dock_hidden_geometry_collapses_at_screen_edge(qapp) -> None:
    geo = QRect(0, -1080, 1920, 1080)
    dock = DockWidget(
        position="top",
        dark_mode=False,
        screen_geo=geo,
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        dock._place_hidden()
        hidden = dock.geometry()
        assert hidden.y() == geo.top()
        assert hidden.height() <= dock.TRIGGER
        assert hidden.width() == geo.width()
    finally:
        dock.destroy_dock()


def test_right_dock_hidden_geometry_slides_off_screen(qapp) -> None:
    if sys.platform == "win32":
        pytest.skip("Windows right dock collapses in-place")
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position="right",
        dark_mode=False,
        screen_geo=geo,
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        dock._place_hidden()
        hidden = dock.geometry()
        assert hidden.x() == geo.right()
        assert hidden.width() == dock._thick
    finally:
        dock.destroy_dock()


def test_right_dock_hidden_geometry_collapses_on_windows(
    qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position="right",
        dark_mode=False,
        screen_geo=geo,
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        dock._place_hidden()
        hidden = dock.geometry()
        assert hidden.x() == geo.right() - dock.TRIGGER
        assert hidden.width() <= dock.TRIGGER
        assert hidden.height() == geo.height()
    finally:
        dock.destroy_dock()


@pytest.mark.parametrize("position", ["right", "left"])
def test_set_dock_width_updates_shown_geometry(position: str, qapp) -> None:
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position=position,
        dark_mode=False,
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=56,
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        dock.set_dock_width(120, persist=False)
        dock._shown = True
        shown = dock._shown_geo()
        if position == "right":
            assert shown.width() == 120
            assert shown.x() == geo.right() - 120
        else:
            assert shown.width() == 120
            assert shown.left() == geo.left()
    finally:
        dock.destroy_dock()


def test_set_dock_width_clamps_to_bounds(qapp) -> None:
    dock = DockWidget(
        position="right",
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        dock.set_dock_width(10, persist=False)
        assert dock._thick == MIN_DOCK_WIDTH
        dock.set_dock_width(999, persist=False)
        assert dock._thick == MAX_DOCK_WIDTH
    finally:
        dock.destroy_dock()


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


def test_resize_handle_drag_clamps_width(qapp, qtbot) -> None:
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position="right",
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=100,
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    dock._shown = True
    dock._set_shown_size_constraints()
    dock.setGeometry(dock._shown_geo())
    handle = dock._resize_handle
    try:
        start = QPoint(geo.right() - 50, 540)
        handle.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
        handle.mouseMoveEvent(
            _mouse_event(
                QMouseEvent.Type.MouseMove,
                QPoint(geo.right() - 100, 540),
            )
        )
        assert dock._thick == 150
        handle.mouseMoveEvent(
            _mouse_event(
                QMouseEvent.Type.MouseMove,
                QPoint(geo.right() - 500, 540),
            )
        )
        assert dock._thick == MAX_DOCK_WIDTH
        handle.mouseReleaseEvent(
            _mouse_event(QMouseEvent.Type.MouseButtonRelease, QPoint(geo.right() - 500, 540))
        )
        assert not dock._resize_dragging
    finally:
        dock.destroy_dock()


def test_resize_drag_avoids_fixed_width_during_moves(qapp, monkeypatch) -> None:
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position="right",
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=100,
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    dock._shown = True
    dock._set_shown_size_constraints()
    dock.setGeometry(dock._shown_geo())
    handle = dock._resize_handle
    fixed_width_calls: list[int] = []
    original = dock.setFixedWidth

    def track_fixed_width(w: int) -> None:
        fixed_width_calls.append(w)
        original(w)

    monkeypatch.setattr(dock, "setFixedWidth", track_fixed_width)
    try:
        start = QPoint(geo.right() - 50, 540)
        handle.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
        for x in range(geo.right() - 60, geo.right() - 200, -10):
            handle.mouseMoveEvent(
                _mouse_event(QMouseEvent.Type.MouseMove, QPoint(x, 540))
            )
        assert fixed_width_calls == []
        handle.mouseReleaseEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonRelease,
                QPoint(geo.right() - 200, 540),
            )
        )
        assert len(fixed_width_calls) == 1
    finally:
        dock.destroy_dock()


def test_resize_drag_pauses_poll_timer(qapp) -> None:
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position="right",
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=100,
    )
    dock._hide_tmr.stop()
    dock._shown = True
    dock._set_shown_size_constraints()
    dock.setGeometry(dock._shown_geo())
    handle = dock._resize_handle
    try:
        assert dock._poll.isActive()
        handle.mousePressEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonPress,
                QPoint(geo.right() - 50, 540),
            )
        )
        assert not dock._poll.isActive()
        handle.mouseReleaseEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonRelease,
                QPoint(geo.right() - 80, 540),
            )
        )
        assert dock._poll.isActive()
    finally:
        dock.destroy_dock()


def test_resize_handle_persists_width_once_on_release(qapp, qtbot) -> None:
    geo = QRect(0, 0, 1920, 1080)
    dock = DockWidget(
        position="right",
        screen_geo=geo,
        content_getter=lambda _nid: "",
        dock_width=100,
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    dock._shown = True
    dock._set_shown_size_constraints()
    dock.setGeometry(dock._shown_geo())
    handle = dock._resize_handle
    emitted: list[int] = []
    dock.sig_dock_width_changed.connect(emitted.append)
    try:
        start = QPoint(geo.right() - 50, 540)
        handle.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
        handle.mouseMoveEvent(
            _mouse_event(
                QMouseEvent.Type.MouseMove,
                QPoint(geo.right() - 80, 540),
            )
        )
        handle.mouseMoveEvent(
            _mouse_event(
                QMouseEvent.Type.MouseMove,
                QPoint(geo.right() - 120, 540),
            )
        )
        assert emitted == []
        handle.mouseReleaseEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonRelease,
                QPoint(geo.right() - 120, 540),
            )
        )
        assert emitted == [dock._thick]
    finally:
        dock.destroy_dock()


def test_dock_width_settings_round_trip(temp_paths) -> None:
    storage = StorageManager(temp_paths, restore_prompt=lambda: False)
    settings = storage.get_settings()
    settings["dock_width"] = 180
    storage.set_settings(settings)
    loaded = storage.get_settings()
    assert loaded["dock_width"] == 180
    normalized = storage._normalize_loaded({"settings": {"dock_width": 999}})
    assert normalized["settings"]["dock_width"] == MAX_DOCK_WIDTH
    assert clamp_dock_width(40) == MIN_DOCK_WIDTH


def test_remove_note_card(dock: DockWidget) -> None:
    n1 = _make_note("Keep")
    n2 = _make_note("Remove")
    dock.refresh_cards({n1["id"]: n1, n2["id"]: n2}, [])
    dock.remove_note_card(n2["id"])
    assert n2["id"] not in dock._indicator_map
    assert len(dock._indicators) == 1
    assert all(isinstance(i, DockNoteIndicator) for i in dock._indicators)


def test_dock_has_no_tag_filter_row(dock: DockWidget) -> None:
    dock.refresh_cards({}, [], tags=["fg", "t1-fgreen"], active_tag="fg")
    assert dock.findChild(QWidget, "tagFilterRow") is None


def test_dock_has_no_standalone_exit_button(dock: DockWidget) -> None:
    tooltips = [w.btn.toolTip() for w in dock._btn_widgets]
    assert "Exit" not in tooltips


def test_settings_menu_includes_exit_and_version(dock: DockWidget) -> None:
    menu = dock._build_settings_menu()
    actions = [action for action in menu.actions() if not action.isSeparator()]
    assert actions[0].text() == "Settings"
    assert actions[1].text() == "Exit"
    assert actions[2].text() == f"Version {__version__}"
    assert actions[3].text().startswith("Built ")
    assert actions[0].isEnabled()
    assert actions[1].isEnabled()
    assert not actions[2].isEnabled()
    assert not actions[3].isEnabled()


def test_settings_menu_signals(qtbot, dock: DockWidget) -> None:
    settings_calls: list[str] = []
    exit_calls: list[str] = []
    dock.sig_settings.connect(lambda: settings_calls.append("settings"))
    dock.sig_exit.connect(lambda: exit_calls.append("exit"))
    menu = dock._build_settings_menu()
    for action in menu.actions():
        if action.text() == "Settings":
            action.trigger()
        elif action.text() == "Exit":
            action.trigger()
    assert settings_calls == ["settings"]
    assert exit_calls == ["exit"]


def _action_button_layout(dock: DockWidget):
    outer = dock.layout()
    assert outer is not None
    item = outer.itemAt(outer.count() - 1)
    return item.layout()


@pytest.mark.parametrize("position", ["right", "left"])
def test_side_dock_action_buttons_vertical_at_default_width(
    position: str, qapp
) -> None:
    dock = DockWidget(
        position=position,
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        btn_lay = _action_button_layout(dock)
        assert isinstance(btn_lay, QVBoxLayout)
    finally:
        dock.destroy_dock()


@pytest.mark.parametrize("position", ["right", "left"])
def test_side_dock_action_buttons_horizontal_when_extended(
    position: str, qapp
) -> None:
    dock = DockWidget(
        position=position,
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
        dock_width=120,
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        btn_lay = _action_button_layout(dock)
        assert isinstance(btn_lay, QHBoxLayout)
    finally:
        dock.destroy_dock()


def test_side_dock_action_buttons_switch_on_resize(qapp) -> None:
    dock = DockWidget(
        position="right",
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    dock._poll.stop()
    dock._hide_tmr.stop()
    try:
        assert isinstance(_action_button_layout(dock), QVBoxLayout)
        dock.set_dock_width(120, persist=False)
        assert isinstance(_action_button_layout(dock), QHBoxLayout)
        dock.set_dock_width(MIN_DOCK_WIDTH, persist=False)
        assert isinstance(_action_button_layout(dock), QVBoxLayout)
    finally:
        dock.destroy_dock()


def test_top_dock_action_buttons_horizontal(dock: DockWidget) -> None:
    btn_lay = _action_button_layout(dock)
    assert isinstance(btn_lay, QHBoxLayout)


def test_dock_note_popup_shows_primary_tag(qapp) -> None:
    nd = _make_note("Tagged note")
    nd["tags"] = ["work", "urgent"]
    popup = DockNotePopup(nd, lambda _nid: nd["content"])
    assert not popup._tag_label.isHidden()
    assert popup._tag_label.text() == "#work"
    assert popup._tag_label.toolTip() == "#work, #urgent"


def test_dock_note_popup_hides_tag_when_empty(qapp) -> None:
    nd = _make_note("No tag")
    popup = DockNotePopup(nd, lambda _nid: nd["content"])
    assert popup._tag_label.isHidden()


def test_dock_note_popup_update_content_refreshes_tag(qapp) -> None:
    nd = _make_note("Tagged note")
    popup = DockNotePopup(nd, lambda _nid: nd["content"])
    assert popup._tag_label.isHidden()
    nd2 = dict(nd)
    nd2["tags"] = ["personal"]
    popup.update_content(nd2)
    assert not popup._tag_label.isHidden()
    assert popup._tag_label.text() == "#personal"
