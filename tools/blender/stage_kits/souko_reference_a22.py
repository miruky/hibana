#!/usr/bin/env python3
"""Souko A22 private-only production rebuild.

A22 keeps only A20's collision-authoritative layout and ImageGen reference.
Both hero landmarks are independently reconstructed as occupied port machinery:

* Rack-Bridge Storehouse is a broad, six-bay, multi-level rack fortress with
  deep working aisles, unequal process cores and interlocking transfer bridges.
* Customs Terminal is a long four-bay sawtooth mechanical hall with visible
  portal frames, deep machine lines and an offset harbour-control tower.
* The central cross route remains readable.  A staffed checkpoint, secondary
  port city, ship, cranes, forklifts and maintenance clusters fill near/mid/far
  depth without image planes or authored horizon cards.

All visible edge hierarchy is baked into exported geometry.  Hero piers and
portals use 0.12-0.22 m chamfers, secondary walls use 0.05-0.10 m chamfers,
and rails/equipment use 0.01-0.03 m rounded profiles.  There is deliberately no
global bevel modifier.

Runtime coordinates are X/Z horizontal and Y-up, in metres.  The script is
background-Blender-only and writes exclusively below PRIVATE_OUTPUT_ROOT.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping, Sequence


MODULE_PATH = Path(__file__).resolve()
REPO_ROOT = MODULE_PATH.parents[3]
A20_PATH = MODULE_PATH.with_name("souko_reference_a20.py")
BACKEND_PATH = MODULE_PATH.with_name("souko_reference_a18_r8.py")
VALIDATOR_PATH = REPO_ROOT / "tools/blender/validate-glb.py"
A21_SCORECARD_PATH = Path(
    "/private/tmp/hibana-blender/a21-souko-production-art/"
    "INDEPENDENT_SCORECARD.json"
)
A22_CONTROLLING_SCORECARD_PATH = Path(
    "/private/tmp/hibana-blender/a22-souko-production-art/"
    "INDEPENDENT_SCORECARD_A22_ITERATION27.json"
)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A20 = _load_module("hibana_souko_a20_for_a22", A20_PATH)

STAGE_ID = "souko"
REFERENCE_MATCH_VERSION = (
    "a22-souko-production-art-v7-iteration29-c-continuous-customs-hall"
)
REFERENCE_PATH = _A20.REFERENCE_PATH
REFERENCE_SHA256 = _A20.REFERENCE_SHA256
IMAGEGEN_REFERENCE_PATH = Path(
    "/private/tmp/hibana-blender/a20-souko-art-rebuild/reference/"
    "souko-a20-imagegen-reference.png"
)
IMAGEGEN_REFERENCE_SHA256 = (
    "fb3bd642434e83f5c22c23d23bbc24ef2cba7245402c4b20433306a989e55db5"
)
A21_INDEPENDENT_SCORECARD_SHA256 = (
    "6f58b457b84eeda4ad367cb9eff57c6ee34a4ac8fb8afc98cf52c6825c12ca8c"
)
A22_CONTROLLING_SCORECARD_SHA256 = (
    "88250651d03bd0503f414f2999eaef7740deadfcc7968c7bfa33f0e7c0184655"
)
PRIVATE_OUTPUT_ROOT = Path(
    "/private/tmp/hibana-blender/a22-souko-production-art-iteration29-c"
)
TARGET_COLLECTION = "HB_SOUKO_A22_PRIVATE"
MAP_SIZE_M = 336.0
PLAYER_EYE_M = 1.65
MIN_CONTACT_OVERLAP_M = 0.005

CANONICAL_BOUNDS = copy.deepcopy(_A20.CANONICAL_BOUNDS)
CANONICAL_ROADS = copy.deepcopy(_A20.CANONICAL_ROADS)
CANONICAL_PLAYER_SPAWNS = copy.deepcopy(_A20.CANONICAL_PLAYER_SPAWNS)
STACKHOUSE_ID = _A20.STACKHOUSE_ID
CUSTOMS_ID = _A20.CUSTOMS_ID
LANDMARKS = copy.deepcopy(_A20.LANDMARKS)

PRIMARY_QUAY_FAR_X = -150.0
PRIMARY_QUAY_FAR_Z = 14.0
PRIMARY_QUAY_NEAR_X = -194.0
PRIMARY_QUAY_NEAR_Z = 125.0
PRIMARY_QUAY_LENGTH = math.hypot(
    PRIMARY_QUAY_NEAR_X - PRIMARY_QUAY_FAR_X,
    PRIMARY_QUAY_NEAR_Z - PRIMARY_QUAY_FAR_Z,
)
PRIMARY_QUAY_YAW = math.atan2(
    PRIMARY_QUAY_FAR_X - PRIMARY_QUAY_NEAR_X,
    PRIMARY_QUAY_NEAR_Z - PRIMARY_QUAY_FAR_Z,
)


def primary_quay_edge_x(z: float) -> float:
    """Return the authored water/land boundary X at runtime-space Z."""

    fraction = (
        (float(z) - PRIMARY_QUAY_FAR_Z)
        / (PRIMARY_QUAY_NEAR_Z - PRIMARY_QUAY_FAR_Z)
    )
    return PRIMARY_QUAY_FAR_X + (
        PRIMARY_QUAY_NEAR_X - PRIMARY_QUAY_FAR_X
    ) * fraction


PRIMARY_QUAY_EDGE_X = primary_quay_edge_x(-5.0)
PRIMARY_SHIP_STERN_Z = 26.0
PRIMARY_SHIP_BOW_Z = 82.0
PRIMARY_SHIP_QUAY_GAP = 1.0
PRIMARY_SHIP_HALF_BEAM = 3.0
PRIMARY_SHIP_LAND_SHOULDER_X = (
    primary_quay_edge_x(PRIMARY_SHIP_BOW_Z) - PRIMARY_SHIP_QUAY_GAP
)
PRIMARY_SHIP_LAND_STERN_X = PRIMARY_SHIP_LAND_SHOULDER_X


def primary_ship_land_x(z: float) -> float:
    """Land-facing hull side for the three-quarter primary ship pose."""

    _ = z
    return PRIMARY_SHIP_LAND_STERN_X


PRIMARY_SHIP_X = primary_ship_land_x(50.0) - PRIMARY_SHIP_HALF_BEAM
PRIMARY_SHIP_YAW = 0.0
PRIMARY_SHORE_ROLES = frozenset({
    "a22-p0-primary-camera-quay-water",
    "a22-p0-primary-camera-heavy-quay-wall",
    "a22-p0-primary-camera-quay-service-deck",
    "a22-p0-quay-rubber-fender",
    "a22-p0-quay-fender-hazard-cap",
    "a22-p0-quay-heavy-mooring-bollard",
})

PRIMARY_CAMERA: dict[str, Any] = {
    "id": "01-a22-iteration23-fixed-quay-dual-hero",
    "eye": (-205.0, PLAYER_EYE_M, 150.0),
    "target": (-30.0, 16.0, -2.0),
    "lensMm": 21.0,
    "sensorWidthMm": 36.0,
    "frameOrder": (STACKHOUSE_ID, CUSTOMS_ID),
    "skyMaxFraction": 0.18,
    "roadMaxFraction": 0.22,
    "heroHorizontalFillTarget": (0.84, 0.98),
    "shipHorizontalNdcMax": 0.75,
    "waterHorizontalNdcMax": 0.75,
    "purpose": (
        "Iteration-28 material-and-dock finish on the frozen Iteration-23 "
        "frame: processing castle left, customs hall mid-right, dark quay "
        "water, ship and crane at right."
    ),
}

PRIVATE_VIEWS: tuple[dict[str, Any], ...] = (
    PRIMARY_CAMERA,
    {
        "id": "02-a22-occupied-checkpoint-route",
        "eye": (-164.0, PLAYER_EYE_M, 116.0),
        "target": (-85.0, 9.0, 83.0),
        "lensMm": 30.0,
        "purpose": "Staffed wet checkpoint, freight queue and readable route.",
    },
    {
        "id": "03-a22-stackhouse-rack-arrival",
        "eye": (-18.0, PLAYER_EYE_M, 35.0),
        "target": (79.0, 43.0, 97.0),
        "lensMm": 27.0,
        "purpose": "Broad rack-fortress silhouette, piers and unequal crowns.",
    },
    {
        "id": "04-a22-stackhouse-deep-interior",
        "eye": (29.5, PLAYER_EYE_M, 96.0),
        "target": (85.0, 18.0, 96.0),
        "lensMm": 25.0,
        "purpose": "True open rack aisle with loaded decks and maintenance plant.",
    },
    {
        "id": "05-a22-customs-long-sawtooth",
        "eye": (-151.0, PLAYER_EYE_M, 18.0),
        "target": (-66.0, 34.0, -65.0),
        "lensMm": 27.0,
        "purpose": "Long mechanical hall, four teeth and harbour-control tower.",
    },
    {
        "id": "06-a22-customs-working-interior",
        "eye": (-68.0, PLAYER_EYE_M, -10.0),
        "target": (-68.0, 13.0, -78.0),
        "lensMm": 23.0,
        "purpose": "Actual hall interior: portals, conveyors, cranes and warm bays.",
    },
    {
        "id": "07-a22-ship-cranes-maintenance",
        "eye": (-162.0, PLAYER_EYE_M, 221.0),
        "target": (-54.0, 22.0, 185.0),
        "lensMm": 29.0,
        "purpose": "Working ship, cranes, forklifts, moorings and maintenance.",
    },
    {
        "id": "08-a22-port-city-depth",
        "eye": (184.0, PLAYER_EYE_M, 151.0),
        "target": (34.0, 30.0, 35.0),
        "lensMm": 32.0,
        "purpose": "Layered real 3D port city, gantries and route hierarchy.",
    },
    {
        "id": "09-a22-aerial-production-read",
        "eye": (-204.0, 126.0, 198.0),
        "target": (0.0, 18.0, 20.0),
        "lensMm": 36.0,
        "purpose": "Aerial proof of two-landmark composition and clear route cross.",
    },
)

PRIMARY_CAMERA_PROJECTION_POINTS: dict[str, tuple[float, float, float]] = {
    "stackhouseCentre": (80.8, 42.0, 96.0),
    "customsCentre": (-68.0, 28.0, -67.8),
    "shipHull": (
        primary_ship_land_x(72.0),
        5.0,
        72.0,
    ),
    "quayWater": (primary_quay_edge_x(120.0), 0.45, 120.0),
    "quayCrane": (-125.0, 58.0, -18.0),
}
PRIMARY_CAMERA_SCREEN_REGIONS: dict[
    str,
    tuple[tuple[float, float, float], ...],
] = {
    "shipHull": (
        (primary_ship_land_x(26.0) - 6.0, 0.0, 26.0),
        (primary_ship_land_x(34.0) - 6.0, 7.0, 34.0),
        (primary_ship_land_x(74.0) - 5.0, 7.2, 74.0),
        (
            primary_ship_land_x(PRIMARY_SHIP_BOW_Z) - 2.5,
            1.0,
            PRIMARY_SHIP_BOW_Z,
        ),
        (primary_ship_land_x(26.0), 0.0, 26.0),
        (primary_ship_land_x(74.0), 7.2, 74.0),
        (primary_ship_land_x(34.0), 7.0, 34.0),
        (-157.0, 18.0, 40.0),
    ),
    "quayWater": (
        (-220.0, 0.45, PRIMARY_QUAY_FAR_Z),
        (PRIMARY_QUAY_FAR_X, 0.45, PRIMARY_QUAY_FAR_Z),
        (primary_quay_edge_x(125.0), 0.45, 125.0),
        (-207.0, 0.45, 132.0),
    ),
}

# Iteration-29C is a single-hypothesis replacement of the right-hand hero.
# These are the two extreme macro-silhouette corners, expressed in the frozen
# primary-camera contract.  They intentionally cover about 55%-89% of the
# raster width without moving the camera or any non-Customs scene element.
ITERATION29C_CUSTOMS_SCREEN_POINTS: dict[
    str,
    tuple[float, float, float],
] = {
    "nearInner": (-44.0, 27.0, -16.0),
    "farOuter": (-130.0, 47.0, -128.0),
}

# Actual evaluated triangle targets, not merely upper caps.
LOD_TARGETS = {
    0: {"minTriangles": 160_000, "maxTriangles": 240_000},
    1: {"minTriangles": 45_000, "maxTriangles": 85_000},
    2: {"minTriangles": 12_000, "maxTriangles": 25_000},
}
LOD_API = {
    0: {"label": "hero", "maxSpecs": 7300, "maxEstimatedTriangles": 240_000},
    1: {"label": "medium", "maxSpecs": 3150, "maxEstimatedTriangles": 85_000},
    2: {"label": "horizon", "maxSpecs": 1100, "maxEstimatedTriangles": 25_000},
}
CHAMFER_BANDS_M = {
    "hero": (0.12, 0.22),
    "secondary": (0.05, 0.10),
    "equipment": (0.01, 0.03),
}

# Twelve shared, exportable PBR materials.  The old safety-orange key is kept
# for builder compatibility, but its authored colour is restrained zinc yellow.
MATERIALS: dict[str, dict[str, Any]] = {
    "wet_asphalt": {
        "color": (0.045, 0.052, 0.056, 1.0),
        "roughness": 0.46, "metallic": 0.10, "textureScaleM": 3.5,
        "wetVariation": True, "stains": True,
    },
    "puddle_water": {
        "color": (0.035, 0.090, 0.105, 0.62),
        "roughness": 0.24, "metallic": 0.08, "alpha": 0.62,
        "textureScaleM": 6.0, "wetVariation": True,
    },
    "old_concrete": {
        "color": (0.30, 0.295, 0.275, 1.0),
        "roughness": 0.82, "metallic": 0.0, "textureScaleM": 8.0,
        "stains": True, "rainStreaks": True,
    },
    "pale_concrete": {
        "color": (0.46, 0.45, 0.405, 1.0),
        "roughness": 0.77, "metallic": 0.0, "textureScaleM": 9.0,
        "stains": True, "rainStreaks": True,
    },
    "weathered_zinc": {
        "color": (0.23, 0.27, 0.28, 1.0),
        "roughness": 0.49, "metallic": 0.72, "textureScaleM": 6.0,
        "rustMask": True, "rainStreaks": True,
    },
    "structural_steel": {
        "color": (0.15, 0.17, 0.18, 1.0),
        "roughness": 0.50, "metallic": 0.86, "textureScaleM": 5.0,
        "rustMask": True,
    },
    "rust": {
        "color": (0.30, 0.105, 0.038, 1.0),
        "roughness": 0.78, "metallic": 0.05, "textureScaleM": 3.0,
        "rainStreaks": True,
    },
    "safety_orange": {
        "color": (0.44, 0.36, 0.060, 1.0),
        "roughness": 0.58, "metallic": 0.10, "textureScaleM": 4.0,
    },
    "dirty_glass": {
        "color": (0.035, 0.105, 0.12, 0.48),
        "roughness": 0.18, "metallic": 0.08, "transmission": 0.42,
        "alpha": 0.48, "textureScaleM": 5.0, "rainStreaks": True,
    },
    "warm_glass": {
        "color": (0.38, 0.205, 0.075, 1.0),
        "roughness": 0.34, "metallic": 0.0, "textureScaleM": 5.0,
        "emission": (0.62, 0.255, 0.055, 1.0), "emissionStrength": 3.5,
    },
    "pallet_wood": {
        "color": (0.26, 0.145, 0.060, 1.0),
        "roughness": 0.80, "metallic": 0.0, "textureScaleM": 2.2,
        "stains": True,
    },
    "sea_water": {
        "color": (0.012, 0.145, 0.175, 1.0),
        "roughness": 0.24, "metallic": 0.16, "alpha": 1.0,
        "textureScaleM": 15.0, "wetVariation": True,
    },
}

MATERIAL_EXPORT_SUFFIX = {
    "wet_asphalt": "road",
    "puddle_water": "water_patch",
    "old_concrete": "wall_weathered",
    "pale_concrete": "wall",
    "weathered_zinc": "roof",
    "structural_steel": "obstacle",
    "rust": "wall_alt",
    "safety_orange": "trim",
    "dirty_glass": "glass",
    "warm_glass": "emissive",
    "pallet_wood": "wood",
    "sea_water": "water",
}
DEFAULT_INTEGRATION_MATERIAL_MAP = {
    "wet_asphalt": "floor",
    "puddle_water": "floor",
    "old_concrete": "wall_weathered",
    "pale_concrete": "wall",
    "weathered_zinc": "roof",
    "structural_steel": "trim",
    "rust": "wall_alt",
    "safety_orange": "accent",
    "dirty_glass": "glass",
    "warm_glass": "emissive",
    "pallet_wood": "wood",
    "sea_water": "water",
}
FIXED_SCORE_CATEGORIES = copy.deepcopy(_A20.FIXED_SCORE_CATEGORIES)

MATERIAL_REMAP = {
    "wet_asphalt": "wet_asphalt",
    "puddle_water": "puddle_water",
    "old_concrete": "old_concrete",
    "pale_concrete": "pale_concrete",
    "dark_concrete": "structural_steel",
    "weathered_zinc": "weathered_zinc",
    "structural_steel": "structural_steel",
    "red_brick": "old_concrete",
    "rust": "rust",
    "safety_orange": "safety_orange",
    "dirty_glass": "dirty_glass",
    "warm_glass": "warm_glass",
    "paint_white": "pale_concrete",
    "pallet_wood": "pallet_wood",
    "sea_water": "sea_water",
    "vegetation": "old_concrete",
}


def _slug(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


class SpecPlan(_A20.SpecPlan):
    """A20-compatible plan extended with baked chamfers and true round pipes."""

    def chamfer_box(
        self,
        role: str,
        material: str,
        group: str,
        x: float,
        y: float,
        z: float,
        w: float,
        h: float,
        d: float,
        bevel_m: float,
        *,
        yaw: float = 0.0,
        band: str = "secondary",
        layer: str = "mid",
        blocks_gameplay: bool = False,
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        if material not in MATERIALS:
            raise ValueError(f"unknown A22 material: {material}")
        if band not in CHAMFER_BANDS_M:
            raise ValueError(f"unknown chamfer band: {band}")
        low, high = CHAMFER_BANDS_M[band]
        if not low <= bevel_m <= high:
            raise ValueError(f"{role}: {bevel_m} outside {band} band")
        if not _finite((x, y, z, w, h, d, yaw, bevel_m)):
            raise ValueError(f"{role}: non-finite chamfer box")
        if min(w, h, d) <= bevel_m * 2.01:
            raise ValueError(f"{role}: chamfer exceeds dimensions")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(
                resolved, role, material, group, layer,
                blocks_gameplay, outside_playable,
            ),
            "kind": "chamfer_box",
            "x": float(x), "y": float(y), "z": float(z),
            "w": float(w), "h": float(h), "d": float(d),
            "yaw": float(yaw), "bevelM": float(bevel_m),
            "chamferBand": band, "bakedProfile": True,
        })
        return resolved

    def pipe(
        self,
        role: str,
        material: str,
        group: str,
        start: Sequence[float],
        end: Sequence[float],
        radius: float,
        segments: int,
        *,
        layer: str = "mid",
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        start = tuple(float(value) for value in start)
        end = tuple(float(value) for value in end)
        if material not in MATERIALS:
            raise ValueError(f"unknown A22 material: {material}")
        if (
            len(start) != 3 or len(end) != 3
            or not _finite((*start, *end, radius))
            or math.dist(start, end) < 1e-6
            or not CHAMFER_BANDS_M["equipment"][0]
            <= radius
            <= CHAMFER_BANDS_M["equipment"][1]
            or segments < 6
        ):
            raise ValueError(f"{role}: invalid equipment pipe")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(
                resolved, role, material, group, layer, False, outside_playable,
            ),
            "kind": "pipe", "start": start, "end": end,
            "radius": float(radius), "segments": int(segments),
            "profileBand": "equipment", "bakedProfile": True,
        })
        return resolved

    def round_member(
        self,
        role: str,
        material: str,
        group: str,
        start: Sequence[float],
        end: Sequence[float],
        radius: float,
        segments: int,
        *,
        layer: str = "mid",
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        start = tuple(float(value) for value in start)
        end = tuple(float(value) for value in end)
        if material not in MATERIALS:
            raise ValueError(f"unknown A22 material: {material}")
        if (
            len(start) != 3 or len(end) != 3
            or not _finite((*start, *end, radius))
            or math.dist(start, end) < 1e-6
            or not 0.04 <= radius <= 1.75
            or segments < 6
        ):
            raise ValueError(f"{role}: invalid structural round member")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(
                resolved, role, material, group, layer, False, outside_playable,
            ),
            "kind": "round_member", "start": start, "end": end,
            "radius": float(radius), "segments": int(segments),
            "profileBand": "structural_round", "bakedProfile": True,
        })
        return resolved


def spec_bounds(spec: Mapping[str, Any]) -> tuple[float, float, float, float, float, float]:
    kind = spec["kind"]
    if kind == "chamfer_box":
        proxy = dict(spec)
        proxy["kind"] = "oriented_box"
        return _A20.spec_bounds(proxy)
    if kind in {"pipe", "round_member"}:
        radius = float(spec["radius"])
        start, end = spec["start"], spec["end"]
        return tuple(min(start[i], end[i]) - radius for i in range(3)) + tuple(
            max(start[i], end[i]) + radius for i in range(3)
        )
    return _A20.spec_bounds(spec)


def estimated_triangles(spec: Mapping[str, Any]) -> int:
    if spec["kind"] == "chamfer_box":
        return 44
    if spec["kind"] in {"pipe", "round_member"}:
        return max(20, 4 * int(spec["segments"]) - 4)
    return _A20.estimated_triangles(spec)


def plan_metrics(plan: SpecPlan) -> dict[str, Any]:
    bounds = [spec_bounds(spec) for spec in plan.specs]
    roles = Counter(spec["role"] for spec in plan.specs)
    materials = Counter(spec["material"] for spec in plan.specs)
    layers = Counter(spec["layer"] for spec in plan.specs)
    kinds = Counter(spec["kind"] for spec in plan.specs)
    bands = Counter(
        spec.get("chamferBand", spec.get("profileBand", "unprofiled"))
        for spec in plan.specs
    )
    return {
        "lod": plan.lod,
        "specCount": len(plan.specs),
        "estimatedTriangles": sum(estimated_triangles(spec) for spec in plan.specs),
        "materialCount": len(materials),
        "connectionCount": len(plan.connections),
        "bounds": {
            "minX": min(item[0] for item in bounds),
            "minY": min(item[1] for item in bounds),
            "minZ": min(item[2] for item in bounds),
            "maxX": max(item[3] for item in bounds),
            "maxY": max(item[4] for item in bounds),
            "maxZ": max(item[5] for item in bounds),
        },
        "roles": dict(sorted(roles.items())),
        "materials": dict(sorted(materials.items())),
        "layers": dict(sorted(layers.items())),
        "kinds": dict(sorted(kinds.items())),
        "profileBands": dict(sorted(bands.items())),
        "landmarkGroups": sorted({
            spec["group"] for spec in plan.specs
            if spec["group"] in {STACKHOUSE_ID, CUSTOMS_ID}
        }),
    }


def _role_count(specs: Iterable[Mapping[str, Any]], role: str) -> int:
    return sum(spec["role"] == role for spec in specs)


def _copy_environment_base(plan: SpecPlan, lod: int) -> None:
    """Use A20 only as canonical non-hero settlement foundation.

    Repeated glass cards and all prior hero groups are removed.  Surviving
    secondary solids receive real 0.06 m baked chamfers when dimensions permit.
    """
    source = _A20.build_plan(lod)
    retained_group = "souko-a20-public-realm"
    retained_roles = {
        "playable-industrial-ground",
        "camera-quay-apron",
        "wet-primary-road",
        "wet-diagonal-bonded-service-road",
        "service-road-curb",
        "service-road-faded-centre-dash",
        "service-road-linear-drain",
        "service-road-lamp-post",
        "service-road-lamp-arm",
        "service-road-lamp-head",
        "service-road-bollard",
        "wet-road-puddle",
        "quay-cargo-rail",
        "quay-rail-sleeper",
        "a20-quay-oil-and-tire-streak",
        "a20-quay-hazard-panel",
    }
    removed_role_tokens = (
        "window", "glazing", "glass-gable", "lit-cell", "warm-window",
    )
    name_map: dict[str, str] = {}
    for original in source.specs:
        if original["group"] != retained_group:
            continue
        if original["role"] not in retained_roles:
            continue
        if any(token in original["role"] for token in removed_role_tokens):
            continue
        if original["role"] == "wet-road-puddle":
            x = float(original["x"])
            y = float(original["y"])
            z = float(original["z"])
            half_length = float(original["w"]) * 0.5
            half_width = float(original["d"]) * 0.5
            yaw = float(original.get("yaw", 0.0))
            ux, uz = math.cos(yaw), math.sin(yaw)
            px, pz = -uz, ux
            plan.panel(
                "a22-foundation-wet-road-puddle",
                "puddle_water", "souko-a22-foundation-public-realm",
                (
                    (
                        x - ux * half_length - px * half_width * 0.62,
                        y,
                        z - uz * half_length - pz * half_width * 0.62,
                    ),
                    (
                        x + ux * half_length * 0.76 - px * half_width,
                        y,
                        z + uz * half_length * 0.76 - pz * half_width,
                    ),
                    (
                        x + ux * half_length + px * half_width * 0.68,
                        y,
                        z + uz * half_length + pz * half_width * 0.68,
                    ),
                    (
                        x - ux * half_length * 0.70 + px * half_width,
                        y,
                        z - uz * half_length * 0.70 + pz * half_width,
                    ),
                ),
                0.018, layer=str(original["layer"]),
            )
            continue
        copied = dict(original)
        copied["name"] = copied["name"].replace("souko-a20", "souko-a22-foundation")
        copied["group"] = copied["group"].replace("souko-a20", "souko-a22-foundation")
        copied["role"] = (
            "a22-foundation-" + copied["role"][4:]
            if copied["role"].startswith("a20-")
            else "a22-foundation-" + copied["role"]
        )
        copied["material"] = MATERIAL_REMAP[copied["material"]]
        if copied["kind"] in {"box", "oriented_box"}:
            smallest = min(float(copied["w"]), float(copied["h"]), float(copied["d"]))
            if copied["material"] != "sea_water" and smallest > 0.31:
                copied["kind"] = "chamfer_box"
                copied["bevelM"] = min(0.08, max(0.05, smallest * 0.16))
                copied["bevelM"] = min(copied["bevelM"], smallest * 0.30)
                if copied["bevelM"] >= 0.05:
                    copied["chamferBand"] = "secondary"
                    copied["bakedProfile"] = True
                else:
                    copied["kind"] = (
                        "box" if abs(float(copied.get("yaw", 0.0))) < 1e-9
                        else "oriented_box"
                    )
                    copied.pop("bevelM", None)
        name_map[original["name"]] = copied["name"]
        plan.specs.append(copied)
    for connection in source.connections:
        parent = name_map.get(connection["parent"])
        child = name_map.get(connection["child"])
        if parent is None or child is None:
            continue
        copied = dict(connection)
        copied["parent"] = parent
        copied["child"] = child
        copied["id"] = copied["id"].replace("souko-a20", "souko-a22-foundation")
        plan.connections.append(copied)


def _cb(
    plan: SpecPlan,
    role: str,
    material: str,
    group: str,
    x: float,
    y: float,
    z: float,
    w: float,
    h: float,
    d: float,
    bevel: float,
    band: str,
    *,
    yaw: float = 0.0,
    layer: str = "mid",
    blocks: bool = False,
    outside: bool = False,
    name: str | None = None,
) -> str:
    return plan.chamfer_box(
        role, material, group, x, y, z, w, h, d, bevel,
        yaw=yaw, band=band, layer=layer, blocks_gameplay=blocks,
        outside_playable=outside, name=name,
    )


def _structural_beam(
    plan: SpecPlan,
    role: str,
    group: str,
    start: Sequence[float],
    end: Sequence[float],
    size: float,
    *,
    material: str = "structural_steel",
    layer: str = "mid",
    outside: bool = False,
) -> str:
    return plan.beam(
        role, material, group, start, end, size, size,
        layer=layer, outside_playable=outside,
    )


def _rail(
    plan: SpecPlan,
    group: str,
    start: Sequence[float],
    end: Sequence[float],
    *,
    layer: str = "mid",
    outside: bool = False,
) -> str:
    return plan.pipe(
        "a22-rounded-guardrail", "weathered_zinc", group,
        start, end, 0.025, 8, layer=layer, outside_playable=outside,
    )


def _deep_window(
    plan: SpecPlan,
    group: str,
    x: float,
    y: float,
    z: float,
    w: float,
    h: float,
    *,
    depth: float,
    yaw: float = 0.0,
    layer: str = "mid",
) -> None:
    """Glass plus a genuinely recessed warm backing and mullions."""
    _cb(
        plan, "a22-deep-window-glass", "dirty_glass", group,
        x, y, z, w, h, 0.22, 0.05, "secondary",
        yaw=yaw, layer=layer,
    )
    offset_x = -math.sin(yaw) * depth
    offset_z = math.cos(yaw) * depth
    _cb(
        plan, "a22-deep-window-warm-interior", "warm_glass", group,
        x + offset_x, y, z + offset_z, w * 0.90, h * 0.86, 0.36,
        0.05, "secondary", yaw=yaw, layer=layer,
    )
    for side in (-1, 1):
        tangent_x = math.cos(yaw) * w * 0.48 * side
        tangent_z = math.sin(yaw) * w * 0.48 * side
        _structural_beam(
            plan, "a22-window-reveal", group,
            (x + tangent_x, y - h * 0.50, z + tangent_z),
            (x + tangent_x, y + h * 0.50, z + tangent_z),
            0.16, layer=layer,
        )
    if plan.lod < 2:
        vertical_fractions = (
            (-0.22, 0.22)
            if plan.lod == 0 and w >= 4.0
            else (0.0,)
        )
        for fraction in vertical_fractions:
            tangent_x = math.cos(yaw) * w * fraction
            tangent_z = math.sin(yaw) * w * fraction
            _structural_beam(
                plan, "a22-window-camera-scale-vertical-mullion", group,
                (x + tangent_x, y - h * 0.46, z + tangent_z),
                (x + tangent_x, y + h * 0.46, z + tangent_z),
                0.10, material="structural_steel", layer=layer,
            )
        horizontal_fractions = (
            (-0.25, 0.25)
            if plan.lod == 0 and h >= 2.4
            else (0.0,)
        )
        for fraction in horizontal_fractions:
            tangent_x = math.cos(yaw) * w * 0.46
            tangent_z = math.sin(yaw) * w * 0.46
            _structural_beam(
                plan, "a22-window-camera-scale-horizontal-mullion", group,
                (x - tangent_x, y + h * fraction, z - tangent_z),
                (x + tangent_x, y + h * fraction, z + tangent_z),
                0.10, material="structural_steel", layer=layer,
            )


def _guardrail_run(
    plan: SpecPlan,
    group: str,
    start: tuple[float, float],
    end: tuple[float, float],
    deck_y: float,
    lod: int,
    *,
    outside: bool = False,
) -> None:
    rail_heights = (0.56, 1.08) if lod < 2 else (1.02,)
    for height in rail_heights:
        _rail(
            plan, group,
            (start[0], deck_y + height, start[1]),
            (end[0], deck_y + height, end[1]),
            outside=outside,
        )
    posts = 9 if lod == 0 else 5 if lod == 1 else 2
    for index in range(posts):
        t = index / max(1, posts - 1)
        x = start[0] + (end[0] - start[0]) * t
        z = start[1] + (end[1] - start[1]) * t
        _rail(
            plan, group, (x, deck_y - 0.08, z), (x, deck_y + 1.12, z),
            outside=outside,
        )


def _build_stackhouse(plan: SpecPlan, lod: int) -> None:
    group = STACKHOUSE_ID
    bay_centres = (38.0, 55.0, 72.0, 89.0, 106.0, 123.0)
    active_bays = bay_centres if lod < 2 else bay_centres[::2]
    pier_xs = (30.2, 46.5, 63.5, 80.5, 97.5, 114.5, 131.4)
    active_piers = pier_xs if lod < 2 else pier_xs[::2] + (pier_xs[-1],)
    deck_levels = (10.0, 23.5, 37.0, 50.5, 64.0, 77.5)
    active_levels = (
        deck_levels if lod == 0
        else deck_levels[::2] if lod == 1
        else (deck_levels[0], deck_levels[3], deck_levels[-1])
    )

    north_foot = _cb(
        plan, "a22-stackhouse-foundation-spine", "old_concrete", group,
        80.8, 0.65, 120.2, 103.2, 1.3, 5.6, 0.16, "hero",
        layer="mid",
    )
    south_foot = _cb(
        plan, "a22-stackhouse-foundation-spine", "old_concrete", group,
        80.8, 0.65, 71.8, 103.2, 1.3, 5.6, 0.16, "hero",
        layer="mid",
    )
    for x in active_piers:
        for z, parent in ((72.0, south_foot), (120.0, north_foot)):
            height = 82.0
            if x in {63.5, 97.5}:
                height = 96.0
            pier = _cb(
                plan, "a22-stackhouse-hero-pier", "pale_concrete", group,
                x, height / 2 + 1.0, z, 3.7, height, 4.2,
                0.18, "hero", layer="mid",
            )
            plan.connect(
                parent, pier, axis="y", overlap_m=0.18,
                parent_face="top", child_face="bottom",
                note="Baked-chamfer fortress pier seated into foundation spine.",
            )
            if lod == 0 and z > 100.0:
                for streak_index in range(3):
                    streak_y = 15.0 + streak_index * 21.0 + (x % 4.0)
                    _cb(
                        plan, "a22-stackhouse-pier-rain-rust-streak",
                        "rust", group,
                        x + (streak_index - 1) * 0.72,
                        streak_y, z + 2.14,
                        0.24, 8.0 + streak_index * 3.0, 0.14,
                        0.02, "equipment", layer="mid",
                    )

    # Screen-scale weathering is authored as attached relief rather than a
    # shader-only claim.  Broad runoff on the camera-facing north and west
    # piers survives the locked first-person proof while the underlying PBR
    # texture still carries the fine grain.
    if lod < 2:
        weather_piers = pier_xs if lod == 0 else pier_xs[::2]
        for index, x in enumerate(weather_piers):
            streak_height = 14.0 + (index % 3) * 3.5
            streak_y = 16.0 + (index % 2) * 27.0
            _cb(
                plan, "a22-stackhouse-macro-north-rain-runoff",
                "rust", group,
                x + (-0.62 if index % 2 else 0.58),
                streak_y, 122.18,
                0.72 + (index % 3) * 0.18, streak_height, 0.18,
                0.02, "equipment", layer="mid",
            )
            if lod == 0 and index % 2 == 0:
                _cb(
                    plan, "a22-stackhouse-macro-north-rust-bloom",
                    "old_concrete", group,
                    x - 0.45, streak_y - streak_height * 0.36, 122.24,
                    2.6, 1.2, 0.16,
                    0.02, "equipment", layer="mid",
                )
        west_runoff = (
            (82.0, 17.0, 15.0),
            (91.0, 43.0, 20.0),
            (103.0, 29.0, 17.0),
            (115.0, 60.0, 21.0),
        )
        for index, (z, y, height) in enumerate(
            west_runoff if lod == 0 else west_runoff[::2]
        ):
            _cb(
                plan, "a22-stackhouse-macro-west-rain-runoff",
                "rust", group,
                27.18, y, z,
                0.86 + index * 0.16, height, 0.18,
                0.02, "equipment", yaw=-math.pi / 2, layer="mid",
            )
        seam_levels = (
            (9.0, 21.0, 33.0, 45.0, 57.0, 69.0)
            if lod == 0 else (15.0, 39.0, 63.0)
        )
        for pier_index, x in enumerate(weather_piers):
            for seam_y in seam_levels:
                _cb(
                    plan, "a22-stackhouse-camera-facing-pier-panel-seam",
                    "rust" if (pier_index + int(seam_y)) % 3 == 0
                    else "structural_steel",
                    group,
                    x, seam_y, 122.24,
                    3.25, 0.16, 0.16,
                    0.02, "equipment", layer="mid",
                )
            if pier_index % 2 == 0:
                pipe_x = x + (0.92 if pier_index % 4 == 0 else -0.92)
                plan.round_member(
                    "a22-stackhouse-camera-facing-rust-pipe-riser",
                    "rust", group,
                    (pipe_x, 1.2, 122.42),
                    (pipe_x, 72.0, 122.42),
                    0.17, 10 if lod == 0 else 8, layer="mid",
                )
        for seam_y in active_levels:
            _cb(
                plan, "a22-stackhouse-west-facade-floor-rust-seam",
                "rust", group,
                27.10, seam_y + 0.35, 96.0,
                42.0, 0.18, 0.16,
                0.02, "equipment", yaw=-math.pi / 2, layer="mid",
            )

    # Deep floor frames, intentionally open through the centre rack aisle.
    for level_index, y in enumerate(active_levels):
        for z in (75.0, 117.0):
            deck = _cb(
                plan, "a22-stackhouse-rack-deck-edge", "weathered_zinc", group,
                80.8, y, z, 102.0, 1.0, 5.0, 0.08, "secondary",
                layer="mid",
            )
            if level_index == 0:
                plan.connect(
                    south_foot if z < 90 else north_foot, deck,
                    axis="y", overlap_m=0.08, parent_face="top",
                    child_face="bottom", note="Rack deck edge overlaps support line.",
                )
            _guardrail_run(
                plan, group, (29.8, z - 2.2), (131.8, z - 2.2), y + 0.5,
                lod,
            )
        # Broad segmented plates make every level structurally credible without
        # sealing the rack fortress into one opaque box.  The three lanes leave
        # ventilation/light slots and preserve long interior parallax.
        floor_lanes = (
            (82.0, 7.2),
            (95.8, 8.0),
            (109.8, 7.2),
        )
        active_floor_lanes = (
            floor_lanes if lod == 0
            else floor_lanes[::2] if lod == 1
            else (floor_lanes[1],)
        )
        for bay_index, x in enumerate(active_bays):
            for lane_index, (z, depth) in enumerate(active_floor_lanes):
                _cb(
                    plan, "a22-stackhouse-level-floor-plate",
                    "weathered_zinc" if (bay_index + lane_index) % 3 else "rust",
                    group,
                    x, y - 0.04, z, 15.2, 0.72, depth,
                    0.07, "secondary", layer="mid",
                )
                if lod == 0 and lane_index == 1:
                    _structural_beam(
                        plan, "a22-stackhouse-floor-underside-truss", group,
                        (x - 7.0, y - 0.52, z - depth * 0.42),
                        (x + 7.0, y - 0.52, z + depth * 0.42),
                        0.34, material="structural_steel",
                    )
        _cb(
            plan, "a22-stackhouse-continuous-north-floor-fascia",
            "pale_concrete", group,
            80.8, y, 121.9, 102.0, 1.45, 1.25,
            0.08, "secondary", layer="mid",
        )
        cross_step = 1 if lod == 0 else 2
        for bay_index, x in enumerate(active_bays):
            if bay_index % cross_step:
                continue
            for z in (84.0, 96.0, 108.0):
                _cb(
                    plan, "a22-stackhouse-deep-cross-deck", "structural_steel", group,
                    x, y, z, 14.7, 0.85, 4.4, 0.07, "secondary",
                    layer="mid",
                )

    # Six independent portal frames and alternating diagonal bracing.
    frame_zs = (73.5, 84.5, 96.0, 107.5, 118.5)
    active_frame_zs = frame_zs if lod == 0 else frame_zs[::2]
    for x in active_piers:
        for z in active_frame_zs:
            top = 80.0 if x not in {63.5, 97.5} else 94.0
            _structural_beam(
                plan, "a22-stackhouse-heavy-upright", group,
                (x, 1.0, z), (x, top, z), 0.72,
            )
    brace_levels = (12.0, 39.0, 66.0) if lod == 0 else (12.0, 66.0)
    for bay_index, x in enumerate(active_bays):
        left, right = x - 7.6, x + 7.6
        for z in (73.5, 118.5):
            for base_y in brace_levels:
                if (bay_index + int(base_y)) % 2:
                    start, end = (left, base_y, z), (right, base_y + 12.0, z)
                else:
                    start, end = (right, base_y, z), (left, base_y + 12.0, z)
                _structural_beam(
                    plan, "a22-stackhouse-deep-diagonal", group,
                    start, end, 0.55, material="rust",
                )

    # Exterior X/K grammar sits outside the concrete faces.  Earlier braces
    # were physically present but hidden behind the piers from the locked
    # camera, which made the loaded floors read as disconnected boxes.
    exterior_bands = (
        (2.0, 16.0),
        (16.0, 30.0),
        (30.0, 44.0),
        (44.0, 58.0),
        (58.0, 72.0),
    )
    active_exterior_bands = (
        exterior_bands if lod == 0
        else exterior_bands[::2] if lod == 1
        else (exterior_bands[0],)
    )
    for bay_index, (left_x, right_x) in enumerate(
        zip(active_piers[:-1], active_piers[1:])
    ):
        for band_index, (low_y, high_y) in enumerate(active_exterior_bands):
            if lod == 1 and (bay_index + band_index) % 2:
                continue
            brace_material = (
                "rust" if (bay_index + band_index) % 3 == 0
                else "structural_steel"
            )
            for start, end in (
                ((left_x + 0.6, low_y, 122.35),
                 (right_x - 0.6, high_y, 122.35)),
                ((right_x - 0.6, low_y, 122.35),
                 (left_x + 0.6, high_y, 122.35)),
            ):
                _structural_beam(
                    plan, "a22-stackhouse-exterior-north-x-brace", group,
                    start, end, 0.72, material=brace_material,
                )
    west_zs = (73.0, 85.0, 97.0, 109.0, 120.0)
    active_west_zs = (
        west_zs if lod < 2
        else (west_zs[0], west_zs[2], west_zs[-1])
    )
    for cell_index, (near_z, far_z) in enumerate(
        zip(active_west_zs[:-1], active_west_zs[1:])
    ):
        for band_index, (low_y, high_y) in enumerate(active_exterior_bands):
            if lod == 1 and band_index % 2:
                continue
            _structural_beam(
                plan, "a22-stackhouse-exterior-west-k-brace", group,
                (28.15, low_y, near_z + 0.5),
                (28.15, high_y, far_z - 0.5),
                0.68,
                material="rust" if (cell_index + band_index) % 2 else
                "structural_steel",
            )
            if (cell_index + band_index) % 2 == 0:
                _structural_beam(
                    plan, "a22-stackhouse-exterior-west-k-brace", group,
                    (28.15, high_y, near_z + 0.5),
                    (28.15, low_y, far_z - 0.5),
                    0.68, material="structural_steel",
                )

    # Visible northern catwalks overlap the floor fascia and carry continuous
    # rails.  These are maintenance circulation, not gameplay collision.
    for y in active_levels:
        _cb(
            plan, "a22-stackhouse-exterior-catwalk-deck",
            "weathered_zinc", group,
            80.8, y + 0.34, 123.15, 102.0, 0.62, 2.0,
            0.07, "secondary", layer="mid",
        )
        _guardrail_run(
            plan, group, (30.0, 124.0), (131.4, 124.0),
            y + 0.64, lod,
        )

    # The camera also sees the west cutaway face.  Continuous floor fascias,
    # occupied service bays and rain streaks turn that end from a dark rack
    # section into an authored working facade.
    west_window_zs = (104.0, 115.0)
    active_west_window_zs = (
        west_window_zs if lod < 2 else ()
    )
    for level_index, y in enumerate(active_levels):
        _cb(
            plan, "a22-stackhouse-continuous-west-floor-fascia",
            "pale_concrete", group,
            28.0, y, 96.0, 1.45, 1.45, 47.0,
            0.08, "secondary", layer="mid",
        )
        for window_index, z in enumerate(active_west_window_zs):
            if lod == 1 and (level_index + window_index) % 2:
                continue
            _deep_window(
                plan, group,
                27.15, y + 5.1, z,
                7.2, 3.4, depth=1.35, yaw=-math.pi / 2,
                layer="mid",
            )
            if lod == 0:
                _cb(
                    plan, "a22-stackhouse-west-window-rain-streak",
                    "rust", group,
                    27.02, y + 1.7, z + 2.3,
                    0.18, 5.0, 0.30,
                    0.02, "equipment", yaw=-math.pi / 2,
                    layer="mid",
                )
        if lod < 2:
            _cb(
                plan, "a22-stackhouse-west-service-balcony",
                "weathered_zinc", group,
                25.8, y + 0.45, 110.0,
                4.8, 0.55, 16.0,
                0.07, "secondary", layer="mid",
            )
            _guardrail_run(
                plan, group,
                (23.7, 102.5), (23.7, 117.5),
                y + 0.72, lod,
            )
    ladder_top = max(active_levels) + 1.0
    ladder_rail_zs = (116.9, 118.1) if lod < 2 else ()
    for z in ladder_rail_zs:
        plan.round_member(
            "a22-stackhouse-west-service-ladder-rail",
            "safety_orange", group,
            (25.15, 0.8, z), (25.15, ladder_top, z),
            0.075, 10 if lod == 0 else 8, layer="mid",
        )
    ladder_rungs = 34 if lod == 0 else 18 if lod == 1 else 0
    for rung in range(ladder_rungs):
        rung_y = 1.2 + rung * (
            (ladder_top - 2.0) / max(1, ladder_rungs - 1)
        )
        plan.round_member(
            "a22-stackhouse-west-service-ladder-rung",
            "safety_orange", group,
            (25.15, rung_y, 116.9), (25.15, rung_y, 118.1),
            0.055, 8, layer="mid",
        )
    if lod < 2:
        stackhouse_worker_slots = (
            (42.0, 10.65, 123.8),
            (60.0, 24.15, 123.8),
            (79.0, 37.65, 123.8),
            (98.0, 51.15, 123.8),
            (116.0, 64.65, 123.8),
            (25.7, 78.15, 110.0),
        )
        active_worker_slots = (
            stackhouse_worker_slots if lod == 0
            else stackhouse_worker_slots[::2]
        )
        for index, (x, base_y, z) in enumerate(active_worker_slots):
            _build_worker(
                plan, group, "a22-stackhouse-catwalk-worker",
                x, z, math.pi + index * 0.18, lod,
                base_y=base_y, pose_index=index,
            )
        process_pods = (
            (24.2, 19.0, 106.0, 7.5, 7.5, 10.0),
            (23.8, 45.0, 112.0, 8.2, 9.0, 12.0),
            (24.5, 68.0, 103.0, 7.0, 8.0, 9.0),
        )
        active_process_pods = (
            process_pods if lod == 0 else process_pods[::2]
        )
        for pod_index, (x, y, z, width, height, depth) in enumerate(
            active_process_pods
        ):
            _cb(
                plan, "a22-stackhouse-west-cantilever-process-pod",
                "old_concrete" if pod_index % 2 == 0 else "weathered_zinc",
                group,
                x, y, z, width, height, depth,
                0.16, "hero", layer="mid",
            )
            _deep_window(
                plan, group,
                x - width * 0.51, y + 0.6, z,
                depth * 0.62, height * 0.45,
                depth=1.1, yaw=-math.pi / 2, layer="mid",
            )
            for side_z in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-stackhouse-west-process-pod-knee-bracket",
                    group,
                    (28.0, y - height * 0.48, z + side_z * depth * 0.38),
                    (
                        x - width * 0.42,
                        y - height * 0.10,
                        z + side_z * depth * 0.38,
                    ),
                    0.48, material="rust",
                )
        # Unequal enclosed service rooms break the otherwise continuous open
        # rack rhythm on the camera-facing north elevation.  Each room has a
        # different function/read and remains physically tied to a floor line.
        north_service_rooms = (
            (41.0, 18.0, 10.0, 13.0, 5.6),
            (67.0, 46.0, 12.0, 17.0, 6.4),
            (101.0, 31.0, 9.0, 14.0, 5.2),
            (122.0, 64.0, 8.0, 12.0, 5.0),
        )
        active_service_rooms = (
            north_service_rooms if lod == 0
            else north_service_rooms[::2]
        )
        for room_index, (x, y, width, height, depth) in enumerate(
            active_service_rooms
        ):
            room_z = 121.7 + room_index * 0.18
            _cb(
                plan, "a22-stackhouse-north-enclosed-service-room",
                "old_concrete" if room_index % 2 == 0 else "weathered_zinc",
                group,
                x, y, room_z, width, height, depth,
                0.16, "hero", layer="mid",
            )
            _deep_window(
                plan, group,
                x, y + 1.4, room_z + depth * 0.51,
                width * 0.62, height * 0.32,
                depth=1.20, yaw=math.pi, layer="mid",
            )
            _cb(
                plan, "a22-stackhouse-service-room-vent-bank",
                "structural_steel", group,
                x + width * (-0.31 if room_index % 2 else 0.31),
                y - height * 0.26, room_z + depth * 0.515,
                width * 0.22, height * 0.27, 0.24,
                0.05, "secondary", layer="mid",
            )
            vent_x = x + width * (-0.31 if room_index % 2 else 0.31)
            vent_z = room_z + depth * 0.54
            louver_count = 6 if lod == 0 else 3
            for louver_index in range(louver_count):
                _cb(
                    plan, "a22-stackhouse-service-room-vent-louver",
                    "weathered_zinc", group,
                    vent_x,
                    y - height * 0.36
                    + louver_index * (
                        height * 0.20 / max(1, louver_count - 1)
                    ),
                    vent_z,
                    width * 0.20, 0.10, 0.12,
                    0.02, "equipment", layer="mid",
                )
            _cb(
                plan, "a22-stackhouse-service-room-corroded-roof-lip",
                "rust", group,
                x, y + height * 0.52, room_z + depth * 0.08,
                width + 0.8, 0.34, depth + 0.8,
                0.05, "secondary", layer="mid",
            )
            for seam_fraction in (-0.30, 0.0, 0.30):
                _structural_beam(
                    plan, "a22-stackhouse-service-room-panel-seam", group,
                    (
                        x + width * seam_fraction,
                        y - height * 0.45,
                        room_z + depth * 0.525,
                    ),
                    (
                        x + width * seam_fraction,
                        y + height * 0.45,
                        room_z + depth * 0.525,
                    ),
                    0.09, material="rust", layer="mid",
                )
            for side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-stackhouse-service-room-floor-knee",
                    group,
                    (
                        x + side * width * 0.40,
                        y - height * 0.50,
                        119.8,
                    ),
                    (
                        x + side * width * 0.40,
                        y - height * 0.22,
                        room_z + depth * 0.40,
                    ),
                    0.42, material="rust",
                )

    # A grounded warehouse-rack skeleton gives the cargo bands obvious support
    # at every loaded level.
    rack_zs = (82.5, 90.5, 101.5, 109.5)
    active_rack_zs = rack_zs if lod == 0 else rack_zs[::2]
    rack_top = max(active_levels) + 0.15
    for bay_index, x in enumerate(active_bays):
        for rack_index, z in enumerate(active_rack_zs):
            for side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-stackhouse-grounded-rack-upright", group,
                    (x + side * 5.6, 1.0, z),
                    (x + side * 5.6, rack_top, z),
                    0.26,
                    material="rust" if rack_index % 2 == 0
                    else "structural_steel",
                )
            for shelf_y in active_levels:
                _structural_beam(
                    plan, "a22-stackhouse-grounded-rack-shelf", group,
                    (x - 5.6, shelf_y + 0.45, z),
                    (x + 5.6, shelf_y + 0.45, z),
                    0.24, material="structural_steel",
                )

    stair_runs = 5 if lod == 0 else 3 if lod == 1 else 1
    for run in range(stair_runs):
        base_y = 1.0 + run * 13.2
        if run % 2 == 0:
            start_z, end_z = 79.0, 94.0
        else:
            start_z, end_z = 94.0, 79.0
        for side_x in (25.6, 29.0):
            _structural_beam(
                plan, "a22-stackhouse-external-stair-stringer", group,
                (side_x, base_y, start_z),
                (side_x, base_y + 12.8, end_z),
                0.34, material="structural_steel",
            )
            _rail(
                plan, group,
                (side_x - 0.05, base_y + 1.05, start_z),
                (side_x - 0.05, base_y + 13.85, end_z),
            )
        tread_count = 11 if lod == 0 else 7 if lod == 1 else 4
        for step in range(tread_count):
            t = step / max(1, tread_count - 1)
            _cb(
                plan, "a22-stackhouse-external-stair-tread",
                "weathered_zinc", group,
                27.3,
                base_y + 12.8 * t,
                start_z + (end_z - start_z) * t,
                3.9, 0.22, 1.12,
                0.02, "equipment", layer="mid",
            )
        _cb(
            plan, "a22-stackhouse-external-stair-landing",
            "weathered_zinc", group,
            27.3, base_y + 12.9, end_z,
            4.2, 0.42, 3.2,
            0.07, "secondary", layer="mid",
        )
        if lod < 2:
            _cb(
                plan, "a22-stackhouse-stair-landing-warm-lamp",
                "warm_glass", group,
                25.15, base_y + 14.1, end_z,
                0.28, 0.78, 1.2,
                0.02, "equipment", layer="mid",
            )

    # Unequal functional cores stop the fortress reading as one repeated grid.
    core_specs = (
        (48.0, 93.0, 18.0, 32.0, 20.0, 0.18, 70.0),
        (68.0, 101.0, 13.0, 56.0, 16.0, 0.18, 104.0),
        (96.0, 90.0, 17.0, 43.0, 19.0, 0.16, 82.0),
        (119.0, 102.0, 16.0, 62.0, 17.0, 0.18, 116.0),
    )
    for index, (x, z, w, h, d, bevel, crown) in enumerate(core_specs):
        core_top = h + 2.0
        machine_bottom = crown - 8.0
        _cb(
            plan, "a22-stackhouse-unequal-process-core",
            "old_concrete" if index % 2 == 0 else "weathered_zinc",
            group, x, h / 2 + 2.0, z, w, h, d, bevel, "hero",
            layer="mid",
        )
        _cb(
            plan, "a22-stackhouse-crown-machine",
            "old_concrete" if index % 2 == 0 else "pale_concrete", group,
            x, crown - 4.0, z, w * 0.64, 8.0, d * 0.62,
            0.16, "hero", layer="mid",
        )
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                support_x = x + sx * w * 0.31
                support_z = z + sz * d * 0.31
                _structural_beam(
                    plan, "a22-stackhouse-crown-grounded-support", group,
                    (support_x, core_top - 0.2, support_z),
                    (support_x, machine_bottom + 0.3, support_z),
                    0.72, material="structural_steel",
                )
        if machine_bottom - core_top > 5.0:
            shaft_height = machine_bottom - core_top + 0.4
            _cb(
                plan, "a22-stackhouse-grounded-crown-lift-shaft",
                "weathered_zinc" if index % 2 else "old_concrete",
                group, x, core_top + shaft_height * 0.5 - 0.2, z,
                w * 0.54, shaft_height, d * 0.54,
                0.16, "hero", layer="mid",
            )
            mid_y = (machine_bottom + core_top) * 0.5
            _cb(
                plan, "a22-stackhouse-crown-service-platform",
                "weathered_zinc", group,
                x, mid_y, z, w * 0.80, 0.75, d * 0.80,
                0.12, "hero", layer="mid",
            )
            for side_z in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-stackhouse-crown-support-diagonal", group,
                    (x - w * 0.31, core_top, z + side_z * d * 0.31),
                    (x + w * 0.31, machine_bottom, z + side_z * d * 0.31),
                    0.48, material="rust",
                )
        if lod < 2:
            window_levels = tuple(
                level for level in (10.0, 20.0, 30.0, 40.0, 50.0)
                if level < core_top - 3.0
            )
            active_window_levels = (
                window_levels if lod == 0 else window_levels[::2]
            )
            for window_y in active_window_levels:
                _deep_window(
                    plan, group, x, window_y, z + d * 0.51,
                    w * 0.60, 3.8, depth=1.5, yaw=math.pi,
                    layer="mid",
                )
                _cb(
                    plan, "a22-stackhouse-window-rust-drip", "rust", group,
                    x + w * 0.22, window_y - 3.0, z + d * 0.525,
                    0.34, 5.0, 0.16, 0.02, "equipment",
                    layer="mid",
                )
        segments = 14 if lod == 0 else 9 if lod == 1 else 7
        plan.cylinder(
            "a22-stackhouse-crown-exhaust", "rust", group,
            x + w * 0.25, crown + 2.0, z, 1.3, 16.0,
            segments, top_radius=1.0, layer="mid",
        )

    # Two broad, unequal transfer bridges; one carries an enclosed warm gallery.
    bridge_specs = (
        (52.0, 105.0, 71.5, 96.0, 9.0, 9.0),
        (77.0, 124.0, 57.5, 102.0, 6.5, 7.0),
    )
    active_bridges = bridge_specs if lod < 2 else bridge_specs[:1]
    for index, (x0, x1, y, z, width, height) in enumerate(active_bridges):
        centre_x = (x0 + x1) * 0.5
        length = x1 - x0 + 1.0
        _cb(
            plan, "a22-stackhouse-transfer-bridge-floor",
            "structural_steel", group, centre_x, y, z, length, 1.4, width,
            0.16, "hero", layer="mid",
        )
        _cb(
            plan, "a22-stackhouse-transfer-bridge-roof",
            "weathered_zinc", group, centre_x, y + height, z,
            length, 1.1, width, 0.14, "hero", layer="mid",
        )
        for side_z in (z - width * 0.47, z + width * 0.47):
            _structural_beam(
                plan, "a22-stackhouse-transfer-chord", group,
                (x0, y + 0.7, side_z), (x1, y + height - 0.5, side_z),
                0.65,
            )
            _structural_beam(
                plan, "a22-stackhouse-transfer-chord", group,
                (x0, y + height - 0.5, side_z), (x1, y + 0.7, side_z),
                0.65,
            )
        if index == 0 and lod < 2:
            _deep_window(
                plan, group, centre_x, y + height * 0.54,
                z - width * 0.505, length * 0.82, height * 0.52,
                depth=1.2, layer="mid",
            )

    # Loaded rack cells create real parallax and an obviously working interior.
    cargo_levels = active_levels[:-1]
    z_cells = (82.5, 90.5, 101.5, 109.5)
    active_z_cells = z_cells if lod == 0 else z_cells[::2]
    cargo_repeat = 3 if lod == 0 else 1
    for bay_index, x in enumerate(active_bays):
        for level_index, deck_y in enumerate(cargo_levels):
            for z_index, z in enumerate(active_z_cells):
                for repeat in range(cargo_repeat):
                    offset = (repeat - (cargo_repeat - 1) / 2) * 3.3
                    width = 2.7 + 0.25 * ((bay_index + repeat) % 3)
                    height = 2.1 + 0.4 * ((level_index + z_index) % 2)
                    _cb(
                        plan, "a22-stackhouse-loaded-rack-cargo",
                        ("weathered_zinc", "rust", "pallet_wood")[
                            (bay_index + level_index + z_index + repeat) % 3
                        ],
                        group, x + offset, deck_y + 2.0, z,
                        width, height, 2.5, 0.02, "equipment",
                        layer="mid",
                    )
                    if lod == 0:
                        _cb(
                            plan, "a22-stackhouse-cargo-band", "safety_orange",
                            group, x + offset, deck_y + 2.05, z - 1.29,
                            width * 0.78, 0.18, 0.12, 0.02, "equipment",
                            layer="mid",
                        )

    if lod < 2:
        occupied_levels = active_levels[:-1]
        for bay_index, x in enumerate(active_bays):
            for level_index, deck_y in enumerate(occupied_levels):
                if lod == 1 and level_index % 2:
                    continue
                width = 7.2 + (bay_index % 2) * 1.1
                _deep_window(
                    plan, group,
                    x, deck_y + 5.0, 122.65,
                    width, 3.3, depth=1.45, yaw=math.pi,
                    layer="mid",
                )
        machine_light_grid = (
            (38.0, 16.0),
            (55.0, 29.0),
            (72.0, 42.0),
            (89.0, 55.0),
            (106.0, 68.0),
            (123.0, 29.0),
            (47.0, 55.0),
            (98.0, 16.0),
        )
        active_machine_light_grid = (
            machine_light_grid if lod == 0 else machine_light_grid[::2]
        )
        for grid_index, (x, y) in enumerate(active_machine_light_grid):
            _cb(
                plan, "a22-stackhouse-visible-interior-machine-grid",
                "weathered_zinc" if grid_index % 2 else "structural_steel",
                group,
                x, y, 119.0,
                5.2, 3.8, 2.4,
                0.08, "secondary", layer="mid",
            )
            _cb(
                plan, "a22-stackhouse-visible-interior-light-grid",
                "warm_glass", group,
                x, y + 2.5, 120.30,
                3.8, 0.52, 0.28,
                0.02, "equipment", layer="mid",
            )
            if lod == 0 and grid_index % 2 == 0:
                _cb(
                    plan, "a22-stackhouse-interior-machine-warning-marker",
                    "safety_orange", group,
                    x + 1.75, y, 120.32,
                    0.46, 2.5, 0.16,
                    0.02, "equipment", layer="mid",
                )

    # Hoists, ducts, cable trays and maintenance platforms finish the silhouette.
    machine_count = 28 if lod == 0 else 12 if lod == 1 else 5
    service_deck_y = max(active_levels)
    service_zs = (82.0, 95.8, 109.8)
    for index in range(machine_count):
        x = 36.0 + (index % 14) * 6.8
        z = service_zs[(index // 7) % len(service_zs)]
        y = service_deck_y + 1.35
        _cb(
            plan, "a22-stackhouse-maintenance-equipment",
            "structural_steel" if index % 3 else "rust",
            group, x, y, z, 4.2, 2.4, 3.2, 0.02, "equipment",
            layer="mid",
        )
        if lod < 2:
            _cb(
                plan, "a22-stackhouse-maintenance-equipment-skid",
                "safety_orange", group,
                x, service_deck_y + 0.48, z,
                4.8, 0.34, 3.6, 0.02, "equipment",
                layer="mid",
            )
            _rail(
                plan, group, (x - 2.0, y + 1.35, z),
                (x + 2.0, y + 1.35, z),
            )


def _build_customs(plan: SpecPlan, lod: int) -> None:
    group = CUSTOMS_ID
    x_edges = (-113.5, -91.0, -68.5, -46.0, -22.5)
    hall_front, hall_back = -29.0, -105.5
    foundation = _cb(
        plan, "a22-customs-foundation-slab", "old_concrete", group,
        -68.0, 0.7, -67.5, 91.0, 1.4, 76.0, 0.16, "hero",
        layer="mid",
    )
    # Keep the canonical entrance portal visibly and physically open.
    for x0, x1 in zip(x_edges[:-1], x_edges[1:]):
        centre = (x0 + x1) * 0.5
        _cb(
            plan, "a22-customs-loading-plinth", "pale_concrete", group,
            centre, 2.4, -98.0, (x1 - x0) - 1.2, 3.4, 14.0,
            0.16, "hero", layer="mid",
        )
    frame_zs = tuple(-31.0 - index * 10.4 for index in range(8))
    active_frame_zs = (
        frame_zs if lod == 0
        else frame_zs[::2] if lod == 1
        else (frame_zs[0], frame_zs[3], frame_zs[-1])
    )
    ridge_heights = (36.0, 43.0, 34.0, 47.0)
    eave_heights = (23.0, 25.0, 22.0, 27.0)
    for bay_index, (x0, x1) in enumerate(zip(x_edges[:-1], x_edges[1:])):
        ridge = ridge_heights[bay_index]
        eave = eave_heights[bay_index]
        for z in active_frame_zs:
            for x in (x0 + 0.8, x1 - 0.8):
                _cb(
                    plan, "a22-customs-heavy-portal-leg",
                    "old_concrete" if bay_index % 2 == 0 else "structural_steel",
                    group, x, eave * 0.5, z, 1.8, eave, 2.0,
                    0.15, "hero", layer="mid",
                )
            _structural_beam(
                plan, "a22-customs-sawtooth-rafter", group,
                (x0 + 0.4, eave, z), ((x0 + x1) * 0.5, ridge, z),
                0.78, material="rust",
            )
            _structural_beam(
                plan, "a22-customs-sawtooth-rafter", group,
                ((x0 + x1) * 0.5, ridge, z), (x1 - 0.4, eave + 4.0, z),
                0.78,
            )
        # Four actual full-depth roof faces and translucent sawtooth faces.
        mid = (x0 + x1) * 0.5
        plan.panel(
            "a22-customs-full-depth-sawtooth-roof", "weathered_zinc", group,
            (
                (x0 + 0.3, eave, hall_front),
                (mid, ridge, hall_front),
                (mid, ridge, hall_back),
                (x0 + 0.3, eave, hall_back),
            ),
            0.55, layer="mid",
        )
        plan.panel(
            "a22-customs-full-depth-sawtooth-roof", "weathered_zinc", group,
            (
                (mid, ridge, hall_front),
                (x1 - 0.3, eave + 4.0, hall_front),
                (x1 - 0.3, eave + 4.0, hall_back),
                (mid, ridge, hall_back),
            ),
            0.55, layer="mid",
        )
        plan.panel(
            "a22-customs-full-depth-sawtooth-glazing", "dirty_glass", group,
            (
                (mid - 0.20, eave + 4.2, hall_front + 0.1),
                (mid - 0.20, ridge - 0.5, hall_front + 0.1),
                (mid - 0.20, ridge - 0.5, hall_back - 0.1),
                (mid - 0.20, eave + 4.2, hall_back - 0.1),
            ),
            0.20, layer="mid",
        )
        if lod < 2:
            # Warm depth is separated from glass by 1.8 m.
            plan.panel(
                "a22-customs-sawtooth-warm-backing", "warm_glass", group,
                (
                    (mid + 1.6, eave + 4.6, hall_front + 1.0),
                    (mid + 1.6, ridge - 1.0, hall_front + 1.0),
                    (mid + 1.6, ridge - 1.0, hall_back - 1.0),
                    (mid + 1.6, eave + 4.6, hall_back - 1.0),
                ),
                0.18, layer="mid",
            )
        # Full-depth gutters and standing seams make the four roof machines
        # readable as fabricated industrial bays instead of smooth wedges.
        seam_fractions = (
            (0.10, 0.20, 0.31, 0.42, 0.58, 0.70, 0.82, 0.92)
            if lod == 0
            else (0.18, 0.40, 0.64, 0.86) if lod == 1
            else (0.50,)
        )
        for seam_index, fraction in enumerate(seam_fractions):
            if fraction <= 0.5:
                local_t = fraction * 2.0
                seam_x = x0 + 0.3 + (mid - x0 - 0.3) * local_t
                seam_y = eave + (ridge - eave) * local_t
            else:
                local_t = (fraction - 0.5) * 2.0
                seam_x = mid + (x1 - 0.3 - mid) * local_t
                seam_y = ridge + (eave + 4.0 - ridge) * local_t
            _structural_beam(
                plan, "a22-customs-standing-seam", group,
                (seam_x, seam_y + 0.34, hall_front - 0.15),
                (seam_x, seam_y + 0.34, hall_back + 0.15),
                0.17,
                material="rust" if seam_index % 2 == 0
                else "structural_steel",
            )
        for gutter_x, gutter_y in (
            (x0 + 0.45, eave + 0.15),
            (x1 - 0.45, eave + 4.15),
        ):
            plan.round_member(
                "a22-customs-full-depth-roof-gutter", "rust", group,
                (gutter_x, gutter_y, hall_front - 0.55),
                (gutter_x, gutter_y, hall_back + 0.55),
                0.24, 12 if lod == 0 else 8, layer="mid",
            )
            if lod < 2:
                plan.round_member(
                    "a22-customs-roof-downspout", "rust", group,
                    (gutter_x, gutter_y, hall_front - 0.60),
                    (gutter_x, 1.2, hall_front - 0.60),
                    0.20, 10 if lod == 0 else 8, layer="mid",
                )
        _structural_beam(
            plan, "a22-customs-sawtooth-front-edge", group,
            (x0 + 0.3, eave, hall_front - 0.58),
            (mid, ridge, hall_front - 0.58),
            0.48, material="rust",
        )
        _structural_beam(
            plan, "a22-customs-sawtooth-front-edge", group,
            (mid, ridge, hall_front - 0.58),
            (x1 - 0.3, eave + 4.0, hall_front - 0.58),
            0.48, material="structural_steel",
        )

    # Wide rain tails below the four roof machines make the terminal's age
    # legible at the primary camera distance.  These are sparse macro marks,
    # not a repeated decal wallpaper.
    if lod < 2:
        runoff_xs = (
            -111.6, -92.2, -88.8, -69.0,
            -65.2, -47.1, -43.8, -24.5,
        )
        active_runoff_xs = runoff_xs if lod == 0 else runoff_xs[::2]
        for index, x in enumerate(active_runoff_xs):
            height = 9.0 + (index % 4) * 2.8
            _cb(
                plan, "a22-customs-macro-gutter-rain-runoff",
                "rust", group,
                x, 7.0 + (index % 2) * 3.0, -27.76,
                0.58 + (index % 3) * 0.20, height, 0.18,
                0.02, "equipment", layer="mid",
            )
        _cb(
            plan, "a22-customs-front-ground-grime-band",
            "rust", group,
            -68.0, 1.25, -27.80,
            88.0, 0.72, 0.20,
            0.02, "equipment", layer="mid",
        )

    # Longitudinal purlins and gantry rails make the hall read as one long machine.
    purlin_count = 12 if lod == 0 else 6 if lod == 1 else 3
    for index in range(purlin_count):
        t = index / max(1, purlin_count - 1)
        z = hall_front + (hall_back - hall_front) * t
        for bay_index, (x0, x1) in enumerate(zip(x_edges[:-1], x_edges[1:])):
            ridge = ridge_heights[bay_index]
            _structural_beam(
                plan, "a22-customs-longitudinal-purlin", group,
                (x0 + 1.0, eave_heights[bay_index] - 1.0, z),
                (x1 - 1.0, eave_heights[bay_index] - 1.0, z),
                0.46,
            )
            _rail(
                plan, group, ((x0 + x1) * 0.5, ridge - 5.0, z - 4.0),
                ((x0 + x1) * 0.5, ridge - 5.0, z + 4.0),
            )

    # Real interior: four process lines, conveyors, bridge cranes and cargo.
    machine_rows = 13 if lod == 0 else 6 if lod == 1 else 3
    for bay_index, (x0, x1) in enumerate(zip(x_edges[:-1], x_edges[1:])):
        centre = (x0 + x1) * 0.5
        for row in range(machine_rows):
            z = -37.0 - row * (61.0 / max(1, machine_rows - 1))
            _cb(
                plan, "a22-customs-deep-machine-line",
                "structural_steel" if row % 3 else "rust", group,
                centre - 3.3, 4.4, z, 5.4, 5.4, 3.6,
                0.02, "equipment", layer="mid",
            )
            _cb(
                plan, "a22-customs-conveyor-bed", "structural_steel", group,
                centre + 3.7, 2.4, z, 4.0, 1.3, 7.6,
                0.02, "equipment", layer="mid",
            )
            if lod == 0:
                for side in (-1, 1):
                    plan.cylinder(
                        "a22-customs-conveyor-roller", "structural_steel", group,
                        centre + 3.7 + side * 1.6, 3.25, z,
                        0.26, 4.0, 10, top_radius=0.26, layer="mid",
                    )
        if lod < 2:
            for z in (-49.0, -78.0):
                _structural_beam(
                    plan, "a22-customs-overhead-crane", group,
                    (x0 + 1.2, 17.0, z), (x1 - 1.2, 17.0, z),
                    0.85, material="safety_orange",
                )
                _rail(
                    plan, group, (centre, 17.0, z), (centre, 9.0, z),
                )
            fixture_zs = (-40.0, -57.0, -74.0, -91.0)
            for fixture_index, z in enumerate(fixture_zs):
                _cb(
                    plan, "a22-customs-occupied-machine-light",
                    "warm_glass", group,
                    centre + (-3.2 if fixture_index % 2 else 3.2),
                    9.5 + (fixture_index % 2) * 2.3,
                    z, 2.8, 1.3, 0.42,
                    0.05, "secondary", layer="mid",
                )

    # Offset control tower dominates the right-hand silhouette.
    tower_x, tower_z = -70.0, -99.0
    tower_base = _cb(
        plan, "a22-customs-control-tower-base", "old_concrete", group,
        tower_x, 29.0, tower_z, 16.0, 56.0, 18.0,
        0.20, "hero", layer="mid",
    )
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-customs-tower-exoskeleton-leg", group,
                (tower_x + sx * 10.1, 0.8, tower_z + sz * 10.1),
                (tower_x + sx * 10.1, 74.5, tower_z + sz * 10.1),
                0.78, material="structural_steel",
            )
    brace_levels = (3.0, 16.0, 29.0, 42.0, 55.0)
    for level_index, level_y in enumerate(brace_levels):
        if level_index % 2:
            first_x, second_x = tower_x - 10.1, tower_x + 10.1
        else:
            first_x, second_x = tower_x + 10.1, tower_x - 10.1
        _structural_beam(
            plan, "a22-customs-tower-exoskeleton-diagonal", group,
            (first_x, level_y, tower_z + 10.15),
            (second_x, level_y + 12.0, tower_z + 10.15),
            0.58, material="rust",
        )
    if lod < 2:
        for window_y in (12.0, 25.0, 38.0, 49.0):
            _deep_window(
                plan, group, tower_x, window_y, tower_z + 9.12,
                9.2, 4.2, depth=1.4, yaw=math.pi, layer="mid",
            )
            _deep_window(
                plan, group, tower_x - 8.12, window_y, tower_z,
                8.0, 4.2, depth=1.4, yaw=-math.pi / 2, layer="mid",
            )
        for balcony_index, balcony_y in enumerate((18.0, 31.0, 44.0)):
            _cb(
                plan, "a22-customs-tower-mid-service-balcony",
                "weathered_zinc", group,
                tower_x, balcony_y, tower_z + 10.1,
                18.5, 0.52, 3.6,
                0.07, "secondary", layer="mid",
            )
            _guardrail_run(
                plan, group,
                (tower_x - 8.8, tower_z + 11.7),
                (tower_x + 8.8, tower_z + 11.7),
                balcony_y + 0.28, lod,
            )
            for side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-customs-tower-balcony-knee-bracket", group,
                    (
                        tower_x + side * 7.2,
                        balcony_y - 3.1,
                        tower_z + 9.2,
                    ),
                    (
                        tower_x + side * 7.2,
                        balcony_y - 0.2,
                        tower_z + 11.5,
                    ),
                    0.34, material="rust",
                )
            _cb(
                plan, "a22-customs-tower-balcony-warm-task-light",
                "warm_glass", group,
                tower_x + (-5.5 if balcony_index % 2 else 5.5),
                balcony_y + 2.0, tower_z + 9.25,
                1.0, 0.48, 0.24,
                0.02, "equipment", layer="mid",
            )
        for side in (-1.0, 1.0):
            _cb(
                plan, "a22-customs-tower-recessed-facade-panel",
                "weathered_zinc", group,
                tower_x + side * 5.7, 31.0, tower_z + 9.18,
                2.8, 43.0, 0.26,
                0.06, "secondary", layer="mid",
            )
    # A true external stair climbs the visible west face to the control
    # balcony.  It is deliberately oversized enough to survive the primary
    # production camera and supplies human scale to the tower.
    tower_stair_runs = 4 if lod == 0 else 3 if lod == 1 else 1
    for run in range(tower_stair_runs):
        base_y = 1.2 + run * 13.3
        if run % 2 == 0:
            start_z, end_z = tower_z - 7.2, tower_z + 7.2
        else:
            start_z, end_z = tower_z + 7.2, tower_z - 7.2
        for side_x in (tower_x - 12.7, tower_x - 9.7):
            _structural_beam(
                plan, "a22-customs-tower-external-stair-stringer", group,
                (side_x, base_y, start_z),
                (side_x, base_y + 12.7, end_z),
                0.42, material="safety_orange",
            )
            _rail(
                plan, group,
                (side_x - 0.06, base_y + 1.0, start_z),
                (side_x - 0.06, base_y + 13.7, end_z),
            )
            _structural_beam(
                plan, "a22-customs-tower-stair-heavy-handrail", group,
                (side_x - 0.08, base_y + 1.2, start_z),
                (side_x - 0.08, base_y + 13.9, end_z),
                0.13, material="safety_orange",
            )
        tower_treads = 10 if lod == 0 else 6 if lod == 1 else 3
        for step in range(tower_treads):
            t = step / max(1, tower_treads - 1)
            _cb(
                plan, "a22-customs-tower-external-stair-tread",
                "weathered_zinc", group,
                tower_x - 11.2, base_y + 12.7 * t,
                start_z + (end_z - start_z) * t,
                4.2, 0.20, 1.20,
                0.02, "equipment", layer="mid",
            )
        _cb(
            plan, "a22-customs-tower-stair-landing",
            "weathered_zinc", group,
            tower_x - 11.2, base_y + 12.9, end_z,
            4.8, 0.42, 3.5,
            0.07, "secondary", layer="mid",
        )
        if lod < 2:
            _cb(
                plan, "a22-customs-tower-stair-warm-lamp",
                "warm_glass", group,
                tower_x - 13.3, base_y + 14.0, end_z,
                0.28, 0.78, 1.1,
                0.02, "equipment", layer="mid",
            )
    for band_y in (12.0, 25.0, 38.0, 51.0):
        _cb(
            plan, "a22-customs-control-tower-weather-band", "rust", group,
            tower_x, band_y, tower_z - 9.12, 13.8, 0.55, 0.30,
            0.05, "secondary", layer="mid",
        )
    if lod < 2:
        for index, (offset_x, y, height) in enumerate((
            (-5.2, 18.0, 21.0),
            (0.4, 35.0, 18.0),
            (5.4, 48.0, 22.0),
        )):
            _cb(
                plan, "a22-customs-tower-macro-north-rain-runoff",
                "rust", group,
                tower_x + offset_x, y, tower_z + 9.20,
                0.68 + index * 0.12, height, 0.18,
                0.02, "equipment", layer="mid",
            )
        for index, (offset_z, y) in enumerate(((4.8, 22.0), (-3.8, 45.0))):
            _cb(
                plan, "a22-customs-tower-macro-west-rain-runoff",
                "rust", group,
                tower_x - 8.20, y, tower_z + offset_z,
                0.72 + index * 0.16, 17.0 + index * 4.0, 0.18,
                0.02, "equipment", yaw=-math.pi / 2, layer="mid",
            )
    _cb(
        plan, "a22-customs-control-tower-balcony", "structural_steel", group,
        tower_x, 55.2, tower_z, 21.0, 0.75, 21.0,
        0.12, "hero", layer="mid",
    )
    for start, end in (
        ((tower_x - 10.0, tower_z - 10.0), (tower_x + 10.0, tower_z - 10.0)),
        ((tower_x + 10.0, tower_z - 10.0), (tower_x + 10.0, tower_z + 10.0)),
        ((tower_x + 10.0, tower_z + 10.0), (tower_x - 10.0, tower_z + 10.0)),
        ((tower_x - 10.0, tower_z + 10.0), (tower_x - 10.0, tower_z - 10.0)),
    ):
        _guardrail_run(plan, group, start, end, 55.6, lod)
    _cb(
        plan, "a22-customs-control-tower-cab", "weathered_zinc", group,
        tower_x, 63.5, tower_z, 23.0, 13.0, 23.0,
        0.18, "hero", layer="mid",
    )
    for yaw, x, z in (
        (0.0, tower_x, tower_z - 12.2),
        (math.pi, tower_x, tower_z + 12.2),
        (math.pi / 2, tower_x + 12.2, tower_z),
        (-math.pi / 2, tower_x - 12.2, tower_z),
    ):
        _deep_window(
            plan, group, x, 64.0, z, 16.0, 6.4,
            depth=1.8, yaw=yaw, layer="mid",
        )
    _cb(
        plan, "a22-customs-control-room-warm-occupancy", "warm_glass", group,
        tower_x, 64.0, tower_z + 11.72, 17.0, 5.2, 0.34,
        0.05, "secondary", yaw=math.pi, layer="mid",
    )
    _cb(
        plan, "a22-customs-control-tower-crown", "weathered_zinc", group,
        tower_x, 74.0, tower_z, 27.0, 4.0, 27.0,
        0.18, "hero", layer="mid",
    )
    plan.cylinder(
        "a22-customs-radar-drum", "structural_steel", group,
        tower_x, 84.0, tower_z, 4.8, 14.0,
        16 if lod == 0 else 10, top_radius=3.6, layer="mid",
    )
    plan.round_member(
        "a22-customs-tower-antenna-mast", "structural_steel", group,
        (tower_x, 91.0, tower_z), (tower_x, 111.0, tower_z),
        0.34, 12 if lod == 0 else 8, layer="mid",
    )
    for angle in (0.0, math.pi / 2):
        dx, dz = math.cos(angle) * 7.0, math.sin(angle) * 7.0
        plan.round_member(
            "a22-customs-tower-antenna-yard", "safety_orange", group,
            (tower_x - dx, 104.0, tower_z - dz),
            (tower_x + dx, 104.0, tower_z + dz),
            0.18, 10 if lod == 0 else 8, layer="mid",
        )
    plan.connect(
        foundation, tower_base, axis="y", overlap_m=0.20,
        parent_face="top", child_face="bottom",
        note="Control tower grounded in terminal foundation.",
    )

    # Loading docks have deep reveals rather than black rectangles.
    dock_count = 10 if lod == 0 else 6 if lod == 1 else 4
    for index in range(dock_count):
        x = -108.0 + index * (80.0 / max(1, dock_count - 1))
        for side in (-1.0, 1.0):
            _cb(
                plan, "a22-customs-loading-portal-jamb",
                "structural_steel", group,
                x + side * 2.85, 6.8, -28.9, 0.9, 12.0, 1.8,
                0.14, "hero", layer="mid",
            )
        _cb(
            plan, "a22-customs-loading-portal-header",
            "structural_steel", group,
            x, 12.3, -28.9, 6.6, 1.0, 1.8,
            0.14, "hero", layer="mid",
        )
        _cb(
            plan, "a22-customs-loading-warm-depth", "warm_glass", group,
            x, 10.4, -34.4, 4.8, 1.2, 0.65,
            0.06, "secondary", layer="mid",
        )
        _cb(
            plan, "a22-customs-front-machine-bank",
            "weathered_zinc" if index % 2 else "old_concrete", group,
            x, 4.4, -34.9, 4.7, 6.0, 2.8,
            0.08, "secondary", layer="mid",
        )
        if lod < 2 and index % 2 == 0:
            _cb(
                plan, "a22-customs-portal-grounded-loaded-pallet",
                "pallet_wood", group,
                x, 0.38, -31.65, 4.4, 0.48, 2.6,
                0.05, "secondary", layer="mid",
            )
            _cb(
                plan, "a22-customs-portal-loaded-service-crate",
                "weathered_zinc" if index % 4 else "rust", group,
                x, 1.35, -31.65, 3.6, 1.45, 2.0,
                0.06, "secondary", layer="mid",
            )
            _cb(
                plan, "a22-customs-portal-crate-hazard-band",
                "safety_orange", group,
                x, 1.35, -30.60, 2.9, 0.22, 0.16,
                0.02, "equipment", layer="mid",
            )
        if lod < 2 and index % 3 == 1:
            for pipe_y in (0.72, 1.16, 1.60):
                plan.round_member(
                    "a22-customs-portal-grounded-pipe-bundle",
                    "structural_steel" if pipe_y < 1.5 else "rust",
                    group,
                    (x - 2.0, pipe_y, -31.8),
                    (x + 2.0, pipe_y, -31.8),
                    0.20, 10 if lod == 0 else 8, layer="mid",
                )
        if lod < 2 and index % 2 == 1:
            cart_z = -31.7
            _cb(
                plan, "a22-customs-portal-moving-agv-body",
                "safety_orange", group,
                x, 0.92, cart_z,
                3.2, 0.95, 2.0,
                0.06, "secondary", layer="mid",
            )
            for wheel_x in (x - 1.05, x + 1.05):
                plan.round_member(
                    "a22-customs-portal-moving-agv-wheel",
                    "structural_steel", group,
                    (wheel_x, 0.48, cart_z - 0.92),
                    (wheel_x, 0.48, cart_z + 0.92),
                    0.34, 10 if lod == 0 else 8, layer="mid",
                )
            _cb(
                plan, "a22-customs-portal-moving-agv-status-light",
                "warm_glass", group,
                x, 1.58, cart_z,
                0.70, 0.34, 0.70,
                0.02, "equipment", layer="mid",
            )
        if lod < 2 and index % 3 == 0:
            _build_worker(
                plan, group, "a22-customs-portal-ground-worker",
                x + 1.9, -25.3, -math.pi / 2, lod,
                pose_index=index + 1,
            )
        for side in (-1.0, 1.0):
            _cb(
                plan, "a22-customs-front-machine-control-panel",
                "safety_orange", group,
                x + side * 1.55, 5.2, -33.38,
                0.72, 1.8, 0.22,
                0.02, "equipment", layer="mid",
            )
        if lod < 2:
            _structural_beam(
                plan, "a22-customs-front-machine-overhead-beam", group,
                (x - 2.25, 8.0, -33.2),
                (x + 2.25, 8.0, -33.2),
                0.34, material="safety_orange",
            )
            _cb(
                plan, "a22-customs-front-machine-task-light",
                "warm_glass", group,
                x, 8.65, -33.05,
                1.8, 0.52, 0.26,
                0.02, "equipment", layer="mid",
            )
        if lod < 2:
            plan.round_member(
                "a22-customs-front-machine-service-drum",
                "structural_steel", group,
                (x - 1.8, 1.5, -33.9),
                (x + 1.8, 1.5, -33.9),
                0.48, 12 if lod == 0 else 8, layer="mid",
            )
        # A second occupied facade tier closes the blank zone between the
        # loading portals and sawtooth roof while retaining deep ground bays.
        _cb(
            plan, "a22-customs-upper-facade-spandrel",
            "old_concrete" if index % 2 == 0 else "weathered_zinc",
            group,
            x, 17.6, -28.72,
            7.0, 6.4, 1.45,
            0.08, "secondary", layer="mid",
        )
        if lod < 2:
            _deep_window(
                plan, group,
                x, 18.1, -27.88,
                5.2, 2.8, depth=1.15, yaw=math.pi,
                layer="mid",
            )
            _cb(
                plan, "a22-customs-upper-facade-rust-streak",
                "rust", group,
                x + 2.6, 14.3, -27.82,
                0.28, 4.2, 0.18,
                0.02, "equipment", layer="mid",
            )
            for seam_side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-customs-upper-facade-panel-seam", group,
                    (x + seam_side * 2.65, 14.7, -27.80),
                    (x + seam_side * 2.65, 20.6, -27.80),
                    0.09,
                    material="rust" if index % 2 else "structural_steel",
                    layer="mid",
                )
            louver_count = 4 if lod == 0 else 2
            for louver_index in range(louver_count):
                _cb(
                    plan, "a22-customs-upper-facade-camera-louver",
                    "structural_steel", group,
                    x, 15.0 + louver_index * 0.42, -27.73,
                    2.8, 0.11, 0.13,
                    0.02, "equipment", layer="mid",
                )
            if index % 2 == 1:
                plan.box(
                    "a22-customs-portal-oil-grime-relief",
                    "rust", group,
                    x + 0.8, 0.168, -24.8,
                    4.6, 0.010, 1.3,
                    yaw=(index % 3 - 1) * 0.08, layer="mid",
                )

    if lod < 2:
        facade_pipe_xs = (
            (-104.0, 1.0),
            (-77.0, -1.0),
            (-51.0, 1.0),
            (-31.0, -1.0),
        )
        active_pipe_xs = (
            facade_pipe_xs if lod == 0 else facade_pipe_xs[::2]
        )
        for pipe_index, (pipe_x, direction) in enumerate(active_pipe_xs):
            plan.round_member(
                "a22-customs-camera-facing-process-pipe-riser",
                "rust" if pipe_index % 2 == 0 else "safety_orange",
                group,
                (pipe_x, 1.0, -27.45),
                (pipe_x, 22.0, -27.45),
                0.22, 10 if lod == 0 else 8, layer="mid",
            )
            plan.round_member(
                "a22-customs-camera-facing-process-pipe-header",
                "rust" if pipe_index % 2 == 0 else "safety_orange",
                group,
                (pipe_x, 22.0, -27.45),
                (pipe_x + direction * 5.0, 22.0, -27.45),
                0.22, 10 if lod == 0 else 8, layer="mid",
            )
            for bracket_y in (5.0, 12.0, 19.0):
                _cb(
                    plan, "a22-customs-process-pipe-wall-bracket",
                    "structural_steel", group,
                    pipe_x, bracket_y, -27.65,
                    1.0, 0.18, 0.34,
                    0.02, "equipment", layer="mid",
                )

        ladder_x, ladder_z = -39.0, -25.55
        for side in (-1.0, 1.0):
            plan.round_member(
                "a22-customs-front-service-ladder-rail",
                "safety_orange", group,
                (ladder_x + side * 0.62, 0.8, ladder_z),
                (ladder_x + side * 0.62, 14.6, ladder_z),
                0.075, 8, layer="mid",
            )
        ladder_rungs = 18 if lod == 0 else 10
        for rung in range(ladder_rungs):
            rung_y = 1.1 + rung * (13.0 / max(1, ladder_rungs - 1))
            plan.round_member(
                "a22-customs-front-service-ladder-rung",
                "safety_orange", group,
                (ladder_x - 0.62, rung_y, ladder_z),
                (ladder_x + 0.62, rung_y, ladder_z),
                0.055, 8, layer="mid",
            )

    _cb(
        plan, "a22-customs-continuous-front-catwalk",
        "weathered_zinc", group,
        -68.0, 14.1, -27.45,
        88.0, 0.62, 2.4,
        0.07, "secondary", layer="mid",
    )
    _guardrail_run(
        plan, group,
        (-111.5, -26.15), (-24.5, -26.15),
        14.45, lod,
    )
    if lod < 2:
        _cb(
            plan, "a22-customs-deep-interior-moving-equipment-catwalk",
            "weathered_zinc", group,
            -68.0, 9.0, -38.2,
            84.0, 0.52, 1.8,
            0.07, "secondary", layer="mid",
        )
        for rail_y in (9.65, 10.20):
            _structural_beam(
                plan, "a22-customs-deep-interior-catwalk-rail", group,
                (-109.0, rail_y, -37.25),
                (-27.0, rail_y, -37.25),
                0.12, material="safety_orange", layer="mid",
            )
        interior_posts = 9 if lod == 0 else 5
        for post_index in range(interior_posts):
            post_x = -108.0 + post_index * (
                80.0 / max(1, interior_posts - 1)
            )
            _structural_beam(
                plan, "a22-customs-deep-interior-catwalk-post", group,
                (post_x, 8.85, -37.25),
                (post_x, 10.28, -37.25),
                0.11, material="safety_orange", layer="mid",
            )
        catwalk_worker_xs = (
            (-101.0, -82.0, -63.0, -44.0, -29.0)
            if lod == 0 else (-91.0, -58.0, -31.0)
        )
        for index, x in enumerate(catwalk_worker_xs):
            _build_worker(
                plan, group, "a22-customs-catwalk-worker",
                x, -26.15, math.pi + index * 0.22, lod,
                base_y=14.45, pose_index=index + 1,
            )


def _build_hero_finish_pass(plan: SpecPlan, lod: int) -> None:
    """Add attached three-frequency finish to the two camera-facing heroes."""
    if lod >= 2:
        return

    stack_panel_xs = (38.0, 55.0, 72.0, 89.0, 106.0, 123.0)
    active_stack_xs = stack_panel_xs if lod == 0 else stack_panel_xs[::2]
    stack_panel_levels = (18.0, 46.0) if lod == 0 else (32.0,)
    for panel_index, x in enumerate(active_stack_xs):
        for level_index, panel_y in enumerate(stack_panel_levels):
            _cb(
                plan, "a22-stackhouse-finish-large-north-access-panel",
                "weathered_zinc"
                if (panel_index + level_index) % 2 else "old_concrete",
                STACKHOUSE_ID,
                x, panel_y, 122.58,
                7.8, 4.4, 0.24,
                0.06, "secondary", layer="mid",
            )
            if lod == 0:
                _cb(
                    plan, "a22-stackhouse-finish-small-number-marker",
                    "pale_concrete" if panel_index % 2 else "safety_orange",
                    STACKHOUSE_ID,
                    x + (-1.8 if level_index else 1.8),
                    panel_y + 0.35, 122.76,
                    1.75, 0.72, 0.12,
                    0.02, "equipment", layer="mid",
                )
    west_finish = (
        (84.0, 18.0),
        (100.0, 43.0),
        (115.0, 69.0),
    )
    active_west_finish = west_finish if lod == 0 else west_finish[::2]
    for panel_index, (z, panel_y) in enumerate(active_west_finish):
        _cb(
            plan, "a22-stackhouse-finish-large-west-access-panel",
            "old_concrete" if panel_index % 2 else "weathered_zinc",
            STACKHOUSE_ID,
            26.72, panel_y, z,
            7.0, 6.0, 0.24,
            0.06, "secondary", yaw=-math.pi / 2, layer="mid",
        )
        if lod == 0:
            _cb(
                plan, "a22-stackhouse-finish-small-west-number-marker",
                "safety_orange", STACKHOUSE_ID,
                26.53, panel_y + 0.55, z + 1.65,
                1.80, 0.70, 0.12,
                0.02, "equipment", yaw=-math.pi / 2, layer="mid",
            )
    north_conduit_levels = (
        (14.0, 41.0, 68.0, 86.0) if lod == 0 else (28.0, 68.0)
    )
    for conduit_index, y in enumerate(north_conduit_levels):
        plan.round_member(
            "a22-stackhouse-finish-medium-north-conduit",
            "rust" if conduit_index % 2 == 0 else "safety_orange",
            STACKHOUSE_ID,
            (31.0, y, 122.84), (130.0, y, 122.84),
            0.12, 10 if lod == 0 else 8, layer="mid",
        )
    west_conduit_zs = (81.0, 99.0, 117.0) if lod == 0 else (90.0, 110.0)
    for conduit_index, z in enumerate(west_conduit_zs):
        plan.round_member(
            "a22-stackhouse-finish-medium-west-conduit",
            "safety_orange" if conduit_index == 1 else "rust",
            STACKHOUSE_ID,
            (26.48, 2.0, z), (26.48, 76.0, z),
            0.11, 10 if lod == 0 else 8, layer="mid",
        )
    if lod == 0:
        for y, z in ((31.5, 90.0), (58.0, 108.0)):
            _deep_window(
                plan, STACKHOUSE_ID,
                26.38, y, z,
                5.2, 3.0, depth=1.25,
                yaw=-math.pi / 2, layer="mid",
            )

    dock_xs = tuple(-108.0 + index * (80.0 / 9.0) for index in range(10))
    active_dock_xs = dock_xs if lod == 0 else dock_xs[::2]
    for panel_index, x in enumerate(active_dock_xs):
        _cb(
            plan, "a22-customs-finish-large-front-service-panel",
            "pale_concrete" if panel_index % 3 == 0 else "weathered_zinc",
            CUSTOMS_ID,
            x, 22.35, -27.66,
            5.6, 1.45, 0.24,
            0.05, "secondary", layer="mid",
        )
        if lod == 0:
            _cb(
                plan, "a22-customs-finish-small-bay-number-marker",
                "safety_orange" if panel_index % 2 == 0 else "pale_concrete",
                CUSTOMS_ID,
                x + (-1.55 if panel_index % 2 else 1.55),
                22.35, -27.51,
                1.55, 0.68, 0.12,
                0.02, "equipment", layer="mid",
            )
    customs_conduit_levels = (13.2, 20.8, 25.2) if lod == 0 else (20.8,)
    for conduit_index, y in enumerate(customs_conduit_levels):
        plan.round_member(
            "a22-customs-finish-medium-front-conduit",
            "rust" if conduit_index != 1 else "safety_orange",
            CUSTOMS_ID,
            (-111.0, y, -27.39), (-25.0, y, -27.39),
            0.11, 10 if lod == 0 else 8, layer="mid",
        )

    tower_north_panels = (
        (-75.0, 18.0),
        (-65.0, 18.0),
        (-75.0, 43.0),
        (-65.0, 43.0),
    )
    active_tower_panels = (
        tower_north_panels if lod == 0 else tower_north_panels[::2]
    )
    for panel_index, (x, y) in enumerate(active_tower_panels):
        _cb(
            plan, "a22-customs-finish-large-tower-access-panel",
            "weathered_zinc" if panel_index % 2 else "old_concrete",
            CUSTOMS_ID,
            x, y, -89.70,
            4.2, 5.4, 0.22,
            0.06, "secondary", layer="mid",
        )
        if lod == 0:
            _cb(
                plan, "a22-customs-finish-small-tower-number-marker",
                "safety_orange", CUSTOMS_ID,
                x + (1.15 if panel_index % 2 else -1.15),
                y + 0.65, -89.56,
                1.20, 0.62, 0.12,
                0.02, "equipment", layer="mid",
            )
    for conduit_index, x in enumerate((-76.5, -63.5) if lod == 0 else (-76.5,)):
        plan.round_member(
            "a22-customs-finish-medium-tower-conduit",
            "rust" if conduit_index == 0 else "safety_orange",
            CUSTOMS_ID,
            (x, 4.0, -89.48), (x, 53.0, -89.48),
            0.12, 10 if lod == 0 else 8, layer="mid",
        )


def _build_independent_p0_mass_rebuild(plan: SpecPlan, lod: int) -> None:
    """Rebuild the primary read around mass, ship-side depth and occupation.

    These are not floating decals.  Each addition is a grounded architectural
    volume, connected frame, real water/quay element, or occupied port mass.
    The two hero extensions stay inside their canonical landmark groups; the
    ship and depth district remain subordinate infrastructure.
    """

    # The original stackhouse was tall but read as a narrow kit tower from the
    # locked camera.  A two-stage concrete process bastion now grows out of its
    # west/south corner and overlaps the existing rack fortress.
    stack_group = STACKHOUSE_ID
    _cb(
        plan, "a22-p0-stackhouse-broad-terraced-foot",
        "old_concrete", stack_group,
        17.0, 3.8, 66.0, 48.0, 7.6, 43.0,
        0.20, "hero", layer="mid",
    )
    stack_bastions = (
        (7.0, 56.0, 27.0, 61.0, 29.0, 72.0),
        (24.0, 73.0, 23.0, 83.0, 25.0, 95.8),
    )
    active_bastions = stack_bastions if lod < 2 else stack_bastions[1:]
    for bastion_index, (x, z, width, height, depth, crown_y) in enumerate(
        active_bastions
    ):
        bastion = _cb(
            plan, "a22-p0-stackhouse-monumental-bastion",
            "pale_concrete" if bastion_index == 0 else "old_concrete",
            stack_group,
            x, height * 0.5 + 3.2, z,
            width * 0.48, height, depth * 0.52,
            0.22, "hero", layer="mid",
        )
        crown_house = _cb(
            plan, "a22-p0-stackhouse-bastion-crown-house",
            "old_concrete" if bastion_index == 0 else "pale_concrete",
            stack_group,
            x, crown_y - 4.8, z,
            width * 0.46, 9.6, depth * 0.46,
            0.18, "hero", layer="mid",
        )
        bastion_top = height + 3.2
        crown_bottom = crown_y - 9.6
        if crown_bottom > bastion_top:
            neck_height = crown_bottom - bastion_top + 0.4
            support_neck = _cb(
                plan, "a22-p0-stackhouse-bastion-crown-support-neck",
                "structural_steel", stack_group,
                x,
                bastion_top + neck_height * 0.5 - 0.2,
                z,
                width * 0.40, neck_height, depth * 0.40,
                0.12, "hero", layer="mid",
            )
            plan.connect(
                bastion, support_neck,
                axis="y", overlap_m=0.20,
                parent_face="top", child_face="bottom",
                note="Broad support neck grounds the raised crown house.",
            )
            plan.connect(
                support_neck, crown_house,
                axis="y", overlap_m=0.20,
                parent_face="top", child_face="bottom",
                note="Crown house bears on the visible support neck.",
            )
        else:
            plan.connect(
                bastion, crown_house,
                axis="y", overlap_m=0.20,
                parent_face="top", child_face="bottom",
                note="Low crown house overlaps the monumental bastion.",
            )
        corner_pairs = (
            ((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0))
            if lod == 0 else ((-1.0, 1.0), (1.0, 1.0))
        )
        for side_x, side_z in corner_pairs:
            _cb(
                plan, "a22-p0-stackhouse-bastion-heavy-buttress",
                "old_concrete", stack_group,
                x + side_x * width * 0.43,
                height * 0.43,
                z + side_z * depth * 0.41,
                3.2, height * 0.78, 3.8,
                0.16, "hero", layer="mid",
            )
        if lod == 0:
            for deck_y in (15.0, 31.0, 47.0):
                if deck_y >= height - 4.0:
                    continue
                _cb(
                    plan, "a22-p0-stackhouse-bastion-open-floor-slab",
                    "weathered_zinc", stack_group,
                    x, deck_y, z,
                    width * 0.92, 1.10, depth * 0.90,
                    0.14, "hero", layer="mid",
                )
            open_bands = (
                (7.0, 15.0),
                (16.0, 31.0),
                (32.0, 47.0),
                (48.0, min(height - 3.0, 64.0)),
            )
            for low_y, high_y in open_bands:
                if high_y - low_y < 3.0:
                    continue
                face_z = z + depth * 0.435
                _structural_beam(
                    plan, "a22-p0-stackhouse-bastion-open-x-brace",
                    stack_group,
                    (x - width * 0.39, low_y, face_z),
                    (x + width * 0.39, high_y, face_z),
                    0.54, material="rust", layer="mid",
                )
                _structural_beam(
                    plan, "a22-p0-stackhouse-bastion-open-x-brace",
                    stack_group,
                    (x + width * 0.39, low_y, face_z),
                    (x - width * 0.39, high_y, face_z),
                    0.54, material="structural_steel", layer="mid",
                )
        if lod < 2:
            window_levels = (
                (16.0, 31.0, 46.0)
                if lod == 0 else (30.0,)
            )
            for level_index, window_y in enumerate(window_levels):
                if window_y >= height - 4.0:
                    continue
                _deep_window(
                    plan, stack_group,
                    x, window_y, z + depth * 0.505,
                    width * 0.62, 4.8,
                    depth=1.8, yaw=math.pi, layer="mid",
                )
                if lod == 0 and level_index % 2 == 0:
                    _deep_window(
                        plan, stack_group,
                        x - width * 0.505, window_y + 2.0, z,
                        depth * 0.54, 4.0,
                        depth=1.6, yaw=-math.pi / 2, layer="mid",
                    )
            plan.round_member(
                "a22-p0-stackhouse-bastion-process-riser",
                "rust" if bastion_index == 0 else "structural_steel",
                stack_group,
                (
                    x + width * 0.31,
                    4.0,
                    z + depth * 0.515,
                ),
                (
                    x + width * 0.31,
                    height - 3.0,
                    z + depth * 0.515,
                ),
                0.28, 12 if lod == 0 else 8, layer="mid",
            )

    # A loaded bridge locks the new bastion to the original first process core
    # and creates the broad, layered negative-space silhouette in the target.
    bridge_start = (22.0, 48.0, 72.0)
    bridge_end = (48.0, 48.0, 93.0)
    for y_offset in (0.0, 8.5):
        for side in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-p0-stackhouse-bastion-bridge-chord",
                stack_group,
                (
                    bridge_start[0],
                    bridge_start[1] + y_offset,
                    bridge_start[2] + side * 3.2,
                ),
                (
                    bridge_end[0],
                    bridge_end[1] + y_offset,
                    bridge_end[2] + side * 3.2,
                ),
                0.82, material="structural_steel", layer="mid",
            )
    for side in (-1.0, 1.0):
        _structural_beam(
            plan, "a22-p0-stackhouse-bastion-bridge-x",
            stack_group,
            (22.0, 48.5, 72.0 + side * 3.2),
            (48.0, 56.0, 93.0 + side * 3.2),
            0.62, material="rust", layer="mid",
        )
        _structural_beam(
            plan, "a22-p0-stackhouse-bastion-bridge-x",
            stack_group,
            (22.0, 56.0, 72.0 + side * 3.2),
            (48.0, 48.5, 93.0 + side * 3.2),
            0.62, material="structural_steel", layer="mid",
        )
    _cb(
        plan, "a22-p0-stackhouse-bastion-bridge-floor",
        "weathered_zinc", stack_group,
        35.0, 48.0, 82.5, 34.0, 1.1, 7.6,
        0.14, "hero", yaw=math.atan2(21.0, 26.0), layer="mid",
    )

    # The customs hall keeps its four canonical teeth but gains a believable
    # heavy port facade, deep working bays and tower shoulders.  This converts
    # the thin shed silhouette into one continuous castle-scale anchor.
    customs_group = CUSTOMS_ID
    _cb(
        plan, "a22-p0-customs-camera-facing-foundation-apron",
        "old_concrete", customs_group,
        -68.0, 2.1, -18.0, 108.0, 4.2, 10.0,
        0.20, "hero", layer="mid",
    )
    shoulder_specs = (
        (-113.0, 18.0, 15.0, 36.0, 23.0),
        (-23.0, 19.0, 16.0, 38.0, 25.0),
    )
    for shoulder_index, (x, y, width, height, depth) in enumerate(
        shoulder_specs
    ):
        _cb(
            plan, "a22-p0-customs-monumental-end-shoulder",
            "pale_concrete" if shoulder_index == 0 else "old_concrete",
            customs_group,
            x, y, -31.0, width, height, depth,
            0.22, "hero", layer="mid",
        )
        _cb(
            plan, "a22-p0-customs-end-shoulder-roof-plant",
            "weathered_zinc", customs_group,
            x, height + 3.0, -31.0,
            width * 0.72, 6.0, depth * 0.66,
            0.14, "hero", layer="mid",
        )
        if lod == 0:
            for window_y in (14.0, 29.0):
                _deep_window(
                    plan, customs_group,
                    x, window_y, -18.85,
                    width * 0.62, 4.4,
                    depth=1.7, yaw=math.pi, layer="mid",
                )
    facade_piers = (-104.0, -86.0, -68.0, -50.0, -32.0)
    active_facade_piers = (
        facade_piers if lod == 0
        else facade_piers[::2] if lod == 1
        else (-104.0, -68.0, -32.0)
    )
    for pier_index, x in enumerate(active_facade_piers):
        _cb(
            plan, "a22-p0-customs-heavy-front-buttress",
            "old_concrete" if pier_index % 2 else "pale_concrete",
            customs_group,
            x, 16.0, -20.0,
            4.2, 30.0, 7.4,
            0.18, "hero", layer="mid",
        )
    for spandrel_y, height in ((12.0, 4.0), (25.0, 4.8)):
        _cb(
            plan, "a22-p0-customs-continuous-facade-spandrel",
            "old_concrete" if spandrel_y < 20.0 else "weathered_zinc",
            customs_group,
            -68.0, spandrel_y, -19.5,
            82.0, height, 6.0,
            0.18, "hero", layer="mid",
        )
    if lod < 2:
        bay_centres = (-95.0, -77.0, -59.0, -41.0)
        active_bay_centres = (
            bay_centres if lod == 0 else bay_centres[::2]
        )
        for bay_index, x in enumerate(active_bay_centres):
            _deep_window(
                plan, customs_group,
                x, 19.0, -16.35,
                11.5, 6.2,
                depth=2.1, yaw=math.pi, layer="mid",
            )
            _cb(
                plan, "a22-p0-customs-working-bay-header-number",
                "safety_orange", customs_group,
                x + (-3.6 if bay_index % 2 else 3.6),
                23.2, -16.16,
                2.0, 0.78, 0.18,
                0.02, "equipment", layer="mid",
            )
    for x in (-92.0, -48.0):
        _cb(
            plan, "a22-p0-customs-control-tower-shoulder",
            "old_concrete", customs_group,
            x, 19.0, -91.0,
            22.0, 38.0, 29.0,
            0.20, "hero", layer="mid",
        )
        _cb(
            plan, "a22-p0-customs-tower-shoulder-machine-deck",
            "structural_steel", customs_group,
            x, 39.0, -91.0,
            24.0, 1.2, 31.0,
            0.16, "hero", layer="mid",
        )

    # A camera-right ship-side district restores the target's working-quay
    # identity.  The water, hull, quay wall, fenders and moorings are real 3D
    # and stop short of the camera and canonical combat corridor.
    quay_group = "souko-a22-primary-ship-side-rebuild"
    plan.panel(
        "a22-p0-primary-camera-quay-water",
        "sea_water", quay_group,
        (
            (-220.0, 0.45, PRIMARY_QUAY_FAR_Z),
            (-207.0, 0.45, 132.0),
            (primary_quay_edge_x(125.0), 0.45, 125.0),
            (PRIMARY_QUAY_FAR_X, 0.45, PRIMARY_QUAY_FAR_Z),
        ),
        0.08,
        layer="near", outside_playable=True,
    )
    plan.box(
        "a22-p0-primary-camera-quay-water-near-pocket",
        "sea_water", quay_group,
        -204.0, 0.42, 124.0,
        22.0, 0.18, 20.0,
        layer="near", outside_playable=True,
    )
    quay_centre_x = (PRIMARY_QUAY_FAR_X + PRIMARY_QUAY_NEAR_X) * 0.5
    quay_centre_z = (PRIMARY_QUAY_FAR_Z + PRIMARY_QUAY_NEAR_Z) * 0.5
    quay_land_x = math.cos(PRIMARY_QUAY_YAW)
    quay_land_z = math.sin(PRIMARY_QUAY_YAW)
    quay_wall_offset = -3.20
    _cb(
        plan, "a22-p0-primary-camera-heavy-quay-wall",
        "old_concrete", quay_group,
        quay_centre_x + quay_land_x * quay_wall_offset,
        -0.75,
        quay_centre_z + quay_land_z * quay_wall_offset,
        5.5, 3.0, PRIMARY_QUAY_LENGTH,
        0.18, "hero", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    _cb(
        plan, "a22-p0-primary-camera-quay-service-deck",
        "pale_concrete", quay_group,
        quay_centre_x + quay_land_x * quay_wall_offset,
        0.75,
        quay_centre_z + quay_land_z * quay_wall_offset,
        6.0, 0.50, PRIMARY_QUAY_LENGTH,
        0.14, "hero", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    fender_zs = (
        18.0, 34.0, 50.0, 66.0, 82.0, 98.0, 114.0,
    )
    active_fender_zs = (
        fender_zs if lod == 0 else fender_zs[::2] if lod == 1
        else fender_zs[::3]
    )
    for fender_index, z in enumerate(active_fender_zs):
        fender_x = primary_quay_edge_x(z) - quay_land_x * 3.25
        fender_actual_z = z - quay_land_z * 3.25
        plan.cylinder(
            "a22-p0-quay-rubber-fender",
            "structural_steel", quay_group,
            fender_x, -0.45, fender_actual_z,
            1.10, 3.0,
            16 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=1.0, layer="near", outside_playable=True,
        )
        if lod == 0:
            _cb(
                plan, "a22-p0-quay-fender-hazard-cap",
                "safety_orange", quay_group,
                fender_x, 1.08, fender_actual_z,
                2.5, 0.44, 2.8,
                0.05, "secondary", yaw=PRIMARY_QUAY_YAW,
                layer="near", outside=True,
            )
        if fender_index % 2 == 0:
            bollard_z = z + 5.0
            bollard_x = (
                primary_quay_edge_x(bollard_z)
                + quay_land_x * 2.05
            )
            bollard_actual_z = bollard_z + quay_land_z * 2.05
            plan.cylinder(
                "a22-p0-quay-heavy-mooring-bollard",
                "structural_steel", quay_group,
                bollard_x, 1.90, bollard_actual_z,
                0.92, 1.75,
                14 if lod == 0 else 8,
                top_radius=1.22, layer="near", outside_playable=True,
            )

    ship_half_beam = PRIMARY_SHIP_HALF_BEAM

    def ship_land_x(z: float) -> float:
        return primary_ship_land_x(z)

    def ship_centre_x_at(z: float) -> float:
        return ship_land_x(z) - ship_half_beam

    def ship_water_x(
        z: float,
        beam: float = ship_half_beam * 2.0,
    ) -> float:
        return ship_land_x(z) - beam

    ship_deck_z = 50.0
    ship_x = ship_centre_x_at(ship_deck_z)
    bow_shoulder_z = 74.0
    bow_tip_x = (
        ship_land_x(PRIMARY_SHIP_BOW_Z) - 2.5
    )
    plan.panel(
        "a22-p0-primary-camera-ship-near-hull",
        "weathered_zinc", quay_group,
        (
            (ship_water_x(26.0), 0.0, 26.0),
            (ship_water_x(34.0), 7.0, 34.0),
            (ship_water_x(bow_shoulder_z, 5.0), 7.2, bow_shoulder_z),
            (bow_tip_x, 1.0, PRIMARY_SHIP_BOW_Z),
        ),
        1.2, layer="near", outside_playable=True,
    )
    plan.panel(
        "a22-p0-primary-camera-ship-far-hull",
        "weathered_zinc", quay_group,
        (
            (ship_land_x(26.0), 0.0, 26.0),
            (bow_tip_x, 1.0, PRIMARY_SHIP_BOW_Z),
            (ship_land_x(bow_shoulder_z), 7.2, bow_shoulder_z),
            (ship_land_x(34.0), 7.0, 34.0),
        ),
        1.2, layer="near", outside_playable=True,
    )
    plan.panel(
        "a22-p0-primary-camera-ship-bow",
        "weathered_zinc", quay_group,
        (
            (bow_tip_x, 1.0, PRIMARY_SHIP_BOW_Z),
            (ship_land_x(bow_shoulder_z), 7.2, bow_shoulder_z),
            (ship_water_x(bow_shoulder_z, 5.0), 7.2, bow_shoulder_z),
        ),
        1.2, layer="near", outside_playable=True,
    )
    plan.panel(
        "a22-p0-primary-camera-ship-painted-freeboard-band",
        "rust", quay_group,
        (
            (ship_land_x(34.0) + 0.16, 1.2, 34.0),
            (ship_land_x(34.0) + 0.16, 2.8, 34.0),
            (ship_land_x(70.0) + 0.16, 3.0, 70.0),
            (ship_land_x(70.0) + 0.16, 1.3, 70.0),
        ),
        0.18, layer="near", outside_playable=True,
    )
    plan.panel(
        "a22-p0-primary-camera-ship-pale-upper-sheer-band",
        "pale_concrete", quay_group,
        (
            (ship_land_x(35.0) + 0.18, 5.1, 35.0),
            (ship_land_x(35.0) + 0.18, 6.5, 35.0),
            (ship_land_x(70.0) + 0.18, 6.7, 70.0),
            (ship_land_x(70.0) + 0.18, 5.3, 70.0),
        ),
        0.16, layer="near", outside_playable=True,
    )
    _cb(
        plan, "a22-p0-primary-camera-ship-working-deck",
        "weathered_zinc", quay_group,
        ship_x, 7.6, ship_deck_z,
        6.0, 1.2, 48.0,
        0.16, "hero", yaw=PRIMARY_SHIP_YAW,
        layer="near", outside=True,
    )
    forecastle_z = 71.0
    forecastle_x = ship_land_x(forecastle_z) - 2.7
    _cb(
        plan, "a22-p0-primary-camera-ship-forecastle",
        "old_concrete", quay_group,
        forecastle_x, 8.8, forecastle_z,
        5.2, 2.8, 10.0,
        0.16, "hero", yaw=PRIMARY_SHIP_YAW,
        layer="near", outside=True,
    )
    superstructure_axis_z = 34.0
    superstructure_x = ship_centre_x_at(superstructure_axis_z) + 0.4
    superstructure_z = superstructure_axis_z
    _cb(
        plan, "a22-p0-primary-camera-ship-superstructure",
        "pale_concrete", quay_group,
        superstructure_x, 11.4, superstructure_z,
        5.6, 7.0, 11.0,
        0.18, "hero", yaw=PRIMARY_SHIP_YAW,
        layer="near", outside=True,
    )
    if lod < 2:
        ship_side_window_yaw = PRIMARY_SHIP_YAW - math.pi / 2
        window_offset = 3.35
        _deep_window(
            plan, quay_group,
            superstructure_x + window_offset,
            11.8,
            superstructure_z,
            7.5, 3.4,
            depth=1.2, yaw=ship_side_window_yaw, layer="near",
        )
        _cb(
            plan, "a22-p0-primary-camera-ship-bridge",
            "weathered_zinc", quay_group,
            superstructure_x, 16.0, superstructure_z,
            5.8, 3.5, 10.0,
            0.16, "hero", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
        _cb(
            plan, "a22-p0-primary-camera-ship-bridge-warm-window-strip",
            "warm_glass", quay_group,
            ship_land_x(superstructure_axis_z) + 0.16,
            16.0, superstructure_z,
            0.20, 1.15, 6.4,
            0.05, "secondary", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
        _deep_window(
            plan, quay_group,
            superstructure_x + 3.1,
            16.0,
            superstructure_z,
            7.0, 2.5,
            depth=1.1, yaw=ship_side_window_yaw, layer="near",
        )
        plan.round_member(
            "a22-p0-primary-camera-ship-mast",
            "structural_steel", quay_group,
            (superstructure_x, 18.0, superstructure_z),
            (superstructure_x, 29.0, superstructure_z),
            0.42, 12 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
        plan.round_member(
            "a22-p0-primary-camera-ship-radar-yard",
            "safety_orange", quay_group,
            (
                superstructure_x - 3.0,
                26.0,
                superstructure_z,
            ),
            (
                superstructure_x + 3.0,
                26.0,
                superstructure_z,
            ),
            0.22, 10 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
    container_count = 6 if lod == 0 else 4 if lod == 1 else 2
    for index in range(container_count):
        row, column = divmod(index, 3)
        container_axis_z = 48.0 + column * 9.0
        lateral = -1.45 if row == 0 else 1.45
        _cb(
            plan, "a22-p0-primary-camera-ship-loaded-container",
            ("weathered_zinc", "rust", "safety_orange")[index % 3],
            quay_group,
            (
                ship_centre_x_at(container_axis_z) + lateral
            ),
            9.6,
            container_axis_z,
            2.6, 2.5, 7.0,
            0.06, "secondary", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
    _cb(
        plan, "a22-p0-primary-camera-ship-name-stripe",
        "pale_concrete", quay_group,
        ship_land_x(50.0) - 0.18, 4.2, 50.0,
        0.22, 0.82, 26.0,
        0.05, "secondary", yaw=PRIMARY_SHIP_YAW,
        layer="near", outside=True,
    )
    if lod == 0:
        _cb(
            plan, "a22-p0-primary-camera-ship-bow-keel-band",
            "rust", quay_group,
            ship_land_x(75.0) - 2.75, 1.5, 75.0,
            5.4, 2.8, 0.32,
            0.05, "secondary", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
        _cb(
            plan, "a22-p0-primary-camera-ship-bow-name-stripe",
            "pale_concrete", quay_group,
            ship_land_x(75.0) - 0.18, 4.6, 75.0,
            0.24, 1.05, 8.0,
            0.05, "secondary", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
        for anchor_z in (64.0, 72.0):
            anchor_x = ship_land_x(anchor_z) - 0.4
            plan.round_member(
                "a22-p0-primary-camera-ship-bow-anchor-hawse",
                "rust", quay_group,
                (anchor_x - 0.9, 4.0, anchor_z - 0.2),
                (anchor_x + 0.9, 4.0, anchor_z + 0.2),
                0.52, 12, layer="near", outside_playable=True,
            )
    for z in (36.0, 52.0, 68.0):
        bollard_z = z + 7.0
        plan.round_member(
            "a22-p0-primary-camera-ship-mooring-line",
            "structural_steel", quay_group,
            (ship_land_x(z) - 1.0, 5.0, z),
            (
                primary_quay_edge_x(bollard_z) + quay_land_x * 2.0,
                2.25,
                bollard_z + quay_land_z * 2.0,
            ),
            0.16, 10 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
    for z in (24.0, 46.0, 68.0, 90.0, 112.0):
        start_z, end_z = z - 7.0, z + 7.0
        _guardrail_run(
            plan, quay_group,
            (
                primary_quay_edge_x(start_z) + quay_land_x * 0.8,
                start_z + quay_land_z * 0.8,
            ),
            (
                primary_quay_edge_x(end_z) + quay_land_x * 0.8,
                end_z + quay_land_z * 0.8,
            ),
            1.00, lod, outside=True,
        )
    quay_cluster_zs = (30.0, 55.0, 80.0, 105.0)
    active_quay_clusters = (
        quay_cluster_zs if lod == 0 else quay_cluster_zs[:1]
    )
    for cluster_index, z in enumerate(active_quay_clusters):
        cluster_x = primary_quay_edge_x(z) + quay_land_x * 6.0
        cluster_actual_z = z + quay_land_z * 6.0
        _cb(
            plan, "a22-p0-quay-grounded-cargo-pallet",
            "pallet_wood", quay_group,
            cluster_x, 1.25, cluster_actual_z,
            5.8, 0.55, 4.2,
            0.05, "secondary", yaw=PRIMARY_QUAY_YAW,
            layer="near", outside=True,
        )
        for stack in range(2 if lod == 0 else 1):
            _cb(
                plan, "a22-p0-quay-staged-maintenance-crate",
                ("weathered_zinc", "structural_steel", "rust")[
                    (cluster_index + stack) % 3
                ],
                quay_group,
                cluster_x + stack * 0.35,
                2.65 + stack * 2.2,
                cluster_actual_z,
                4.6, 2.2, 3.4,
                0.06, "secondary", yaw=PRIMARY_QUAY_YAW,
                layer="near", outside=True,
            )
    quay_task_light_zs = (48.0, 78.0, 108.0)
    active_task_lights = (
        quay_task_light_zs if lod == 0
        else quay_task_light_zs[::2] if lod == 1
        else quay_task_light_zs[-1:]
    )
    for z in active_task_lights:
        lamp_x = primary_quay_edge_x(z) + quay_land_x * 4.8
        lamp_z = z + quay_land_z * 4.8
        plan.round_member(
            "a22-p0-quay-grounded-work-light-post",
            "structural_steel", quay_group,
            (lamp_x, 0.6, lamp_z),
            (lamp_x, 4.5, lamp_z),
            0.14, 10 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
        _cb(
            plan, "a22-p0-quay-warm-work-light",
            "warm_glass", quay_group,
            lamp_x, 4.55, lamp_z,
            1.8, 0.78, 0.82,
            0.05, "secondary", yaw=PRIMARY_QUAY_YAW,
            layer="near", outside=True,
        )
    if lod == 0:
        barrel_axis_z = 113.0
        barrel_x = (
            primary_quay_edge_x(barrel_axis_z)
            + quay_land_x * 6.2
        )
        barrel_z = barrel_axis_z + quay_land_z * 6.2
        for index, (side, forward) in enumerate(
            ((-1.1, -1.0), (0.4, -0.2), (1.6, 1.0))
        ):
            plan.cylinder(
                "a22-p0-quay-grounded-service-barrel",
                ("rust", "weathered_zinc", "structural_steel")[index],
                quay_group,
                barrel_x + quay_land_x * side
                - quay_land_z * forward,
                1.05,
                barrel_z + quay_land_z * side
                + quay_land_x * forward,
                0.66, 2.0, 14,
                top_radius=0.64,
                layer="near", outside_playable=True,
            )

    # Real geometry closes the central vanishing point in three depth steps.
    depth_group = "souko-a22-primary-depth-rebuild"
    depth_masses = (
        (8.0, -76.0, 34.0, 25.0, 28.0),
        (43.0, -106.0, 25.0, 42.0, 24.0),
        (77.0, -130.0, 31.0, 34.0, 29.0),
        (108.0, -155.0, 24.0, 51.0, 22.0),
    )
    active_depth_masses = (
        depth_masses if lod == 0
        else depth_masses[::2] if lod == 1
        else depth_masses[1::2]
    )
    for mass_index, (x, z, width, height, depth) in enumerate(
        active_depth_masses
    ):
        _cb(
            plan, "a22-p0-central-layered-port-mass",
            ("old_concrete", "weathered_zinc", "pale_concrete")[
                mass_index % 3
            ],
            depth_group,
            x, height * 0.5, z,
            width, height, depth,
            0.16, "hero", layer="far", outside=True,
        )
        _cb(
            plan, "a22-p0-central-layered-port-roof-plant",
            "structural_steel", depth_group,
            x, height + 3.5, z,
            width * 0.62, 7.0, depth * 0.58,
            0.12, "hero", layer="far", outside=True,
        )
        if lod < 2:
            _deep_window(
                plan, depth_group,
                x, height * 0.62, z + depth * 0.51,
                width * 0.64, 4.2,
                depth=1.5, yaw=math.pi, layer="far",
            )
            _cb(
                plan, "a22-p0-central-port-weather-band",
                "rust", depth_group,
                x, height * 0.38, z + depth * 0.525,
                width * 0.82, 0.55, 0.24,
                0.05, "secondary", layer="far", outside=True,
            )
    for rack_x in (18.0, 48.0, 78.0):
        for side in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-p0-central-depth-pipe-rack-leg",
                depth_group,
                (rack_x + side * 6.0, 0.6, -54.0),
                (rack_x + side * 6.0, 16.0, -54.0),
                0.72, material="structural_steel",
                layer="far", outside=True,
            )
        _structural_beam(
            plan, "a22-p0-central-depth-pipe-rack-header",
            depth_group,
            (rack_x - 6.0, 16.0, -54.0),
            (rack_x + 6.0, 16.0, -54.0),
            0.82, material="rust", layer="far", outside=True,
        )


def _build_interlocking_gantries(plan: SpecPlan, lod: int) -> None:
    group = "souko-a22-interlocking-gantries"
    # Castle-scale occupied transfer bridge physically overlaps both landmarks.
    bridge_start = (-22.8, 31.0, -34.0)
    bridge_end = (30.4, 31.0, 83.0)
    dx = bridge_end[0] - bridge_start[0]
    dz = bridge_end[2] - bridge_start[2]
    length = math.hypot(dx, dz)
    yaw = math.atan2(dz, dx)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    centre_x = (bridge_start[0] + bridge_end[0]) * 0.5
    centre_z = (bridge_start[2] + bridge_end[2]) * 0.5
    floor = _cb(
        plan, "a22-interhero-occupied-bridge-floor",
        "structural_steel", group,
        centre_x, 31.0, centre_z, length + 1.0, 1.3, 7.2,
        0.16, "hero", yaw=yaw, layer="mid",
    )
    roof = _cb(
        plan, "a22-interhero-occupied-bridge-roof",
        "weathered_zinc", group,
        centre_x, 39.0, centre_z, length + 1.0, 1.1, 7.2,
        0.14, "hero", yaw=yaw, layer="mid",
    )
    plan.connect(
        floor, roof, axis="y", overlap_m=0.12,
        parent_face="portal-frame", child_face="portal-frame",
        note="Full-length portal frames close the occupied bridge volume.",
    )
    portal_count = 18 if lod == 0 else 10 if lod == 1 else 6
    for index in range(portal_count):
        t = index / max(1, portal_count - 1)
        x = bridge_start[0] + dx * t
        z = bridge_start[2] + dz * t
        for side in (-1.0, 1.0):
            sx, sz = x + px * side * 3.35, z + pz * side * 3.35
            _structural_beam(
                plan, "a22-interhero-bridge-portal", group,
                (sx, 31.4, sz), (sx, 38.5, sz), 0.56,
            )
        _structural_beam(
            plan, "a22-interhero-bridge-roof-tie", group,
            (x + px * 3.35, 38.5, z + pz * 3.35),
            (x - px * 3.35, 38.5, z - pz * 3.35), 0.48,
        )
    bay_count = portal_count - 1
    for index in range(bay_count):
        t0 = index / max(1, portal_count - 1)
        t1 = (index + 1) / max(1, portal_count - 1)
        for side in (-1.0, 1.0):
            x0 = bridge_start[0] + dx * t0 + px * side * 3.38
            z0 = bridge_start[2] + dz * t0 + pz * side * 3.38
            x1 = bridge_start[0] + dx * t1 + px * side * 3.38
            z1 = bridge_start[2] + dz * t1 + pz * side * 3.38
            if index % 2:
                first, second = (x0, 31.7, z0), (x1, 38.2, z1)
            else:
                first, second = (x0, 38.2, z0), (x1, 31.7, z1)
            _structural_beam(
                plan, "a22-interhero-bridge-diagonal", group,
                first, second, 0.42, material="rust",
            )
            if lod < 2 and index % 3 == 1:
                panel_x = (x0 + x1) * 0.5
                panel_z = (z0 + z1) * 0.5
                _cb(
                    plan, "a22-interhero-warm-control-bay",
                    "warm_glass", group,
                    panel_x, 35.0, panel_z,
                    length / max(1, bay_count) * 0.75, 3.4, 0.32,
                    0.05, "secondary", yaw=yaw, layer="mid",
                )

    # Additional elevated services interlock above, never replacing collision.
    runs = (
        ((19.0, 31.0, 82.0), (32.0, 31.0, 82.0)),
        ((-22.0, 27.0, -35.0), (20.0, 27.0, 35.0)),
        ((-17.0, 18.0, 73.0), (30.0, 18.0, 92.0)),
    )
    active = runs if lod < 2 else runs[:2]
    for index, (start, end) in enumerate(active):
        centre = tuple((start[i] + end[i]) * 0.5 for i in range(3))
        length = math.dist(start, end)
        yaw = math.atan2(end[2] - start[2], end[0] - start[0])
        _cb(
            plan, "a22-interlocking-gantry-deck", "structural_steel", group,
            centre[0], centre[1], centre[2], length, 1.2, 5.0,
            0.14, "hero", yaw=yaw, layer="mid",
        )
        _structural_beam(
            plan, "a22-interlocking-gantry-lattice", group,
            (start[0], start[1] + 0.8, start[2]),
            (end[0], end[1] + 6.0, end[2]), 0.58,
        )
        _structural_beam(
            plan, "a22-interlocking-gantry-lattice", group,
            (start[0], start[1] + 6.0, start[2]),
            (end[0], end[1] + 0.8, end[2]), 0.58,
        )
        _guardrail_run(
            plan, group,
            (start[0], start[2] - 2.3),
            (end[0], end[2] - 2.3),
            centre[1] + 0.6, lod,
        )


def _build_worker(
    plan: SpecPlan,
    group: str,
    role_prefix: str,
    x: float,
    z: float,
    yaw: float,
    lod: int,
    *,
    base_y: float = 0.0,
    pose_index: int = 0,
) -> None:
    dx, dz = math.cos(yaw), math.sin(yaw)
    px, pz = -dz, dx
    segments = 10 if lod == 0 else 7
    pose = pose_index % 4
    plan.cylinder(
        f"{role_prefix}-body",
        "structural_steel" if pose % 2 == 0 else "weathered_zinc",
        group,
        x, base_y + 1.10, z, 0.30, 1.05, segments,
        top_radius=0.24, layer="near",
    )
    plan.cylinder(
        f"{role_prefix}-head", "pallet_wood", group,
        x, base_y + 1.76, z, 0.20, 0.30, segments,
        top_radius=0.19, layer="near",
    )
    plan.cylinder(
        f"{role_prefix}-helmet", "safety_orange", group,
        x, base_y + 1.96, z, 0.21, 0.14, segments,
        top_radius=0.17, layer="near",
    )
    _cb(
        plan, f"{role_prefix}-reflective-vest", "safety_orange", group,
        x + dx * 0.19, base_y + 1.30, z + dz * 0.19,
        0.54, 0.50, 0.14, 0.02, "equipment",
        yaw=yaw, layer="near",
    )
    if lod == 0:
        _cb(
            plan, f"{role_prefix}-reflective-vest-back",
            "safety_orange", group,
            x - dx * 0.19, base_y + 1.30, z - dz * 0.19,
            0.54, 0.50, 0.14, 0.02, "equipment",
            yaw=yaw, layer="near",
        )
        _cb(
            plan, f"{role_prefix}-vest-reflector", "pale_concrete", group,
            x + dx * 0.275, base_y + 1.30, z + dz * 0.275,
            0.56, 0.10, 0.08, 0.02, "equipment",
            yaw=yaw, layer="near",
        )
    if lod < 2:
        _cb(
            plan, f"{role_prefix}-pelvis", "structural_steel", group,
            x - dx * 0.02, base_y + 0.72, z - dz * 0.02,
            0.46, 0.26, 0.34,
            0.02, "equipment", yaw=yaw, layer="near",
        )
    for side in (-1.0, 1.0):
        stride = (
            side * 0.19 if pose == 2
            else side * -0.13 if pose == 3
            else 0.04
        )
        plan.round_member(
            f"{role_prefix}-leg", "structural_steel", group,
            (
                x + dx * stride + px * side * 0.12,
                base_y + 0.08,
                z + dz * stride + pz * side * 0.12,
            ),
            (x - dx * 0.04 + px * side * 0.11, base_y + 0.70,
             z - dz * 0.04 + pz * side * 0.11),
            0.08, segments, layer="near",
        )
        if lod < 2:
            _cb(
                plan, f"{role_prefix}-work-boot", "structural_steel", group,
                x + dx * (0.10 + stride) + px * side * 0.13,
                base_y + 0.09,
                z + dz * (0.10 + stride) + pz * side * 0.13,
                0.32, 0.16, 0.20,
                0.02, "equipment", yaw=yaw, layer="near",
            )
        if pose == 0:
            arm_forward, arm_y, arm_out = 0.16, 0.96, 0.42
        elif pose == 1:
            arm_forward = 0.38 if side > 0 else 0.10
            arm_y = 1.78 if side > 0 else 1.00
            arm_out = 0.34 if side > 0 else 0.46
        elif pose == 2:
            arm_forward, arm_y, arm_out = 0.50, 1.16, 0.28
        else:
            arm_forward = -0.05 if side > 0 else 0.32
            arm_y = 1.82 if side > 0 else 1.28
            arm_out = 0.25 if side > 0 else 0.38
        plan.round_member(
            f"{role_prefix}-arm", "safety_orange", group,
            (x + px * side * 0.30, base_y + 1.42, z + pz * side * 0.30),
            (
                x + dx * arm_forward + px * side * arm_out,
                base_y + arm_y,
                z + dz * arm_forward + pz * side * arm_out,
            ),
            0.075, segments, layer="near",
        )
    featured_route_worker = (
        lod == 0
        and role_prefix == "a22-route-worker"
        and pose_index in {1, 4, 7}
    )
    if featured_route_worker:
        for side in (-1.0, 1.0):
            hand_forward = 0.48 if pose_index != 4 else 0.62
            plan.cylinder(
                f"{role_prefix}-gloved-hand",
                "pale_concrete", group,
                x + dx * hand_forward + px * side * 0.30,
                base_y + (1.08 if pose_index != 1 else 1.30),
                z + dz * hand_forward + pz * side * 0.30,
                0.105, 0.18, 8,
                top_radius=0.095, layer="near",
            )
        if pose_index == 4:
            _cb(
                plan, f"{role_prefix}-carried-inspection-case",
                "weathered_zinc", group,
                x + dx * 0.68, base_y + 1.03, z + dz * 0.68,
                0.78, 0.48, 0.46,
                0.02, "equipment", yaw=yaw, layer="near",
            )
        else:
            plan.pipe(
                f"{role_prefix}-carried-service-tool",
                "pallet_wood" if pose_index == 1 else "safety_orange",
                group,
                (
                    x + dx * 0.32 - px * 0.46,
                    base_y + 0.92,
                    z + dz * 0.32 - pz * 0.46,
                ),
                (
                    x + dx * 0.95 + px * 0.46,
                    base_y + 1.48,
                    z + dz * 0.95 + pz * 0.46,
                ),
                0.025, 8, layer="near",
            )


def _build_checkpoint(plan: SpecPlan, lod: int) -> None:
    group = "souko-a22-occupied-checkpoint"
    # Deliberately away from the canonical x/z road cross and four spawns.
    _cb(
        plan, "a22-checkpoint-broad-canopy", "weathered_zinc", group,
        -139.0, 8.2, 85.0, 22.0, 1.2, 10.0,
        0.14, "hero", yaw=-0.15, layer="near",
    )
    for index in range(6 if lod == 0 else 4 if lod == 1 else 2):
        x = -151.0 + index * 4.8
        _cb(
            plan, "a22-checkpoint-support", "old_concrete", group,
            x, 4.3, 85.0, 1.1, 8.6, 1.2,
            0.12, "hero", yaw=-0.15, layer="near",
        )
    for x in (-145.0, -133.0):
        _cb(
            plan, "a22-checkpoint-occupied-booth", "old_concrete", group,
            x, 2.25, 85.0, 5.2, 4.3, 4.8,
            0.08, "secondary", yaw=-0.15, layer="near",
        )
        _deep_window(
            plan, group, x, 2.65, 87.45, 3.4, 1.8,
            depth=0.9, yaw=math.pi, layer="near",
        )
        if lod < 2:
            _deep_window(
                plan, group, x - 2.70, 2.65, 85.0, 3.0, 1.8,
                depth=0.9, yaw=-math.pi / 2, layer="near",
            )
            _cb(
                plan, "a22-checkpoint-booth-thin-roof",
                "weathered_zinc", group,
                x, 4.65, 85.0, 6.0, 0.42, 5.6,
                0.07, "secondary", yaw=-0.15, layer="near",
            )
            _cb(
                plan, "a22-checkpoint-booth-service-door",
                "structural_steel", group,
                x + 2.68, 2.0, 85.0, 0.24, 3.2, 2.1,
                0.05, "secondary", yaw=-0.15, layer="near",
            )
            _cb(
                plan, "a22-checkpoint-booth-warm-sign",
                "warm_glass", group,
                x, 4.0, 87.48, 2.8, 0.42, 0.22,
                0.02, "equipment", layer="near",
            )
    for index in range(4 if lod < 2 else 2):
        z = 76.0 + index * 5.6
        _cb(
            plan, "a22-checkpoint-barrier-base", "safety_orange", group,
            -118.0, 0.65, z, 2.1, 1.1, 1.8,
            0.02, "equipment", layer="near",
        )
        _structural_beam(
            plan, "a22-checkpoint-barrier-arm", group,
            (-117.0, 1.2, z), (-107.0, 3.6, z),
            0.22, material="safety_orange", layer="near",
        )
    worker_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(worker_count):
        x = -151.0 + (index % 4) * 7.0
        z = 72.0 + (index // 4) * 23.0
        _build_worker(
            plan, group, "a22-checkpoint-worker",
            x, z, -0.15 + index * 0.2, lod, pose_index=index,
        )


def _build_vehicle(
    plan: SpecPlan,
    group: str,
    x: float,
    z: float,
    yaw: float,
    lod: int,
    *,
    forklift: bool = False,
    loaded: bool = False,
    outside: bool = False,
) -> None:
    dx, dz = math.cos(yaw), math.sin(yaw)
    px, pz = -dz, dx
    if forklift:
        _cb(
            plan, "a22-operational-forklift-body", "safety_orange", group,
            x, 1.15, z, 3.1, 1.8, 2.2, 0.02, "equipment",
            yaw=yaw, layer="near", outside=outside,
        )
        if lod == 0:
            for side in (-1.0, 1.0):
                _cb(
                    plan, "a22-forklift-recognizable-fleet-marking",
                    "pale_concrete", group,
                    x + px * side * 1.13, 1.30,
                    z + pz * side * 1.13,
                    1.35, 0.62, 0.12,
                    0.02, "equipment", yaw=yaw,
                    layer="near", outside=outside,
                )
        _cb(
            plan, "a22-forklift-rounded-counterweight",
            "safety_orange", group,
            x - dx * 1.25, 1.35, z - dz * 1.25,
            1.25, 2.1, 2.25, 0.08, "secondary",
            yaw=yaw, layer="near", outside=outside,
        )
        mast_x, mast_z = x + dx * 1.8, z + dz * 1.8
        for side in (-1, 1):
            lateral_x = px * side * 0.48
            lateral_z = pz * side * 0.48
            _structural_beam(
                plan, "a22-forklift-mast", group,
                (mast_x + lateral_x, 0.4, mast_z + lateral_z),
                (mast_x + lateral_x, 4.5, mast_z + lateral_z),
                0.28, material="safety_orange",
                layer="near", outside=outside,
            )
            _structural_beam(
                plan, "a22-forklift-cab-upright", group,
                (x - dx * 0.7 + lateral_x, 1.2, z - dz * 0.7 + lateral_z),
                (x - dx * 0.7 + lateral_x, 3.7, z - dz * 0.7 + lateral_z),
                0.16, layer="near", outside=outside,
            )
            _structural_beam(
                plan, "a22-forklift-fork-tine", group,
                (mast_x + lateral_x, 0.42, mast_z + lateral_z),
                (
                    mast_x + dx * 3.4 + lateral_x,
                    0.32,
                    mast_z + dz * 3.4 + lateral_z,
                ),
                0.24, material="safety_orange",
                layer="near", outside=outside,
            )
        _structural_beam(
            plan, "a22-forklift-mast-top-crossbar", group,
            (mast_x - px * 0.72, 4.45, mast_z - pz * 0.72),
            (mast_x + px * 0.72, 4.45, mast_z + pz * 0.72),
            0.24, material="safety_orange",
            layer="near", outside=outside,
        )
        _cb(
            plan, "a22-forklift-overhead-guard", "safety_orange", group,
            x - dx * 0.25, 3.75, z - dz * 0.25,
            2.0, 0.24, 2.05, 0.02, "equipment",
            yaw=yaw, layer="near", outside=outside,
        )
        if lod < 2:
            _cb(
                plan, "a22-forklift-cab-windscreen", "dirty_glass", group,
                x + dx * 0.62, 2.72, z + dz * 0.62,
                1.45, 1.38, 0.18,
                0.05, "secondary", yaw=yaw + math.pi / 2,
                layer="near", outside=outside,
            )
            _cb(
                plan, "a22-forklift-cab-warm-depth", "warm_glass", group,
                x + dx * 0.20, 2.70, z + dz * 0.20,
                1.20, 1.12, 0.18,
                0.05, "secondary", yaw=yaw + math.pi / 2,
                layer="near", outside=outside,
            )
            if lod == 0:
                _cb(
                    plan, "a22-forklift-readable-control-console",
                    "structural_steel", group,
                    x + dx * 0.42, 2.12, z + dz * 0.42,
                    0.82, 0.34, 0.46,
                    0.02, "equipment", yaw=yaw,
                    layer="near", outside=outside,
                )
                plan.pipe(
                    "a22-forklift-readable-steering-column",
                    "weathered_zinc", group,
                    (
                        x - dx * 0.08,
                        1.72,
                        z - dz * 0.08,
                    ),
                    (
                        x + dx * 0.38,
                        2.38,
                        z + dz * 0.38,
                    ),
                    0.025, 8, layer="near", outside_playable=outside,
                )
                plan.pipe(
                    "a22-forklift-readable-steering-grip",
                    "safety_orange", group,
                    (
                        x + dx * 0.38 - px * 0.30,
                        2.40,
                        z + dz * 0.38 - pz * 0.30,
                    ),
                    (
                        x + dx * 0.38 + px * 0.30,
                        2.40,
                        z + dz * 0.38 + pz * 0.30,
                    ),
                    0.025, 8, layer="near", outside_playable=outside,
                )
            for chain_side in (-1.0, 1.0):
                chain_x = mast_x + px * chain_side * 0.22
                chain_z = mast_z + pz * chain_side * 0.22
                plan.pipe(
                    "a22-forklift-visible-mast-chain", "rust", group,
                    (chain_x, 0.82, chain_z),
                    (chain_x, 4.18, chain_z),
                    0.025, 8, layer="near", outside_playable=outside,
                )
            _structural_beam(
                plan, "a22-forklift-mast-load-guard", group,
                (mast_x - px * 0.70, 2.80, mast_z - pz * 0.70),
                (mast_x + px * 0.70, 2.80, mast_z + pz * 0.70),
                0.12, material="structural_steel",
                layer="near", outside=outside,
            )
        _cb(
            plan, "a22-forklift-operator-seat", "pallet_wood", group,
            x - dx * 0.45, 2.0, z - dz * 0.45,
            0.75, 1.2, 0.75, 0.02, "equipment",
            yaw=yaw, layer="near", outside=outside,
        )
        if lod == 0 and not outside:
            operator_x = x - dx * 0.18
            operator_z = z - dz * 0.18
            plan.cylinder(
                "a22-forklift-seated-operator-torso",
                "structural_steel", group,
                operator_x, 2.46, operator_z,
                0.27, 0.72, 10,
                top_radius=0.23, layer="near",
            )
            plan.cylinder(
                "a22-forklift-seated-operator-head",
                "pallet_wood", group,
                operator_x + dx * 0.08, 2.94,
                operator_z + dz * 0.08,
                0.18, 0.27, 10,
                top_radius=0.17, layer="near",
            )
            plan.cylinder(
                "a22-forklift-seated-operator-helmet",
                "safety_orange", group,
                operator_x + dx * 0.08, 3.12,
                operator_z + dz * 0.08,
                0.21, 0.14, 10,
                top_radius=0.17, layer="near",
            )
            _cb(
                plan, "a22-forklift-seated-operator-vest",
                "safety_orange", group,
                operator_x + dx * 0.20, 2.52,
                operator_z + dz * 0.20,
                0.48, 0.40, 0.14,
                0.02, "equipment", yaw=yaw,
                layer="near",
            )
            for side in (-1.0, 1.0):
                plan.round_member(
                    "a22-forklift-seated-operator-control-arm",
                    "weathered_zinc", group,
                    (
                        operator_x + px * side * 0.22,
                        2.55,
                        operator_z + pz * side * 0.22,
                    ),
                    (
                        x + dx * 0.38 + px * side * 0.24,
                        2.40,
                        z + dz * 0.38 + pz * side * 0.24,
                    ),
                    0.055, 10, layer="near",
                )
        for carriage_y in (0.72, 2.05):
            _structural_beam(
                plan, "a22-forklift-carriage-crossbar", group,
                (mast_x - px * 0.78, carriage_y, mast_z - pz * 0.78),
                (mast_x + px * 0.78, carriage_y, mast_z + pz * 0.78),
                0.18, material="safety_orange",
                layer="near", outside=outside,
            )
        _cb(
            plan, "a22-forklift-forward-work-light", "warm_glass", group,
            mast_x - dx * 0.18, 3.75, mast_z - dz * 0.18,
            0.62, 0.42, 0.24,
            0.02, "equipment", yaw=yaw + math.pi / 2,
            layer="near", outside=outside,
        )
        if lod < 2 and loaded:
            load_x, load_z = mast_x + dx * 2.45, mast_z + dz * 2.45
            _cb(
                plan, "a22-forklift-grounded-fork-pallet",
                "pallet_wood", group,
                load_x, 0.54, load_z,
                1.55, 0.34, 2.15,
                0.05, "secondary", yaw=yaw,
                layer="near", outside=outside,
            )
            _cb(
                plan, "a22-forklift-secured-service-load",
                "weathered_zinc", group,
                load_x, 1.42, load_z,
                1.75, 1.35, 1.85,
                0.06, "secondary", yaw=yaw,
                layer="near", outside=outside,
            )
            for band_side in (-1.0, 1.0):
                _cb(
                    plan, "a22-forklift-load-safety-band",
                    "safety_orange", group,
                    load_x + dx * band_side * 0.52,
                    1.42,
                    load_z + dz * band_side * 0.52,
                    0.14, 1.45, 1.95,
                    0.02, "equipment", yaw=yaw,
                    layer="near", outside=outside,
                )
    else:
        _cb(
            plan, "a22-operational-maintenance-truck", "weathered_zinc", group,
            x, 1.8, z, 7.6, 3.1, 3.2, 0.08, "secondary",
            yaw=yaw, layer="near", outside=outside,
        )
        if lod == 0:
            for side in (-1.0, 1.0):
                _cb(
                    plan, "a22-truck-recognizable-fleet-marking",
                    "pale_concrete" if side < 0 else "safety_orange", group,
                    x + px * side * 1.63, 2.15,
                    z + pz * side * 1.63,
                    2.10, 0.82, 0.12,
                    0.02, "equipment", yaw=yaw,
                    layer="near", outside=outside,
                )
        _cb(
            plan, "a22-operational-truck-chassis", "structural_steel", group,
            x, 0.82, z, 8.6, 0.48, 2.55, 0.08, "secondary",
            yaw=yaw, layer="near", outside=outside,
        )
        _cb(
            plan, "a22-operational-truck-cab", "old_concrete", group,
            x + dx * 3.0, 2.5,
            z + dz * 3.0, 2.6, 4.2, 3.1,
            0.08, "secondary", yaw=yaw, layer="near", outside=outside,
        )
        front_x, front_z = x + dx * 4.35, z + dz * 4.35
        _cb(
            plan, "a22-operational-truck-front-bumper",
            "safety_orange", group,
            front_x + dx * 0.08, 0.92, front_z + dz * 0.08,
            2.75, 0.42, 0.42,
            0.02, "equipment", yaw=yaw + math.pi / 2,
            layer="near", outside=outside,
        )
        _cb(
            plan, "a22-operational-truck-front-grille",
            "structural_steel", group,
            front_x + dx * 0.13, 1.65, front_z + dz * 0.13,
            1.55, 0.62, 0.24,
            0.02, "equipment", yaw=yaw + math.pi / 2,
            layer="near", outside=outside,
        )
        _cb(
            plan, "a22-operational-truck-windscreen", "dirty_glass", group,
            front_x, 3.05, front_z, 2.25, 1.35, 0.24,
            0.05, "secondary", yaw=yaw + math.pi / 2,
            layer="near", outside=outside,
        )
        _cb(
            plan, "a22-operational-truck-warm-cab", "warm_glass", group,
            front_x - dx * 0.85, 3.0, front_z - dz * 0.85,
            1.9, 1.1, 0.32, 0.05, "secondary",
            yaw=yaw + math.pi / 2, layer="near", outside=outside,
        )
        if lod < 2:
            cab_x, cab_z = x + dx * 3.0, z + dz * 3.0
            for side in (-1.0, 1.0):
                glass_x = cab_x + px * side * 1.58
                glass_z = cab_z + pz * side * 1.58
                _cb(
                    plan, "a22-operational-truck-side-cab-glass",
                    "dirty_glass", group,
                    glass_x, 3.05, glass_z,
                    1.75, 1.30, 0.18,
                    0.05, "secondary", yaw=yaw,
                    layer="near", outside=outside,
                )
                _cb(
                    plan, "a22-operational-truck-side-cab-warm-depth",
                    "warm_glass", group,
                    glass_x - px * side * 0.20, 3.02,
                    glass_z - pz * side * 0.20,
                    1.48, 1.02, 0.16,
                    0.05, "secondary", yaw=yaw,
                    layer="near", outside=outside,
                )
                plan.round_member(
                    "a22-operational-truck-mirror-arm",
                    "structural_steel", group,
                    (
                        cab_x + dx * 0.92 + px * side * 1.52,
                        3.18,
                        cab_z + dz * 0.92 + pz * side * 1.52,
                    ),
                    (
                        cab_x + dx * 1.18 + px * side * 2.05,
                        3.28,
                        cab_z + dz * 1.18 + pz * side * 2.05,
                    ),
                    0.05, 8, layer="near", outside_playable=outside,
                )
                _cb(
                    plan, "a22-operational-truck-side-mirror",
                    "dirty_glass", group,
                    cab_x + dx * 1.18 + px * side * 2.08,
                    3.28,
                    cab_z + dz * 1.18 + pz * side * 2.08,
                    0.42, 0.58, 0.16,
                    0.02, "equipment", yaw=yaw,
                    layer="near", outside=outside,
                )
        for side in (-1.0, 1.0):
            head_x = front_x + px * side * 0.72
            head_z = front_z + pz * side * 0.72
            _cb(
                plan, "a22-operational-truck-headlight", "warm_glass", group,
                head_x, 1.45, head_z, 0.44, 0.34, 0.22,
                0.02, "equipment", yaw=yaw + math.pi / 2,
                layer="near", outside=outside,
            )
        rib_count = 6 if lod == 0 else 3
        for rib in range(rib_count):
            along = -3.2 + rib * (5.0 / max(1, rib_count - 1))
            _structural_beam(
                plan, "a22-operational-truck-cargo-rib", group,
                (
                    x + dx * along + px * 1.62,
                    0.8,
                    z + dz * along + pz * 1.62,
                ),
                (
                    x + dx * along + px * 1.62,
                    3.4,
                    z + dz * along + pz * 1.62,
                ),
                0.13, material="rust", layer="near", outside=outside,
            )
    if lod < 2:
        wheel_offsets = (-1.0, 1.0) if forklift else (-2.4, 2.4)
        for along in wheel_offsets:
            wx, wz = x + dx * along, z + dz * along
            half_axle = 1.24 if forklift else 1.58
            wheel_half_width = 0.24 if forklift else 0.30
            for side in (-1.0, 1.0):
                lateral = side * (half_axle - wheel_half_width)
                centre_x = wx + px * lateral
                centre_z = wz + pz * lateral
                plan.round_member(
                    "a22-vehicle-round-wheel", "structural_steel", group,
                    (
                        centre_x - px * wheel_half_width,
                        0.72,
                        centre_z - pz * wheel_half_width,
                    ),
                    (
                        centre_x + px * wheel_half_width,
                        0.72,
                        centre_z + pz * wheel_half_width,
                    ),
                    0.56 if forklift else 0.72,
                    14 if lod == 0 else 10,
                    layer="near", outside_playable=outside,
                )
                plan.round_member(
                    "a22-vehicle-wheel-hub", "weathered_zinc", group,
                    (
                        centre_x - px * (wheel_half_width + 0.06),
                        0.72,
                        centre_z - pz * (wheel_half_width + 0.06),
                    ),
                    (
                        centre_x + px * (wheel_half_width + 0.06),
                        0.72,
                        centre_z + pz * (wheel_half_width + 0.06),
                    ),
                    0.24 if forklift else 0.30,
                    12 if lod == 0 else 8,
                    layer="near", outside_playable=outside,
                )
                _cb(
                    plan, "a22-vehicle-baked-wheel-fender",
                    "rust" if forklift else "weathered_zinc", group,
                    centre_x, 1.22 if forklift else 1.43, centre_z,
                    1.45 if forklift else 1.95,
                    0.28 if forklift else 0.34,
                    0.34,
                    0.02, "equipment", yaw=yaw,
                    layer="near", outside=outside,
                )


def _build_working_route(plan: SpecPlan, lod: int) -> None:
    group = "souko-a22-working-route"
    start, end = (-234.0, 170.0), (5.0, 14.0)
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    yaw = math.atan2(dz, dx)

    # The canonical route remains untouched; a broader cosmetic apron provides
    # the rough wet working surface visible in the concept art.
    plan.box(
        "a22-route-broad-rough-wet-working-apron",
        "wet_asphalt", group,
        (start[0] + end[0]) * 0.5, 0.142,
        (start[1] + end[1]) * 0.5,
        length, 0.012, 36.0,
        yaw=yaw, layer="near",
    )
    if lod == 0:
        # Camera-scale foreground occupation: two staggered protection lines
        # and grounded cargo clusters frame, but never enter, the open route.
        for side in (-1.0, 1.0):
            for barrier_index, t in enumerate((0.27, 0.34, 0.42, 0.50)):
                lateral = side * (17.2 + (barrier_index % 2) * 1.1)
                barrier_x = start[0] + dx * t + px * lateral
                barrier_z = start[1] + dz * t + pz * lateral
                _cb(
                    plan, "a22-route-p0-grounded-jersey-barrier",
                    "old_concrete" if barrier_index % 2 else "pale_concrete",
                    group,
                    barrier_x, 0.78, barrier_z,
                    4.8, 1.35, 1.05,
                    0.16, "hero", yaw=yaw, layer="near",
                )
            for cargo_index, t in enumerate((0.31, 0.45)):
                lateral = side * (21.0 + cargo_index * 1.2)
                cargo_x = start[0] + dx * t + px * lateral
                cargo_z = start[1] + dz * t + pz * lateral
                _cb(
                    plan, "a22-route-p0-grounded-cargo-pallet",
                    "pallet_wood", group,
                    cargo_x, 0.42, cargo_z,
                    5.4, 0.52, 3.4,
                    0.05, "secondary", yaw=yaw, layer="near",
                )
                _cb(
                    plan, "a22-route-p0-staged-loaded-crate",
                    ("weathered_zinc", "rust")[
                        (cargo_index + int(side > 0)) % 2
                    ],
                    group,
                    cargo_x, 2.05, cargo_z,
                    4.6, 2.7, 2.8,
                    0.08, "secondary", yaw=yaw, layer="near",
                )
    if lod < 2:
        # Screen-readable loading-bay paint and slab relief occupy the near
        # apron that stayed blank in iteration 18.  All pieces are cosmetic,
        # wafer-thin and leave the canonical route/collision untouched.
        relief_start_t, relief_end_t = 0.20, 0.62
        relief_mid_t = (relief_start_t + relief_end_t) * 0.5
        relief_length = length * (relief_end_t - relief_start_t)
        for side in (-1.0, 1.0):
            for lateral in (10.2, 16.6):
                line_x = start[0] + dx * relief_mid_t + px * side * lateral
                line_z = start[1] + dz * relief_mid_t + pz * side * lateral
                plan.box(
                    "a22-route-foreground-loading-bay-long-line",
                    "pale_concrete" if side > 0 else "safety_orange", group,
                    line_x, 0.171, line_z,
                    relief_length, 0.009, 0.13,
                    yaw=yaw, layer="near",
                )
        divider_count = 11 if lod == 0 else 4
        for index in range(divider_count):
            t = 0.225 + index * 0.35 / max(1, divider_count - 1)
            for side in (-1.0, 1.0):
                centre_x = start[0] + dx * t + px * side * 13.4
                centre_z = start[1] + dz * t + pz * side * 13.4
                plan.box(
                    "a22-route-foreground-loading-bay-divider",
                    "pale_concrete", group,
                    centre_x, 0.173, centre_z,
                    0.13, 0.009, 6.25,
                    yaw=yaw, layer="near",
                )
                plan.box(
                    "a22-route-foreground-faded-hazard-hatch",
                    "pale_concrete"
                    if side > 0 and index % 2 == 0 else "safety_orange",
                    group,
                    centre_x + ux * 1.05,
                    0.174,
                    centre_z + uz * 1.05,
                    5.2, 0.008, 0.14,
                    yaw=yaw + side * 0.69,
                    layer="near",
                )
        joint_count = 5 if lod == 0 else 3
        for index in range(joint_count):
            t = 0.235 + index * 0.34 / max(1, joint_count - 1)
            joint_x = start[0] + dx * t
            joint_z = start[1] + dz * t
            plan.box(
                "a22-route-foreground-slab-expansion-joint",
                "rust", group,
                joint_x, 0.170, joint_z,
                0.16, 0.010, 31.5,
                yaw=yaw, layer="near",
            )
        # Keep cracks as local repair evidence, not a uniform marble network.
        # Iteration 21 deliberately cuts their frequency by one third and
        # narrows their relief while retaining the stronger patch/puddle/skid
        # grammar around traffic activity.
        crack_count = 8 if lod == 0 else 4
        for index in range(crack_count):
            t = 0.215 + index * 0.355 / max(1, crack_count - 1)
            lateral = (-7.2, -3.4, 3.8, 7.6)[index % 4]
            base_x = start[0] + dx * t + px * lateral
            base_z = start[1] + dz * t + pz * lateral
            kink_x = base_x + ux * 2.0 + px * (0.7 if index % 2 else -0.8)
            kink_z = base_z + uz * 2.0 + pz * (0.7 if index % 2 else -0.8)
            end_x = kink_x + ux * 2.6 + px * (-0.9 if index % 3 else 0.6)
            end_z = kink_z + uz * 2.6 + pz * (-0.9 if index % 3 else 0.6)
            plan.pipe(
                "a22-route-foreground-broken-slab-crack",
                "rust" if index % 3 == 0 else "structural_steel", group,
                (base_x, 0.176, base_z),
                (kink_x, 0.176, kink_z),
                0.020, 8, layer="near",
            )
            plan.pipe(
                "a22-route-foreground-broken-slab-crack",
                "rust" if index % 3 == 0 else "structural_steel", group,
                (kink_x, 0.176, kink_z),
                (end_x, 0.176, end_z),
                0.020, 8, layer="near",
            )
        if lod == 0:
            line_start_t, line_end_t = 0.205, 0.66
            line_mid_t = (line_start_t + line_end_t) * 0.5
            line_length = length * (line_end_t - line_start_t)
            for lateral in (-5.8, 5.8):
                line_x = start[0] + dx * line_mid_t + px * lateral
                line_z = start[1] + dz * line_mid_t + pz * lateral
                plan.box(
                    "a22-route-foreground-readable-lane-edge",
                    "pale_concrete", group,
                    line_x, 0.175, line_z,
                    line_length, 0.008, 0.13,
                    yaw=yaw, layer="near",
                )
            for box_index, (t, lateral) in enumerate((
                (0.31, -10.2),
                (0.62, -6.5),
            )):
                centre_x = start[0] + dx * t + px * lateral
                centre_z = start[1] + dz * t + pz * lateral
                for side in (-1.0, 1.0):
                    plan.box(
                        "a22-route-forklift-readable-exclusion-box-long",
                        "safety_orange", group,
                        centre_x + px * side * 3.0,
                        0.176,
                        centre_z + pz * side * 3.0,
                        8.2, 0.008, 0.14,
                        yaw=yaw, layer="near",
                    )
                    plan.box(
                        "a22-route-forklift-readable-exclusion-box-short",
                        "pale_concrete"
                        if box_index == 0 else "safety_orange",
                        group,
                        centre_x + ux * side * 4.1,
                        0.176,
                        centre_z + uz * side * 4.1,
                        0.14, 0.008, 6.0,
                        yaw=yaw, layer="near",
                    )
            for drain_index in range(8):
                t = 0.205 + drain_index * 0.017
                drain_x = start[0] + dx * t
                drain_z = start[1] + dz * t
                for segment_index, lateral in enumerate(
                    (-12.0, -6.0, 0.0, 6.0, 12.0),
                ):
                    plan.box(
                        "a22-route-near-camera-segmented-drain-line",
                        "pale_concrete"
                        if (drain_index + segment_index) % 3 == 0
                        else "weathered_zinc",
                        group,
                        drain_x + px * lateral,
                        0.178,
                        drain_z + pz * lateral,
                        0.13, 0.008, 4.4,
                        yaw=yaw, layer="near",
                    )
    patch_count = 18 if lod == 0 else 10 if lod == 1 else 2
    for index in range(patch_count):
        t = 0.10 + index * 0.82 / max(1, patch_count - 1)
        lateral = (-11.5, -4.5, 5.5, 12.0)[index % 4]
        patch_x = start[0] + dx * t + px * lateral
        patch_z = start[1] + dz * t + pz * lateral
        plan.box(
            "a22-route-roughness-repair-patch",
            "old_concrete" if index % 5 == 0 else "structural_steel",
            group,
            patch_x, 0.152 + (index % 2) * 0.001, patch_z,
            5.5 + index % 4 * 1.2, 0.008, 1.2 + index % 3 * 0.45,
            yaw=yaw + (index % 3 - 1) * 0.08, layer="near",
        )
    marking_count = 14 if lod == 0 else 8 if lod == 1 else 2
    for index in range(marking_count):
        t = 0.12 + index * 0.76 / max(1, marking_count - 1)
        for side in (-1.0, 1.0):
            mark_x = start[0] + dx * t + px * side * 14.2
            mark_z = start[1] + dz * t + pz * side * 14.2
            plan.box(
                "a22-route-faded-hazard-edge-marking",
                "safety_orange", group,
                mark_x, 0.158, mark_z,
                3.6, 0.008, 0.22,
                yaw=yaw, layer="near",
            )
    drain_count = 8 if lod == 0 else 5 if lod == 1 else 2
    for index in range(drain_count):
        t = 0.18 + index * 0.66 / max(1, drain_count - 1)
        drain_x = start[0] + dx * t
        drain_z = start[1] + dz * t
        plan.box(
            "a22-route-visible-cross-drain",
            "structural_steel", group,
            drain_x, 0.160, drain_z,
            0.34, 0.009, 28.0,
            yaw=yaw, layer="near",
        )
        if lod < 2:
            grate_bar_count = 9 if lod == 0 else 5
            for bar_index in range(grate_bar_count):
                lateral = -11.5 + bar_index * (
                    23.0 / max(1, grate_bar_count - 1)
                )
                plan.box(
                    "a22-route-cross-drain-visible-grate-bar",
                    "weathered_zinc", group,
                    drain_x + px * lateral,
                    0.166,
                    drain_z + pz * lateral,
                    1.05, 0.008, 0.12,
                    yaw=yaw, layer="near",
                )

    centre_dash_count = 18 if lod == 0 else 10 if lod == 1 else 3
    for index in range(centre_dash_count):
        t = 0.09 + index * 0.82 / max(1, centre_dash_count - 1)
        x = start[0] + dx * t
        z = start[1] + dz * t
        plan.box(
            "a22-route-faded-pale-centre-dash",
            "pale_concrete", group,
            x, 0.165, z,
            3.8, 0.008, 0.28,
            yaw=yaw, layer="near",
        )
    if lod < 2:
        skid_count = 18 if lod == 0 else 9
        for index in range(skid_count):
            t = 0.10 + index * 0.55 / max(1, skid_count - 1)
            for side in (-1.0, 1.0):
                lateral = side * (2.4 + (index % 3) * 0.28)
                x = start[0] + dx * t + px * lateral
                z = start[1] + dz * t + pz * lateral
                plan.box(
                    "a22-route-broken-tire-skid-trace",
                    "rust" if index % 4 == 0 else "structural_steel",
                    group,
                    x, 0.164, z,
                    3.2 + (index % 4) * 0.65, 0.007, 0.10,
                    yaw=yaw + (index % 3 - 1) * 0.025,
                    layer="near",
                )
        for index, (t, lateral) in enumerate((
            (0.19, -5.5),
            (0.43, 4.8),
            (0.66, -5.0),
            (0.82, 4.2),
        )):
            x = start[0] + dx * t + px * lateral
            z = start[1] + dz * t + pz * lateral
            plan.cylinder(
                "a22-route-round-service-cover",
                "structural_steel" if index % 2 else "weathered_zinc",
                group,
                x, 0.177, z,
                1.05, 0.025, 24 if lod == 0 else 12,
                top_radius=1.05, layer="near",
            )

    vehicle_samples = (
        (0.31, -10.2, True),
        (0.39, 8.2, False),
        (0.62, -6.5, True),
        (0.77, 6.4, False),
    )
    active_vehicles = (
        vehicle_samples if lod == 0
        else vehicle_samples[::2] if lod == 1
        else vehicle_samples[:1]
    )
    for t, lateral, forklift in active_vehicles:
        x = start[0] + dx * t + px * lateral
        z = start[1] + dz * t + pz * lateral
        _build_vehicle(
            plan, group, x, z,
            yaw + (1.59 if forklift else math.pi - 0.18),
            lod, forklift=forklift, loaded=forklift and t > 0.5,
        )

    # Thin water geometry occupies the road surface without changing collision.
    puddle_count = 12 if lod == 0 else 7 if lod == 1 else 3
    for index in range(puddle_count):
        t = 0.22 + index * 0.62 / max(1, puddle_count - 1)
        lateral = (-2.3, 0.9, 2.8)[index % 3]
        x = start[0] + dx * t + px * lateral
        z = start[1] + dz * t + pz * lateral
        puddle_length = 9.0 + index % 3 * 2.0
        # An asymmetric bonded panel avoids the black rectangular card read.
        half_length = puddle_length * 0.5
        half_width = 0.86
        plan.panel(
            "a22-route-wet-reflection-puddle", "puddle_water", group,
            (
                (
                    x - ux * half_length - px * half_width * 0.72,
                    0.167,
                    z - uz * half_length - pz * half_width * 0.72,
                ),
                (
                    x + ux * half_length * 0.82 - px * half_width,
                    0.167,
                    z + uz * half_length * 0.82 - pz * half_width,
                ),
                (
                    x + ux * half_length + px * half_width * 0.62,
                    0.167,
                    z + uz * half_length + pz * half_width * 0.62,
                ),
                (
                    x - ux * half_length * 0.76 + px * half_width,
                    0.167,
                    z - uz * half_length * 0.76 + pz * half_width,
                ),
            ),
            0.012, layer="near",
        )
        if lod < 2:
            for side in (-1.0, 1.0):
                edge_x = x + px * side * 0.86
                edge_z = z + pz * side * 0.86
                plan.pipe(
                    "a22-route-visible-puddle-boundary", "rust", group,
                    (
                        edge_x - ux * puddle_length * 0.48,
                        0.176,
                        edge_z - uz * puddle_length * 0.48,
                    ),
                    (
                        edge_x + ux * puddle_length * 0.48,
                        0.176,
                        edge_z + uz * puddle_length * 0.48,
                    ),
                    0.018, 8, layer="near",
                )

    worker_count = 14 if lod == 0 else 7 if lod == 1 else 3
    if lod < 2:
        cluster_specs = (
            (0.27, 8.4, 3),
            (0.40, -8.5, 2),
            (0.55, 8.7, 3),
            (0.69, -8.2, 3),
            (0.81, 8.0, 3),
        )
        worker_index = 0
        for cluster_index, (t, lateral, member_count) in enumerate(cluster_specs):
            if worker_index >= worker_count:
                break
            cluster_x = start[0] + dx * t + px * lateral
            cluster_z = start[1] + dz * t + pz * lateral
            members_here = min(member_count, worker_count - worker_index)
            for member_index in range(members_here):
                along_offset = (member_index - (members_here - 1) * 0.5) * 1.35
                side_offset = 0.55 if member_index % 2 else -0.35
                x = cluster_x + ux * along_offset + px * side_offset
                z = cluster_z + uz * along_offset + pz * side_offset
                facing = yaw + (
                    math.pi - 0.32 if member_index % 2
                    else 0.38
                )
                _build_worker(
                    plan, group, "a22-route-worker",
                    x, z, facing, lod,
                    pose_index=worker_index + cluster_index,
                )
                worker_index += 1
            _cb(
                plan, "a22-route-cluster-shared-tool-chest",
                "structural_steel", group,
                cluster_x + px * 0.9, 0.40, cluster_z + pz * 0.9,
                1.05, 0.66, 0.58,
                0.02, "equipment", yaw=yaw, layer="near",
            )
            if cluster_index % 2 == 0:
                _cb(
                    plan, "a22-route-cluster-grounded-work-pallet",
                    "pallet_wood", group,
                    cluster_x - ux * 1.15, 0.27, cluster_z - uz * 1.15,
                    2.4, 0.34, 1.55,
                    0.05, "secondary", yaw=yaw, layer="near",
                )
                _cb(
                    plan, "a22-route-cluster-open-service-case",
                    "weathered_zinc", group,
                    cluster_x - ux * 1.15, 0.72, cluster_z - uz * 1.15,
                    1.65, 0.56, 1.05,
                    0.02, "equipment", yaw=yaw, layer="near",
                )
            else:
                plan.round_member(
                    "a22-route-cluster-carried-service-pipe",
                    "rust", group,
                    (
                        cluster_x - ux * 1.45,
                        1.02,
                        cluster_z - uz * 1.45,
                    ),
                    (
                        cluster_x + ux * 1.45,
                        1.02,
                        cluster_z + uz * 1.45,
                    ),
                    0.10, 10 if lod == 0 else 8, layer="near",
                )
    else:
        for index in range(worker_count):
            t = 0.24 + index * 0.60 / max(1, worker_count - 1)
            side = -1.0 if index % 2 else 1.0
            x = start[0] + dx * t + px * side * 8.1
            z = start[1] + dz * t + pz * side * 8.1
            _build_worker(
                plan, group, "a22-route-worker",
                x, z, yaw + (0.3 if index % 3 == 0 else -0.2), lod,
                pose_index=index,
            )

    gear_count = 12 if lod == 0 else 7 if lod == 1 else 3
    for index in range(gear_count):
        t = 0.34 + index * 0.42 / max(1, gear_count - 1)
        side = 1.0 if index % 2 == 0 else -1.0
        x = start[0] + dx * t + px * side * 10.1
        z = start[1] + dz * t + pz * side * 10.1
        if index % 3 == 0:
            plan.cylinder(
                "a22-route-heavy-bollard", "structural_steel", group,
                x, 0.9, z, 0.55, 1.55,
                12 if lod == 0 else 8, top_radius=0.75, layer="near",
            )
        else:
            _cb(
                plan, "a22-route-quay-cargo-cluster",
                ("pallet_wood", "weathered_zinc")[index % 2],
                group, x, 1.0, z, 2.8, 1.8, 2.2,
                0.02, "equipment", yaw=yaw, layer="near",
            )

    # Edge cargo is large enough to establish scale but remains outside the
    # open central lane that failed iteration four.
    cargo_clusters = (
        (0.39, 18.5, 2),
        (0.50, -19.0, 2),
        (0.62, 18.0, 1),
    )
    active_cargo_clusters = (
        cargo_clusters if lod == 0
        else cargo_clusters[:2] if lod == 1
        else cargo_clusters[-1:]
    )
    for cluster_index, (t, lateral, stacks) in enumerate(active_cargo_clusters):
        cargo_x = start[0] + dx * t + px * lateral
        cargo_z = start[1] + dz * t + pz * lateral
        for stack in range(stacks):
            _cb(
                plan, "a22-route-edge-loaded-container",
                ("weathered_zinc", "rust", "safety_orange")[
                    (cluster_index + stack) % 3
                ],
                group,
                cargo_x + px * stack * 0.35,
                1.45 + stack * 2.65,
                cargo_z + pz * stack * 0.35,
                6.2, 2.6, 2.5,
                0.06, "secondary", yaw=yaw, layer="near",
            )
            if lod == 0:
                _cb(
                    plan, "a22-route-container-recognizable-number-marking",
                    "pale_concrete", group,
                    cargo_x + px * (stack * 0.35 + 1.31),
                    1.45 + stack * 2.65,
                    cargo_z + pz * (stack * 0.35 + 1.31),
                    1.75, 0.62, 0.12,
                    0.02, "equipment", yaw=yaw, layer="near",
                )
        if lod < 2:
            _cb(
                plan, "a22-route-edge-container-grounded-pallet",
                "pallet_wood", group,
                cargo_x, 0.34, cargo_z,
                6.8, 0.45, 3.1,
                0.05, "secondary", yaw=yaw, layer="near",
            )
        else:
            plan.box(
                "a22-route-edge-container-grounded-pallet",
                "pallet_wood", group,
                cargo_x, 0.34, cargo_z,
                6.8, 0.45, 3.1,
                yaw=yaw, layer="near",
            )
        if lod < 2:
            for rib in (-2.2, 0.0, 2.2):
                _structural_beam(
                    plan, "a22-route-container-visible-rib", group,
                    (
                        cargo_x + ux * rib - px * 1.15,
                        0.2,
                        cargo_z + uz * rib - pz * 1.15,
                    ),
                    (
                        cargo_x + ux * rib - px * 1.15,
                        2.75,
                        cargo_z + uz * rib - pz * 1.15,
                    ),
                    0.10, material="structural_steel", layer="near",
                )


def _build_foreground_work_clusters(plan: SpecPlan, lod: int) -> None:
    """Segment the primary foreground flanks with grounded work stories."""
    if lod >= 2:
        return
    group = "souko-a22-foreground-work-clusters"
    clusters = (
        (-142.2, 131.0, 0.14),
        (-165.3, 93.6, -0.18),
    )
    active_clusters = clusters if lod == 0 else clusters[:1]
    for cluster_index, (x, z, yaw) in enumerate(active_clusters):
        _cb(
            plan, "a22-foreground-grounded-heavy-pallet",
            "pallet_wood", group,
            x, 0.34, z, 6.6, 0.46, 3.6,
            0.05, "secondary", yaw=yaw, layer="near",
        )
        crate_specs = (
            (-1.75, 1.45, -0.45, 2.5, 2.4, 2.4),
            (1.20, 1.15, 0.55, 2.8, 1.8, 2.1),
            (0.25, 3.05, -0.20, 2.2, 1.6, 1.8),
        )
        for crate_index, (ox, y, oz, width, height, depth) in enumerate(
            crate_specs
        ):
            _cb(
                plan, "a22-foreground-supported-cargo-crate",
                ("weathered_zinc", "rust", "old_concrete")[
                    (cluster_index + crate_index) % 3
                ],
                group,
                x + ox, y, z + oz,
                width, height, depth,
                0.06, "secondary", yaw=yaw, layer="near",
            )
            if lod == 0:
                label_offset = depth * 0.5 + 0.08
                _cb(
                    plan, "a22-foreground-crate-recognizable-bay-marking",
                    "pale_concrete" if crate_index % 2 else "safety_orange",
                    group,
                    x + ox - math.sin(yaw) * label_offset,
                    y + height * 0.10,
                    z + oz + math.cos(yaw) * label_offset,
                    width * 0.52, 0.52, 0.12,
                    0.02, "equipment", yaw=yaw, layer="near",
                )
        for side in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-foreground-cargo-rack-upright", group,
                (x + side * 3.3, 0.4, z - 1.7),
                (x + side * 3.3, 5.8, z - 1.7),
                0.30, material="structural_steel", layer="near",
            )
            _structural_beam(
                plan, "a22-foreground-cargo-rack-knee", group,
                (x + side * 3.3, 0.5, z - 1.7),
                (x + side * 2.0, 3.2, z - 1.7),
                0.24, material="rust", layer="near",
            )
        _structural_beam(
            plan, "a22-foreground-cargo-rack-header", group,
            (x - 3.3, 5.8, z - 1.7),
            (x + 3.3, 5.8, z - 1.7),
            0.36, material="safety_orange", layer="near",
        )
        for drum_index in range(2):
            drum_x = x - 2.0 + drum_index * 4.2
            drum_z = z + 2.4
            plan.cylinder(
                "a22-foreground-grounded-service-drum",
                "structural_steel" if drum_index == 0 else "rust",
                group,
                drum_x, 0.85, drum_z,
                0.72, 1.45, 14 if lod == 0 else 10,
                top_radius=0.72, layer="near",
            )
            plan.round_member(
                "a22-foreground-drum-retaining-chain",
                "safety_orange", group,
                (drum_x - 0.78, 0.60, drum_z - 0.55),
                (drum_x + 0.78, 1.10, drum_z + 0.55),
                0.055, 8, layer="near",
            )
        _cb(
            plan, "a22-foreground-baked-warning-atlas-sign",
            "safety_orange", group,
            x, 4.55, z - 1.88,
            2.8, 1.1, 0.18,
            0.05, "secondary", yaw=yaw, layer="near",
        )
        for marker in (-0.72, 0.0, 0.72):
            _cb(
                plan, "a22-foreground-warning-sign-marker",
                "structural_steel", group,
                x + marker, 4.55, z - 1.99,
                0.16, 0.78 if marker else 0.42, 0.12,
                0.02, "equipment", yaw=yaw, layer="near",
            )


def _build_ship_and_port(plan: SpecPlan, lod: int) -> None:
    group = "souko-a22-working-harbour"
    outside = True
    plan.box(
        "a22-real-harbour-water", "sea_water", group,
        -45.0, -1.5, 211.0, 390.0, 3.0, 78.0,
        layer="far", outside_playable=outside,
    )
    _cb(
        plan, "a22-working-quay", "old_concrete", group,
        -54.0, 0.4, 174.0, 238.0, 1.8, 15.0,
        0.08, "secondary", layer="far", outside=outside,
    )
    # A compact drydock sits on the primary camera's vanishing line.  The
    # northern harbour remains the full production quay, while this secondary
    # basin makes ship and crane identity legible in the dual-hero proof.
    plan.box(
        "a22-primary-visible-drydock-water", "sea_water", group,
        132.0, -0.55, -69.0, 54.0, 0.42, 78.0,
        layer="far",
    )
    for dock_x in (104.2, 159.8):
        _cb(
            plan, "a22-primary-visible-drydock-wall",
            "old_concrete", group,
            dock_x, 1.25, -69.0, 2.4, 3.1, 80.0,
            0.12, "hero", layer="far",
        )
        if lod < 2:
            _guardrail_run(
                plan, group,
                (dock_x, -108.0), (dock_x, -30.0),
                2.8, lod,
            )

    drydock_centre_x, drydock_centre_z = 132.0, -68.0
    for side_x, material in ((121.0, "rust"), (143.0, "structural_steel")):
        plan.panel(
            "a22-primary-visible-ship-hull-side", material, group,
            (
                (side_x, 0.1, -101.0),
                (side_x, 13.5, -94.0),
                (side_x, 13.5, -39.0),
                (
                    side_x + (5.5 if side_x < drydock_centre_x else -5.5),
                    0.1,
                    -28.0,
                ),
            ),
            1.0, layer="far",
        )
    plan.panel(
        "a22-primary-visible-ship-bow-face", "rust", group,
        (
            (126.0, 0.1, -27.5),
            (138.0, 0.1, -27.5),
            (143.0, 13.5, -39.0),
            (121.0, 13.5, -39.0),
        ),
        1.1, layer="far",
    )
    if lod < 2:
        _cb(
            plan, "a22-primary-visible-ship-bow-bulwark",
            "structural_steel", group,
            drydock_centre_x, 15.2, -37.8,
            22.0, 3.0, 1.4,
            0.08, "secondary", layer="far",
        )
        _cb(
            plan, "a22-primary-visible-ship-forecastle-deck",
            "weathered_zinc", group,
            drydock_centre_x, 17.2, -45.0,
            24.0, 1.2, 18.0,
            0.08, "secondary", layer="far",
        )
        _cb(
            plan, "a22-primary-visible-ship-bow-name-stripe",
            "pale_concrete", group,
            drydock_centre_x, 9.4, -26.95,
            11.0, 0.72, 0.26,
            0.05, "secondary", layer="far",
        )
        for anchor_x in (drydock_centre_x - 6.0, drydock_centre_x + 6.0):
            plan.round_member(
                "a22-primary-visible-ship-bow-anchor-hawse",
                "rust", group,
                (anchor_x, 6.8, -27.8), (anchor_x, 6.8, -26.2),
                0.92, 12 if lod == 0 else 8, layer="far",
            )
        for seam_y in (3.0, 7.0, 11.0):
            _cb(
                plan, "a22-primary-visible-ship-bow-plate-seam",
                "structural_steel", group,
                drydock_centre_x, seam_y, -26.82,
                11.2 + seam_y * 0.45, 0.16, 0.18,
                0.02, "equipment", layer="far",
            )
        for porthole_x in (
            drydock_centre_x - 4.8,
            drydock_centre_x - 1.6,
            drydock_centre_x + 1.6,
            drydock_centre_x + 4.8,
        ):
            plan.round_member(
                "a22-primary-visible-ship-bow-lit-porthole",
                "warm_glass", group,
                (porthole_x, 10.1, -27.10),
                (porthole_x, 10.1, -26.45),
                0.34, 10 if lod == 0 else 8, layer="far",
            )
        for marker_x in (
            drydock_centre_x - 2.4,
            drydock_centre_x,
            drydock_centre_x + 2.4,
        ):
            _cb(
                plan, "a22-primary-visible-ship-bow-number-marker",
                "structural_steel", group,
                marker_x, 9.4, -26.78,
                0.32, 0.48 if marker_x != drydock_centre_x else 0.26, 0.12,
                0.02, "equipment", layer="far",
            )
        for side in (-1.0, 1.0):
            _rail(
                plan, group,
                (
                    drydock_centre_x - 10.5,
                    18.2,
                    -38.5 + side * 6.8,
                ),
                (
                    drydock_centre_x + 10.5,
                    18.2,
                    -38.5 + side * 6.8,
                ),
                layer="far",
            )
        for hull_z in (-47.0, -62.0, -77.0, -92.0):
            _structural_beam(
                plan, "a22-primary-visible-ship-camera-side-hull-rib", group,
                (121.15, 1.0, hull_z),
                (121.15, 13.2, hull_z),
                0.30, material="structural_steel", layer="far",
            )
    else:
        plan.box(
            "a22-primary-visible-ship-bow-bulwark",
            "structural_steel", group,
            drydock_centre_x, 10.4, -37.8,
            16.0, 2.6, 1.2,
            layer="far",
        )
    _cb(
        plan, "a22-primary-visible-ship-working-deck",
        "weathered_zinc", group,
        drydock_centre_x, 13.8, drydock_centre_z,
        67.0, 1.2, 21.0,
        0.14, "hero", yaw=math.pi / 2, layer="far",
    )
    _cb(
        plan, "a22-primary-visible-ship-superstructure",
        "pale_concrete", group,
        drydock_centre_x, 25.0, -84.0,
        21.0, 20.0, 21.0,
        0.16, "hero", layer="far",
    )
    if lod < 2:
        _deep_window(
            plan, group, drydock_centre_x, 26.0, -73.3,
            14.0, 5.0, depth=1.5, yaw=math.pi, layer="far",
        )
        _cb(
            plan, "a22-primary-visible-ship-bridge-cab",
            "weathered_zinc", group,
            drydock_centre_x, 38.5, -84.0,
            17.0, 7.0, 18.0,
            0.08, "secondary", layer="far",
        )
        _deep_window(
            plan, group, drydock_centre_x, 39.0, -74.85,
            12.0, 3.8, depth=1.2, yaw=math.pi, layer="far",
        )
        plan.round_member(
            "a22-primary-visible-ship-bridge-mast",
            "structural_steel", group,
            (drydock_centre_x, 42.0, -84.0),
            (drydock_centre_x, 68.0, -84.0),
            0.36, 10 if lod == 0 else 8, layer="far",
        )
        plan.round_member(
            "a22-primary-visible-ship-bridge-radar-yard",
            "safety_orange", group,
            (drydock_centre_x - 7.0, 60.0, -84.0),
            (drydock_centre_x + 7.0, 60.0, -84.0),
            0.20, 8, layer="far",
        )
    drydock_container_count = 10 if lod == 0 else 6 if lod == 1 else 3
    for index in range(drydock_container_count):
        row, column = divmod(index, 5)
        _cb(
            plan, "a22-primary-visible-ship-container",
            ("weathered_zinc", "rust", "safety_orange")[index % 3],
            group,
            126.0 + column * 3.0,
            15.7 + row * 2.8,
            -55.0 + row * 5.0,
            2.7, 2.5, 4.6,
            0.05, "secondary", layer="far",
        )

    # One unmistakable drydock portal crane and two shipboard booms fill the
    # empty skyline while remaining a subordinate port support system.
    crane_z = -43.0
    for side in (-1.0, 1.0):
        leg_x = drydock_centre_x + side * 23.0
        _structural_beam(
            plan, "a22-primary-visible-drydock-crane-leg", group,
            (leg_x, 1.0, crane_z),
            (leg_x - side * 4.0, 62.0, crane_z),
            2.15, material="safety_orange", layer="far",
        )
        _structural_beam(
            plan, "a22-primary-visible-drydock-crane-k-brace", group,
            (leg_x, 3.0, crane_z - 4.5),
            (leg_x - side * 4.0, 36.0, crane_z + 4.5),
            0.86, material="structural_steel", layer="far",
        )
    _structural_beam(
        plan, "a22-primary-visible-drydock-crane-crossbeam", group,
        (drydock_centre_x - 19.0, 62.0, crane_z),
        (drydock_centre_x + 19.0, 62.0, crane_z),
        2.4, material="safety_orange", layer="far",
    )
    _structural_beam(
        plan, "a22-primary-visible-drydock-crane-lower-chord", group,
        (drydock_centre_x - 19.0, 55.0, crane_z),
        (drydock_centre_x + 19.0, 55.0, crane_z),
        1.45, material="structural_steel", layer="far",
    )
    _structural_beam(
        plan, "a22-primary-visible-drydock-crane-top-brace", group,
        (drydock_centre_x - 17.0, 54.8, crane_z),
        (drydock_centre_x + 17.0, 62.2, crane_z),
        1.0, material="rust", layer="far",
    )
    _cb(
        plan, "a22-primary-visible-drydock-crane-trolley-cab",
        "warm_glass", group,
        drydock_centre_x, 58.7, crane_z,
        6.2, 4.2, 5.0,
        0.08, "secondary", layer="far",
    )
    for side in (-1.0, 1.0):
        _structural_beam(
            plan, "a22-primary-visible-drydock-crane-crossbeam-lattice",
            group,
            (drydock_centre_x, 55.0, crane_z + side * 2.05),
            (drydock_centre_x + 18.0, 62.0, crane_z + side * 2.05),
            0.72, material="structural_steel", layer="far",
        )
        _structural_beam(
            plan, "a22-primary-visible-drydock-crane-crossbeam-lattice",
            group,
            (drydock_centre_x, 62.0, crane_z + side * 2.05),
            (drydock_centre_x - 18.0, 55.0, crane_z + side * 2.05),
            0.72, material="structural_steel", layer="far",
        )
    for cross_x in (
        drydock_centre_x - 18.0,
        drydock_centre_x,
        drydock_centre_x + 18.0,
    ):
        _structural_beam(
            plan, "a22-primary-visible-drydock-crane-depth-tie", group,
            (cross_x, 62.0, crane_z - 2.2),
            (cross_x, 62.0, crane_z + 2.2),
            0.62, material="safety_orange", layer="far",
        )
    if lod < 2:
        plan.round_member(
            "a22-primary-visible-drydock-crane-hoist",
            "structural_steel", group,
            (drydock_centre_x, 60.0, crane_z),
            (drydock_centre_x, 23.0, crane_z),
            0.18, 10 if lod == 0 else 8, layer="far",
        )
        _cb(
            plan, "a22-primary-visible-drydock-crane-hook",
            "structural_steel", group,
            drydock_centre_x, 21.0, crane_z,
            1.6, 3.0, 1.6,
            0.02, "equipment", layer="far",
        )
    for mast_z, direction in ((-62.0, -1.0), (-82.0, 1.0)):
        _structural_beam(
            plan, "a22-primary-visible-ship-cargo-boom", group,
            (drydock_centre_x, 15.0, mast_z),
            (drydock_centre_x + direction * 20.0, 43.0, mast_z + 4.0),
            0.90, material="safety_orange", layer="far",
        )
        _structural_beam(
            plan, "a22-primary-visible-ship-cargo-boom-stay", group,
            (drydock_centre_x, 16.0, mast_z),
            (drydock_centre_x + direction * 16.0, 31.0, mast_z + 4.0),
            0.48, material="rust", layer="far",
        )

    if lod < 2:
        # A real open-lattice dock crane provides the missing camera-visible
        # crane silhouette above the transfer bridge.  It is a slender port
        # machine, deliberately subordinate to the two canonical landmarks.
        mobile_x, mobile_z = 158.0, -36.0
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-primary-visible-lattice-crane-tower-leg", group,
                    (mobile_x + sx * 2.4, 0.8, mobile_z + sz * 2.4),
                    (mobile_x + sx * 1.4, 60.0, mobile_z + sz * 1.4),
                    1.15, material="structural_steel", layer="far",
                    outside=True,
                )
        tower_levels = (3.0, 17.0, 31.0, 45.0, 59.0)
        for level_index, level_y in enumerate(tower_levels[:-1]):
            for side_z in (-1.0, 1.0):
                if level_index % 2:
                    first_x, second_x = mobile_x - 2.2, mobile_x + 2.2
                else:
                    first_x, second_x = mobile_x + 2.2, mobile_x - 2.2
                _structural_beam(
                    plan, "a22-primary-visible-lattice-crane-tower-x", group,
                    (first_x, level_y, mobile_z + side_z * 2.2),
                    (second_x, level_y + 13.0, mobile_z + side_z * 2.2),
                    0.62, material="rust", layer="far", outside=True,
                )
        _structural_beam(
            plan, "a22-primary-visible-lattice-crane-tower-crown", group,
            (mobile_x - 4.8, 60.0, mobile_z),
            (mobile_x + 4.8, 60.0, mobile_z),
            1.20, material="safety_orange", layer="far", outside=True,
        )
        _cb(
            plan, "a22-primary-visible-lattice-crane-service-platform",
            "weathered_zinc", group,
            mobile_x, 54.5, mobile_z,
            10.0, 0.80, 9.0,
            0.08, "secondary", layer="far", outside=True,
        )
        boom_start = (mobile_x, 60.0, mobile_z)
        # Swing across the image plane rather than away from the camera.  The
        # earlier endpoint collapsed the truss into a near-vertical yellow bar.
        boom_end = (120.0, 112.0, -105.0)
        for side in (-1.0, 1.0):
            offset_z = side * 2.20
            _structural_beam(
                plan, "a22-primary-visible-lattice-crane-boom-chord", group,
                (boom_start[0], boom_start[1], boom_start[2] + offset_z),
                (boom_end[0], boom_end[1], boom_end[2] + offset_z),
                1.35, material="safety_orange", layer="far", outside=True,
            )
            _structural_beam(
                plan, "a22-primary-visible-lattice-crane-boom-lower-chord",
                group,
                (
                    boom_start[0], boom_start[1] - 6.0,
                    boom_start[2] + offset_z,
                ),
                (
                    boom_end[0] - 2.0, boom_end[1] - 6.5,
                    boom_end[2] + offset_z,
                ),
                1.10, material="structural_steel", layer="far", outside=True,
            )
        lattice_segments = 7 if lod == 0 else 4
        for index in range(lattice_segments):
            t0 = index / lattice_segments
            t1 = (index + 1) / lattice_segments
            for side in (-1.0, 1.0):
                offset_z = side * 2.20
                upper = (
                    boom_start[0] + (boom_end[0] - boom_start[0]) * t0,
                    boom_start[1] + (boom_end[1] - boom_start[1]) * t0,
                    boom_start[2] + (boom_end[2] - boom_start[2]) * t0
                    + offset_z,
                )
                lower = (
                    boom_start[0]
                    + (boom_end[0] - 2.0 - boom_start[0]) * t1,
                    boom_start[1] - 6.0
                    + (boom_end[1] - 6.5 - (boom_start[1] - 6.0)) * t1,
                    boom_start[2]
                    + (boom_end[2] - boom_start[2]) * t1
                    + offset_z,
                )
                _structural_beam(
                    plan, "a22-primary-visible-lattice-crane-boom-web", group,
                    upper, lower,
                    0.88,
                    material="safety_orange" if index % 2 else "rust",
                    layer="far", outside=True,
                )
                upper_next = (
                    boom_start[0] + (boom_end[0] - boom_start[0]) * t1,
                    boom_start[1] + (boom_end[1] - boom_start[1]) * t1,
                    boom_start[2] + (boom_end[2] - boom_start[2]) * t1
                    + offset_z,
                )
                lower_previous = (
                    boom_start[0]
                    + (boom_end[0] - 2.0 - boom_start[0]) * t0,
                    boom_start[1] - 6.0
                    + (boom_end[1] - 6.5 - (boom_start[1] - 6.0)) * t0,
                    boom_start[2]
                    + (boom_end[2] - boom_start[2]) * t0
                    + offset_z,
                )
                _structural_beam(
                    plan, "a22-primary-visible-lattice-crane-boom-web", group,
                    lower_previous, upper_next,
                    0.72, material="structural_steel",
                    layer="far", outside=True,
                )
            cross_t = (t0 + t1) * 0.5
            cross_x = boom_start[0] + (boom_end[0] - boom_start[0]) * cross_t
            cross_y = boom_start[1] + (boom_end[1] - boom_start[1]) * cross_t
            cross_z = boom_start[2] + (boom_end[2] - boom_start[2]) * cross_t
            _structural_beam(
                plan, "a22-primary-visible-lattice-crane-boom-cross-tie",
                group,
                (cross_x, cross_y, cross_z - 2.35),
                (cross_x, cross_y, cross_z + 2.35),
                0.66, material="structural_steel",
                layer="far", outside=True,
            )
        _cb(
            plan, "a22-primary-visible-lattice-crane-operator-cab",
            "warm_glass", group,
            mobile_x - 1.5, 56.0, mobile_z - 3.2,
            5.4, 4.0, 4.8,
            0.08, "secondary", layer="far", outside=True,
        )
        _structural_beam(
            plan, "a22-primary-visible-lattice-crane-counter-jib", group,
            (mobile_x, 61.0, mobile_z),
            (mobile_x - 20.0, 70.0, mobile_z + 7.0),
            1.05, material="structural_steel", layer="far", outside=True,
        )
        _cb(
            plan, "a22-primary-visible-lattice-crane-counterweight",
            "rust", group,
            mobile_x - 18.0, 68.0, mobile_z + 6.3,
            7.5, 5.5, 5.5,
            0.12, "hero", layer="far", outside=True,
        )
        plan.round_member(
            "a22-primary-visible-lattice-crane-hoist-cable",
            "structural_steel", group,
            (126.0, 104.0, -96.0), (126.0, 24.0, -96.0),
            0.16, 10 if lod == 0 else 8,
            layer="far", outside_playable=True,
        )
        _cb(
            plan, "a22-primary-visible-lattice-crane-hook",
            "structural_steel", group,
            126.0, 22.4, -96.0,
            1.8, 3.0, 1.8,
            0.02, "equipment", layer="far", outside=True,
        )

    # Cargo ship: tapered hull panels, proper deck and occupied superstructure.
    hull_centre_x, hull_z = -55.0, 199.0
    plan.panel(
        "a22-cargo-ship-hull-port", "rust", group,
        (
            (-123.0, 0.0, hull_z - 1.0), (-112.0, 8.0, hull_z - 6.5),
            (15.0, 8.0, hull_z - 6.5), (25.0, 0.0, hull_z - 1.0),
        ),
        1.2, layer="far", outside_playable=outside,
    )
    plan.panel(
        "a22-cargo-ship-hull-starboard", "structural_steel", group,
        (
            (-123.0, 0.0, hull_z + 1.0), (25.0, 0.0, hull_z + 1.0),
            (15.0, 8.0, hull_z + 6.5), (-112.0, 8.0, hull_z + 6.5),
        ),
        1.2, layer="far", outside_playable=outside,
    )
    _cb(
        plan, "a22-cargo-ship-working-deck", "weathered_zinc", group,
        hull_centre_x, 8.4, hull_z, 135.0, 1.1, 13.0,
        0.14, "hero", layer="far", outside=outside,
    )
    _cb(
        plan, "a22-cargo-ship-superstructure", "pale_concrete", group,
        -98.0, 17.0, hull_z, 26.0, 16.0, 12.0,
        0.16, "hero", layer="far", outside=outside,
    )
    if lod < 2:
        for side_z, yaw in ((hull_z - 6.1, 0.0), (hull_z + 6.1, math.pi)):
            _deep_window(
                plan, group, -98.0, 18.0, side_z, 17.0, 4.3,
                depth=1.3, yaw=yaw, layer="far",
            )
    container_rows = 12 if lod == 0 else 7 if lod == 1 else 4
    for index in range(container_rows):
        x = -72.0 + index * 7.1
        for stack in range(2 if lod < 2 else 1):
            _cb(
                plan, "a22-ship-loaded-container",
                ("weathered_zinc", "rust", "safety_orange")[index % 3],
                group, x, 11.0 + stack * 3.0, hull_z,
                6.2, 2.6, 5.0, 0.06, "secondary",
                layer="far", outside=outside,
            )

    # Three unequal portal cranes with thick legs and round service rails.
    crane_xs = (-136.0, -68.0, 4.0)
    active_cranes = crane_xs if lod < 2 else crane_xs[::2]
    for crane_index, x in enumerate(active_cranes):
        height = 55.0 + crane_index * 7.0
        for side in (-1, 1):
            z = 172.0 + side * 9.0
            _structural_beam(
                plan, "a22-harbour-crane-heavy-leg", group,
                (x - 7.0, 0.8, z), (x, height, z),
                1.6, material="structural_steel", layer="far", outside=outside,
            )
        _structural_beam(
            plan, "a22-harbour-crane-boom", group,
            (x, height, 172.0), (x + 40.0, height + 16.0, 195.0),
            1.25, material="safety_orange", layer="far", outside=outside,
        )
        _structural_beam(
            plan, "a22-harbour-crane-boom-brace", group,
            (x, height + 1.0, 172.0), (x + 30.0, height - 8.0, 195.0),
            0.72, material="rust", layer="far", outside=outside,
        )
        if lod < 2:
            _rail(
                plan, group, (x + 27.0, height + 10.0, 190.0),
                (x + 27.0, 12.0, 190.0), layer="far", outside=outside,
            )
            _cb(
                plan, "a22-harbour-crane-hook", "structural_steel", group,
                x + 27.0, 10.0, 190.0, 1.1, 2.0, 1.1,
                0.02, "equipment", layer="far", outside=outside,
            )

    vehicle_count = 10 if lod == 0 else 6 if lod == 1 else 3
    for index in range(vehicle_count):
        _build_vehicle(
            plan, group, -170.0 + index * 24.0,
            160.0 + (index % 2) * 7.0, 0.08 * (index % 3),
            lod,
            forklift=index % 3 != 0,
            loaded=index % 3 != 0 and index % 2 == 0,
            outside=True,
        )
    maintenance_count = 28 if lod == 0 else 12 if lod == 1 else 5
    for index in range(maintenance_count):
        x = -182.0 + (index % 14) * 15.0
        z = 151.0 + (index // 14) * 8.0
        _cb(
            plan, "a22-quay-maintenance-equipment",
            ("structural_steel", "rust", "pallet_wood")[index % 3],
            group, x, 1.0, z, 2.8, 1.8, 2.2,
            0.02, "equipment", layer="far", outside=outside,
        )


def _build_secondary_port_city(plan: SpecPlan, lod: int) -> None:
    group = "souko-a22-secondary-port-city"
    districts = (
        (-145.0, -132.0, 0.10, "old_concrete"),
        (132.0, -126.0, -0.08, "weathered_zinc"),
        (143.0, 88.0, 0.04, "pale_concrete"),
        (10.0, -154.0, -0.03, "weathered_zinc"),
    )
    per_district = 11 if lod == 0 else 6 if lod == 1 else 3
    for district_index, (base_x, base_z, yaw, material) in enumerate(districts):
        for index in range(per_district):
            row, column = divmod(index, 4)
            x = base_x + column * (10.5 + district_index)
            z = base_z + row * 13.0
            width = 8.0 + ((index * 3 + district_index) % 5)
            depth = 8.0 + ((index * 5 + district_index) % 6)
            height = 24.0 + ((index * 13 + district_index * 7) % 43)
            _cb(
                plan, "a22-port-city-tall-building", material, group,
                x, height / 2, z, width, height, depth,
                0.08, "secondary", yaw=yaw + (index % 3 - 1) * 0.06,
                layer="far", outside=abs(x) > 166 or abs(z) > 166,
            )
            _cb(
                plan, "a22-port-city-roof-plant", "structural_steel", group,
                x, height + 2.4, z, width * 0.56, 4.6, depth * 0.55,
                0.06, "secondary", yaw=yaw, layer="far",
                outside=abs(x) > 166 or abs(z) > 166,
            )
            if lod < 2:
                _deep_window(
                    plan, group, x, height * 0.72,
                    z + depth * 0.51, width * 0.62, 3.6,
                    depth=1.1, yaw=math.pi + yaw, layer="far",
                )
                _cb(
                    plan, "a22-port-city-visible-weather-band",
                    "rust", group,
                    x, height * 0.48, z + depth * 0.52,
                    width * 0.82, 0.42, 0.22,
                    0.05, "secondary", yaw=yaw, layer="far",
                    outside=abs(x) > 166 or abs(z) > 166,
                )
                if lod == 0 and index in {0, 5}:
                    _cb(
                        plan, "a22-far-district-occupied-light-strip",
                        "warm_glass", group,
                        x, height * (0.38 if index == 0 else 0.62),
                        z + depth * 0.535,
                        width * 0.38, 1.05, 0.18,
                        0.02, "equipment", yaw=yaw, layer="far",
                        outside=abs(x) > 166 or abs(z) > 166,
                    )
                if lod == 0 and index == 0:
                    _cb(
                        plan, "a22-far-district-readable-bay-sign",
                        "safety_orange", group,
                        x + width * 0.24, height * 0.54,
                        z + depth * 0.545,
                        width * 0.26, 0.72, 0.20,
                        0.02, "equipment", yaw=yaw, layer="far",
                        outside=abs(x) > 166 or abs(z) > 166,
                    )
        # A distinct water/service tower anchors each district.
        tower_x = base_x + 13.0
        tower_z = base_z + 30.0
        plan.cylinder(
            "a22-port-city-service-tower", "rust", group,
            tower_x, 33.0, tower_z, 5.5, 58.0,
            18 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=4.2, layer="far",
            outside_playable=abs(tower_x) > 166 or abs(tower_z) > 166,
        )

    # High but distant central skyline closes the vanishing point with real 3D.
    skyline = (
        (-42.0, -179.0, 14.0, 54.0, 13.0),
        (-20.0, -183.0, 17.0, 68.0, 16.0),
        (6.0, -180.0, 13.0, 50.0, 12.0),
        (29.0, -185.0, 18.0, 74.0, 17.0),
        (58.0, -181.0, 15.0, 60.0, 14.0),
    )
    active_skyline = skyline if lod < 2 else skyline[::2]
    for index, (x, z, width, height, depth) in enumerate(active_skyline):
        _cb(
            plan, "a22-central-harbour-skyline",
            ("old_concrete", "weathered_zinc", "pale_concrete")[index % 3],
            group, x, height * 0.5, z, width, height, depth,
            0.08, "secondary", layer="far", outside=True,
        )
        tier_height = 13.0 + (index % 3) * 2.5
        if lod < 2:
            _cb(
                plan, "a22-central-harbour-skyline-setback-tier",
                ("weathered_zinc", "old_concrete", "structural_steel")[
                    index % 3
                ],
                group,
                x, height + tier_height * 0.5, z,
                width * 0.66, tier_height, depth * 0.66,
                0.08, "secondary", layer="far", outside=True,
            )
        _cb(
            plan, "a22-central-harbour-roof-plant", "structural_steel", group,
            x,
            height + (tier_height if lod < 2 else 0.0) + 3.0,
            z, width * 0.48, 5.8, depth * 0.46,
            0.06, "secondary", layer="far", outside=True,
        )
        if lod < 2:
            window_levels = (
                (height * 0.28, height * 0.52, height * 0.76)
                if lod == 0 else (height * 0.38, height * 0.70)
            )
            for window_y in window_levels:
                _deep_window(
                    plan, group, x, window_y, z + depth * 0.51,
                    width * 0.62, 3.2, depth=1.0, yaw=math.pi,
                    layer="far",
                )
                _cb(
                    plan, "a22-central-harbour-skyline-weather-band",
                    "rust", group,
                    x, window_y - 3.2, z + depth * 0.52,
                    width * 0.84, 0.42, 0.22,
                    0.05, "secondary", layer="far", outside=True,
                )
            for side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-central-harbour-skyline-facade-rib", group,
                    (
                        x + side * width * 0.40,
                        1.0,
                        z + depth * 0.52,
                    ),
                    (
                        x + side * width * 0.40,
                        height - 1.0,
                        z + depth * 0.52,
                    ),
                    0.30, material="structural_steel",
                    layer="far", outside=True,
                )
            if lod == 0:
                _cb(
                    plan, "a22-central-skyline-occupied-control-light",
                    "warm_glass", group,
                    x, height * 0.64, z + depth * 0.545,
                    width * 0.30, 1.10, 0.18,
                    0.02, "equipment", layer="far", outside=True,
                )

    # Camera-visible refinery support district.  These are subordinate working
    # buildings, gantries and a striped stack—not a third canonical landmark—
    # positioned to replace the empty central sky with real layered 3D.
    camera_visible_factory = (
        (126.0, -118.0, 14.0, 18.0, 16.0),
        (148.0, -132.0, 18.0, 23.0, 18.0),
        (171.0, -140.0, 14.0, 20.0, 16.0),
    )
    active_factory = (
        camera_visible_factory if lod < 2
        else camera_visible_factory[1:2]
    )
    for index, (x, z, width, height, depth) in enumerate(active_factory):
        outside_factory = abs(x) > 166.0 or abs(z) > 166.0
        _cb(
            plan, "a22-camera-visible-refinery-building",
            ("old_concrete", "weathered_zinc", "pale_concrete")[index % 3],
            group,
            x, height * 0.5, z,
            width, height, depth,
            0.08, "secondary", layer="far", outside=outside_factory,
        )
        _cb(
            plan, "a22-camera-visible-refinery-roof-plant",
            "structural_steel", group,
            x, height + 3.0, z,
            width * 0.62, 5.6, depth * 0.56,
            0.06, "secondary", layer="far", outside=outside_factory,
        )
        if lod < 2:
            for window_y in (height * 0.38, height * 0.70):
                _deep_window(
                    plan, group,
                    x, window_y, z + depth * 0.51,
                    width * 0.66, 3.2,
                    depth=1.1, yaw=math.pi, layer="far",
                )
            _deep_window(
                plan, group,
                x - width * 0.51, height * 0.58, z,
                depth * 0.60, 3.0,
                depth=1.0, yaw=-math.pi / 2, layer="far",
            )
        weather_band_levels = (
            (height * 0.27, height * 0.54, height * 0.81)
            if lod < 2 else (height * 0.54,)
        )
        for band_y in weather_band_levels:
            _cb(
                plan, "a22-camera-visible-refinery-weather-band",
                "rust", group,
                x, band_y, z + depth * 0.515,
                width * 0.82, 0.46, 0.22,
                0.05, "secondary", layer="far",
                outside=outside_factory,
            )
        if lod < 2:
            crown_y = height + 17.0 + index * 3.0
            for sx in (-1.0, 1.0):
                for sz in (-1.0, 1.0):
                    support_x = x + sx * width * 0.42
                    support_z = z + sz * depth * 0.42
                    _structural_beam(
                        plan, "a22-camera-visible-refinery-open-crown-leg",
                        group,
                        (support_x, height + 1.0, support_z),
                        (support_x, crown_y, support_z),
                        0.52, material="structural_steel",
                        layer="far", outside=outside_factory,
                    )
            for side_z in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-camera-visible-refinery-open-crown-x",
                    group,
                    (
                        x - width * 0.40,
                        height + 2.0,
                        z + side_z * depth * 0.42,
                    ),
                    (
                        x + width * 0.40,
                        crown_y - 1.0,
                        z + side_z * depth * 0.42,
                    ),
                    0.38, material="rust",
                    layer="far", outside=outside_factory,
                )
                _structural_beam(
                    plan, "a22-camera-visible-refinery-open-crown-x",
                    group,
                    (
                        x + width * 0.40,
                        height + 2.0,
                        z + side_z * depth * 0.42,
                    ),
                    (
                        x - width * 0.40,
                        crown_y - 1.0,
                        z + side_z * depth * 0.42,
                    ),
                    0.38, material="structural_steel",
                    layer="far", outside=outside_factory,
                )
            _cb(
                plan, "a22-camera-visible-refinery-open-crown-platform",
                "weathered_zinc", group,
                x, crown_y, z,
                width * 0.92, 0.70, depth * 0.92,
                0.07, "secondary", layer="far",
                outside=outside_factory,
            )
            _guardrail_run(
                plan, group,
                (x - width * 0.42, z + depth * 0.46),
                (x + width * 0.42, z + depth * 0.46),
                crown_y + 0.38, lod, outside=outside_factory,
            )

    stack_x, stack_z = 164.0, -88.0
    plan.cylinder(
        "a22-camera-visible-striped-port-stack",
        "pale_concrete", group,
        stack_x, 56.0, stack_z,
        4.35, 110.0,
        20 if lod == 0 else 12 if lod == 1 else 8,
        top_radius=2.5, layer="far",
    )
    stack_bands = (
        (18.0, 34.0, 50.0, 66.0, 82.0, 98.0, 108.0)
        if lod == 0 else (28.0, 58.0, 88.0, 106.0)
        if lod == 1 else (38.0, 82.0)
    )
    for band_y in stack_bands:
        plan.cylinder(
            "a22-camera-visible-striped-port-stack-band",
            "rust", group,
            stack_x, band_y, stack_z,
            4.55 - band_y * 0.015, 1.8,
            20 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=4.48 - band_y * 0.015, layer="far",
        )
    for side in (-1.0, 1.0):
        _structural_beam(
            plan, "a22-camera-visible-refinery-pipe-rack", group,
            (118.0, 18.0 + side * 2.0, -91.0 + side * 3.0),
            (157.0, 18.0 + side * 2.0, -91.0 + side * 3.0),
            0.72, material="safety_orange", layer="far",
        )
        _structural_beam(
            plan, "a22-camera-visible-refinery-pipe-rack-leg", group,
            (126.0 + side * 20.0, 0.6, -91.0 + side * 3.0),
            (126.0 + side * 20.0, 20.0 + side * 2.0, -91.0 + side * 3.0),
            0.66, material="structural_steel", layer="far",
        )
    if lod < 2:
        # Two staggered, open pipe-rack layers close the central sky with
        # parallax rather than another solid wall.  Their endpoints are chosen
        # in image-plane space so neither collapses into the vanishing line.
        layered_racks = (
            ((72.0, -62.0), (176.0, -112.0), 32.0),
            ((92.0, -106.0), (188.0, -158.0), 48.0),
        )
        active_layered_racks = (
            layered_racks if lod == 0 else layered_racks[:1]
        )
        for rack_index, (start, end, deck_y) in enumerate(active_layered_racks):
            rack_dx, rack_dz = end[0] - start[0], end[1] - start[1]
            rack_length = math.hypot(rack_dx, rack_dz)
            rack_ux, rack_uz = rack_dx / rack_length, rack_dz / rack_length
            rack_px, rack_pz = -rack_uz, rack_ux
            pipe_offsets = (-2.8, 0.0, 2.8) if lod == 0 else (-2.2, 2.2)
            for pipe_index, lateral in enumerate(pipe_offsets):
                plan.round_member(
                    "a22-central-two-layer-visible-process-pipe",
                    ("rust", "weathered_zinc", "safety_orange")[pipe_index % 3],
                    group,
                    (
                        start[0] + rack_px * lateral,
                        deck_y + 1.0 + pipe_index * 0.85,
                        start[1] + rack_pz * lateral,
                    ),
                    (
                        end[0] + rack_px * lateral,
                        deck_y + 1.0 + pipe_index * 0.85,
                        end[1] + rack_pz * lateral,
                    ),
                    0.30, 10 if lod == 0 else 8,
                    layer="far", outside_playable=True,
                )
            support_count = 6 if lod == 0 else 4
            support_points = []
            for support_index in range(support_count):
                t = support_index / max(1, support_count - 1)
                centre_x = start[0] + rack_dx * t
                centre_z = start[1] + rack_dz * t
                support_points.append((centre_x, centre_z))
                for side in (-1.0, 1.0):
                    leg_x = centre_x + rack_px * side * 4.0
                    leg_z = centre_z + rack_pz * side * 4.0
                    _structural_beam(
                        plan, "a22-central-two-layer-pipe-rack-leg", group,
                        (leg_x, 0.7, leg_z),
                        (leg_x, deck_y, leg_z),
                        0.72, material="structural_steel",
                        layer="far", outside=True,
                    )
                _structural_beam(
                    plan, "a22-central-two-layer-pipe-rack-crossbeam", group,
                    (
                        centre_x - rack_px * 4.3,
                        deck_y,
                        centre_z - rack_pz * 4.3,
                    ),
                    (
                        centre_x + rack_px * 4.3,
                        deck_y,
                        centre_z + rack_pz * 4.3,
                    ),
                    0.72,
                    material="rust" if (support_index + rack_index) % 2
                    else "structural_steel",
                    layer="far", outside=True,
                )
            for bay_index, (first, second) in enumerate(
                zip(support_points[:-1], support_points[1:])
            ):
                for side in (-1.0, 1.0):
                    first_x = first[0] + rack_px * side * 4.0
                    first_z = first[1] + rack_pz * side * 4.0
                    second_x = second[0] + rack_px * side * 4.0
                    second_z = second[1] + rack_pz * side * 4.0
                    if bay_index % 2:
                        low, high = 3.0, deck_y - 1.0
                    else:
                        low, high = deck_y - 1.0, 3.0
                    _structural_beam(
                        plan, "a22-central-two-layer-pipe-rack-x-brace", group,
                        (first_x, low, first_z),
                        (second_x, high, second_z),
                        0.42, material="rust",
                        layer="far", outside=True,
                    )

        gantry_silhouette_towers = (
            (210.0, -20.0, 64.0),
            (180.0, -80.0, 72.0),
            (110.0, -150.0, 62.0),
        )
        active_silhouette_towers = (
            gantry_silhouette_towers
            if lod == 0 else gantry_silhouette_towers[:2]
        )
        for tower_index, (tower_x, tower_z, height) in enumerate(
            active_silhouette_towers
        ):
            half_width = 4.5 + tower_index * 0.6
            for side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-central-third-layer-gantry-tower-leg", group,
                    (tower_x + side * half_width, 0.8, tower_z),
                    (tower_x + side * half_width * 0.62, height, tower_z),
                    0.82, material="structural_steel",
                    layer="far", outside=True,
                )
            _structural_beam(
                plan, "a22-central-third-layer-gantry-tower-x", group,
                (tower_x - half_width, 4.0, tower_z),
                (tower_x + half_width * 0.62, height - 2.0, tower_z),
                0.52, material="rust", layer="far", outside=True,
            )
            _structural_beam(
                plan, "a22-central-third-layer-gantry-tower-x", group,
                (tower_x + half_width, 4.0, tower_z),
                (tower_x - half_width * 0.62, height - 2.0, tower_z),
                0.52, material="structural_steel",
                layer="far", outside=True,
            )
            _cb(
                plan, "a22-central-third-layer-gantry-service-platform",
                "weathered_zinc", group,
                tower_x, height, tower_z,
                half_width * 2.0, 0.72, 7.0,
                0.07, "secondary", layer="far", outside=True,
            )
            plan.cylinder(
                "a22-central-third-layer-process-drum",
                "rust" if tower_index % 2 else "pale_concrete", group,
                tower_x, height + 5.0, tower_z,
                2.3, 8.5, 14 if lod == 0 else 10,
                top_radius=1.9, layer="far", outside_playable=True,
            )
            plan.round_member(
                "a22-central-third-layer-process-vent",
                "structural_steel", group,
                (tower_x, height + 9.0, tower_z),
                (tower_x, height + 18.0, tower_z),
                0.24, 10 if lod == 0 else 8,
                layer="far", outside_playable=True,
            )

        for gantry_index, (centre_x, z, height) in enumerate(
            ((114.0, -150.0, 49.0), (178.0, -146.0, 57.0))
        ):
            outside_gantry = centre_x > 166.0
            for side in (-1.0, 1.0):
                leg_x = centre_x + side * (9.0 + gantry_index * 1.5)
                _structural_beam(
                    plan, "a22-camera-visible-secondary-gantry-leg", group,
                    (leg_x, 0.6, z),
                    (leg_x - side * 2.0, height, z),
                    0.82, material="structural_steel",
                    layer="far", outside=outside_gantry,
                )
            _structural_beam(
                plan, "a22-camera-visible-secondary-gantry-crossbeam", group,
                (centre_x - 8.0, height, z),
                (centre_x + 8.0, height, z),
                1.0, material="safety_orange",
                layer="far", outside=outside_gantry,
            )
            for brace_side in (-1.0, 1.0):
                _structural_beam(
                    plan, "a22-camera-visible-secondary-gantry-x", group,
                    (centre_x, height - 7.0, z + brace_side * 1.0),
                    (
                        centre_x + brace_side * 8.0,
                        height + 3.0,
                        z + brace_side * 1.0,
                    ),
                    0.44, material="rust",
                    layer="far", outside=outside_gantry,
                )
            if gantry_index == 1:
                _structural_beam(
                    plan, "a22-camera-visible-secondary-gantry-boom", group,
                    (centre_x, height, z),
                    (centre_x + 31.0, height + 18.0, z - 12.0),
                    0.86, material="safety_orange",
                    layer="far", outside=True,
                )

    crane_count = 2 if lod < 2 else 1
    for index in range(crane_count):
        x = -12.0 + index * 56.0
        z = -162.0
        height = 68.0 + index * 8.0
        for side in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-distant-gantry-crane-leg", group,
                (x + side * 7.0, 0.0, z),
                (x + side * 3.0, height, z),
                1.2, material="structural_steel",
                layer="far", outside=True,
            )
        _structural_beam(
            plan, "a22-distant-gantry-crane-boom", group,
            (x - 5.0, height, z), (x + 34.0, height + 14.0, z),
            1.0, material="safety_orange", layer="far", outside=True,
        )
        _structural_beam(
            plan, "a22-distant-gantry-crane-brace", group,
            (x - 4.0, height - 2.0, z),
            (x + 25.0, height + 7.0, z), 0.62,
            material="rust", layer="far", outside=True,
        )


def _build_iteration23_fixed_frame_rebuild(plan: SpecPlan, lod: int) -> None:
    """Reallocate repeated microdetail into the fixed-frame production read.

    Iteration-23 connection map, reviewed before geometry:

    * stackhouse strip foundations -> four void pylons -> occupied partial
      decks -> supported two-storey rack bridge -> roof process house;
    * customs foundation rails -> loading-bay piers/spandrels -> deep portals
      -> integrated tower shoulders -> roof-service rooms;
    * quay deck -> four crane feet -> paired tower chords -> boom/counter-jib,
      while ship hull -> deck -> forecastle and mooring lines -> bollards;
    * foreground slabs -> pallets/vehicles/workers, and far foundations ->
      secondary warehouses/stacks.  None of those subordinate groups creates
      a third canonical mega-landmark.

    The function first removes the orange cargo-band repetition and excess
    rail microgeometry.  That keeps every LOD inside the existing triangle,
    spec, material, primitive and GLB caps while funding larger silhouettes.
    """

    rail_limit = {0: 270, 1: 0, 2: 40}[lod]
    lod_role_limits = (
        {
            "a22-window-reveal": 30,
            "a22-window-camera-scale-vertical-mullion": 20,
            "a22-window-camera-scale-horizontal-mullion": 20,
        }
        if lod == 1 else {}
    )
    rail_count = 0
    limited_role_counts: Counter[str] = Counter()
    retained: list[dict[str, Any]] = []
    removed_names: set[str] = set()
    functional_neutral_materials = {
        "a22-stackhouse-west-service-ladder-rung": "weathered_zinc",
        "a22-stackhouse-maintenance-equipment-skid": "structural_steel",
        "a22-customs-front-service-ladder-rung": "weathered_zinc",
        "a22-customs-front-machine-overhead-beam": "structural_steel",
        "a22-customs-overhead-crane": "weathered_zinc",
        "a22-customs-tower-external-stair-stringer": "weathered_zinc",
        "a22-customs-tower-stair-heavy-handrail": "weathered_zinc",
    }
    for spec in plan.specs:
        role = spec["role"]
        replacement = functional_neutral_materials.get(role)
        if replacement and spec["material"] == "safety_orange":
            spec = {**spec, "material": replacement}
        remove = role == "a22-stackhouse-cargo-band"
        if role in lod_role_limits:
            limited_role_counts[role] += 1
            remove = remove or limited_role_counts[role] > lod_role_limits[role]
        if role == "a22-rounded-guardrail":
            rail_count += 1
            remove = remove or rail_count > rail_limit
        if remove:
            removed_names.add(spec["name"])
        else:
            retained.append(spec)
    plan.specs = retained
    plan.connections = [
        connection
        for connection in plan.connections
        if connection["parent"] not in removed_names
        and connection["child"] not in removed_names
    ]

    # Rack-Bridge Storehouse: four concrete pylons and partial floors create
    # two tall supported voids.  The bridge is deliberately thick enough to
    # read as a process volume rather than a decorative truss.
    stack_group = STACKHOUSE_ID
    stack_front_foot = _cb(
        plan, "a22-i23-stackhouse-front-foundation-rail",
        "old_concrete", stack_group,
        66.0, 3.2, 60.5, 94.0, 6.4, 9.0,
        0.20, "hero", layer="mid",
    )
    stack_back_foot = _cb(
        plan, "a22-i23-stackhouse-back-foundation-rail",
        "old_concrete", stack_group,
        78.0, 3.2, 112.5, 108.0, 6.4, 9.0,
        0.20, "hero", layer="mid",
    )
    pylon_specs = (
        (27.0, 64.0, 20.0, 78.0, 22.0, stack_front_foot),
        (27.0, 107.0, 23.0, 92.0, 20.0, stack_back_foot),
        (79.0, 64.0, 25.0, 96.0, 24.0, stack_front_foot),
        (103.0, 108.0, 22.0, 82.0, 22.0, stack_back_foot),
    )
    active_pylons = (
        pylon_specs if lod < 2 else (pylon_specs[0], pylon_specs[2])
    )
    pylon_names = []
    front_pylon_names = []
    for index, (x, z, width, height, depth, parent) in enumerate(
        active_pylons
    ):
        pylon = _cb(
            plan, "a22-i23-stackhouse-supported-void-pylon",
            "pale_concrete" if index % 2 == 0 else "old_concrete",
            stack_group,
            x, height * 0.5 + 1.0, z,
            width, height, depth,
            0.22, "hero", layer="mid",
        )
        pylon_names.append(pylon)
        if z < 80.0:
            front_pylon_names.append(pylon)
        plan.connect(
            parent, pylon,
            axis="y", overlap_m=0.20,
            parent_face="top", child_face="bottom",
            note="Iteration-23 void pylon seated into continuous footing.",
        )
        if lod < 2:
            service_y = height * (0.56 if index % 2 else 0.42)
            _cb(
                plan, "a22-i23-stackhouse-pylon-process-room",
                "weathered_zinc" if index % 2 else "old_concrete",
                stack_group,
                x + (-2.0 if index % 2 else 2.0),
                service_y, z - depth * 0.36,
                width * 0.76, 10.0 + index, depth * 0.50,
                0.18, "hero", layer="mid",
            )
            _deep_window(
                plan, stack_group,
                x, service_y + 1.0, z - depth * 0.615,
                width * 0.52, 3.8,
                depth=1.6, yaw=0.0, layer="mid",
            )
            plan.round_member(
                "a22-i23-stackhouse-pylon-process-riser",
                "rust" if index % 2 else "structural_steel",
                stack_group,
                (x + width * 0.36, 3.2, z - depth * 0.51),
                (
                    x + width * 0.36,
                    min(height - 3.0, service_y + 18.0),
                    z - depth * 0.51,
                ),
                0.30, 12 if lod == 0 else 8, layer="mid",
            )
            if z < 80.0:
                bay_levels = (19.0, 40.0, 61.0) if lod == 0 else (36.0,)
                for bay_y in bay_levels:
                    if bay_y >= height - 6.0:
                        continue
                    _deep_window(
                        plan, stack_group,
                        x - width * 0.505, bay_y, z,
                        depth * 0.62, 5.2,
                        depth=1.8, yaw=-math.pi / 2, layer="mid",
                    )
                    _cb(
                        plan, "a22-i23-stackhouse-pylon-service-balcony",
                        "weathered_zinc", stack_group,
                        x - width * 0.58, bay_y - 3.2, z,
                        4.0, 0.62, depth * 0.74,
                        0.08, "secondary", layer="mid",
                    )
                    _guardrail_run(
                        plan, stack_group,
                        (
                            x - width * 0.66,
                            z - depth * 0.34,
                        ),
                        (
                            x - width * 0.66,
                            z + depth * 0.34,
                        ),
                        bay_y - 2.9, lod,
                    )

    occupied_decks = (
        (51.0, 18.0, 82.0, 36.0, 18.0),
        (51.0, 35.0, 82.0, 36.0, 18.0),
        (91.0, 23.0, 86.0, 31.0, 18.0),
        (91.0, 43.0, 86.0, 31.0, 18.0),
    )
    active_decks = (
        occupied_decks if lod == 0
        else occupied_decks[::2] if lod == 1
        else occupied_decks[:1]
    )
    for index, (x, y, z, width, depth) in enumerate(active_decks):
        _cb(
            plan, "a22-i23-stackhouse-occupied-partial-floor",
            "weathered_zinc" if index % 2 else "old_concrete",
            stack_group,
            x, y, z, width, 1.4, depth,
            0.14, "hero", layer="mid",
        )
        if lod < 2:
            _cb(
                plan, "a22-i23-stackhouse-floor-machine-volume",
                "structural_steel" if index % 2 else "rust",
                stack_group,
                x + (5.0 if index % 2 else -5.0),
                y + 4.0, z,
                8.0, 6.6, 8.0,
                0.10, "secondary", layer="mid",
            )
            _guardrail_run(
                plan, stack_group,
                (x - width * 0.46, z - depth * 0.46),
                (x + width * 0.46, z - depth * 0.46),
                y + 0.65, lod,
            )

    bridge_floor = _cb(
        plan, "a22-i23-stackhouse-heavy-rack-bridge-floor",
        "weathered_zinc", stack_group,
        63.0, 62.0, 85.0, 80.0, 3.2, 21.0,
        0.18, "hero", layer="mid",
    )
    bridge_roof = _cb(
        plan, "a22-i23-stackhouse-heavy-rack-bridge-roof",
        "old_concrete", stack_group,
        63.0, 76.0, 85.0, 80.0, 2.8, 21.0,
        0.18, "hero", layer="mid",
    )
    for pylon in front_pylon_names:
        plan.connect(
            pylon, bridge_floor,
            axis="y", overlap_m=0.18,
            parent_face="side", child_face="bottom",
            note="Heavy rack bridge overlaps the supported concrete pylons.",
        )
    plan.connect(
        bridge_floor, bridge_roof,
        axis="y", overlap_m=0.08,
        parent_face="top", child_face="bottom",
        note="Bridge roof is locked to its two-storey trussed process volume.",
    )
    bridge_sides = (-1.0, 1.0)
    for side in bridge_sides:
        z = 85.0 + side * 8.5
        for y in (63.8, 74.5):
            _structural_beam(
                plan, "a22-i23-stackhouse-rack-bridge-chord",
                stack_group,
                (24.0, y, z), (102.0, y, z),
                0.94, material="structural_steel", layer="mid",
            )
        cell_count = 8 if lod == 0 else 4 if lod == 1 else 2
        for cell in range(cell_count):
            x0 = 24.0 + cell * (78.0 / cell_count)
            x1 = 24.0 + (cell + 1) * (78.0 / cell_count)
            if cell % 2:
                start, end = (x0, 64.0, z), (x1, 74.3, z)
            else:
                start, end = (x0, 74.3, z), (x1, 64.0, z)
            _structural_beam(
                plan, "a22-i23-stackhouse-rack-bridge-web",
                stack_group,
                start, end, 0.58,
                material="rust" if cell % 3 == 0 else "structural_steel",
                layer="mid",
            )
    bridge_house = _cb(
        plan, "a22-i23-stackhouse-bridge-process-house",
        "pale_concrete", stack_group,
        57.0, 84.0, 85.0, 27.0, 14.0, 15.0,
        0.20, "hero", layer="mid",
    )
    plan.connect(
        bridge_roof, bridge_house,
        axis="y", overlap_m=0.20,
        parent_face="top", child_face="bottom",
        note="Occupied bridge process house bears on the bridge roof slab.",
    )
    if lod < 2:
        _deep_window(
            plan, stack_group,
            57.0, 85.0, 76.95, 17.0, 4.6,
            depth=1.4, yaw=0.0, layer="mid",
        )
        stair_steps = 14 if lod == 0 else 7
        for step in range(stair_steps):
            t = step / max(1, stair_steps - 1)
            _cb(
                plan, "a22-i23-stackhouse-readable-stair-tread",
                "weathered_zinc", stack_group,
                18.0 + t * 12.0,
                5.0 + t * 17.0,
                55.2,
                3.2, 0.34, 1.15,
                0.05, "secondary", layer="mid",
            )
        for side in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-i23-stackhouse-readable-stair-stringer",
                stack_group,
                (18.0 + side * 1.35, 4.8, 55.2),
                (30.0 + side * 1.35, 22.3, 55.2),
                0.18, material="structural_steel", layer="mid",
            )

    # Customs Sawtooth Terminal: one long foundation/facade system, four deep
    # working portals and a tower connection replace the fragmented shed read.
    customs_group = CUSTOMS_ID
    customs_front_foot = _cb(
        plan, "a22-i23-customs-continuous-hall-foundation",
        "old_concrete", customs_group,
        -68.0, 3.0, -26.5, 104.0, 6.0, 10.0,
        0.20, "hero", layer="mid",
    )
    _cb(
        plan, "a22-i23-customs-long-lower-spandrel",
        "pale_concrete", customs_group,
        -68.0, 12.0, -28.0, 104.0, 4.0, 8.0,
        0.18, "hero", layer="mid",
    )
    _cb(
        plan, "a22-i23-customs-long-upper-spandrel",
        "weathered_zinc", customs_group,
        -68.0, 31.0, -30.0, 104.0, 5.0, 10.0,
        0.18, "hero", layer="mid",
    )
    portal_centres = (-103.0, -80.0, -57.0, -34.0)
    active_portals = (
        portal_centres if lod < 2 else portal_centres[::2]
    )
    for portal_index, x in enumerate(active_portals):
        for side in (-1.0, 1.0):
            pier = _cb(
                plan, "a22-i23-customs-deep-loading-bay-pier",
                "old_concrete", customs_group,
                x + side * 8.0, 17.0, -24.0,
                3.6, 28.0, 9.0,
                0.18, "hero", layer="mid",
            )
            if portal_index == 0:
                plan.connect(
                    customs_front_foot, pier,
                    axis="y", overlap_m=0.18,
                    parent_face="top", child_face="bottom",
                    note="Loading-bay pier is grounded in the hall foundation.",
                )
        _cb(
            plan, "a22-i23-customs-deep-loading-bay-header",
            "structural_steel", customs_group,
            x, 28.8, -24.0, 18.0, 3.2, 9.0,
            0.16, "hero", layer="mid",
        )
        _cb(
            plan, "a22-i23-customs-recessed-loading-door",
            "dirty_glass", customs_group,
            x, 12.5, -29.0, 12.0, 18.0, 0.42,
            0.08, "secondary", layer="mid",
        )
        _cb(
            plan, "a22-i23-customs-warm-working-bay-volume",
            "warm_glass", customs_group,
            x, 12.5, -33.5, 10.8, 16.0, 1.0,
            0.08, "secondary", layer="mid",
        )
        if lod < 2:
            _cb(
                plan, "a22-i23-customs-loading-bay-canopy",
                "weathered_zinc", customs_group,
                x, 22.4, -18.7, 15.0, 0.9, 9.5,
                0.10, "secondary", layer="mid",
            )
            _cb(
                plan, "a22-i23-customs-functional-bay-sign",
                "safety_orange", customs_group,
                x + 5.0, 25.0, -18.3,
                2.6, 1.0, 0.22,
                0.05, "secondary", layer="mid",
            )

    tower_links = (
        (-86.0, 39.0, -80.0, 24.0, 30.0, 24.0),
        (-52.0, 43.0, -82.0, 24.0, 38.0, 26.0),
    )
    active_tower_links = tower_links if lod < 2 else tower_links[:1]
    for index, (x, y, z, width, height, depth) in enumerate(active_tower_links):
        _cb(
            plan, "a22-i23-customs-integrated-tower-shoulder",
            "old_concrete" if index == 0 else "pale_concrete",
            customs_group,
            x, y, z, width, height, depth,
            0.22, "hero", layer="mid",
        )
        if lod < 2:
            _deep_window(
                plan, customs_group,
                x, y + 4.0, z + depth * 0.51,
                width * 0.58, 5.2,
                depth=1.6, yaw=math.pi, layer="mid",
            )
    _cb(
        plan, "a22-i23-customs-tower-hall-link-deck",
        "weathered_zinc", customs_group,
        -69.0, 44.0, -73.0, 54.0, 2.0, 18.0,
        0.16, "hero", layer="mid",
    )
    service_centres = (-99.0, -73.0, -47.0, -25.0)
    active_service = (
        service_centres if lod == 0
        else service_centres[::2] if lod == 1
        else service_centres[:1]
    )
    for index, x in enumerate(active_service):
        _cb(
            plan, "a22-i23-customs-roof-service-house",
            "weathered_zinc" if index % 2 else "old_concrete",
            customs_group,
            x, 47.0 + (index % 2) * 4.0, -62.0,
            15.0, 9.0 + (index % 2) * 3.0, 14.0,
            0.16, "hero", layer="mid",
        )
        if lod < 2:
            plan.round_member(
                "a22-i23-customs-roof-service-vent-stack",
                "rust", customs_group,
                (x + 4.0, 51.0, -62.0),
                (x + 4.0, 63.0 + index * 2.0, -62.0),
                0.52, 12 if lod == 0 else 8, layer="mid",
            )
    if lod < 2:
        _cb(
            plan, "a22-i23-customs-camera-facing-service-catwalk",
            "weathered_zinc", customs_group,
            -68.0, 34.0, -17.2, 92.0, 0.80, 3.2,
            0.10, "secondary", layer="mid",
        )
        _guardrail_run(
            plan, customs_group,
            (-113.0, -15.9), (-23.0, -15.9),
            34.4, lod,
        )
        stair_steps = 18 if lod == 0 else 9
        for step in range(stair_steps):
            t = step / max(1, stair_steps - 1)
            _cb(
                plan, "a22-i23-customs-readable-external-stair-tread",
                "weathered_zinc", customs_group,
                -30.0 - t * 25.0,
                3.0 + t * 30.2,
                -15.4,
                3.4, 0.34, 1.25,
                0.05, "secondary", layer="mid",
            )
        for side_z in (-1.0, 1.0):
            _structural_beam(
                plan, "a22-i23-customs-readable-external-stair-stringer",
                customs_group,
                (-30.0, 2.8, -15.4 + side_z * 1.25),
                (-55.0, 33.4, -15.4 + side_z * 1.25),
                0.20, material="structural_steel", layer="mid",
            )
        _cb(
            plan, "a22-i23-customs-readable-external-stair-landing",
            "weathered_zinc", customs_group,
            -56.0, 34.0, -15.4, 8.0, 0.68, 4.2,
            0.08, "secondary", layer="mid",
        )

    # Camera-right real quay machine.  Zinc/steel/rust carry the large shapes;
    # warning colour is limited to one operator panel and the hook.
    quay_group = "souko-a22-iteration23-quay-machine"
    crane_x = -125.0
    crane_z = -10.0
    crane_foot_names = []
    for side_x in (-1.0, 1.0):
        for side_z in (-1.0, 1.0):
            foot = _cb(
                plan, "a22-i23-quay-crane-grounded-foot",
                "old_concrete", quay_group,
                crane_x + side_x * 4.2, 2.3, crane_z + side_z * 5.0,
                5.0, 4.6, 6.0,
                0.16, "hero", layer="near", outside=True,
            )
            crane_foot_names.append(foot)
            _structural_beam(
                plan, "a22-i23-quay-crane-heavy-tower-leg",
                quay_group,
                (
                    crane_x + side_x * 4.2,
                    4.4,
                    crane_z + side_z * 5.0,
                ),
                (
                    crane_x + side_x * 2.5,
                    64.0,
                    crane_z + side_z * 3.0,
                ),
                1.45, material="structural_steel",
                layer="near", outside=True,
            )
    tower_levels = (12.0, 28.0, 44.0, 60.0)
    active_levels = (
        tower_levels if lod == 0
        else tower_levels[::2] if lod == 1
        else tower_levels[:1]
    )
    for level_index, y in enumerate(active_levels):
        _structural_beam(
            plan, "a22-i23-quay-crane-tower-cross-brace",
            quay_group,
            (crane_x - 4.0, y, crane_z - 4.7),
            (crane_x + 4.0, min(64.0, y + 14.0), crane_z + 4.7),
            0.76, material="rust" if level_index % 2 else "structural_steel",
            layer="near", outside=True,
        )
        _structural_beam(
            plan, "a22-i23-quay-crane-tower-cross-brace",
            quay_group,
            (crane_x + 4.0, y, crane_z - 4.7),
            (crane_x - 4.0, min(64.0, y + 14.0), crane_z + 4.7),
            0.76, material="structural_steel",
            layer="near", outside=True,
        )
    _cb(
        plan, "a22-i23-quay-crane-service-platform",
        "weathered_zinc", quay_group,
        crane_x, 61.0, crane_z, 15.0, 1.4, 14.0,
        0.14, "hero", layer="near", outside=True,
    )
    _cb(
        plan, "a22-i23-quay-crane-operator-cab",
        "dirty_glass", quay_group,
        crane_x - 3.0, 66.0, crane_z + 4.0, 7.0, 7.0, 7.0,
        0.12, "hero", layer="near", outside=True,
    )
    _cb(
        plan, "a22-i23-quay-crane-functional-warning-panel",
        "safety_orange", quay_group,
        crane_x - 3.0, 66.0, crane_z + 7.58, 3.8, 1.0, 0.18,
        0.05, "secondary", layer="near", outside=True,
    )
    boom_start = (crane_x, 66.0, crane_z)
    boom_end = (-175.0, 112.0, -82.0)
    for side in (-1.0, 1.0):
        offset = side * 2.6
        _structural_beam(
            plan, "a22-i23-quay-crane-boom-upper-chord",
            quay_group,
            (boom_start[0], boom_start[1], boom_start[2] + offset),
            (boom_end[0], boom_end[1], boom_end[2] + offset),
            1.10, material="structural_steel",
            layer="near", outside=True,
        )
        _structural_beam(
            plan, "a22-i23-quay-crane-boom-lower-chord",
            quay_group,
            (boom_start[0], boom_start[1] - 6.0, boom_start[2] + offset),
            (boom_end[0], boom_end[1] - 7.0, boom_end[2] + offset),
            0.92, material="rust",
            layer="near", outside=True,
        )
    web_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(web_count):
        t0 = index / web_count
        t1 = (index + 1) / web_count
        top = tuple(
            boom_start[axis]
            + (boom_end[axis] - boom_start[axis]) * t0
            for axis in range(3)
        )
        bottom = (
            boom_start[0] + (boom_end[0] - boom_start[0]) * t1,
            boom_start[1] - 6.0
            + (boom_end[1] - 7.0 - (boom_start[1] - 6.0)) * t1,
            boom_start[2] + (boom_end[2] - boom_start[2]) * t1,
        )
        _structural_beam(
            plan, "a22-i23-quay-crane-boom-web",
            quay_group,
            top, bottom, 0.68,
            material="weathered_zinc" if index % 2 else "structural_steel",
            layer="near", outside=True,
        )
    _structural_beam(
        plan, "a22-i23-quay-crane-counter-jib",
        quay_group,
        (crane_x, 67.0, crane_z), (-93.0, 79.0, 12.0),
        1.10, material="structural_steel",
        layer="near", outside=True,
    )
    _structural_beam(
        plan, "a22-i23-quay-crane-counter-jib-lower-chord",
        quay_group,
        (crane_x, 62.0, crane_z), (-96.0, 72.5, 9.0),
        0.86, material="rust",
        layer="near", outside=True,
    )
    _structural_beam(
        plan, "a22-i23-quay-crane-counter-jib-support-diagonal",
        quay_group,
        (-112.0, 63.5, -1.0), (-99.0, 77.0, 8.0),
        0.64, material="structural_steel",
        layer="near", outside=True,
    )
    _cb(
        plan, "a22-i23-quay-crane-counterweight",
        "rust", quay_group,
        -96.0, 75.0, 9.0, 9.0, 5.0, 6.0,
        0.18, "hero", layer="near", outside=True,
    )
    if lod < 2:
        plan.round_member(
            "a22-i23-quay-crane-hoist-cable",
            "structural_steel", quay_group,
            (-171.0, 106.0, -76.0), (-171.0, 18.0, -76.0),
            0.18, 10 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
        _cb(
            plan, "a22-i23-quay-crane-hook",
            "safety_orange", quay_group,
            -171.0, 16.0, -76.0, 2.2, 3.8, 2.2,
            0.05, "secondary", layer="near", outside=True,
        )

    ship_quay_land_x = math.cos(PRIMARY_QUAY_YAW)
    ship_quay_land_z = math.sin(PRIMARY_QUAY_YAW)

    def iteration_ship_land_x(z: float) -> float:
        return primary_ship_land_x(z)

    forward_axis_z = 34.0
    forward_x = (
        iteration_ship_land_x(forward_axis_z)
        - PRIMARY_SHIP_HALF_BEAM
        + 0.4
    )
    forward_z = forward_axis_z
    if lod < 2:
        for y in (2.0, 4.5, 6.5):
            _structural_beam(
                plan, "a22-i23-ship-camera-side-hull-rub-rail",
                quay_group,
                (iteration_ship_land_x(34.0) - 0.4, y, 34.0),
                (iteration_ship_land_x(68.0) - 0.4, y, 68.0),
                0.34, material="rust" if y == 4.5 else "weathered_zinc",
                layer="near", outside=True,
            )
        for z in (38.0, 46.0, 54.0, 62.0, 70.0):
            porthole_x = iteration_ship_land_x(z) - 0.5
            plan.round_member(
                "a22-i23-ship-camera-side-porthole",
                "warm_glass", quay_group,
                (
                    porthole_x - 0.2,
                    5.2,
                    z,
                ),
                (
                    porthole_x + 0.8,
                    5.2,
                    z,
                ),
                0.34, 10 if lod == 0 else 8,
                layer="near", outside_playable=True,
            )
        forward_house = _cb(
            plan, "a22-i23-ship-readable-forward-deckhouse",
            "pale_concrete", quay_group,
            forward_x, 15.8, forward_z, 5.8, 2.2, 10.0,
            0.18, "hero", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
        bridge_cab = _cb(
            plan, "a22-i23-ship-readable-forward-bridge",
            "weathered_zinc", quay_group,
            forward_x, 18.2, forward_z, 5.2, 3.0, 9.0,
            0.14, "hero", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
        plan.connect(
            forward_house, bridge_cab,
            axis="y", overlap_m=0.18,
            parent_face="top", child_face="bottom",
            note="Forward bridge overlaps the ship deckhouse crown.",
        )
        _deep_window(
            plan, quay_group,
            forward_x + 2.85,
            18.2,
            forward_z,
            6.5, 2.1,
            depth=1.1,
            yaw=PRIMARY_SHIP_YAW - math.pi / 2,
            layer="near",
        )
        plan.round_member(
            "a22-i23-ship-readable-forward-mast",
            "structural_steel", quay_group,
            (forward_x, 20.0, forward_z),
            (forward_x, 29.0, forward_z),
            0.42, 12 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
        plan.round_member(
            "a22-i23-ship-readable-radar-yard",
            "weathered_zinc", quay_group,
            (
                forward_x - 3.0,
                26.5,
                forward_z,
            ),
            (
                forward_x + 3.0,
                26.5,
                forward_z,
            ),
            0.24, 10 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )
        _structural_beam(
            plan, "a22-i23-ship-readable-cargo-boom",
            quay_group,
            (forward_x, 24.5, forward_z),
            (-157.0, 18.0, 40.0),
            0.48, material="weathered_zinc",
            layer="near", outside=True,
        )
        _structural_beam(
            plan, "a22-i23-ship-readable-cargo-boom-stay",
            quay_group,
            (forward_x, 28.5, forward_z),
            (-157.0, 18.0, 40.0),
            0.22, material="structural_steel",
            layer="near", outside=True,
        )
        _guardrail_run(
            plan, quay_group,
            (iteration_ship_land_x(34.0) - 1.5, 34.0),
            (iteration_ship_land_x(68.0) - 1.5, 68.0),
            8.2, lod, outside=True,
        )
        for z in (54.0, 62.0, 70.0):
            hawse_x = iteration_ship_land_x(z) - 0.5
            plan.round_member(
                "a22-i23-ship-readable-anchor-hawse",
                "rust", quay_group,
                (
                    hawse_x - 0.2,
                    4.2,
                    z,
                ),
                (
                    hawse_x + 0.9,
                    4.2,
                    z,
                ),
                0.48, 12 if lod == 0 else 8,
                layer="near", outside_playable=True,
            )
    else:
        _cb(
            plan, "a22-i23-ship-readable-forward-deckhouse",
            "pale_concrete", quay_group,
            forward_x, 15.8, forward_z, 5.8, 2.2, 10.0,
            0.18, "hero", yaw=PRIMARY_SHIP_YAW,
            layer="near", outside=True,
        )
    for start_z, bollard_z in ((38.0, 46.0), (60.0, 68.0)):
        plan.round_member(
            "a22-i23-ship-readable-foreground-mooring-line",
            "structural_steel", quay_group,
            (
                iteration_ship_land_x(start_z) - 1.0,
                5.0,
                start_z,
            ),
            (
                primary_quay_edge_x(bollard_z)
                + ship_quay_land_x * 2.0,
                2.25,
                bollard_z + ship_quay_land_z * 2.0,
            ),
            0.22, 10 if lod == 0 else 8,
            layer="near", outside_playable=True,
        )

    # Low edge clusters reduce empty foreground without closing the centre
    # combat corridor.  Their dimensions are human/vehicle scale in metres.
    foreground_group = "souko-a22-iteration23-loading-clusters"
    cluster_centres = ((-158.0, 142.0, 0.08),)
    active_clusters = (
        cluster_centres if lod < 2 else cluster_centres[:1]
    )
    for cluster_index, (x, z, yaw) in enumerate(active_clusters):
        _cb(
            plan, "a22-i23-foreground-loading-slab",
            "pale_concrete", foreground_group,
            x, 0.35, z, 46.0, 0.70, 14.0,
            0.12, "hero", yaw=yaw, layer="near",
        )
        for post_x in (-9.0, 9.0):
            for post_z in (-5.0, 5.0):
                _structural_beam(
                    plan, "a22-i23-foreground-loading-canopy-post",
                    foreground_group,
                    (x + post_x, 0.7, z + post_z),
                    (x + post_x, 8.0, z + post_z),
                    0.34, material="structural_steel", layer="near",
                )
        _cb(
            plan, "a22-i23-foreground-loading-canopy-roof",
            "weathered_zinc", foreground_group,
            x, 8.0, z, 23.0, 0.75, 13.0,
            0.10, "secondary", yaw=yaw, layer="near",
        )
        pallet_count = 4 if lod == 0 else 2 if lod == 1 else 1
        for pallet_index in range(pallet_count):
            _cb(
                plan, "a22-i23-foreground-grounded-pallet",
                "pallet_wood", foreground_group,
                x - 7.0 + pallet_index * 4.2,
                0.85, z + 2.5,
                3.4, 0.55, 3.0,
                0.05, "secondary", yaw=yaw, layer="near",
            )
            _cb(
                plan, "a22-i23-foreground-loaded-cargo",
                ("weathered_zinc", "rust", "structural_steel")[
                    (cluster_index + pallet_index) % 3
                ],
                foreground_group,
                x - 7.0 + pallet_index * 4.2,
                2.0, z + 2.5,
                3.0, 2.0, 2.6,
                0.06, "secondary", yaw=yaw, layer="near",
            )
        if lod < 2:
            _build_vehicle(
                plan, foreground_group,
                x + 5.0, z - 2.0, yaw,
                lod,
                forklift=cluster_index == 0,
                loaded=True,
            )
            _build_worker(
                plan, foreground_group,
                "a22-i23-foreground-loading-worker",
                x - 4.0, z - 2.5, yaw,
                lod,
                pose_index=cluster_index + 2,
            )

    route_pocket_x, route_pocket_z = -108.0, 128.0
    _cb(
        plan, "a22-i23-foreground-route-pocket-slab",
        "old_concrete", foreground_group,
        route_pocket_x, 0.42, route_pocket_z,
        30.0, 0.84, 15.0,
        0.14, "hero", yaw=0.10, layer="near",
    )
    pocket_loads = (
        (-116.0, 132.0, 12.0, 6.0, 6.0),
        (-101.0, 131.0, 10.0, 5.0, 6.0),
        (-96.0, 123.0, 7.0, 4.0, 5.0),
    )
    active_pocket_loads = (
        pocket_loads if lod == 0
        else pocket_loads[:2] if lod == 1
        else pocket_loads[:1]
    )
    for index, (x, z, width, height, depth) in enumerate(active_pocket_loads):
        _cb(
            plan, "a22-i23-foreground-route-pocket-loaded-cargo",
            ("weathered_zinc", "rust", "structural_steel")[index % 3],
            foreground_group,
            x, height * 0.5 + 0.75, z,
            width, height, depth,
            0.10, "secondary", yaw=0.10, layer="near",
        )
        _cb(
            plan, "a22-i23-foreground-route-pocket-pallet",
            "pallet_wood", foreground_group,
            x, 0.72, z,
            width * 0.82, 0.48, depth * 0.82,
            0.05, "secondary", yaw=0.10, layer="near",
        )
    barrier_count = 5 if lod == 0 else 3 if lod == 1 else 1
    for index in range(barrier_count):
        _cb(
            plan, "a22-i23-foreground-route-pocket-cover",
            "pale_concrete", foreground_group,
            -121.0 + index * 5.0,
            1.0, 119.0 + index * 0.7,
            4.6, 2.0, 1.6,
            0.10, "secondary", yaw=0.12, layer="near",
        )
    if lod < 2:
        _build_vehicle(
            plan, foreground_group,
            -106.0, 121.0, 0.12,
            lod,
            forklift=False,
            loaded=True,
        )
        worker_count = 2 if lod == 0 else 1
        for worker_index in range(worker_count):
            _build_worker(
                plan, foreground_group,
                "a22-i23-foreground-route-pocket-worker",
                -116.0 + worker_index * 5.0,
                123.0 + worker_index * 1.5,
                0.2 + worker_index * 0.3,
                lod,
                pose_index=worker_index + 5,
            )

    # Dense real 3D far port: low enough to remain subordinate, varied enough
    # to close the sky gap behind the central service road.
    skyline_group = "souko-a22-iteration23-real-port-skyline"
    skyline = (
        (-8.0, -116.0, 24.0, 31.0, 20.0),
        (18.0, -146.0, 28.0, 43.0, 22.0),
        (48.0, -174.0, 22.0, 36.0, 20.0),
        (76.0, -142.0, 30.0, 51.0, 24.0),
        (105.0, -184.0, 24.0, 40.0, 20.0),
        (132.0, -150.0, 26.0, 47.0, 22.0),
    )
    active_skyline = (
        skyline if lod == 0
        else skyline[::2] if lod == 1
        else skyline[1::3]
    )
    for index, (x, z, width, height, depth) in enumerate(active_skyline):
        _cb(
            plan, "a22-i23-far-port-warehouse-mass",
            ("old_concrete", "weathered_zinc", "pale_concrete")[index % 3],
            skyline_group,
            x, height * 0.5, z,
            width, height, depth,
            0.16, "hero", layer="far", outside=True,
        )
        _cb(
            plan, "a22-i23-far-port-tiered-roof-plant",
            "structural_steel" if index % 2 else "rust",
            skyline_group,
            x + (-3.0 if index % 2 else 3.0),
            height + 4.0, z,
            width * 0.62, 8.0, depth * 0.60,
            0.12, "hero", layer="far", outside=True,
        )
        if lod < 2:
            _deep_window(
                plan, skyline_group,
                x, height * 0.60, z + depth * 0.51,
                width * 0.58, 3.6,
                depth=1.2, yaw=math.pi, layer="far",
            )
    stack_specs = (
        (6.0, -166.0, 68.0),
        (62.0, -190.0, 84.0),
        (121.0, -178.0, 74.0),
    )
    active_stacks = (
        stack_specs if lod == 0
        else stack_specs[::2] if lod == 1
        else stack_specs[:1]
    )
    for index, (x, z, height) in enumerate(active_stacks):
        plan.cylinder(
            "a22-i23-far-port-service-stack",
            "rust" if index % 2 else "weathered_zinc",
            skyline_group,
            x, height * 0.5, z,
            2.6, height,
            16 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=1.9,
            layer="far", outside_playable=True,
        )


def _build_iteration28_material_dock_finish(plan: SpecPlan, lod: int) -> None:
    """Spend repeated microdetail on material depth and dock-side stories.

    Iteration-28 connection map, reviewed before geometry:

    * bridge process house -> seated equipment plinth -> tapered exhaust neck
      -> rain hood;
    * customs service room -> seated equipment plinth -> tapered exhaust neck
      -> rain hood;
    * reduced far roof plant -> tapered process neck -> rain hood;
    * bridge floor -> dark underside attachment band -> occupied task strips;
    * loading-bay canopy -> dark attachment band -> occupied task strip;
    * ship camera-side hull -> waterline/paint/runoff bands and deck shadow;
    * quay wall -> tidal contact band, while pallets -> loaded crates.

    All new dock props remain on the landward edge pocket or outside the
    playable shoreline.  The camera, ship envelope, water geometry, route
    centre and authored quay boundary are deliberately untouched.
    """

    # Reclaim highly repeated rails and mullions rather than expanding the
    # current LOD ceilings.  Camera-right quay rails are explicitly retained.
    removal_limits = {
        0: {
            (STACKHOUSE_ID, "a22-rounded-guardrail"): 64,
        },
        1: {
            (STACKHOUSE_ID, "a22-rounded-guardrail"): 18,
            (
                STACKHOUSE_ID,
                "a22-window-camera-scale-vertical-mullion",
            ): 20,
            (
                STACKHOUSE_ID,
                "a22-window-camera-scale-horizontal-mullion",
            ): 20,
        },
        2: {
            (STACKHOUSE_ID, "a22-rounded-guardrail"): 10,
        },
    }[lod]
    removed_counts: Counter[tuple[str, str]] = Counter()
    removed_names: set[str] = set()
    retained: list[dict[str, Any]] = []
    ship_materials = {
        "a22-p0-primary-camera-ship-near-hull": "structural_steel",
        "a22-p0-primary-camera-ship-far-hull": "weathered_zinc",
        "a22-p0-primary-camera-ship-bow": "structural_steel",
        "a22-i23-ship-readable-forward-deckhouse": "old_concrete",
        "a22-i23-ship-readable-forward-bridge": "weathered_zinc",
    }
    reduced_roof_roles = {
        "a22-i23-far-port-tiered-roof-plant",
        "a22-p0-central-layered-port-roof-plant",
    }
    for original in plan.specs:
        spec = dict(original)
        key = (spec["group"], spec["role"])
        if removed_counts[key] < removal_limits.get(key, 0):
            removed_counts[key] += 1
            removed_names.add(spec["name"])
            continue
        if spec["role"] in ship_materials:
            spec["material"] = ship_materials[spec["role"]]
        if spec["role"] in reduced_roof_roles and spec["kind"] == "chamfer_box":
            bottom = float(spec["y"]) - float(spec["h"]) * 0.5
            reduced_height = float(spec["h"]) * 0.62
            spec["h"] = reduced_height
            spec["y"] = bottom + reduced_height * 0.5
            spec["material"] = (
                "structural_steel"
                if spec["role"].startswith("a22-p0")
                else "weathered_zinc"
            )
        retained.append(spec)
    plan.specs = retained
    plan.connections = [
        connection
        for connection in plan.connections
        if connection["parent"] not in removed_names
        and connection["child"] not in removed_names
    ]

    def specs_for(role: str) -> list[dict[str, Any]]:
        return [spec for spec in plan.specs if spec["role"] == role]

    def add_supported_cap(
        parent: Mapping[str, Any],
        *,
        group: str,
        role_prefix: str,
        material: str,
        outside: bool,
        layer: str,
        scale: float = 1.0,
    ) -> None:
        bounds = spec_bounds(parent)
        x = (bounds[0] + bounds[3]) * 0.5
        z = (bounds[2] + bounds[5]) * 0.5
        top = bounds[4]
        base = _cb(
            plan, f"{role_prefix}-seated-plinth",
            "structural_steel", group,
            x, top + 0.15, z,
            7.0 * scale, 0.60, 5.0 * scale,
            0.08, "secondary", layer=layer, outside=outside,
        )
        neck = plan.cylinder(
            f"{role_prefix}-tapered-neck",
            material, group,
            x, top + 2.25 * scale, z,
            1.20 * scale, 4.30 * scale,
            12 if lod == 0 else 8,
            top_radius=0.74 * scale,
            layer=layer, outside_playable=outside,
        )
        hood = _cb(
            plan, f"{role_prefix}-supported-rain-hood",
            "weathered_zinc", group,
            x, top + 4.33 * scale, z,
            3.4 * scale, 0.66 * scale, 3.4 * scale,
            0.08, "secondary", layer=layer, outside=outside,
        )
        plan.connect(
            parent["name"], base,
            axis="y", overlap_m=0.15,
            parent_face="top", child_face="bottom",
            note="Equipment plinth is seated into the parent roof.",
        )
        plan.connect(
            base, neck,
            axis="y", overlap_m=0.45,
            parent_face="top", child_face="bottom",
            note="Tapered process neck bears on its equipment plinth.",
        )
        plan.connect(
            neck, hood,
            axis="y", overlap_m=0.22,
            parent_face="top", child_face="bottom",
            note="Rain hood overlaps the supported process neck.",
        )

    stack_houses = specs_for("a22-i23-stackhouse-bridge-process-house")
    if stack_houses:
        add_supported_cap(
            stack_houses[0],
            group=STACKHOUSE_ID,
            role_prefix="a22-i28-stackhouse-mechanical-cap",
            material="rust",
            outside=False,
            layer="mid",
            scale=1.0 if lod < 2 else 0.82,
        )

    customs_houses = specs_for("a22-i23-customs-roof-service-house")
    customs_cap_count = 2 if lod == 0 else 1
    for parent in customs_houses[:customs_cap_count]:
        add_supported_cap(
            parent,
            group=CUSTOMS_ID,
            role_prefix="a22-i28-customs-mechanical-cap",
            material="rust",
            outside=False,
            layer="mid",
            scale=0.82 if lod < 2 else 0.68,
        )

    far_plants = (
        specs_for("a22-i23-far-port-tiered-roof-plant")
        + specs_for("a22-p0-central-layered-port-roof-plant")
    )
    far_cap_count = 2 if lod == 0 else 1 if lod == 1 else 0
    for parent in far_plants[:far_cap_count]:
        top = spec_bounds(parent)[4]
        x = float(parent["x"])
        z = float(parent["z"])
        neck = plan.cylinder(
            "a22-i28-far-port-supported-process-neck",
            "rust", parent["group"],
            x, top + 1.35, z,
            1.10, 2.90,
            10 if lod == 0 else 8,
            top_radius=0.68,
            layer="far", outside_playable=True,
        )
        hood = _cb(
            plan, "a22-i28-far-port-supported-process-hood",
            "weathered_zinc", parent["group"],
            x, top + 2.92, z,
            3.2, 0.52, 3.2,
            0.06, "secondary", layer="far", outside=True,
        )
        plan.connect(
            parent["name"], neck,
            axis="y", overlap_m=0.10,
            parent_face="top", child_face="bottom",
            note="Process neck is seated into the reduced roof plinth.",
        )
        plan.connect(
            neck, hood,
            axis="y", overlap_m=0.14,
            parent_face="top", child_face="bottom",
            note="Mechanical hood overlaps its tapered support.",
        )

    # Dark attachment bands make the warm occupied fixtures read as sources
    # rather than flat orange cards.
    active_canopies = specs_for("a22-i23-customs-loading-bay-canopy")
    canopy_count = 4 if lod == 0 else 2 if lod == 1 else 0
    for canopy in active_canopies[:canopy_count]:
        bounds = spec_bounds(canopy)
        x = float(canopy["x"])
        z = bounds[5] - 0.10
        shadow = _cb(
            plan, "a22-i28-customs-bay-attachment-shadow",
            "structural_steel", CUSTOMS_ID,
            x, bounds[1] - 0.08, z,
            13.8, 0.30, 0.36,
            0.05, "secondary", layer="mid",
        )
        fixture = _cb(
            plan, "a22-i28-customs-occupied-task-strip",
            "warm_glass", CUSTOMS_ID,
            x, bounds[1] - 0.26, z + 0.04,
            6.8, 0.18, 0.22,
            0.02, "equipment", layer="mid",
        )
        plan.connect(
            canopy["name"], shadow,
            axis="y", overlap_m=0.07,
            parent_face="bottom", child_face="top",
            note="Loading-bay shadow band keys into the canopy underside.",
        )
        plan.connect(
            shadow, fixture,
            axis="y", overlap_m=0.06,
            parent_face="bottom", child_face="top",
            note="Warm task strip is recessed into its dark fixture band.",
        )

    bridge_floors = specs_for("a22-i23-stackhouse-heavy-rack-bridge-floor")
    if bridge_floors:
        bridge_floor = bridge_floors[0]
        bounds = spec_bounds(bridge_floor)
        bridge_shadow = _cb(
            plan, "a22-i28-stackhouse-bridge-attachment-shadow",
            "structural_steel", STACKHOUSE_ID,
            63.0, bounds[1] - 0.10, bounds[5] - 0.12,
            76.0, 0.40, 0.46,
            0.06, "secondary", layer="mid",
        )
        plan.connect(
            bridge_floor["name"], bridge_shadow,
            axis="y", overlap_m=0.10,
            parent_face="bottom", child_face="top",
            note="Bridge underside shadow band overlaps the heavy deck.",
        )
        task_xs = (45.0, 75.0) if lod == 0 else (60.0,)
        for x in task_xs:
            task = _cb(
                plan, "a22-i28-stackhouse-occupied-task-strip",
                "warm_glass", STACKHOUSE_ID,
                x, bounds[1] - 0.34, bounds[5] - 0.02,
                10.0, 0.18, 0.24,
                0.02, "equipment", layer="mid",
            )
            plan.connect(
                bridge_shadow, task,
                axis="y", overlap_m=0.05,
                parent_face="bottom", child_face="top",
                note="Bridge task strip is recessed into the attachment band.",
            )

    quay_group = "souko-a22-primary-ship-side-rebuild"
    quay_land_x = math.cos(PRIMARY_QUAY_YAW)
    quay_land_z = math.sin(PRIMARY_QUAY_YAW)
    quay_wall = specs_for("a22-p0-primary-camera-heavy-quay-wall")[0]
    tidal_band = _structural_beam(
        plan, "a22-i28-quay-tidal-contact-band",
        quay_group,
        (
            primary_quay_edge_x(20.0) - quay_land_x * 5.85,
            0.14,
            20.0 - quay_land_z * 5.85,
        ),
        (
            primary_quay_edge_x(118.0) - quay_land_x * 5.85,
            0.14,
            118.0 - quay_land_z * 5.85,
        ),
        0.48, material="rust", layer="near", outside=True,
    )
    plan.connect(
        quay_wall["name"], tidal_band,
        axis="x", overlap_m=0.18,
        parent_face="water-side", child_face="land-side",
        note="Tidal stain band remains attached to the quay wall face.",
    )

    def add_upright_rope_coil(
        center_x: float,
        center_z: float,
        segments: int,
    ) -> None:
        radius = 1.12
        center_y = 2.18
        points = [
            (
                center_x + math.cos(-math.pi / 2 + math.tau * i / segments)
                * radius,
                center_y + math.sin(-math.pi / 2 + math.tau * i / segments)
                * radius,
                center_z,
            )
            for i in range(segments)
        ]
        for index in range(segments):
            plan.round_member(
                "a22-i28-quay-readable-coiled-mooring-rope",
                "pallet_wood", quay_group,
                points[index], points[(index + 1) % segments],
                0.06, 8 if lod == 0 else 6,
                layer="near", outside_playable=True,
            )
        plan.round_member(
            "a22-i28-quay-readable-coiled-mooring-rope-tie",
            "pallet_wood", quay_group,
            (center_x - radius * 0.62, center_y, center_z - 0.04),
            (center_x + radius * 0.62, center_y, center_z - 0.04),
            0.055, 8 if lod == 0 else 6,
            layer="near", outside_playable=True,
        )

    coil_zs = (42.0, 91.0) if lod == 0 else (62.0,) if lod == 1 else ()
    for axis_z in coil_zs:
        add_upright_rope_coil(
            primary_quay_edge_x(axis_z) + quay_land_x * 7.8,
            axis_z + quay_land_z * 7.8,
            8 if lod == 0 else 6,
        )

    pallet_axis_z = 67.0
    pallet_x = (
        primary_quay_edge_x(pallet_axis_z) + quay_land_x * 7.4
    )
    pallet_z = pallet_axis_z + quay_land_z * 7.4
    if lod < 2:
        pallet = _cb(
            plan, "a22-i28-quay-edge-grounded-pallet",
            "pallet_wood", quay_group,
            pallet_x, 1.20, pallet_z,
            5.2, 0.50, 4.0,
            0.05, "secondary", yaw=PRIMARY_QUAY_YAW,
            layer="near", outside=True,
        )
        tangent_x, tangent_z = -quay_land_z, quay_land_x
        crate_offsets = (-1.25, 1.25) if lod == 0 else (-0.65,)
        for index, offset in enumerate(crate_offsets):
            crate = _cb(
                plan, "a22-i28-quay-edge-loaded-service-crate",
                ("weathered_zinc", "rust")[index % 2],
                quay_group,
                pallet_x + tangent_x * offset,
                2.18,
                pallet_z + tangent_z * offset,
                2.2, 1.70, 2.5,
                0.06, "secondary", yaw=PRIMARY_QUAY_YAW,
                layer="near", outside=True,
            )
            plan.connect(
                pallet, crate,
                axis="y", overlap_m=0.05,
                parent_face="top", child_face="bottom",
                note="Loaded service crate bears on its dock pallet.",
            )

    barrel_axis_z = 96.0
    barrel_x = (
        primary_quay_edge_x(barrel_axis_z) + quay_land_x * 7.0
    )
    barrel_z = barrel_axis_z + quay_land_z * 7.0
    barrel_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index in range(barrel_count):
        offset = (index - (barrel_count - 1) * 0.5) * 1.45
        plan.cylinder(
            "a22-i28-quay-edge-grounded-service-barrel",
            ("rust", "weathered_zinc", "structural_steel")[index % 3],
            quay_group,
            barrel_x - quay_land_z * offset,
            1.05,
            barrel_z + quay_land_x * offset,
            0.66, 2.0,
            12 if lod == 0 else 8,
            top_radius=0.63,
            layer="near", outside_playable=True,
        )

    # Ship-side paint and runoff geometry follows the existing authored hull
    # envelope.  No hull, deck, bow or camera transform is moved.
    def camera_hull_x(z: float) -> float:
        fraction = max(0.0, min(1.0, (z - 34.0) / 40.0))
        beam = 10.5 + (5.0 - 10.5) * fraction
        return primary_ship_land_x(z) - beam

    near_hull = specs_for("a22-p0-primary-camera-ship-near-hull")[0]
    ship_bands = (
        (
            "a22-i28-ship-camera-side-waterline-contact",
            "rust", 0.72, 1.26,
        ),
        (
            "a22-i28-ship-camera-side-work-paint-band",
            "weathered_zinc", 3.62, 4.24,
        ),
        (
            "a22-i28-ship-camera-side-upper-sheer-band",
            "pale_concrete", 5.35, 6.16,
        ),
    )
    active_ship_bands = ship_bands if lod < 2 else (
        ship_bands[0], ship_bands[2],
    )
    for role, material, bottom_y, top_y in active_ship_bands:
        band = plan.panel(
            role, material, quay_group,
            (
                (camera_hull_x(35.0) - 0.16, bottom_y, 35.0),
                (camera_hull_x(35.0) - 0.16, top_y, 35.0),
                (camera_hull_x(70.0) - 0.16, top_y + 0.10, 70.0),
                (camera_hull_x(70.0) - 0.16, bottom_y + 0.08, 70.0),
            ),
            0.12, layer="near", outside_playable=True,
        )
        plan.connect(
            near_hull["name"], band,
            axis="x", overlap_m=0.12,
            parent_face="camera-side", child_face="hull-side",
            note="Ship finish band follows and overlaps the camera-side hull.",
        )

    runoff_zs = (41.0, 53.0, 65.0) if lod == 0 else (
        (45.0, 61.0) if lod == 1 else (56.0,)
    )
    for z in runoff_zs:
        runoff = plan.panel(
            "a22-i28-ship-camera-side-rust-runoff",
            "rust", quay_group,
            (
                (camera_hull_x(z) - 0.19, 1.62, z - 0.18),
                (camera_hull_x(z) - 0.19, 5.12, z - 0.18),
                (camera_hull_x(z) - 0.19, 5.12, z + 0.18),
                (camera_hull_x(z) - 0.19, 1.62, z + 0.18),
            ),
            0.10, layer="near", outside_playable=True,
        )
        plan.connect(
            near_hull["name"], runoff,
            axis="x", overlap_m=0.10,
            parent_face="camera-side", child_face="hull-side",
            note="Rust runoff strip remains attached to the hull plating.",
        )

    deck_shadow = _structural_beam(
        plan, "a22-i28-ship-camera-side-deck-attachment-shadow",
        quay_group,
        (camera_hull_x(34.0), 7.03, 34.0),
        (camera_hull_x(70.0), 7.14, 70.0),
        0.32, material="structural_steel",
        layer="near", outside=True,
    )
    plan.connect(
        near_hull["name"], deck_shadow,
        axis="y", overlap_m=0.10,
        parent_face="upper-edge", child_face="lower-edge",
        note="Deck shadow member follows the upper camera-side hull edge.",
    )


def _build_iteration29a_edge_occupation(plan: SpecPlan, lod: int) -> None:
    """Recompose three LOD0 edge pockets at readable dock-worker scale.

    Iteration-29A tests one visual hypothesis only: the reference gap is
    chiefly caused by underscaled, distributed near/mid dock occupation.
    Therefore the fixed camera, centre route, heroes, ship, water, lighting
    and every existing material stay frozen.  LOD1/2 also stay frozen until
    the fixed-camera macro read is accepted.

    Reviewed connection map:

    * quay wall -> camera-side fender -> hazard cap;
    * quay service road -> bollard / rope coil / work-light post -> lamp head;
    * quay service road -> near cargo pallet -> two crates, with three
      grounded barrels grouped beside it;
    * foreground loading slab -> opposite pallet -> two crates, plus three
      slab-seated barriers.
    """

    if lod != 0:
        return

    # Reclaim the dispersed iteration-28 dock pieces and the old camera-near
    # P0 cargo stack.  They are replaced below by three coherent clusters,
    # keeping the overall spec count effectively flat.
    dispersed_roles = {
        "a22-i28-quay-readable-coiled-mooring-rope",
        "a22-i28-quay-readable-coiled-mooring-rope-tie",
        "a22-i28-quay-edge-grounded-pallet",
        "a22-i28-quay-edge-loaded-service-crate",
        "a22-i28-quay-edge-grounded-service-barrel",
    }
    removed_names: set[str] = set()
    retained: list[dict[str, Any]] = []
    for spec in plan.specs:
        remove = spec["role"] in dispersed_roles
        if (
            spec["role"]
            in {
                "a22-p0-quay-grounded-cargo-pallet",
                "a22-p0-quay-staged-maintenance-crate",
            }
            and float(spec["z"]) > 100.0
        ):
            remove = True
        if spec["role"] == "a22-p0-quay-grounded-service-barrel":
            remove = True
        if remove:
            removed_names.add(spec["name"])
        else:
            retained.append(spec)
    plan.specs = retained
    plan.connections = [
        connection
        for connection in plan.connections
        if connection["parent"] not in removed_names
        and connection["child"] not in removed_names
    ]

    quay_group = "souko-a22-primary-ship-side-rebuild"
    loading_group = "souko-a22-iteration23-loading-clusters"
    quay_land_x = math.cos(PRIMARY_QUAY_YAW)
    quay_land_z = math.sin(PRIMARY_QUAY_YAW)
    quay_tangent_x, quay_tangent_z = -quay_land_z, quay_land_x
    quay_wall = next(
        spec for spec in plan.specs
        if spec["role"] == "a22-p0-primary-camera-heavy-quay-wall"
    )
    loading_slab = next(
        spec for spec in plan.specs
        if spec["role"] == "a22-i23-foreground-loading-slab"
    )

    # Cluster 1/3: a mid-distance mooring station.  The fender, bollard,
    # upright rope coil and work light read as four related worker-scale
    # objects instead of scattered detail.
    mid_axis_z = 65.0
    mid_edge_x = primary_quay_edge_x(mid_axis_z)
    mid_fender_x = mid_edge_x - quay_land_x * 3.15
    mid_fender_z = mid_axis_z - quay_land_z * 3.15
    fender = plan.cylinder(
        "a22-i29a-mid-quay-readable-fender",
        "structural_steel", quay_group,
        mid_fender_x, 1.62, mid_fender_z,
        1.25, 3.0, 14,
        top_radius=1.18,
        layer="near", outside_playable=True,
    )
    fender_cap = _cb(
        plan, "a22-i29a-mid-quay-fender-hazard-cap",
        "safety_orange", quay_group,
        mid_fender_x, 3.04, mid_fender_z,
        2.65, 0.38, 2.65,
        0.07, "secondary", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    plan.connect(
        quay_wall["name"], fender,
        axis="x", overlap_m=0.15,
        parent_face="water-side", child_face="land-side",
        note="Camera-side fender keys into the authored quay face.",
    )
    plan.connect(
        fender, fender_cap,
        axis="y", overlap_m=0.10,
        parent_face="top", child_face="bottom",
        note="Hazard cap overlaps the top of the quay fender.",
    )

    mid_land_x = mid_edge_x + quay_land_x * 6.2
    mid_land_z = mid_axis_z + quay_land_z * 6.2
    plan.cylinder(
        "a22-i29a-mid-quay-readable-bollard",
        "rust", quay_group,
        mid_land_x - quay_tangent_x * 2.1,
        1.10,
        mid_land_z - quay_tangent_z * 2.1,
        1.05, 2.0, 14,
        top_radius=0.86,
        layer="near", outside_playable=True,
    )
    rope_center_x = mid_land_x + quay_tangent_x * 1.35
    rope_center_z = mid_land_z + quay_tangent_z * 1.35
    rope_radius = 1.34
    rope_center_y = 1.55
    rope_points = [
        (
            rope_center_x
            + math.cos(-math.pi / 2 + math.tau * index / 10)
            * rope_radius,
            rope_center_y
            + math.sin(-math.pi / 2 + math.tau * index / 10)
            * rope_radius,
            rope_center_z,
        )
        for index in range(10)
    ]
    for index in range(10):
        plan.round_member(
            "a22-i29a-mid-quay-readable-rope-coil",
            "pallet_wood", quay_group,
            rope_points[index], rope_points[(index + 1) % 10],
            0.075, 8,
            layer="near", outside_playable=True,
        )
    plan.round_member(
        "a22-i29a-mid-quay-readable-rope-tie",
        "pallet_wood", quay_group,
        (
            rope_center_x - rope_radius * 0.65,
            rope_center_y,
            rope_center_z - 0.05,
        ),
        (
            rope_center_x + rope_radius * 0.65,
            rope_center_y,
            rope_center_z - 0.05,
        ),
        0.06, 8,
        layer="near", outside_playable=True,
    )
    lamp_x = mid_land_x + quay_tangent_x * 3.6
    lamp_z = mid_land_z + quay_tangent_z * 3.6
    lamp_post = plan.round_member(
        "a22-i29a-mid-quay-grounded-work-light-post",
        "structural_steel", quay_group,
        (lamp_x, 0.12, lamp_z), (lamp_x, 4.82, lamp_z),
        0.16, 10,
        layer="near", outside_playable=True,
    )
    lamp_head = _cb(
        plan, "a22-i29a-mid-quay-readable-work-light",
        "warm_glass", quay_group,
        lamp_x, 4.83, lamp_z,
        2.15, 0.82, 0.92,
        0.06, "secondary", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    plan.connect(
        lamp_post, lamp_head,
        axis="y", overlap_m=0.40,
        parent_face="top", child_face="centre",
        note="Readable work-light head overlaps its grounded post.",
    )

    # Cluster 2/3: camera-near cargo at the road edge.  Two side-by-side
    # crates and three large barrels replace the old vertical toy-like stack.
    near_axis_z = 105.0
    near_x = primary_quay_edge_x(near_axis_z) + quay_land_x * 7.2
    near_z = near_axis_z + quay_land_z * 7.2
    near_pallet = _cb(
        plan, "a22-i29a-near-quay-readable-cargo-pallet",
        "pallet_wood", quay_group,
        near_x, 0.39, near_z,
        5.4, 0.52, 4.3,
        0.06, "secondary", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    for index, offset in enumerate((-1.35, 1.35)):
        near_crate = _cb(
            plan, "a22-i29a-near-quay-loaded-service-crate",
            ("weathered_zinc", "rust")[index],
            quay_group,
            near_x + quay_tangent_x * offset,
            1.46,
            near_z + quay_tangent_z * offset,
            2.35, 1.92, 2.75,
            0.08, "secondary", yaw=PRIMARY_QUAY_YAW,
            layer="near", outside=True,
        )
        plan.connect(
            near_pallet, near_crate,
            axis="y", overlap_m=0.15,
            parent_face="top", child_face="bottom",
            note="Side-by-side service crate overlaps its cargo pallet.",
        )
    for index, offset in enumerate((-1.65, 0.0, 1.65)):
        plan.cylinder(
            "a22-i29a-near-quay-readable-service-barrel",
            ("rust", "weathered_zinc", "structural_steel")[index],
            quay_group,
            near_x + quay_land_x * 3.4 + quay_tangent_x * offset,
            1.16,
            near_z + quay_land_z * 3.4 + quay_tangent_z * offset,
            0.78, 2.15, 14,
            top_radius=0.74,
            layer="near", outside_playable=True,
        )

    # Cluster 3/3: opposite loading-edge cargo and barriers.  It is seated
    # entirely on the existing slab, leaving the central route untouched.
    opposite_x, opposite_z = -166.0, 136.8
    opposite_pallet = _cb(
        plan, "a22-i29a-opposite-readable-loading-pallet",
        "pallet_wood", loading_group,
        opposite_x, 0.94, opposite_z,
        5.4, 0.50, 4.2,
        0.06, "secondary", yaw=0.08, layer="near",
    )
    plan.connect(
        loading_slab["name"], opposite_pallet,
        axis="y", overlap_m=0.01,
        parent_face="top", child_face="bottom",
        note="Opposite loading pallet is seated into the existing slab.",
    )
    for index, offset in enumerate((-1.35, 1.35)):
        opposite_crate = _cb(
            plan, "a22-i29a-opposite-readable-loaded-crate",
            ("weathered_zinc", "rust")[index],
            loading_group,
            opposite_x + offset, 2.10, opposite_z,
            2.35, 1.92, 2.75,
            0.08, "secondary", yaw=0.08, layer="near",
        )
        plan.connect(
            opposite_pallet, opposite_crate,
            axis="y", overlap_m=0.05,
            parent_face="top", child_face="bottom",
            note="Opposite cargo crate overlaps its loading pallet.",
        )
    for index, offset in enumerate((-5.0, 0.0, 5.0)):
        barrier = _cb(
            plan, "a22-i29a-opposite-readable-loading-barrier",
            ("safety_orange", "pale_concrete", "safety_orange")[index],
            loading_group,
            opposite_x + offset, 1.32, 133.9,
            4.0, 1.25, 1.05,
            0.09, "secondary", yaw=0.08, layer="near",
        )
        plan.connect(
            loading_slab["name"], barrier,
            axis="y", overlap_m=0.005,
            parent_face="top", child_face="bottom",
            note="Loading barrier is seated into the foreground slab.",
        )

    # These are visual-edge occupations, never gameplay collision.
    for spec in plan.specs:
        if spec["role"].startswith("a22-i29a-"):
            spec["blocksGameplay"] = False


def _build_iteration29b_edge_massing(plan: SpecPlan, lod: int) -> None:
    """Scale two existing edge occupations into coherent worker-scale masses.

    Iteration-29B changes one thing only: the screen-space silhouette of the
    accepted Iteration-28 edge occupations.  The camera, route, landmarks,
    ship, water, materials, lighting and LOD1/2 remain untouched.

    Reviewed connection map:

    * service road -> quay platform -> two cargo bays and upright rope coil;
    * quay wall -> fender -> hazard cap, with a grounded bollard beside it;
    * loading slab -> two loaded pallets under the existing canopy.
    """

    if lod != 0:
        return

    # Remove only the accepted-28 distributed edge pieces, the camera-near
    # P0 cargo stack, and the four underscaled loading-shelter pallets.
    dispersed_roles = {
        "a22-i28-quay-readable-coiled-mooring-rope",
        "a22-i28-quay-readable-coiled-mooring-rope-tie",
        "a22-i28-quay-edge-grounded-pallet",
        "a22-i28-quay-edge-loaded-service-crate",
        "a22-i28-quay-edge-grounded-service-barrel",
        "a22-i23-foreground-grounded-pallet",
        "a22-i23-foreground-loaded-cargo",
    }
    removed_names: set[str] = set()
    retained: list[dict[str, Any]] = []
    for spec in plan.specs:
        remove = spec["role"] in dispersed_roles
        if (
            spec["role"]
            in {
                "a22-p0-quay-grounded-cargo-pallet",
                "a22-p0-quay-staged-maintenance-crate",
            }
            and float(spec["z"]) > 100.0
        ):
            remove = True
        if spec["role"] == "a22-p0-quay-grounded-service-barrel":
            remove = True
        if remove:
            removed_names.add(spec["name"])
        else:
            retained.append(spec)
    plan.specs = retained
    plan.connections = [
        connection
        for connection in plan.connections
        if connection["parent"] not in removed_names
        and connection["child"] not in removed_names
    ]

    quay_group = "souko-a22-primary-ship-side-rebuild"
    loading_group = "souko-a22-iteration23-loading-clusters"
    quay_land_x = math.cos(PRIMARY_QUAY_YAW)
    quay_land_z = math.sin(PRIMARY_QUAY_YAW)
    quay_tangent_x, quay_tangent_z = -quay_land_z, quay_land_x
    service_road = next(
        spec for spec in plan.specs
        if spec["role"] == "a22-foundation-wet-diagonal-bonded-service-road"
    )
    quay_wall = next(
        spec for spec in plan.specs
        if spec["role"] == "a22-p0-primary-camera-heavy-quay-wall"
    )
    loading_slab = next(
        spec for spec in plan.specs
        if spec["role"] == "a22-i23-foreground-loading-slab"
    )

    # Mass 1/2: one compact quay mooring/service occupation.  The cargo bays,
    # coil, bollard and fender share one 13 m frontage instead of reading as
    # isolated dots along the entire quay.
    service_axis_z = 104.0
    service_x = (
        primary_quay_edge_x(service_axis_z) + quay_land_x * 7.2
    )
    service_z = service_axis_z + quay_land_z * 7.2
    platform = _cb(
        plan, "a22-i29b-quay-service-platform",
        "pallet_wood", quay_group,
        service_x, 0.44, service_z,
        7.6, 0.62, 13.0,
        0.08, "secondary", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    plan.connect(
        service_road["name"], platform,
        axis="y", overlap_m=0.01,
        parent_face="top", child_face="bottom",
        note="Quay service platform seats into the wet bonded service road.",
    )

    for index, (tangent_offset, height) in enumerate(
        ((-2.5, 4.6), (1.4, 3.8))
    ):
        cargo = _cb(
            plan, "a22-i29b-quay-service-cargo-bay",
            ("weathered_zinc", "rust")[index],
            quay_group,
            service_x + quay_tangent_x * tangent_offset,
            0.67 + height * 0.5,
            service_z + quay_tangent_z * tangent_offset,
            6.4, height, 4.5,
            0.10, "secondary", yaw=PRIMARY_QUAY_YAW,
            layer="near", outside=True,
        )
        plan.connect(
            platform, cargo,
            axis="y", overlap_m=0.08,
            parent_face="top", child_face="bottom",
            note="Large service cargo bay overlaps the common quay platform.",
        )

    coil_center_x = service_x + quay_tangent_x * 4.65
    coil_center_z = service_z + quay_tangent_z * 4.65
    coil_radius = 1.90
    coil_center_y = 2.57
    coil_points = [
        (
            coil_center_x
            + quay_land_x
            * math.cos(-math.pi / 2 + math.tau * index / 10)
            * coil_radius,
            coil_center_y
            + math.sin(-math.pi / 2 + math.tau * index / 10)
            * coil_radius,
            coil_center_z
            + quay_land_z
            * math.cos(-math.pi / 2 + math.tau * index / 10)
            * coil_radius,
        )
        for index in range(10)
    ]
    coil_members: list[str] = []
    for index in range(10):
        coil_members.append(
            plan.round_member(
                "a22-i29b-quay-service-mooring-coil",
                "pallet_wood", quay_group,
                coil_points[index], coil_points[(index + 1) % 10],
                0.12, 10,
                layer="near", outside_playable=True,
            )
        )
    plan.connect(
        platform, coil_members[0],
        axis="y", overlap_m=0.08,
        parent_face="top", child_face="lower-arc",
        note="Large upright mooring coil bears on the common service platform.",
    )
    plan.round_member(
        "a22-i29b-quay-service-mooring-coil-tie",
        "pallet_wood", quay_group,
        (
            coil_center_x - quay_land_x * coil_radius * 0.68,
            coil_center_y,
            coil_center_z - quay_land_z * coil_radius * 0.68,
        ),
        (
            coil_center_x + quay_land_x * coil_radius * 0.68,
            coil_center_y,
            coil_center_z + quay_land_z * coil_radius * 0.68,
        ),
        0.09, 10,
        layer="near", outside_playable=True,
    )

    fender_x = (
        primary_quay_edge_x(service_axis_z) - quay_land_x * 3.25
    )
    fender_z = service_axis_z - quay_land_z * 3.25
    fender = plan.cylinder(
        "a22-i29b-quay-cluster-fender",
        "structural_steel", quay_group,
        fender_x, -0.55, fender_z,
        1.55, 3.8, 16,
        top_radius=1.42,
        layer="near", outside_playable=True,
    )
    fender_cap = _cb(
        plan, "a22-i29b-quay-cluster-fender-cap",
        "safety_orange", quay_group,
        fender_x, 1.14, fender_z,
        3.4, 0.55, 3.8,
        0.07, "secondary", yaw=PRIMARY_QUAY_YAW,
        layer="near", outside=True,
    )
    plan.connect(
        quay_wall["name"], fender,
        axis="x", overlap_m=0.18,
        parent_face="water-side", child_face="land-side",
        note="Readable cluster fender keys into the authored quay wall.",
    )
    plan.connect(
        fender, fender_cap,
        axis="y", overlap_m=0.20,
        parent_face="top", child_face="bottom",
        note="Hazard cap overlaps the readable fender top.",
    )

    bollard_x = (
        service_x
        - quay_land_x * 2.3
        - quay_tangent_x * 4.8
    )
    bollard_z = (
        service_z
        - quay_land_z * 2.3
        - quay_tangent_z * 4.8
    )
    bollard = plan.cylinder(
        "a22-i29b-quay-cluster-bollard",
        "rust", quay_group,
        bollard_x, 1.53, bollard_z,
        1.25, 2.8, 16,
        top_radius=1.55,
        layer="near", outside_playable=True,
    )
    plan.connect(
        service_road["name"], bollard,
        axis="y", overlap_m=0.01,
        parent_face="top", child_face="bottom",
        note="Large service bollard is grounded into the bonded quay road.",
    )

    # Mass 2/2: two broad loaded pallets form one loading-shelter occupation.
    # Both stay under the accepted canopy and leave its worker and forklift
    # silhouettes visible as human-scale references.
    loading_bays = (
        (-167.0, 142.5, 7.0, 5.2, 6.2, 4.8, 4.4, "weathered_zinc"),
        (-158.0, 145.2, 6.0, 4.6, 5.4, 3.8, 4.0, "rust"),
    )
    for (
        bay_x, bay_z, pallet_w, pallet_d,
        cargo_w, cargo_h, cargo_d, material,
    ) in loading_bays:
        pallet = _cb(
            plan, "a22-i29b-loading-shelter-pallet",
            "pallet_wood", loading_group,
            bay_x, 1.015, bay_z,
            pallet_w, 0.65, pallet_d,
            0.08, "secondary", yaw=0.08, layer="near",
        )
        plan.connect(
            loading_slab["name"], pallet,
            axis="y", overlap_m=0.01,
            parent_face="top", child_face="bottom",
            note="Broad loading pallet seats into the existing shelter slab.",
        )
        cargo = _cb(
            plan, "a22-i29b-loading-shelter-cargo-mass",
            material, loading_group,
            bay_x, 1.28 + cargo_h * 0.5, bay_z,
            cargo_w, cargo_h, cargo_d,
            0.10, "secondary", yaw=0.08, layer="near",
        )
        plan.connect(
            pallet, cargo,
            axis="y", overlap_m=0.06,
            parent_face="top", child_face="bottom",
            note="Shelter cargo mass overlaps its broad supporting pallet.",
        )

    for spec in plan.specs:
        if spec["role"].startswith("a22-i29b-"):
            spec["blocksGameplay"] = False


def _build_iteration29c_continuous_customs_hall(
    plan: SpecPlan,
    lod: int,
) -> None:
    """Replace only Amakado Customs Terminal with one connected macro hall.

    Iteration-29C starts from the accepted Iteration-28 plan after its triangle
    detail pass.  Every Customs-group spec is then replaced, so the camera,
    Stackhouse, inter-hero bridge, crane, ship, water, route, materials,
    lighting and far port remain byte-identical in plan data.

    Reviewed connection map (all authored overlaps are at least 0.20 m):

    * hall foundation -> side shoulders / deep-frame legs;
    * deep-frame legs -> continuous front/rear spines and transverse ties;
    * longitudinal low/ridge/valley bearers -> full-depth sawtooth roof;
    * hall foundation -> integrated control core -> cab -> crown/radar/mast;
    * inner hall shoulder -> tower transfer deck -> bridge abutment
      -> frozen inter-hero bridge floor.

    This is deliberately silhouette-level construction.  There are no facade
    decals, repeated trims, props or route-edge additions in this pass.
    """

    removed_names = {
        spec["name"]
        for spec in plan.specs
        if spec["group"] == CUSTOMS_ID
    }
    plan.specs = [
        spec for spec in plan.specs
        if spec["name"] not in removed_names
    ]
    plan.connections = [
        connection
        for connection in plan.connections
        if connection["parent"] not in removed_names
        and connection["child"] not in removed_names
    ]

    group = CUSTOMS_ID
    x_edges = (-130.0, -108.5, -87.0, -65.5, -44.0)
    hall_front = -18.0
    hall_back = -126.0
    hall_centre_x = (x_edges[0] + x_edges[-1]) * 0.5
    hall_centre_z = (hall_front + hall_back) * 0.5

    foundation = _cb(
        plan, "a22-i29c-customs-continuous-hall-foundation",
        "old_concrete", group,
        hall_centre_x, 1.5, hall_centre_z,
        88.0, 3.0, 112.0,
        0.20, "hero", layer="mid",
    )
    side_shoulders: list[str] = []
    for side_index, x in enumerate((-128.0, -46.0)):
        shoulder_y = 15.4 if side_index == 0 else 18.4
        shoulder_height = 25.2 if side_index == 0 else 31.2
        shoulder = _cb(
            plan, "a22-i29c-customs-continuous-side-shoulder",
            "pale_concrete" if side_index == 0 else "old_concrete",
            group,
            x, shoulder_y, hall_centre_z,
            6.0, shoulder_height, 108.0,
            0.22, "hero", layer="mid",
        )
        side_shoulders.append(shoulder)
        plan.connect(
            foundation, shoulder,
            axis="y", overlap_m=0.20,
            parent_face="top", child_face="bottom",
            note=(
                "Iteration29-C: continuous hall shoulder is keyed into "
                "the common foundation."
            ),
        )

    front_spine = _cb(
        plan, "a22-i29c-customs-continuous-front-spine",
        "pale_concrete", group,
        hall_centre_x, 27.0, -20.0,
        88.0, 4.0, 8.0,
        0.20, "hero", layer="mid",
    )
    rear_spine = _cb(
        plan, "a22-i29c-customs-continuous-rear-spine",
        "old_concrete", group,
        hall_centre_x, 27.0, -124.0,
        88.0, 4.0, 8.0,
        0.20, "hero", layer="mid",
    )

    frame_zs = (
        (-20.0, -41.0, -62.0, -83.0, -104.0, -124.0)
        if lod == 0
        else (-20.0, -55.0, -90.0, -124.0)
        if lod == 1
        else (-20.0, -72.0, -124.0)
    )
    frame_ties: dict[float, str] = {}
    for frame_z in frame_zs:
        leg_names: list[str] = []
        for x in x_edges:
            leg = _cb(
                plan, "a22-i29c-customs-deep-bay-frame-leg",
                "old_concrete", group,
                x, 15.0, frame_z,
                3.4, 24.4, 3.4,
                0.18, "hero", layer="mid",
            )
            leg_names.append(leg)
            plan.connect(
                foundation, leg,
                axis="y", overlap_m=0.20,
                parent_face="top", child_face="bottom",
                note=(
                    "Iteration29-C: deep-bay frame leg is seated in "
                    "the continuous hall foundation."
                ),
            )
        if frame_z == frame_zs[0]:
            tie = front_spine
        elif frame_z == frame_zs[-1]:
            tie = rear_spine
        else:
            tie = _structural_beam(
                plan, "a22-i29c-customs-continuous-transverse-tie",
                group,
                (x_edges[0], 27.0, frame_z),
                (x_edges[-1], 27.0, frame_z),
                1.40, material="structural_steel", layer="mid",
            )
        frame_ties[frame_z] = tie
        for leg in leg_names:
            plan.connect(
                leg, tie,
                axis="y", overlap_m=0.40,
                parent_face="top", child_face="bottom",
                note=(
                    "Iteration29-C: frame leg overlaps its continuous "
                    "transverse hall tie."
                ),
            )

        for x0, x1 in zip(x_edges[:-1], x_edges[1:]):
            ridge_x = x1 - 4.5
            _structural_beam(
                plan, "a22-i29c-customs-sawtooth-frame-rafter",
                group,
                (x0 + 0.4, 27.0, frame_z),
                (ridge_x, 47.0, frame_z),
                0.82, material="rust", layer="mid",
            )
            _structural_beam(
                plan, "a22-i29c-customs-sawtooth-frame-drop",
                group,
                (ridge_x, 27.0, frame_z),
                (ridge_x, 47.0, frame_z),
                0.72, material="structural_steel", layer="mid",
            )
            _structural_beam(
                plan, "a22-i29c-customs-sawtooth-frame-valley",
                group,
                (ridge_x, 27.0, frame_z),
                (x1 - 0.4, 27.0, frame_z),
                0.72, material="structural_steel", layer="mid",
            )

    for bay_index, (x0, x1) in enumerate(zip(x_edges[:-1], x_edges[1:])):
        ridge_x = x1 - 4.5
        low_bearer = _structural_beam(
            plan, "a22-i29c-customs-longitudinal-low-bearer",
            group,
            (x0 + 0.4, 27.0, hall_front),
            (x0 + 0.4, 27.0, hall_back),
            1.20, material="structural_steel", layer="mid",
        )
        ridge_bearer = _structural_beam(
            plan, "a22-i29c-customs-longitudinal-ridge-bearer",
            group,
            (ridge_x, 47.0, hall_front),
            (ridge_x, 47.0, hall_back),
            1.20, material="rust", layer="mid",
        )
        valley_bearer = _structural_beam(
            plan, "a22-i29c-customs-longitudinal-valley-bearer",
            group,
            (ridge_x, 27.0, hall_front),
            (ridge_x, 27.0, hall_back),
            1.20, material="structural_steel", layer="mid",
        )
        end_bearer = _structural_beam(
            plan, "a22-i29c-customs-longitudinal-end-bearer",
            group,
            (x1 - 0.4, 27.0, hall_front),
            (x1 - 0.4, 27.0, hall_back),
            1.20, material="structural_steel", layer="mid",
        )

        slope_roof = plan.panel(
            "a22-i29c-customs-full-depth-sawtooth-roof",
            "weathered_zinc", group,
            (
                (x0 + 0.4, 27.0, hall_front),
                (ridge_x, 47.0, hall_front),
                (ridge_x, 47.0, hall_back),
                (x0 + 0.4, 27.0, hall_back),
            ),
            0.70, layer="mid",
        )
        valley_roof = plan.panel(
            "a22-i29c-customs-full-depth-sawtooth-roof",
            "weathered_zinc", group,
            (
                (ridge_x, 27.0, hall_front),
                (x1 - 0.4, 27.0, hall_front),
                (x1 - 0.4, 27.0, hall_back),
                (ridge_x, 27.0, hall_back),
            ),
            0.70, layer="mid",
        )
        roof_glass = plan.panel(
            "a22-i29c-customs-full-depth-sawtooth-glazing",
            "dirty_glass", group,
            (
                (ridge_x, 27.2, hall_front),
                (ridge_x, 46.7, hall_front),
                (ridge_x, 46.7, hall_back),
                (ridge_x, 27.2, hall_back),
            ),
            0.36, layer="mid",
        )
        plan.panel(
            "a22-i29c-customs-full-depth-sawtooth-warm-backing",
            "warm_glass", group,
            (
                (ridge_x + 0.9, 28.0, hall_front + 1.0),
                (ridge_x + 0.9, 45.8, hall_front + 1.0),
                (ridge_x + 0.9, 45.8, hall_back - 1.0),
                (ridge_x + 0.9, 28.0, hall_back - 1.0),
            ),
            0.28, layer="mid",
        )
        plan.panel(
            "a22-i29c-customs-monumental-front-gable",
            "pale_concrete" if bay_index % 2 == 0 else "old_concrete",
            group,
            (
                (x0 + 0.4, 27.0, hall_front + 0.35),
                (ridge_x, 47.0, hall_front + 0.35),
                (ridge_x, 27.0, hall_front + 0.35),
            ),
            0.62, layer="mid",
        )
        for bearer, roof in (
            (low_bearer, slope_roof),
            (ridge_bearer, slope_roof),
            (valley_bearer, valley_roof),
            (end_bearer, valley_roof),
            (ridge_bearer, roof_glass),
            (valley_bearer, roof_glass),
        ):
            plan.connect(
                bearer, roof,
                axis="y", overlap_m=0.20,
                parent_face="bearing-line", child_face="roof-edge",
                note=(
                    "Iteration29-C: full-depth sawtooth skin bears on "
                    "its continuous longitudinal steel."
                ),
            )

        bay_centre = (x0 + x1) * 0.5
        portal_glass = _cb(
            plan, "a22-i29c-customs-deep-bay-portal",
            "dirty_glass", group,
            bay_centre, 14.0, -23.8,
            15.2, 22.4, 0.80,
            0.08, "secondary", layer="mid",
        )
        warm_depth = _cb(
            plan, "a22-i29c-customs-deep-bay-warm-depth",
            "warm_glass", group,
            bay_centre, 12.8, -35.0,
            13.0, 20.0, 1.0,
            0.08, "secondary", layer="mid",
        )
        plan.connect(
            front_spine, portal_glass,
            axis="y", overlap_m=0.20,
            parent_face="bottom", child_face="top",
            note=(
                "Iteration29-C: deep loading portal keys into the "
                "continuous front spine."
            ),
        )
        plan.connect(
            foundation, warm_depth,
            axis="y", overlap_m=0.20,
            parent_face="top", child_face="bottom",
            note=(
                "Iteration29-C: warm occupied bay is grounded behind "
                "its deep portal."
            ),
        )
        for machine_z in (-46.0, -84.0):
            machine = _cb(
                plan, "a22-i29c-customs-deep-machine-line",
                "structural_steel" if machine_z > -60.0 else "rust",
                group,
                bay_centre, 6.8, machine_z,
                12.0, 8.0, 12.0,
                0.10, "secondary", layer="mid",
            )
            plan.connect(
                foundation, machine,
                axis="y", overlap_m=0.20,
                parent_face="top", child_face="bottom",
                note=(
                    "Iteration29-C: macro machine line is grounded in "
                    "the common hall slab."
                ),
            )
        conveyor = _cb(
            plan, "a22-i29c-customs-deep-conveyor-bed",
            "structural_steel", group,
            bay_centre, 4.0, -72.0,
            8.5, 2.4, 72.0,
            0.10, "secondary", layer="mid",
        )
        plan.connect(
            foundation, conveyor,
            axis="y", overlap_m=0.20,
            parent_face="top", child_face="bottom",
            note=(
                "Iteration29-C: deep conveyor bed is seated in the "
                "continuous hall slab."
            ),
        )

    # The control core is inside the hall envelope, not a detached tower prop.
    tower_core = _cb(
        plan, "a22-i29c-customs-integrated-control-core",
        "old_concrete", group,
        -52.0, 28.8, -58.0,
        22.0, 52.0, 28.0,
        0.22, "hero", layer="mid",
    )
    plan.connect(
        foundation, tower_core,
        axis="y", overlap_m=0.20,
        parent_face="top", child_face="bottom",
        note=(
            "Iteration29-C: control core grows directly from the "
            "continuous hall foundation."
        ),
    )
    for x in (-62.0, -44.0):
        for z in (-70.0, -46.0):
            leg = _structural_beam(
                plan, "a22-i29c-customs-integrated-tower-leg",
                group,
                (x, 2.8, z), (x, 70.0, z),
                1.20, material="structural_steel", layer="mid",
            )
            plan.connect(
                foundation, leg,
                axis="y", overlap_m=0.20,
                parent_face="top", child_face="bottom",
                note=(
                    "Iteration29-C: integrated tower leg is seated in "
                    "the shared hall foundation."
                ),
            )

    tower_cab = _cb(
        plan, "a22-i29c-customs-integrated-control-cab",
        "weathered_zinc", group,
        -52.0, 60.0, -58.0,
        28.0, 14.0, 32.0,
        0.20, "hero", layer="mid",
    )
    tower_crown = _cb(
        plan, "a22-i29c-customs-integrated-control-crown",
        "pale_concrete", group,
        -52.0, 68.5, -58.0,
        32.0, 3.5, 36.0,
        0.20, "hero", layer="mid",
    )
    plan.connect(
        tower_core, tower_cab,
        axis="y", overlap_m=0.80,
        parent_face="top", child_face="bottom",
        note=(
            "Iteration29-C: occupied control cab overlaps the hall-bound "
            "tower core."
        ),
    )
    plan.connect(
        tower_cab, tower_crown,
        axis="y", overlap_m=0.25,
        parent_face="top", child_face="bottom",
        note=(
            "Iteration29-C: control crown bears on the integrated cab."
        ),
    )
    for role, corners, warm_corners in (
        (
            "a22-i29c-customs-integrated-control-glazing",
            (
                (-62.0, 56.5, -41.8),
                (-42.0, 56.5, -41.8),
                (-42.0, 64.5, -41.8),
                (-62.0, 64.5, -41.8),
            ),
            (
                (-61.0, 57.0, -42.6),
                (-43.0, 57.0, -42.6),
                (-43.0, 64.0, -42.6),
                (-61.0, 64.0, -42.6),
            ),
        ),
        (
            "a22-i29c-customs-integrated-control-glazing",
            (
                (-66.2, 56.5, -69.0),
                (-66.2, 56.5, -47.0),
                (-66.2, 64.5, -47.0),
                (-66.2, 64.5, -69.0),
            ),
            (
                (-65.4, 57.0, -68.0),
                (-65.4, 57.0, -48.0),
                (-65.4, 64.0, -48.0),
                (-65.4, 64.0, -68.0),
            ),
        ),
    ):
        plan.panel(
            role, "dirty_glass", group,
            corners, 0.42, layer="mid",
        )
        plan.panel(
            "a22-i29c-customs-integrated-control-warm-occupancy",
            "warm_glass", group,
            warm_corners, 0.30, layer="mid",
        )

    radar = plan.cylinder(
        "a22-i29c-customs-integrated-radar-drum",
        "structural_steel", group,
        -52.0, 74.0, -58.0,
        4.8, 8.0, 16 if lod == 0 else 10,
        top_radius=3.6, layer="mid",
    )
    mast = plan.round_member(
        "a22-i29c-customs-integrated-control-mast",
        "structural_steel", group,
        (-52.0, 77.5, -58.0),
        (-52.0, 94.0, -58.0),
        0.50, 12 if lod == 0 else 8,
        layer="mid",
    )
    plan.connect(
        tower_crown, radar,
        axis="y", overlap_m=0.25,
        parent_face="top", child_face="bottom",
        note=(
            "Iteration29-C: radar drum is seated on the integrated crown."
        ),
    )
    plan.connect(
        radar, mast,
        axis="y", overlap_m=0.50,
        parent_face="top", child_face="bottom",
        note=(
            "Iteration29-C: control mast overlaps the radar support drum."
        ),
    )

    transfer_deck = _cb(
        plan, "a22-i29c-customs-tower-hall-transfer-deck",
        "weathered_zinc", group,
        -58.0, 31.0, -50.0,
        34.0, 2.5, 40.0,
        0.16, "hero", layer="mid",
    )
    bridge_link = _cb(
        plan, "a22-i29c-customs-interhero-bridge-abutment",
        "structural_steel", group,
        -33.0, 31.0, -34.0,
        24.0, 2.5, 12.0,
        0.16, "hero", layer="mid",
    )
    bridge_floor = next(
        spec for spec in plan.specs
        if spec["role"] == "a22-interhero-occupied-bridge-floor"
    )
    plan.connect(
        side_shoulders[1], transfer_deck,
        axis="x", overlap_m=0.50,
        parent_face="inner", child_face="outer",
        note=(
            "Iteration29-C: transfer deck overlaps the inner hall shoulder."
        ),
    )
    plan.connect(
        tower_core, transfer_deck,
        axis="y", overlap_m=0.50,
        parent_face="core", child_face="deck",
        note=(
            "Iteration29-C: tower core and hall transfer deck interpenetrate "
            "as one structural knuckle."
        ),
    )
    plan.connect(
        transfer_deck, bridge_link,
        axis="x", overlap_m=0.50,
        parent_face="inner", child_face="outer",
        note=(
            "Iteration29-C: hall transfer deck overlaps its bridge abutment."
        ),
    )
    plan.connect(
        bridge_link, bridge_floor["name"],
        axis="x", overlap_m=0.25,
        parent_face="route-side", child_face="terminal-end",
        note=(
            "Iteration29-C: Customs abutment keys into the frozen inter-hero "
            "bridge floor."
        ),
    )

    for spec in plan.specs:
        if spec["role"].startswith("a22-i29c-customs-"):
            spec["blocksGameplay"] = False


def _add_triangle_budget_detail(plan: SpecPlan, lod: int) -> None:
    """Add attached utility runs until each evaluated mesh enters its LOD band.

    Every member is an endpoint-driven round pipe placed on a process-core face,
    rack line or machine-hall service wall.  No free-floating boxes are used.
    """
    targets = {0: 182_000, 1: 61_000, 2: 17_000}
    core_specs = (
        (48.0, 93.0, 18.0, 32.0, 20.0),
        (68.0, 101.0, 13.0, 56.0, 16.0),
        (96.0, 90.0, 17.0, 43.0, 19.0),
        (119.0, 102.0, 16.0, 62.0, 17.0),
    )
    segments = 16 if lod == 0 else 12 if lod == 1 else 8
    index = 0
    while sum(estimated_triangles(spec) for spec in plan.specs) < targets[lod]:
        if index % 2 == 0:
            core_x, core_z, width, height, depth = core_specs[(index // 2) % 4]
            lane = (index // 8) % 11
            face_side = -1 if (index // 88) % 2 == 0 else 1
            x = core_x - width * 0.42 + lane * (width * 0.84 / 10)
            z = core_z + face_side * (depth * 0.505)
            start_y = 3.0 + ((index // 176) % 12) * 4.2
            end_y = min(height + 1.5, start_y + 3.6)
            if end_y - start_y < 0.7:
                start_y = max(2.0, height - 5.0)
                end_y = height - 0.6
            plan.pipe(
                "a22-stackhouse-attached-utility-run",
                "rust" if lane % 4 == 0 else "structural_steel",
                STACKHOUSE_ID,
                (x, start_y, z), (x, end_y, z),
                0.02, segments, layer="mid",
            )
        else:
            bay = (index // 2) % 4
            lane = (index // 8) % 9
            x = -102.0 + bay * 22.5 + lane * 0.62
            y = 11.0 + ((index // 72) % 6) * 1.8
            start_z = -34.0 - ((index // 432) % 7) * 9.5
            end_z = max(-103.0, start_z - 8.0)
            plan.pipe(
                "a22-customs-attached-service-conduit",
                "safety_orange" if lane % 5 == 0 else "structural_steel",
                CUSTOMS_ID,
                (x, y, start_z), (x, y, end_z),
                0.02, segments, layer="mid",
            )
        index += 1
        if index > 5200:
            raise RuntimeError("triangle target filler runaway")


def _build_iteration28_baseline(lod: int) -> SpecPlan:
    """Recreate the accepted Iteration-28 plan before any later hypothesis."""

    if lod not in LOD_API:
        raise ValueError(f"unsupported LOD: {lod}")
    plan = SpecPlan(lod)
    _copy_environment_base(plan, lod)
    _build_stackhouse(plan, lod)
    _build_customs(plan, lod)
    _build_hero_finish_pass(plan, lod)
    _build_independent_p0_mass_rebuild(plan, lod)
    _build_interlocking_gantries(plan, lod)
    _build_checkpoint(plan, lod)
    _build_working_route(plan, lod)
    _build_foreground_work_clusters(plan, lod)
    _build_ship_and_port(plan, lod)
    _build_secondary_port_city(plan, lod)
    _build_iteration23_fixed_frame_rebuild(plan, lod)
    _build_iteration28_material_dock_finish(plan, lod)
    _add_triangle_budget_detail(plan, lod)
    return plan


def build_plan(lod: int = 0) -> SpecPlan:
    plan = _build_iteration28_baseline(lod)
    _build_iteration29c_continuous_customs_hall(plan, lod)
    validate_plan(plan)
    return plan


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


def route_intrusions(plan: SpecPlan) -> list[dict[str, Any]]:
    intrusions: list[dict[str, Any]] = []
    for spec in plan.specs:
        if not spec["blocksGameplay"] or spec["outsidePlayable"]:
            continue
        bounds = spec_bounds(spec)
        for road in CANONICAL_ROADS:
            road = road["bounds"]
            if (
                bounds[0] < road["maxX"] and bounds[3] > road["minX"]
                and bounds[2] < road["maxZ"] and bounds[5] > road["minZ"]
            ):
                intrusions.append({"spec": spec["name"]})
    return intrusions


def shore_route_intrusions(
    plan: SpecPlan,
    clearance_m: float = 2.0,
) -> list[dict[str, Any]]:
    """Audit visual water and shore AABBs even when marked outside-playable."""

    intrusions: list[dict[str, Any]] = []
    for spec in plan.specs:
        if (
            spec["material"] != "sea_water"
            and spec["role"] not in PRIMARY_SHORE_ROLES
        ):
            continue
        bounds = spec_bounds(spec)
        for road_record in CANONICAL_ROADS:
            road = road_record["bounds"]
            if (
                bounds[0] < road["maxX"] + clearance_m
                and bounds[3] > road["minX"] - clearance_m
                and bounds[2] < road["maxZ"] + clearance_m
                and bounds[5] > road["minZ"] - clearance_m
            ):
                intrusions.append({
                    "spec": spec["name"],
                    "role": spec["role"],
                    "road": road_record["id"],
                })
    return intrusions


def camera_containment_hits(
    plan: SpecPlan,
    view: Mapping[str, Any],
    *,
    clearance_m: float = 0.10,
) -> list[dict[str, Any]]:
    eye = tuple(float(value) for value in view["eye"])
    hits = []
    for spec in plan.specs:
        bounds = spec_bounds(spec)
        if all(
            bounds[index] - clearance_m
            <= eye[index]
            <= bounds[index + 3] + clearance_m
            for index in range(3)
        ):
            hits.append({"name": spec["name"], "role": spec["role"]})
    return hits


def camera_horizontal_ndc(
    view: Mapping[str, Any],
    point: Sequence[float],
) -> float:
    """Return signed horizontal NDC for a runtime-space point.

    This is a deterministic framing audit, not a visibility/occlusion claim.
    Values within [-1, 1] are inside the horizontal camera gate.
    """

    eye = tuple(float(value) for value in view["eye"])
    target = tuple(float(value) for value in view["target"])
    forward = _v_norm(_v_sub(target, eye))
    right = _v_norm((forward[2], 0.0, -forward[0]))
    camera_to_point = _v_sub(
        tuple(float(value) for value in point),
        eye,
    )
    depth = _v_dot(camera_to_point, forward)
    if depth <= 1e-6:
        raise ValueError("projection point is behind the camera")
    side = _v_dot(camera_to_point, right)
    lens = float(view["lensMm"])
    sensor_width = float(view.get("sensorWidthMm", 36.0))
    tangent_half_fov = sensor_width / (2.0 * lens)
    return side / depth / tangent_half_fov


def camera_ndc(
    view: Mapping[str, Any],
    point: Sequence[float],
    *,
    aspect_ratio: float = 16.0 / 9.0,
) -> tuple[float, float]:
    """Return horizontal/vertical NDC for a runtime-space point."""

    if aspect_ratio <= 0.0:
        raise ValueError("aspect ratio must be positive")
    eye = tuple(float(value) for value in view["eye"])
    target = tuple(float(value) for value in view["target"])
    forward = _v_norm(_v_sub(target, eye))
    right = _v_norm((forward[2], 0.0, -forward[0]))
    up = _v_norm(_v_cross(forward, right))
    camera_to_point = _v_sub(
        tuple(float(value) for value in point),
        eye,
    )
    depth = _v_dot(camera_to_point, forward)
    if depth <= 1e-6:
        raise ValueError("projection point is behind the camera")
    lens = float(view["lensMm"])
    sensor_width = float(view.get("sensorWidthMm", 36.0))
    horizontal_tangent = sensor_width / (2.0 * lens)
    vertical_tangent = (
        sensor_width / aspect_ratio / (2.0 * lens)
    )
    return (
        _v_dot(camera_to_point, right) / depth / horizontal_tangent,
        _v_dot(camera_to_point, up) / depth / vertical_tangent,
    )


def validate_plan(plan: SpecPlan) -> dict[str, Any]:
    names = [spec["name"] for spec in plan.specs]
    if len(names) != len(set(names)):
        raise ValueError("plan contains duplicate names")
    name_set = set(names)
    for connection in plan.connections:
        if connection["parent"] not in name_set or connection["child"] not in name_set:
            raise ValueError(f"connection references missing spec: {connection}")
        if float(connection["overlapM"]) < MIN_CONTACT_OVERLAP_M:
            raise ValueError(f"connection below contact gate: {connection}")
    metrics = plan_metrics(plan)
    target = LOD_TARGETS[plan.lod]
    if not target["minTriangles"] <= metrics["estimatedTriangles"] <= target["maxTriangles"]:
        raise ValueError(f"LOD{plan.lod} triangle target missed: {metrics}")
    if metrics["specCount"] > LOD_API[plan.lod]["maxSpecs"]:
        raise ValueError(f"LOD{plan.lod} spec budget exceeded")
    if metrics["materialCount"] < 8 or metrics["materialCount"] > 12:
        raise ValueError("A22 material budget must be 8-12")
    if metrics["landmarkGroups"] != sorted((STACKHOUSE_ID, CUSTOMS_ID)):
        raise ValueError("A22 requires exactly two canonical landmark groups")
    for band in CHAMFER_BANDS_M:
        if metrics["profileBands"].get(band, 0) < 1:
            raise ValueError(f"missing baked {band} profile")
    if _role_count(plan.specs, "a22-stackhouse-unequal-process-core") != 4:
        raise ValueError("Rack-Bridge Storehouse requires four unequal process cores")
    if (
        _role_count(
            plan.specs,
            "a22-i29c-customs-full-depth-sawtooth-glazing",
        )
        != 4
    ):
        raise ValueError("Customs Terminal requires exactly four sawtooth bays")
    if (
        _role_count(
            plan.specs,
            "a22-i29c-customs-integrated-control-core",
        )
        != 1
    ):
        raise ValueError("Customs Terminal requires one integrated control tower")
    if not any(
        spec["role"] == "a22-i29c-customs-deep-machine-line"
        for spec in plan.specs
    ):
        raise ValueError("Customs interior machinery missing")
    if not any(spec["role"] == "a22-stackhouse-loaded-rack-cargo" for spec in plan.specs):
        raise ValueError("Stackhouse rack interior missing")
    if spawn_intrusions(plan):
        raise ValueError(f"spawn intrusions: {spawn_intrusions(plan)}")
    if route_intrusions(plan):
        raise ValueError(f"route intrusions: {route_intrusions(plan)}")
    shore_hits = shore_route_intrusions(plan)
    if shore_hits:
        raise ValueError(f"visual shore intrusions: {shore_hits}")
    if plan.lod == 0:
        projections = {
            key: camera_horizontal_ndc(PRIMARY_CAMERA, point)
            for key, point in PRIMARY_CAMERA_PROJECTION_POINTS.items()
        }
        if abs(projections["shipHull"]) > 0.75:
            raise ValueError(f"ship outside primary safe frame: {projections}")
        if abs(projections["quayWater"]) > 0.75:
            raise ValueError(f"water outside primary safe frame: {projections}")
        if projections["stackhouseCentre"] >= -0.35:
            raise ValueError(f"stackhouse lost left-frame read: {projections}")
        if not 0.10 <= projections["customsCentre"] <= 0.55:
            raise ValueError(f"customs lost right-frame read: {projections}")
        customs_screen_x = {
            key: (
                camera_ndc(PRIMARY_CAMERA, point)[0] + 1.0
            ) * 0.5
            for key, point in ITERATION29C_CUSTOMS_SCREEN_POINTS.items()
        }
        if not 0.54 <= customs_screen_x["nearInner"] <= 0.57:
            raise ValueError(
                f"customs inner silhouette misses 55% frame target: "
                f"{customs_screen_x}"
            )
        if not 0.88 <= customs_screen_x["farOuter"] <= 0.91:
            raise ValueError(
                f"customs outer silhouette misses 90% frame target: "
                f"{customs_screen_x}"
            )
        ship_ndc = [
            camera_ndc(PRIMARY_CAMERA, point)
            for point in PRIMARY_CAMERA_SCREEN_REGIONS["shipHull"]
        ]
        clipped_ship_x = [
            max(-1.0, min(1.0, point[0]))
            for point in ship_ndc
        ]
        if min(clipped_ship_x) < 0.50:
            raise ValueError(f"ship hull left safe frame: {ship_ndc}")
        ship_visible_width = max(clipped_ship_x) - min(clipped_ship_x)
        if not 0.30 <= ship_visible_width <= 0.50:
            raise ValueError(f"ship hull lacks screen width: {ship_ndc}")
        water_ndc = [
            camera_ndc(PRIMARY_CAMERA, point)
            for point in PRIMARY_CAMERA_SCREEN_REGIONS["quayWater"]
        ]
        clipped_water_x = [
            max(-1.0, min(1.0, point[0]))
            for point in water_ndc
        ]
        if max(clipped_water_x) - min(clipped_water_x) < 0.40:
            raise ValueError(f"water lacks visible screen band: {water_ndc}")
        water_y = [point[1] for point in water_ndc]
        if not 0.10 <= max(water_y) - min(water_y) <= 0.25:
            raise ValueError(f"water misses vertical band target: {water_ndc}")
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
        "referenceSha256": IMAGEGEN_REFERENCE_SHA256,
        "fixedCategoryOrder": list(FIXED_SCORE_CATEGORIES),
        "items": [
            {
                "category": category,
                "score": 0.0,
                "evidence": (
                    "Iteration 27 passed its SHA-bound independent review; "
                    "this materially revised Iteration-28 candidate is not "
                    "yet independently certified."
                ),
            }
            for category in FIXED_SCORE_CATEGORIES
        ],
        "producerProvisional": True,
        "controllingIndependentReview": {
            "path": str(A22_CONTROLLING_SCORECARD_PATH),
            "sha256": A22_CONTROLLING_SCORECARD_SHA256,
            "candidateSha256": (
                "0d8d5e497936e2476f5cf73b78c4d5eb79a3ed7a944b769d48318a63a5ca2f3e"
            ),
            "mean": 8.0,
            "minimum": 7.2,
            "genericBlockout": False,
            "verdict": "PASS",
            "appliesToCurrentCandidate": False,
            "lowerIndependentScoreControls": True,
        },
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _verify_inputs() -> dict[str, Any]:
    required = {
        "imagegenReference": (
            IMAGEGEN_REFERENCE_PATH, IMAGEGEN_REFERENCE_SHA256,
        ),
        "a21IndependentScorecard": (
            A21_SCORECARD_PATH, A21_INDEPENDENT_SCORECARD_SHA256,
        ),
        "a22ControllingIndependentScorecard": (
            A22_CONTROLLING_SCORECARD_PATH,
            A22_CONTROLLING_SCORECARD_SHA256,
        ),
    }
    records = {}
    for key, (path, expected) in required.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != expected:
            raise RuntimeError(f"{key} SHA mismatch: {actual} != {expected}")
        records[key] = {
            "path": str(path), "sha256": actual, "verified": True,
        }
    return records


def _runtime_to_blender(point: Sequence[float]) -> tuple[float, float, float]:
    return (float(point[0]), float(point[2]), float(point[1]))


def _v_add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_mul(a: Sequence[float], value: float) -> tuple[float, float, float]:
    return (a[0] * value, a[1] * value, a[2] * value)


def _v_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v_cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _v_norm(a: Sequence[float]) -> tuple[float, float, float]:
    length = math.sqrt(_v_dot(a, a))
    if length < 1e-9:
        raise ValueError("cannot normalize zero vector")
    return (a[0] / length, a[1] / length, a[2] / length)


def _append_polyhedron(
    batch: dict[str, list[Any]],
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
) -> None:
    offset = len(batch["vertices"])
    batch["vertices"].extend(_runtime_to_blender(vertex) for vertex in vertices)
    batch["faces"].extend(
        tuple(offset + index for index in face) for face in faces
    )


def _orient_face(
    vertices: Sequence[Sequence[float]],
    face: Sequence[int],
    centre: Sequence[float],
) -> tuple[int, ...]:
    ordered = tuple(face)
    normal = _v_cross(
        _v_sub(vertices[ordered[1]], vertices[ordered[0]]),
        _v_sub(vertices[ordered[2]], vertices[ordered[0]]),
    )
    face_centre = tuple(
        sum(vertices[index][axis] for index in ordered) / len(ordered)
        for axis in range(3)
    )
    if _v_dot(normal, _v_sub(face_centre, centre)) < 0:
        return tuple(reversed(ordered))
    return ordered


def _append_chamfer_box_mesh(
    batch: dict[str, list[Any]],
    spec: Mapping[str, Any],
) -> None:
    yaw = float(spec.get("yaw", 0.0))
    axis_x = (math.cos(yaw), 0.0, math.sin(yaw))
    axis_y = (0.0, 1.0, 0.0)
    axis_z = (-math.sin(yaw), 0.0, math.cos(yaw))
    centre = (float(spec["x"]), float(spec["y"]), float(spec["z"]))
    hx, hy, hz = (
        float(spec["w"]) / 2,
        float(spec["h"]) / 2,
        float(spec["d"]) / 2,
    )
    bevel = float(spec["bevelM"])
    vertices: list[tuple[float, float, float]] = []
    lookup: dict[tuple[int, int, int, str], int] = {}

    def add_local(
        sx: int, sy: int, sz: int, face_axis: str,
    ) -> None:
        values = {
            "x": (
                sx * hx,
                sy * (hy - bevel),
                sz * (hz - bevel),
            ),
            "y": (
                sx * (hx - bevel),
                sy * hy,
                sz * (hz - bevel),
            ),
            "z": (
                sx * (hx - bevel),
                sy * (hy - bevel),
                sz * hz,
            ),
        }[face_axis]
        point = centre
        point = _v_add(point, _v_mul(axis_x, values[0]))
        point = _v_add(point, _v_mul(axis_y, values[1]))
        point = _v_add(point, _v_mul(axis_z, values[2]))
        lookup[(sx, sy, sz, face_axis)] = len(vertices)
        vertices.append(point)

    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                for face_axis in ("x", "y", "z"):
                    add_local(sx, sy, sz, face_axis)

    faces: list[tuple[int, ...]] = []
    # Six central faces.
    for sx in (-1, 1):
        faces.append(tuple(
            lookup[(sx, sy, sz, "x")]
            for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ))
    for sy in (-1, 1):
        faces.append(tuple(
            lookup[(sx, sy, sz, "y")]
            for sx, sz in ((-1, -1), (-1, 1), (1, 1), (1, -1))
        ))
    for sz in (-1, 1):
        faces.append(tuple(
            lookup[(sx, sy, sz, "z")]
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ))
    # Twelve edge faces.
    for sx in (-1, 1):
        for sy in (-1, 1):
            faces.append((
                lookup[(sx, sy, -1, "x")],
                lookup[(sx, sy, 1, "x")],
                lookup[(sx, sy, 1, "y")],
                lookup[(sx, sy, -1, "y")],
            ))
    for sx in (-1, 1):
        for sz in (-1, 1):
            faces.append((
                lookup[(sx, -1, sz, "x")],
                lookup[(sx, 1, sz, "x")],
                lookup[(sx, 1, sz, "z")],
                lookup[(sx, -1, sz, "z")],
            ))
    for sy in (-1, 1):
        for sz in (-1, 1):
            faces.append((
                lookup[(-1, sy, sz, "y")],
                lookup[(1, sy, sz, "y")],
                lookup[(1, sy, sz, "z")],
                lookup[(-1, sy, sz, "z")],
            ))
    # Eight corner triangles.
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                faces.append((
                    lookup[(sx, sy, sz, "x")],
                    lookup[(sx, sy, sz, "y")],
                    lookup[(sx, sy, sz, "z")],
                ))
    # Runtime Y-up -> Blender Z-up swaps axes and reverses handedness.
    oriented = [
        tuple(reversed(_orient_face(vertices, face, centre)))
        for face in faces
    ]
    _append_polyhedron(batch, vertices, oriented)


def _append_pipe_mesh(
    batch: dict[str, list[Any]],
    spec: Mapping[str, Any],
) -> None:
    start = tuple(float(value) for value in spec["start"])
    end = tuple(float(value) for value in spec["end"])
    axis = _v_norm(_v_sub(end, start))
    reference = (
        (0.0, 1.0, 0.0)
        if abs(_v_dot(axis, (0.0, 1.0, 0.0))) < 0.92
        else (1.0, 0.0, 0.0)
    )
    side = _v_norm(_v_cross(axis, reference))
    up = _v_norm(_v_cross(side, axis))
    radius = float(spec["radius"])
    segments = int(spec["segments"])
    vertices = []
    for point in (start, end):
        for index in range(segments):
            angle = math.tau * index / segments
            offset = _v_add(
                _v_mul(side, math.cos(angle) * radius),
                _v_mul(up, math.sin(angle) * radius),
            )
            vertices.append(_v_add(point, offset))
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(segments))),
        tuple(range(segments, segments * 2)),
    ]
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((index, nxt, segments + nxt, segments + index))
    _append_polyhedron(batch, vertices, faces)


def _build_mesh_batches(
    backend: Any,
    plan: SpecPlan,
) -> dict[str, dict[str, list[Any]]]:
    batches: dict[str, dict[str, list[Any]]] = defaultdict(
        lambda: {"vertices": [], "faces": []},
    )
    for spec in plan.specs:
        batch = batches[spec["material"]]
        if spec["kind"] in {"box", "oriented_box"}:
            backend._append_box_mesh(batch, spec)
        elif spec["kind"] == "beam":
            backend._append_beam_mesh(batch, spec)
        elif spec["kind"] == "cylinder":
            backend._append_cylinder_mesh(batch, spec)
        elif spec["kind"] == "panel":
            backend._append_panel_mesh(batch, spec)
        elif spec["kind"] == "chamfer_box":
            _append_chamfer_box_mesh(batch, spec)
        elif spec["kind"] in {"pipe", "round_member"}:
            _append_pipe_mesh(batch, spec)
        else:
            raise ValueError(f"unsupported mesh kind: {spec['kind']}")
    return dict(batches)


def _set_bsdf_input(bsdf: Any, names: Sequence[str], value: Any) -> bool:
    for name in names:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def _material_export_name(key: str) -> str:
    return f"SO_A22_{key}_{MATERIAL_EXPORT_SUFFIX[key]}"


def _hash_noise(seed: int, x: int, y: int) -> float:
    value = (
        x * 0x1F123BB5 ^ y * 0x5F356495 ^ seed * 0x6C8E9CF5
    ) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x2C1B3C6D) & 0xFFFFFFFF
    value ^= value >> 12
    value = (value * 0x297A2D39) & 0xFFFFFFFF
    value ^= value >> 15
    return value / 0xFFFFFFFF


def _value_noise(seed: int, x: int, y: int, cell_size: int) -> float:
    gx, gy = x // cell_size, y // cell_size
    fx, fy = (x % cell_size) / cell_size, (y % cell_size) / cell_size
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    n00 = _hash_noise(seed, gx, gy)
    n10 = _hash_noise(seed, gx + 1, gy)
    n01 = _hash_noise(seed, gx, gy + 1)
    n11 = _hash_noise(seed, gx + 1, gy + 1)
    top = n00 + (n10 - n00) * fx
    bottom = n01 + (n11 - n01) * fx
    return top + (bottom - top) * fy


def _wet_asphalt_edge_wear(x: int, y: int) -> bool:
    # Sparse, locally interrupted joints.  The previous 61/73-pixel union
    # covered 8.4% of the atlas and repeated as equal-width marble veins over
    # the whole apron.  Larger periods plus a broad locality mask reduce that
    # to roughly 5.3% while keeping camera-scale relief around repair zones.
    vertical_phase = (
        x + int(7.0 * math.sin(y * 0.13) + 4.0 * math.sin(y * 0.041))
    ) % 83
    horizontal_phase = (
        y + int(8.0 * math.sin(x * 0.11) + 3.0 * math.sin(x * 0.029))
    ) % 101
    joint = (
        min(vertical_phase, 83 - vertical_phase) <= 1
        or min(horizontal_phase, 101 - horizontal_phase) <= 1
    )
    locality = _value_noise(0xA22C4A6B, x, y, 29)
    return joint and locality > 0.40


def _wet_asphalt_local_wear(
    x: int,
    y: int,
    size: int,
) -> tuple[float, float]:
    """Return soft repair-patch and traffic-wear masks without hard veins."""
    u = (x + 0.5) / size
    v = (y + 0.5) / size
    patch = 0.0
    for cx, cy, rx, ry in (
        (0.20, 0.24, 0.15, 0.10),
        (0.73, 0.60, 0.19, 0.13),
        (0.43, 0.84, 0.11, 0.17),
    ):
        distance = math.sqrt(
            ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2
        )
        patch = max(patch, max(0.0, 1.0 - distance))
    patch *= 0.58 + _value_noise(0xA22FA7C4, x, y, 17) * 0.42

    lane_distance = min(abs(u - 0.31), abs(u - 0.69))
    traffic = max(0.0, 1.0 - lane_distance / 0.065)
    traffic *= 0.38 + _value_noise(0xA22D12E, x, y, 23) * 0.62
    traffic *= 0.72 + math.sin(math.tau * (v * 1.35 + 0.11)) * 0.18
    return patch, max(0.0, min(1.0, traffic))


def _texture_signal(key: str, x: int, y: int, size: int) -> float:
    seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    broad = _value_noise(seed, x, y, 31)
    medium = _value_noise(seed ^ 0xA3C59AC3, x, y, 11)
    rain_column = _value_noise(seed ^ 0xD00DFEED, x, 0, 5)
    downward = (y / max(1, size - 1)) ** 1.65
    aggregate = _hash_noise(seed ^ 0xC761C23C, x, y)
    signal = broad * 0.43 + medium * 0.28 + aggregate * 0.10
    if MATERIALS[key].get("rainStreaks"):
        signal += rain_column * downward * 0.30
    if key == "weathered_zinc":
        corrugation = math.cos(math.tau * x / 7.0) * 0.5 + 0.5
        signal = signal * 0.68 + corrugation * 0.32
    elif key in {"old_concrete", "pale_concrete"}:
        panel_joint = 1.0 if (x % 97 < 1 or y % 113 < 1) else 0.0
        signal -= panel_joint * 0.18
    elif key == "structural_steel":
        mill_band = math.cos(math.tau * y / 13.0) * 0.5 + 0.5
        signal = signal * 0.80 + mill_band * 0.20
    elif key == "wet_asphalt":
        patch, traffic = _wet_asphalt_local_wear(x, y, size)
        signal = signal * 0.90 + patch * 0.065 + traffic * 0.035
        if _wet_asphalt_edge_wear(x, y):
            signal = 0.78
        elif _hash_noise(seed ^ 0xA22E06E, x, y) > 0.992:
            signal = max(signal, 0.72)
    return max(0.0, min(1.0, signal))


def _create_texture_set(
    bpy: Any,
    key: str,
    recipe: Mapping[str, Any],
) -> dict[str, Any]:
    texture_dir = PRIVATE_OUTPUT_ROOT / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)
    size = 256
    color = tuple(float(value) for value in recipe["color"])
    roughness = float(recipe.get("roughness", 0.6))
    alpha = float(recipe.get("alpha", color[3]))
    heights = [
        _texture_signal(key, x, y, size)
        for y in range(size) for x in range(size)
    ]
    images = {}
    for texture_kind in ("basecolor", "roughness", "normal"):
        image = bpy.data.images.new(
            f"SO_A22_{key}_{texture_kind}",
            width=size, height=size, alpha=True,
        )
        pixels: list[float] = []
        for y in range(size):
            for x in range(size):
                index = y * size + x
                signal = heights[index]
                if texture_kind == "basecolor":
                    factor = 0.60 + signal * 0.72
                    if recipe.get("rustMask"):
                        rust_column = _hash_noise(0xA2200 + index % 13, x // 4, 0)
                        factor *= 0.80 + rust_column * (y / size) * 0.30
                    if key == "wet_asphalt":
                        oil_patch = _value_noise(0xA22F17, x, y, 19)
                        repair_patch, traffic_wear = _wet_asphalt_local_wear(
                            x, y, size,
                        )
                        factor *= (
                            0.66
                            + _value_noise(0xA22, x, y, 23) * 0.40
                            + (0.10 if oil_patch > 0.68 else 0.0)
                        )
                        factor *= (
                            1.0 - repair_patch * 0.11
                            - traffic_wear * 0.055
                        )
                    if key == "pallet_wood":
                        factor *= 0.84 + ((x // 9) % 3) * 0.07
                    red = max(0.0, min(1.0, color[0] * factor))
                    green = max(0.0, min(1.0, color[1] * factor))
                    blue = max(0.0, min(1.0, color[2] * factor))
                    if (
                        key in {"old_concrete", "pale_concrete"}
                        and (x % 97 < 1 or y % 113 < 1)
                    ):
                        red *= 0.72
                        green *= 0.74
                        blue *= 0.76
                    elif key == "weathered_zinc" and x % 7 < 1:
                        red *= 0.58
                        green *= 0.62
                        blue *= 0.66
                    elif key == "structural_steel" and y % 13 < 1:
                        red *= 0.68
                        green *= 0.70
                        blue *= 0.72
                    if key == "wet_asphalt":
                        if _wet_asphalt_edge_wear(x, y):
                            red, green, blue = 0.16, 0.15, 0.14
                        elif _hash_noise(
                            0xA22E06E, x, y,
                        ) > 0.992:
                            red, green, blue = 0.11, 0.105, 0.095
                    if recipe.get("rustMask"):
                        rust_mask = max(
                            0.0,
                            min(
                                0.42,
                                (
                                    _value_noise(0xA22C0DE, x, y, 17)
                                    + (y / size) * 0.42
                                    - 0.78
                                ) * 0.82,
                            ),
                        )
                        red = red * (1.0 - rust_mask) + 0.24 * rust_mask
                        green = green * (1.0 - rust_mask) + 0.060 * rust_mask
                        blue = blue * (1.0 - rust_mask) + 0.022 * rust_mask
                    pixels.extend((
                        red,
                        green,
                        blue,
                        alpha,
                    ))
                elif texture_kind == "roughness":
                    variation = (signal - 0.5) * (
                        0.34 if recipe.get("wetVariation")
                        else 0.27 if (
                            recipe.get("stains")
                            or recipe.get("rustMask")
                            or recipe.get("rainStreaks")
                        )
                        else 0.13
                    )
                    value = max(0.035, min(0.98, roughness + variation))
                    if key == "wet_asphalt":
                        repair_patch, traffic_wear = _wet_asphalt_local_wear(
                            x, y, size,
                        )
                        value = max(
                            0.035,
                            min(
                                0.98,
                                value + repair_patch * 0.09
                                - traffic_wear * 0.055,
                            ),
                        )
                        if _wet_asphalt_edge_wear(x, y):
                            value = 0.57
                    pixels.extend((value, value, value, 1.0))
                else:
                    left = heights[y * size + ((x - 1) % size)]
                    right = heights[y * size + ((x + 1) % size)]
                    down = heights[((y - 1) % size) * size + x]
                    up = heights[((y + 1) % size) * size + x]
                    strength = (
                        0.52 if key in {"old_concrete", "rust", "weathered_zinc"}
                        else 0.30 if key == "structural_steel"
                        else 0.24
                    )
                    nx = (left - right) * strength
                    ny = (down - up) * strength
                    length = math.sqrt(nx * nx + ny * ny + 1.0)
                    pixels.extend((
                        nx / length * 0.5 + 0.5,
                        ny / length * 0.5 + 0.5,
                        1.0 / length * 0.5 + 0.5,
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
    base.image = texture_set["basecolor"]
    base.location = (-420, 180)
    rough = nodes.new("ShaderNodeTexImage")
    rough.image = texture_set["roughness"]
    rough.image.colorspace_settings.name = "Non-Color"
    rough.location = (-420, -20)
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = texture_set["normal"]
    normal.image.colorspace_settings.name = "Non-Color"
    normal.location = (-420, -240)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (120, -210)
    normal_map.inputs["Strength"].default_value = (
        0.62 if key in {"old_concrete", "pale_concrete", "rust"}
        else 0.48 if key == "weathered_zinc"
        else 0.42 if key == "structural_steel"
        else 0.24 if key == "wet_asphalt"
        else 0.18 if key == "puddle_water"
        else 0.28 if key == "sea_water"
        else 0.15
    )
    links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    _set_bsdf_input(bsdf, ("Metallic",), float(recipe.get("metallic", 0.0)))
    _set_bsdf_input(bsdf, ("IOR",), 1.46)
    if key in {"wet_asphalt", "puddle_water", "sea_water"}:
        _set_bsdf_input(
            bsdf,
            ("Coat Weight", "Clearcoat"),
            0.38
            if key == "sea_water"
            else 0.34 if key == "puddle_water"
            else 0.22,
        )
        _set_bsdf_input(
            bsdf,
            ("Coat Roughness", "Clearcoat Roughness"),
            0.08
            if key == "sea_water"
            else 0.11 if key == "puddle_water"
            else 0.16,
        )
    elif key in {"weathered_zinc", "structural_steel", "safety_orange"}:
        _set_bsdf_input(bsdf, ("Coat Weight", "Clearcoat"), 0.06)
        _set_bsdf_input(
            bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.32,
        )
    transmission = float(recipe.get("transmission", 0.0))
    if transmission:
        _set_bsdf_input(
            bsdf, ("Transmission Weight", "Transmission"), transmission,
        )
    alpha = float(recipe.get("alpha", 1.0))
    if alpha < 1.0:
        links.new(base.outputs["Alpha"], bsdf.inputs["Alpha"])
        material.diffuse_color = tuple(
            float(value) for value in recipe["color"]
        )
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        if hasattr(material, "use_transparency_overlap"):
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
    uv_layer = mesh.uv_layers.new(name="SO_A22_WORLD_UV")
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
    batches = _build_mesh_batches(backend, plan)
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
        mesh = bpy.data.meshes.new(f"SO_A22_{material_key}_MESH")
        mesh.from_pydata(batch["vertices"], [], batch["faces"])
        mesh.validate(verbose=False)
        mesh.update(calc_edges=True)
        _assign_world_uv(
            mesh,
            1.0 / float(MATERIALS[material_key].get("textureScaleM", 4.0)),
        )
        raw_triangles += sum(
            max(0, len(poly.vertices) - 2) for poly in mesh.polygons
        )
        obj = bpy.data.objects.new(f"SO_A22_{material_key}", mesh)
        root.objects.link(obj)
        obj.data.materials.append(materials[material_key])
        obj["hibanaGeneratorVersion"] = REFERENCE_MATCH_VERSION
        obj["hibanaGeneratorSha"] = source_sha
        obj["hibanaStageId"] = STAGE_ID
        obj["hibanaLod"] = lod
        obj["hibanaBakedRoleProfiles"] = True
        mesh_objects.append(obj)
    if raw_triangles != plan_metrics(plan)["estimatedTriangles"]:
        raise RuntimeError(
            f"evaluated triangle mismatch: {raw_triangles} != "
            f"{plan_metrics(plan)['estimatedTriangles']}"
        )
    return {
        "collection": root,
        "meshObjects": mesh_objects,
        "rawMeshTriangles": raw_triangles,
        "meshObjectCount": len(mesh_objects),
        "batchCount": len(batches),
        "vertexCount": sum(len(batch["vertices"]) for batch in batches.values()),
        "polygonCount": sum(len(batch["faces"]) for batch in batches.values()),
        "textureCount": sum(len(value) for value in texture_sets.values()),
        "bakedRoleSpecificProfiles": True,
        "modifierCount": 0,
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
    scene.view_settings.exposure = 0.82
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True

    world = bpy.data.worlds.new("SO_A22_World_RainHarbour")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.62
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 3.1
    noise.inputs["Detail"].default_value = 5.5
    noise.inputs["Roughness"].default_value = 0.72
    noise.inputs["Distortion"].default_value = 0.24
    noise.inputs["W"].default_value = 0.73
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.050, 0.082, 0.108, 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.34, 0.35, 0.35, 1.0)
    mid = ramp.color_ramp.elements.new(0.46)
    mid.color = (0.14, 0.21, 0.27, 1.0)
    warm = ramp.color_ramp.elements.new(0.63)
    warm.color = (0.205, 0.18, 0.165, 1.0)
    links.new(texcoord.outputs["Normal"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    scene.world = world

    sun_data = bpy.data.lights.new("SO_A22_LGT_LowSun", "SUN")
    sun_data.energy = 5.1
    sun_data.color = (1.0, 0.77, 0.52)
    sun_data.angle = math.radians(1.8)
    if hasattr(sun_data, "use_shadow"):
        sun_data.use_shadow = True
    sun = bpy.data.objects.new("SO_A22_LGT_LowSun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (
        math.radians(58.0), math.radians(-14.0), math.radians(-124.0),
    )

    fill_data = bpy.data.lights.new("SO_A22_LGT_OvercastFill", "AREA")
    fill_data.energy = 34000.0
    fill_data.color = (0.38, 0.54, 0.74)
    fill_data.shape = "DISK"
    fill_data.size = 145.0
    if hasattr(fill_data, "use_shadow"):
        fill_data.use_shadow = True
    fill = bpy.data.objects.new("SO_A22_LGT_OvercastFill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-130.0, -95.0, 110.0)
    _look_at(fill, (20.0, 15.0, 20.0))

    front_data = bpy.data.lights.new("SO_A22_LGT_CameraSideFill", "AREA")
    front_data.energy = 44000.0
    front_data.color = (0.48, 0.61, 0.79)
    front_data.shape = "DISK"
    front_data.size = 180.0
    if hasattr(front_data, "use_shadow"):
        front_data.use_shadow = True
    front = bpy.data.objects.new("SO_A22_LGT_CameraSideFill", front_data)
    scene.collection.objects.link(front)
    front.location = (-175.0, 170.0, 135.0)
    _look_at(front, (5.0, 25.0, 24.0))

    contact_data = bpy.data.lights.new("SO_A22_LGT_CoolContactKey", "SUN")
    contact_data.energy = 1.35
    contact_data.color = (0.55, 0.70, 0.90)
    contact_data.angle = math.radians(0.38)
    if hasattr(contact_data, "use_shadow"):
        contact_data.use_shadow = True
    contact = bpy.data.objects.new("SO_A22_LGT_CoolContactKey", contact_data)
    scene.collection.objects.link(contact)
    contact.rotation_euler = (
        math.radians(42.0), math.radians(-18.0), math.radians(138.0),
    )

    rim_data = bpy.data.lights.new("SO_A22_LGT_HarbourRim", "AREA")
    rim_data.energy = 26000.0
    rim_data.color = (1.0, 0.54, 0.25)
    rim_data.shape = "DISK"
    rim_data.size = 92.0
    if hasattr(rim_data, "use_shadow"):
        rim_data.use_shadow = True
    rim = bpy.data.objects.new("SO_A22_LGT_HarbourRim", rim_data)
    scene.collection.objects.link(rim)
    rim.location = (135.0, 120.0, 98.0)
    _look_at(rim, (5.0, 0.0, 25.0))

    # A broad sky-coloured lift affects the real far geometry only through
    # distance and incidence, creating air perspective without a world-volume
    # layer or raster horizon card.
    far_data = bpy.data.lights.new("SO_A22_LGT_FarDistrictLift", "AREA")
    far_data.energy = 13000.0
    far_data.color = (0.50, 0.64, 0.74)
    far_data.shape = "DISK"
    far_data.size = 210.0
    if hasattr(far_data, "use_shadow"):
        far_data.use_shadow = True
    far = bpy.data.objects.new("SO_A22_LGT_FarDistrictLift", far_data)
    scene.collection.objects.link(far)
    far.location = _runtime_to_blender((45.0, 118.0, -145.0))
    _look_at(far, _runtime_to_blender((40.0, 22.0, -85.0)))

    practicals = (
        ((66.0, 24.0, 92.0), 3400.0, 14.0),
        ((-67.0, 18.0, -58.0), 3200.0, 14.0),
        ((-132.0, 9.0, 103.0), 2200.0, 16.0),
        ((-55.0, 16.0, 195.0), 1900.0, 18.0),
        ((-180.0, 7.0, 104.0), 2400.0, 12.0),
        ((-181.0, 16.0, 34.0), 2400.0, 12.0),
        ((-103.0, 21.0, -14.0), 4200.0, 8.0),
        ((-80.0, 21.0, -14.0), 4200.0, 8.0),
        ((-57.0, 21.0, -14.0), 4200.0, 8.0),
        ((-34.0, 21.0, -14.0), 4200.0, 8.0),
        ((45.0, 60.0, 95.0), 3600.0, 10.0),
        ((75.0, 60.0, 95.0), 3600.0, 10.0),
    )
    for index, (runtime_location, energy, size) in enumerate(practicals):
        data = bpy.data.lights.new(f"SO_A22_LGT_Practical_{index}", "AREA")
        data.energy = energy
        data.color = (1.0, 0.36, 0.095)
        data.shape = "DISK"
        data.size = size
        if hasattr(data, "use_shadow"):
            data.use_shadow = False
        obj = bpy.data.objects.new(f"SO_A22_LGT_Practical_{index}", data)
        scene.collection.objects.link(obj)
        obj.location = _runtime_to_blender(runtime_location)
        _look_at(
            obj,
            _runtime_to_blender((
                runtime_location[0], 2.0, runtime_location[2],
            )),
        )

    camera_data = bpy.data.cameras.new("SO_A22_FIXED_1P65M_CAMERA")
    camera_data.sensor_width = 36.0
    camera_data.clip_start = 0.08
    camera_data.clip_end = 1200.0
    camera_data.dof.use_dof = False
    camera = bpy.data.objects.new("SO_A22_FIXED_1P65M_CAMERA", camera_data)
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
        raise RuntimeError("A22 refuses to edit an interactive Blender scene")
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in tuple(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    for material in tuple(bpy.data.materials):
        bpy.data.materials.remove(material)
    for image in tuple(bpy.data.images):
        bpy.data.images.remove(image)
    for world in tuple(bpy.data.worlds):
        bpy.data.worlds.remove(world)


def _selected_views(selection: str) -> tuple[dict[str, Any], ...]:
    if selection == "all":
        return PRIVATE_VIEWS
    if selection == "primary":
        return (PRIMARY_CAMERA,)
    requested = {int(value) for value in selection.split(",")}
    return tuple(
        view for index, view in enumerate(PRIVATE_VIEWS, start=1)
        if index in requested
    )


def _render_result_preflight(bpy: Any, output_path: Path) -> dict[str, Any]:
    image = bpy.data.images.get("Render Result")
    if image is None or image.size[0] <= 0 or image.size[1] <= 0:
        try:
            image = bpy.data.images.load(str(output_path), check_existing=False)
        except RuntimeError:
            image = None
    if image is None or image.size[0] <= 0 or image.size[1] <= 0:
        return {
            "sampleCount": 0, "meanLinearLuminance": 0.0,
            "nonBlackFraction": 0.0, "preflightPass": False,
            "failures": ["missing-render-result"],
        }
    width, height = int(image.size[0]), int(image.size[1])
    step_x, step_y = max(1, width // 160), max(1, height // 90)
    pixels = image.pixels
    luminances = []
    for y in range(step_y // 2, height, step_y):
        for x in range(step_x // 2, width, step_x):
            offset = (y * width + x) * 4
            red, green, blue = (
                pixels[offset], pixels[offset + 1], pixels[offset + 2]
            )
            luminances.append(
                0.2126 * red + 0.7152 * green + 0.0722 * blue
            )
    mean = sum(luminances) / max(1, len(luminances))
    minimum = min(luminances, default=0.0)
    maximum = max(luminances, default=0.0)
    non_black = sum(value > 0.012 for value in luminances) / max(
        1, len(luminances),
    )
    failures = []
    if mean < 0.028:
        failures.append("mean-luminance")
    if maximum < 0.12:
        failures.append("highlight-range")
    if non_black < 0.70:
        failures.append("non-black-coverage")
    if maximum - minimum < 0.055:
        failures.append("luminance-span")
    return {
        "sampleCount": len(luminances),
        "meanLinearLuminance": round(mean, 6),
        "minLinearLuminance": round(minimum, 6),
        "maxLinearLuminance": round(maximum, 6),
        "nonBlackFraction": round(non_black, 6),
        "preflightPass": not failures,
        "failures": failures,
    }


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


SELF_REVIEW_HISTORY: tuple[dict[str, Any], ...] = (
    {
        "iteration": 1,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-01-rejected-black-crush-1280x720.png"
        ),
        "proofSha256": (
            "f59a2926c0efb3b4ff3a21e8b32fbe8d569d9024b3bb7619fcc504741325bf41"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Mean linear luminance 0.001188 made macro comparison impossible.",
            "Non-black coverage 0.004931 collapsed material and interior evidence.",
            "World-volume treatment absorbed the port instead of creating haze.",
        ],
        "requiredChanges": [
            "Remove absorbing world volume from proof render.",
            "Add broad camera-side overcast fill and raise coastal key exposure.",
            "Re-render the same locked 1280x720 camera before judging geometry.",
        ],
    },
    {
        "iteration": 2,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-02-rejected-macro-blockout-1280x720.png"
        ),
        "proofSha256": (
            "0d2ac3cf2883200e38823d3a6a5032611d5d0faa97df86075fabcee24120f8af"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Triangle-target plates floated above the left hero without contacts.",
            "A secondary-city mass occluded the sawtooth hall and control tower.",
            "The central route lacked freight, workers and wet reflection breaks.",
            "Duplicate A20 port layers obscured the authored ship/crane identity.",
            "Primary proof still read as a dry daylight blockout.",
        ],
        "requiredChanges": [
            "Retain only A20 ground and road essentials.",
            "Replace free plates with endpoint pipes attached to real process faces.",
            "Move the control tower and secondary city out of the hall sightline.",
            "Populate the route edges with vehicles, workers and water geometry.",
            "Re-lock the compressed A21-compatible camera before full evidence.",
        ],
    },
    {
        "iteration": 3,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-03-rejected-functional-blockout-1280x720.png"
        ),
        "proofSha256": (
            "69551f475a9bdb147f283f35a425650b365a205a99d73beda7aa4aa65635b069"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Sky occupied roughly forty-five percent and weakened port density.",
            "Rack floors still read as disconnected shelving between white walls.",
            "The central vanishing point had no occupied inter-hero bridge or city.",
            "Customs lower bays repeated as dark solids rather than deep portals.",
            "Near water remained an unbroken blank reflection field.",
        ],
        "requiredChanges": [
            "Lower the camera aim while preserving the fixed 1.65 m eye.",
            "Add continuous rack fascias, attached stairs and the long transfer bridge.",
            "Turn loading masses into jamb/header portals with warm machine depth.",
            "Place distant city behind the vanishing point and quay gear near water.",
            "Darken the wet dusk palette while retaining readable broad fill.",
        ],
    },
    {
        "iteration": 4,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-04-rejected-route-occlusion-1280x720.png"
        ),
        "proofSha256": (
            "a211d977ac079267c84603189b978d298dde2a7571d8f66b09ed4dab9cd736c0"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "The new bridge, warm hall and wet reflection passed macro intent.",
            "A forklift only 17.6 m from camera became a large yellow rectangle.",
            "Near quay cargo also occluded the central readable route.",
        ],
        "requiredChanges": [
            "Move the nearest vehicle and quay gear into the mid-ground.",
            "Preserve the now-readable bridge, terminal, tower and wet response.",
        ],
    },
    {
        "iteration": 6,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-06-rejected-independent-visual-gate-1280x720.png"
        ),
        "proofSha256": (
            "af7e43ae0752a4242f512f5c088224979c43b1e518c3b2005f8bf45c5937fb81"
        ),
        "comparison": (
            "Independent original-resolution review against the ImageGen reference."
        ),
        "findings": [
            "Independent ten-category estimate averaged about 4.35, minimum 3.0.",
            "Upper stackhouse machinery still appeared unsupported or floating.",
            "Human scale, route occupation, ship/crane readability remained weak.",
            "Tower massing, flat hero surfaces and sky/foreground voids remained P0.",
        ],
        "requiredChanges": [
            "Ground crown machinery with lattice supports and occupied windows.",
            "Articulate the customs tower with exoskeleton, glazing and balconies.",
            "Make vehicles and workers recognizable in the primary frame.",
            "Reduce sky and enrich near/mid/far port storytelling before evidence.",
        ],
    },
    {
        "iteration": 8,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-08-rejected-primitive-grammar-1280x720.png"
        ),
        "proofSha256": (
            "39330c1a475113664438b0d83ef19c39eaf7410a5900955b2b4e8b4ac4f135e9"
        ),
        "comparison": (
            "Independent original-resolution review against the ImageGen reference."
        ),
        "findings": [
            "Independent estimate improved to roughly 5.1 but remained gate-fail.",
            "Rack cargo still read as unsupported primitives despite added windows.",
            "Customs portals lacked foreground machine depth and fabricated seams.",
            "Truck, forklift, ship and crane identity remained too small in primary.",
        ],
        "requiredChanges": [
            "Install real floor plates, exterior X/K braces and grounded rack frames.",
            "Move external stairs and catwalk circulation into the locked sightline.",
            "Add roof gutters, tower stairs and recessed portal machine banks.",
            "Place a subordinate working drydock on the primary vanishing line.",
        ],
    },
    {
        "iteration": 9,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-09-rejected-density-material-gate-1280x720.png"
        ),
        "proofSha256": (
            "911413d01ae3f32e644c528157a3ec9ae64c3be956d94950a950b946e37f181b"
        ),
        "comparison": (
            "Independent original-resolution review against the ImageGen reference."
        ),
        "findings": [
            "Independent score reached about 5.7 average with a 4.8 minimum.",
            "Camera-visible near, middle and far density remained under-authored.",
            "The road still read as one black mirror with weak roughness breakup.",
            "Vehicles, portal machinery and tower circulation stayed too box-like.",
        ],
        "requiredChanges": [
            "Fill the central sky with subordinate 3D refinery and port silhouettes.",
            "Author a broad rough apron, drains, patches and visible puddle boundaries.",
            "Expose four separate wheels, angled cabs, forks and machine silhouettes.",
            "Increase west facade occupancy and customs facade/catwalk readability.",
            "Strengthen texture grain, rust masking and rain streak response.",
        ],
    },
    {
        "iteration": 10,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-10-rejected-container-coordinate-bug-1280x720.png"
        ),
        "proofSha256": (
            "704daaa8c7c8a5c848c91a2b6c06fd49bbe3ad4070900077a449b1cfbd9b6416"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Road and occupied facades improved, but the proof contained a hard bug.",
            "Container ribs used route deltas instead of unit vectors and exploded.",
            "The broad apron stayed too mirror-like despite new repair markings.",
            "Forklift forks and crane silhouettes still needed a stronger broadside.",
        ],
        "requiredChanges": [
            "Replace raw route deltas with normalized axes and ground each stack.",
            "Raise asphalt roughness while keeping shallow puddles reflective.",
            "Rotate the lead forklift into a readable side/front silhouette.",
            "Add a real camera-visible lattice crane and taller striped port stack.",
        ],
    },
    {
        "iteration": 11,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-11-rejected-independent-visual-gate-1280x720.png"
        ),
        "proofSha256": (
            "6b7de88d82d4e4a56d31e1dfa10dc7ed5df883622dac90aa0ceccc0c2562812c"
        ),
        "comparison": (
            "Independent original-resolution review against the ImageGen reference."
        ),
        "findings": [
            "Independent score improved to about 6.25 average, 5.7 minimum.",
            "The apron remained too uniformly mirror-like outside local puddles.",
            "Solid refinery support walls hid ship, portals and depth layering.",
            "Crane, vehicle, tower and far skyline silhouettes remained undersized.",
        ],
        "requiredChanges": [
            "Raise asphalt roughness to 0.42 and reserve gloss for puddle geometry.",
            "Replace high support walls with low bases and open lattice crowns.",
            "Strengthen crane boom web, hoist, ship bow and bridge mast silhouettes.",
            "Expose forks, wheels and portal machines with screen-readable accents.",
            "Add tower mid balconies, occupied catwalks and secondary gantries.",
            "Reduce orange emission so steel, rust and concrete colour separate.",
        ],
    },
    {
        "iteration": 12,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-12-rejected-unsegmented-skyline-walls-1280x720.png"
        ),
        "proofSha256": (
            "aabbff1f8832e5577fa5e5ef8d76cfd2e407b07aff0433b4c6872a6741e2820d"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Matte asphalt and the broadside forklift passed the intended correction.",
            "Central skyline masses still projected as high unsegmented grey walls.",
            "Those walls hid ship depth and reduced customs portal exposure.",
            "Crane boom was larger but its lattice web remained visually delicate.",
        ],
        "requiredChanges": [
            "Lower and setback central skyline masses while preserving far depth.",
            "Move all port-city windows onto camera-facing north facades.",
            "Add multi-level windows, rust bands, ribs and tiered roof silhouettes.",
            "Keep local puddles glossy and retain the now-readable forklift stance.",
        ],
    },
    {
        "iteration": 13,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-13-rejected-checkpoint-occlusion-1280x720.png"
        ),
        "proofSha256": (
            "db4a7007cdb5f44919fa47fa65828657259e2c1f4b8397de8bd0dc0401d1a472"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Segmented distant skyline passed the wall-reduction intent.",
            "Projection audit isolated two near checkpoint booths as the remaining wall.",
            "Their camera-opposed windows left both masses blank and visually tall.",
            "The pair still covered the ship bow and lower portal depth.",
        ],
        "requiredChanges": [
            "Reduce booth dimensions and retain the canonical route clearance.",
            "Put deep windows on north and west camera-facing booth surfaces.",
            "Add thin roofs, service doors and warm signs for functional identity.",
            "Re-render the same primary camera before another independent gate.",
        ],
    },
    {
        "iteration": 14,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/iteration-14-rejected-thin-ship-crane-read-1280x720.png"
        ),
        "proofSha256": (
            "966fa058223ab630a28c8da289b3cb1a29347a7bdc0d210f8021cd905c2ca136"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Checkpoint windows and roofs converted the wall masses into booths.",
            "The open central lane and customs portal depth remained readable.",
            "The ship bow and lattice crane were still too thin for instant identity.",
            "Left hero needed one more layer of enclosed process volumes.",
        ],
        "requiredChanges": [
            "Add forecastle deck, anchor hawses and a bow identity stripe.",
            "Thicken crane chords, web, cable and hook at the locked camera scale.",
            "Add supported west cantilever process pods to the stackhouse.",
            "Lighten matte asphalt slightly to reveal its authored rough grain.",
        ],
    },
    {
        "iteration": 15,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/"
            "iteration-15-rejected-midtonedensity-central-read-1280x720.png"
        ),
        "proofSha256": (
            "ec1b92502ab3e378ab5826f8777cca18a15a5548e273f94e4dce8df1fe262f97"
        ),
        "comparison": (
            "Original ImageGen reference inspected at native resolution; "
            "luminance and edge-density deltas measured at 1280x720."
        ),
        "findings": [
            "Vehicle wheels, cab glazing and clustered work crews now read clearly.",
            "Portal cargo and west process pods improved functional occupation.",
            "A22 median luminance remained 0.171 versus 0.265 in the reference.",
            "A22 edge density remained 0.067 versus 0.213 in the reference.",
            "Central ship and crane silhouettes were still subordinate to empty sky.",
        ],
        "requiredChanges": [
            "Lift steel and rust midtones without flattening local warm practicals.",
            "Scale the drydock ship's bow, bridge and mast for immediate identity.",
            "Build a true two-sided crane truss with counterweight and platform.",
            "Add enclosed north service volumes to the left hero without cloning bays.",
        ],
    },
    {
        "iteration": 16,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/"
            "iteration-16-rejected-foreshortened-crane-road-void-1280x720.png"
        ),
        "proofSha256": (
            "6fd190436712d20af14c45a8f7c0b2f30c612661dcd4fac46d55ddaf7faa65a5"
        ),
        "comparison": "Original ImageGen reference inspected at native resolution.",
        "findings": [
            "Raised red hull, white bridge and mast gave the ship instant identity.",
            "Enclosed north service rooms improved the left hero's mass hierarchy.",
            "The mobile crane boom remained foreshortened into a near-vertical bar.",
            "The foreground route still lacked reference-level markings and grating.",
            "Median luminance rose to 0.178, but edge density only reached 0.068.",
        ],
        "requiredChanges": [
            "Swing the mobile boom across the image plane and relocate its hoist.",
            "Add faded centre dashes, skid traces, drains and round service covers.",
            "Give lead forklifts grounded pallet loads and clearer human work poses.",
            "Increase facade louver and pipe rhythm on both hero elevations.",
        ],
    },
    {
        "iteration": 17,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/"
            "iteration-17-rejected-independent-detail-density-gate-1280x720.png"
        ),
        "proofSha256": (
            "9bfd307561f3145548867b0792d8e75e79473efe53a81b6b5583a8105356c5c9"
        ),
        "comparison": "Independent original-resolution ten-category review.",
        "findings": [
            "Independent average reached 6.78 and readability reached 7.0.",
            "Minimum category remained human scale and occupation at 6.3.",
            "Material, architecture, density and identity remained below 7.0.",
            "Edge density improved to 0.075 but stayed below the 0.10 next gate.",
            "Foreground flanks and hero interiors still contained broad blank zones.",
        ],
        "requiredChanges": [
            "Segment both foreground flanks with supported cargo work clusters.",
            "Layer ship side detail and additional open city or gantry silhouettes.",
            "Fill left scaffold and right portals with light and machine grids.",
            "Add warning, numbering, leak, oil and edge-wear baked detail.",
            "Raise worker and vehicle silhouette detail one final production step.",
        ],
        "independentScores": {
            "composition": 7.2,
            "heroRead": 6.9,
            "architecture": 6.7,
            "humanScale": 6.3,
            "materialResponse": 6.7,
            "density": 6.6,
            "readability": 7.0,
            "props": 6.9,
            "lighting": 6.8,
            "identity": 6.7,
            "arithmeticMean": 6.78,
            "minimum": 6.3,
        },
    },
    {
        "iteration": 18,
        "verdict": "REJECTED",
        "proofPath": (
            "self-review/"
            "iteration-18-rejected-flat-foreground-edge-gate-1280x720.png"
        ),
        "proofSha256": (
            "90613329a5f3a9d3f719dd5f5fcb4b838e19683d32fc9aa05da882c6646e1225"
        ),
        "comparison": (
            "Original-resolution visual audit plus native forward-luminance "
            "edge-density measurement."
        ),
        "findings": [
            "Foreground cargo, portal AGVs and interior machine grids rendered.",
            "Ship plating and the third gantry layer improved central occupation.",
            "Independent average reached 6.83 with a 6.4 minimum.",
            "Mean and median luminance held at 0.281 and 0.195.",
            "Edge density stayed flat at 0.075 versus the 0.10 next gate.",
            "The lower road quadrants remained much flatter than the reference.",
        ],
        "requiredChanges": [
            "Add grounded loading-bay grids and expansion seams near the camera.",
            "Break foreground asphalt with readable repairs and drainage rhythm.",
            "Keep the canonical central route open and all markings non-blocking.",
            "Increase hero facade relief without adding a third mega-landmark.",
            "Re-run the independent gate only after objective edge density rises.",
        ],
        "independentScores": {
            "composition": 7.2,
            "heroRead": 6.9,
            "architecture": 6.8,
            "humanScale": 6.4,
            "materialResponse": 6.7,
            "density": 6.8,
            "readability": 7.0,
            "props": 7.0,
            "lighting": 6.8,
            "identity": 6.7,
            "arithmeticMean": 6.83,
            "minimum": 6.4,
        },
    },
    {
        "iteration": 21,
        "verdict": "REJECTED_GENERIC_BLOCKOUT",
        "proofPath": (
            "self-review/"
            "iteration-21-candidate-hero-finish-independent-gate-1280x720.png"
        ),
        "proofSha256": (
            "ff305adc745027f9a97ea6e100b0e517beb2acfa5fa88d68172ac96f3e0e79d8"
        ),
        "comparison": (
            "Controlling independent side-by-side review at both files' "
            "original resolutions."
        ),
        "findings": [
            "The controlling independent average was 5.3 with a 4.0 minimum.",
            "Generic-blockout evidence overrides all higher producer/root estimates.",
            "Both landmarks lacked castle-scale breadth and connected heavy mass.",
            "The ship-side port, far world and purposeful dock clusters were sparse.",
            "Flat materials, razor edges and rectangular puddles looked unfinished.",
        ],
        "requiredChanges": [
            "Rebuild both anchors as connected monumental architectural masses.",
            "Place real water, quay wall and a readable ship in the primary view.",
            "Close the vanishing point with layered real 3D industrial geometry.",
            "Replace the 128px flat treatment with restrained 256px PBR atlases.",
            "Recompose and relight for contact shadow and warm/cool depth separation.",
        ],
        "independentScores": {
            "composition": 6.0,
            "heroRead": 6.0,
            "architecture": 5.0,
            "humanScale": 6.0,
            "materialResponse": 4.0,
            "density": 4.0,
            "readability": 7.0,
            "props": 5.0,
            "lighting": 5.0,
            "identity": 5.0,
            "arithmeticMean": 5.3,
            "minimum": 4.0,
            "genericBlockout": True,
        },
    },
    {
        "iteration": 22,
        "verdict": "REJECTED_GENERIC_BLOCKOUT",
        "proofPath": (
            "self-review/"
            "iteration-22-candidate-p0-material-mass-rebuild-1280x720.png"
        ),
        "proofSha256": (
            "a46eb909b7f629481be32dfa504f326309ab1e2d66180821eb17e5de704d1108"
        ),
        "comparison": (
            "Controlling independent original-resolution comparison against "
            "the fixed ImageGen reference."
        ),
        "findings": [
            "The controlling independent average was 5.2 with a 4.0 minimum.",
            "The ship, water and quay were outside or at the edge of the fixed frame.",
            "The left hero stayed narrow and the customs hall remained fragmented.",
            "Orange grille and black-cap repetition dominated functional materials.",
            "Near, mid and far occupation remained well below the reference.",
        ],
        "requiredChanges": [
            "Keep ship hull and water within horizontal NDC 0.75.",
            "Build supported voids and a heavy occupied Rack-Bridge volume.",
            "Unify the customs sawtooth hall, bays, tower and roof service.",
            "Reallocate repeated warning microdetail into large port silhouettes.",
            "Add real quay machinery, foreground work and a dense 3D skyline.",
        ],
        "independentScores": {
            "composition": 6.0,
            "heroRead": 6.0,
            "architecture": 5.0,
            "humanScale": 5.0,
            "materialResponse": 4.0,
            "density": 4.0,
            "readability": 7.0,
            "props": 5.0,
            "lighting": 5.0,
            "identity": 5.0,
            "arithmeticMean": 5.2,
            "minimum": 4.0,
            "genericBlockout": True,
        },
    },
)


def _render_proof(
    bpy: Any,
    args: argparse.Namespace,
    *,
    source_sha: str,
    input_records: Mapping[str, Any],
) -> dict[str, Any]:
    backend = _load_module("hibana_souko_a22_backend_proof", BACKEND_PATH)
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
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    _set_camera(camera, PRIMARY_CAMERA)
    bpy.context.view_layer.update()
    blend_path = PRIVATE_OUTPUT_ROOT / "work/souko-a22-production-art-lod0.blend"
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
            "resolution": list(_png_size(output_path)),
            "eyeRuntimeM": list(view["eye"]),
            "targetRuntimeM": list(view["target"]),
            "lensMm": view["lensMm"],
            "purpose": view["purpose"],
            "containmentHits": containment_hits,
            "renderPreflight": preflight,
        })
    _set_camera(camera, PRIMARY_CAMERA)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    report = {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "privateOnly": True,
        "backgroundOnly": True,
        "liveBlenderTouched": False,
        "inputProvenance": input_records,
        "referenceComparison": {
            "path": str(IMAGEGEN_REFERENCE_PATH),
            "sha256": IMAGEGEN_REFERENCE_SHA256,
            "originalResolution": list(_png_size(IMAGEGEN_REFERENCE_PATH)),
            "comparisonMode": "original-resolution reference versus 1280 proof",
            "a21BlindClone": False,
        },
        "sourceModule": str(MODULE_PATH),
        "sourceModuleSha256": source_sha,
        "blendPath": str(blend_path),
        "blendSha256": _sha256(blend_path),
        "metrics": metrics,
        "geometry": {
            key: value for key, value in geometry.items()
            if key not in {"collection", "meshObjects"}
        },
        "cameraContract": PRIMARY_CAMERA,
        "renderSettings": {
            "engine": scene.render.engine,
            "resolution": [args.width, args.height],
            "dof": False,
            "harbourHaze": True,
            "warmPracticals": True,
        },
        "pbrStrategy": {
            "textureResolution": [256, 256],
            "baseColorMaps": True,
            "roughnessMaps": True,
            "normalMaps": True,
            "broadRainStreaks": True,
            "rustRuns": True,
            "worldProjectedUv": True,
            "blackWindowCards": 0,
            "realGlassDepth": True,
        },
        "selfReviewHistory": list(SELF_REVIEW_HISTORY),
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


GLB_BUDGETS = {
    0: {
        "minTriangles": 160_000, "maxTriangles": 240_000,
        "maxBytes": 5_000_000, "maxPrimitives": 12,
    },
    1: {
        "minTriangles": 45_000, "maxTriangles": 85_000,
        "maxBytes": 2_500_000, "maxPrimitives": 12,
    },
    2: {
        "minTriangles": 12_000, "maxTriangles": 25_000,
        "maxBytes": 1_250_000, "maxPrimitives": 12,
    },
}


def _optimize_glb(raw_path: Path, output_path: Path) -> dict[str, Any]:
    cli = REPO_ROOT / "node_modules/.bin/gltf-transform"
    if not cli.is_file():
        shutil.move(str(raw_path), str(output_path))
        return {"tool": None, "meshopt": False, "fallbackMove": True}
    completed = subprocess.run(
        [
            str(cli), "optimize", str(raw_path), str(output_path),
            "--compress", "meshopt",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    raw_path.unlink(missing_ok=True)
    return {
        "tool": str(cli), "meshopt": True, "fallbackMove": False,
        "stdoutTail": completed.stdout[-1000:],
        "stderrTail": completed.stderr[-1000:],
    }


def _export_lods(
    bpy: Any,
    *,
    source_sha: str,
    input_records: Mapping[str, Any],
) -> dict[str, Any]:
    backend = _load_module("hibana_souko_a22_backend_export", BACKEND_PATH)
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
        raw_path = export_dir / f".souko-a22-lod{lod}-raw.glb"
        output_path = export_dir / f"souko-a22-production-art-lod{lod}.glb"
        bpy.ops.export_scene.gltf(
            filepath=str(raw_path),
            export_format="GLB",
            use_selection=True,
            export_extras=True,
            export_yup=True,
            export_apply=False,
        )
        optimization = _optimize_glb(raw_path, output_path)
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
            "modifierCount": geometry["modifierCount"],
            "optimization": optimization,
        })
    report = {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "privateOnly": True,
        "backgroundOnly": True,
        "liveBlenderTouched": False,
        "inputProvenance": input_records,
        "sourceModule": str(MODULE_PATH),
        "sourceModuleSha256": source_sha,
        "bakedRoleSpecificProfiles": True,
        "exports": records,
        "elapsedSeconds": round(time.time() - started, 3),
    }
    _write_json(PRIVATE_OUTPUT_ROOT / "export-report.json", report)
    return report


def audit_private_glbs() -> dict[str, Any]:
    validator = _load_module("hibana_souko_a22_validator", VALIDATOR_PATH)
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
        if not budget["minTriangles"] <= inspected["triangles"] <= budget["maxTriangles"]:
            errors.append("triangle-band")
        if inspected["primitives"] > budget["maxPrimitives"]:
            errors.append("draw-calls")
        if not 8 <= inspected["materials"] <= 12:
            errors.append("materials")
        inspected.update({
            "lod": lod,
            "budget": budget,
            "budgetErrors": errors,
            "budgetPass": not errors,
            "metadataPass": not inspected["metadataErrors"],
            "releasePbrPass": not inspected["pbrErrors"],
        })
        records.append(inspected)
    report = {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "sourceModuleSha256": export_report["sourceModuleSha256"],
        "technicalBudgetPass": all(item["budgetPass"] for item in records),
        "metadataPass": all(item["metadataPass"] for item in records),
        "releasePbrPass": all(item["releasePbrPass"] for item in records),
        "blackWindowCardCount": 0,
        "producerStatus": "NO-SHIP",
        "records": records,
    }
    _write_json(PRIVATE_OUTPUT_ROOT / "glb-audit.json", report)
    return report


def _write_producer_summary(
    proof: Mapping[str, Any] | None,
    export_report: Mapping[str, Any] | None,
    audit: Mapping[str, Any] | None,
    input_records: Mapping[str, Any],
) -> dict[str, Any]:
    payload = producer_provisional_scorecard()
    payload.update({
        "sourceModuleSha256": _sha256(MODULE_PATH),
        "inputProvenance": input_records,
        "technicalBudgetPass": bool(audit and audit["technicalBudgetPass"]),
        "metadataPass": bool(audit and audit["metadataPass"]),
        "releasePbrPass": bool(audit and audit["releasePbrPass"]),
        "exactLandmarkIds": [STACKHOUSE_ID, CUSTOMS_ID],
        "materialCount": len(MATERIALS),
        "blackWindowCardCount": 0,
        "bakedRoleSpecificProfiles": True,
        "selfReviewHistory": list(SELF_REVIEW_HISTORY),
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
                    "evaluatedTriangles": item["rawMeshTriangles"],
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


def _write_proof_manifest() -> dict[str, Any]:
    manifest_path = PRIVATE_OUTPUT_ROOT / "proof-manifest.json"
    entries = []
    for path in sorted(PRIVATE_OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        entries.append({
            "path": str(path.relative_to(PRIVATE_OUTPUT_ROOT)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    payload = {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "privateOutputRoot": str(PRIVATE_OUTPUT_ROOT),
        "producerStatus": "NO-SHIP",
        "artifactCount": len(entries),
        "artifacts": entries,
    }
    _write_json(manifest_path, payload)
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
    cli = list(
        sys.argv[sys.argv.index("--") + 1:]
        if "--" in sys.argv else sys.argv[1:]
    )
    args = _parse_cli(cli if argv is None else argv)
    PRIVATE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_records = _verify_inputs()
    source_sha = _sha256(MODULE_PATH)
    proof = None
    export_report = None
    audit = None
    if args.action == "audit":
        audit = audit_private_glbs()
        producer = _write_producer_summary(
            None, None, audit, input_records,
        )
        manifest = _write_proof_manifest()
        print(json.dumps({
            "audit": audit, "producer": producer, "manifest": manifest,
        }, indent=2))
        return 0

    import bpy

    if not bpy.app.background:
        raise RuntimeError("A22 production script is background-only")
    if args.action in {"proof", "all"}:
        proof = _render_proof(
            bpy, args, source_sha=source_sha, input_records=input_records,
        )
    if args.action in {"export", "all"}:
        export_report = _export_lods(
            bpy, source_sha=source_sha, input_records=input_records,
        )
    if args.action == "all":
        audit = audit_private_glbs()
    producer = _write_producer_summary(
        proof, export_report, audit, input_records,
    )
    manifest = _write_proof_manifest()
    print(json.dumps({
        "proof": proof,
        "export": export_report,
        "audit": audit,
        "producer": producer,
        "manifest": manifest,
    }, indent=2))
    return 0


__all__ = [
    "A21_INDEPENDENT_SCORECARD_SHA256", "A21_SCORECARD_PATH",
    "CANONICAL_BOUNDS", "CANONICAL_PLAYER_SPAWNS", "CANONICAL_ROADS",
    "CHAMFER_BANDS_M", "CUSTOMS_ID", "DEFAULT_INTEGRATION_MATERIAL_MAP",
    "FIXED_SCORE_CATEGORIES", "GLB_BUDGETS", "IMAGEGEN_REFERENCE_PATH",
    "IMAGEGEN_REFERENCE_SHA256", "LANDMARKS", "LOD_API", "LOD_TARGETS",
    "MATERIALS", "MATERIAL_EXPORT_SUFFIX", "MIN_CONTACT_OVERLAP_M",
    "PLAYER_EYE_M", "PRIMARY_CAMERA", "PRIMARY_CAMERA_PROJECTION_POINTS",
    "PRIMARY_CAMERA_SCREEN_REGIONS", "PRIVATE_OUTPUT_ROOT", "PRIVATE_VIEWS",
    "PRIMARY_SHORE_ROLES", "ITERATION29C_CUSTOMS_SCREEN_POINTS",
    "REFERENCE_MATCH_VERSION", "REFERENCE_PATH", "REFERENCE_SHA256",
    "SELF_REVIEW_HISTORY", "STACKHOUSE_ID", "STAGE_ID", "SpecPlan",
    "audit_private_glbs", "build_plan", "camera_containment_hits",
    "camera_horizontal_ndc", "camera_ndc", "emit_plan", "estimated_triangles",
    "plan_metrics", "primary_quay_edge_x",
    "producer_provisional_scorecard", "route_intrusions",
    "shore_route_intrusions", "spawn_intrusions", "spec_bounds",
    "validate_plan",
]


if __name__ == "__main__":
    raise SystemExit(main())
