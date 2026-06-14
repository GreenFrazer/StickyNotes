"""Benchmark DockWidget.refresh_cards at various note counts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication

from stickynotes.storage import StorageManager
from stickynotes.ui.dock import DockWidget
from tests.benchmarks._timing import run_timed


def _notes(count: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(count):
        nd = StorageManager.default_note()
        nd["content"] = f"Note {i} content"
        nd["modified_at"] = f"2026-06-14T{10 + i % 14:02d}:00:00"
        out[nd["id"]] = nd
    return out


def run_benchmarks() -> list[dict]:
    app = QApplication.instance() or QApplication([])
    dock = DockWidget(
        position="top",
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )
    results: list[dict] = []
    for count in (0, 10, 50):
        notes = _notes(count)

        def do_refresh(n=notes, d=dock) -> None:
            d.refresh_cards(n, [])

        results.append(
            run_timed(
                "dock_refresh_cards",
                f"{count}_notes",
                do_refresh,
                iterations=30 if count <= 10 else 15,
            )
        )
    return results


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmarks(), indent=2))
