#!/usr/bin/env python3
"""Independent Souko A20 reference-first art rebuild plan.

This module owns a deterministic, Blender-free geometry plan for a private
Souko rebuild.  It never imports or edits ``build_all_stages.py`` or the A18
prototype, and it has no public/runtime side effects.  Runtime coordinates are
X/Z horizontal and Y-up, in metres.

Reference-led production brief
------------------------------
* Fix the primary shot first: a 1.65 m eye on the north-west quay, 28 mm lens,
  Rack-Bridge Storehouse on frame-left and Customs Sawtooth Terminal on right.
* Stackhouse is four completed, occupied process towers with deep rack floors,
  a castle-scale transfer bridge, smaller service bridge, windows and plant.
* Customs is a heavy terminal with exactly four full-depth glazed sawteeth,
  visible trusses/purlins, loading base, control tower and two chimneys.
* Continuous foreground depth is real geometry: camera pier, wet service road,
  loading shed, pallets, forklifts, rail, containers, quay, ship and cranes.
* The horizon is layered 3D architecture/port infrastructure; raster mattes,
  image planes, cylindrical pictures and flat-background shortcuts are banned.
* Shared materials encode plausible concrete, zinc, steel, rust, wetness and
  glass response.  Micro-detail belongs in material relief, not loose geometry.

Connection map (minimum designed overlap 0.005 m)
--------------------------------------------------
* industrial ground <-> roads/pads/quay: 0.02-0.18 m
* hero plinths <-> tower/base feet: 0.12-0.24 m
* stackhouse piers <-> floor slabs/envelopes/roof plant: 0.08-0.24 m
* stackhouse tower B <-> main bridge <-> tower D: 0.22 m at each end
* stackhouse tower A <-> service bridge <-> tower B: 0.18 m at each end
* customs plinth <-> loading base/occupied bays: 0.16-0.24 m
* occupied bays <-> four roof/glass planes/trusses: 0.10-0.20 m
* customs deck <-> control tower/chimneys: 0.15-0.20 m
* loading shed slab <-> posts/walls/roof: 0.10-0.18 m
* quay <-> rails/bollards/cranes; ship hull <-> deck/bridge: 0.10-0.24 m

Every directional member is represented by explicit endpoints.  There are no
ambiguous primitive-scale assumptions or Euler-rotated cylinders.
"""

from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


STAGE_ID = "souko"
REFERENCE_MATCH_VERSION = "a20-souko-art-rebuild-v1"
REFERENCE_PATH = "tools/blender/concepts/souko-reference-v1.png"
REFERENCE_SHA256 = "967c0e599e687d59bdcb0057ed84bebe7816de15772c5a6532e3d64b52d4eef6"
IMAGEGEN_REFERENCE_PATH = Path(
    "/private/tmp/hibana-blender/a20-souko-art-rebuild/reference/"
    "souko-a20-imagegen-reference.png"
)
IMAGEGEN_REFERENCE_SHA256 = "fb3bd642434e83f5c22c23d23bbc24ef2cba7245402c4b20433306a989e55db5"
INDEPENDENT_A19_BASELINE_SCORE = 4.54
PRIVATE_OUTPUT_ROOT = Path("/private/tmp/hibana-blender/a20-souko-art-rebuild")
TARGET_COLLECTION = "HB_SOUKO_A20_PRIVATE"
MAP_SIZE_M = 336.0
PLAYER_EYE_M = 1.65
MIN_CONTACT_OVERLAP_M = 0.005

CANONICAL_BOUNDS = {
    "min_x": -168.0,
    "max_x": 168.0,
    "min_z": -168.0,
    "max_z": 168.0,
}
CANONICAL_ROADS = (
    {
        "id": "primary-north-south",
        "bounds": {"minX": -8.0, "maxX": 8.0, "minZ": -164.0, "maxZ": 164.0},
    },
    {
        "id": "primary-east-west",
        "bounds": {"minX": -164.0, "maxX": 164.0, "minZ": -8.0, "maxZ": 8.0},
    },
)
CANONICAL_PLAYER_SPAWNS = (
    (-156.0, 0.0, 0.0),
    (0.0, 0.0, -156.0),
    (156.0, 0.0, 0.0),
    (0.0, 0.0, 156.0),
)

STACKHOUSE_ID = "souko-shiosai-stackhouse"
CUSTOMS_ID = "souko-amakado-customs-terminal"
LANDMARKS = (
    {
        "index": 0,
        "id": STACKHOUSE_ID,
        "referenceName": "Rack-Bridge Storehouse",
        "cx": 80.8,
        "cz": 96.0,
        "rot": 0.0,
        "width": 104.0,
        "depth": 66.0,
        "canonicalHeight": 64.0,
        "visualCrownHeight": 126.0,
        "entrance": (28.0, 96.0),
        "approach": {"start": (8.0, 96.0), "end": (28.0, 96.0), "width": 12.0},
        "collisionTemplate": "bridge",
    },
    {
        "index": 1,
        "id": CUSTOMS_ID,
        "referenceName": "Customs Sawtooth Terminal",
        "cx": -68.0,
        "cz": -67.8,
        "rot": 0.0,
        "width": 92.0,
        "depth": 78.0,
        "canonicalHeight": 47.0,
        "visualCrownHeight": 92.0,
        "entrance": (-68.0, -28.0),
        "approach": {"start": (-68.0, -8.0), "end": (-68.0, -28.0), "width": 12.0},
        "collisionTemplate": "hall",
    },
)

# The first shot is a non-negotiable A20 contract, not a render-time guess.
PRIMARY_CAMERA: dict[str, Any] = {
    "id": "01-a20-dual-hero-working-quay",
    "eye": (-205.0, PLAYER_EYE_M, 145.0),
    "target": (3.0, 31.0, 15.0),
    "lensMm": 26.0,
    "sensorWidthMm": 36.0,
    "frameOrder": (STACKHOUSE_ID, CUSTOMS_ID),
    "skyMaxFraction": 0.20,
    "roadMaxFraction": 0.24,
    "heroHorizontalFillTarget": (0.80, 0.96),
    "purpose": "Tight ImageGen-locked dual-hero identity view from an occupied wet quay.",
}

PRIVATE_VIEWS: tuple[dict[str, Any], ...] = (
    PRIMARY_CAMERA,
    {
        "id": "02-stackhouse-arrival",
        "eye": (-24.0, PLAYER_EYE_M, 24.0),
        "target": (80.0, 42.0, 97.0),
        "lensMm": 30.0,
        "purpose": "Occupied four-tower silhouette and bridge arrival.",
    },
    {
        "id": "03-stackhouse-rack-interior",
        "eye": (2.0, PLAYER_EYE_M, 96.0),
        "target": (35.0, 10.0, 96.0),
        "lensMm": 24.0,
        "purpose": "Human-eye view through a real portal aisle, rack floors, cargo and catwalks.",
    },
    {
        "id": "04-stackhouse-rack-elevation",
        "eye": (0.0, PLAYER_EYE_M, 118.0),
        "target": (82.0, 65.0, 100.0),
        "lensMm": 26.0,
        "purpose": "Low west rack elevation, loaded decks, stairs and transfer bridge underside.",
    },
    {
        "id": "05-customs-loading-approach",
        "eye": (-136.0, PLAYER_EYE_M, 22.0),
        "target": (-68.0, 31.0, -56.0),
        "lensMm": 28.0,
        "purpose": "Loading base, four glazed teeth, control tower and chimneys.",
    },
    {
        "id": "06-customs-sawtooth-depth",
        "eye": (-5.0, PLAYER_EYE_M, 17.0),
        "target": (-68.0, 35.0, -64.0),
        "lensMm": 27.0,
        "purpose": "Four full-depth sawtooth planes, trusses and occupied bays.",
    },
    {
        "id": "07-loading-life",
        "eye": (-225.0, PLAYER_EYE_M, 170.0),
        "target": (-150.0, 4.5, 150.0),
        "lensMm": 28.0,
        "purpose": "Occupied diagonal yard, truck, pallets, forklift, rail and wet curb.",
    },
    {
        "id": "08-quay-ship-cranes",
        "eye": (-150.0, PLAYER_EYE_M, 230.0),
        "target": (-45.0, 28.0, 188.0),
        "lensMm": 32.0,
        "purpose": "Quay, ship, three cranes, rails, containers and real sea.",
    },
)

LOD_API = {
    0: {"label": "hero", "maxSpecs": 5200, "maxEstimatedTriangles": 240_000},
    1: {"label": "medium", "maxSpecs": 2800, "maxEstimatedTriangles": 120_000},
    2: {"label": "horizon", "maxSpecs": 1350, "maxEstimatedTriangles": 52_000},
}

MATERIALS: dict[str, dict[str, Any]] = {
    "wet_asphalt": {
        "color": (0.018, 0.027, 0.031, 1.0), "roughness": 0.18, "metallic": 0.0,
        "noise": 0.28, "wetVariation": True,
    },
    "puddle_water": {
        "color": (0.018, 0.055, 0.067, 1.0), "roughness": 0.075,
        "metallic": 0.03, "transmission": 0.16,
    },
    "old_concrete": {
        "color": (0.27, 0.255, 0.225, 1.0), "roughness": 0.82,
        "metallic": 0.0, "noise": 0.30, "stains": True,
    },
    "pale_concrete": {
        "color": (0.43, 0.415, 0.365, 1.0), "roughness": 0.72,
        "metallic": 0.0, "noise": 0.23, "stains": True,
    },
    "dark_concrete": {
        "color": (0.045, 0.060, 0.064, 1.0), "roughness": 0.73,
        "metallic": 0.0, "noise": 0.23, "stains": True,
    },
    "weathered_zinc": {
        "color": (0.16, 0.245, 0.255, 1.0), "roughness": 0.39,
        "metallic": 0.74, "noise": 0.22, "rustMask": True,
    },
    "structural_steel": {
        "color": (0.035, 0.052, 0.057, 1.0), "roughness": 0.44,
        "metallic": 0.90, "noise": 0.16, "rustMask": True,
    },
    "red_brick": {
        "color": (0.18, 0.050, 0.026, 1.0), "roughness": 0.84,
        "metallic": 0.0, "noise": 0.20, "stains": True,
    },
    "rust": {
        "color": (0.29, 0.050, 0.012, 1.0), "roughness": 0.84,
        "metallic": 0.02, "noise": 0.24,
    },
    "safety_orange": {
        "color": (0.55, 0.105, 0.015, 1.0), "roughness": 0.43,
        "metallic": 0.0, "noise": 0.07,
    },
    "dirty_glass": {
        "color": (0.025, 0.095, 0.115, 0.58), "roughness": 0.16,
        "metallic": 0.05, "transmission": 0.58, "alpha": 0.58, "noise": 0.10,
    },
    "warm_glass": {
        "color": (0.29, 0.095, 0.022, 1.0), "roughness": 0.24,
        "metallic": 0.0, "emission": (0.42, 0.105, 0.012, 1.0),
        "emissionStrength": 1.25,
    },
    "paint_white": {
        "color": (0.72, 0.69, 0.60, 1.0), "roughness": 0.59,
        "metallic": 0.0, "noise": 0.04,
    },
    "pallet_wood": {
        "color": (0.21, 0.095, 0.035, 1.0), "roughness": 0.75,
        "metallic": 0.0, "noise": 0.17,
    },
    "sea_water": {
        "color": (0.012, 0.095, 0.13, 1.0), "roughness": 0.13,
        "metallic": 0.14, "noise": 0.05,
    },
    "vegetation": {
        "color": (0.045, 0.09, 0.045, 1.0), "roughness": 0.84,
        "metallic": 0.0, "noise": 0.10,
    },
}

DEFAULT_INTEGRATION_MATERIAL_MAP = {
    "wet_asphalt": "floor", "puddle_water": "water",
    "old_concrete": "wall_weathered", "pale_concrete": "wall",
    "dark_concrete": "wall_cool", "weathered_zinc": "roof",
    "structural_steel": "trim", "red_brick": "wall_warm",
    "rust": "wall_alt", "safety_orange": "accent",
    "dirty_glass": "glass", "warm_glass": "emissive",
    "paint_white": "wall", "pallet_wood": "wood",
    "sea_water": "water", "vegetation": "natural",
}

FIXED_SCORE_CATEGORIES = (
    "composition", "hero silhouettes", "architectural grammar", "human scale",
    "material realism", "near/mid/far density", "gameplay readability",
    "props and environmental storytelling", "lighting and atmosphere",
    "reference identity",
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


class SpecPlan:
    """Pure-data geometry plan with explicit contact records."""

    def __init__(self, lod: int):
        if lod not in LOD_API:
            raise ValueError(f"unsupported LOD: {lod}")
        self.lod = lod
        self.specs: list[dict[str, Any]] = []
        self.connections: list[dict[str, Any]] = []
        self._counts: Counter[tuple[str, str]] = Counter()

    def _name(self, group: str, role: str, name: str | None) -> str:
        if name:
            resolved = name
        else:
            key = (_slug(group), _slug(role))
            self._counts[key] += 1
            resolved = f"{key[0]}.{key[1]}.{self._counts[key]:03d}"
        if any(spec["name"] == resolved for spec in self.specs):
            raise ValueError(f"duplicate spec name: {resolved}")
        return resolved

    @staticmethod
    def _base(
        name: str,
        role: str,
        material: str,
        group: str,
        layer: str,
        blocks_gameplay: bool,
        outside_playable: bool,
    ) -> dict[str, Any]:
        if material not in MATERIALS:
            raise ValueError(f"unknown material: {material}")
        if layer not in {"near", "mid", "far"}:
            raise ValueError(f"invalid layer: {layer}")
        return {
            "name": name,
            "role": role,
            "material": material,
            "group": group,
            "layer": layer,
            "blocksGameplay": blocks_gameplay,
            "outsidePlayable": outside_playable,
        }

    def box(
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
        *,
        yaw: float = 0.0,
        layer: str = "mid",
        blocks_gameplay: bool = False,
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        if not _finite((x, y, z, w, h, d, yaw)) or min(w, h, d) <= 0:
            raise ValueError(f"{role}: invalid box")
        resolved = self._name(group, role, name)
        kind = "box" if abs(yaw) < 1e-9 else "oriented_box"
        self.specs.append({
            **self._base(
                resolved, role, material, group, layer, blocks_gameplay, outside_playable,
            ),
            "kind": kind,
            "x": float(x), "y": float(y), "z": float(z),
            "w": float(w), "h": float(h), "d": float(d), "yaw": float(yaw),
        })
        return resolved

    def beam(
        self,
        role: str,
        material: str,
        group: str,
        start: Sequence[float],
        end: Sequence[float],
        width: float,
        depth: float,
        *,
        layer: str = "mid",
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        start = tuple(float(value) for value in start)
        end = tuple(float(value) for value in end)
        values = (*start, *end, width, depth)
        if len(start) != 3 or len(end) != 3 or not _finite(values):
            raise ValueError(f"{role}: invalid beam")
        if math.dist(start, end) < 1e-6 or min(width, depth) <= 0:
            raise ValueError(f"{role}: zero beam")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(resolved, role, material, group, layer, False, outside_playable),
            "kind": "beam", "start": start, "end": end,
            "width": float(width), "depth": float(depth),
        })
        return resolved

    def cylinder(
        self,
        role: str,
        material: str,
        group: str,
        x: float,
        y: float,
        z: float,
        radius: float,
        height: float,
        segments: int,
        *,
        top_radius: float | None = None,
        layer: str = "mid",
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        top_radius = radius if top_radius is None else top_radius
        if not _finite((x, y, z, radius, height, top_radius)):
            raise ValueError(f"{role}: invalid cylinder")
        if min(radius, height) <= 0 or segments < 3 or top_radius < 0:
            raise ValueError(f"{role}: invalid cylinder dimensions")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(resolved, role, material, group, layer, False, outside_playable),
            "kind": "cylinder", "x": float(x), "y": float(y), "z": float(z),
            "radius": float(radius), "height": float(height),
            "segments": int(segments), "topRadius": float(top_radius),
        })
        return resolved

    def panel(
        self,
        role: str,
        material: str,
        group: str,
        corners: Iterable[Sequence[float]],
        thickness: float,
        *,
        layer: str = "mid",
        outside_playable: bool = False,
        name: str | None = None,
    ) -> str:
        corners = tuple(tuple(float(value) for value in point) for point in corners)
        if len(corners) not in {3, 4} or any(len(point) != 3 for point in corners):
            raise ValueError(f"{role}: panel requires three or four corners")
        values = (*[value for point in corners for value in point], thickness)
        if not _finite(values) or thickness <= 0:
            raise ValueError(f"{role}: invalid panel")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(resolved, role, material, group, layer, False, outside_playable),
            "kind": "panel", "corners": corners, "thickness": float(thickness),
        })
        return resolved

    def connect(
        self,
        parent: str,
        child: str,
        *,
        axis: str,
        overlap_m: float,
        parent_face: str,
        child_face: str,
        note: str = "",
    ) -> None:
        if overlap_m < MIN_CONTACT_OVERLAP_M:
            raise ValueError(f"contact overlap too small: {parent} -> {child}")
        self.connections.append({
            "id": f"{_slug(parent)}--{_slug(child)}--{len(self.connections):04d}",
            "parent": parent, "child": child, "axis": axis,
            "parentFace": parent_face, "childFace": child_face,
            "overlapM": float(overlap_m), "note": note,
        })


def _role_count(specs: Iterable[Mapping[str, Any]], role: str) -> int:
    return sum(spec["role"] == role for spec in specs)


def _segment_box(
    plan: SpecPlan,
    role: str,
    material: str,
    group: str,
    start: tuple[float, float],
    end: tuple[float, float],
    y: float,
    height: float,
    width: float,
    *,
    layer: str,
) -> str:
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    return plan.box(
        role, material, group,
        (start[0] + end[0]) / 2, y, (start[1] + end[1]) / 2,
        length, height, width, yaw=math.atan2(dz, dx), layer=layer,
    )


def _add_guardrail(
    plan: SpecPlan,
    group: str,
    start: tuple[float, float],
    end: tuple[float, float],
    deck_y: float,
    *,
    posts: int,
    layer: str = "near",
) -> None:
    for rail_y, size in ((deck_y + 0.55, 0.055), (deck_y + 1.10, 0.075)):
        plan.beam(
            "human-scale-guardrail", "structural_steel", group,
            (start[0], rail_y, start[1]), (end[0], rail_y, end[1]),
            size, size, layer=layer,
        )
    for index in range(max(2, posts)):
        t = index / max(1, posts - 1)
        x = start[0] + (end[0] - start[0]) * t
        z = start[1] + (end[1] - start[1]) * t
        plan.beam(
            "human-scale-guardrail", "structural_steel", group,
            (x, deck_y - 0.04, z), (x, deck_y + 1.14, z),
            0.055, 0.055, layer=layer,
        )


