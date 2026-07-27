#!/usr/bin/env python3
"""Private A20 art rebuild for Nakaniwa, derived from the isolated r11 kit.

Production brief
----------------
Target: a static, game-readable WebGL FPS environment at one Blender metre per
runtime metre.  The authoritative 320 m bounds, 16 m cross roads, player and
bot spawns, landmark envelopes, entrances and approaches are immutable.  The
ImageGen reference is used only for modelling comparison.

The locked 1.65 m camera must read foreground garden architecture and water,
an occupied midground of bridges/terraces, and a real three-dimensional far
garden-city horizon.  The Crowned Water Palace is rebuilt as supported,
habitable vertical layers terminating in a framed petal crown.  The Fan-Glass
Conservatory is rebuilt from five overlapping vaults with transparent glazing,
a planted interior, irrigation, two upper walks, stairs and a rear destination.

Forbidden motifs: box plus spikes, one long barrel-vault shed, empty straight
plaza, emissive square-window wallpaper, unsupported slabs, thin floating
parts, raster mattes and cylindrical picture walls.

Connection map (minimum real contact in metres)
------------------------------------------------
  ground top Y=0.00 <-> palace plinth bottom Y=-0.10       overlap 0.10
  plinth top Y=1.20 <-> arcade/wing bases Y=1.10           overlap 0.10
  columns top <-> supported terrace underside              overlap 0.12
  terrace top <-> occupied keep bottom                     overlap 0.10
  keep roof <-> crown drum                                 overlap 0.18
  crown drum <-> petal frames                              overlap 0.12
  petal glazing <-> four edge frames                       overlap 0.04
  entry stair <-> palace threshold                         overlap 0.10
  water court <-> dressed coping                           overlap 0.04
  conservatory plinth <-> vault buttress                   overlap 0.10
  buttress <-> transverse vault rib                        overlap 0.12
  transverse rib <-> longitudinal purlin                   overlap 0.04
  purlin/rib cells <-> glazing                             overlap 0.03
  threshold <-> central promenade                          overlap 0.10
  promenade <-> rear destination                           overlap 0.10
  walk support <-> upper walk underside                    overlap 0.12
  stair top <-> upper walk                                 overlap 0.08
  upper walk <-> rear crosswalk                            overlap 0.08
  irrigation rill <-> water channel coping                 overlap 0.04
  planter soil <-> trunk/plant stem                        overlap 0.10
  foreground arcade <-> flanking pavilion                 overlap 0.10
  bridge deck <-> canal coping                             overlap 0.04
  skyline roof <-> occupied facade                         overlap 0.10

All directional members are explicit start/end beams.  Cubes are represented
as full dimensions and the private builder creates them from size=2 semantics.
No Euler-rotated cylinder is used for a spanning connection.

This module never edits ``nakaniwa_reference_a18.py``, ``build_all_stages.py``,
public assets, runtime source or manifests.  Its optional Blender proof writes
only below ``/private/tmp/hibana-blender/a20-nakaniwa-art-rebuild`` and remains
provisional NO-SHIP until a different reviewer signs a new scorecard.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import nakaniwa_reference_a18 as R11  # noqa: E402


STAGE_ID = "nakaniwa"
KIT_VERSION = "nakaniwa-reference-a20-v1"
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/nakaniwa-reference-v1.png"
REFERENCE_SHA256 = "c0b3bec12431c264ebe04a0757ea67eb521eab2c4e32e004da88cf6e6eebe15d"
PRIVATE_PROOF_DEFAULT = Path("/private/tmp/hibana-blender/a20-nakaniwa-art-rebuild")
CANONICAL_LAYOUT_DEFAULT = Path("/private/tmp/hibana-blender/canonical-stage-layouts.json")
TARGET_COLLECTION = "HB_NAKANIWA_A20_ART_REBUILD"

MAP_SIZE_M = 320.0
CANONICAL_BOUNDS = {
    "min_x": -160.0,
    "max_x": 160.0,
    "min_z": -160.0,
    "max_z": 160.0,
}
CANONICAL_ROADS = copy.deepcopy(R11.CANONICAL_ROADS)
CANONICAL_PLAYER_SPAWNS = copy.deepcopy(R11.CANONICAL_PLAYER_SPAWNS)
CANONICAL_BOT_SPAWNS = (
    (0.0, 0.0, 88.0), (0.0, 0.0, 82.0), (0.0, 0.0, 76.0),
    (0.0, 0.0, 68.0), (0.0, 0.0, 62.0), (0.0, 0.0, 56.0),
    (0.0, 0.0, 48.0), (0.0, 0.0, 42.0), (0.0, 0.0, 36.0),
    (0.0, 0.0, 28.0), (-4.0, 0.0, 72.0), (4.0, 0.0, 72.0),
    (-4.0, 0.0, 52.0), (4.0, 0.0, 52.0), (-4.0, 0.0, 32.0),
    (4.0, 0.0, 32.0), (-8.0, 0.0, 88.0), (-8.0, 0.0, 80.0),
    (-8.0, 0.0, 68.0), (-8.0, 0.0, 60.0), (-8.0, 0.0, 48.0),
    (-8.0, 0.0, 40.0), (-12.0, 0.0, 84.0), (-12.0, 0.0, 76.0),
    (-12.0, 0.0, 64.0), (-16.0, 0.0, 88.0), (-16.0, 0.0, 80.0),
    (-16.0, 0.0, 72.0), (-20.0, 0.0, 84.0), (-20.0, 0.0, 76.0),
    (-24.0, 0.0, 92.0), (-24.0, 0.0, 80.0),
)
LANDMARKS = copy.deepcopy(R11.LANDMARKS)
PALACE_ID = LANDMARKS[0]["id"]
CONSERVATORY_ID = LANDMARKS[1]["id"]
PLAYER_EYE_M = 1.65


FIXED_SCORE_CATEGORIES = (
    "composition",
    "hero silhouettes",
    "architectural grammar",
    "human scale",
    "material realism",
    "near/mid/far density",
    "gameplay readability",
    "props and environmental storytelling",
    "lighting and atmosphere",
    "reference identity",
)

# Camera is intentionally locked before geometry detail.  It lies on the
# south-east perpendicular of the canonical hero-centre segment, close enough
# for both destinations to dominate while retaining a navigable foreground.
MAIN_REFERENCE_CAMERA = {
    "name": "CAM_Nakaniwa_A20_Eye165_Dual",
    # The south-east perpendicular of the immutable landmark axis puts the
    # palace on frame-left and the conservatory on frame-right, matching the
    # reference's identity.  Both are at nearly equal camera distance and the
    # central canal remains a real traversable pull into the middle distance.
    "location": (90.0, PLAYER_EYE_M, -70.0),
    "target": (-4.0, 3.5, -3.0),
    "lensMm": 15.0,
    "sensorWidthMm": 36.0,
    "resolution": (1280, 720),
    "eyeHeightM": PLAYER_EYE_M,
    "intent": "tight dual-hero near-mid-far reference composition",
}

PROOF_CAMERAS = (
    MAIN_REFERENCE_CAMERA,
    {
        "name": "CAM_Nakaniwa_A20_Eye165_PalaceWaterCourt",
        "location": (-68.0, PLAYER_EYE_M, 8.0),
        "target": (-60.0, 20.0, -54.0),
        "lensMm": 24.0,
        "sensorWidthMm": 36.0,
        "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "palace supported facade and water court",
    },
    {
        "name": "CAM_Nakaniwa_A20_Eye165_ConservatoryThreshold",
        "location": (52.0, PLAYER_EYE_M, 13.0),
        "target": (52.0, 14.0, 69.0),
        "lensMm": 22.0,
        "sensorWidthMm": 36.0,
        "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "clear entrance and overlapping fan vaults",
    },
    {
        "name": "CAM_Nakaniwa_A20_Eye165_ConservatoryInterior",
        "location": (46.5, PLAYER_EYE_M, 38.0),
        "target": (52.0, 4.0, 76.0),
        "lensMm": 22.0,
        "sensorWidthMm": 36.0,
        "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "botanical interior and rear destination",
    },
    {
        "name": "CAM_Nakaniwa_A20_UpperWalk",
        "location": (52.0, 13.5, 78.0),
        "target": (52.0, 7.0, 43.0),
        "lensMm": 20.0,
        "sensorWidthMm": 36.0,
        "resolution": (1280, 720),
        "eyeHeightM": 13.5,
        "intent": "paired upper walks, stairs and botanical nave",
    },
    {
        "name": "CAM_Nakaniwa_A20_Eye165_CanalStory",
        "location": (7.0, PLAYER_EYE_M, -9.0),
        "target": (-45.0, 8.5, -48.0),
        "lensMm": 27.0,
        "sensorWidthMm": 36.0,
        "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "human-scale cover, bridge and irrigation story",
    },
    {
        "name": "CAM_Nakaniwa_A20_Aerial",
        "location": (168.0, 96.0, -172.0),
        "target": (-4.0, 10.0, -3.0),
        "lensMm": 48.0,
        "sensorWidthMm": 36.0,
        "resolution": (1280, 720),
        "eyeHeightM": 142.0,
        "intent": "canonical composition and exact two landmarks",
    },
)


MATERIALS = {
    "wet_stone": {
        "color": (0.095, 0.072, 0.052, 1.0), "roughness": (0.30, 0.64),
        "metallic": 0.0, "noiseScale": 5.0, "bump": 0.20,
    },
    "honey_stone": {
        "color": (0.30, 0.155, 0.065, 1.0), "roughness": (0.42, 0.73),
        "metallic": 0.0, "noiseScale": 4.2, "bump": 0.16,
    },
    "white_marble": {
        "color": (0.42, 0.34, 0.245, 1.0), "roughness": (0.22, 0.46),
        "metallic": 0.0, "noiseScale": 6.2, "bump": 0.08,
    },
    "verdigris_bronze": {
        "color": (0.018, 0.105, 0.080, 1.0), "roughness": (0.20, 0.42),
        "metallic": 0.82, "noiseScale": 8.0, "bump": 0.06,
    },
    "dark_wood": {
        "color": (0.025, 0.008, 0.003, 1.0), "roughness": (0.38, 0.64),
        "metallic": 0.0, "noiseScale": 7.0, "bump": 0.10,
    },
    "brass": {
        "color": (0.31, 0.105, 0.012, 1.0), "roughness": (0.16, 0.33),
        "metallic": 0.88, "noiseScale": 10.0, "bump": 0.035,
    },
    "glass": {
        "color": (0.018, 0.105, 0.12, 0.30), "roughness": (0.035, 0.095),
        "metallic": 0.0, "transmission": 0.90, "alpha": 0.30, "ior": 1.45,
        "noiseScale": 18.0, "bump": 0.015,
    },
    "water": {
        "color": (0.0015, 0.016, 0.028, 1.0), "roughness": (0.26, 0.40),
        "metallic": 0.04, "transmission": 0.02, "alpha": 1.0, "ior": 1.333,
        "noiseScale": 2.2, "bump": 0.12,
    },
    "foliage_dark": {
        "color": (0.006, 0.050, 0.010, 1.0), "roughness": (0.54, 0.80),
        "metallic": 0.0, "noiseScale": 5.5, "bump": 0.07, "subsurface": 0.04,
    },
    "foliage_light": {
        "color": (0.030, 0.155, 0.020, 1.0), "roughness": (0.50, 0.75),
        "metallic": 0.0, "noiseScale": 6.5, "bump": 0.07, "subsurface": 0.04,
    },
    "flower": {
        "color": (0.30, 0.035, 0.18, 1.0), "roughness": (0.38, 0.58),
        "metallic": 0.0, "noiseScale": 9.0, "bump": 0.04,
    },
    "warm_window": {
        "color": (0.28, 0.055, 0.006, 1.0), "roughness": (0.30, 0.48),
        "metallic": 0.0, "emission": (1.0, 0.22, 0.015, 1.0),
        "emissionStrength": 1.25, "noiseScale": 12.0, "bump": 0.0,
    },
}

DEFAULT_INTEGRATION_MATERIAL_MAP = copy.deepcopy(R11.DEFAULT_INTEGRATION_MATERIAL_MAP)

LOD_BUDGETS = {
    0: {"maxEstimatedTriangles": 180_000, "maxSpecs": 8_200, "maxMaterials": 12},
    1: {"maxEstimatedTriangles": 80_000, "maxSpecs": 4_000, "maxMaterials": 12},
    2: {"maxEstimatedTriangles": 24_000, "maxSpecs": 1_350, "maxMaterials": 12},
}

CONNECTION_MAP = tuple(copy.deepcopy(item) for item in R11.CONNECTION_MAP) + (
    {"id": "a20-palace-column-terrace", "a": "palace-supported-column", "aFace": "top", "b": "palace-supported-terrace", "bFace": "underside", "axis": "y", "overlapM": 0.12},
    {"id": "a20-palace-terrace-keep", "a": "palace-supported-terrace", "aFace": "top", "b": "palace-occupied-keep", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a20-palace-keep-crown", "a": "palace-tiered-roof", "aFace": "ridge", "b": "palace-crown-drum", "bFace": "bottom", "axis": "y", "overlapM": 0.18},
    {"id": "a20-palace-crown-petal", "a": "palace-crown-drum", "aFace": "ring", "b": "palace-crown-petal-frame", "bFace": "root", "axis": "surface", "overlapM": 0.12},
    {"id": "a20-palace-petal-glass", "a": "palace-crown-petal-frame", "aFace": "inside", "b": "palace-crown-petal-glass", "bFace": "edge", "axis": "surface", "overlapM": 0.04},
    {"id": "a20-palace-water-coping", "a": "palace-water-court", "aFace": "edge", "b": "palace-water-coping", "bFace": "inside", "axis": "surface", "overlapM": 0.04},
    {"id": "a20-vault-rib-buttress", "a": "conservatory-vault-buttress", "aFace": "top", "b": "conservatory-fan-vault-rib", "bFace": "spring", "axis": "surface", "overlapM": 0.12},
    {"id": "a20-vault-rib-purlin", "a": "conservatory-fan-vault-rib", "aFace": "crossing", "b": "conservatory-vault-purlin", "bFace": "crossing", "axis": "surface", "overlapM": 0.04},
    {"id": "a20-vault-glazing", "a": "conservatory-vault-purlin", "aFace": "cell", "b": "conservatory-glass-cell", "bFace": "edge", "axis": "surface", "overlapM": 0.03},
    {"id": "a20-walk-support", "a": "conservatory-walk-support", "aFace": "top", "b": "conservatory-upper-walk", "bFace": "underside", "axis": "y", "overlapM": 0.12},
    {"id": "a20-stair-walk", "a": "conservatory-interior-stair", "aFace": "top", "b": "conservatory-upper-walk", "bFace": "deck", "axis": "y", "overlapM": 0.08},
    {"id": "a20-walk-destination", "a": "conservatory-rear-crosswalk", "aFace": "rear", "b": "conservatory-botanical-destination", "bFace": "front", "axis": "z", "overlapM": 0.08},
    {"id": "a20-irrigation-rill", "a": "conservatory-interior-water", "aFace": "side", "b": "conservatory-irrigation-coping", "bFace": "inside", "axis": "surface", "overlapM": 0.04},
    {"id": "a20-story-prop-ground", "a": "story-prop", "aFace": "bottom", "b": "wet-plaza", "bFace": "top", "axis": "y", "overlapM": 0.02},
    {"id": "a20-palace-keep-gate-tier", "a": "palace-occupied-keep", "aFace": "front", "b": "palace-projecting-gate-tier", "bFace": "rear", "axis": "z", "overlapM": 0.20},
    {"id": "a20-palace-gate-tier-roof", "a": "palace-projecting-gate-tier", "aFace": "top", "b": "palace-projecting-gate-roof", "bFace": "underside", "axis": "y", "overlapM": 0.15},
    {"id": "a20-palace-gate-crown", "a": "palace-gate-crown-roof", "aFace": "ridge", "b": "palace-crown-drum", "bFace": "bottom", "axis": "y", "overlapM": 0.18},
    {"id": "a20-palace-lower-petal-drum", "a": "palace-crown-drum", "aFace": "outer", "b": "palace-lower-crown-petal", "bFace": "root", "axis": "surface", "overlapM": 0.12},
    {"id": "a20-palace-inner-lantern-ring", "a": "palace-crown-support-ring", "aFace": "top", "b": "palace-crown-inner-lantern", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a20-conservatory-floor-foundation", "a": "conservatory-interior-floor", "aFace": "edge", "b": "conservatory-perimeter-foundation", "bFace": "inside", "axis": "surface", "overlapM": 0.08},
    {"id": "a20-conservatory-soil-plant", "a": "conservatory-deep-soil-bed", "aFace": "top", "b": "conservatory-flowering-understory", "bFace": "bottom", "axis": "y", "overlapM": 0.08},
    {"id": "a20-conservatory-vault-chain", "a": "conservatory-fan-vault-rib", "aFace": "underside", "b": "conservatory-hanging-chain", "bFace": "top", "axis": "y", "overlapM": 0.04},
    {"id": "a20-conservatory-chain-pot", "a": "conservatory-hanging-chain", "aFace": "bottom", "b": "conservatory-hanging-pot", "bFace": "top", "axis": "y", "overlapM": 0.05},
    {"id": "a20-conservatory-destination-arcade", "a": "conservatory-botanical-destination", "aFace": "front", "b": "conservatory-destination-arcade", "bFace": "rear", "axis": "z", "overlapM": 0.12},
    {"id": "a20-corridor-water-coping", "a": "reference-corridor-water", "aFace": "edge", "b": "reference-corridor-coping", "bFace": "inside", "axis": "surface", "overlapM": 0.04},
    {"id": "a20-corridor-water-bridge", "a": "reference-corridor-water", "aFace": "top", "b": "reference-corridor-bridge", "bFace": "underside", "axis": "y", "overlapM": 0.06},
    {"id": "a20-corridor-column-roof", "a": "near-corridor-pavilion-column", "aFace": "top", "b": "near-corridor-pavilion-roof", "bFace": "underside", "axis": "y", "overlapM": 0.12},
)


def _box(specs: list[dict], role: str, material: str, group: str,
         x: float, y: float, z: float, w: float, h: float, d: float,
         *, blocks_gameplay: bool = False) -> None:
    R11._box(specs, role, material, group, x, y, z, w, h, d,
             blocks_gameplay=blocks_gameplay)


def _beam(specs: list[dict], role: str, material: str, group: str,
          start: tuple[float, float, float], end: tuple[float, float, float],
          width: float, depth: float) -> None:
    R11._beam(specs, role, material, group, start, end, width, depth)


def _cylinder(specs: list[dict], role: str, material: str, group: str,
              x: float, y: float, z: float, radius: float, height: float,
              segments: int, *, top_radius: float | None = None) -> None:
    R11._cylinder(specs, role, material, group, x, y, z, radius, height,
                  segments, top_radius=top_radius)


def _panel(specs: list[dict], role: str, material: str, group: str,
           corners: Iterable[tuple[float, float, float]], thickness: float = 0.08) -> None:
    R11._panel(specs, role, material, group, corners, thickness)


def _ellipsoid(specs: list[dict], role: str, material: str, group: str,
               x: float, y: float, z: float,
               radius_x: float, radius_y: float, radius_z: float,
               segments: int = 10, rings: int = 6) -> None:
    """Add a low-cost organic volume without relying on Blender operators."""
    if min(radius_x, radius_y, radius_z) <= 0.0 or segments < 6 or rings < 4:
        raise ValueError(f"{role}: invalid ellipsoid")
    specs.append({
        "role": role,
        "material": material,
        "group": group,
        "blocksGameplay": False,
        "kind": "ellipsoid",
        "x": x,
        "y": y,
        "z": z,
        "radiusX": radius_x,
        "radiusY": radius_y,
        "radiusZ": radius_z,
        "segments": segments,
        "rings": rings,
    })


def _deep_roof(specs: list[dict], *, cx: float, base_y: float, cz: float,
               width: float, depth: float, height: float, axis: str,
               group: str, role: str, lod: int,
               material: str = "verdigris_bronze") -> None:
    R11._add_deep_gable_roof(
        specs, cx=cx, base_y=base_y, cz=cz, width=width, depth=depth,
        height=height, axis=axis, material=material, group=group,
        role_prefix=role, lod=lod,
    )


def _balustrade(specs: list[dict], *, x: float, y: float, z: float,
                length: float, axis: str, group: str, role: str, lod: int) -> None:
    R11._add_balustrade(
        specs, x=x, y=y, z=z, length=length, axis=axis,
        material="white_marble", group=group, role_prefix=role, lod=lod,
    )


def _arcade(specs: list[dict], *, cx: float, base_y: float, z: float,
            width: float, bays: int, group: str, role: str, lod: int) -> None:
    R11._add_arcade(
        specs, cx=cx, base_y=base_y, z=z, width=width,
        bay_count=bays, material="white_marble", group=group,
        role_prefix=role, lod=lod,
    )


def _side_arcade(specs: list[dict], *, x: float, base_y: float, cz: float,
                 length: float, bays: int, group: str, role: str, lod: int) -> None:
    R11._add_side_arcade(
        specs, x=x, base_y=base_y, cz=cz, length=length,
        bay_count=bays, material="white_marble", group=group,
        role_prefix=role, lod=lod,
    )


def _add_palace_a20(specs: list[dict], lod: int) -> None:
    """Layered, supported palace; replaces the r11 box-and-spike hero."""
    group = PALACE_ID
    detail = lod == 0
    medium = lod <= 1

    _box(specs, "a20-palace-water-plinth", "wet_stone", group,
         -60.0, 0.55, -67.8, 91.6, 1.30, 77.4)
    # Human-scale, climb-readable entry stair and deep threshold.
    stair_count = 7 if detail else 5 if medium else 3
    for index in range(stair_count):
        rise = 0.17 * (index + 1)
        _box(specs, "a20-palace-entry-stair", "white_marble", group,
             -60.0, rise / 2.0, -27.95 - index * 0.58,
             14.0 + index * 0.75, rise, 0.72)
    _box(specs, "a20-palace-entry-threshold", "white_marble", group,
         -60.0, 0.66, -33.2, 15.2, 1.10, 8.6)

    # Water court and coping turn the facade approach into the reference's
    # palace-garden foreground rather than an empty slab.
    for side in (-1.0, 1.0):
        x = -60.0 + side * 26.0
        _box(specs, "a20-palace-water-court", "water", group,
             x, 0.12, -42.0, 18.0, 0.22, 16.0)
        for edge_x in (x - 9.25, x + 9.25):
            _box(specs, "a20-palace-water-coping", "white_marble", group,
                 edge_x, 0.42, -42.0, 0.50, 0.72, 16.7)
        for edge_z in (-50.25, -33.75):
            _box(specs, "a20-palace-water-coping", "white_marble", group,
                 x, 0.42, edge_z, 18.5, 0.72, 0.50)
        _cylinder(specs, "a20-palace-court-fountain-bowl", "brass", group,
                  x, 0.65, -42.0, 2.25, 0.50, 16, top_radius=1.8)
        _cylinder(specs, "a20-palace-court-fountain-jet", "water", group,
                  x, 1.7, -42.0, 0.18, 2.1, 10, top_radius=0.08)

    # Three lower occupied masses keep the entry permeable and eliminate the
    # monolithic r11 facade slab.
    lower_masses = (
        (-83.0, 6.45, -70.5, 37.0, 10.7, 52.0, "west"),
        (-60.0, 8.10, -73.0, 31.0, 14.0, 43.0, "centre"),
        (-37.0, 6.45, -70.5, 37.0, 10.7, 52.0, "east"),
    )
    for cx, cy, cz, width, height, depth, suffix in lower_masses:
        _box(specs, "a20-palace-occupied-lower-mass", "honey_stone", group,
             cx, cy, cz, width, height, depth)
        # Deep facade piers and inset timber bays establish real wall depth.
        bay_count = 5 if detail else 3 if medium else 2
        for bay in range(bay_count):
            tx = cx - width * 0.38 + bay * (width * 0.76 / max(1, bay_count - 1))
            _box(specs, "a20-palace-deep-window-recess", "dark_wood", group,
                 tx, 6.6, cz + depth / 2.0 + 0.16, 3.2, 4.2, 0.42)
            for dx in (-1.75, 1.75):
                _beam(specs, "a20-palace-window-stone-frame", "white_marble", group,
                      (tx + dx, 4.25, cz + depth / 2.0 + 0.42),
                      (tx + dx, 8.95, cz + depth / 2.0 + 0.42), 0.20, 0.20)
            _beam(specs, "a20-palace-window-stone-frame", "white_marble", group,
                  (tx - 1.95, 9.15, cz + depth / 2.0 + 0.42),
                  (tx + 1.95, 9.15, cz + depth / 2.0 + 0.42), 0.22, 0.22)
        _deep_roof(specs, cx=cx, base_y=11.65, cz=cz, width=width - 1.0,
                   depth=depth - 1.2, height=3.8 if suffix != "centre" else 4.6,
                   axis="x", group=group, role="a20-palace-tiered-roof", lod=lod)

    # A genuine ground arcade in front of the three masses.  Columns continue
    # to the supported balcony so the overhang never reads as floating.
    _arcade(specs, cx=-60.0, base_y=1.12, z=-34.05, width=84.0,
            bays=12 if detail else 8 if medium else 5,
            group=group, role="a20-palace-grand-arcade", lod=lod)
    # Deep, occupied shadow boxes sit behind the arcade rather than exposing
    # a flat beige backing wall.  Timber transoms and brass mullions separate
    # each threshold at a believable civic scale.
    arcade_bays = 12 if detail else 8 if medium else 5
    arcade_bay_width = 84.0 / arcade_bays
    for bay in range(arcade_bays):
        x = -102.0 + arcade_bay_width * (bay + 0.5)
        _box(specs, "a20-palace-arcade-deep-opening", "dark_wood", group,
             x, 4.15, -34.48, arcade_bay_width * 0.70, 5.65, 0.34)
        _beam(specs, "a20-palace-arcade-opening-mullion", "brass", group,
              (x, 1.45, -34.70), (x, 6.90, -34.70), 0.105, 0.10)
        _beam(specs, "a20-palace-arcade-opening-transom", "brass", group,
              (x - arcade_bay_width * 0.28, 4.55, -34.70),
              (x + arcade_bay_width * 0.28, 4.55, -34.70), 0.10, 0.10)
        if detail and bay in {1, 4, 7, 10}:
            _box(specs, "a20-palace-arcade-warm-interior", "warm_window", group,
                 x, 3.05, -34.73, arcade_bay_width * 0.34, 1.35, 0.08)
    support_count = 12 if detail else 8 if medium else 6
    for index in range(support_count):
        x = -99.0 + index * 78.0 / max(1, support_count - 1)
        _cylinder(specs, "a20-palace-supported-column", "white_marble", group,
                  x, 6.1, -42.3, 0.62, 10.2, 12, top_radius=0.52)
        _box(specs, "a20-palace-column-capital", "white_marble", group,
             x, 11.28, -42.3, 1.75, 0.48, 1.75)
    _box(specs, "a20-palace-supported-terrace", "white_marble", group,
         -60.0, 11.55, -48.0, 84.5, 0.82, 13.0)
    _balustrade(specs, x=-60.0, y=12.35, z=-41.6, length=82.0, axis="x",
                group=group, role="a20-palace-terrace-balustrade", lod=lod)

    # Second and third habitable tiers establish the palace as a destination.
    _box(specs, "a20-palace-occupied-keep", "white_marble", group,
         -60.0, 18.4, -71.5, 31.5, 13.2, 32.0)
    _box(specs, "a20-palace-occupied-side-tower", "honey_stone", group,
         -82.5, 17.0, -73.0, 17.0, 10.5, 24.0)
    _box(specs, "a20-palace-occupied-side-tower", "honey_stone", group,
         -37.5, 17.0, -73.0, 17.0, 10.5, 24.0)

    # A three-dimensional gate-palace steps forward from the deep keep.  Its
    # two occupied tiers, loggia and broad roofs break the former rectangular
    # facade into the reference's stacked, habitable water-palace silhouette.
    _box(specs, "a20-palace-projecting-gate-tier", "honey_stone", group,
         -60.0, 17.25, -50.7, 28.0, 9.7, 10.2)
    _arcade(specs, cx=-60.0, base_y=12.35, z=-45.48, width=25.6,
            bays=5 if detail else 4 if medium else 3,
            group=group, role="a20-palace-projecting-loggia", lod=lod)
    _deep_roof(specs, cx=-60.0, base_y=21.95, cz=-50.7,
               width=29.5, depth=11.4, height=3.65, axis="x", group=group,
               role="a20-palace-projecting-gate-roof", lod=lod)
    _box(specs, "a20-palace-projecting-gate-tier", "white_marble", group,
         -60.0, 25.35, -52.0, 17.5, 7.4, 8.2)
    upper_bays = 5 if detail else 3
    for bay in range(upper_bays):
        px = -60.0 - 6.3 + 12.6 * bay / max(1, upper_bays - 1)
        _box(specs, "a20-palace-gate-upper-recess", "dark_wood", group,
             px, 25.4, -47.72, 1.7, 3.1, 0.34)
        _beam(specs, "a20-palace-gate-upper-frame", "brass", group,
              (px - 1.02, 23.55, -47.95), (px - 1.02, 27.25, -47.95), 0.12, 0.13)
        _beam(specs, "a20-palace-gate-upper-frame", "brass", group,
              (px + 1.02, 23.55, -47.95), (px + 1.02, 27.25, -47.95), 0.12, 0.13)
    _deep_roof(specs, cx=-60.0, base_y=28.9, cz=-52.0,
               width=19.2, depth=9.8, height=3.35, axis="x", group=group,
               role="a20-palace-gate-crown-roof", lod=lod)

    # Roofed side belvederes and flying braces make the broad terrace read as
    # supported architectural depth instead of a single horizontal slab.
    for cx in (-84.0, -36.0):
        _box(specs, "a20-palace-side-belvedere", "white_marble", group,
             cx, 15.65, -51.8, 12.0, 7.3, 9.0)
        _box(specs, "a20-palace-side-belvedere-recess", "dark_wood", group,
             cx, 15.8, -47.14, 4.8, 3.5, 0.34)
        _deep_roof(specs, cx=cx, base_y=19.25, cz=-51.8,
                   width=13.4, depth=10.4, height=3.0, axis="x", group=group,
                   role="a20-palace-side-belvedere-roof", lod=lod)
        brace_inner = -71.0 if cx < -60.0 else -49.0
        _beam(specs, "a20-palace-flying-terrace-brace", "white_marble", group,
              (cx, 11.35, -45.0), (brace_inner, 18.2, -51.4), 0.28, 0.26)
    _arcade(specs, cx=-60.0, base_y=12.2, z=-55.1, width=29.0,
            bays=6 if detail else 4 if medium else 3,
            group=group, role="a20-palace-upper-loggia", lod=lod)
    for cx in (-82.5, -60.0, -37.5):
        width = 16.5 if cx != -60.0 else 31.0
        depth = 23.0 if cx != -60.0 else 31.0
        base = 22.3 if cx != -60.0 else 25.0
        _deep_roof(specs, cx=cx, base_y=base, cz=-73.0 if cx != -60.0 else -71.5,
                   width=width, depth=depth, height=3.5 if cx != -60.0 else 4.4,
                   axis="x", group=group, role="a20-palace-tiered-roof", lod=lod)

    # The side towers terminate in occupied lantern pavilions, not blank roof
    # caps.  Their overlap with the lower gables makes the vertical hierarchy
    # continuous while keeping the central crystal crown dominant.
    for cx in (-82.5, -37.5):
        _box(specs, "a20-palace-side-lantern-pavilion", "white_marble", group,
             cx, 27.25, -73.0, 8.4, 5.0, 9.2)
        _box(specs, "a20-palace-side-lantern-recess", "dark_wood", group,
             cx, 27.3, -68.25, 3.2, 2.8, 0.38)
        for dx in (-1.8, 1.8):
            _beam(specs, "a20-palace-side-lantern-frame", "brass", group,
                  (cx + dx, 25.6, -68.48), (cx + dx, 29.1, -68.48), 0.15, 0.16)
        _deep_roof(specs, cx=cx, base_y=29.55, cz=-73.0, width=9.4, depth=10.2,
                   height=3.15, axis="x", group=group,
                   role="a20-palace-side-lantern-roof", lod=lod)

    # Vertical facade lattice, drip hoods and supported corner buttresses.
    facade_positions = tuple(-72.0 + i * 4.8 for i in range(6 if detail else 4 if medium else 3))
    for index, x in enumerate(facade_positions):
        _beam(specs, "a20-palace-facade-pilaster", "verdigris_bronze", group,
              (x, 14.0, -55.6), (x, 23.8, -55.6), 0.18, 0.22)
        _beam(specs, "a20-palace-weathering-drip-hood", "brass", group,
              (x - 1.5, 19.4 + (index % 2) * 2.0, -55.85),
              (x + 1.5, 19.4 + (index % 2) * 2.0, -55.85), 0.16, 0.18)
    for x in (-103.0, -17.0):
        _cylinder(specs, "a20-palace-grounded-buttress", "honey_stone", group,
                  x, 7.0, -69.0, 2.3, 12.2, 8, top_radius=1.25)

    # The immutable diagonal map placement exposes the palace's east side to
    # the reference-order dual camera.  Treat it as a complete ceremonial
    # elevation: deep arcades, shadowed rooms, a supported side gallery and an
    # occupied upper loggia, never an undressed back/side box.
    east_x = -17.72
    east_length = 50.0
    east_bays = 9 if detail else 6 if medium else 4
    _side_arcade(specs, x=east_x, base_y=1.12, cz=-70.5,
                 length=east_length, bays=east_bays, group=group,
                 role="a20-palace-east-grand-arcade", lod=lod)
    east_bay_depth = east_length / east_bays
    for bay in range(east_bays):
        z = -70.5 - east_length / 2.0 + east_bay_depth * (bay + 0.5)
        _box(specs, "a20-palace-east-deep-opening", "dark_wood", group,
             east_x - 0.40, 4.15, z, 0.34, 5.6, east_bay_depth * 0.68)
        _beam(specs, "a20-palace-east-opening-mullion", "brass", group,
              (east_x + 0.25, 1.45, z), (east_x + 0.25, 6.85, z),
              0.10, 0.10)
        if detail and bay % 3 == 1:
            _box(specs, "a20-palace-east-warm-interior", "warm_window", group,
                 east_x + 0.28, 3.05, z, 0.08, 1.35, east_bay_depth * 0.32)
    _box(specs, "a20-palace-east-supported-gallery", "white_marble", group,
         -17.05, 11.55, -70.5, 1.25, 0.82, 50.4)
    _balustrade(specs, x=-16.55, y=12.35, z=-70.5, length=48.0, axis="z",
                group=group, role="a20-palace-east-gallery-balustrade", lod=lod)
    upper_east_x = -28.72
    _side_arcade(specs, x=upper_east_x, base_y=12.35, cz=-73.0,
                 length=21.5, bays=4 if detail else 3, group=group,
                 role="a20-palace-east-upper-loggia", lod=lod)
    for z in (-81.0, -73.0, -65.0):
        _box(specs, "a20-palace-east-upper-recess", "dark_wood", group,
             upper_east_x - 0.36, 16.25, z, 0.34, 4.6, 3.3)
        _beam(specs, "a20-palace-east-upper-brass-frame", "brass", group,
              (upper_east_x + 0.25, 13.6, z - 1.9),
              (upper_east_x + 0.25, 19.0, z - 1.9), 0.12, 0.11)
        _beam(specs, "a20-palace-east-upper-brass-frame", "brass", group,
              (upper_east_x + 0.25, 13.6, z + 1.9),
              (upper_east_x + 0.25, 19.0, z + 1.9), 0.12, 0.11)

    # Flower-like structural crown: broad framed petals with glass infill, not
    # repeated thin spikes.  The drum and ring carry every panel root.
    crown_x, crown_z = -60.0, -52.0
    _cylinder(specs, "a20-palace-crown-drum", "white_marble", group,
              crown_x, 30.2, crown_z, 10.4, 5.4, 16, top_radius=9.6)
    _cylinder(specs, "a20-palace-crown-support-ring", "brass", group,
              crown_x, 32.75, crown_z, 10.15, 0.55, 20, top_radius=10.15)
    drum_pilasters = 10 if detail else 8 if medium else 6
    for index in range(drum_pilasters):
        angle = math.tau * index / drum_pilasters
        x = crown_x + math.cos(angle) * 9.75
        z = crown_z + math.sin(angle) * 9.75
        _cylinder(specs, "a20-palace-crown-drum-pilaster", "brass", group,
                  x, 30.15, z, 0.20, 5.25, 8, top_radius=0.15)
    # Two roofed shoulder lanterns step the gate tower into the circular crown
    # instead of jumping directly from a gable to the petal ring.
    for x in (-69.0, -51.0):
        _box(specs, "a20-palace-crown-shoulder-lantern", "honey_stone", group,
             x, 30.0, -51.8, 5.8, 4.4, 6.2)
        _box(specs, "a20-palace-crown-shoulder-recess", "dark_wood", group,
             x, 30.0, -48.55, 2.6, 2.6, 0.30)
        _deep_roof(specs, cx=x, base_y=32.15, cz=-51.8,
                   width=6.4, depth=6.8, height=2.7, axis="x", group=group,
                   role="a20-palace-crown-shoulder-roof", lod=lod)
        _cylinder(specs, "a20-palace-crown-shoulder-finial", "brass", group,
                  x, 35.7, -51.8, 0.20, 2.1, 8, top_radius=0.045)
    # Four diagonal stone/metal carriers tie the flower crown to the gate roof
    # below; the silhouette now reads as a supported tower termination.
    for sx, sz in ((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)):
        _beam(specs, "a20-palace-crown-gate-buttress", "white_marble", group,
              (crown_x + sx * 7.2, 29.0, crown_z + sz * 3.5),
              (crown_x + sx * 8.6, 32.85, crown_z + sz * 4.9), 0.34, 0.30)
        _beam(specs, "a20-palace-crown-gate-brace", "brass", group,
              (crown_x + sx * 5.3, 29.15, crown_z + sz * 3.8),
              (crown_x + sx * 8.6, 32.85, crown_z + sz * 4.9), 0.16, 0.15)
    # Broad opaque lotus sepals form a lower crown tier beneath the glazed
    # blades.  This continuous bowl is the crucial antidote to a spike ring.
    lower_petal_count = 8 if lod <= 1 else 6
    for index in range(lower_petal_count):
        angle = math.tau * index / lower_petal_count + math.radians(22.5)
        tangent = (-math.sin(angle), math.cos(angle))
        radial = (math.cos(angle), math.sin(angle))
        inner = (crown_x + radial[0] * 5.4, crown_z + radial[1] * 5.4)
        outer = (crown_x + radial[0] * 11.6, crown_z + radial[1] * 11.6)
        corners = (
            (inner[0] - tangent[0] * 2.10, 30.45, inner[1] - tangent[1] * 2.10),
            (inner[0] + tangent[0] * 2.10, 30.45, inner[1] + tangent[1] * 2.10),
            (outer[0] + tangent[0] * 3.05, 34.75, outer[1] + tangent[1] * 3.05),
            (outer[0] - tangent[0] * 3.05, 34.75, outer[1] - tangent[1] * 3.05),
        )
        _panel(specs, "a20-palace-lower-crown-petal", "white_marble", group,
               corners, 0.15)
        for start, end in zip(corners, corners[1:] + corners[:1]):
            _beam(specs, "a20-palace-lower-crown-frame", "brass", group,
                  start, end, 0.17, 0.16)
        inset = tuple(
            (
                point[0] * 0.82 + crown_x * 0.18,
                point[1] + (0.16 if corner < 2 else -0.18),
                point[2] * 0.82 + crown_z * 0.18,
            )
            for corner, point in enumerate(corners)
        )
        _panel(specs, "a20-palace-lower-crown-glass-inset", "glass", group,
               inset, 0.055)
        _beam(specs, "a20-palace-lower-crown-spine", "brass", group,
              ((inner[0]), 30.45, inner[1]), (outer[0], 34.95, outer[1]),
              0.16, 0.15)
    # A habitable glazed lantern sits inside the petal ring.  Two galleries,
    # vertical mullions and the radial garland make the crown read as one
    # supported architectural room instead of disconnected spikes.
    _cylinder(specs, "a20-palace-crown-inner-lantern", "glass", group,
              crown_x, 35.85, crown_z, 4.55, 6.7,
              16 if detail else 12 if medium else 8, top_radius=3.8)
    for y, radius in ((32.75, 4.75), (39.05, 4.0)):
        _cylinder(specs, "a20-palace-crown-inner-gallery", "brass", group,
                  crown_x, y, crown_z, radius, 0.38,
                  16 if detail else 12 if medium else 8, top_radius=radius)
    mullion_count = 8 if detail else 6 if medium else 4
    for index in range(mullion_count):
        angle = math.tau * index / mullion_count
        radius = 4.25
        _cylinder(specs, "a20-palace-crown-inner-mullion", "verdigris_bronze", group,
                  crown_x + math.cos(angle) * radius, 35.9,
                  crown_z + math.sin(angle) * radius,
                  0.15, 6.5, 8, top_radius=0.12)
    petal_count = 9 if detail else 7 if medium else 5
    crown_roots = []
    for index in range(petal_count):
        angle = math.tau * index / petal_count + math.radians(10.0)
        tangent = (-math.sin(angle), math.cos(angle))
        radial = (math.cos(angle), math.sin(angle))
        base_c = (crown_x + radial[0] * 8.8, crown_z + radial[1] * 8.8)
        top_c = (crown_x + radial[0] * 13.0, crown_z + radial[1] * 13.0)
        half_base = 3.25
        half_top = 2.05
        corners = (
            (base_c[0] - tangent[0] * half_base, 31.6, base_c[1] - tangent[1] * half_base),
            (base_c[0] + tangent[0] * half_base, 31.6, base_c[1] + tangent[1] * half_base),
            (top_c[0] + tangent[0] * half_top, 40.8, top_c[1] + tangent[1] * half_top),
            (top_c[0] - tangent[0] * half_top, 40.8, top_c[1] - tangent[1] * half_top),
        )
        _panel(specs, "a20-palace-crown-petal-glass", "glass", group, corners, 0.11)
        for start, end in zip(corners, corners[1:] + corners[:1]):
            _beam(specs, "a20-palace-crown-petal-frame", "verdigris_bronze", group,
                  start, end, 0.25, 0.22)
        if lod <= 1:
            _beam(specs, "a20-palace-crown-petal-lattice", "brass", group,
                  corners[0], corners[2], 0.10, 0.10)
            _beam(specs, "a20-palace-crown-petal-lattice", "brass", group,
                  corners[1], corners[3], 0.10, 0.10)
        _beam(specs, "a20-palace-crown-petal-spine", "white_marble", group,
              ((base_c[0]), 31.6, base_c[1]), (top_c[0], 41.1, top_c[1]), 0.18, 0.20)
        crown_roots.append((base_c[0], 34.0, base_c[1]))
    for start, end in zip(crown_roots, crown_roots[1:] + crown_roots[:1]):
        _beam(specs, "a20-palace-crown-root-garland", "brass", group,
              start, end, 0.16, 0.14)
    _cylinder(specs, "a20-palace-master-spire", "brass", group,
              crown_x, 37.5, crown_z, 0.95, 10.8, 12, top_radius=0.16)
    _cylinder(specs, "a20-palace-master-orb", "verdigris_bronze", group,
              crown_x, 39.4, crown_z, 1.35, 1.25, 16, top_radius=1.05)
    for angle in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
        x = crown_x + math.cos(angle) * 3.0
        z = crown_z + math.sin(angle) * 3.0
        _cylinder(specs, "a20-palace-crown-companion-spire", "brass", group,
                  x, 38.5, z, 0.26, 8.2, 10, top_radius=0.055)
        _beam(specs, "a20-palace-crown-spire-flying-brace", "verdigris_bronze", group,
              (crown_x + math.cos(angle) * 4.2, 33.1,
               crown_z + math.sin(angle) * 4.2),
              (x, 40.1, z), 0.12, 0.11)

    # Occupied terraces: greenery, lanterns, benches and ceremonial banners.
    terrace_clusters = (
        (-92.0, -47.0), (-77.0, -47.0), (-43.0, -47.0), (-28.0, -47.0),
        (-74.0, -57.0), (-46.0, -57.0),
    )
    for index, (x, z) in enumerate(terrace_clusters[:6 if detail else 4 if medium else 2]):
        _box(specs, "a20-palace-terrace-planter", "white_marble", group,
             x, 12.75, z, 3.2, 0.8, 2.2)
        _cylinder(specs, "a20-palace-terrace-plant", "foliage_light", group,
                  x, 14.4, z, 1.2, 2.8, 8, top_radius=0.18)
        _cylinder(specs, "a20-palace-ceremonial-lantern", "brass", group,
                  x + (1.8 if index % 2 == 0 else -1.8), 13.65, z, 0.16, 2.2, 8)
        _box(specs, "a20-palace-ceremonial-lantern-light", "warm_window", group,
             x + (1.8 if index % 2 == 0 else -1.8), 14.45, z, 0.55, 0.65, 0.55)
    if detail:
        for x in (-87.0, -71.0, -49.0, -33.0):
            _box(specs, "a20-palace-civic-bench-seat", "dark_wood", group,
                 x, 0.70, -29.8, 3.0, 0.24, 0.72)
            _box(specs, "a20-palace-civic-bench-leg", "brass", group,
                 x - 1.0, 0.36, -29.8, 0.18, 0.55, 0.55)
            _box(specs, "a20-palace-civic-bench-leg", "brass", group,
                 x + 1.0, 0.36, -29.8, 0.18, 0.55, 0.55)


def _vault_points(cx: float, spring_y: float, z: float,
                  half_width: float, rise: float, segments: int) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        (
            cx - half_width * math.cos(math.pi * index / segments),
            spring_y + rise * math.sin(math.pi * index / segments),
            z,
        )
        for index in range(segments + 1)
    )


def _add_fan_vault(specs: list[dict], *, name: str, cx: float, z0: float, z1: float,
                   half_width: float, spring_y: float, rise: float, lod: int) -> None:
    group = CONSERVATORY_ID
    segments = 14 if lod == 0 and name == "central" else 10 if lod == 0 else 9 if lod == 1 else 6
    sections = 9 if lod == 0 and name == "central" else 6 if lod == 0 else 5 if lod == 1 else 3
    rings = []
    for section in range(sections):
        z = z0 + (z1 - z0) * section / max(1, sections - 1)
        ring = _vault_points(cx, spring_y, z, half_width, rise, segments)
        rings.append(ring)
        for start, end in zip(ring, ring[1:]):
            _beam(specs, "a20-conservatory-fan-vault-rib", "verdigris_bronze", group,
                  start, end, 0.20 if lod == 0 else 0.26, 0.18 if lod == 0 else 0.22)
    # Longitudinal purlins make every glass cell structurally attached.
    purlin_stride = 1 if lod <= 1 else 2
    for arc_index in range(0, segments + 1, purlin_stride):
        _beam(specs, "a20-conservatory-vault-purlin", "brass", group,
              rings[0][arc_index], rings[-1][arc_index], 0.12 if lod == 0 else 0.17, 0.11)
    # Transparent cells expose the botanical interior.  LOD2 retains alternate
    # cells to read as a vault instead of an opaque shed.
    cell_stride = 1 if lod <= 1 else 2
    for section in range(0, sections - 1):
        for arc_index in range(0, segments, cell_stride):
            next_arc = min(segments, arc_index + cell_stride)
            _panel(
                specs, "a20-conservatory-glass-cell", "glass", group,
                (
                    rings[section][arc_index],
                    rings[section][next_arc],
                    rings[section + 1][next_arc],
                    rings[section + 1][arc_index],
                ),
                0.045 if lod == 0 else 0.065,
            )
    # Every spring has a grounded buttress.
    buttress_sections = sections if lod <= 1 else 2
    for section in range(buttress_sections):
        z = z0 + (z1 - z0) * section / max(1, buttress_sections - 1)
        for side in (-1.0, 1.0):
            x = cx + side * half_width
            _cylinder(specs, "a20-conservatory-vault-buttress", "white_marble", group,
                      x, spring_y / 2.0, z, 0.75, spring_y + 0.18, 8, top_radius=0.48)


def _add_conservatory_a20(specs: list[dict], lod: int) -> None:
    """Five overlapping fan vaults and a deep botanical destination."""
    group = CONSERVATORY_ID
    detail = lod == 0
    medium = lod <= 1

    # A flush floor plus true perimeter strips carry the shell without filling
    # both side aisles with 32 m-wide opaque slabs.  The botanical hall is
    # therefore visually and physically open at the locked 1.65 m height.
    _box(specs, "a20-conservatory-interior-floor", "wet_stone", group,
         52.0, 0.06, 61.8, 72.0, 0.18, 63.8)
    for x in (14.8, 89.2):
        _box(specs, "a20-conservatory-perimeter-foundation", "white_marble", group,
             x, 0.62, 61.8, 1.6, 1.35, 65.2)
    _box(specs, "a20-conservatory-rear-foundation-left", "white_marble", group,
         31.0, 0.62, 94.35, 34.0, 1.35, 0.9)
    _box(specs, "a20-conservatory-rear-foundation-right", "white_marble", group,
         73.0, 0.62, 94.35, 34.0, 1.35, 0.9)
    _box(specs, "a20-conservatory-threshold-left", "white_marble", group,
         30.0, 0.62, 29.30, 32.0, 1.35, 1.0)
    _box(specs, "a20-conservatory-threshold-right", "white_marble", group,
         74.0, 0.62, 29.30, 32.0, 1.35, 1.0)
    for x in (47.25, 56.75):
        _cylinder(specs, "a20-conservatory-portal-pier", "white_marble", group,
                  x, 4.0, 29.45, 0.78, 8.0, 10, top_radius=0.62)
    portal_ring = _vault_points(52.0, 4.0, 29.45, 4.75, 4.1, 8)
    for start, end in zip(portal_ring, portal_ring[1:]):
        _beam(specs, "a20-conservatory-entrance-arch", "brass", group,
              start, end, 0.22, 0.20)
    _box(specs, "a20-conservatory-entry-sign", "dark_wood", group,
         52.0, 8.65, 29.25, 7.2, 0.75, 0.34)
    for x in (48.2, 55.8):
        _box(specs, "a20-conservatory-entry-lantern", "warm_window", group,
             x, 5.2, 29.0, 0.48, 0.78, 0.32)

    # Monumental nested entry fans expose the five-vault identity immediately
    # from player height.  Broad ribs converge on grounded side plinths rather
    # than reading as another long anonymous barrel shed.
    entry_fans = (
        (52.0, 30.55, 17.6, 5.6, 36.0),
        (43.0, 29.05, 12.0, 4.8, 28.0),
        (76.0, 37.75, 13.0, 5.0, 31.0),
    )
    for fan_index, (cx, z, half_width, spring, rise) in enumerate(entry_fans):
        ring = _vault_points(cx, spring, z, half_width, rise, 14 if detail else 9)
        for point_index in range(2, len(ring) - 1, 4 if detail else 4):
            side = -1.0 if point_index < len(ring) / 2 else 1.0
            anchor = (cx + side * half_width, 0.68, z - 0.18 * fan_index)
            _beam(specs, "a20-conservatory-monumental-fan-spoke",
                  "verdigris_bronze", group, anchor, ring[point_index],
                  0.115 if detail else 0.18, 0.105)
        for side in (-1.0, 1.0):
            _box(specs, "a20-conservatory-fan-spoke-plinth", "honey_stone", group,
                 cx + side * half_width, 0.82, z, 2.1, 1.55, 2.4)

    # Entry planting and service doors turn the shell into an inhabited civic
    # threshold instead of a purely structural shed mouth.
    for side, x in ((-1.0, 39.8), (1.0, 64.2)):
        _box(specs, "a20-conservatory-entry-botanical-plinth", "honey_stone", group,
             x, 0.72, 31.4, 6.8, 1.30, 4.2)
        _box(specs, "a20-conservatory-entry-botanical-soil", "dark_wood", group,
             x, 1.40, 31.4, 6.0, 0.20, 3.5)
        for plant in range(3 if detail else 2):
            px = x + (plant - 1) * 1.65
            _ellipsoid(specs, "a20-conservatory-entry-botanical-mass",
                       "foliage_light" if (plant + (0 if side < 0 else 1)) % 2
                       else "foliage_dark",
                       group, px, 2.65 + 0.35 * plant, 31.4,
                       1.15, 1.55 + 0.25 * plant, 1.05,
                       10 if detail else 8, 6 if detail else 4)
        _box(specs, "a20-conservatory-entry-service-door", "dark_wood", group,
             x + side * 5.3, 2.2, 30.05, 2.2, 4.2, 0.35)
        _beam(specs, "a20-conservatory-entry-service-door-frame", "brass", group,
              (x + side * 6.55, 0.10, 29.82),
              (x + side * 6.55, 4.45, 29.82), 0.13, 0.12)

    # Five laterally and longitudinally offset shells; the central shell is
    # tallest, side shells overlap it, and front/rear shells create a fan-like
    # compound silhouette from the locked dual view.
    vaults = (
        ("central", 52.0, 31.0, 94.1, 17.6, 5.6, 36.0),
        ("west", 28.0, 38.0, 91.5, 13.0, 5.0, 27.0),
        ("east", 76.0, 38.0, 91.5, 13.0, 5.0, 31.0),
        ("front-fan", 43.0, 29.3, 68.5, 12.0, 4.8, 28.0),
        ("rear-fan", 61.0, 53.0, 94.2, 12.0, 5.2, 30.0),
    )
    for args in vaults:
        _add_fan_vault(
            specs, name=args[0], cx=args[1], z0=args[2], z1=args[3],
            half_width=args[4], spring_y=args[5], rise=args[6], lod=lod,
        )

    # Continuous central destination route and paired irrigation rills.
    _box(specs, "a20-conservatory-central-promenade", "honey_stone", group,
         52.0, 0.30, 62.0, 7.6, 0.58, 64.0)
    _box(specs, "a20-conservatory-promenade-water-inlay", "water", group,
         52.0, 0.62, 64.0, 3.35, 0.12, 50.0)
    stepping_count = 10 if detail else 6 if medium else 4
    for step in range(stepping_count):
        z = 41.0 + 46.0 * step / max(1, stepping_count - 1)
        _box(specs, "a20-conservatory-promenade-stepping-stone", "white_marble", group,
             52.0, 0.78, z, 4.2, 0.26, 1.25)
    for x in (44.3, 59.7):
        _box(specs, "a20-conservatory-interior-water", "water", group,
             x, 0.08, 63.0, 2.15, 0.18, 56.0)
        for side in (-1.0, 1.0):
            _box(specs, "a20-conservatory-irrigation-coping", "white_marble", group,
                 x + side * 1.28, 0.34, 63.0, 0.40, 0.64, 56.5)
    for z in (43.0, 58.0, 73.0, 87.0):
        _box(specs, "a20-conservatory-rill-crossing", "dark_wood", group,
             52.0, 0.50, z, 20.2, 0.34, 2.0)
    _box(specs, "a20-conservatory-foreground-threshold-bridge", "honey_stone", group,
         52.0, 0.72, 40.4, 13.5, 0.48, 2.8)
    for x in (45.7, 58.3):
        _beam(specs, "a20-conservatory-threshold-bridge-edge", "brass", group,
              (x, 0.98, 39.1), (x, 0.98, 41.7), 0.13, 0.11)
    for x in (42.5, 61.5):
        _box(specs, "a20-conservatory-near-interior-planter", "honey_stone", group,
             x, 0.72, 42.0, 5.2, 1.25, 4.2)
        _box(specs, "a20-conservatory-near-interior-soil", "dark_wood", group,
             x, 1.37, 42.0, 4.5, 0.18, 3.5)
        for offset in (-1.25, 0.0, 1.25):
            _ellipsoid(specs, "a20-conservatory-near-interior-leaf-mass",
                       "foliage_light" if offset == 0.0 else "foliage_dark", group,
                       x + offset, 2.55 + (0.55 if offset == 0.0 else 0.0), 42.0,
                       1.1, 1.35, 1.0,
                       10 if detail else 8, 6 if detail else 4)

    # Deep multi-height botanical interior.  Plants are deliberately unequal
    # in scale and adjacency, avoiding cloned green boxes.
    plant_rows = (
        (32.0, (41.0, 53.0, 67.0, 82.0), 5.8),
        (39.0, (46.0, 61.0, 77.0, 89.0), 3.8),
        (65.0, (43.0, 57.0, 72.0, 86.0), 4.5),
        (72.0, (48.0, 64.0, 80.0, 90.0), 6.2),
    )
    max_rows = 4 if detail else 3 if medium else 2
    for row_index, (x, zs, base_height) in enumerate(plant_rows[:max_rows]):
        for plant_index, z in enumerate(zs if detail else zs[::2] if medium else zs[:2]):
            height = base_height * (0.82 + 0.16 * ((plant_index + row_index) % 3))
            _box(specs, "a20-conservatory-botanical-planter", "wet_stone", group,
                 x, 0.58, z, 4.6, 1.05, 3.6)
            _box(specs, "a20-conservatory-planter-soil", "dark_wood", group,
                 x, 1.14, z, 4.1, 0.20, 3.1)
            _cylinder(specs, "a20-conservatory-botanical-trunk", "dark_wood", group,
                      x, 1.2 + height * 0.36, z, 0.28 + 0.05 * (plant_index % 2),
                      height * 0.72, 8, top_radius=0.18)
            crown_y = 1.2 + height * 0.76
            for layer in range(3 if detail else 2):
                radius = height * (0.24 - layer * 0.035)
                _cylinder(specs, "a20-conservatory-dense-planting",
                          "foliage_light" if (plant_index + layer) % 2 else "foliage_dark",
                          group, x + (layer - 1) * 0.35, crown_y + layer * 0.62, z,
                          radius, 1.8 + layer * 0.55, 9, top_radius=radius * 0.25)
            cluster_count = 3 if detail else 1 if medium else 0
            for cluster in range(cluster_count):
                _ellipsoid(
                    specs, "a20-conservatory-broadleaf-cluster",
                    "foliage_light" if (plant_index + row_index + cluster) % 2 else "foliage_dark",
                    group,
                    x + (-1.0 + cluster) * height * 0.18,
                    crown_y + 0.45 + (cluster % 2) * 0.72,
                    z + (0.65 if cluster == 1 else -0.45),
                    height * (0.25 if cluster == 1 else 0.21),
                    height * 0.16,
                    height * 0.22,
                    10 if detail else 8,
                    6 if detail else 4,
                )

    # Tall unequal specimen trees bridge the ground and upper-walk layers so
    # the transparent hall exposes a botanical interior rather than a white
    # structural canyon.  Their crowns stay outside the clear promenade.
    specimen_positions = (
        (24.0, 47.0, 12.5), (41.5, 55.0, 10.5),
        (62.5, 48.0, 13.5), (80.0, 59.0, 11.5),
        (24.5, 76.0, 10.0), (41.0, 83.0, 12.0),
        (63.0, 75.0, 11.0), (79.0, 87.0, 13.0),
    )
    specimen_limit = 8 if detail else 4 if medium else 2
    for index, (x, z, height) in enumerate(specimen_positions[:specimen_limit]):
        _cylinder(specs, "a20-conservatory-specimen-trunk", "dark_wood", group,
                  x, 0.9 + height * 0.42, z, 0.34, height * 0.84,
                  9 if detail else 7, top_radius=0.18)
        crown_base = 1.0 + height * 0.62
        for layer in range(4 if detail else 3):
            radius = height * (0.22 - layer * 0.028)
            _cylinder(specs, "a20-conservatory-specimen-canopy",
                      "foliage_light" if (index + layer) % 2 else "foliage_dark",
                      group, x + (layer % 2 - 0.5) * 0.55,
                      crown_base + layer * 1.05, z + (layer - 1.5) * 0.35,
                      radius, 2.0 + layer * 0.45, 10 if detail else 8,
                      top_radius=max(0.24, radius * 0.22))
        cluster_count = 5 if detail else 2 if medium else 0
        for cluster in range(cluster_count):
            angle = math.tau * cluster / max(1, cluster_count) + index * 0.41
            _ellipsoid(
                specs, "a20-conservatory-specimen-broadleaf-canopy",
                "foliage_light" if (index + cluster) % 3 else "foliage_dark",
                group,
                x + math.cos(angle) * height * 0.17,
                crown_base + 1.4 + (cluster % 3) * 0.95,
                z + math.sin(angle) * height * 0.15,
                height * 0.23,
                height * 0.15,
                height * 0.20,
                11 if detail else 8,
                6 if detail else 4,
            )

    # Continuous dark soil beds, wet borders and flowers warm the base of the
    # blue-green shell.  They sit outside the 7.6 m central promenade and the
    # two upper-walk support lines.
    for side, x in ((-1.0, 24.0), (1.0, 80.0)):
        _box(specs, "a20-conservatory-deep-soil-bed", "dark_wood", group,
             x, 0.30, 66.0, 9.0, 0.52, 46.0)
        for edge_x in (x - 4.7, x + 4.7):
            _box(specs, "a20-conservatory-soil-bed-border", "honey_stone", group,
                 edge_x, 0.46, 66.0, 0.42, 0.82, 47.0)
        flower_count = 14 if detail else 7 if medium else 3
        for flower_index in range(flower_count):
            z = 44.0 + 44.0 * flower_index / max(1, flower_count - 1)
            offset = -1.8 if flower_index % 2 else 1.8
            _cylinder(specs, "a20-conservatory-flowering-understory", "flower", group,
                      x + offset, 1.05 + 0.16 * (flower_index % 3), z,
                      0.42, 1.25 + 0.22 * (flower_index % 3), 8, top_radius=0.10)
            if detail:
                _ellipsoid(
                    specs, "a20-conservatory-understory-leaf-mass",
                    "foliage_light" if flower_index % 3 else "foliage_dark",
                    group, x - offset * 0.58, 1.25,
                    z + (0.75 if flower_index % 2 else -0.75),
                    1.25, 0.72, 1.05, 9, 5,
                )

    # Climbing vines bridge shell and planting bed.  Each reaches a real rib
    # or purlin and descends through unequal leaf clusters, producing the
    # reference's occupied glass volume without narrowing the central route.
    vine_positions = tuple(
        (x, z, top_y)
        for z, top_y in ((45.0, 21.0), (56.0, 27.0), (69.0, 31.0), (82.0, 25.0))
        for x in (19.3, 84.7)
    )
    vine_limit = 8 if detail else 4 if medium else 0
    for vine_index, (x, z, top_y) in enumerate(vine_positions[:vine_limit]):
        _beam(specs, "a20-conservatory-climbing-vine", "foliage_dark", group,
              (x, 1.15, z), (x + (-0.8 if x < 52.0 else 0.8), top_y, z + 0.7),
              0.075, 0.065)
        leaf_count = 6 if detail else 3
        for leaf in range(leaf_count):
            ratio = (leaf + 1) / (leaf_count + 1)
            _ellipsoid(
                specs, "a20-conservatory-climbing-vine-leaf",
                "foliage_light" if (vine_index + leaf) % 2 else "foliage_dark",
                group,
                x + (-0.65 if x < 52.0 else 0.65) * ratio
                + (0.42 if leaf % 2 else -0.42),
                1.15 + (top_y - 1.15) * ratio,
                z + 0.7 * ratio,
                0.78, 0.46, 0.55, 8, 4,
            )

    # Hanging collections are physically chained to the central vault and
    # make the upper volume botanical as well as the ground plane.
    hanging_positions = tuple(
        (x, z) for z in (47.0, 61.0, 75.0, 87.0) for x in (40.0, 64.0)
    )
    hanging_limit = 8 if detail else 4 if medium else 2
    for index, (x, z) in enumerate(hanging_positions[:hanging_limit]):
        _beam(specs, "a20-conservatory-hanging-chain", "brass", group,
              (x, 31.3, z), (x, 18.6, z), 0.055, 0.055)
        _cylinder(specs, "a20-conservatory-hanging-pot", "honey_stone", group,
                  x, 18.15, z, 1.05, 0.90, 12, top_radius=1.28)
        for layer in range(3 if detail else 2):
            _cylinder(specs, "a20-conservatory-hanging-foliage",
                      "foliage_light" if (index + layer) % 2 else "foliage_dark",
                      group, x + (layer - 1) * 0.28, 16.9 - layer * 0.62, z,
                      0.92 - layer * 0.12, 2.2, 9, top_radius=0.18)
        if detail:
            for cluster in range(3):
                _ellipsoid(
                    specs, "a20-conservatory-hanging-broadleaf",
                    "foliage_light" if (index + cluster) % 2 else "foliage_dark",
                    group, x + (cluster - 1) * 0.75,
                    16.7 - cluster * 0.55, z + (0.45 if cluster % 2 else -0.35),
                    0.82, 0.55, 0.70, 9, 5,
                )

    # Fine irrigation mist and warm service lamps supply humidity and human
    # occupation without relying on an expensive volumetric pass.
    mist_zs = (49.0, 64.0, 79.0) if lod <= 1 else (64.0,)
    for z in mist_zs:
        for x in (44.3, 59.7):
            _cylinder(specs, "a20-conservatory-irrigation-mist", "water", group,
                      x, 2.25, z, 0.055, 4.2, 8, top_radius=0.24)
            if lod == 0:
                _box(specs, "a20-conservatory-warm-service-light", "warm_window", group,
                     x + (-1.0 if x < 52.0 else 1.0), 2.2, z,
                     0.38, 0.58, 0.38)

    # Elevated circulation has real supports, stairs, rails and a rear bridge.
    for side, x in ((-1.0, 35.0), (1.0, 69.0)):
        _box(specs, "a20-conservatory-upper-walk", "dark_wood", group,
             x, 9.15, 65.0, 3.4, 0.58, 53.0)
        support_zs = (42.0, 55.0, 68.0, 81.0, 90.0) if detail else (44.0, 66.0, 88.0)
        for z in support_zs:
            _cylinder(specs, "a20-conservatory-walk-support", "brass", group,
                      x, 4.65, z, 0.28, 8.9, 8, top_radius=0.24)
        _balustrade(specs, x=x - side * 1.65, y=9.72, z=65.0, length=50.5,
                    axis="z", group=group, role="a20-conservatory-upper-walk-rail", lod=lod)
        stair_count = 15 if detail else 10 if medium else 6
        for step in range(stair_count):
            ratio = (step + 1) / stair_count
            _box(specs, "a20-conservatory-interior-stair", "wet_stone", group,
                 x, 9.0 * ratio / 2.0,
                 39.0 + side * 0.0 + step * (9.0 / stair_count),
                 3.1, 9.0 * ratio, 0.78)
    _box(specs, "a20-conservatory-rear-crosswalk", "dark_wood", group,
         52.0, 10.0, 88.5, 31.5, 0.62, 3.0)
    for x in (37.0, 67.0):
        _cylinder(specs, "a20-conservatory-crosswalk-support", "brass", group,
                  x, 5.0, 88.5, 0.32, 9.9, 8, top_radius=0.26)
    _balustrade(specs, x=52.0, y=10.58, z=87.0, length=30.0, axis="x",
                group=group, role="a20-conservatory-rear-crosswalk-rail", lod=lod)

    # Rear irrigation observatory is the interior destination rather than a
    # generic civic facade seen through the shed.
    _cylinder(specs, "a20-conservatory-botanical-destination", "white_marble", group,
              52.0, 7.0, 90.0, 7.2, 12.5, 16, top_radius=6.2)
    _cylinder(specs, "a20-conservatory-irrigation-gallery", "verdigris_bronze", group,
              52.0, 13.2, 90.0, 6.3, 1.1, 16, top_radius=6.3)
    _cylinder(specs, "a20-conservatory-irrigation-lantern", "glass", group,
              52.0, 16.3, 90.0, 4.1, 5.2, 14, top_radius=2.2)
    _cylinder(specs, "a20-conservatory-irrigation-cap", "brass", group,
              52.0, 19.15, 90.0, 2.5, 0.65, 14, top_radius=0.55)
    _cylinder(specs, "a20-conservatory-irrigation-finial", "brass", group,
              52.0, 21.4, 90.0, 0.32, 4.0, 10, top_radius=0.08)
    # The rear observatory has a readable public face and water garden rather
    # than ending the nave with an undressed white cylinder.
    for x in (48.2, 52.0, 55.8):
        _box(specs, "a20-conservatory-destination-recess", "dark_wood", group,
             x, 6.2, 82.72, 2.25, 4.5, 0.34)
    _arcade(specs, cx=52.0, base_y=1.15, z=82.48, width=13.2,
            bays=3, group=group, role="a20-conservatory-destination-arcade", lod=lod)
    _box(specs, "a20-conservatory-destination-water", "water", group,
         52.0, 0.13, 79.2, 13.5, 0.22, 5.2)
    for x in (45.0, 59.0):
        _box(specs, "a20-conservatory-destination-planter", "honey_stone", group,
             x, 0.72, 79.2, 3.4, 1.25, 4.5)
        _cylinder(specs, "a20-conservatory-destination-plant", "foliage_light", group,
                  x, 2.55, 79.2, 1.45, 3.3, 9, top_radius=0.22)
        _box(specs, "a20-conservatory-destination-light", "warm_window", group,
             x, 3.25, 81.2, 0.48, 0.72, 0.44)

    # Botanical work story: potting benches, carts, irrigation valves, labels.
    if detail:
        for index, (x, z) in enumerate(((42.0, 48.0), (62.0, 55.0), (42.0, 76.0), (62.0, 82.0))):
            _box(specs, "a20-conservatory-potting-bench", "dark_wood", group,
                 x, 1.10, z, 4.2, 0.28, 1.5)
            for dx in (-1.65, 1.65):
                _box(specs, "a20-conservatory-potting-bench-leg", "brass", group,
                     x + dx, 0.55, z, 0.20, 1.1, 1.1)
            for pot in range(3):
                px = x - 1.2 + pot * 1.2
                _cylinder(specs, "a20-conservatory-work-pot", "honey_stone", group,
                          px, 1.48, z, 0.36, 0.48, 10, top_radius=0.45)
                _cylinder(specs, "a20-conservatory-work-plant", "foliage_light", group,
                          px, 2.05, z, 0.42, 0.85, 8, top_radius=0.10)
            valve_x = x + (2.8 if index % 2 == 0 else -2.8)
            _cylinder(specs, "a20-conservatory-irrigation-pipe", "brass", group,
                      valve_x, 0.78, z, 0.15, 1.4, 8)
            _cylinder(specs, "a20-conservatory-irrigation-valve", "verdigris_bronze", group,
                      valve_x, 1.48, z, 0.48, 0.18, 12, top_radius=0.48)
            _box(specs, "a20-conservatory-plant-label", "white_marble", group,
                 x, 1.55, z - 1.1, 0.9, 0.55, 0.10)


def _add_story_cover_cluster(specs: list[dict], *, x: float, z: float,
                             facing: str, index: int, lod: int) -> None:
    if lod == 2:
        return
    group = "a20-story-cover"
    axis_x = facing == "x"
    _box(specs, "a20-human-cover-planter", "white_marble", group,
         x, 0.62, z, 3.6 if axis_x else 1.6, 1.15, 1.6 if axis_x else 3.6)
    _box(specs, "a20-human-cover-planter-soil", "dark_wood", group,
         x, 1.22, z, 3.2 if axis_x else 1.25, 0.16, 1.25 if axis_x else 3.2)
    _cylinder(specs, "a20-human-cover-shrub", "foliage_dark", group,
              x, 2.0, z, 0.92, 1.55, 9, top_radius=0.28)
    offset = 2.7 if index % 2 == 0 else -2.7
    bx, bz = (x + offset, z) if axis_x else (x, z + offset)
    _box(specs, "a20-garden-bench-seat", "dark_wood", group,
         bx, 0.68, bz, 2.6 if axis_x else 0.72, 0.24, 0.72 if axis_x else 2.6)
    _cylinder(specs, "a20-garden-lantern-post", "brass", group,
              bx + (1.75 if axis_x else 0.0), 1.6,
              bz + (0.0 if axis_x else 1.75), 0.12, 3.0, 8)
    _box(specs, "a20-garden-lantern-light", "warm_window", group,
         bx + (1.75 if axis_x else 0.0), 3.0,
         bz + (0.0 if axis_x else 1.75), 0.48, 0.62, 0.48)


def _add_city_facade_overlays_a20(specs: list[dict], lod: int) -> None:
    """Dress the camera-facing north/west sides of inherited occupied towers.

    The r11 foundation supplies the canonical district placement.  These
    attached recesses, pilasters and planted balconies prevent its mid/far
    masses from reading as undifferentiated boxes in the locked A20 view.
    """
    buildings = (
        (-128.0, -118.0, 32.0, 30.0, 24.0),
        (-91.0, -126.0, 28.0, 24.0, 29.0),
        (-28.0, -132.0, 32.0, 22.0, 26.0),
        (37.0, -132.0, 34.0, 22.0, 31.0),
        (91.0, -124.0, 30.0, 26.0, 28.0),
        (62.0, -98.0, 20.0, 26.0, 18.0),
        (128.0, -93.0, 24.0, 34.0, 34.0),
        (130.0, -43.0, 24.0, 34.0, 25.0),
        (130.0, 47.0, 24.0, 34.0, 30.0),
        (125.0, 104.0, 30.0, 30.0, 35.0),
        (86.0, 132.0, 30.0, 22.0, 26.0),
        (44.0, 132.0, 28.0, 22.0, 30.0),
        (-44.0, 132.0, 28.0, 22.0, 27.0),
        (-92.0, 128.0, 30.0, 26.0, 33.0),
        (-128.0, 92.0, 26.0, 34.0, 28.0),
        (-130.0, 40.0, 24.0, 30.0, 31.0),
        (-130.0, -18.0, 24.0, 26.0, 24.0),
        (-126.0, -72.0, 28.0, 30.0, 32.0),
        (102.0, -18.0, 28.0, 22.0, 22.0),
        (94.0, 12.0, 26.0, 22.0, 20.0),
        (-132.0, 10.0, 22.0, 24.0, 23.0),
        (-120.0, 60.0, 28.0, 22.0, 21.0),
        (110.0, 72.0, 22.0, 26.0, 22.0),
        (-45.0, 102.0, 24.0, 20.0, 20.0),
    )
    limit = 21 if lod == 0 else 16 if lod == 1 else 6
    for index, (cx, cz, width, depth, height) in enumerate(buildings[:limit]):
        group = "a20-city-facade-kit"
        north_z = cz + depth / 2.0 + 0.24
        west_x = cx - width / 2.0 - 0.24
        level_y = min(height * 0.58, height - 5.0)
        bay_count = 4 if lod == 0 else 3 if lod == 1 else 2
        # North-facing deep window rhythm and attached pilasters.
        for bay in range(bay_count):
            ratio = (bay + 0.5) / bay_count - 0.5
            px = cx + ratio * width * 0.76
            _box(specs, "a20-city-deep-window", "dark_wood", group,
                 px, level_y - 2.3, north_z, 2.3, 3.2, 0.42)
            _beam(specs, "a20-city-window-jamb", "white_marble", group,
                  (px - 1.35, level_y - 4.1, north_z + 0.18),
                  (px - 1.35, level_y - 0.45, north_z + 0.18), 0.14, 0.14)
            _beam(specs, "a20-city-window-jamb", "white_marble", group,
                  (px + 1.35, level_y - 4.1, north_z + 0.18),
                  (px + 1.35, level_y - 0.45, north_z + 0.18), 0.14, 0.14)
        pilaster_count = 5 if lod == 0 else 3
        for pier in range(pilaster_count):
            px = cx - width * 0.40 + width * 0.80 * pier / max(1, pilaster_count - 1)
            _beam(specs, "a20-city-facade-pilaster", "verdigris_bronze", group,
                  (px, 2.0, north_z + 0.15), (px, height * 0.82, north_z + 0.15),
                  0.16, 0.18)
        _box(specs, "a20-city-planted-balcony", "white_marble", group,
             cx, level_y, north_z + 0.62, width * 0.82, 0.50, 1.55)
        _beam(specs, "a20-city-balcony-rail", "brass", group,
              (cx - width * 0.40, level_y + 1.0, north_z + 1.22),
              (cx + width * 0.40, level_y + 1.0, north_z + 1.22), 0.13, 0.12)
        # West-side belt and bays catch the oblique dual-camera view.
        _box(specs, "a20-city-west-facade-belt", "white_marble", group,
             west_x, level_y + 3.2, cz, 0.52, 0.62, depth * 0.78)
        for bay in range(3 if lod == 0 else 2):
            ratio = (bay + 0.5) / (3 if lod == 0 else 2) - 0.5
            pz = cz + ratio * depth * 0.66
            _box(specs, "a20-city-west-deep-window", "dark_wood", group,
                 west_x - 0.08, level_y - 2.0, pz, 0.42, 3.0, 2.2)
        # The opposite south/east elevations are equally authored because the
        # A20 reference-order camera looks north-west across the district.
        south_z = cz - depth / 2.0 - 0.24
        east_x = cx + width / 2.0 + 0.24
        row_heights = (6.1, level_y - 1.9) if lod == 0 else (level_y - 1.9,)
        for row, row_y in enumerate(row_heights):
            for bay in range(bay_count):
                ratio = (bay + 0.5) / bay_count - 0.5
                px = cx + ratio * width * 0.76
                _box(specs, "a20-city-south-deep-window", "dark_wood", group,
                     px, row_y, south_z, 2.35, 3.05, 0.42)
                for dx in (-1.34, 1.34):
                    _beam(specs, "a20-city-south-window-jamb", "white_marble", group,
                          (px + dx, row_y - 1.75, south_z - 0.18),
                          (px + dx, row_y + 1.75, south_z - 0.18), 0.13, 0.13)
                _beam(specs, "a20-city-south-window-hood", "brass", group,
                      (px - 1.48, row_y + 1.78, south_z - 0.30),
                      (px + 1.48, row_y + 1.78, south_z - 0.30), 0.13, 0.12)
        for pier in range(pilaster_count):
            px = cx - width * 0.40 + width * 0.80 * pier / max(1, pilaster_count - 1)
            _beam(specs, "a20-city-south-facade-pilaster", "verdigris_bronze", group,
                  (px, 1.8, south_z - 0.15), (px, height * 0.83, south_z - 0.15),
                  0.16, 0.18)
        for belt_y in (9.0, level_y + 3.2):
            _box(specs, "a20-city-south-facade-belt", "white_marble", group,
                 cx, belt_y, south_z - 0.08, width * 0.86, 0.52, 0.48)
        east_bays = 4 if lod == 0 else 2
        for row_y in row_heights:
            for bay in range(east_bays):
                ratio = (bay + 0.5) / east_bays - 0.5
                pz = cz + ratio * depth * 0.70
                _box(specs, "a20-city-east-deep-window", "dark_wood", group,
                     east_x, row_y, pz, 0.42, 3.05, 2.2)
                _beam(specs, "a20-city-east-window-hood", "brass", group,
                      (east_x + 0.22, row_y + 1.78, pz - 1.35),
                      (east_x + 0.22, row_y + 1.78, pz + 1.35), 0.13, 0.12)
        _box(specs, "a20-city-east-facade-belt", "white_marble", group,
             east_x + 0.08, level_y + 3.2, cz, 0.48, 0.55, depth * 0.80)
        if lod == 0:
            for planter in (-0.28, 0.28):
                px = cx + planter * width
                _box(specs, "a20-city-balcony-planter", "honey_stone", group,
                     px, level_y + 0.62, north_z + 1.10, 2.8, 0.48, 0.72)
                _cylinder(specs, "a20-city-balcony-plant", "foliage_light", group,
                          px, level_y + 1.55, north_z + 1.10,
                          0.72, 1.5, 8, top_radius=0.18)


def _add_composition_layers_a20(specs: list[dict], lod: int) -> None:
    """Near/mid/far framing that keeps the canonical cross roads readable."""
    cam_x, _, cam_z = MAIN_REFERENCE_CAMERA["location"]
    target_x, _, target_z = MAIN_REFERENCE_CAMERA["target"]
    forward_x, forward_z = target_x - cam_x, target_z - cam_z
    forward_length = math.hypot(forward_x, forward_z)
    forward_x, forward_z = forward_x / forward_length, forward_z / forward_length
    right_x, right_z = -forward_z, forward_x

    def view_point(distance: float, offset: float, y: float) -> tuple[float, float, float]:
        return (
            cam_x + forward_x * distance + right_x * offset,
            y,
            cam_z + forward_z * distance + right_z * offset,
        )

    # Near-camera side frames; centre remains open for the 1.65 m sightline.
    group = "a20-composition"
    left_frame = view_point(11.0, -18.0, 0.0)
    right_frame = view_point(11.0, 18.0, 0.0)
    near_frames = (
        (left_frame[0], left_frame[2], 16.0, "left"),
        (right_frame[0], right_frame[2], 16.0, "right"),
    )
    for x, z, width, side in near_frames:
        post_count = 5 if lod == 0 else 3
        for post in range(post_count):
            px = x - width / 2.0 + width * post / max(1, post_count - 1)
            _cylinder(specs, "a20-near-pergola-post", "dark_wood", group,
                      px, 3.3, z, 0.28, 6.4, 8, top_radius=0.24)
        _beam(specs, "a20-near-pergola-header", "dark_wood", group,
              (x - width / 2.0, 6.35, z), (x + width / 2.0, 6.35, z), 0.28, 0.28)
        slat_count = 8 if lod == 0 else 4
        for slat in range(slat_count):
            px = x - width * 0.45 + width * 0.9 * slat / max(1, slat_count - 1)
            _beam(specs, "a20-near-pergola-slat", "verdigris_bronze", group,
                  (px, 6.45, z - 2.4), (px, 6.45, z + 2.4), 0.10, 0.12)
        _box(specs, "a20-near-terrace-wall", "wet_stone", group,
             x, 0.75, z + (3.2 if side == "left" else -3.2), width + 4.0, 1.35, 1.2)
        # A roofed edge pavilion converts each pergola into real near-camera
        # architecture and keeps the central water axis open.
        _box(specs, "a20-near-corridor-pavilion-base", "honey_stone", group,
             x, 0.45, z, width + 1.4, 0.85, 7.2)
        for px in (x - width * 0.42, x + width * 0.42):
            for pz in (z - 2.7, z + 2.7):
                _cylinder(specs, "a20-near-corridor-pavilion-column", "white_marble", group,
                          px, 4.0, pz, 0.34, 7.2, 10, top_radius=0.29)
        _deep_roof(specs, cx=x, base_y=7.45, cz=z, width=width + 2.0, depth=7.8,
                   height=3.2, axis="x", group=group,
                   role="a20-near-corridor-pavilion-roof", lod=lod)

    # The main proof now looks down a shallow reflective garden rill rather
    # than across an empty white slab.  Three real stepping bridges preserve
    # cross-circulation and build strong near/mid/far leading lines.
    rill_start, rill_end, rill_half = 7.0, 88.0, 4.3
    _panel(specs, "a20-reference-corridor-water", "water", group,
           (
               view_point(rill_start, -rill_half, 0.12),
               view_point(rill_start, rill_half, 0.12),
               view_point(rill_end, rill_half, 0.12),
               view_point(rill_end, -rill_half, 0.12),
           ), 0.10)
    for offset in (-rill_half - 0.28, rill_half + 0.28):
        _beam(specs, "a20-reference-corridor-coping", "white_marble", group,
              view_point(rill_start, offset, 0.34),
              view_point(rill_end, offset, 0.34), 0.24, 0.22)
    for bridge_index, distance in enumerate((22.0, 51.0, 78.0)):
        half_depth = 2.2 if bridge_index == 1 else 1.65
        corners = (
            view_point(distance - half_depth, -6.2, 0.48),
            view_point(distance - half_depth, 6.2, 0.48),
            view_point(distance + half_depth, 6.2, 0.48),
            view_point(distance + half_depth, -6.2, 0.48),
        )
        _panel(specs, "a20-reference-corridor-bridge", "honey_stone", group,
               corners, 0.38)
        for offset in (-5.85, 5.85):
            _beam(specs, "a20-reference-corridor-bridge-rail", "brass", group,
                  view_point(distance - half_depth, offset, 1.28),
                  view_point(distance + half_depth, offset, 1.28), 0.14, 0.12)
            _cylinder(specs, "a20-reference-corridor-bridge-post", "white_marble", group,
                      *view_point(distance, offset, 0.72),
                      0.24, 1.15, 8, top_radius=0.20)

    # Midground cover rhythm and occupied irrigation story; positions stay out
    # of the two 16 m primary road corridors and all canonical approaches.
    clusters = (
        (-28.0, -18.0, "x"), (28.0, 18.0, "x"),
        (-18.0, 28.0, "z"), (18.0, -28.0, "z"),
        (-104.0, -18.0, "x"), (100.0, 20.0, "x"),
        (-20.0, -104.0, "z"), (20.0, 110.0, "z"),
    )
    for index, (x, z, facing) in enumerate(clusters[:8 if lod == 0 else 6 if lod == 1 else 0]):
        _add_story_cover_cluster(specs, x=x, z=z, facing=facing, index=index, lod=lod)

    _add_city_facade_overlays_a20(specs, lod)

    # Dense near-camera garden banks give the player-height proof a readable
    # foreground edge without narrowing either canonical road corridor.
    left_bank = view_point(22.0, -15.0, 0.0)
    right_bank = view_point(24.0, 15.0, 0.0)
    near_banks = (
        (left_bank[0], left_bank[2], 15.0),
        (right_bank[0], right_bank[2], 13.0),
    )
    for x, z, width in near_banks:
        _box(specs, "a20-near-botanical-bank", "honey_stone", group,
             x, 0.58, z, width, 1.05, 3.4)
        _box(specs, "a20-near-botanical-soil", "dark_wood", group,
             x, 1.12, z, width - 0.8, 0.18, 2.7)
        plant_count = 7 if lod == 0 else 4 if lod == 1 else 2
        for plant in range(plant_count):
            px = x - width * 0.40 + width * 0.80 * plant / max(1, plant_count - 1)
            height = 1.8 + 0.55 * ((plant + int(abs(x))) % 3)
            _cylinder(specs, "a20-near-botanical-plant",
                      "foliage_light" if plant % 2 else "foliage_dark", group,
                      px, 1.15 + height / 2.0, z,
                      0.72, height, 8, top_radius=0.16)
            if lod == 0:
                _ellipsoid(
                    specs, "a20-near-botanical-leaf-mass",
                    "foliage_light" if plant % 2 else "foliage_dark", group,
                    px + (0.35 if plant % 2 else -0.35),
                    2.15 + height * 0.42, z,
                    1.0, 0.72, 0.82, 9, 5,
                )

    # Low, irregular garden courts fill the side quadrants while the 16 m
    # roads, landmark approaches and firing lanes remain visually explicit.
    garden_courts = (
        (-82.0, 35.0, 12.0, 8.0), (-59.0, 57.0, 14.0, 9.0),
        (-35.0, 24.0, 11.0, 8.0), (-24.0, 49.0, 13.0, 10.0),
        (27.0, -24.0, 12.0, 9.0), (35.0, 32.0, 14.0, 8.0),
        (78.0, -34.0, 13.0, 9.0), (82.0, 34.0, 11.0, 8.0),
    )
    court_limit = 8 if lod == 0 else 6 if lod == 1 else 3
    for court_index, (x, z, width, depth) in enumerate(garden_courts[:court_limit]):
        _box(specs, "a20-layered-garden-court", "honey_stone", group,
             x, 0.52, z, width, 0.95, depth)
        _box(specs, "a20-layered-garden-court-soil", "dark_wood", group,
             x, 1.02, z, width - 0.8, 0.16, depth - 0.8)
        plant_count = 5 if lod == 0 else 3
        for plant in range(plant_count):
            px = x - width * 0.34 + width * 0.68 * plant / max(1, plant_count - 1)
            pz = z + (-1.3 if (plant + court_index) % 2 else 1.3)
            height = 1.8 + 0.7 * ((plant + court_index) % 3)
            _cylinder(specs, "a20-layered-garden-court-plant",
                      "foliage_light" if plant % 2 else "foliage_dark", group,
                      px, 1.08 + height / 2.0, pz,
                      0.72, height, 8, top_radius=0.15)
            if lod == 0:
                _ellipsoid(
                    specs, "a20-layered-garden-court-leaf-mass",
                    "foliage_light" if plant % 2 else "foliage_dark", group,
                    px, 1.9 + height * 0.38, pz,
                    0.92, 0.64, 0.80, 9, 5,
                )

    # A small arched midground bridge, framed stair and canal service cart.
    _box(specs, "a20-midground-bridge-deck", "white_marble", group,
         -18.0, 1.20, -16.0, 13.0, 1.0, 5.0)
    for side in (-1.0, 1.0):
        _beam(specs, "a20-midground-bridge-parapet", "white_marble", group,
              (-24.0, 1.75, -16.0 + side * 2.1),
              (-12.0, 1.75, -16.0 + side * 2.1), 0.20, 0.22)
    if lod == 0:
        _box(specs, "a20-irrigation-service-cart", "dark_wood", group,
             -10.0, 0.75, -22.0, 2.8, 1.2, 1.5)
        for x in (-11.0, -9.0):
            _cylinder(specs, "a20-irrigation-service-cart-wheel", "brass", group,
                      x, 0.43, -22.85, 0.42, 0.18, 12, top_radius=0.42)

    # Far skyline crowns turn the inherited cuboids into a layered garden-city
    # horizon.  These remain real geometry and do not touch collision truth.
    skyline = (
        (-132.0, -128.0, 22.0, 31.0), (-92.0, -136.0, 18.0, 28.0),
        (-36.0, -138.0, 20.0, 34.0), (38.0, -136.0, 20.0, 31.0),
        (96.0, -132.0, 18.0, 27.0), (132.0, -112.0, 20.0, 33.0),
        (-136.0, 118.0, 20.0, 30.0), (-92.0, 136.0, 18.0, 27.0),
        (92.0, 136.0, 18.0, 29.0), (136.0, 108.0, 20.0, 32.0),
    )
    skyline_limit = 10 if lod == 0 else 8 if lod == 1 else 5
    for index, (x, z, width, height) in enumerate(skyline[:skyline_limit]):
        _box(specs, "a20-far-occupied-tower", "honey_stone" if index % 2 else "white_marble",
             group, x, height / 2.0, z, width, height, 16.0)
        _deep_roof(specs, cx=x, base_y=height, cz=z, width=width, depth=16.0,
                   height=4.0 + (index % 3), axis="x", group=group,
                   role="a20-far-layered-roof", lod=lod)
        if lod <= 1:
            _cylinder(specs, "a20-far-roof-lantern", "verdigris_bronze", group,
                      x, height + 5.7, z, 1.7, 3.2, 10, top_radius=1.05)


def build_specs(lod: int = 0) -> list[dict]:
    """Return deterministic A20 specs without importing Blender."""
    if lod not in (0, 1, 2):
        raise ValueError(f"unsupported LOD: {lod}")
    # Reuse only r11's canonical garden-city foundation.  Both r11 landmark
    # groups and the flat warm-window cards are removed, never mutated.
    specs = [
        copy.deepcopy(spec)
        for spec in R11.build_specs(lod)
        if spec["group"] not in {PALACE_ID, CONSERVATORY_ID}
        and spec["material"] != "warm_window"
    ]
    _add_palace_a20(specs, lod)
    _add_conservatory_a20(specs, lod)
    _add_composition_layers_a20(specs, lod)

    if lod == 2:
        # Keep only silhouette-bearing inherited city layers in HLOD.  Hero
        # glass shells, crown petals, water and principal bridges remain.
        inherited_drop = {
            "garden-flower", "garden-bench-seat", "garden-bench-leg",
            "garden-lantern-post", "garden-lantern-light",
            "civic-ground-arcade-column", "civic-ground-arcade-arch-rib",
            "foreground-arcade-column", "foreground-arcade-arch-rib",
            "canal-bridge-arched-parapet",
            "a20-conservatory-upper-walk-rail-post",
            "a20-conservatory-rear-crosswalk-rail-post",
            "a20-conservatory-flowering-understory",
            "a20-conservatory-hanging-chain",
            "a20-conservatory-hanging-pot",
            "a20-conservatory-hanging-foliage",
            "a20-conservatory-irrigation-mist",
            "a20-conservatory-destination-arcade-column",
            "a20-conservatory-destination-arcade-arch-rib",
            "a20-palace-terrace-balustrade-post",
            "a20-palace-window-stone-frame",
            "a20-palace-lower-crown-frame",
            "a20-palace-gate-upper-frame",
            "a20-reference-corridor-bridge-post",
            "a20-reference-corridor-bridge-rail",
            "a20-layered-garden-court-plant",
        }
        lod2_prefix_drop = ("a20-city-", "a20-near-")
        specs = [
            spec for spec in specs
            if spec["role"] not in inherited_drop
            and not spec["role"].startswith(lod2_prefix_drop)
        ]
    return specs


def emit_specs_to_builder(builder, specs: Iterable[dict],
                          material_map: Mapping[str, str] | None = None) -> list[dict]:
    specs = list(specs)
    mapping = DEFAULT_INTEGRATION_MATERIAL_MAP if material_map is None else material_map
    for spec in specs:
        key = mapping.get(spec["material"], spec["material"])
        if spec["kind"] == "box":
            builder.add_box(spec["x"], spec["y"], spec["z"],
                            spec["w"], spec["h"], spec["d"], key)
        elif spec["kind"] == "beam":
            builder.add_beam(spec["start"], spec["end"],
                             spec["width"], spec["depth"], key)
        elif spec["kind"] == "cylinder":
            builder.add_cylinder(
                spec["x"], spec["y"], spec["z"], spec["radius"],
                spec["height"], key, spec["segments"], spec["topRadius"],
            )
        elif spec["kind"] == "panel":
            if hasattr(builder, "add_surface_panel"):
                builder.add_surface_panel(spec["corners"], spec["thickness"], key)
            else:
                builder.add_sloped_panel(spec["corners"], spec["thickness"], key)
        elif spec["kind"] == "ellipsoid":
            builder.add_ellipsoid(
                spec["x"], spec["y"], spec["z"],
                spec["radiusX"], spec["radiusY"], spec["radiusZ"],
                key, spec["segments"], spec["rings"],
            )
        else:
            raise ValueError(f"unsupported spec kind: {spec['kind']}")
    return specs


def emit_to_builder(builder, lod: int = 0,
                    material_map: Mapping[str, str] | None = None) -> list[dict]:
    return emit_specs_to_builder(builder, build_specs(lod), material_map)


def spec_bounds(spec: Mapping[str, object]) -> tuple[float, float, float, float, float, float]:
    if spec["kind"] == "ellipsoid":
        return (
            float(spec["x"]) - float(spec["radiusX"]),
            float(spec["y"]) - float(spec["radiusY"]),
            float(spec["z"]) - float(spec["radiusZ"]),
            float(spec["x"]) + float(spec["radiusX"]),
            float(spec["y"]) + float(spec["radiusY"]),
            float(spec["z"]) + float(spec["radiusZ"]),
        )
    return R11.spec_bounds(dict(spec))


def estimated_triangles(specs: Sequence[Mapping[str, object]]) -> int:
    total = 0
    for spec in specs:
        if spec["kind"] == "cylinder":
            total += int(spec["segments"]) * 4
        elif spec["kind"] == "ellipsoid":
            total += int(spec["segments"]) * 2 * (int(spec["rings"]) - 1)
        else:
            total += 12
    return total


def _camera_basis(camera: Mapping[str, object]) -> tuple[tuple[float, float, float], ...]:
    location = tuple(float(value) for value in camera["location"])
    target = tuple(float(value) for value in camera["target"])

    def sub(a, b):
        return tuple(a[index] - b[index] for index in range(3))

    def dot(a, b):
        return sum(a[index] * b[index] for index in range(3))

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    def unit(value):
        length = math.sqrt(dot(value, value))
        return tuple(component / length for component in value)

    forward = unit(sub(target, location))
    right = unit(cross(forward, (0.0, 1.0, 0.0)))
    up = unit(cross(right, forward))
    return location, forward, right, up


def reference_camera_frame_metrics(lod: int = 0,
                                   aspect: float = 16.0 / 9.0) -> dict:
    camera = MAIN_REFERENCE_CAMERA
    location, forward, right, up = _camera_basis(camera)

    def sub(a, b):
        return tuple(a[index] - b[index] for index in range(3))

    def dot(a, b):
        return sum(a[index] * b[index] for index in range(3))

    tan_half_x = float(camera["sensorWidthMm"]) / (2.0 * float(camera["lensMm"]))
    tan_half_y = tan_half_x / aspect
    specs = build_specs(lod)
    heroes = []
    for landmark in LANDMARKS:
        points = []
        for spec in specs:
            if spec["group"] != landmark["id"]:
                continue
            min_x, min_y, min_z, max_x, max_y, max_z = spec_bounds(spec)
            points.extend(
                (x, y, z)
                for x in (min_x, max_x)
                for y in (min_y, max_y)
                for z in (min_z, max_z)
            )
        projected = []
        for point in points:
            relative = sub(point, location)
            depth = dot(relative, forward)
            if depth <= 0.01:
                continue
            projected.append((
                0.5 + dot(relative, right) / depth / (2.0 * tan_half_x),
                0.5 + dot(relative, up) / depth / (2.0 * tan_half_y),
            ))
        xs = [point[0] for point in projected]
        ys = [point[1] for point in projected]
        visible_x_min = max(0.0, min(xs))
        visible_x_max = min(1.0, max(xs))
        visible_y_min = max(0.0, min(ys))
        visible_y_max = min(1.0, max(ys))
        heroes.append({
            "id": landmark["id"],
            "rawFrameBounds": (min(xs), min(ys), max(xs), max(ys)),
            "visibleFrameBounds": (visible_x_min, visible_y_min, visible_x_max, visible_y_max),
            "visibleFrameHeightRatio": max(0.0, visible_y_max - visible_y_min),
            "visibleFrameWidthRatio": max(0.0, visible_x_max - visible_x_min),
        })
    return {
        "camera": copy.deepcopy(camera),
        "heroes": heroes,
        # The wide 1.65 m corridor deliberately keeps both complete hero
        # silhouettes instead of cropping one landmark for a larger metric.
        "passed": (
            heroes[0]["visibleFrameHeightRatio"] >= 0.26
            and heroes[1]["visibleFrameHeightRatio"] >= 0.32
            and all(hero["visibleFrameWidthRatio"] >= 0.34 for hero in heroes)
        ),
    }


def plan_metrics(lod: int) -> dict:
    specs = build_specs(lod)
    bounds = [spec_bounds(spec) for spec in specs]
    return {
        "lod": lod,
        "specCount": len(specs),
        "estimatedTriangles": estimated_triangles(specs),
        "materials": sorted({spec["material"] for spec in specs}),
        "kindCounts": dict(sorted(Counter(spec["kind"] for spec in specs).items())),
        "roleCounts": dict(sorted(Counter(spec["role"] for spec in specs).items())),
        "bounds": {
            "minX": min(item[0] for item in bounds),
            "minY": min(item[1] for item in bounds),
            "minZ": min(item[2] for item in bounds),
            "maxX": max(item[3] for item in bounds),
            "maxY": max(item[4] for item in bounds),
            "maxZ": max(item[5] for item in bounds),
        },
    }


PRODUCER_PROVISIONAL_SCORES = {
    "composition": 6.7,
    "hero silhouettes": 7.0,
    "architectural grammar": 6.8,
    "human scale": 6.7,
    "material realism": 6.5,
    "near/mid/far density": 6.8,
    "gameplay readability": 7.7,
    "props and environmental storytelling": 6.8,
    "lighting and atmosphere": 6.6,
    "reference identity": 6.9,
}


def producer_provisional_scorecard(evidence_paths: Sequence[str] = ()) -> dict:
    scores = [
        {"category": category, "score": PRODUCER_PROVISIONAL_SCORES[category]}
        for category in FIXED_SCORE_CATEGORIES
    ]
    return {
        "schemaVersion": 1,
        "audit": "hibana-producer-provisional-reference-art-scorecard-v1",
        "stageId": STAGE_ID,
        "candidate": KIT_VERSION,
        "reviewer": "producer-self-review-only",
        "reference": {
            "path": str(REFERENCE_PATH),
            "sha256": REFERENCE_SHA256,
            "inspectedAtOriginalResolution": True,
        },
        "eyeHeightM": PLAYER_EYE_M,
        "evidencePaths": list(evidence_paths),
        "scores": scores,
        "minimumScore": min(item["score"] for item in scores),
        "averageScore": round(sum(item["score"] for item in scores) / len(scores), 2),
        "strongestRemainingVisualMismatch": (
            "A20 materially rebuilds the two r11 blockouts and the locked composition, "
            "but only a different reviewer may decide whether the rendered stone, glass, "
            "foliage and occupied depth reach the ImageGen target at original size."
        ),
        "referencePassClaimed": False,
        "verdict": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
    }


def _load_canonical_stage(path: Path) -> Mapping[str, object]:
    data = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    stages = data if isinstance(data, list) else data.get("stages", [])
    return next(stage for stage in stages if stage.get("id") == STAGE_ID)


def canonical_contract_report(layout_path: Path = CANONICAL_LAYOUT_DEFAULT) -> dict:
    stage = _load_canonical_stage(layout_path)
    def normalized(value):
        if isinstance(value, Mapping):
            return {key: normalized(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalized(item) for item in value]
        return value

    expected_landmarks = [
        {
            key: landmark[key]
            for key in ("id", "cx", "cz", "width", "depth", "height", "entrance", "approach")
        }
        for landmark in LANDMARKS
    ]
    actual_landmarks = [
        {
            key: landmark[key]
            for key in ("id", "cx", "cz", "width", "depth", "height", "entrance", "approach")
        }
        for landmark in stage["landmarkPlacements"]
    ]
    return {
        "mapSizeMatches": float(stage["size"]) == MAP_SIZE_M,
        "playerSpawnsMatch": tuple(tuple(float(v) for v in p) for p in stage["playerSpawns"]) == CANONICAL_PLAYER_SPAWNS,
        "botSpawnsMatch": tuple(tuple(float(v) for v in p) for p in stage["botSpawns"]) == CANONICAL_BOT_SPAWNS,
        "landmarksMatch": normalized(actual_landmarks) == normalized(expected_landmarks),
        "exactLandmarkCount": len(actual_landmarks),
        "allMatched": (
            float(stage["size"]) == MAP_SIZE_M
            and tuple(tuple(float(v) for v in p) for p in stage["playerSpawns"]) == CANONICAL_PLAYER_SPAWNS
            and tuple(tuple(float(v) for v in p) for p in stage["botSpawns"]) == CANONICAL_BOT_SPAWNS
            and normalized(actual_landmarks) == normalized(expected_landmarks)
            and len(actual_landmarks) == 2
        ),
    }


class A20MeshBuilder(R11.PrototypeMeshBuilder):
    """Material-batched private proof builder with A20 provenance names."""

    def add_ellipsoid(self, x, y, z, radius_x, radius_y, radius_z,
                      key="foliage_dark", segments=10, rings=6):
        part = self._part(key)
        base = len(part["verts"])
        # North pole, intermediate latitude rings, south pole.  Runtime Y is
        # up and is converted through the same handedness as every other part.
        part["verts"].append(self._rv((x, y + radius_y, z)))
        for ring in range(1, rings):
            phi = math.pi * ring / rings
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            for segment in range(segments):
                theta = math.tau * segment / segments
                part["verts"].append(self._rv((
                    x + radius_x * sin_phi * math.cos(theta),
                    y + radius_y * cos_phi,
                    z + radius_z * sin_phi * math.sin(theta),
                )))
        south = len(part["verts"])
        part["verts"].append(self._rv((x, y - radius_y, z)))
        first_ring = base + 1
        for segment in range(segments):
            nxt = (segment + 1) % segments
            part["faces"].append((base, first_ring + segment, first_ring + nxt))
        for ring in range(rings - 2):
            lower = first_ring + ring * segments
            upper = lower + segments
            for segment in range(segments):
                nxt = (segment + 1) % segments
                part["faces"].append((
                    lower + segment, upper + segment,
                    upper + nxt, lower + nxt,
                ))
        last_ring = first_ring + (rings - 2) * segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            part["faces"].append((south, last_ring + nxt, last_ring + segment))

    def flush(self):
        import bpy  # type: ignore

        objects = []
        for key, part in sorted(self.parts.items()):
            mesh = bpy.data.meshes.new(f"HB_NAKANIWA_A20_{key}_MESH")
            mesh.from_pydata(part["verts"], [], part["faces"])
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new(f"HB_NAKANIWA_A20_{key}", mesh)
            self.collection.objects.link(obj)
            obj.data.materials.append(self.materials[key])
            obj["hibanaStageId"] = STAGE_ID
            obj["hibanaKitVersion"] = KIT_VERSION
            obj["hibanaMaterialRole"] = key
            if key in {
                "wet_stone", "honey_stone", "white_marble", "dark_wood",
                "brass", "verdigris_bronze",
            }:
                bevel = obj.modifiers.new("HB_A20_CONTACT_BEVEL", "BEVEL")
                bevel.width = 0.065 if key in {"wet_stone", "honey_stone", "white_marble"} else 0.035
                bevel.segments = 2
                bevel.limit_method = "ANGLE"
                bevel.angle_limit = math.radians(22.0)
            objects.append(obj)
        return objects


def _make_blender_materials():
    import bpy  # type: ignore

    materials = {}
    for role, recipe in MATERIALS.items():
        material = bpy.data.materials.new(f"MAT_Nakaniwa_A20_{role}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        texcoord = nodes.new("ShaderNodeTexCoord")
        noise = nodes.new("ShaderNodeTexNoise")
        ramp = nodes.new("ShaderNodeValToRGB")
        roughness = nodes.new("ShaderNodeMapRange")
        bump = nodes.new("ShaderNodeBump")

        base = recipe["color"]
        rough_min, rough_max = recipe["roughness"]
        noise.inputs["Scale"].default_value = recipe.get("noiseScale", 6.0)
        noise.inputs["Detail"].default_value = 4.0
        noise.inputs["Roughness"].default_value = 0.72
        ramp.color_ramp.elements[0].position = 0.24
        ramp.color_ramp.elements[1].position = 0.78
        ramp.color_ramp.elements[0].color = tuple(max(0.0, value * 0.62) for value in base[:3]) + (base[3],)
        ramp.color_ramp.elements[1].color = tuple(min(1.0, value * 1.24 + 0.018) for value in base[:3]) + (base[3],)
        roughness.inputs["To Min"].default_value = rough_min
        roughness.inputs["To Max"].default_value = rough_max
        bump.inputs["Strength"].default_value = recipe.get("bump", 0.0)
        bump.inputs["Distance"].default_value = 0.11 if "stone" in role or "marble" in role else 0.045
        shader.inputs["Metallic"].default_value = recipe.get("metallic", 0.0)
        transmission = shader.inputs.get("Transmission Weight") or shader.inputs.get("Transmission")
        if transmission is not None:
            transmission.default_value = recipe.get("transmission", 0.0)
        if shader.inputs.get("IOR") is not None:
            shader.inputs["IOR"].default_value = recipe.get("ior", 1.45)
        if shader.inputs.get("Alpha") is not None:
            shader.inputs["Alpha"].default_value = recipe.get("alpha", base[3])
        subsurface = shader.inputs.get("Subsurface Weight") or shader.inputs.get("Subsurface")
        if subsurface is not None:
            subsurface.default_value = recipe.get("subsurface", 0.0)
        emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if emission is not None and recipe.get("emission"):
            emission.default_value = recipe["emission"]
            if shader.inputs.get("Emission Strength") is not None:
                shader.inputs["Emission Strength"].default_value = recipe.get("emissionStrength", 0.4)
        # All parts sharing a material are intentionally batched into one mesh.
        # Generated coordinates would normalize across the full 320 m scene
        # and turn stone noise into fifty-metre stains; object coordinates keep
        # the authored roughness and relief at human-readable scale.
        links.new(texcoord.outputs["Object"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        if role in {"wet_stone", "honey_stone", "white_marble", "dark_wood"}:
            separate = nodes.new("ShaderNodeSeparateXYZ")
            contact = nodes.new("ShaderNodeMapRange")
            contact.clamp = True
            contact.inputs["From Min"].default_value = 0.0
            contact.inputs["From Max"].default_value = 5.5
            contact.inputs["To Min"].default_value = 0.34 if role != "white_marble" else 0.48
            contact.inputs["To Max"].default_value = 1.0
            multiply = nodes.new("ShaderNodeMixRGB")
            multiply.blend_type = "MULTIPLY"
            multiply.inputs["Fac"].default_value = 1.0
            links.new(texcoord.outputs["Object"], separate.inputs["Vector"])
            # Blender Z is runtime Y-up in the deterministic mesh builder.
            links.new(separate.outputs["Z"], contact.inputs["Value"])
            links.new(ramp.outputs["Color"], multiply.inputs[1])
            links.new(contact.outputs["Result"], multiply.inputs[2])
            if role in {"wet_stone", "honey_stone", "white_marble"}:
                joints = nodes.new("ShaderNodeTexVoronoi")
                joints.feature = "DISTANCE_TO_EDGE"
                joints.distance = "EUCLIDEAN"
                joints.inputs["Scale"].default_value = {
                    "wet_stone": 0.78,
                    "honey_stone": 0.92,
                    "white_marble": 1.10,
                }[role]
                joint_ramp = nodes.new("ShaderNodeValToRGB")
                joint_ramp.color_ramp.elements[0].position = 0.008
                joint_ramp.color_ramp.elements[0].color = (0.58, 0.55, 0.50, 1.0)
                joint_ramp.color_ramp.elements[1].position = 0.042
                joint_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
                joint_ramp.color_ramp.elements.new(0.021).color = (0.82, 0.80, 0.76, 1.0)
                weathered = nodes.new("ShaderNodeMixRGB")
                weathered.blend_type = "MULTIPLY"
                weathered.inputs["Fac"].default_value = 0.38
                links.new(texcoord.outputs["Object"], joints.inputs["Vector"])
                links.new(joints.outputs["Distance"], joint_ramp.inputs["Fac"])
                links.new(multiply.outputs["Color"], weathered.inputs[1])
                links.new(joint_ramp.outputs["Color"], weathered.inputs[2])
                links.new(weathered.outputs["Color"], shader.inputs["Base Color"])
            else:
                links.new(multiply.outputs["Color"], shader.inputs["Base Color"])
        else:
            links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
        links.new(noise.outputs["Fac"], roughness.inputs["Value"])
        links.new(roughness.outputs["Result"], shader.inputs["Roughness"])
        if recipe.get("bump", 0.0) > 0.0:
            links.new(noise.outputs["Fac"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        material.diffuse_color = base
        material["a20RequiredChannels"] = "baseColor,roughness,normalOrBump"
        if recipe.get("alpha", base[3]) < 1.0:
            try:
                material.surface_render_method = "DITHERED"
            except Exception:
                try:
                    material.blend_method = "BLEND"
                except Exception:
                    pass
            if hasattr(material, "use_transparency_overlap"):
                material.use_transparency_overlap = False
        materials[role] = material
    return materials


def _runtime_to_blender(point: Sequence[float]):
    from mathutils import Vector  # type: ignore
    # PrototypeMeshBuilder._rv maps runtime X/Y-up/Z-plan directly to Blender
    # X/Y-plan/Z-up.  Cameras and lights must use the identical handedness.
    return Vector((float(point[0]), float(point[2]), float(point[1])))


def _make_camera(collection, spec: Mapping[str, object]):
    import bpy  # type: ignore

    data = bpy.data.cameras.new(str(spec["name"]) + "_DATA")
    data.lens = float(spec["lensMm"])
    data.sensor_width = float(spec["sensorWidthMm"])
    data.dof.use_dof = False
    camera = bpy.data.objects.new(str(spec["name"]), data)
    collection.objects.link(camera)
    camera.location = _runtime_to_blender(spec["location"])
    direction = _runtime_to_blender(spec["target"]) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera["a20EyeHeightM"] = float(spec["eyeHeightM"])
    camera["a20Intent"] = str(spec["intent"])
    return camera


def build_private_proof(output_dir: Path = PRIVATE_PROOF_DEFAULT,
                        layout_path: Path = CANONICAL_LAYOUT_DEFAULT,
                        lod: int = 0,
                        view_indices: Sequence[int] | None = None) -> dict:
    import bpy  # type: ignore

    output_dir = output_dir.expanduser().resolve()
    approved = PRIVATE_PROOF_DEFAULT.resolve()
    if output_dir != approved and approved not in output_dir.parents:
        raise ValueError(f"A20 proof output must stay below {approved}: {output_dir}")
    if str(output_dir).startswith(str(REPO_ROOT.resolve())):
        raise ValueError("A20 proof output must stay outside the repository")
    views_dir = output_dir / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    if view_indices is None:
        # A full deterministic proof supersedes private iteration frames.  The
        # directory is already constrained below PRIVATE_PROOF_DEFAULT.
        for stale_view in views_dir.iterdir():
            if stale_view.is_file() and stale_view.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                stale_view.unlink()

    contract = canonical_contract_report(layout_path)
    if not contract["allMatched"]:
        raise RuntimeError(f"canonical Nakaniwa contract drift: {contract}")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except (TypeError, ValueError):
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.48

    root = bpy.data.collections.new(TARGET_COLLECTION)
    scene.collection.children.link(root)
    geometry = bpy.data.collections.new("HB_NAKANIWA_A20_GEOMETRY")
    cameras = bpy.data.collections.new("HB_NAKANIWA_A20_CAMERAS")
    lighting = bpy.data.collections.new("HB_NAKANIWA_A20_LIGHTING")
    root.children.link(geometry)
    root.children.link(cameras)
    root.children.link(lighting)

    materials = _make_blender_materials()
    builder = A20MeshBuilder(geometry, materials)
    specs = emit_to_builder(builder, lod, {key: key for key in MATERIALS})
    objects = builder.flush()
    authored_vertices = sum(len(obj.data.vertices) for obj in objects)
    authored_polygons = sum(len(obj.data.polygons) for obj in objects)
    authored_triangles = sum(
        max(1, len(polygon.vertices) - 2)
        for obj in objects for polygon in obj.data.polygons
    )

    world = scene.world or bpy.data.worlds.new("HB_NAKANIWA_A20_WORLD")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    sky = nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "NISHITA"
    except TypeError:
        sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(18.0)
    sky.sun_rotation = math.radians(228.0)
    sky.air_density = 1.15
    if hasattr(sky, "dust_density"):
        sky.dust_density = 3.8
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.105
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(sky.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])

    sun_data = bpy.data.lights.new("LGT_Nakaniwa_A20_Sun_DATA", "SUN")
    sun_data.energy = 4.2
    sun_data.angle = math.radians(0.72)
    sun_data.color = (1.0, 0.56, 0.29)
    sun = bpy.data.objects.new("LGT_Nakaniwa_A20_Sun", sun_data)
    lighting.objects.link(sun)
    sun.location = _runtime_to_blender((118.0, 96.0, -138.0))
    sun.rotation_euler = (
        _runtime_to_blender((-10.0, 8.0, -4.0)) - sun.location
    ).to_track_quat("-Z", "Y").to_euler()

    fill_data = bpy.data.lights.new("LGT_Nakaniwa_A20_CoolFill_DATA", "AREA")
    fill_data.energy = 115.0
    fill_data.shape = "DISK"
    fill_data.size = 105.0
    fill_data.color = (0.18, 0.30, 0.48)
    fill = bpy.data.objects.new("LGT_Nakaniwa_A20_CoolFill", fill_data)
    lighting.objects.link(fill)
    fill.location = _runtime_to_blender((-30.0, 96.0, 20.0))
    fill.rotation_euler = (
        _runtime_to_blender((-4.0, 8.0, -3.0)) - fill.location
    ).to_track_quat("-Z", "Y").to_euler()

    rim_data = bpy.data.lights.new("LGT_Nakaniwa_A20_GlassRim_DATA", "AREA")
    rim_data.energy = 185.0
    rim_data.shape = "RECTANGLE"
    rim_data.size = 68.0
    rim_data.color = (0.32, 0.50, 0.70)
    rim = bpy.data.objects.new("LGT_Nakaniwa_A20_GlassRim", rim_data)
    lighting.objects.link(rim)
    rim.location = _runtime_to_blender((92.0, 54.0, 98.0))
    rim.rotation_euler = (
        _runtime_to_blender((52.0, 12.0, 61.8)) - rim.location
    ).to_track_quat("-Z", "Y").to_euler()

    # Warm pools are actual low-radius practical light, not a wall of
    # emissive cards.  They reveal palace thresholds, conservatory plants and
    # wet stone contacts while leaving the navigation silhouette crisp.
    practicals = (
        ("PalaceGate", (-60.0, 5.5, -31.5), 520.0, 8.0),
        ("PalaceCrown", (-60.0, 31.5, -52.0), 690.0, 10.0),
        ("ConservatoryEntry", (52.0, 5.5, 31.0), 540.0, 9.0),
        ("ConservatoryNave", (52.0, 8.0, 64.0), 760.0, 12.0),
        ("ConservatoryDestination", (52.0, 8.0, 88.0), 620.0, 9.0),
    )
    for name, location, energy, radius in practicals:
        light_data = bpy.data.lights.new(f"LGT_Nakaniwa_A20_{name}_DATA", "POINT")
        light_data.energy = energy
        light_data.color = (1.0, 0.24, 0.055)
        light_data.shadow_soft_size = radius
        light = bpy.data.objects.new(f"LGT_Nakaniwa_A20_{name}", light_data)
        lighting.objects.link(light)
        light.location = _runtime_to_blender(location)

    selected_indices = set(range(len(PROOF_CAMERAS))) if view_indices is None else set(view_indices)
    invalid_indices = sorted(selected_indices - set(range(len(PROOF_CAMERAS))))
    if invalid_indices:
        raise ValueError(f"invalid proof view indices: {invalid_indices}")
    evidence_paths = []
    for index, camera_spec in enumerate(PROOF_CAMERAS):
        camera = _make_camera(cameras, camera_spec)
        if index not in selected_indices:
            continue
        scene.camera = camera
        slug = str(camera_spec["name"]).removeprefix("CAM_Nakaniwa_A20_").lower()
        path = views_dir / f"{index:02d}_{slug}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        evidence_paths.append(str(path))

    # Leave the saved .blend on the user's requested dual-player view without
    # mutating a running Blender UI or any unrelated visible collection.
    dual = next(obj for obj in cameras.objects if obj.name == MAIN_REFERENCE_CAMERA["name"])
    scene.camera = dual

    blend_path = output_dir / "nakaniwa-a20-art-rebuild.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    presentation_triangles = 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        evaluated_mesh = evaluated.to_mesh()
        presentation_triangles += sum(
            max(1, len(polygon.vertices) - 2)
            for polygon in evaluated_mesh.polygons
        )
        evaluated.to_mesh_clear()
    scorecard = producer_provisional_scorecard(evidence_paths)
    scorecard_path = output_dir / "producer-provisional-scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    all_metrics = [plan_metrics(level) for level in range(3)]
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    render_set_hasher = hashlib.sha256()
    view_artifacts = []
    for evidence_path in evidence_paths:
        artifact_path = Path(evidence_path)
        artifact_bytes = artifact_path.read_bytes()
        artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
        render_set_hasher.update(artifact_path.name.encode("utf-8"))
        render_set_hasher.update(b"\0")
        render_set_hasher.update(bytes.fromhex(artifact_sha))
        view_artifacts.append(
            {
                "path": str(artifact_path),
                "sha256": artifact_sha,
                "bytes": len(artifact_bytes),
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            }
        )
    manifest = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "kitVersion": KIT_VERSION,
        "sourcePath": str(Path(__file__).resolve()),
        "sourceSha256": source_sha,
        "reference": {"path": str(REFERENCE_PATH), "sha256": REFERENCE_SHA256},
        "canonicalContract": contract,
        "exactLandmarkCount": 2,
        "landmarkIds": [item["id"] for item in LANDMARKS],
        "mainReferenceCamera": MAIN_REFERENCE_CAMERA,
        "heroFrameMetrics": reference_camera_frame_metrics(lod),
        "lodMetrics": all_metrics,
        "builtLod": lod,
        "builtSpecCount": len(specs),
        "builtObjectCount": len(objects),
        "authoredMeshVertexCount": authored_vertices,
        "authoredMeshPolygonCount": authored_polygons,
        "authoredMeshTriangleCount": authored_triangles,
        "presentationEvaluatedTriangleCount": presentation_triangles,
        "builtMaterialCount": len(materials),
        "drawCallEstimate": len(objects),
        "blend": str(blend_path),
        "blendBytes": blend_path.stat().st_size,
        "views": evidence_paths,
        "viewArtifacts": view_artifacts,
        "renderSetSha256": render_set_hasher.hexdigest(),
        "renderedViewIndices": sorted(selected_indices),
        "producerScorecard": str(scorecard_path),
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        "releaseMutation": False,
    }
    manifest_path = output_dir / "proof-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["manifest"] = str(manifest_path)
    return manifest


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    arguments = list(argv)
    if "--" in arguments:
        arguments = arguments[arguments.index("--") + 1:]
    parser = argparse.ArgumentParser(description="Build private Nakaniwa A20 art proof")
    parser.add_argument("--layout", type=Path, default=CANONICAL_LAYOUT_DEFAULT)
    parser.add_argument("--proof-dir", type=Path, default=PRIVATE_PROOF_DEFAULT)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument(
        "--view-indices", default="",
        help="comma-separated proof-view indices for private iteration; default renders all",
    )
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.plan_only:
        print(json.dumps({
            "kitVersion": KIT_VERSION,
            "canonicalContract": canonical_contract_report(args.layout),
            "lodMetrics": [plan_metrics(level) for level in range(3)],
            "heroFrameMetrics": reference_camera_frame_metrics(args.lod),
            "producerScorecard": producer_provisional_scorecard(),
        }, ensure_ascii=False, indent=2))
        return 0
    try:
        import bpy  # type: ignore  # noqa: F401
    except ImportError:
        print(json.dumps({
            "kitVersion": KIT_VERSION,
            "lodMetrics": [plan_metrics(level) for level in range(3)],
            "heroFrameMetrics": reference_camera_frame_metrics(args.lod),
        }, ensure_ascii=False, indent=2))
        return 0
    view_indices = None
    if args.view_indices.strip():
        view_indices = tuple(int(item) for item in args.view_indices.split(",") if item.strip())
    manifest = build_private_proof(args.proof_dir, args.layout, args.lod, view_indices)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


__all__ = [
    "CANONICAL_BOT_SPAWNS",
    "CANONICAL_BOUNDS",
    "CANONICAL_PLAYER_SPAWNS",
    "CANONICAL_ROADS",
    "CONNECTION_MAP",
    "CONSERVATORY_ID",
    "DEFAULT_INTEGRATION_MATERIAL_MAP",
    "FIXED_SCORE_CATEGORIES",
    "KIT_VERSION",
    "LANDMARKS",
    "LOD_BUDGETS",
    "MAIN_REFERENCE_CAMERA",
    "MAP_SIZE_M",
    "MATERIALS",
    "PALACE_ID",
    "PRIVATE_PROOF_DEFAULT",
    "PRODUCER_PROVISIONAL_SCORES",
    "PROOF_CAMERAS",
    "build_private_proof",
    "build_specs",
    "canonical_contract_report",
    "emit_specs_to_builder",
    "emit_to_builder",
    "estimated_triangles",
    "plan_metrics",
    "producer_provisional_scorecard",
    "reference_camera_frame_metrics",
    "spec_bounds",
]


if __name__ == "__main__":
    raise SystemExit(main())
