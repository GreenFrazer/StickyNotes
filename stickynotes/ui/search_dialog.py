"""Global search and quick switcher palette."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from stickynotes.models import (
    fmt_dt,
    is_private,
    normalize_tags,
    note_title,
    private_preview_text,
)
from stickynotes.theme import dialog_stylesheet


class SearchDialog(QDialog):
    note_selected = pyqtSignal(str)

    DEBOUNCE_MS = 300

    def __init__(
        self,
        notes: dict[str, dict[str, Any]],
        content_getter: Callable[[str], str],
        *,
        dark_mode: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._notes = dict(notes)
        self._content_getter = content_getter
        self._dark = dark_mode
        self._revealed_private: set[str] = set()
        self.setWindowTitle("Search Notes")
        self.setMinimumSize(480, 360)
        self.setWindowFlags(
            (self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(self.DEBOUNCE_MS)
        self._debounce.timeout.connect(self._run_search)
        self._build()
        self.setStyleSheet(dialog_stylesheet(dark=dark_mode))

    def _build(self) -> None:
        lo = QVBoxLayout(self)
        lo.setSpacing(8)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search notes and tags\u2026")
        self._input.textChanged.connect(self._on_text_changed)
        lo.addWidget(self._input)
        self._status = QLabel("")
        self._status.setObjectName("searchStatus")
        lo.addWidget(self._status)
        self._results = QListWidget()
        self._results.itemActivated.connect(self._on_activated)
        self._results.itemDoubleClicked.connect(self._on_activated)
        lo.addWidget(self._results, 1)
        hint = QLabel("Enter to open  \u00B7  Esc to close")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(hint)

    def update_notes(self, notes: dict[str, dict[str, Any]]) -> None:
        self._notes = dict(notes)

    def show_and_focus(self) -> None:
        if self._debounce.isActive():
            self._debounce.stop()
        self._input.blockSignals(True)
        try:
            self._input.clear()
            self._results.clear()
            self._status.setText("")
            self._revealed_private.clear()
        finally:
            self._input.blockSignals(False)
        if not self.isVisible():
            self.show()
        # Defer raise/focus to avoid re-entrant showEvent crashes on macOS.
        QTimer.singleShot(0, self._raise_and_focus)

    def _raise_and_focus(self) -> None:
        if not self.isVisible():
            return
        self.raise_()
        self.activateWindow()
        self._input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _on_text_changed(self, _text: str) -> None:
        self._debounce.start()

    def _run_search(self) -> None:
        query = self._input.text().strip().lower()
        self._results.clear()
        if not query:
            self._status.setText("")
            return
        matches: list[tuple[str, dict[str, Any], str]] = []
        for nid, nd in self._notes.items():
            raw_content = self._content_getter(nid)
            content = raw_content if isinstance(raw_content, str) else str(raw_content or "")
            title = note_title(content)
            tags = normalize_tags(nd.get("tags", []))
            tags_text = " ".join(tags)
            haystack = f"{title}\n{content}\n{tags_text}".lower()
            if query not in haystack:
                continue
            if is_private(nd) and nid not in self._revealed_private:
                preview = private_preview_text()
            else:
                content_haystack = f"{title}\n{content}".lower()
                matching_tags = [t for t in tags if query in t]
                if query in content_haystack:
                    idx = content_haystack.find(query)
                    start = max(0, idx - 20)
                    preview = content[start : start + 80].replace("\n", " ")
                elif matching_tags:
                    preview = "Tags: " + ", ".join(f"#{t}" for t in matching_tags)
                else:
                    preview = content[:80].replace("\n", " ") or ""
            matches.append((nid, nd, preview))
        matches.sort(key=lambda m: m[1].get("modified_at", ""), reverse=True)
        for nid, nd, preview in matches:
            colour = nd.get("colour", "yellow")
            raw_title_content = self._content_getter(nid)
            title_content = (
                raw_title_content
                if isinstance(raw_title_content, str)
                else str(raw_title_content or "")
            )
            title = note_title(title_content)
            needs_reveal = is_private(nd) and nid not in self._revealed_private
            if needs_reveal:
                title = "Private note"
            mod = fmt_dt(nd.get("modified_at", ""))
            label = f"[{colour}] {title}  \u00B7  {mod}\n{preview}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, nid)
            item.setData(Qt.ItemDataRole.UserRole + 1, needs_reveal)
            self._results.addItem(item)
        count = len(matches)
        self._status.setText(f"{count} result{'s' if count != 1 else ''}")

    def _on_activated(self, item: QListWidgetItem) -> None:
        nid = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(nid, str):
            return
        if item.data(Qt.ItemDataRole.UserRole + 1):
            self._revealed_private.add(nid)
            # Refresh after the click handler returns; clearing items here can crash Qt on Windows.
            QTimer.singleShot(0, self._run_search)
            return
        self.note_selected.emit(nid)
        QTimer.singleShot(0, self.accept)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self._results.currentItem()
            if item:
                self._on_activated(item)
            return
        if event.key() == Qt.Key.Key_Down and self._results.count():
            self._results.setCurrentRow(0)
            self._results.setFocus()
            return
        super().keyPressEvent(event)
