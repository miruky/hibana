"""Capture only Blender's own window for article-ready progress records.

Run through the localhost Blender bridge.  This deliberately avoids macOS
desktop capture so other applications and Spaces can never enter the image.
"""

import bpy
from pathlib import Path


EXEC_ARGS = globals().get("args", {})
if EXEC_ARGS.get("project_root"):
    PROJECT = Path(EXEC_ARGS["project_root"]).expanduser().resolve()
elif globals().get("__file__"):
    PROJECT = Path(__file__).resolve().parents[2]
else:
    raise RuntimeError("project_root is required when Blender executes the script through MCP")
DEFAULT_PATH = PROJECT / "tools/blender/screenshots/blender-progress.png"
output = Path(EXEC_ARGS.get("output", str(DEFAULT_PATH))).resolve()
allowed = (PROJECT / "tools/blender/screenshots").resolve()
if allowed not in output.parents:
    raise RuntimeError(f"Blender screenshot must remain below {allowed}")
output.parent.mkdir(parents=True, exist_ok=True)

try:
    bpy.ops.screen.screenshot(filepath=str(output), full=True)
except TypeError:
    bpy.ops.screen.screenshot(filepath=str(output))

result = {"output": str(output), "exists": output.exists(), "bytes": output.stat().st_size if output.exists() else 0}
