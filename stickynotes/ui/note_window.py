"""Individual sticky note window."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizeGrip,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from stickynotes.models import (
    checklist_progress,
    content_has_checklist_items,
    fmt_dt,
    is_private,
    normalize_tags,
    parse_checklist,
    private_preview_text,
)
from stickynotes.reminders import ReminderService
from stickynotes.theme import (
    DEFAULT_NOTE_H,
    DEFAULT_NOTE_W,
    FONT_BODY,
    FONT_FINE,
    INK_MUTED,
    NOTE_COLOURS,
    SNAP_THRESHOLD,
    TITLE_BAR_COLOURS,
    colour_dot_stylesheet,
    menu_stylesheet,
    note_window_stylesheet,
    title_button_stylesheet,
)
from stickynotes.ui.icons import set_button_icon

if TYPE_CHECKING:
    from stickynotes.storage import StorageManager

logger = logging.getLogger(__name__)


class NoteWindow(QWidget):
    request_new_note = pyqtSignal()
    request_delete = pyqtSignal(str)
    request_duplicate = pyqtSignal(str)
    note_data_changed = pyqtSignal(str)
    TB = 28

    def __init__(
        self,
        note_data: dict[str, Any],
        storage: StorageManager,
        *,
        dark_mode: bool = False,
    ) -> None:
        super().__init__()
        self.note_data = note_data
        self.storage = storage
        self.note_id = note_data["id"]
        self._dark = dark_mode
        self._revealed = False
        self._drag_on = False
        self._drag_start = QPoint()
        self._editing = False
        self._auto_resizing = False
        self._full_h = note_data.get("height", DEFAULT_NOTE_H)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._persist)
        self._expand_timer = QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.setInterval(24)
        self._expand_timer.timeout.connect(self._expand_for_editing)
        self._copy_revert = QTimer(self)
        self._copy_revert.setSingleShot(True)
        self._copy_revert.setInterval(1000)
        self._copy_revert.timeout.connect(self._reset_copy_icon)
        self._checklist_syncing = False
        self._build_ui()
        self._apply_data()
        self._apply_style()
        self._refresh_dots()
        self._apply_shadow()

    def _apply_shadow(self) -> None:
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(16)
        effect.setOffset(0, 4)
        effect.setColor(QColor(0, 0, 0, 48))
        self.setGraphicsEffect(effect)

    def _reset_copy_icon(self) -> None:
        set_button_icon(self.btn_copy, "copy", 16)

    def _build_ui(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.note_data.get("always_on_top", False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setMinimumSize(180, 60)
        self.title_bar = QWidget(self)
        self.title_bar.setFixedHeight(self.TB)
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setCursor(Qt.CursorShape.OpenHandCursor)

        self.btn_copy = QPushButton(self.title_bar)
        self.btn_copy.setFixedSize(24, 24)
        self.btn_copy.setToolTip("Copy to clipboard")
        self.btn_copy.clicked.connect(self._copy)
        self.btn_copy.setObjectName("titleBtn")
        set_button_icon(self.btn_copy, "copy", 16)

        self.btn_lock = QPushButton(self.title_bar)
        self.btn_lock.setFixedSize(24, 24)
        self.btn_lock.setToolTip("Toggle private")
        self.btn_lock.clicked.connect(self._toggle_private)
        self.btn_lock.setObjectName("titleBtn")

        self.btn_compact = QPushButton(self.title_bar)
        self.btn_compact.setFixedSize(24, 24)
        self.btn_compact.setToolTip("Compact / Expand")
        self.btn_compact.clicked.connect(self._toggle_compact)
        self.btn_compact.setObjectName("titleBtn")
        set_button_icon(self.btn_compact, "compact", 16)

        self.btn_pin = QPushButton(self.title_bar)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setToolTip("Toggle always on top")
        self.btn_pin.clicked.connect(self._toggle_on_top)
        self.btn_pin.setObjectName("titleBtn")

        self.btn_close = QPushButton(self.title_bar)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setToolTip("Hide note")
        self.btn_close.clicked.connect(self._hide_note)
        self.btn_close.setObjectName("titleBtn")
        set_button_icon(self.btn_close, "close", 16)

        tb = QHBoxLayout(self.title_bar)
        tb.setContentsMargins(6, 2, 4, 2)
        self._tag_chip = QLabel(self.title_bar)
        self._tag_chip.setObjectName("tagChip")
        self._tag_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tag_chip.mousePressEvent = self._edit_tags  # type: ignore[method-assign]
        tb.addWidget(self._tag_chip)
        for b in (self.btn_copy, self.btn_lock, self.btn_compact):
            tb.addWidget(b)
        tb.addStretch()
        for b in (self.btn_pin, self.btn_close):
            tb.addWidget(b)

        self.checklist_widget = QListWidget(self)
        self.checklist_widget.setObjectName("checklistWidget")
        self.checklist_widget.hide()
        self.checklist_widget.itemChanged.connect(self._on_checklist_item_changed)

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("Type your note here\u2026")
        self.editor.textChanged.connect(self._on_text)
        self.editor.setObjectName("noteEditor")
        self.title_bar.installEventFilter(self)
        self.editor.installEventFilter(self)
        # Clicks land on the viewport, not the QTextEdit widget itself.
        self.editor.viewport().installEventFilter(self)
        self._private_overlay = QWidget(self.editor)
        self._private_overlay.setObjectName("privateOverlay")
        self._private_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self._private_overlay.mousePressEvent = self._reveal_private  # type: ignore[method-assign]
        ov_lo = QVBoxLayout(self._private_overlay)
        ov_lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_lbl = QLabel(
            f"\U0001F512  {private_preview_text()}", self._private_overlay
        )
        self._overlay_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_lbl.setWordWrap(True)
        self._overlay_lbl.setObjectName("privateOverlayLabel")
        ov_lo.addWidget(self._overlay_lbl)

        self.colour_row = QWidget(self)
        self.colour_row.setObjectName("colourRow")
        self.colour_row.setFixedHeight(24)
        cr = QHBoxLayout(self.colour_row)
        cr.setContentsMargins(8, 2, 8, 2)
        cr.setSpacing(4)
        self._dots: dict[str, QPushButton] = {}
        for name in NOTE_COLOURS:
            d = QPushButton(self.colour_row)
            d.setFixedSize(16, 16)
            d.setToolTip(name.capitalize())
            d.setCursor(Qt.CursorShape.PointingHandCursor)
            d.clicked.connect(lambda _, n=name: self._change_colour(n))
            cr.addWidget(d)
            self._dots[name] = d
        cr.addStretch()
        self.grip = QSizeGrip(self.colour_row)
        self.grip.setFixedSize(16, 16)
        cr.addWidget(self.grip)

        self.meta_row = QWidget(self)
        self.meta_row.setObjectName("metaRow")
        self.meta_row.setFixedHeight(18)
        meta_lo = QHBoxLayout(self.meta_row)
        meta_lo.setContentsMargins(0, 0, 0, 0)
        self.lbl_ts = QLabel(self.meta_row)
        self.lbl_ts.setObjectName("tsLabel")
        self.lbl_ts.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        meta_lo.addWidget(self.lbl_ts, 1)
        self._update_ts()

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        lo.addWidget(self.title_bar)
        lo.addWidget(self.checklist_widget)
        lo.addWidget(self.editor, 1)
        lo.addWidget(self.colour_row)
        lo.addWidget(self.meta_row)

    def set_dark_mode(self, dark: bool) -> None:
        self._dark = dark

    def _refresh_title_icons(self) -> None:
        set_button_icon(self.btn_copy, "copy", 16)
        lock_name = "lock" if is_private(self.note_data) else "unlock"
        set_button_icon(self.btn_lock, lock_name, 16)
        compact_name = "expand" if self.note_data.get("compact") else "compact"
        set_button_icon(self.btn_compact, compact_name, 16)
        pin_name = "pin" if self.note_data.get("always_on_top") else "unpin"
        set_button_icon(self.btn_pin, pin_name, 16)
        set_button_icon(self.btn_close, "close", 16)
        for btn in (self.btn_copy, self.btn_lock, self.btn_compact, self.btn_pin, self.btn_close):
            btn.setStyleSheet(title_button_stylesheet(size=24))

    def get_content(self) -> str:
        if self.note_data.get("checklist"):
            return self._checklist_to_text()
        return self.editor.toPlainText()

    def _checklist_to_text(self) -> str:
        lines: list[str] = []
        for i in range(self.checklist_widget.count()):
            item = self.checklist_widget.item(i)
            if item is None:
                continue
            mark = "x" if item.checkState() == Qt.CheckState.Checked else " "
            text = item.text().strip()
            lines.append(f"- [{mark}] {text}")
        return "\n".join(lines)

    def _text_to_checklist(self, content: str) -> None:
        self._checklist_syncing = True
        try:
            self.checklist_widget.clear()
            for checked, text in parse_checklist(content):
                item = QListWidgetItem(text)
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                item.setCheckState(
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
                font = item.font()
                font.setStrikeOut(checked)
                item.setFont(font)
                self.checklist_widget.addItem(item)
        finally:
            self._checklist_syncing = False

    def _on_checklist_item_changed(self, item: QListWidgetItem) -> None:
        if self._checklist_syncing:
            return
        checked = item.checkState() == Qt.CheckState.Checked
        font = item.font()
        font.setStrikeOut(checked)
        item.setFont(font)
        self._update_ts()
        self._save_timer.start()

    def _set_checklist_mode(self, on: bool) -> None:
        if self.note_data.get("checklist") == on:
            return
        if on:
            content = self.editor.toPlainText()
            if not content_has_checklist_items(content) and content.strip():
                content = "\n".join(f"- [ ] {line}" for line in content.splitlines())
            self.note_data["content"] = content
            self._text_to_checklist(content)
            self.editor.hide()
            self.checklist_widget.show()
        else:
            self.note_data["content"] = self._checklist_to_text()
            self.editor.setPlainText(self.note_data["content"])
            self.checklist_widget.hide()
            self.editor.show()
        self.note_data["checklist"] = on
        self._update_ts()
        self._persist()

    def _toggle_checklist_mode(self) -> None:
        self._set_checklist_mode(not self.note_data.get("checklist", False))

    def _add_checklist_item(self) -> None:
        text, ok = QInputDialog.getText(self, "Add item", "Item text:")
        if not ok or not text.strip():
            return
        item = QListWidgetItem(text.strip())
        item.setFlags(
            item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
        )
        item.setCheckState(Qt.CheckState.Unchecked)
        self.checklist_widget.addItem(item)
        self._persist()

    def _clear_completed_checklist(self) -> None:
        if not self.note_data.get("checklist"):
            return
        self._checklist_syncing = True
        try:
            for i in range(self.checklist_widget.count() - 1, -1, -1):
                item = self.checklist_widget.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    self.checklist_widget.takeItem(i)
        finally:
            self._checklist_syncing = False
        self._persist()

    def _update_tag_chip(self) -> None:
        tags = self.note_data.get("tags", [])
        if tags:
            self._tag_chip.setText(f"#{tags[0]}")
            self._tag_chip.setToolTip(", ".join(f"#{t}" for t in tags))
            self._tag_chip.show()
        else:
            self._tag_chip.setText("")
            self._tag_chip.hide()

    def _edit_tags(self, _event=None) -> None:
        current = ", ".join(self.note_data.get("tags", []))
        text, ok = QInputDialog.getText(
            self,
            "Note tags",
            "Tags (comma-separated):",
            text=current,
        )
        if not ok:
            return
        self.note_data["tags"] = normalize_tags(
            [part.strip() for part in text.split(",") if part.strip()]
        )
        self._update_tag_chip()
        self._persist()

    def set_reminder(self, iso: str | None) -> None:
        self.note_data["reminder_at"] = iso
        self._update_ts()
        self._persist()

    def _pick_reminder(self, when: datetime) -> None:
        self.set_reminder(when.isoformat(timespec="seconds"))

    def _clear_reminder_menu(self) -> None:
        self.set_reminder(None)

    def _custom_reminder(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            "Custom reminder",
            "Date/time (YYYY-MM-DD HH:MM):",
        )
        if not ok or not text.strip():
            return
        try:
            when = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            QMessageBox.warning(self, "Invalid date", "Use format YYYY-MM-DD HH:MM")
            return
        self._pick_reminder(when)

    def _real_content(self) -> str:
        return self.get_content()

    def _copy(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self._real_content())
        set_button_icon(self.btn_copy, "check", 16)
        self._copy_revert.start()

    def _reveal_private(self, _e=None) -> None:
        self._revealed = True
        self._apply_private_state()
        self._editing = True
        self.editor.setFocus()
        self._expand_for_editing()

    def _hide_private_content(self) -> None:
        self._revealed = False
        self._apply_private_state()

    def _set_private(self, on: bool) -> None:
        if is_private(self.note_data) == on:
            return
        self.note_data["private"] = on
        if on:
            self._revealed = False
        self._apply_private_state()
        self._persist()

    def _toggle_private(self) -> None:
        self._set_private(not is_private(self.note_data))

    def _apply_private_state(self) -> None:
        masked = is_private(self.note_data) and not self._revealed
        compact = self.note_data.get("compact", False)
        self.btn_lock.setToolTip(
            "Remove private" if is_private(self.note_data) else "Make private"
        )
        lock_name = "lock" if is_private(self.note_data) else "unlock"
        set_button_icon(self.btn_lock, lock_name, 16)
        if masked and not compact:
            self._private_overlay.show()
            self._private_overlay.raise_()
            self.editor.setReadOnly(True)
        else:
            self._private_overlay.hide()
            self.editor.setReadOnly(False)
        self._update_ts()
        self._update_overlay_style()
        self.note_data_changed.emit(self.note_id)

    def _update_overlay_style(self) -> None:
        cn = self.note_data.get("colour", "yellow")
        bg = NOTE_COLOURS.get(cn, "#FDFD96")
        self._private_overlay.setStyleSheet(
            f"#privateOverlay{{background:{bg};border:none;}}"
            f"#privateOverlayLabel{{font-size:{FONT_BODY}px;color:{INK_MUTED};background:transparent;padding:12px;}}"
        )

    def _apply_data(self) -> None:
        d = self.note_data
        self.move(d.get("x", 200), d.get("y", 200))
        self._full_h = d.get("height", DEFAULT_NOTE_H)
        self.resize(d.get("width", DEFAULT_NOTE_W), self._full_h)
        content = d.get("content", "")
        if d.get("checklist"):
            self._text_to_checklist(content)
            self.editor.hide()
            self.checklist_widget.show()
        else:
            self.editor.setPlainText(content)
        self._update_tag_chip()
        self.setWindowOpacity(d.get("opacity", 1.0))
        if d.get("compact", False):
            self._set_compact(True)
        if is_private(d):
            self._revealed = False
        self._apply_private_state()
        if d.get("visible", True):
            self.show()

    def _apply_style(self) -> None:
        cn = self.note_data.get("colour", "yellow")
        bg = NOTE_COLOURS.get(cn, "#FDFD96")
        tb = TITLE_BAR_COLOURS.get(cn, "#E8E85C")
        self.setStyleSheet(note_window_stylesheet(bg, tb))
        self.editor.setStyleSheet("")
        for btn in (self.btn_copy, self.btn_lock, self.btn_compact, self.btn_pin, self.btn_close):
            btn.setStyleSheet(title_button_stylesheet(size=24))
        self._refresh_title_icons()
        self._update_overlay_style()

    def _refresh_dots(self) -> None:
        active = self.note_data.get("colour", "yellow")
        for name, dot in self._dots.items():
            dot.setStyleSheet(
                colour_dot_stylesheet(NOTE_COLOURS[name], selected=name == active)
            )

    def _update_ts(self) -> None:
        mod = self.note_data.get("modified_at", "")
        reminder = self.note_data.get("reminder_at")
        reminder_txt = ""
        if reminder:
            overdue = ReminderService.is_overdue(reminder)
            prefix = "Overdue" if overdue else "Reminder"
            reminder_txt = (
                f"  \u00B7  {prefix}: {ReminderService.format_reminder(reminder)}"
            )
        if is_private(self.note_data) and not self._revealed:
            self.lbl_ts.setText(
                f"Private{reminder_txt}  \u00B7  Modified: {fmt_dt(mod)}"
                if mod
                else f"Private{reminder_txt}"
            )
            return
        c = len(self.get_content())
        if self.note_data.get("checklist"):
            done, total = checklist_progress(self.get_content())
            prog = f"  \u00B7  {done}/{total} done" if total else ""
            self.lbl_ts.setText(
                f"{c} chars{prog}{reminder_txt}  \u00B7  Modified: {fmt_dt(mod)}"
                if mod
                else f"{c} chars{prog}{reminder_txt}"
            )
            return
        self.lbl_ts.setText(
            f"{c} chars{reminder_txt}  \u00B7  Modified: {fmt_dt(mod)}"
            if mod
            else f"{c} chars{reminder_txt}"
        )

    def contextMenuEvent(self, e) -> None:
        m = QMenu(self)
        m.setStyleSheet(menu_stylesheet(dark=self._dark))
        m.addAction("\u2795  New Note").triggered.connect(
            lambda: self.request_new_note.emit()
        )
        m.addAction("\U0001F4C4  Duplicate Note").triggered.connect(
            lambda: self.request_duplicate.emit(self.note_id)
        )
        m.addAction("\U0001F4CB  Copy to Clipboard").triggered.connect(self._copy)
        m.addSeparator()
        cl = m.addAction("\u2611  Checklist mode")
        cl.setCheckable(True)
        cl.setChecked(self.note_data.get("checklist", False))
        cl.triggered.connect(self._toggle_checklist_mode)
        if self.note_data.get("checklist"):
            m.addAction("Clear completed").triggered.connect(self._clear_completed_checklist)
            m.addAction("Add checklist item\u2026").triggered.connect(self._add_checklist_item)
        m.addAction("\U0001F3F7  Edit tags\u2026").triggered.connect(self._edit_tags)
        rm = m.addMenu("\u23F0  Remind me\u2026")
        for label, when in ReminderService.reminder_presets():
            rm.addAction(label).triggered.connect(
                lambda _checked=False, w=when: self._pick_reminder(w)
            )
        rm.addAction("Custom\u2026").triggered.connect(self._custom_reminder)
        if self.note_data.get("reminder_at"):
            rm.addSeparator()
            rm.addAction("Clear reminder").triggered.connect(self._clear_reminder_menu)
        m.addSeparator()
        priv = m.addAction("\U0001F512  Make Private")
        priv.setCheckable(True)
        priv.setChecked(is_private(self.note_data))
        priv.triggered.connect(self._set_private)
        if is_private(self.note_data) and self._revealed:
            m.addAction("\U0001F648  Hide content").triggered.connect(
                self._hide_private_content
            )
        m.addSeparator()
        cm = m.addMenu("\U0001F3A8  Change Colour")
        for name in NOTE_COLOURS:
            cm.addAction(f"\u25CF  {name.capitalize()}").triggered.connect(
                lambda _, n=name: self._change_colour(n)
            )
        ap = m.addAction("\U0001F4CC  Always on Top")
        ap.setCheckable(True)
        ap.setChecked(self.note_data.get("always_on_top", False))
        ap.triggered.connect(self._toggle_on_top)
        om = m.addMenu("\U0001F441  Opacity")
        for label, val in [
            ("100%", 1.0),
            ("85%", 0.85),
            ("70%", 0.70),
            ("50%", 0.50),
        ]:
            om.addAction(label).triggered.connect(lambda _, v=val: self._set_opacity(v))
        m.addSeparator()
        m.addAction("\U0001F5D1  Delete Note").triggered.connect(self._confirm_delete)
        m.exec(e.globalPos())

    def _confirm_delete(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Delete",
                "Delete this note?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.request_delete.emit(self.note_id)

    def _title_bar_is_draggable_at(self, pos: QPoint) -> bool:
        return self.title_bar.childAt(pos) is None

    def _begin_window_drag(self, global_pos: QPoint) -> None:
        if self._drag_on:
            return
        self._drag_on = True
        self._editing = False
        self._drag_start = global_pos - self.frameGeometry().topLeft()
        self.title_bar.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.title_bar.grabMouse()
        self.editor.clearFocus()
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)

    def _move_window_drag(self, global_pos: QPoint) -> None:
        if not self._drag_on:
            return
        self.move(self._snap(global_pos - self._drag_start))

    def _end_window_drag(self) -> None:
        if not self._drag_on:
            return
        self._drag_on = False
        self.title_bar.releaseMouse()
        self.title_bar.setCursor(Qt.CursorShape.OpenHandCursor)
        self.note_data["user_resized"] = True
        self._persist()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_on:
            self._move_window_drag(e.globalPosition().toPoint())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_on and e.button() == Qt.MouseButton.LeftButton:
            self._end_window_drag()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _snap(self, pos: QPoint) -> QPoint:
        s = self.screen()
        if not s:
            return pos
        g = s.availableGeometry()
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        if abs(x - g.left()) < SNAP_THRESHOLD:
            x = g.left()
        if abs(y - g.top()) < SNAP_THRESHOLD:
            y = g.top()
        if abs((x + w) - g.right()) < SNAP_THRESHOLD:
            x = g.right() - w
        if abs((y + h) - g.bottom()) < SNAP_THRESHOLD:
            y = g.bottom() - h
        return QPoint(x, y)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if hasattr(self, "_private_overlay"):
            self._private_overlay.setGeometry(self.editor.rect())
        if (
            not self.note_data.get("compact", False)
            and not self._auto_resizing
            and not self._editing
        ):
            self._full_h = self.height()
        self.note_data["user_resized"] = True
        self._save_timer.start()

    def moveEvent(self, e) -> None:
        super().moveEvent(e)
        self._save_timer.start()

    def _on_text(self) -> None:
        self._update_ts()
        if (
            self._editing
            and not self.note_data.get("compact")
            and not self._drag_on
        ):
            self._expand_timer.start()
        self._save_timer.start()

    def _persist(self) -> None:
        c = self.get_content()
        if c != self.note_data.get("content", ""):
            self.note_data["modified_at"] = datetime.now().isoformat(timespec="seconds")
        self.note_data.update(
            {
                "content": c,
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self._full_h,
            }
        )
        self._update_ts()
        self.storage.set_note(self.note_id, self.note_data)
        self.note_data_changed.emit(self.note_id)

    def _change_colour(self, n: str) -> None:
        if n not in NOTE_COLOURS:
            return
        self.note_data["colour"] = n
        self._apply_style()
        self._refresh_dots()
        self._persist()

    def _chrome_height(self) -> int:
        return self.TB + self.colour_row.height() + self.meta_row.height()

    def _expanded_height(self) -> int:
        doc = self.editor.document()
        vw = self.editor.viewport().width()
        if vw <= 1:
            vw = max(1, self.editor.width() - 2 * self.editor.frameWidth())
        doc.setTextWidth(max(1, vw))
        # Stylesheet padding (8px top/bottom) + document margins.
        pad = 16 + int(2 * doc.documentMargin())
        content_h = int(doc.size().height()) + pad
        return self._chrome_height() + max(40, content_h)

    def _editor_content_overflows(self) -> bool:
        sb = self.editor.verticalScrollBar()
        return sb is not None and sb.maximum() > 0

    def _begin_editing_expand(self) -> None:
        if self._drag_on or self.note_data.get("compact"):
            return
        self._editing = True
        self._expand_timer.start()

    def _deferred_end_editing(self) -> None:
        if self._drag_on:
            return
        fw = QApplication.focusWidget()
        if fw is not None and self.isAncestorOf(fw):
            return
        self._editing = False
        self._collapse_to_rest()

    def _expand_for_editing(self) -> None:
        if (
            self.note_data.get("compact")
            or self._drag_on
            or self._auto_resizing
        ):
            return
        target = max(self._full_h, self._expanded_height())
        if target <= self.height():
            if not self._editor_content_overflows():
                return
            sb = self.editor.verticalScrollBar()
            target = self.height() + sb.maximum() - sb.value() + 8
        self._auto_resizing = True
        try:
            self.resize(self.width(), target)
        finally:
            self._auto_resizing = False

    def _collapse_to_rest(self) -> None:
        if self.note_data.get("compact"):
            return
        if self.height() == self._full_h:
            return
        self.resize(self.width(), self._full_h)

    def eventFilter(self, obj, event) -> bool:
        try:
            return self._dispatch_event_filter(obj, event)
        except Exception:
            logger.exception("note %s eventFilter error", self.note_id)
            return False

    def _dispatch_event_filter(self, obj, event) -> bool:
        if obj is self.title_bar:
            et = event.type()
            if et == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
                if (
                    event.button() == Qt.MouseButton.LeftButton
                    and self._title_bar_is_draggable_at(event.pos())
                ):
                    self._begin_window_drag(event.globalPosition().toPoint())
                    return True
            elif self._drag_on:
                if et == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
                    self._move_window_drag(event.globalPosition().toPoint())
                    return True
                if (
                    et == QEvent.Type.MouseButtonRelease
                    and isinstance(event, QMouseEvent)
                    and event.button() == Qt.MouseButton.LeftButton
                ):
                    self._end_window_drag()
                    return True

        editor_targets = (self.editor, self.editor.viewport())
        if self._drag_on and obj in editor_targets:
            if event.type() in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseMove,
                QEvent.Type.MouseButtonDblClick,
                QEvent.Type.DragEnter,
                QEvent.Type.DragMove,
                QEvent.Type.Drop,
            ):
                return True

        if not self.note_data.get("compact"):
            if (
                obj is self.editor.viewport()
                and event.type() == QEvent.Type.MouseButtonPress
                and isinstance(event, QMouseEvent)
                and event.button() == Qt.MouseButton.LeftButton
                and not self._drag_on
            ):
                self._begin_editing_expand()
            elif obj is self.editor and event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(0, self._deferred_end_editing)
        return super().eventFilter(obj, event)

    def _set_opacity(self, v: float) -> None:
        self.note_data["opacity"] = v
        self.setWindowOpacity(v)
        self._persist()

    def _toggle_on_top(self) -> None:
        on = not self.note_data.get("always_on_top", False)
        self.note_data["always_on_top"] = on
        f = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if on:
            f |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(f)
        self.show()
        self._configure_macos_window_level()
        self._apply_style()
        self._persist()

    def _toggle_compact(self) -> None:
        c = not self.note_data.get("compact", False)
        self._set_compact(c)
        self.note_data["compact"] = c
        self._apply_private_state()
        self._persist()

    def _set_compact(self, c: bool) -> None:
        if c:
            if not self.note_data.get("compact", False):
                self._full_h = self.height()
            self.editor.hide()
            self.checklist_widget.hide()
            self.colour_row.hide()
            self.meta_row.hide()
            self.setFixedHeight(self.TB + 4)
            set_button_icon(self.btn_compact, "expand", 16)
            self.btn_compact.setToolTip("Expand")
        else:
            self.colour_row.show()
            self.meta_row.show()
            if self.note_data.get("checklist"):
                self.checklist_widget.show()
                self.editor.hide()
            else:
                self.editor.show()
                self.checklist_widget.hide()
            self.setMinimumHeight(60)
            self.setMaximumHeight(16777215)
            self.resize(self.width(), self._full_h)
            self.setMinimumHeight(60)
            self.setMaximumHeight(16777215)
            set_button_icon(self.btn_compact, "compact", 16)
            self.btn_compact.setToolTip("Compact")

    def _hide_note(self) -> None:
        if not self.get_content().strip():
            self.request_delete.emit(self.note_id)
            return
        self.note_data["visible"] = False
        self._persist()
        self.hide()

    def show_note(self) -> None:
        self.note_data["visible"] = True
        if self.get_content().strip():
            self._persist()
        self.show()
        self.raise_()
        self.activateWindow()

    def _configure_macos_window_level(self) -> None:
        if sys.platform != "darwin":
            return
        try:
            from stickynotes.platform.macos.windows import configure_floating_window

            configure_floating_window(
                self, on_top=self.note_data.get("always_on_top", False)
            )
        except Exception:
            pass

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._configure_macos_window_level()
