"""Dark theme — shared QSS palette for the installer tool."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

_QSS = """
QWidget {
    background: #1e1e1e;
    color: #d4d4d4;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    color: #9cdcfe;
}
QTabWidget::pane {
    border: 1px solid #3c3c3c;
}
QTabBar::tab {
    background: #2d2d2d;
    color: #cccccc;
    padding: 6px 16px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #ffffff;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 3px 6px;
}
QLineEdit:focus, QPlainTextEdit:focus {
    border-color: #007acc;
}
QComboBox QAbstractItemView {
    background: #252526;
    selection-background-color: #094771;
}
QPushButton {
    background: #0e639c;
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 5px 14px;
}
QPushButton:hover  { background: #1177bb; }
QPushButton:pressed { background: #0a4d7a; }
QPushButton:disabled { background: #3c3c3c; color: #6a6a6a; }
QCheckBox::indicator { width: 14px; height: 14px; }
QSplitter::handle { background: #3c3c3c; }
QStatusBar { background: #007acc; color: #ffffff; font-size: 12px; }
QLabel { color: #9cdcfe; }
QFormLayout QLabel { color: #d4d4d4; }
"""


def apply_dark_theme(app: QApplication) -> None:
    app.setStyleSheet(_QSS)
