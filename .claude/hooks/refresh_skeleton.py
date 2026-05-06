"""Post-edit hook: refresh skeleton cache when a us_swing src .py file changes."""
import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

src_marker = os.path.join("us_swing", "src", "us_swing")
if not (file_path.endswith(".py") and src_marker in file_path):
    sys.exit(0)

tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "us_swing", "tools"))
env = {**os.environ, "PYTHONPATH": tools_dir}

subprocess.run(
    [sys.executable, "-m", "skeleton_extractor", "refresh"],
    cwd=tools_dir,
    env=env,
    capture_output=True,
)
