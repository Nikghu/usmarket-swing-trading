"""
Module: MD-GUI-001.001.M01 — Theme
Dark Catppuccin Mocha colour palette and global QSS stylesheet.
"""
from __future__ import annotations


class C:
    """Colour token constants."""
    BG       = "#1e1e2e"
    SURFACE  = "#181825"
    OVERLAY  = "#313244"
    OVERLAY2 = "#45475a"
    TEXT     = "#cdd6f4"
    SUBTEXT  = "#bac2de"
    MUTED    = "#7f849c"

    GREEN    = "#a6e3a1"
    RED      = "#f38ba8"
    YELLOW   = "#f9e2af"
    ORANGE   = "#fab387"
    BLUE     = "#89b4fa"
    TEAL     = "#94e2d5"
    MAUVE    = "#cba6f7"

    # Position state colours
    STATE_NEW             = "#7f849c"
    STATE_PARTIAL_ENTRY   = "#f9e2af"
    STATE_OPEN            = "#a6e3a1"
    STATE_PARTIAL_EXIT    = "#fab387"
    STATE_CLOSED          = "#6c7086"

    # P&L cell background (dark tint)
    PNL_POS_BG = "#1a3326"
    PNL_NEG_BG = "#331a1a"

    # Standard widget heights — use these everywhere; never hardcode px values
    BTN_H    = 28   # all QPushButton variants
    BTN_H_SM = 26   # compact buttons in group-card / dialog headers
    INPUT_H  = 28   # QLineEdit / QSpinBox / QDoubleSpinBox / QComboBox / QTimeEdit


STATE_COLORS: dict[str, str] = {
    "NEW":           C.STATE_NEW,
    "PARTIAL_ENTRY": C.STATE_PARTIAL_ENTRY,
    "OPEN":          C.STATE_OPEN,
    "PARTIAL_EXIT":  C.STATE_PARTIAL_EXIT,
    "CLOSED":        C.STATE_CLOSED,
}

