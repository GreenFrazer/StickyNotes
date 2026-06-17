"""Colour themes and styling constants."""

NOTE_COLOURS = {
    "yellow": "#FDFD96",
    "blue": "#A7C7E7",
    "green": "#77DD77",
    "pink": "#FFB7CE",
    "purple": "#D8B4FE",
    "orange": "#FFD580",
    "white": "#F5F5F5",
}

TITLE_BAR_COLOURS = {
    "yellow": "#E8E85C",
    "blue": "#7BA7D7",
    "green": "#4CBB4C",
    "pink": "#FF8FB2",
    "purple": "#B78FE0",
    "orange": "#F0B84A",
    "white": "#E0E0E0",
}

DEFAULT_NOTE_W = 240
DEFAULT_NOTE_H = 180
# #checklistWidget::item { min-height:24px; padding:2px 0; }
CHECKLIST_ITEM_MIN_H = 28
# #checklistWidget { padding:8px 6px; }
CHECKLIST_WIDGET_PAD_V = 16
# #addChecklistItemBtn { padding:2px 8px 8px 14px; } + FONT_CAPTION line height
CHECKLIST_ADD_BTN_MIN_H = 27
SNAP_THRESHOLD = 20
DATE_FMT = "%d %b %Y, %H:%M"

# DESIGN.md tokens
PRIMARY = "#0066cc"
PRIMARY_FOCUS = "#0071e3"
PRIMARY_HOVER = "#005aad"
INK = "#1d1d1f"
INK_MUTED = "#7a7a7a"
BODY_MUTED = "#cccccc"
INK_MUTED_80 = "#333333"
CANVAS_PARCHMENT = "#f5f5f7"
SURFACE_TILE_1 = "#272729"
SURFACE_TILE_3 = "#252527"
ON_DARK = "#ffffff"
HAIRLINE = "#e0e0e0"
CHIP_TRANSLUCENT = "rgba(210, 210, 215, 0.64)"

FONT_FAMILY = '"SF Pro Text", system-ui, -apple-system, sans-serif'
FONT_BODY = 17
FONT_CAPTION = 14
FONT_FINE = 12
RADIUS_MD = 11
RADIUS_DOCK = 11
RADIUS_SM = 8


def _font(size: int) -> str:
    return f"font-family:{FONT_FAMILY};font-size:{size}px;"


def tag_chip_stylesheet(*, dark_rail: bool = True) -> str:
    if dark_rail:
        fg = ON_DARK
        bg = "rgba(255,255,255,0.12)"
        border = "rgba(255,255,255,0.18)"
        hover_bg = "rgba(255,255,255,0.20)"
        checked_bg = "rgba(0,113,227,0.35)"
        checked_border = PRIMARY_FOCUS
    else:
        fg = INK_MUTED_80
        bg = "rgba(255,255,255,0.55)"
        border = "rgba(0,0,0,0.12)"
        hover_bg = "rgba(255,255,255,0.75)"
        checked_bg = "rgba(0,113,227,0.15)"
        checked_border = PRIMARY_FOCUS
    return f"""
        #tagChip {{
            {_font(FONT_FINE)}
            color:{fg};
            background:{bg};
            border:1px solid {border};
            border-radius:9999px;
            padding:4px 10px;
            min-height:22px;
        }}
        #tagChip:hover {{
            background:{hover_bg};
        }}
        QPushButton#tagChip:checked {{
            background:{checked_bg};
            border:1px solid {checked_border};
            color:{fg};
        }}
    """


def dock_stylesheet(*, dark: bool = False, drag_over: bool = False) -> str:
    if drag_over:
        bg = "rgba(45,70,45,0.88)" if dark else "rgba(50,80,50,0.85)"
    elif dark:
        bg = "rgba(37,37,39,0.88)"
    else:
        bg = "rgba(39,39,41,0.82)"
    return f"""
        DockWidget {{
            background:{bg};
            border:1px solid rgba(255,255,255,0.08);
            border-radius:{RADIUS_DOCK}px;
        }}
        #dockBtn {{
            background:rgba(255,255,255,0.10);
            border:none;
            border-radius:{RADIUS_SM}px;
            color:{ON_DARK};
            font-size:20px;
            padding:0;
        }}
        #dockBtn:hover {{ background:rgba(255,255,255,0.22); }}
        #dockBtn:pressed {{ background:rgba(255,255,255,0.35); }}
        #dockSep {{ color:rgba(255,255,255,0.12); background:rgba(255,255,255,0.12); }}
        {tag_chip_stylesheet()}
    """


def dock_resize_handle_stylesheet() -> str:
    return """
        #dockResizeHandle {
            background: transparent;
        }
        #dockResizeHandle:hover {
            background: rgba(255,255,255,0.15);
        }
    """


