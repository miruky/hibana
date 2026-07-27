#!/usr/bin/env python3
"""Inspect and validate Hibana's original, rigged enemy-soldier GLB pack.

This validator intentionally reads only the glTF JSON chunk.  It therefore works
without importing unknown-license reference assets into Blender and without
decoding their embedded textures.  The same report format is used for reference
measurement and for strict release validation of Hibana-authored exports.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any


REQUIRED_VARIANTS = {
    "rifleman",
    "breacher",
    "scout",
    "marksman",
    "support",
    "medic",
}

REQUIRED_JOINTS = {
    "root",
    "pelvis",
    "spine_01",
    "spine_02",
    "neck",
    "head",
    "clavicle_l",
    "upper_arm_l",
    "forearm_l",
    "hand_l",
    "clavicle_r",
    "upper_arm_r",
    "forearm_r",
    "hand_r",
    "thigh_l",
    "shin_l",
    "foot_l",
    "thigh_r",
    "shin_r",
    "foot_r",
    "weapon",
    "magazine",
}

REQUIRED_ANIMATIONS = {
    "AN_Soldier_Idle",
    "AN_Soldier_RifleReady",
    "AN_Soldier_Aim",
    "AN_Soldier_Fire",
    "AN_Soldier_Reload",
    "AN_Soldier_WalkForward",
    "AN_Soldier_WalkBackward",
    "AN_Soldier_StrafeLeft",
    "AN_Soldier_StrafeRight",
    "AN_Soldier_RunForward",
    "AN_Soldier_HitFront",
    "AN_Soldier_HitBack",
    "AN_Soldier_DeathFront",
    "AN_Soldier_DeathBack",
}


def load_document(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("file-too-small")
    magic, version, declared = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67 or version != 2 or declared != len(raw):
        raise ValueError("invalid-glb-header")
    json_length, json_kind = struct.unpack_from("<II", raw, 12)
    if json_kind != 0x4E4F534A or 20 + json_length > len(raw):
        raise ValueError("invalid-json-chunk")
    return json.loads(raw[20 : 20 + json_length].decode("utf-8").rstrip(" \t\r\n\0"))


def finite_vector(value: Any, size: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == size
        and all(isinstance(component, (int, float)) and math.isfinite(component) for component in value)
    )


def primitive_metrics(document: dict[str, Any]) -> tuple[int, int, int, list[list[float]]]:
    accessors = document.get("accessors", [])
    primitive_count = 0
    triangles = 0
    vertices = 0
    position_bounds: list[list[float]] = []
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            primitive_count += 1
            position_index = primitive.get("attributes", {}).get("POSITION")
            index_index = primitive.get("indices")
            if isinstance(position_index, int) and 0 <= position_index < len(accessors):
                accessor = accessors[position_index]
                vertices += int(accessor.get("count", 0))
                minimum = accessor.get("min")
                maximum = accessor.get("max")
                if finite_vector(minimum, 3) and finite_vector(maximum, 3):
                    position_bounds.append([*minimum, *maximum])
            if isinstance(index_index, int) and 0 <= index_index < len(accessors):
                triangles += int(accessors[index_index].get("count", 0)) // 3
            elif isinstance(position_index, int) and 0 <= position_index < len(accessors):
                triangles += int(accessors[position_index].get("count", 0)) // 3
    return primitive_count, vertices, triangles, position_bounds


def merged_bounds(bounds: list[list[float]]) -> dict[str, list[float]] | None:
    if not bounds:
        return None
    minimum = [min(item[axis] for item in bounds) for axis in range(3)]
    maximum = [max(item[axis + 3] for item in bounds) for axis in range(3)]
    return {
        "min": minimum,
        "max": maximum,
        "size": [maximum[axis] - minimum[axis] for axis in range(3)],
    }


def animation_duration(document: dict[str, Any], animation: dict[str, Any]) -> float:
    accessors = document.get("accessors", [])
    duration = 0.0
    for sampler in animation.get("samplers", []):
        input_index = sampler.get("input")
        if not isinstance(input_index, int) or not 0 <= input_index < len(accessors):
            continue
        maximum = accessors[input_index].get("max")
        if finite_vector(maximum, 1):
            duration = max(duration, float(maximum[0]))
    return duration


def node_variant(node: dict[str, Any]) -> str | None:
    extras = node.get("extras")
    if isinstance(extras, dict) and isinstance(extras.get("variantId"), str):
        return extras["variantId"]
    return None


def inspect(path: Path) -> dict[str, Any]:
    document = load_document(path)
    primitives, vertices, triangles, bounds = primitive_metrics(document)
    nodes = document.get("nodes", [])
    skins = document.get("skins", [])
    animations = document.get("animations", [])
    joint_indices = {
        joint
        for skin in skins
        for joint in skin.get("joints", [])
        if isinstance(joint, int) and 0 <= joint < len(nodes)
    }
    joints = sorted(
        node.get("name", "")
        for index, node in enumerate(nodes)
        if index in joint_indices and isinstance(node.get("name"), str)
    )
    variants = sorted({variant for node in nodes if (variant := node_variant(node))})
    skin_joint_sets = {
        tuple(joint for joint in skin.get("joints", []) if isinstance(joint, int))
        for skin in skins
    }
    uris = []
    for collection_name in ("buffers", "images"):
        for item in document.get(collection_name, []):
            uri = item.get("uri")
            if isinstance(uri, str):
                uris.append(uri)
    animation_report = [
        {
            "name": animation.get("name", ""),
            "duration": round(animation_duration(document, animation), 6),
            "channels": len(animation.get("channels", [])),
            "samplers": len(animation.get("samplers", [])),
        }
        for animation in animations
    ]
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "generator": document.get("asset", {}).get("generator"),
        "extensionsUsed": document.get("extensionsUsed", []),
        "scenes": len(document.get("scenes", [])),
        "nodes": len(nodes),
        "meshes": len(document.get("meshes", [])),
        "primitives": primitives,
        "vertices": vertices,
        "triangles": triangles,
        "materials": len(document.get("materials", [])),
        "textures": len(document.get("textures", [])),
        "images": len(document.get("images", [])),
        "skins": len(skins),
        "skinJointSetCount": len(skin_joint_sets),
        "jointCount": len(joint_indices),
        "joints": joints,
        "variants": variants,
        "animations": animation_report,
        "bounds": merged_bounds(bounds),
        "externalUris": uris,
    }


def validate_release(report: dict[str, Any], lod: int) -> list[str]:
    errors: list[str] = []
    max_triangles = {0: 90_000, 1: 42_000, 2: 18_000}[lod]
    max_bytes = {0: 5_500_000, 1: 3_500_000, 2: 2_500_000}[lod]
    if report["bytes"] > max_bytes:
        errors.append(f"file-size:{report['bytes']}>{max_bytes}")
    if report["triangles"] > max_triangles:
        errors.append(f"triangles:{report['triangles']}>{max_triangles}")
    if report["materials"] > 8:
        errors.append(f"materials:{report['materials']}>8")
    # Meshopt may duplicate the tiny skin descriptor per SkinnedMesh while all
    # descriptors still target the same 22-bone hierarchy. The hierarchy, not
    # the number of equivalent descriptors, is the actual sharing contract.
    if not 1 <= report["skins"] <= len(REQUIRED_VARIANTS):
        errors.append(f"skin-count:{report['skins']}")
    if report.get("skinJointSetCount") != 1:
        errors.append(f"shared-joint-hierarchy:{report.get('skinJointSetCount')}")
    joint_set = set(report["joints"])
    missing_joints = sorted(REQUIRED_JOINTS - joint_set)
    if missing_joints:
        errors.append("missing-joints:" + ",".join(missing_joints))
    if report["jointCount"] > 32:
        errors.append(f"joint-budget:{report['jointCount']}>32")
    missing_variants = sorted(REQUIRED_VARIANTS - set(report["variants"]))
    if missing_variants:
        errors.append("missing-variants:" + ",".join(missing_variants))
    animation_names = {item["name"] for item in report["animations"]}
    missing_animations = sorted(REQUIRED_ANIMATIONS - animation_names)
    if missing_animations:
        errors.append("missing-animations:" + ",".join(missing_animations))
    for animation in report["animations"]:
        if animation["name"] in REQUIRED_ANIMATIONS:
            if animation["duration"] <= 0.0:
                errors.append(f"zero-duration:{animation['name']}")
            if animation["channels"] <= 0:
                errors.append(f"no-channels:{animation['name']}")
    if report["externalUris"]:
        errors.append("external-uri:" + ",".join(report["externalUris"]))
    bounds = report.get("bounds")
    if not isinstance(bounds, dict) or not finite_vector(bounds.get("size"), 3):
        errors.append("missing-bounds")
    elif "EXT_meshopt_compression" not in report.get("extensionsUsed", []):
        # glTF is Y-up; six variants overlap at the origin by design.
        height = float(bounds["size"][1])
        if not 1.65 <= height <= 2.10:
            errors.append(f"height:{height:.3f}")
    return errors


def validate_manifest(path: Path, reports: list[dict[str, Any]]) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if document.get("packVersion") != 1:
        errors.append("pack-version")
    variants = document.get("variants")
    if not isinstance(variants, list) or set(variants) != REQUIRED_VARIANTS:
        errors.append("manifest-variants")
    animations = document.get("animations")
    if not isinstance(animations, list) or not REQUIRED_ANIMATIONS.issubset(animations):
        errors.append("manifest-animations")
    lods = document.get("lods")
    if not isinstance(lods, list) or len(lods) != 3:
        errors.append("manifest-lods")
    else:
        root = path.parent
        for lod in lods:
            url = lod.get("url") if isinstance(lod, dict) else None
            if not isinstance(url, str) or not (root / url).is_file():
                errors.append(f"missing:{url}")
    if len(reports) == 3:
        triangle_counts = [int(report.get("triangles", 0)) for report in reports]
        if triangle_counts[0] and triangle_counts[1] > triangle_counts[0] * 0.50:
            errors.append("lod1-ratio")
        if triangle_counts[0] and triangle_counts[2] > triangle_counts[0] * 0.24:
            errors.append("lod2-ratio")
    return {"path": str(path), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--release", action="store_true", help="enforce Hibana enemy-pack budgets/contracts")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    reports = []
    failed = False
    for index, path in enumerate(args.paths):
        try:
            report = inspect(path)
            report["errors"] = validate_release(report, min(index, 2)) if args.release else []
        except Exception as exc:  # noqa: BLE001
            report = {"path": str(path), "errors": [str(exc)]}
        failed = failed or bool(report["errors"])
        reports.append(report)

    manifest_report = None
    if args.manifest:
        try:
            manifest_report = validate_manifest(args.manifest, reports)
        except Exception as exc:  # noqa: BLE001
            manifest_report = {"path": str(args.manifest), "errors": [str(exc)]}
        failed = failed or bool(manifest_report["errors"])

    print(json.dumps({"ok": not failed, "assets": reports, "manifest": manifest_report}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
