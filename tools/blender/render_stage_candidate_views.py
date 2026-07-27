#!/usr/bin/env python3
"""Render deterministic first-person and audit views from a stage candidate blend."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def load_nakaniwa_contract():
    module_path = Path(__file__).resolve().parent / "stage_kits/nakaniwa_reference_a18.py"
    spec = importlib.util.spec_from_file_location("hibana_nakaniwa_render_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Nakaniwa render contract: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def argv_after_separator() -> list[str]:
    argv = os.sys.argv
    return argv[argv.index("--") + 1 :] if "--" in argv else []


def runtime_point(x: float, y: float, z: float) -> Vector:
    return Vector((x, -z, y))


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def count_scene_ray_crossings(scene: bpy.types.Scene, origin: Vector, direction: Vector,
                              max_distance: float = 1000.0) -> int:
    """Count closed-surface crossings for a deterministic point-in-mesh test."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    direction = direction.normalized()
    cursor = origin.copy()
    travelled = 0.0
    crossings = 0
    while travelled < max_distance and crossings < 512:
        hit, location, _normal, _face, _obj, _matrix = scene.ray_cast(
            depsgraph, cursor, direction, distance=max_distance - travelled
        )
        if not hit:
            break
        crossings += 1
        cursor = location + direction * 0.01
        travelled = (cursor - origin).length
    return crossings


def preflight_camera(scene: bpy.types.Scene, location: Vector, target: Vector) -> dict:
    """Reject cameras embedded in meshes or pressed against forward geometry."""
    parity_direction = Vector((1.0, 0.173, 0.097)).normalized()
    crossings = count_scene_ray_crossings(scene, location, parity_direction)
    inside = crossings % 2 == 1
    forward = target - location
    distance = forward.length
    depsgraph = bpy.context.evaluated_depsgraph_get()
    hit, hit_location, _normal, _face, hit_object, _matrix = scene.ray_cast(
        depsgraph, location, forward.normalized(), distance=max(0.001, distance)
    )
    forward_clearance = (hit_location - location).length if hit else distance
    passed = not inside and forward_clearance >= 4.0
    return {
        "passed": passed,
        "insideClosedMesh": inside,
        "parityCrossings": crossings,
        "forwardClearanceM": round(float(forward_clearance), 4),
        "firstForwardHit": hit_object.name if hit and hit_object else None,
    }