def dock_scroll_stylesheet() -> str:
    return """
        QScrollArea{background:transparent;border:none;}
        QScrollBar:vertical{background:transparent;width:6px;margin:2px 0;}
        QScrollBar::handle:vertical{background:rgba(255,255,255,0.2);border-radius:3px;min-height:20px;}
        QScrollBar::handle:vertical:hover{background:rgba(255,255,255,0.35);}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        QScrollBar:horizontal{background:transparent;height:6px;margin:0 2px;}
        QScrollBar::handle:horizontal{background:rgba(255,255,255,0.2);border-radius:3px;min-width:20px;}
        QScrollBar::handle:horizontal:hover{background:rgba(255,255,255,0.35);}
        QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0;}
    """


def title_button_stylesheet(*, dark_chrome: bool = False, size: int = 24) -> str:
    fg = ON_DARK if dark_chrome else INK_MUTED_80
    hover = "rgba(255,255,255,0.18)" if dark_chrome else "rgba(255,255,255,0.45)"
    fs = max(12, int(size * 0.54))
    return (
        f"QPushButton{{background:transparent;border:none;border-radius:6px;color:{fg};"
        f"font-size:{fs}px;padding:0;min-width:{size}px;max-width:{size}px;"
        f"min-height:{size}px;max-height:{size}px;}}"
        f"QPushButton:hover{{background:{hover};}}"
    )


def copy_button_stylesheet(*, size: int = 22, dark_chrome: bool = False) -> str:
    fg = ON_DARK if dark_chrome else INK_MUTED_80
    hover = "rgba(255,255,255,0.18)" if dark_chrome else "rgba(255,255,255,0.8)"
    base = "rgba(255,255,255,0.12)" if dark_chrome else "rgba(255,255,255,0.65)"
    fs = max(10, int(size * 0.55))
    return (
        f"QPushButton{{background:{base};border:none;border-radius:6px;color:{fg};"
        f"font-size:{fs}px;min-width:{size}px;max-width:{size}px;"
        f"min-height:{size}px;max-height:{size}px;}}"
        f"QPushButton:hover{{background:{hover};}}"
    )


def colour_dot_stylesheet(hex_colour: str, *, selected: bool) -> str:
    if selected:
        border = f"2px solid {PRIMARY_FOCUS}"
    else:
        border = f"1px solid {HAIRLINE}"
    hover = "" if selected else f"QPushButton:hover{{border:2px solid {INK_MUTED};}}"
    return (
        f"QPushButton{{background:{hex_colour};border:{border};border-radius:8px;}}"
        f"{hover}"
    )


def colour_dot_frame_stylesheet(hex_colour: str, *, selected: bool) -> str:
    border = f"2px solid {PRIMARY_FOCUS}" if selected else f"1px solid {HAIRLINE}"
    return f"background:{hex_colour};border:{border};border-radius:6px;"


def note_window_stylesheet(bg: str, tb: str) -> str:
    """Unified single-colour note chrome — header/body/footer share one palette."""
    title_top_r = RADIUS_MD
    title_divider = "rgba(0,0,0,0.06)"
    return f"""
        NoteWindow {{
            background:{bg};
            border:1px solid {tb};
            border-radius:{RADIUS_MD}px;
        }}
        #titleBar {{
            background:{tb};
            border-top-left-radius:{title_top_r}px;
            border-top-right-radius:{title_top_r}px;
            border-bottom:1px solid {title_divider};
        }}
        #noteEditor {{
            background:{bg};
            border:none;
            {_font(FONT_BODY)}
            padding:8px 6px;
            color:{INK};
            selection-background-color:{tb};
        }}
        #checklistBody {{
            background:{bg};
            border:none;
        }}
        #checklistWidget {{
            background:{bg};
            border:none;
            outline:none;
            {_font(FONT_BODY)}
            padding:8px 6px;
            color:{INK};
        }}
        #checklistWidget::viewport {{
            background:{bg};
        }}
        #checklistWidget::item {{
            min-height:24px;
            padding:2px 0;
            color:{INK};
            background:transparent;
        }}
        #checklistWidget::item:selected {{
            background:{tb};
            color:{INK};
        }}
        #checklistWidget::item:selected:active {{
            background:{tb};
            color:{INK};
        }}
        #checklistWidget QLineEdit {{
            background:{bg};
            border:none;
            {_font(FONT_BODY)}
            color:{INK};
            padding:0;
            selection-background-color:{tb};
        }}
        #checklistWidget::indicator {{
            width:18px;
            height:18px;
        }}
        #addChecklistItemBtn {{
            background:{bg};
            border:none;
            outline:none;
            {_font(FONT_CAPTION)}
            color:{INK_MUTED};
            text-align:left;
            padding:2px 8px 8px 14px;
        }}
        #addChecklistItemBtn:hover {{
            background:{bg};
            color:{INK};
        }}
        #addChecklistItemBtn:pressed {{
            background:{bg};
            color:{INK};
        }}
        #addChecklistItemBtn:focus {{
            background:{bg};
            border:none;
            outline:none;
        }}
        #colourRow {{ background:{bg}; }}
        #metaRow {{
            background:{bg};
            border-bottom-left-radius:{RADIUS_MD}px;
            border-bottom-right-radius:{RADIUS_MD}px;
        }}
        #tsLabel {{
            {_font(FONT_FINE)}
            color:{INK_MUTED};
            font-style:italic;
            padding:2px 8px 4px 8px;
            background:transparent;
        }}
        QSizeGrip {{ background:transparent; width:16px; height:16px; }}
        {tag_chip_stylesheet(dark_rail=False)}
    """


