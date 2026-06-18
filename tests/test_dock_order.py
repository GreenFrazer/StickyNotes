"""Tests for dock item ordering helpers."""

from __future__ import annotations

from stickynotes.models import default_dock_item_order, ordered_dock_item_ids


def test_default_dock_item_order_shortcuts_then_notes() -> None:
    shortcuts = {
        "s2": {"added_at": "2026-06-14T10:00:00"},
        "s1": {"added_at": "2026-06-14T09:00:00"},
    }
    notes = {
        "n1": {"modified_at": "2026-06-14T08:00:00"},
        "n2": {"modified_at": "2026-06-14T11:00:00"},
    }
    order = default_dock_item_order(
        ["s2", "s1"],
        ["n1", "n2"],
        shortcuts,
        notes,
    )
    assert order == ["s1", "s2", "n2", "n1"]


def test_ordered_dock_item_ids_preserves_saved_order() -> None:
    shortcuts = {"s1": {"added_at": "2026-06-14T09:00:00"}}
    notes = {
        "n1": {"modified_at": "2026-06-14T08:00:00"},
        "n2": {"modified_at": "2026-06-14T11:00:00"},
    }
    order = ordered_dock_item_ids(
        ["n2", "s1", "n1"],
        ["s1"],
        ["n1", "n2"],
        shortcuts,
        notes,
    )
    assert order == ["n2", "s1", "n1"]


def test_ordered_dock_item_ids_appends_new_items() -> None:
    shortcuts = {"s1": {"added_at": "2026-06-14T09:00:00"}}
    notes = {
        "n1": {"modified_at": "2026-06-14T08:00:00"},
        "n2": {"modified_at": "2026-06-14T11:00:00"},
    }
    order = ordered_dock_item_ids(
        ["n1"],
        ["s1"],
        ["n1", "n2"],
        shortcuts,
        notes,
    )
    assert order == ["n1", "s1", "n2"]
