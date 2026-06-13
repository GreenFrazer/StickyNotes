"""macOS application lifecycle helpers."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def configure_menu_bar_app() -> None:
    """Run as a menu-bar accessory app (tray icon only, no Dock icon).

    PyQt6 creates a regular GUI application by default, which macOS shows in
    the Dock. Sticky Notes also installs a QSystemTrayIcon, so users were
    seeing both. NSApplicationActivationPolicyAccessory keeps the tray entry
    without a Dock tile.
    """
    if sys.platform != "darwin":
        return

    try:
        from AppKit import NSApp, NSApplicationActivationPolicyAccessory

        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except ImportError:
        return
    except Exception:
        logger.exception("Failed to configure menu-bar-only activation policy")
