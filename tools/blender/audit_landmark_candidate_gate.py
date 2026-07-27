#!/usr/bin/env python3
"""Audit private Hibana stage candidates for landmark height, support and access.

This is intentionally a candidate-only gate.  It reads the canonical solver
layout and exported GLBs but refuses the public release tree.  Geometry support
reconstructs disconnected indexed-mesh islands after material batching, then
checks that their AABB contact graph reaches the ground.  Entrance visibility
uses the authoritative collision boxes, plus exported landmark bounds and
entrance metadata; final visual approval still requires muted browser/viewport
captures.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from .validate_dense_stage_assets import (
        load_glb_document,
        load_json,
        merge_bounds,
        node_mesh_bounds,
        node_world_matrices,
        transform_point,
    )
except ImportError:  # pragma: no cover - supports direct execution
    from validate_dense_stage_assets import (
        load_glb_document,
        load_json,
        merge_bounds,
        node_mesh_bounds,
        node_world_matrices,
        transform_point,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ROOT = (PROJECT_ROOT / "public").resolve()
PLACEMENT_SOURCE = "canonical-solver-v2-authoring"
LOD_PATTERN = re.compile(r"-lod([012])\.glb$", re.IGNORECASE)
BIN_CHUNK = 0x004E4942
COMPONENT_FORMATS = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
ACCESSOR_WIDTHS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


@dataclass(frozen=True)
class GateConfig:
    min_height_ratio: float = 0.82
    # Canonical height is also a placement/sightline ceiling.  Allow bevel and
    # export noise, but reject a visibly taller crown (for example 48.5 m on a
    # 47 m contract).
    max_height_ratio: float = 1.02
    max_ground_gap_m: float = 0.35
    max_support_gap_m: float = 0.75
    min_support_coverage: float = 0.02
    min_component_contact_coverage: float = 0.0005
    eye_height_m: float = 1.65
    entrance_probe_radius_m: float = 0.20
    entrance_end_clearance_m: float = 0.75
    max_entrance_bounds_offset_m: float = 1.50
    max_entrance_inset_m: float = 3.00


def finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def finite_pair(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, list) or len(value) != 2 or not all(finite(part) for part in value):
        return None
    return float(value[0]), float(value[1])


def is_below(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents


def rounded(value: float | None, digits: int = 4) -> float | None:
    return None if value is None or not math.isfinite(value) else round(value, digits)


def load_glb_binary_chunk(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("file-too-small")
    magic, version, declared_length = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67 or version != 2 or declared_length != len(raw):
        raise ValueError("invalid-glb-header")
    offset = 12
    binary: bytes | None = None
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("truncated-chunk-header")
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        end = offset + length
        if end > len(raw):
            raise ValueError("truncated-chunk-payload")
        if kind == BIN_CHUNK and binary is None:
            binary = raw[offset:end]
        offset = end
    if binary is None:
        raise ValueError("missing-binary-chunk")
    return binary


def accessor_values(document: dict[str, Any], binary: bytes, accessor_index: Any) -> list[Any]:
    accessors = document.get("accessors")
    views = document.get("bufferViews")
    if not isinstance(accessors, list) or not isinstance(views, list) or not isinstance(accessor_index, int):
        raise ValueError("invalid-accessor-index")
    if accessor_index < 0 or accessor_index >= len(accessors):
        raise ValueError("accessor-index-out-of-range")
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict) or "sparse" in accessor:
        raise ValueError("sparse-or-invalid-accessor-unsupported")
    view_index = accessor.get("bufferView")
    if not isinstance(view_index, int) or view_index < 0 or view_index >= len(views):
        raise ValueError("accessor-buffer-view-invalid")
    view = views[view_index]
    if not isinstance(view, dict) or view.get("buffer", 0) != 0:
        raise ValueError("external-buffer-view-unsupported")
    if isinstance(view.get("extensions"), dict) and view["extensions"]:
        raise ValueError("compressed-buffer-view-unsupported")
    component = COMPONENT_FORMATS.get(accessor.get("componentType"))
    width = ACCESSOR_WIDTHS.get(accessor.get("type"))
    count = accessor.get("count")
    if component is None or width is None or not isinstance(count, int) or count < 0:
        raise ValueError("accessor-layout-invalid")
    fmt, component_bytes = component
    packed_bytes = component_bytes * width
    stride = view.get("byteStride", packed_bytes)
    if not isinstance(stride, int) or stride < packed_bytes:
        raise ValueError("accessor-stride-invalid")
    offset = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    if offset < 0 or (count and offset + (count - 1) * stride + packed_bytes > len(binary)):
        raise ValueError("accessor-outside-binary-chunk")
    unpacker = struct.Struct("<" + fmt * width)
    values: list[Any] = []
    for item_index in range(count):
        value = unpacker.unpack_from(binary, offset + item_index * stride)
        values.append(value[0] if width == 1 else tuple(float(part) for part in value))
    return values


def primitive_triangles(indices: list[int], mode: int) -> list[tuple[int, int, int]]:
    if mode == 4:
        return [tuple(indices[index:index + 3]) for index in range(0, len(indices) - 2, 3)]
    if mode == 5:
        return [
            (indices[index], indices[index + 1], indices[index + 2])
            if index % 2 == 0 else (indices[index + 1], indices[index], indices[index + 2])
            for index in range(len(indices) - 2)
        ]
    if mode == 6 and len(indices) >= 3:
        return [(indices[0], indices[index], indices[index + 1]) for index in range(1, len(indices) - 1)]
    raise ValueError(f"primitive-mode-unsupported:{mode}")


def primitive_component_bounds(
    document: dict[str, Any],
    binary: bytes,
    primitive: dict[str, Any],
    matrix: tuple[float, ...],
) -> list[tuple[float, ...]]:
    attributes = primitive.get("attributes")
    if not isinstance(attributes, dict):
        raise ValueError("primitive-attributes-invalid")
    positions_value = accessor_values(document, binary, attributes.get("POSITION"))
    positions = [
        tuple(float(part) for part in value)
        for value in positions_value
        if isinstance(value, tuple) and len(value) == 3
    ]
    if len(positions) != len(positions_value):
        raise ValueError("position-accessor-not-vec3")
    if "indices" in primitive:
        raw_indices = accessor_values(document, binary, primitive.get("indices"))
        if not all(isinstance(value, int) for value in raw_indices):
            raise ValueError("index-accessor-not-integer")
        indices = [int(value) for value in raw_indices]
    else:
        indices = list(range(len(positions)))
    triangles = primitive_triangles(indices, int(primitive.get("mode", 4)))
    parent: dict[int, int] = {}

    def find(index: int) -> int:
        parent.setdefault(index, index)
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    used: set[int] = set()
    for triangle in triangles:
        if any(index < 0 or index >= len(positions) for index in triangle):
            raise ValueError("primitive-index-out-of-range")
        first, second, third = triangle
        used.update(triangle)
        union(first, second)
        union(second, third)

    # Blender may duplicate vertices along hard normals and UV seams.  Weld
    # identical positions for connectivity only; exported positions stay intact.
    position_owner: dict[tuple[int, int, int], int] = {}
    for index in used:
        key = tuple(round(component * 100_000) for component in positions[index])
        owner = position_owner.setdefault(key, index)
        union(owner, index)

    components: dict[int, list[tuple[float, float, float]]] = {}
    for index in used:
        components.setdefault(find(index), []).append(transform_point(matrix, positions[index]))
    bounds: list[tuple[float, ...]] = []
    for points in components.values():
        minimum = tuple(min(point[axis] for point in points) for axis in range(3))
        maximum = tuple(max(point[axis] for point in points) for axis in range(3))
        if all(maximum[axis] - minimum[axis] > 1e-6 for axis in range(3)):
            bounds.append(minimum + maximum)
    return bounds


def node_component_bounds(
    document: dict[str, Any],
    binary: bytes,
    node_index: int,
    matrices: list[tuple[float, ...] | None],
) -> list[tuple[float, ...]]:
    nodes, meshes = document.get("nodes"), document.get("meshes")
    if not isinstance(nodes, list) or not isinstance(meshes, list) or node_index >= len(nodes):
        raise ValueError("node-or-mesh-table-invalid")
    node = nodes[node_index]
    matrix = matrices[node_index] if node_index < len(matrices) else None
    if not isinstance(node, dict) or matrix is None or not isinstance(node.get("mesh"), int):
        raise ValueError("landmark-node-mesh-invalid")
    mesh_index = node["mesh"]
    if mesh_index < 0 or mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
        raise ValueError("landmark-mesh-index-invalid")
    primitives = meshes[mesh_index].get("primitives")
    if not isinstance(primitives, list):
        raise ValueError("landmark-primitives-invalid")
    result: list[tuple[float, ...]] = []
    for primitive in primitives:
        if isinstance(primitive, dict):
            result.extend(primitive_component_bounds(document, binary, primitive, matrix))
    return result


def bounds_height_audit(bounds: tuple[float, ...], target_height: float, config: GateConfig) -> dict[str, Any]:
    minimum_y, maximum_y = bounds[1], bounds[4]
    bounds_height = maximum_y - minimum_y
    # The canonical target is measured from stage ground.  Do not reward a
    # buried foundation, and assess a floating base separately as a ground gap.
    above_ground_height = max(0.0, maximum_y - max(0.0, minimum_y))
    ratio = above_ground_height / target_height if target_height > 0 else math.inf
    if ratio < config.min_height_ratio:
        status = "under"
    elif ratio > config.max_height_ratio:
        status = "over"
    else:
        status = "within"
    return {
        "targetHeightM": rounded(target_height),
        "boundsHeightM": rounded(bounds_height),
        "aboveGroundHeightM": rounded(above_ground_height),
        "visualTopY": rounded(maximum_y),
        "heightRatio": rounded(ratio, 6),
        "status": status,
    }


def horizontal_coverage(child: tuple[float, ...], support: tuple[float, ...]) -> float:
    overlap_x = max(0.0, min(child[3], support[3]) - max(child[0], support[0]))
    overlap_z = max(0.0, min(child[5], support[5]) - max(child[2], support[2]))
    child_area = max(1e-9, (child[3] - child[0]) * (child[5] - child[2]))
    return overlap_x * overlap_z / child_area


def support_chain_audit(nodes: list[dict[str, Any]], config: GateConfig) -> dict[str, Any]:
    """Find a coarse, ground-reachable support chain between exported AABBs."""
    grounded = {
        index for index, node in enumerate(nodes)
        if node["bounds"][1] <= config.max_ground_gap_m
    }
    supported = set(grounded)
    links: dict[int, dict[str, Any]] = {
        index: {"kind": "ground", "gapM": max(0.0, nodes[index]["bounds"][1])}
        for index in grounded
    }
    changed = True
    while changed:
        changed = False
        for child_index, child in enumerate(nodes):
            if child_index in supported:
                continue
            child_bounds = child["bounds"]
            choices: list[tuple[float, float, int]] = []
            for support_index in supported:
                support_bounds = nodes[support_index]["bounds"]
                if support_bounds[1] >= child_bounds[1] - 1e-6:
                    continue
                coverage = horizontal_coverage(child_bounds, support_bounds)
                gap = max(0.0, child_bounds[1] - support_bounds[4])
                if coverage >= config.min_support_coverage and gap <= config.max_support_gap_m:
                    choices.append((gap, -coverage, support_index))
            if not choices:
                continue
            gap, negative_coverage, support_index = min(choices)
            supported.add(child_index)
            links[child_index] = {
                "kind": "node-aabb",
                "node": nodes[support_index]["name"],
                "gapM": rounded(gap),
                "coverage": rounded(-negative_coverage, 6),
            }
            changed = True

    unsupported: list[dict[str, Any]] = []
    for child_index, child in enumerate(nodes):
        if child_index in supported:
            continue
        child_bounds = child["bounds"]
        candidates: list[tuple[float, float, str]] = []
        for support_index, support in enumerate(nodes):
            if support_index == child_index or support["bounds"][1] >= child_bounds[1] - 1e-6:
                continue
            coverage = horizontal_coverage(child_bounds, support["bounds"])
            if coverage <= 0:
                continue
            gap = max(0.0, child_bounds[1] - support["bounds"][4])
            candidates.append((gap, -coverage, support["name"]))
        best = min(candidates) if candidates else None
        unsupported.append({
            "node": child["name"],
            "bottomY": rounded(child_bounds[1]),
            "nearestGapM": rounded(best[0]) if best else None,
            "nearestCoverage": rounded(-best[1], 6) if best else 0.0,
            "nearestNode": best[2] if best else None,
        })

    linked_gaps = [float(link["gapM"]) for link in links.values() if finite(link.get("gapM"))]
    return {
        "method": "ground-reachable-export-node-aabb-chain",
        "confidence": "coarse-after-material-batching",
        "nodeCount": len(nodes),
        "groundedNodeCount": len(grounded),
        "supportedNodeCount": len(supported),
        "unsupportedNodeCount": len(unsupported),
        "maxAcceptedGapM": rounded(max(linked_gaps, default=0.0)),
        "links": [
            {"node": nodes[index]["name"], **links[index]}
            for index in sorted(links)
        ],
        "unsupported": unsupported,
    }


def component_contact(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> tuple[float, float, str] | None:
    gaps = [
        max(0.0, left[axis] - right[axis + 3], right[axis] - left[axis + 3])
        for axis in range(3)
    ]
    separated = [axis for axis, gap in enumerate(gaps) if gap > 1e-6]
    if len(separated) > 1:
        return None
    if separated:
        contact_axis = separated[0]
    else:
        overlaps = [
            min(left[axis + 3], right[axis + 3]) - max(left[axis], right[axis])
            for axis in range(3)
        ]
        contact_axis = min(range(3), key=lambda axis: overlaps[axis])
    face_axes = [axis for axis in range(3) if axis != contact_axis]
    overlap_lengths = [
        max(0.0, min(left[axis + 3], right[axis + 3]) - max(left[axis], right[axis]))
        for axis in face_axes
    ]
    if any(length <= 1e-6 for length in overlap_lengths):
        return None
    overlap_area = overlap_lengths[0] * overlap_lengths[1]
    left_area = math.prod(left[axis + 3] - left[axis] for axis in face_axes)
    right_area = math.prod(right[axis + 3] - right[axis] for axis in face_axes)
    coverage = overlap_area / max(1e-9, min(left_area, right_area))
    return gaps[contact_axis], coverage, "XYZ"[contact_axis]


def component_support_audit(components: list[dict[str, Any]], config: GateConfig) -> dict[str, Any]:
    """Audit actual disconnected geometry islands through an AABB contact graph."""
    count = len(components)
    adjacency: list[list[tuple[int, float, float, str]]] = [[] for _ in components]
    for left_index in range(count):
        for right_index in range(left_index + 1, count):
            contact = component_contact(components[left_index]["bounds"], components[right_index]["bounds"])
            if contact is None:
                continue
            gap, coverage, axis = contact
            if gap > config.max_support_gap_m or coverage < config.min_component_contact_coverage:
                continue
            adjacency[left_index].append((right_index, gap, coverage, axis))
            adjacency[right_index].append((left_index, gap, coverage, axis))

    grounded = {
        index for index, component in enumerate(components)
        if component["bounds"][1] <= config.max_ground_gap_m
    }
    reached = set(grounded)
    queue = list(sorted(grounded))
    accepted_gaps: list[float] = []
    while queue:
        current = queue.pop()
        for neighbour, gap, _coverage, _axis in adjacency[current]:
            if neighbour in reached:
                continue
            reached.add(neighbour)
            queue.append(neighbour)
            accepted_gaps.append(gap)

    unsupported_indices = set(range(count)) - reached
    islands: list[dict[str, Any]] = []
    unseen = set(unsupported_indices)
    while unseen:
        seed = unseen.pop()
        island = {seed}
        pending = [seed]
        while pending:
            current = pending.pop()
            for neighbour, _gap, _coverage, _axis in adjacency[current]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    island.add(neighbour)
                    pending.append(neighbour)
        island_bounds = merge_bounds([components[index]["bounds"] for index in island])
        nearest: tuple[float, float, str] | None = None
        for island_index in island:
            for reached_index in reached:
                contact = component_contact(
                    components[island_index]["bounds"], components[reached_index]["bounds"]
                )
                if contact is None:
                    continue
                gap, coverage, axis = contact
                candidate = (gap, -coverage, axis)
                if nearest is None or candidate < nearest:
                    nearest = candidate
        names = [components[index]["name"] for index in sorted(island)]
        islands.append({
            "componentCount": len(island),
            "sampleNames": names[:8],
            "boundsXYZ": [rounded(value) for value in island_bounds] if island_bounds else None,
            "nearestGroundedGapM": rounded(nearest[0]) if nearest else None,
            "nearestGroundedCoverage": rounded(-nearest[1], 6) if nearest else 0.0,
            "nearestGroundedAxis": nearest[2] if nearest else None,
        })
    islands.sort(key=lambda island: (-island["componentCount"], repr(island["boundsXYZ"])))
    return {
        "method": "disconnected-mesh-island-aabb-contact-graph",
        "confidence": "strong-for-large-gaps; screenshots-required-for-small-contact-quality",
        "componentCount": count,
        "groundedComponentCount": len(grounded),
        "supportedComponentCount": len(reached),
        "unsupportedComponentCount": len(unsupported_indices),
        "unsupportedIslandCount": len(islands),
        "maxAcceptedGapM": rounded(max(accepted_gaps, default=0.0)),
        "unsupportedIslands": islands,
    }


def segment_intersects_rect(
    start: tuple[float, float],
    end: tuple[float, float],
    rect: tuple[float, float, float, float],
) -> bool:
    """Liang-Barsky intersection for a finite XZ segment and an axis-aligned box."""
    dx, dz = end[0] - start[0], end[1] - start[1]
    first, last = 0.0, 1.0
    for p, q in (
        (-dx, start[0] - rect[0]),
        (dx, rect[2] - start[0]),
        (-dz, start[1] - rect[1]),
        (dz, rect[3] - start[1]),
    ):
        if abs(p) <= 1e-12:
            if q < 0:
                return False
            continue
        candidate = q / p
        if p < 0:
            if candidate > last:
                return False
            first = max(first, candidate)
        else:
            if candidate < first:
                return False
            last = min(last, candidate)
    return True


def entrance_visibility_audit(stage: dict[str, Any], placement: dict[str, Any], config: GateConfig) -> dict[str, Any]:
    entrance = finite_pair(placement.get("entrance"))
    approach = placement.get("approach")
    start = finite_pair(approach.get("start")) if isinstance(approach, dict) else None
    width = approach.get("width") if isinstance(approach, dict) else None
    errors: list[str] = []
    if entrance is None or start is None or not finite(width) or float(width) <= 0:
        return {"method": "canonical-collision-proxy", "samples": [], "errors": ["invalid-entrance-approach"]}
    dx, dz = entrance[0] - start[0], entrance[1] - start[1]
    length = math.hypot(dx, dz)
    if length <= config.entrance_end_clearance_m + 0.01:
        return {"method": "canonical-collision-proxy", "samples": [], "errors": ["approach-too-short"]}
    forward_x, forward_z = dx / length, dz / length
    side_x, side_z = -forward_z, forward_x
    end = (
        entrance[0] - forward_x * config.entrance_end_clearance_m,
        entrance[1] - forward_z * config.entrance_end_clearance_m,
    )
    side_offset = min(1.5, float(width) * 0.25)
    offsets = (-side_offset, 0.0, side_offset)
    boxes = stage.get("boxes") if isinstance(stage.get("boxes"), list) else []
    samples: list[dict[str, Any]] = []
    for offset in offsets:
        ray_start = (start[0] + side_x * offset, start[1] + side_z * offset)
        ray_end = (end[0] + side_x * offset, end[1] + side_z * offset)
        blockers: list[dict[str, Any]] = []
        for box_index, box in enumerate(boxes):
            if not isinstance(box, dict) or box.get("ghost") is True:
                continue
            values = [box.get(key) for key in ("x", "y", "z", "w", "h", "d")]
            if not all(finite(value) for value in values):
                continue
            x, y, z, box_width, box_height, depth = (float(value) for value in values)
            if box_width <= 0 or box_height <= 0 or depth <= 0:
                continue
            if not y - box_height / 2 <= config.eye_height_m <= y + box_height / 2:
                continue
            padding = config.entrance_probe_radius_m
            rect = (
                x - box_width / 2 - padding,
                z - depth / 2 - padding,
                x + box_width / 2 + padding,
                z + depth / 2 + padding,
            )
            if segment_intersects_rect(ray_start, ray_end, rect):
                blockers.append({
                    "boxIndex": box_index,
                    "landmarkId": box.get("landmarkId"),
                    "part": box.get("landmarkPart"),
                    "centreXZ": [rounded(x), rounded(z)],
                    "sizeXZ": [rounded(box_width), rounded(depth)],
                })
        samples.append({
            "offsetM": rounded(offset),
            "startXZ": [rounded(ray_start[0]), rounded(ray_start[1])],
            "endXZ": [rounded(ray_end[0]), rounded(ray_end[1])],
            "clear": not blockers,
            "blockers": blockers,
        })
    if samples[1]["blockers"]:
        errors.append("entrance-centerline-blocked")
    if not any(sample["clear"] for sample in samples):
        errors.append("entrance-all-probes-blocked")
    return {
        "method": "canonical-collision-proxy-three-eye-rays",
        "eyeHeightM": config.eye_height_m,
        "clearRayCount": sum(bool(sample["clear"]) for sample in samples),
        "samples": samples,
        "errors": errors,
    }


def entrance_bounds_audit(bounds: tuple[float, ...], placement: dict[str, Any], config: GateConfig) -> dict[str, Any]:
    entrance = finite_pair(placement.get("entrance"))
    if entrance is None:
        return {"errors": ["invalid-entrance"]}
    x, z = entrance
    outside_x = max(bounds[0] - x, 0.0, x - bounds[3])
    outside_z = max(bounds[2] - z, 0.0, z - bounds[5])
    outside_distance = math.hypot(outside_x, outside_z)
    inside = outside_distance <= 1e-9
    inset = (
        min(x - bounds[0], bounds[3] - x, z - bounds[2], bounds[5] - z)
        if inside else None
    )
    errors: list[str] = []
    if outside_distance > config.max_entrance_bounds_offset_m:
        errors.append("entrance-outside-visual-bounds")
    if inset is not None and inset > config.max_entrance_inset_m:
        errors.append("entrance-too-deep-inside-visual-bounds")
    return {
        "method": "exported-landmark-aabb-perimeter",
        "entranceXZ": [rounded(x), rounded(z)],
        "insideBounds": inside,
        "outsideDistanceM": rounded(outside_distance),
        "perimeterInsetM": rounded(inset),
        "errors": errors,
    }


def metadata_audit(nodes: list[dict[str, Any]], placement: dict[str, Any]) -> list[str]:
    expected = {
        "hibanaLandmarkEntranceXZ": finite_pair(placement.get("entrance")),
        "hibanaLandmarkApproachStartXZ": finite_pair(placement.get("approach", {}).get("start")),
        "hibanaLandmarkApproachEndXZ": finite_pair(placement.get("approach", {}).get("end")),
    }
    errors: list[str] = []
    for key, expected_value in expected.items():
        values = {finite_pair(node["extras"].get(key)) for node in nodes}
        if values != {expected_value}:
            errors.append(f"metadata-{key}-mismatch")
    for key in ("hibanaLandmarkGrounded", "hibanaLandmarkCombatSpace"):
        if {node["extras"].get(key) for node in nodes} != {True}:
            errors.append(f"metadata-{key}-not-true")
    return errors


def landmark_nodes(
    document: dict[str, Any],
    binary: bytes,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    matrices = node_world_matrices(document)
    nodes = document.get("nodes")
    if not isinstance(nodes, list):
        return groups, ["node-table-invalid"]
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        extras = node.get("extras")
        landmark_id = extras.get("hibanaLandmarkId") if isinstance(extras, dict) else None
        if not isinstance(landmark_id, str) or not landmark_id:
            continue
        bounds = node_mesh_bounds(document, index, matrices)
        if bounds is None:
            errors.append(f"{landmark_id}:{node.get('name', index)}:node-bounds-missing")
            continue
        try:
            component_bounds = node_component_bounds(document, binary, index, matrices)
        except ValueError as error:
            errors.append(f"{landmark_id}:{node.get('name', index)}:component-decode:{error}")
            component_bounds = []
        node_name = str(node.get("name", f"node[{index}]"))
        groups.setdefault(landmark_id, []).append({
            "name": node_name,
            "bounds": bounds,
            "extras": extras,
            "components": [
                {"name": f"{node_name}#island-{component_index}", "bounds": component_bounds_value}
                for component_index, component_bounds_value in enumerate(component_bounds)
            ],
        })
    return groups, errors


def audit_landmark(
    placement: dict[str, Any],
    nodes: list[dict[str, Any]],
    visibility: dict[str, Any],
    config: GateConfig,
) -> dict[str, Any]:
    landmark_id = str(placement.get("id", ""))
    errors: list[str] = []
    bounds = merge_bounds([node["bounds"] for node in nodes])
    if bounds is None:
        return {"id": landmark_id, "nodes": len(nodes), "errors": ["visual-bounds-missing"]}
    target_height = placement.get("height")
    if not finite(target_height) or float(target_height) <= 0:
        return {"id": landmark_id, "nodes": len(nodes), "errors": ["target-height-invalid"]}
    height = bounds_height_audit(bounds, float(target_height), config)
    if height["status"] == "under":
        errors.append(f"height-under-target:{height['heightRatio']}<{config.min_height_ratio}")
    elif height["status"] == "over":
        errors.append(f"height-over-target:{height['heightRatio']}>{config.max_height_ratio}")
    ground_gap = max(0.0, bounds[1])
    if placement.get("grounded") is not True:
        errors.append("canonical-grounded-not-true")
    if ground_gap > config.max_ground_gap_m:
        errors.append(f"ground-gap:{ground_gap:.4f}>{config.max_ground_gap_m:.4f}")
    node_envelope_support = support_chain_audit(nodes, config)
    components = [component for node in nodes for component in node.get("components", [])]
    support = component_support_audit(components, config)
    support["nodeEnvelopeAudit"] = node_envelope_support
    if not components:
        errors.append("component-support-unavailable")
    elif support["unsupportedIslandCount"]:
        errors.append(
            f"unsupported-mesh-islands:{support['unsupportedIslandCount']}"
            f"/{support['unsupportedComponentCount']}"
        )
    entrance_bounds = entrance_bounds_audit(bounds, placement, config)
    errors.extend(entrance_bounds["errors"])
    errors.extend(visibility["errors"])
    errors.extend(metadata_audit(nodes, placement))
    return {
        "id": landmark_id,
        "nodes": len(nodes),
        "visualBoundsXYZ": [rounded(value) for value in bounds],
        "height": height,
        "ground": {
            "baseY": rounded(bounds[1]),
            "gapM": rounded(ground_gap),
            "maxGapM": config.max_ground_gap_m,
        },
        "support": support,
        "entranceVisibility": visibility,
        "entranceBounds": entrance_bounds,
        "errors": errors,
    }


def audit_glb(path: Path, stage: dict[str, Any], lod: int, config: GateConfig) -> dict[str, Any]:
    report: dict[str, Any] = {"lod": lod, "path": str(path), "landmarks": [], "errors": []}
    if not path.is_file():
        report["errors"].append("missing-glb")
        return report
    try:
        document = load_glb_document(path)
        binary = load_glb_binary_chunk(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        report["errors"].append(f"invalid-glb:{error}")
        return report
    groups, component_errors = landmark_nodes(document, binary)
    report["errors"].extend(component_errors)
    placements = stage.get("landmarkPlacements")
    if not isinstance(placements, list) or len(placements) != 2:
        report["errors"].append("canonical-landmark-count-not-two")
        return report
    expected_ids = {placement.get("id") for placement in placements if isinstance(placement, dict)}
    if set(groups) != expected_ids:
        report["errors"].append(
            "landmark-id-set:missing=" + ",".join(sorted(expected_ids - set(groups)))
            + ";extra=" + ",".join(sorted(set(groups) - expected_ids))
        )
    for placement in placements:
        if not isinstance(placement, dict) or not isinstance(placement.get("id"), str):
            continue
        visibility = entrance_visibility_audit(stage, placement, config)
        landmark_report = audit_landmark(placement, groups.get(placement["id"], []), visibility, config)
        report["landmarks"].append(landmark_report)
        report["errors"].extend(f"{placement['id']}:{error}" for error in landmark_report["errors"])
    return report


def stage_entries(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    entries: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return entries, ["manifest-assets-missing"]
    for index, entry in enumerate(assets):
        if not isinstance(entry, dict):
            errors.append(f"manifest-entry[{index}]-invalid")
            continue
        stages = entry.get("stages")
        if not isinstance(stages, list) or len(stages) != 1 or not isinstance(stages[0], str):
            errors.append(f"manifest-entry[{index}]-stage-singleton-invalid")
            continue
        stage_id = stages[0]
        if stage_id in entries:
            errors.append(f"manifest-stage-duplicate:{stage_id}")
            continue
        entries[stage_id] = entry
    return entries, errors


def lod_urls(entry: dict[str, Any]) -> tuple[dict[int, str], list[str]]:
    urls: dict[int, str] = {}
    errors: list[str] = []
    candidates: list[tuple[int, Any]] = [(0, entry.get("url"))]
    lod_entries = entry.get("lods")
    if isinstance(lod_entries, list):
        candidates.extend((index + 1, lod.get("url") if isinstance(lod, dict) else None)
                          for index, lod in enumerate(lod_entries))
    for fallback_lod, value in candidates:
        if not isinstance(value, str) or not value:
            errors.append(f"lod{fallback_lod}-url-invalid")
            continue
        match = LOD_PATTERN.search(value)
        lod = int(match.group(1)) if match else fallback_lod
        if lod not in (0, 1, 2):
            errors.append(f"lod-index-invalid:{lod}")
        elif lod in urls:
            errors.append(f"lod-url-duplicate:{lod}")
        else:
            urls[lod] = value
    if set(urls) != {0, 1, 2}:
        errors.append("lod-url-set-not-0-1-2")
    return urls, errors


def resolve_candidate_asset(manifest_path: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or "://" in value:
        raise ValueError(f"asset-url-must-be-relative:{value}")
    root = manifest_path.parent.resolve()
    asset = (root / relative).resolve()
    if not is_below(asset, root):
        raise ValueError(f"asset-url-escapes-candidate-root:{value}")
    if is_below(asset, PUBLIC_ROOT):
        raise ValueError(f"public-asset-forbidden:{asset}")
    return asset


def audit_candidate(
    layouts_path: Path,
    manifest_path: Path,
    selected_stages: list[str] | None = None,
    selected_lods: list[int] | None = None,
    config: GateConfig | None = None,
) -> dict[str, Any]:
    config = config or GateConfig()
    layouts_path = layouts_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if is_below(manifest_path, PUBLIC_ROOT):
        raise ValueError(f"candidate manifest must not be below public/: {manifest_path}")
    layouts = load_json(layouts_path)
    manifest = load_json(manifest_path)
    errors: list[str] = []
    if layouts.get("placementSource") != PLACEMENT_SOURCE:
        errors.append("canonical-layout-placement-source-invalid")
    if manifest.get("placementSource") != PLACEMENT_SOURCE:
        errors.append("candidate-manifest-placement-source-invalid")
    stages_value = layouts.get("stages")
    canonical_stages = {
        stage["id"]: stage for stage in stages_value
        if isinstance(stage, dict) and isinstance(stage.get("id"), str)
    } if isinstance(stages_value, list) else {}
    entries, manifest_errors = stage_entries(manifest)
    errors.extend(manifest_errors)
    requested = selected_stages or list(entries)
    unknown = sorted(set(requested) - set(canonical_stages))
    missing_entries = sorted(set(requested) - set(entries))
    if unknown:
        errors.append("unknown-canonical-stage:" + ",".join(unknown))
    if missing_entries:
        errors.append("candidate-stage-missing:" + ",".join(missing_entries))
    requested_lods = sorted(set(selected_lods or (0, 1, 2)))
    if any(lod not in (0, 1, 2) for lod in requested_lods):
        errors.append("selected-lod-invalid")

    stage_reports: list[dict[str, Any]] = []
    for stage_id in requested:
        if stage_id not in canonical_stages or stage_id not in entries:
            continue
        stage = canonical_stages[stage_id]
        stage_errors: list[str] = []
        if stage.get("placementSource") != PLACEMENT_SOURCE:
            stage_errors.append("canonical-stage-placement-source-invalid")
        urls, url_errors = lod_urls(entries[stage_id])
        stage_errors.extend(url_errors)
        lod_reports: list[dict[str, Any]] = []
        for lod in requested_lods:
            value = urls.get(lod)
            if value is None:
                stage_errors.append(f"lod{lod}:url-missing")
                continue
            try:
                asset_path = resolve_candidate_asset(manifest_path, value)
                lod_report = audit_glb(asset_path, stage, lod, config)
            except ValueError as error:
                lod_report = {"lod": lod, "path": value, "landmarks": [], "errors": [str(error)]}
            lod_reports.append(lod_report)
            stage_errors.extend(f"lod{lod}:{error}" for error in lod_report["errors"])
        stage_reports.append({"id": stage_id, "lods": lod_reports, "errors": stage_errors})

    landmark_reports = [
        landmark
        for stage in stage_reports
        for lod in stage["lods"]
        for landmark in lod["landmarks"]
    ]
    summary = {
        "stageCount": len(stage_reports),
        "lodAssetCount": sum(len(stage["lods"]) for stage in stage_reports),
        "landmarkCheckCount": len(landmark_reports),
        "heightUnderCount": sum(landmark.get("height", {}).get("status") == "under" for landmark in landmark_reports),
        "heightOverCount": sum(landmark.get("height", {}).get("status") == "over" for landmark in landmark_reports),
        "groundGapCount": sum(bool(landmark.get("ground", {}).get("gapM", 0) > config.max_ground_gap_m)
                              for landmark in landmark_reports),
        "unsupportedComponentCount": sum(
            int(landmark.get("support", {}).get("unsupportedComponentCount", 0))
            for landmark in landmark_reports
        ),
        "unsupportedIslandCount": sum(
            int(landmark.get("support", {}).get("unsupportedIslandCount", 0))
            for landmark in landmark_reports
        ),
        "blockedEntranceCount": sum(bool(landmark.get("entranceVisibility", {}).get("errors"))
                                    for landmark in landmark_reports),
    }
    ok = not errors and all(not stage["errors"] for stage in stage_reports) and bool(stage_reports)
    return {
        "schemaVersion": 1,
        "audit": "hibana-private-landmark-height-support-entrance",
        "candidateOnly": True,
        "ok": ok,
        "verdict": "SHIP-CANDIDATE" if ok else "NO-SHIP",
        "coordinateSystem": "glTF-Y-up/runtime-XZ",
        "limitations": [
            "support reconstructs disconnected indexed-mesh islands, then uses their AABB contact graph",
            "small contact quality still requires six-side screenshots; this gate targets large air gaps",
            "entrance visibility uses canonical collision boxes and exported bounds; screenshots remain mandatory",
        ],
        "layouts": str(layouts_path),
        "manifest": str(manifest_path),
        "thresholds": asdict(config),
        "summary": summary,
        "stages": stage_reports,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--stage", action="append", dest="stages")
    parser.add_argument("--lod", action="append", type=int, dest="lods")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--min-height-ratio", type=float, default=GateConfig.min_height_ratio)
    parser.add_argument("--max-height-ratio", type=float, default=GateConfig.max_height_ratio)
    parser.add_argument("--max-ground-gap-m", type=float, default=GateConfig.max_ground_gap_m)
    parser.add_argument("--max-support-gap-m", type=float, default=GateConfig.max_support_gap_m)
    args = parser.parse_args()
    config = GateConfig(
        min_height_ratio=args.min_height_ratio,
        max_height_ratio=args.max_height_ratio,
        max_ground_gap_m=args.max_ground_gap_m,
        max_support_gap_m=args.max_support_gap_m,
    )
    try:
        report = audit_candidate(args.layouts, args.manifest, args.stages, args.lods, config)
        if args.report:
            destination = args.report.expanduser().resolve()
            if is_below(destination, PUBLIC_ROOT):
                raise ValueError(f"candidate report must not be below public/: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "verdict": "NO-SHIP", "errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
