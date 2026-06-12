"""macOS NSWindow configuration for floating note and dock widgets."""

from __future__ import annotations

import logging
import sys
from ctypes import c_void_p
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def configure_floating_window(widget: QWidget, *, on_top: bool = False) -> None:
    """Keep widgets visible across monitors, Spaces, and when the app is inactive."""
    if sys.platform != "darwin":
        return

    try:
        wid = int(widget.winId())
        if not wid:
            return

        import objc
        from AppKit import (
            NSFloatingWindowLevel,
            NSNormalWindowLevel,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowCollectionBehaviorStationary,
        )

        view = objc.objc_object(c_void_p=wid)
        ns_window = view.window()
        if ns_window is None:
            return

        behavior = (
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        ns_window.setCollectionBehavior_(behavior)
        ns_window.setHidesOnDeactivate_(False)
        # Qt.Tool windows default to a floating level on macOS; only elevate when pinned.
        if on_top:
            ns_window.setLevel_(NSFloatingWindowLevel + 1)
        else:
            ns_window.setLevel_(NSNormalWindowLevel)
    except ImportError:
        return
    except Exception:
        logger.exception("Failed to configure macOS floating window for %r", widget)
