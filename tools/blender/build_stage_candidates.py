#!/usr/bin/env python3
"""Build isolated Hibana stage candidates from the canonical solver layout.

Run this file with Blender in background mode.  It deliberately refuses to
write below ``public/`` so a visual candidate cannot become a release merely
because its placement solver passed.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import bpy


def blender_argv() -> list[str]:
    argv = os.sys.argv
    return argv[argv.index("--") + 1 :] if "--" in argv else []


def is_below(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--stage", action="append", dest="stages")
    args = parser.parse_args(blender_argv())

    repo = args.repo.expanduser().resolve()
    layouts = args.layouts.expanduser().resolve()
    output = args.output_root.expanduser().resolve()
    source = repo / "tools/blender/build_all_stages.py"
    public = (repo / "public").resolve()
    allowed = (
        Path("/private/tmp/hibana-blender").resolve(),
        (repo / "tools/blender/work").resolve(),
    )
    if not source.is_file() or not layouts.is_file():
        raise RuntimeError("Hibana generator or canonical layout is missing")
    if not any(is_below(output, root) for root in allowed):
        raise RuntimeError(f"output-root must stay below one of {allowed}: {output}")
    if is_below(output, public):
        raise RuntimeError(f"candidate builder must never write below public/: {output}")

    layout_document = json.loads(layouts.read_text(encoding="utf-8"))
    if layout_document.get("placementSource") != "canonical-solver-v2-authoring":
        raise RuntimeError("candidate builder requires canonical-solver-v2-authoring layouts")
    layout_stage_ids = {
        stage.get("id") for stage in layout_document.get("stages", [])
        if isinstance(stage, dict)
    }
    selected = args.stages or sorted(stage_id for stage_id in layout_stage_ids if stage_id)
    unknown = sorted(set(selected) - layout_stage_ids)
    if unknown:
        raise RuntimeError(f"unknown stage IDs: {unknown}")

    output.mkdir(parents=True, exist_ok=True)
    namespace = {
        "__name__": "hibana_isolated_stage_candidates",
        "args": {
            "project_root": str(repo),
            "layout_path": str(layouts),
            "output_dir": str(output / "stages"),
            "work_dir": str(output / "work"),
            "render_dir": str(output / "renders"),
            "progress_path": str(output / "progress.json"),
            "manifest_path": str(output / "manifest.json"),
            "stage_ids": selected,
        },
    }
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    timer = namespace["build_timer"]
    if bpy.app.timers.is_registered(timer):
        bpy.app.timers.unregister(timer)
    while namespace["STATE"]["index"] < len(namespace["STAGES"]):
        timer()
        progress = json.loads((output / "progress.json").read_text(encoding="utf-8"))
        print(
            f"[hibana-stage-candidate] {progress.get('current', 0)}/"
            f"{progress.get('total', len(selected))} {progress.get('stage', '')}",
            flush=True,
        )
        if progress.get("status") == "error":
            raise RuntimeError(str(progress.get("error", "candidate build failed")))
    timer()
    print(json.dumps({
        "ok": True,
        "placementSource": layout_document["placementSource"],
        "stages": selected,
        "outputRoot": str(output),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
