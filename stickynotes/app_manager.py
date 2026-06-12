"""Coordinates notes, docks, tray, settings, and hotkeys."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QMessageBox, QSystemTrayIcon

from stickynotes.models import auto_size
from stickynotes.platform import get_hotkey_service
from stickynotes.storage import StorageManager
from stickynotes.theme import DEFAULT_NOTE_H, DEFAULT_NOTE_W
from stickynotes.ui.dock import DockWidget
from stickynotes.ui.note_window import NoteWindow
from stickynotes.ui.settings_dialog import SettingsDialog


class AppManager:
    DOCK_REFRESH_MS = 1000

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.storage = StorageManager()
        self.notes: dict[str, NoteWindow] = {}
        self.docks: list[DockWidget] = []
        s = self.storage.get_settings()
        self._dock_pos = s.get("dock_position", "top")
        self._dark = s.get("dark_mode", False)

        self._dock_refresh_timer = QTimer()
        self._dock_refresh_timer.setSingleShot(True)
        self._dock_refresh_timer.setInterval(self.DOCK_REFRESH_MS)
        self._dock_refresh_timer.timeout.connect(self._refresh_all_docks)
        self._pending_note_updates: set[str] = set()

        self.tray = QSystemTrayIcon(self._ico(), self.app)
        tm = QMenu()
        tm.addAction("\u2795  New Note").triggered.connect(self.create_note)
        tm.addAction("\U0001F4CB  Show All").triggered.connect(self.show_all_notes)
        tm.addAction("\U0001F648  Hide All").triggered.connect(self.hide_all_notes)
        tm.addSeparator()
        tm.addAction("\u2699  Settings").triggered.connect(self.open_settings)
        tm.addSeparator()
        tm.addAction("\u274C  Exit").triggered.connect(self.exit_app)
        self.tray.setContextMenu(tm)
        self.tray.activated.connect(self._tray_act)
        self.tray.show()
        self._tt()

        self._hotkeys = get_hotkey_service(self)
        self._hotkeys.start()

        self._create_docks()
        qapp = QGuiApplication.instance()
        if qapp:
            qapp.screenAdded.connect(lambda _s: self._create_docks())
            qapp.screenRemoved.connect(lambda _s: self._create_docks())

        saved = self.storage.get_all_notes()
        if saved:
            for nd in saved.values():
                self._spawn(nd)
        else:
            self.create_note()
        self._refresh_all_docks()

    def get_live_content(self, nid: str) -> str:
        n = self.notes.get(nid)
        if n:
            return n.editor.toPlainText()
        nd = self.storage.get_all_notes().get(nid)
        return nd.get("content", "") if nd else ""

    def _create_docks(self) -> None:
        for dock in self.docks:
            dock.destroy_dock()
            dock.deleteLater()
        self.docks.clear()
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        getter = self.get_live_content

        for scr in screens:
            geo = scr.availableGeometry()
            if self._dock_pos == "top":
                pos = "top"
            else:
                pos = "right" if scr == primary else "left"

            dock = DockWidget(
                position=pos,
                dark_mode=self._dark,
                screen_geo=geo,
                screen=scr,
                content_getter=getter,
            )
            dock.sig_new_note.connect(self.create_note)
            dock.sig_show_all.connect(self.show_all_notes)
            dock.sig_hide_all.connect(self.hide_all_notes)
            dock.sig_settings.connect(self.open_settings)
            dock.sig_exit.connect(self.exit_app)
            dock.sig_card_click.connect(self._card_clicked)
            self.docks.append(dock)
        self._refresh_all_docks()

    def _refresh_all_docks(self) -> None:
        notes = self.storage.get_all_notes()
        for nid in list(self._pending_note_updates):
            nd = notes.get(nid)
            for dock in self.docks:
                if nd:
                    live = dict(nd)
                    live["content"] = self.get_live_content(nid)
                    dock.update_note_card(nid, live)
                else:
                    dock.remove_note_card(nid)
        self._pending_note_updates.clear()
        for dock in self.docks:
            enriched = {}
            for nid, nd in notes.items():
                live = dict(nd)
                live["content"] = self.get_live_content(nid)
                enriched[nid] = live
            dock.refresh_cards(enriched)

    def _schedule_dock_refresh(self, nid: str | None = None) -> None:
        if nid:
            self._pending_note_updates.add(nid)
            note = self.notes.get(nid)
            if note:
                nd = dict(self.storage.get_all_notes().get(nid, note.note_data))
                nd["content"] = note.editor.toPlainText()
                for dock in self.docks:
                    dock.update_note_card(nid, nd)
        self._dock_refresh_timer.start()

    @staticmethod
    def _ico() -> QIcon:
        px = QPixmap(64, 64)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#FDFD96")))
        p.setPen(QPen(QColor("#D0D050"), 2))
        p.drawRoundedRect(4, 4, 56, 56, 8, 8)
        p.setPen(QPen(QColor("#999"), 2))
        for y in (20, 32, 44):
            p.drawLine(14, y, 50, y)
        p.end()
        return QIcon(px)

    def _tt(self) -> None:
        c = len([n for n in self.notes.values() if n.editor.toPlainText().strip()])
        self.tray.setToolTip(f"Sticky Notes ({c} note{'s' if c != 1 else ''})")

    def _centre(self) -> tuple[int, int]:
        scr = QGuiApplication.primaryScreen()
        if scr:
            g = scr.availableGeometry()
            return (
                g.center().x() - DEFAULT_NOTE_W // 2,
                g.center().y() - DEFAULT_NOTE_H // 2,
            )
        return 400, 300

    def create_note(self) -> None:
        nd = StorageManager.default_note()
        cx, cy = self._centre()
        off = (len(self.notes) % 8) * 20
        nd["x"] = cx + off
        nd["y"] = cy + off
        w, h = auto_size("")
        nd["width"] = w
        nd["height"] = h
        self._spawn(nd)
        self._tt()
        self._refresh_all_docks()

    def _spawn(self, nd: dict) -> None:
        n = NoteWindow(nd, self.storage)
        n.request_new_note.connect(self.create_note)
        n.request_delete.connect(self.delete_note)
        n.request_duplicate.connect(self.duplicate_note)
        n.note_data_changed.connect(self._on_changed)
        self.notes[nd["id"]] = n

    def delete_note(self, nid: str) -> None:
        n = self.notes.pop(nid, None)
        if n:
            n.close()
        self.storage.delete_note(nid)
        self._tt()
        for dock in self.docks:
            dock.remove_note_card(nid)

    def duplicate_note(self, nid: str) -> None:
        src = self.notes.get(nid)
        if not src:
            return
        nd = StorageManager.default_note()
        content = src.editor.toPlainText()
        nd["content"] = content
        nd["colour"] = src.note_data.get("colour", "yellow")
        nd["x"] = src.x() + 30
        nd["y"] = src.y() + 30
        w, h = auto_size(content)
        nd["width"] = w
        nd["height"] = h
        nd["user_resized"] = False
        self._spawn(nd)
        self.notes[nd["id"]]._persist()
        self._tt()
        self._refresh_all_docks()

    def show_all_notes(self) -> None:
        for n in self.notes.values():
            n.show_note()

    def hide_all_notes(self) -> None:
        for n in list(self.notes.values()):
            n._hide_note()
        self._tt()
        self._refresh_all_docks()

    def _card_clicked(self, nid: str) -> None:
        n = self.notes.get(nid)
        if n:
            n.show_note()

    def _on_changed(self, nid: str) -> None:
        self._tt()
        self._schedule_dock_refresh(nid)

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.storage.get_settings())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ns = dlg.settings
            self.storage.set_settings(ns)
            self._dock_pos = ns["dock_position"]
            self._dark = ns.get("dark_mode", False)
            self._create_docks()

    def exit_app(self) -> None:
        if (
            QMessageBox.question(
                None,
                "Exit",
                "Exit? Notes are saved automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            for n in self.notes.values():
                n._persist()
            self._hotkeys.stop()
            self.tray.hide()
            self.app.quit()

    def _tray_act(self, r) -> None:
        if r == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_all_notes()
