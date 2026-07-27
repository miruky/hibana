#!/usr/bin/env python3
"""Extract only collision-safe upper landmark art from an approved V10 GLB."""

from __future__ import annotations

import argparse
import bmesh
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


GROUPS = {
    "MeridianSanctuary": {
        "id": "kairou-meridian-hypostyle-sanctuary",
        "runtimeTranslation": (-11.5, 0.0, 79.665),
    },
    "WindcrownObservatory": {
        "id": "kairou-windcrown-caravan-observatory",
        "runtimeTranslation": (-11.5, 0.0, 83.18),
    },
    "DetailOverlay": {
        "id": "kairou-district-upper",
        "runtimeTranslation": (-11.5, 0.0, 81.4225),
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), required=True)
    parser.add_argument("--minimum-height", type=float, default=7.0)
    parser.add_argument("--district-minimum-height", type=float, default=14.0)
    parser.add_argument("--include-supported-district", action="store_true")
    parser.add_argument("--decimate-ratio", type=float, default=1.0)
    return parser.parse_args(argv)


def bake_world_transform(obj: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    # glTF's Y-up conversion is represented by an import parent. Detach before
    # resetting the matrix or that conversion is applied a second time on
    # export (the classic exploded-assembly failure this recipe must prevent).
    obj.parent = None
    obj.data.transform(world)
    obj.matrix_world = Matrix.Identity(4)
    obj.data.update()


def triangulated_face_count(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def runtime_bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    values = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    runtime = [(value.x, value.z, -value.y) for value in values]
    return {
        "minXYZ": [min(value[index] for value in runtime) for index in range(3)],
        "maxXYZ": [max(value[index] for value in runtime) for index in range(3)],
    }


def component_supported(
    component: set,
    collision_boxes: list[dict],
    minimum_height: float,
    require_box_support: bool,
) -> bool:
    runtime = [(vertex.co.x, vertex.co.z, -vertex.co.y) for vertex in component]
    x0, x1 = min(value[0] for value in runtime), max(value[0] for value in runtime)
    y0, y1 = min(value[1] for value in runtime), max(value[1] for value in runtime)
    z0, z1 = min(value[2] for value in runtime), max(value[2] for value in runtime)
    if y0 < minimum_height - 1e-6:
        return False
    if not require_box_support:
        return True
    centre_x, centre_z = (x0 + x1) * 0.5, (z0 + z1) * 0.5
    # Real geometry beyond the 300 m playable square is horizon mass. It must
    # be well above the player band and cannot become reachable cover.
    if abs(centre_x) > 150.0 or abs(centre_z) > 150.0:
        return y0 >= max(24.0, minimum_height)
    component_area = max(0.04, (x1 - x0) * (z1 - z0))
    for box in collision_boxes:
        bx0, bx1 = box["x"] - box["w"] * 0.5, box["x"] + box["w"] * 0.5
        bz0, bz1 = box["z"] - box["d"] * 0.5, box["z"] + box["d"] * 0.5
        overlap_x = max(0.0, min(x1, bx1) - max(x0, bx0))
        overlap_z = max(0.0, min(z1, bz1) - max(z0, bz0))
        overlap_ratio = overlap_x * overlap_z / component_area
        centre_supported = (
            bx0 - 1.25 <= centre_x <= bx1 + 1.25
            and bz0 - 1.25 <= centre_z <= bz1 + 1.25
        )
        box_top = box["y"] + box["h"] * 0.5
        vertical_contact = y0 <= box_top + 2.0 and y1 >= box_top - 0.35
        if vertical_contact and (centre_supported or overlap_ratio >= 0.20):
            return True
    return False


def strip_below_height(
    obj: bpy.types.Object,
    minimum_height: float,
    collision_boxes: list[dict],
    require_box_support: bool,
) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # The source atlas mesh duplicates vertices at hard-normal and UV seams.
    # Weld position-identical copies before finding connected components, then
    # retain only complete components whose *entire* geometry clears the safe
    # height. Cropping individual vertices would create floating half-roofs.
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.00001)
    unseen = set(bm.verts)
    doomed = []
    kept_components = 0
    rejected_components = 0
    while unseen:
        seed = unseen.pop()
        component = {seed}
        stack = [seed]
        while stack:
            vertex = stack.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    component.add(other)
                    stack.append(other)
        if not component_supported(
            component,
            collision_boxes,
            minimum_height,
            require_box_support,
        ):
            doomed.extend(component)
            rejected_components += 1
        else:
            kept_components += 1
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    orphaned = [vertex for vertex in bm.verts if not vertex.link_faces]
    if orphaned:
        bmesh.ops.delete(bm, geom=orphaned, context="VERTS")
    if bm.faces:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "keptConnectedComponents": kept_components,
        "rejectedConnectedComponents": rejected_components,
    }


