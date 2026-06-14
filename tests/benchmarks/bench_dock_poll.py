"""Benchmark DockWidget._poll_mouse call cost."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication

from stickynotes.ui.dock import DockWidget
from tests.benchmarks._timing import run_timed


def run_benchmarks() -> list[dict]:
    app = QApplication.instance() or QApplication([])
    dock = DockWidget(
        position="top",
        screen_geo=QRect(0, 0, 1920, 1080),
        content_getter=lambda _nid: "",
    )

    def poll_10k() -> None:
        for _ in range(10_000):
            dock._poll_mouse()

    return [
        run_timed(
            "dock_poll_mouse",
            "10k_iterations",
            poll_10k,
            iterations=5,
            warmup=2,
        )
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmarks(), indent=2))
