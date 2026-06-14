"""Shared pytest fixtures for StickyNotes tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# Headless Qt for CI and local runs without a display server.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FakePaths:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def data_file(self) -> Path:
        return self._data_dir / "data.json"

    @property
    def backup_file(self) -> Path:
        return self._data_dir / "data.json.bak"

    @property
    def lock_file(self) -> Path:
        return self._data_dir / "app.lock"


@pytest.fixture
def temp_paths(tmp_path: Path) -> FakePaths:
    return FakePaths(tmp_path / "StickyNotesApp")
