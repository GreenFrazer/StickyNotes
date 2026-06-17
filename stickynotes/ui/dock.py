"""Auto-hiding dock widgets — one per monitor."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import (
    QPoint,
    QPropertyAnimation,
    QRect,
    QEasingCurve,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
    QEvent,
)
from PyQt6.QtGui import (
    QCursor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from stickynotes import __version__, build_date_display
from stickynotes.models import (
    MAX_DOCK_WIDTH,
    MIN_DOCK_WIDTH,
    clamp_dock_width,
    checklist_progress,
    dock_file_badge,
    dock_file_label,
    dock_indicator_text,
    dock_popup_preview_text,
    fmt_dt,
    is_dock_pinnable_file,
    is_private,
    local_paths_from_mime_urls,
)
from stickynotes.reminders import ReminderService
from stickynotes.theme import (
    NOTE_COLOURS,
    TITLE_BAR_COLOURS,
    colour_dot_frame_stylesheet,
    copy_button_stylesheet,
    dock_file_icon_stylesheet,
    dock_file_indicator_stylesheet,
    dock_file_label_stylesheet,
    dock_note_indicator_stylesheet,
    dock_preview_label_stylesheet,
    dock_resize_handle_stylesheet,
    dock_scroll_stylesheet,
    dock_stylesheet,
    file_popup_stylesheet,
    menu_stylesheet,
    note_popup_stylesheet,
)
from stickynotes.ui.file_icons import file_icon_pixmap
from stickynotes.ui.icons import set_button_icon

DOCK_FILE_ICON_SIZE = 24


def _make_dock_btn(
    icon_name: str,
    label_text: str,
    signal=None,
    *,
    on_click: Callable[[], None] | None = None,
) -> QWidget:
    w = QWidget()
    w.setFixedWidth(48)
    lo = QVBoxLayout(w)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(0)
    lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn = QPushButton()
    btn.setToolTip(label_text)
    btn.setFixedSize(44, 44)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click is not None:
        btn.clicked.connect(on_click)
    elif signal is not None:
        btn.clicked.connect(signal.emit)
    btn.setObjectName("dockBtn")
    set_button_icon(btn, icon_name, 20, light=True)
    lo.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
    w.btn = btn  # type: ignore[attr-defined]
    return w


def _make_sep(horiz: bool = False) -> QFrame:
    sep = QFrame()
    sep.setObjectName("dockSep")
    if horiz:
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(2)
        sep.setFixedHeight(44)
    else:
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(2)
    return sep


class DockNotePopup(QWidget):
    clicked = pyqtSignal(str)

    def __init__(
        self,
        note_data: dict[str, Any],
        content_getter: Callable[[str], str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.note_id = note_data["id"]
        self._content_getter = content_getter
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(240, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_revert = QTimer(self)
        self._copy_revert.setSingleShot(True)
        self._copy_revert.setInterval(1000)
        self._build(note_data)

    def _build(self, d: dict[str, Any]) -> None:
        cn = d.get("colour", "yellow")
        bg = NOTE_COLOURS.get(cn, "#FDFD96")
        tb = TITLE_BAR_COLOURS.get(cn, "#E8E85C")
        title = QWidget(self)
        title.setFixedHeight(28)
        title.setObjectName("pTitleBar")
        tl = QHBoxLayout(title)
        tl.setContentsMargins(8, 2, 4, 2)
        tl.addStretch()
        self.btn_copy = QPushButton(title)
        self.btn_copy.setFixedSize(22, 22)
        self.btn_copy.setToolTip("Copy to clipboard")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setObjectName("pTitleBtn")
        set_button_icon(self.btn_copy, "copy", 14)
        self.btn_copy.clicked.connect(self._copy)
        self._copy_revert.timeout.connect(
            lambda: set_button_icon(self.btn_copy, "copy", 14)
        )
        tl.addWidget(self.btn_copy)
        content = d.get("content", "")
        if is_private(d):
            preview_text = dock_popup_preview_text()
        else:
            preview_text = content[:300] if content else ""
        self.preview = QLabel(preview_text)
        self.preview.setWordWrap(True)
        self.preview.setObjectName("pText")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignTop)
        crow = QWidget()
        crow.setFixedHeight(22)
        crow.setObjectName("pColourRow")
        cl = QHBoxLayout(crow)
        cl.setContentsMargins(8, 2, 8, 2)
        cl.setSpacing(4)
        for nm in NOTE_COLOURS:
            dot = QFrame(crow)
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(
                colour_dot_frame_stylesheet(
                    NOTE_COLOURS[nm], selected=nm == cn
                )
            )
            cl.addWidget(dot)
        cl.addStretch()
        chars = len(content)
        mod = d.get("modified_at", "")
        if is_private(d):
            ts = f"Private  \u00B7  Modified: {fmt_dt(mod)}" if mod else "Private"
        elif d.get("checklist"):
            done, total = checklist_progress(content)
            extra = f"  \u00B7  {done}/{total} done" if total else ""
            ts = f"{chars} chars{extra}  \u00B7  Modified: {fmt_dt(mod)}" if mod else ""
        else:
            ts = f"{chars} chars  \u00B7  Modified: {fmt_dt(mod)}" if mod else ""
        self.ts_label = QLabel(ts)
        self.ts_label.setObjectName("pTs")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 4)
        lo.setSpacing(0)
        lo.addWidget(title)
        lo.addWidget(self.preview, 1)
        lo.addWidget(crow)
        lo.addWidget(self.ts_label)
        self.btn_copy.setStyleSheet(copy_button_stylesheet(size=22))
        self.setStyleSheet(note_popup_stylesheet(bg, tb))

    def update_content(self, note_data: dict[str, Any]) -> None:
        content = note_data.get("content", "")
        if is_private(note_data):
            self.preview.setText(dock_popup_preview_text())
            mod = note_data.get("modified_at", "")
            self.ts_label.setText(
                f"Private  \u00B7  Modified: {fmt_dt(mod)}" if mod else "Private"
            )
            return
        self.preview.setText(content[:300] if content else "")
        mod = note_data.get("modified_at", "")
        chars = len(content)
        if note_data.get("checklist"):
            done, total = checklist_progress(content)
            extra = f"  \u00B7  {done}/{total} done" if total else ""
            self.ts_label.setText(
                f"{chars} chars{extra}  \u00B7  Modified: {fmt_dt(mod)}" if mod else ""
            )
            return
        self.ts_label.setText(
            f"{chars} chars  \u00B7  Modified: {fmt_dt(mod)}" if mod else ""
        )

    def _copy(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self._content_getter(self.note_id))
        set_button_icon(self.btn_copy, "check", 14)
        self._copy_revert.start()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.note_id)
        super().mousePressEvent(e)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if sys.platform == "darwin":
            from stickynotes.platform.macos.windows import schedule_configure_floating_window

            schedule_configure_floating_window(self, on_top=True)


class DockNoteIndicator(QFrame):
    sig_click = pyqtSignal(str)
    sig_hover_enter = pyqtSignal(str, QPoint)
    sig_hover_leave = pyqtSignal(str)

    def __init__(
        self,
        note_data: dict[str, Any],
        content_getter: Callable[[str], str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.note_id = note_data["id"]
        self._content_getter = content_getter
        self._colour = note_data.get("colour", "yellow")
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(2, 1, 2, 2)
        lo.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        top.addStretch()
        self.btn_copy = QPushButton(self)
        self.btn_copy.setFixedSize(18, 18)
        self.btn_copy.setToolTip("Copy")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setObjectName("dockIndCopy")
        set_button_icon(self.btn_copy, "copy", 12, light=False)
        self.btn_copy.setStyleSheet(copy_button_stylesheet(size=18))
        self.btn_copy.clicked.connect(self._do_copy)
        self._copy_revert = QTimer(self)
        self._copy_revert.setSingleShot(True)
        self._copy_revert.setInterval(1000)
        self._copy_revert.timeout.connect(
            lambda: set_button_icon(self.btn_copy, "copy", 12, light=False)
        )
        top.addWidget(self.btn_copy)
        lo.addLayout(top)
        self.lbl_preview = QLabel(self)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet(dock_preview_label_stylesheet())
        lo.addWidget(self.lbl_preview)
        self._apply_appearance(note_data)

    def _apply_appearance(self, note_data: dict[str, Any]) -> None:
        self._colour = note_data.get("colour", "yellow")
        cn = self._colour
        bg = NOTE_COLOURS.get(cn, "#FDFD96")
        tb = TITLE_BAR_COLOURS.get(cn, "#E8E85C")
        txt = dock_indicator_text(note_data)
        self.lbl_preview.setText(txt)
        visible = note_data.get("visible", True)
        overdue = ReminderService.is_overdue(note_data.get("reminder_at"))
        self.setStyleSheet(
            dock_note_indicator_stylesheet(
                bg, tb, visible=visible, overdue=overdue
            )
        )

    def update_note(self, note_data: dict[str, Any]) -> None:
        self._apply_appearance(note_data)

    def _do_copy(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self._content_getter(self.note_id))
        set_button_icon(self.btn_copy, "check", 12, light=False)
        self._copy_revert.start()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(e.pos())
            if child is not self.btn_copy:
                self.sig_click.emit(self.note_id)
        super().mousePressEvent(e)

    def enterEvent(self, e) -> None:
        self.sig_hover_enter.emit(self.note_id, self.mapToGlobal(QPoint(0, 0)))
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self.sig_hover_leave.emit(self.note_id)
        super().leaveEvent(e)


class DockFilePopup(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, shortcut_data: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.shortcut_id = shortcut_data["id"]
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(260, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(shortcut_data)

    def _build(self, d: dict[str, Any]) -> None:
        path = d.get("path", "")
        label = dock_file_label(path, d.get("label"))
        badge = dock_file_badge(path)
        exists = bool(path) and os.path.isfile(path)
        title_row = QWidget()
        title_lo = QHBoxLayout(title_row)
        title_lo.setContentsMargins(0, 0, 0, 0)
        title_lo.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setObjectName("fpIcon")
        pixmap = file_icon_pixmap(path, size=20)
        if pixmap is not None and not pixmap.isNull():
            icon_lbl.setPixmap(pixmap)
            icon_lbl.setStyleSheet(dock_file_icon_stylesheet())
        else:
            icon_lbl.setText(badge)
            icon_lbl.setStyleSheet(dock_file_label_stylesheet(badge=True))
        title = QLabel(label)
        title.setObjectName("fpTitle")
        title_lo.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        title_lo.addWidget(title, 1, Qt.AlignmentFlag.AlignVCenter)
        path_lbl = QLabel(path)
        path_lbl.setObjectName("fpPath")
        path_lbl.setWordWrap(True)
        hint = QLabel("Click to open" if exists else "File missing")
        hint.setObjectName("fpHint")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 8, 10, 8)
        lo.setSpacing(2)
        lo.addWidget(title_row)
        lo.addWidget(path_lbl, 1)
        lo.addWidget(hint)
        self.setStyleSheet(file_popup_stylesheet(missing=not exists))

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.shortcut_id)
        super().mousePressEvent(e)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if sys.platform == "darwin":
            from stickynotes.platform.macos.windows import schedule_configure_floating_window

            schedule_configure_floating_window(self, on_top=True)


class DockFileIndicator(QFrame):
    sig_click = pyqtSignal(str)
    sig_hover_enter = pyqtSignal(str, QPoint)
    sig_hover_leave = pyqtSignal(str)
    sig_remove = pyqtSignal(str)

    def __init__(self, shortcut_data: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.shortcut_id = shortcut_data["id"]
        self._path = shortcut_data.get("path", "")
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(2, 2, 2, 2)
        lo.setSpacing(0)
        lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge = QLabel(self)
        self.lbl_badge.setObjectName("fileBadge")
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(self.lbl_badge, 0, Qt.AlignmentFlag.AlignCenter)
        self._apply_appearance(shortcut_data)

    def _apply_appearance(self, shortcut_data: dict[str, Any]) -> None:
        self._path = shortcut_data.get("path", "")
        label = dock_file_label(self._path, shortcut_data.get("label"))
        pixmap = file_icon_pixmap(self._path, size=DOCK_FILE_ICON_SIZE)
        if pixmap is not None and not pixmap.isNull():
            self.lbl_badge.setPixmap(pixmap)
            self.lbl_badge.setText("")
            self.lbl_badge.setStyleSheet(dock_file_icon_stylesheet())
        else:
            self.lbl_badge.setPixmap(QPixmap())
            badge = dock_file_badge(self._path)
            self.lbl_badge.setText(badge)
            self.lbl_badge.setStyleSheet(dock_file_label_stylesheet(badge=True))
        exists = bool(self._path) and os.path.isfile(self._path)
        self.setStyleSheet(dock_file_indicator_stylesheet(exists=exists))
        tip = f"{label}\n{self._path}"
        if not exists:
            tip += "\n(File missing)"
        self.setToolTip(tip)

    def update_shortcut(self, shortcut_data: dict[str, Any]) -> None:
        self._apply_appearance(shortcut_data)

    def contextMenuEvent(self, e) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(menu_stylesheet(dark=True))
        menu.addAction("Open file location", lambda: self._open_location())
        menu.addAction("Remove from dock", lambda: self.sig_remove.emit(self.shortcut_id))
        menu.exec(e.globalPos())

    def _open_location(self) -> None:
        from pathlib import Path

        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        path = self._path
        if not path:
            return
        target = path if os.path.isfile(path) else str(Path(path).parent)
        if target and os.path.exists(target):
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.sig_click.emit(self.shortcut_id)
        super().mousePressEvent(e)

    def enterEvent(self, e) -> None:
        self.sig_hover_enter.emit(self.shortcut_id, self.mapToGlobal(QPoint(0, 0)))
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self.sig_hover_leave.emit(self.shortcut_id)
        super().leaveEvent(e)


class DockResizeHandle(QWidget):
    """Draggable strip on the dock inner edge for width/height resize."""

    def __init__(self, dock: DockWidget) -> None:
        super().__init__(dock)
        self._dock = dock
        self._dragging = False
        self._start_global = 0
        self._start_thick = 0
        self._changed = False
        self.setObjectName("dockResizeHandle")
        self.setStyleSheet(dock_resize_handle_stylesheet())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    def _axis_coord(self, pt: QPoint) -> int:
        if self._dock._pos == "top":
            return pt.y()
        return pt.x()

    def _signed_delta(self, delta: int) -> int:
        pos = self._dock._pos
        if pos == "right":
            return -delta
        return delta

    def _update_cursor(self) -> None:
        if self._dock._pos == "top":
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeHorCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_global = self._axis_coord(event.globalPosition().toPoint())
            self._start_thick = self._dock._thick
            self._changed = False
            self.grabMouse()
            self._dock._begin_resize_drag()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            coord = self._axis_coord(event.globalPosition().toPoint())
            delta = self._signed_delta(coord - self._start_global)
            prev = self._dock._thick
            self._dock.set_dock_width(self._start_thick + delta, persist=False)
            if self._dock._thick != prev:
                self._changed = True
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.releaseMouse()
            self._dock._end_resize_drag()
            if self._changed:
                self._dock.sig_dock_width_changed.emit(self._dock._thick)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class DockWidget(QWidget):
    sig_new_note = pyqtSignal()
    sig_show_all = pyqtSignal()
    sig_hide_all = pyqtSignal()
    sig_settings = pyqtSignal()
    sig_search = pyqtSignal()
    sig_exit = pyqtSignal()
    sig_card_click = pyqtSignal(str)
    sig_shortcut_click = pyqtSignal(str)
    sig_pin_file = pyqtSignal()
    sig_files_dropped = pyqtSignal(list)
    sig_remove_shortcut = pyqtSignal(str)
    sig_tag_filter = pyqtSignal(str)
    sig_dock_width_changed = pyqtSignal(int)

    DEFAULT_THICK = MIN_DOCK_WIDTH
    THICK = DEFAULT_THICK
    TILE = 44
    TRIGGER = 4
    RESIZE_HANDLE = 7
    ANIM_MS = 200
    HIDE_MS = 600
    POLL_FAST_MS = 50
    POLL_SLOW_MS = 400
    POLL_NEAR_MS = 120

    _SCROLL_CSS = dock_scroll_stylesheet()

    def __init__(
        self,
        position: str = "top",
        dark_mode: bool = False,
        screen_geo: QRect | None = None,
        screen=None,
        content_getter: Callable[[str], str] | None = None,
        dock_width: int = DEFAULT_THICK,
    ) -> None:
        super().__init__()
        self._pos = position
        self._dark = dark_mode
        self._screen = screen
        self._screen_geo = screen_geo or QRect(0, 0, 1920, 1080)
        self._content_getter = content_getter or (lambda _nid: "")
        self._thick = clamp_dock_width(dock_width)
        self._resize_dragging = False
        self._shown = False
        self._anim = None
        self._btn_widgets: list[QWidget] = []
        self._indicators: list[DockNoteIndicator] = []
        self._indicator_map: dict[str, DockNoteIndicator] = {}
        self._file_indicators: list[DockFileIndicator] = []
        self._file_indicator_map: dict[str, DockFileIndicator] = {}
        self._popup: DockNotePopup | None = None
        self._file_popup: DockFilePopup | None = None
        self._popup_timer = QTimer(self)
        self._popup_timer.setSingleShot(True)
        self._popup_timer.setInterval(300)
        self._popup_timer.timeout.connect(self._hide_popup)
        self._notes_data: dict[str, dict[str, Any]] = {}
        self._shortcuts_data: list[dict[str, Any]] = []
        self._settings_btn: QPushButton | None = None
        self._btn_layout: QHBoxLayout | QVBoxLayout | None = None
        self._drag_over = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._build_ui()
        self._resize_handle = DockResizeHandle(self)
        self._resize_handle._update_cursor()
        self._position_resize_handle()
        self._apply_style()
        self._poll = QTimer(self)
        self._poll_interval_ms = self.POLL_FAST_MS
        self._poll.setInterval(self._poll_interval_ms)
        self._last_poll_cursor: QPoint | None = None
        self._last_poll_shown = False
        self._poll.timeout.connect(self._poll_mouse)
        self._poll.start()
        self._hide_tmr = QTimer(self)
        self._hide_tmr.setSingleShot(True)
        self._hide_tmr.setInterval(self.HIDE_MS)
        self._hide_tmr.timeout.connect(self._slide_out)
        self._layout_tmr = QTimer(self)
        self._layout_tmr.setSingleShot(True)
        self._layout_tmr.setInterval(0)
        self._layout_tmr.timeout.connect(self._sync_indicator_layout)
        if self._screen is not None:
            self._screen.geometryChanged.connect(self._on_screen_changed)
            self._screen.availableGeometryChanged.connect(self._on_screen_changed)
        self._place_hidden()

    def _build_ui(self) -> None:
        horiz = self._pos == "top"
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(dock_scroll_stylesheet())
        if horiz:
            self.scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
        else:
            self.scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self.scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
        self.ind_container = QWidget()
        self.ind_container.setStyleSheet("background:transparent;")
        self.ind_layout = (
            QHBoxLayout(self.ind_container)
            if horiz
            else QVBoxLayout(self.ind_container)
        )
        self.ind_layout.setContentsMargins(0, 0, 0, 0)
        self.ind_layout.setSpacing(4)
        self.ind_layout.addStretch()
        self.scroll.setWidget(self.ind_container)
        outer.addWidget(self.scroll, 1)
        self._action_sep = _make_sep(horiz)
        outer.addWidget(self._action_sep)
        for w in (self.scroll, self.scroll.viewport(), self.ind_container):
            w.setAcceptDrops(True)
            w.installEventFilter(self)
        btn_groups = [
            [("pin_file", "Pin file\u2026", self.sig_pin_file)],
            [("plus", "New Note", self.sig_new_note)],
            [
                ("show_all", "Show All", self.sig_show_all),
                ("hide_all", "Hide All", self.sig_hide_all),
                ("search", "Search notes\u2026", self.sig_search),
            ],
        ]
        self._btn_widgets = []
        for group in btn_groups:
            for icon, label, sig in group:
                bw = _make_dock_btn(icon, label, sig)
                self._btn_widgets.append(bw)
        settings_bw = _make_dock_btn(
            "settings",
            "Settings",
            on_click=self._show_settings_menu,
        )
        self._btn_widgets.append(settings_bw)
        self._settings_btn = settings_bw.btn  # type: ignore[attr-defined]
        self._sync_action_button_layout()

    def _action_buttons_horizontal(self) -> bool:
        if self._pos == "top":
            return True
        return self._pos in ("left", "right") and self._thick > MIN_DOCK_WIDTH

    def _sync_action_button_layout(self) -> None:
        horiz = self._action_buttons_horizontal()
        if self._btn_layout is not None and horiz == isinstance(
            self._btn_layout, QHBoxLayout
        ):
            return

        outer = self.layout()
        assert outer is not None

        scroll_idx = outer.indexOf(self.scroll)
        outer.removeWidget(self._action_sep)
        self._action_sep.deleteLater()
        self._action_sep = _make_sep(horiz)
        outer.insertWidget(scroll_idx + 1, self._action_sep)

        if self._btn_layout is not None:
            for i in range(outer.count()):
                item = outer.itemAt(i)
                if item is not None and item.layout() == self._btn_layout:
                    outer.takeAt(i)
                    break
            while self._btn_layout.count():
                item = self._btn_layout.takeAt(0)
                widget = item.widget()
                if widget is not None and widget not in self._btn_widgets:
                    widget.deleteLater()
            self._btn_layout.deleteLater()

        self._btn_layout = QHBoxLayout() if horiz else QVBoxLayout()
        self._btn_layout.setContentsMargins(0, 0, 0, 0)
        self._btn_layout.setSpacing(2)
        if horiz:
            self._btn_layout.addStretch()

        groups = [
            [self._btn_widgets[0]],
            [self._btn_widgets[1]],
            self._btn_widgets[2:5],
            [self._btn_widgets[5]],
        ]
        for i, group in enumerate(groups):
            if i > 0:
                self._btn_layout.addWidget(_make_sep(horiz))
            for widget in group:
                self._btn_layout.addWidget(widget)
        outer.addLayout(self._btn_layout)

    def _position_resize_handle(self) -> None:
        h = self.RESIZE_HANDLE
        w, ht = self.width(), self.height()
        if self._pos == "left":
            self._resize_handle.setGeometry(w - h, 0, h, ht)
        elif self._pos == "right":
            self._resize_handle.setGeometry(0, 0, h, ht)
        else:
            self._resize_handle.setGeometry(0, ht - h, w, h)
        self._resize_handle.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_resize_handle()

    def _begin_resize_drag(self) -> None:
        self._hide_tmr.stop()
        self._poll.stop()
        self._resize_dragging = True
        if self._shown:
            self._clear_size_constraints()

    def _end_resize_drag(self) -> None:
        self._resize_dragging = False
        if self._shown:
            self._set_shown_size_constraints()
            self.setGeometry(self._shown_geo())
        elif self._collapse_on_hide():
            self._set_hidden_size_constraints()
            self.setGeometry(self._hidden_geo())
        else:
            self.setGeometry(self._hidden_geo())
        self._position_resize_handle()
        self._schedule_indicator_layout()
        self._poll.start()

    def set_dock_width(self, width: int, *, persist: bool = True) -> None:
        w = clamp_dock_width(width)
        if w == self._thick:
            return
        self._thick = w
        self._sync_action_button_layout()
        if self._resize_dragging:
            self.setGeometry(
                self._shown_geo() if self._shown else self._hidden_geo()
            )
        elif self._shown:
            self._set_shown_size_constraints()
            self.setGeometry(self._shown_geo())
        elif self._collapse_on_hide():
            self._set_hidden_size_constraints()
            self.setGeometry(self._hidden_geo())
        else:
            self.setGeometry(self._hidden_geo())
        if not self._resize_dragging:
            self._position_resize_handle()
        if persist:
            self.sig_dock_width_changed.emit(w)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            dock_stylesheet(dark=self._dark, drag_over=self._drag_over)
        )

    def _mime_has_pinnable_files(self, mime) -> bool:
        if not mime.hasUrls():
            return False
        for path in local_paths_from_mime_urls(mime.urls()):
            if is_dock_pinnable_file(path):
                return True
        return False

    def _paths_from_drop(self, mime) -> list[str]:
        if not mime.hasUrls():
            return []
        return [
            path
            for path in local_paths_from_mime_urls(mime.urls())
            if is_dock_pinnable_file(path)
        ]

    def _set_drag_over(self, active: bool) -> None:
        if self._drag_over == active:
            return
        self._drag_over = active
        self._apply_style()

    def eventFilter(self, obj, event) -> bool:
        t = event.type()
        if t == QEvent.Type.DragEnter:
            self.dragEnterEvent(event)
            return True
        if t == QEvent.Type.DragMove:
            self.dragMoveEvent(event)
            return True
        if t == QEvent.Type.Drop:
            self.dropEvent(event)
            return True
        if t == QEvent.Type.DragLeave:
            self._set_drag_over(False)
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._mime_has_pinnable_files(event.mimeData()):
            event.acceptProposedAction()
            self._set_drag_over(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._mime_has_pinnable_files(event.mimeData()):
            event.acceptProposedAction()
            self._set_drag_over(True)
        else:
            event.ignore()
            self._set_drag_over(False)

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_over(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_over(False)
        paths = self._paths_from_drop(event.mimeData())
        if paths:
            event.acceptProposedAction()
            self.sig_files_dropped.emit(paths)
        else:
            event.ignore()

    def set_dark_mode(self, d: bool) -> None:
        self._dark = d
        self._apply_style()

    def set_content_getter(self, getter: Callable[[str], str]) -> None:
        self._content_getter = getter

    def _build_settings_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(menu_stylesheet(dark=True))
        menu.addAction("Settings", lambda: self.sig_settings.emit())
        menu.addSeparator()
        menu.addAction("Exit", lambda: self.sig_exit.emit())
        menu.addSeparator()
        version_action = menu.addAction(f"Version {__version__}")
        version_action.setEnabled(False)
        build_action = menu.addAction(f"Built {build_date_display()}")
        build_action.setEnabled(False)
        return menu

    def _show_settings_menu(self) -> None:
        menu = self._build_settings_menu()
        btn = self._settings_btn
        if btn is not None:
            menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

    def refresh_cards(
        self,
        notes: dict[str, dict[str, Any]],
        shortcuts: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        active_tag: str = "",
    ) -> None:
        del tags, active_tag
        for ind in self._file_indicators:
            ind.setParent(None)
            ind.deleteLater()
        self._file_indicators.clear()
        self._file_indicator_map.clear()
        for ind in self._indicators:
            ind.setParent(None)
            ind.deleteLater()
        self._indicators.clear()
        self._indicator_map.clear()
        while self.ind_layout.count():
            self.ind_layout.takeAt(0)
        self._notes_data = dict(notes)
        self._shortcuts_data = list(shortcuts or [])
        sorted_shortcuts = sorted(
            self._shortcuts_data,
            key=lambda s: s.get("added_at", ""),
        )
        for sd in sorted_shortcuts:
            file_ind = DockFileIndicator(sd, self.ind_container)
            file_ind.sig_click.connect(self._on_file_click)
            file_ind.sig_hover_enter.connect(self._show_file_popup)
            file_ind.sig_hover_leave.connect(self._schedule_hide)
            file_ind.sig_remove.connect(self.sig_remove_shortcut.emit)
            self.ind_layout.addWidget(file_ind)
            self._file_indicators.append(file_ind)
            self._file_indicator_map[sd["id"]] = file_ind
        if sorted_shortcuts:
            self.ind_layout.addWidget(_make_sep(self._pos == "top"))
        dockable = [
            nd
            for nd in self._notes_data.values()
            if nd.get("content", "").strip() or nd.get("private")
        ]
        sorted_n = sorted(
            dockable,
            key=lambda n: n.get("modified_at", ""),
            reverse=True,
        )
        for nd in sorted_n:
            ind = DockNoteIndicator(nd, self._content_getter, self.ind_container)
            ind.sig_click.connect(self._on_note_click)
            ind.sig_hover_enter.connect(self._show_popup)
            ind.sig_hover_leave.connect(self._schedule_hide)
            self.ind_layout.addWidget(ind)
            self._indicators.append(ind)
            self._indicator_map[nd["id"]] = ind
        self.ind_layout.addStretch()
        self._schedule_indicator_layout()

    def update_note_card(self, nid: str, note_data: dict[str, Any]) -> None:
        has_content = bool(note_data.get("content", "").strip())
        if not has_content and not note_data.get("private"):
            self.remove_note_card(nid)
            return
        self._notes_data[nid] = note_data
        ind = self._indicator_map.get(nid)
        if ind:
            ind.update_note(note_data)
            if self._popup and self._popup.note_id == nid:
                self._popup.update_content(note_data)
        else:
            self._insert_note_indicator(nid, note_data)

    def _note_layout_index(self, indicator_index: int) -> int:
        idx = len(self._file_indicators)
        if self._file_indicators:
            idx += 1
        return idx + indicator_index

    def _ensure_trailing_stretch(self) -> None:
        if self.ind_layout.count() == 0:
            self.ind_layout.addStretch()
            return
        last = self.ind_layout.itemAt(self.ind_layout.count() - 1)
        if last is None or last.spacerItem() is None:
            self.ind_layout.addStretch()

    def _indicator_span_px(self) -> int:
        count = len(self._indicators) + len(self._file_indicators)
        if self._file_indicators:
            count += 1
        if count <= 0:
            return 0
        spacing = self.ind_layout.spacing()
        return count * self.TILE + max(0, count - 1) * spacing

    def _sync_indicator_layout(self) -> None:
        """Apply layout once the dock has room to lay out tiles."""
        self._ensure_trailing_stretch()
        self.ind_layout.invalidate()
        self.ind_layout.activate()
        span = self._indicator_span_px()
        if span > 0:
            if self._pos == "top":
                self.ind_container.setMinimumWidth(span)
            else:
                self.ind_container.setMinimumHeight(span)
        self.ind_container.adjustSize()
        cr = self.ind_container.contentsRect()
        if cr.width() > 0 and cr.height() > 0:
            self.ind_layout.setGeometry(cr)

    def _schedule_indicator_layout(self) -> None:
        self._layout_tmr.start()

    def _insert_note_indicator(self, nid: str, note_data: dict[str, Any]) -> None:
        ind = DockNoteIndicator(note_data, self._content_getter, self.ind_container)
        ind.sig_click.connect(self._on_note_click)
        ind.sig_hover_enter.connect(self._show_popup)
        ind.sig_hover_leave.connect(self._schedule_hide)
        mod = note_data.get("modified_at", "")
        insert_at = len(self._indicators)
        for i, existing in enumerate(self._indicators):
            em = self._notes_data.get(existing.note_id, {}).get("modified_at", "")
            if mod > em:
                insert_at = i
                break
        self._indicators.insert(insert_at, ind)
        self._indicator_map[nid] = ind
        self._ensure_trailing_stretch()
        layout_idx = self._note_layout_index(insert_at)
        self.ind_layout.insertWidget(layout_idx, ind)
        self._schedule_indicator_layout()

    def remove_note_card(self, nid: str) -> None:
        self._notes_data.pop(nid, None)
        ind = self._indicator_map.pop(nid, None)
        if ind:
            self.ind_layout.removeWidget(ind)
            ind.setParent(None)
            ind.deleteLater()
            self._indicators = [i for i in self._indicators if i.note_id != nid]
        if self._popup and self._popup.note_id == nid:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None

    def _show_file_popup(self, sid: str, gpos: QPoint) -> None:
        if (
            self._file_popup
            and self._file_popup.shortcut_id == sid
            and self._file_popup.isVisible()
        ):
            return
        self._popup_timer.stop()
        if self._file_popup:
            self._file_popup.close()
            self._file_popup.deleteLater()
            self._file_popup = None
        if self._popup:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None
        sd = next((s for s in self._shortcuts_data if s.get("id") == sid), None)
        if not sd:
            return
        self._file_popup = DockFilePopup(dict(sd))
        self._file_popup.clicked.connect(self._on_file_click)
        pw, ph = self._file_popup.width(), self._file_popup.height()
        g = self._screen_geo
        if self._pos == "left":
            x = g.left() + self._thick + 4
            y = gpos.y() - ph // 4
        elif self._pos == "right":
            x = g.right() - self._thick - pw - 4
            y = gpos.y() - ph // 4
        else:
            x = gpos.x() - pw // 4
            y = g.top() + self._thick + 4
        if x + pw > g.right():
            x = g.right() - pw
        if y + ph > g.bottom():
            y = g.bottom() - ph
        if x < g.left():
            x = g.left()
        if y < g.top():
            y = g.top()
        self._file_popup.move(x, y)
        self._file_popup.show()

    def _show_popup(self, nid: str, gpos: QPoint) -> None:
        if self._popup and self._popup.note_id == nid and self._popup.isVisible():
            return
        self._popup_timer.stop()
        if self._file_popup:
            self._file_popup.close()
            self._file_popup.deleteLater()
            self._file_popup = None
        if self._popup:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None
        nd = self._notes_data.get(nid)
        if not nd:
            return
        self._popup = DockNotePopup(dict(nd), self._content_getter)
        self._popup.clicked.connect(self._on_note_click)
        pw, ph = self._popup.width(), self._popup.height()
        g = self._screen_geo
        if self._pos == "left":
            x = g.left() + self._thick + 4
            y = gpos.y() - ph // 4
        elif self._pos == "right":
            x = g.right() - self._thick - pw - 4
            y = gpos.y() - ph // 4
        else:
            x = gpos.x() - pw // 4
            y = g.top() + self._thick + 4
        if x + pw > g.right():
            x = g.right() - pw
        if y + ph > g.bottom():
            y = g.bottom() - ph
        if x < g.left():
            x = g.left()
        if y < g.top():
            y = g.top()
        self._popup.move(x, y)
        self._popup.show()

    def _schedule_hide(self, _id: str) -> None:
        self._popup_timer.start()

    def _dismiss_popups(self) -> None:
        self._popup_timer.stop()
        if self._popup:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None
        if self._file_popup:
            self._file_popup.close()
            self._file_popup.deleteLater()
            self._file_popup = None

    def _on_file_click(self, sid: str) -> None:
        self._dismiss_popups()
        self.sig_shortcut_click.emit(sid)

    def _on_note_click(self, nid: str) -> None:
        self._dismiss_popups()
        self.sig_card_click.emit(nid)

    def _hide_popup(self) -> None:
        if self._popup:
            if self._popup.geometry().contains(QCursor.pos()):
                self._popup_timer.start()
                return
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None
        if self._file_popup:
            if self._file_popup.geometry().contains(QCursor.pos()):
                self._popup_timer.start()
                return
            self._file_popup.close()
            self._file_popup.deleteLater()
            self._file_popup = None

    def _set_hidden_size_constraints(self) -> None:
        if self._pos == "left":
            self.setFixedWidth(self.TRIGGER)
        elif self._pos == "top":
            self.setFixedHeight(self.TRIGGER)
        elif self._pos == "right":
            self.setFixedWidth(self.TRIGGER)

    def _clear_size_constraints(self) -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

    def _set_shown_size_constraints(self) -> None:
        if self._pos == "left":
            self.setFixedWidth(self._thick)
        elif self._pos == "top":
            self.setFixedHeight(self._thick)
        else:
            self.setFixedWidth(self._thick)

    def _collapse_on_hide(self) -> bool:
        if sys.platform == "win32":
            return self._pos in ("left", "top", "right")
        return self._pos in ("left", "top")

    def _shown_geo(self) -> QRect:
        g = self._screen_geo
        t = self._thick
        if self._pos == "top":
            return QRect(g.left(), g.top(), g.width(), t)
        if self._pos == "left":
            return QRect(g.left(), g.top(), t, g.height())
        return QRect(g.right() - t, g.top(), t, g.height())

    def _hidden_geo(self) -> QRect:
        g = self._screen_geo
        t = self._thick
        z = self.TRIGGER
        if self._pos == "top":
            return QRect(g.left(), g.top(), g.width(), z)
        if self._pos == "left":
            return QRect(g.left(), g.top(), z, g.height())
        if self._collapse_on_hide():
            return QRect(g.right() - z, g.top(), z, g.height())
        return QRect(g.right(), g.top(), t, g.height())

    def _place_hidden(self) -> None:
        if self._collapse_on_hide():
            self._set_hidden_size_constraints()
        self.setGeometry(self._hidden_geo())
        self.show()
        if self._collapse_on_hide():
            self.setGeometry(self._hidden_geo())
        self._shown = False

    def _vis_pos(self) -> QPoint:
        return self._shown_geo().topLeft()

    def _hid_pos(self) -> QPoint:
        return self._hidden_geo().topLeft()

    def _on_screen_changed(self, *_args) -> None:
        if self._screen is not None:
            self._screen_geo = self._screen.availableGeometry()
        if self._shown:
            self._set_shown_size_constraints()
            self.setGeometry(self._shown_geo())
        else:
            self._place_hidden()

    def _on_slide_in_finished(self) -> None:
        self._set_shown_size_constraints()
        self._sync_indicator_layout()

    def _slide_in(self) -> None:
        if self._shown:
            return
        self._shown = True
        self._hide_tmr.stop()
        self.show()
        self.raise_()
        if self._collapse_on_hide():
            self._clear_size_constraints()
            anim = self._anim_geom(self._hidden_geo(), self._shown_geo())
            anim.finished.connect(self._on_slide_in_finished)
        else:
            self.setGeometry(self._hidden_geo())
            self._anim_to(self._vis_pos())

    def _slide_out(self) -> None:
        if not self._shown:
            return
        if self.geometry().contains(QCursor.pos()):
            self._hide_tmr.start()
            return
        if (
            self._popup
            and self._popup.isVisible()
            and self._popup.geometry().contains(QCursor.pos())
        ):
            self._hide_tmr.start()
            return
        if (
            self._file_popup
            and self._file_popup.isVisible()
            and self._file_popup.geometry().contains(QCursor.pos())
        ):
            self._hide_tmr.start()
            return
        self._shown = False
        self._dismiss_popups()
        if self._collapse_on_hide():
            anim = self._anim_geom(self._shown_geo(), self._hidden_geo())
            anim.finished.connect(self._set_hidden_size_constraints)
        else:
            self._anim_to(self._hid_pos())

    def _anim_to(self, tgt: QPoint) -> None:
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(self.ANIM_MS)
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(tgt)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _anim_geom(self, start: QRect, end: QRect) -> QPropertyAnimation:
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(self.ANIM_MS)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        return self._anim

    def _cursor_near_trigger(self, c: QPoint) -> bool:
        g = self._screen_geo
        margin = 48
        if self._pos == "top":
            return (
                g.top() - margin <= c.y() <= g.top() + margin
                and g.left() <= c.x() <= g.right()
            )
        if self._pos == "left":
            return (
                g.left() - margin <= c.x() <= g.left() + margin
                and g.top() <= c.y() <= g.bottom()
            )
        return (
            g.right() - margin <= c.x() <= g.right() + margin
            and g.top() <= c.y() <= g.bottom()
        )

    def _ensure_poll_interval(self, ms: int) -> None:
        if self._poll_interval_ms != ms:
            self._poll_interval_ms = ms
            self._poll.setInterval(ms)

    def _poll_mouse(self) -> None:
        if self._resize_dragging:
            return
        c = QCursor.pos()
        if (
            self._last_poll_cursor is not None
            and self._last_poll_cursor == c
            and self._last_poll_shown == self._shown
        ):
            return
        g = self._screen_geo
        z = self.TRIGGER
        hit = False
        if self._pos == "top":
            hit = c.y() <= g.top() + z and g.left() <= c.x() <= g.right()
        elif self._pos == "left":
            hit = c.x() <= g.left() + z and g.top() <= c.y() <= g.bottom()
        else:
            hit = c.x() >= g.right() - z and g.top() <= c.y() <= g.bottom()
        if hit and not self._shown:
            self._slide_in()
        elif self._shown and not self.geometry().contains(c):
            popup_hover = (
                self._popup
                and self._popup.isVisible()
                and self._popup.geometry().contains(c)
            ) or (
                self._file_popup
                and self._file_popup.isVisible()
                and self._file_popup.geometry().contains(c)
            )
            if (
                not popup_hover
                and not self._hide_tmr.isActive()
                and not self._resize_dragging
            ):
                self._hide_tmr.start()
        active = hit or self._shown
        if active:
            self._ensure_poll_interval(self.POLL_FAST_MS)
        elif self._cursor_near_trigger(c):
            self._ensure_poll_interval(self.POLL_NEAR_MS)
        else:
            self._ensure_poll_interval(self.POLL_SLOW_MS)
        self._last_poll_cursor = QPoint(c)
        self._last_poll_shown = self._shown

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if sys.platform == "darwin":
            from stickynotes.platform.macos.windows import schedule_configure_floating_window

            schedule_configure_floating_window(self, on_top=True)

    def destroy_dock(self) -> None:
        if self._screen is not None:
            try:
                self._screen.geometryChanged.disconnect(self._on_screen_changed)
                self._screen.availableGeometryChanged.disconnect(
                    self._on_screen_changed
                )
            except TypeError:
                pass
        self._poll.stop()
        self._hide_tmr.stop()
        self._layout_tmr.stop()
        self._dismiss_popups()
        self.close()
