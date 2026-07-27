#!/usr/bin/env python3
"""Souko A21 private production-art candidate.

This module is an isolated, deterministic successor to Souko A20.  It keeps
the collision-authoritative 336 m layout and the two canonical landmark
identities, but removes the A20 hero meshes before building both landmarks
again from function-specific structural masses.

Production brief
----------------
* Primary proof is a compressed 1.65 m working-quay view.  The Rack-Bridge
  Storehouse owns frame-left and the Customs Sawtooth Terminal owns frame-right.
* Stackhouse is not an apartment-like tower row.  It is four unequal process
  masses: an open rack intake, a lift spine, a crusher tower and a service
  tower.  Large machinery voids, thick concrete piers, exposed trusses,
  occupied control rooms and two unequal transfer bridges define the silhouette.
* Customs is not a window-grid box.  Four full-depth, unequal sawtooth halls
  sit over deep loading chambers, exposed roof trusses and an offset customs
  control tower.  Large machine-hall apertures replace repeated window bands.
* Near, mid and far geometry remains real 3D.  The working quay includes
  freight, cover, rail, wet paving, a cargo ship, cranes and layered industrial
  horizons without raster mattes.
* Release surfaces use deterministic private base-color, roughness and tangent
  normal textures.  Water also carries authored alpha and exports as BLEND.
  Texture files, Blender files, GLBs, reports and proofs are written only below
  ``/private/tmp/hibana-blender/a21-souko-production-art``.

Connection map
--------------
* ground -> hero plinths: 0.18 m
* plinths -> concrete feet / base chambers: 0.16-0.24 m
* feet -> slabs / cores / exoskeleton: 0.08-0.20 m
* tower cores -> control rooms / crown plant: 0.10-0.20 m
* tower masses -> rack bridges: 0.18-0.24 m
* customs base -> hall piers / loading chambers: 0.16-0.22 m
* hall piers -> roof planes / glazing / trusses: 0.10-0.18 m
* quay -> rails / bollards / crane feet: 0.10-0.20 m
* ship hull -> deck -> superstructure: 0.16-0.24 m

Runtime coordinates are X/Z horizontal and Y-up, in metres.  Directional
members use explicit endpoints.  Blender imports are lazy and background-only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Mapping, Sequence


MODULE_PATH = Path(__file__).resolve()
REPO_ROOT = MODULE_PATH.parents[3]
A20_PATH = MODULE_PATH.with_name("souko_reference_a20.py")
BACKEND_PATH = MODULE_PATH.with_name("souko_reference_a18_r8.py")
VALIDATOR_PATH = REPO_ROOT / "tools/blender/validate-glb.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A20 = _load_module("hibana_souko_a20_for_a21", A20_PATH)

STAGE_ID = "souko"
REFERENCE_MATCH_VERSION = "a21-souko-production-art-v1"
REFERENCE_PATH = _A20.REFERENCE_PATH
REFERENCE_SHA256 = _A20.REFERENCE_SHA256
IMAGEGEN_REFERENCE_PATH = _A20.IMAGEGEN_REFERENCE_PATH
IMAGEGEN_REFERENCE_SHA256 = _A20.IMAGEGEN_REFERENCE_SHA256
INDEPENDENT_A20_BASELINE_SCORE = 4.65
PRIVATE_OUTPUT_ROOT = Path("/private/tmp/hibana-blender/a21-souko-production-art")
TARGET_COLLECTION = "HB_SOUKO_A21_PRIVATE"
MAP_SIZE_M = _A20.MAP_SIZE_M
PLAYER_EYE_M = 1.65
MIN_CONTACT_OVERLAP_M = _A20.MIN_CONTACT_OVERLAP_M

CANONICAL_BOUNDS = copy.deepcopy(_A20.CANONICAL_BOUNDS)
CANONICAL_ROADS = copy.deepcopy(_A20.CANONICAL_ROADS)
CANONICAL_PLAYER_SPAWNS = copy.deepcopy(_A20.CANONICAL_PLAYER_SPAWNS)
STACKHOUSE_ID = _A20.STACKHOUSE_ID
CUSTOMS_ID = _A20.CUSTOMS_ID
LANDMARKS = copy.deepcopy(_A20.LANDMARKS)

PRIMARY_CAMERA: dict[str, Any] = {
    "id": "01-a21-compressed-working-quay",
    "eye": (-192.0, PLAYER_EYE_M, 136.0),
    "target": (2.0, 39.0, 16.0),
    "lensMm": 26.0,
    "sensorWidthMm": 36.0,
    "frameOrder": (STACKHOUSE_ID, CUSTOMS_ID),
    "skyMaxFraction": 0.20,
    "roadMaxFraction": 0.24,
    "heroHorizontalFillTarget": (0.82, 0.97),
    "purpose": "Reference-ordered dual hero view from an occupied wet quay.",
}

PRIVATE_VIEWS: tuple[dict[str, Any], ...] = (
    PRIMARY_CAMERA,
    {
        "id": "02-a21-stackhouse-process-arrival",
        "eye": (-68.0, PLAYER_EYE_M, 18.0),
        "target": (80.0, 45.0, 98.0),
        "lensMm": 28.0,
        "purpose": "Unequal process masses, deep voids and bridge silhouette.",
    },
    {
        "id": "03-a21-stackhouse-rack-interior",
        "eye": (5.0, PLAYER_EYE_M, 61.0),
        "target": (44.0, 23.0, 96.0),
        "lensMm": 26.0,
        "purpose": "Human-eye rack intake with loaded decks and machinery.",
    },
    {
        "id": "04-a21-stackhouse-crown-and-bridges",
        "eye": (-50.0, PLAYER_EYE_M, 10.0),
        "target": (82.0, 68.0, 98.0),
        "lensMm": 32.0,
        "purpose": "Crown machinery, lift spine and unequal transfer bridges.",
    },
    {
        "id": "05-a21-customs-loading-court",
        "eye": (-150.0, PLAYER_EYE_M, 20.0),
        "target": (-67.0, 32.0, -61.0),
        "lensMm": 24.0,
        "purpose": "Deep loading chambers, control tower and sawtooth halls.",
    },
    {
        "id": "06-a21-customs-sawtooth-interior",
        "eye": (-95.0, PLAYER_EYE_M, 8.0),
        "target": (-68.0, 35.0, -40.0),
        "lensMm": 22.0,
        "purpose": "Full-depth roof trusses, warm machinery and unequal ridges.",
    },
    {
        "id": "07-a21-operational-quay-life",
        "eye": (-215.0, PLAYER_EYE_M, 150.0),
        "target": (-135.0, 12.0, 115.0),
        "lensMm": 28.0,
        "purpose": "Freight, cover, workers, wet paving and rail at human scale.",
    },
    {
        "id": "08-a21-ship-quay-and-cranes",
        "eye": (18.0, PLAYER_EYE_M, 236.0),
        "target": (-47.0, 16.0, 188.0),
        "lensMm": 30.0,
        "purpose": "Cargo ship broadside, quay hardware and operational cranes.",
    },
)

LOD_API = {
    0: {"label": "hero", "maxSpecs": 4800, "maxEstimatedTriangles": 220_000},
    1: {"label": "medium", "maxSpecs": 2700, "maxEstimatedTriangles": 110_000},
    2: {"label": "horizon", "maxSpecs": 1300, "maxEstimatedTriangles": 48_000},
}

MATERIALS: dict[str, dict[str, Any]] = copy.deepcopy(_A20.MATERIALS)
MATERIALS.update({
    "wet_asphalt": {
        **MATERIALS["wet_asphalt"],
        "color": (0.026, 0.033, 0.035, 1.0),
        "roughness": 0.17,
        "metallic": 0.035,
        "textureScaleM": 22.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "puddle_water": {
        **MATERIALS["puddle_water"],
        "color": (0.025, 0.060, 0.067, 0.72),
        "roughness": 0.065,
        "alpha": 0.72,
        "textureScaleM": 14.0,
        "textureStrategy": "baseColor+roughness+normal+alphaBlend",
    },
    "old_concrete": {
        **MATERIALS["old_concrete"],
        "color": (0.30, 0.285, 0.245, 1.0),
        "roughness": 0.77,
        "textureScaleM": 9.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "pale_concrete": {
        **MATERIALS["pale_concrete"],
        "color": (0.46, 0.43, 0.36, 1.0),
        "roughness": 0.69,
        "textureScaleM": 9.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "dark_concrete": {
        **MATERIALS["dark_concrete"],
        "color": (0.045, 0.055, 0.052, 1.0),
        "roughness": 0.66,
        "textureScaleM": 8.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "weathered_zinc": {
        **MATERIALS["weathered_zinc"],
        "color": (0.17, 0.23, 0.23, 1.0),
        "roughness": 0.40,
        "textureScaleM": 6.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "structural_steel": {
        **MATERIALS["structural_steel"],
        "color": (0.035, 0.044, 0.042, 1.0),
        "roughness": 0.43,
        "textureScaleM": 5.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "red_brick": {
        **MATERIALS["red_brick"],
        "color": (0.19, 0.060, 0.030, 1.0),
        "roughness": 0.80,
        "textureScaleM": 4.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "rust": {
        **MATERIALS["rust"],
        "color": (0.31, 0.070, 0.016, 1.0),
        "roughness": 0.79,
        "textureScaleM": 3.5,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "safety_orange": {
        **MATERIALS["safety_orange"],
        "color": (0.64, 0.16, 0.025, 1.0),
        "textureScaleM": 4.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "dirty_glass": {
        **MATERIALS["dirty_glass"],
        "color": (0.022, 0.070, 0.075, 0.54),
        "alpha": 0.54,
        "textureScaleM": 6.0,
        "textureStrategy": "baseColor+roughness+normal+alphaBlend",
    },
    "warm_glass": {
        **MATERIALS["warm_glass"],
        "color": (0.32, 0.066, 0.008, 1.0),
        "emission": (0.52, 0.11, 0.008, 1.0),
        "emissionStrength": 2.25,
        "textureScaleM": 6.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "paint_white": {
        **MATERIALS["paint_white"],
        "color": (0.63, 0.59, 0.50, 1.0),
        "textureScaleM": 7.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "pallet_wood": {
        **MATERIALS["pallet_wood"],
        "color": (0.22, 0.095, 0.030, 1.0),
        "textureScaleM": 2.2,
        "textureStrategy": "baseColor+roughness+normal",
    },
    "sea_water": {
        **MATERIALS["sea_water"],
        "color": (0.010, 0.070, 0.085, 0.78),
        "roughness": 0.11,
        "alpha": 0.78,
        "textureScaleM": 16.0,
        "textureStrategy": "baseColor+roughness+normal+alphaBlend",
    },
    "vegetation": {
        **MATERIALS["vegetation"],
        "textureScaleM": 2.0,
        "textureStrategy": "baseColor+roughness+normal",
    },
})

MATERIAL_EXPORT_SUFFIX = {
    "wet_asphalt": "road",
    "puddle_water": "water",
    "old_concrete": "wall_weathered",
    "pale_concrete": "wall",
    "dark_concrete": "wall_cool",
    "weathered_zinc": "roof",
    "structural_steel": "obstacle",
    "red_brick": "wall_warm",
    "rust": "wall_alt",
    "safety_orange": "trim",
    "dirty_glass": "glass",
    "warm_glass": "emissive",
    "paint_white": "wall",
    "pallet_wood": "wood",
    "sea_water": "water",
    "vegetation": "natural",
}

DEFAULT_INTEGRATION_MATERIAL_MAP = copy.deepcopy(_A20.DEFAULT_INTEGRATION_MATERIAL_MAP)
FIXED_SCORE_CATEGORIES = copy.deepcopy(_A20.FIXED_SCORE_CATEGORIES)
SpecPlan = _A20.SpecPlan
spec_bounds = _A20.spec_bounds
estimated_triangles = _A20.estimated_triangles


def _role_count(specs: Iterable[Mapping[str, Any]], role: str) -> int:
    return sum(spec["role"] == role for spec in specs)


def _copy_environment_base(plan: SpecPlan, lod: int) -> None:
    """Copy A20 environment layers while removing both A20 hero builds."""
    source = _A20.build_plan(lod)
    removed_groups = {
        STACKHOUSE_ID,
        CUSTOMS_ID,
        "souko-a20-inter-landmark-transfer",
    }
    name_map: dict[str, str] = {}
    for spec in source.specs:
        if spec["group"] in removed_groups:
            continue
        copied = dict(spec)
        copied["name"] = copied["name"].replace("souko-a20", "souko-a21-base")
        copied["group"] = copied["group"].replace("souko-a20", "souko-a21-base")
        if copied["role"].startswith("a20-"):
            copied["role"] = "a21-base-" + copied["role"][4:]
        name_map[spec["name"]] = copied["name"]
        plan.specs.append(copied)
    for connection in source.connections:
        parent = name_map.get(connection["parent"])
        child = name_map.get(connection["child"])
        if parent is None or child is None:
            continue
        copied = dict(connection)
        copied["parent"] = parent
        copied["child"] = child
        copied["id"] = copied["id"].replace("souko-a20", "souko-a21-base")
        plan.connections.append(copied)


def _guardrail(
    plan: SpecPlan,
    group: str,
    start: tuple[float, float],
    end: tuple[float, float],
    deck_y: float,
    lod: int,
    *,
    layer: str = "mid",
) -> None:
    posts = 8 if lod == 0 else 5 if lod == 1 else 3
    for height, thickness in ((0.58, 0.07), (1.12, 0.08)):
        plan.beam(
            "a21-human-scale-guardrail", "structural_steel", group,
            (start[0], deck_y + height, start[1]),
            (end[0], deck_y + height, end[1]),
            thickness, thickness, layer=layer,
        )
    for index in range(posts):
        t = index / max(1, posts - 1)
        x = start[0] + (end[0] - start[0]) * t
        z = start[1] + (end[1] - start[1]) * t
        plan.beam(
            "a21-human-scale-guardrail-post", "structural_steel", group,
            (x, deck_y - 0.05, z), (x, deck_y + 1.15, z),
            0.06, 0.06, layer=layer,
        )


def _external_stair(
    plan: SpecPlan,
    group: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
    lod: int,
) -> None:
    dx, dz = end[0] - start[0], end[2] - start[2]
    run = math.hypot(dx, dz)
    ux, uz = dx / run, dz / run
    px, pz = -uz, ux
    for side in (-1.0, 1.0):
        offset = width * 0.43 * side
        plan.beam(
            "a21-industrial-stair-stringer", "structural_steel", group,
            (start[0] + px * offset, start[1], start[2] + pz * offset),
            (end[0] + px * offset, end[1], end[2] + pz * offset),
            0.18, 0.15, layer="mid",
        )
        plan.beam(
            "a21-industrial-stair-handrail", "structural_steel", group,
            (start[0] + px * offset, start[1] + 1.0, start[2] + pz * offset),
            (end[0] + px * offset, end[1] + 1.0, end[2] + pz * offset),
            0.07, 0.07, layer="mid",
        )
    steps = 15 if lod == 0 else 8 if lod == 1 else 4
    yaw = math.atan2(pz, px)
    for index in range(steps):
        t = index / max(1, steps - 1)
        plan.box(
            "a21-industrial-stair-tread", "weathered_zinc", group,
            start[0] + dx * t,
            start[1] + (end[1] - start[1]) * t,
            start[2] + dz * t,
            width, 0.16 if lod == 0 else 0.24, 0.62,
            yaw=yaw, layer="mid",
        )


def _truss_bridge(
    plan: SpecPlan,
    group: str,
    label: str,
    start: tuple[float, float],
    end: tuple[float, float],
    bottom: float,
    top: float,
    depth: float,
    lod: int,
    *,
    role_prefix: str,
) -> tuple[str, str]:
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    yaw = math.atan2(dz, dx)
    mx, mz = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    floor = plan.box(
        f"{role_prefix}-floor", "weathered_zinc", group,
        mx, bottom + 0.34, mz, length + 3.0, 0.68, depth,
        yaw=yaw, layer="mid", name=f"{group}.{label}.floor",
    )
    roof = plan.box(
        f"{role_prefix}-roof", "structural_steel", group,
        mx, top - 0.30, mz, length + 3.0, 0.60, depth + 0.4,
        yaw=yaw, layer="mid", name=f"{group}.{label}.roof",
    )
    plan.connect(
        floor, roof, axis="frame", overlap_m=0.10,
        parent_face="portal", child_face="portal",
    )
    frames = 9 if lod == 0 else 6 if lod == 1 else 4
    for index in range(frames):
        t = index / max(1, frames - 1)
        bx, bz = start[0] + dx * t, start[1] + dz * t
        for side in (-1.0, 1.0):
            sx, sz = bx + px * depth * 0.5 * side, bz + pz * depth * 0.5 * side
            plan.beam(
                f"{role_prefix}-portal", "structural_steel", group,
                (sx, bottom + 0.15, sz), (sx, top - 0.15, sz),
                0.30 if lod == 0 else 0.44,
                0.24 if lod == 0 else 0.36, layer="mid",
            )
        plan.beam(
            f"{role_prefix}-portal", "structural_steel", group,
            (bx - px * depth * 0.5, top - 0.18, bz - pz * depth * 0.5),
            (bx + px * depth * 0.5, top - 0.18, bz + pz * depth * 0.5),
            0.30 if lod == 0 else 0.44,
            0.24 if lod == 0 else 0.36, layer="mid",
        )
    for side in (-1.0, 1.0):
        side_x = mx + px * (depth * 0.5 + 0.14) * side
        side_z = mz + pz * (depth * 0.5 + 0.14) * side
        plan.box(
            f"{role_prefix}-deep-glazing", "dirty_glass", group,
            side_x, (bottom + top) / 2, side_z,
            length + 1.8, top - bottom - 1.55, 0.20,
            yaw=yaw, layer="mid",
        )
        for bay in range(frames - 1):
            t0, t1 = bay / (frames - 1), (bay + 1) / (frames - 1)
            ax = start[0] + dx * t0 + px * depth * 0.5 * side
            az = start[1] + dz * t0 + pz * depth * 0.5 * side
            bx = start[0] + dx * t1 + px * depth * 0.5 * side
            bz = start[1] + dz * t1 + pz * depth * 0.5 * side
            low, high = bottom + 0.7, top - 0.7
            ay, by = (low, high) if (bay + (side > 0)) % 2 == 0 else (high, low)
            plan.beam(
                f"{role_prefix}-diagonal", "rust", group,
                (ax, ay, az), (bx, by, bz),
                0.16 if lod == 0 else 0.26,
                0.13 if lod == 0 else 0.21, layer="mid",
            )
    if lod < 2:
        plan.box(
            f"{role_prefix}-occupied-control-room", "warm_glass", group,
            mx + ux * length * 0.12, (bottom + top) / 2,
            mz + uz * length * 0.12,
            min(16.0, length * 0.28), top - bottom - 1.4, depth - 1.2,
            yaw=yaw, layer="mid",
        )
    return floor, roof


def _stackhouse_mass(
    plan: SpecPlan,
    *,
    label: str,
    function: str,
    x: float,
    z: float,
    width: float,
    depth: float,
    height: float,
    plinth: str,
    lod: int,
) -> dict[str, Any]:
    group = STACKHOUSE_ID
    base = plan.box(
        "a21-stackhouse-functional-mass", "old_concrete", group,
        x, 0.64, z, width + 1.2, 1.28, depth + 1.2,
        layer="mid", blocks_gameplay=True,
        name=f"{group}.{label}.functional-base",
    )
    plan.connect(
        plinth, base, axis="y", overlap_m=0.18,
        parent_face="top", child_face="bottom",
        note=f"{function} mass grounded to canonical plinth",
    )
    pier_w = 2.6 if lod == 0 else 3.2
    pier_names: list[str] = []
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            pier = plan.box(
                "a21-stackhouse-thick-concrete-pier", "pale_concrete", group,
                x + sx * (width / 2 - 1.4), height * 0.42,
                z + sz * (depth / 2 - 1.4),
                pier_w, height * 0.84, pier_w, layer="mid",
            )
            plan.connect(
                base, pier, axis="y", overlap_m=0.18,
                parent_face="top", child_face="bottom",
            )
            pier_names.append(pier)
    core_x = x + width * (0.10 if label in {"lift", "service"} else -0.08)
    core_z = z + depth * (-0.08 if label in {"intake", "crusher"} else 0.08)
    core_bottom = 15.0 if label == "intake" else 11.0
    core_top = height - (16.0 if label == "lift" else 12.0)
    core = plan.box(
        "a21-stackhouse-offset-process-core",
        "old_concrete" if label in {"intake", "crusher"} else "weathered_zinc",
        group, core_x, (core_bottom + core_top) / 2, core_z,
        width * 0.58, core_top - core_bottom, depth * 0.58,
        layer="mid", name=f"{group}.{label}.offset-core",
    )
    plan.connect(
        pier_names[0], core, axis="surface", overlap_m=0.12,
        parent_face="inner", child_face="corner",
    )

    slab_levels = {
        "intake": (15.0, 34.0, 55.0, 74.0),
        "lift": (12.0, 38.0, 66.0, 92.0),
        "crusher": (12.0, 31.0, 54.0, 77.0),
        "service": (11.0, 29.0, 50.0, 70.0),
    }[label]
    selected_levels = slab_levels if lod == 0 else slab_levels[::2] if lod == 1 else (
        slab_levels[0], slab_levels[-1],
    )
    for level_index, y in enumerate(selected_levels):
        slab = plan.box(
            "a21-stackhouse-irregular-process-slab",
            "weathered_zinc" if level_index % 2 == 0 else "structural_steel",
            group, x + (-0.8 if level_index % 2 else 0.6), y, z,
            width * (0.96 if level_index % 2 == 0 else 0.82),
            0.54 if lod == 0 else 0.78,
            depth * (0.92 if level_index % 3 else 0.78),
            layer="mid",
        )
        plan.connect(
            pier_names[level_index % len(pier_names)], slab,
            axis="surface", overlap_m=0.10,
            parent_face="side", child_face="corner",
        )

    # Broad voids replace the A20 apartment/window rhythm.
    void_levels = {
        "intake": (27.0, 52.0),
        "lift": (31.0, 70.0),
        "crusher": (29.0, 63.0),
        "service": (25.0, 55.0),
    }[label]
    for void_index, y in enumerate(void_levels[: (2 if lod < 2 else 1)]):
        void_height = 15.0 if void_index == 0 else 19.0
        plan.box(
            "a21-stackhouse-open-machinery-void", "dark_concrete", group,
            x - width * 0.305, y, z + depth * (0.10 if void_index else -0.10),
            width * 0.08, void_height, depth * 0.64,
            layer="mid",
        )
        plan.box(
            "a21-stackhouse-warm-machine-core", "warm_glass", group,
            x - width * 0.355, y - 1.0,
            z + depth * (0.10 if void_index else -0.10),
            width * 0.025, void_height * 0.50, depth * 0.36,
            layer="mid",
        )
        for side in (-1.0, 1.0):
            zz = z + depth * (0.10 if void_index else -0.10) + side * depth * 0.31
            plan.beam(
                "a21-stackhouse-machinery-void-frame", "structural_steel", group,
                (x - width * 0.36, y - void_height * 0.52, zz),
                (x - width * 0.36, y + void_height * 0.52, zz),
                0.42 if lod == 0 else 0.62,
                0.32 if lod == 0 else 0.48, layer="mid",
            )
        plan.beam(
            "a21-stackhouse-machinery-void-x-brace", "rust", group,
            (x - width * 0.37, y - void_height * 0.44, z - depth * 0.28),
            (x - width * 0.37, y + void_height * 0.44, z + depth * 0.28),
            0.30 if lod == 0 else 0.46,
            0.22 if lod == 0 else 0.36, layer="mid",
        )
        if lod < 2:
            for deck_index, deck_offset in enumerate((-0.25, 0.22)):
                deck_y = y + void_height * deck_offset
                plan.box(
                    "a21-stackhouse-void-occupied-process-deck",
                    "weathered_zinc", group,
                    x - width * 0.31, deck_y,
                    z + depth * (0.10 if void_index else -0.10),
                    width * 0.18, 0.32, depth * 0.56,
                    layer="mid",
                )
                plan.beam(
                    "a21-stackhouse-void-warm-inspection-line",
                    "warm_glass", group,
                    (
                        x - width * 0.372,
                        deck_y + 0.78,
                        z - depth * 0.24,
                    ),
                    (
                        x - width * 0.372,
                        deck_y + 0.78,
                        z + depth * 0.24,
                    ),
                    0.16 if lod == 0 else 0.24,
                    0.12 if lod == 0 else 0.18,
                    layer="mid",
                )
        plan.beam(
            "a21-stackhouse-machinery-void-x-brace", "rust", group,
            (x - width * 0.37, y + void_height * 0.44, z - depth * 0.28),
            (x - width * 0.37, y - void_height * 0.44, z + depth * 0.28),
            0.30 if lod == 0 else 0.46,
            0.22 if lod == 0 else 0.36, layer="mid",
        )

    # North control room is intentionally one large occupied aperture.
    control_y = min(height - 20.0, 66.0 + (8.0 if label == "lift" else 0.0))
    control = plan.box(
        "a21-stackhouse-cantilever-control-room", "weathered_zinc", group,
        x, control_y, z + depth * 0.51,
        width * 0.70, 7.5, 5.8, layer="mid",
    )
    control_glass = plan.box(
        "a21-stackhouse-control-room-glazing", "warm_glass", group,
        x, control_y, z + depth * 0.51 + 3.0,
        width * 0.54, 3.0, 0.20, layer="mid",
    )
    plan.connect(
        core, control, axis="surface", overlap_m=0.14,
        parent_face="north", child_face="rear",
    )
    plan.connect(
        control, control_glass, axis="surface", overlap_m=0.08,
        parent_face="front", child_face="rear",
    )

    # External frame makes the silhouette structural at 1280 px.
    for z_side in (-1.0, 1.0):
        zz = z + z_side * depth * 0.47
        plan.beam(
            "a21-stackhouse-exoskeleton-leg", "structural_steel", group,
            (x - width * 0.52, 0.5, zz),
            (x - width * 0.38, height - 5.0, zz),
            0.72 if lod == 0 else 1.0,
            0.58 if lod == 0 else 0.82, layer="mid",
        )
        plan.beam(
            "a21-stackhouse-exoskeleton-diagonal", "rust", group,
            (x - width * 0.52, 4.0, zz),
            (x + width * 0.42, height * 0.62, zz),
            0.44 if lod == 0 else 0.68,
            0.34 if lod == 0 else 0.52, layer="mid",
        )

    # Two occupied maintenance decks, large process risers and floor-scale
    # equipment give each mass an operational mid layer without reverting to
    # repeated apartment windows.
    if lod < 2:
        for deck_index, deck_y in enumerate((31.0, 57.0)):
            deck_z = z + depth * (0.47 if deck_index == 0 else -0.47)
            plan.box(
                "a21-stackhouse-occupied-maintenance-deck",
                "weathered_zinc", group,
                x, deck_y, deck_z,
                width * (0.82 if deck_index == 0 else 0.68),
                0.32, 1.75, layer="mid",
            )
            _guardrail(
                plan, group,
                (x - width * (0.39 if deck_index == 0 else 0.32), deck_z + 0.72),
                (x + width * (0.39 if deck_index == 0 else 0.32), deck_z + 0.72),
                deck_y + 0.14, lod,
            )
        for pipe_side in (-1.0, 1.0):
            pipe_z = z + pipe_side * depth * 0.28
            plan.cylinder(
                "a21-stackhouse-grounded-process-riser", "rust", group,
                x - width * 0.43, height * 0.34, pipe_z,
                0.44 if lod == 0 else 0.62, height * 0.66,
                12 if lod == 0 else 8, top_radius=0.36 if lod == 0 else 0.52,
                layer="mid",
            )
            plan.beam(
                "a21-stackhouse-overhead-process-duct", "weathered_zinc", group,
                (x - width * 0.43, height * 0.62, pipe_z),
                (x + width * 0.18, height * 0.62 + pipe_side * 2.5, pipe_z),
                0.52 if lod == 0 else 0.76,
                0.48 if lod == 0 else 0.70, layer="mid",
            )
        for equipment_side in (-1.0, 1.0):
            plan.box(
                "a21-stackhouse-floor-machine-skid", "dark_concrete", group,
                x + width * 0.14, 4.0,
                z + equipment_side * depth * 0.22,
                width * 0.28, 6.0, depth * 0.24, layer="mid",
            )

    head = plan.box(
        "a21-stackhouse-function-specific-headhouse",
        "dark_concrete" if label in {"lift", "crusher"} else "weathered_zinc",
        group, x + width * 0.10, height - 6.0, z - depth * 0.05,
        width * (0.62 if label != "lift" else 0.50),
        12.0, depth * (0.58 if label != "intake" else 0.46),
        layer="mid", name=f"{group}.{label}.headhouse",
    )
    plan.connect(
        core, head, axis="y", overlap_m=0.18,
        parent_face="top", child_face="bottom",
    )
    cap = plan.box(
        "a21-stackhouse-weather-cap", "weathered_zinc", group,
        x + width * 0.10, height + 0.12, z - depth * 0.05,
        width * 0.70, 0.64, depth * 0.65, layer="mid",
        name=f"{group}.{label}.cap",
    )
    plan.connect(
        head, cap, axis="y", overlap_m=0.14,
        parent_face="top", child_face="bottom",
    )
    if lod < 2:
        radius = 4.0 if label == "intake" else 5.3 if label == "lift" else 3.4
        drum = plan.cylinder(
            "a21-stackhouse-crown-process-drum", "weathered_zinc", group,
            x - width * 0.10, height + 3.1, z,
            radius, 5.8, 16 if lod == 0 else 10,
            top_radius=radius * 0.82, layer="mid",
        )
        plan.connect(
            cap, drum, axis="y", overlap_m=0.10,
            parent_face="top", child_face="bottom",
        )
        plan.beam(
            "a21-stackhouse-crown-service-mast", "structural_steel", group,
            (x + width * 0.20, height, z),
            (x + width * 0.20, height + 12.0 + 2.0 * len(label), z),
            0.30, 0.30, layer="mid",
        )
    if lod < 2:
        # Unequal weather chases break up the large process shells without
        # becoming apartment-style window repetition.
        plan.box(
            "a21-stackhouse-weather-repair-chase",
            "rust" if label in {"intake", "service"} else "dark_concrete",
            group,
            x - width * 0.505, height * (0.60 if label != "lift" else 0.69),
            z + depth * (0.14 if label in {"intake", "crusher"} else -0.17),
            0.18, height * (0.24 if label != "service" else 0.18),
            depth * (0.15 if label != "crusher" else 0.22),
            layer="mid",
        )
        plan.box(
            "a21-stackhouse-weather-repair-panel",
            "weathered_zinc" if label in {"intake", "lift"} else "rust",
            group,
            x + width * (-0.13 if label in {"intake", "service"} else 0.16),
            height * (0.43 if label != "crusher" else 0.50),
            z + depth * 0.505,
            width * (0.16 if label != "lift" else 0.23),
            height * (0.18 if label != "intake" else 0.25),
            0.18,
            layer="mid",
        )
    return {
        "label": label,
        "x": x,
        "z": z,
        "width": width,
        "depth": depth,
        "height": height,
        "base": base,
        "core": core,
        "cap": cap,
    }


def _build_stackhouse(plan: SpecPlan, lod: int) -> None:
    group = STACKHOUSE_ID
    plinth = plan.box(
        "a21-stackhouse-collision-anchored-plinth", "old_concrete", group,
        80.8, 0.24, 96.0, 102.8, 0.64, 64.8,
        layer="mid", blocks_gameplay=True, name=f"{group}.a21.plinth",
    )
    configs = (
        ("intake", "open rack intake", 44.0, 95.0, 27.0, 55.0, 86.0),
        ("lift", "vertical lift spine", 69.5, 108.0, 24.0, 31.0, 121.0),
        ("crusher", "crusher and separator tower", 96.0, 83.5, 27.0, 38.0, 106.0),
        ("service", "service and control tower", 119.0, 108.0, 20.0, 31.0, 92.0),
    )
    masses = {
        label: _stackhouse_mass(
            plan, label=label, function=function, x=x, z=z, width=width,
            depth=depth, height=height, plinth=plinth, lod=lod,
        )
        for label, function, x, z, width, depth, height in configs
    }

    main_floor, _ = _truss_bridge(
        plan, group, "main-rack-bridge",
        (masses["intake"]["x"], masses["intake"]["z"]),
        (masses["service"]["x"], masses["service"]["z"]),
        62.0, 80.0, 12.0, lod,
        role_prefix="a21-stackhouse-castle-rack-bridge",
    )
    plan.connect(
        masses["intake"]["core"], main_floor, axis="surface", overlap_m=0.22,
        parent_face="upper", child_face="start",
    )
    plan.connect(
        masses["service"]["core"], main_floor, axis="surface", overlap_m=0.22,
        parent_face="upper", child_face="end",
    )
    crown_floor, _ = _truss_bridge(
        plan, group, "crown-lift-bridge",
        (masses["lift"]["x"], masses["lift"]["z"]),
        (masses["crusher"]["x"], masses["crusher"]["z"]),
        89.0, 103.0, 8.5, lod,
        role_prefix="a21-stackhouse-crown-lift-bridge",
    )
    plan.connect(
        masses["lift"]["core"], crown_floor, axis="surface", overlap_m=0.20,
        parent_face="upper", child_face="start",
    )
    plan.connect(
        masses["crusher"]["core"], crown_floor, axis="surface", overlap_m=0.20,
        parent_face="upper", child_face="end",
    )

    # Three-storey open rack intake occupies the entire west face.
    rack_xs = (30.8, 37.5, 44.2, 50.9, 57.6)
    rack_zs = (74.0, 96.0, 118.0)
    rack_levels = (8.0, 17.0, 27.0, 38.0, 50.0, 61.0)
    x_selection = rack_xs if lod == 0 else rack_xs[::2]
    levels = rack_levels if lod == 0 else rack_levels[::2] if lod == 1 else (
        rack_levels[0], rack_levels[-1],
    )
    for x in x_selection:
        for z in rack_zs:
            upright = plan.beam(
                "a21-stackhouse-open-rack-upright", "structural_steel", group,
                (x, 0.42, z), (x, 63.0, z),
                0.42 if lod == 0 else 0.64,
                0.38 if lod == 0 else 0.56, layer="mid",
            )
            plan.connect(
                plinth, upright, axis="y", overlap_m=0.16,
                parent_face="top", child_face="bottom",
            )
    for z in rack_zs:
        for level_index, y in enumerate(levels):
            plan.beam(
                "a21-stackhouse-loaded-rack-chord",
                "safety_orange" if level_index in {1, 3} else "structural_steel",
                group, (x_selection[0], y, z), (x_selection[-1], y, z),
                0.30 if lod == 0 else 0.46,
                0.24 if lod == 0 else 0.38, layer="mid",
            )
        for bay in range(len(x_selection) - 1):
            for level in range(len(levels) - 1):
                ay, by = (
                    (levels[level], levels[level + 1])
                    if (bay + level) % 2 == 0
                    else (levels[level + 1], levels[level])
                )
                plan.beam(
                    "a21-stackhouse-open-rack-cross-brace", "rust", group,
                    (x_selection[bay], ay, z),
                    (x_selection[bay + 1], by, z),
                    0.18 if lod == 0 else 0.28,
                    0.14 if lod == 0 else 0.22, layer="mid",
                )
    if lod < 2:
        cargo_xs = (33.0, 38.5, 44.0, 49.5, 55.0) if lod == 0 else (37.0, 51.0)
        for zi, z in enumerate(rack_zs):
            for li, y in enumerate(levels[:-1]):
                for xi, x in enumerate(cargo_xs):
                    if (xi + li + zi) % 3 == 1:
                        continue
                    plan.box(
                        "a21-stackhouse-rack-cargo",
                        "safety_orange" if (xi + li) % 4 == 0 else "weathered_zinc",
                        group, x, y + 1.55, z,
                        5.8, 2.75, 2.42, yaw=math.pi / 2, layer="mid",
                    )
        _external_stair(
            plan, group, (25.0, 0.35, 75.0), (27.0, 19.0, 91.0), 2.8, lod,
        )
        _external_stair(
            plan, group, (27.0, 19.0, 91.0), (27.0, 42.0, 111.0), 2.8, lod,
        )
    for catwalk_y in (19.0, 42.0):
        plan.box(
            "a21-stackhouse-rack-maintenance-gallery", "weathered_zinc", group,
            27.0, catwalk_y, 96.0, 3.6, 0.46, 58.0, layer="mid",
        )
        if lod < 2:
            _guardrail(
                plan, group, (25.3, 68.0), (25.3, 124.0),
                catwalk_y + 0.12, lod,
            )


def _build_customs(plan: SpecPlan, lod: int) -> None:
    group = CUSTOMS_ID
    cx, cz = -68.0, -67.8
    front_z, rear_z = -104.8, -32.8
    plinth = plan.box(
        "a21-customs-collision-anchored-plinth", "old_concrete", group,
        cx, 0.24, cz, 90.8, 0.64, 76.8,
        layer="mid", blocks_gameplay=True, name=f"{group}.a21.plinth",
    )
    base = plan.box(
        "a21-customs-bonded-loading-base", "red_brick", group,
        cx, 6.1, cz, 89.2, 12.0, 74.8,
        layer="mid", blocks_gameplay=True, name=f"{group}.a21.base",
    )
    plan.connect(
        plinth, base, axis="y", overlap_m=0.20,
        parent_face="top", child_face="bottom",
    )
    deck = plan.box(
        "a21-customs-hall-bearing-deck", "old_concrete", group,
        cx, 12.2, cz, 90.0, 0.65, 75.4,
        layer="mid", name=f"{group}.a21.deck",
    )
    plan.connect(
        base, deck, axis="y", overlap_m=0.18,
        parent_face="top", child_face="bottom",
    )

    left_edge = cx - 42.5
    tooth_width = 21.25
    peak_heights = (62.0, 69.0, 65.0, 73.0)
    valley_heights = (47.0, 48.0, 46.0, 50.0)
    for tooth in range(4):
        left = left_edge + tooth * tooth_width
        right = left + tooth_width
        peak_x = left + tooth_width * (0.28 + tooth * 0.035)
        bay_x = (left + right) / 2
        peak_y = peak_heights[tooth]
        valley_y = valley_heights[tooth]
        void = plan.box(
            "a21-customs-deep-machine-hall-void", "dark_concrete", group,
            bay_x, 30.0, cz,
            tooth_width - 2.0, 34.0, 66.0,
            layer="mid", name=f"{group}.a21.hall.{tooth + 1}.void",
        )
        plan.connect(
            deck, void, axis="y", overlap_m=0.18,
            parent_face="top", child_face="bottom",
        )
        for edge_x in (left + 1.0, right - 1.0):
            pier = plan.box(
                "a21-customs-monumental-hall-pier", "pale_concrete", group,
                edge_x, 30.0, cz, 2.0, 35.5, 69.0, layer="mid",
            )
            plan.connect(
                deck, pier, axis="y", overlap_m=0.16,
                parent_face="top", child_face="bottom",
            )
        roof = plan.panel(
            "a21-customs-full-depth-sawtooth-roof", "weathered_zinc", group,
            (
                (peak_x, peak_y, front_z),
                (right, valley_y, front_z),
                (right, valley_y, rear_z),
                (peak_x, peak_y, rear_z),
            ),
            0.36, layer="mid", name=f"{group}.a21.tooth.{tooth + 1}.roof",
        )
        glass = plan.panel(
            "a21-customs-full-depth-sawtooth-glazing", "dirty_glass", group,
            (
                (left, valley_y, front_z),
                (peak_x, peak_y, front_z),
                (peak_x, peak_y, rear_z),
                (left, valley_y, rear_z),
            ),
            0.28, layer="mid", name=f"{group}.a21.tooth.{tooth + 1}.glass",
        )
        rear_gable = plan.panel(
            "a21-customs-rear-sawtooth-gable", "dirty_glass", group,
            (
                (left + 0.3, valley_y + 0.2, rear_z + 0.30),
                (peak_x, peak_y - 0.2, rear_z + 0.30),
                (right - 0.3, valley_y + 0.2, rear_z + 0.30),
            ),
            0.24, layer="mid",
        )
        plan.connect(
            void, roof, axis="surface", overlap_m=0.16,
            parent_face="top", child_face="eave",
        )
        plan.connect(
            void, glass, axis="surface", overlap_m=0.14,
            parent_face="top", child_face="lower-edge",
        )
        plan.connect(
            void, rear_gable, axis="surface", overlap_m=0.12,
            parent_face="rear", child_face="bottom",
        )
        frames = 8 if lod == 0 else 5 if lod == 1 else 3
        for frame in range(frames):
            z = front_z + (rear_z - front_z) * frame / max(1, frames - 1)
            for start, end in (
                ((left + 0.3, valley_y + 0.2, z), (peak_x, peak_y - 0.2, z)),
                ((peak_x, peak_y - 0.2, z), (right - 0.3, valley_y + 0.2, z)),
            ):
                plan.beam(
                    "a21-customs-sawtooth-internal-truss",
                    "structural_steel" if frame % 2 == 0 else "rust",
                    group, start, end,
                    0.24 if lod == 0 else 0.38,
                    0.19 if lod == 0 else 0.30, layer="mid",
                )
        if lod < 2:
            for purlin in range(4 if lod == 0 else 2):
                t = (purlin + 1) / (5 if lod == 0 else 3)
                x = peak_x + (right - peak_x) * t
                y = peak_y + (valley_y - peak_y) * t
                plan.beam(
                    "a21-customs-long-roof-purlin", "structural_steel", group,
                    (x, y - 0.20, front_z), (x, y - 0.20, rear_z),
                    0.18, 0.15, layer="mid",
                )
        # One unequal operational aperture per hall, not a repeated window grid.
        aperture_widths = (18.0, 9.0, 19.0, 12.0)
        aperture_heights = (22.0, 12.0, 25.0, 15.0)
        aperture_centres = (30.0, 22.0, 33.0, 25.5)
        aperture_y = aperture_centres[tooth]
        aperture = plan.box(
            "a21-customs-monumental-machine-aperture", "dark_concrete", group,
            bay_x, aperture_y, rear_z + 0.62,
            aperture_widths[tooth] + 1.8,
            aperture_heights[tooth] + 1.8, 1.15, layer="mid",
        )
        glazing = plan.box(
            "a21-customs-machine-aperture-glazing", "dirty_glass", group,
            bay_x, aperture_y, rear_z + 1.25,
            aperture_widths[tooth] * 0.88,
            aperture_heights[tooth] * 0.84, 0.18, layer="mid",
        )
        warm_core = plan.box(
            "a21-customs-occupied-machine-aperture", "warm_glass", group,
            bay_x + (-1.5 if tooth % 2 == 0 else 1.0),
            aperture_y - 1.0, rear_z + 1.28,
            aperture_widths[tooth] * 0.42,
            aperture_heights[tooth] * 0.30, 0.20, layer="mid",
        )
        plan.connect(
            void, aperture, axis="surface", overlap_m=0.12,
            parent_face="rear", child_face="inner",
        )
        plan.connect(
            aperture, glazing, axis="surface", overlap_m=0.08,
            parent_face="front", child_face="rear",
        )
        plan.connect(
            glazing, warm_core, axis="surface", overlap_m=0.06,
            parent_face="front", child_face="rear",
        )
        for side in (-1.0, 1.0):
            plan.beam(
                "a21-customs-machine-aperture-x-truss", "structural_steel", group,
                (
                    bay_x - aperture_widths[tooth] * 0.47,
                    aperture_y + side * aperture_heights[tooth] * 0.43,
                    rear_z + 1.52,
                ),
                (
                    bay_x + aperture_widths[tooth] * 0.47,
                    aperture_y - side * aperture_heights[tooth] * 0.43,
                    rear_z + 1.52,
                ),
                0.32 if lod == 0 else 0.48,
                0.24 if lod == 0 else 0.38, layer="mid",
            )
        if lod < 2:
            deck_offsets = (-0.23, 0.17) if tooth % 2 == 0 else (-0.16, 0.27)
            for deck_index, deck_offset in enumerate(deck_offsets):
                deck_y = aperture_y + aperture_heights[tooth] * deck_offset
                interior_deck = plan.box(
                    "a21-customs-occupied-machine-service-deck",
                    "weathered_zinc", group,
                    bay_x + (0.8 if deck_index else -0.6),
                    deck_y, rear_z + 1.62,
                    aperture_widths[tooth] * (
                        0.72 if deck_index == 0 else 0.54
                    ),
                    0.34, 2.4 + tooth * 0.35, layer="mid",
                )
                plan.connect(
                    aperture, interior_deck,
                    axis="surface", overlap_m=0.08,
                    parent_face="interior", child_face="rear",
                )
                plan.beam(
                    "a21-customs-warm-machine-service-line",
                    "warm_glass", group,
                    (
                        bay_x - aperture_widths[tooth] * 0.28,
                        deck_y + 0.82,
                        rear_z + 2.92,
                    ),
                    (
                        bay_x + aperture_widths[tooth] * (
                            0.21 if deck_index else 0.31
                        ),
                        deck_y + 0.82,
                        rear_z + 2.92,
                    ),
                    0.18 if lod == 0 else 0.26,
                    0.14 if lod == 0 else 0.22,
                    layer="mid",
                )

    # Deep asymmetric loading chambers on the canonical entrance elevation.
    bay_specs = (
        (-104.0, 14.0, 9.0, 7.0),
        (-84.0, 10.0, 7.0, 4.5),
        (-61.0, 17.0, 12.0, 8.0),
        (-35.0, 12.0, 8.5, 5.5),
    )
    for index, (x, width, height, canopy_depth) in enumerate(
        bay_specs if lod < 2 else bay_specs[::2]
    ):
        recess = plan.box(
            "a21-customs-deep-loading-chamber", "dark_concrete", group,
            x, 6.4, rear_z + 0.68, width + 1.8, height, 1.3,
            layer="near",
        )
        warm = plan.box(
            "a21-customs-warm-loading-chamber", "warm_glass", group,
            x, 6.1, rear_z + 1.42,
            width - 2.0, max(4.0, height - 3.0), 0.22, layer="near",
        )
        canopy = plan.box(
            "a21-customs-unequal-loading-canopy", "weathered_zinc", group,
            x, height + 1.2, rear_z + canopy_depth * 0.45,
            width + 3.2, 0.48, canopy_depth, layer="near",
        )
        plan.connect(
            base, recess, axis="surface", overlap_m=0.12,
            parent_face="rear", child_face="inner",
        )
        plan.connect(
            recess, warm, axis="surface", overlap_m=0.08,
            parent_face="front", child_face="rear",
        )
        plan.connect(
            base, canopy, axis="surface", overlap_m=0.12,
            parent_face="rear", child_face="inner-edge",
        )
        plan.box(
            "a21-customs-dock-leveller", "structural_steel", group,
            x, 0.32, rear_z + 4.0, width - 2.5, 0.24, 5.0,
            layer="near",
        )
        if lod < 2:
            _A20._add_pallet_stack(plan, group, x + width * 0.35, rear_z + 7.0, lod)

    # Offset customs tower is a layered operational silhouette, not a roof box.
    tower_x, tower_z = -51.0, -62.0
    tower_base = plan.box(
        "a21-customs-control-tower-buttress", "old_concrete", group,
        tower_x, 55.0, tower_z, 18.0, 40.0, 17.0,
        layer="mid", name=f"{group}.a21.control.base",
    )
    plan.connect(
        deck, tower_base, axis="y", overlap_m=0.18,
        parent_face="top", child_face="bottom",
    )
    tower_mid = plan.box(
        "a21-customs-control-tower-occupied-deck", "warm_glass", group,
        tower_x - 1.0, 78.0, tower_z,
        23.0, 8.5, 22.0, layer="mid",
        name=f"{group}.a21.control.occupied",
    )
    tower_top = plan.box(
        "a21-customs-control-tower-watch-room", "dirty_glass", group,
        tower_x + 1.5, 91.0, tower_z - 1.0,
        16.0, 12.0, 16.0, layer="mid",
        name=f"{group}.a21.control.watch",
    )
    roof = plan.box(
        "a21-customs-control-tower-roof", "weathered_zinc", group,
        tower_x + 1.5, 97.5, tower_z - 1.0,
        20.0, 0.8, 20.0, layer="mid",
        name=f"{group}.a21.control.roof",
    )
    plan.connect(
        tower_base, tower_mid, axis="y", overlap_m=0.18,
        parent_face="top", child_face="bottom",
    )
    plan.connect(
        tower_mid, tower_top, axis="y", overlap_m=0.16,
        parent_face="top", child_face="bottom",
    )
    plan.connect(
        tower_top, roof, axis="y", overlap_m=0.14,
        parent_face="top", child_face="bottom",
    )
    plan.beam(
        "a21-customs-control-tower-antenna", "structural_steel", group,
        (tower_x + 1.5, 97.8, tower_z - 1.0),
        (tower_x + 1.5, 112.0, tower_z - 1.0),
        0.32, 0.32, layer="mid",
    )
    for chimney_index, (x, height) in enumerate(((-105.0, 91.0), (-24.0, 102.0))):
        chimney = plan.cylinder(
            "a21-customs-weathered-industrial-chimney", "rust", group,
            x, height / 2, -54.0 + chimney_index * 9.0,
            1.6 if lod == 0 else 2.0, height,
            16 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=1.05, layer="mid",
        )
        plan.connect(
            deck, chimney, axis="y", overlap_m=0.18,
            parent_face="top", child_face="bottom",
        )
        if lod < 2:
            for collar_y in (height * 0.32, height * 0.62, height * 0.84):
                plan.cylinder(
                    "a21-customs-chimney-collar", "paint_white", group,
                    x, collar_y, -54.0 + chimney_index * 9.0,
                    1.82 if lod == 0 else 2.2, 0.65,
                    16 if lod == 0 else 10,
                    top_radius=1.82 if lod == 0 else 2.2, layer="mid",
                )
    if lod < 2:
        _external_stair(
            plan, group, (-115.0, 0.4, -26.0), (-114.0, 22.0, -35.0), 2.8, lod,
        )
        _external_stair(
            plan, group, (-114.0, 22.0, -35.0), (-108.0, 44.0, -33.5), 2.8, lod,
        )
    plan.box(
        "a21-customs-rear-maintenance-catwalk", "weathered_zinc", group,
        cx, 43.8, rear_z + 2.6, 86.0, 0.48, 4.0, layer="mid",
    )
    if lod < 2:
        _guardrail(
            plan, group, (cx - 41.5, rear_z + 4.4),
            (cx + 41.5, rear_z + 4.4), 44.0, lod,
        )
        for pipe_index, (pipe_x, pipe_y, pipe_z, pipe_height) in enumerate((
            (-111.6, 29.0, -70.0, 48.0),
            (-112.0, 21.0, -53.0, 32.0),
            (-24.1, 27.0, -78.0, 43.0),
        )):
            plan.cylinder(
                "a21-customs-external-process-riser",
                "rust" if pipe_index != 1 else "weathered_zinc",
                group, pipe_x, pipe_y, pipe_z,
                0.46 + pipe_index * 0.08, pipe_height,
                12 if lod == 0 else 8,
                top_radius=0.38 + pipe_index * 0.06, layer="mid",
            )
            plan.beam(
                "a21-customs-external-riser-return",
                "weathered_zinc", group,
                (pipe_x, pipe_y + pipe_height * 0.45, pipe_z),
                (
                    pipe_x + (7.0 if pipe_index < 2 else -7.0),
                    pipe_y + pipe_height * 0.45,
                    pipe_z,
                ),
                0.42 if lod == 0 else 0.58,
                0.36 if lod == 0 else 0.52,
                layer="mid",
            )


def _build_inter_landmark_transfer(plan: SpecPlan, lod: int) -> None:
    group = "souko-a21-bonded-transfer"
    floor, _ = _truss_bridge(
        plan, group, "customs-bonded-conveyor",
        (31.0, 78.0), (-22.0, -31.0),
        29.0, 39.5, 7.2, lod,
        role_prefix="a21-bonded-inter-landmark-transfer",
    )
    plan.connect(
        f"{STACKHOUSE_ID}.intake.offset-core", floor,
        axis="surface", overlap_m=0.20,
        parent_face="southwest", child_face="start",
    )
    plan.connect(
        f"{CUSTOMS_ID}.a21.hall.4.void", floor,
        axis="surface", overlap_m=0.20,
        parent_face="northeast", child_face="end",
    )


def _build_a21_operational_layers(plan: SpecPlan, lod: int) -> None:
    group = "souko-a21-operational-dressing"
    # Dense but asymmetric near-field story clusters stay outside the clear
    # diagonal service-road centerline.
    clusters = (
        (-190.0, 159.0, -0.58, "forklift"),
        (-174.0, 142.0, -0.55, "container"),
        (-151.0, 126.0, -0.50, "pallet"),
        (-126.0, 108.0, -0.48, "cover"),
        (-102.0, 91.0, -0.44, "forklift"),
        (-80.0, 72.0, -0.42, "container"),
        (-56.0, 55.0, -0.38, "pallet"),
        (-32.0, 38.0, -0.34, "cover"),
    )
    selection = clusters if lod == 0 else clusters[::2] if lod == 1 else clusters[::4]
    for index, (x, z, yaw, kind) in enumerate(selection):
        side = -1.0 if index % 2 == 0 else 1.0
        cx, cz = x - side * 8.8, z - side * 5.8
        plan.box(
            "a21-quay-tactical-cover", "old_concrete", group,
            cx, 0.72, cz, 5.0 + index % 3, 1.35, 1.1,
            yaw=yaw, layer="near",
        )
        if lod < 2:
            if kind == "forklift":
                _A20._add_forklift(plan, group, cx + 3.0, cz + 2.5, yaw + 0.2, lod)
            elif kind == "container":
                _A20._add_container(
                    plan, group, cx + 3.5, cz + 2.0, yaw,
                    "weathered_zinc" if index % 3 else "safety_orange",
                    lod, layer="near",
                )
            else:
                _A20._add_pallet_stack(plan, group, cx + 2.8, cz + 2.0, lod)
            _A20._add_worker(plan, group, cx - 2.0, cz + 2.2, yaw)
    if lod < 2:
        for index in range(12 if lod == 0 else 6):
            t = 0.08 + index * 0.80 / (11 if lod == 0 else 5)
            x = -234.0 + 239.0 * t
            z = 170.0 - 156.0 * t
            plan.box(
                "a21-wet-quay-oil-track", "dark_concrete", group,
                x, 0.150, z, 8.0 + (index % 3) * 2.0, 0.025, 0.34,
                yaw=-0.58, layer="near",
            )
            if index % 2 == 0:
                plan.box(
                    "a21-quay-hazard-chevron", "safety_orange", group,
                    x - 6.0, 0.172, z - 4.0, 3.0, 0.04, 0.36,
                    yaw=-0.58, layer="near",
                )

        # Broad wet patches, drainage grates and two service gantries make the
        # primary quay read as an occupied workplace rather than an empty road.
        # They are visual dressing only and leave canonical gameplay collision
        # untouched.
        road_start = (-234.0, 170.0)
        road_end = (5.0, 14.0)
        road_dx = road_end[0] - road_start[0]
        road_dz = road_end[1] - road_start[1]
        road_length = math.hypot(road_dx, road_dz)
        road_ux, road_uz = road_dx / road_length, road_dz / road_length
        road_px, road_pz = -road_uz, road_ux
        road_yaw = math.atan2(road_dz, road_dx)
        puddle_ts = (0.10, 0.22, 0.35, 0.49, 0.63, 0.76, 0.87)
        for index, t in enumerate(
            puddle_ts if lod == 0 else puddle_ts[::2],
        ):
            lateral = (-1.0 if index % 2 == 0 else 1.0) * (
                1.8 + (index % 3) * 1.1
            )
            x = road_start[0] + road_dx * t + road_px * lateral
            z = road_start[1] + road_dz * t + road_pz * lateral
            plan.box(
                "a21-reflective-working-quay-puddle", "puddle_water", group,
                x, 0.184, z,
                13.0 + (index % 3) * 4.0, 0.028,
                2.8 + (index % 2) * 1.8,
                yaw=road_yaw + (index - 3) * 0.012, layer="near",
            )
        for t in ((0.18, 0.43, 0.70) if lod == 0 else (0.24, 0.66)):
            x = road_start[0] + road_dx * t
            z = road_start[1] + road_dz * t
            plan.box(
                "a21-working-quay-cross-drain", "structural_steel", group,
                x, 0.196, z, 17.5, 0.05, 0.52,
                yaw=road_yaw + math.pi / 2.0, layer="near",
            )
        gantry_ts = (0.31, 0.62) if lod == 0 else (0.50,)
        for gantry_index, t in enumerate(gantry_ts):
            center_x = road_start[0] + road_dx * t
            center_z = road_start[1] + road_dz * t
            post_height = 8.2 + gantry_index * 1.4
            for side in (-1.0, 1.0):
                foot_x = center_x + road_px * 11.2 * side
                foot_z = center_z + road_pz * 11.2 * side
                plan.beam(
                    "a21-working-quay-service-gantry-leg",
                    "structural_steel", group,
                    (foot_x, 0.18, foot_z),
                    (foot_x, post_height, foot_z),
                    0.34 if lod == 0 else 0.50,
                    0.30 if lod == 0 else 0.46,
                    layer="near",
                )
            left = (
                center_x - road_px * 11.2,
                post_height,
                center_z - road_pz * 11.2,
            )
            right = (
                center_x + road_px * 11.2,
                post_height,
                center_z + road_pz * 11.2,
            )
            plan.beam(
                "a21-working-quay-service-gantry-header",
                "weathered_zinc", group, left, right,
                0.46 if lod == 0 else 0.66,
                0.40 if lod == 0 else 0.60,
                layer="near",
            )
            plan.beam(
                "a21-working-quay-overhead-utility-pipe",
                "rust", group,
                (left[0], left[1] + 0.72, left[2]),
                (right[0], right[1] + 0.72, right[2]),
                0.30 if lod == 0 else 0.44,
                0.30 if lod == 0 else 0.44,
                layer="near",
            )
            if lod == 0:
                for lamp_side in (-0.45, 0.45):
                    lamp_x = center_x + road_px * 11.2 * lamp_side
                    lamp_z = center_z + road_pz * 11.2 * lamp_side
                    plan.box(
                        "a21-working-quay-gantry-lamp", "warm_glass", group,
                        lamp_x, post_height - 0.42, lamp_z,
                        0.95, 0.30, 0.95, yaw=road_yaw, layer="near",
                    )

    # Upgrade the inherited ship/quay proof with visible machinery and a
    # broadside silhouette.  Everything remains outside playable bounds.
    port = "souko-a21-ship-upgrade"
    outside = True
    for side in (-1.0, 1.0):
        for x in (-82.0, -60.0, -38.0, -16.0):
            plan.box(
                "a21-cargo-ship-hull-plate",
                "rust" if int(abs(x)) % 3 == 1 else "dark_concrete",
                port, x, 3.6, 188.0 + side * 11.15,
                19.0, 3.6, 0.22, layer="far", outside_playable=outside,
            )
    for x in (-70.0, -48.0, -26.0, -4.0):
        plan.box(
            "a21-cargo-ship-deck-hatch", "weathered_zinc", port,
            x, 7.4, 188.0, 13.0, 0.48, 8.0,
            layer="far", outside_playable=outside,
        )
        if lod < 2:
            plan.cylinder(
                "a21-cargo-ship-deck-vent", "rust", port,
                x + 4.0, 9.2, 188.0, 0.72, 3.6,
                12 if lod == 0 else 8, top_radius=0.58,
                layer="far", outside_playable=outside,
            )
    if lod < 2:
        for x in (-84.0, -54.0, -24.0, 6.0):
            plan.beam(
                "a21-cargo-ship-mooring-line", "pallet_wood", port,
                (x, 1.4, 179.0), (x + 9.0, 5.5, 187.0),
                0.13, 0.11, layer="far", outside_playable=outside,
            )
    for x in (-188.0, -158.0, -128.0, -98.0, -68.0, -38.0, -8.0):
        plan.box(
            "a21-quay-rubber-fender", "dark_concrete", port,
            x, 0.5, 183.1, 3.4, 3.8, 1.0,
            layer="far", outside_playable=outside,
        )
        plan.cylinder(
            "a21-quay-heavy-bollard", "structural_steel", port,
            x + 6.0, 1.0, 178.7, 0.74, 1.5,
            12 if lod == 0 else 8, top_radius=0.94,
            layer="far", outside_playable=outside,
        )


def build_plan(lod: int = 0) -> SpecPlan:
    """Return the deterministic standalone A21 plan."""
    if lod not in LOD_API:
        raise ValueError(f"unsupported LOD: {lod}")
    plan = SpecPlan(lod)
    _copy_environment_base(plan, lod)
    _build_stackhouse(plan, lod)
    _build_customs(plan, lod)
    _build_inter_landmark_transfer(plan, lod)
    _build_a21_operational_layers(plan, lod)
    validate_plan(plan)
    return plan


def plan_metrics(plan: SpecPlan) -> dict[str, Any]:
    metrics = _A20.plan_metrics(plan)
    landmark_groups = sorted({
        spec["group"] for spec in plan.specs
        if spec["group"] in {STACKHOUSE_ID, CUSTOMS_ID}
    })
    metrics["landmarkGroups"] = landmark_groups
    metrics["releaseSurfaceMaterials"] = sorted(
        material for material in metrics["materials"]
        if MATERIAL_EXPORT_SUFFIX[material] in {
            "wall_weathered", "wall_warm", "wall_cool", "wall_alt",
            "obstacle", "natural", "terrain", "floor", "road", "wall",
            "water", "roof", "wood",
        }
    )
    return metrics


def spawn_intrusions(plan: SpecPlan, clearance_m: float = 5.0) -> list[dict[str, Any]]:
    intrusions: list[dict[str, Any]] = []
    for spec in plan.specs:
        if not spec["blocksGameplay"] or spec["outsidePlayable"]:
            continue
        bounds = spec_bounds(spec)
        for spawn in CANONICAL_PLAYER_SPAWNS:
            if (
                bounds[0] - clearance_m <= spawn[0] <= bounds[3] + clearance_m
                and bounds[2] - clearance_m <= spawn[2] <= bounds[5] + clearance_m
            ):
                intrusions.append({"spec": spec["name"], "spawn": spawn})
    return intrusions


def camera_containment_hits(
    plan: SpecPlan,
    view: Mapping[str, Any],
    *,
    near_clip_clearance_m: float = 0.10,
) -> list[dict[str, Any]]:
    """Return solids containing, or almost touching, a proof camera eye."""
    eye_x, eye_y, eye_z = (float(value) for value in view["eye"])
    hits: list[dict[str, Any]] = []
    for spec in plan.specs:
        bounds = spec_bounds(spec)
        if (
            bounds[0] - near_clip_clearance_m
            <= eye_x
            <= bounds[3] + near_clip_clearance_m
            and bounds[1] - near_clip_clearance_m
            <= eye_y
            <= bounds[4] + near_clip_clearance_m
            and bounds[2] - near_clip_clearance_m
            <= eye_z
            <= bounds[5] + near_clip_clearance_m
        ):
            hits.append({
                "name": spec["name"],
                "role": spec["role"],
                "bounds": list(bounds),
            })
    return hits


def route_intrusions(plan: SpecPlan) -> list[dict[str, Any]]:
    intrusions: list[dict[str, Any]] = []
    for spec in plan.specs:
        if not spec["blocksGameplay"] or spec["outsidePlayable"]:
            continue
        bounds = spec_bounds(spec)
        for road in CANONICAL_ROADS:
            road_bounds = road["bounds"]
            if (
                bounds[0] < road_bounds["maxX"]
                and bounds[3] > road_bounds["minX"]
                and bounds[2] < road_bounds["maxZ"]
                and bounds[5] > road_bounds["minZ"]
            ):
                intrusions.append({"spec": spec["name"], "road": road["id"]})
    return intrusions


def validate_plan(plan: SpecPlan) -> dict[str, Any]:
    names = [spec["name"] for spec in plan.specs]
    if len(names) != len(set(names)):
        raise ValueError("plan contains duplicate names")
    name_set = set(names)
    for connection in plan.connections:
        if connection["parent"] not in name_set or connection["child"] not in name_set:
            raise ValueError(f"connection references missing spec: {connection}")
        if connection["overlapM"] < MIN_CONTACT_OVERLAP_M:
            raise ValueError(f"connection overlap below gate: {connection}")
    metrics = plan_metrics(plan)
    budget = LOD_API[plan.lod]
    if metrics["specCount"] > budget["maxSpecs"]:
        raise ValueError(f"LOD{plan.lod} spec budget exceeded")
    if metrics["estimatedTriangles"] > budget["maxEstimatedTriangles"]:
        raise ValueError(f"LOD{plan.lod} triangle budget exceeded")
    if metrics["materialCount"] > 16:
        raise ValueError("material budget exceeded")
    if metrics["landmarkGroups"] != sorted((STACKHOUSE_ID, CUSTOMS_ID)):
        raise ValueError("A21 requires exactly two canonical landmark groups")
    if _role_count(plan.specs, "a21-stackhouse-functional-mass") != 4:
        raise ValueError("Stackhouse must keep four unequal functional masses")
    for role in (
        "a21-customs-full-depth-sawtooth-roof",
        "a21-customs-full-depth-sawtooth-glazing",
        "a21-customs-deep-machine-hall-void",
    ):
        if _role_count(plan.specs, role) != 4:
            raise ValueError(f"Customs must keep exactly four: {role}")
    if spawn_intrusions(plan):
        raise ValueError(f"spawn intrusions: {spawn_intrusions(plan)}")
    if route_intrusions(plan):
        raise ValueError(f"route intrusions: {route_intrusions(plan)}")
    return metrics


def emit_plan(
    builder: Any,
    plan: SpecPlan,
    material_map: Mapping[str, str] = DEFAULT_INTEGRATION_MATERIAL_MAP,
) -> None:
    for spec in plan.specs:
        payload = dict(spec)
        payload["material"] = material_map.get(spec["material"], spec["material"])
        method = getattr(builder, f"add_{spec['kind']}", None)
        if method is None and spec["kind"] == "oriented_box":
            method = getattr(builder, "add_box", None)
        if method is None:
            raise AttributeError(f"builder cannot emit {spec['kind']}")
        method(**payload)


def producer_provisional_scorecard() -> dict[str, Any]:
    return {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "referenceSha256": REFERENCE_SHA256,
        "fixedCategoryOrder": list(FIXED_SCORE_CATEGORIES),
        "items": [
            {
                "category": category,
                "score": 0.0,
                "evidence": (
                    "A21 producer candidate; independent visual review has not "
                    "certified this category."
                ),
            }
            for category in FIXED_SCORE_CATEGORIES
        ],
        "producerProvisional": True,
        "verdict": "NO-SHIP",
        "formalReferencePassClaimed": False,
        "independentReviewRequired": True,
        "formalPassGate": {
            "minimumEach": 7.0,
            "minimumAverage": 8.0,
            "currentlyMeetsNumericGate": False,
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _runtime_to_blender(point: Sequence[float]) -> tuple[float, float, float]:
    return (float(point[0]), float(point[2]), float(point[1]))


def _set_bsdf_input(bsdf: Any, names: Sequence[str], value: Any) -> bool:
    for name in names:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def _material_export_name(key: str) -> str:
    return f"SO_A21_{key}_{MATERIAL_EXPORT_SUFFIX[key]}"


def _hash_noise(seed: int, x: int, y: int) -> float:
    value = (
        x * 0x1F123BB5
        ^ y * 0x5F356495
        ^ seed * 0x6C8E9CF5
    ) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x2C1B3C6D) & 0xFFFFFFFF
    value ^= value >> 12
    value = (value * 0x297A2D39) & 0xFFFFFFFF
    value ^= value >> 15
    return value / 0xFFFFFFFF


def _value_noise(seed: int, x: int, y: int, cell_size: int) -> float:
    grid_x, grid_y = x // cell_size, y // cell_size
    fx, fy = (x % cell_size) / cell_size, (y % cell_size) / cell_size
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    n00 = _hash_noise(seed, grid_x, grid_y)
    n10 = _hash_noise(seed, grid_x + 1, grid_y)
    n01 = _hash_noise(seed, grid_x, grid_y + 1)
    n11 = _hash_noise(seed, grid_x + 1, grid_y + 1)
    top = n00 + (n10 - n00) * fx
    bottom = n01 + (n11 - n01) * fx
    return top + (bottom - top) * fy


def _texture_noise(key: str, x: int, y: int, size: int) -> float:
    del size
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    broad = _value_noise(seed, x, y, 17)
    medium = _value_noise(seed ^ 0xA3C59AC3, x, y, 7)
    aggregate = _hash_noise(seed ^ 0xC761C23C, x, y)
    return max(0.0, min(1.0, broad * 0.54 + medium * 0.31 + aggregate * 0.15))


def _create_texture_set(bpy: Any, key: str, recipe: Mapping[str, Any]) -> dict[str, Any]:
    texture_dir = PRIVATE_OUTPUT_ROOT / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)
    size = 64
    base_color = tuple(float(value) for value in recipe["color"])
    roughness = float(recipe.get("roughness", 0.6))
    alpha = float(recipe.get("alpha", base_color[3] if len(base_color) > 3 else 1.0))
    images: dict[str, Any] = {}
    heights = [
        _texture_noise(key, x, y, size)
        for y in range(size)
        for x in range(size)
    ]
    for texture_kind in ("basecolor", "roughness", "normal"):
        image = bpy.data.images.new(
            f"SO_A21_{key}_{texture_kind}", width=size, height=size, alpha=True,
        )
        pixels: list[float] = []
        for y in range(size):
            for x in range(size):
                index = y * size + x
                noise = heights[index]
                if texture_kind == "basecolor":
                    stain = 0.88 + noise * (
                        0.20 if recipe.get("stains") or recipe.get("rustMask") else 0.12
                    )
                    if recipe.get("rustMask"):
                        stain *= 0.90 + noise * 0.16
                    if key == "red_brick":
                        row = y // 8
                        brick_x = (x + (row % 2) * 8) % 16
                        if y % 8 == 0 or brick_x == 0:
                            stain *= 0.48
                    elif key in {"old_concrete", "pale_concrete"}:
                        if _hash_noise(index ^ 0x71A5, x, y) > 0.975:
                            stain *= 0.48
                    elif key == "rust":
                        streak = _hash_noise(0xA21, x // 3, 0)
                        stain *= 0.74 + streak * 0.38 + (y / size) * 0.05
                    elif key == "wet_asphalt":
                        stain *= 0.88 + _hash_noise(0xA5221, x, y) * 0.22
                    pixels.extend((
                        max(0.0, min(1.0, base_color[0] * stain)),
                        max(0.0, min(1.0, base_color[1] * stain)),
                        max(0.0, min(1.0, base_color[2] * stain)),
                        alpha,
                    ))
                elif texture_kind == "roughness":
                    variation = (noise - 0.5) * (
                        0.18 if recipe.get("wetVariation") else 0.10
                    )
                    value = max(0.035, min(0.98, roughness + variation))
                    pixels.extend((value, value, value, 1.0))
                else:
                    left = heights[y * size + ((x - 1) % size)]
                    right = heights[y * size + ((x + 1) % size)]
                    down = heights[((y - 1) % size) * size + x]
                    up = heights[((y + 1) % size) * size + x]
                    strength = (
                        0.34 if key in {"old_concrete", "red_brick", "rust"}
                        else 0.16
                    )
                    nx = (left - right) * strength
                    ny = (down - up) * strength
                    nz = 1.0
                    length = math.sqrt(nx * nx + ny * ny + nz * nz)
                    pixels.extend((
                        nx / length * 0.5 + 0.5,
                        ny / length * 0.5 + 0.5,
                        nz / length * 0.5 + 0.5,
                        1.0,
                    ))
        image.pixels.foreach_set(pixels)
        image.update()
        image.file_format = "PNG"
        path = texture_dir / f"{key}-{texture_kind}.png"
        image.filepath_raw = str(path)
        image.save()
        if texture_kind != "basecolor":
            image.colorspace_settings.name = "Non-Color"
        images[texture_kind] = image
    return images


def _make_release_material(
    bpy: Any,
    key: str,
    recipe: Mapping[str, Any],
    texture_set: Mapping[str, Any],
) -> Any:
    material = bpy.data.materials.new(_material_export_name(key))
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (720, 60)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (430, 60)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    base = nodes.new("ShaderNodeTexImage")
    base.name = f"SO_A21_{key}_BaseColor"
    base.image = texture_set["basecolor"]
    base.location = (-400, 180)
    rough = nodes.new("ShaderNodeTexImage")
    rough.name = f"SO_A21_{key}_Roughness"
    rough.image = texture_set["roughness"]
    rough.image.colorspace_settings.name = "Non-Color"
    rough.location = (-400, -20)
    normal = nodes.new("ShaderNodeTexImage")
    normal.name = f"SO_A21_{key}_Normal"
    normal.image = texture_set["normal"]
    normal.image.colorspace_settings.name = "Non-Color"
    normal.location = (-400, -240)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (120, -210)
    normal_map.inputs["Strength"].default_value = (
        0.25 if key in {"old_concrete", "red_brick", "rust"}
        else 0.08 if key in {"wet_asphalt", "puddle_water", "sea_water"}
        else 0.14
    )
    links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    _set_bsdf_input(bsdf, ("Metallic",), float(recipe.get("metallic", 0.0)))
    _set_bsdf_input(bsdf, ("IOR",), 1.46)
    transmission = float(recipe.get("transmission", 0.0))
    if transmission:
        _set_bsdf_input(bsdf, ("Transmission Weight", "Transmission"), transmission)
    alpha = float(recipe.get("alpha", 1.0))
    if alpha < 1.0:
        links.new(base.outputs["Alpha"], bsdf.inputs["Alpha"])
        material.diffuse_color = tuple(float(value) for value in recipe["color"])
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        material.use_transparency_overlap = False
    emission = recipe.get("emission")
    if emission:
        if bsdf.inputs.get("Emission Color") is not None:
            links.new(base.outputs["Color"], bsdf.inputs["Emission Color"])
        elif bsdf.inputs.get("Emission") is not None:
            links.new(base.outputs["Color"], bsdf.inputs["Emission"])
        _set_bsdf_input(
            bsdf, ("Emission Strength",),
            float(recipe.get("emissionStrength", 1.0)),
        )
    return material


def _assign_world_uv(mesh: Any, scale: float) -> None:
    uv_layer = mesh.uv_layers.new(name="SO_A21_WORLD_UV")
    for polygon in mesh.polygons:
        normal = polygon.normal
        axis = max(range(3), key=lambda index: abs(normal[index]))
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            if axis == 0:
                uv = (vertex.y * scale, vertex.z * scale)
            elif axis == 1:
                uv = (vertex.x * scale, vertex.z * scale)
            else:
                uv = (vertex.x * scale, vertex.y * scale)
            uv_layer.data[loop_index].uv = uv


def _create_blender_geometry(
    bpy: Any,
    backend: Any,
    plan: SpecPlan,
    *,
    source_sha: str,
    lod: int,
) -> dict[str, Any]:
    root = bpy.data.collections.new(TARGET_COLLECTION)
    bpy.context.scene.collection.children.link(root)
    batches = backend._build_mesh_batches(plan)
    texture_sets = {
        key: _create_texture_set(bpy, key, MATERIALS[key])
        for key in sorted(batches)
    }
    materials = {
        key: _make_release_material(bpy, key, MATERIALS[key], texture_sets[key])
        for key in sorted(batches)
    }
    raw_triangles = 0
    mesh_objects = []
    for material_key in sorted(batches):
        batch = batches[material_key]
        mesh = bpy.data.meshes.new(f"SO_A21_{material_key}_MESH")
        mesh.from_pydata(batch["vertices"], [], batch["faces"])
        mesh.update(calc_edges=True)
        _assign_world_uv(
            mesh, 1.0 / float(MATERIALS[material_key].get("textureScaleM", 4.0)),
        )
        raw_triangles += sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        obj = bpy.data.objects.new(f"SO_A21_{material_key}", mesh)
        root.objects.link(obj)
        obj.data.materials.append(materials[material_key])
        obj["hibanaGeneratorVersion"] = REFERENCE_MATCH_VERSION
        obj["hibanaGeneratorSha"] = source_sha
        obj["hibanaStageId"] = STAGE_ID
        obj["hibanaLod"] = lod
        if material_key not in {"dirty_glass", "puddle_water", "sea_water", "warm_glass"}:
            bevel = obj.modifiers.new("SO_A21_visibility_bevel", "BEVEL")
            bevel.width = 0.045
            bevel.segments = 1
            bevel.limit_method = "ANGLE"
        mesh_objects.append(obj)
    return {
        "collection": root,
        "meshObjects": mesh_objects,
        "rawMeshTriangles": raw_triangles,
        "meshObjectCount": len(mesh_objects),
        "batchCount": len(batches),
        "vertexCount": sum(len(batch["vertices"]) for batch in batches.values()),
        "polygonCount": sum(len(batch["faces"]) for batch in batches.values()),
        "textureCount": sum(len(value) for value in texture_sets.values()),
    }


def _look_at(obj: Any, target: Sequence[float]) -> None:
    from mathutils import Vector

    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_lighting_and_camera(bpy: Any) -> Any:
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        pass
    scene.view_settings.exposure = 0.86

    world = bpy.data.worlds.new("SO_A21_World_CoastalDusk")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.82
    coordinates = nodes.new("ShaderNodeTexCoord")
    cloud_noise = nodes.new("ShaderNodeTexNoise")
    cloud_noise.noise_dimensions = "4D"
    cloud_noise.inputs["Scale"].default_value = 2.2
    cloud_noise.inputs["Detail"].default_value = 3.2
    cloud_noise.inputs["Roughness"].default_value = 0.64
    cloud_noise.inputs["Distortion"].default_value = 0.14
    cloud_noise.inputs["W"].default_value = 0.37
    cloud_ramp = nodes.new("ShaderNodeValToRGB")
    cloud_ramp.color_ramp.interpolation = "EASE"
    cloud_ramp.color_ramp.elements[0].position = 0.18
    cloud_ramp.color_ramp.elements[0].color = (0.030, 0.065, 0.115, 1.0)
    cloud_ramp.color_ramp.elements[1].position = 0.80
    cloud_ramp.color_ramp.elements[1].color = (0.30, 0.25, 0.23, 1.0)
    blue_cloud = cloud_ramp.color_ramp.elements.new(0.44)
    blue_cloud.color = (0.085, 0.145, 0.22, 1.0)
    warm_cloud = cloud_ramp.color_ramp.elements.new(0.61)
    warm_cloud.color = (0.23, 0.18, 0.165, 1.0)
    links.new(coordinates.outputs["Normal"], cloud_noise.inputs["Vector"])
    links.new(cloud_noise.outputs["Fac"], cloud_ramp.inputs["Fac"])
    links.new(cloud_ramp.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    scene.world = world

    sun_data = bpy.data.lights.new("SO_A21_LGT_Key_Warm", "SUN")
    sun_data.energy = 4.9
    sun_data.color = (1.0, 0.67, 0.43)
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("SO_A21_LGT_Key_Warm", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (
        math.radians(54.0), math.radians(-18.0), math.radians(-118.0),
    )

    fill_data = bpy.data.lights.new("SO_A21_LGT_Fill_CoolCoast", "AREA")
    fill_data.energy = 9800.0
    fill_data.color = (0.34, 0.46, 0.63)
    fill_data.shape = "DISK"
    fill_data.size = 125.0
    fill = bpy.data.objects.new("SO_A21_LGT_Fill_CoolCoast", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-160.0, -110.0, 92.0)
    _look_at(fill, (20.0, 5.0, 25.0))

    rim_data = bpy.data.lights.new("SO_A21_LGT_Rim_Port", "AREA")
    rim_data.energy = 7600.0
    rim_data.color = (1.0, 0.50, 0.24)
    rim_data.shape = "DISK"
    rim_data.size = 80.0
    rim = bpy.data.objects.new("SO_A21_LGT_Rim_Port", rim_data)
    scene.collection.objects.link(rim)
    rim.location = (160.0, 120.0, 115.0)
    _look_at(rim, (15.0, -10.0, 28.0))

    for index, (location, energy, size) in enumerate((
        ((48.0, -96.0, 24.0), 3800.0, 24.0),
        ((-72.0, 31.0, 24.0), 3400.0, 28.0),
    )):
        practical_data = bpy.data.lights.new(f"SO_A21_LGT_Practical_{index}", "AREA")
        practical_data.energy = energy
        practical_data.color = (1.0, 0.19, 0.055)
        practical_data.shape = "DISK"
        practical_data.size = size
        practical = bpy.data.objects.new(f"SO_A21_LGT_Practical_{index}", practical_data)
        scene.collection.objects.link(practical)
        practical.location = location
        _look_at(practical, (location[0], location[1], 8.0))

    camera_data = bpy.data.cameras.new("SO_A21_FIXED_1P65M_CAMERA")
    camera_data.sensor_width = 36.0
    camera_data.clip_start = 0.08
    camera_data.clip_end = 1100.0
    camera_data.dof.use_dof = False
    camera = bpy.data.objects.new("SO_A21_FIXED_1P65M_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def _set_camera(camera: Any, view: Mapping[str, Any]) -> None:
    camera.location = _runtime_to_blender(view["eye"])
    camera.data.lens = float(view["lensMm"])
    camera.data.sensor_width = float(view.get("sensorWidthMm", 36.0))
    _look_at(camera, _runtime_to_blender(view["target"]))


def _clear_background_scene(bpy: Any) -> None:
    if not bpy.app.background:
        raise RuntimeError("A21 refuses to edit an interactive Blender scene")
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in tuple(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    for material in tuple(bpy.data.materials):
        bpy.data.materials.remove(material)
    for image in tuple(bpy.data.images):
        bpy.data.images.remove(image)


def _selected_views(selection: str) -> tuple[dict[str, Any], ...]:
    if selection == "all":
        return PRIVATE_VIEWS
    if selection == "primary":
        return (PRIMARY_CAMERA,)
    requested = {int(value) for value in selection.split(",")}
    return tuple(view for index, view in enumerate(PRIVATE_VIEWS, start=1) if index in requested)


def _render_result_preflight(bpy: Any, output_path: Path) -> dict[str, Any]:
    image = bpy.data.images.get("Render Result")
    if image is None or image.size[0] <= 0 or image.size[1] <= 0:
        try:
            image = bpy.data.images.load(str(output_path), check_existing=False)
        except RuntimeError:
            image = None
    if image is None or image.size[0] <= 0 or image.size[1] <= 0:
        return {
            "sampleCount": 0,
            "meanLinearLuminance": 0.0,
            "minLinearLuminance": 0.0,
            "maxLinearLuminance": 0.0,
            "nonBlackFraction": 0.0,
            "preflightPass": False,
            "failures": ["missing-render-result"],
        }
    width, height = int(image.size[0]), int(image.size[1])
    step_x = max(1, width // 160)
    step_y = max(1, height // 90)
    pixels = image.pixels
    luminances: list[float] = []
    for y in range(step_y // 2, height, step_y):
        for x in range(step_x // 2, width, step_x):
            offset = (y * width + x) * 4
            r, g, b = pixels[offset], pixels[offset + 1], pixels[offset + 2]
            luminances.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    mean_luminance = sum(luminances) / max(1, len(luminances))
    min_luminance = min(luminances, default=0.0)
    max_luminance = max(luminances, default=0.0)
    non_black_fraction = (
        sum(value > 0.012 for value in luminances) / max(1, len(luminances))
    )
    failures = []
    if mean_luminance < 0.030:
        failures.append("mean-luminance")
    if max_luminance < 0.12:
        failures.append("highlight-range")
    if non_black_fraction < 0.72:
        failures.append("non-black-coverage")
    if max_luminance - min_luminance < 0.055:
        failures.append("luminance-span")
    return {
        "sampleCount": len(luminances),
        "meanLinearLuminance": round(mean_luminance, 6),
        "minLinearLuminance": round(min_luminance, 6),
        "maxLinearLuminance": round(max_luminance, 6),
        "nonBlackFraction": round(non_black_fraction, 6),
        "preflightPass": not failures,
        "failures": failures,
    }


def _render_proof(
    bpy: Any,
    args: argparse.Namespace,
    *,
    source_sha: str,
) -> dict[str, Any]:
    backend = _load_module("hibana_souko_a21_backend_proof", BACKEND_PATH)
    started = time.time()
    plan = build_plan(0)
    metrics = plan_metrics(plan)
    _clear_background_scene(bpy)
    geometry = _create_blender_geometry(
        bpy, backend, plan, source_sha=source_sha, lod=0,
    )
    camera = _setup_lighting_and_camera(bpy)
    scene = bpy.context.scene
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    _set_camera(camera, PRIMARY_CAMERA)
    scene.camera = camera
    bpy.context.view_layer.update()
    blend_path = PRIVATE_OUTPUT_ROOT / "work/souko-a21-production-art-lod0.blend"
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    renders = []
    for view in _selected_views(args.views):
        containment_hits = camera_containment_hits(plan, view)
        if containment_hits:
            raise RuntimeError(
                f"{view['id']}: camera containment hits: {containment_hits}"
            )
        _set_camera(camera, view)
        bpy.context.view_layer.update()
        output_path = (
            PRIVATE_OUTPUT_ROOT / "views"
            / f"{view['id']}-{args.width}x{args.height}.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        preflight = _render_result_preflight(bpy, output_path)
        if not preflight["preflightPass"]:
            raise RuntimeError(
                f"{view['id']}: render preflight failed: {preflight}"
            )
        renders.append({
            "id": view["id"],
            "path": str(output_path),
            "sha256": _sha256(output_path),
            "bytes": output_path.stat().st_size,
            "eyeRuntimeM": list(view["eye"]),
            "targetRuntimeM": list(view["target"]),
            "lensMm": view["lensMm"],
            "containmentHits": containment_hits,
            "renderPreflight": preflight,
        })
    _set_camera(camera, PRIMARY_CAMERA)
    scene.camera = camera
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    report = {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "referenceSha256": REFERENCE_SHA256,
        "imagegenReferencePath": str(IMAGEGEN_REFERENCE_PATH),
        "imagegenReferenceSha256": IMAGEGEN_REFERENCE_SHA256,
        "independentA20BaselineScore": INDEPENDENT_A20_BASELINE_SCORE,
        "backgroundOnly": True,
        "liveBlenderTouched": False,
        "sourceModule": str(MODULE_PATH),
        "sourceModuleSha256": source_sha,
        "blendPath": str(blend_path),
        "blendSha256": _sha256(blend_path),
        "metrics": metrics,
        "geometry": {
            key: value
            for key, value in geometry.items()
            if key not in {"collection", "meshObjects"}
        },
        "cameraContract": PRIMARY_CAMERA,
        "renderSettings": {
            "engine": scene.render.engine,
            "resolution": [args.width, args.height],
            "dof": False,
            "warmDirectionalKey": True,
            "worldHazeDensity": 0.0,
        },
        "pbrStrategy": {
            "deterministicPrivateTextureSets": True,
            "baseColorMaps": True,
            "roughnessMaps": True,
            "normalMaps": True,
            "waterAlphaBlend": True,
            "worldProjectedUv": True,
        },
        "renders": renders,
        "producerStatus": producer_provisional_scorecard(),
        "elapsedSeconds": round(time.time() - started, 3),
    }
    report_path = (
        PRIVATE_OUTPUT_ROOT
        / f"proof-report-{args.views}-{args.width}x{args.height}.json"
    )
    _write_json(report_path, report)
    return report


def _export_lods(bpy: Any, *, source_sha: str) -> dict[str, Any]:
    backend = _load_module("hibana_souko_a21_backend_export", BACKEND_PATH)
    export_dir = PRIVATE_OUTPUT_ROOT / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    records = []
    started = time.time()
    for lod in (0, 1, 2):
        plan = build_plan(lod)
        metrics = plan_metrics(plan)
        _clear_background_scene(bpy)
        geometry = _create_blender_geometry(
            bpy, backend, plan, source_sha=source_sha, lod=lod,
        )
        bpy.ops.object.select_all(action="DESELECT")
        for obj in geometry["meshObjects"]:
            obj.select_set(True)
        if geometry["meshObjects"]:
            bpy.context.view_layer.objects.active = geometry["meshObjects"][0]
        output_path = export_dir / f"souko-a21-production-art-lod{lod}.glb"
        bpy.ops.export_scene.gltf(
            filepath=str(output_path),
            export_format="GLB",
            use_selection=True,
            export_extras=True,
            export_yup=True,
            export_apply=False,
        )
        records.append({
            "lod": lod,
            "path": str(output_path),
            "sha256": _sha256(output_path),
            "bytes": output_path.stat().st_size,
            "planMetrics": metrics,
            "rawMeshTriangles": geometry["rawMeshTriangles"],
            "meshObjectCount": geometry["meshObjectCount"],
            "vertexCount": geometry["vertexCount"],
            "polygonCount": geometry["polygonCount"],
            "textureCount": geometry["textureCount"],
        })
    report = {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "sourceModule": str(MODULE_PATH),
        "sourceModuleSha256": source_sha,
        "backgroundOnly": True,
        "liveBlenderTouched": False,
        "exports": records,
        "elapsedSeconds": round(time.time() - started, 3),
    }
    _write_json(PRIVATE_OUTPUT_ROOT / "export-report.json", report)
    return report


GLB_BUDGETS = {
    0: {"maxBytes": 4_000_000, "maxTriangles": 100_000, "maxPrimitives": 16},
    1: {"maxBytes": 2_000_000, "maxTriangles": 50_000, "maxPrimitives": 16},
    2: {"maxBytes": 750_000, "maxTriangles": 20_000, "maxPrimitives": 16},
}


def audit_private_glbs() -> dict[str, Any]:
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "tools/blender"))
    validator = _load_module("hibana_souko_a21_validator", VALIDATOR_PATH)
    export_report = json.loads(
        (PRIVATE_OUTPUT_ROOT / "export-report.json").read_text(encoding="utf-8")
    )
    records = []
    for item in export_report["exports"]:
        lod = int(item["lod"])
        inspected = validator.inspect(
            Path(item["path"]),
            generator_version=export_report["version"],
            generator_sha=export_report["sourceModuleSha256"],
        )
        budget = GLB_BUDGETS[lod]
        errors = []
        if inspected["bytes"] > budget["maxBytes"]:
            errors.append("file-size")
        if inspected["triangles"] > budget["maxTriangles"]:
            errors.append("triangles")
        if inspected["primitives"] > budget["maxPrimitives"]:
            errors.append("draw-calls")
        if inspected["materials"] > 16:
            errors.append("materials")
        inspected["lod"] = lod
        inspected["budget"] = budget
        inspected["budgetErrors"] = errors
        inspected["budgetPass"] = not errors
        inspected["metadataPass"] = not inspected["metadataErrors"]
        inspected["releasePbrPass"] = not inspected["pbrErrors"]
        records.append(inspected)
    report = {
        "stageId": export_report["stageId"],
        "version": export_report["version"],
        "sourceModuleSha256": export_report["sourceModuleSha256"],
        "technicalBudgetPass": all(item["budgetPass"] for item in records),
        "metadataPass": all(item["metadataPass"] for item in records),
        "releasePbrPass": all(item["releasePbrPass"] for item in records),
        "producerStatus": "NO-SHIP",
        "records": records,
    }
    _write_json(PRIVATE_OUTPUT_ROOT / "glb-audit.json", report)
    return report


def _write_producer_summary(
    proof: Mapping[str, Any] | None,
    export_report: Mapping[str, Any] | None,
    audit: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = producer_provisional_scorecard()
    payload.update({
        "sourceModuleSha256": _sha256(MODULE_PATH),
        "originalReferenceSha256": REFERENCE_SHA256,
        "imagegenReferenceSha256": IMAGEGEN_REFERENCE_SHA256,
        "independentA20BaselineScore": INDEPENDENT_A20_BASELINE_SCORE,
        "technicalBudgetPass": bool(audit and audit["technicalBudgetPass"]),
        "metadataPass": bool(audit and audit["metadataPass"]),
        "releasePbrPass": bool(audit and audit["releasePbrPass"]),
        "proof": (
            {
                "resolution": proof["renderSettings"]["resolution"],
                "viewCount": len(proof["renders"]),
                "fixedEyeHeightM": PLAYER_EYE_M,
            }
            if proof else None
        ),
        "lods": (
            [
                {
                    "lod": item["lod"],
                    "bytes": item["bytes"],
                    "planEstimatedTriangles": item["planMetrics"]["estimatedTriangles"],
                    "materials": item["planMetrics"]["materialCount"],
                }
                for item in export_report["exports"]
            ]
            if export_report else []
        ),
        "blockingFindings": [
            "Independent ten-category visual review is still required.",
            "This private candidate is not integrated into gameplay or a public manifest.",
            "Real-browser collision, LOS and performance audits have not been run.",
        ],
    })
    _write_json(PRIVATE_OUTPUT_ROOT / "producer-provisional.json", payload)
    return payload


def _parse_cli(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action", choices=("proof", "export", "audit", "all"), default="all",
    )
    parser.add_argument("--views", default="all")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    cli = list(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    args = _parse_cli(cli if argv is None else argv)
    PRIVATE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    source_sha = _sha256(MODULE_PATH)
    proof = None
    export_report = None
    audit = None
    if args.action == "audit":
        audit = audit_private_glbs()
        _write_producer_summary(None, None, audit)
        print(json.dumps(audit, indent=2))
        return 0
    import bpy

    if not bpy.app.background:
        raise RuntimeError("A21 production script is background-only")
    if args.action in {"proof", "all"}:
        proof = _render_proof(bpy, args, source_sha=source_sha)
    if args.action in {"export", "all"}:
        export_report = _export_lods(bpy, source_sha=source_sha)
    if args.action == "all":
        audit = audit_private_glbs()
    summary = _write_producer_summary(proof, export_report, audit)
    print(json.dumps({
        "proof": proof,
        "export": export_report,
        "audit": audit,
        "producer": summary,
    }, indent=2))
    return 0


__all__ = [
    "CANONICAL_BOUNDS", "CANONICAL_PLAYER_SPAWNS", "CANONICAL_ROADS",
    "CUSTOMS_ID", "DEFAULT_INTEGRATION_MATERIAL_MAP", "FIXED_SCORE_CATEGORIES",
    "GLB_BUDGETS", "IMAGEGEN_REFERENCE_PATH", "IMAGEGEN_REFERENCE_SHA256",
    "INDEPENDENT_A20_BASELINE_SCORE", "LANDMARKS", "LOD_API", "MATERIALS",
    "MATERIAL_EXPORT_SUFFIX", "MIN_CONTACT_OVERLAP_M", "PLAYER_EYE_M",
    "PRIMARY_CAMERA", "PRIVATE_OUTPUT_ROOT", "PRIVATE_VIEWS",
    "REFERENCE_MATCH_VERSION", "REFERENCE_PATH", "REFERENCE_SHA256",
    "STACKHOUSE_ID", "STAGE_ID", "SpecPlan", "audit_private_glbs",
    "build_plan", "camera_containment_hits", "emit_plan", "estimated_triangles",
    "plan_metrics",
    "producer_provisional_scorecard", "route_intrusions", "spawn_intrusions",
    "spec_bounds", "validate_plan",
]


if __name__ == "__main__":
    raise SystemExit(main())
