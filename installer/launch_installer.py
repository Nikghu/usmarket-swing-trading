import runpy
import sys
from pathlib import Path

# Ensure the project root (parent of this file's directory) is on sys.path
# so that "installer" is importable as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

runpy.run_module("installer", run_name="__main__", alter_sys=True)
