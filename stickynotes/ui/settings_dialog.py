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
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from stickynotes.theme import dialog_stylesheet


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
        self.setMinimumSize(420, 480)
        self.resize(420, 520)
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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        la = QVBoxLayout(body)
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
        la.addWidget(g)

        self.cd = QCheckBox("Enable Dark Mode (dock, dialogs && note chrome)")
        self.cd.setChecked(self.settings.get("dark_mode", False))
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
        btn_export = QPushButton("Export\u2026")
        btn_export.clicked.connect(self._export)
        btn_import = QPushButton("Import\u2026")
        btn_import.clicked.connect(self._import)
        row1.addWidget(btn_export)
        row1.addWidget(btn_import)
        bl.addLayout(row1)
        row2 = QHBoxLayout()
        btn_restore = QPushButton("Restore from backup\u2026")
        btn_restore.clicked.connect(self._restore)
        btn_folder = QPushButton("Open data folder")
        btn_folder.clicked.connect(self._open_folder)
        row2.addWidget(btn_restore)
        row2.addWidget(btn_folder)
        bl.addLayout(row2)
        bl.addWidget(
            QLabel(
                "<small>Export as .json or .stickynotes zip. "
                "Import can merge (newer wins) or replace all data.</small>"
            )
        )
        la.addWidget(bg)

        la.addWidget(QLabel(self._shortcut_text()))
        ab = QLabel("<small>Sticky Notes v3.5 \u2013 PyQt6</small>")
        ab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        la.addWidget(ab)
        la.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

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
        self.settings["default_tag"] = self.tag_combo.currentText().strip().lower()
        self.accept()

    def _on_dark_changed(self) -> None:
        self.setStyleSheet(dialog_stylesheet(dark=self.cd.isChecked()))

    def _style(self) -> None:
        self.setStyleSheet(dialog_stylesheet(dark=self.settings.get("dark_mode", False)))
