from __future__ import annotations

"""Read-only inventory for the private Kouwan R9.5 Blender candidate."""

import json
import os
from pathlib import Path

import bpy


ROOT = Path(
    os.environ.get(
        "HIBANA_KOUWAN_R10_ROOT",
        Path(__file__).resolve().parents[3] / "work/kouwan-r10",
    )
).expanduser().resolve()
REPO = Path(__file__).resolve().parents[5]
PUBLIC = (REPO / "public").resolve()
WORK = (REPO / "tools/blender/work").resolve()
if ROOT == PUBLIC or PUBLIC in ROOT.parents:
    raise RuntimeError(f"private candidate must never write below public/: {ROOT}")
if REPO in ROOT.parents and ROOT != WORK and WORK not in ROOT.parents:
    raise RuntimeError(f"repository-local output must stay below ignored {WORK}: {ROOT}")
OUT = ROOT / "r10-r9-5-scene-inspection.json"


def world_bounds(obj: bpy.types.Object) -> dict[str, list[float]] | None:
    if obj.type != "MESH" or not obj.bound_box:
        return None
    corners = [obj.matrix_world @ __import__("mathutils").Vector(corner) for corner in obj.bound_box]
    return {
        axis: [
            round(min(getattr(corner, axis) for corner in corners), 4),
            round(max(getattr(corner, axis) for corner in corners), 4),
        ]
        for axis in ("x", "y", "z")
    }


scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == "MESH"]
visible = [obj for obj in meshes if not obj.hide_render]
for obj in visible:
    obj.data.calc_loop_triangles()

prefixes = (
    "HB_R7_SHIP",
    "HB_V4_SHIPLIFT",
    "HB_R8",
    "HB_R9",
    "HB_V5",
    "HB_TOWER",
)

interesting = []
for obj in sorted(visible, key=lambda item: item.name):
    if obj.name.startswith(prefixes) or any(token in obj.name for token in ("WAREHOUSE", "WATER", "DOCK", "CRANE", "TOWER", "WINDOW", "GLASS")):
        interesting.append(
            {
                "name": obj.name,
                "collections": sorted(collection.name for collection in obj.users_collection),
                "triangles": len(obj.data.loop_triangles),
                "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
                "bounds": world_bounds(obj),
                "sourcePass": obj.get("hibanaSourcePass"),
                "artOnly": obj.get("hibanaArtOnly"),
                "walkBlocker": obj.get("hbWalkBlocker"),
            }
        )

payload = {
    "blend": bpy.data.filepath,
    "collections": [
        {
            "name": collection.name,
            "objects": len(collection.objects),
            "children": sorted(child.name for child in collection.children),
        }
        for collection in sorted(bpy.data.collections, key=lambda item: item.name)
    ],
    "objectCount": len(scene.objects),
    "meshCount": len(meshes),
    "visibleMeshCount": len(visible),
    "visibleTrianglesEvaluated": sum(len(obj.data.loop_triangles) for obj in visible),
    "materials": [
        {
            "name": material.name,
            "users": material.users,
            "blendMethod": getattr(material, "surface_render_method", None),
        }
        for material in sorted(bpy.data.materials, key=lambda item: item.name)
    ],
    "images": [
        {
            "name": image.name,
            "filepath": image.filepath,
            "packed": image.packed_file is not None,
            "source": image.source,
        }
        for image in sorted(bpy.data.images, key=lambda item: item.name)
    ],
    "interestingObjects": interesting,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: payload[key] for key in ("objectCount", "meshCount", "visibleMeshCount", "visibleTrianglesEvaluated")}, indent=2))
print(f"inspection={OUT}")
