"""Tests for OS shell file icons used on dock tiles."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtGui import QPixmap

from stickynotes.ui.dock import DOCK_FILE_ICON_SIZE, DockFileIndicator
from stickynotes.ui.file_icons import (
    clear_file_icon_cache,
    file_icon_pixmap,
    has_file_icon,
)

_OFFSCREEN = os.environ.get("QT_QPA_PLATFORM") == "offscreen"
_SKIP_REAL_SHELL_ICONS = _OFFSCREEN or (
    sys.platform == "win32" and os.environ.get("STICKYNOTES_TEST_SHELL_ICONS") != "1"
)


@pytest.fixture(autouse=True)
def _clear_icon_cache() -> None:
    clear_file_icon_cache()
    yield
    clear_file_icon_cache()


def test_file_icon_pixmap_empty_path_returns_none() -> None:
    assert file_icon_pixmap("") is None
    assert file_icon_pixmap("   ") is None


def test_file_icon_pixmap_missing_file_returns_none(tmp_path: Path) -> None:
    assert file_icon_pixmap(str(tmp_path / "missing.txt")) is None


def test_file_icon_pixmap_cache_returns_same_object(qapp, tmp_path: Path) -> None:
    path = tmp_path / "cached.txt"
    path.write_text("cache", encoding="utf-8")
    fake = QPixmap(28, 28)
    fake.fill()
    with patch(
        "stickynotes.ui.file_icons._icon_from_qt",
        return_value=fake,
    ):
        first = file_icon_pixmap(str(path), size=28)
        second = file_icon_pixmap(str(path), size=28)
    assert first is not None
    assert second is first


def test_file_icon_pixmap_cache_invalidates_on_mtime_change(qapp, tmp_path: Path) -> None:
    path = tmp_path / "mtime.txt"
    path.write_text("v1", encoding="utf-8")
    fake_v1 = QPixmap(28, 28)
    fake_v1.fill()
    fake_v2 = QPixmap(28, 28)
    fake_v2.fill()
    with patch(
        "stickynotes.ui.file_icons._icon_from_qt",
        side_effect=[fake_v1, fake_v2],
    ):
        first = file_icon_pixmap(str(path), size=28)
        path.write_text("v2", encoding="utf-8")
        second = file_icon_pixmap(str(path), size=28)
    assert first is fake_v1
    assert second is fake_v2
    assert second is not first


def test_file_icon_pixmap_falls_back_to_platform_when_qt_unavailable(
    qapp, tmp_path: Path,
) -> None:
    path = tmp_path / "shortcut.lnk"
    path.write_text("lnk", encoding="utf-8")
    fake = QPixmap(28, 28)
    fake.fill()
    with (
        patch("stickynotes.ui.file_icons._icon_from_qt", return_value=None),
        patch("stickynotes.ui.file_icons._icon_from_platform", return_value=fake),
    ):
        pixmap = file_icon_pixmap(str(path), size=28)
    assert pixmap is fake


def test_has_file_icon_matches_pixmap_availability(qapp, tmp_path: Path) -> None:
    path = tmp_path / "probe.txt"
    path.write_text("x", encoding="utf-8")
    fake = QPixmap(28, 28)
    fake.fill()
    with patch("stickynotes.ui.file_icons.file_icon_pixmap", return_value=fake):
        assert has_file_icon(str(path)) is True
    with patch("stickynotes.ui.file_icons.file_icon_pixmap", return_value=None):
        assert has_file_icon(str(path)) is False


@pytest.mark.skipif(
    _SKIP_REAL_SHELL_ICONS,
    reason="QFileIconProvider is skipped offscreen / in pytest on Windows",
)
def test_file_icon_pixmap_returns_pixmap_for_real_file(qapp, tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello", encoding="utf-8")
    pixmap = file_icon_pixmap(str(path))
    if pixmap is None:
        pytest.skip("OS shell icons unavailable in this environment")
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()


def test_dock_file_indicator_shows_pixmap_when_icon_available(
    qapp, qtbot, tmp_path: Path
) -> None:
    path = tmp_path / "word.docx"
    path.write_text("doc", encoding="utf-8")
    fake = QPixmap(28, 28)
    fake.fill()
    with patch(
        "stickynotes.ui.dock.file_icon_pixmap",
        return_value=fake,
    ):
        indicator = DockFileIndicator(
            {"id": "sc-1", "path": str(path), "label": None},
        )
    qtbot.addWidget(indicator)
    assert indicator.lbl_badge.pixmap() is not None
    assert not indicator.lbl_badge.pixmap().isNull()
    assert indicator.lbl_badge.text() == ""


def test_dock_file_indicator_falls_back_to_text_badge(
    qapp, qtbot, tmp_path: Path
) -> None:
    path = tmp_path / "report.docx"
    path.write_text("doc", encoding="utf-8")
    with patch(
        "stickynotes.ui.dock.file_icon_pixmap",
        return_value=None,
    ):
        indicator = DockFileIndicator(
            {"id": "sc-2", "path": str(path), "label": None},
        )
    qtbot.addWidget(indicator)
    assert indicator.lbl_badge.text() == "DOC"
    pixmap = indicator.lbl_badge.pixmap()
    assert pixmap is None or pixmap.isNull()


def test_dock_file_indicator_tooltip_includes_label(
    qapp, qtbot, tmp_path: Path
) -> None:
    path = tmp_path / "report.docx"
    path.write_text("doc", encoding="utf-8")
    with patch(
        "stickynotes.ui.dock.file_icon_pixmap",
        return_value=QPixmap(DOCK_FILE_ICON_SIZE, DOCK_FILE_ICON_SIZE),
    ):
        indicator = DockFileIndicator(
            {"id": "sc-4", "path": str(path), "label": "My Report"},
        )
    qtbot.addWidget(indicator)
    assert "My Report" in indicator.toolTip()
    assert str(path) in indicator.toolTip()


def test_dock_file_indicator_uses_configured_icon_size(
    qapp, qtbot, tmp_path: Path
) -> None:
    path = tmp_path / "size.txt"
    path.write_text("x", encoding="utf-8")
    with patch(
        "stickynotes.ui.dock.file_icon_pixmap",
        return_value=QPixmap(DOCK_FILE_ICON_SIZE, DOCK_FILE_ICON_SIZE),
    ) as mock_icon:
        DockFileIndicator({"id": "sc-3", "path": str(path), "label": None})
    mock_icon.assert_called_once_with(str(path), size=DOCK_FILE_ICON_SIZE)
