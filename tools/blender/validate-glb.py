#!/usr/bin/env python3
"""Validate generated Hibana GLB structure and release budgets."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

try:
    from tools.blender.validate_dense_stage_assets import (
        EXPECTED_GENERATOR_SHA,
        EXPECTED_STAGE_IDS,
        GENERATOR_VERSION,
        is_sha256,
    )
except ModuleNotFoundError:  # direct execution outside the repository cwd
    from validate_dense_stage_assets import (  # type: ignore[no-redef]
        EXPECTED_GENERATOR_SHA,
        EXPECTED_STAGE_IDS,
        GENERATOR_VERSION,
        is_sha256,
    )


SURFACE_KEYS = (
    "wall_weathered",
    "wall_warm",
    "wall_cool",
    "wall_alt",
    "obstacle",
    "natural",
    "terrain",
    "floor",
    "road",
    "wall",
    "water",
    "roof",
    "wood",
)


def surface_key(name: str) -> str | None:
    return next((key for key in SURFACE_KEYS if name.endswith(f"_{key}")), None)


def load_document(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("file is too small")
    magic, version, declared = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67 or version != 2 or declared != len(raw):
        raise ValueError("invalid GLB header")
    length, kind = struct.unpack_from("<II", raw, 12)
    if kind != 0x4E4F534A or 20 + length > len(raw):
        raise ValueError("invalid JSON chunk")
    return json.loads(raw[20:20 + length].decode("utf-8").rstrip(" \t\r\n\0"))


def inspect(
    path: Path,
    generator_version: str = GENERATOR_VERSION,
    generator_sha: str = EXPECTED_GENERATOR_SHA,
) -> dict:
    document = load_document(path)
    accessors = document.get("accessors", [])
    primitives = [primitive for mesh in document.get("meshes", []) for primitive in mesh.get("primitives", [])]
    triangles = 0
    vertices = 0
    for primitive in primitives:
        position = primitive.get("attributes", {}).get("POSITION")
        indices = primitive.get("indices")
        if isinstance(position, int) and position < len(accessors):
            vertices += int(accessors[position].get("count", 0))
        if isinstance(indices, int) and indices < len(accessors):
            triangles += int(accessors[indices].get("count", 0)) // 3
        elif isinstance(position, int) and position < len(accessors):
            triangles += int(accessors[position].get("count", 0)) // 3
    surface_materials = []
    pbr_errors = []
    for material in document.get("materials", []):
        name = material.get("name", "")
        kind = surface_key(name)
        if kind is None:
            continue
        surface_materials.append(kind)
        pbr = material.get("pbrMetallicRoughness", {})
        if "metallicRoughnessTexture" not in pbr:
            pbr_errors.append(f"{name}:roughness-map")
        if "normalTexture" not in material:
            pbr_errors.append(f"{name}:normal-map")
        if kind == "water" and material.get("alphaMode") != "BLEND":
            pbr_errors.append(f"{name}:alpha-blend")
    metadata_errors = []
    nodes = document.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        metadata_errors.append("missing-nodes")
        nodes = []
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            metadata_errors.append(f"node[{node_index}]:invalid")
            continue
        extras = node.get("extras")
        if not isinstance(extras, dict):
            metadata_errors.append(f"node[{node_index}]:missing-extras")
            continue
        if extras.get("hibanaGeneratorVersion") != generator_version:
            metadata_errors.append(f"node[{node_index}]:generator-version")
        if extras.get("hibanaGeneratorSha") != generator_sha:
            metadata_errors.append(f"node[{node_index}]:generator-sha")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "nodes": len(document.get("nodes", [])),
        "meshes": len(document.get("meshes", [])),
        "primitives": len(primitives),
        "materials": len(document.get("materials", [])),
        "vertices": vertices,
        "triangles": triangles,
        "surfaceMaterials": len(surface_materials),
        "surfaceMaterialKeys": sorted(set(surface_materials)),
        "pbrErrors": pbr_errors,
        "metadataErrors": metadata_errors,
    }


def validate_manifest(path: Path, assets: list[Path], expected_count: int | None) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    entries = document.get("assets", [])
    errors = []
    if document.get("generatorVersion") != GENERATOR_VERSION:
        errors.append(f"generator-version:{document.get('generatorVersion')}!={GENERATOR_VERSION}")
    if document.get("generatorSha") != EXPECTED_GENERATOR_SHA:
        errors.append("generator-sha-mismatch")
    if document.get("placementSource") not in (
        "runtime-release",
        "canonical-solver-v2-authoring",
    ):
        errors.append("placement-source-invalid")
    for field in ("placementSolverSha256", "stageWorldCatalogSha256"):
        if not is_sha256(document.get(field)):
            errors.append(f"{field}-invalid")
    if not isinstance(entries, list):
        return {"path": str(path), "entries": 0, "errors": errors + ["assets-not-array"]}
    valid_entries = [entry for entry in entries if isinstance(entry, dict)]
    if len(valid_entries) != len(entries):
        errors.append("non-object-asset-entry")
    ids = [entry.get("id") for entry in valid_entries]
    if len(ids) != len(set(ids)):
        errors.append("duplicate-asset-id")
    contract_count = len(EXPECTED_STAGE_IDS)
    if expected_count is not None and expected_count != contract_count:
        errors.append(f"expected-count-override:{expected_count}!={contract_count}")
    if len(entries) != contract_count:
        errors.append(f"asset-count:{len(entries)}!={contract_count}")
    expected_asset_ids = {f"stage-{stage_id}" for stage_id in EXPECTED_STAGE_IDS}
    actual_asset_ids = {asset_id for asset_id in ids if isinstance(asset_id, str)}
    if actual_asset_ids != expected_asset_ids:
        errors.append(
            "asset-ids:missing="
            + ",".join(sorted(expected_asset_ids - actual_asset_ids))
            + ";extra="
            + ",".join(sorted(actual_asset_ids - expected_asset_ids))
        )
    root = path.parent
    referenced = set()
    declared_stage_ids = []
    for entry in valid_entries:
        entry_id = entry.get("id")
        stages = entry.get("stages")
        if not isinstance(stages, list) or len(stages) != 1 or not isinstance(stages[0], str):
            errors.append(f"{entry_id}:stages-must-be-exact-singleton")
            stage_id = None
        else:
            stage_id = stages[0]
            declared_stage_ids.append(stage_id)
            if entry_id != f"stage-{stage_id}":
                errors.append(f"{entry_id}:stage-id-mismatch:{stage_id}")
        for field, label in (
            ("replacesDistantMatte", "distant-matte-gate"),
            ("replacesProceduralProps", "procedural-props-gate"),
            ("replacesProceduralStageShell", "procedural-stage-shell-gate"),
        ):
            if entry.get(field) is not True:
                errors.append(f"{entry_id}:{label}")
        provenance = entry.get("stageProvenance")
        if not isinstance(provenance, dict):
            errors.append(f"{entry_id}:stage-provenance-missing")
        else:
            if provenance.get("placementSource") not in (
                "runtime-release",
                "canonical-solver-v2-authoring",
            ):
                errors.append(f"{entry_id}:stage-provenance-placement-source-invalid")
            for field in ("placementSolverSha256", "stageWorldCatalogSha256"):
                if not is_sha256(provenance.get(field)):
                    errors.append(f"{entry_id}:stage-provenance-{field}-invalid")
            for field in (
                "placementSource",
                "placementSolverSha256",
                "stageWorldCatalogSha256",
            ):
                if provenance.get(field) != document.get(field):
                    errors.append(f"{entry_id}:stage-provenance-{field}-mismatch")
            layout_sha = provenance.get("stageLayoutSha256")
            asset_sha = provenance.get("assetSha256")
            if layout_sha is not None and not is_sha256(layout_sha):
                errors.append(f"{entry_id}:stage-provenance-stageLayoutSha256-invalid")
            if asset_sha is not None and not is_sha256(asset_sha):
                errors.append(f"{entry_id}:stage-provenance-assetSha256-invalid")
            if layout_sha is None and asset_sha is None:
                errors.append(f"{entry_id}:stage-provenance-stage-identity-missing")
        lods = entry.get("lods", [])
        urls = [entry.get("url")]
        if isinstance(lods, list):
            urls.extend(lod.get("url") for lod in lods if isinstance(lod, dict))
        if stage_id is not None:
            expected_urls = [
                f"stages/{stage_id}-lod0.glb",
                f"stages/{stage_id}-lod1.glb",
                f"stages/{stage_id}-lod2.glb",
            ]
            if urls != expected_urls:
                errors.append(f"{entry_id}:lod-urls")
        for url in urls:
            if not isinstance(url, str):
                errors.append(f"{entry_id}:missing-url")
                continue
            target = (root / url).resolve()
            referenced.add(target)
            if not target.is_file():
                errors.append(f"missing:{url}")
    expected_stage_set = set(EXPECTED_STAGE_IDS)
    declared_stage_set = set(declared_stage_ids)
    if declared_stage_set != expected_stage_set or len(declared_stage_ids) != contract_count:
        errors.append(
            "stage-ids:missing="
            + ",".join(sorted(expected_stage_set - declared_stage_set))
            + ";extra="
            + ",".join(sorted(declared_stage_set - expected_stage_set))
            + f";count={len(declared_stage_ids)}"
        )
    thumbnail_dir = path.parent.parent / "stage-thumbs"
    if not thumbnail_dir.is_dir():
        errors.append(f"missing-stage-thumbs:{thumbnail_dir}")
    else:
        thumbnail_ids = {
            thumbnail.stem
            for thumbnail in thumbnail_dir.iterdir()
            if thumbnail.is_file() and thumbnail.suffix == ".webp"
        }
        if thumbnail_ids != expected_stage_set:
            errors.append(
                "thumbnail-stage-ids:missing="
                + ",".join(sorted(expected_stage_set - thumbnail_ids))
                + ";extra="
                + ",".join(sorted(thumbnail_ids - expected_stage_set))
            )
    lod0_assets = {asset.resolve() for asset in assets}
    unreferenced = sorted(str(asset) for asset in lod0_assets if asset not in referenced)
    if unreferenced:
        errors.extend(f"unreferenced:{asset}" for asset in unreferenced)
    return {
        "path": str(path),
        "entries": len(entries),
        "generatorVersion": document.get("generatorVersion"),
        "generatorSha": document.get("generatorSha"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--max-bytes", type=int, default=5_500_000)
    parser.add_argument("--max-triangles", type=int, default=260_000)
    parser.add_argument("--max-materials", type=int, default=24)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-count", type=int)
    args = parser.parse_args()
    reports = []
    failed = False
    for path in args.paths:
        try:
            report = inspect(path)
            errors = []
            if report["bytes"] > args.max_bytes:
                errors.append("file-size")
            if report["triangles"] > args.max_triangles:
                errors.append("triangles")
            if report["materials"] > args.max_materials:
                errors.append("materials")
            errors.extend(report.pop("pbrErrors", []))
            errors.extend(report.pop("metadataErrors", []))
            report["errors"] = errors
        except Exception as exc:  # noqa: BLE001
            report = {"path": str(path), "errors": [str(exc)]}
        failed = failed or bool(report["errors"])
        reports.append(report)
    manifest_report = None
    if args.manifest:
        try:
            manifest_report = validate_manifest(args.manifest, args.paths, args.expect_count)
        except Exception as exc:  # noqa: BLE001
            manifest_report = {"path": str(args.manifest), "errors": [str(exc)]}
        failed = failed or bool(manifest_report["errors"])
    print(json.dumps({"ok": not failed, "assets": reports, "manifest": manifest_report}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
