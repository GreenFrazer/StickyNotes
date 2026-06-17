"""Application settings dialog."""

from __future__ import annotations

import sys
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from stickynotes import __version__
from stickynotes.models import MAX_DOCK_WIDTH, MIN_DOCK_WIDTH
from stickynotes.theme import dialog_stylesheet

_CONTENT_WIDTH = 500


def _version_footer() -> str:
    return f"<small>Sticky Notes v{__version__} \u2013 PyQt6</small>"


class SettingsDialog(QDialog):
    def __init__(
        self,
        cur: dict[str, Any],
        parent=None,
        *,
        on_export: Callable[[], None] | None = None,
        on_import: Callable[[], None] | None = None,
        on_restore: Callable[[], None] | None = None,
        on_open_data_folder: Callable[[], None] | None = None,
        known_tags: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sticky Notes \u2013 Settings")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.settings = dict(cur)
        self._on_export = on_export
        self._on_import = on_import
        self._on_restore = on_restore
        self._on_open_data_folder = on_open_data_folder
        self._known_tags = known_tags or []
        self._build()
        self._style()

    def _shortcut_text(self) -> str:
        if sys.platform == "darwin":
            return (
                "\u2328  Shortcuts (global, requires Accessibility on macOS):<br>"
                "<b>Cmd+Shift+N</b> or <b>Ctrl+Shift+N</b> \u2013 New note<br>"
                "<b>Cmd+Shift+H</b> or <b>Ctrl+Shift+H</b> \u2013 Hide all notes<br>"
                "<b>Cmd+Shift+F</b> or <b>Ctrl+Shift+F</b> \u2013 Search notes<br>"
                "Search is also on the dock toolbar and tray menu"
            )
        return (
            "\u2328  Shortcuts:<br>"
            "<b>Ctrl+Shift+N</b> \u2013 New note<br>"
            "<b>Ctrl+Shift+H</b> \u2013 Hide all notes<br>"
            "<b>Ctrl+Shift+F</b> \u2013 Search notes<br>"
            "Search is also on the dock toolbar and tray menu"
        )

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(12)

        la = QVBoxLayout()
        la.setSpacing(14)

        g = QGroupBox("Dock Position")
        gl = QVBoxLayout(g)
        self.rt = QRadioButton("Top  \u2013  appears at the top of each monitor")
        self.rs = QRadioButton("Side  \u2013  right of primary, left of secondary")
        self.bg = QButtonGroup(self)
        for r in (self.rt, self.rs):
            gl.addWidget(r)
            self.bg.addButton(r)
        {"top": self.rt, "side": self.rs}.get(
            self.settings.get("dock_position", "top"), self.rt
        ).setChecked(True)
        width_row = QHBoxLayout()
        width_row.addWidget(QLabel("Dock width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(MIN_DOCK_WIDTH, MAX_DOCK_WIDTH)
        self.width_spin.setSuffix(" px")
        self.width_spin.setValue(
            int(self.settings.get("dock_width", MIN_DOCK_WIDTH))
        )
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(MIN_DOCK_WIDTH, MAX_DOCK_WIDTH)
        self.width_slider.setValue(self.width_spin.value())
        self.width_spin.valueChanged.connect(self.width_slider.setValue)
        self.width_slider.valueChanged.connect(self.width_spin.setValue)
        width_row.addWidget(self.width_slider, 1)
        width_row.addWidget(self.width_spin)
        gl.addLayout(width_row)
        la.addWidget(g)

        self.cd = QCheckBox("Enable Dark Mode (dock, dialogs && note chrome)")
        self.cd.blockSignals(True)
        self.cd.setChecked(self.settings.get("dark_mode", False))
        self.cd.blockSignals(False)
        self.cd.stateChanged.connect(self._on_dark_changed)
        la.addWidget(self.cd)

        tg = QGroupBox("Tags")
        tl = QVBoxLayout(tg)
        tl.addWidget(QLabel("Default tag for new notes (optional):"))
        self.tag_combo = QComboBox()
        self.tag_combo.setEditable(True)
        self.tag_combo.addItem("")
        for tag in sorted(self._known_tags):
            if tag:
                self.tag_combo.addItem(tag)
        default_tag = self.settings.get("default_tag", "")
        idx = self.tag_combo.findText(default_tag)
        self.tag_combo.setCurrentIndex(idx if idx >= 0 else 0)
        tl.addWidget(self.tag_combo)
        la.addWidget(tg)

        bg = QGroupBox("Data & Backup")
        bl = QVBoxLayout(bg)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        btn_export = QPushButton("Export\u2026")
        btn_export.clicked.connect(self._export)
        btn_import = QPushButton("Import\u2026")
        btn_import.clicked.connect(self._import)
        row1.addWidget(btn_export, 1)
        row1.addWidget(btn_import, 1)
        bl.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        btn_restore = QPushButton("Restore from backup\u2026")
        btn_restore.clicked.connect(self._restore)
        btn_folder = QPushButton("Open data folder")
        btn_folder.clicked.connect(self._open_folder)
        row2.addWidget(btn_restore, 1)
        row2.addWidget(btn_folder, 1)
        bl.addLayout(row2)
        backup_hint = QLabel(
            "<small>Export as .json or .stickynotes zip. "
            "Import can merge (newer wins) or replace all data.</small>"
        )
        backup_hint.setWordWrap(True)
        backup_hint.setMaximumWidth(_CONTENT_WIDTH - 48)
        bl.addWidget(backup_hint)
        la.addWidget(bg)

        shortcuts = QLabel(self._shortcut_text())
        shortcuts.setWordWrap(True)
        shortcuts.setMaximumWidth(_CONTENT_WIDTH - 48)
        la.addWidget(shortcuts)

        version = QLabel(_version_footer())
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        la.addWidget(version)

        outer.addLayout(la)

        btn_row = QHBoxLayout()
        ba = QPushButton("Apply && Close")
        ba.setFixedHeight(34)
        ba.clicked.connect(self._apply)
        bc = QPushButton("Cancel")
        bc.setFixedHeight(34)
        bc.setObjectName("cancelBtn")
        bc.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(ba)
        btn_row.addWidget(bc)
        outer.addLayout(btn_row)

        self.setMinimumWidth(_CONTENT_WIDTH)

    def _export(self) -> None:
        if self._on_export:
            self._on_export()

    def _import(self) -> None:
        if self._on_import:
            self._on_import()

    def _restore(self) -> None:
        if self._on_restore:
            self._on_restore()

    def _open_folder(self) -> None:
        if self._on_open_data_folder:
            self._on_open_data_folder()

    def _apply(self) -> None:
        self.settings["dock_position"] = "top" if self.rt.isChecked() else "side"
        self.settings["dark_mode"] = self.cd.isChecked()
        self.settings["dock_width"] = self.width_spin.value()
        self.settings["default_tag"] = self.tag_combo.currentText().strip().lower()
        self.accept()

    def _on_dark_changed(self) -> None:
        self.setStyleSheet(dialog_stylesheet(dark=self.cd.isChecked()))

    def _style(self) -> None:
        self.setStyleSheet(dialog_stylesheet(dark=self.settings.get("dark_mode", False)))
