#!/usr/bin/env python3
"""Root entry shim — run with: python main.py"""

import sys

# py2app only bundles modules reachable from static imports. Hotkey deps are
# imported lazily in stickynotes.platform.macos.hotkeys, so pull them in here.
if sys.platform == "darwin":
    import AppKit  # noqa: F401
    import Cocoa  # noqa: F401
    import stickynotes.platform.macos.windows  # noqa: F401
    import stickynotes.platform.macos.app  # noqa: F401
    import CoreFoundation  # noqa: F401
    import HIServices  # noqa: F401
    import PyObjCTools  # noqa: F401
    import Quartz  # noqa: F401
    import pynput  # noqa: F401

from stickynotes.main import main

if __name__ == "__main__":
    main()
