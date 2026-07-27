#!/usr/bin/env python3
"""A18 reference-match module and private Blender prototype for Nakaniwa.

This module deliberately does not import or edit ``build_all_stages.py``.  Its
pure spec API can be unit-tested outside Blender and later integrated after the
concurrent Souko pass is complete.  Executing the file through Blender MCP
builds only ``HB_NAKANIWA_A18_REFERENCE`` and writes only below
``/private/tmp/hibana-blender/a18-nakaniwa-reference-prototype``.

Connection Map (runtime metres; Y is vertical):
  wet plaza top Y=0.00 <-> palace terrace bottom Y=-0.10    overlap 0.10 m
  palace terrace top Y=1.20 <-> lower wings bottom Y=1.10  overlap 0.10 m
  lower wings top Y=11.10 <-> roof belts bottom Y=10.90    overlap 0.20 m
  central keep top Y=23.10 <-> crown drum bottom Y=22.90   overlap 0.20 m
  crown drum top Y=28.10 <-> crown spires bottom Y=27.90  overlap 0.20 m
  arcade columns top <-> segmented arch spring             overlap 0.12 m
  arcade arch crown <-> entablature bottom                  overlap 0.12 m
  palace entry bridge <-> palace terrace                    overlap 0.15 m
  canal water top Y=-0.08 <-> dressed canal banks Y=-0.10 overlap 0.02 m
  bridge deck underside Y=0.18 <-> bank coping top Y=0.22  overlap 0.04 m
  conservatory perimeter foundation top Y=3.12 <-> buttress bottom Y=3.08 overlap 0.04 m
  buttress top Y=9.10 <-> vault rib spring Y=8.90          overlap 0.20 m
  vault rib section <-> adjacent glass panel                overlap 0.08 m
  vault ridge rail <-> front/rear portal ribs               overlap 0.10 m
  interior stair top <-> upper planted walk                 overlap 0.08 m
  irrigation tower base <-> conservatory plinth             overlap 0.15 m
  civic wing base <-> wet plaza                              overlap 0.10 m
  civic roof belt <-> civic facade                           overlap 0.12 m
  mature tree trunk <-> planter soil                         overlap 0.15 m
  foreground arcade <-> flanking civic wing                 overlap 0.10 m

All spanning ribs, arches, rails and braces are explicit start/end beams.  No
Euler-rotated cylinder is used.  Prototype meshes are assembled from explicit
vertices, so the cube half-size ambiguity cannot occur.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


STAGE_ID = "nakaniwa"
REFERENCE_MATCH_VERSION = "a18-nakaniwa-reference-match-r11"
REFERENCE_PATH = "tools/blender/concepts/nakaniwa-reference-v1.png"
REFERENCE_SHA256 = "c0b3bec12431c264ebe04a0757ea67eb521eab2c4e32e004da88cf6e6eebe15d"
PRIVATE_OUTPUT_ROOT = Path("/private/tmp/hibana-blender/a18-nakaniwa-reference-prototype")
TARGET_COLLECTION = "HB_NAKANIWA_A18_REFERENCE"
MAP_SIZE_M = 320.0
CANONICAL_BOUNDS = {"min_x": -160.0, "max_x": 160.0, "min_z": -160.0, "max_z": 160.0}
ROAD_HALF_WIDTH_M = 8.0
PLAYER_EYE_M = 1.65

# Reference-first camera contract.  This point lies on the perpendicular
# bisector of the two canonical landmark centres, so neither hero is reduced
# to a distant skyline speck.  The 18 mm lens contains both broad silhouettes
# while the forward palace crown and near greenhouse fan each occupy roughly
# forty percent of the 16:9 frame height.
REFERENCE_DUAL_CAMERA = {
    "location": (-102.36, PLAYER_EYE_M, 82.00),
    "target": (-4.0, 22.0, -3.0),
    "lensMm": 19.0,
    "targetFrameHeightRatio": 0.40,
    "acceptedFrameHeightRatio": (0.33, 0.55),
}

CONSERVATORY_THRESHOLD_CAMERA = {
    "location": (52.0, PLAYER_EYE_M, 19.0),
    "target": (52.0, 5.0, 72.0),
    "lensMm": 25.0,
    "openingWidthM": 8.0,
    "maxOpaqueObstructionRatio": 0.10,
}

CONSERVATORY_INTERIOR_CAMERA = {
    "location": (52.0, PLAYER_EYE_M, 64.0),
    "target": (52.0, 7.0, 112.0),
    "lensMm": 28.0,
    "clearViewWidthM": 6.4,
    "maxOpaqueObstructionRatio": 0.10,
}

CANONICAL_ROADS = (
    {"id": "primary-north-south", "axis": "z", "centre": 0.0, "width": 16.0,
     "bounds": {"minX": -8.0, "maxX": 8.0, "minZ": -156.0, "maxZ": 156.0}},
    {"id": "primary-east-west", "axis": "x", "centre": 0.0, "width": 16.0,
     "bounds": {"minX": -156.0, "maxX": 156.0, "minZ": -8.0, "maxZ": 8.0}},
)

CANONICAL_PLAYER_SPAWNS = (
    (0.0, 0.0, 148.0), (148.0, 0.0, 0.0),
    (0.0, 0.0, -148.0), (-148.0, 0.0, 0.0),
)

LANDMARKS = (
    {
        "index": 0,
        "id": "nakaniwa-suiren-crown-palace",
        "referenceName": "Crowned Water Palace",
        "cx": -60.0, "cz": -67.8, "rot": 0.0,
        "width": 92.0, "depth": 78.0, "height": 43.0,
        "entrance": (-60.0, -28.0),
        "approach": {"start": (-60.0, -8.0), "end": (-60.0, -28.0), "width": 12.0},
        "collisionTemplate": "courtyard",
    },
    {
        "index": 1,
        "id": "nakaniwa-kakou-conservatory-citadel",
        "referenceName": "Fan-Glass Conservatory",
        "cx": 52.0, "cz": 61.8, "rot": 0.0,
        "width": 76.0, "depth": 66.0, "height": 50.0,
        "entrance": (52.0, 28.0),
        "approach": {"start": (52.0, 8.0), "end": (52.0, 28.0), "width": 12.0},
        "collisionTemplate": "hall",
    },
)

LOD_API = {
    0: {"label": "hero", "preserve": ("two-hero-silhouettes", "five-fan-vaults", "canals", "arcades", "bridges", "mature-trees", "near-mid-far")},
    1: {"label": "medium", "preserve": ("two-hero-silhouettes", "five-fan-vaults", "canals", "arcades", "bridges", "near-mid-far")},
    2: {"label": "horizon", "preserve": ("two-hero-silhouettes", "three-fan-vaults", "canals", "bridges", "near-mid-far")},
}

CONNECTION_MAP = (
    {"id": "palace-terrace-ground", "a": "wet-plaza", "aFace": "top", "b": "palace-terrace", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "palace-wing-terrace", "a": "palace-terrace", "aFace": "top", "b": "palace-wings", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "palace-roof-wing", "a": "palace-wings", "aFace": "top", "b": "palace-roof-belts", "bFace": "bottom", "axis": "y", "overlapM": 0.20},
    {"id": "palace-keep-drum", "a": "central-keep", "aFace": "top", "b": "crown-drum", "bFace": "bottom", "axis": "y", "overlapM": 0.20},
    {"id": "palace-drum-spires", "a": "crown-drum", "aFace": "top", "b": "crown-spires", "bFace": "bottom", "axis": "y", "overlapM": 0.20},
    {"id": "palace-arcade-columns", "a": "arcade-columns", "aFace": "top", "b": "arcade-arch-ribs", "bFace": "spring", "axis": "y", "overlapM": 0.12},
    {"id": "palace-arcade-entablature", "a": "arcade-arch-ribs", "aFace": "crown", "b": "arcade-entablature", "bFace": "bottom", "axis": "y", "overlapM": 0.12},
    {"id": "palace-canal-entry", "a": "entry-bridge", "aFace": "rear", "b": "palace-terrace", "bFace": "front", "axis": "z", "overlapM": 0.15},
    {"id": "canal-bank-water", "a": "canal-water", "aFace": "top", "b": "canal-bank", "bFace": "inside", "axis": "y", "overlapM": 0.02},
    {"id": "bridge-bank", "a": "bridge-deck", "aFace": "underside", "b": "canal-bank", "bFace": "coping", "axis": "y", "overlapM": 0.04},
    {"id": "conservatory-plinth-buttress", "a": "conservatory-perimeter-foundation", "aFace": "top", "b": "vault-buttresses", "bFace": "bottom", "axis": "y", "overlapM": 0.04},
    {"id": "conservatory-buttress-rib", "a": "vault-buttresses", "aFace": "top", "b": "vault-ribs", "bFace": "spring", "axis": "y", "overlapM": 0.20},
    {"id": "conservatory-rib-glass", "a": "vault-ribs", "aFace": "side", "b": "glass-panels", "bFace": "edge", "axis": "surface", "overlapM": 0.08},
    {"id": "conservatory-ridge-portals", "a": "vault-ridge", "aFace": "ends", "b": "portal-ribs", "bFace": "crown", "axis": "z", "overlapM": 0.10},
    {"id": "conservatory-stair-walk", "a": "interior-stair", "aFace": "top", "b": "upper-planted-walk", "bFace": "front", "axis": "z", "overlapM": 0.08},
    {"id": "conservatory-threshold-promenade", "a": "front-terrace", "aFace": "rear", "b": "central-promenade", "bFace": "front", "axis": "z", "overlapM": 0.20},
    {"id": "conservatory-water-coping", "a": "interior-water", "aFace": "side", "b": "interior-water-coping", "bFace": "inside", "axis": "x", "overlapM": 0.05},
    {"id": "conservatory-side-circulation", "a": "interior-stair", "aFace": "top", "b": "side-upper-walks", "bFace": "front", "axis": "z", "overlapM": 0.12},
    {"id": "conservatory-tower-plinth", "a": "irrigation-tower", "aFace": "bottom", "b": "conservatory-tower-pad", "bFace": "top", "axis": "y", "overlapM": 0.02},
    {"id": "civic-ground", "a": "civic-wing", "aFace": "bottom", "b": "wet-plaza", "bFace": "top", "axis": "y", "overlapM": 0.10},
    {"id": "civic-roof", "a": "civic-wing", "aFace": "top", "b": "civic-roof-belt", "bFace": "bottom", "axis": "y", "overlapM": 0.12},
    {"id": "tree-planter", "a": "mature-tree-trunk", "aFace": "bottom", "b": "planter-soil", "bFace": "top", "axis": "y", "overlapM": 0.15},
    {"id": "foreground-arcade-wing", "a": "foreground-arcade", "aFace": "ends", "b": "civic-wing", "bFace": "facade", "axis": "x", "overlapM": 0.10},
    {"id": "central-terrace-stack", "a": "stepped-garden-terrace", "aFace": "top", "b": "stepped-garden-soil", "bFace": "bottom", "axis": "y", "overlapM": 0.02},
    {"id": "avenue-planter-soil", "a": "avenue-tier-planter", "aFace": "top", "b": "avenue-tier-soil", "bFace": "bottom", "axis": "y", "overlapM": 0.02},
)

MATERIALS = {
    "wet_stone": {"color": (0.25, 0.23, 0.20, 1.0), "roughness": 0.34, "metallic": 0.0, "noise": 0.18},
    "honey_stone": {"color": (0.57, 0.42, 0.26, 1.0), "roughness": 0.56, "metallic": 0.0, "noise": 0.12},
    "white_marble": {"color": (0.78, 0.75, 0.67, 1.0), "roughness": 0.28, "metallic": 0.0, "noise": 0.08},
    "verdigris_bronze": {"color": (0.10, 0.33, 0.30, 1.0), "roughness": 0.27, "metallic": 0.72, "noise": 0.10},
    "dark_wood": {"color": (0.12, 0.065, 0.035, 1.0), "roughness": 0.48, "metallic": 0.0, "noise": 0.10},
    "brass": {"color": (0.53, 0.31, 0.08, 1.0), "roughness": 0.25, "metallic": 0.82, "noise": 0.05},
    "glass": {"color": (0.10, 0.38, 0.42, 0.56), "roughness": 0.10, "metallic": 0.0, "transmission": 0.82, "alpha": 0.56},
    "water": {"color": (0.025, 0.24, 0.31, 1.0), "roughness": 0.12, "metallic": 0.26, "transmission": 0.0, "alpha": 1.0},
    "foliage_dark": {"color": (0.035, 0.18, 0.075, 1.0), "roughness": 0.72, "metallic": 0.0, "noise": 0.12},
    "foliage_light": {"color": (0.16, 0.36, 0.10, 1.0), "roughness": 0.68, "metallic": 0.0, "noise": 0.12},
    "flower": {"color": (0.42, 0.12, 0.46, 1.0), "roughness": 0.50, "metallic": 0.0, "emission": (0.08, 0.01, 0.10, 1.0)},
    "warm_window": {"color": (0.48, 0.19, 0.045, 1.0), "roughness": 0.30, "metallic": 0.0, "emission": (1.0, 0.24, 0.04, 1.0), "emission_strength": 1.5},
}

DEFAULT_INTEGRATION_MATERIAL_MAP = {
    "wet_stone": "wall_weathered", "honey_stone": "wall_warm", "white_marble": "wall",
    "verdigris_bronze": "roof", "dark_wood": "wood", "brass": "accent", "glass": "glass",
    "water": "water", "foliage_dark": "natural", "foliage_light": "natural",
    "flower": "accent", "warm_window": "emissive",
}

# Controlling baseline from the independent root review of v8.  This is kept
# deliberately explicit so a producer cannot self-certify a visual pass from
# geometry counts.  R9 must be re-scored from fresh rendered evidence; until an
# independent reviewer signs that evidence, NO-SHIP remains the only truthful
# status even when topology, layout and browser gates pass.
REFERENCE_SCORE_ITEMS = (
    {"category": "composition", "score": 4.5, "evidence": "v8 left a broad empty road and did not frame both heroes with the reference's occupied foreground."},
    {"category": "hero silhouettes", "score": 6.5, "evidence": "Both hero types were identifiable, but palace and conservatory silhouettes were much simpler than the reference."},
    {"category": "architectural grammar", "score": 4.8, "evidence": "The v8 blockout lacked the reference's layered carved outer shells, screens, balconies and deep roof grammar."},
    {"category": "human scale", "score": 4.0, "evidence": "Sparse doors, props, planting and facade relief made most masses read as oversized blocks."},
    {"category": "material realism", "score": 3.5, "evidence": "v8 materials read as smooth flat swatches rather than weathered stone, metal, glass, water and planting."},
    {"category": "near-mid-far density", "score": 3.8, "evidence": "Large empty paving and weak midground occlusion did not reproduce the reference's dense layered city."},
    {"category": "gameplay readability", "score": 8.0, "evidence": "Canonical routes, approaches and crossings remained clear in the technical prototype."},
    {"category": "props/storytelling", "score": 3.5, "evidence": "v8 contained too few inhabited garden, craft, irrigation and civic details."},
    {"category": "lighting/atmosphere", "score": 4.5, "evidence": "The flat prototype lighting did not produce the reference's warm/cool depth and material separation."},
    {"category": "reference identity", "score": 5.5, "evidence": "The palace/garden/glass triad was present, but the lush carved reference identity was not yet matched."},
)


def _base(role: str, material: str, group: str, *, blocks_gameplay: bool = False) -> dict:
    return {"role": role, "material": material, "group": group, "blocksGameplay": blocks_gameplay}


def _box(specs: list[dict], role: str, material: str, group: str, x: float, y: float, z: float,
         w: float, h: float, d: float, *, blocks_gameplay: bool = False) -> None:
    if min(w, h, d) <= 0:
        raise ValueError(f"{role}: box dimensions must be positive")
    specs.append({**_base(role, material, group, blocks_gameplay=blocks_gameplay), "kind": "box",
                  "x": x, "y": y, "z": z, "w": w, "h": h, "d": d})


def _beam(specs: list[dict], role: str, material: str, group: str,
          start: tuple[float, float, float], end: tuple[float, float, float],
          width: float, depth: float) -> None:
    if math.dist(start, end) < 1e-6 or min(width, depth) <= 0:
        raise ValueError(f"{role}: invalid spanning beam")
    specs.append({**_base(role, material, group), "kind": "beam", "start": start, "end": end,
                  "width": width, "depth": depth})


def _cylinder(specs: list[dict], role: str, material: str, group: str, x: float, y: float, z: float,
              radius: float, height: float, segments: int, *, top_radius: float | None = None,
              blocks_gameplay: bool = False) -> None:
    if radius <= 0 or height <= 0 or segments < 3:
        raise ValueError(f"{role}: invalid cylinder")
    specs.append({**_base(role, material, group, blocks_gameplay=blocks_gameplay), "kind": "cylinder",
                  "x": x, "y": y, "z": z, "radius": radius, "height": height,
                  "segments": segments, "topRadius": radius if top_radius is None else top_radius})


def _panel(specs: list[dict], role: str, material: str, group: str,
           corners: Iterable[tuple[float, float, float]], thickness: float = 0.08) -> None:
    corners = tuple(corners)
    if len(corners) != 4 or thickness <= 0:
        raise ValueError(f"{role}: invalid panel")
    specs.append({**_base(role, material, group), "kind": "panel", "corners": corners, "thickness": thickness})


def _add_deep_gable_roof(specs: list[dict], *, cx: float, base_y: float, cz: float,
                          width: float, depth: float, height: float, axis: str,
                          material: str, group: str, role_prefix: str, lod: int) -> None:
    """Add two real roof slopes plus seated ridge/eave and gable frames."""
    eave = 0.9 if lod == 0 else 0.65
    w, d = width + eave * 2, depth + eave * 2
    if axis == "z":
        slopes = (
            ((cx-w/2, base_y, cz-d/2), (cx, base_y+height, cz-d/2),
             (cx, base_y+height, cz+d/2), (cx-w/2, base_y, cz+d/2)),
            ((cx, base_y+height, cz-d/2), (cx+w/2, base_y, cz-d/2),
             (cx+w/2, base_y, cz+d/2), (cx, base_y+height, cz+d/2)),
        )
        ridge_start, ridge_end = (cx, base_y+height, cz-d/2), (cx, base_y+height, cz+d/2)
        eaves = (((cx-w/2, base_y, cz-d/2), (cx-w/2, base_y, cz+d/2)),
                 ((cx+w/2, base_y, cz-d/2), (cx+w/2, base_y, cz+d/2)))
        gables = (
            ((cx-w/2, base_y, cz-d/2), ridge_start, (cx+w/2, base_y, cz-d/2)),
            ((cx-w/2, base_y, cz+d/2), ridge_end, (cx+w/2, base_y, cz+d/2)),
        )
    else:
        slopes = (
            ((cx-w/2, base_y, cz-d/2), (cx-w/2, base_y, cz+d/2),
             (cx+w/2, base_y, cz+d/2), (cx+w/2, base_y, cz-d/2)),
            ((cx-w/2, base_y, cz-d/2), (cx+w/2, base_y, cz-d/2),
             (cx+w/2, base_y+height, cz), (cx-w/2, base_y+height, cz)),
        )
        # Replace the first flat loop with the opposite pitched plane.
        slopes = (
            ((cx-w/2, base_y, cz-d/2), (cx-w/2, base_y+height, cz),
             (cx+w/2, base_y+height, cz), (cx+w/2, base_y, cz-d/2)),
            ((cx-w/2, base_y+height, cz), (cx-w/2, base_y, cz+d/2),
             (cx+w/2, base_y, cz+d/2), (cx+w/2, base_y+height, cz)),
        )
        ridge_start, ridge_end = (cx-w/2, base_y+height, cz), (cx+w/2, base_y+height, cz)
        eaves = (((cx-w/2, base_y, cz-d/2), (cx+w/2, base_y, cz-d/2)),
                 ((cx-w/2, base_y, cz+d/2), (cx+w/2, base_y, cz+d/2)))
        gables = (
            ((cx-w/2, base_y, cz-d/2), ridge_start, (cx-w/2, base_y, cz+d/2)),
            ((cx+w/2, base_y, cz-d/2), ridge_end, (cx+w/2, base_y, cz+d/2)),
        )
    for corners in slopes:
        _panel(specs, f"{role_prefix}-slope", material, group, corners, 0.16 if lod == 0 else 0.24)
    _beam(specs, f"{role_prefix}-ridge", material, group, ridge_start, ridge_end, 0.24, 0.20)
    for start, end in eaves:
        _beam(specs, f"{role_prefix}-eave", material, group, start, end, 0.28, 0.18)
    for left, crown, right in gables:
        _beam(specs, f"{role_prefix}-gable-frame", "dark_wood", group, left, crown, 0.20, 0.16)
        _beam(specs, f"{role_prefix}-gable-frame", "dark_wood", group, crown, right, 0.20, 0.16)


def _add_balustrade(specs: list[dict], *, x: float, y: float, z: float, length: float,
                    axis: str, material: str, group: str, role_prefix: str, lod: int) -> None:
    posts = max(3, int(length / (2.2 if lod == 0 else 3.8)))
    for index in range(posts + 1):
        t = index / posts - 0.5
        px = x + t * length if axis == "x" else x
        pz = z if axis == "x" else z + t * length
        _box(specs, f"{role_prefix}-post", material, group, px, y + 0.62, pz,
             0.18, 1.24, 0.18)
    start = (x - length / 2, y + 1.20, z) if axis == "x" else (x, y + 1.20, z - length / 2)
    end = (x + length / 2, y + 1.20, z) if axis == "x" else (x, y + 1.20, z + length / 2)
    _beam(specs, f"{role_prefix}-rail", material, group, start, end, 0.16, 0.12)


def _add_facade_lattice(specs: list[dict], *, cx: float, base_y: float, z: float,
                        width: float, height: float, material: str, group: str,
                        role_prefix: str, lod: int) -> None:
    """Build open diamond relief instead of a flat dark window card."""
    half = width / 2
    _box(specs, f"{role_prefix}-sill", material, group, cx, base_y, z, width + 0.35, 0.20, 0.18)
    _box(specs, f"{role_prefix}-head", material, group, cx, base_y + height, z,
         width + 0.35, 0.20, 0.18)
    for side in (-1, 1):
        _box(specs, f"{role_prefix}-jamb", material, group, cx + side * half,
             base_y + height / 2, z, 0.20, height, 0.18)
    diagonal_count = 4 if lod == 0 else 2
    for index in range(diagonal_count):
        t0 = index / diagonal_count
        t1 = (index + 1) / diagonal_count
        x0, x1 = cx - half + t0 * width, cx - half + t1 * width
        _beam(specs, f"{role_prefix}-diagonal", material, group,
              (x0, base_y, z), (x1, base_y + height, z), 0.09, 0.08)
        _beam(specs, f"{role_prefix}-diagonal", material, group,
              (x0, base_y + height, z), (x1, base_y, z), 0.09, 0.08)


def _add_arch(specs: list[dict], *, cx: float, base_y: float, z: float, bay_width: float,
              spring_y: float, depth: float, material: str, group: str, role_prefix: str,
              segments: int) -> None:
    radius = bay_width * 0.42
    left = cx - radius
    right = cx + radius
    _box(specs, f"{role_prefix}-column", material, group, left, base_y + (spring_y - base_y) / 2,
         z, 0.58, spring_y - base_y + 0.12, depth)
    _box(specs, f"{role_prefix}-column", material, group, right, base_y + (spring_y - base_y) / 2,
         z, 0.58, spring_y - base_y + 0.12, depth)
    points = []
    for index in range(segments + 1):
        angle = math.pi - math.pi * index / segments
        points.append((cx + math.cos(angle) * radius, spring_y + math.sin(angle) * radius, z))
    for start, end in zip(points, points[1:]):
        _beam(specs, f"{role_prefix}-arch-rib", material, group, start, end, 0.18, depth * 0.48)


def _add_arcade(specs: list[dict], *, cx: float, base_y: float, z: float, width: float,
                bay_count: int, material: str, group: str, role_prefix: str, lod: int) -> None:
    bay = width / bay_count
    segments = 11 if lod == 0 else 6 if lod == 1 else 4
    spring = base_y + 4.05
    for index in range(bay_count):
        _add_arch(specs, cx=cx - width / 2 + bay * (index + 0.5), base_y=base_y, z=z,
                  bay_width=bay * 0.86, spring_y=spring, depth=0.72 if lod == 0 else 0.92,
                  material=material, group=group, role_prefix=role_prefix, segments=segments)
    _box(specs, f"{role_prefix}-entablature", material, group, cx, spring + bay * 0.43 + 0.12,
         z, width + 0.6, 0.55, 1.05)


def _add_side_arcade(specs: list[dict], *, x: float, base_y: float, cz: float, length: float,
                     bay_count: int, material: str, group: str, role_prefix: str,
                     lod: int) -> None:
    """Build a real YZ-plane arcade for a conservatory side elevation."""
    bay = length / bay_count
    segments = 9 if lod == 0 else 6 if lod == 1 else 4
    spring = base_y + 4.0
    radius = bay * 0.40
    for bay_index in range(bay_count):
        centre_z = cz - length / 2 + bay * (bay_index + 0.5)
        for column_z in (centre_z - radius, centre_z + radius):
            _box(specs, f"{role_prefix}-column", material, group,
                 x, base_y + (spring - base_y) / 2, column_z,
                 0.74, spring - base_y + 0.12, 0.58)
        points = []
        for segment in range(segments + 1):
            angle = math.pi - math.pi * segment / segments
            points.append((x, spring + math.sin(angle) * radius,
                           centre_z + math.cos(angle) * radius))
        for start, end in zip(points, points[1:]):
            _beam(specs, f"{role_prefix}-arch-rib", material, group,
                  start, end, 0.19, 0.16)
    _box(specs, f"{role_prefix}-entablature", material, group,
         x, spring + radius + 0.12, cz, 0.88, 0.55, length + 0.6)


def _add_plant_cluster(specs: list[dict], x: float, z: float, height: float,
                       group: str, lod: int, role: str) -> None:
    """Layer several offset leaf masses so planting never reads as one cone."""
    _cylinder(specs, f"{role}-stem", "dark_wood", group,
              x, 0.82 + height * 0.24, z, 0.10, height * 0.48,
              7 if lod == 0 else 5, top_radius=0.07)
    lobe_count = 4 if lod == 0 else 2
    for lobe in range(lobe_count):
        angle = math.tau * lobe / lobe_count + (x * 0.17 + z * 0.11)
        radius = height * (0.21 if lobe % 2 == 0 else 0.17)
        lobe_h = height * (0.42 if lobe % 2 == 0 else 0.34)
        _cylinder(specs, role,
                  "foliage_light" if lobe in (0, 3) else "foliage_dark", group,
                  x + math.cos(angle) * height * 0.12,
                  0.82 + height * (0.42 + 0.08 * (lobe % 2)),
                  z + math.sin(angle) * height * 0.12,
                  radius, lobe_h, 9 if lod == 0 else 6,
                  top_radius=radius * 0.72)


def _add_tree(specs: list[dict], x: float, z: float, height: float, group: str, lod: int,
              *, planter: bool = True) -> None:
    if planter:
        _box(specs, "garden-planter", "white_marble", group, x, 0.45, z, 4.0, 0.90, 4.0)
        _box(specs, "planter-soil", "dark_wood", group, x, 0.92, z, 3.35, 0.16, 3.35)
    base = 0.82 if planter else 0.0
    trunk_h = height * 0.42
    _cylinder(specs, "mature-tree-trunk", "dark_wood", group, x, base + trunk_h / 2, z,
              0.38 if lod == 0 else 0.48, trunk_h + 0.20, 9 if lod == 0 else 7)
    crown_base = base + trunk_h * 0.78
    layers = 5 if lod == 0 else 3 if lod == 1 else 1
    for layer in range(layers):
        angle = math.tau * layer / max(1, layers)
        offset_radius = height * (0.055 if layer else 0.0)
        radius = height * (0.25 - layer * 0.014)
        layer_h = height * (0.25 - layer * 0.012)
        _cylinder(specs, "mature-tree-canopy", "foliage_light" if layer == 1 else "foliage_dark",
                  group, x + math.cos(angle) * offset_radius,
                  crown_base + layer * height * 0.065 + layer_h / 2,
                  z + math.sin(angle) * offset_radius, radius, layer_h,
                  12 if lod == 0 else 8, top_radius=radius * 0.52)


def _add_flower_planter(specs: list[dict], x: float, z: float, length: float, axis: str, lod: int) -> None:
    w, d = (length, 2.2) if axis == "x" else (2.2, length)
    _box(specs, "flower-planter", "white_marble", "garden-city", x, 0.38, z, w, 0.76, d)
    _box(specs, "flower-soil", "dark_wood", "garden-city", x, 0.80, z, w - 0.5, 0.14, d - 0.5)
    count = max(2, int(length // (1.8 if lod == 0 else 3.4)))
    for index in range(count):
        t = (index + 0.5) / count - 0.5
        fx = x + t * (length - 1.0) if axis == "x" else x
        fz = z if axis == "x" else z + t * (length - 1.0)
        _cylinder(specs, "garden-flower", "flower", "garden-city", fx, 1.16, fz,
                  0.20 if lod == 0 else 0.28, 0.62, 6, top_radius=0.06)


def _add_garden_furniture_cluster(specs: list[dict], x: float, z: float, axis: str, lod: int) -> None:
    """Add player-scale bench and lit garden standard beside a canal."""
    if lod > 1:
        return
    bench_w, bench_d = ((4.6, 1.2) if axis == "x" else (1.2, 4.6))
    _box(specs, "garden-bench-seat", "dark_wood", "garden-city",
         x, 1.05, z, bench_w, 0.22, bench_d)
    back_x = x if axis == "x" else x + 0.46
    back_z = z + 0.46 if axis == "x" else z
    _box(specs, "garden-bench-back", "dark_wood", "garden-city",
         back_x, 1.72, back_z, bench_w if axis == "x" else 0.18,
         1.05, 0.18 if axis == "x" else bench_d)
    for side in (-1, 1):
        leg_x = x + side * (bench_w * 0.34) if axis == "x" else x
        leg_z = z if axis == "x" else z + side * (bench_d * 0.34)
        _box(specs, "garden-bench-leg", "brass", "garden-city",
             leg_x, 0.56, leg_z, 0.22, 0.98, 0.22)
    lamp_x = x + (3.1 if axis == "x" else -2.2)
    lamp_z = z + (-2.2 if axis == "x" else 3.1)
    _cylinder(specs, "garden-lantern-post", "brass", "garden-city",
              lamp_x, 2.45, lamp_z, 0.13, 4.8, 10 if lod == 0 else 7, top_radius=0.10)
    _box(specs, "garden-lantern-light", "warm_window", "garden-city",
         lamp_x, 4.82, lamp_z, 0.68, 0.92, 0.68)
    _cylinder(specs, "garden-lantern-cap", "verdigris_bronze", "garden-city",
              lamp_x, 5.50, lamp_z, 0.62, 0.52, 8 if lod == 0 else 6, top_radius=0.06)


def _add_palace(specs: list[dict], lod: int) -> None:
    p = LANDMARKS[0]
    x, z = p["cx"], p["cz"]
    group = p["id"]
    _box(specs, "palace-terrace", "wet_stone", group, x, 0.55, z, 92.0, 1.30, 78.0)
    _box(specs, "palace-water-court", "water", group, x, 0.10, z + 22.0, 26.0, 0.22, 17.0)
    _box(specs, "palace-entry-bridge", "white_marble", group, x, 0.78, z + 32.4, 8.0, 1.45, 9.2)

    # Horizontally layered palace mass: two deep civic wings and a central keep.
    for side in (-1, 1):
        wing_x = x + side * 28.0
        _box(specs, "palace-lower-wing", "honey_stone", group, wing_x, 6.10, z - 1.0,
             24.0, 10.0, 46.0, blocks_gameplay=True)
        _box(specs, "palace-upper-wing", "white_marble", group, wing_x, 13.10, z - 7.0,
             19.0, 4.2, 34.0)
        _box(specs, "palace-roof-belt", "verdigris_bronze", group, wing_x, 11.02, z - 1.0,
             27.0, 0.46, 49.0)
        _box(specs, "palace-roof-belt", "verdigris_bronze", group, wing_x, 15.10, z - 7.0,
             22.0, 0.42, 37.0)
        _add_deep_gable_roof(
            specs, cx=wing_x, base_y=15.28, cz=z-7.0, width=21.0, depth=36.0,
            height=5.4, axis="z", material="verdigris_bronze", group=group,
            role_prefix="palace-wing-roof", lod=lod,
        )
        # Deep facade register: pale pilasters, recessed warm windows and a
        # continuous gallery rail give the wing human scale at 1.65 m.
        front_z = z + 22.10
        for bay in range(4 if lod == 0 else 3 if lod == 1 else 2):
            bx = wing_x - 8.1 + bay * (16.2 / max(1, (4 if lod == 0 else 3 if lod == 1 else 2) - 1))
            _box(specs, "palace-facade-pilaster", "white_marble", group,
                 bx, 6.0, front_z, 0.72, 10.2, 0.62)
            if lod < 2:
                for level_y in (4.6, 8.2):
                    _box(specs, "palace-warm-window", "warm_window", group,
                         bx + side * 1.55, level_y, front_z - 0.18, 1.25, 1.85, 0.16)
        _box(specs, "palace-gallery-rail", "brass", group, wing_x, 11.55, front_z + 0.25,
             23.2, 0.34, 0.32)
        tower_count = 2 if lod < 2 else 1
        for tower_index in range(tower_count):
            tower_z = z - 24.0 + tower_index * 48.0
            _box(specs, "palace-corner-tower", "honey_stone", group, wing_x, 12.1, tower_z,
                 12.0, 22.0, 12.0)
            _add_deep_gable_roof(
                specs, cx=wing_x, base_y=23.05, cz=tower_z, width=13.2, depth=13.2,
                height=5.2, axis="z", material="verdigris_bronze", group=group,
                role_prefix="palace-corner-roof", lod=lod,
            )
            _cylinder(specs, "palace-corner-finial", "brass", group, wing_x, 29.0, tower_z,
                      0.34, 4.2, 8 if lod == 0 else 6, top_radius=0.05)

    # R11 macro reset: pull the keep and crown toward the ceremonial facade.
    # The old crown sat near the rear edge (z-10), making the palace read as a
    # tiny distant comb from the only camera that could include both heroes.
    # Every upper tier below is now supported by the forward keep volume.
    keep_z = z + 6.0
    crown_z = z + 25.0
    _box(specs, "palace-central-keep", "white_marble", group, x, 12.1, keep_z,
         34.0, 22.0, 36.0, blocks_gameplay=True)
    _box(specs, "palace-central-balcony", "honey_stone", group, x, 18.8, z + 24.0, 44.0, 1.0, 5.0)
    _add_balustrade(specs, x=x, y=19.25, z=z+26.0, length=41.5, axis="x",
                    material="brass", group=group, role_prefix="palace-central-balustrade", lod=lod)
    # A stepped upper citadel keeps the crown supported by architecture rather
    # than reading as a dome placed on a box.
    _box(specs, "palace-upper-citadel", "honey_stone", group, x, 21.7, crown_z,
         28.0, 8.2, 25.0)
    _box(specs, "palace-upper-citadel-belt", "white_marble", group, x, 25.55, crown_z,
         31.0, 0.72, 28.0)
    # A five-bay upper loggia and paired stepped pavilions break the former
    # three-box facade into the carved horizontal tiers visible in the
    # reference.  All pieces seat into the forward keep/citadel stack.
    _add_arcade(specs, cx=x, base_y=12.25, z=z + 24.55, width=26.0,
                bay_count=5 if lod == 0 else 4 if lod == 1 else 3,
                material="honey_stone", group=group,
                role_prefix="palace-upper-loggia", lod=lod)
    for side in (-1, 1):
        pavilion_x = x + side * 18.5
        _box(specs, "palace-stepped-pavilion", "honey_stone", group,
             pavilion_x, 18.8, crown_z - 1.0, 11.0, 13.0, 14.0)
        _box(specs, "palace-stepped-pavilion-belt", "white_marble", group,
             pavilion_x, 25.12, crown_z - 1.0, 12.2, 0.58, 15.2)
        _add_deep_gable_roof(
            specs, cx=pavilion_x, base_y=25.35, cz=crown_z-1.0,
            width=12.0, depth=15.0, height=4.6, axis="z",
            material="verdigris_bronze", group=group,
            role_prefix="palace-stepped-pavilion-roof", lod=lod,
        )
        _cylinder(specs, "palace-stepped-pavilion-finial", "brass", group,
                  pavilion_x, 31.0, crown_z-1.0, 0.24, 2.5,
                  8 if lod == 0 else 6, top_radius=0.04)
    for side in (-1, 1):
        shoulder_x = x + side * 10.2
        _box(specs, "palace-crown-shoulder", "white_marble", group,
             shoulder_x, 27.0, crown_z + 1.0, 6.0, 8.0, 8.0)
        _cylinder(specs, "palace-crown-shoulder-roof", "verdigris_bronze", group,
                  shoulder_x, 32.1, crown_z + 1.0, 4.4, 3.0, 8 if lod == 0 else 6, top_radius=0.7)
        _box(specs, "palace-crown-window", "warm_window", group,
             shoulder_x, 27.8, crown_z + 5.08, 1.6, 2.8, 0.16)
    _cylinder(specs, "palace-crown-drum", "white_marble", group, x, 25.6, crown_z,
              11.4, 5.4, 18 if lod == 0 else 12)
    # Shallow bronze lotus dome, then an unmistakable multi-spire crown.
    dome_tiers = 4 if lod == 0 else 3 if lod == 1 else 2
    radii = [15.0, 13.2, 10.2, 6.2, 2.6]
    for tier in range(dome_tiers):
        _cylinder(specs, "palace-lotus-dome", "verdigris_bronze", group, x,
                  28.25 + tier * 1.35, crown_z, radii[tier], 1.55,
                  18 if lod == 0 else 12, top_radius=radii[tier + 1])
    crown_base = 29.0
    crown_count = 9 if lod == 0 else 7 if lod == 1 else 5
    for index in range(crown_count):
        angle = math.tau * index / crown_count
        radius = 10.8 if index % 2 == 0 else 8.0
        sx = x + math.cos(angle) * radius
        sz = crown_z + math.sin(angle) * radius
        height = 10.5 + (index % 3) * 1.2
        _cylinder(specs, "palace-crown-spire", "brass" if index % 2 else "verdigris_bronze",
                  group, sx, crown_base + height / 2, sz, 1.25 if lod == 0 else 1.55,
                  height, 8 if lod == 0 else 6, top_radius=0.05)
    _cylinder(specs, "palace-master-spire", "brass", group, x, 36.0, crown_z,
              1.05, 13.8, 10 if lod == 0 else 7, top_radius=0.04)

    # Tall tapered crown petals echo the reference palace's clustered blades.
    # Each glass/bronze petal is a connected quadrilateral with an explicit
    # structural frame, avoiding loose cones and exploded-looking transforms.
    petal_count = 7 if lod == 0 else 5 if lod == 1 else 3
    for index in range(petal_count):
        t = index / max(1, petal_count - 1) - 0.5
        px = x + t * 28.0
        base_y = 29.2 + abs(t) * 1.8
        tip_y = 43.45 - abs(t) * 4.0
        half_base = 2.3 if lod == 0 else 2.7
        half_tip = 0.34
        panel_z = crown_z + 5.5 - abs(t) * 1.3
        corners = ((px-half_base, base_y, panel_z), (px+half_base, base_y, panel_z),
                   (px+half_tip, tip_y, panel_z), (px-half_tip, tip_y, panel_z))
        _panel(specs, "palace-crown-petal-glass", "glass", group, corners, 0.10)
        for start, end in zip(corners, corners[1:] + corners[:1]):
            _beam(specs, "palace-crown-petal-frame", "brass", group,
                  start, end, 0.18 if lod == 0 else 0.24, 0.14)
    # A shorter rear rank gives the crown measurable depth from the fixed
    # north-west camera instead of seven coplanar black blades.
    rear_petal_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(rear_petal_count):
        t = index / max(1, rear_petal_count - 1) - 0.5
        px = x + t * 22.0
        base_y = 28.8 + abs(t) * 1.2
        tip_y = 39.8 - abs(t) * 2.0
        panel_z = crown_z - 3.8
        corners = ((px-1.9, base_y, panel_z), (px+1.9, base_y, panel_z),
                   (px+0.30, tip_y, panel_z), (px-0.30, tip_y, panel_z))
        _panel(specs, "palace-rear-crown-petal-glass", "glass", group, corners, 0.10)
        for start, end in zip(corners, corners[1:] + corners[:1]):
            _beam(specs, "palace-rear-crown-petal-frame", "brass", group,
                  start, end, 0.16 if lod == 0 else 0.22, 0.13)

    # Central facade relief survives medium LOD and makes the palace read as
    # occupied civic architecture rather than a blank hero shell.
    facade_z = z + 24.12
    central_bays = 7 if lod == 0 else 5 if lod == 1 else 3
    for bay in range(central_bays):
        bx = x - 12.0 + bay * (24.0 / max(1, central_bays - 1))
        _box(specs, "palace-central-pilaster", "white_marble", group,
             bx, 11.8, facade_z, 0.72, 18.0, 0.62)
        if lod < 2:
            for level_y in (7.0, 12.0, 17.0):
                _box(specs, "palace-warm-window", "warm_window", group,
                     bx + 1.35, level_y, facade_z + 0.05, 1.35, 2.05, 0.15)
    if lod < 2:
        for screen_x in (x-9.0, x, x+9.0):
            _add_facade_lattice(
                specs, cx=screen_x, base_y=20.0, z=facade_z+0.18, width=5.2,
                height=4.8, material="brass", group=group,
                role_prefix="palace-carved-screen", lod=lod,
            )

    # Two storeys of real segmented arcades face the ceremonial water court.
    _add_arcade(specs, cx=x, base_y=1.20, z=z + 30.0, width=78.0,
                bay_count=12 if lod == 0 else 8 if lod == 1 else 6,
                material="white_marble", group=group, role_prefix="palace-lower-arcade", lod=lod)
    if lod < 2:
        _add_arcade(specs, cx=x, base_y=8.3, z=z + 16.8, width=64.0,
                    bay_count=10 if lod == 0 else 7, material="honey_stone", group=group,
                    role_prefix="palace-upper-arcade", lod=lod)
    # Roof gardens make the horizontal wings inhabited rather than block masses.
    if lod == 0:
        for tx in (x - 29.0, x + 29.0):
            for tz in (z - 12.0, z + 8.0):
                _add_tree(specs, tx, tz, 8.5, group, lod, planter=True)
        for px in (x - 16.0, x + 16.0):
            _add_flower_planter(specs, px, z + 17.5, 12.0, "z", lod)
        # Ceremonial urns and flanking lamps make the arrival read at human scale.
        for side in (-1, 1):
            ux = x + side * 8.0
            uz = z + 34.2
            _cylinder(specs, "palace-entry-urn-base", "white_marble", group,
                      ux, 1.05, uz, 0.85, 0.70, 10, top_radius=0.62)
            _cylinder(specs, "palace-entry-urn-bowl", "honey_stone", group,
                      ux, 1.75, uz, 1.15, 0.85, 12, top_radius=0.78)
            _cylinder(specs, "palace-entry-urn-plant", "foliage_light", group,
                      ux, 3.05, uz, 1.45, 2.2, 10, top_radius=0.25)


def _vault_points(cx: float, base_y: float, z: float, half_width: float, height: float,
                  segments: int) -> list[tuple[float, float, float]]:
    points = []
    for index in range(segments + 1):
        angle = math.pi - math.pi * index / segments
        points.append((cx + math.cos(angle) * half_width, base_y + math.sin(angle) * height, z))
    return points


def _add_vault_lobe(specs: list[dict], *, cx: float, base_y: float, z0: float, z1: float,
                    half_width: float, height: float, lod: int, lobe_index: int) -> None:
    group = LANDMARKS[1]["id"]
    section_count = 7 if lod == 0 else 5 if lod == 1 else 3
    arc_segments = 9 if lod == 0 else 7 if lod == 1 else 5
    sections = [z0 + (z1 - z0) * index / (section_count - 1) for index in range(section_count)]
    section_points = []
    for section_z in sections:
        points = _vault_points(cx, base_y, section_z, half_width, height, arc_segments)
        section_points.append(points)
        for start, end in zip(points, points[1:]):
            _beam(specs, "conservatory-vault-rib", "brass", group, start, end,
                  0.22 if lod == 0 else 0.30, 0.18 if lod == 0 else 0.24)
    for section_index in range(len(sections) - 1):
        for arc_index in range(arc_segments):
            corners = (
                section_points[section_index][arc_index],
                section_points[section_index][arc_index + 1],
                section_points[section_index + 1][arc_index + 1],
                section_points[section_index + 1][arc_index],
            )
            _panel(specs, "conservatory-curved-glass-panel", "glass", group, corners,
                   0.07 if lod == 0 else 0.10)
    # Longitudinal ridge/eave rails tie every vault section physically.
    for arc_index in (0, arc_segments // 2, arc_segments):
        start = section_points[0][arc_index]
        end = section_points[-1][arc_index]
        _beam(specs, "conservatory-vault-longitudinal", "brass", group, start, end,
              0.20 if lod == 0 else 0.28, 0.16 if lod == 0 else 0.22)
    lobe_count = 5 if lod < 2 else 3
    for side in (-1, 1):
        outer_edge = (lobe_index == 0 and side == -1) or (lobe_index == lobe_count - 1 and side == 1)
        if lod < 2 and outer_edge:
            # A full-depth box here made each fan edge a 56 m solid wall and
            # reduced the greenhouse to a row of stone corridors.  Section-
            # aligned piers carry every rib while leaving the nave visually
            # and physically open at player height.
            for section_z in sections:
                _box(specs, "conservatory-vault-buttress", "white_marble", group,
                     cx + side * half_width, 6.10, section_z,
                     1.20, 6.10, 1.55)
        elif lod >= 2 and outer_edge:
            # Horizon LOD keeps the supported outer rhythm in one inexpensive
            # strip; it is never used for the first-person interior proof.
            _box(specs, "conservatory-vault-buttress", "white_marble", group,
                 cx + side * half_width, (base_y + 3.08) / 2, (z0 + z1) / 2,
                 1.20, base_y + 3.20, z1 - z0 + 1.2)


def _add_conservatory(specs: list[dict], lod: int) -> None:
    p = LANDMARKS[1]
    x, z = p["cx"], p["cz"]
    group = p["id"]
    # A solid 76 x 66 m podium made the hall look intact from outside while
    # silently putting a 1.65 m player camera inside stone after crossing the
    # portal.  Use a load-bearing perimeter instead: the side/rear strips
    # support every buttress, the split front strip keeps the canonical 12 m
    # aperture open, and a thin floor makes the interior truly traversable.
    foundation_y = 1.51
    foundation_h = 3.22
    _box(specs, "conservatory-perimeter-foundation", "wet_stone", group,
         x - 36.5, foundation_y, z, 3.0, foundation_h, 66.0)
    _box(specs, "conservatory-perimeter-foundation", "wet_stone", group,
         x + 36.5, foundation_y, z, 3.0, foundation_h, 66.0)
    # The rear wall is split around a 12 m garden exit.  This keeps the full
    # 58 m promenade continuous and removes the blank opaque terminus exposed
    # by the first-person interior review.
    for side in (-1, 1):
        _box(specs, "conservatory-perimeter-foundation", "wet_stone", group,
             x + side * 20.5, foundation_y, z + 31.5,
             29.0, foundation_h, 3.0)
    # Two 34 m front foundations meet at an exact 8 m entrance aperture.
    # This is deliberately smaller than the 12 m gameplay approach so the
    # arrival reads as a real threshold without narrowing the route collider.
    for side in (-1, 1):
        _box(specs, "conservatory-perimeter-foundation", "wet_stone", group,
             x + side * 21.0, foundation_y, z - 31.5,
             34.0, foundation_h, 3.0)
    _box(specs, "conservatory-interior-floor", "wet_stone", group,
         x, 0.04, z, 70.0, 0.16, 60.0)
    # Player-height evidence exposed the old 1.55 m slab as an opaque wall
    # across the lower half of the portal.  This is now a flush threshold
    # apron: a 1.65 m camera can cross it without a step or visual barricade.
    _box(specs, "conservatory-front-terrace", "white_marble", group,
         x, 0.14, z - 31.6, 40.0, 0.30, 6.0)

    if lod < 2:
        offsets = (-24.0, -12.0, 0.0, 12.0, 24.0)
        # The fan is a castle-scale macro silhouette, not five shallow sheds.
        # The west/near lobes remain tall so the fixed dual-camera composition
        # reads the greenhouse at ~40% frame height beside the palace.
        # The fixed dual camera sees the west flank.  A low-to-high fan keeps
        # all five vault crowns legible instead of letting the nearest lobe
        # collapse them into one dark rectangular shed.
        heights = (27.0, 33.0, 40.5, 38.0, 34.0)
    else:
        offsets = (-20.0, 0.0, 20.0)
        heights = (18.0, 28.0, 18.0)
    for lobe_index, (offset, height) in enumerate(zip(offsets, heights)):
        _add_vault_lobe(specs, cx=x + offset, base_y=9.0, z0=z - 27.0, z1=z + 28.0,
                        half_width=11.0 if lod < 2 else 13.0, height=height,
                        lod=lod, lobe_index=lobe_index)

    # Paired ventilation lanterns interrupt the long vault ridges and echo
    # the reference's botanical cupolas without exceeding the 50 m envelope.
    vent_specs = ((x-24.0, 36.15, 5.5), (x+24.0, 43.15, 3.9)) if lod < 2 else ((x-20.0, 27.2, 3.2),)
    for vent_x, vent_base, vent_height in vent_specs:
        drum_h = vent_height * 0.54
        _cylinder(specs, "conservatory-ventilation-lantern", "glass", group,
                  vent_x, vent_base + drum_h/2, z+4.0,
                  3.0 if lod == 0 else 2.6, drum_h,
                  12 if lod == 0 else 8, top_radius=2.55 if lod == 0 else 2.2)
        _cylinder(specs, "conservatory-ventilation-crown", "verdigris_bronze", group,
                  vent_x, vent_base + drum_h + (vent_height-drum_h)/2, z+4.0,
                  3.15 if lod == 0 else 2.75, vent_height-drum_h,
                  12 if lod == 0 else 8, top_radius=0.28)
        _cylinder(specs, "conservatory-ventilation-finial", "brass", group,
                  vent_x, vent_base + vent_height + 0.55, z+4.0,
                  0.18, 1.1, 8 if lod == 0 else 6, top_radius=0.035)

    # Monumental front portal follows the fan section rather than a gabled box.
    portal_points = _vault_points(x, 8.9, z - 28.1, 36.0, 29.0, 13 if lod == 0 else 8)
    for start, end in zip(portal_points, portal_points[1:]):
        _beam(specs, "conservatory-fan-portal-rib", "brass", group, start, end, 0.36, 0.28)
    _box(specs, "conservatory-portal-entablature", "white_marble", group,
         x, 8.55, z - 28.4, 76.0, 0.85, 1.4)
    # Exact 8 m wide, 8.6 m high open portal.  The opening is intentionally
    # free of glass cards and transverse gallery boxes.
    _box(specs, "conservatory-portal-left", "white_marble", group,
         x - 21.0, 5.8, z - 29.0, 34.0, 5.6, 3.0)
    _box(specs, "conservatory-portal-right", "white_marble", group,
         x + 21.0, 5.8, z - 29.0, 34.0, 5.6, 3.0)
    for portal_x in (x - 4.5, x + 4.5):
        _box(specs, "conservatory-portal-jamb", "brass", group,
             portal_x, 5.9, z - 30.7, 0.45, 8.8, 0.50)
    _beam(specs, "conservatory-portal-head", "brass", group,
          (x - 4.7, 10.15, z - 30.7), (x + 4.7, 10.15, z - 30.7), 0.34, 0.28)
    # Transparent entrance canopy: an unmistakable 8 m arrival marker that
    # stays above every 1.65 m clearance ray.
    # Keep the shallow canopy within 3 m of the canonical z=28 entrance so
    # the exported landmark perimeter still proves an exterior threshold.
    canopy_z0, canopy_z1 = z - 36.5, z - 29.8
    canopy_left = ((x-4.6, 9.55, canopy_z0), (x, 11.55, canopy_z0),
                   (x, 11.55, canopy_z1), (x-4.6, 9.55, canopy_z1))
    canopy_right = ((x, 11.55, canopy_z0), (x+4.6, 9.55, canopy_z0),
                    (x+4.6, 9.55, canopy_z1), (x, 11.55, canopy_z1))
    for corners in (canopy_left, canopy_right):
        _panel(specs, "conservatory-entrance-canopy-glass", "glass", group, corners, 0.08)
    for start, end in (
        ((x-4.6, 9.55, canopy_z0), (x-4.6, 9.55, canopy_z1)),
        ((x+4.6, 9.55, canopy_z0), (x+4.6, 9.55, canopy_z1)),
        ((x, 11.55, canopy_z0), (x, 11.55, canopy_z1)),
    ):
        _beam(specs, "conservatory-entrance-canopy-frame", "brass", group,
              start, end, 0.20, 0.15)
    _add_arcade(specs, cx=x-24.0, base_y=3.2, z=z-30.58, width=25.0,
                bay_count=4 if lod == 0 else 3 if lod == 1 else 2,
                material="white_marble", group=group,
                role_prefix="conservatory-base-arcade", lod=lod)
    _add_arcade(specs, cx=x+24.0, base_y=3.2, z=z-30.58, width=25.0,
                bay_count=4 if lod == 0 else 3 if lod == 1 else 2,
                material="white_marble", group=group,
                role_prefix="conservatory-base-arcade", lod=lod)
    for side in (-1, 1):
        side_x = x + side * 36.7
        for pier_index in range(6 if lod == 0 else 4 if lod == 1 else 3):
            pz = z - 24.0 + pier_index * (48.0 / (5 if lod == 0 else 3 if lod == 1 else 2))
            _box(specs, "conservatory-side-pilaster", "white_marble", group,
                 side_x, 6.0, pz, 1.1, 5.8, 1.1)
        _add_balustrade(specs, x=side_x-side*0.35, y=8.0, z=z, length=51.0, axis="z",
                        material="brass", group=group,
                        role_prefix="conservatory-side-balustrade", lod=lod)
        _add_side_arcade(
            specs, x=side_x-side*0.18, base_y=3.15, cz=z, length=51.0,
            bay_count=6 if lod == 0 else 4 if lod == 1 else 3,
            material="white_marble", group=group,
            role_prefix="conservatory-side-arcade", lod=lod,
        )

    # Internal planted promenades, water beds and a visible stair procession.
    # The former pair crossed the entire nave at head height, reading as two
    # opaque black lintels in every first-person arrival/interior view.  Run
    # the galleries longitudinally along the side aisles instead.  The west
    # gallery still overlaps the authored stair landing, while the central
    # water axis and fan-vault silhouette remain continuously readable.
    for walk_x in (x - 18.5, x + 18.5):
        _box(specs, "conservatory-upper-walk", "dark_wood", group,
             walk_x, 7.95, z, 4.0, 0.55, 50.0)
    for rail_x in (x - 20.5, x - 16.5, x + 16.5, x + 20.5):
        _add_balustrade(specs, x=rail_x, y=8.15, z=z, length=47.0, axis="z",
                        material="brass", group=group,
                        role_prefix="conservatory-upper-walk-rail", lod=lod)
    # A continuous 8 m promenade connects threshold to the rear garden.  Two
    # flanking water beds preserve the lush irrigation identity without
    # turning the route into a pool or a visual dead end.
    _box(specs, "conservatory-central-promenade", "white_marble", group,
         x, 0.24, z + 1.5, 8.0, 0.36, 58.0)
    for water_x in (x - 9.0, x + 9.0):
        _box(specs, "conservatory-interior-water", "water", group,
             water_x, 0.17, z + 2.0, 8.0, 0.18, 40.0)
        for bank_x in (water_x - 4.15, water_x + 4.15):
            _box(specs, "conservatory-interior-water-coping", "wet_stone", group,
                 bank_x, 0.26, z + 2.0, 0.45, 0.52, 40.0)
    step_count = 14 if lod == 0 else 9 if lod == 1 else 4
    step_height = max(0.36, 7.7 / step_count + 0.12)
    step_depth = max(2.2, 18.0 / step_count + 0.40)
    for stair_x, direction in ((x - 18.5, 1.0), (x + 18.5, 1.0)):
        for index in range(step_count):
            t = (index + 0.5) / step_count
            _box(specs, "conservatory-interior-stair", "white_marble", group,
                 stair_x, 0.22 + t * 7.58, z - 22.0 + direction * t * 18.0,
                 5.0, step_height, step_depth)
    # Two connected rear belvederes give each stair/walk a visible upper-level
    # destination without recreating an opaque transverse lintel.
    for lookout_x in (x-15.0, x+15.0):
        _box(specs, "conservatory-upper-lookout", "white_marble", group,
             lookout_x, 7.95, z+25.0, 7.0, 0.55, 5.0)
        outer_x = lookout_x + (3.45 if lookout_x < x else -3.45)
        _add_balustrade(specs, x=outer_x, y=8.15, z=z+25.0, length=4.4,
                        axis="z", material="brass", group=group,
                        role_prefix="conservatory-upper-lookout-rail", lod=lod)
    tree_positions = ((x - 20, z - 6), (x + 20, z - 6), (x - 18, z + 17),
                      (x + 18, z + 17), (x - 28, z + 6), (x + 28, z + 6))
    for tx, tz in tree_positions[:6 if lod == 0 else 4 if lod == 1 else 2]:
        _add_tree(specs, tx, tz, 10.0 if abs(tx - x) > 10 else 8.5, group, lod, planter=True)
    if lod == 0:
        # Dense planted aisles remain outside the 8 m central walk.
        for planter_x in (x - 15.0, x + 15.0):
            for planter_z in (z - 15.0, z, z + 15.0):
                _box(specs, "conservatory-planted-bed", "white_marble", group,
                     planter_x, 0.55, planter_z, 7.0, 1.1, 8.5)
                _box(specs, "conservatory-planter-soil", "dark_wood", group,
                     planter_x, 1.16, planter_z, 6.3, 0.14, 7.8)
                for plant_index in range(5):
                    px = planter_x - 2.4 + plant_index * 1.2
                    height = 2.4 + (plant_index % 3) * 0.55
                    _add_plant_cluster(specs, px, planter_z, height, group, lod,
                                       "conservatory-dense-planting")
        # The main beds above sit too far into the fan lobes to read at the
        # threshold.  Two narrow botanical borders begin immediately behind
        # the 8 m opening, remain outside its x=48..56 clearance, and create a
        # visible planted allée without any opaque object entering the walk.
        for border_x in (x - 5.8, x + 5.8):
            for border_z in (z - 20.0, z - 10.0, z, z + 10.0):
                _box(specs, "conservatory-botanical-border", "white_marble", group,
                     border_x, 0.34, border_z, 3.4, 0.68, 7.4)
                _box(specs, "conservatory-botanical-soil", "dark_wood", group,
                     border_x, 0.73, border_z, 2.9, 0.14, 6.9)
                for plant_index in range(3):
                    plant_z = border_z - 2.25 + plant_index * 2.25
                    plant_h = 3.8 + ((plant_index + int(border_z)) % 3) * 0.8
                    _add_plant_cluster(specs, border_x, plant_z, plant_h, group, lod,
                                       "conservatory-botanical-plant")
        for side in (-1, 1):
            for vine_index in range(5):
                vx = x + side * (27.0 + vine_index * 1.5)
                vz = z - 25.8 + vine_index * 10.5
                vine_height = 5.8 + (vine_index % 3)
                _cylinder(specs, "conservatory-hanging-vine", "foliage_dark", group,
                          vx, 3.08 + vine_height / 2, vz,
                          0.45, vine_height, 8, top_radius=0.18)
        for px in (x-28.0, x-16.0, x+16.0, x+28.0):
            _add_tree(specs, px, z-33.5, 7.5, group, lod, planter=True)

    # Open rear garden arch and a real exterior botanical destination replace
    # the civic blank wall that previously terminated the interior view.  The
    # arch columns stay outside the central 6.4 m proof cone; its crown is high
    # enough for all player-height rays to pass beneath it.
    _add_arch(specs, cx=x, base_y=0.12, z=z+30.45, bay_width=13.8,
              spring_y=5.0, depth=0.82, material="white_marble", group=group,
              role_prefix="conservatory-rear-garden-arch",
              segments=11 if lod == 0 else 7 if lod == 1 else 5)
    _box(specs, "conservatory-rear-garden-threshold", "white_marble", group,
         x, 0.16, z+31.2, 12.0, 0.32, 3.6)
    for water_x in (x-8.5, x+8.5):
        _box(specs, "rear-botanical-water", "water", "garden-city",
             water_x, 0.08, z+43.0, 7.0, 0.16, 17.0)
        _box(specs, "rear-botanical-bank", "white_marble", "garden-city",
             water_x, 0.26, z+43.0, 7.8, 0.52, 17.8)
        _box(specs, "rear-botanical-water", "water", "garden-city",
             water_x, 0.54, z+43.0, 6.7, 0.14, 16.7)
    # A transparent water sculpture gives the open rear arch a botanical
    # focal point while keeping the full central route ray-clear.
    for fountain_x, fountain_h in ((x-2.2, 4.8), (x, 7.0), (x+2.2, 5.6)):
        _cylinder(specs, "rear-botanical-water-sculpture", "water", "garden-city",
                  fountain_x, fountain_h/2, z+44.5, 0.72,
                  fountain_h, 10 if lod == 0 else 7, top_radius=0.22)
    if lod == 0:
        for garden_x in (x-13.0, x+13.0):
            for garden_z in (z+37.0, z+48.0):
                _add_plant_cluster(specs, garden_x, garden_z, 5.2,
                                   "garden-city", lod, "rear-botanical-plant")

    # Slender irrigation tower gives the citadel a second vertical register.
    tower_x, tower_z = x + 31.0, z + 8.0
    _box(specs, "conservatory-tower-pad", "wet_stone", group,
         tower_x, 1.51, tower_z, 10.0, 3.22, 10.0)
    _cylinder(specs, "conservatory-irrigation-tower", "white_marble", group,
              tower_x, 20.55, tower_z, 4.2, 34.9, 12 if lod == 0 else 8)
    for level in range(3 if lod < 2 else 2):
        _cylinder(specs, "conservatory-irrigation-balcony", "verdigris_bronze", group,
                  tower_x, 10.0 + level * 8.5, tower_z, 5.4, 0.55, 12 if lod == 0 else 8)
    _cylinder(specs, "conservatory-irrigation-crown", "verdigris_bronze", group,
              tower_x, 42.0, tower_z, 5.5, 8.0, 12 if lod == 0 else 8, top_radius=1.3)
    _cylinder(specs, "conservatory-irrigation-finial", "brass", group,
              tower_x, 47.7, tower_z, 0.34, 3.6, 8 if lod == 0 else 6, top_radius=0.05)


def _add_bridge(specs: list[dict], x: float, z: float, axis: str, lod: int, *, hero: bool = False) -> None:
    group = "garden-city"
    length = 14.0 if hero else 11.0
    width = 8.0 if hero else 6.0
    w, d = (length, width) if axis == "x" else (width, length)
    _box(specs, "canal-bridge-deck", "white_marble", group, x, 0.78, z, w, 1.30, d)
    # Arched parapets read at 1.65 m and keep the water crossing identity.
    rail_offset = d / 2 - 0.35 if axis == "x" else w / 2 - 0.35
    segments = 7 if lod == 0 else 5 if lod == 1 else 3
    for side in (-1, 1):
        points = []
        for index in range(segments + 1):
            t = index / segments
            along = -length / 2 + t * length
            rise = 1.1 + math.sin(math.pi * t) * (1.2 if hero else 0.7)
            if axis == "x":
                points.append((x + along, rise, z + side * rail_offset))
            else:
                points.append((x + side * rail_offset, rise, z + along))
        for start, end in zip(points, points[1:]):
            _beam(specs, "canal-bridge-arched-parapet", "brass", group, start, end,
                  0.24 if lod == 0 else 0.30, 0.20)


def _add_canals_and_bridges(specs: list[dict], lod: int) -> None:
    # Cross-shaped real water network flanks—never replaces—the 16 m canonical roads.
    for x in (-18.0, 18.0):
        _box(specs, "lush-canal-water", "water", "garden-city", x, 0.07, 0.0, 9.0, 0.18, 304.0)
        for bank_x in (x - 4.2, x + 4.2):
            _box(specs, "canal-bank-coping", "wet_stone", "garden-city", bank_x, 0.16, 0.0,
                 1.3, 0.52, 304.0)
    for z in (-18.0, 18.0):
        _box(specs, "lush-canal-water", "water", "garden-city", 0.0, 0.07, z, 304.0, 0.18, 9.0)
        for bank_z in (z - 4.2, z + 4.2):
            _box(specs, "canal-bank-coping", "wet_stone", "garden-city", 0.0, 0.16, bank_z,
                 304.0, 0.52, 1.3)
    # Landmark-owned basins connect the water identity into each hero footprint.
    _box(specs, "palace-ceremonial-canal", "water", "garden-city", -60.0, 0.08, -41.0, 17.0, 0.18, 25.0)
    _box(specs, "conservatory-irrigation-canal", "water", "garden-city", 52.0, 0.08, 43.0, 15.0, 0.18, 23.0)

    for x in (-18.0, 18.0):
        for z in (-106.0, -54.0, 54.0, 106.0):
            _add_bridge(specs, x, z, "x", lod)
    for z in (-18.0, 18.0):
        for x in (-112.0, -64.0, 64.0, 112.0):
            _add_bridge(specs, x, z, "z", lod)
    # Hero bridges follow the north/south approaches.  The old transverse
    # orientation put arched parapets directly across each arrival sightline.
    _add_bridge(specs, -60.0, -45.0, "z", lod, hero=True)
    _add_bridge(specs, 52.0, 43.0, "z", lod, hero=True)


def _add_civic_building(specs: list[dict], index: int, x: float, z: float, w: float, d: float,
                        h: float, lod: int) -> None:
    group = "civic-wings"
    # Dense-world contract: even the secondary Nakaniwa district is primarily
    # tall.  The former 18–24 m shells left half the fixed frame as empty sky
    # and made the heroes look like isolated props on a plaza.
    h = max(h, 30.0 + (index % 3) * 2.0)
    material = "honey_stone" if index % 3 else "white_marble"
    _box(specs, "layered-civic-wing", material, group, x, h / 2 - 0.05, z, w, h + 0.10, d,
         blocks_gameplay=True)
    _box(specs, "civic-stepped-plinth", "wet_stone", group, x, 0.28, z,
         w + 1.8, 0.56, d + 1.8)
    _box(specs, "civic-stone-belt", "white_marble", group, x, min(6.2, h*0.32), z,
         w + 0.72, 0.48, d + 0.72)
    _box(specs, "civic-roof-belt", "verdigris_bronze", group, x, h + 0.12, z, w + 1.8, 0.45, d + 1.8)
    upper_h = h * 0.36
    _box(specs, "civic-upper-pavilion", material, group, x, h + upper_h / 2, z,
         w * 0.68, upper_h, d * 0.70)
    _box(specs, "civic-upper-roof", "verdigris_bronze", group, x, h + upper_h + 0.12, z,
         w * 0.74, 0.42, d * 0.76)
    civic_roof_base = h + upper_h + 0.28
    civic_roof_height = max(1.3, min(2.8 + (index % 3) * 0.55, 49.35 - civic_roof_base))
    _add_deep_gable_roof(
        specs, cx=x, base_y=civic_roof_base, cz=z, width=w*0.72, depth=d*0.74,
        height=civic_roof_height, axis="z" if d >= w else "x",
        material="verdigris_bronze", group=group, role_prefix="civic-deep-roof", lod=lod,
    )
    if lod == 0 and index % 2 == 0 and h + upper_h <= 41.0:
        lantern_y = h + upper_h + 2.0
        _cylinder(specs, "civic-roof-lantern", material, group, x, lantern_y, z,
                  2.1 + (index % 3) * 0.25, 3.6, 10, top_radius=1.75)
        _cylinder(specs, "civic-roof-lantern-cap", "verdigris_bronze", group,
                  x, lantern_y + 2.65, z, 2.7, 1.8, 10, top_radius=0.25)
        _cylinder(specs, "civic-roof-finial", "brass", group,
                  x, lantern_y + 4.2, z, 0.20, 1.8, 8, top_radius=0.035)
    # Large facade bays and a human-scale entrance replace blank cuboids.
    front_z = z - d / 2 - 0.08
    rear_z = z + d / 2 + 0.08
    door_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for bay in range(door_count):
        bx = x + (bay - (door_count - 1) / 2) * min(6.0, w / max(2, door_count))
        _box(specs, "civic-recessed-bay", "dark_wood", group, bx, 3.0, front_z, 2.3, 4.8, 0.34)
        _box(specs, "civic-warm-window", "warm_window", group, bx, 5.1, front_z - 0.20, 1.45, 1.2, 0.12)
        _box(specs, "civic-rear-recessed-bay", "dark_wood", group,
             bx, 3.0, rear_z, 2.3, 4.8, 0.34)
        _box(specs, "civic-warm-window", "warm_window", group,
             bx, 5.1, rear_z + 0.20, 1.45, 1.2, 0.12)
    if lod < 2:
        facade_bays = max(4, min(9, int(w // (4.0 if lod == 0 else 5.5))))
        floor_count = max(1, min(3, int(h // 8.0)))
        for floor in range(floor_count):
            window_y = 7.5 + floor * 5.2
            if window_y + 1.2 >= h:
                continue
            for bay in range(facade_bays):
                window_x = x - w * 0.40 + bay * (w * 0.80 / max(1, facade_bays - 1))
                _box(specs, "civic-warm-window", "warm_window", group,
                     window_x, window_y, front_z - 0.20, 1.35, 1.75, 0.13)
                _box(specs, "civic-warm-window", "warm_window", group,
                     window_x, window_y, rear_z + 0.20, 1.35, 1.75, 0.13)
        side_bays = max(2, min(5, int(d // 5.5)))
        for side in (-1, 1):
            side_x = x + side * (w/2 + 0.09)
            for bay in range(side_bays):
                side_z = z - d*0.34 + bay * (d*0.68/max(1, side_bays-1))
                _box(specs, "civic-side-pilaster", "white_marble", group,
                     side_x, min(6.8, h*0.38), side_z, 0.42, min(10.0, h*0.58), 0.66)
                if bay % 2 == index % 2:
                    _box(specs, "civic-side-window", "warm_window", group,
                         side_x + side*0.20, min(7.0, h*0.42), side_z,
                         0.12, 1.65, 1.25)
    if lod < 2 and w >= 18.0:
        _add_arcade(specs, cx=x, base_y=0.0, z=front_z - 0.42, width=w * 0.84,
                    bay_count=4 if lod == 0 else 3, material="white_marble", group=group,
                    role_prefix="civic-ground-arcade", lod=lod)
    if lod == 0 and index % 2 == 1:
        _add_facade_lattice(
            specs, cx=x, base_y=max(7.0, h*0.48), z=front_z-0.38,
            width=min(8.0, w*0.42), height=min(5.0, h*0.24),
            material="brass", group=group, role_prefix="civic-stone-screen", lod=lod,
        )
        _add_balustrade(specs, x=x, y=min(h-1.8, 10.5), z=front_z-0.60,
                        length=w*0.68, axis="x", material="white_marble", group=group,
                        role_prefix="civic-planted-balcony", lod=lod)


def _add_garden_city(specs: list[dict], lod: int) -> None:
    # Wet stone is visible between real canals; the central road strips remain open.
    _box(specs, "wet-palace-garden-plaza", "wet_stone", "garden-city", 0.0, -0.30, 0.0,
         320.0, 0.60, 320.0)
    _box(specs, "canonical-road-visual", "white_marble", "garden-city", 0.0, 0.02, 0.0,
         16.0, 0.10, 312.0)
    _box(specs, "canonical-road-visual", "white_marble", "garden-city", 0.0, 0.025, 0.0,
         312.0, 0.11, 16.0)
    # Flush stone joints and darker inlay bands break the runway-like road
    # without changing collision or narrowing its 16 m traversal contract.
    if lod < 2:
        for coordinate in range(-132, 133, 22 if lod == 0 else 44):
            _box(specs, "ceremonial-road-inlay", "wet_stone", "garden-city",
                 0.0, 0.085, float(coordinate), 15.2, 0.04, 0.26)
            _box(specs, "ceremonial-road-inlay", "wet_stone", "garden-city",
                 float(coordinate), 0.09, 0.0, 0.26, 0.04, 15.2)
    _add_canals_and_bridges(specs, lod)

    # Four stepped garden rooms replace the old flat central plaza.  Their
    # inner edges stay beyond the canal copings and the canonical ±8 m road,
    # while the nested pale/warm/green bands create near/mid/far depth from the
    # fixed dual camera and every cardinal spawn.
    terrace_centres = ((-36.0, -36.0), (36.0, -36.0), (-36.0, 36.0), (36.0, 36.0))
    for terrace_index, (terrace_x, terrace_z) in enumerate(terrace_centres):
        for tier, (size, height) in enumerate(((24.0, 0.32), (20.0, 0.62), (15.5, 0.92))):
            _box(specs, "stepped-garden-terrace", "white_marble" if tier != 1 else "honey_stone",
                 "garden-city", terrace_x, height/2, terrace_z,
                 size, height, size)
        _box(specs, "stepped-garden-soil", "dark_wood", "garden-city",
             terrace_x, 1.00, terrace_z, 13.8, 0.18, 13.8)
        # A deliberate asymmetry prevents the four rooms from reading as
        # stamped copies while keeping the circulation clear.
        rill_axis = "x" if terrace_index % 2 == 0 else "z"
        rill_w, rill_d = ((11.5, 2.2) if rill_axis == "x" else (2.2, 11.5))
        _box(specs, "stepped-garden-rill", "water", "garden-city",
             terrace_x, 1.10, terrace_z, rill_w, 0.16, rill_d)
        if lod < 2:
            for side in (-1, 1):
                planter_x = terrace_x + side * (7.2 if rill_axis == "z" else 0.0)
                planter_z = terrace_z + side * (7.2 if rill_axis == "x" else 0.0)
                _box(specs, "terrace-retaining-planter", "white_marble", "garden-city",
                     planter_x, 1.22, planter_z,
                     5.8 if rill_axis == "z" else 13.0, 0.72,
                     13.0 if rill_axis == "z" else 5.8)
                _box(specs, "terrace-planter-soil", "dark_wood", "garden-city",
                     planter_x, 1.62, planter_z,
                     5.2 if rill_axis == "z" else 12.4, 0.14,
                     12.4 if rill_axis == "z" else 5.2)
        if lod == 0:
            _add_garden_furniture_cluster(
                specs,
                terrace_x + (-8.5 if terrace_index in (0, 2) else 8.5),
                terrace_z + (8.5 if terrace_index in (0, 1) else -8.5),
                "x" if terrace_index % 2 else "z",
                lod,
            )

    # Repeated low planters and tree crowns layer the avenue without placing a
    # single opaque object in the 16 m road.  These are the lived-in garden
    # details visible in the reference foreground, not generic plaza boxes.
    if lod < 2:
        avenue_zs = (-102.0, -72.0, -42.0, 42.0, 72.0, 102.0)
        for avenue_index, avenue_z in enumerate(avenue_zs):
            for side in (-1, 1):
                planter_x = side * (12.8 + (avenue_index % 2) * 1.6)
                _box(specs, "avenue-tier-planter", "honey_stone", "garden-city",
                     planter_x, 0.52, avenue_z, 5.8, 1.04, 7.4)
                _box(specs, "avenue-tier-soil", "dark_wood", "garden-city",
                     planter_x, 1.10, avenue_z, 5.1, 0.16, 6.7)
                if lod == 0:
                    for plant_index in range(3):
                        plant_z = avenue_z - 2.1 + plant_index * 2.1
                        plant_h = 1.8 + ((avenue_index + plant_index) % 2) * 0.8
                        _cylinder(specs, "avenue-layered-shrub", "foliage_light", "garden-city",
                                  planter_x, 1.18 + plant_h/2, plant_z,
                                  0.92, plant_h, 8, top_radius=0.28)

    buildings = (
        (-128, -118, 32, 30, 24), (-91, -126, 28, 24, 29), (-28, -132, 32, 22, 26),
        (37, -132, 34, 22, 31), (91, -124, 30, 26, 28), (128, -93, 24, 34, 34),
        (130, -43, 24, 34, 25), (130, 47, 24, 34, 30), (125, 104, 30, 30, 35),
        (86, 132, 30, 22, 26), (44, 132, 28, 22, 30), (-44, 132, 28, 22, 27),
        (-92, 128, 30, 26, 33), (-128, 92, 26, 34, 28), (-130, 40, 24, 30, 31),
        (-130, -18, 24, 26, 24), (-126, -72, 28, 30, 32), (102, -18, 28, 22, 22),
        (94, 12, 26, 22, 20), (-132, 10, 22, 24, 23), (-120, 60, 28, 22, 21),
        # Keep the canonical north/south road and its flanking canal vistas open.
        # The former (6, -90) pavilion sat directly in the 16 m road and obscured
        # the reference-height establishing view.
        (62, -98, 20, 26, 18), (110, 72, 22, 26, 22), (-45, 102, 24, 20, 20),
    )
    keep = len(buildings) if lod == 0 else 20 if lod == 1 else 14
    for index, data in enumerate(buildings[:keep]):
        _add_civic_building(specs, index, *data, lod)

    tree_positions = (
        (-145, -140, 14), (-112, -145, 12), (-70, -142, 11), (-20, -144, 13),
        (67, -145, 12), (118, -140, 14), (145, -112, 13), (145, -62, 12),
        (145, 20, 13), (145, 62, 12), (142, 118, 14), (112, 145, 12),
        (62, 145, 13), (20, 145, 12), (-62, 145, 13), (-118, 142, 14),
        (-145, 110, 13), (-145, 55, 12), (-145, -20, 13), (-145, -55, 12),
        (-44, -18, 11), (44, -18, 10), (-42, 18, 10), (42, 18, 11),
        (-90, -20, 12), (90, 20, 12), (-20, 92, 11), (34, -100, 11),
        (-48, 42, 11), (-34, 64, 10), (34, -48, 11), (48, -34, 10),
        (-42, -12, 10), (42, 12, 10), (-12, 42, 9), (12, -42, 9),
    )
    keep_trees = len(tree_positions) if lod == 0 else 20 if lod == 1 else 10
    for tx, tz, th in tree_positions[:keep_trees]:
        _add_tree(specs, tx, tz, th, "garden-city", lod, planter=True)

    # Player-height garden rooms frame the main axis from the canonical north
    # and south spawns.  Everything stays outside the ±8 m road strip.
    if lod < 2:
        room_zs = (-116.0, -82.0, 82.0, 116.0)
        for room_z in room_zs:
            for side in (-1, 1):
                px = side * 11.2
                _box(specs, "garden-pergola-post", "white_marble", "garden-city",
                     px, 2.7, room_z-4.0, 0.42, 5.4, 0.42)
                _box(specs, "garden-pergola-post", "white_marble", "garden-city",
                     px, 2.7, room_z+4.0, 0.42, 5.4, 0.42)
                _beam(specs, "garden-pergola-header", "dark_wood", "garden-city",
                      (px, 5.25, room_z-4.2), (px, 5.25, room_z+4.2), 0.25, 0.20)
                _cylinder(specs, "garden-pergola-vine", "foliage_dark", "garden-city",
                          px-side*0.35, 4.0, room_z, 0.34, 3.8, 8, top_radius=0.16)
                if lod == 0:
                    _add_flower_planter(specs, side*13.8, room_z, 7.0, "z", lod)

    # The fixed reference camera stands on the north-west garden diagonal.
    # A dedicated low forecourt replaces the previous featureless brown
    # foreground with connected stepped stone, a real water court and planted
    # edges.  All pieces remain under waist height and outside both canonical
    # 16 m road strips, so the camera and route stay physically clear.
    for tier, (size_x, size_z, height) in enumerate((
        (38.0, 29.0, 0.18), (33.0, 24.0, 0.36), (28.0, 19.0, 0.54),
    )):
        _box(specs, "reference-forecourt-terrace",
             "white_marble" if tier != 1 else "honey_stone", "garden-city",
             -77.0, height / 2, 64.0, size_x, height, size_z)
    _box(specs, "reference-forecourt-water", "water", "garden-city",
         -77.0, 0.61, 64.0, 21.0, 0.14, 9.0)
    _box(specs, "reference-forecourt-bridge", "white_marble", "garden-city",
         -77.0, 0.78, 64.0, 6.0, 0.42, 11.0)
    for planter_x in (-91.5, -62.5):
        _box(specs, "reference-forecourt-planter", "honey_stone", "garden-city",
             planter_x, 0.62, 64.0, 5.0, 1.24, 18.0)
        _box(specs, "reference-forecourt-soil", "dark_wood", "garden-city",
             planter_x, 1.29, 64.0, 4.35, 0.14, 17.2)
        if lod == 0:
            for plant_index in range(5):
                plant_z = 57.5 + plant_index * 3.25
                plant_h = 2.2 + (plant_index % 3) * 0.65
                _add_plant_cluster(specs, planter_x, plant_z, plant_h,
                                   "garden-city", lod, "reference-forecourt-plant")

    if lod == 0:
        for x, z, length, axis in (
            (-86, -18, 18, "x"), (86, 18, 18, "x"), (-18, 78, 20, "z"),
            (18, -78, 20, "z"), (-112, 18, 14, "x"), (112, -18, 14, "x"),
        ):
            _add_flower_planter(specs, x, z, length, axis, lod)
        for x, z, axis in (
            (-35.0, -31.0, "x"), (35.0, -31.0, "x"),
            (-35.0, 31.0, "x"), (35.0, 31.0, "x"),
            (-31.0, -70.0, "z"), (31.0, -70.0, "z"),
            (-31.0, 72.0, "z"), (31.0, 72.0, "z"),
        ):
            _add_garden_furniture_cluster(specs, x, z, axis, lod)

    # Foreground framing arcade creates the reference's strong near layer.
    _add_arcade(specs, cx=-92.0, base_y=0.0, z=-147.0, width=44.0,
                bay_count=6 if lod == 0 else 4 if lod == 1 else 3,
                material="white_marble", group="foreground", role_prefix="foreground-arcade", lod=lod)
    _add_arcade(specs, cx=94.0, base_y=0.0, z=-147.0, width=42.0,
                bay_count=6 if lod == 0 else 4 if lod == 1 else 3,
                material="honey_stone", group="foreground", role_prefix="foreground-arcade", lod=lod)


def build_specs(lod: int = 0) -> list[dict]:
    """Return deterministic A18 geometry specs without importing Blender."""
    if lod not in LOD_API:
        raise ValueError(f"unsupported LOD: {lod}")
    specs: list[dict] = []
    _add_garden_city(specs, lod)
    _add_palace(specs, lod)
    _add_conservatory(specs, lod)
    if lod == 2:
        # HLOD preserves roof planes and primary rails, not every small post or
        # ornamental timber frame.  This keeps LOD2 below 12% of LOD0 while the
        # two hero silhouettes, canal crossings and fan ribs remain intact.
        drop_roles = {
            "conservatory-upper-walk-rail-post",
            "conservatory-upper-walk-rail-rail",
            "conservatory-side-balustrade-post",
            "conservatory-side-balustrade-rail",
            "civic-deep-roof-gable-frame",
        }
        specs = [spec for spec in specs if spec["role"] not in drop_roles]
    return specs


def emit_specs_to_builder(builder, specs: Iterable[dict],
                          material_map: dict[str, str] | None = None) -> list[dict]:
    """Emit an explicit spec subset using the production MeshBuilder API."""
    specs = list(specs)
    material_map = DEFAULT_INTEGRATION_MATERIAL_MAP if material_map is None else material_map
    for spec in specs:
        key = material_map.get(spec["material"], spec["material"])
        if spec["kind"] == "box":
            builder.add_box(spec["x"], spec["y"], spec["z"], spec["w"], spec["h"], spec["d"], key)
        elif spec["kind"] == "beam":
            builder.add_beam(spec["start"], spec["end"], spec["width"], spec["depth"], key)
        elif spec["kind"] == "cylinder":
            builder.add_cylinder(spec["x"], spec["y"], spec["z"], spec["radius"], spec["height"],
                                 key, spec["segments"], spec["topRadius"])
        elif spec["kind"] == "panel":
            if hasattr(builder, "add_surface_panel"):
                builder.add_surface_panel(spec["corners"], spec["thickness"], key)
            else:
                builder.add_sloped_panel(spec["corners"], spec["thickness"], key)
        else:
            raise ValueError(f"unsupported spec kind: {spec['kind']}")
    return specs


def emit_to_builder(builder, lod: int = 0, material_map: dict[str, str] | None = None) -> list[dict]:
    """Emit all deterministic Nakaniwa specs into one compatible builder."""
    return emit_specs_to_builder(builder, build_specs(lod), material_map)


def connection_metadata() -> dict:
    return {
        "version": REFERENCE_MATCH_VERSION,
        "stageId": STAGE_ID,
        "canonicalBounds": dict(CANONICAL_BOUNDS),
        "roads": [dict(item) for item in CANONICAL_ROADS],
        "playerSpawns": [list(item) for item in CANONICAL_PLAYER_SPAWNS],
        "landmarks": [dict(item) for item in LANDMARKS],
        "connectionMap": [dict(item) for item in CONNECTION_MAP],
        "referenceDualCamera": dict(REFERENCE_DUAL_CAMERA),
        "conservatoryThresholdCamera": dict(CONSERVATORY_THRESHOLD_CAMERA),
        "conservatoryInteriorCamera": dict(CONSERVATORY_INTERIOR_CAMERA),
        "lodApi": LOD_API,
        "reference": {"path": REFERENCE_PATH, "sha256": REFERENCE_SHA256},
    }


def spec_bounds(spec: dict) -> tuple[float, float, float, float, float, float]:
    """Return runtime AABB as minX,minY,minZ,maxX,maxY,maxZ."""
    if spec["kind"] == "box":
        return (spec["x"] - spec["w"] / 2, spec["y"] - spec["h"] / 2, spec["z"] - spec["d"] / 2,
                spec["x"] + spec["w"] / 2, spec["y"] + spec["h"] / 2, spec["z"] + spec["d"] / 2)
    if spec["kind"] == "cylinder":
        radius = max(spec["radius"], spec["topRadius"])
        return (spec["x"] - radius, spec["y"] - spec["height"] / 2, spec["z"] - radius,
                spec["x"] + radius, spec["y"] + spec["height"] / 2, spec["z"] + radius)
    points = spec["corners"] if spec["kind"] == "panel" else (spec["start"], spec["end"])
    margin = spec.get("thickness", max(spec.get("width", 0), spec.get("depth", 0)))
    return (min(p[0] for p in points) - margin, min(p[1] for p in points) - margin,
            min(p[2] for p in points) - margin, max(p[0] for p in points) + margin,
            max(p[1] for p in points) + margin, max(p[2] for p in points) + margin)


def reference_camera_frame_metrics(lod: int = 0, aspect: float = 16 / 9) -> dict:
    """Project deterministic hero bounds into the fixed 1.65 m camera frame.

    This pure-python preflight is intentionally conservative: every explicit
    primitive contributes its runtime AABB corners.  The Blender render gate
    repeats the measurement from exported mesh bounds and owns the final
    verdict, but a module edit can no longer silently shrink either hero.
    """
    location = REFERENCE_DUAL_CAMERA["location"]
    target = REFERENCE_DUAL_CAMERA["target"]

    def sub(a, b):
        return tuple(a[i] - b[i] for i in range(3))

    def dot(a, b):
        return sum(a[i] * b[i] for i in range(3))

    def cross(a, b):
        return (
            a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0],
        )

    def unit(v):
        length = math.sqrt(dot(v, v))
        return tuple(value / length for value in v)

    forward = unit(sub(target, location))
    right = unit(cross(forward, (0.0, 1.0, 0.0)))
    up = unit(cross(right, forward))
    tan_half_x = 18.0 / REFERENCE_DUAL_CAMERA["lensMm"]
    tan_half_y = tan_half_x / aspect
    hero_metrics = []
    specs = build_specs(lod)
    for landmark in LANDMARKS:
        points = []
        for spec in specs:
            if spec["group"] != landmark["id"]:
                continue
            min_x, min_y, min_z, max_x, max_y, max_z = spec_bounds(spec)
            points.extend(
                (px, py, pz)
                for px in (min_x, max_x)
                for py in (min_y, max_y)
                for pz in (min_z, max_z)
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
        raw_height = max(ys) - min(ys)
        visible_height = max(0.0, min(1.0, max(ys)) - max(0.0, min(ys)))
        hero_metrics.append({
            "id": landmark["id"],
            "rawFrameHeightRatio": raw_height,
            "visibleFrameHeightRatio": visible_height,
            "frameBounds": (min(xs), min(ys), max(xs), max(ys)),
        })
    accepted_min, accepted_max = REFERENCE_DUAL_CAMERA["acceptedFrameHeightRatio"]
    return {
        "camera": dict(REFERENCE_DUAL_CAMERA),
        "heroes": hero_metrics,
        "passed": all(
            accepted_min <= item["visibleFrameHeightRatio"] <= accepted_max
            for item in hero_metrics
        ),
    }


class PrototypeMeshBuilder:
    """Material-batched explicit mesh builder used only by the private prototype."""

    def __init__(self, collection, materials):
        self.collection = collection
        self.materials = materials
        self.parts: dict[str, dict[str, list]] = defaultdict(lambda: {"verts": [], "faces": []})

    @staticmethod
    def _rv(point):
        # Runtime X/Y-up/Z-plan -> Blender X/Y-plan/Z-up.
        return (float(point[0]), float(point[2]), float(point[1]))

    def _part(self, key):
        return self.parts[key]

    def add_box(self, x, y, z, w, h, d, key="wet_stone"):
        part = self._part(key)
        base = len(part["verts"])
        hx, hy, hz = w / 2, h / 2, d / 2
        runtime = ((x-hx,y-hy,z-hz),(x+hx,y-hy,z-hz),(x+hx,y-hy,z+hz),(x-hx,y-hy,z+hz),
                   (x-hx,y+hy,z-hz),(x+hx,y+hy,z-hz),(x+hx,y+hy,z+hz),(x-hx,y+hy,z+hz))
        part["verts"].extend(self._rv(p) for p in runtime)
        part["faces"].extend((base+a,base+b,base+c,base+d0) for a,b,c,d0 in
                             ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)))

    def add_beam(self, start, end, width, depth, key="brass"):
        dx, dy, dz = (end[i] - start[i] for i in range(3))
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 1e-6:
            return
        fx, fy, fz = dx/length, dy/length, dz/length
        ux, uy, uz = ((0.0, 1.0, 0.0) if abs(fy) < 0.96 else (1.0, 0.0, 0.0))
        rx, ry, rz = fy*uz-fz*uy, fz*ux-fx*uz, fx*uy-fy*ux
        rl = math.sqrt(rx*rx+ry*ry+rz*rz)
        rx, ry, rz = rx/rl, ry/rl, rz/rl
        upx, upy, upz = ry*fz-rz*fy, rz*fx-rx*fz, rx*fy-ry*fx
        part = self._part(key)
        base = len(part["verts"])
        for point in (start, end):
            for sx, sy in ((-1,-1),(1,-1),(1,1),(-1,1)):
                runtime = (point[0]+rx*width*sx+upx*depth*sy,
                           point[1]+ry*width*sx+upy*depth*sy,
                           point[2]+rz*width*sx+upz*depth*sy)
                part["verts"].append(self._rv(runtime))
        part["faces"].extend((base+a,base+b,base+c,base+d0) for a,b,c,d0 in
                             ((0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(0,3,2,1),(4,5,6,7)))

    def add_cylinder(self, x, y, z, radius, height, key="brass", segments=12, top_radius=None):
        top_radius = radius if top_radius is None else top_radius
        part = self._part(key)
        base = len(part["verts"])
        for ring_radius, yy in ((radius, y-height/2), (top_radius, y+height/2)):
            for index in range(segments):
                angle = math.tau * index / segments
                part["verts"].append(self._rv((x+math.cos(angle)*ring_radius, yy, z+math.sin(angle)*ring_radius)))
        part["verts"].extend((self._rv((x,y-height/2,z)), self._rv((x,y+height/2,z))))
        bottom, top = base + segments*2, base + segments*2 + 1
        for index in range(segments):
            nxt = (index + 1) % segments
            part["faces"].append((base+index, base+nxt, base+segments+nxt, base+segments+index))
            part["faces"].append((bottom, base+nxt, base+index))
            part["faces"].append((top, base+segments+index, base+segments+nxt))

    def add_sloped_panel(self, corners, thickness, key="glass"):
        part = self._part(key)
        base = len(part["verts"])
        corners = tuple(corners)
        part["verts"].extend(self._rv(p) for p in corners)
        part["verts"].extend(self._rv((p[0], p[1]-thickness, p[2])) for p in corners)
        part["faces"].extend((base+a,base+b,base+c,base+d0) for a,b,c,d0 in
                             ((0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)))

    def flush(self):
        import bpy
        objects = []
        for key, part in sorted(self.parts.items()):
            mesh = bpy.data.meshes.new(f"HB_NAKANIWA_A18_{key}_MESH")
            mesh.from_pydata(part["verts"], [], part["faces"])
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new(f"HB_NAKANIWA_A18_{key}", mesh)
            self.collection.objects.link(obj)
            obj.data.materials.append(self.materials[key])
            obj["hibanaStageId"] = STAGE_ID
            obj["hibanaReferenceMatchVersion"] = REFERENCE_MATCH_VERSION
            obj["hibanaMaterialRole"] = key
            # Render-only presentation bevel. The deterministic integration API
            # remains explicit geometry, while the private audit avoids the
            # razor edges that make first-person scale and contacts unreadable.
            if key in {"wet_stone", "honey_stone", "white_marble", "dark_wood", "brass", "verdigris_bronze"}:
                bevel = obj.modifiers.new("HB_A18_PRESENTATION_BEVEL", "BEVEL")
                bevel.width = 0.055 if key in {"wet_stone", "honey_stone", "white_marble"} else 0.035
                bevel.segments = 2
                bevel.limit_method = "ANGLE"
                bevel.angle_limit = math.radians(24.0)
            objects.append(obj)
        return objects


def _make_materials():
    import bpy
    materials = {}
    for role, recipe in MATERIALS.items():
        name = f"MAT_Nakaniwa_A18_{role}"
        material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        for node in list(nodes):
            nodes.remove(node)
        output = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = recipe["color"]
        bsdf.inputs["Roughness"].default_value = recipe["roughness"]
        bsdf.inputs["Metallic"].default_value = recipe["metallic"]
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = recipe.get("alpha", recipe["color"][3])
        transmission_input = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
        if transmission_input is not None:
            transmission_input.default_value = recipe.get("transmission", 0.0)
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission_input is not None and recipe.get("emission"):
            emission_input.default_value = recipe["emission"]
            strength = bsdf.inputs.get("Emission Strength")
            if strength is not None:
                strength.default_value = recipe.get("emission_strength", 0.5)
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
        if recipe.get("noise"):
            noise = nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value = 3.2
            noise.inputs["Detail"].default_value = 2.0
            ramp = nodes.new("ShaderNodeValToRGB")
            base_color = recipe["color"]
            ramp.color_ramp.elements[0].position = 0.24
            ramp.color_ramp.elements[0].color = tuple(
                max(0.0, component * 0.72) for component in base_color[:3]
            ) + (base_color[3],)
            ramp.color_ramp.elements[1].position = 0.78
            ramp.color_ramp.elements[1].color = tuple(
                min(1.0, component * 1.20 + 0.02) for component in base_color[:3]
            ) + (base_color[3],)
            bump = nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = recipe["noise"]
            bump.inputs["Distance"].default_value = 0.16
            links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
            links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
            links.new(noise.outputs["Fac"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        material.diffuse_color = recipe["color"]
        if recipe.get("alpha", 1.0) < 1.0:
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


def _remove_collection_tree(collection):
    import bpy
    for child in list(collection.children):
        _remove_collection_tree(child)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def _point_camera(camera, target):
    from mathutils import Vector
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


PROTOTYPE_VIEWS = (
    ("01-reference-vista-eye165", (0.0, -112.0, PLAYER_EYE_M), (-3.0, 34.0, 11.0), 33.0),
    ("02-palace-approach-eye165", (-60.0, 22.0, PLAYER_EYE_M), (-60.0, -70.0, 18.0), 34.0),
    ("03-conservatory-approach-eye165", (52.0, -27.0, PLAYER_EYE_M), (52.0, 65.0, 17.0), 40.0),
    ("04-central-north-eye165", (0.0, -118.0, PLAYER_EYE_M), (-53.0, -72.0, 15.0), 43.0),
    ("05-central-south-eye165", (0.0, -44.0, PLAYER_EYE_M), (50.0, 61.0, 16.0), 43.0),
    ("06-canal-garden-eye165", (18.0, -98.0, PLAYER_EYE_M), (18.0, 82.0, 5.5), 35.0),
    ("07-aerial-overview", (178.0, -194.0, 150.0), (-5.0, -2.0, 8.0), 52.0),
    ("08-aerial-opposite", (-184.0, 190.0, 125.0), (-8.0, -5.0, 10.0), 55.0),
)


def _set_camera_view(camera, view) -> None:
    _, location, target, lens = view
    camera.location = location
    camera.data.lens = lens
    _point_camera(camera, target)


def _render_views(scene, camera, output_dir: Path) -> list[dict]:
    import bpy
    records = []
    for view in PROTOTYPE_VIEWS:
        name, location, target, lens = view
        _set_camera_view(camera, view)
        path = output_dir / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records.append({"id": name, "path": str(path), "location": location, "target": target, "lensMm": lens})
    # Leave the visible Blender viewport on the most reference-like player view.
    _set_camera_view(camera, PROTOTYPE_VIEWS[0])
    return records


def build_private_prototype(arguments: dict | None = None) -> dict:
    """Build a private LOD prototype without changing an open UI by default."""
    import bpy
    arguments = arguments or {}
    output_dir = Path(arguments.get("output_dir", PRIVATE_OUTPUT_ROOT)).expanduser().resolve()
    approved = PRIVATE_OUTPUT_ROOT.resolve()
    if output_dir != approved and approved not in output_dir.parents:
        raise RuntimeError(f"output_dir must stay below {approved}: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    lod = int(arguments.get("lod", 0))
    render = bool(arguments.get("render", True))
    update_viewport = bool(arguments.get("update_viewport", False))

    existing = bpy.data.collections.get(TARGET_COLLECTION)
    if existing:
        _remove_collection_tree(existing)
    collection = bpy.data.collections.new(TARGET_COLLECTION)
    bpy.context.scene.collection.children.link(collection)

    if update_viewport:
        for obj in bpy.data.objects:
            if obj.name.startswith("HB_") and not obj.name.startswith("HB_NAKANIWA_A18"):
                if "hbA18PreviousHideViewport" not in obj:
                    obj["hbA18PreviousHideViewport"] = bool(obj.hide_viewport)
                    obj["hbA18PreviousHideRender"] = bool(obj.hide_render)
                obj.hide_viewport = True
                obj.hide_render = True

    materials = _make_materials()
    builder = PrototypeMeshBuilder(collection, materials)
    specs = emit_to_builder(builder, lod=lod, material_map={key: key for key in MATERIALS})
    objects = builder.flush()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        scene.view_settings.look = "Medium High Contrast"
    world = scene.world or bpy.data.worlds.new("HB_Nakaniwa_A18_World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.28, 0.38, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.78

    camera_data = bpy.data.cameras.new("HB_NAKANIWA_A18_CAMERA_DATA")
    camera = bpy.data.objects.new("HB_NAKANIWA_A18_CAMERA", camera_data)
    collection.objects.link(camera)
    camera.data.sensor_width = 36.0
    scene.camera = camera

    sun_data = bpy.data.lights.new("HB_NAKANIWA_A18_SUN_DATA", "SUN")
    sun = bpy.data.objects.new("HB_NAKANIWA_A18_SUN", sun_data)
    collection.objects.link(sun)
    sun.rotation_euler = (math.radians(33.0), math.radians(-18.0), math.radians(132.0))
    sun.data.energy = 4.1
    sun.data.color = (1.0, 0.76, 0.52)
    sun.data.angle = math.radians(12.0)
    area_data = bpy.data.lights.new("HB_NAKANIWA_A18_SKY_FILL_DATA", "AREA")
    area = bpy.data.objects.new("HB_NAKANIWA_A18_SKY_FILL", area_data)
    collection.objects.link(area)
    area.location = (-20.0, -10.0, 120.0)
    area.data.energy = 1600.0
    area.data.shape = "DISK"
    area.data.size = 90.0
    area.data.color = (0.34, 0.52, 0.70)

    records = _render_views(scene, camera, output_dir) if render else []
    if not render:
        _set_camera_view(camera, PROTOTYPE_VIEWS[0])
    # Explicit opt-in only: the current production session may be presenting a
    # different stage in the left Blender window.
    if update_viewport and bpy.context.screen:
        for area_ui in bpy.context.screen.areas:
            if area_ui.type == "VIEW_3D":
                area_ui.spaces.active.region_3d.view_perspective = "CAMERA"
                area_ui.spaces.active.overlay.show_overlays = False

    role_counts = Counter(spec["role"] for spec in specs)
    kind_counts = Counter(spec["kind"] for spec in specs)
    bounds = [spec_bounds(spec) for spec in specs]
    if "__file__" in globals():
        source_path = Path(__file__).resolve()
    else:
        source_path = Path(arguments.get("source_path", "")).expanduser().resolve()
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path.is_file() else None
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "version": REFERENCE_MATCH_VERSION,
        "lod": lod,
        "reference": {"path": REFERENCE_PATH, "sha256": REFERENCE_SHA256},
        "canonical": connection_metadata(),
        "specCount": len(specs),
        "objectCount": len(objects),
        "roleCounts": dict(sorted(role_counts.items())),
        "kindCounts": dict(sorted(kind_counts.items())),
        "bounds": {
            "minX": min(item[0] for item in bounds), "minY": min(item[1] for item in bounds),
            "minZ": min(item[2] for item in bounds), "maxX": max(item[3] for item in bounds),
            "maxY": max(item[4] for item in bounds), "maxZ": max(item[5] for item in bounds),
        },
        "views": records,
        "sourcePath": str(source_path) if source_path.is_file() else None,
        "sourceSha256": source_sha,
    }
    report_path = output_dir / "prototype-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    score_average = round(sum(item["score"] for item in REFERENCE_SCORE_ITEMS) / len(REFERENCE_SCORE_ITEMS), 2)
    score_minimum = min(item["score"] for item in REFERENCE_SCORE_ITEMS)
    scorecard = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "referenceMatchVersion": REFERENCE_MATCH_VERSION,
        "prototypeRevision": output_dir.name,
        "reference": {"path": REFERENCE_PATH, "sha256": REFERENCE_SHA256, "inspectedAtOriginalResolution": True},
        "evidenceViews": records,
        "playerEyeHeightM": PLAYER_EYE_M,
        "scores": [dict(item) for item in REFERENCE_SCORE_ITEMS],
        "minimum": score_minimum,
        "average": score_average,
        "thresholds": {"minimumEach": 7.0, "minimumAverage": 8.0},
        "prototypeGatePassed": False,
        "verdict": "NO-SHIP",
        "signedBy": "root-independent-v8-baseline",
        "signatureScope": "controlling v8 baseline; r9 requires fresh independent visual review",
        "browserGate": "pending-build_all-integration",
        "sourceSha256": source_sha,
    }
    scorecard_path = output_dir / "reference-scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    blend_path = output_dir / "nakaniwa-a18-reference-prototype.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report["blendPath"] = str(blend_path)
    report["reportPath"] = str(report_path)
    report["scorecardPath"] = str(scorecard_path)
    report["prototypeReferenceGatePassed"] = scorecard["prototypeGatePassed"]
    return report


if __name__ == "__main__" or "args" in globals():
    if "args" in globals():
        _arguments = globals().get("args", {})
    else:
        import argparse
        import sys
        _parser = argparse.ArgumentParser(description="Build the private Nakaniwa A18 reference prototype")
        _parser.add_argument("--output-dir", default=str(PRIVATE_OUTPUT_ROOT))
        _parser.add_argument("--lod", type=int, default=0, choices=sorted(LOD_API))
        _parser.add_argument("--no-render", action="store_true")
        _cli = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        _parsed = _parser.parse_args(_cli)
        _arguments = {"output_dir": _parsed.output_dir, "lod": _parsed.lod, "render": not _parsed.no_render}
    _result = build_private_prototype(_arguments if isinstance(_arguments, dict) else {})
    globals()["__result__"] = _result
