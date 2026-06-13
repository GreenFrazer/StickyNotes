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
SNAP_THRESHOLD = 20
DATE_FMT = "%d %b %Y, %H:%M"


def dialog_stylesheet(dark: bool = False) -> str:
    """Stylesheet for settings and other modal dialogs."""
    if dark:
        return """
            QDialog{background:#2d2d2d;color:#e8e8e8;}
            QLabel{color:#e8e8e8;background:transparent;}
            QGroupBox{color:#e8e8e8;font-weight:bold;padding-top:14px;border:1px solid #555;border-radius:6px;margin-top:8px;}
            QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}
            QRadioButton{color:#e8e8e8;}
            QCheckBox{color:#e8e8e8;}
            QPushButton{background:#0078D4;color:white;border:none;border-radius:6px;padding:6px 18px;font-size:13px;}
            QPushButton:hover{background:#005FA3;}
            #cancelBtn{background:#555;color:#eee;}
            #cancelBtn:hover{background:#666;}
        """
    return """
        QDialog{background:#f5f5f5;color:#222;}
        QLabel{color:#222;background:transparent;}
        QGroupBox{color:#222;font-weight:bold;padding-top:14px;border:1px solid #ccc;border-radius:6px;margin-top:8px;}
        QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}
        QRadioButton{color:#222;}
        QCheckBox{color:#222;}
        QPushButton{background:#0078D4;color:white;border:none;border-radius:6px;padding:6px 18px;font-size:13px;}
        QPushButton:hover{background:#005FA3;}
        #cancelBtn{background:#ddd;color:#333;}
        #cancelBtn:hover{background:#ccc;}
    """