def load_collision_boxes(path: Path) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    stage = next(item for item in document["stages"] if item["id"] == "kairou")
    return [
        box for box in stage["boxes"]
        if not box.get("ghost") and not box.get("legacyHorizon")
    ]


def apply_decimate(obj: bpy.types.Object, ratio: float) -> None:
    if ratio >= 0.999:
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new("KairouV10_1UpperLodBudget", "DECIMATE")
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def main() -> None:
    args = parse_args()
    if not 0.05 <= args.decimate_ratio <= 1.0:
        raise ValueError("--decimate-ratio must be between 0.05 and 1.0")
    collision_boxes = load_collision_boxes(args.layouts.resolve())
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(args.source.resolve()))
    created = [obj for obj in bpy.data.objects if obj not in before]
    kept: list[bpy.types.Object] = []
    report_objects = []
    for obj in created:
        if obj.type != "MESH":
            continue
        match = next((token for token in GROUPS if token in obj.name), None)
        # Closed-frond foliage is intentionally excluded: cutting away a palm
        # trunk would leave a visibly floating canopy even though it is above
        # the player collision band.
        if (
            match is None
            or "Foliage" in obj.name
            or (match == "DetailOverlay" and not args.include_supported_district)
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        bake_world_transform(obj)
        triangles_before = triangulated_face_count(obj)
        minimum_height = (
            args.district_minimum_height
            if match == "DetailOverlay"
            else args.minimum_height
        )
        dx, dy, dz = GROUPS[match]["runtimeTranslation"]
        # Bake the calibrated runtime-frame offset into vertex data. Keeping a
        # non-zero object transform here makes Blender's modifier/export paths
        # disagree about whether glTF's root-axis conversion is already baked.
        obj.data.transform(Matrix.Translation(Vector((dx, -dz, dy))))
        obj.matrix_world = Matrix.Identity(4)
        obj.data.update()
        component_report = strip_below_height(
            obj,
            minimum_height,
            collision_boxes,
            require_box_support=match == "DetailOverlay",
        )
        if not obj.data.polygons:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        apply_decimate(obj, args.decimate_ratio)
        obj.name = f"SM_Kairou_V10_1_{match}_Upper_LOD{args.lod}_{'Metal' if 'Metal' in obj.name else 'Dielectric'}"
        obj["hibanaStage"] = "kairou"
        obj["hibanaLod"] = args.lod
        obj["hibanaMaterial"] = "dielectric"
        obj["hibanaRole"] = "overhead-detail"
        if match == "DetailOverlay":
            obj["hibanaDistrictId"] = GROUPS[match]["id"]
        else:
            obj["hibanaLandmarkId"] = GROUPS[match]["id"]
        obj["hibanaKairouArtRevision"] = "v10.1-collision-aligned"
        obj["hibanaKairouSafeDetailMinHeightM"] = minimum_height
        obj["hibanaFacadeGlassPaneCount"] = 0
        obj["hibanaFacadeDarkCardCount"] = 0
        obj["hibanaFacadeGlassNearCoplanarCount"] = 0
        obj["hibanaFacadeGlassFloatingCount"] = 0
        obj["hibanaFacadeGlassEmbeddedCount"] = 0
        bounds = runtime_bounds(obj)
        if bounds["minXYZ"][1] < minimum_height - 0.001:
            raise RuntimeError(f"{obj.name}: retained geometry below safe height: {bounds}")
        triangles_after = triangulated_face_count(obj)
        report_objects.append({
            "name": obj.name,
            "landmarkId": GROUPS[match]["id"],
            "trianglesBeforeCrop": triangles_before,
            "trianglesAfterCropAndLod": triangles_after,
            **component_report,
            "runtimeBounds": bounds,
        })
        kept.append(obj)
    for token in ("MeridianSanctuary", "WindcrownObservatory"):
        if not any(token in obj.name for obj in kept):
            raise RuntimeError(f"safe extraction removed the complete {token} identity")
    if len(kept) < 4:
        raise RuntimeError(f"expected at least four connected upper meshes, found {len(kept)}")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in kept:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = kept[0]
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
        "source": str(args.source),
        "output": str(args.output),
        "lod": args.lod,
        "minimumHeightM": args.minimum_height,
        "districtMinimumHeightM": args.district_minimum_height,
        "decimateRatio": args.decimate_ratio,
        "objects": report_objects,
        "totalTriangles": sum(item["trianglesAfterCropAndLod"] for item in report_objects),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
