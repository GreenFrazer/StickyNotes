"""No-op hotkey backend for unsupported platforms."""

from __future__ import annotations


class NoOpHotkeys:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