def dual_hero_visibility(scene: bpy.types.Scene, camera: bpy.types.Object,
                         landmarks: list[dict]) -> dict:
    """Require both hero meshes to own a visible, in-frame ray sample."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    visible_ids = []
    evidence = []
    for landmark in landmarks:
        landmark_id = landmark["id"]
        samples = []
        for x_fraction in (-0.22, 0.0, 0.22):
            for y_fraction in (0.48, 0.68, 0.84):
                target = runtime_point(
                    landmark["cx"] + landmark["width"] * x_fraction,
                    landmark["height"] * y_fraction,
                    landmark["cz"],
                )
                ndc = world_to_camera_view(scene, camera, target)
                in_frame = 0.0 <= ndc.x <= 1.0 and 0.0 <= ndc.y <= 1.0 and ndc.z > 0.0
                direction = target - camera.location
                hit = False
                owner = None
                if in_frame and direction.length > 0.001:
                    did_hit, _location, _normal, _face, hit_object, _matrix = scene.ray_cast(
                        depsgraph, camera.location, direction.normalized(), distance=direction.length
                    )
                    if did_hit and hit_object:
                        owner = hit_object.get("hibanaLandmarkId")
                        hit = owner == landmark_id
                samples.append({
                    "inFrame": in_frame,
                    "hitsHero": hit,
                    "firstOwner": owner,
                    "ndc": [round(float(ndc.x), 4), round(float(ndc.y), 4)],
                })
        visible = any(sample["hitsHero"] for sample in samples)
        if visible:
            visible_ids.append(landmark_id)
        evidence.append({"id": landmark_id, "visible": visible, "samples": samples})
    return {
        "passed": len(visible_ids) == len(landmarks),
        "visibleHeroIds": visible_ids,
        "heroes": evidence,
    }


def landmark_frame_metrics(scene: bpy.types.Scene, camera: bpy.types.Object,
                           landmarks: list[dict], accepted_range: tuple[float, float]) -> dict:
    """Measure actual exported hero mesh coverage in the fixed camera."""
    metrics = []
    for landmark in landmarks:
        projected = []
        for obj in scene.objects:
            if obj.get("hibanaLandmarkId") != landmark["id"] or obj.type != "MESH":
                continue
            for local_corner in obj.bound_box:
                ndc = world_to_camera_view(scene, camera, obj.matrix_world @ Vector(local_corner))
                if ndc.z > 0.0:
                    projected.append((float(ndc.x), float(ndc.y)))
        if not projected:
            metrics.append({"id": landmark["id"], "passed": False, "reason": "no-owned-mesh"})
            continue
        xs = [point[0] for point in projected]
        ys = [point[1] for point in projected]
        raw_height = max(ys) - min(ys)
        visible_height = max(0.0, min(1.0, max(ys)) - max(0.0, min(ys)))
        intersects_frame = max(xs) >= 0.0 and min(xs) <= 1.0 and max(ys) >= 0.0 and min(ys) <= 1.0
        passed = accepted_range[0] <= visible_height <= accepted_range[1] and intersects_frame
        metrics.append({
            "id": landmark["id"],
            "passed": passed,
            "rawFrameHeightRatio": round(raw_height, 4),
            "visibleFrameHeightRatio": round(visible_height, 4),
            "frameBounds": [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)],
        })
    return {"passed": all(item["passed"] for item in metrics), "heroes": metrics}


def threshold_opaque_obstruction(scene: bpy.types.Scene, camera: bpy.types.Object,
                                 target_x: float, target_z: float, landmark_id: str,
                                 max_ratio: float) -> dict:
    """Trace a 7x5 player-view grid through a greenhouse route section."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    samples = []
    for x_index in range(7):
        x = target_x - 3.2 + x_index * (6.4 / 6.0)
        for y_index in range(5):
            y = 2.0 + y_index * 1.45
            target = runtime_point(x, y, target_z)
            direction = target - camera.location
            total_distance = direction.length
            direction.normalize()
            cursor = camera.location.copy()
            travelled = 0.0
            first_opaque = None
            first_owner = None
            while travelled < total_distance - 0.35:
                hit, location, _normal, _face, hit_object, _matrix = scene.ray_cast(
                    depsgraph, cursor, direction, distance=total_distance - travelled - 0.25
                )
                if not hit or hit_object is None:
                    break
                material_names = [material.name.lower() for material in hit_object.data.materials if material]
                transparent = any("glass" in name or "water" in name for name in material_names)
                if not transparent:
                    first_opaque = hit_object.name
                    first_owner = hit_object.get("hibanaLandmarkId")
                    break
                cursor = location + direction * 0.03
                travelled = (cursor - camera.location).length
            samples.append({
                "x": round(x, 3), "y": round(y, 3),
                "opaque": first_opaque is not None,
                "firstOpaque": first_opaque,
                "firstOwner": first_owner,
            })
    blocked = sum(1 for sample in samples if sample["opaque"])
    ratio = blocked / len(samples)
    return {
        "passed": ratio < max_ratio,
        "opaqueObstructionRatio": round(ratio, 4),
        "blockedSamples": blocked,
        "sampleCount": len(samples),
        "landmarkId": landmark_id,
        "samples": samples,
    }