def note_popup_stylesheet(bg: str, tb: str) -> str:
    return f"""
        DockNotePopup {{
            background:{bg};
            border:1px solid {tb};
            border-radius:{RADIUS_MD}px;
        }}
        #pTitleBar {{
            background:{tb};
            border-top-left-radius:{RADIUS_MD}px;
            border-top-right-radius:{RADIUS_MD}px;
            border-bottom:1px solid rgba(0,0,0,0.06);
        }}
        #pText {{
            {_font(FONT_CAPTION)}
            color:{INK};
            padding:8px 6px;
            background:{bg};
        }}
        #pColourRow {{ background:{bg}; }}
        #pTs {{
            {_font(FONT_FINE)}
            color:{INK_MUTED};
            font-style:italic;
            padding:2px 8px 4px 8px;
            background:transparent;
        }}
    """


def file_popup_stylesheet(*, missing: bool = False) -> str:
    border = INK_MUTED if missing else HAIRLINE
    hint = INK_MUTED if missing else INK_MUTED
    return f"""
        DockFilePopup {{
            background:{CANVAS_PARCHMENT};
            border:1px solid {border};
            border-radius:{RADIUS_MD}px;
        }}
        #fpTitle {{
            {_font(FONT_CAPTION)}
            font-weight:600;
            color:{INK};
            background:transparent;
        }}
        #fpPath {{
            {_font(FONT_FINE)}
            color:{INK_MUTED_80};
            background:transparent;
        }}
        #fpHint {{
            {_font(FONT_FINE)}
            color:{hint};
            font-style:italic;
            background:transparent;
        }}
    """


def dock_note_indicator_stylesheet(
    bg: str,
    tb: str,
    *,
    visible: bool = True,
    overdue: bool = False,
) -> str:
    border = "#E53935" if overdue else tb
    dot = (
        "DockNoteIndicator::after { }"
        if not visible
        else ""
    )
    return f"""
        DockNoteIndicator {{
            background:{bg};
            border:2px solid {border};
            border-radius:{RADIUS_SM}px;
        }}
        DockNoteIndicator:hover {{
            border:2px solid rgba(255,255,255,0.35);
            background:{tb};
        }}
        {dot}
    """


def dock_file_indicator_stylesheet(*, exists: bool) -> str:
    if exists:
        bg = "rgba(255,255,255,0.20)"
        border = "rgba(255,255,255,0.28)"
        hover_bg = "rgba(255,255,255,0.32)"
    else:
        bg = "rgba(255,80,80,0.18)"
        border = "rgba(255,120,120,0.35)"
        hover_bg = "rgba(255,80,80,0.28)"
    return f"""
        DockFileIndicator {{
            background:{bg};
            border:1px solid {border};
            border-radius:{RADIUS_SM}px;
        }}
        DockFileIndicator:hover {{
            border:1px solid rgba(255,255,255,0.35);
            background:{hover_bg};
        }}
    """


def dock_file_label_stylesheet(*, badge: bool = True) -> str:
    if badge:
        return f"{_font(FONT_CAPTION)}font-weight:600;color:{ON_DARK};background:transparent;"
    return f"{_font(FONT_FINE)}color:{BODY_MUTED};background:transparent;"


def dock_file_icon_stylesheet() -> str:
    return "background:transparent;"


def dock_preview_label_stylesheet() -> str:
    return f"{_font(FONT_FINE)}color:{INK_MUTED_80};background:transparent;"


