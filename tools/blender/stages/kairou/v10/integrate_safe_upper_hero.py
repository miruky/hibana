#!/usr/bin/env python3
"""Combine a collision-aligned Kairou base with a vetted upper-hero GLB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


PROVENANCE_KEYS = (
    "hibanaStage",
    "hibanaLod",
    "hibanaMegaLandmarks",
    "hibanaCityArchetype",
    "hibanaDenseBuildingTarget",
    "hibanaGeneratorVersion",
    "hibanaGeneratorSha",
    "hibanaPlacementSource",
    "hibanaPlacementSolverSha256",
    "hibanaStageWorldCatalogSha256",
    "hibanaKairouCollisionBackedVisualBuildingCount",
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--upper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), required=True)
    return parser.parse_args(argv)


def import_meshes(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    return [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]


def triangles(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def main() -> None:
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    base = import_meshes(args.base)
    if not base:
        raise RuntimeError("base GLB contains no mesh")
    provenance = {
        key: base[0][key]
        for key in PROVENANCE_KEYS
        if key in base[0]
    }
    upper = import_meshes(args.upper)
    if len(upper) < 4:
        raise RuntimeError(f"expected at least four upper hero/district meshes, found {len(upper)}")
    for obj in upper:
        for key, value in provenance.items():
            if key not in {"hibanaLod"}:
                obj[key] = value
        obj["hibanaStage"] = "kairou"
        obj["hibanaLod"] = args.lod
        obj["hibanaKairouArtRevision"] = "v10.1-collision-aligned"
        obj["hibanaKairouContactSkeleton"] = "current-release-legacy-boxspec"
        obj["hibanaFacadeDarkCardCount"] = 0

    selected = base + upper
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base[0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_tangents=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )
    report = {
        "schemaVersion": 1,
        "status": "PASS",
        "base": str(args.base),
        "upper": str(args.upper),
        "output": str(args.output),
        "lod": args.lod,
        "baseObjectCount": len(base),
        "upperObjectCount": len(upper),
        "baseTriangles": sum(triangles(obj) for obj in base),
        "upperTriangles": sum(triangles(obj) for obj in upper),
        "totalTriangles": sum(triangles(obj) for obj in selected),
        "materialCount": len({material.name for obj in selected for material in obj.data.materials if material}),
        "provenance": provenance,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
