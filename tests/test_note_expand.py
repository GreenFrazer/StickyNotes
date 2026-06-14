"""Regression tests for note expand via viewport click and ActiveWindow FocusIn."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt, QTimer
from PyQt6.QtGui import QFocusEvent, QMouseEvent

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


def test_viewport_click_expands(expand_note: NoteWindow, qtbot) -> None:
    w = expand_note
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
    from PyQt6.QtWidgets import QApplication

    QApplication.sendEvent(vp, ev)
    qtbot.wait(100)
    assert w.height() > REST_H, "viewport click should expand note height"


def test_active_window_focus_expands(expand_note: NoteWindow, qtbot) -> None:
    w = expand_note
    w._editing = False
    w._collapse_to_rest()
    w.editor.clearFocus()
    qtbot.wait(50)
    assert w.height() == REST_H

    from PyQt6.QtWidgets import QApplication

    QApplication.setOverrideCursor(w.cursor())
    fe = QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.ActiveWindowFocusReason)
    QApplication.sendEvent(w.editor, fe)
    qtbot.wait(100)
    QApplication.restoreOverrideCursor()
    assert w.height() > REST_H, "ActiveWindow FocusIn should expand note height"
