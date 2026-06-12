"""macOS global hotkeys via pynput (Cmd+Ctrl + Shift)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stickynotes.app_manager import AppManager

logger = logging.getLogger(__name__)


class MacOSHotkeys:
    """Register Cmd+Shift+N/H and Ctrl+Shift+N/H global shortcuts."""

    def __init__(self, app_manager: AppManager) -> None:
        self._mgr = app_manager
        self._listener = None
        self._pressed: set[str] = set()
        self._new_armed = False
        self._hide_armed = False
        self._warned = False

    def start(self) -> None:
        try:
            from pynput import keyboard
        except ImportError:
            logger.warning("pynput not installed; global hotkeys disabled on macOS")
            self._show_accessibility_dialog(
                "pynput is not installed. Install with: pip install pynput"
            )
            return

        def on_press(key) -> None:
            self._pressed.add(self._key_id(key))
            if not self._modifiers_ok():
                return
            kid = self._key_id(key)
            if kid in ("n", "N") and not self._new_armed:
                self._new_armed = True
                self._invoke(self._mgr.create_note)
            elif kid in ("h", "H") and not self._hide_armed:
                self._hide_armed = True
                self._invoke(self._mgr.hide_all_notes)

        def on_release(key) -> None:
            kid = self._key_id(key)
            self._pressed.discard(kid)
            if kid in ("n", "N"):
                self._new_armed = False
            if kid in ("h", "H"):
                self._hide_armed = False

        try:
            self._listener = keyboard.Listener(
                on_press=on_press, on_release=on_release
            )
            self._listener.start()
        except Exception as exc:
            logger.exception("Failed to start macOS hotkey listener: %s", exc)
            if not self._warned:
                self._warned = True
                self._show_accessibility_dialog(
                    "Global shortcuts require Accessibility permission.\n\n"
                    "Open System Settings → Privacy & Security → Accessibility "
                    "and enable Sticky Notes.\n\n"
                    "Shortcuts: Cmd+Shift+N / Ctrl+Shift+N (new note), "
                    "Cmd+Shift+H / Ctrl+Shift+H (hide all)."
                )

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _modifiers_ok(self) -> bool:
        from pynput.keyboard import Key

        shift_keys = {str(Key.shift), str(Key.shift_l), str(Key.shift_r)}
        cmd_keys = {str(Key.cmd), str(Key.cmd_r), str(Key.cmd_l)}
        ctrl_keys = {str(Key.ctrl), str(Key.ctrl_l), str(Key.ctrl_r)}
        has_shift = bool(self._pressed & shift_keys)
        has_cmd_or_ctrl = bool(self._pressed & cmd_keys) or bool(
            self._pressed & ctrl_keys
        )
        return has_shift and has_cmd_or_ctrl

    @staticmethod
    def _key_id(key) -> str:
        from pynput.keyboard import KeyCode

        if isinstance(key, KeyCode) and key.char:
            return key.char
        return str(key)

    def _invoke(self, fn) -> None:
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, fn)

    def _show_accessibility_dialog(self, message: str) -> None:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QMessageBox

        def show() -> None:
            QMessageBox.warning(
                None,
                "Sticky Notes — Shortcuts",
                message,
            )

        QTimer.singleShot(500, show)
