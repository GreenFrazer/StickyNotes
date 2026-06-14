"""Regression tests for note expand via viewport click and collapse on focus loss."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QFocusEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QWidget

from stickynotes.storage import StorageManager
from stickynotes.ui.note_window import NoteWindow

CONTENT = ("Line of text.\n" * 40)[:411]
REST_H = 180


@pytest.fixture
def expand_note(qapp, qtbot) -> NoteWindow:
    nd = StorageManager.default_note()
    nd["content"] = CONTENT
    nd["height"] = REST_H
    nd["width"] = 240
    w = NoteWindow(nd, StorageManager())
    qtbot.addWidget(w)
    w.show()
    w.raise_()
    w.activateWindow()
    w.editor.clearFocus()
    qtbot.wait(50)
    return w


def _viewport_click(w: NoteWindow) -> None:
    vp = w.editor.viewport()
    pos = QPointF(vp.width() / 2, vp.height() / 2)
    gpos = QPointF(vp.mapToGlobal(pos.toPoint()))
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        pos,
        gpos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(vp, ev)


def _simulate_focus_loss(w: NoteWindow, qtbot) -> None:
    helper = QWidget()
    qtbot.addWidget(helper)
    helper.show()
    w.editor.setFocus()
    qtbot.wait(10)
    helper.setFocus()
    fe_out = QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.OtherFocusReason)
    QApplication.sendEvent(w.editor, fe_out)
    qtbot.wait(50)


def test_viewport_click_expands(expand_note: NoteWindow, qtbot) -> None:
    w = expand_note
    _viewport_click(w)
    qtbot.wait(100)
    assert w.height() > REST_H, "viewport click should expand note height"


def test_collapse_on_focus_loss(expand_note: NoteWindow, qtbot) -> None:
    w = expand_note
    _viewport_click(w)
    qtbot.wait(100)
    assert w.height() > REST_H

    _simulate_focus_loss(w, qtbot)
    assert w.height() == REST_H, "focus loss should collapse note to rest height"


def test_active_window_focus_does_not_expand(expand_note: NoteWindow, qtbot) -> None:
    w = expand_note
    _viewport_click(w)
    qtbot.wait(100)
    expanded_h = w.height()
    assert expanded_h > REST_H

    _simulate_focus_loss(w, qtbot)
    assert w.height() == REST_H

    QApplication.setOverrideCursor(w.cursor())
    fe = QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.ActiveWindowFocusReason)
    QApplication.sendEvent(w.editor, fe)
    qtbot.wait(100)
    QApplication.restoreOverrideCursor()
    assert w.height() == REST_H, (
        "ActiveWindow FocusIn alone should not re-expand after collapse"
    )


def test_show_note_focus_regain_does_not_reexpand(
    expand_note: NoteWindow, qtbot
) -> None:
    """Dock card click calls show_note(); note must not expand again."""
    w = expand_note
    _viewport_click(w)
    qtbot.wait(100)
    assert w.height() > REST_H

    _simulate_focus_loss(w, qtbot)
    assert w.height() == REST_H

    w.show_note()
    qtbot.wait(100)
    assert w.height() == REST_H, "show_note/focus regain should not re-expand"