QSS = f"""
/* ═══════════════════════════════════════════════════════════
   GLOBAL  — Catppuccin Mocha · TIKR / Finviz terminal style
   ═══════════════════════════════════════════════════════════ */
QMainWindow, QDialog, QWidget {{
    background: {C.BG};
    color: {C.TEXT};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}}

/* ── Compact frameless title bar ─────────────────────────── */
QWidget#title_bar {{
    background: #11111b;
    border-bottom: 1px solid {C.OVERLAY};
}}
QLabel#top_brand {{
    color: {C.BLUE};
    font-size: 9pt;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 0 4px 0 8px;
}}
QLabel#user_chip  {{ color: {C.TEXT};   font-size: 8pt; padding: 0 4px; }}

/* ── Horizontal tab nav (inside title bar) ────────────────── */
QPushButton#tab_btn {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {C.MUTED};
    font-size: 8pt;
    padding: 0 10px;
    min-height: 38px;
    max-height: 38px;
    outline: none;
}}
QPushButton#tab_btn:hover {{
    color: {C.TEXT};
    background: {C.OVERLAY}22;
    outline: none;
}}
QPushButton#tab_btn:checked {{
    color: {C.TEXT};
    background: {C.OVERLAY2}55;
    border-bottom: none;
    border-radius: 4px;
    font-weight: bold;
    outline: none;
}}
QPushButton#tab_btn:focus {{
    outline: none;
}}
QPushButton#tab_btn:checked:focus {{
    outline: none;
}}


/* ── Accent underline below title bar ─────────────────────── */
QFrame#accent_line {{ color: {C.TEXT}; max-height: 2px; }}

/* ── Dashboard QTabWidget ─────────────────────────────────────── */
QTabWidget#dash_tabs::pane {{
    border: 1px solid {C.OVERLAY};
    border-radius: 4px;
    background: {C.BG};
}}
QTabWidget#dash_tabs > QTabBar::tab {{
    background: {C.SURFACE};
    color: {C.MUTED};
    font-size: 9pt;
    padding: 6px 16px;
    border: 1px solid {C.OVERLAY};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}}
QTabWidget#dash_tabs > QTabBar::tab:selected {{
    background: {C.BG};
    color: {C.BLUE};
    border-bottom: 2px solid {C.BLUE};
    font-weight: bold;
}}
QTabWidget#dash_tabs > QTabBar::tab:hover:!selected {{
    color: {C.TEXT};
    background: {C.OVERLAY};
}}

/* ── Stat cards (TIKR KPI style) ─────────────────────────── */
QFrame#stat_card {{
    background: {C.SURFACE};
    border: 1px solid {C.OVERLAY};
    border-radius: 8px;
    padding: 10px;
}}
QFrame#stat_card:hover {{
    border: 1px solid {C.OVERLAY2};
}}
QWidget#stat_card_inner {{
    background: transparent;
}}
QWidget#stat_card_inner QLabel {{
    background: transparent;
}}

/* ── Screener chip / badge row ────────────────────────────── */
QFrame#filter_chip {{
    background: {C.OVERLAY};
    border: 1px solid {C.OVERLAY2};
    border-radius: 12px;
    padding: 2px 10px;
}}
QFrame#filter_chip[active="true"] {{
    background: #1a2d45;
    border: 1px solid {C.BLUE};
}}

/* ── Mode/status badges ───────────────────────────────────── */
QLabel#mode_live {{
    background: #331a1a;
    color: {C.RED};
    border: 1px solid {C.RED};
    border-radius: 8px;
    padding: 2px 10px;
    font-weight: bold;
    font-size: 8pt;
}}
QLabel#mode_paper {{
    background: #1a2d45;
    color: {C.BLUE};
    border: 1px solid {C.BLUE};
    border-radius: 8px;
    padding: 2px 10px;
    font-weight: bold;
    font-size: 8pt;
}}
QLabel#can_enter_yes {{
    background: #1a3326;
    color: {C.GREEN};
    border: 1px solid {C.GREEN};
    border-radius: 6px;
    padding: 4px 10px;
    font-weight: bold;
    font-size: 9pt;
}}
QLabel#can_enter_no {{
    background: #331a1a;
    color: {C.RED};
    border: 1px solid {C.RED};
    border-radius: 6px;
    padding: 4px 10px;
    font-weight: bold;
    font-size: 9pt;
}}

/* ── (legacy) Tab widget — kept for any residual usage ────── */
QTabWidget::pane {{
    border: 1px solid {C.OVERLAY};
    background: {C.BG};
}}
QTabBar::tab {{
    background: {C.SURFACE};
    color: {C.MUTED};
    padding: 8px 22px;
    border: 1px solid {C.OVERLAY};
    border-bottom: none;
    margin-right: 2px;
    font-size: 9pt;
}}
QTabBar::tab:selected {{
    background: {C.BG};
    color: {C.TEXT};
    border-bottom: 2px solid {C.BLUE};
}}
QTabBar::tab:hover:!selected {{
    background: {C.OVERLAY};
    color: {C.TEXT};
}}
QTableView, QTreeView {{
    background: {C.SURFACE};
    alternate-background-color: {C.BG};
    color: {C.TEXT};
    gridline-color: {C.OVERLAY};
    border: 1px solid {C.OVERLAY};
    border-radius: 4px;
    selection-background-color: {C.OVERLAY2};
    selection-color: {C.TEXT};
    outline: none;
}}
QTableView::item, QTreeView::item {{
    padding: 3px 6px;
}}
QHeaderView::section {{
    background: {C.OVERLAY};
    color: {C.SUBTEXT};
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {C.OVERLAY2};
    border-bottom: 1px solid {C.OVERLAY2};
    font-weight: bold;
    font-size: 8pt;
    text-transform: uppercase;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit {{
    background: {C.OVERLAY};
    border: 1px solid {C.OVERLAY2};
    border-radius: 4px;
    color: {C.TEXT};
    padding: 0 8px;
    min-height: {C.INPUT_H}px;
    max-height: {C.INPUT_H}px;
    outline: none;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTimeEdit:focus {{
    border: 1px solid {C.BLUE};
    outline: none;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {C.OVERLAY};
    selection-background-color: {C.OVERLAY2};
    color: {C.TEXT};
    border: 1px solid {C.OVERLAY2};
}}
QPushButton {{
    background: {C.OVERLAY};
    border: 1px solid {C.OVERLAY2};
    border-radius: 4px;
    color: {C.TEXT};
    padding: 0 16px;
    font-size: 9pt;
    min-height: {C.BTN_H}px;
    max-height: {C.BTN_H}px;
    outline: none;
}}
QPushButton:focus {{
    outline: none;
}}
QPushButton:hover {{
    background: {C.OVERLAY2};
    border: 1px solid {C.BLUE};
}}
QPushButton:pressed {{
    background: {C.OVERLAY2};
}}
QPushButton:disabled {{
    color: {C.MUTED};
    background: {C.SURFACE};
    border-color: {C.OVERLAY};
}}
QPushButton#buy_btn {{
    background: #1a3326;
    border: 1px solid {C.GREEN};
    color: {C.GREEN};
    font-weight: bold;
}}
QPushButton#buy_btn:hover {{ background: #223d2e; }}
QPushButton#close_btn {{
    background: #331a1a;
    border: 1px solid {C.RED};
    color: {C.RED};
}}
QPushButton#close_btn:hover {{ background: #3d2222; }}
QPushButton#run_btn {{
    background: #1a2d45;
    border: 1px solid {C.BLUE};
    color: {C.BLUE};
    font-weight: bold;
    padding: 0 24px;
    min-height: {C.BTN_H}px;
    max-height: {C.BTN_H}px;
}}
QPushButton#run_btn:hover {{ background: #1e3658; }}
QPushButton#run_btn:disabled {{ color: {C.MUTED}; background: {C.OVERLAY}44; border-color: {C.OVERLAY}; }}
QPushButton#add_btn {{
    background: #2a1a3a;
    border: 1px solid {C.MAUVE};
    color: {C.MAUVE};
    padding: 0 8px;
    font-size: 9pt;
}}
QPushButton#add_btn:hover {{ background: #33214d; }}
QPushButton#add_btn:disabled {{ color: {C.MUTED}; background: {C.OVERLAY}44; border-color: {C.OVERLAY}; }}
QPushButton#danger_btn {{
    background: #331a1a;
    border: 1px solid {C.RED};
    color: {C.RED};
}}
QPushButton#danger_btn:hover {{ background: #3d2222; }}

/* ── Reusable named colour variants (standard 28 px height) ── */
QPushButton#btn_green {{
    background: #1a3d2a;
    color: {C.GREEN};
    border: 1px solid {C.GREEN};
    border-radius: 4px;
    padding: 0 16px;
}}
QPushButton#btn_green:hover {{ background: #1e4a32; }}
QPushButton#btn_blue {{
    background: #1a2d45;
    color: {C.BLUE};
    border: 1px solid {C.BLUE};
    border-radius: 4px;
    font-size: 9pt;
}}
QPushButton#btn_blue:hover {{ background: #1e3558; }}

/* ── Compact variants ({C.BTN_H_SM} px — group-card header controls) ─ */
QPushButton#btn_add_screener {{
    background: #1a3d2a;
    color: {C.GREEN};
    border: 1px solid {C.GREEN}66;
    border-radius: 4px;
    font-size: 8pt;
    padding: 0 10px;
    min-height: {C.BTN_H_SM}px;
    max-height: {C.BTN_H_SM}px;
}}
QPushButton#btn_add_screener:hover {{ background: #1e4a32; border-color: {C.GREEN}; }}
QPushButton#btn_configure {{
    background: transparent;
    color: {C.SUBTEXT};
    border: 1px solid {C.OVERLAY2};
    border-radius: 4px;
    font-size: 8pt;
    padding: 0 8px;
    min-height: {C.BTN_H_SM}px;
    max-height: {C.BTN_H_SM}px;
}}
QPushButton#btn_configure:hover:enabled {{ color: {C.BLUE}; border-color: {C.BLUE}; }}
QPushButton#btn_configure:disabled {{ color: {C.OVERLAY2}; border-color: {C.OVERLAY}; }}
QPushButton#btn_remove {{
    background: transparent;
    color: {C.MUTED};
    border: 1px solid {C.OVERLAY2};
    border-radius: 4px;
    font-size: 8pt;
    padding: 0 8px;
    min-height: {C.BTN_H_SM}px;
    max-height: {C.BTN_H_SM}px;
}}
QPushButton#btn_remove:hover {{ color: {C.RED}; border-color: {C.RED}; }}

/* ── Square nav arrow buttons (toolbar date navigation) ────── */
QPushButton#btn_nav {{
    background: {C.OVERLAY};
    color: {C.TEXT};
    border: 1px solid {C.OVERLAY2};
    border-radius: 4px;
    font-size: 12pt;
    padding: 0;
}}
QPushButton#btn_nav:hover {{ background: {C.OVERLAY2}; border-color: {C.BLUE}; }}
QPushButton#btn_nav:disabled {{ color: {C.MUTED}; background: {C.OVERLAY}44; border-color: {C.OVERLAY}; }}

QProgressBar {{
    background: {C.SURFACE};
    border: 1px solid {C.OVERLAY};
    border-radius: 3px;
    max-height: 10px;
    text-align: center;
    font-size: 7pt;
    color: {C.TEXT};
}}
QProgressBar::chunk {{
    background: {C.BLUE};
    border-radius: 3px;
}}
QGroupBox {{
    border: 1px solid {C.OVERLAY};
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 6px;
    color: {C.SUBTEXT};
    font-weight: bold;
    font-size: 9pt;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    background: {C.BG};
    padding: 0 4px;
}}
QCheckBox {{
    color: {C.TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {C.OVERLAY2};
    border-radius: 3px;
    background: {C.SURFACE};
}}
QCheckBox::indicator:checked {{
    background: {C.BLUE};
    border-color: {C.BLUE};
}}
QStatusBar {{
    background: {C.SURFACE};
    color: {C.MUTED};
    border-top: 1px solid {C.OVERLAY};
    font-size: 9pt;
    min-height: 28px;
}}
QStatusBar::item {{ border: none; }}
QSplitter::handle {{
    background: {C.OVERLAY};
    width: 2px;
}}
QScrollBar:vertical {{
    background: {C.SURFACE};
    width: 10px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.OVERLAY2};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C.SURFACE};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {C.OVERLAY2};
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QTextEdit {{
    background: {C.SURFACE};
    color: {C.TEXT};
    border: 1px solid {C.OVERLAY};
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 9pt;
    outline: none;
}}
QListWidget {{
    background: {C.SURFACE};
    border: 1px solid {C.OVERLAY};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item:focus {{
    outline: none;
    border: none;
}}
QLabel {{ color: {C.TEXT}; }}
QToolTip {{
    background: {C.OVERLAY};
    color: {C.TEXT};
    border: 1px solid {C.OVERLAY2};
    padding: 4px;
}}
"""
