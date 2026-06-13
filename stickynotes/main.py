"""Application entry point with QLockFile single-instance guard."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QLockFile
from PyQt6.QtWidgets import QApplication, QMessageBox

from stickynotes.app_manager import AppManager
from stickynotes.platform import get_paths


def main() -> None:
    paths = get_paths()
    paths.data_dir.mkdir(parents=True, exist_ok=True)

    lock = QLockFile(str(paths.lock_file))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "Sticky Notes",
            "Sticky Notes is already running.",
        )
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName("Sticky Notes")
    app.setQuitOnLastWindowClosed(False)
    if sys.platform == "darwin":
        from stickynotes.platform.macos.app import configure_menu_bar_app

        configure_menu_bar_app()
    AppManager(app)
    ec = app.exec()
    lock.unlock()
    sys.exit(ec)


if __name__ == "__main__":
    main()
