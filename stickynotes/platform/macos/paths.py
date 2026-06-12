"""macOS Application Support data paths."""

from __future__ import annotations

from pathlib import Path


class MacOSPaths:
    def __init__(self) -> None:
        self._data_dir = (
            Path.home() / "Library" / "Application Support" / "StickyNotesApp"
        )
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
