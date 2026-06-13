"""Application settings dialog."""

from __future__ import annotations

import sys
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from stickynotes.theme import dialog_stylesheet


class SettingsDialog(QDialog):
    def __init__(self, cur: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sticky Notes \u2013 Settings")
        self.setFixedSize(400, 360)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.settings = dict(cur)
        self._build()
        self._style()

    def _shortcut_text(self) -> str:
        if sys.platform == "darwin":
            return (
                "\u2328  Shortcuts (global, requires Accessibility on macOS):<br>"
                "<b>Cmd+Shift+N</b> or <b>Ctrl+Shift+N</b> \u2013 New note<br>"
                "<b>Cmd+Shift+H</b> or <b>Ctrl+Shift+H</b> \u2013 Hide all notes"
            )
        return (
            "\u2328  Shortcuts:<br>"
            "<b>Ctrl+Shift+N</b> \u2013 New note<br>"
            "<b>Ctrl+Shift+H</b> \u2013 Hide all notes"
        )

    def _build(self) -> None:
        la = QVBoxLayout(self)
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
        la.addWidget(QLabel(self._shortcut_text()))
        ab = QLabel("<small>Sticky Notes v3.5 \u2013 PyQt6</small>")
        ab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        la.addWidget(ab)
        la.addStretch()
        bl = QHBoxLayout()
        ba = QPushButton("Apply && Close")
        ba.setFixedHeight(34)
        ba.clicked.connect(self._apply)
        bc = QPushButton("Cancel")
        bc.setFixedHeight(34)
        bc.setObjectName("cancelBtn")
        bc.clicked.connect(self.reject)
        bl.addStretch()
        bl.addWidget(ba)
        bl.addWidget(bc)
        la.addLayout(bl)

    def _apply(self) -> None:
        self.settings["dock_position"] = "top" if self.rt.isChecked() else "side"
        self.settings["dark_mode"] = self.cd.isChecked()
        self.accept()

    def _on_dark_changed(self) -> None:
        self.setStyleSheet(dialog_stylesheet(dark=self.cd.isChecked()))

    def _style(self) -> None:
        self.setStyleSheet(dialog_stylesheet(dark=self.settings.get("dark_mode", False)))
