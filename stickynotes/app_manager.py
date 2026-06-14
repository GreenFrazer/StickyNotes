"""Coordinates notes, docks, tray, settings, and hotkeys."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from stickynotes.models import (
    auto_size,
    dock_pin_dialog_filters,
    is_dock_pinnable_file,
    is_private,
    normalize_tags,
    note_title,
    private_preview_text,
)
from stickynotes.platform import get_hotkey_service, get_paths
from stickynotes.reminders import ReminderService
from stickynotes.storage import StorageManager
from stickynotes.theme import DEFAULT_NOTE_H, DEFAULT_NOTE_W, dialog_stylesheet
from stickynotes.ui.dock import DockWidget
from stickynotes.ui.note_window import NoteWindow
from stickynotes.ui.search_dialog import SearchDialog
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
        self._active_tag_filter = ""
        self._search_dialog: SearchDialog | None = None

        self.tray = QSystemTrayIcon(self._ico(), self.app)
        tm = QMenu()
        tm.addAction("\u2795  New Note").triggered.connect(self.create_note)
        self._tray_new_in_tag = tm.addMenu("\U0001F3F7  New note in tag\u2026")
        self._rebuild_tray_tag_menu()
        tm.addAction("\U0001F4CE  Pin file to dock\u2026").triggered.connect(self.pin_file)
        tm.addAction("\U0001F4E4  Export all notes\u2026").triggered.connect(self.export_notes)
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

        self._reminders = ReminderService(self._notes_for_reminders, self.app)
        self._reminders.reminder_due.connect(self._on_reminder_due)
        self._reminders.start()

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
            return n.get_content()
        nd = self.storage.get_all_notes().get(nid)
        return nd.get("content", "") if nd else ""

    def _notes_for_reminders(self) -> dict:
        result = {}
        for nid, nd in self.storage.get_all_notes().items():
            live = dict(nd)
            n = self.notes.get(nid)
            if n:
                live["reminder_at"] = n.note_data.get("reminder_at")
            result[nid] = live
        return result

    def _all_known_tags(self) -> list[str]:
        tags: set[str] = set()
        for nd in self.storage.get_all_notes().values():
            tags.update(nd.get("tags", []))
        default = self.storage.get_settings().get("default_tag", "")
        if default:
            tags.add(default)
        return sorted(tags)

    def _rebuild_tray_tag_menu(self) -> None:
        self._tray_new_in_tag.clear()
        tags = self._all_known_tags()
        if not tags:
            action = self._tray_new_in_tag.addAction("(No tags yet)")
            action.setEnabled(False)
            return
        for tag in tags:
            self._tray_new_in_tag.addAction(tag).triggered.connect(
                lambda _checked=False, t=tag: self.create_note(tag=t)
            )

    def open_search(self) -> None:
        notes = self.storage.get_all_stored_notes()
        if self._search_dialog is None:
            self._search_dialog = SearchDialog(
                notes,
                self.get_live_content,
                dark_mode=self._dark,
            )
            self._search_dialog.note_selected.connect(self._search_note_selected)
        else:
            self._search_dialog.update_notes(notes)
            self._search_dialog.setStyleSheet(dialog_stylesheet(dark=self._dark))
        self._search_dialog.show_and_focus()

    def _search_note_selected(self, nid: str) -> None:
        n = self.notes.get(nid)
        if n:
            n.show_note()
            n.raise_()
            n.activateWindow()

    def export_notes(self) -> None:
        path, selected_filter = QFileDialog.getSaveFileName(
            None,
            "Export notes",
            "stickynotes-export.stickynotes",
            "Sticky Notes archive (*.stickynotes);;JSON (*.json)",
        )
        if not path:
            return
        dest = Path(path)
        if selected_filter.startswith("JSON") and dest.suffix.lower() != ".json":
            dest = dest.with_suffix(".json")
        elif selected_filter.startswith("Sticky") and dest.suffix.lower() != ".stickynotes":
            dest = dest.with_suffix(".stickynotes")
        try:
            self.storage.export_archive(dest)
            QMessageBox.information(
                None,
                "Export complete",
                f"Exported {len(self.storage.get_all_notes())} notes to:\n{dest}",
            )
        except OSError as exc:
            QMessageBox.warning(None, "Export failed", str(exc))

    def _import_notes_dialog(self, *, from_settings: bool = False) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Import notes",
            "",
            "Sticky Notes (*.stickynotes *.json);;All files (*)",
        )
        if not path:
            return
        src = Path(path)
        try:
            preview = self.storage.preview_import(src)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(None, "Import failed", f"Could not read file:\n{exc}")
            return

        msg = (
            f"Incoming notes: {preview['incoming_count']}\n"
            f"Existing notes: {preview['existing_count']}\n"
            f"Overlapping IDs: {preview['overlap_count']}\n"
            f"Likely conflicts: {preview['conflict_count']}\n\n"
            "Merge keeps your newer notes on conflict. Replace overwrites all data."
        )
        merge_btn = QMessageBox.StandardButton.Yes
        replace_btn = QMessageBox.StandardButton.No
        cancel_btn = QMessageBox.StandardButton.Cancel
        reply = QMessageBox.question(
            None,
            "Import notes",
            msg,
            merge_btn | replace_btn | cancel_btn,
            merge_btn,
        )
        if reply == cancel_btn:
            return
        merge = reply == merge_btn
        try:
            stats = self.storage.import_data(src, merge=merge)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(None, "Import failed", str(exc))
            return
        self.reload_notes_from_storage()
        if stats.get("mode") == "merge":
            detail = (
                f"Added: {stats.get('added', 0)}, "
                f"updated: {stats.get('merged', 0)}, "
                f"kept: {stats.get('kept', 0)}"
            )
        else:
            detail = f"Loaded {stats.get('note_count', 0)} notes"
        QMessageBox.information(None, "Import complete", detail)
        if from_settings:
            self.open_settings()

    def _restore_backup_dialog(self) -> None:
        backups = self.storage.list_backups()
        if not backups:
            QMessageBox.information(
                None,
                "Restore backup",
                "No backup file found (data.json.bak).",
            )
            return
        bk = backups[0]
        reply = QMessageBox.question(
            None,
            "Restore backup",
            f"Restore from backup dated {bk['modified_at']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.storage.restore_from_backup():
            self.reload_notes_from_storage()
            QMessageBox.information(None, "Restore complete", "Notes restored from backup.")
        else:
            QMessageBox.warning(None, "Restore failed", "Could not restore backup.")

    def _open_data_folder(self) -> None:
        folder = get_paths().data_dir
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def reload_notes_from_storage(self) -> None:
        for n in list(self.notes.values()):
            n.close()
        self.notes.clear()
        self._notes_with_content.clear()
        self._reminders.clear_fired()
        saved = self.storage.get_all_notes()
        if saved:
            for nd in saved.values():
                self._spawn(nd)
                if nd.get("content", "").strip():
                    self._notes_with_content.add(nd["id"])
        else:
            self.create_note()
        self._rebuild_tray_tag_menu()
        self._create_docks()
        self._tt()

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
                dock.sig_tag_filter,
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
            dock.sig_tag_filter.connect(self._set_tag_filter)
            self.docks.append(dock)
        self._refresh_all_docks()

    def _set_tag_filter(self, tag: str) -> None:
        self._active_tag_filter = tag.strip().lower()
        self._refresh_all_docks()

    def _notes_for_dock(self) -> dict:
        notes = self.storage.get_all_notes()
        if self._active_tag_filter:
            notes = {
                nid: nd
                for nid, nd in notes.items()
                if self._active_tag_filter in nd.get("tags", [])
            }
        return notes

    def _refresh_all_docks(self) -> None:
        notes = self._notes_for_dock()
        shortcuts = self.storage.get_dock_shortcuts()
        tags = self._all_known_tags()
        self._pending_note_updates.clear()
        for dock in self.docks:
            enriched = {}
            for nid, nd in notes.items():
                live = dict(nd)
                live["content"] = self.get_display_content(nid)
                enriched[nid] = live
            dock.refresh_cards(enriched, shortcuts, tags, self._active_tag_filter)

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
        has = bool(n.get_content().strip())
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

    def create_note(self, *, tag: str | None = None) -> None:
        nd = StorageManager.default_note()
        cx, cy = self._centre()
        off = (len(self.notes) % 8) * 20
        nd["x"] = cx + off
        nd["y"] = cy + off
        w, h = auto_size("")
        nd["width"] = w
        nd["height"] = h
        chosen = (tag or self.storage.get_settings().get("default_tag", "")).strip().lower()
        if chosen:
            nd["tags"] = [chosen]
        self._spawn(nd)
        self._track_note_content(nd["id"])
        self._tt()
        self._rebuild_tray_tag_menu()
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
        nd["tags"] = list(src.note_data.get("tags", []))
        nd["checklist"] = src.note_data.get("checklist", False)
        nd["reminder_at"] = src.note_data.get("reminder_at")
        nd["x"] = src.x() + 30
        nd["y"] = src.y() + 30
        w, h = auto_size(content)
        nd["width"] = w
        nd["height"] = h
        nd["user_resized"] = False
        nd["grip_resized"] = False
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
        self._rebuild_tray_tag_menu()
        self._schedule_dock_refresh(nid)

    def _on_reminder_due(self, nid: str, nd: dict) -> None:
        title = note_title(nd.get("content", "")) or "Sticky Note"
        self.tray.showMessage(
            "Reminder",
            title,
            QSystemTrayIcon.MessageIcon.Information,
            10_000,
        )
        reply = QMessageBox(self.app.activeWindow())
        reply.setWindowTitle("Reminder")
        reply.setText(note_title(nd.get("content", "")) or "Sticky Note")
        reply.setInformativeText("What would you like to do?")
        show_btn = reply.addButton("Show note", QMessageBox.ButtonRole.AcceptRole)
        snooze_btn = reply.addButton("Snooze 1h", QMessageBox.ButtonRole.ActionRole)
        dismiss_btn = reply.addButton("Dismiss", QMessageBox.ButtonRole.RejectRole)
        reply.setDefaultButton(show_btn)
        reply.exec()
        clicked = reply.clickedButton()
        if clicked == show_btn:
            self._show_note_and_clear_reminder(nid)
        elif clicked == snooze_btn:
            self._snooze_reminder(nid, hours=1)
        else:
            self._clear_reminder(nid)

    def _show_note_and_clear_reminder(self, nid: str) -> None:
        n = self.notes.get(nid)
        if n:
            n.show_note()
        self._clear_reminder(nid)

    def _snooze_reminder(self, nid: str, *, hours: int = 1) -> None:
        n = self.notes.get(nid)
        if not n:
            return
        due = datetime.now() + timedelta(hours=hours)
        n.set_reminder(due.isoformat(timespec="seconds"))
        self._reminders.clear_fired(nid)

    def _clear_reminder(self, nid: str) -> None:
        n = self.notes.get(nid)
        if n:
            n.set_reminder(None)
        self._reminders.clear_fired(nid)
        self._schedule_dock_refresh(nid)

    def open_settings(self) -> None:
        dlg = SettingsDialog(
            self.storage.get_settings(),
            on_export=self.export_notes,
            on_import=lambda: self._import_notes_dialog(from_settings=True),
            on_restore=self._restore_backup_dialog,
            on_open_data_folder=self._open_data_folder,
            known_tags=self._all_known_tags(),
        )
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
            self._reminders.stop()
            self._hotkeys.stop()
            self.tray.hide()
            self.app.quit()

    def _tray_act(self, r) -> None:
        if r == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_all_notes()
