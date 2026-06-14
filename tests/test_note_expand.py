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


def test_typing_without_viewport_click_expands(qapp, qtbot) -> None:
    """Typing with editor focus should grow the note even without a viewport click."""
    nd = StorageManager.default_note()
    nd["content"] = "Short"
    nd["height"] = REST_H
    nd["width"] = 240
    w = NoteWindow(nd, StorageManager())
    qtbot.addWidget(w)
    w.show()
    w.editor.setFocus()
    qtbot.wait(50)
    h0 = w.height()
    w.editor.setPlainText("Line one\nLine two\nLine three\nLine four\nLine five\n")
    qtbot.wait(100)
    assert w.height() > h0, "focused typing should expand note height"


def test_user_resized_skips_collapse_on_focus_loss(
    expand_note: NoteWindow, qtbot
) -> None:
    w = expand_note
    w.note_data["user_resized"] = True
    _viewport_click(w)
    qtbot.wait(100)
    expanded_h = w.height()
    assert expanded_h > REST_H

    _simulate_focus_loss(w, qtbot)
    assert w.height() == expanded_h, "user-resized notes should not collapse"


def test_user_resized_still_expands_when_typing(qapp, qtbot) -> None:
    """Manual resize must not block growth when content needs more space."""
    nd = StorageManager.default_note()
    nd["content"] = "Short"
    nd["height"] = REST_H
    nd["width"] = 240
    nd["user_resized"] = True
    w = NoteWindow(nd, StorageManager())
    qtbot.addWidget(w)
    w.show()
    w._full_h = REST_H
    w.editor.setFocus()
    qtbot.wait(50)
    h0 = w.height()
    w.editor.setPlainText("Line one\nLine two\nLine three\nLine four\nLine five\n")
    qtbot.wait(100)
    assert w.height() > h0, "user-resized notes should still expand for content"


def test_enter_key_expands_incrementally(expand_note: NoteWindow, qtbot) -> None:
    """Pressing Enter to add lines should grow the note without setPlainText."""
    w = expand_note
    w.editor.setFocus()
    qtbot.wait(50)
    h0 = w.height()
    for _ in range(8):
        qtbot.keyPress(w.editor, Qt.Key.Key_Return)
        qtbot.wait(30)
    assert w.height() > h0, "Enter key should expand note incrementally"


def test_init_does_not_mark_user_resized(qapp, qtbot) -> None:
    nd = StorageManager.default_note()
    w = NoteWindow(nd, StorageManager())
    qtbot.addWidget(w)
    w.show()
    qtbot.wait(50)
    assert w.note_data.get("user_resized") is not True


def test_auto_expand_does_not_mark_user_resized(expand_note: NoteWindow, qtbot) -> None:
    w = expand_note
    w.editor.setFocus()
    qtbot.wait(50)
    w.editor.setPlainText("Line one\nLine two\nLine three\nLine four\nLine five\n")
    qtbot.wait(100)
    assert w.height() > REST_H
    assert w.note_data.get("user_resized") is not True
