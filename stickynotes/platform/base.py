"""Platform abstraction protocols."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class PlatformPaths(Protocol):
    @property
    def data_dir(self) -> Path: ...

    @property
    def data_file(self) -> Path: ...

    @property
    def backup_file(self) -> Path: ...

    @property
    def lock_file(self) -> Path: ...


@runtime_checkable
class HotkeyService(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...
