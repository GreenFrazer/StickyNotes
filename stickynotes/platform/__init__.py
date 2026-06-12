"""Platform factory — lazy-imports OS-specific backends."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from stickynotes.platform.base import HotkeyService, PlatformPaths

if TYPE_CHECKING:
    from stickynotes.app_manager import AppManager


class NoOpHotkeys:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def get_paths() -> PlatformPaths:
    if sys.platform == "win32":
        from stickynotes.platform.windows.paths import WindowsPaths

        return WindowsPaths()
    if sys.platform == "darwin":
        from stickynotes.platform.macos.paths import MacOSPaths

        return MacOSPaths()
    from stickynotes.platform.linux.paths import LinuxPaths

    return LinuxPaths()


def get_hotkey_service(app_manager: AppManager) -> HotkeyService:
    if sys.platform == "win32":
        from stickynotes.platform.windows.hotkeys import WindowsHotkeys

        return WindowsHotkeys(app_manager)
    if sys.platform == "darwin":
        from stickynotes.platform.macos.hotkeys import MacOSHotkeys

        return MacOSHotkeys(app_manager)
    return NoOpHotkeys()
