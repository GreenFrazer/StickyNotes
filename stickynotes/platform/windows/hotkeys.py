"""Windows global hotkeys via ctypes GetAsyncKeyState polling."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer

if TYPE_CHECKING:
    from stickynotes.app_manager import AppManager

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_N = 0x4E
VK_H = 0x48
VK_F = 0x46


class WindowsHotkeys:
    def __init__(self, app_manager: AppManager) -> None:
        self._mgr = app_manager
        self._hkn = False
        self._hkh = False
        self._hkf = False
        self._timer = QTimer()
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        try:
            user32 = ctypes.windll.user32
            ctrl = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
            shift = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
            pn = ctrl and shift and bool(user32.GetAsyncKeyState(VK_N) & 0x8000)
            if pn and not self._hkn:
                self._mgr.create_note()
            self._hkn = pn
            ph = ctrl and shift and bool(user32.GetAsyncKeyState(VK_H) & 0x8000)
            if ph and not self._hkh:
                self._mgr.hide_all_notes()
            self._hkh = ph
            pf = ctrl and shift and bool(user32.GetAsyncKeyState(VK_F) & 0x8000)
            if pf and not self._hkf:
                self._mgr.open_search()
            self._hkf = pf
        except Exception:
            pass
