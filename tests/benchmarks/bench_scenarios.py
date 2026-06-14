"""Scenario benchmarks: typing session, bulk load, screen change."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from stickynotes.app_manager import AppManager
from stickynotes.storage import StorageManager
from tests.benchmarks._timing import run_timed
from tests.conftest import FakePaths


def _make_storage(note_count: int, base: Path) -> StorageManager:
    paths = FakePaths(base)
    storage = StorageManager(paths, restore_prompt=lambda: False)
    for i in range(note_count):
        nd = StorageManager.default_note()
        nd["content"] = f"Stored note {i}"
        storage.set_note(nd["id"], nd)
    return storage


def _typing_session() -> dict:
    paths = FakePaths(Path("/tmp/stickynotes_bench_typing"))
    storage = StorageManager(paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "Start"
    storage.set_note(nd["id"], nd)
    app = QApplication.instance() or QApplication([])

    def do_typing() -> None:
        with (
            patch("stickynotes.app_manager.StorageManager", return_value=storage),
            patch("stickynotes.app_manager.QSystemTrayIcon"),
            patch("stickynotes.app_manager.get_hotkey_service") as hk,
        ):
            hk.return_value = MagicMock()
            mgr = AppManager(app)
            nid = next(iter(mgr.notes))
            note = mgr.notes[nid]
            note.editor.setPlainText(note.editor.toPlainText() + ("x" * 500))
            note._persist()
            mgr._schedule_dock_refresh(nid)
            mgr._refresh_all_docks()

    return run_timed(
        "scenario",
        "typing_session_500_chars",
        do_typing,
        iterations=10,
        warmup=1,
    )


def _bulk_load() -> dict:
    base = Path("/tmp/stickynotes_bench_bulk50")
    storage = _make_storage(50, base)
    app = QApplication.instance() or QApplication([])

    t0 = time.perf_counter()
    with (
        patch("stickynotes.app_manager.StorageManager", return_value=storage),
        patch("stickynotes.app_manager.QSystemTrayIcon"),
        patch("stickynotes.app_manager.get_hotkey_service") as hk,
    ):
        hk.return_value = MagicMock()
        mgr = AppManager(app)
        mgr._refresh_all_docks()
    elapsed = (time.perf_counter() - t0) * 1000.0
    return {
        "name": "scenario",
        "scenario": "bulk_load_50_notes",
        "median_ms": round(elapsed, 4),
        "p95_ms": round(elapsed, 4),
        "iterations": 1,
    }


def _screen_change() -> dict:
    paths = FakePaths(Path("/tmp/stickynotes_bench_screen"))
    storage = StorageManager(paths, restore_prompt=lambda: False)
    nd = StorageManager.default_note()
    nd["content"] = "One note"
    storage.set_note(nd["id"], nd)
    app = QApplication.instance() or QApplication([])

    with (
        patch("stickynotes.app_manager.StorageManager", return_value=storage),
        patch("stickynotes.app_manager.QSystemTrayIcon"),
        patch("stickynotes.app_manager.get_hotkey_service") as hk,
    ):
        hk.return_value = MagicMock()
        manager = AppManager(app)

    t0 = time.perf_counter()
    manager._create_docks()
    manager._create_docks()
    elapsed = (time.perf_counter() - t0) * 1000.0
    return {
        "name": "scenario",
        "scenario": "screen_change_2x_create_docks",
        "median_ms": round(elapsed, 4),
        "p95_ms": round(elapsed, 4),
        "iterations": 1,
    }


def run_benchmarks() -> list[dict]:
    return [_bulk_load(), _screen_change(), _typing_session()]


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmarks(), indent=2))
