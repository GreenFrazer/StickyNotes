"""Reminder polling and native notification delivery."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from stickynotes.app_manager import AppManager

logger = logging.getLogger(__name__)

POLL_MS = 20_000


class ReminderService(QObject):
    reminder_due = pyqtSignal(str, dict)

    def __init__(
        self,
        notes_provider: Callable[[], dict[str, dict[str, Any]]],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._notes_provider = notes_provider
        self._fired: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()
        QTimer.singleShot(2000, self._poll)

    def stop(self) -> None:
        self._timer.stop()

    def clear_fired(self, note_id: str | None = None) -> None:
        if note_id:
            self._fired.discard(note_id)
        else:
            self._fired.clear()

    def _poll(self) -> None:
        now = datetime.now()
        for nid, nd in self._notes_provider().items():
            raw = nd.get("reminder_at")
            if not raw:
                self._fired.discard(nid)
                continue
            try:
                due = datetime.fromisoformat(str(raw))
            except (ValueError, TypeError):
                continue
            if due > now:
                self._fired.discard(nid)
                continue
            if nid not in self._fired:
                self._fired.add(nid)
                self.reminder_due.emit(nid, dict(nd))

    @staticmethod
    def reminder_presets() -> list[tuple[str, int]]:
        """Return (label, minutes-from-now) pairs for the context menu."""
        return [
            ("In 5 minutes", 5),
            ("In 10 minutes", 10),
            ("In 15 minutes", 15),
            ("In 30 minutes", 30),
            ("In 60 minutes", 60),
        ]

    @staticmethod
    def reminder_at_offset(minutes: int) -> datetime:
        return datetime.now() + timedelta(minutes=minutes)

    @staticmethod
    def format_reminder(iso: str | None) -> str:
        if not iso:
            return ""
        try:
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return iso or ""

    @staticmethod
    def is_overdue(iso: str | None) -> bool:
        if not iso:
            return False
        try:
            return datetime.fromisoformat(iso) < datetime.now()
        except (ValueError, TypeError):
            return False
