"""Benchmark note expand height calculation and _on_text simulation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from stickynotes.storage import StorageManager
from stickynotes.ui.note_window import NoteWindow
from tests.benchmarks._timing import run_timed

EXPAND_CONTENT = ("Line of text.\n" * 40)[:411]
CONTENT_1K = "Word " * 200
CONTENT_10K = "Word " * 2000


def run_benchmarks() -> list[dict]:
    app = QApplication.instance() or QApplication([])
    results: list[dict] = []

    for label, content in (
        ("1kb", CONTENT_1K),
        ("10kb", CONTENT_10K),
        ("40_lines", EXPAND_CONTENT),
    ):
        nd = StorageManager.default_note()
        nd["content"] = content
        nd["width"] = 260
        nd["height"] = 180
        w = NoteWindow(nd, StorageManager())
        w.show()
        w._editing = True

        def do_expand(win=w) -> None:
            win._expanded_height()

        results.append(
            run_timed(
                "note_expanded_height",
                label,
                do_expand,
                iterations=50,
            )
        )

        def do_on_text(win=w) -> None:
            win._on_text()

        results.append(
            run_timed(
                "note_on_text",
                label,
                do_on_text,
                iterations=30,
            )
        )

    return results


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmarks(), indent=2))
