"""Root conftest — adds us_swing/src to sys.path for src-layout imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
