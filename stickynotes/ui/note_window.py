"""Individual sticky note window."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizeGrip,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from stickynotes.models import fmt_dt
from stickynotes.theme import (
    DEFAULT_NOTE_H,
    DEFAULT_NOTE_W,
    NOTE_COLOURS,
    SNAP_THRESHOLD,
    TITLE_BAR_COLOURS,
)

if TYPE_CHECKING:
    from stickynotes.storage import StorageManager


class NoteWindow(QWidget):
    request_new_note = pyqtSignal()
    request_delete = pyqtSignal(str)
    request_duplicate = pyqtSignal(str)
    note_data_changed = pyqtSignal(str)
    TB = 28

    def __init__(self, note_data: dict[str, Any], storage: StorageManager) -> None:
        super().__init__()
        self.note_data = note_data
        self.storage = storage
        self.note_id = note_data["id"]
        self._drag_on = False
        self._drag_start = QPoint()
        self._full_h = note_data.get("height", DEFAULT_NOTE_H)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._persist)
        self._copy_revert = QTimer(self)
        self._copy_revert.setSingleShot(True)
        self._copy_revert.setInterval(1000)
        self._copy_revert.timeout.connect(lambda: self.btn_copy.setText("\U0001F4CB"))
        self._build_ui()
        self._apply_data()
        self._apply_style()
        self._refresh_dots()

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
        self.btn_copy = QPushButton("\U0001F4CB", self.title_bar)
        self.btn_copy.setFixedSize(24, 24)
        self.btn_copy.setToolTip("Copy to clipboard")
        self.btn_copy.clicked.connect(self._copy)
        self.btn_copy.setObjectName("titleBtn")
        self.btn_compact = QPushButton("\u25AC", self.title_bar)
        self.btn_compact.setFixedSize(24, 24)
        self.btn_compact.setToolTip("Compact / Expand")
        self.btn_compact.clicked.connect(self._toggle_compact)
        self.btn_compact.setObjectName("titleBtn")
        self.btn_pin = QPushButton("\U0001F4CC", self.title_bar)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setToolTip("Toggle always on top")
        self.btn_pin.clicked.connect(self._toggle_on_top)
        self.btn_pin.setObjectName("titleBtn")
        self.btn_close = QPushButton("\u2715", self.title_bar)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setToolTip("Hide note")
        self.btn_close.clicked.connect(self._hide_note)
        self.btn_close.setObjectName("titleBtn")
        tb = QHBoxLayout(self.title_bar)
        tb.setContentsMargins(6, 2, 4, 2)
        tb.addStretch()
        for b in (self.btn_copy, self.btn_compact, self.btn_pin, self.btn_close):
            tb.addWidget(b)
        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("Type your note here\u2026")
        self.editor.textChanged.connect(self._on_text)
        self.editor.setObjectName("noteEditor")
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
        self.lbl_ts = QLabel(self)
        self.lbl_ts.setObjectName("tsLabel")
        self.lbl_ts.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._update_ts()
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        bot = QHBoxLayout()
        bot.setContentsMargins(6, 0, 2, 2)
        bot.addWidget(self.lbl_ts, 1)
        bot.addWidget(self.grip, 0)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        lo.addWidget(self.title_bar)
        lo.addWidget(self.editor, 1)
        lo.addWidget(self.colour_row)
        lo.addLayout(bot)

    def _copy(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.editor.toPlainText())
        self.btn_copy.setText("\u2713")
        self._copy_revert.start()

    def _apply_data(self) -> None:
        d = self.note_data
        self.move(d.get("x", 200), d.get("y", 200))
        self._full_h = d.get("height", DEFAULT_NOTE_H)
        self.resize(d.get("width", DEFAULT_NOTE_W), self._full_h)
        self.editor.setPlainText(d.get("content", ""))
        self.setWindowOpacity(d.get("opacity", 1.0))
        if d.get("compact", False):
            self._set_compact(True)
        if d.get("visible", True):
            self.show()

    def _apply_style(self) -> None:
        cn = self.note_data.get("colour", "yellow")
        bg = NOTE_COLOURS.get(cn, "#FDFD96")
        tb = TITLE_BAR_COLOURS.get(cn, "#E8E85C")
        self.btn_pin.setText(
            "\U0001F4CC" if self.note_data.get("always_on_top") else "\U0001F4CD"
        )
        self.setStyleSheet(f"""
            NoteWindow {{background:{bg};border:1px solid {tb};border-radius:8px;}}
            #titleBar {{background:{tb};border-top-left-radius:8px;border-top-right-radius:8px;}}
            #titleBtn {{background:transparent;border:none;font-size:13px;border-radius:4px;color:#333;}}
            #titleBtn:hover {{background:rgba(255,255,255,0.45);}}
            #noteEditor {{background:{bg};border:none;font-size:13px;padding:6px;color:#222;selection-background-color:{tb};}}
            #colourRow {{background:transparent;}}
            #tsLabel {{font-size:10px;color:#777;font-style:italic;padding:0 4px;background:transparent;}}
            QSizeGrip {{background:transparent;width:16px;height:16px;}}
        """)

    def _refresh_dots(self) -> None:
        active = self.note_data.get("colour", "yellow")
        for name, dot in self._dots.items():
            hc = NOTE_COLOURS[name]
            if name == active:
                dot.setStyleSheet(
                    f"QPushButton{{background:{hc};border:2px solid #333;border-radius:8px;}}"
                )
            else:
                dot.setStyleSheet(
                    f"QPushButton{{background:{hc};border:1px solid #aaa;border-radius:8px;}}"
                    f"QPushButton:hover{{border:2px solid #555;}}"
                )

    def _update_ts(self) -> None:
        mod = self.note_data.get("modified_at", "")
        c = len(self.editor.toPlainText())
        self.lbl_ts.setText(
            f"{c} chars  \u00B7  Modified: {fmt_dt(mod)}" if mod else f"{c} chars"
        )

    def contextMenuEvent(self, e) -> None:
        m = QMenu(self)
        m.setStyleSheet(
            "QMenu{background:#fff;border:1px solid #ccc;padding:4px;border-radius:6px;}"
            "QMenu::item{padding:6px 20px;border-radius:4px;}"
            "QMenu::item:selected{background:#0078D4;color:#fff;}"
            "QMenu::separator{height:1px;background:#ddd;margin:4px 8px;}"
        )
        m.addAction("\u2795  New Note").triggered.connect(
            lambda: self.request_new_note.emit()
        )
        m.addAction("\U0001F4C4  Duplicate Note").triggered.connect(
            lambda: self.request_duplicate.emit(self.note_id)
        )
        m.addAction("\U0001F4CB  Copy to Clipboard").triggered.connect(self._copy)
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

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and e.pos().y() <= self.TB:
            self._drag_on = True
            self._drag_start = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.title_bar.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if self._drag_on:
            self.move(self._snap(e.globalPosition().toPoint() - self._drag_start))
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_on:
            self._drag_on = False
            self.title_bar.setCursor(Qt.CursorShape.OpenHandCursor)
            self.note_data["user_resized"] = True
            self._persist()
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
        if not self.note_data.get("compact", False):
            self._full_h = self.height()
        self.note_data["user_resized"] = True
        self._save_timer.start()

    def moveEvent(self, e) -> None:
        super().moveEvent(e)
        self._save_timer.start()

    def _on_text(self) -> None:
        self._update_ts()
        self._save_timer.start()

    def _persist(self) -> None:
        c = self.editor.toPlainText()
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
        self.note_data["colour"] = n
        self._apply_style()
        self._refresh_dots()
        self._persist()

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
        self._persist()

    def _set_compact(self, c: bool) -> None:
        if c:
            if not self.note_data.get("compact", False):
                self._full_h = self.height()
            self.editor.hide()
            self.lbl_ts.hide()
            self.grip.hide()
            self.setFixedHeight(self.TB + 28)
            self.btn_compact.setText("\u25BC")
            self.btn_compact.setToolTip("Expand")
        else:
            self.editor.show()
            self.lbl_ts.show()
            self.grip.show()
            self.setMinimumHeight(60)
            self.setMaximumHeight(16777215)
            self.resize(self.width(), self._full_h)
            self.setMinimumHeight(60)
            self.setMaximumHeight(16777215)
            self.btn_compact.setText("\u25AC")
            self.btn_compact.setToolTip("Compact")

    def _hide_note(self) -> None:
        if not self.editor.toPlainText().strip():
            self.request_delete.emit(self.note_id)
            return
        self.note_data["visible"] = False
        self._persist()
        self.hide()

    def show_note(self) -> None:
        self.note_data["visible"] = True
        if self.editor.toPlainText().strip():
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
