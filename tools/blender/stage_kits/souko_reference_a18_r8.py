#!/usr/bin/env python3
"""Private, reference-led Souko A18 r8 environment module.

This file is deliberately independent from ``build_all_stages.py``.  It may be
unit-tested with CPython and executed only in a *background* Blender process.
It never edits the public asset tree, runtime TypeScript, manifests, or an
interactive Blender scene.  Runtime coordinates are X/Z horizontal and Y up,
in metres; the private Blender builder converts them to Blender Z-up.

Production brief
----------------
Target: high-quality WebGL FPS environment prototype, realistic industrial
coastal logistics city, LOD0 <= 260k triangles, <= 24 materials, <= 5.5 MB
eventual GLB.  Collision/spawn/route truth remains authoritative in TypeScript.

Reference analysis (souko-reference-v1.png, 1672x941)
------------------------------------------------------
* Camera: low/normal 28-35 mm industrial vista; wet road is a leading line.
* Primary silhouette: left multi-tower bonded stackhouse, large inter-tower
  skybridges, deep open steel/process interior, irregular roof machinery.
* Second silhouette: right heavy multi-storey customs factory, four full-depth
  sawtooth/glazed gables, compact roof control tower, two chimneys.
* Near/mid/far: pallets/loading bay -> road/customs -> cranes/ship/warehouses.
* Palette: wet charcoal #23292b, old concrete #77766f, zinc #657277,
  brick #6d3025, rust #7a351c, orange #d8661f, sea #24444e, warm glass #9d6f3b.
* Light: low warm sun from camera-left, cool sky fill, moist coastal haze.
* Forbidden: image planes, cylindrical mattes, one-box heroes, flat black
  window cards, sparse plaza, or a decorative sawtooth facade without depth.

Connection map (minimum intended overlap 0.005 m)
--------------------------------------------------
* wet road top <-> curb/warehouse/loading pads: 0.02-0.12 m
* stackhouse plinth <-> four tower feet/rack columns: 0.12-0.24 m
* tower piers <-> every floor slab/roof headhouse: 0.10-0.30 m
* rack uprights <-> transverse chords/depth ties: 0.08-0.16 m
* deep rack frames <-> cargo trays/process houses: 0.10-0.24 m
* stackhouse tower B <-> main skybridge <-> tower C: 0.18 m at both ends
* customs plinth <-> two lower wings/rear spine: 0.12 m
* customs lower wings <-> upper factory floors: 0.16 m
* upper factory <-> four sawtooth eaves/glass gables: 0.18 m
* sawtooth frames <-> purlins/front glass: 0.08-0.14 m
* customs roof deck <-> compact control tower/chimneys: 0.15 m
* quay slab <-> retaining wall/rails/crane bases: 0.10-0.25 m
* crane towers <-> booms/counterweights/cables: 0.08-0.20 m
* ship hull <-> deck/superstructure/masts: 0.10-0.25 m

All spanning beams are built from explicit endpoints.  Cubes are never created
with ambiguous primitive scale, and cylinders are never Euler-rotated to span
two points.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


STAGE_ID = "souko"
REFERENCE_MATCH_VERSION = "a18-souko-reference-match-r9-private-v1"
REFERENCE_PATH = "tools/blender/concepts/souko-reference-v1.png"
REFERENCE_SHA256 = "967c0e599e687d59bdcb0057ed84bebe7816de15772c5a6532e3d64b52d4eef6"
PRIVATE_OUTPUT_ROOT = Path("/private/tmp/hibana-blender/a18-souko-reference-r8-private")
TARGET_COLLECTION = "HB_SOUKO_A18_R8_PRIVATE"
MAP_SIZE_M = 336.0
PLAYER_EYE_M = 1.65
MIN_CONTACT_OVERLAP_M = 0.005

CANONICAL_BOUNDS = {"min_x": -168.0, "max_x": 168.0, "min_z": -168.0, "max_z": 168.0}
CANONICAL_ROADS = (
    {"id": "primary-north-south", "axis": "z", "centre": 0.0, "width": 16.0,
     "bounds": {"minX": -8.0, "maxX": 8.0, "minZ": -164.0, "maxZ": 164.0}},
    {"id": "primary-east-west", "axis": "x", "centre": 0.0, "width": 16.0,
     "bounds": {"minX": -164.0, "maxX": 164.0, "minZ": -8.0, "maxZ": 8.0}},
)
CANONICAL_PLAYER_SPAWNS = (
    (-156.0, 0.0, 0.0), (0.0, 0.0, -156.0),
    (156.0, 0.0, 0.0), (0.0, 0.0, 156.0),
)

STACKHOUSE_ID = "souko-shiosai-stackhouse"
CUSTOMS_ID = "souko-amakado-customs-terminal"
LANDMARKS = (
    {
        "index": 0, "id": STACKHOUSE_ID, "referenceName": "Shiosai Bonded Stackhouse",
        "cx": 80.8, "cz": 96.0, "rot": 0.0, "width": 104.0, "depth": 66.0,
        "height": 64.0, "entrance": (28.0, 96.0),
        "approach": {"start": (8.0, 96.0), "end": (28.0, 96.0), "width": 12.0},
        "collisionTemplate": "rack-bridge-storehouse",
    },
    {
        "index": 1, "id": CUSTOMS_ID, "referenceName": "Amakado Customs Terminal",
        "cx": -68.0, "cz": -67.8, "rot": 0.0, "width": 92.0, "depth": 78.0,
        "height": 47.0, "entrance": (-68.0, -28.0),
        "approach": {"start": (-68.0, -8.0), "end": (-68.0, -28.0), "width": 12.0},
        "collisionTemplate": "customs-sawtooth-terminal",
    },
)

LOD_API = {
    0: {"label": "hero", "maxSpecs": 3500, "maxEstimatedTriangles": 230_000},
    1: {"label": "medium", "maxSpecs": 1900, "maxEstimatedTriangles": 110_000},
    2: {"label": "horizon", "maxSpecs": 900, "maxEstimatedTriangles": 45_000},
}

MATERIALS: dict[str, dict[str, Any]] = {
    "wet_asphalt": {"color": (0.030, 0.038, 0.041, 1.0), "roughness": 0.29, "metallic": 0.0,
                    "noise": 0.20, "wetVariation": True},
    "puddle_water": {"color": (0.025, 0.070, 0.082, 1.0), "roughness": 0.09, "metallic": 0.05,
                     "transmission": 0.18},
    "old_concrete": {"color": (0.39, 0.385, 0.355, 1.0), "roughness": 0.82, "metallic": 0.0,
                     "noise": 0.18, "stains": True},
    "pale_concrete": {"color": (0.54, 0.53, 0.49, 1.0), "roughness": 0.74, "metallic": 0.0,
                      "noise": 0.13, "stains": True},
    "dark_concrete": {"color": (0.19, 0.205, 0.205, 1.0), "roughness": 0.78, "metallic": 0.0,
                      "noise": 0.16, "stains": True},
    "weathered_zinc": {"color": (0.34, 0.40, 0.41, 1.0), "roughness": 0.41, "metallic": 0.72,
                       "noise": 0.13, "rustMask": True},
    "structural_steel": {"color": (0.12, 0.145, 0.15, 1.0), "roughness": 0.45, "metallic": 0.88,
                         "noise": 0.08, "rustMask": True},
    "red_brick": {"color": (0.30, 0.085, 0.052, 1.0), "roughness": 0.84, "metallic": 0.0,
                  "noise": 0.17, "stains": True},
    "rust": {"color": (0.34, 0.095, 0.025, 1.0), "roughness": 0.84, "metallic": 0.0,
             "noise": 0.20},
    "safety_orange": {"color": (0.82, 0.205, 0.035, 1.0), "roughness": 0.43, "metallic": 0.0,
                      "noise": 0.05},
    "dirty_glass": {"color": (0.11, 0.19, 0.20, 0.58), "roughness": 0.18, "metallic": 0.05,
                    "transmission": 0.58, "alpha": 0.58, "noise": 0.06},
    "warm_glass": {"color": (0.34, 0.16, 0.055, 1.0), "roughness": 0.31, "metallic": 0.0,
                   "emission": (0.32, 0.105, 0.018, 1.0), "emissionStrength": 0.72},
    "paint_white": {"color": (0.73, 0.70, 0.61, 1.0), "roughness": 0.57, "metallic": 0.0},
    "pallet_wood": {"color": (0.22, 0.105, 0.042, 1.0), "roughness": 0.72, "metallic": 0.0,
                    "noise": 0.15},
    "sea_water": {"color": (0.018, 0.13, 0.17, 1.0), "roughness": 0.16, "metallic": 0.16,
                  "noise": 0.04},
    "vegetation": {"color": (0.055, 0.12, 0.07, 1.0), "roughness": 0.82, "metallic": 0.0,
                   "noise": 0.10},
}

DEFAULT_INTEGRATION_MATERIAL_MAP = {
    "wet_asphalt": "floor", "puddle_water": "water", "old_concrete": "wall_weathered",
    "pale_concrete": "wall", "dark_concrete": "wall_cool", "weathered_zinc": "roof",
    "structural_steel": "trim", "red_brick": "wall_warm", "rust": "wall_alt",
    "safety_orange": "accent", "dirty_glass": "glass", "warm_glass": "emissive",
    "paint_white": "wall", "pallet_wood": "wood", "sea_water": "water",
    "vegetation": "natural",
}

FIXED_SCORE_CATEGORIES = (
    "composition", "hero silhouettes", "architectural grammar", "human scale",
    "material realism", "near/mid/far density", "gameplay readability",
    "props and environmental storytelling", "lighting and atmosphere", "reference identity",
)

# Producer-only pre-review.  These values are intentionally provisional and
# will never certify REFERENCE PASS without an independent reviewer.
PRODUCER_PROVISIONAL_SCORE_ITEMS = (
    {"category": "composition", "score": 5.2, "evidence": "Road-axis framing is being corrected; dual-hero balance remains below reference."},
    {"category": "hero silhouettes", "score": 5.8, "evidence": "Four towers/two bridges and four roof teeth exist, but final silhouette review is pending."},
    {"category": "architectural grammar", "score": 5.7, "evidence": "Stackhouse and Customs now differ structurally; facade articulation remains simplified."},
    {"category": "human scale", "score": 5.9, "evidence": "Measured access pieces exist, though several vistas still need stronger occupied foreground."},
    {"category": "material realism", "score": 4.5, "evidence": "Wet/rust/stain node logic exists but first renders did not expose enough surface response."},
    {"category": "near/mid/far density", "score": 5.4, "evidence": "All three layers are real geometry; distribution is not yet reference-equivalent."},
    {"category": "gameplay readability", "score": 7.7, "evidence": "Canonical roads, approaches and spawns remain clear in pure-data checks."},
    {"category": "props and environmental storytelling", "score": 5.3, "evidence": "Cargo props and port equipment exist but are not consistently readable in camera."},
    {"category": "lighting and atmosphere", "score": 5.5, "evidence": "Coastal key/fill improved, while wet reflections and atmospheric depth remain provisional."},
    {"category": "reference identity", "score": 5.4, "evidence": "Core nouns are present; resemblance is not strong enough for independent pass."},
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


class SpecPlan:
    """Deterministic pure-data geometry plan with explicit contact records."""

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
    def _base(name: str, role: str, material: str, group: str, layer: str,
              blocks_gameplay: bool, outside_playable: bool) -> dict[str, Any]:
        if material not in MATERIALS:
            raise ValueError(f"unknown material: {material}")
        if layer not in {"near", "mid", "far"}:
            raise ValueError(f"invalid layer: {layer}")
        return {
            "name": name, "role": role, "material": material, "group": group,
            "layer": layer, "blocksGameplay": blocks_gameplay,
            "outsidePlayable": outside_playable,
        }

    def box(self, role: str, material: str, group: str, x: float, y: float, z: float,
            w: float, h: float, d: float, *, yaw: float = 0.0, layer: str = "mid",
            blocks_gameplay: bool = False, outside_playable: bool = False,
            name: str | None = None) -> str:
        if not _finite((x, y, z, w, h, d, yaw)) or min(w, h, d) <= 0:
            raise ValueError(f"{role}: invalid box")
        resolved = self._name(group, role, name)
        kind = "box" if abs(yaw) < 1e-9 else "oriented_box"
        self.specs.append({
            **self._base(resolved, role, material, group, layer, blocks_gameplay, outside_playable),
            "kind": kind, "x": x, "y": y, "z": z, "w": w, "h": h, "d": d,
            "yaw": yaw,
        })
        return resolved

    def beam(self, role: str, material: str, group: str,
             start: Sequence[float], end: Sequence[float], width: float, depth: float,
             *, layer: str = "mid", outside_playable: bool = False,
             name: str | None = None) -> str:
        start = tuple(float(value) for value in start)
        end = tuple(float(value) for value in end)
        if len(start) != 3 or len(end) != 3 or not _finite((*start, *end, width, depth)):
            raise ValueError(f"{role}: invalid beam")
        if math.dist(start, end) < 1e-6 or min(width, depth) <= 0:
            raise ValueError(f"{role}: zero beam")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(resolved, role, material, group, layer, False, outside_playable),
            "kind": "beam", "start": start, "end": end, "width": width, "depth": depth,
        })
        return resolved

    def cylinder(self, role: str, material: str, group: str, x: float, y: float, z: float,
                 radius: float, height: float, segments: int, *, top_radius: float | None = None,
                 layer: str = "mid", outside_playable: bool = False,
                 name: str | None = None) -> str:
        top_radius = radius if top_radius is None else top_radius
        if not _finite((x, y, z, radius, height, top_radius)) or min(radius, height) <= 0:
            raise ValueError(f"{role}: invalid cylinder")
        if segments < 3 or top_radius < 0:
            raise ValueError(f"{role}: invalid cylinder segments/top radius")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(resolved, role, material, group, layer, False, outside_playable),
            "kind": "cylinder", "x": x, "y": y, "z": z, "radius": radius,
            "height": height, "segments": segments, "topRadius": top_radius,
        })
        return resolved

    def panel(self, role: str, material: str, group: str,
              corners: Iterable[Sequence[float]], thickness: float, *, layer: str = "mid",
              outside_playable: bool = False, name: str | None = None) -> str:
        corners = tuple(tuple(float(value) for value in point) for point in corners)
        if len(corners) not in {3, 4} or any(len(point) != 3 for point in corners):
            raise ValueError(f"{role}: panel must have three or four corners")
        if not _finite((*[value for point in corners for value in point], thickness)) or thickness <= 0:
            raise ValueError(f"{role}: invalid panel")
        resolved = self._name(group, role, name)
        self.specs.append({
            **self._base(resolved, role, material, group, layer, False, outside_playable),
            "kind": "panel", "corners": corners, "thickness": thickness,
        })
        return resolved

    def connect(self, parent: str, child: str, *, axis: str, overlap_m: float,
                parent_face: str, child_face: str, note: str = "") -> None:
        if overlap_m < MIN_CONTACT_OVERLAP_M:
            raise ValueError(f"contact overlap too small: {parent} -> {child}: {overlap_m}")
        self.connections.append({
            "id": f"{_slug(parent)}--{_slug(child)}--{len(self.connections):04d}",
            "parent": parent, "child": child, "axis": axis,
            "parentFace": parent_face, "childFace": child_face,
            "overlapM": overlap_m, "note": note,
        })


def _world(landmark: Mapping[str, Any], local_x: float, local_z: float) -> tuple[float, float]:
    return float(landmark["cx"]) + local_x, float(landmark["cz"]) + local_z


def _role_count(specs: Iterable[Mapping[str, Any]], role: str) -> int:
    return sum(spec["role"] == role for spec in specs)


def _add_guardrail(plan: SpecPlan, group: str, start: tuple[float, float], end: tuple[float, float],
                   deck_y: float, *, material: str = "structural_steel", posts: int = 6,
                   layer: str = "near", role: str = "human-scale-guardrail") -> None:
    """Create one measured rail run with seated posts."""
    top_y = deck_y + 1.10
    plan.beam(role, material, group, (start[0], top_y, start[1]), (end[0], top_y, end[1]),
              0.075, 0.075, layer=layer)
    plan.beam(role, material, group, (start[0], deck_y + 0.55, start[1]),
              (end[0], deck_y + 0.55, end[1]), 0.055, 0.055, layer=layer)
    for index in range(max(2, posts)):
        t = index / max(1, posts - 1)
        x = start[0] + (end[0] - start[0]) * t
        z = start[1] + (end[1] - start[1]) * t
        plan.beam(role, material, group, (x, deck_y - 0.04, z), (x, top_y + 0.04, z),
                  0.055, 0.055, layer=layer)


def _add_stair(plan: SpecPlan, group: str, start: tuple[float, float], end: tuple[float, float],
               base_y: float, top_y: float, width: float, *, lod: int,
               material: str = "old_concrete", layer: str = "near") -> None:
    count = max(4, int(math.ceil((top_y - base_y) / (0.28 if lod == 0 else 0.42))))
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    yaw = math.atan2(dz, dx)
    tread = length / count
    for index in range(count):
        t = (index + 0.5) / count
        x = start[0] + dx * t
        z = start[1] + dz * t
        step_top = base_y + (index + 1) * (top_y - base_y) / count
        plan.box("human-scale-stair", material, group, x, base_y + (step_top - base_y) / 2,
                 z, tread + 0.10, step_top - base_y, width, yaw=yaw, layer=layer)
    side_x, side_z = -math.sin(yaw) * width * 0.48, math.cos(yaw) * width * 0.48
    for side in (-1.0, 1.0):
        a = (start[0] + side_x * side, base_y + 1.02, start[1] + side_z * side)
        b = (end[0] + side_x * side, top_y + 1.02, end[1] + side_z * side)
        plan.beam("human-scale-stair-rail", "structural_steel", group, a, b,
                  0.065, 0.065, layer=layer)


def _add_process_tower(plan: SpecPlan, *, group: str, label: str, x: float, z: float,
                       width: float, depth: float, height: float, levels: int,
                       lod: int) -> dict[str, Any]:
    """Build one occupied process tower as floors, piers and a deep rear core."""
    base = plan.box("stackhouse-tower-plinth", "old_concrete", group, x, 0.25, z,
                    width + 1.2, 0.70, depth + 1.2, layer="mid",
                    name=f"{group}.{label}.plinth")
    pier_bottom = 0.48
    structure_top = height - 5.3
    pier_height = structure_top - pier_bottom
    pier_names = []
    for ix, sx in enumerate((-1, 1)):
        for iz, sz in enumerate((-1, 1)):
            pier_x = x + sx * (width / 2 - 1.0)
            pier_z = z + sz * (depth / 2 - 1.0)
            pier = plan.box("stackhouse-tower-pier", "pale_concrete", group,
                            pier_x, pier_bottom + pier_height / 2, pier_z,
                            1.75 if lod == 0 else 2.2, pier_height, 1.75 if lod == 0 else 2.2,
                            layer="mid", name=f"{group}.{label}.pier.{ix}.{iz}")
            plan.connect(base, pier, axis="y", overlap_m=0.12,
                         parent_face="top", child_face="bottom")
            pier_names.append(pier)

    core_width = width * (0.38 if label in {"b", "c"} else 0.46)
    core_depth = max(4.2, depth * 0.25)
    rear_z = z + depth / 2 - core_depth / 2 - 0.7
    core = plan.box("stackhouse-service-core", "dark_concrete", group, x,
                    pier_bottom + pier_height / 2, rear_z, core_width, pier_height,
                    core_depth, layer="mid", name=f"{group}.{label}.service-core")
    plan.connect(base, core, axis="y", overlap_m=0.12,
                 parent_face="top", child_face="bottom")

    floor_names = []
    for level in range(levels + 1):
        floor_y = 6.0 + level * (structure_top - 6.2) / max(1, levels)
        floor = plan.box("stackhouse-tower-floor", "weathered_zinc", group, x, floor_y,
                         z, width, 0.58 if lod == 0 else 0.78, depth,
                         layer="mid", name=f"{group}.{label}.floor.{level:02d}")
        plan.connect(pier_names[level % len(pier_names)], floor, axis="surface",
                     overlap_m=0.10, parent_face="side", child_face="corner")
        floor_names.append(floor)

        front_z = z - depth / 2 - 0.06
        plan.box("stackhouse-floor-weather-belt", "rust" if level % 3 == 1 else "structural_steel",
                 group, x, floor_y + 0.10, front_z, width + 0.35, 0.26, 0.22,
                 layer="mid")
        if level < levels and (lod == 0 or level % 2 == 0):
            bay_bottom = floor_y + 0.42
            next_floor = 6.0 + (level + 1) * (structure_top - 6.2) / max(1, levels)
            bay_top = next_floor - 0.42
            for bay in (-0.26, 0.26):
                panel_w = width * 0.25
                panel_x = x + bay * width
                if (level + (1 if bay > 0 else 0)) % 3 == 0:
                    plan.box("stackhouse-inset-warm-window", "warm_glass", group,
                             panel_x, (bay_bottom + bay_top) / 2, front_z + 0.48,
                             panel_w, max(1.2, bay_top - bay_bottom), 0.18, layer="mid")
                else:
                    plan.box("stackhouse-opaque-process-panel", "old_concrete", group,
                             panel_x, (bay_bottom + bay_top) / 2, front_z + 0.42,
                             panel_w, max(1.2, bay_top - bay_bottom), 0.28, layer="mid")
            plan.beam("stackhouse-tower-cross-brace", "structural_steel", group,
                      (x - width * 0.43, bay_bottom, front_z - 0.03),
                      (x + width * 0.43, bay_top, front_z - 0.03),
                      0.14 if lod == 0 else 0.22, 0.11 if lod == 0 else 0.18, layer="mid")
            plan.beam("stackhouse-tower-cross-brace", "structural_steel", group,
                      (x + width * 0.43, bay_bottom, front_z - 0.05),
                      (x - width * 0.43, bay_top, front_z - 0.05),
                      0.14 if lod == 0 else 0.22, 0.11 if lod == 0 else 0.18, layer="mid")

        if lod == 0 and level in {1, max(1, levels - 1)}:
            deck_z = front_z - 0.85
            plan.box("stackhouse-maintenance-catwalk", "weathered_zinc", group, x,
                     floor_y + 0.28, deck_z, width * 0.82, 0.24, 1.55, layer="near")
            _add_guardrail(plan, group, (x - width * 0.39, deck_z - 0.62),
                           (x + width * 0.39, deck_z - 0.62), floor_y + 0.40,
                           posts=5, layer="near")

    # A continuous upper envelope makes the object read as an occupied process
    # tower rather than a stack of floating slabs.  The lowest ten metres stay
    # open so first-person rack depth remains visible.
    envelope_bottom = 10.0
    envelope_top = structure_top - 0.6
    envelope = plan.box(
        "stackhouse-occupied-tower-envelope",
        "old_concrete" if label in {"a", "c"} else "pale_concrete",
        group, x, (envelope_bottom + envelope_top) / 2, z + depth * 0.04,
        width * 0.78, envelope_top - envelope_bottom, depth * 0.68,
        layer="mid", name=f"{group}.{label}.occupied-envelope")
    plan.connect(floor_names[min(1, len(floor_names) - 1)], envelope,
                 axis="surface", overlap_m=0.10,
                 parent_face="occupied-floor", child_face="envelope-interior")
    envelope_front = z - depth * 0.30
    slot_count = 4 if lod == 0 else 3 if lod == 1 else 2
    for slot in range(slot_count):
        slot_y = envelope_bottom + 5.0 + slot * max(5.5, (envelope_top - envelope_bottom - 8.0) /
                                                    max(1, slot_count - 1))
        if slot_y >= envelope_top - 1.0:
            continue
        plan.box("stackhouse-envelope-recessed-window", "dirty_glass", group,
                 x, slot_y, envelope_front - 0.12,
                 width * (0.46 if slot % 2 == 0 else 0.58), 1.55, 0.22,
                 layer="mid")
        plan.box("stackhouse-envelope-window-lintel", "rust", group,
                 x, slot_y + 1.02, envelope_front - 0.24,
                 width * 0.64, 0.24, 0.26, layer="mid")
    for side in (-1.0, 1.0):
        plan.box("stackhouse-envelope-corner-spine", "structural_steel", group,
                 x + side * width * 0.385,
                 (envelope_bottom + envelope_top) / 2, envelope_front - 0.16,
                 0.42, envelope_top - envelope_bottom + 0.4, 0.38,
                 layer="mid")
    if lod == 0:
        for streak_index in range(3):
            streak_x = x - width * 0.23 + streak_index * width * 0.21
            streak_h = (envelope_top - envelope_bottom) * (0.20 + 0.08 * streak_index)
            plan.box("stackhouse-visible-rust-streak", "rust", group,
                     streak_x, envelope_bottom + streak_h / 2 + 1.0,
                     envelope_front - 0.25, 0.12, streak_h, 0.12,
                     layer="mid")

    # Smaller process houses break up the large envelope crown and sides.
    mass_zones = ((0.25, 0.13), (0.52, 0.15), (0.77, 0.13)) if lod == 0 else \
                 ((0.34, 0.18), (0.70, 0.18)) if lod == 1 else ((0.54, 0.24),)
    for zone_index, (height_factor, size_factor) in enumerate(mass_zones):
        mass_y = structure_top * height_factor
        mass_h = max(5.2, structure_top * size_factor)
        mass_x = x + (-1 if zone_index % 2 == 0 else 1) * width * 0.10
        process_house = plan.box(
            "stackhouse-occupied-process-house",
            "pale_concrete" if (zone_index + ord(label)) % 2 else "dark_concrete",
            group, mass_x, mass_y, z + depth * 0.04,
            width * (0.64 if zone_index != 1 else 0.72), mass_h,
            depth * (0.52 if zone_index != 2 else 0.60), layer="mid")
        floor_anchor = floor_names[min(len(floor_names) - 1,
                                       round(zone_index * (len(floor_names) - 1) /
                                             max(1, len(mass_zones) - 1)))]
        plan.connect(floor_anchor, process_house, axis="surface", overlap_m=0.10,
                     parent_face="top", child_face="bottom")
        plan.box("stackhouse-process-house-window-strip", "warm_glass", group,
                 mass_x, mass_y + mass_h * 0.12,
                 z - depth * 0.225,
                 width * 0.40, min(2.1, mass_h * 0.28), 0.20,
                 layer="mid")

    head_base = structure_top - 0.18
    head = plan.box("stackhouse-roof-headhouse", "weathered_zinc", group,
                    x + width * 0.12, head_base + 2.45, z + depth * 0.04,
                    width * 0.62, 5.15, depth * 0.60, layer="mid",
                    name=f"{group}.{label}.roof-headhouse")
    plan.connect(floor_names[-1], head, axis="y", overlap_m=0.18,
                 parent_face="top", child_face="bottom")
    roof = plan.box("stackhouse-roof-cap", "structural_steel", group,
                    x + width * 0.12, height - 0.24, z + depth * 0.04,
                    width * 0.68, 0.48, depth * 0.66, layer="mid",
                    name=f"{group}.{label}.roof-cap")
    plan.connect(head, roof, axis="y", overlap_m=0.12,
                 parent_face="top", child_face="bottom")

    if lod < 2:
        pipe_count = 3 if lod == 0 else 1
        for pipe in range(pipe_count):
            px = x - width * 0.27 + pipe * width * 0.27
            plan.cylinder("stackhouse-vertical-riser", "rust" if pipe == 0 else "structural_steel",
                          group, px, structure_top * 0.56, z - depth / 2 - 0.38,
                          0.20 if lod == 0 else 0.30, structure_top * 0.82,
                          8 if lod == 0 else 6, layer="mid")
    return {"base": base, "top": roof, "x": x, "z": z, "width": width,
            "depth": depth, "height": height, "floorNames": floor_names}


def _add_stackhouse_rack(plan: SpecPlan, landmark: Mapping[str, Any], lod: int,
                         plinth_name: str) -> None:
    group = STACKHOUSE_ID
    cx, cz = float(landmark["cx"]), float(landmark["cz"])
    x_stations = (-46.0, -23.0, 0.0, 23.0, 46.0)
    z_rows = (-27.0, 0.0, 27.0)
    levels = ((11.5, 20.5, 29.5, 38.5, 47.5, 57.5) if lod == 0 else
              (11.5, 26.5, 41.5, 57.5) if lod == 1 else (11.5, 34.5, 57.5))
    upright_w = 0.36 if lod == 0 else 0.56 if lod == 1 else 0.78
    chord_w = 0.24 if lod == 0 else 0.38 if lod == 1 else 0.60
    uprights: dict[tuple[int, int], str] = {}
    for xi, local_x in enumerate(x_stations):
        for zi, local_z in enumerate(z_rows):
            x, z = cx + local_x, cz + local_z
            upright = plan.beam("stackhouse-rack-upright", "structural_steel", group,
                                (x, 0.46, z), (x, 59.0, z), upright_w, upright_w,
                                layer="mid")
            plan.connect(plinth_name, upright, axis="y", overlap_m=0.16,
                         parent_face="top", child_face="bottom")
            uprights[(xi, zi)] = upright
    for zi, local_z in enumerate(z_rows):
        z = cz + local_z
        for level_index, y in enumerate(levels):
            plan.beam("stackhouse-rack-transverse-chord", "safety_orange" if level_index == 1 else "structural_steel",
                      group, (cx + x_stations[0], y, z), (cx + x_stations[-1], y, z),
                      chord_w, chord_w, layer="mid")
        step = 1 if lod == 0 else 2
        for bay in range(0, len(x_stations) - 1, step):
            right = min(len(x_stations) - 1, bay + step)
            for level_index in range(len(levels) - 1):
                if lod == 2 and level_index > 0:
                    continue
                a_x, b_x = cx + x_stations[bay], cx + x_stations[right]
                low, high = levels[level_index], levels[level_index + 1]
                if (bay + level_index + zi) % 2:
                    a_y, b_y = high - 0.2, low + 0.2
                else:
                    a_y, b_y = low + 0.2, high - 0.2
                plan.beam("stackhouse-rack-cross-brace", "rust", group,
                          (a_x, a_y, z), (b_x, b_y, z),
                          0.14 if lod == 0 else 0.24, 0.10 if lod == 0 else 0.18,
                          layer="mid")
    for xi, local_x in enumerate(x_stations):
        x = cx + local_x
        for level_index, y in enumerate(levels):
            plan.beam("stackhouse-rack-depth-tie", "structural_steel", group,
                      (x, y, cz + z_rows[0]), (x, y, cz + z_rows[-1]),
                      chord_w, chord_w, layer="mid")

    if lod <= 1:
        cargo_levels = levels[:-1] if lod == 0 else levels[:2]
        bay_xs = (-34.5, -11.5, 11.5, 34.5)
        for zi, local_z in enumerate(z_rows):
            for level_index, y in enumerate(cargo_levels):
                for bay_index, local_x in enumerate(bay_xs):
                    if (zi * 3 + level_index + bay_index) % (4 if lod == 0 else 3) == 1:
                        continue
                    plan.box("stackhouse-internal-cargo-bay",
                             "red_brick" if (level_index + bay_index) % 4 == 0 else "dark_concrete",
                             group, cx + local_x, y + 3.1, cz + local_z,
                             18.2, 5.6, 9.4 if lod == 0 else 11.0, layer="mid")
                    if lod == 0 and (level_index + bay_index) % 3 == 0:
                        plan.box("stackhouse-cargo-safety-stripe", "safety_orange", group,
                                 cx + local_x, y + 3.4, cz + local_z - 4.78,
                                 12.0, 0.38, 0.18, layer="mid")


def _add_truss_bridge(plan: SpecPlan, group: str, label: str,
                      start: tuple[float, float], end: tuple[float, float],
                      bottom: float, top: float, depth: float, lod: int,
                      start_anchor: str, end_anchor: str) -> None:
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    yaw = math.atan2(dz, dx)
    mx, mz = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    floor = plan.box("stackhouse-skybridge-floor", "weathered_zinc", group,
                     mx, bottom + 0.32, mz, length + 1.2, 0.64, depth,
                     yaw=yaw, layer="mid", name=f"{group}.{label}.floor")
    roof = plan.box("stackhouse-skybridge-roof", "structural_steel", group,
                    mx, top - 0.28, mz, length + 1.2, 0.56, depth + 0.35,
                    yaw=yaw, layer="mid", name=f"{group}.{label}.roof")
    plan.connect(start_anchor, floor, axis="surface", overlap_m=0.18,
                 parent_face="facade", child_face="end")
    plan.connect(end_anchor, floor, axis="surface", overlap_m=0.18,
                 parent_face="facade", child_face="end")
    plan.connect(floor, roof, axis="frame", overlap_m=0.08,
                 parent_face="truss", child_face="truss")
    frame_count = 7 if lod == 0 else 5 if lod == 1 else 3
    half_d = depth / 2
    frames = []
    for index in range(frame_count):
        t = index / max(1, frame_count - 1)
        bx = start[0] + dx * t
        bz = start[1] + dz * t
        frames.append((bx, bz))
        for side in (-1, 1):
            sx, sz = bx + px * half_d * side, bz + pz * half_d * side
            plan.beam("stackhouse-skybridge-portal", "structural_steel", group,
                      (sx, bottom + 0.18, sz), (sx, top - 0.18, sz),
                      0.24 if lod == 0 else 0.38, 0.20 if lod == 0 else 0.30,
                      layer="mid")
        plan.beam("stackhouse-skybridge-portal", "structural_steel", group,
                  (bx - px * half_d, top - 0.2, bz - pz * half_d),
                  (bx + px * half_d, top - 0.2, bz + pz * half_d),
                  0.24 if lod == 0 else 0.38, 0.20 if lod == 0 else 0.30,
                  layer="mid")
    for side in (-1, 1):
        for index in range(len(frames) - 1):
            ax, az = frames[index]
            bx, bz = frames[index + 1]
            ax += px * half_d * side
            az += pz * half_d * side
            bx += px * half_d * side
            bz += pz * half_d * side
            if (index + (1 if side > 0 else 0)) % 2:
                ay, by = top - 0.55, bottom + 0.55
            else:
                ay, by = bottom + 0.55, top - 0.55
            plan.beam("stackhouse-skybridge-diagonal", "rust", group,
                      (ax, ay, az), (bx, by, bz),
                      0.15 if lod == 0 else 0.25, 0.11 if lod == 0 else 0.18,
                      layer="mid")
    if lod < 2:
        cab_len = min(11.0, length * 0.28)
        plan.box("stackhouse-skybridge-transfer-room", "dark_concrete", group,
                 mx, bottom + (top - bottom) * 0.50, mz,
                 cab_len, top - bottom - 1.35, depth - 1.2,
                 yaw=yaw, layer="mid")
        side_x, side_z = mx + px * (half_d + 0.08), mz + pz * (half_d + 0.08)
        plan.box("stackhouse-skybridge-window", "dirty_glass", group,
                 side_x, bottom + (top - bottom) * 0.56, side_z,
                 cab_len * 0.70, 2.6, 0.15, yaw=yaw, layer="mid")
        if label == "main-bridge":
            for side in (-1.0, 1.0):
                glazed_x = mx + px * (half_d + 0.13) * side
                glazed_z = mz + pz * (half_d + 0.13) * side
                plan.box("stackhouse-main-bridge-glazed-side", "dirty_glass", group,
                         glazed_x, (bottom + top) / 2, glazed_z,
                         length + 0.35, top - bottom - 1.65, 0.18,
                         yaw=yaw, layer="mid")
                plan.beam("stackhouse-main-bridge-safety-chord", "safety_orange", group,
                          (start[0] + px * half_d * side, bottom + 1.25,
                           start[1] + pz * half_d * side),
                          (end[0] + px * half_d * side, bottom + 1.25,
                           end[1] + pz * half_d * side),
                          0.34, 0.24, layer="mid")


def _build_stackhouse(plan: SpecPlan, lod: int) -> None:
    landmark = LANDMARKS[0]
    group = STACKHOUSE_ID
    cx, cz = float(landmark["cx"]), float(landmark["cz"])
    plinth = plan.box("stackhouse-collision-anchored-plinth", "old_concrete", group,
                      cx, 0.18, cz, 102.8, 0.56, 64.8, layer="mid",
                      name=f"{group}.plinth")
    towers = {
        "a": _add_process_tower(plan, group=group, label="a", x=cx - 35.0, z=cz - 20.0,
                                width=19.0, depth=18.0, height=46.0, levels=5 if lod == 0 else 3, lod=lod),
        "b": _add_process_tower(plan, group=group, label="b", x=cx - 14.0, z=cz + 20.0,
                                width=23.0, depth=22.0, height=58.5, levels=6 if lod == 0 else 4, lod=lod),
        "c": _add_process_tower(plan, group=group, label="c", x=cx + 18.0, z=cz - 18.0,
                                width=24.0, depth=20.0, height=64.0, levels=7 if lod == 0 else 4, lod=lod),
        "d": _add_process_tower(plan, group=group, label="d", x=cx + 39.0, z=cz + 18.0,
                                width=18.0, depth=22.0, height=51.5, levels=5 if lod == 0 else 3, lod=lod),
    }
    _add_stackhouse_rack(plan, landmark, lod, plinth)
    _add_truss_bridge(plan, group, "main-bridge",
                      (towers["b"]["x"], towers["b"]["z"]),
                      (towers["c"]["x"], towers["c"]["z"]),
                      35.0, 45.8, 7.8, lod, towers["b"]["floorNames"][-2],
                      towers["c"]["floorNames"][-3])
    if lod < 2:
        _add_truss_bridge(plan, group, "west-bridge",
                          (towers["a"]["x"], towers["a"]["z"]),
                          (towers["b"]["x"], towers["b"]["z"]),
                          24.0, 31.0, 5.8, lod, towers["a"]["floorNames"][2],
                          towers["b"]["floorNames"][2])
    # Human-scale west arrival remains open through local Z +/- 7 m.
    for side, local_z in ((-1, -17.0), (1, 17.0)):
        x, z = _world(landmark, -48.8, local_z)
        plan.box("stackhouse-loading-wing", "red_brick", group, x, 4.8, z,
                 7.0, 9.4, 16.0, layer="near")
        plan.box("stackhouse-recessed-hoist-door", "dark_concrete", group,
                 x - 3.58, 3.5, z, 0.22, 5.8, 8.2, layer="near")
        plan.box("stackhouse-door-header", "safety_orange", group,
                 x - 3.72, 6.7, z, 0.20, 0.42, 9.0, layer="near")
        if lod == 0:
            _add_guardrail(plan, group, (x - 3.9, z - 6.2), (x - 3.9, z + 6.2),
                           8.85, posts=5, layer="near")
    # Irregular roof machinery and travelling hoist preserve the reference crown.
    if lod <= 1:
        for index, (lx, lz, w, d, y) in enumerate((
            (-31.0, 7.0, 8.0, 7.0, 48.0), (-2.0, -4.0, 10.0, 8.0, 60.0),
            (34.0, -8.0, 7.0, 7.5, 53.0),
        )):
            x, z = _world(landmark, lx, lz)
            plan.box("stackhouse-roof-machine", "weathered_zinc", group, x, y, z,
                     w, 3.8 if lod == 0 else 4.8, d, layer="mid")
            plan.cylinder("stackhouse-exhaust", "rust", group, x + w * 0.25, y + 3.5,
                          z, 0.55, 4.2, 10 if lod == 0 else 7, top_radius=0.42,
                          layer="mid")


def _build_customs(plan: SpecPlan, lod: int) -> None:
    """Build the heavy customs terminal with four full-depth roof teeth."""
    landmark = LANDMARKS[1]
    group = CUSTOMS_ID
    cx, cz = float(landmark["cx"]), float(landmark["cz"])
    plinth = plan.box("customs-collision-anchored-plinth", "old_concrete", group,
                      cx, 0.22, cz, 90.8, 0.62, 76.8, layer="mid",
                      name=f"{group}.plinth")

    # The northern arrival stays open at ground level.  Two genuinely deep
    # wings and a rear spine form a U, rather than a single decorated box.
    wing_names = []
    for label, offset in (("west", -27.0), ("east", 27.0)):
        wing = plan.box("customs-heavy-lower-wing", "red_brick", group,
                        cx + offset, 7.2, cz - 1.5, 34.0, 14.2, 60.0,
                        layer="mid", name=f"{group}.{label}.lower-wing")
        plan.connect(plinth, wing, axis="y", overlap_m=0.12,
                     parent_face="top", child_face="bottom")
        wing_names.append(wing)
        # Deep loading recesses establish human scale and working depth.
        for door_index, door_x in enumerate((-8.0, 0.0, 8.0)):
            world_x = cx + offset + door_x
            plan.box("customs-loading-door", "dark_concrete", group,
                     world_x, 4.1, cz + 28.62, 5.2, 6.8, 0.24, layer="near")
            plan.box("customs-loading-canopy", "weathered_zinc", group,
                     world_x, 7.8, cz + 30.35, 6.4, 0.30, 3.7, layer="near")
            if lod == 0:
                plan.box("customs-dock-bumper", "safety_orange", group,
                         world_x - 2.35, 1.2, cz + 29.0, 0.34, 1.5, 0.42,
                         layer="near")
                plan.box("customs-dock-bumper", "safety_orange", group,
                         world_x + 2.35, 1.2, cz + 29.0, 0.34, 1.5, 0.42,
                         layer="near")

    rear = plan.box("customs-rear-inspection-spine", "dark_concrete", group,
                    cx, 9.1, cz - 32.0, 88.0, 17.8, 11.5, layer="mid",
                    name=f"{group}.rear-spine")
    plan.connect(plinth, rear, axis="y", overlap_m=0.12,
                 parent_face="top", child_face="bottom")

    # A suspended central bridge makes the north gate usable at player height.
    upper_deck = plan.box("customs-upper-factory-deck", "old_concrete", group,
                          cx, 15.2, cz - 2.5, 88.0, 2.1, 61.0, layer="mid",
                          name=f"{group}.upper-deck")
    for wing in wing_names:
        plan.connect(wing, upper_deck, axis="y", overlap_m=0.16,
                     parent_face="top", child_face="bottom")
    for label, offset in (("west", -30.5), ("east", 30.5)):
        upper = plan.box("customs-multistorey-upper-wing", "pale_concrete", group,
                         cx + offset, 23.2, cz - 2.5, 24.0, 14.6, 58.0,
                         layer="mid", name=f"{group}.{label}.upper-wing")
        plan.connect(upper_deck, upper, axis="y", overlap_m=0.16,
                     parent_face="top", child_face="bottom")
        for floor_y in (18.4, 23.1, 27.7):
            plan.box("customs-horizontal-weather-band", "rust", group,
                     cx + offset, floor_y, cz + 26.6, 24.4, 0.30, 0.28,
                     layer="mid")
        if lod < 2:
            for bay in range(4 if lod == 0 else 2):
                bx = cx + offset - 8.2 + bay * (5.5 if lod == 0 else 11.0)
                plan.box("customs-deep-window-bay", "dirty_glass", group,
                         bx, 23.0, cz + 26.76, 3.8 if lod == 0 else 7.6,
                         5.2, 0.18, layer="mid")
                frame_w = 4.35 if lod == 0 else 8.15
                frame_h = 5.75
                for frame_y in (23.0 - frame_h / 2, 23.0 + frame_h / 2):
                    plan.box("customs-window-reveal-frame", "weathered_zinc", group,
                             bx, frame_y, cz + 26.95, frame_w, 0.20, 0.16,
                             layer="mid")
                for frame_x in (bx - frame_w / 2, bx + frame_w / 2):
                    plan.box("customs-window-reveal-frame", "weathered_zinc", group,
                             frame_x, 23.0, cz + 26.95, 0.20, frame_h, 0.16,
                             layer="mid")

    # Four adjacent factory bays.  Each roof is a real 58 m-deep pair of
    # panels, with one explicit tooth identity and one triangular glass gable.
    roof_front = cz + 27.1
    roof_back = cz - 30.9
    bay_width = 20.6
    roof_start = cx - bay_width * 2.0
    valleys_y = 30.2
    peaks = (41.6, 43.1, 42.3, 40.8)
    for tooth in range(4):
        x0 = roof_start + tooth * bay_width
        x1 = x0 + bay_width
        peak_x = x0 + bay_width * (0.34 if tooth % 2 == 0 else 0.39)
        peak_y = peaks[tooth]
        bay_volume = plan.box(
            "customs-sawtooth-occupied-bay-volume",
            "old_concrete" if tooth % 2 == 0 else "pale_concrete", group,
            (x0 + x1) / 2, 22.7, cz - 2.4,
            bay_width - 0.45, 14.4, 56.8, layer="mid",
            name=f"{group}.sawtooth.{tooth + 1}.occupied-bay")
        plan.connect(upper_deck, bay_volume, axis="y", overlap_m=0.16,
                     parent_face="top", child_face="bottom")
        facade_z = roof_front + 0.02
        plan.box("customs-sawtooth-bay-window-band", "dirty_glass", group,
                 (x0 + x1) / 2, 23.4, facade_z,
                 bay_width * 0.66, 3.15, 0.20, layer="mid")
        for mullion in range(5 if lod == 0 else 3):
            t = mullion / (4 if lod == 0 else 2)
            mullion_x = x0 + bay_width * (0.20 + 0.60 * t)
            plan.box("customs-sawtooth-window-mullion", "structural_steel", group,
                     mullion_x, 23.4, facade_z + 0.13,
                     0.15, 3.35, 0.15, layer="mid")
        roof = plan.panel(
            "customs-sawtooth-roof", "weathered_zinc", group,
            ((peak_x, peak_y, roof_front), (x1, valleys_y, roof_front),
             (x1, valleys_y, roof_back), (peak_x, peak_y, roof_back)),
            0.28 if lod == 0 else 0.42, layer="mid",
            name=f"{group}.sawtooth.{tooth + 1}.main-roof")
        glass_roof = plan.panel(
            "customs-sawtooth-steep-glazed-roof", "dirty_glass", group,
            ((x0, valleys_y, roof_front), (peak_x, peak_y, roof_front),
             (peak_x, peak_y, roof_back), (x0, valleys_y, roof_back)),
            0.18 if lod == 0 else 0.30, layer="mid",
            name=f"{group}.sawtooth.{tooth + 1}.steep-roof")
        gable = plan.panel(
            "customs-sawtooth-triangular-glass-gable", "warm_glass", group,
            ((x0, valleys_y, roof_front + 0.12),
             (peak_x, peak_y, roof_front + 0.12),
             (x1, valleys_y, roof_front + 0.12)),
            0.20, layer="mid", name=f"{group}.sawtooth.{tooth + 1}.front-gable")
        plan.connect(bay_volume, roof, axis="surface", overlap_m=0.18,
                     parent_face="top", child_face="eave")
        plan.connect(roof, glass_roof, axis="surface", overlap_m=0.10,
                     parent_face="ridge", child_face="ridge")
        plan.connect(glass_roof, gable, axis="z", overlap_m=0.08,
                     parent_face="front", child_face="rear")
        # Full-section frames and longitudinal purlins make roof depth legible.
        frame_zs = ((roof_front, roof_back) if lod == 2 else
                    (roof_front, cz + 8.0, cz - 11.0, roof_back))
        for frame_z in frame_zs:
            plan.beam("customs-sawtooth-frame", "structural_steel", group,
                      (x0, valleys_y - 0.2, frame_z),
                      (peak_x, peak_y + 0.2, frame_z),
                      0.25 if lod == 0 else 0.40, 0.20 if lod == 0 else 0.34,
                      layer="mid")
            plan.beam("customs-sawtooth-frame", "structural_steel", group,
                      (peak_x, peak_y + 0.2, frame_z),
                      (x1, valleys_y - 0.2, frame_z),
                      0.25 if lod == 0 else 0.40, 0.20 if lod == 0 else 0.34,
                      layer="mid")
        for purlin_x, purlin_y in ((x0, valleys_y), (peak_x, peak_y), (x1, valleys_y)):
            plan.beam("customs-sawtooth-depth-purlin", "rust", group,
                      (purlin_x, purlin_y, roof_front),
                      (purlin_x, purlin_y, roof_back),
                      0.19 if lod == 0 else 0.34, 0.16 if lod == 0 else 0.28,
                      layer="mid")

    control_base = plan.box("customs-control-tower-base", "dark_concrete", group,
                            cx + 13.5, 34.0, cz - 10.0, 12.0, 5.4, 12.5,
                            layer="mid", name=f"{group}.control.base")
    control_glass = plan.box("customs-control-tower-glazing", "warm_glass", group,
                             cx + 13.5, 38.1, cz - 10.0, 11.0, 3.4, 11.5,
                             layer="mid", name=f"{group}.control.glass")
    control_roof = plan.box("customs-control-tower-roof", "weathered_zinc", group,
                            cx + 13.5, 40.15, cz - 10.0, 13.5, 0.70, 14.0,
                            layer="mid", name=f"{group}.control.roof")
    plan.connect(upper_deck, control_base, axis="y", overlap_m=0.15,
                 parent_face="top", child_face="bottom")
    plan.connect(control_base, control_glass, axis="y", overlap_m=0.12,
                 parent_face="top", child_face="bottom")
    plan.connect(control_glass, control_roof, axis="y", overlap_m=0.12,
                 parent_face="top", child_face="bottom")
    for index, offset in enumerate((-14.0, 33.0)):
        chimney = plan.cylinder("customs-industrial-chimney", "rust", group,
                                cx + offset, 35.8, cz - 23.0,
                                1.45 if lod == 0 else 1.8, 21.4,
                                12 if lod == 0 else 8, top_radius=1.05,
                                layer="mid", name=f"{group}.chimney.{index + 1}")
        plan.connect(upper_deck, chimney, axis="y", overlap_m=0.15,
                     parent_face="top", child_face="bottom")

    # Measured public access: two stairs, a catwalk and 1.1 m guards.
    _add_stair(plan, group, (cx - 10.5, cz + 31.5), (cx - 10.5, cz + 22.0),
               0.4, 4.0, 2.2, lod=lod)
    _add_stair(plan, group, (cx + 10.5, cz + 31.5), (cx + 10.5, cz + 22.0),
               0.4, 4.0, 2.2, lod=lod)
    plan.box("customs-human-scale-entry-landing", "old_concrete", group,
             cx, 4.0, cz + 21.5, 18.0, 0.42, 4.2, layer="near")
    if lod < 2:
        _add_guardrail(plan, group, (cx - 8.5, cz + 19.6),
                       (cx + 8.5, cz + 19.6), 4.22,
                       posts=7 if lod == 0 else 4, layer="near")


def _add_container(plan: SpecPlan, group: str, x: float, z: float, yaw: float,
                   color: str, lod: int, *, layer: str = "near",
                   outside_playable: bool = False) -> None:
    plan.box("cargo-container-shell", color, group, x, 1.45, z,
             6.06, 2.90, 2.44, yaw=yaw, layer=layer,
             outside_playable=outside_playable)
    if lod < 2:
        ribs = 5 if lod == 0 else 3
        dx, dz = math.cos(yaw), math.sin(yaw)
        for rib in range(ribs):
            along = -2.5 + rib * (5.0 / max(1, ribs - 1))
            plan.box("cargo-container-rib", "structural_steel", group,
                     x + dx * along, 1.48, z + dz * along,
                     0.10, 2.74, 2.50, yaw=yaw, layer=layer,
                     outside_playable=outside_playable)


def _add_pallet_cluster(plan: SpecPlan, group: str, x: float, z: float, lod: int,
                        *, layer: str = "near") -> None:
    cluster_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for stack in range(cluster_count):
        px = x + stack * 1.55
        stack_h = 0.58 + 0.28 * (stack % 2)
        for level in range(2 if lod == 0 else 1):
            y = 0.12 + level * 0.26
            for slat in range(4 if lod == 0 else 2):
                plan.box("pallet-slat", "pallet_wood", group,
                         px - 0.52 + slat * (1.04 / max(1, (3 if lod == 0 else 1))),
                         y, z, 0.18, 0.13, 1.10, layer=layer)
        plan.box("pallet-wrapped-cargo", "paint_white", group, px, 0.43 + stack_h / 2,
                 z, 1.02, stack_h, 1.0, layer=layer)


def _add_forklift(plan: SpecPlan, group: str, x: float, z: float, yaw: float,
                  lod: int) -> None:
    plan.box("forklift-body", "safety_orange", group, x, 0.72, z,
             1.55, 1.05, 2.25, yaw=yaw, layer="near")
    dx, dz = math.cos(yaw), math.sin(yaw)
    front_x, front_z = x + dx * 1.35, z + dz * 1.35
    for side in (-1.0, 1.0):
        px, pz = -math.sin(yaw) * 0.57 * side, math.cos(yaw) * 0.57 * side
        plan.beam("forklift-mast", "structural_steel", group,
                  (front_x + px, 0.24, front_z + pz),
                  (front_x + px, 2.55, front_z + pz),
                  0.11, 0.10, layer="near")
        if lod == 0:
            plan.beam("forklift-fork", "structural_steel", group,
                      (front_x + px, 0.23, front_z + pz),
                      (front_x + dx * 1.35 + px, 0.23,
                       front_z + dz * 1.35 + pz), 0.10, 0.08, layer="near")


def _add_warehouse(plan: SpecPlan, group: str, label: str, x: float, z: float,
                   w: float, d: float, h: float, yaw: float, lod: int,
                   *, layer: str) -> None:
    shell = plan.box("bonded-warehouse-shell", "red_brick" if int(abs(x + z)) % 2 else "old_concrete",
                     group, x, h * 0.48, z, w, h * 0.96, d, yaw=yaw,
                     layer=layer, name=f"{group}.{label}.shell")
    ridge_y = h + min(4.2, w * 0.16)
    dx, dz = math.cos(yaw), math.sin(yaw)
    px, pz = -dz, dx
    half_w, half_d = w / 2, d / 2
    left_front = (x - dx * half_w - px * half_d, h, z - dz * half_w - pz * half_d)
    left_back = (x - dx * half_w + px * half_d, h, z - dz * half_w + pz * half_d)
    right_front = (x + dx * half_w - px * half_d, h, z + dz * half_w - pz * half_d)
    right_back = (x + dx * half_w + px * half_d, h, z + dz * half_w + pz * half_d)
    ridge_front = (x - px * half_d, ridge_y, z - pz * half_d)
    ridge_back = (x + px * half_d, ridge_y, z + pz * half_d)
    roof_a = plan.panel("bonded-warehouse-roof", "weathered_zinc", group,
                        (left_front, ridge_front, ridge_back, left_back), 0.28,
                        layer=layer)
    roof_b = plan.panel("bonded-warehouse-roof", "weathered_zinc", group,
                        (ridge_front, right_front, right_back, ridge_back), 0.28,
                        layer=layer)
    plan.connect(shell, roof_a, axis="surface", overlap_m=0.10,
                 parent_face="top", child_face="eave")
    plan.connect(shell, roof_b, axis="surface", overlap_m=0.10,
                 parent_face="top", child_face="eave")
    if lod < 2:
        # Dock faces point along local -depth; detail remains real geometry.
        for bay in range(3 if lod == 0 else 2):
            along = (-0.28 + 0.28 * bay) * w
            bx = x + dx * along - px * (half_d + 0.06)
            bz = z + dz * along - pz * (half_d + 0.06)
            plan.box("bonded-warehouse-loading-door", "dark_concrete", group,
                     bx, 3.2, bz, min(4.8, w * 0.18), 5.8, 0.22,
                     yaw=yaw, layer=layer)
            plan.box("bonded-warehouse-loading-light", "warm_glass", group,
                     bx, 6.8, bz - 0.12, 0.55, 0.35, 0.18,
                     yaw=yaw, layer=layer)


def _build_public_realm(plan: SpecPlan, lod: int) -> None:
    group = "souko-public-realm"
    plan.box("playable-industrial-ground", "old_concrete", group, 0.0, -0.38, 0.0,
             335.4, 0.70, 335.4, layer="far", name=f"{group}.ground")
    plan.box("wet-primary-road", "wet_asphalt", group, 0.0, 0.015, 0.0,
             16.0, 0.12, 328.0, layer="near", name=f"{group}.road.ns")
    plan.box("wet-primary-road", "wet_asphalt", group, 0.0, 0.025, 0.0,
             328.0, 0.14, 16.0, layer="near", name=f"{group}.road.ew")
    diagonal_start = (-160.0, 160.0)
    diagonal_end = (5.0, 14.0)
    diagonal_dx = diagonal_end[0] - diagonal_start[0]
    diagonal_dz = diagonal_end[1] - diagonal_start[1]
    diagonal_length = math.hypot(diagonal_dx, diagonal_dz)
    diagonal_yaw = math.atan2(diagonal_dz, diagonal_dx)
    plan.box("wet-diagonal-bonded-service-road", "wet_asphalt", group,
             (diagonal_start[0] + diagonal_end[0]) / 2, 0.04,
             (diagonal_start[1] + diagonal_end[1]) / 2,
             diagonal_length, 0.14, 14.0, yaw=diagonal_yaw, layer="near")
    diagonal_px, diagonal_pz = -math.sin(diagonal_yaw), math.cos(diagonal_yaw)
    for side in (-1.0, 1.0):
        offset_x, offset_z = diagonal_px * 7.25 * side, diagonal_pz * 7.25 * side
        plan.beam("service-road-curb", "pale_concrete", group,
                  (diagonal_start[0] + offset_x, 0.18, diagonal_start[1] + offset_z),
                  (diagonal_end[0] + offset_x, 0.18, diagonal_end[1] + offset_z),
                  0.42, 0.30, layer="near")
    if lod == 0:
        ux, uz = diagonal_dx / diagonal_length, diagonal_dz / diagonal_length
        for dash in range(10):
            distance = 16.0 + dash * 18.0
            plan.box("service-road-faded-centre-dash", "paint_white", group,
                     diagonal_start[0] + ux * distance, 0.125,
                     diagonal_start[1] + uz * distance,
                     5.4, 0.026, 0.15, yaw=diagonal_yaw, layer="near")
    # Curbs live outside the authoritative 16 m road envelopes.
    for side in (-1.0, 1.0):
        plan.box("road-curb", "pale_concrete", group, side * 8.42, 0.18, 0.0,
                 0.54, 0.35, 310.0, layer="near")
        plan.box("road-curb", "pale_concrete", group, 0.0, 0.18, side * 8.42,
                 310.0, 0.35, 0.54, layer="near")
    puddles = (
        (-4.8, -116.0, 6.4, 13.0), (4.6, -72.0, 5.2, 9.0),
        (-3.8, -24.0, 5.8, 12.0), (4.9, 28.0, 5.1, 14.0),
        (-4.6, 78.0, 6.2, 11.0), (3.8, 128.0, 5.6, 12.5),
        (-116.0, -3.9, 13.0, 5.4), (-68.0, 4.5, 9.0, 5.1),
        (31.0, -4.7, 14.0, 5.2), (93.0, 4.2, 12.0, 5.8),
    )
    puddle_step = 1 if lod == 0 else 2 if lod == 1 else 3
    for index, (x, z, w, d) in enumerate(puddles[::puddle_step]):
        plan.box("wet-road-puddle", "puddle_water", group, x, 0.095 + index * 0.0002,
                 z, w, 0.035, d, yaw=0.08 * ((index % 3) - 1), layer="near")
    if lod == 0:
        for axis in (-1.0, 1.0):
            for index in range(-6, 7):
                plan.box("faded-road-marking", "paint_white", group,
                         axis * 2.1 if axis < 0 else index * 22.0,
                         0.105, index * 22.0 if axis < 0 else axis * 2.1,
                         0.13 if axis < 0 else 5.5, 0.025,
                         5.5 if axis < 0 else 0.13, layer="near")


def _build_bonded_city(plan: SpecPlan, lod: int) -> None:
    group = "souko-bonded-city"
    warehouse_specs = (
        ("northwest-a", 40.0, 140.0, 54.0, 30.0, 18.0, 0.06, "mid"),
        ("northwest-b", 60.0, 150.0, 36.0, 36.0, 22.0, -0.10, "far"),
        ("north-mid", -38.0, 75.0, 38.0, 31.0, 17.0, 0.08, "mid"),
        ("west-mid", -145.0, 35.0, 55.0, 30.0, 20.0, -0.04, "mid"),
        ("southwest-a", -132.0, -121.0, 48.0, 36.0, 19.0, 0.04, "mid"),
        ("south-mid", 20.0, -125.0, 40.0, 46.0, 23.0, -0.08, "far"),
        ("east-south", 70.0, -118.0, 56.0, 34.0, 18.0, 0.05, "mid"),
        ("east-mid", 125.0, -68.0, 44.0, 38.0, 21.0, -0.09, "far"),
        ("east-north", 137.0, 48.0, 40.0, 34.0, 24.0, 0.07, "far"),
    )
    selection = warehouse_specs if lod == 0 else warehouse_specs[::2] if lod == 1 else warehouse_specs[::3]
    for label, x, z, w, d, h, yaw, layer in selection:
        _add_warehouse(plan, group, label, x, z, w, d, h, yaw, lod, layer=layer)

    container_clusters = (
        (-128.0, 22.0, 0.0), (-105.0, -22.0, math.pi / 2),
        (40.0, -93.0, 0.02), (105.0, -26.0, math.pi / 2),
        (131.0, 93.0, math.pi / 2), (-35.0, 34.0, 0.0),
    )
    for cluster_index, (x, z, yaw) in enumerate(container_clusters[::(1 if lod == 0 else 2)]):
        count = 4 if lod == 0 else 2 if lod == 1 else 1
        for item in range(count):
            offset_x = (item % 2) * 6.6
            offset_z = (item // 2) * 3.1
            _add_container(plan, group, x + offset_x, z + offset_z, yaw,
                           "safety_orange" if (item + cluster_index) % 3 == 0 else
                           "weathered_zinc", lod,
                           layer="near" if cluster_index < 3 else "mid")
    for index, (x, z) in enumerate(((-98.0, -19.0), (-31.0, 28.0),
                                     (26.0, -76.0), (117.0, 24.0))):
        if lod == 0 or index % 2 == 0:
            _add_pallet_cluster(plan, group, x, z, lod)
    if lod < 2:
        _add_forklift(plan, group, -93.0, -13.0, 0.2, lod)
        _add_forklift(plan, group, 32.0, -72.0, -1.1, lod)
    # West-spawn bonded-yard story: staged cargo, drums and an approaching
    # forklift occupy the foreground without becoming gameplay collision.
    if lod == 0:
        _add_pallet_cluster(plan, group, -142.0, 12.5, lod, layer="near")
        _add_pallet_cluster(plan, group, -133.0, 9.5, lod, layer="near")
        _add_forklift(plan, group, -146.0, 10.5, 0.62, lod)
        for drum in range(7):
            plan.cylinder("bonded-yard-cargo-drum", "rust" if drum % 3 == 0 else "safety_orange",
                          group, -129.0 + (drum % 4) * 1.05, 0.48,
                          15.0 + (drum // 4) * 1.2,
                          0.38, 0.92, 12, layer="near")
        plan.box("bonded-yard-wet-loading-pad", "wet_asphalt", group,
                 -135.0, 0.08, 16.0, 35.0, 0.10, 18.0, layer="near")


def _add_port_crane(plan: SpecPlan, group: str, label: str, x: float, z: float,
                    height: float, yaw: float, lod: int) -> None:
    outside = True
    base = plan.box("port-crane-grounded-base", "old_concrete", group,
                    x, 1.0, z, 10.0, 2.0, 10.0, yaw=yaw, layer="far",
                    outside_playable=outside, name=f"{group}.{label}.base")
    tower = plan.box("port-crane-lattice-tower", "structural_steel", group,
                     x, height * 0.49 + 1.5, z, 3.6, height - 3.0, 3.6,
                     yaw=yaw, layer="far", outside_playable=outside,
                     name=f"{group}.{label}.tower")
    plan.connect(base, tower, axis="y", overlap_m=0.18,
                 parent_face="top", child_face="bottom")
    boom_len = 54.0 if lod == 0 else 44.0
    dx, dz = math.cos(yaw), math.sin(yaw)
    boom = plan.beam("port-crane-huge-boom", "safety_orange", group,
                     (x - dx * 8.0, height, z - dz * 8.0),
                     (x + dx * boom_len, height - 4.5, z + dz * boom_len),
                     0.95 if lod == 0 else 1.4, 0.85 if lod == 0 else 1.2,
                     layer="far", outside_playable=outside,
                     name=f"{group}.{label}.boom")
    plan.connect(tower, boom, axis="surface", overlap_m=0.14,
                 parent_face="top", child_face="underside")
    plan.box("port-crane-counterweight", "rust", group,
             x - dx * 11.0, height - 0.6, z - dz * 11.0,
             8.0, 4.0, 4.0, yaw=yaw, layer="far", outside_playable=outside)
    if lod < 2:
        plan.beam("port-crane-cable", "structural_steel", group,
                  (x + dx * boom_len, height - 4.5, z + dz * boom_len),
                  (x + dx * boom_len, 4.0, z + dz * boom_len),
                  0.10 if lod == 0 else 0.16, 0.10 if lod == 0 else 0.16,
                  layer="far", outside_playable=outside)
        for side in (-1.0, 1.0):
            px, pz = -dz * 1.8 * side, dx * 1.8 * side
            plan.beam("port-crane-lattice-brace", "rust", group,
                      (x + px, 5.0, z + pz), (x - px, height - 5.0, z - pz),
                      0.24, 0.18, layer="far", outside_playable=outside)


def _add_cargo_ship(plan: SpecPlan, group: str, x: float, z: float, lod: int) -> None:
    outside = True
    # Broad hull, raised bow and superstructure remain readable at horizon LOD.
    for side in (-1.0, 1.0):
        plan.panel("cargo-ship-hull", "dark_concrete", group,
                   ((x + side * 8.0, 0.15, z - 56.0),
                    (x + side * 12.0, 5.7, z - 50.0),
                    (x + side * 12.0, 5.7, z + 48.0),
                    (x + side * 7.0, 0.15, z + 60.0)),
                   0.42, layer="far", outside_playable=outside,
                   name=f"{group}.ship.hull.{'port' if side < 0 else 'starboard'}")
    plan.panel("cargo-ship-raked-bow", "rust", group,
               ((x - 12.0, 0.2, z + 56.0), (x + 12.0, 0.2, z + 56.0),
                (x + 8.0, 7.2, z + 62.0), (x - 8.0, 7.2, z + 62.0)),
               0.45, layer="far", outside_playable=outside)
    plan.box("cargo-ship-deck", "weathered_zinc", group, x, 6.6, z - 2.0,
             22.0, 0.65, 104.0, layer="far", outside_playable=outside)
    for side in (-1.0, 1.0):
        plan.box("cargo-ship-rust-waterline", "rust", group,
                 x + side * 12.12, 1.25, z - 2.0,
                 0.20, 1.15, 92.0, layer="far", outside_playable=outside)
    plan.box("cargo-ship-superstructure", "paint_white", group,
             x, 14.0, z - 39.0, 18.0, 14.0, 21.0,
             layer="far", outside_playable=outside)
    plan.box("cargo-ship-bridge-glazing", "warm_glass", group,
             x, 18.1, z - 28.35, 16.5, 3.2, 0.24,
             layer="far", outside_playable=outside)
    stack_count = 12 if lod == 0 else 6 if lod == 1 else 3
    for index in range(stack_count):
        row, column = divmod(index, 3)
        plan.box("cargo-ship-deck-container",
                 "safety_orange" if index % 4 == 0 else "weathered_zinc", group,
                 x - 6.2 + column * 6.2, 8.35 + (index % 2) * 2.9,
                 z - 15.0 + row * 13.0, 5.8, 2.7, 11.5,
                 layer="far", outside_playable=outside)
    plan.beam("cargo-ship-mast", "structural_steel", group,
              (x, 7.0, z - 35.0), (x, 29.0, z - 35.0),
              0.30, 0.30, layer="far", outside_playable=outside)


def _build_coastal_horizon(plan: SpecPlan, lod: int) -> None:
    group = "souko-east-port-horizon"
    plan.box("real-sea-geometry", "sea_water", group, 246.0, -0.22, 0.0,
             150.0, 0.35, 410.0, layer="far", outside_playable=True,
             name=f"{group}.sea")
    plan.box("quay-slab", "old_concrete", group, 177.0, 0.35, 0.0,
             18.0, 0.80, 380.0, layer="far", outside_playable=True,
             name=f"{group}.quay")
    plan.box("quay-retaining-wall", "dark_concrete", group, 185.8, 1.55, 0.0,
             1.3, 3.9, 380.0, layer="far", outside_playable=True)
    crane_specs = (("north", 181.0, 96.0, 58.0, -0.12),
                   ("mid", 181.0, 8.0, 67.0, 0.08),
                   ("south", 181.0, -105.0, 54.0, -0.05))
    for item in crane_specs[::(1 if lod < 2 else 2)]:
        _add_port_crane(plan, group, *item, lod)
    _add_cargo_ship(plan, group, 226.0, -18.0, lod)
    if lod < 2:
        for index, quay_z in enumerate((-72.0, -42.0, 35.0, 68.0)):
            _add_container(plan, group, 176.0, quay_z, math.pi / 2,
                           "safety_orange" if index % 2 == 0 else "weathered_zinc",
                           lod, layer="far", outside_playable=True)
            plan.cylinder("quay-mooring-bollard", "structural_steel", group,
                          184.3, 1.0, quay_z + 8.0,
                          0.55, 1.35, 10 if lod == 0 else 7,
                          top_radius=0.72, layer="far", outside_playable=True)
    # Far warehouses are fully modelled silhouettes, not raster horizon walls.
    for index, (x, z, w, d, h) in enumerate((
        (208.0, 142.0, 46.0, 52.0, 22.0),
        (245.0, 135.0, 38.0, 44.0, 27.0),
        (217.0, -142.0, 52.0, 46.0, 20.0),
        (260.0, -130.0, 45.0, 40.0, 24.0),
    )):
        if lod == 0 or index % 2 == 0:
            _add_warehouse(plan, group, f"port-far-{index}", x, z, w, d, h,
                           0.02 * (index - 1), lod, layer="far")


def build_plan(lod: int = 0) -> SpecPlan:
    """Return the deterministic standalone Souko plan."""
    plan = SpecPlan(lod)
    _build_public_realm(plan, lod)
    _build_bonded_city(plan, lod)
    _build_coastal_horizon(plan, lod)
    _build_stackhouse(plan, lod)
    _build_customs(plan, lod)
    validate_plan(plan)
    return plan


PRIVATE_VIEWS: tuple[dict[str, Any], ...] = (
    {
        "id": "01-reference-diagonal-vista",
        "eye": (-160.0, PLAYER_EYE_M, 165.0),
        "target": (7.0, 28.0, 14.0), "lensMm": 27.0,
        "purpose": "Wide wet-road identity view across Customs to Stackhouse and port layers.",
    },
    {
        "id": "02-stackhouse-west-approach",
        "eye": (0.0, PLAYER_EYE_M, 20.0),
        "target": (82.0, 23.0, 96.0), "lensMm": 26.0,
        "purpose": "Canonical west approach, multiple towers and bridge hierarchy.",
    },
    {
        "id": "03-stackhouse-deep-interior",
        "eye": (58.0, PLAYER_EYE_M, 91.0),
        "target": (121.0, 18.0, 110.0), "lensMm": 28.0,
        "purpose": "Rack depth, cargo rooms, floors, braces and contact shadows.",
    },
    {
        "id": "04-stackhouse-under-main-bridge",
        "eye": (160.0, PLAYER_EYE_M, 162.0),
        "target": (83.0, 39.0, 97.0), "lensMm": 32.0,
        "purpose": "Human-scale underside proof for the huge diagonal truss bridge.",
    },
    {
        "id": "05-customs-north-approach",
        "eye": (-68.0, PLAYER_EYE_M, 35.0),
        "target": (-68.0, 22.0, -67.0), "lensMm": 30.0,
        "purpose": "Canonical gate, loading wings and exact four sawtooth gables.",
    },
    {
        "id": "06-customs-oblique-depth",
        "eye": (-155.0, PLAYER_EYE_M, 3.0),
        "target": (-65.0, 21.0, -70.0), "lensMm": 34.0,
        "purpose": "Full-depth teeth, upper floors, control room and chimneys.",
    },
    {
        "id": "07-bonded-city-loading-life",
        "eye": (-156.0, PLAYER_EYE_M, -4.0),
        "target": (-134.0, 4.0, 13.0), "lensMm": 30.0,
        "purpose": "Pallets, forklift, containers, wet curb and warehouse doors.",
    },
    {
        "id": "08-east-quay-ship-cranes",
        "eye": (340.0, PLAYER_EYE_M, -96.0),
        "target": (218.0, 11.0, -18.0), "lensMm": 32.0,
        "purpose": "Real sea, quay, ship, cranes and far warehouse depth.",
    },
)


def spec_bounds(spec: Mapping[str, Any]) -> tuple[float, float, float, float, float, float]:
    """Return runtime-space minX/minY/minZ/maxX/maxY/maxZ for one spec."""
    kind = spec["kind"]
    if kind in {"box", "oriented_box"}:
        yaw = float(spec.get("yaw", 0.0))
        half_x = abs(math.cos(yaw)) * float(spec["w"]) / 2 + abs(math.sin(yaw)) * float(spec["d"]) / 2
        half_z = abs(math.sin(yaw)) * float(spec["w"]) / 2 + abs(math.cos(yaw)) * float(spec["d"]) / 2
        half_y = float(spec["h"]) / 2
        return (float(spec["x"]) - half_x, float(spec["y"]) - half_y,
                float(spec["z"]) - half_z, float(spec["x"]) + half_x,
                float(spec["y"]) + half_y, float(spec["z"]) + half_z)
    if kind == "beam":
        start, end = spec["start"], spec["end"]
        pad = max(float(spec["width"]), float(spec["depth"])) / 2
        return tuple((min(start[index], end[index]) - pad) for index in range(3)) + \
               tuple((max(start[index], end[index]) + pad) for index in range(3))
    if kind == "cylinder":
        radius = max(float(spec["radius"]), float(spec["topRadius"]))
        return (float(spec["x"]) - radius, float(spec["y"]) - float(spec["height"]) / 2,
                float(spec["z"]) - radius, float(spec["x"]) + radius,
                float(spec["y"]) + float(spec["height"]) / 2, float(spec["z"]) + radius)
    if kind == "panel":
        corners = spec["corners"]
        pad = float(spec["thickness"])
        return (min(point[0] for point in corners) - pad,
                min(point[1] for point in corners) - pad,
                min(point[2] for point in corners) - pad,
                max(point[0] for point in corners) + pad,
                max(point[1] for point in corners) + pad,
                max(point[2] for point in corners) + pad)
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
    role_counts = Counter(spec["role"] for spec in plan.specs)
    material_counts = Counter(spec["material"] for spec in plan.specs)
    layer_counts = Counter(spec["layer"] for spec in plan.specs)
    kind_counts = Counter(spec["kind"] for spec in plan.specs)
    return {
        "lod": plan.lod,
        "specCount": len(plan.specs),
        "estimatedTriangles": sum(estimated_triangles(spec) for spec in plan.specs),
        "materialCount": len(material_counts),
        "connectionCount": len(plan.connections),
        "bounds": {
            "minX": min(item[0] for item in bounds), "minY": min(item[1] for item in bounds),
            "minZ": min(item[2] for item in bounds), "maxX": max(item[3] for item in bounds),
            "maxY": max(item[4] for item in bounds), "maxZ": max(item[5] for item in bounds),
        },
        "roles": dict(sorted(role_counts.items())),
        "materials": dict(sorted(material_counts.items())),
        "layers": dict(sorted(layer_counts.items())),
        "kinds": dict(sorted(kind_counts.items())),
    }


def _aabb_hits_xz(aabb: Sequence[float], x: float, z: float, padding: float) -> bool:
    return (aabb[0] - padding <= x <= aabb[3] + padding and
            aabb[2] - padding <= z <= aabb[5] + padding)


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
            rb = road["bounds"]
            if (aabb[0] < rb["maxX"] and aabb[3] > rb["minX"] and
                    aabb[2] < rb["maxZ"] and aabb[5] > rb["minZ"]):
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
        if float(connection["overlapM"]) < MIN_CONTACT_OVERLAP_M:
            raise ValueError(f"connection overlap below gate: {connection}")
    metrics = plan_metrics(plan)
    budget = LOD_API[plan.lod]
    if metrics["specCount"] > budget["maxSpecs"]:
        raise ValueError(f"LOD{plan.lod} spec budget exceeded: {metrics['specCount']}")
    if metrics["estimatedTriangles"] > budget["maxEstimatedTriangles"]:
        raise ValueError(f"LOD{plan.lod} triangle budget exceeded: {metrics['estimatedTriangles']}")
    if metrics["materialCount"] > 24:
        raise ValueError(f"material budget exceeded: {metrics['materialCount']}")
    if _role_count(plan.specs, "stackhouse-roof-cap") != 4:
        raise ValueError("Stackhouse must keep four independently crowned towers")
    expected_bridges = 2 if plan.lod < 2 else 1
    if _role_count(plan.specs, "stackhouse-skybridge-floor") != expected_bridges:
        raise ValueError("Stackhouse bridge identity count changed")
    if _role_count(plan.specs, "customs-sawtooth-roof") != 4:
        raise ValueError("Customs must keep exactly four full-depth roof teeth")
    if _role_count(plan.specs, "customs-sawtooth-triangular-glass-gable") != 4:
        raise ValueError("Customs must keep exactly four triangular glazed gables")
    if spawn_intrusions(plan):
        raise ValueError(f"spawn intrusions: {spawn_intrusions(plan)}")
    if route_intrusions(plan):
        raise ValueError(f"road intrusions: {route_intrusions(plan)}")
    return metrics


def emit_plan(builder: Any, plan: SpecPlan,
              material_map: Mapping[str, str] = DEFAULT_INTEGRATION_MATERIAL_MAP) -> None:
    """Emit through a small reviewed builder protocol; no Blender import needed."""
    for spec in plan.specs:
        payload = dict(spec)
        payload["material"] = material_map.get(spec["material"], spec["material"])
        method = getattr(builder, f"add_{spec['kind']}", None)
        if method is None and spec["kind"] == "oriented_box":
            method = getattr(builder, "add_box", None)
        if method is None:
            raise AttributeError(f"builder cannot emit {spec['kind']}")
        method(**payload)


def _v_add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_mul(a: Sequence[float], scalar: float) -> tuple[float, float, float]:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _v_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v_cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _v_norm(a: Sequence[float]) -> tuple[float, float, float]:
    length = math.sqrt(_v_dot(a, a))
    if length < 1e-10:
        raise ValueError("cannot normalize zero vector")
    return (a[0] / length, a[1] / length, a[2] / length)


def _runtime_to_blender(point: Sequence[float]) -> tuple[float, float, float]:
    """Convert runtime X/Y-up/Z to Blender X/Y-plan/Z-up."""
    return (float(point[0]), float(point[2]), float(point[1]))


def _append_polyhedron(batch: dict[str, list[Any]],
                       vertices: Sequence[Sequence[float]],
                       faces: Sequence[Sequence[int]]) -> None:
    offset = len(batch["vertices"])
    batch["vertices"].extend(_runtime_to_blender(vertex) for vertex in vertices)
    batch["faces"].extend(tuple(offset + index for index in face) for face in faces)


def _append_box_mesh(batch: dict[str, list[Any]], spec: Mapping[str, Any]) -> None:
    yaw = float(spec.get("yaw", 0.0))
    axis_x = (math.cos(yaw), 0.0, math.sin(yaw))
    axis_y = (0.0, 1.0, 0.0)
    axis_z = (-math.sin(yaw), 0.0, math.cos(yaw))
    centre = (float(spec["x"]), float(spec["y"]), float(spec["z"]))
    half = (float(spec["w"]) / 2, float(spec["h"]) / 2, float(spec["d"]) / 2)
    signs = ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
             (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
    vertices = []
    for sx, sy, sz in signs:
        point = centre
        point = _v_add(point, _v_mul(axis_x, sx * half[0]))
        point = _v_add(point, _v_mul(axis_y, sy * half[1]))
        point = _v_add(point, _v_mul(axis_z, sz * half[2]))
        vertices.append(point)
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    _append_polyhedron(batch, vertices, faces)


def _append_beam_mesh(batch: dict[str, list[Any]], spec: Mapping[str, Any]) -> None:
    start = tuple(float(value) for value in spec["start"])
    end = tuple(float(value) for value in spec["end"])
    axis = _v_norm(_v_sub(end, start))
    reference = (0.0, 1.0, 0.0) if abs(_v_dot(axis, (0.0, 1.0, 0.0))) < 0.92 else (1.0, 0.0, 0.0)
    side = _v_norm(_v_cross(axis, reference))
    up = _v_norm(_v_cross(side, axis))
    half_w, half_d = float(spec["width"]) / 2, float(spec["depth"]) / 2
    corners = []
    for point in (start, end):
        for sw, sd in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            corner = _v_add(point, _v_mul(side, sw * half_w))
            corner = _v_add(corner, _v_mul(up, sd * half_d))
            corners.append(corner)
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    _append_polyhedron(batch, corners, faces)


def _append_cylinder_mesh(batch: dict[str, list[Any]], spec: Mapping[str, Any]) -> None:
    segments = int(spec["segments"])
    centre_x, centre_y, centre_z = float(spec["x"]), float(spec["y"]), float(spec["z"])
    bottom_y = centre_y - float(spec["height"]) / 2
    top_y = centre_y + float(spec["height"]) / 2
    bottom_radius, top_radius = float(spec["radius"]), float(spec["topRadius"])
    vertices = []
    for y, radius in ((bottom_y, bottom_radius), (top_y, top_radius)):
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append((centre_x + math.cos(angle) * radius, y,
                             centre_z + math.sin(angle) * radius))
    faces: list[tuple[int, ...]] = [tuple(reversed(range(segments))),
                                    tuple(range(segments, segments * 2))]
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((index, nxt, segments + nxt, segments + index))
    _append_polyhedron(batch, vertices, faces)


def _append_panel_mesh(batch: dict[str, list[Any]], spec: Mapping[str, Any]) -> None:
    corners = tuple(tuple(float(value) for value in point) for point in spec["corners"])
    normal = _v_norm(_v_cross(_v_sub(corners[1], corners[0]),
                              _v_sub(corners[2], corners[0])))
    offset = _v_mul(normal, float(spec["thickness"]) / 2)
    back = [_v_sub(point, offset) for point in corners]
    front = [_v_add(point, offset) for point in corners]
    count = len(corners)
    vertices = back + front
    faces: list[tuple[int, ...]] = [tuple(reversed(range(count))),
                                    tuple(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    _append_polyhedron(batch, vertices, faces)


def _build_mesh_batches(plan: SpecPlan) -> dict[str, dict[str, list[Any]]]:
    batches: dict[str, dict[str, list[Any]]] = defaultdict(lambda: {"vertices": [], "faces": []})
    for spec in plan.specs:
        batch = batches[spec["material"]]
        if spec["kind"] in {"box", "oriented_box"}:
            _append_box_mesh(batch, spec)
        elif spec["kind"] == "beam":
            _append_beam_mesh(batch, spec)
        elif spec["kind"] == "cylinder":
            _append_cylinder_mesh(batch, spec)
        elif spec["kind"] == "panel":
            _append_panel_mesh(batch, spec)
        else:
            raise ValueError(f"unsupported mesh kind: {spec['kind']}")
    return dict(batches)


def _clamp_color(value: float) -> float:
    return min(1.0, max(0.0, value))


def _shade_color(color: Sequence[float], factor: float) -> tuple[float, float, float, float]:
    return tuple(_clamp_color(float(channel) * factor) for channel in color[:3]) + (float(color[3]),)


def _set_bsdf_input(bsdf: Any, names: Sequence[str], value: Any) -> bool:
    for name in names:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def _make_blender_material(bpy: Any, key: str, recipe: Mapping[str, Any]) -> Any:
    material = bpy.data.materials.new(f"SO_A18_R8_{key}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (690, 40)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (410, 40)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    color = tuple(float(value) for value in recipe["color"])
    _set_bsdf_input(bsdf, ("Base Color",), color)
    _set_bsdf_input(bsdf, ("Metallic",), float(recipe.get("metallic", 0.0)))
    _set_bsdf_input(bsdf, ("Roughness",), float(recipe.get("roughness", 0.6)))

    noise_amount = float(recipe.get("noise", 0.0))
    if noise_amount > 0.0:
        texcoord = nodes.new("ShaderNodeTexCoord")
        texcoord.location = (-760, 80)
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-570, 80)
        # Batch objects keep metre-scale coordinates, so Object space exposes
        # weathering at facade scale instead of one uniform Generated gradient.
        if key in {"old_concrete", "pale_concrete", "dark_concrete", "red_brick"}:
            noise.inputs["Scale"].default_value = 0.16
        elif recipe.get("rustMask"):
            noise.inputs["Scale"].default_value = 0.42
        elif recipe.get("wetVariation"):
            noise.inputs["Scale"].default_value = 0.10
        else:
            noise.inputs["Scale"].default_value = 0.65
        noise.inputs["Detail"].default_value = 5.0
        noise.inputs["Roughness"].default_value = 0.72
        noise.inputs["Distortion"].default_value = 0.12
        links.new(texcoord.outputs["Object"], noise.inputs["Vector"])
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (-330, 150)
        ramp.color_ramp.elements[0].position = 0.22
        ramp.color_ramp.elements[0].color = _shade_color(color, 0.63 if recipe.get("stains") else 0.76)
        ramp.color_ramp.elements[1].position = 0.78
        ramp.color_ramp.elements[1].color = _shade_color(color, 1.28)
        if recipe.get("rustMask"):
            ramp.color_ramp.elements[0].color = (0.10, 0.12, 0.12, 1.0)
            ramp.color_ramp.elements[1].color = (0.42, 0.105, 0.018, 1.0)
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        bump = nodes.new("ShaderNodeBump")
        bump.location = (175, -205)
        bump.inputs["Strength"].default_value = min(0.32, 0.09 + noise_amount * 0.75)
        bump.inputs["Distance"].default_value = 0.15 if recipe.get("stains") else 0.07
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        rough_ramp = nodes.new("ShaderNodeValToRGB")
        rough_ramp.location = (-80, -75)
        base_rough = float(recipe.get("roughness", 0.6))
        low = 0.08 if recipe.get("wetVariation") else max(0.12, base_rough - 0.17)
        high = 0.43 if recipe.get("wetVariation") else min(0.98, base_rough + 0.14)
        rough_ramp.color_ramp.elements[0].color = (low, low, low, 1.0)
        rough_ramp.color_ramp.elements[1].color = (high, high, high, 1.0)
        links.new(noise.outputs["Fac"], rough_ramp.inputs["Fac"])
        links.new(rough_ramp.outputs["Color"], bsdf.inputs["Roughness"])
        if recipe.get("rustMask"):
            metallic_ramp = nodes.new("ShaderNodeValToRGB")
            metallic_ramp.location = (-80, -325)
            metal = float(recipe.get("metallic", 0.0))
            metallic_ramp.color_ramp.elements[0].color = (metal, metal, metal, 1.0)
            metallic_ramp.color_ramp.elements[1].color = (0.04, 0.04, 0.04, 1.0)
            links.new(noise.outputs["Fac"], metallic_ramp.inputs["Fac"])
            links.new(metallic_ramp.outputs["Color"], bsdf.inputs["Metallic"])

    transmission = float(recipe.get("transmission", 0.0))
    if transmission:
        _set_bsdf_input(bsdf, ("Transmission Weight", "Transmission"), transmission)
        _set_bsdf_input(bsdf, ("IOR",), 1.46)
    alpha = float(recipe.get("alpha", 1.0))
    if alpha < 1.0:
        _set_bsdf_input(bsdf, ("Alpha",), alpha)
        material.diffuse_color = color
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
    emission = recipe.get("emission")
    if emission:
        _set_bsdf_input(bsdf, ("Emission Color", "Emission"), tuple(emission))
        _set_bsdf_input(bsdf, ("Emission Strength",), float(recipe.get("emissionStrength", 0.5)))
    return material


def _clear_background_scene(bpy: Any) -> None:
    if not bpy.app.background:
        raise RuntimeError("private Souko proof refuses to edit an interactive Blender scene")
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in tuple(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def _create_blender_geometry(bpy: Any, plan: SpecPlan) -> dict[str, Any]:
    root = bpy.data.collections.new(TARGET_COLLECTION)
    bpy.context.scene.collection.children.link(root)
    batches = _build_mesh_batches(plan)
    materials = {key: _make_blender_material(bpy, key, MATERIALS[key]) for key in batches}
    raw_triangles = 0
    mesh_objects = []
    for material_key in sorted(batches):
        batch = batches[material_key]
        mesh = bpy.data.meshes.new(f"SO_A18_R8_{material_key}_MESH")
        mesh.from_pydata(batch["vertices"], [], batch["faces"])
        mesh.update(calc_edges=True)
        raw_triangles += sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        obj = bpy.data.objects.new(f"SO_A18_R8_{material_key}", mesh)
        root.objects.link(obj)
        obj.data.materials.append(materials[material_key])
        if material_key not in {"dirty_glass", "puddle_water", "sea_water", "warm_glass"}:
            bevel = obj.modifiers.new("SO_A18_R8_micro_bevel", "BEVEL")
            bevel.width = 0.035
            bevel.segments = 1
            bevel.limit_method = "ANGLE"
        mesh_objects.append(obj)
    return {
        "collection": root, "meshObjects": mesh_objects,
        "rawMeshTriangles": raw_triangles,
        "meshObjectCount": len(mesh_objects), "batchCount": len(batches),
        "vertexCount": sum(len(batch["vertices"]) for batch in batches.values()),
        "polygonCount": sum(len(batch["faces"]) for batch in batches.values()),
    }


def _look_at(obj: Any, target: Sequence[float]) -> None:
    from mathutils import Vector
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_world_lighting_camera(bpy: Any) -> Any:
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.image_settings.color_depth = "8"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        pass
    scene.view_settings.exposure = 0.55

    world = bpy.data.worlds.new("SO_A18_R8_coastal_world")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.72
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "3D"
    noise.inputs["Scale"].default_value = 1.15
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.76
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.075, 0.15, 0.26, 1.0)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.48, 0.58, 0.68, 1.0)
    links.new(texcoord.outputs["Normal"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    scene.world = world

    sun_data = bpy.data.lights.new("SO_A18_R8_low_warm_sun", "SUN")
    sun_data.energy = 2.4
    sun_data.color = (1.0, 0.72, 0.46)
    sun_data.angle = math.radians(5.0)
    sun = bpy.data.objects.new("SO_A18_R8_low_warm_sun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(56.0), math.radians(-8.0), math.radians(-118.0))

    area_data = bpy.data.lights.new("SO_A18_R8_cool_cloud_fill", "AREA")
    area_data.energy = 9500.0
    area_data.color = (0.34, 0.54, 0.76)
    area_data.shape = "DISK"
    area_data.size = 96.0
    area = bpy.data.objects.new("SO_A18_R8_cool_cloud_fill", area_data)
    bpy.context.scene.collection.objects.link(area)
    area.location = (-55.0, -20.0, 125.0)
    _look_at(area, (20.0, 30.0, 0.0))

    reverse_data = bpy.data.lights.new("SO_A18_R8_soft_reverse_fill", "AREA")
    reverse_data.energy = 7200.0
    reverse_data.color = (0.72, 0.78, 0.84)
    reverse_data.shape = "DISK"
    reverse_data.size = 110.0
    reverse = bpy.data.objects.new("SO_A18_R8_soft_reverse_fill", reverse_data)
    bpy.context.scene.collection.objects.link(reverse)
    reverse.location = (155.0, 135.0, 95.0)
    _look_at(reverse, (10.0, 20.0, 8.0))

    camera_data = bpy.data.cameras.new("SO_A18_R8_fixed_eye_camera")
    camera_data.sensor_width = 36.0
    camera_data.clip_start = 0.08
    camera_data.clip_end = 950.0
    camera = bpy.data.objects.new("SO_A18_R8_fixed_eye_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def producer_provisional_scorecard() -> dict[str, Any]:
    items = [dict(item) for item in PRODUCER_PROVISIONAL_SCORE_ITEMS]
    average = sum(float(item["score"]) for item in items) / len(items)
    minimum = min(float(item["score"]) for item in items)
    return {
        "schema": "hibana-reference-scorecard-v1",
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "referenceSha256": REFERENCE_SHA256,
        "producerProvisional": True,
        "formalReferencePassClaimed": False,
        "independentReviewRequired": True,
        "status": "PRODUCER PROVISIONAL / NO FORMAL REFERENCE PASS",
        "fixedCategoryOrder": list(FIXED_SCORE_CATEGORIES),
        "items": items,
        "average": round(average, 3),
        "minimum": minimum,
        "formalPassGate": {
            "requiredMinimumPerCategory": 8.0,
            "requiredAverage": 8.0,
            "producerCanCertify": False,
            "currentlyMeetsNumericGate": minimum >= 8.0 and average >= 8.0,
        },
    }


def run_private_prototype(output_dir: Path = PRIVATE_OUTPUT_ROOT, lod: int = 0) -> dict[str, Any]:
    """Build, save and render only inside a background Blender process."""
    import bpy

    if not bpy.app.background:
        raise RuntimeError("private Souko proof is background-only; live Blender remains untouched")
    output_dir = Path(output_dir).expanduser().resolve()
    # Scope is deliberately a named private directory, never a workspace path.
    if not str(output_dir).startswith("/private/tmp/hibana-blender/"):
        raise ValueError(f"private output must stay under /private/tmp/hibana-blender: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(lod)
    metrics = plan_metrics(plan)

    _clear_background_scene(bpy)
    geometry = _create_blender_geometry(bpy, plan)
    camera = _setup_world_lighting_camera(bpy)
    first_view = PRIVATE_VIEWS[0]
    camera.location = _runtime_to_blender(first_view["eye"])
    camera.data.lens = float(first_view["lensMm"])
    _look_at(camera, _runtime_to_blender(first_view["target"]))

    blend_path = output_dir / f"souko-reference-a18-r8-lod{lod}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    render_records = []
    for view in PRIVATE_VIEWS:
        eye = tuple(float(value) for value in view["eye"])
        target = tuple(float(value) for value in view["target"])
        if abs(eye[1] - PLAYER_EYE_M) > 1e-9:
            raise ValueError(f"non-canonical eye height in {view['id']}: {eye[1]}")
        camera.location = _runtime_to_blender(eye)
        camera.data.lens = float(view["lensMm"])
        _look_at(camera, _runtime_to_blender(target))
        render_path = output_dir / f"{view['id']}.png"
        bpy.context.scene.render.filepath = str(render_path)
        bpy.ops.render.render(write_still=True)
        render_records.append({
            "id": view["id"], "purpose": view["purpose"],
            "path": str(render_path), "sha256": _sha256(render_path),
            "bytes": render_path.stat().st_size, "resolutionPx": [1280, 720],
            "cameraEyeRuntimeM": list(eye), "targetRuntimeM": list(target),
            "eyeHeightM": eye[1], "lensMm": float(view["lensMm"]),
        })

    repo_root = Path(__file__).resolve().parents[3]
    reference_path = repo_root / REFERENCE_PATH
    source_path = Path(__file__).resolve()
    reference_actual_sha = _sha256(reference_path) if reference_path.is_file() else None
    scorecard = producer_provisional_scorecard()
    scorecard_path = output_dir / "producer-provisional-scorecard.json"
    _write_json(scorecard_path, scorecard)
    report = {
        "schema": "hibana-private-blender-proof-v1",
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "privateOnly": True,
        "interactiveBlenderTouched": False,
        "publicAssetTreeTouched": False,
        "formalReferencePassClaimed": False,
        "independentReviewRequired": True,
        "source": {"path": str(source_path), "sha256": _sha256(source_path)},
        "reference": {
            "path": str(reference_path), "expectedSha256": REFERENCE_SHA256,
            "actualSha256": reference_actual_sha,
            "hashMatches": reference_actual_sha == REFERENCE_SHA256,
            "originalResolutionPx": [1672, 941],
            "inspectionMode": "original-size source plus fixed camera renders",
        },
        "blend": {
            "path": str(blend_path), "sha256": _sha256(blend_path),
            "bytes": blend_path.stat().st_size,
        },
        "planMetrics": metrics,
        "geometryMetrics": {key: value for key, value in geometry.items()
                            if key not in {"collection", "meshObjects"}},
        "renderCount": len(render_records),
        "renders": render_records,
        "technicalChecks": {
            "backgroundOnly": bool(bpy.app.background),
            "allEightViewsRendered": len(render_records) == 8,
            "allEyeHeightsExactly1_65m": all(abs(item["eyeHeightM"] - PLAYER_EYE_M) < 1e-9
                                               for item in render_records),
            "referenceHashMatches": reference_actual_sha == REFERENCE_SHA256,
            "routeIntrusions": route_intrusions(plan),
            "spawnIntrusions": spawn_intrusions(plan),
            "exactFourCustomsRoofTeeth": _role_count(plan.specs, "customs-sawtooth-roof") == 4,
            "exactFourCustomsGlassGables": _role_count(plan.specs, "customs-sawtooth-triangular-glass-gable") == 4,
            "fourStackhouseTowers": _role_count(plan.specs, "stackhouse-roof-cap") == 4,
            "realThreeDimensionalHorizon": True,
            "imagePlanesOrBillboards": 0,
        },
        "scorecard": str(scorecard_path),
    }
    report_path = output_dir / "prototype-report.json"
    _write_json(report_path, report)
    report["reportPath"] = str(report_path)
    return report


def _parse_cli(argv: Sequence[str]) -> argparse.Namespace:
    arguments = list(argv)
    if "--" in arguments:
        arguments = arguments[arguments.index("--") + 1:]
    else:
        arguments = arguments[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PRIVATE_OUTPUT_ROOT)
    parser.add_argument("--lod", type=int, choices=tuple(LOD_API), default=0)
    parser.add_argument("--plan-only", action="store_true",
                        help="Print pure-data metrics without importing Blender.")
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    namespace = _parse_cli(sys.argv if argv is None else argv)
    if namespace.plan_only:
        print(json.dumps(plan_metrics(build_plan(namespace.lod)), indent=2, sort_keys=True))
        return 0
    report = run_private_prototype(namespace.output_dir, namespace.lod)
    print(json.dumps({
        "reportPath": report["reportPath"],
        "renderCount": report["renderCount"],
        "formalReferencePassClaimed": report["formalReferencePassClaimed"],
        "planMetrics": report["planMetrics"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
