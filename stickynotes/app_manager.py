"""Coordinates notes, docks, tray, settings, and hotkeys."""

from __future__ import annotations

import os

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from stickynotes.models import (
    auto_size,
    dock_pin_dialog_filters,
    is_dock_pinnable_file,
    is_private,
    private_preview_text,
)
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
        self._notes_with_content: set[str] = set()

        self.tray = QSystemTrayIcon(self._ico(), self.app)
        tm = QMenu()
        tm.addAction("\u2795  New Note").triggered.connect(self.create_note)
        tm.addAction("\U0001F4CE  Pin file to dock\u2026").triggered.connect(self.pin_file)
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
                if nd.get("content", "").strip():
                    self._notes_with_content.add(nd["id"])
        else:
            self.create_note()
        self._refresh_all_docks()

    def get_live_content(self, nid: str) -> str:
        n = self.notes.get(nid)
        if n:
            return n.editor.toPlainText()
        nd = self.storage.get_all_notes().get(nid)
        return nd.get("content", "") if nd else ""

    def get_display_content(self, nid: str) -> str:
        n = self.notes.get(nid)
        if n and is_private(n.note_data) and not n._revealed:
            return private_preview_text()
        return self.get_live_content(nid)

    def _create_docks(self) -> None:
        for dock in self.docks:
            for sig in (
                dock.sig_new_note,
                dock.sig_show_all,
                dock.sig_hide_all,
                dock.sig_settings,
                dock.sig_exit,
                dock.sig_card_click,
                dock.sig_shortcut_click,
                dock.sig_pin_file,
                dock.sig_files_dropped,
                dock.sig_remove_shortcut,
            ):
                try:
                    sig.disconnect()
                except TypeError:
                    pass
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
            dock.sig_shortcut_click.connect(self._shortcut_clicked)
            dock.sig_pin_file.connect(self.pin_file)
            dock.sig_files_dropped.connect(self.pin_dropped_files)
            dock.sig_remove_shortcut.connect(self.remove_shortcut)
            self.docks.append(dock)
        self._refresh_all_docks()

    def _refresh_all_docks(self) -> None:
        notes = self.storage.get_all_notes()
        shortcuts = self.storage.get_dock_shortcuts()
        self._pending_note_updates.clear()
        for dock in self.docks:
            enriched = {}
            for nid, nd in notes.items():
                live = dict(nd)
                live["content"] = self.get_display_content(nid)
                enriched[nid] = live
            dock.refresh_cards(enriched, shortcuts)

    def _schedule_dock_refresh(self, nid: str | None = None) -> None:
        if nid:
            self._pending_note_updates.add(nid)
        self._dock_refresh_timer.start()

    @staticmethod
    def _ico() -> QIcon:
        from pathlib import Path

        from stickynotes.ui.icons import app_icon

        root = Path(__file__).resolve().parent.parent
        for candidate in (
            root / "packaging" / "macos" / "StickyNotes.icns",
            root / "packaging" / "windows" / "StickyNotes.ico",
            root / "packaging" / "StickyNotes.png",
        ):
            if candidate.is_file():
                return QIcon(str(candidate))
        return app_icon()

    def _tt(self) -> None:
        c = len(self._notes_with_content)
        self.tray.setToolTip(f"Sticky Notes ({c} note{'s' if c != 1 else ''})")

    def _track_note_content(self, nid: str) -> None:
        n = self.notes.get(nid)
        if not n:
            return
        has = bool(n.editor.toPlainText().strip())
        if has:
            self._notes_with_content.add(nid)
        else:
            self._notes_with_content.discard(nid)

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
        self._track_note_content(nd["id"])
        self._tt()
        self._refresh_all_docks()

    def _spawn(self, nd: dict) -> None:
        n = NoteWindow(nd, self.storage, dark_mode=self._dark)
        n.request_new_note.connect(self.create_note)
        n.request_delete.connect(self.delete_note)
        n.request_duplicate.connect(self.duplicate_note)
        n.note_data_changed.connect(self._on_changed)
        self.notes[nd["id"]] = n

    def delete_note(self, nid: str) -> None:
        n = self.notes.pop(nid, None)
        if n:
            n.close()
        self._notes_with_content.discard(nid)
        self.storage.delete_note(nid)
        self._tt()
        for dock in self.docks:
            dock.remove_note_card(nid)

    def duplicate_note(self, nid: str) -> None:
        src = self.notes.get(nid)
        if not src:
            return
        nd = StorageManager.default_note()
        content = self.get_live_content(nid)
        nd["content"] = content
        nd["colour"] = src.note_data.get("colour", "yellow")
        nd["private"] = src.note_data.get("private", False)
        nd["x"] = src.x() + 30
        nd["y"] = src.y() + 30
        w, h = auto_size(content)
        nd["width"] = w
        nd["height"] = h
        nd["user_resized"] = False
        self._spawn(nd)
        self.notes[nd["id"]]._persist()
        self._track_note_content(nd["id"])
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

    @staticmethod
    def filter_new_dock_paths(
        paths: list[str], existing_shortcuts: list[dict]
    ) -> list[str]:
        """Return absolute paths to pin, skipping missing files and duplicates."""
        seen = {
            os.path.normcase(os.path.abspath(str(s.get("path", ""))))
            for s in existing_shortcuts
            if s.get("path")
        }
        added: list[str] = []
        for path in paths:
            if not is_dock_pinnable_file(path):
                continue
            resolved = os.path.abspath(path)
            key = os.path.normcase(resolved)
            if key in seen:
                continue
            seen.add(key)
            added.append(resolved)
        return added

    def _pin_paths(self, paths: list[str]) -> None:
        new_paths = self.filter_new_dock_paths(
            paths, self.storage.get_dock_shortcuts()
        )
        for path in new_paths:
            self.storage.add_dock_shortcut(path)
        if new_paths:
            self._refresh_all_docks()

    def pin_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Pin file to dock",
            "",
            dock_pin_dialog_filters(),
        )
        if not path:
            return
        resolved = os.path.abspath(path)
        if not os.path.isfile(resolved):
            QMessageBox.warning(
                None,
                "Pin file",
                "The selected file could not be found.",
            )
            return
        self._pin_paths([resolved])

    def pin_dropped_files(self, paths: list[str]) -> None:
        self._pin_paths(paths)

    def _shortcut_clicked(self, shortcut_id: str) -> None:
        shortcuts = self.storage.get_dock_shortcuts()
        shortcut = next((s for s in shortcuts if s.get("id") == shortcut_id), None)
        if not shortcut:
            return
        path = shortcut.get("path", "")
        if not path or not os.path.isfile(path):
            label = shortcut.get("label", "File")
            reply = QMessageBox.warning(
                None,
                "File missing",
                f'"{label}" could not be found at:\n{path}\n\n'
                "Remove this shortcut from the dock?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.remove_shortcut(shortcut_id)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def remove_shortcut(self, shortcut_id: str) -> None:
        self.storage.remove_dock_shortcut(shortcut_id)
        self._refresh_all_docks()

    def _on_changed(self, nid: str) -> None:
        self._track_note_content(nid)
        self._tt()
        self._schedule_dock_refresh(nid)

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.storage.get_settings())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ns = dlg.settings
            self.storage.set_settings(ns)
            self._dock_pos = ns["dock_position"]
            dark = ns.get("dark_mode", False)
            if dark != self._dark:
                self._dark = dark
                for n in self.notes.values():
                    n.set_dark_mode(dark)
            else:
                self._dark = dark
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