def _add_pallet_stack(
    plan: SpecPlan, group: str, x: float, z: float, lod: int, *, layer: str = "near",
) -> None:
    levels = 3 if lod == 0 else 2 if lod == 1 else 1
    for level in range(levels):
        base_y = 0.12 + level * 0.30
        slats = 4 if lod == 0 else 3
        for index in range(slats):
            plan.box(
                "pallet-slat", "pallet_wood", group,
                x - 0.52 + index * 1.04 / max(1, slats - 1), base_y, z,
                0.13, 0.12, 1.10, layer=layer,
            )
        plan.box(
            "pallet-cross-member", "pallet_wood", group,
            x, base_y - 0.02, z, 1.15, 0.10, 0.16, layer=layer,
        )
    if lod < 2:
        plan.box(
            "pallet-wrapped-load", "paint_white", group,
            x, 1.35, z, 1.05, 1.35, 1.02, layer=layer,
        )


def _add_container(
    plan: SpecPlan,
    group: str,
    x: float,
    z: float,
    yaw: float,
    material: str,
    lod: int,
    *,
    layer: str = "near",
    outside: bool = False,
) -> None:
    plan.box(
        "cargo-container-shell", material, group, x, 1.45, z,
        6.06, 2.90, 2.44, yaw=yaw, layer=layer, outside_playable=outside,
    )
    if lod < 2:
        rib_count = 5 if lod == 0 else 3
        dx, dz = math.cos(yaw), math.sin(yaw)
        for index in range(rib_count):
            along = -2.55 + 5.10 * index / max(1, rib_count - 1)
            plan.box(
                "cargo-container-rib", "structural_steel", group,
                x + dx * along, 1.47, z + dz * along,
                0.10, 2.72, 2.49, yaw=yaw, layer=layer,
                outside_playable=outside,
            )


def _add_forklift(
    plan: SpecPlan, group: str, x: float, z: float, yaw: float, lod: int,
) -> None:
    body = plan.box(
        "forklift-body", "safety_orange", group,
        x, 0.72, z, 1.55, 1.08, 2.25, yaw=yaw, layer="near",
    )
    plan.box(
        "forklift-cab", "dark_concrete", group,
        x - math.cos(yaw) * 0.25, 1.65, z - math.sin(yaw) * 0.25,
        1.38, 1.25, 1.45, yaw=yaw, layer="near",
    )
    dx, dz = math.cos(yaw), math.sin(yaw)
    px, pz = -dz, dx
    for side in (-1.0, 1.0):
        mast_x, mast_z = x + dx * 1.34 + px * side * 0.55, z + dz * 1.34 + pz * side * 0.55
        mast = plan.beam(
            "forklift-mast", "structural_steel", group,
            (mast_x, 0.22, mast_z), (mast_x, 2.75, mast_z),
            0.11, 0.10, layer="near",
        )
        plan.connect(body, mast, axis="surface", overlap_m=0.08,
                     parent_face="front", child_face="base")
        if lod == 0:
            plan.beam(
                "forklift-fork", "structural_steel", group,
                (mast_x, 0.20, mast_z),
                (mast_x + dx * 1.45, 0.20, mast_z + dz * 1.45),
                0.10, 0.08, layer="near",
            )


def _add_worker(
    plan: SpecPlan, group: str, x: float, z: float, yaw: float, *, layer: str = "near",
) -> None:
    """Add a measured 1.78 m dock worker as an environment scale cue."""
    plan.cylinder(
        "human-scale-dock-worker-torso", "safety_orange", group,
        x, 1.10, z, 0.25, 0.92, 10, top_radius=0.20, layer=layer,
    )
    plan.cylinder(
        "human-scale-dock-worker-head", "pallet_wood", group,
        x, 1.67, z, 0.17, 0.30, 10, top_radius=0.16, layer=layer,
    )
    dx, dz = math.cos(yaw), math.sin(yaw)
    px, pz = -dz, dx
    for side in (-1.0, 1.0):
        plan.box(
            "human-scale-dock-worker-leg", "dark_concrete", group,
            x - dx * 0.03 + px * side * 0.11, 0.42,
            z - dz * 0.03 + pz * side * 0.11,
            0.15, 0.78, 0.16, yaw=yaw, layer=layer,
        )
        plan.beam(
            "human-scale-dock-worker-arm", "safety_orange", group,
            (x + px * side * 0.22, 1.35, z + pz * side * 0.22),
            (x + px * side * 0.33 + dx * 0.08, 0.92,
             z + pz * side * 0.33 + dz * 0.08),
            0.11, 0.10, layer=layer,
        )


def _add_yard_truck(
    plan: SpecPlan, group: str, x: float, z: float, yaw: float, lod: int,
) -> None:
    dx, dz = math.cos(yaw), math.sin(yaw)
    trailer = plan.box(
        "human-scale-yard-truck-trailer", "weathered_zinc", group,
        x, 1.75, z, 8.6, 3.25, 2.55, yaw=yaw, layer="near",
    )
    cab = plan.box(
        "human-scale-yard-truck-cab", "safety_orange", group,
        x + dx * 5.4, 1.45, z + dz * 5.4,
        2.4, 2.70, 2.45, yaw=yaw, layer="near",
    )
    plan.connect(trailer, cab, axis="surface", overlap_m=0.12,
                 parent_face="front", child_face="rear")
    plan.box(
        "human-scale-yard-truck-windscreen", "dirty_glass", group,
        x + dx * 6.65, 2.05, z + dz * 6.65,
        0.22, 1.05, 1.95, yaw=yaw, layer="near",
    )
    wheel_positions = (-3.2, 2.8, 5.4) if lod == 0 else (-2.8, 5.2)
    for along in wheel_positions:
        for side in (-1.0, 1.0):
            plan.box(
                "human-scale-yard-truck-wheel", "dark_concrete", group,
                x + dx * along - dz * side * 1.22, 0.46,
                z + dz * along + dx * side * 1.22,
                0.62, 0.92, 0.34, yaw=yaw, layer="near",
            )


def _add_gabled_warehouse(
    plan: SpecPlan,
    group: str,
    label: str,
    x: float,
    z: float,
    w: float,
    d: float,
    h: float,
    yaw: float,
    lod: int,
    *,
    layer: str,
    outside: bool = False,
) -> None:
    shell = plan.box(
        "bonded-warehouse-shell", "red_brick" if int(abs(x + z)) % 2 else "old_concrete",
        group, x, h * 0.48, z, w, h * 0.96, d, yaw=yaw, layer=layer,
        outside_playable=outside, name=f"{group}.{label}.shell",
    )
    dx, dz = math.cos(yaw), math.sin(yaw)
    px, pz = -dz, dx
    hw, hd = w / 2, d / 2
    ridge_h = h + min(5.5, w * 0.16)
    left_front = (x - dx * hw - px * hd, h, z - dz * hw - pz * hd)
    left_back = (x - dx * hw + px * hd, h, z - dz * hw + pz * hd)
    right_front = (x + dx * hw - px * hd, h, z + dz * hw - pz * hd)
    right_back = (x + dx * hw + px * hd, h, z + dz * hw + pz * hd)
    ridge_front = (x - px * hd, ridge_h, z - pz * hd)
    ridge_back = (x + px * hd, ridge_h, z + pz * hd)
    for role, corners in (
        ("bonded-warehouse-roof", (left_front, ridge_front, ridge_back, left_back)),
        ("bonded-warehouse-roof", (ridge_front, right_front, right_back, ridge_back)),
    ):
        roof = plan.panel(
            role, "weathered_zinc", group, corners, 0.30,
            layer=layer, outside_playable=outside,
        )
        plan.connect(shell, roof, axis="surface", overlap_m=0.10,
                     parent_face="top", child_face="eave")
    if lod < 2:
        for bay in range(3 if lod == 0 else 2):
            along = (-0.28 + 0.28 * bay) * w
            bx = x + dx * along - px * (hd + 0.08)
            bz = z + dz * along - pz * (hd + 0.08)
            plan.box(
                "bonded-warehouse-loading-door", "dark_concrete", group,
                bx, 3.0, bz, min(4.8, w * 0.18), 5.4, 0.22,
                yaw=yaw, layer=layer, outside_playable=outside,
            )
            plan.box(
                "bonded-warehouse-loading-light", "warm_glass", group,
                bx, 6.4, bz - 0.12, 0.50, 0.28, 0.16,
                yaw=yaw, layer=layer, outside_playable=outside,
            )


def _add_external_stair_run(
    plan: SpecPlan,
    group: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
    lod: int,
    *,
    layer: str = "mid",
) -> None:
    """Add a measured open steel stair with stringers, treads and handrails."""
    dx, dz = end[0] - start[0], end[2] - start[2]
    horizontal = math.hypot(dx, dz)
    if horizontal < 0.25:
        raise ValueError("external stair requires a horizontal run")
    ux, uz = dx / horizontal, dz / horizontal
    px, pz = -uz, ux
    side_offset = width * 0.42
    for side in (-1.0, 1.0):
        plan.beam(
            "industrial-stair-stringer", "structural_steel", group,
            (start[0] + px * side_offset * side, start[1],
             start[2] + pz * side_offset * side),
            (end[0] + px * side_offset * side, end[1],
             end[2] + pz * side_offset * side),
            0.20 if lod == 0 else 0.30,
            0.16 if lod == 0 else 0.24, layer=layer,
        )
        plan.beam(
            "industrial-stair-handrail", "structural_steel", group,
            (start[0] + px * side_offset * side, start[1] + 1.0,
             start[2] + pz * side_offset * side),
            (end[0] + px * side_offset * side, end[1] + 1.0,
             end[2] + pz * side_offset * side),
            0.07, 0.07, layer=layer,
        )
    step_count = 13 if lod == 0 else 7 if lod == 1 else 4
    tread_yaw = math.atan2(pz, px)
    for index in range(step_count):
        t = index / max(1, step_count - 1)
        plan.box(
            "industrial-stair-tread", "weathered_zinc", group,
            start[0] + dx * t, start[1] + (end[1] - start[1]) * t,
            start[2] + dz * t,
            width, 0.18 if lod == 0 else 0.26, 0.58,
            yaw=tread_yaw, layer=layer,
        )


def _build_ground_and_foreground(plan: SpecPlan, lod: int) -> None:
    group = "souko-a20-public-realm"
    plan.box(
        "playable-industrial-ground", "old_concrete", group,
        0.0, -0.38, 0.0, 335.4, 0.70, 335.4, layer="far",
        name=f"{group}.ground",
    )
    plan.box(
        "camera-quay-apron", "old_concrete", group,
        -124.0, -0.34, 193.0, 288.0, 0.72, 52.0,
        layer="near", outside_playable=True, name=f"{group}.camera-apron",
    )
    plan.box(
        "fixed-camera-pier", "dark_concrete", group,
        -240.0, 0.12, 170.0, 28.0, 0.42, 18.0,
        layer="near", outside_playable=True, name=f"{group}.camera-pier",
    )
    plan.box(
        "wet-primary-road", "wet_asphalt", group,
        0.0, 0.02, 0.0, 16.0, 0.12, 328.0, layer="near",
        name=f"{group}.road.ns",
    )
    plan.box(
        "wet-primary-road", "wet_asphalt", group,
        0.0, 0.03, 0.0, 328.0, 0.14, 16.0, layer="near",
        name=f"{group}.road.ew",
    )

    start, end = (-234.0, 170.0), (5.0, 14.0)
    road = _segment_box(
        plan, "wet-diagonal-bonded-service-road", "wet_asphalt", group,
        start, end, 0.055, 0.16, 15.0, layer="near",
    )
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    for side in (-1.0, 1.0):
        curb = plan.beam(
            "service-road-curb", "pale_concrete", group,
            (start[0] + px * 7.65 * side, 0.20, start[1] + pz * 7.65 * side),
            (end[0] + px * 7.65 * side, 0.20, end[1] + pz * 7.65 * side),
            0.42, 0.32, layer="near",
        )
        plan.connect(road, curb, axis="surface", overlap_m=0.02,
                     parent_face="edge", child_face="bottom")
    if lod < 2:
        dash_count = 14 if lod == 0 else 8
        road_yaw = math.atan2(dz, dx)
        for index in range(dash_count):
            distance = 12.0 + index * (length - 28.0) / max(1, dash_count - 1)
            plan.box(
                "service-road-faded-centre-dash", "paint_white", group,
                start[0] + ux * distance, 0.145, start[1] + uz * distance,
                5.0, 0.028, 0.16, yaw=road_yaw, layer="near",
            )
        # Occupied road edges: drainage, battered retaining segments, lamps
        # and bollards compress the vista without entering the clear lane.
        edge_samples = 7 if lod == 0 else 4
        for side in (-1.0, 1.0):
            for index in range(edge_samples):
                t = 0.10 + index * 0.72 / max(1, edge_samples - 1)
                edge_x = start[0] + dx * t + px * side * 9.2
                edge_z = start[1] + dz * t + pz * side * 9.2
                plan.box(
                    "service-road-retaining-block",
                    "old_concrete" if index % 2 == 0 else "dark_concrete",
                    group, edge_x, 0.66, edge_z,
                    7.5, 1.25, 0.70, yaw=road_yaw, layer="near",
                )
                plan.box(
                    "service-road-linear-drain", "structural_steel", group,
                    edge_x - px * side * 1.05, 0.12,
                    edge_z - pz * side * 1.05,
                    6.8, 0.08, 0.30, yaw=road_yaw, layer="near",
                )
                if index % 2 == 0:
                    plan.beam(
                        "service-road-lamp-post", "structural_steel", group,
                        (edge_x + px * side * 0.6, 0.18,
                         edge_z + pz * side * 0.6),
                        (edge_x + px * side * 0.6, 8.2,
                         edge_z + pz * side * 0.6),
                        0.20, 0.20, layer="near",
                    )
                    plan.beam(
                        "service-road-lamp-arm", "structural_steel", group,
                        (edge_x + px * side * 0.6, 8.0,
                         edge_z + pz * side * 0.6),
                        (edge_x - px * side * 1.8, 8.0,
                         edge_z - pz * side * 1.8),
                        0.15, 0.15, layer="near",
                    )
                    plan.box(
                        "service-road-lamp-head", "warm_glass", group,
                        edge_x - px * side * 2.0, 7.95,
                        edge_z - pz * side * 2.0,
                        0.70, 0.24, 0.35, yaw=road_yaw, layer="near",
                    )
                plan.cylinder(
                    "service-road-bollard", "safety_orange", group,
                    edge_x - px * side * 1.75, 0.55,
                    edge_z - pz * side * 1.75,
                    0.15, 1.05, 8, top_radius=0.13, layer="near",
                )
            rail_start_t, rail_end_t = 0.06, 0.86
            _add_guardrail(
                plan, group,
                (
                    start[0] + dx * rail_start_t + px * side * 9.55,
                    start[1] + dz * rail_start_t + pz * side * 9.55,
                ),
                (
                    start[0] + dx * rail_end_t + px * side * 9.55,
                    start[1] + dz * rail_end_t + pz * side * 9.55,
                ),
                0.30, posts=18 if lod == 0 else 10, layer="near",
            )

    puddles = (
        (-176.0, 196.0, 13.0, 4.0, -0.18),
        (-154.0, 169.0, 8.0, 3.4, 0.12),
        (-131.0, 141.0, 12.0, 4.2, -0.09),
        (-100.0, 103.0, 9.0, 3.6, 0.16),
        (-67.0, 63.0, 11.0, 4.0, -0.11),
        (-34.0, 24.0, 8.5, 3.0, 0.08),
        (-4.8, -118.0, 6.2, 13.0, 0.02),
        (4.5, -70.0, 5.2, 10.0, -0.02),
        (-4.0, 33.0, 5.8, 12.0, 0.04),
    )
    step = 1 if lod == 0 else 2 if lod == 1 else 3
    for index, (x, z, w, d, yaw) in enumerate(puddles[::step]):
        plan.box(
            "wet-road-puddle", "puddle_water", group,
            x, 0.145 + index * 0.0003, z, w, 0.035, d,
            yaw=yaw, layer="near",
        )

    # The near loading shed is a cropped, occupied left-edge frame in the
    # primary camera.  Its open face points north-west toward the 1.65 m eye;
    # the earlier central canopy hid both heroes and read as a floating slab.
    shed_group = "souko-a20-camera-loading-shed"
    shed_x, shed_z = -111.0, 153.0
    shed_width, shed_depth = 44.0, 25.0
    slab = plan.box(
        "foreground-loading-shed-slab", "wet_asphalt", shed_group,
        shed_x, 0.18, shed_z, shed_width, 0.48, shed_depth,
        yaw=-0.05, layer="near", name=f"{shed_group}.slab",
    )
    post_xs = (-92.0, -104.7, -117.3, -130.0)
    post_names = []
    for x in post_xs:
        for z in (164.0, 142.0):
            post = plan.box(
                "foreground-loading-shed-post", "structural_steel", shed_group,
                x, 4.8, z, 0.65, 9.4, 0.65, layer="near",
            )
            plan.connect(slab, post, axis="y", overlap_m=0.14,
                         parent_face="top", child_face="bottom")
            post_names.append(post)
    roof = plan.box(
        "foreground-loading-shed-roof", "weathered_zinc", shed_group,
        shed_x, 9.55, shed_z, shed_width + 0.8, 0.65, shed_depth + 0.8,
        yaw=-0.05, layer="near", name=f"{shed_group}.roof",
    )
    plan.connect(post_names[0], roof, axis="y", overlap_m=0.12,
                 parent_face="top", child_face="bottom")
    rear = plan.box(
        "foreground-loading-shed-rear-wall", "red_brick", shed_group,
        shed_x, 4.7, shed_z - shed_depth * 0.48,
        shed_width - 1.8, 9.2, 0.65,
        yaw=-0.05, layer="near", name=f"{shed_group}.rear",
    )
    plan.connect(slab, rear, axis="y", overlap_m=0.16,
                 parent_face="top", child_face="bottom")
    if lod < 2:
        for bay in range(4 if lod == 0 else 3):
            x = -95.0 - bay * 10.7
            plan.box(
                "foreground-loading-bay-deep-recess", "dark_concrete", shed_group,
                x, 3.65, shed_z + shed_depth * 0.505,
                8.3, 6.9, 0.58, layer="near",
            )
            plan.box(
                "foreground-loading-bay-door", "dark_concrete", shed_group,
                x, 3.45, shed_z + shed_depth * 0.535,
                6.9, 6.25, 0.22, layer="near",
            )
            plan.box(
                "foreground-loading-bay-lamp", "warm_glass", shed_group,
                x, 7.55, shed_z + shed_depth * 0.555,
                0.55, 0.32, 0.18, layer="near",
            )
            if lod == 0:
                for slat in range(5):
                    plan.box(
                        "foreground-loading-door-slat", "weathered_zinc", shed_group,
                        x, 0.80 + slat * 1.25,
                        shed_z + shed_depth * 0.548,
                        6.55, 0.10, 0.12, layer="near",
                    )
        _add_guardrail(plan, shed_group, (-89.5, 165.2), (-132.5, 165.2),
                       0.42, posts=12 if lod == 0 else 7)

    cluster_points = (
        (-84.0, 158.0), (-94.0, 158.0), (-132.0, 159.0),
        (-126.0, 157.0), (-139.0, 161.0), (-142.0, 153.0),
        (-88.0, 141.0), (-139.0, 139.0),
    )
    for index, (x, z) in enumerate(cluster_points[::(1 if lod == 0 else 2)]):
        _add_pallet_stack(plan, shed_group, x, z, lod)
        # Leave the player's north-east loading-bay sightline open.  Clusters
        # zero and two keep pallets/workers but move their large container mass
        # to the other asymmetric groups instead of walling off the shed proof.
        if index % 2 == 0 and index not in {0, 2}:
            _add_container(
                plan, shed_group, x - 3.5, z + 2.5,
                0.08 if index % 3 else math.pi / 2,
                "safety_orange" if index % 3 == 0 else "weathered_zinc",
                lod, layer="near",
            )
    if lod < 2:
        _add_forklift(plan, shed_group, -104.0, 170.0, -2.59, lod)
        _add_forklift(plan, shed_group, -140.0, 150.0, -0.99, lod)
        _add_yard_truck(plan, shed_group, -166.0, 145.0, -0.36, lod)
        worker_points = (
            (-132.0, 164.0, 0.20),
            (-119.0, 168.0, -0.55),
            (-102.0, 165.5, 1.10),
            (-88.0, 158.0, -1.70),
        )
        for x, z, yaw in worker_points[::(1 if lod == 0 else 2)]:
            _add_worker(plan, shed_group, x, z, yaw)

    # Two real rail lines continue the foreground toward the bonded city.
    for side in (-1.0, 1.0):
        plan.beam(
            "quay-cargo-rail", "rust", group,
            (-68.0 + side * 0.9, 0.22, 174.0),
            (-154.0 + side * 0.9, 0.22, 174.0),
            0.16, 0.12, layer="near", outside_playable=True,
        )
    if lod == 0:
        for x in range(-70, -156, -3):
            plan.box(
                "quay-rail-sleeper", "pallet_wood", group,
                float(x), 0.12, 174.0, 0.28, 0.14, 3.0,
                layer="near", outside_playable=True,
            )


