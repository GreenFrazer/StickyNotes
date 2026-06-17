# Dock Visual & Size Review

A comparative design review of StickyNotes dock dimensions and visual treatment against common dock/sidebar apps, with prioritized recommendations.

**Status:** P0 implemented (Jun 2026). macOS validated. Windows screenshot pending.

## Implementation todos

- [x] Remove file labels from 44×44 rail tiles; rely on tooltip + hover popup; reduce icon to 24px
- [x] Add `#tagChip` stylesheet in `theme.py` matching dark-rail design tokens
- [x] ~~Prototype THICK 52–48px~~ — **deprioritized:** keep 56px per product direction
- [x] Reduce separator density (one hairline before exit group, not between every action group)
- [ ] Windows validation screenshot when available (pinned `.lnk` file shortcut)

---

## Platform validation

### macOS (confirmed Jun 2026)

Screenshot: right-edge dock, sparse state (one note, no file shortcuts).

| Finding | Result |
|---------|--------|
| `#tagChip` unstyled — bright blue Qt default "All" button | **Fixed** — dark-rail pill chip in `tag_chip_stylesheet()` |
| Sparse scroll gap between note tiles and action stack | **Confirmed** — expected with few pinned notes |
| Semi-transparent rounded dark chrome (11px radius) | **Confirmed** — polished, macOS-adjacent |
| 56px rail width | **Confirmed acceptable** — not bulky; keep at 56px |
| Action separators between emoji groups | **Fixed** — one hairline before exit group only |
| Colour-coded note tiles | **Confirmed** — strong differentiator at this width |
| File label clipping | **Fixed** — icon-only tiles; full name in tooltip + popup |

**Post-implementation tests:** full suite passing (`python3 -m pytest -q`).

### Windows (pending)

When on laptop, capture dock with at least one pinned `.lnk` / app shortcut to validate shell icons in icon-only tiles.

---

## Peer research (web + doc cross-check)

### Icon rails — closest peers (fixed width)

| App | Rail width | Icon size | Labels | Resize model |
|-----|-----------|-----------|--------|--------------|
| **VS Code Activity Bar** | 48px (36px compact) | 24px | Tooltip only | `workbench.activityBar.compact` preset |
| **Obsidian ribbon** | 44px (`--ribbon-width`) | ~18–22px | Tooltip only | CSS hacks only |
| **Material 3 Navigation Rail** | 80dp | 24dp | Label below icon | Fixed |
| **StickyNotes** | **56px** | **24px** file / 20px action | **Tooltip only** | Fixed |

**Takeaway:** Icon rails are fixed width. StickyNotes now matches the icon-only + tooltip pattern.

### Content panels — different paradigm

| App | Width | Resize |
|-----|-------|--------|
| OneNote dock-to-desktop | 250–350px | Drag-resize |
| Obsidian file tree | 150–300px | Drag-resize |
| Win11 Copilot dock | ~300px+ | Drag-resize |
| Start11 / Seelen vertical taskbar | 48–100px | Taskbar mods |

**Decision:** Keep **THICK = 56**. Option B (wide preset 56→72) only if users request inline file names.

---

## Your dock today

From [`stickynotes/ui/dock.py`](../../stickynotes/ui/dock.py) and [`stickynotes/theme.py`](../../stickynotes/theme.py):

| Element | Value |
|---------|-------|
| Dock thickness (`THICK`) | **56px** |
| Hidden peek strip (`TRIGGER`) | **4px** |
| Outer padding / spacing | **4px** margins, **4px** gaps |
| Note / file / action tiles | **44×44px** |
| Action glyph size | **20px** emoji |
| File icon (indicator) | **24px** pixmap, icon-only |
| Border radius (dock chrome) | **11px** |
| Border radius (tiles) | **8px** |
| Tag chips | Dark-rail pill (`tag_chip_stylesheet`) |

---

## Assessment summary

| Dimension | Verdict |
|-----------|---------|
| **Overall width (56px)** | **Keep** |
| **Tile size (44×44)** | Correct |
| **File shortcut labels in rail** | **Fixed** — icon-only |
| **Tag filter chip styling** | **Fixed** |
| **Action button stack** | **Improved** — fewer separators |
| **Colour-coded note tiles** | Strong differentiator |
| **Semi-transparent rounded chrome** | Polished; keep |

---

## Remaining polish (P2, optional)

1. **Wide preset** (56 → 72 in Settings) for inline file labels
2. **Pin actions to bottom** with max-height scroll for note/file tiles
3. **Active-state accent** on hovered file tile (2px left border)

---

## Reference constants

```
THICK = 56
TILE = 44
FILE_ICON = 24
GLYPH = 20
OUTER_PAD = 4
```

Any `THICK` change must update geometry tests in `tests/test_dock.py`.
