#!/usr/bin/env python3
"""Audit a Kairou GLB against the live BoxSpec collision contract.

This gate exists because a visually successful Blender scene is not safe to
publish when the external stage hides Hibana's procedural shell.  It measures
the player-height, collision-significant surfaces of a raw (uncompressed) GLB
against the exact boxes exported from ``generateStage()`` and emits a top-down
proof image.  The script never mutates the GLB, layout, or runtime collision.

The optional ``legacy-centroid-fit`` mode is intentionally conservative.  It
centres the two hero meshes on their live landmark footprints and applies the
mean hero offset to the integrated district meshes.  If even this best-case
rigid fit fails, the candidate must not replace the procedural stage shell.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw


COMPONENT_DTYPES = {
    5121: np.dtype("<u1"),
    5123: np.dtype("<u2"),
    5125: np.dtype("<u4"),
    5126: np.dtype("<f4"),
}
TYPE_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
LANDMARK_IDS = (
    "kairou-meridian-hypostyle-sanctuary",
    "kairou-windcrown-caravan-observatory",
)


@dataclass(frozen=True)
class MeshTriangles:
    name: str
    role: str | None
    positions: np.ndarray
    triangles: np.ndarray


def read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"{path}: truncated GLB")
    magic, version, declared = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67 or version != 2 or declared != len(raw):
        raise ValueError(f"{path}: invalid GLB header")
    offset = 12
    document: dict[str, Any] | None = None
    binary = b""
    while offset + 8 <= len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        payload = raw[offset + 8:offset + 8 + length]
        offset += 8 + length
        if kind == 0x4E4F534A:
            document = json.loads(payload.decode("utf-8").rstrip(" \t\r\n\0"))
        elif kind == 0x004E4942:
            binary = payload
    if document is None or not binary:
        raise ValueError(f"{path}: JSON or BIN chunk missing")
    if "EXT_meshopt_compression" in document.get("extensionsUsed", []):
        raise ValueError("audit requires the raw, uncompressed Blender export")
    return document, binary


def accessor_array(document: dict[str, Any], binary: bytes, index: int) -> np.ndarray:
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    dtype = COMPONENT_DTYPES.get(accessor["componentType"])
    width = TYPE_COMPONENTS.get(accessor["type"])
    if dtype is None or width is None:
        raise ValueError(f"unsupported accessor {index}")
    count = int(accessor["count"])
    byte_offset = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    stride = int(view.get("byteStride", dtype.itemsize * width))
    if stride == dtype.itemsize * width:
        return np.frombuffer(binary, dtype=dtype, count=count * width, offset=byte_offset).reshape(count, width).copy()
    result = np.empty((count, width), dtype=dtype)
    for row in range(count):
        result[row] = np.frombuffer(
            binary,
            dtype=dtype,
            count=width,
            offset=byte_offset + row * stride,
        )
    return result


def node_matrix(node: dict[str, Any]) -> np.ndarray:
    if isinstance(node.get("matrix"), list):
        return np.asarray(node["matrix"], dtype=np.float64).reshape(4, 4).T
    translation = np.asarray(node.get("translation", [0.0, 0.0, 0.0]), dtype=np.float64)
    scale = np.asarray(node.get("scale", [1.0, 1.0, 1.0]), dtype=np.float64)
    x, y, z, w = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
    rotation = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rotation @ np.diag(scale)
    matrix[:3, 3] = translation
    return matrix


def load_meshes(path: Path) -> list[MeshTriangles]:
    document, binary = read_glb(path)
    meshes: list[MeshTriangles] = []
    for node in document.get("nodes", []):
        mesh_index = node.get("mesh")
        if not isinstance(mesh_index, int):
            continue
        matrix = node_matrix(node)
        name = str(node.get("name", f"mesh-{mesh_index}"))
        extras = node.get("extras") if isinstance(node.get("extras"), dict) else {}
        role_value = extras.get("hibanaMaterial") or extras.get("hibanaRole")
        role = str(role_value) if isinstance(role_value, str) else None
        for primitive_index, primitive in enumerate(document["meshes"][mesh_index].get("primitives", [])):
            position_index = primitive.get("attributes", {}).get("POSITION")
            if not isinstance(position_index, int):
                continue
            positions = accessor_array(document, binary, position_index).astype(np.float64)
            homogeneous = np.column_stack((positions, np.ones(len(positions))))
            # Avoid routing an identity transform through platform BLAS.  Some
            # Accelerate builds emit spurious overflow warnings for this very
            # large but finite matrix multiply even though every source value
            # and the resulting bounds are valid.
            if np.array_equal(matrix, np.eye(4, dtype=np.float64)):
                positions = positions.copy()
            else:
                positions = (homogeneous @ matrix.T)[:, :3]
            if isinstance(primitive.get("indices"), int):
                indices = accessor_array(document, binary, primitive["indices"]).reshape(-1).astype(np.int64)
            else:
                indices = np.arange(len(positions), dtype=np.int64)
            mode = int(primitive.get("mode", 4))
            if mode != 4 or len(indices) % 3:
                raise ValueError(f"{name}: primitive {primitive_index} is not TRIANGLES")
            meshes.append(MeshTriangles(name, role, positions, indices.reshape(-1, 3)))
    return meshes


def stage_from_layout(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    stages = document.get("stages", [])
    stage = next((item for item in stages if isinstance(item, dict) and item.get("id") == "kairou"), None)
    if stage is None:
        raise ValueError(f"{path}: kairou missing")
    return stage


def mesh_bounds(meshes: Iterable[MeshTriangles], predicate) -> tuple[np.ndarray, np.ndarray]:
    values = [mesh.positions for mesh in meshes if predicate(mesh.name)]
    if not values:
        raise ValueError("no meshes matched landmark group")
    points = np.concatenate(values, axis=0)
    return points.min(axis=0), points.max(axis=0)


def collision_boxes(stage: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        box for box in stage.get("boxes", [])
        # Ghost boundary walls are still authoritative player colliders.  They
        # must count as support for the real 3D perimeter terrain that visually
        # replaces the old flat horizon, even though ray/LOS logic ignores
        # their special ``boundary`` tag.
        if not box.get("legacyHorizon")
    ]


def expanded_contains(points: np.ndarray, boxes: list[dict[str, Any]], tolerance: float) -> np.ndarray:
    supported = np.zeros(len(points), dtype=bool)
    # Vectorise across points in modest blocks to keep peak memory bounded.
    for start in range(0, len(points), 4096):
        block = points[start:start + 4096]
        hit = np.zeros(len(block), dtype=bool)
        for box in boxes:
            lo = np.array([
                box["x"] - box["w"] * 0.5 - tolerance,
                box["y"] - box["h"] * 0.5 - tolerance,
                box["z"] - box["d"] * 0.5 - tolerance,
            ])
            hi = np.array([
                box["x"] + box["w"] * 0.5 + tolerance,
                box["y"] + box["h"] * 0.5 + tolerance,
                box["z"] + box["d"] * 0.5 + tolerance,
            ])
            hit |= np.all((block >= lo) & (block <= hi), axis=1)
        supported[start:start + len(block)] = hit
    return supported


def group_for_name(name: str) -> str:
    if "MeridianSanctuary" in name:
        return "sanctuary"
    if "WindcrownObservatory" in name:
        return "observatory"
    return "district"


def fit_transforms(meshes: list[MeshTriangles], stage: dict[str, Any], mode: str) -> dict[str, np.ndarray]:
    zero = np.zeros(3, dtype=np.float64)
    if mode == "as-authored":
        return {"sanctuary": zero.copy(), "observatory": zero.copy(), "district": zero.copy()}
    placements = {item["id"]: item for item in stage["landmarkPlacements"]}
    result: dict[str, np.ndarray] = {}
    for group, token, landmark_id in (
        ("sanctuary", "MeridianSanctuary", LANDMARK_IDS[0]),
        ("observatory", "WindcrownObservatory", LANDMARK_IDS[1]),
    ):
        low, high = mesh_bounds(meshes, lambda name, value=token: value in name)
        centre = (low + high) * 0.5
        target = placements[landmark_id]
        result[group] = np.array([target["cx"] - centre[0], 0.0, target["cz"] - centre[2]])
    result["district"] = (result["sanctuary"] + result["observatory"]) * 0.5
    return result


def surface_samples(mesh: MeshTriangles, transform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    triangles = mesh.positions[mesh.triangles] + transform
    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    cross = np.cross(edge_a, edge_b)
    double_area = np.linalg.norm(cross, axis=1)
    normal_y = np.divide(cross[:, 1], double_area, out=np.zeros_like(double_area), where=double_area > 1e-12)
    centres = triangles.mean(axis=1)
    player_vertical = (
        (double_area >= 0.04)
        & (np.abs(normal_y) <= 0.58)
        & (triangles[:, :, 1].min(axis=1) <= 2.35)
        & (triangles[:, :, 1].max(axis=1) >= 0.20)
    )
    raised_floor = (
        (double_area >= 0.04)
        & (np.abs(normal_y) >= 0.68)
        & (centres[:, 1] >= 0.28)
        & (centres[:, 1] <= 2.35)
    )
    mask = player_vertical | raised_floor
    # Three deterministic samples per important face catch thin walls whose
    # centroid alone happens to land inside a nearby proxy.
    chosen = triangles[mask]
    if not len(chosen):
        return np.empty((0, 3)), np.empty((0,), dtype=np.float64)
    samples = np.concatenate((
        chosen.mean(axis=1),
        (chosen[:, 0] + chosen[:, 1]) * 0.5,
        (chosen[:, 1] + chosen[:, 2]) * 0.5,
        (chosen[:, 2] + chosen[:, 0]) * 0.5,
    ), axis=0)
    weights = np.tile(double_area[mask] * 0.5 / 4.0, 4)
    return samples, weights


def route_corridors(stage: dict[str, Any]) -> list[dict[str, Any]]:
    corridors = []
    for landmark in stage["landmarkPlacements"]:
        start = landmark["approach"]["start"]
        end = landmark["approach"]["end"]
        half = landmark["approach"]["width"] * 0.5
        corridors.append({
            "id": f"{landmark['id']}-approach",
            "minX": min(start[0], end[0]) - half,
            "maxX": max(start[0], end[0]) + half,
            "minZ": min(start[1], end[1]) - half,
            "maxZ": max(start[1], end[1]) + half,
        })
    west = stage["landmarkPlacements"][0]
    east = stage["landmarkPlacements"][1]
    corridors.append({
        "id": "principal-north-south-boulevard",
        "minX": west["cx"] + west["width"] * 0.5,
        "maxX": east["cx"] - east["width"] * 0.5,
        "minZ": -stage["size"] * 0.5,
        "maxZ": stage["size"] * 0.5,
    })
    return corridors


def in_corridor(points: np.ndarray, corridor: dict[str, Any]) -> np.ndarray:
    return (
        (points[:, 0] >= corridor["minX"])
        & (points[:, 0] <= corridor["maxX"])
        & (points[:, 2] >= corridor["minZ"])
        & (points[:, 2] <= corridor["maxZ"])
        & (points[:, 1] >= 0.2)
        & (points[:, 1] <= 2.35)
    )


def audited_samples(
    meshes: list[MeshTriangles],
    transforms: dict[str, np.ndarray],
    stage: dict[str, Any],
    boundary_tolerance: float,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    samples_by_mesh = []
    weights_by_mesh = []
    names_by_sample: list[str] = []
    for mesh in meshes:
        if "Foliage" in mesh.name or "Water" in mesh.name or "_Metal" in mesh.name:
            continue
        # The released dense-world skeleton contains terrain skirts, road
        # bevels, trim, doors, foliage and thin set dressing that are deliberately
        # visual-only.  This gate is about newly introduced major player-height
        # blockers, so only load-bearing/cover families (or an unclassified V10
        # dielectric aggregate) participate in the hard support ratio.
        if mesh.role is not None and mesh.role not in {
            "dielectric", "wall", "wall_warm", "wall_weathered", "obstacle",
        }:
            continue
        values, value_weights = surface_samples(mesh, transforms[group_for_name(mesh.name)])
        samples_by_mesh.append(values)
        weights_by_mesh.append(value_weights)
        names_by_sample.extend([mesh.name] * len(values))
    samples = np.concatenate(samples_by_mesh, axis=0) if samples_by_mesh else np.empty((0, 3))
    weights = np.concatenate(weights_by_mesh, axis=0) if weights_by_mesh else np.empty((0,))
    # Layered 3D horizon buildings deliberately sit beyond the ghost boundary.
    # They are unreachable set dressing, not player-contact surfaces.
    half = float(stage["size"]) * 0.5
    reachable = (
        (samples[:, 0] >= -half - boundary_tolerance)
        & (samples[:, 0] <= half + boundary_tolerance)
        & (samples[:, 2] >= -half - boundary_tolerance)
        & (samples[:, 2] <= half + boundary_tolerance)
    )
    return (
        samples[reachable],
        weights[reachable],
        [name for name, keep in zip(names_by_sample, reachable, strict=True) if keep],
    )


def proximity_support(points: np.ndarray, reference: np.ndarray, tolerance: float) -> np.ndarray:
    """Return points within ``tolerance`` of the approved contact skeleton."""
    if not len(points) or not len(reference):
        return np.zeros(len(points), dtype=bool)
    cell = max(tolerance, 1e-6)
    buckets: dict[tuple[int, int, int], list[np.ndarray]] = {}
    for value in reference:
        key = tuple(np.floor(value / cell).astype(np.int64))
        buckets.setdefault(key, []).append(value)
    result = np.zeros(len(points), dtype=bool)
    limit2 = tolerance * tolerance
    neighbours = tuple(
        (x, y, z)
        for x in (-1, 0, 1)
        for y in (-1, 0, 1)
        for z in (-1, 0, 1)
    )
    for index, value in enumerate(points):
        base = tuple(np.floor(value / cell).astype(np.int64))
        for dx, dy, dz in neighbours:
            candidates = buckets.get((base[0] + dx, base[1] + dy, base[2] + dz))
            if candidates is None:
                continue
            if any(float(np.dot(value - candidate, value - candidate)) <= limit2 for candidate in candidates):
                result[index] = True
                break
    return result


def draw_proof(
    output: Path,
    stage: dict[str, Any],
    meshes: list[MeshTriangles],
    transforms: dict[str, np.ndarray],
    unsupported: np.ndarray,
    corridors: list[dict[str, Any]],
) -> None:
    size = 1800
    half = stage["size"] * 0.5
    margin = 70
    scale = (size - margin * 2) / (half * 2)
    image = Image.new("RGB", (size, size), (18, 22, 28))
    draw = ImageDraw.Draw(image, "RGBA")

    def point(x: float, z: float) -> tuple[float, float]:
        return margin + (x + half) * scale, size - margin - (z + half) * scale

    for box in collision_boxes(stage):
        x0, y0 = point(box["x"] - box["w"] * 0.5, box["z"] + box["d"] * 0.5)
        x1, y1 = point(box["x"] + box["w"] * 0.5, box["z"] - box["d"] * 0.5)
        landmark = bool(box.get("landmarkId"))
        draw.rectangle((x0, y0, x1, y1), outline=(85, 190, 255, 150 if landmark else 55), width=2 if landmark else 1)
    for corridor in corridors:
        x0, y0 = point(corridor["minX"], corridor["maxZ"])
        x1, y1 = point(corridor["maxX"], corridor["minZ"])
        draw.rectangle((x0, y0, x1, y1), fill=(55, 220, 125, 24), outline=(55, 220, 125, 170), width=2)
    # Downsample vertices deterministically. Blue shows candidate geometry;
    # red shows player-height visual surfaces unsupported by a collider.
    for mesh in meshes:
        if "Foliage" in mesh.name or "Water" in mesh.name:
            continue
        values = mesh.positions + transforms[group_for_name(mesh.name)]
        stride = max(1, len(values) // 9000)
        for x, _, z in values[::stride]:
            if -half <= x <= half and -half <= z <= half:
                px, py = point(float(x), float(z))
                draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill=(245, 194, 88, 80))
    stride = max(1, len(unsupported) // 14000)
    for x, _, z in unsupported[::stride]:
        if -half <= x <= half and -half <= z <= half:
            px, py = point(float(x), float(z))
            draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 55, 60, 190))
    draw.text((margin, 22), "Kairou V10 collision overlay: cyan=live BoxSpec, amber=GLB, red=unsupported player-height surface, green=protected route", fill=(240, 245, 250, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--mode", choices=("as-authored", "legacy-centroid-fit"), default="as-authored")
    parser.add_argument("--tolerance", type=float, default=0.45)
    parser.add_argument("--baseline-glb", type=Path)
    parser.add_argument("--baseline-tolerance", type=float, default=0.12)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()

    meshes = load_meshes(args.glb)
    stage = stage_from_layout(args.layouts)
    boxes = collision_boxes(stage)
    transforms = fit_transforms(meshes, stage, args.mode)
    samples, weights, names_by_sample = audited_samples(meshes, transforms, stage, args.tolerance)
    box_supported = expanded_contains(samples, boxes, args.tolerance)
    baseline_supported = np.zeros(len(samples), dtype=bool)
    baseline_sample_count = 0
    if args.baseline_glb is not None:
        baseline_meshes = load_meshes(args.baseline_glb)
        baseline_transforms = fit_transforms(baseline_meshes, stage, "as-authored")
        baseline_samples, _, _ = audited_samples(
            baseline_meshes,
            baseline_transforms,
            stage,
            args.tolerance,
        )
        baseline_sample_count = len(baseline_samples)
        baseline_supported = proximity_support(samples, baseline_samples, args.baseline_tolerance)
    supported = box_supported | baseline_supported
    total_weight = float(weights.sum())
    unsupported_weight = float(weights[~supported].sum())
    unsupported = samples[~supported]
    corridors = route_corridors(stage)
    route_reports = []
    for corridor in corridors:
        mask = in_corridor(unsupported, corridor)
        route_reports.append({
            "id": corridor["id"],
            "unsupportedSampleCount": int(mask.sum()),
            "pass": int(mask.sum()) == 0,
        })

    per_group = {}
    names = np.asarray(names_by_sample, dtype=object)
    for group in ("sanctuary", "observatory", "district"):
        mask = np.array([group_for_name(str(name)) == group for name in names], dtype=bool)
        group_weight = float(weights[mask].sum())
        group_unsupported = float(weights[mask & ~supported].sum())
        per_group[group] = {
            "sampleCount": int(mask.sum()),
            "unsupportedSampleCount": int((mask & ~supported).sum()),
            "supportedAreaRatio": round(1.0 - group_unsupported / max(group_weight, 1e-12), 6),
            "translationXYZ": [round(float(value), 6) for value in transforms[group]],
        }

    unsupported_ratio = unsupported_weight / max(total_weight, 1e-12)
    pass_gate = unsupported_ratio <= 0.002 and all(item["pass"] for item in route_reports)
    report = {
        "schemaVersion": 1,
        "status": "PASS" if pass_gate else "NO-SHIP",
        "candidate": str(args.glb),
        "authoritativeLayout": str(args.layouts),
        "authoritativePlacementSource": stage.get("placementSource", "runtime-release/legacy"),
        "mode": args.mode,
        "toleranceMetres": args.tolerance,
        "approvedContactSkeleton": str(args.baseline_glb) if args.baseline_glb else None,
        "approvedContactSkeletonToleranceMetres": args.baseline_tolerance if args.baseline_glb else None,
        "approvedContactSkeletonSampleCount": baseline_sample_count,
        "playerHeightBandMetres": [0.2, 2.35],
        "collisionPolicy": "TypeScript BoxSpec remains authoritative; external GLB owns visuals only.",
        "sampleCount": int(len(samples)),
        "supportedSampleCount": int(supported.sum()),
        "boxSupportedSampleCount": int(box_supported.sum()),
        "baselineSupportedSampleCount": int((baseline_supported & ~box_supported).sum()),
        "unsupportedSampleCount": int((~supported).sum()),
        "supportedAreaRatio": round(1.0 - unsupported_ratio, 6),
        "requiredSupportedAreaRatio": 0.998,
        "perGroup": per_group,
        "protectedRoutes": route_reports,
        "failures": [] if pass_gate else [
            f"unsupported-player-surface-area-ratio:{unsupported_ratio:.6f}>0.002000"
        ] + [f"route-blocker:{item['id']}:{item['unsupportedSampleCount']}" for item in route_reports if not item["pass"]],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    draw_proof(args.proof, stage, meshes, transforms, unsupported, corridors)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if pass_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
