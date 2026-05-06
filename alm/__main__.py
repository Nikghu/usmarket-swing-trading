"""
Launch the ALM viewer:  python -m alm
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `alm` is importable
_repo_root = str(Path(__file__).resolve().parents[1])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from PyQt6.QtWidgets import QApplication

from alm.main_window import ALMMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ALM Viewer")

    window = ALMMainWindow()  # No docs_root — will prompt to browse
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
