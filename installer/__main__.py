"""Entry point: python -m installer"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from installer.main_window import InstallerMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Installer Generator")
    app.setApplicationVersion("1.0.0")
    w = InstallerMainWindow(app)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