def _add_stackhouse_tower(
    plan: SpecPlan,
    label: str,
    x: float,
    z: float,
    width: float,
    depth: float,
    height: float,
    lod: int,
    plinth: str,
) -> dict[str, Any]:
    group = STACKHOUSE_ID
    tower_base = plan.box(
        "stackhouse-tower-base", "old_concrete", group,
        x, 0.52, z, width + 1.0, 1.05, depth + 1.0,
        layer="mid", blocks_gameplay=True, name=f"{group}.{label}.base",
    )
    plan.connect(plinth, tower_base, axis="y", overlap_m=0.18,
                 parent_face="top", child_face="bottom")
    open_height = 17.0
    pier_names = []
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            pier = plan.box(
                "stackhouse-grounded-pier", "pale_concrete", group,
                x + sx * (width / 2 - 1.05), open_height / 2,
                z + sz * (depth / 2 - 1.05),
                1.8 if lod == 0 else 2.3, open_height + 0.4,
                1.8 if lod == 0 else 2.3, layer="mid",
            )
            plan.connect(tower_base, pier, axis="y", overlap_m=0.18,
                         parent_face="top", child_face="bottom")
            pier_names.append(pier)

    lower_floor_names = []
    # A20 deliberately keeps the 0–16 m undercroft vertically open.  The A19
    # floor stack formed an opaque ceiling at eye height and hid the racks.
    lower_levels = (16.1,)
    for index, floor_y in enumerate(lower_levels):
        floor = plan.box(
            "stackhouse-open-interior-floor", "weathered_zinc", group,
            x, floor_y, z, width, 0.55 if lod == 0 else 0.78, depth,
            layer="mid", name=f"{group}.{label}.open-floor.{index}",
        )
        plan.connect(pier_names[index % len(pier_names)], floor, axis="surface",
                     overlap_m=0.10, parent_face="side", child_face="corner")
        lower_floor_names.append(floor)

    envelope_bottom = 16.0
    headhouse_height = 7.0
    envelope_top = height - headhouse_height
    envelope = plan.box(
        "stackhouse-completed-tower-envelope",
        "pale_concrete" if label in {"a", "c"} else "old_concrete",
        group, x, (envelope_bottom + envelope_top) / 2, z + depth * 0.04,
        width * 0.88, envelope_top - envelope_bottom, depth * 0.82,
        layer="mid", blocks_gameplay=True,
        name=f"{group}.{label}.completed-envelope",
    )
    plan.connect(lower_floor_names[-1], envelope, axis="y", overlap_m=0.16,
                 parent_face="top", child_face="bottom")

    floor_step = 6.8 if lod == 0 else 9.5 if lod == 1 else 14.0
    floor_count = max(2, int((envelope_top - envelope_bottom) // floor_step))
    facade_z = z - depth * 0.415
    facade_x = x + width * 0.445
    for level in range(floor_count):
        y = envelope_bottom + 4.0 + level * (envelope_top - envelope_bottom - 7.0) / max(1, floor_count - 1)
        plan.box(
            "stackhouse-window-recess", "dark_concrete",
            group, x, y, facade_z - 0.12,
            width * (0.68 if level % 2 == 0 else 0.76), 2.75, 0.44,
            layer="mid",
        )
        window_width = width * (0.52 if level % 2 == 0 else 0.60)
        plan.box(
            "stackhouse-occupied-window-band",
            "warm_glass" if level % 3 == 0 else "dirty_glass",
            group, x, y, facade_z - 0.40,
            window_width, 1.55, 0.20,
            layer="mid",
        )
        if lod == 0:
            for mullion in (-0.25, 0.0, 0.25):
                plan.box(
                    "stackhouse-window-mullion", "structural_steel", group,
                    x + window_width * mullion, y, facade_z - 0.54,
                    0.14, 1.85, 0.14, layer="mid",
                )
            for side in (-1.0, 1.0):
                plan.box(
                    "stackhouse-window-deep-jamb", "rust", group,
                    x + side * width * 0.35, y, facade_z - 0.35,
                    0.26, 2.85, 0.34, layer="mid",
                )
        plan.box(
            "stackhouse-facade-rust-belt", "rust", group,
            x, y + 1.22, facade_z - 0.20, width * 0.78, 0.22, 0.28,
            layer="mid",
        )
        if lod < 2:
            plan.box(
                "stackhouse-side-window-band", "dirty_glass", group,
                facade_x + 0.10, y + 0.55, z,
                0.22, 1.4, depth * 0.48, layer="mid",
            )
    for side in (-1.0, 1.0):
        plan.box(
            "stackhouse-envelope-corner-spine", "structural_steel", group,
            x + side * width * 0.45,
            (envelope_bottom + envelope_top) / 2,
            facade_z - 0.16, 0.46, envelope_top - envelope_bottom + 0.6, 0.40,
            layer="mid",
        )
    if lod < 2:
        # Deep, recessed logistics bays and two continuous catwalks turn the
        # tower from a slab stack into an occupied process building.
        bay_count = 3 if lod == 0 else 2
        for bay in range(bay_count):
            bay_x = x - width * 0.27 + bay * width * 0.54 / max(1, bay_count - 1)
            plan.box(
                "stackhouse-recessed-logistics-bay", "dark_concrete", group,
                bay_x, envelope_bottom + 4.6, facade_z - 0.26,
                width * 0.20, 5.8, 0.34, layer="mid",
            )
            plan.box(
                "stackhouse-logistics-bay-header", "safety_orange", group,
                bay_x, envelope_bottom + 7.65, facade_z - 0.35,
                width * 0.23, 0.34, 0.30, layer="mid",
            )
        catwalk_levels = (
            envelope_bottom + 11.0,
            envelope_bottom + (envelope_top - envelope_bottom) * 0.58,
        )
        for catwalk_y in catwalk_levels:
            deck_z = facade_z - 1.05
            plan.box(
                "stackhouse-occupied-catwalk", "weathered_zinc", group,
                x, catwalk_y, deck_z, width * 0.92, 0.26, 1.75,
                layer="mid",
            )
            _add_guardrail(
                plan, group,
                (x - width * 0.43, deck_z - 0.72),
                (x + width * 0.43, deck_z - 0.72),
                catwalk_y + 0.12,
                posts=7 if lod == 0 else 4,
                layer="mid",
            )
        for riser in (-0.31, 0.31):
            plan.cylinder(
                "stackhouse-facade-process-riser", "rust", group,
                x + width * riser,
                (envelope_bottom + envelope_top) / 2,
                facade_z - 0.54,
                0.28 if lod == 0 else 0.42,
                envelope_top - envelope_bottom - 1.2,
                9 if lod == 0 else 7,
                top_radius=0.24 if lod == 0 else 0.36,
                layer="mid",
            )
    if lod == 0:
        for streak in range(4):
            streak_x = x - width * 0.28 + streak * width * 0.19
            streak_h = 7.0 + streak * 2.2
            plan.box(
                "stackhouse-rust-runoff-streak", "rust", group,
                streak_x, envelope_bottom + 1.5 + streak_h / 2,
                facade_z - 0.26, 0.10, streak_h, 0.11, layer="mid",
            )

    # Primary-camera faces are west (x-) and north (z+).  They receive their
    # own deep facade hierarchy; decorating only the opposite faces produced
    # the blank concrete monoliths visible in the first A19 proof.
    west_x = x - width * 0.455
    north_z = z + depth * 0.425
    primary_rows = 5 if lod == 0 else 3 if lod == 1 else 2
    for row in range(primary_rows):
        y = envelope_bottom + 8.0 + row * (
            envelope_top - envelope_bottom - 15.0
        ) / max(1, primary_rows - 1)
        west_span = depth * (0.64 if row % 2 == 0 else 0.52)
        north_span = width * (0.66 if row % 2 == 0 else 0.54)
        plan.box(
            "stackhouse-primary-west-window-recess", "dark_concrete", group,
            west_x - 0.16, y, z, 0.52, 4.8, west_span, layer="mid",
        )
        plan.box(
            "stackhouse-primary-west-window", 
            "warm_glass" if (row + ord(label)) % 3 == 0 else "dirty_glass",
            group, west_x - 0.48, y, z, 0.18, 2.65, west_span * 0.78,
            layer="mid",
        )
        plan.box(
            "stackhouse-primary-north-window-recess", "dark_concrete", group,
            x, y + 0.45, north_z + 0.16,
            north_span, 4.8, 0.52, layer="mid",
        )
        plan.box(
            "stackhouse-primary-north-window",
            "warm_glass" if (row + ord(label)) % 4 == 0 else "dirty_glass",
            group, x, y + 0.45, north_z + 0.48,
            north_span * 0.78, 2.65, 0.18, layer="mid",
        )
        if lod == 0:
            for offset in (-0.25, 0.0, 0.25):
                plan.box(
                    "stackhouse-primary-west-window-mullion", "rust", group,
                    west_x - 0.60, y, z + west_span * offset,
                    0.14, 2.95, 0.14, layer="mid",
                )
                plan.box(
                    "stackhouse-primary-north-window-mullion", "rust", group,
                    x + north_span * offset, y + 0.45, north_z + 0.60,
                    0.14, 2.95, 0.14, layer="mid",
                )
        plan.box(
            "stackhouse-primary-west-weathering-belt", "rust", group,
            west_x - 0.44, y + 2.48, z,
            0.20, 0.26, west_span + 0.7, layer="mid",
        )
        plan.box(
            "stackhouse-primary-north-weathering-belt", "rust", group,
            x, y + 2.93, north_z + 0.44,
            north_span + 0.7, 0.26, 0.20, layer="mid",
        )

    # Heavy exoskeleton, inhabited lower intake bays, catwalks, pipes and an
    # open stair turn the camera-facing walls into working process facades.
    for z_offset in (-0.34, 0.34):
        plan.beam(
            "stackhouse-primary-west-exoskeleton", "structural_steel", group,
            (west_x - 0.55, envelope_bottom - 0.3, z + depth * z_offset),
            (west_x - 0.55, envelope_top + 0.3, z + depth * z_offset),
            0.42 if lod == 0 else 0.62,
            0.34 if lod == 0 else 0.52, layer="mid",
        )
    for x_offset in (-0.34, 0.34):
        plan.beam(
            "stackhouse-primary-north-exoskeleton", "structural_steel", group,
            (x + width * x_offset, envelope_bottom - 0.3, north_z + 0.55),
            (x + width * x_offset, envelope_top + 0.3, north_z + 0.55),
            0.42 if lod == 0 else 0.62,
            0.34 if lod == 0 else 0.52, layer="mid",
        )
    intake_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for intake in range(intake_count):
        intake_z = z - depth * 0.27 + intake * depth * 0.54 / max(1, intake_count - 1)
        plan.box(
            "stackhouse-primary-west-deep-intake", "dark_concrete", group,
            west_x - 0.32, envelope_bottom + 4.8, intake_z,
            0.58, 8.2, depth * 0.18, layer="mid",
        )
        plan.box(
            "stackhouse-primary-west-cargo-silhouette",
            "safety_orange" if intake == 1 else "structural_steel", group,
            west_x - 0.67, envelope_bottom + 3.8, intake_z,
            0.18, 4.8, depth * 0.11, layer="mid",
        )
        plan.box(
            "stackhouse-primary-west-intake-header", "rust", group,
            west_x - 0.60, envelope_bottom + 9.0, intake_z,
            0.22, 0.42, depth * 0.20, layer="mid",
        )
    if lod < 2:
        primary_catwalks = (
            envelope_bottom + 14.0,
            envelope_bottom + (envelope_top - envelope_bottom) * 0.62,
        )
        for catwalk_y in primary_catwalks:
            plan.box(
                "stackhouse-primary-west-catwalk", "weathered_zinc", group,
                west_x - 1.05, catwalk_y, z,
                1.80, 0.28, depth * 0.88, layer="mid",
            )
            _add_guardrail(
                plan, group,
                (west_x - 1.82, z - depth * 0.41),
                (west_x - 1.82, z + depth * 0.41),
                catwalk_y + 0.14,
                posts=7 if lod == 0 else 4, layer="mid",
            )
        for pipe_z in (-0.23, 0.23):
            plan.cylinder(
                "stackhouse-primary-west-process-riser", "rust", group,
                west_x - 0.78,
                (envelope_bottom + envelope_top) / 2,
                z + depth * pipe_z,
                0.30 if lod == 0 else 0.46,
                envelope_top - envelope_bottom - 1.0,
                9 if lod == 0 else 7,
                top_radius=0.25 if lod == 0 else 0.38, layer="mid",
            )
        if label in {"a", "c"}:
            _add_external_stair_run(
                plan, group,
                (west_x - 2.20, envelope_bottom + 0.5, z - depth * 0.32),
                (west_x - 2.20, envelope_bottom + 13.9, z + depth * 0.32),
                1.65, lod, layer="mid",
            )

    head = plan.box(
        "stackhouse-roof-headhouse", "weathered_zinc", group,
        x + width * 0.08, envelope_top + headhouse_height * 0.48, z,
        width * 0.68, headhouse_height, depth * 0.65,
        layer="mid", name=f"{group}.{label}.headhouse",
    )
    plan.connect(envelope, head, axis="y", overlap_m=0.20,
                 parent_face="top", child_face="bottom")
    cap = plan.box(
        "stackhouse-roof-cap", "structural_steel", group,
        x + width * 0.08, height + 0.08, z,
        width * 0.74, 0.48, depth * 0.70,
        layer="mid", name=f"{group}.{label}.roof-cap",
    )
    plan.connect(head, cap, axis="y", overlap_m=0.16,
                 parent_face="top", child_face="bottom")
    if lod < 2:
        machine = plan.box(
            "stackhouse-roof-machine", "dark_concrete", group,
            x - width * 0.14, height + 2.0, z,
            width * 0.32, 3.8, depth * 0.35, layer="mid",
        )
        plan.connect(cap, machine, axis="y", overlap_m=0.12,
                     parent_face="top", child_face="bottom")
        plan.cylinder(
            "stackhouse-roof-exhaust", "rust", group,
            x + width * 0.22, height + 3.4, z - depth * 0.12,
            0.72, 6.4, 12 if lod == 0 else 8, top_radius=0.54,
            layer="mid",
        )
    return {
        "label": label, "x": x, "z": z, "width": width, "depth": depth,
        "height": height, "envelope": envelope, "top": cap,
        "floorAnchors": lower_floor_names,
    }


def _add_transfer_bridge(
    plan: SpecPlan,
    label: str,
    start_tower: Mapping[str, Any],
    end_tower: Mapping[str, Any],
    bottom: float,
    top: float,
    depth: float,
    lod: int,
) -> None:
    group = STACKHOUSE_ID
    start = (float(start_tower["x"]), float(start_tower["z"]))
    end = (float(end_tower["x"]), float(end_tower["z"]))
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    yaw = math.atan2(dz, dx)
    mx, mz = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    floor = plan.box(
        "stackhouse-deep-transfer-bridge-floor", "weathered_zinc", group,
        mx, bottom + 0.34, mz, length + 3.2, 0.68, depth,
        yaw=yaw, layer="mid", name=f"{group}.{label}.floor",
    )
    roof = plan.box(
        "stackhouse-deep-transfer-bridge-roof", "structural_steel", group,
        mx, top - 0.30, mz, length + 3.2, 0.60, depth + 0.4,
        yaw=yaw, layer="mid", name=f"{group}.{label}.roof",
    )
    overlap = 0.22 if label == "main" else 0.18
    plan.connect(start_tower["envelope"], floor, axis="surface", overlap_m=overlap,
                 parent_face="facade", child_face="end")
    plan.connect(end_tower["envelope"], floor, axis="surface", overlap_m=overlap,
                 parent_face="facade", child_face="end")
    plan.connect(floor, roof, axis="frame", overlap_m=0.10,
                 parent_face="truss", child_face="truss")
    frames = 10 if lod == 0 else 7 if lod == 1 else 4
    for index in range(frames):
        t = index / max(1, frames - 1)
        bx, bz = start[0] + dx * t, start[1] + dz * t
        for side in (-1.0, 1.0):
            sx, sz = bx + px * depth * 0.5 * side, bz + pz * depth * 0.5 * side
            plan.beam(
                "stackhouse-bridge-portal", "structural_steel", group,
                (sx, bottom + 0.18, sz), (sx, top - 0.18, sz),
                0.26 if lod == 0 else 0.40,
                0.22 if lod == 0 else 0.34, layer="mid",
            )
        plan.beam(
            "stackhouse-bridge-portal", "structural_steel", group,
            (bx - px * depth * 0.5, top - 0.22, bz - pz * depth * 0.5),
            (bx + px * depth * 0.5, top - 0.22, bz + pz * depth * 0.5),
            0.26 if lod == 0 else 0.40,
            0.22 if lod == 0 else 0.34, layer="mid",
        )
    for side in (-1.0, 1.0):
        for index in range(frames - 1):
            t0, t1 = index / (frames - 1), (index + 1) / (frames - 1)
            ax = start[0] + dx * t0 + px * depth * 0.5 * side
            az = start[1] + dz * t0 + pz * depth * 0.5 * side
            bx = start[0] + dx * t1 + px * depth * 0.5 * side
            bz = start[1] + dz * t1 + pz * depth * 0.5 * side
            low, high = bottom + 0.65, top - 0.65
            ay, by = (low, high) if (index + (side > 0)) % 2 == 0 else (high, low)
            plan.beam(
                "stackhouse-bridge-diagonal", "rust", group,
                (ax, ay, az), (bx, by, bz),
                0.16 if lod == 0 else 0.26,
                0.12 if lod == 0 else 0.20, layer="mid",
            )
    if lod < 2:
        for side in (-1.0, 1.0):
            sx, sz = mx + px * (depth * 0.5 + 0.14) * side, mz + pz * (depth * 0.5 + 0.14) * side
            plan.box(
                "stackhouse-bridge-glazed-side", "dirty_glass", group,
                sx, (bottom + top) / 2, sz,
                length + 1.8, top - bottom - 1.7, 0.20,
                yaw=yaw, layer="mid",
            )
            plan.box(
                "stackhouse-bridge-weathered-spandrel", "old_concrete", group,
                sx, bottom + 1.30, sz,
                length + 2.2, 2.15, 0.42,
                yaw=yaw, layer="mid",
            )
            plan.box(
                "stackhouse-bridge-upper-window-header", "safety_orange", group,
                sx, top - 1.05, sz,
                length + 2.2, 0.46, 0.44,
                yaw=yaw, layer="mid",
            )
            plan.beam(
                "stackhouse-bridge-safety-chord", "safety_orange", group,
                (start[0] + px * depth * 0.5 * side, bottom + 1.3,
                 start[1] + pz * depth * 0.5 * side),
                (end[0] + px * depth * 0.5 * side, bottom + 1.3,
                 end[1] + pz * depth * 0.5 * side),
                0.32, 0.22, layer="mid",
            )
        plan.box(
            "stackhouse-bridge-occupied-transfer-room", "dark_concrete", group,
            mx, (bottom + top) / 2, mz,
            min(18.0, length * 0.32), top - bottom - 1.4, depth - 1.4,
            yaw=yaw, layer="mid",
        )


def _build_stackhouse(plan: SpecPlan, lod: int) -> None:
    group = STACKHOUSE_ID
    cx, cz = 80.8, 96.0
    plinth = plan.box(
        "stackhouse-collision-anchored-plinth", "old_concrete", group,
        cx, 0.22, cz, 102.8, 0.62, 64.8,
        layer="mid", blocks_gameplay=True, name=f"{group}.plinth",
    )
    configs = (
        ("a", cx - 37.0, cz - 14.0, 22.0, 29.0, 94.0),
        ("b", cx - 13.0, cz + 13.0, 25.0, 33.0, 120.0),
        ("c", cx + 16.0, cz - 12.0, 26.0, 31.0, 108.0),
        ("d", cx + 39.0, cz + 14.0, 20.0, 29.0, 101.0),
    )
    towers = {
        label: _add_stackhouse_tower(plan, label, x, z, w, d, h, lod, plinth)
        for label, x, z, w, d, h in configs
    }

    _add_transfer_bridge(plan, "main", towers["a"], towers["d"],
                         62.0, 79.0, 11.5, lod)
    if lod < 2:
        _add_transfer_bridge(plan, "service", towers["a"], towers["c"],
                             45.0, 58.0, 9.0, lod)

        # A shorter crown bridge sits on the camera-facing tier, separating
        # the Stackhouse silhouette from a row of unrelated tall slabs.
        crown_start = (towers["a"]["x"], towers["a"]["z"])
        crown_end = (towers["b"]["x"], towers["b"]["z"])
        crown_dx = crown_end[0] - crown_start[0]
        crown_dz = crown_end[1] - crown_start[1]
        crown_length = math.hypot(crown_dx, crown_dz)
        crown_px, crown_pz = -crown_dz / crown_length, crown_dx / crown_length
        crown_yaw = math.atan2(crown_dz, crown_dx)
        crown_mx = (crown_start[0] + crown_end[0]) / 2
        crown_mz = (crown_start[1] + crown_end[1]) / 2
        crown_floor = plan.box(
            "stackhouse-primary-crown-bridge-floor", "weathered_zinc", group,
            crown_mx, 83.35, crown_mz,
            crown_length + 3.2, 0.70, 7.5,
            yaw=crown_yaw, layer="mid",
        )
        crown_roof = plan.box(
            "stackhouse-primary-crown-bridge-roof", "structural_steel", group,
            crown_mx, 94.20, crown_mz,
            crown_length + 3.2, 0.60, 7.9,
            yaw=crown_yaw, layer="mid",
        )
        plan.connect(towers["a"]["envelope"], crown_floor, axis="surface",
                     overlap_m=0.18, parent_face="upper", child_face="start")
        plan.connect(towers["b"]["envelope"], crown_floor, axis="surface",
                     overlap_m=0.18, parent_face="upper", child_face="end")
        plan.connect(crown_floor, crown_roof, axis="frame", overlap_m=0.10,
                     parent_face="frame", child_face="frame")
        crown_frames = 6 if lod == 0 else 4
        for frame in range(crown_frames):
            t = frame / max(1, crown_frames - 1)
            bx = crown_start[0] + crown_dx * t
            bz = crown_start[1] + crown_dz * t
            for side in (-1.0, 1.0):
                sx = bx + crown_px * 3.75 * side
                sz = bz + crown_pz * 3.75 * side
                plan.beam(
                    "stackhouse-primary-crown-bridge-portal",
                    "structural_steel", group,
                    (sx, 83.5, sz), (sx, 94.0, sz),
                    0.24 if lod == 0 else 0.38,
                    0.20 if lod == 0 else 0.32, layer="mid",
                )
            plan.beam(
                "stackhouse-primary-crown-bridge-portal",
                "structural_steel", group,
                (bx - crown_px * 3.75, 93.9, bz - crown_pz * 3.75),
                (bx + crown_px * 3.75, 93.9, bz + crown_pz * 3.75),
                0.24 if lod == 0 else 0.38,
                0.20 if lod == 0 else 0.32, layer="mid",
            )
        for side in (-1.0, 1.0):
            side_x = crown_mx + crown_px * 3.90 * side
            side_z = crown_mz + crown_pz * 3.90 * side
            plan.box(
                "stackhouse-primary-crown-bridge-glazing", "dirty_glass", group,
                side_x, 88.7, side_z,
                crown_length + 1.8, 8.8, 0.20,
                yaw=crown_yaw, layer="mid",
            )
            for bay in range(crown_frames - 1):
                t0, t1 = bay / (crown_frames - 1), (bay + 1) / (crown_frames - 1)
                ax = crown_start[0] + crown_dx * t0 + crown_px * 3.75 * side
                az = crown_start[1] + crown_dz * t0 + crown_pz * 3.75 * side
                bx = crown_start[0] + crown_dx * t1 + crown_px * 3.75 * side
                bz = crown_start[1] + crown_dz * t1 + crown_pz * 3.75 * side
                ay, by = (84.2, 93.2) if (bay + (side > 0)) % 2 == 0 else (93.2, 84.2)
                plan.beam(
                    "stackhouse-primary-crown-bridge-diagonal", "rust", group,
                    (ax, ay, az), (bx, by, bz),
                    0.15 if lod == 0 else 0.24,
                    0.12 if lod == 0 else 0.20, layer="mid",
                )

    # Deep rack interior stays visible through and below the completed towers.
    x_stations = (35.0, 52.0, 69.0, 86.0, 103.0, 120.0)
    z_rows = (70.5, 95.5, 120.5)
    rack_top = 58.5
    upright_names = []
    for x in x_stations[::(1 if lod < 2 else 2)]:
        for z in z_rows:
            upright = plan.beam(
                "stackhouse-rack-upright", "structural_steel", group,
                (x, 0.48, z), (x, rack_top, z),
                0.38 if lod == 0 else 0.58, 0.38 if lod == 0 else 0.58,
                layer="mid",
            )
            plan.connect(plinth, upright, axis="y", overlap_m=0.16,
                         parent_face="top", child_face="bottom")
            upright_names.append(upright)
    rack_levels = (8.5, 18.0, 27.5, 37.0, 46.5, 58.0) if lod == 0 else (
        (10.0, 25.0, 41.0, 58.0) if lod == 1 else (14.0, 36.0, 58.0)
    )
    selected_x = x_stations[::(1 if lod < 2 else 2)]
    for z in z_rows:
        for level_index, y in enumerate(rack_levels):
            plan.beam(
                "stackhouse-rack-long-chord",
                "safety_orange" if level_index == 1 else "structural_steel",
                group, (selected_x[0], y, z), (selected_x[-1], y, z),
                0.26 if lod == 0 else 0.42, 0.22 if lod == 0 else 0.36,
                layer="mid",
            )
        for bay in range(len(selected_x) - 1):
            for level in range(len(rack_levels) - 1):
                if lod == 2 and level > 0:
                    continue
                ax, bx = selected_x[bay], selected_x[bay + 1]
                low, high = rack_levels[level], rack_levels[level + 1]
                ay, by = (low, high) if (bay + level) % 2 == 0 else (high, low)
                plan.beam(
                    "stackhouse-rack-cross-brace", "rust", group,
                    (ax, ay, z), (bx, by, z),
                    0.16 if lod == 0 else 0.27, 0.12 if lod == 0 else 0.20,
                    layer="mid",
                )
    for x in selected_x:
        for y in rack_levels:
            plan.beam(
                "stackhouse-rack-depth-tie", "structural_steel", group,
                (x, y, z_rows[0]), (x, y, z_rows[-1]),
                0.24 if lod == 0 else 0.40, 0.20 if lod == 0 else 0.34,
                layer="mid",
            )
    if lod < 2:
        cargo_step = 1 if lod == 0 else 2
        for zi, z in enumerate(z_rows):
            for li, y in enumerate(rack_levels[:-1: cargo_step]):
                for xi, x in enumerate((43.5, 60.5, 77.5, 94.5, 111.5)[::cargo_step]):
                    if (xi + li + zi) % 4 == 1:
                        continue
                    plan.box(
                        "stackhouse-deep-interior-cargo",
                        "safety_orange" if (xi + li) % 4 == 0 else "weathered_zinc",
                        group, x, y + 1.55, z, 6.06, 2.70, 2.44,
                        yaw=math.pi / 2, layer="mid",
                    )
                    if lod == 0:
                        for rib in (-2.45, 0.0, 2.45):
                            plan.box(
                                "stackhouse-deep-cargo-rib", "structural_steel", group,
                                x - 1.26, y + 1.58, z + rib,
                                0.14, 2.55, 0.12, layer="mid",
                            )
                    if lod == 0 and (xi + li) % 3 == 0:
                        plan.box(
                            "stackhouse-cargo-safety-stripe", "safety_orange", group,
                            x - 1.34, y + 1.85, z, 0.14, 0.24, 4.8,
                            layer="mid",
                        )
        # Low undercroft stacks sit outside the clear centre line and give the
        # human-height rack proof readable cargo silhouettes below the slabs.
        undercroft_xs = (52.0, 73.0, 94.0) if lod == 0 else (58.0, 88.0)
        for cargo_index, cargo_x in enumerate(undercroft_xs):
            for side in (-1.0, 1.0):
                plan.box(
                    "stackhouse-undercroft-container",
                    "safety_orange" if (cargo_index + (side > 0)) % 3 == 0
                    else "weathered_zinc",
                    group, cargo_x, 1.55, 96.0 + side * 7.5,
                    6.06, 2.70, 2.44, yaw=math.pi / 2, layer="mid",
                )
                if lod == 0:
                    plan.box(
                        "stackhouse-undercroft-container-face", "structural_steel",
                        group, cargo_x - 1.26, 1.58, 96.0 + side * 7.5,
                        0.14, 2.55, 4.9, layer="mid",
                    )

    # West playable arrival: loading wings frame, rather than close, the route.
    for side in (-1.0, 1.0):
        z = cz + side * 18.0
        wing = plan.box(
            "stackhouse-human-scale-loading-wing", "red_brick", group,
            32.2, 5.2, z, 7.2, 10.2, 15.5,
            layer="near", blocks_gameplay=True,
        )
        plan.connect(plinth, wing, axis="surface", overlap_m=0.14,
                     parent_face="edge", child_face="floor")
        plan.box(
            "stackhouse-recessed-hoist-door", "dark_concrete", group,
            28.5, 3.7, z, 0.22, 6.4, 8.5, layer="near",
        )
        plan.box(
            "stackhouse-loading-lamp", "warm_glass", group,
            28.35, 7.3, z, 0.16, 0.35, 0.72, layer="near",
        )
    if lod < 2:
        _add_worker(plan, group, 24.5, 92.0, 0.05)
        _add_worker(plan, group, 25.5, 101.0, -0.25)


def _build_customs(plan: SpecPlan, lod: int) -> None:
    group = CUSTOMS_ID
    cx, cz = -68.0, -67.8
    front_z, rear_z = cz - 37.0, cz + 35.0
    plinth = plan.box(
        "customs-collision-anchored-plinth", "old_concrete", group,
        cx, 0.24, cz, 90.8, 0.64, 76.8,
        layer="mid", blocks_gameplay=True, name=f"{group}.plinth",
    )
    base = plan.box(
        "customs-heavy-loading-base", "red_brick", group,
        cx, 6.1, cz, 89.2, 12.0, 74.8,
        layer="mid", blocks_gameplay=True, name=f"{group}.loading-base",
    )
    plan.connect(plinth, base, axis="y", overlap_m=0.20,
                 parent_face="top", child_face="bottom")
    deck = plan.box(
        "customs-upper-plant-deck", "old_concrete", group,
        cx, 12.2, cz, 90.0, 0.65, 75.5,
        layer="mid", name=f"{group}.upper-deck",
    )
    plan.connect(base, deck, axis="y", overlap_m=0.18,
                 parent_face="top", child_face="bottom")

    tooth_width = 21.25
    first_left = cx - 42.5
    occupied_bays = []
    for tooth in range(4):
        left = first_left + tooth * tooth_width
        right = left + tooth_width
        peak_x = left + tooth_width * 0.31
        bay_x = (left + right) / 2
        occupied = plan.box(
            "customs-sawtooth-occupied-bay-volume",
            "pale_concrete" if tooth % 2 == 0 else "old_concrete",
            group, bay_x, 30.0, cz + 0.8,
            tooth_width - 1.0, 35.6, 68.0,
            layer="mid", blocks_gameplay=True,
            name=f"{group}.bay.{tooth + 1}.occupied",
        )
        plan.connect(deck, occupied, axis="y", overlap_m=0.18,
                     parent_face="top", child_face="bottom")
        occupied_bays.append(occupied)

        peak_y, valley_y = 68.0, 48.0
        roof = plan.panel(
            "customs-sawtooth-roof", "weathered_zinc", group,
            (
                (peak_x, peak_y, front_z), (right, valley_y, front_z),
                (right, valley_y, rear_z), (peak_x, peak_y, rear_z),
            ),
            0.34, layer="mid", name=f"{group}.tooth.{tooth + 1}.roof",
        )
        glass = plan.panel(
            "customs-sawtooth-glazed-face", "dirty_glass", group,
            (
                (left, valley_y, front_z), (peak_x, peak_y, front_z),
                (peak_x, peak_y, rear_z), (left, valley_y, rear_z),
            ),
            0.26, layer="mid", name=f"{group}.tooth.{tooth + 1}.deep-glass",
        )
        gable = plan.panel(
            "customs-sawtooth-triangular-glass-gable", "dirty_glass", group,
            (
                (left + 0.2, valley_y + 0.2, front_z - 0.24),
                (peak_x, peak_y - 0.2, front_z - 0.24),
                (right - 0.2, valley_y + 0.2, front_z - 0.24),
            ),
            0.22, layer="mid", name=f"{group}.tooth.{tooth + 1}.front-gable",
        )
        plan.connect(occupied, roof, axis="surface", overlap_m=0.16,
                     parent_face="top", child_face="eave")
        plan.connect(occupied, glass, axis="surface", overlap_m=0.14,
                     parent_face="top", child_face="lower-edge")
        plan.connect(occupied, gable, axis="surface", overlap_m=0.12,
                     parent_face="front", child_face="bottom")
        rear_gable = plan.panel(
            "customs-primary-rear-sawtooth-gable", "dirty_glass", group,
            (
                (left + 0.2, valley_y + 0.2, rear_z + 0.24),
                (peak_x, peak_y - 0.2, rear_z + 0.24),
                (right - 0.2, valley_y + 0.2, rear_z + 0.24),
            ),
            0.22, layer="mid",
            name=f"{group}.tooth.{tooth + 1}.primary-rear-gable",
        )
        plan.connect(occupied, rear_gable, axis="surface", overlap_m=0.12,
                     parent_face="rear", child_face="bottom")
        for start_point, end_point in (
            ((left + 0.2, valley_y + 0.2, rear_z + 0.40),
             (peak_x, peak_y - 0.2, rear_z + 0.40)),
            ((peak_x, peak_y - 0.2, rear_z + 0.40),
             (right - 0.2, valley_y + 0.2, rear_z + 0.40)),
            ((left + 0.2, valley_y + 0.2, rear_z + 0.40),
             (right - 0.2, valley_y + 0.2, rear_z + 0.40)),
        ):
            plan.beam(
                "customs-primary-rear-sawtooth-chord", "structural_steel", group,
                start_point, end_point,
                0.34 if lod == 0 else 0.52,
                0.26 if lod == 0 else 0.42, layer="mid",
            )
        if lod < 2:
            for mullion in (0.25, 0.50, 0.75):
                mullion_x = left + (right - left) * mullion
                roof_t = min(
                    1.0,
                    max(0.0, (mullion_x - peak_x) / max(0.01, right - peak_x)),
                )
                mullion_top = (
                    peak_y + (valley_y - peak_y) * roof_t
                    if mullion_x >= peak_x
                    else valley_y + (peak_y - valley_y) * (
                        mullion_x - left
                    ) / max(0.01, peak_x - left)
                )
                plan.beam(
                    "customs-primary-rear-sawtooth-mullion", "rust", group,
                    (mullion_x, valley_y + 0.3, rear_z + 0.46),
                    (mullion_x, mullion_top - 0.25, rear_z + 0.46),
                    0.16, 0.14, layer="mid",
                )
        # Heavy front chords make each glazed tooth read as a deep industrial
        # truss rather than a flat orange triangle.
        for start_point, end_point in (
            ((left + 0.2, valley_y + 0.2, front_z - 0.40),
             (peak_x, peak_y - 0.2, front_z - 0.40)),
            ((peak_x, peak_y - 0.2, front_z - 0.40),
             (right - 0.2, valley_y + 0.2, front_z - 0.40)),
            ((left + 0.2, valley_y + 0.2, front_z - 0.40),
             (right - 0.2, valley_y + 0.2, front_z - 0.40)),
        ):
            plan.beam(
                "customs-front-sawtooth-chord", "structural_steel", group,
                start_point, end_point,
                0.34 if lod == 0 else 0.52,
                0.26 if lod == 0 else 0.42, layer="mid",
            )
        if lod < 2:
            for mullion in (0.25, 0.50, 0.75):
                mullion_x = left + (right - left) * mullion
                roof_t = min(1.0, max(0.0, (mullion_x - peak_x) / max(0.01, right - peak_x)))
                mullion_top = peak_y + (valley_y - peak_y) * roof_t if mullion_x >= peak_x else (
                    valley_y + (peak_y - valley_y) * (mullion_x - left) / max(0.01, peak_x - left)
                )
                plan.beam(
                    "customs-front-sawtooth-mullion", "rust", group,
                    (mullion_x, valley_y + 0.3, front_z - 0.46),
                    (mullion_x, mullion_top - 0.25, front_z - 0.46),
                    0.16, 0.14, layer="mid",
                )

        frame_count = 7 if lod == 0 else 4 if lod == 1 else 2
        for frame in range(frame_count):
            z = front_z + (rear_z - front_z) * frame / max(1, frame_count - 1)
            plan.beam(
                "customs-sawtooth-internal-truss", "structural_steel", group,
                (left + 0.25, valley_y + 0.2, z),
                (peak_x, peak_y - 0.2, z),
                0.20 if lod == 0 else 0.34, 0.16 if lod == 0 else 0.28,
                layer="mid",
            )
            plan.beam(
                "customs-sawtooth-internal-truss", "rust", group,
                (peak_x, peak_y - 0.2, z),
                (right - 0.25, valley_y + 0.2, z),
                0.20 if lod == 0 else 0.34, 0.16 if lod == 0 else 0.28,
                layer="mid",
            )
        purlin_count = 4 if lod == 0 else 2
        for purlin in range(purlin_count):
            t = (purlin + 1) / (purlin_count + 1)
            x = peak_x + (right - peak_x) * t
            y = peak_y + (valley_y - peak_y) * t
            plan.beam(
                "customs-sawtooth-long-purlin", "structural_steel", group,
                (x, y - 0.18, front_z), (x, y - 0.18, rear_z),
                0.18 if lod == 0 else 0.30, 0.15 if lod == 0 else 0.24,
                layer="mid",
            )

        window_rows = 3 if lod == 0 else 2 if lod == 1 else 1
        for row in range(window_rows):
            y = 20.5 + row * 10.5
            recess_width = tooth_width * (0.74 if row != 1 else 0.62)
            plan.box(
                "customs-front-deep-bay-recess", "dark_concrete", group,
                bay_x, y, front_z - 0.34,
                recess_width, 6.6, 0.52, layer="mid",
            )
            glass_width = recess_width * 0.76
            plan.box(
                "customs-occupied-bay-window-band",
                "warm_glass" if (tooth + row) % 3 == 0 else "dirty_glass",
                group, bay_x, y, front_z - 0.68,
                glass_width, 3.5, 0.20, layer="mid",
            )
            plan.box(
                "customs-window-rust-lintel", "rust", group,
                bay_x, y + 3.45, front_z - 0.55,
                recess_width + 0.6, 0.34, 0.30, layer="mid",
            )
            for side in (-1.0, 1.0):
                plan.box(
                    "customs-window-deep-jamb", "structural_steel", group,
                    bay_x + side * recess_width * 0.50, y,
                    front_z - 0.56, 0.32, 6.8, 0.32, layer="mid",
                )
            if lod == 0:
                for mullion in (-0.25, 0.0, 0.25):
                    plan.box(
                        "customs-window-mullion", "structural_steel", group,
                        bay_x + glass_width * mullion, y,
                        front_z - 0.82, 0.14, 3.75, 0.14, layer="mid",
                    )

            # The north/rear elevation faces the fixed primary camera and is
            # also the canonical entrance side.  Match the south facade's
            # depth without mirroring its exact rhythm.
            rear_recess_width = tooth_width * (0.66 if row != 1 else 0.52)
            plan.box(
                "customs-primary-rear-deep-bay-recess", "dark_concrete", group,
                bay_x, y + 0.6, rear_z + 0.34,
                rear_recess_width, 6.2, 0.52, layer="mid",
            )
            rear_glass_width = rear_recess_width * 0.72
            plan.box(
                "customs-primary-rear-occupied-window",
                "warm_glass" if (tooth + row) % 4 == 1 else "dirty_glass",
                group, bay_x, y + 0.6, rear_z + 0.68,
                rear_glass_width, 3.35, 0.20, layer="mid",
            )
            plan.box(
                "customs-primary-rear-rust-lintel", "rust", group,
                bay_x, y + 3.88, rear_z + 0.55,
                rear_recess_width + 0.5, 0.34, 0.30, layer="mid",
            )
            for side in (-1.0, 1.0):
                plan.box(
                    "customs-primary-rear-deep-jamb", "structural_steel", group,
                    bay_x + side * rear_recess_width * 0.50,
                    y + 0.6, rear_z + 0.56,
                    0.32, 6.4, 0.32, layer="mid",
                )
            if lod == 0:
                for mullion in (-0.25, 0.0, 0.25):
                    plan.box(
                        "customs-primary-rear-window-mullion",
                        "structural_steel", group,
                        bay_x + rear_glass_width * mullion,
                        y + 0.6, rear_z + 0.82,
                        0.14, 3.60, 0.14, layer="mid",
                    )

    if lod < 2:
        for balcony_y in (27.0, 43.0):
            balcony_z = rear_z + 1.05
            plan.box(
                "customs-primary-rear-maintenance-balcony",
                "weathered_zinc", group,
                cx, balcony_y, balcony_z,
                86.0, 0.28, 1.80, layer="mid",
            )
            _add_guardrail(
                plan, group,
                (cx - 41.5, balcony_z + 0.76),
                (cx + 41.5, balcony_z + 0.76),
                balcony_y + 0.14,
                posts=12 if lod == 0 else 7, layer="mid",
            )

    # Articulated long elevations: inset window slots, heavy ribs, process
    # risers and a full-depth maintenance catwalk make the roof depth legible
    # from either oblique view instead of presenting a blank terminal wall.
    if lod < 2:
        outer_xs = (first_left - 0.42, first_left + tooth_width * 4 + 0.42)
        side_zs = tuple(front_z + 9.0 + index * 13.5 for index in range(5))
        for side_index, outer_x in enumerate(outer_xs):
            for z in side_zs[::(1 if lod == 0 else 2)]:
                plan.box(
                    "customs-side-structural-rib", "structural_steel", group,
                    outer_x, 30.0, z, 0.48, 35.0, 0.62, layer="mid",
                )
                for row, y in enumerate((20.0, 31.0, 42.0)):
                    if lod == 1 and row == 1:
                        continue
                    plan.box(
                        "customs-deep-side-window-slot",
                        "warm_glass" if (row + side_index) % 3 == 0 else "dirty_glass",
                        group, outer_x + (-0.18 if side_index == 0 else 0.18),
                        y, z, 0.22, 2.2, 9.8, layer="mid",
                    )
            catwalk_x = outer_x + (-1.05 if side_index == 0 else 1.05)
            plan.box(
                "customs-full-depth-side-catwalk", "weathered_zinc", group,
                catwalk_x, 25.0, (front_z + rear_z) / 2,
                1.75, 0.28, rear_z - front_z - 3.0, layer="mid",
            )
            _add_guardrail(
                plan, group,
                (catwalk_x + (-0.65 if side_index == 0 else 0.65), front_z + 2.0),
                (catwalk_x + (-0.65 if side_index == 0 else 0.65), rear_z - 2.0),
                25.14, posts=12 if lod == 0 else 7, layer="mid",
            )
            for pipe_index in range(2):
                plan.cylinder(
                    "customs-side-process-riser", "rust", group,
                    outer_x + (-0.62 if side_index == 0 else 0.62),
                    29.5, front_z + 15.0 + pipe_index * 34.0,
                    0.34 if lod == 0 else 0.48, 34.0,
                    10 if lod == 0 else 7,
                    top_radius=0.30 if lod == 0 else 0.42,
                    layer="mid",
                )
            if side_index == 0:
                primary_side_bays = side_zs if lod == 0 else side_zs[::2]
                for bay_index, side_z in enumerate(primary_side_bays):
                    plan.box(
                        "customs-primary-west-deep-bay", "dark_concrete", group,
                        outer_x - 0.34, 35.5, side_z,
                        0.62, 7.2, 10.8, layer="mid",
                    )
                    plan.box(
                        "customs-primary-west-occupied-window",
                        "warm_glass" if bay_index % 3 == 1 else "dirty_glass",
                        group, outer_x - 0.70, 35.5, side_z,
                        0.18, 3.5, 8.4, layer="mid",
                    )
                    for jamb_side in (-1.0, 1.0):
                        plan.box(
                            "customs-primary-west-deep-jamb", "rust", group,
                            outer_x - 0.62, 35.5,
                            side_z + jamb_side * 5.35,
                            0.24, 7.4, 0.34, layer="mid",
                        )
                _add_external_stair_run(
                    plan, group,
                    (outer_x - 2.05, 12.6, front_z + 8.0),
                    (outer_x - 2.05, 24.8, front_z + 29.0),
                    1.75, lod, layer="mid",
                )

    # Eight human-scale loading bays keep the base occupied at 1.65 m.
    door_count = 8 if lod == 0 else 5 if lod == 1 else 3
    for bay in range(door_count):
        x = cx - 36.0 + bay * 72.0 / max(1, door_count - 1)
        plan.box(
            "customs-loading-door-deep-recess", "dark_concrete", group,
            x, 3.9, front_z - 0.36, 7.8, 7.4, 0.58, layer="near",
        )
        plan.box(
            "customs-loading-door", "weathered_zinc", group,
            x, 3.8, front_z - 0.73, 6.6, 6.8, 0.22, layer="near",
        )
        plan.box(
            "customs-loading-bay-bumper", "safety_orange", group,
            x, 0.72, front_z - 0.66, 6.9, 0.42, 0.40, layer="near",
        )
        plan.box(
            "customs-dock-leveller", "structural_steel", group,
            x, 0.28, front_z - 2.2, 6.2, 0.22, 3.3, layer="near",
        )
        for side in (-1.0, 1.0):
            plan.box(
                "customs-loading-door-bumper", "rust", group,
                x + side * 3.48, 1.2, front_z - 1.0,
                0.30, 2.1, 0.42, layer="near",
            )
        if lod < 2:
            plan.box(
                "customs-loading-lamp", "warm_glass", group,
                x, 8.0, front_z - 0.68, 0.65, 0.34, 0.18, layer="near",
            )
            slat_count = 7 if lod == 0 else 4
            for slat in range(slat_count):
                plan.box(
                    "customs-loading-door-slat", "structural_steel", group,
                    x, 0.85 + slat * 5.8 / max(1, slat_count - 1),
                    front_z - 0.87, 6.35, 0.10, 0.12, layer="near",
                )
        if lod == 0 and bay in {1, 5}:
            _add_pallet_stack(plan, group, x + 1.6, front_z - 5.0, lod)
    canopy = plan.box(
        "customs-loading-canopy", "weathered_zinc", group,
        cx, 9.2, front_z - 2.3, 84.0, 0.45, 4.0,
        layer="near", name=f"{group}.loading-canopy",
    )
    plan.connect(base, canopy, axis="surface", overlap_m=0.12,
                 parent_face="front", child_face="rear")

    # Canonical entrance and primary-camera loading life are on the north
    # elevation.  Deep docks, two asymmetric annexes and an inset public gate
    # prevent the full-width base from reading as one unoccupied grey box.
    primary_canopy = plan.box(
        "customs-primary-rear-loading-canopy", "weathered_zinc", group,
        cx, 10.0, rear_z + 2.3, 82.0, 0.48, 4.2,
        layer="near", name=f"{group}.primary-rear-loading-canopy",
    )
    plan.connect(base, primary_canopy, axis="surface", overlap_m=0.12,
                 parent_face="rear", child_face="inner-edge")
    primary_bay_count = 6 if lod == 0 else 4 if lod == 1 else 3
    for bay in range(primary_bay_count):
        bay_x = cx - 34.0 + bay * 68.0 / max(1, primary_bay_count - 1)
        plan.box(
            "customs-primary-rear-loading-recess", "dark_concrete", group,
            bay_x, 4.1, rear_z + 0.40, 8.2, 7.6, 0.62, layer="near",
        )
        plan.box(
            "customs-primary-rear-loading-door", "weathered_zinc", group,
            bay_x, 3.95, rear_z + 0.78, 6.8, 6.9, 0.22, layer="near",
        )
        plan.box(
            "customs-primary-rear-dock-leveller", "structural_steel", group,
            bay_x, 0.30, rear_z + 2.3, 6.3, 0.22, 3.2, layer="near",
        )
        plan.box(
            "customs-primary-rear-loading-lamp", "warm_glass", group,
            bay_x, 8.1, rear_z + 0.74, 0.62, 0.34, 0.18, layer="near",
        )
        if lod == 0:
            for slat in range(6):
                plan.box(
                    "customs-primary-rear-loading-door-slat", "rust", group,
                    bay_x, 0.9 + slat * 1.12, rear_z + 0.91,
                    6.5, 0.09, 0.12, layer="near",
                )
    for annex_index, (annex_x, annex_h, annex_w) in enumerate((
        (cx - 34.5, 14.0, 17.0),
        (cx + 34.0, 17.0, 16.0),
    )):
        annex = plan.box(
            "customs-primary-rear-occupied-annex",
            "red_brick" if annex_index == 0 else "old_concrete", group,
            annex_x, annex_h * 0.5, rear_z + 6.0,
            annex_w, annex_h, 11.5, layer="near",
        )
        plan.connect(base, annex, axis="surface", overlap_m=0.14,
                     parent_face="rear", child_face="back")
        plan.box(
            "customs-primary-rear-annex-window", "warm_glass", group,
            annex_x, annex_h * 0.62, rear_z + 11.85,
            annex_w * 0.62, 2.1, 0.18, layer="near",
        )
        plan.box(
            "customs-primary-rear-annex-door", "dark_concrete", group,
            annex_x, 2.4, rear_z + 11.88,
            3.8, 4.6, 0.20, layer="near",
        )
        plan.box(
            "customs-primary-rear-annex-roof", "weathered_zinc", group,
            annex_x, annex_h + 0.25, rear_z + 6.0,
            annex_w + 0.8, 0.50, 12.3, layer="near",
        )
    primary_landing = plan.box(
        "customs-primary-human-scale-entry-landing", "old_concrete", group,
        cx, 0.42, rear_z + 6.2, 18.0, 0.48, 6.5, layer="near",
    )
    plan.connect(base, primary_landing, axis="surface", overlap_m=0.12,
                 parent_face="rear", child_face="inner-edge")
    if lod < 2:
        _add_guardrail(
            plan, group,
            (cx - 8.2, rear_z + 9.0), (cx + 8.2, rear_z + 9.0),
            0.62, posts=8 if lod == 0 else 5, layer="near",
        )
        for x, z, yaw in (
            (cx - 18.0, rear_z + 7.0, 0.4),
            (cx + 1.5, rear_z + 8.0, -0.8),
            (cx + 22.0, rear_z + 6.2, 1.1),
        )[::(1 if lod == 0 else 2)]:
            _add_worker(plan, group, x, z, yaw)

    control_base = plan.box(
        "customs-control-tower-base", "dark_concrete", group,
        cx + 27.0, 61.5, cz + 6.0, 15.5, 29.0, 16.5,
        layer="mid", name=f"{group}.control.base",
    )
    plan.connect(occupied_bays[-1], control_base, axis="surface", overlap_m=0.18,
                 parent_face="roof", child_face="bottom")
    control_glass = plan.box(
        "customs-control-tower-glazing", "warm_glass", group,
        cx + 27.0, 78.0, cz + 6.0, 14.2, 4.0, 15.2,
        layer="mid", name=f"{group}.control.glass",
    )
    control_roof = plan.box(
        "customs-control-tower-roof", "weathered_zinc", group,
        cx + 27.0, 80.4, cz + 6.0, 17.0, 0.80, 18.0,
        layer="mid", name=f"{group}.control.roof",
    )
    plan.connect(control_base, control_glass, axis="y", overlap_m=0.16,
                 parent_face="top", child_face="bottom")
    plan.connect(control_glass, control_roof, axis="y", overlap_m=0.14,
                 parent_face="top", child_face="bottom")
    for index, offset in enumerate((-31.0, 9.0)):
        chimney = plan.cylinder(
            "customs-industrial-chimney", "rust", group,
            cx + offset, 51.0 + index * 2.0, cz + 23.0,
            1.55 if lod == 0 else 1.9, 77.0 + index * 4.0,
            14 if lod == 0 else 9, top_radius=1.06,
            layer="mid", name=f"{group}.chimney.{index + 1}",
        )
        plan.connect(deck, chimney, axis="y", overlap_m=0.18,
                     parent_face="top", child_face="bottom")

    landing = plan.box(
        "customs-human-scale-entry-landing", "old_concrete", group,
        cx, 3.9, front_z - 4.6, 20.0, 0.46, 4.6,
        layer="near", name=f"{group}.entry-landing",
    )
    plan.connect(base, landing, axis="surface", overlap_m=0.12,
                 parent_face="front", child_face="rear")
    if lod < 2:
        _add_guardrail(plan, group,
                       (cx - 9.0, front_z - 6.5),
                       (cx + 9.0, front_z - 6.5),
                       4.12, posts=8 if lod == 0 else 5)
        customs_workers = (
            (cx - 24.0, front_z - 7.2, 0.3),
            (cx - 3.0, front_z - 8.0, -0.5),
            (cx + 20.0, front_z - 7.0, 0.8),
        )
        for x, z, yaw in customs_workers[::(1 if lod == 0 else 2)]:
            _add_worker(plan, group, x, z, yaw)


def _build_inter_landmark_transfer(plan: SpecPlan, lod: int) -> None:
    """Build the high customs conveyor that closes the dual-hero gap."""
    group = "souko-a20-inter-landmark-transfer"
    start = (33.0, 77.0)
    end = (-23.0, -31.0)
    bottom, top, depth = 28.0, 36.5, 6.5
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    yaw = math.atan2(dz, dx)
    mx, mz = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    floor = plan.box(
        "inter-landmark-transfer-floor", "weathered_zinc", group,
        mx, bottom + 0.34, mz, length + 4.0, 0.68, depth,
        yaw=yaw, layer="mid", name=f"{group}.floor",
    )
    roof = plan.box(
        "inter-landmark-transfer-roof", "structural_steel", group,
        mx, top - 0.30, mz, length + 4.0, 0.60, depth + 0.4,
        yaw=yaw, layer="mid", name=f"{group}.roof",
    )
    plan.connect(
        f"{STACKHOUSE_ID}.a.completed-envelope", floor,
        axis="surface", overlap_m=0.20,
        parent_face="west-south", child_face="start",
    )
    plan.connect(
        f"{CUSTOMS_ID}.bay.4.occupied", floor,
        axis="surface", overlap_m=0.20,
        parent_face="north-east", child_face="end",
    )
    plan.connect(floor, roof, axis="frame", overlap_m=0.10,
                 parent_face="side-frame", child_face="side-frame")
    frame_count = 12 if lod == 0 else 7 if lod == 1 else 4
    for frame in range(frame_count):
        t = frame / max(1, frame_count - 1)
        bx, bz = start[0] + dx * t, start[1] + dz * t
        for side in (-1.0, 1.0):
            sx, sz = bx + px * depth * 0.5 * side, bz + pz * depth * 0.5 * side
            plan.beam(
                "inter-landmark-transfer-portal", "structural_steel", group,
                (sx, bottom + 0.2, sz), (sx, top - 0.2, sz),
                0.24 if lod == 0 else 0.38,
                0.20 if lod == 0 else 0.32, layer="mid",
            )
        plan.beam(
            "inter-landmark-transfer-portal", "structural_steel", group,
            (bx - px * depth * 0.5, top - 0.22, bz - pz * depth * 0.5),
            (bx + px * depth * 0.5, top - 0.22, bz + pz * depth * 0.5),
            0.24 if lod == 0 else 0.38,
            0.20 if lod == 0 else 0.32, layer="mid",
        )
    for side in (-1.0, 1.0):
        side_x = mx + px * (depth * 0.5 + 0.15) * side
        side_z = mz + pz * (depth * 0.5 + 0.15) * side
        plan.box(
            "inter-landmark-transfer-deep-glazed-side", "dirty_glass", group,
            side_x, (bottom + top) / 2, side_z,
            length + 2.0, top - bottom - 1.6, 0.20,
            yaw=yaw, layer="mid",
        )
        plan.box(
            "inter-landmark-transfer-weathered-spandrel", "old_concrete", group,
            side_x, bottom + 1.25, side_z,
            length + 2.4, 1.9, 0.38, yaw=yaw, layer="mid",
        )
        for bay in range(frame_count - 1):
            t0, t1 = bay / (frame_count - 1), (bay + 1) / (frame_count - 1)
            ax = start[0] + dx * t0 + px * depth * 0.5 * side
            az = start[1] + dz * t0 + pz * depth * 0.5 * side
            bx = start[0] + dx * t1 + px * depth * 0.5 * side
            bz = start[1] + dz * t1 + pz * depth * 0.5 * side
            low, high = bottom + 0.75, top - 0.75
            ay, by = (low, high) if (bay + (side > 0)) % 2 == 0 else (high, low)
            plan.beam(
                "inter-landmark-transfer-diagonal", "rust", group,
                (ax, ay, az), (bx, by, bz),
                0.15 if lod == 0 else 0.24,
                0.12 if lod == 0 else 0.20, layer="mid",
            )
    if lod < 2:
        plan.box(
            "inter-landmark-transfer-occupied-control-room", "dark_concrete", group,
            mx + ux * length * 0.16, (bottom + top) / 2,
            mz + uz * length * 0.16,
            14.0, top - bottom - 1.3, depth - 1.2,
            yaw=yaw, layer="mid",
        )
        for lamp in (-0.34, 0.0, 0.34):
            plan.box(
                "inter-landmark-transfer-warm-window", "warm_glass", group,
                mx + ux * length * lamp, bottom + 3.2,
                mz + uz * length * lamp,
                4.2, 1.15, depth + 0.24, yaw=yaw, layer="mid",
            )


def _add_port_crane(
    plan: SpecPlan,
    label: str,
    x: float,
    z: float,
    height: float,
    boom_direction: float,
    lod: int,
) -> None:
    group = "souko-a20-south-port"
    outside = True
    base = plan.box(
        "port-crane-grounded-base", "old_concrete", group,
        x, 1.0, z, 9.0, 2.0, 9.0,
        layer="far", outside_playable=outside, name=f"{group}.{label}.base",
    )
    tower = plan.box(
        "port-crane-lattice-tower", "structural_steel", group,
        x, height * 0.49 + 1.5, z, 1.25, height - 3.0, 1.25,
        layer="far", outside_playable=outside, name=f"{group}.{label}.tower",
    )
    plan.connect(base, tower, axis="y", overlap_m=0.20,
                 parent_face="top", child_face="bottom")
    dx, dz = math.cos(boom_direction), math.sin(boom_direction)
    px, pz = -dz, dx
    if lod < 2:
        for along in (-1.0, 1.0):
            for side in (-1.0, 1.0):
                plan.beam(
                    "port-crane-splayed-gantry-leg", "structural_steel", group,
                    (x + dx * along * 3.4 + px * side * 3.4, 1.6,
                     z + dz * along * 3.4 + pz * side * 3.4),
                    (x + dx * along * 1.1 + px * side * 1.1, height - 4.0,
                     z + dz * along * 1.1 + pz * side * 1.1),
                    0.52 if lod == 0 else 0.75,
                    0.44 if lod == 0 else 0.65,
                    layer="far", outside_playable=outside,
                )
        for level in (height * 0.30, height * 0.58, height * 0.82):
            plan.beam(
                "port-crane-gantry-cross-tie", "rust", group,
                (x + px * 2.0, level, z + pz * 2.0),
                (x - px * 2.0, level, z - pz * 2.0),
                0.30, 0.24, layer="far", outside_playable=outside,
            )
    boom_len = 54.0 if lod == 0 else 44.0 if lod == 1 else 36.0
    boom = plan.beam(
        "port-crane-huge-boom", "safety_orange", group,
        (x - dx * 7.0, height, z - dz * 7.0),
        (x + dx * boom_len, height - 5.0, z + dz * boom_len),
        0.95 if lod == 0 else 1.4, 0.85 if lod == 0 else 1.2,
        layer="far", outside_playable=outside,
        name=f"{group}.{label}.boom",
    )
    plan.connect(tower, boom, axis="surface", overlap_m=0.16,
                 parent_face="top", child_face="underside")
    plan.beam(
        "port-crane-boom-upper-chord", "structural_steel", group,
        (x - dx * 4.0, height + 6.0, z - dz * 4.0),
        (x + dx * boom_len, height - 4.5, z + dz * boom_len),
        0.42 if lod == 0 else 0.65, 0.34 if lod == 0 else 0.55,
        layer="far", outside_playable=outside,
    )
    if lod < 2:
        brace_count = 5 if lod == 0 else 3
        for brace in range(brace_count):
            t = (brace + 1) / (brace_count + 1)
            lower_along = -7.0 + (boom_len + 7.0) * t
            upper_along = -4.0 + (boom_len + 4.0) * t
            lower_y = height - 5.0 * t
            upper_y = height + 6.0 - 10.5 * t
            plan.beam(
                "port-crane-boom-lattice", "rust", group,
                (x + dx * lower_along, lower_y,
                 z + dz * lower_along),
                (x + dx * upper_along, upper_y,
                 z + dz * upper_along),
                0.20 if lod == 0 else 0.30,
                0.16 if lod == 0 else 0.24,
                layer="far", outside_playable=outside,
            )
    plan.box(
        "port-crane-operator-cab", "warm_glass", group,
        x + dx * 4.5, height - 7.0, z + dz * 4.5,
        4.8, 3.8, 4.0, yaw=boom_direction,
        layer="far", outside_playable=outside,
    )
    plan.box(
        "port-crane-counterweight", "rust", group,
        x - dx * 10.0, height - 0.8, z - dz * 10.0,
        8.0, 4.2, 4.4, yaw=boom_direction,
        layer="far", outside_playable=outside,
    )
    if lod < 2:
        plan.beam(
            "port-crane-cable", "structural_steel", group,
            (x + dx * boom_len, height - 5.0, z + dz * boom_len),
            (x + dx * boom_len, 4.0, z + dz * boom_len),
            0.10 if lod == 0 else 0.16, 0.10 if lod == 0 else 0.16,
            layer="far", outside_playable=outside,
        )
        for side in (-1.0, 1.0):
            brace_px, brace_pz = -dz * 1.9 * side, dx * 1.9 * side
            plan.beam(
                "port-crane-lattice-brace", "rust", group,
                (x + brace_px, 4.0, z + brace_pz),
                (x - brace_px, height - 5.0, z - brace_pz),
                0.24, 0.18, layer="far", outside_playable=outside,
            )


def _add_cargo_ship(plan: SpecPlan, lod: int) -> None:
    group = "souko-a20-south-port"
    outside = True
    # Keep the ship on the far left quay edge in the dual-hero shot.  The
    # dedicated quay view turns toward it, but it can never become the former
    # giant central blocker.
    x, z = -45.0, 188.0
    # Ship length runs X along the south quay so it reads in the primary view.
    for side in (-1.0, 1.0):
        plan.panel(
            "cargo-ship-hull", "dark_concrete", group,
            (
                (x - 49.0, 0.2, z + side * 7.0),
                (x - 43.0, 6.4, z + side * 11.0),
                (x + 43.0, 6.4, z + side * 11.0),
                (x + 52.0, 0.2, z + side * 6.0),
            ),
            0.46, layer="far", outside_playable=outside,
            name=f"{group}.ship.hull.{'port' if side < 0 else 'starboard'}",
        )
    plan.panel(
        "cargo-ship-raked-bow", "rust", group,
        (
            (x + 48.0, 0.3, z - 7.0), (x + 48.0, 0.3, z + 7.0),
            (x + 54.0, 7.0, z + 5.0), (x + 54.0, 7.0, z - 5.0),
        ),
        0.46, layer="far", outside_playable=outside,
    )
    deck = plan.box(
        "cargo-ship-deck", "weathered_zinc", group,
        x, 6.7, z, 96.0, 0.62, 20.0,
        layer="far", outside_playable=outside, name=f"{group}.ship.deck",
    )
    for side in (-1.0, 1.0):
        plan.box(
            "cargo-ship-rust-waterline", "rust", group,
            x, 1.55, z + side * 10.95, 92.0, 1.15, 0.24,
            layer="far", outside_playable=outside,
        )
        if lod < 2:
            plate_count = 5 if lod == 0 else 3
            for plate in range(plate_count):
                plate_x = x - 36.0 + plate * 72.0 / max(1, plate_count - 1)
                plan.box(
                    "cargo-ship-weathered-hull-plate",
                    "rust" if (plate + (side > 0)) % 3 == 0 else "dark_concrete",
                    group, plate_x, 3.65, z + side * 11.12,
                    14.0, 2.15, 0.18,
                    layer="far", outside_playable=outside,
                )
    lower_bridge = plan.box(
        "cargo-ship-superstructure-lower", "paint_white", group,
        x - 34.0, 11.2, z, 21.0, 9.4, 17.0,
        layer="far", outside_playable=outside, name=f"{group}.ship.bridge.lower",
    )
    plan.connect(deck, lower_bridge, axis="y", overlap_m=0.22,
                 parent_face="top", child_face="bottom")
    upper_bridge = plan.box(
        "cargo-ship-superstructure-upper", "pale_concrete", group,
        x - 34.0, 17.7, z, 17.0, 4.2, 14.5,
        layer="far", outside_playable=outside, name=f"{group}.ship.bridge.upper",
    )
    bridge_roof = plan.box(
        "cargo-ship-bridge-roof", "weathered_zinc", group,
        x - 34.0, 20.2, z, 19.5, 0.65, 16.5,
        layer="far", outside_playable=outside, name=f"{group}.ship.bridge.roof",
    )
    plan.connect(lower_bridge, upper_bridge, axis="y", overlap_m=0.18,
                 parent_face="top", child_face="bottom")
    plan.connect(upper_bridge, bridge_roof, axis="y", overlap_m=0.14,
                 parent_face="top", child_face="bottom")
    for side in (-1.0, 1.0):
        for level_y in (14.7, 18.1):
            plan.box(
                "cargo-ship-bridge-window-strip", "warm_glass", group,
                x - 34.0, level_y, z + side * (8.60 if level_y < 16.0 else 7.35),
                15.0 if level_y < 16.0 else 13.0, 1.25, 0.22,
                layer="far", outside_playable=outside,
            )
            if lod == 0:
                for mullion in (-0.30, -0.10, 0.10, 0.30):
                    plan.box(
                        "cargo-ship-bridge-window-mullion", "structural_steel", group,
                        x - 34.0 + (15.0 if level_y < 16.0 else 13.0) * mullion,
                        level_y, z + side * (8.74 if level_y < 16.0 else 7.49),
                        0.12, 1.45, 0.12,
                        layer="far", outside_playable=outside,
                    )
    forecastle = plan.box(
        "cargo-ship-forecastle", "weathered_zinc", group,
        x + 42.0, 8.0, z, 16.0, 2.8, 15.0,
        layer="far", outside_playable=outside,
    )
    plan.connect(deck, forecastle, axis="y", overlap_m=0.16,
                 parent_face="top", child_face="bottom")
    if lod < 2:
        for side in (-1.0, 1.0):
            _add_guardrail(
                plan, group, (x - 48.0, z + side * 9.55),
                (x + 47.0, z + side * 9.55), 7.0,
                posts=18 if lod == 0 else 10, layer="far",
            )
        for lifeboat_side in (-1.0, 1.0):
            plan.box(
                "cargo-ship-lifeboat", "safety_orange", group,
                x - 24.0, 10.2, z + lifeboat_side * 9.4,
                6.4, 1.5, 1.6, layer="far", outside_playable=outside,
            )
    if lod < 2:
        for winch_x in (x - 24.0, x + 31.0):
            for side in (-1.0, 1.0):
                plan.cylinder(
                    "cargo-ship-deck-winch", "structural_steel", group,
                    winch_x, 7.65, z + side * 7.7,
                    0.72, 1.25, 10 if lod == 0 else 7,
                    top_radius=0.58, layer="far", outside_playable=outside,
                )
    count = 20 if lod == 0 else 10 if lod == 1 else 4
    for index in range(count):
        level, remainder = divmod(index, 10)
        row, column = divmod(remainder, 5)
        container_x = x - 13.0 + column * 7.0
        container_z = z - 3.2 + row * 6.4
        plan.box(
            "cargo-ship-deck-container",
            "safety_orange" if index % 4 == 0 else "weathered_zinc",
            group, container_x, 8.35 + level * 2.80,
            container_z, 6.06, 2.70, 2.44,
            layer="far", outside_playable=outside,
        )
        if lod == 0:
            for rib in (-2.45, 0.0, 2.45):
                plan.box(
                    "cargo-ship-container-rib", "structural_steel", group,
                    container_x + rib, 8.38 + level * 2.80,
                    container_z - 1.26, 0.12, 2.54, 0.14,
                    layer="far", outside_playable=outside,
                )
    plan.beam(
        "cargo-ship-mast", "structural_steel", group,
        (x - 34.0, 20.0, z), (x - 34.0, 33.0, z),
        0.34, 0.34, layer="far", outside_playable=outside,
    )
    plan.beam(
        "cargo-ship-mast-yard", "structural_steel", group,
        (x - 39.0, 29.0, z), (x - 29.0, 29.0, z),
        0.22, 0.22, layer="far", outside_playable=outside,
    )
    plan.box(
        "cargo-ship-bow-anchor", "structural_steel", group,
        x + 51.5, 3.5, z - 5.7, 0.45, 2.4, 2.1,
        layer="far", outside_playable=outside,
    )


def _build_port(plan: SpecPlan, lod: int) -> None:
    group = "souko-a20-south-port"
    plan.box(
        "real-sea-geometry", "sea_water", group,
        -15.0, -0.26, 249.0, 520.0, 0.42, 150.0,
        layer="far", outside_playable=True, name=f"{group}.sea",
    )
    quay = plan.box(
        "quay-slab", "old_concrete", group,
        -15.0, 0.34, 175.0, 410.0, 0.82, 15.0,
        layer="far", outside_playable=True, name=f"{group}.quay",
    )
    retaining = plan.box(
        "quay-retaining-wall", "dark_concrete", group,
        -15.0, 1.35, 182.3, 410.0, 3.4, 1.25,
        layer="far", outside_playable=True, name=f"{group}.retaining",
    )
    plan.connect(quay, retaining, axis="surface", overlap_m=0.18,
                 parent_face="edge", child_face="top")
    cranes = (
        ("west", -42.0, 169.0, 57.0, -2.79),
        ("mid", -103.0, 169.0, 68.0, -2.92),
        ("east", -166.0, 169.0, 61.0, -3.06),
    )
    for item in cranes[::(1 if lod < 2 else 2)]:
        _add_port_crane(plan, *item, lod)
    _add_cargo_ship(plan, lod)
    for index, x in enumerate((-61.0, -76.0, -157.0, -174.0)[::(1 if lod < 2 else 2)]):
        _add_container(
            plan, group, x, 171.0, math.pi,
            "safety_orange" if index % 2 == 0 else "weathered_zinc",
            lod, layer="far", outside=True,
        )
        plan.cylinder(
            "quay-mooring-bollard", "structural_steel", group,
            x - 6.0, 0.95, 179.5, 0.58, 1.30,
            12 if lod == 0 else 8, top_radius=0.74,
            layer="far", outside_playable=True,
        )


def _build_layered_city(plan: SpecPlan, lod: int) -> None:
    group = "souko-a20-bonded-city"
    warehouses = (
        ("west-a", -180.0, 20.0, 48.0, 30.0, 24.0, -0.06, "mid", False),
        ("west-b", -185.0, -125.0, 46.0, 27.0, 22.0, 0.04, "mid", True),
        ("northwest", -60.0, 160.0, 42.0, 32.0, 28.0, 0.08, "far", False),
        ("north", 20.0, 150.0, 38.0, 34.0, 26.0, -0.05, "far", False),
        ("mid-east", 108.0, 28.0, 44.0, 27.0, 23.0, 0.07, "mid", False),
        ("south-mid", 110.0, -135.0, 38.0, 28.0, 21.0, -0.08, "mid", False),
        ("far-east", 205.0, 105.0, 48.0, 46.0, 31.0, 0.04, "far", True),
        ("far-north", 82.0, 184.0, 58.0, 40.0, 29.0, -0.04, "far", True),
        ("far-west", -205.0, 42.0, 55.0, 38.0, 27.0, 0.06, "far", True),
    )
    selection = warehouses if lod == 0 else warehouses[::2] if lod == 1 else warehouses[::3]
    for label, x, z, w, d, h, yaw, layer, outside in selection:
        _add_gabled_warehouse(
            plan, group, label, x, z, w, d, h, yaw, lod,
            layer=layer, outside=outside,
        )
    clusters = (
        (-145.0, -105.0, 0.0), (-118.0, 22.0, math.pi / 2),
        (-24.0, 41.0, 0.0), (34.0, -96.0, 0.08),
        (119.0, -86.0, math.pi / 2), (143.0, 67.0, 0.0),
    )
    for cluster_index, (x, z, yaw) in enumerate(clusters[::(1 if lod == 0 else 2)]):
        count = 4 if lod == 0 else 2 if lod == 1 else 1
        for item in range(count):
            _add_container(
                plan, group, x + (item % 2) * 6.7, z + (item // 2) * 3.2,
                yaw, "safety_orange" if (item + cluster_index) % 3 == 0 else "weathered_zinc",
                lod, layer="mid" if cluster_index > 2 else "near",
            )
    for index, (x, z) in enumerate(((-139.0, -90.0), (-112.0, 17.0),
                                     (-25.0, 35.0), (38.0, -88.0),
                                     (116.0, -78.0), (140.0, 58.0))):
        if lod == 0 or index % 2 == 0:
            _add_pallet_stack(plan, group, x, z, lod,
                              layer="near" if index < 4 else "mid")
    if lod < 2:
        _add_forklift(plan, group, -126.0, -86.0, 0.38, lod)
        _add_forklift(plan, group, 43.0, -80.0, -1.0, lod)

    # A real, distant process skyline closes the former blank centre between
    # the two heroes without putting a collision box in the road corridor.
    horizon_group = "souko-a20-central-process-horizon"
    silo_specs = (
        (42.0, -116.0, 9.0, 72.0),
        (76.0, -108.0, 10.5, 82.0),
        (110.0, -120.0, 13.0, 96.0),
        (144.0, -116.0, 9.5, 70.0),
    )
    for index, (x, z, radius, height) in enumerate(silo_specs[::(1 if lod < 2 else 2)]):
        silo = plan.cylinder(
            "far-process-silo", "old_concrete", horizon_group,
            x, height / 2, z, radius, height,
            16 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=radius * 0.94, layer="far",
        )
        crown = plan.box(
            "far-process-silo-headhouse", "weathered_zinc", horizon_group,
            x, height + 3.2, z, radius * 1.3, 6.2, radius * 1.25,
            layer="far",
        )
        plan.connect(silo, crown, axis="y", overlap_m=0.16,
                     parent_face="top", child_face="bottom")
        if lod < 2:
            plan.box(
                "far-process-silo-window", "warm_glass", horizon_group,
                x, height + 3.5, z - radius * 0.66,
                radius * 0.70, 1.25, 0.18, layer="far",
            )
            plan.cylinder(
                "far-process-silo-vent", "rust", horizon_group,
                x + radius * 0.28, height + 8.0, z,
                0.55, 10.0, 10 if lod == 0 else 7,
                top_radius=0.42, layer="far",
            )
            for angle in (math.pi * 0.25, math.pi * 0.75,
                          math.pi * 1.25, math.pi * 1.75):
                rib_x = x + math.cos(angle) * radius * 0.96
                rib_z = z + math.sin(angle) * radius * 0.96
                plan.beam(
                    "far-process-silo-external-rib", "rust", horizon_group,
                    (rib_x, 2.0, rib_z), (rib_x, height - 2.0, rib_z),
                    0.24 if lod == 0 else 0.36,
                    0.18 if lod == 0 else 0.28, layer="far",
                )
            plan.box(
                "far-process-silo-maintenance-belt", "structural_steel",
                horizon_group, x, height * 0.64, z - radius * 0.97,
                radius * 1.75, 0.42, 0.26, layer="far",
            )
    for index in range(1 if lod == 2 else 2):
        x = 70.0 + index * 42.0
        plan.beam(
            "far-process-overhead-pipe", "rust", horizon_group,
            (x, 30.0 + index * 5.0, -102.0),
            (x + 38.0, 34.0 + index * 4.0, -116.0),
            0.65 if lod == 0 else 0.95,
            0.65 if lod == 0 else 0.95, layer="far",
        )
    _add_port_crane(plan, "far-skyline", 188.0, -96.0, 72.0, 2.72, lod)


def _build_a20_art_pass(plan: SpecPlan, lod: int) -> None:
    """Add the reference-locked A20 macro/meso layer missing from A19.

    The base plan already establishes canonical footprints and three LODs.
    This pass spends the remaining private budget on features that materially
    alter first-person silhouettes, facade depth, operations and harbor life.
    It deliberately avoids tiny free-floating greebles and never blocks the
    canonical cross roads.
    """
    stack = STACKHOUSE_ID
    customs = CUSTOMS_ID

    # WEST/NORTH STACKHOUSE FACE — three deep black rack halls framed by
    # grounded concrete shoulders.  These broad cavities survive screen-size
    # reduction and replace the A19 scaffold pasted over blank tower slabs.
    portal_z = (72.5, 96.0, 119.5)
    portal_count = 3 if lod < 2 else 2
    for index, z in enumerate(portal_z[:portal_count]):
        recess = plan.box(
            "a20-stackhouse-west-rack-cavity", "dark_concrete", stack,
            28.20, 32.0, z, 0.90, 55.0, 17.2,
            layer="mid", name=f"{stack}.a20.west-cavity.{index}",
        )
        sill = plan.box(
            "a20-stackhouse-west-cavity-sill", "rust", stack,
            27.60, 4.2, z, 1.35, 1.10, 17.8,
            layer="mid", name=f"{stack}.a20.west-sill.{index}",
        )
        plan.connect(recess, sill, axis="surface", overlap_m=0.10,
                     parent_face="front", child_face="edge")
        levels = (8.0, 17.0, 26.0, 35.0, 44.0, 53.0) if lod == 0 else (
            (10.0, 25.0, 40.0, 53.0) if lod == 1 else (14.0, 40.0)
        )
        for level_index, y in enumerate(levels):
            plan.box(
                "a20-stackhouse-west-rack-floor",
                "safety_orange" if level_index in {1, 4} else "structural_steel",
                stack, 27.55, y, z, 1.10, 0.42, 16.4,
                layer="mid",
            )
            if lod < 2:
                for side in (-1.0, 1.0):
                    plan.beam(
                        "a20-stackhouse-west-rack-upright", "structural_steel", stack,
                        (27.05, 5.0, z + side * 6.2),
                        (27.05, 55.0, z + side * 6.2),
                        0.34 if lod == 0 else 0.48,
                        0.28 if lod == 0 else 0.40, layer="mid",
                    )
            if lod == 0 and level_index < len(levels) - 1:
                for side in (-1.0, 1.0):
                    plan.box(
                        "a20-stackhouse-west-rack-cargo",
                        "weathered_zinc" if (level_index + (side > 0)) % 3
                        else "safety_orange",
                        stack, 26.92, y + 2.0, z + side * 4.2,
                        1.25, 3.25, 5.8, layer="mid",
                    )

    shoulder_zs = (63.7, 82.5, 108.0, 128.3)
    for index, z in enumerate(shoulder_zs[::(1 if lod < 2 else 2)]):
        shoulder = plan.box(
            "a20-stackhouse-grounded-shoulder", "old_concrete", stack,
            31.0, 25.0, z, 7.0, 50.0, 4.8,
            layer="mid", name=f"{stack}.a20.shoulder.{index}",
        )
        plan.beam(
            "a20-stackhouse-flying-buttress", "pale_concrete", stack,
            (24.5, 0.4, z), (30.2, 47.0, z),
            1.25 if lod == 0 else 1.65,
            1.05 if lod == 0 else 1.35, layer="mid",
        )
        plan.connect(shoulder, f"{stack}.plinth", axis="surface", overlap_m=0.16,
                     parent_face="bottom", child_face="west-edge")

    # Two continuous maintenance galleries and a connected stair make the
    # cavities a believable occupied logistics facade.
    gallery_levels = (20.0, 43.5) if lod < 2 else (30.0,)
    for level_index, y in enumerate(gallery_levels):
        plan.box(
            "a20-stackhouse-west-maintenance-gallery", "weathered_zinc", stack,
            25.5, y, 96.0, 4.6, 0.52, 65.0, layer="mid",
        )
        if lod < 2:
            _add_guardrail(
                plan, stack, (23.25, 64.0), (23.25, 128.0), y + 0.15,
                posts=18 if lod == 0 else 10, layer="mid",
            )
    if lod < 2:
        _add_external_stair_run(
            plan, stack, (20.2, 0.3, 66.0), (23.8, 20.0, 82.0),
            3.2, lod, layer="mid",
        )
        _add_external_stair_run(
            plan, stack, (23.8, 20.0, 82.0), (23.8, 43.5, 105.0),
            3.2, lod, layer="mid",
        )

    # The fixed rack proof now enters a physical aisle rather than pointing
    # at decoration on a slab.  Repeated portal frames establish real vertical
    # volume; side shelves, cargo, an overhead service deck and guardrails keep
    # the 8 m centre lane readable at the player's 1.65 m eye height.
    plan.box(
        "a20-stackhouse-rack-aisle-floor", "dark_concrete", stack,
        19.0, 0.10, 96.0, 22.0, 0.18, 17.0, layer="mid",
    )
    portal_xs = (9.0, 15.0, 21.0, 27.0) if lod == 0 else (
        (9.0, 18.0, 27.0) if lod == 1 else (10.0, 27.0)
    )
    for portal_index, x in enumerate(portal_xs):
        for side in (-1.0, 1.0):
            z = 96.0 + side * 7.3
            plan.beam(
                "a20-stackhouse-rack-aisle-portal-upright", "structural_steel", stack,
                (x, 0.15, z), (x, 17.0, z),
                0.44 if lod == 0 else 0.62,
                0.38 if lod == 0 else 0.54, layer="mid",
            )
        plan.beam(
            "a20-stackhouse-rack-aisle-portal-header", "structural_steel", stack,
            (x, 17.0, 88.7), (x, 17.0, 103.3),
            0.46 if lod == 0 else 0.64,
            0.40 if lod == 0 else 0.56, layer="mid",
        )
        if lod < 2:
            plan.beam(
                "a20-stackhouse-rack-aisle-overhead-brace", "safety_orange", stack,
                (x, 17.0, 88.9), (x, 10.0, 103.1),
                0.22 if lod == 0 else 0.34,
                0.18 if lod == 0 else 0.28, layer="mid",
            )
        if portal_index < len(portal_xs) - 1:
            next_x = portal_xs[portal_index + 1]
            for side in (-1.0, 1.0):
                z = 96.0 + side * 6.3
                for level_index, y in enumerate((3.8, 8.3, 12.8) if lod == 0 else (5.5, 11.5)):
                    plan.box(
                        "a20-stackhouse-rack-aisle-side-shelf", "weathered_zinc", stack,
                        (x + next_x) * 0.5, y, z,
                        next_x - x - 0.55, 0.34, 2.0, layer="mid",
                    )
                    if lod == 0 and level_index < 2:
                        plan.box(
                            "a20-stackhouse-rack-aisle-loaded-cargo",
                            "safety_orange" if (portal_index + level_index + (side > 0)) % 3 == 0
                            else "pallet_wood",
                            stack, (x + next_x) * 0.5, y + 1.15, z,
                            next_x - x - 1.1, 1.8, 1.45, layer="mid",
                        )

    plan.box(
        "a20-stackhouse-rack-aisle-service-catwalk", "weathered_zinc", stack,
        18.0, 10.0, 96.0, 18.0, 0.48, 2.3, layer="mid",
    )
    if lod < 2:
        for side in (-1.0, 1.0):
            _add_guardrail(
                plan, stack, (9.2, 96.0 + side * 1.10),
                (26.8, 96.0 + side * 1.10), 10.15,
                posts=7 if lod == 0 else 4, layer="mid",
            )

    # Camera-facing north process windows and cantilever rooms break the four
    # towers into an interlocked citadel rather than parallel monoliths.
    north_xs = (42.0, 65.5, 91.5, 117.0)
    for index, x in enumerate(north_xs):
        plan.box(
            "a20-stackhouse-north-deep-process-void", "dark_concrete", stack,
            x, 49.0 + (index % 2) * 7.0, 128.75,
            15.5, 22.0, 0.95, layer="mid",
        )
        plan.box(
            "a20-stackhouse-north-cantilever-control-room",
            "old_concrete" if index % 2 else "weathered_zinc", stack,
            x, 63.0 + (index % 2) * 8.0, 132.0,
            13.0, 8.0, 7.0, layer="mid",
        )
        plan.box(
            "a20-stackhouse-north-control-glazing", "warm_glass", stack,
            x, 63.5 + (index % 2) * 8.0, 135.55,
            9.5, 2.2, 0.20, layer="mid",
        )
        if lod == 0:
            for stripe in (-0.32, 0.0, 0.32):
                plan.box(
                    "a20-stackhouse-north-window-mullion", "structural_steel", stack,
                    x + stripe * 9.5, 63.5 + (index % 2) * 8.0, 135.72,
                    0.12, 2.55, 0.12, layer="mid",
                )

    # Roof machinery and asymmetrical beacon frames make the crown read from
    # the fixed shot without relying on needle-thin scaffold silhouettes.
    crown_specs = (
        (44.0, 82.0, 94.3, 8.0),
        (68.0, 109.0, 120.3, 10.0),
        (97.0, 84.0, 108.3, 9.0),
        (120.0, 110.0, 101.3, 7.0),
    )
    for index, (x, z, base_y, radius) in enumerate(crown_specs):
        tank = plan.cylinder(
            "a20-stackhouse-crown-process-drum", "weathered_zinc", stack,
            x, base_y + 3.2, z, radius, 6.2,
            16 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=radius * 0.86, layer="mid",
        )
        plan.cylinder(
            "a20-stackhouse-crown-rust-band", "rust", stack,
            x, base_y + 3.4, z, radius + 0.15, 0.42,
            16 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=radius + 0.15, layer="mid",
        )
        antenna_height = 12.0 + index * 1.8
        plan.beam(
            "a20-stackhouse-crown-antenna", "structural_steel", stack,
            (x, base_y + 6.0, z), (x, base_y + 6.0 + antenna_height, z),
            0.28, 0.28, layer="mid",
        )
        plan.connect(tank, f"{stack}.{('a','b','c','d')[index]}.roof-cap",
                     axis="surface", overlap_m=0.08,
                     parent_face="bottom", child_face="top")

    # CUSTOMS NORTH LOADING FACE — deliberately irregular bays with deep
    # warm interiors, projecting canopies and an elevated maintenance route.
    bay_specs = (
        (-104.5, 15.0, 13.0, 6.5, "safety_orange"),
        (-84.0, 11.5, 9.5, 4.5, "weathered_zinc"),
        (-61.0, 18.5, 15.0, 8.0, "safety_orange"),
        (-35.0, 14.0, 11.5, 5.5, "weathered_zinc"),
    )
    selected_bays = bay_specs if lod < 2 else bay_specs[::2]
    for index, (x, width, height, canopy_depth, accent) in enumerate(selected_bays):
        plan.box(
            "a20-customs-deep-loading-cavity", "dark_concrete", customs,
            x, 7.0, -29.45, width + 1.8, height, 1.20,
            layer="mid", name=f"{customs}.a20.cavity.{index}",
        )
        plan.box(
            "a20-customs-warm-loading-interior", "warm_glass", customs,
            x, 6.5, -28.76, width - 2.2, max(4.0, height - 3.4), 0.28,
            layer="mid",
        )
        plan.box(
            "a20-customs-projecting-loading-canopy", "weathered_zinc", customs,
            x, height + 1.2, -27.0, width + 4.0, 0.56, canopy_depth,
            layer="mid",
        )
        plan.box(
            "a20-customs-dock-leveller", accent, customs,
            x, 0.50, -25.3, width - 3.0, 0.74, 5.0,
            layer="near",
        )
        if lod < 2:
            for side in (-1.0, 1.0):
                plan.box(
                    "a20-customs-loading-bumper", "structural_steel", customs,
                    x + side * (width * 0.5 - 1.2), 2.0, -27.9,
                    0.42, 3.0, 0.55, layer="near",
                )
            if lod == 0:
                slats = max(3, int(width // 3.0))
                for slat in range(slats):
                    plan.box(
                        "a20-customs-door-panel-joint", "rust", customs,
                        x - width * 0.38 + slat * width * 0.76 / max(1, slats - 1),
                        6.5, -28.55, 0.12, height - 3.0, 0.10, layer="mid",
                    )

    pilaster_xs = (-113.0, -95.0, -74.0, -48.0, -24.0)
    for index, x in enumerate(pilaster_xs):
        plan.box(
            "a20-customs-rear-structural-pilaster", "pale_concrete", customs,
            x, 25.0, -31.1, 2.4, 49.0, 4.0,
            layer="mid", name=f"{customs}.a20.pilaster.{index}",
        )
        if lod == 0:
            for y in (19.0, 31.0, 43.0):
                plan.box(
                    "a20-customs-pilaster-rust-collar", "rust", customs,
                    x, y, -33.15, 2.7, 0.32, 0.18, layer="mid",
                )

    upper_windows = (
        (-101.0, 16.0, 26.0), (-81.0, 12.0, 31.0),
        (-59.0, 18.0, 27.0), (-35.0, 14.0, 34.0),
    )
    for index, (x, width, y) in enumerate(upper_windows):
        plan.box(
            "a20-customs-upper-deep-window-recess", "dark_concrete", customs,
            x, y, -30.1, width + 1.6, 6.8, 1.0, layer="mid",
        )
        plan.box(
            "a20-customs-upper-occupied-window",
            "warm_glass" if index in {0, 2} else "dirty_glass", customs,
            x, y, -29.5, width - 1.4, 4.2, 0.20, layer="mid",
        )
        if lod == 0:
            for mullion in (-0.30, 0.0, 0.30):
                plan.box(
                    "a20-customs-upper-window-mullion", "structural_steel", customs,
                    x + width * mullion, y, -29.33,
                    0.13, 4.7, 0.12, layer="mid",
                )

    # Two large, unequal machine-hall windows sit in front of the inherited
    # small window grid.  Their deep dark reveals and exposed X trusses are
    # the dominant north facade language in the A20 fixed shot.
    machine_halls = (
        (-93.0, 33.0, 31.0, 20.0),
        (-48.0, 41.0, 34.0, 25.0),
    )
    for hall_index, (x, width, y, height) in enumerate(machine_halls):
        plan.box(
            "a20-customs-monumental-machine-hall-reveal", "dark_concrete", customs,
            x, y, -27.9, width + 2.2, height + 2.4, 1.45,
            layer="mid", name=f"{customs}.a20.machine-hall.{hall_index}.reveal",
        )
        plan.box(
            "a20-customs-monumental-machine-hall-glass", "dirty_glass", customs,
            x, y, -27.02, width - 1.2, height - 1.2, 0.22,
            layer="mid", name=f"{customs}.a20.machine-hall.{hall_index}.glass",
        )
        for side in (-1.0, 1.0):
            plan.beam(
                "a20-customs-machine-hall-x-truss", "structural_steel", customs,
                (x - width * 0.47, y + side * height * 0.44, -26.72),
                (x + width * 0.47, y - side * height * 0.44, -26.72),
                0.34 if lod == 0 else 0.52,
                0.24 if lod == 0 else 0.40, layer="mid",
            )
        mullions = 5 if lod == 0 else 3 if lod == 1 else 2
        for mullion in range(mullions):
            t = mullion / max(1, mullions - 1)
            mx = x - width * 0.43 + t * width * 0.86
            plan.box(
                "a20-customs-machine-hall-heavy-mullion", "rust", customs,
                mx, y, -26.62, 0.28, height - 1.0, 0.22, layer="mid",
            )
        plan.box(
            "a20-customs-machine-hall-warm-core", "warm_glass", customs,
            x + (-0.18 if hall_index == 0 else 0.22) * width,
            y - height * 0.16, -26.46,
            width * 0.24, height * 0.22, 0.16, layer="mid",
        )

    for pipe_index, x in enumerate((-116.0, -20.0)):
        plan.cylinder(
            "a20-customs-grounded-process-riser", "rust", customs,
            x, 27.0, -25.8, 0.82 + pipe_index * 0.18, 53.0,
            14 if lod == 0 else 9 if lod == 1 else 7,
            top_radius=0.72 + pipe_index * 0.16, layer="mid",
        )
        if lod < 2:
            for y in (9.0, 24.0, 39.0):
                plan.cylinder(
                    "a20-customs-process-riser-collar", "safety_orange", customs,
                    x, y, -25.8, 1.04 + pipe_index * 0.18, 0.46,
                    14 if lod == 0 else 9,
                    top_radius=1.04 + pipe_index * 0.18, layer="mid",
                )

    catwalk_y = 42.5
    plan.box(
        "a20-customs-rear-maintenance-catwalk", "weathered_zinc", customs,
        -68.0, catwalk_y, -27.7, 88.0, 0.52, 4.4, layer="mid",
    )
    if lod < 2:
        _add_guardrail(
            plan, customs, (-111.0, -25.6), (-25.0, -25.6), catwalk_y + 0.15,
            posts=22 if lod == 0 else 12, layer="mid",
        )
        _add_external_stair_run(
            plan, customs, (-116.0, 0.3, -20.5), (-114.0, 21.0, -28.0),
            3.0, lod, layer="mid",
        )
        _add_external_stair_run(
            plan, customs, (-114.0, 21.0, -28.0), (-108.0, 42.5, -26.5),
            3.0, lod, layer="mid",
        )

    # Sawtooth lanterns and offset service exhausts give each roof bay a
    # distinct operational read rather than four cloned triangles.
    for tooth in range(4):
        x = -100.0 + tooth * 21.25
        plan.box(
            "a20-customs-sawtooth-ridge-lantern", "warm_glass", customs,
            x + (tooth % 2) * 2.0, 67.0 - (tooth % 2) * 3.0, -64.0 + tooth * 2.5,
            6.5 + tooth, 2.2, 5.5, layer="mid",
        )
        if lod < 2:
            plan.cylinder(
                "a20-customs-roof-exhaust", "rust", customs,
                x - 3.0, 72.0 + tooth * 1.8, -55.0 - tooth * 4.0,
                0.72 + tooth * 0.08, 13.0 + tooth * 1.5,
                12 if lod == 0 else 8, top_radius=0.58,
                layer="mid",
            )

    # HUMAN-SCALE WORKING QUAY — dense, asymmetric operational clusters leave
    # the 15 m diagonal lane open while compressing its edges like ImageGen.
    roadside_clusters = (
        (-180.0, 184.0, -0.12), (-162.0, 165.0, 0.18),
        (-139.0, 145.0, -0.08), (-118.0, 128.0, 0.12),
        (-96.0, 107.0, -0.15), (-77.0, 88.0, 0.09),
        (-55.0, 68.0, -0.08), (-34.0, 48.0, 0.11),
    )
    cluster_step = 1 if lod == 0 else 2 if lod == 1 else 4
    for index, (x, z, yaw) in enumerate(roadside_clusters[::cluster_step]):
        # Alternating sides keep the route legible instead of creating a fence.
        side = -1.0 if index % 2 == 0 else 1.0
        px, pz = -0.54, -0.84
        cx, cz = x + px * side * 13.0, z + pz * side * 13.0
        plan.box(
            "a20-roadside-tactical-cover", "old_concrete", "souko-a20-public-realm",
            cx, 0.72, cz, 4.5 + (index % 3), 1.35, 1.1,
            yaw=yaw, layer="near",
        )
        _add_pallet_stack(plan, "souko-a20-public-realm", cx + 3.0, cz + 1.7,
                          lod, layer="near")
        if lod < 2:
            _add_container(
                plan, "souko-a20-public-realm", cx - 4.8, cz - 2.4,
                yaw + (math.pi / 2 if index % 3 == 0 else 0.0),
                "safety_orange" if index % 3 == 0 else "weathered_zinc",
                lod, layer="near",
            )
            if index % 3 == 1:
                _add_forklift(plan, "souko-a20-public-realm", cx + 1.0, cz - 3.8,
                              yaw + 0.4, lod)
            _add_worker(plan, "souko-a20-public-realm", cx - 1.5, cz + 3.0, yaw)

    if lod < 2:
        # Fixed-camera apron anchors.  These sit outside the 15 m road and
        # create a readable foreground scale layer instead of a blank runway.
        apron_anchors = (
            (-190.0, 159.0, -0.55, "forklift"),
            (-192.0, 130.0, -0.55, "pallets"),
            (-171.0, 151.0, -0.55, "container"),
            (-177.0, 120.0, -0.55, "barrier"),
        )
        for anchor_index, (x, z, yaw, kind) in enumerate(apron_anchors):
            plan.box(
                "a20-fixed-camera-apron-cover", "old_concrete",
                "souko-a20-public-realm", x, 0.68, z,
                5.5 + anchor_index, 1.25, 1.05, yaw=yaw, layer="near",
            )
            if kind == "forklift":
                _add_forklift(plan, "souko-a20-public-realm", x - 2.0, z + 2.6,
                              yaw + 0.35, lod)
            elif kind == "pallets":
                _add_pallet_stack(plan, "souko-a20-public-realm", x - 2.0, z + 2.0,
                                  lod, layer="near")
                _add_pallet_stack(plan, "souko-a20-public-realm", x + 2.2, z - 1.0,
                                  lod, layer="near")
            elif kind == "container":
                _add_container(
                    plan, "souko-a20-public-realm", x - 2.0, z + 2.0, yaw,
                    "weathered_zinc", lod, layer="near",
                )
            else:
                for offset in (-2.5, 0.0, 2.5):
                    plan.box(
                        "a20-apron-water-barrier", "safety_orange",
                        "souko-a20-public-realm",
                        x + offset, 0.58, z - offset * 0.55,
                        2.0, 1.05, 0.65, yaw=yaw, layer="near",
                    )

    # Painted hazard panels, drain grates and oil streaks are broad enough to
    # read at 1280 without consuming a texture atlas in this private proof.
    if lod < 2:
        for index in range(14 if lod == 0 else 7):
            t = 0.08 + index * 0.80 / (13 if lod == 0 else 6)
            x = -234.0 + (239.0 * t)
            z = 170.0 + (-156.0 * t)
            plan.box(
                "a20-quay-oil-and-tire-streak", "dark_concrete",
                "souko-a20-public-realm", x, 0.148, z,
                7.0 + (index % 3) * 2.0, 0.025, 0.32,
                yaw=-0.58, layer="near",
            )
            if index % 2 == 0:
                plan.box(
                    "a20-quay-hazard-panel", "safety_orange",
                    "souko-a20-public-realm", x - 6.8, 0.17, z - 4.4,
                    2.8, 0.04, 0.34, yaw=-0.58, layer="near",
                )

    # WORKING WATER EDGE — fenders, mooring lines, hooks and deck machinery
    # turn the existing hull/cranes into one coherent port operation.
    port = "souko-a20-south-port"
    fender_xs = (-190.0, -165.0, -140.0, -115.0, -90.0, -65.0, -40.0, -15.0)
    for index, x in enumerate(fender_xs[::(1 if lod < 2 else 2)]):
        plan.box(
            "a20-quay-rubber-fender", "dark_concrete", port,
            x, 0.5, 183.1, 3.2, 3.6, 1.0,
            layer="far", outside_playable=True,
        )
        plan.cylinder(
            "a20-quay-heavy-bollard", "structural_steel", port,
            x + 5.5, 1.0, 178.6, 0.72, 1.45,
            12 if lod == 0 else 8, top_radius=0.92,
            layer="far", outside_playable=True,
        )
    if lod < 2:
        for index, (quay_x, ship_x) in enumerate(((-88.0, -79.0), (-58.0, -48.0),
                                                  (-28.0, -17.0), (0.0, 8.0))):
            plan.beam(
                "a20-cargo-ship-mooring-line", "pallet_wood", port,
                (quay_x, 1.4, 178.8), (ship_x, 5.4, 187.0),
                0.12 if lod == 0 else 0.18,
                0.10 if lod == 0 else 0.15,
                layer="far", outside_playable=True,
            )
        for crane_index, (x, height, angle) in enumerate(((-42.0, 57.0, -2.79),
                                                           (-103.0, 68.0, -2.92),
                                                           (-166.0, 61.0, -3.06))):
            dx, dz = math.cos(angle), math.sin(angle)
            hook_x = x + dx * 50.0
            hook_z = 169.0 + dz * 50.0
            plan.box(
                "a20-port-crane-hook-block", "safety_orange", port,
                hook_x, 3.9, hook_z, 1.4, 2.2, 1.0,
                yaw=angle, layer="far", outside_playable=True,
            )
            plan.cylinder(
                "a20-port-crane-hook", "structural_steel", port,
                hook_x, 2.45, hook_z, 0.36, 1.1,
                10 if lod == 0 else 7, top_radius=0.18,
                layer="far", outside_playable=True,
            )
        for x in (-63.0, -36.0, -8.0):
            plan.cylinder(
                "a20-cargo-ship-deck-vent", "weathered_zinc", port,
                x, 8.4, 188.0, 0.65, 3.2,
                12 if lod == 0 else 8, top_radius=0.78,
                layer="far", outside_playable=True,
            )
            plan.box(
                "a20-cargo-ship-deck-hatch", "rust", port,
                x + 4.0, 7.2, 188.0, 5.5, 0.42, 5.0,
                layer="far", outside_playable=True,
            )

        quay_cargo = (
            (-178.0, 171.0, 0.0), (-164.0, 174.0, 0.0),
            (-140.0, 171.5, math.pi / 2), (-128.0, 174.5, math.pi / 2),
            (-104.0, 171.5, 0.0), (-92.0, 174.0, 0.0),
            (-16.0, 171.5, math.pi / 2), (0.0, 174.0, math.pi / 2),
        )
        for cargo_index, (x, z, yaw) in enumerate(quay_cargo[::(1 if lod == 0 else 2)]):
            _add_container(
                plan, port, x, z, yaw,
                "safety_orange" if cargo_index % 3 == 0 else "weathered_zinc",
                lod, layer="far", outside=True,
            )
            if lod == 0 and cargo_index % 2 == 0:
                _add_pallet_stack(plan, port, x + 4.5, z - 2.4, lod, layer="far")

        for tank_index, x in enumerate((22.0, 34.0, 48.0)):
            plan.cylinder(
                "a20-quay-fuel-service-tank", "weathered_zinc", port,
                x, 3.5, 175.0, 3.8 + tank_index * 0.4, 6.8,
                16 if lod == 0 else 10, top_radius=3.4 + tank_index * 0.4,
                layer="far", outside_playable=True,
            )
            plan.beam(
                "a20-quay-fuel-service-pipe", "rust", port,
                (x, 6.7, 175.0), (x - 8.0, 6.7 + tank_index, 184.0),
                0.34, 0.30, layer="far", outside_playable=True,
            )

    # A layered harbor horizon closes the blank sea without raster shortcuts.
    horizon = "souko-a20-harbor-depth"
    horizon_specs = (
        (-220.0, 292.0, 54.0, 24.0, 30.0),
        (-150.0, 304.0, 62.0, 26.0, 36.0),
        (-72.0, 300.0, 58.0, 25.0, 28.0),
        (12.0, 306.0, 66.0, 28.0, 34.0),
        (102.0, 296.0, 72.0, 30.0, 40.0),
        (194.0, 308.0, 58.0, 24.0, 32.0),
    )
    selection = horizon_specs if lod == 0 else horizon_specs[::2] if lod == 1 else horizon_specs[::3]
    for index, (x, z, width, depth, height) in enumerate(selection):
        _add_gabled_warehouse(
            plan, horizon, f"harbor-{index}", x, z, width, depth, height,
            0.03 * (-1 if index % 2 else 1), lod,
            layer="far", outside=True,
        )
        if lod < 2:
            plan.cylinder(
                "a20-harbor-horizon-chimney", "rust", horizon,
                x + width * 0.31, height + 12.0, z,
                1.2, 28.0, 12 if lod == 0 else 8,
                top_radius=0.95, layer="far", outside_playable=True,
            )


def build_plan(lod: int = 0) -> SpecPlan:
    """Return the deterministic standalone A20 Souko plan."""
    plan = SpecPlan(lod)
    _build_ground_and_foreground(plan, lod)
    _build_layered_city(plan, lod)
    _build_port(plan, lod)
    _build_stackhouse(plan, lod)
    _build_customs(plan, lod)
    _build_inter_landmark_transfer(plan, lod)
    _build_a20_art_pass(plan, lod)
    validate_plan(plan)
    return plan


def spec_bounds(spec: Mapping[str, Any]) -> tuple[float, float, float, float, float, float]:
    """Return runtime minX/minY/minZ/maxX/maxY/maxZ bounds for one spec."""
    kind = spec["kind"]
    if kind in {"box", "oriented_box"}:
        yaw = float(spec.get("yaw", 0.0))
        half_x = abs(math.cos(yaw)) * float(spec["w"]) / 2 + abs(math.sin(yaw)) * float(spec["d"]) / 2
        half_z = abs(math.sin(yaw)) * float(spec["w"]) / 2 + abs(math.cos(yaw)) * float(spec["d"]) / 2
        half_y = float(spec["h"]) / 2
        return (
            float(spec["x"]) - half_x, float(spec["y"]) - half_y,
            float(spec["z"]) - half_z, float(spec["x"]) + half_x,
            float(spec["y"]) + half_y, float(spec["z"]) + half_z,
        )
    if kind == "beam":
        start, end = spec["start"], spec["end"]
        pad = max(float(spec["width"]), float(spec["depth"])) / 2
        return tuple(min(start[i], end[i]) - pad for i in range(3)) + tuple(
            max(start[i], end[i]) + pad for i in range(3)
        )
    if kind == "cylinder":
        radius = max(float(spec["radius"]), float(spec["topRadius"]))
        return (
            float(spec["x"]) - radius,
            float(spec["y"]) - float(spec["height"]) / 2,
            float(spec["z"]) - radius,
            float(spec["x"]) + radius,
            float(spec["y"]) + float(spec["height"]) / 2,
            float(spec["z"]) + radius,
        )
    if kind == "panel":
        corners = spec["corners"]
        pad = float(spec["thickness"])
        return (
            min(point[0] for point in corners) - pad,
            min(point[1] for point in corners) - pad,
            min(point[2] for point in corners) - pad,
            max(point[0] for point in corners) + pad,
            max(point[1] for point in corners) + pad,
            max(point[2] for point in corners) + pad,
        )
    raise ValueError(f"unsupported kind: {kind}")


def estimated_triangles(spec: Mapping[str, Any]) -> int:
    kind = spec["kind"]
    if kind in {"box", "oriented_box", "beam"}:
        return 12
    if kind == "cylinder":
        return max(8, 4 * int(spec["segments"]) - 4)
    if kind == "panel":
        return 12 if len(spec["corners"]) == 4 else 8
    raise ValueError(f"unsupported kind: {kind}")


def plan_metrics(plan: SpecPlan) -> dict[str, Any]:
    bounds = [spec_bounds(spec) for spec in plan.specs]
    roles = Counter(spec["role"] for spec in plan.specs)
    materials = Counter(spec["material"] for spec in plan.specs)
    layers = Counter(spec["layer"] for spec in plan.specs)
    kinds = Counter(spec["kind"] for spec in plan.specs)
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
    }


def _aabb_hits_xz(aabb: Sequence[float], x: float, z: float, padding: float) -> bool:
    return (
        aabb[0] - padding <= x <= aabb[3] + padding
        and aabb[2] - padding <= z <= aabb[5] + padding
    )


def spawn_intrusions(plan: SpecPlan, clearance_m: float = 5.0) -> list[dict[str, Any]]:
    intrusions = []
    for spec in plan.specs:
        if not spec["blocksGameplay"] or spec["outsidePlayable"]:
            continue
        aabb = spec_bounds(spec)
        for spawn in CANONICAL_PLAYER_SPAWNS:
            if _aabb_hits_xz(aabb, spawn[0], spawn[2], clearance_m):
                intrusions.append({"spec": spec["name"], "spawn": spawn})
    return intrusions


def route_intrusions(plan: SpecPlan) -> list[dict[str, Any]]:
    intrusions = []
    for spec in plan.specs:
        if not spec["blocksGameplay"] or spec["outsidePlayable"]:
            continue
        aabb = spec_bounds(spec)
        for road in CANONICAL_ROADS:
            bounds = road["bounds"]
            if (
                aabb[0] < bounds["maxX"] and aabb[3] > bounds["minX"]
                and aabb[2] < bounds["maxZ"] and aabb[5] > bounds["minZ"]
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
    if _role_count(plan.specs, "stackhouse-completed-tower-envelope") != 4:
        raise ValueError("Stackhouse must keep four completed occupied towers")
    expected_bridges = 2 if plan.lod < 2 else 1
    if _role_count(plan.specs, "stackhouse-deep-transfer-bridge-floor") != expected_bridges:
        raise ValueError("Stackhouse bridge identity count changed")
    for role in (
        "customs-sawtooth-roof",
        "customs-sawtooth-glazed-face",
        "customs-sawtooth-triangular-glass-gable",
        "customs-sawtooth-occupied-bay-volume",
    ):
        if _role_count(plan.specs, role) != 4:
            raise ValueError(f"Customs must keep exactly four: {role}")
    if spawn_intrusions(plan):
        raise ValueError(f"spawn intrusions: {spawn_intrusions(plan)}")
    if route_intrusions(plan):
        raise ValueError(f"road intrusions: {route_intrusions(plan)}")
    return metrics


def emit_plan(
    builder: Any,
    plan: SpecPlan,
    material_map: Mapping[str, str] = DEFAULT_INTEGRATION_MATERIAL_MAP,
) -> None:
    """Emit only through a small reviewed builder protocol."""
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
    """Return a deliberately non-certifying producer status."""
    items = [
        {
            "category": category,
            "score": 0.0,
            "evidence": "A20 producer build; independent visual review has not certified this category.",
        }
        for category in FIXED_SCORE_CATEGORIES
    ]
    return {
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "referenceSha256": REFERENCE_SHA256,
        "fixedCategoryOrder": list(FIXED_SCORE_CATEGORIES),
        "items": items,
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


__all__ = [
    "CANONICAL_BOUNDS", "CANONICAL_PLAYER_SPAWNS", "CANONICAL_ROADS",
    "CUSTOMS_ID", "DEFAULT_INTEGRATION_MATERIAL_MAP", "FIXED_SCORE_CATEGORIES",
    "LANDMARKS", "LOD_API", "MATERIALS", "MIN_CONTACT_OVERLAP_M",
    "PLAYER_EYE_M", "PRIMARY_CAMERA", "PRIVATE_OUTPUT_ROOT", "PRIVATE_VIEWS",
    "REFERENCE_MATCH_VERSION", "REFERENCE_PATH", "REFERENCE_SHA256",
    "STACKHOUSE_ID", "STAGE_ID", "SpecPlan", "build_plan", "emit_plan",
    "estimated_triangles", "plan_metrics", "producer_provisional_scorecard",
    "route_intrusions", "spawn_intrusions", "spec_bounds", "validate_plan",
]