def menu_stylesheet(*, dark: bool = False) -> str:
    if dark:
        return (
            f"QMenu{{background:#2d2d2d;color:{ON_DARK};border:1px solid #555;padding:4px;border-radius:{RADIUS_SM}px;{_font(FONT_CAPTION)}}}"
            f"QMenu::item{{padding:6px 20px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{PRIMARY};color:{ON_DARK};}}"
            f"QMenu::separator{{height:1px;background:#555;margin:4px 8px;}}"
        )
    return (
        f"QMenu{{background:#fff;color:{INK};border:1px solid {HAIRLINE};padding:4px;border-radius:{RADIUS_SM}px;{_font(FONT_CAPTION)}}}"
        f"QMenu::item{{padding:6px 20px;border-radius:4px;}}"
        f"QMenu::item:selected{{background:{PRIMARY};color:{ON_DARK};}}"
        f"QMenu::separator{{height:1px;background:{HAIRLINE};margin:4px 8px;}}"
    )


def _dialog_indicators(*, dark: bool) -> str:
    if dark:
        ring = "#888888"
        fill = "#3a3a3a"
    else:
        ring = INK_MUTED
        fill = "#ffffff"
    return f"""
            QRadioButton::indicator {{
                width:18px; height:18px;
                border:2px solid {ring};
                border-radius:10px;
                background:{fill};
            }}
            QRadioButton::indicator:checked {{
                border:5px solid {PRIMARY};
                background:{fill};
            }}
            QRadioButton::indicator:hover {{
                border-color:{PRIMARY_FOCUS};
            }}
            QCheckBox::indicator {{
                width:18px; height:18px;
                border:2px solid {ring};
                border-radius:4px;
                background:{fill};
            }}
            QCheckBox::indicator:checked {{
                border:2px solid {PRIMARY};
                background:{PRIMARY};
            }}
            QCheckBox::indicator:hover {{
                border-color:{PRIMARY_FOCUS};
            }}
        """


def dialog_stylesheet(dark: bool = False) -> str:
    indicators = _dialog_indicators(dark=dark)
    if dark:
        return f"""
            QDialog,QWidget{{background:#2d2d2d;color:#e8e8e8;{_font(FONT_BODY)}}}
            QLabel{{color:#e8e8e8;background:transparent;}}
            QGroupBox{{color:#e8e8e8;font-weight:600;padding-top:14px;border:1px solid #555;border-radius:{RADIUS_SM}px;margin-top:8px;background:transparent;}}
            QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}
            QRadioButton{{color:#e8e8e8;background:transparent;spacing:8px;}}
            QCheckBox{{color:#e8e8e8;background:transparent;spacing:8px;}}
            {indicators}
            QComboBox{{background:#3a3a3a;color:#e8e8e8;border:1px solid #555;border-radius:4px;padding:4px 8px;}}
            QComboBox QAbstractItemView{{background:#3a3a3a;color:#e8e8e8;selection-background-color:{PRIMARY};}}
            QLineEdit{{background:#3a3a3a;color:#e8e8e8;border:1px solid #555;border-radius:4px;padding:6px 8px;}}
            QListWidget{{background:#3a3a3a;color:#e8e8e8;border:1px solid #555;border-radius:4px;}}
            QPushButton{{background:{PRIMARY};color:{ON_DARK};border:none;border-radius:9999px;padding:8px 16px;{_font(FONT_CAPTION)}}}
            QPushButton:hover{{background:{PRIMARY_HOVER};}}
            #cancelBtn{{background:#555;color:#eee;border-radius:{RADIUS_SM}px;}}
            #cancelBtn:hover{{background:#666;}}
        """
    return f"""
        QDialog,QWidget{{background:{CANVAS_PARCHMENT};color:{INK};{_font(FONT_BODY)}}}
        QLabel{{color:{INK};background:transparent;}}
        QGroupBox{{color:{INK};font-weight:600;padding-top:14px;border:1px solid {HAIRLINE};border-radius:{RADIUS_SM}px;margin-top:8px;background:transparent;}}
        QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}
        QRadioButton{{color:{INK};background:transparent;spacing:8px;}}
        QCheckBox{{color:{INK};background:transparent;spacing:8px;}}
        {indicators}
        QComboBox{{background:#fff;color:{INK};border:1px solid {HAIRLINE};border-radius:4px;padding:4px 8px;}}
        QComboBox QAbstractItemView{{background:#fff;color:{INK};selection-background-color:{PRIMARY};selection-color:{ON_DARK};}}
        QLineEdit{{background:#fff;color:{INK};border:1px solid {HAIRLINE};border-radius:4px;padding:6px 8px;}}
        QListWidget{{background:#fff;color:{INK};border:1px solid {HAIRLINE};border-radius:4px;}}
        QPushButton{{background:{PRIMARY};color:{ON_DARK};border:none;border-radius:9999px;padding:8px 16px;{_font(FONT_CAPTION)}}}
        QPushButton:hover{{background:{PRIMARY_HOVER};}}
        #cancelBtn{{background:#ddd;color:{INK_MUTED_80};border-radius:{RADIUS_SM}px;}}
        #cancelBtn:hover{{background:#ccc;}}
    """
