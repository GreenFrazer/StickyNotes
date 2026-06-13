"""
py2app build configuration for Sticky Notes (macOS).

Run from repo root:
    bash packaging/macos/build.sh
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    # pynput is imported lazily in hotkeys.start(), so list it explicitly for py2app.
    "packages": [
        "stickynotes",
        "PyQt6",
        "pynput",
        "six",
        "objc",
        "Quartz",
        "CoreFoundation",
        "HIServices",
        "AppKit",
        "Foundation",
    ],
    "includes": [
        "PyObjCTools",
        "PyObjCTools.MachSignals",
    ],
    "plist": {
        "CFBundleName": "Sticky Notes",
        "CFBundleDisplayName": "Sticky Notes",
        "CFBundleIdentifier": "com.stickynotes.app",
        "CFBundleVersion": "3.5.0",
        "CFBundleShortVersionString": "3.5",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        # Menu-bar accessory: no Dock icon (tray is the primary UI).
        "LSUIElement": True,
    },
}

setup(
    name="StickyNotes",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
