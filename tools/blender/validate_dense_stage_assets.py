#!/usr/bin/env python3
"""Validate Hibana's 31 dense Blender stages and their three-LOD release contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_STAGE_IDS = (
    "kunren", "souko", "nakaniwa", "kairou", "kouwan", "takadai", "sakyuu",
    "setsugen", "koushou", "yoichi", "okujou", "saisekiba", "chikurin", "tanada",
    "misaki", "haieki", "kyokoku", "kohan", "kuko", "onsengai", "z01", "z02",
    "z03", "z04", "z05", "z06", "z07", "z08", "z09", "z10", "renshujo",
)
JSON_CHUNK = 0x4E4F534A
TRIANGLES = 4
TRIANGLE_STRIP = 5
TRIANGLE_FAN = 6
GENERATOR_VERSION = "dense-world-v4"
GENERATOR_PATH = PROJECT_ROOT / "tools/blender/build_all_stages.py"
# The runtime-release layout that build_all_stages.py itself reads as its
# landmark placement input (see build_landmark_objects/build_nakaniwa_reference_lod).
# When a stage carries populated landmarkPlacements here, that is the single
# source of truth the generator baked into the GLB's hibanaLandmarkTargetDimensionsXYZ
# / hibanaLandmarkPlacement extras (in-bounds-collision-authoritative). Stage
# profiles' megaLandmarks.dimensionsM is a deliberately larger, separate
# "visualEnvelopeM" declaration (see tools/blender/stage-world.catalog.json and
# docs/STAGE_WORLD_CATALOG.md's "collision footprints kept separate from larger
# visual envelopes") and is never expected to equal the built collision footprint.
RUNTIME_LAYOUTS_PATH = PROJECT_ROOT / "tools/blender/generated/stage-layouts.json"


def current_generator_sha(path: Path = GENERATOR_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


EXPECTED_GENERATOR_SHA = current_generator_sha()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def finite_vector(value: Any, length: int) -> tuple[float, ...] | None:
    if not isinstance(value, list) or len(value) != length or not all(finite_number(item) for item in value):
        return None
    return tuple(float(item) for item in value)


IDENTITY_MATRIX = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)


def multiply_matrices(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    """Multiply two glTF column-major 4x4 matrices."""
    return tuple(
        sum(left[k * 4 + row] * right[column * 4 + k] for k in range(4))
        for column in range(4)
        for row in range(4)
    )


def node_local_matrix(node: dict[str, Any]) -> tuple[float, ...] | None:
    matrix = finite_vector(node.get("matrix"), 16)
    if matrix is not None:
        return matrix
    if "matrix" in node:
        return None
    translation = finite_vector(node.get("translation", [0, 0, 0]), 3)
    rotation = finite_vector(node.get("rotation", [0, 0, 0, 1]), 4)
    scale = finite_vector(node.get("scale", [1, 1, 1]), 3)
    if translation is None or rotation is None or scale is None:
        return None
    x, y, z, w = rotation
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length <= 1e-12:
        return None
    x, y, z, w = (component / length for component in (x, y, z, w))
    sx, sy, sz = scale
    tx, ty, tz = translation
    return (
        (1 - 2 * y * y - 2 * z * z) * sx,
        (2 * x * y + 2 * z * w) * sx,
        (2 * x * z - 2 * y * w) * sx,
        0.0,
        (2 * x * y - 2 * z * w) * sy,
        (1 - 2 * x * x - 2 * z * z) * sy,
        (2 * y * z + 2 * x * w) * sy,
        0.0,
        (2 * x * z + 2 * y * w) * sz,
        (2 * y * z - 2 * x * w) * sz,
        (1 - 2 * x * x - 2 * y * y) * sz,
        0.0,
        tx,
        ty,
        tz,
        1.0,
    )


def transform_point(matrix: tuple[float, ...], point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
        matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
        matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
    )


def node_world_matrices(document: dict[str, Any]) -> list[tuple[float, ...] | None]:
    nodes = document.get("nodes", [])
    if not isinstance(nodes, list):
        return []
    parents: dict[int, int] = {}
    for parent_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        children = node.get("children", [])
        if not isinstance(children, list):
            continue
        for child in children:
            if isinstance(child, int) and 0 <= child < len(nodes) and child not in parents:
                parents[child] = parent_index
    cache: list[tuple[float, ...] | None] = [None] * len(nodes)
    visiting: set[int] = set()

    def resolve(index: int) -> tuple[float, ...] | None:
        if cache[index] is not None:
            return cache[index]
        if index in visiting:
            return None
        node = nodes[index]
        if not isinstance(node, dict):
            return None
        local = node_local_matrix(node)
        if local is None:
            return None
        visiting.add(index)
        parent_index = parents.get(index)
        parent = IDENTITY_MATRIX if parent_index is None else resolve(parent_index)
        visiting.discard(index)
        if parent is None:
            return None
        cache[index] = multiply_matrices(parent, local)
        return cache[index]

    for node_index in range(len(nodes)):
        resolve(node_index)
    return cache


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def load_runtime_landmark_placements(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    """Load per-stage landmarkPlacements from the runtime-release layout.

    This is an optional cross-check against the same file build_all_stages.py
    already reads to build the GLBs, so a missing/malformed/non-runtime-release
    file must never crash the validator: it simply means no stage gets the
    in-bounds contract below, and every stage falls back to the profile's
    declared visual-envelope contract exactly as before this check existed.
    """
    if path is None:
        return {}
    try:
        document = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    if document.get("placementSource") != "runtime-release":
        return {}
    stages = document.get("stages")
    if not isinstance(stages, list):
        return {}
    result: dict[str, list[dict[str, Any]]] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        stage_id = stage.get("id")
        placements = stage.get("landmarkPlacements")
        if isinstance(stage_id, str) and isinstance(placements, list) and len(placements) == 2:
            result[stage_id] = placements
    return result


def load_glb_document(path: Path) -> dict[str, Any]:
    """Read a GLB 2.0 JSON chunk with strict length and chunk-bound checks."""
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("file-too-small")
    magic, version, declared_length = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67:
        raise ValueError("invalid-glb-magic")
    if version != 2:
        raise ValueError(f"unsupported-glb-version:{version}")
    if declared_length != len(raw):
        raise ValueError(f"declared-length:{declared_length}!={len(raw)}")

    offset = 12
    json_payload: bytes | None = None
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("truncated-chunk-header")
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk_end = offset + chunk_length
        if chunk_end > len(raw):
            raise ValueError("truncated-chunk-payload")
        if chunk_type == JSON_CHUNK and json_payload is None:
            json_payload = raw[offset:chunk_end]
        offset = chunk_end
    if offset != len(raw):
        raise ValueError("invalid-chunk-layout")
    if json_payload is None:
        raise ValueError("missing-json-chunk")
    document = json.loads(json_payload.decode("utf-8").rstrip(" \t\r\n\0"))
    if not isinstance(document, dict):
        raise ValueError("glb-json-root-must-be-object")
    return document


def accessor_count(document: dict[str, Any], accessor_index: Any) -> int:
    accessors = document.get("accessors", [])
    if not isinstance(accessor_index, int) or not isinstance(accessors, list):
        return 0
    if accessor_index < 0 or accessor_index >= len(accessors):
        return 0
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict):
        return 0
    count = accessor.get("count", 0)
    return int(count) if isinstance(count, int) and count >= 0 else 0


def primitive_triangle_count(document: dict[str, Any], primitive: dict[str, Any]) -> int:
    count = accessor_count(document, primitive.get("indices"))
    if count == 0:
        attributes = primitive.get("attributes", {})
        if isinstance(attributes, dict):
            count = accessor_count(document, attributes.get("POSITION"))
    mode = primitive.get("mode", TRIANGLES)
    if mode == TRIANGLES:
        return count // 3
    if mode in (TRIANGLE_STRIP, TRIANGLE_FAN):
        return max(0, count - 2)
    return 0


def mesh_triangle_count(document: dict[str, Any], mesh_index: int) -> int:
    meshes = document.get("meshes", [])
    if not isinstance(meshes, list) or mesh_index < 0 or mesh_index >= len(meshes):
        return 0
    mesh = meshes[mesh_index]
    if not isinstance(mesh, dict):
        return 0
    primitives = mesh.get("primitives", [])
    if not isinstance(primitives, list):
        return 0
    return sum(
        primitive_triangle_count(document, primitive)
        for primitive in primitives
        if isinstance(primitive, dict)
    )


def total_triangle_count(document: dict[str, Any]) -> int:
    meshes = document.get("meshes", [])
    if not isinstance(meshes, list):
        return 0
    return sum(mesh_triangle_count(document, index) for index in range(len(meshes)))


def accessor_bounds(document: dict[str, Any], accessor_index: Any) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    accessors = document.get("accessors", [])
    if not isinstance(accessor_index, int) or not isinstance(accessors, list):
        return None
    if accessor_index < 0 or accessor_index >= len(accessors):
        return None
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict):
        return None
    minimum = finite_vector(accessor.get("min"), 3)
    maximum = finite_vector(accessor.get("max"), 3)
    if minimum is None or maximum is None:
        return None
    # glTF-Transform's meshopt pass quantizes POSITION accessors to normalized
    # integers and moves the dequantization range into the owning node's TRS.
    # Accessor min/max remain encoded integer values in the JSON.  Applying
    # the node matrix to those raw values inflates a 100 m landmark into a
    # million-metre false bound, so normalize exactly as WebGL does before the
    # world transform.  KHR_mesh_quantization permits these integer formats.
    if accessor.get("normalized") is True:
        component_type = accessor.get("componentType")
        normalized_ranges = {
            5120: (127.0, True),    # BYTE
            5121: (255.0, False),   # UNSIGNED_BYTE
            5122: (32767.0, True),  # SHORT
            5123: (65535.0, False), # UNSIGNED_SHORT
        }
        normalizer = normalized_ranges.get(component_type)
        if normalizer is None:
            return None
        denominator, signed = normalizer

        def decode(value: float) -> float:
            decoded = value / denominator
            return max(-1.0, decoded) if signed else decoded

        minimum = tuple(decode(value) for value in minimum)
        maximum = tuple(decode(value) for value in maximum)
    if any(minimum[axis] >= maximum[axis] for axis in range(3)):
        return None
    return minimum, maximum


def node_mesh_bounds(
    document: dict[str, Any],
    node_index: int,
    world_matrices: list[tuple[float, ...] | None],
) -> tuple[float, ...] | None:
    nodes = document.get("nodes", [])
    meshes = document.get("meshes", [])
    if not isinstance(nodes, list) or not isinstance(meshes, list):
        return None
    if node_index < 0 or node_index >= len(nodes) or node_index >= len(world_matrices):
        return None
    node = nodes[node_index]
    matrix = world_matrices[node_index]
    if not isinstance(node, dict) or matrix is None:
        return None
    mesh_index = node.get("mesh")
    if not isinstance(mesh_index, int) or mesh_index < 0 or mesh_index >= len(meshes):
        return None
    mesh = meshes[mesh_index]
    if not isinstance(mesh, dict):
        return None
    points: list[tuple[float, float, float]] = []
    primitives = mesh.get("primitives", [])
    if not isinstance(primitives, list):
        return None
    for primitive in primitives:
        if not isinstance(primitive, dict):
            continue
        attributes = primitive.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        bounds = accessor_bounds(document, attributes.get("POSITION"))
        if bounds is None:
            continue
        minimum, maximum = bounds
        for x in (minimum[0], maximum[0]):
            for y in (minimum[1], maximum[1]):
                for z in (minimum[2], maximum[2]):
                    points.append(transform_point(matrix, (x, y, z)))
    if not points:
        return None
    minimum = tuple(min(point[axis] for point in points) for axis in range(3))
    maximum = tuple(max(point[axis] for point in points) for axis in range(3))
    if any(minimum[axis] >= maximum[axis] for axis in range(3)):
        return None
    return minimum + maximum


def merge_bounds(values: list[tuple[float, ...]]) -> tuple[float, ...] | None:
    if not values:
        return None
    minimum = tuple(min(value[axis] for value in values) for axis in range(3))
    maximum = tuple(max(value[axis + 3] for value in values) for axis in range(3))
    if any(minimum[axis] >= maximum[axis] for axis in range(3)):
        return None
    return minimum + maximum


def bounds_match(left: tuple[float, ...], right: tuple[float, ...], tolerance: float = 0.002) -> bool:
    return all(math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance) for a, b in zip(left, right))


def landmark_ids_from_extra(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, list) and all(isinstance(part, str) for part in value):
        return tuple(value)
    return ()


def expected_profile_metadata(profile: dict[str, Any]) -> tuple[tuple[str, ...], str, int]:
    landmarks = profile.get("megaLandmarks", [])
    city = profile.get("cityProfile", {})
    if not isinstance(landmarks, list) or len(landmarks) != 2:
        raise ValueError("profile-must-have-two-mega-landmarks")
    landmark_ids = tuple(
        entry.get("id", "") if isinstance(entry, dict) else ""
        for entry in landmarks
    )
    if any(not value for value in landmark_ids):
        raise ValueError("profile-landmark-id-missing")
    if not isinstance(city, dict) or not isinstance(city.get("archetype"), str):
        raise ValueError("profile-city-archetype-missing")
    target = city.get("targetBuildingCount")
    if not isinstance(target, list) or len(target) != 2 or not isinstance(target[1], int):
        raise ValueError("profile-dense-building-target-missing")
    return landmark_ids, city["archetype"], target[1]


def expected_landmark_contracts(
    profile: dict[str, Any],
    canonical_stage: dict[str, Any] | None = None,
    runtime_landmarks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    landmarks = profile.get("megaLandmarks", [])
    if not isinstance(landmarks, list) or len(landmarks) != 2:
        raise ValueError("profile-must-have-two-mega-landmarks")
    canonical_landmarks = None
    if canonical_stage is not None:
        canonical_landmarks = canonical_stage.get("landmarkPlacements")
        if (
            canonical_stage.get("placementSource") != "canonical-solver-v2-authoring"
            or not isinstance(canonical_landmarks, list)
            or len(canonical_landmarks) != 2
        ):
            raise ValueError("canonical-stage-landmarks-invalid")
    if runtime_landmarks is not None and len(runtime_landmarks) != 2:
        raise ValueError("runtime-stage-landmarks-invalid")
    contracts: list[dict[str, Any]] = []
    for index, landmark in enumerate(landmarks):
        if not isinstance(landmark, dict) or not isinstance(landmark.get("id"), str):
            raise ValueError(f"profile-landmark-{index}-invalid")
        canonical_landmark = canonical_landmarks[index] if canonical_landmarks else None
        runtime_landmark = runtime_landmarks[index] if runtime_landmarks else None
        if canonical_landmark is not None:
            if (
                not isinstance(canonical_landmark, dict)
                or canonical_landmark.get("id") != landmark["id"]
            ):
                raise ValueError(f"canonical-landmark-{index}-id-mismatch")
            dimensions = {
                "width": canonical_landmark.get("width"),
                "height": canonical_landmark.get("height"),
                "depth": canonical_landmark.get("depth"),
            }
            placement = "in-bounds-collision-authoritative"
        elif runtime_landmark is not None:
            # This stage's landmarks were built in-bounds against the real
            # gameplay collision shell (see build_all_stages.py's
            # add_inbounds_landmark_visual / build_nakaniwa_reference_lod),
            # exactly like the explicit --layouts canonical-solver branch
            # above, but sourced from the standing runtime-release layout that
            # actually produced the shipped GLB instead of a one-off audit
            # export. The profile's dimensionsM/placement remain the intended
            # larger visual envelope and free-text design narrative; they are
            # not expected to equal the collision-authoritative footprint.
            if (
                not isinstance(runtime_landmark, dict)
                or runtime_landmark.get("id") != landmark["id"]
            ):
                raise ValueError(f"runtime-landmark-{index}-id-mismatch")
            dimensions = {
                "width": runtime_landmark.get("width"),
                "height": runtime_landmark.get("height"),
                "depth": runtime_landmark.get("depth"),
            }
            placement = "in-bounds-collision-authoritative"
        else:
            dimensions = landmark.get("dimensionsM")
            placement = landmark.get("placement")
        if not isinstance(dimensions, dict):
            raise ValueError(f"profile-landmark-{index}-dimensions-missing")
        target_dimensions = finite_vector(
            [dimensions.get("width"), dimensions.get("height"), dimensions.get("depth")],
            3,
        )
        if target_dimensions is None or any(value <= 0 for value in target_dimensions):
            raise ValueError(f"profile-landmark-{index}-dimensions-invalid")
        if not isinstance(placement, str) or not placement.strip():
            raise ValueError(f"profile-landmark-{index}-placement-invalid")
        contracts.append({
            "id": landmark["id"],
            "index": index,
            "targetDimensionsXYZ": target_dimensions,
            "placement": placement,
        })
    return contracts


def validate_landmark_nodes(
    document: dict[str, Any],
    owned_nodes: list[tuple[int, dict[str, Any]]],
    stage_id: str,
    lod: int,
    profile: dict[str, Any],
    canonical_stage: dict[str, Any] | None = None,
    runtime_landmarks: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    try:
        expected = expected_landmark_contracts(profile, canonical_stage, runtime_landmarks)
    except ValueError as error:
        return [], [str(error)]
    expected_by_id = {contract["id"]: contract for contract in expected}
    prefix = f"HB_{stage_id}_LOD{lod}_"
    groups: dict[str, list[tuple[int, dict[str, Any], dict[str, Any]]]] = {}
    for node_index, node in owned_nodes:
        name = str(node.get("name", ""))
        extras = node.get("extras")
        extras = extras if isinstance(extras, dict) else {}
        landmark_id = extras.get("hibanaLandmarkId")
        named_landmark = name.startswith(prefix + "LANDMARK_")
        if named_landmark and not isinstance(landmark_id, str):
            errors.append(f"landmark-node:{name}:missing-hibanaLandmarkId")
            continue
        if isinstance(landmark_id, str) and not named_landmark:
            errors.append(f"landmark-node:{name}:invalid-name")
            continue
        if isinstance(landmark_id, str):
            groups.setdefault(landmark_id, []).append((node_index, node, extras))

    actual_ids = set(groups)
    expected_ids = set(expected_by_id)
    if actual_ids != expected_ids:
        errors.append(
            "landmark-id-set:missing="
            + ",".join(sorted(expected_ids - actual_ids))
            + ";extra="
            + ",".join(sorted(actual_ids - expected_ids))
        )
    world_matrices = node_world_matrices(document)
    reports: list[dict[str, Any]] = []
    for contract in expected:
        landmark_id = contract["id"]
        group = groups.get(landmark_id, [])
        group_errors: list[str] = []
        triangles = 0
        geometry_bounds: list[tuple[float, ...]] = []
        metadata_bounds: list[tuple[float, ...]] = []
        for node_index, node, extras in group:
            name = str(node.get("name", ""))
            expected_prefix = prefix + f"LANDMARK_{contract['index']}_"
            if not name.startswith(expected_prefix):
                group_errors.append(f"node:{name}:index-name-mismatch")
            index_value = extras.get("hibanaLandmarkIndex")
            if (
                not isinstance(index_value, int)
                or isinstance(index_value, bool)
                or index_value != contract["index"]
            ):
                group_errors.append(f"node:{name}:index-mismatch:{index_value}!={contract['index']}")
            target_dimensions = finite_vector(extras.get("hibanaLandmarkTargetDimensionsXYZ"), 3)
            if target_dimensions != contract["targetDimensionsXYZ"]:
                group_errors.append(
                    f"node:{name}:target-dimensions-mismatch:{target_dimensions}!={contract['targetDimensionsXYZ']}"
                )
            if extras.get("hibanaLandmarkPlacement") != contract["placement"]:
                group_errors.append(f"node:{name}:placement-mismatch")
            declared_bounds = finite_vector(extras.get("hibanaLandmarkBounds"), 6)
            if declared_bounds is None or any(declared_bounds[axis] >= declared_bounds[axis + 3] for axis in range(3)):
                group_errors.append(f"node:{name}:invalid-declared-bounds")
            else:
                metadata_bounds.append(declared_bounds)
            mesh_index = node.get("mesh")
            if not isinstance(mesh_index, int):
                group_errors.append(f"node:{name}:missing-mesh")
            else:
                triangles += mesh_triangle_count(document, mesh_index)
            actual_bounds = node_mesh_bounds(document, node_index, world_matrices)
            if actual_bounds is None:
                group_errors.append(f"node:{name}:invalid-position-bounds")
            else:
                geometry_bounds.append(actual_bounds)

        combined_bounds = merge_bounds(geometry_bounds)
        declared_bounds = metadata_bounds[0] if metadata_bounds else None
        if len(set(metadata_bounds)) > 1:
            group_errors.append("declared-bounds-not-uniform")
        if combined_bounds is not None and declared_bounds is not None and not bounds_match(combined_bounds, declared_bounds):
            group_errors.append(
                "declared-bounds-mismatch:"
                + json.dumps(list(declared_bounds))
                + "!="
                + json.dumps([round(value, 4) for value in combined_bounds])
            )
        if triangles <= 0:
            group_errors.append("triangles-not-positive")
        errors.extend(f"{landmark_id}:{error}" for error in group_errors)
        reports.append({
            "id": landmark_id,
            "index": contract["index"],
            "nodes": len(group),
            "triangles": triangles,
            "bounds": list(combined_bounds) if combined_bounds is not None else None,
            "errors": group_errors,
        })

    valid_bounds = [
        tuple(report["bounds"])
        for report in reports
        if isinstance(report.get("bounds"), list) and len(report["bounds"]) == 6
    ]
    if len(valid_bounds) == 2:
        if valid_bounds[0] == valid_bounds[1]:
            errors.append("landmark-bounds-not-distinct")
        centroids = [
            tuple((bounds[axis] + bounds[axis + 3]) / 2 for axis in range(3))
            for bounds in valid_bounds
        ]
        centroid_distance = math.sqrt(sum((centroids[0][axis] - centroids[1][axis]) ** 2 for axis in range(3)))
        if centroid_distance <= 0.001:
            errors.append("landmark-centroids-not-distinct")
    return reports, errors


def validate_catalog(profile_document: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    profiles = profile_document.get("profiles", {})
    if not isinstance(profiles, dict):
        return {"stageCount": 0, "landmarkCount": 0, "uniqueLandmarkIds": 0, "errors": ["profiles-missing"]}
    stage_ids = tuple(profiles.keys())
    expected_set = set(EXPECTED_STAGE_IDS)
    actual_set = set(stage_ids)
    if actual_set != expected_set:
        errors.append(
            "stage-ids:missing="
            + ",".join(sorted(expected_set - actual_set))
            + ";extra="
            + ",".join(sorted(actual_set - expected_set))
        )
    landmark_ids: list[str] = []
    for stage_id in EXPECTED_STAGE_IDS:
        profile = profiles.get(stage_id)
        if not isinstance(profile, dict):
            continue
        try:
            stage_landmarks, _, _ = expected_profile_metadata(profile)
        except ValueError as error:
            errors.append(f"{stage_id}:{error}")
            continue
        if len(stage_landmarks) != 2:
            errors.append(f"{stage_id}:landmark-count:{len(stage_landmarks)}!=2")
        for landmark_id in stage_landmarks:
            if not landmark_id.startswith(f"{stage_id}-"):
                errors.append(f"{stage_id}:foreign-landmark-id:{landmark_id}")
            landmark_ids.append(landmark_id)
    unique_ids = set(landmark_ids)
    if len(landmark_ids) != 62:
        errors.append(f"landmark-count:{len(landmark_ids)}!=62")
    if len(unique_ids) != 62:
        errors.append(f"unique-landmark-ids:{len(unique_ids)}!=62")
    return {
        "stageCount": len(stage_ids),
        "landmarkCount": len(landmark_ids),
        "uniqueLandmarkIds": len(unique_ids),
        "errors": errors,
    }


def validate_lod_asset(
    path: Path,
    stage_id: str,
    lod: int,
    profile: dict[str, Any],
    max_bytes: int,
    generator_version: str = GENERATOR_VERSION,
    generator_sha: str = EXPECTED_GENERATOR_SHA,
    canonical_stage: dict[str, Any] | None = None,
    placement_provenance: dict[str, str] | None = None,
    runtime_landmarks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    result: dict[str, Any] = {"lod": lod, "path": str(path), "errors": errors}
    if not path.is_file():
        errors.append("missing-file")
        return result
    byte_count = path.stat().st_size
    result["bytes"] = byte_count
    if byte_count > max_bytes:
        errors.append(f"file-size:{byte_count}>{max_bytes}")
    try:
        document = load_glb_document(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"invalid-glb:{error}")
        return result

    triangles = total_triangle_count(document)
    result["triangles"] = triangles
    if triangles <= 0:
        errors.append("no-triangles")
    expected_landmarks, expected_archetype, expected_target = expected_profile_metadata(profile)
    nodes = document.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []
    prefix = f"HB_{stage_id}_LOD{lod}_"
    owned_nodes = [
        (node_index, node)
        for node_index, node in enumerate(nodes)
        if isinstance(node, dict) and str(node.get("name", "")).startswith(prefix)
    ]
    result["ownedNodes"] = len(owned_nodes)
    if not owned_nodes:
        errors.append("missing-owned-nodes")
    terrain_mesh_indices: set[int] = set()
    metadata_variants: set[tuple[tuple[str, ...], Any, Any, Any, Any]] = set()
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node[{node_index}]:invalid-node")
            continue
        extras = node.get("extras")
        if not isinstance(extras, dict):
            errors.append(f"node[{node_index}]:missing-extras")
            continue
        if extras.get("hibanaGeneratorVersion") != generator_version:
            errors.append(
                f"node[{node_index}]:generator-version:{extras.get('hibanaGeneratorVersion')}!={generator_version}"
            )
        if extras.get("hibanaGeneratorSha") != generator_sha:
            errors.append(f"node[{node_index}]:generator-sha-mismatch")
        if placement_provenance is not None:
            expected_extras = {
                "hibanaPlacementSource": placement_provenance["placementSource"],
                "hibanaPlacementSolverSha256": placement_provenance["placementSolverSha256"],
                "hibanaStageWorldCatalogSha256": placement_provenance["stageWorldCatalogSha256"],
            }
            if "stageLayoutSha256" in placement_provenance:
                expected_extras["hibanaStageLayoutSha256"] = placement_provenance[
                    "stageLayoutSha256"
                ]
            for key, expected_value in expected_extras.items():
                if extras.get(key) != expected_value:
                    errors.append(f"node[{node_index}]:{key}-mismatch")
    for node_index, node in owned_nodes:
        extras = node.get("extras")
        if not isinstance(extras, dict):
            continue
        metadata_variants.add((
            landmark_ids_from_extra(extras.get("hibanaMegaLandmarks")),
            extras.get("hibanaCityArchetype"),
            extras.get("hibanaDenseBuildingTarget"),
            extras.get("hibanaStage"),
            extras.get("hibanaLod"),
        ))
        if extras.get("hibanaExport") is not True:
            errors.append(f"node[{node_index}]:hibanaExport-not-true")
        if extras.get("hibanaMaterial") == "terrain" and isinstance(node.get("mesh"), int):
            terrain_mesh_indices.add(node["mesh"])
    expected_variant = (expected_landmarks, expected_archetype, expected_target, stage_id, lod)
    if metadata_variants != {expected_variant}:
        serialised = [
            {
                "landmarks": list(variant[0]),
                "archetype": variant[1],
                "target": variant[2],
                "stage": variant[3],
                "lod": variant[4],
            }
            for variant in sorted(metadata_variants, key=repr)
        ]
        errors.append(
            "metadata-mismatch:expected="
            + json.dumps({
                "landmarks": list(expected_landmarks),
                "archetype": expected_archetype,
                "target": expected_target,
                "stage": stage_id,
                "lod": lod,
            }, ensure_ascii=False, sort_keys=True)
            + ":actual="
            + json.dumps(serialised, ensure_ascii=False, sort_keys=True)
        )
    terrain_triangles = sum(mesh_triangle_count(document, mesh_index) for mesh_index in terrain_mesh_indices)
    result["terrainTriangles"] = terrain_triangles
    if terrain_triangles <= 0:
        errors.append("missing-real-mesh-horizon-terrain")
    landmark_reports, landmark_errors = validate_landmark_nodes(
        document,
        owned_nodes,
        stage_id,
        lod,
        profile,
        canonical_stage,
        runtime_landmarks,
    )
    result["landmarks"] = landmark_reports
    errors.extend(landmark_errors)
    return result


def stage_manifest_entry(
    manifest: dict[str, Any],
    stage_id: str,
    expected_layout_sha: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return None, ["manifest-assets-missing"]
    matches = [
        entry for entry in assets
        if isinstance(entry, dict)
        and entry.get("id") == f"stage-{stage_id}"
        and entry.get("stages") == [stage_id]
    ]
    if len(matches) != 1:
        errors.append(f"manifest-entry-count:{len(matches)}!=1")
        return None, errors
    entry = matches[0]
    if entry.get("replacesDistantMatte") is not True:
        errors.append("real-mesh-horizon-flag-not-true")
    if entry.get("replacesProceduralProps") is not True:
        errors.append("procedural-prop-replacement-flag-not-true")
    if entry.get("replacesProceduralStageShell") is not True:
        errors.append("procedural-stage-shell-replacement-flag-not-true")
    provenance = entry.get("stageProvenance")
    if not isinstance(provenance, dict):
        errors.append("stage-provenance-missing")
    else:
        if provenance.get("placementSource") not in (
            "runtime-release",
            "canonical-solver-v2-authoring",
        ):
            errors.append("stage-provenance-placement-source-invalid")
        for field in ("placementSolverSha256", "stageWorldCatalogSha256"):
            if not is_sha256(provenance.get(field)):
                errors.append(f"stage-provenance-{field}-invalid")
        for field in (
            "placementSource",
            "placementSolverSha256",
            "stageWorldCatalogSha256",
        ):
            if manifest.get(field) is not None and provenance.get(field) != manifest.get(field):
                errors.append(f"stage-provenance-{field}-mismatch")
        layout_sha = provenance.get("stageLayoutSha256")
        asset_sha = provenance.get("assetSha256")
        if layout_sha is not None and not is_sha256(layout_sha):
            errors.append("stage-provenance-stageLayoutSha256-invalid")
        if asset_sha is not None and not is_sha256(asset_sha):
            errors.append("stage-provenance-assetSha256-invalid")
        if layout_sha is None and asset_sha is None:
            errors.append("stage-provenance-stage-identity-missing")
        if expected_layout_sha is not None and layout_sha != expected_layout_sha:
            errors.append("stage-provenance-stageLayoutSha256-mismatch")
    expected_urls = [
        f"stages/{stage_id}-lod0.glb",
        f"stages/{stage_id}-lod1.glb",
        f"stages/{stage_id}-lod2.glb",
    ]
    urls = [entry.get("url")]
    lod_entries = entry.get("lods", [])
    if isinstance(lod_entries, list):
        urls.extend(lod.get("url") for lod in lod_entries if isinstance(lod, dict))
    if urls != expected_urls:
        errors.append(f"lod-urls:{urls}!={expected_urls}")
    return entry, errors


def validate_manifest_contract(
    manifest: dict[str, Any],
    generator_version: str = GENERATOR_VERSION,
    generator_sha: str = EXPECTED_GENERATOR_SHA,
) -> list[str]:
    errors: list[str] = []
    if manifest.get("generatorVersion") != generator_version:
        errors.append(
            f"manifest-generator-version:{manifest.get('generatorVersion')}!={generator_version}"
        )
    if manifest.get("generatorSha") != generator_sha:
        errors.append("manifest-generator-sha-mismatch")
    if manifest.get("placementSource") not in (
        "runtime-release",
        "canonical-solver-v2-authoring",
    ):
        errors.append("manifest-placementSource-invalid")
    for field in ("placementSolverSha256", "stageWorldCatalogSha256"):
        if not is_sha256(manifest.get(field)):
            errors.append(f"manifest-{field}-invalid")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return errors + ["manifest-assets-missing"]
    if len(assets) != len(EXPECTED_STAGE_IDS):
        errors.append(f"manifest-asset-count:{len(assets)}!={len(EXPECTED_STAGE_IDS)}")
    valid_entries = [entry for entry in assets if isinstance(entry, dict)]
    if len(valid_entries) != len(assets):
        errors.append("manifest-non-object-entry")
    expected_asset_ids = {f"stage-{stage_id}" for stage_id in EXPECTED_STAGE_IDS}
    actual_asset_ids = {
        entry.get("id")
        for entry in valid_entries
        if isinstance(entry.get("id"), str)
    }
    if actual_asset_ids != expected_asset_ids:
        errors.append(
            "manifest-asset-ids:missing="
            + ",".join(sorted(expected_asset_ids - actual_asset_ids))
            + ";extra="
            + ",".join(sorted(actual_asset_ids - expected_asset_ids))
        )
    declared_stage_ids: list[str] = []
    for entry in valid_entries:
        stages = entry.get("stages")
        if isinstance(stages, list) and len(stages) == 1 and isinstance(stages[0], str):
            declared_stage_ids.append(stages[0])
        else:
            errors.append(f"{entry.get('id')}:stages-must-be-exact-singleton")
    expected_stage_set = set(EXPECTED_STAGE_IDS)
    declared_stage_set = set(declared_stage_ids)
    if declared_stage_set != expected_stage_set or len(declared_stage_ids) != len(EXPECTED_STAGE_IDS):
        errors.append(
            "manifest-stage-ids:missing="
            + ",".join(sorted(expected_stage_set - declared_stage_set))
            + ";extra="
            + ",".join(sorted(declared_stage_set - expected_stage_set))
            + f";count={len(declared_stage_ids)}"
        )
    for stage_id in EXPECTED_STAGE_IDS:
        _, stage_errors = stage_manifest_entry(manifest, stage_id)
        errors.extend(f"{stage_id}:{error}" for error in stage_errors)
    return errors


def validate_thumbnail_contract(thumbnail_dir: Path) -> list[str]:
    if not thumbnail_dir.is_dir():
        return [f"stage-thumbnails-missing:{thumbnail_dir}"]
    actual_ids = {
        thumbnail.stem
        for thumbnail in thumbnail_dir.iterdir()
        if thumbnail.is_file() and thumbnail.suffix == ".webp"
    }
    expected_ids = set(EXPECTED_STAGE_IDS)
    if actual_ids == expected_ids:
        return []
    return [
        "thumbnail-stage-ids:missing="
        + ",".join(sorted(expected_ids - actual_ids))
        + ";extra="
        + ",".join(sorted(actual_ids - expected_ids))
    ]


def validate_release(
    profiles_path: Path,
    manifest_path: Path,
    selected_stage_ids: list[str] | None = None,
    max_bytes: int = 5_500_000,
    max_lod0_triangles: int = 260_000,
    max_lod1_ratio: float = 0.45,
    max_lod2_ratio: float = 0.12,
    thumbnail_dir: Path | None = None,
    layouts_path: Path | None = None,
    runtime_layouts_path: Path | None = RUNTIME_LAYOUTS_PATH,
) -> dict[str, Any]:
    profiles_document = load_json(profiles_path)
    manifest = load_json(manifest_path)
    catalog_report = validate_catalog(profiles_document)
    profiles = profiles_document.get("profiles", {})
    canonical_stages: dict[str, dict[str, Any]] = {}
    runtime_landmarks_by_stage = load_runtime_landmark_placements(runtime_layouts_path)
    placement_provenance: dict[str, str] | None = None
    if layouts_path is not None:
        layout_document = load_json(layouts_path)
        if layout_document.get("placementSource") != "canonical-solver-v2-authoring":
            raise ValueError("canonical-layout-root-placement-source-invalid")
        layout_stages = layout_document.get("stages")
        if not isinstance(layout_stages, list) or len(layout_stages) != len(EXPECTED_STAGE_IDS):
            raise ValueError("canonical-layout-stage-count-invalid")
        for stage in layout_stages:
            if not isinstance(stage, dict) or not isinstance(stage.get("id"), str):
                raise ValueError("canonical-layout-stage-invalid")
            if stage["id"] in canonical_stages:
                raise ValueError(f"canonical-layout-duplicate-stage:{stage['id']}")
            canonical_stages[stage["id"]] = stage
        if set(canonical_stages) != set(EXPECTED_STAGE_IDS):
            raise ValueError("canonical-layout-stage-id-set-invalid")
        placement_manifest = load_json(
            PROJECT_ROOT / "tools/blender/generated/stage-placement.manifest.json"
        )
        placement_provenance = {
            "placementSource": "canonical-solver-v2-authoring",
            "placementSolverSha256": str(placement_manifest.get("solverSha256", "")),
            "stageWorldCatalogSha256": str(placement_manifest.get("catalogSha256", "")),
        }
        for key, expected_value in placement_provenance.items():
            if layout_document.get(key) != expected_value:
                raise ValueError(f"canonical-layout-{key}-mismatch")
    requested = selected_stage_ids or list(EXPECTED_STAGE_IDS)
    stages: list[dict[str, Any]] = []
    global_errors = list(catalog_report["errors"])
    global_errors.extend(validate_manifest_contract(manifest))
    if placement_provenance is not None:
        for key, expected_value in placement_provenance.items():
            if manifest.get(key) != expected_value:
                global_errors.append(f"manifest-{key}-mismatch")
    global_errors.extend(validate_thumbnail_contract(
        thumbnail_dir or PROJECT_ROOT / "public/assets/stage-thumbs"
    ))
    unknown = [stage_id for stage_id in requested if stage_id not in EXPECTED_STAGE_IDS]
    if unknown:
        global_errors.append("unknown-stage-ids:" + ",".join(unknown))

    for stage_id in requested:
        stage_errors: list[str] = []
        report: dict[str, Any] = {"id": stage_id, "lods": [], "errors": stage_errors}
        profile = profiles.get(stage_id) if isinstance(profiles, dict) else None
        if not isinstance(profile, dict):
            stage_errors.append("profile-missing")
            stages.append(report)
            continue
        expected_layout_sha = (
            canonical_json_sha256(canonical_stages[stage_id])
            if stage_id in canonical_stages
            else None
        )
        manifest_entry, manifest_errors = stage_manifest_entry(
            manifest,
            stage_id,
            expected_layout_sha,
        )
        stage_errors.extend(manifest_errors)
        stage_placement_provenance = placement_provenance
        if placement_provenance is not None and expected_layout_sha is not None:
            stage_placement_provenance = {
                **placement_provenance,
                "stageLayoutSha256": expected_layout_sha,
            }
        lod_reports = [
            validate_lod_asset(
                manifest_path.parent / f"stages/{stage_id}-lod{lod}.glb",
                stage_id,
                lod,
                profile,
                max_bytes,
                GENERATOR_VERSION,
                EXPECTED_GENERATOR_SHA,
                canonical_stages.get(stage_id),
                stage_placement_provenance,
                runtime_landmarks_by_stage.get(stage_id),
            )
            for lod in range(3)
        ]
        report["lods"] = lod_reports
        for lod_report in lod_reports:
            stage_errors.extend(f"lod{lod_report['lod']}:{error}" for error in lod_report["errors"])
        if all(isinstance(lod_report.get("triangles"), int) for lod_report in lod_reports):
            lod0, lod1, lod2 = (int(lod_report["triangles"]) for lod_report in lod_reports)
            if lod0 > max_lod0_triangles:
                stage_errors.append(f"lod0-triangles:{lod0}>{max_lod0_triangles}")
            if lod0 <= 0:
                stage_errors.append("lod0-triangles-zero")
            else:
                lod1_ratio = lod1 / lod0
                lod2_ratio = lod2 / lod0
                report["lodRatios"] = {"lod1": lod1_ratio, "lod2": lod2_ratio}
                if lod1_ratio > max_lod1_ratio + 1e-12:
                    stage_errors.append(f"lod1-ratio:{lod1_ratio:.6f}>{max_lod1_ratio:.6f}")
                if lod2_ratio > max_lod2_ratio + 1e-12:
                    stage_errors.append(f"lod2-ratio:{lod2_ratio:.6f}>{max_lod2_ratio:.6f}")
        stages.append(report)
    ok = not global_errors and all(not stage["errors"] for stage in stages)
    return {"ok": ok, "catalog": catalog_report, "stages": stages, "errors": global_errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        type=Path,
        default=PROJECT_ROOT / "tools/blender/stage-profiles.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "public/assets/aaa/manifest.json",
    )
    parser.add_argument(
        "--thumbnails",
        type=Path,
        default=PROJECT_ROOT / "public/assets/stage-thumbs",
    )
    parser.add_argument("--stage", action="append", dest="stages", help="validate one stage; repeatable")
    parser.add_argument("--max-bytes", type=int, default=5_500_000)
    parser.add_argument("--max-lod0-triangles", type=int, default=260_000)
    parser.add_argument("--max-lod1-ratio", type=float, default=0.45)
    parser.add_argument("--max-lod2-ratio", type=float, default=0.12)
    parser.add_argument(
        "--layouts",
        type=Path,
        help="canonical solver-v2 authoring layout used by this isolated Blender build",
    )
    parser.add_argument(
        "--runtime-layouts",
        type=Path,
        default=RUNTIME_LAYOUTS_PATH,
        help=(
            "runtime-release layout build_all_stages.py reads for in-bounds "
            "landmark placement; pass a nonexistent path to disable this "
            "cross-check"
        ),
    )
    args = parser.parse_args()
    try:
        report = validate_release(
            args.profiles,
            args.manifest,
            args.stages,
            args.max_bytes,
            args.max_lod0_triangles,
            args.max_lod1_ratio,
            args.max_lod2_ratio,
            args.thumbnails,
            args.layouts,
            args.runtime_layouts,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        report = {"ok": False, "catalog": None, "stages": [], "errors": [str(error)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
