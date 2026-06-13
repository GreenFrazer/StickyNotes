#!/usr/bin/env python3
"""Generate StickyNotes app icon assets for macOS (.icns) and Windows (.ico)."""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def build_icns(out: Path, sizes: list[int]) -> None:
    from PyQt6.QtWidgets import QApplication

    from stickynotes.ui.icons import render_app_icon

    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        iconset = tdir / "AppIcon.iconset"
        iconset.mkdir()
        mapping = {
            16: "icon_16x16.png",
            32: "icon_16x16@2x.png",
            32: "icon_32x32.png",
            64: "icon_32x32@2x.png",
            128: "icon_128x128.png",
            256: "icon_128x128@2x.png",
            512: "icon_512x512.png",
            1024: "icon_512x512@2x.png",
        }
        seen: set[str] = set()
        for s in sizes:
            if s == 32 and "icon_32x32.png" not in seen:
                name = "icon_32x32.png"
            elif s == 64:
                name = "icon_32x32@2x.png"
            elif s == 256:
                name = "icon_128x128@2x.png"
            elif s == 512:
                name = "icon_512x512.png"
            elif s == 1024:
                name = "icon_512x512@2x.png"
            elif s == 16:
                name = "icon_16x16.png"
            elif s == 128:
                name = "icon_128x128.png"
            else:
                name = f"icon_{s}x{s}.png"
            if name in seen:
                continue
            seen.add(name)
            render_app_icon(s).save(str(iconset / name), "PNG")
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(out)],
            check=True,
        )


def build_ico(out: Path, sizes: list[int]) -> None:
    from PyQt6.QtCore import QBuffer, QIODevice
    from PyQt6.QtWidgets import QApplication

    from stickynotes.ui.icons import render_app_icon

    images: list[tuple[int, bytes]] = []
    for s in sizes:
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        render_app_icon(s).save(buf, "PNG")
        images.append((s, bytes(buf.data())))

    offset = 6 + 16 * len(images)
    parts = [struct.pack("<HHH", 0, 1, len(images))]
    blobs: list[bytes] = []
    for s, png in images:
        w = 0 if s >= 256 else s
        h = 0 if s >= 256 else s
        parts.append(
            struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
        )
        blobs.append(png)
        offset += len(png)
    with out.open("wb") as f:
        for part in parts:
            f.write(part)
        for blob in blobs:
            f.write(blob)


def main() -> int:
    root = Path(__file__).resolve().parent
    repo = root.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    mac_dir = root / "macos"
    win_dir = root / "windows"
    mac_dir.mkdir(parents=True, exist_ok=True)
    win_dir.mkdir(parents=True, exist_ok=True)

    from stickynotes.ui.icons import render_app_icon

    png_path = root / "StickyNotes.png"
    render_app_icon(512).save(str(png_path), "PNG")
    print(f"Wrote {png_path}")

    icns_path = mac_dir / "StickyNotes.icns"
    build_icns(icns_path, [16, 32, 64, 128, 256, 512, 1024])
    print(f"Wrote {icns_path}")

    ico_path = win_dir / "StickyNotes.ico"
    build_ico(ico_path, [16, 32, 48, 64, 128, 256])
    print(f"Wrote {ico_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
