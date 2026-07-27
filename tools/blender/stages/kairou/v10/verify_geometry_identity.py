#!/usr/bin/env python3
"""Prove that a Kairou material pass did not change scene geometry.

The release candidate is allowed to replace material textures and scalar PBR
response only.  This gate compares decoded accessor values, primitive topology,
node transforms, node metadata, and scene hierarchy instead of relying on GLB
byte identity (which naturally changes when images are repacked).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from audit_collision_alignment import accessor_array, read_glb


def digest(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    hasher = hashlib.sha256()
    hasher.update(str(contiguous.dtype).encode("ascii"))
    hasher.update(str(contiguous.shape).encode("ascii"))
    hasher.update(contiguous.tobytes())
    return hasher.hexdigest()


def accessor_signature(document: dict[str, Any], binary: bytes, index: int) -> dict[str, Any]:
    accessor = document["accessors"][index]
    values = accessor_array(document, binary, index)
    return {
        "componentType": accessor["componentType"],
        "type": accessor["type"],
        "count": accessor["count"],
        "normalized": bool(accessor.get("normalized", False)),
        "valuesSha256": digest(values),
    }


def canonical_json_numbers(value: Any) -> Any:
    """Treat JSON integers and equivalent floats as the same metadata value.

    glTF-Transform serialises an extras value such as ``0.0`` as ``0``.  JSON
    does not distinguish those numerically, so the proof digest must not turn
    that harmless encoding normalisation into a geometry failure.
    """
    if isinstance(value, dict):
        return {key: canonical_json_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical_json_numbers(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return "0" if value == 0 else format(float(value), ".17g")
    return value


def immutable_signature(path: Path) -> dict[str, Any]:
    document, binary = read_glb(path)
    meshes = []
    for mesh in document.get("meshes", []):
        primitives = []
        for primitive in mesh.get("primitives", []):
            attributes = {
                semantic: accessor_signature(document, binary, accessor_index)
                for semantic, accessor_index in sorted(primitive.get("attributes", {}).items())
            }
            indices = primitive.get("indices")
            primitives.append({
                "mode": int(primitive.get("mode", 4)),
                "attributes": attributes,
                "indices": accessor_signature(document, binary, indices)
                if isinstance(indices, int)
                else None,
                "targets": [
                    {
                        semantic: accessor_signature(document, binary, accessor_index)
                        for semantic, accessor_index in sorted(target.items())
                    }
                    for target in primitive.get("targets", [])
                ],
            })
        meshes.append({
            "name": mesh.get("name"),
            "weights": mesh.get("weights"),
            "extras": mesh.get("extras"),
            "primitives": primitives,
        })

    nodes = []
    for node in document.get("nodes", []):
        nodes.append({
            "name": node.get("name"),
            "mesh": node.get("mesh"),
            "skin": node.get("skin"),
            "camera": node.get("camera"),
            "children": node.get("children", []),
            "matrix": node.get("matrix"),
            "translation": node.get("translation"),
            "rotation": node.get("rotation"),
            "scale": node.get("scale"),
            "weights": node.get("weights"),
            "extras": node.get("extras"),
        })

    scenes = [
        {"name": scene.get("name"), "nodes": scene.get("nodes", []), "extras": scene.get("extras")}
        for scene in document.get("scenes", [])
    ]
    return {
        "defaultScene": document.get("scene"),
        "scenes": scenes,
        "nodes": nodes,
        "meshes": meshes,
        "skins": document.get("skins", []),
        "animations": document.get("animations", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    baseline = immutable_signature(args.baseline)
    candidate = immutable_signature(args.candidate)
    identical = baseline == candidate
    baseline_json = json.dumps(canonical_json_numbers(baseline), sort_keys=True, separators=(",", ":"))
    candidate_json = json.dumps(canonical_json_numbers(candidate), sort_keys=True, separators=(",", ":"))
    report = {
        "schemaVersion": 1,
        "status": "PASS" if identical else "FAIL",
        "policy": "decoded geometry, topology, transforms, hierarchy and node extras are immutable",
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "baselineSemanticSha256": hashlib.sha256(baseline_json.encode("utf-8")).hexdigest(),
        "candidateSemanticSha256": hashlib.sha256(candidate_json.encode("utf-8")).hexdigest(),
        "nodeCount": len(candidate["nodes"]),
        "meshCount": len(candidate["meshes"]),
        "primitiveCount": sum(len(mesh["primitives"]) for mesh in candidate["meshes"]),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
