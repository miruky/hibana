#!/usr/bin/env python3
"""Build only Kairou's collision-aligned dense-world skeleton in isolation.

Run with Blender in background mode.  Generated files must stay below either
the ignored repository work directory or ``/private/tmp/hibana-blender``.  The
helper therefore cannot truncate the production manifest or overwrite a
public GLB while an art candidate is still under review.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import bpy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args, _ = parser.parse_known_args(os.sys.argv[os.sys.argv.index("--") + 1:])
    repo = args.repo.expanduser().resolve()
    output = args.output_root.expanduser().resolve()
    source = repo / "tools/blender/build_all_stages.py"
    layout = repo / "tools/blender/generated/stage-layouts.json"
    if not source.is_file() or not layout.is_file():
        raise RuntimeError("invalid Hibana repository")
    allowed_roots = (
        Path("/private/tmp/hibana-blender").resolve(),
        (repo / "tools/blender/work").resolve(),
    )
    if not any(output == root or root in output.parents for root in allowed_roots):
        raise RuntimeError(f"output root must stay below one of {allowed_roots}: {output}")
    public = (repo / "public").resolve()
    if output == public or public in output.parents:
        raise RuntimeError(f"candidate builder must never write below public/: {output}")
    output.mkdir(parents=True, exist_ok=True)
    namespace = {
        "__name__": "hibana_kairou_collision_skeleton",
        "args": {
            "project_root": str(repo),
            "layout_path": str(layout),
            "output_dir": str(output / "stages"),
            "work_dir": str(output / "work"),
            "render_dir": str(output / "renders"),
            "progress_path": str(output / "progress.json"),
            "manifest_path": str(output / "manifest.json"),
            "stage_ids": ["kairou"],
        },
    }
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    timer = namespace["build_timer"]
    if bpy.app.timers.is_registered(timer):
        bpy.app.timers.unregister(timer)
    while namespace["STATE"]["index"] < len(namespace["STAGES"]):
        timer()
        status = bpy.context.scene.get("hibanaBuildStatus", "")
        if isinstance(status, str) and status.startswith("error:"):
            raise RuntimeError(status)
    timer()  # complete progress and isolated manifest


if __name__ == "__main__":
    main()
