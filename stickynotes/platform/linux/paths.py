"""Linux XDG data directory paths."""

from __future__ import annotations

from pathlib import Path


class LinuxPaths:
    def __init__(self) -> None:
        self._data_dir = Path.home() / ".local" / "share" / "StickyNotesApp"
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
