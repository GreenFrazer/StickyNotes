#!/usr/bin/env python3
"""Copy PyObjC extras py2app often misses (namespace packages)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_LIB = ROOT / "dist/Sticky Notes.app/Contents/Resources/lib/python3.9"
VENV_SITE = ROOT / ".venv/lib/python3.9/site-packages"

# PyObjCTools has no __init__.py; Cocoa is a thin umbrella — both are skipped easily.
EXTRAS = ("PyObjCTools", "Cocoa")


def site_packages() -> Path:
    if VENV_SITE.is_dir():
        return VENV_SITE
    import site

    for path in site.getsitepackages():
        candidate = Path(path)
        if (candidate / "PyObjCTools").is_dir():
            return candidate
    raise SystemExit("Could not locate site-packages with PyObjCTools")


def main() -> None:
    if not APP_LIB.is_dir():
        raise SystemExit(f"App bundle lib not found: {APP_LIB}")

    src_root = site_packages()
    for name in EXTRAS:
        src = src_root / name
        if not src.is_dir():
            print(f"warning: missing {src}", file=sys.stderr)
            continue
        dest = APP_LIB / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        print(f"Bundled extra: {name}")


if __name__ == "__main__":
    main()