def is_below(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv_after_separator())

    layouts = args.layouts.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    allowed = (Path("/private/tmp/hibana-blender").resolve(),)
    if not any(is_below(output, root) for root in allowed):
        raise RuntimeError(f"output-dir must stay below {allowed}: {output}")
    document = json.loads(layouts.read_text(encoding="utf-8"))
    if document.get("placementSource") != "canonical-solver-v2-authoring":
        raise RuntimeError("render audit requires canonical solver layouts")
    stage = next((item for item in document["stages"] if item["id"] == args.stage), None)
    if stage is None:
        raise RuntimeError(f"unknown stage {args.stage}")
    if len(stage.get("landmarkPlacements", [])) != 2:
        raise RuntimeError(f"{args.stage}: exact two landmarks required")
    output.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    camera = scene.camera
    if camera is None:
        data = bpy.data.cameras.new(f"HB_{args.stage}_AUDIT_CAMERA_DATA")
        camera = bpy.data.objects.new(f"HB_{args.stage}_AUDIT_CAMERA", data)
        scene.collection.objects.link(camera)
        scene.camera = camera
    camera.data.sensor_width = 36
    camera.data.lens = 34
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    spawn = stage["playerSpawns"][0]
    landmarks = stage["landmarkPlacements"]
    half = stage["size"] / 2
    nakaniwa_contract = load_nakaniwa_contract() if args.stage == "nakaniwa" else None
    views: list[tuple[str, Vector, Vector, float]] = []
    for index, landmark in enumerate(landmarks):
        target = runtime_point(landmark["cx"], min(landmark["height"] * 0.42, 24.0), landmark["cz"])
        views.append((
            f"01-eye165-spawn-landmark-{index}",
            runtime_point(spawn[0], 1.65, spawn[2]),
            target,
            35.0,
        ))
        start = landmark["approach"]["start"]
        entrance = landmark["entrance"]
        dx, dz = entrance[0] - start[0], entrance[1] - start[1]
        length = max(0.001, math.hypot(dx, dz))
        # Use a player-height three-quarter view rather than aiming steeply at
        # the lintel from directly beneath it.  The previous audit camera hid
        # the entire hero behind a common gateway and could not judge facade
        # depth, support chains or the skyline that a player actually reads.
        side = -1.0 if index == 0 else 1.0
        px = start[0] - dx / length * 16.0 + (-dz / length) * 5.5 * side
        pz = start[1] - dz / length * 16.0 + (dx / length) * 5.5 * side
        views.append((
            f"02-eye165-approach-landmark-{index}",
            runtime_point(px, 1.65, pz),
            runtime_point(entrance[0], min(5.0, landmark["height"] * 0.14), entrance[1]),
            35.0,
        ))

    views.extend((
        (
            "03-eye165-central-street-north",
            runtime_point(0, 1.65, half * 0.22),
            runtime_point(0, 5.0, -half * 0.34),
            31.0,
        ),
        (
            "04-eye165-central-street-south",
            runtime_point(0, 1.65, -half * 0.22),
            runtime_point(0, 5.0, half * 0.34),
            31.0,
        ),
        (
            "05-aerial-overview",
            runtime_point(half * 0.70, half * 0.46, half * 0.70),
            runtime_point(0, 3.0, 0),
            42.0,
        ),
        (
            "06-aerial-opposite",
            runtime_point(-half * 0.70, half * 0.42, -half * 0.70),
            runtime_point(0, 3.0, 0),
            42.0,
        ),
    ))

    if args.stage == "nakaniwa":
        # Fixed A18 reference evidence.  These views are intentionally at
        # player height and include the threshold/interior relationship that a
        # distant overview cannot judge.
        views.extend((
            (
                "00-eye165-reference-dual-r11",
                runtime_point(*nakaniwa_contract.REFERENCE_DUAL_CAMERA["location"]),
                runtime_point(*nakaniwa_contract.REFERENCE_DUAL_CAMERA["target"]),
                nakaniwa_contract.REFERENCE_DUAL_CAMERA["lensMm"],
            ),
            (
                "07-eye165-palace-water-court",
                runtime_point(-70.0, 1.65, 10.0),
                runtime_point(-60.0, 21.0, -66.0),
                19.0,
            ),
            (
                "08-eye165-conservatory-threshold",
                runtime_point(*nakaniwa_contract.CONSERVATORY_THRESHOLD_CAMERA["location"]),
                runtime_point(*nakaniwa_contract.CONSERVATORY_THRESHOLD_CAMERA["target"]),
                nakaniwa_contract.CONSERVATORY_THRESHOLD_CAMERA["lensMm"],
            ),
            (
                "09-eye165-conservatory-interior",
                runtime_point(*nakaniwa_contract.CONSERVATORY_INTERIOR_CAMERA["location"]),
                runtime_point(*nakaniwa_contract.CONSERVATORY_INTERIOR_CAMERA["target"]),
                nakaniwa_contract.CONSERVATORY_INTERIOR_CAMERA["lensMm"],
            ),
            (
                "10-eye165-canal-route-human-scale",
                runtime_point(10.5, 1.65, -96.0),
                runtime_point(18.0, 5.2, 78.0),
                35.0,
            ),
        ))

    rendered = []
    perspective_preflight = []
    camera.data.type = "PERSP"
    for label, location, target, lens in views:
        camera.location = location
        camera.data.lens = lens
        point_camera(camera, target)
        preflight = preflight_camera(scene, location, target)
        if "dual-hero" in label:
            dual = dual_hero_visibility(scene, camera, landmarks)
            preflight["dualHeroVisibility"] = dual
            preflight["passed"] = preflight["passed"] and dual["passed"]
        if label == "00-eye165-reference-dual-r11":
            dual = dual_hero_visibility(scene, camera, landmarks)
            coverage = landmark_frame_metrics(
                scene,
                camera,
                landmarks,
                tuple(nakaniwa_contract.REFERENCE_DUAL_CAMERA["acceptedFrameHeightRatio"]),
            )
            preflight["dualHeroVisibility"] = dual
            preflight["heroFrameCoverage"] = coverage
            preflight["passed"] = preflight["passed"] and dual["passed"] and coverage["passed"]
        if label == "08-eye165-conservatory-threshold":
            threshold = threshold_opaque_obstruction(
                scene,
                camera,
                nakaniwa_contract.CONSERVATORY_THRESHOLD_CAMERA["target"][0],
                nakaniwa_contract.CONSERVATORY_THRESHOLD_CAMERA["target"][2],
                landmarks[1]["id"],
                nakaniwa_contract.CONSERVATORY_THRESHOLD_CAMERA["maxOpaqueObstructionRatio"],
            )
            preflight["thresholdOpaqueObstruction"] = threshold
            preflight["passed"] = preflight["passed"] and threshold["passed"]
        if label == "09-eye165-conservatory-interior":
            interior = threshold_opaque_obstruction(
                scene,
                camera,
                nakaniwa_contract.CONSERVATORY_INTERIOR_CAMERA["target"][0],
                nakaniwa_contract.CONSERVATORY_INTERIOR_CAMERA["target"][2],
                landmarks[1]["id"],
                nakaniwa_contract.CONSERVATORY_INTERIOR_CAMERA["maxOpaqueObstructionRatio"],
            )
            preflight["interiorOpaqueObstruction"] = interior
            preflight["passed"] = preflight["passed"] and interior["passed"]
        perspective_preflight.append({"label": label, **preflight})
        if not preflight["passed"]:
            continue
        destination = output / f"{args.stage}-{label}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        rendered.append(str(destination))

    orthographic_views = (
        ("ortho-front", runtime_point(0, 24, -420), runtime_point(0, 18, 0)),
        ("ortho-back", runtime_point(0, 24, 420), runtime_point(0, 18, 0)),
        ("ortho-left", runtime_point(-420, 24, 0), runtime_point(0, 18, 0)),
        ("ortho-right", runtime_point(420, 24, 0), runtime_point(0, 18, 0)),
        ("ortho-top", runtime_point(0, 420, 0), runtime_point(0, 0, 0)),
        ("ortho-bottom", runtime_point(0, -420, 0), runtime_point(0, 0, 0)),
    )
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = stage["size"] * 1.08
    camera.data.clip_start = 0.1
    camera.data.clip_end = 1000.0
    for label, location, target in orthographic_views:
        camera.location = location
        point_camera(camera, target)
        destination = output / f"{args.stage}-{label}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        rendered.append(str(destination))
    report = {
        "schemaVersion": 1,
        "stage": args.stage,
        "placementSource": document["placementSource"],
        "viewCount": len(rendered),
        "perspectiveViewCount": len(views),
        "acceptedPerspectiveViewCount": sum(
            1 for item in perspective_preflight if item["passed"]
        ),
        "rejectedPerspectiveViewCount": sum(
            1 for item in perspective_preflight if not item["passed"]
        ),
        "orthographicViewCount": len(orthographic_views),
        "perspectivePreflight": perspective_preflight,
        "renders": rendered,
    }
    (output / f"{args.stage}-render-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
