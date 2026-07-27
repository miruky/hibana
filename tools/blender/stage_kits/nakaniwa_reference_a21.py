#!/usr/bin/env python3
"""Private A21 R4 production-art rebuild for Nakaniwa.

Production brief
----------------
Nakaniwa is a dense palace-garden city at one Blender metre per runtime metre.
The immutable 320 m bounds, 16 m cross roads, spawns, landmark footprints,
entrances, approaches and collision templates remain sourced from A20's
canonical contract.  The ImageGen concept is a modelling reference only.

The locked 1.65 m view composes a close garden/canal/bridge foreground,
the Crowned Water Palace large on frame-left, the Fan-Glass Conservatory large
on frame-right, and a tall real-geometry garden district behind both.

Hero grammar:
* Crowned Water Palace: an ivory water plinth, three deep occupied arcade
  terraces, supported loggias, a tall central keep and one rooted floral crown.
* Fan-Glass Conservatory: five separately readable rounded fan/barrel vaults
  on a carved stone plinth, monumental fan entry, transparent weathered glass,
  primary/secondary ribs, upper walks, water rills and a dense interior garden.

Dedicated facade language: chamfered pale palace stone, carved arch extrusions,
deep warm glazed openings, planted loggias, verdigris garden roofs and brass
weathering accents.  The horizon is actual 3D architecture and vegetation.

Forbidden: orange boxes, black holes, global post-merge bevel, uniform-noise
materials, faceted primitive trees, flat stone slabs, empty plaza, generic
single-barrel greenhouse, raster/cylindrical mattes and runtime mutation.

Connection map
--------------
Every attached part has >=0.02 m contact.  Palace plinth -> arcade columns ->
entablatures -> occupied terraces -> keep -> crown drum -> thick petals.
Conservatory plinth -> buttresses -> curved primary ribs -> secondary purlins
-> glazing cells.  Soil beds -> trunks -> branches -> leaf clusters.  Bridge
decks overlap both copings.  Role-specific chamfers are baked before batching:
macro palace stone 0.10-0.20 m, carved frames 0.03-0.08 m, rails/ribs
0.01-0.035 m.  Curved members are swept meshes, not box chains.

The script writes only below
``/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4``.  It never
edits public assets, runtime source, manifests, A20, the immutable R3 proof
directory, or a visible Blender session.  The independently fixed R3 score of
4.50/10 remains controlling after this rebuild; the release decision remains
NO-SHIP until a different reviewer signs a new fixed ten-category scorecard.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import nakaniwa_reference_a20 as A20  # noqa: E402


STAGE_ID = "nakaniwa"
KIT_VERSION = "nakaniwa-reference-a21-production-r4"
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/nakaniwa-reference-v1.png"
REFERENCE_SHA256 = "c0b3bec12431c264ebe04a0757ea67eb521eab2c4e32e004da88cf6e6eebe15d"
R3_PRODUCTION_ROOT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art"
)
PRIVATE_PRODUCTION_DEFAULT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4"
)
INDEPENDENT_SCORECARD_PATH = (
    R3_PRODUCTION_ROOT / "INDEPENDENT_SCORECARD_A21.json"
)
INDEPENDENT_REBUILD_SCORECARD_PATH = (
    R3_PRODUCTION_ROOT / "INDEPENDENT_SCORECARD_A21_REBUILD.json"
)
INDEPENDENT_SCORECARD_R3_PATH = (
    R3_PRODUCTION_ROOT / "INDEPENDENT_SCORECARD_A21_R3.json"
)
INDEPENDENT_SCORECARD_R3_SHA256 = (
    "80e105729b3dd20309547fa930bcc9417ffd60b2c499354c6f3ae91ddbe9e7eb"
)
CANONICAL_LAYOUT_DEFAULT = A20.CANONICAL_LAYOUT_DEFAULT
TARGET_COLLECTION = "HB_NAKANIWA_A21_ROOT"

MAP_SIZE_M = A20.MAP_SIZE_M
CANONICAL_BOUNDS = copy.deepcopy(A20.CANONICAL_BOUNDS)
CANONICAL_ROADS = copy.deepcopy(A20.CANONICAL_ROADS)
CANONICAL_PLAYER_SPAWNS = copy.deepcopy(A20.CANONICAL_PLAYER_SPAWNS)
CANONICAL_BOT_SPAWNS = copy.deepcopy(A20.CANONICAL_BOT_SPAWNS)
LANDMARKS = copy.deepcopy(A20.LANDMARKS)
PALACE_ID = LANDMARKS[0]["id"]
CONSERVATORY_ID = LANDMARKS[1]["id"]
PLAYER_EYE_M = 1.65

FIXED_SCORE_CATEGORIES = A20.FIXED_SCORE_CATEGORIES

MATERIALS = {
    "wet_stone": {
        "color": (0.052, 0.070, 0.068, 1.0),
        "roughness": (0.12, 0.34), "metallic": 0.04,
        "noiseScale": 1.7, "detailScale": 26.0, "bump": 0.08,
    },
    "ivory_stone": {
        "color": (0.60, 0.575, 0.520, 1.0),
        "roughness": (0.24, 0.48), "metallic": 0.0,
        "noiseScale": 0.58, "detailScale": 24.0, "bump": 0.075,
    },
    "carved_stone": {
        "color": (0.315, 0.300, 0.270, 1.0),
        "roughness": (0.24, 0.49), "metallic": 0.0,
        "noiseScale": 1.35, "detailScale": 32.0, "bump": 0.065,
    },
    "moss_stone": {
        "color": (0.13, 0.19, 0.125, 1.0),
        "roughness": (0.36, 0.60), "metallic": 0.0,
        "noiseScale": 2.3, "detailScale": 34.0, "bump": 0.075,
    },
    "brass": {
        "color": (0.38, 0.235, 0.070, 1.0),
        "roughness": (0.14, 0.32), "metallic": 0.90,
        "noiseScale": 8.5, "detailScale": 42.0, "bump": 0.025,
    },
    "verdigris_bronze": {
        "color": (0.030, 0.235, 0.195, 1.0),
        "roughness": (0.16, 0.36), "metallic": 0.82,
        "noiseScale": 5.2, "detailScale": 39.0, "bump": 0.045,
    },
    "dirty_glass": {
        "color": (0.070, 0.225, 0.235, 0.34),
        "roughness": (0.045, 0.14), "metallic": 0.03,
        "transmission": 0.84, "alpha": 0.34, "ior": 1.45,
        "emission": (0.0, 0.012, 0.016, 1.0), "emissionStrength": 0.05,
        "noiseScale": 2.0, "detailScale": 52.0, "bump": 0.022,
    },
    "glass_highlight": {
        "color": (0.14, 0.39, 0.40, 0.14),
        "roughness": (0.035, 0.11), "metallic": 0.04,
        "transmission": 0.82, "alpha": 0.14, "ior": 1.45,
        "emission": (0.0, 0.025, 0.030, 1.0), "emissionStrength": 0.07,
        "noiseScale": 3.8, "detailScale": 58.0, "bump": 0.010,
    },
    "water": {
        "color": (0.010, 0.105, 0.135, 1.0),
        "roughness": (0.08, 0.22), "metallic": 0.0,
        "transmission": 0.16, "alpha": 1.0, "ior": 1.333,
        "noiseScale": 1.05, "detailScale": 34.0, "bump": 0.07,
    },
    "dark_wood": {
        "color": (0.075, 0.030, 0.014, 1.0),
        "roughness": (0.35, 0.62), "metallic": 0.0,
        "noiseScale": 4.0, "detailScale": 45.0, "bump": 0.08,
    },
    "foliage_dark": {
        "color": (0.018, 0.095, 0.028, 1.0),
        "roughness": (0.46, 0.68), "metallic": 0.0,
        "noiseScale": 5.0, "detailScale": 30.0, "bump": 0.035,
        "subsurface": 0.15,
    },
    "foliage_light": {
        "color": (0.065, 0.285, 0.050, 1.0),
        "roughness": (0.43, 0.65), "metallic": 0.0,
        "noiseScale": 6.5, "detailScale": 36.0, "bump": 0.035,
        "subsurface": 0.18,
    },
    "flower": {
        "color": (0.30, 0.018, 0.055, 1.0),
        "roughness": (0.36, 0.58), "metallic": 0.0,
        "noiseScale": 9.0, "detailScale": 48.0, "bump": 0.025,
        "subsurface": 0.045,
    },
    "warm_glow": {
        "color": (0.52, 0.155, 0.025, 0.82),
        "roughness": (0.23, 0.38), "metallic": 0.05,
        "emission": (1.0, 0.20, 0.035, 1.0), "emissionStrength": 1.35,
        "noiseScale": 10.0, "detailScale": 50.0, "bump": 0.0,
    },
}
DEFAULT_INTEGRATION_MATERIAL_MAP = {key: key for key in MATERIALS}

LOD_BUDGETS = {
    0: {"minEvaluatedTriangles": 180_000, "maxEvaluatedTriangles": 260_000,
        "maxMaterials": 14, "maxSpecs": 7_800},
    1: {"minEvaluatedTriangles": 55_000, "maxEvaluatedTriangles": 90_000,
        "maxMaterials": 14, "maxSpecs": 4_400},
    2: {"minEvaluatedTriangles": 14_000, "maxEvaluatedTriangles": 28_000,
        "maxMaterials": 14, "maxSpecs": 1_900},
}

CONNECTION_MAP = (
    {"id": "a21-ground-palace-plinth", "a": "ground", "aFace": "top",
     "b": "palace-water-plinth", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a21-palace-plinth-arcade", "a": "palace-water-plinth", "aFace": "top",
     "b": "palace-arcade-pier", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a21-palace-pier-entablature", "a": "palace-arcade-pier", "aFace": "top",
     "b": "palace-arcade-entablature", "bFace": "bottom", "axis": "y", "overlapM": 0.08},
    {"id": "a21-palace-entablature-terrace", "a": "palace-arcade-entablature", "aFace": "top",
     "b": "palace-occupied-terrace", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a21-palace-terrace-keep", "a": "palace-occupied-terrace", "aFace": "top",
     "b": "palace-central-keep", "bFace": "bottom", "axis": "y", "overlapM": 0.12},
    {"id": "a21-r4-palace-keep-crown", "a": "palace-central-keep", "aFace": "shoulder",
     "b": "a21-r4-palace-rooted-crown-occupied-drum", "bFace": "inside",
     "axis": "volume", "overlapM": 4.00},
    {"id": "a21-r4-palace-drum-petal",
     "a": "a21-r4-palace-rooted-crown-occupied-drum", "aFace": "front-ring",
     "b": "a21-r4-palace-rooted-five-petal-crown", "bFace": "root",
     "axis": "surface", "overlapM": 0.48},
    {"id": "a21-r4-palace-petal-frame",
     "a": "a21-r4-palace-rooted-five-petal-crown", "aFace": "centre",
     "b": "a21-r4-palace-rooted-crown-brass-spine", "bFace": "inside",
     "axis": "surface", "overlapM": 0.08},
    {"id": "a21-r4-palace-terrace-loggia",
     "a": "a21-r4-palace-lower-water-loggia-deep-terrace-slab",
     "aFace": "top",
     "b": "a21-r4-palace-lower-water-loggia-grounded-carved-column",
     "bFace": "bottom", "axis": "y", "overlapM": 0.18},
    {"id": "a21-palace-water-coping", "a": "palace-water", "aFace": "edge",
     "b": "palace-water-coping", "bFace": "inside", "axis": "surface", "overlapM": 0.04},
    {"id": "a21-ground-conservatory-plinth", "a": "ground", "aFace": "top",
     "b": "conservatory-stone-plinth", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a21-conservatory-plinth-buttress", "a": "conservatory-stone-plinth", "aFace": "top",
     "b": "conservatory-vault-buttress", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
    {"id": "a21-conservatory-buttress-rib", "a": "conservatory-vault-buttress", "aFace": "top",
     "b": "conservatory-curved-primary-rib", "bFace": "spring", "axis": "surface", "overlapM": 0.08},
    {"id": "a21-conservatory-rib-purlin", "a": "conservatory-curved-primary-rib", "aFace": "crossing",
     "b": "conservatory-secondary-purlin", "bFace": "crossing", "axis": "surface", "overlapM": 0.03},
    {"id": "a21-conservatory-rib-glass", "a": "conservatory-curved-primary-rib", "aFace": "cell",
     "b": "conservatory-dirty-glass-cell", "bFace": "edge", "axis": "surface", "overlapM": 0.025},
    {"id": "a21-conservatory-walk-support", "a": "conservatory-walk-support", "aFace": "top",
     "b": "conservatory-upper-walk", "bFace": "bottom", "axis": "y", "overlapM": 0.08},
    {"id": "a21-soil-trunk", "a": "garden-soil", "aFace": "top",
     "b": "garden-trunk", "bFace": "bottom", "axis": "y", "overlapM": 0.08},
    {"id": "a21-trunk-branch", "a": "garden-trunk", "aFace": "crown",
     "b": "garden-branch", "bFace": "root", "axis": "surface", "overlapM": 0.04},
    {"id": "a21-branch-leaf", "a": "garden-branch", "aFace": "tip",
     "b": "garden-leaf-cluster", "bFace": "centre", "axis": "surface", "overlapM": 0.02},
    {"id": "a21-canal-bridge", "a": "garden-canal-coping", "aFace": "top",
     "b": "garden-bridge-deck", "bFace": "underside", "axis": "y", "overlapM": 0.06},
    {"id": "a21-r4-canal-bridge-contact-key", "a": "garden-bridge-deck",
     "aFace": "threshold", "b": "a21-r4-bridge-coping-contact-key",
     "bFace": "inside", "axis": "route", "overlapM": 0.21},
    {"id": "a21-district-roof", "a": "district-occupied-facade", "aFace": "top",
     "b": "district-garden-roof", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
)

MAIN_REFERENCE_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_DualHero",
    "location": (63.15, PLAYER_EYE_M, -82.98),
    "target": (-8.0, 13.0, -4.0),
    "lensMm": 18.0,
    "sensorWidthMm": 36.0,
    "resolution": (1280, 720),
    "eyeHeightM": PLAYER_EYE_M,
    "intent": "close diagonal canal and bridge with both monumental heroes",
}

PROOF_CAMERAS = (
    MAIN_REFERENCE_CAMERA,
    {
        "name": "CAM_Nakaniwa_A21_Eye165_PalaceArcade",
        "location": (-34.0, PLAYER_EYE_M, -16.0),
        "target": (-61.0, 18.0, -66.0), "lensMm": 24.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "continuous palace arcade, terraces and integrated crown",
    },
    {
        "name": "CAM_Nakaniwa_A21_Eye165_ConservatoryFiveVaults",
        "location": (16.0, PLAYER_EYE_M, 12.0),
        "target": (54.0, 17.0, 66.0), "lensMm": 23.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "five-vault silhouette, plinth and monumental threshold",
    },
    {
        "name": "CAM_Nakaniwa_A21_Eye165_ConservatoryInterior",
        "location": (54.0, PLAYER_EYE_M, 42.0),
        "target": (61.0, 10.5, 80.0), "lensMm": 22.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "inside central vault: garden, water rills, walks and ribs",
    },
    {
        "name": "CAM_Nakaniwa_A21_Eye165_GardenBridge",
        "location": (16.0, PLAYER_EYE_M, -22.0),
        "target": (28.8, 4.0, -34.1), "lensMm": 24.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "near garden, canal, bridge and palace-water story",
    },
    {
        "name": "CAM_Nakaniwa_A21_Eye165_PalaceWaterCourt",
        "location": (-82.0, PLAYER_EYE_M, -50.0),
        "target": (-82.0, 3.0, -37.0), "lensMm": 18.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "water court, occupied thresholds and ceremonial props",
    },
    {
        "name": "CAM_Nakaniwa_A21_Eye165_BoundaryDepth",
        "location": (155.0, PLAYER_EYE_M, -85.0),
        "target": (45.0, 12.0, -65.0), "lensMm": 30.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": PLAYER_EYE_M,
        "intent": "real layered 3D district boundary and skyline depth",
    },
    {
        "name": "CAM_Nakaniwa_A21_Aerial",
        "location": (168.0, 112.0, -176.0),
        "target": (-4.0, 9.0, -2.0), "lensMm": 48.0,
        "sensorWidthMm": 36.0, "resolution": (1280, 720),
        "eyeHeightM": 112.0,
        "intent": "exact two landmarks, dense districts and route preservation",
    },
)

SELF_REJECT_HISTORY = (
    {
        "iteration": 0,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art/"
            "self-reject/iteration-0/views/00_eye165_dualhero.png"
        ),
        "sha256": "959fc8a41813eef6c34062b6df0937e07bada70623462df33ef55a071cece387",
        "verdict": "REJECTED_GENERIC_BLOCKOUT",
        "reasons": [
            "palace cropped at frame-left and floral crown read too small",
            "five conservatory shells collapsed into a generic single barrel",
            "stone and glass were washed out by exposure",
            "foreground still read as broad flat paving",
        ],
        "correctiveActions": [
            "rebalance the locked camera while retaining 1.65 m eye height",
            "offset five shells laterally and give each a distinct rise",
            "darken and separate stone/glass material response",
            "pull the canal, three bridges, paving joints and planted rooms forward",
        ],
    },
    {
        "iteration": 1,
        "evidence": str(INDEPENDENT_SCORECARD_PATH),
        "verdict": "INDEPENDENT_NO_SHIP_GENERIC_BLOCKOUT",
        "arithmeticMean": 3.93,
        "minimumCategoryScore": 2.6,
        "reasons": [
            "empty pavement did not read as an intimate garden-canal corridor",
            "palace crown and conservatory silhouettes were proxy-grade",
            "materials, foliage, water and lighting remained blockout-grade",
            "perimeter districts lacked Nakaniwa-specific density and story",
        ],
        "correctiveActions": [
            "build a close diagonal canal with three bridges and planted rooms",
            "integrate a castle-scale occupied flower crown into the palace",
            "replace bubbles with five nested fan/petal conservatory vaults",
            "add dedicated pavilions, garden arcades and maintenance story",
        ],
    },
    {
        "iteration": 2,
        "evidence": str(INDEPENDENT_REBUILD_SCORECARD_PATH),
        "verdict": "INDEPENDENT_NO_SHIP_GENERIC_BLOCKOUT",
        "arithmeticMean": 4.37,
        "minimumCategoryScore": 2.8,
        "reasons": [
            "heroes remained distant and structurally simplified",
            "material response still read as flat blockout surfaces",
            "midground and skyline lacked overlapping palace-city depth",
            "lighting stayed cool, flat and airless",
        ],
        "correctiveActions": [
            "bring monumental hero masses to their camera-facing envelopes",
            "reallocate detail from micro parts into macro occupied structures",
            "add a dense canal-side middle city and enclosing garden arcades",
            "strengthen stone joints, glass reflection, water and warm haze",
        ],
    },
    {
        "iteration": 3,
        "evidence": str(INDEPENDENT_SCORECARD_R3_PATH),
        "sha256": INDEPENDENT_SCORECARD_R3_SHA256,
        "verdict": "INDEPENDENT_NO_SHIP_GENERIC_BLOCKOUT",
        "arithmeticMean": 4.50,
        "minimumCategoryScore": 2.90,
        "reasons": [
            "palace still read as brown block masses with repeated crown teeth",
            "conservatory frames remained straight triangular proxies",
            "stone, glass and water lacked production PBR separation",
            "near/mid/far city and occupied storytelling remained too sparse",
        ],
        "correctiveActions": [
            "replace duplicate crowns with one rooted ivory castle-scale crown",
            "use five overlapping rounded transparent fan/barrel vaults",
            "move the locked player-height camera closer to canal and bridge",
            "add supported loggias, stairs, rails and maintenance/botanical story",
        ],
    },
    {
        "iteration": 4,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4/"
            "self-reject/iteration-0/views/00_eye165_dualhero.png"
        ),
        "sha256": "5175f5eb8f7fd1d8df0db639b4686def5ffedd2400020bdee3863dc7344517fd",
        "verdict": "PRODUCER_REJECTED_OVEREXPOSED_CENTRED_CANAL",
        "reasons": [
            "overexposure erased ivory stone depth and wet-contact contrast",
            "camera centred the canal into an oversized lower-frame slab",
            "near skeletal arcades occluded the two landmark façades",
            "the rooted crown was too far behind the camera-facing palace edge",
        ],
        "correctiveActions": [
            "move the player-height camera to the dry promenade side",
            "reduce exposure, world fill and pale-stone albedo",
            "remove the two occluding near arcade frames",
            "move the rooted crown onto the occupied east shoulder tower",
        ],
    },
    {
        "iteration": 5,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4/"
            "self-reject/iteration-1/views/00_eye165_dualhero.png"
        ),
        "sha256": "8e51dc7f2675b2df612410a6cb083f86ab5e451edadeafb8064df5d0492aab32",
        "verdict": "PRODUCER_REJECTED_SPARSE_COOL_FOREGROUND",
        "reasons": [
            "the right foreground remained a broad empty paved plane",
            "five curved shells still collapsed into one dominant glass canopy",
            "interior planting remained weak behind stacked glass layers",
            "lighting and stone response remained cool and materially flat",
        ],
        "correctiveActions": [
            "build a close occupied right-edge loggia and planted frame",
            "separate all five shells laterally and in depth",
            "increase glass transmission and interior canopy scale",
            "restore a warm directional key with stronger PBR variation",
        ],
    },
    {
        "iteration": 6,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4/"
            "self-reject/iteration-2/views/00_eye165_dualhero.png"
        ),
        "sha256": "9cff37c6fe5c45e3adf58435cd81524a2107704e0111043318992a15feff9ebb",
        "verdict": "PRODUCER_REJECTED_FOREGROUND_LANDMARK_OCCLUSION",
        "reasons": [
            "the new right loggia hid the conservatory landmark",
            "foreground paving joints read as oversized black wires",
            "cool fill still overpowered the intended late-afternoon key",
        ],
        "correctiveActions": [
            "move and narrow the loggia to a 15-20 percent right-edge frame",
            "reduce foreground joint radii to subtle masonry seams",
            "reduce cool fill and restore the warm directional sun",
        ],
    },
    {
        "iteration": 7,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4/"
            "self-reject/iteration-3/views/00_eye165_dualhero.png"
        ),
        "sha256": "7b8716a1b867eda44bd2bbee1eccd59cedba01bcd12bb453c984923ae4a8d818",
        "verdict": "PRODUCER_REJECTED_FIVE_SHELL_COLLAPSE",
        "reasons": [
            "right-edge framing was fixed but the five shells still nested",
            "long foreground paving seams remained visually over-weighted",
        ],
        "correctiveActions": [
            "separate shells into small-medium-large-medium-small fans",
            "reduce foreground paving seams below hero-detail frequency",
        ],
    },
    {
        "iteration": 8,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4/"
            "self-reject/iteration-4/views/00_eye165_dualhero.png"
        ),
        "sha256": "41fc83a01d0da170732078885e4e702a3a1f5866d40b30deba9c7146e9385e20",
        "verdict": "PRODUCER_REJECTED_CLOSE_ARCADE_OCCLUSION",
        "reasons": [
            "the closer diagonal camera was correct in scale and canal proximity",
            "the camera-side mid-canal arcade hid most of the water palace",
            "its large blue-grey piers split the dual-landmark composition",
        ],
        "correctiveActions": [
            "retain the closer 1.65 m player-height camera",
            "remove only the camera-side occluding arcade module",
            "keep the opposite arcade to preserve occupied garden density",
        ],
    },
    {
        "iteration": 9,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4/"
            "self-reject/iteration-5/views/00_eye165_dualhero.png"
        ),
        "sha256": "3d1999ba226e7069977d26d55eb854073df17d67f1a3a6a3889ba1b5d2de57af",
        "verdict": "PRODUCER_REJECTED_LOOSE_WIDE_FRAMING",
        "reasons": [
            "both landmark identities were finally unobstructed",
            "the 16 mm field of view left too much low-information paving",
            "hero façade and conservatory rib details read smaller than necessary",
        ],
        "correctiveActions": [
            "tighten only the lens to 18 mm without moving the player camera",
            "retain the diagonal canal, foreground bridge and both hero silhouettes",
            "revalidate minimum visible hero frame coverage after the crop",
        ],
    },
)


def _box(specs: list[dict], role: str, material: str, group: str,
         x: float, y: float, z: float, w: float, h: float, d: float) -> None:
    specs.append({
        "kind": "box", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "x": x, "y": y, "z": z,
        "w": w, "h": h, "d": d,
    })


def _chamfer_box(specs: list[dict], role: str, material: str, group: str,
                 x: float, y: float, z: float, w: float, h: float, d: float,
                 bevel: float, segments: int = 1) -> None:
    if bevel <= 0.0 or bevel >= min(w, h, d) * 0.49:
        raise ValueError(f"{role}: invalid baked chamfer {bevel}")
    specs.append({
        "kind": "chamfer_box", "role": role, "material": material,
        "group": group, "blocksGameplay": False,
        "x": x, "y": y, "z": z, "w": w, "h": h, "d": d,
        "bevel": bevel, "segments": segments,
    })


def _panel(specs: list[dict], role: str, material: str, group: str,
           corners: Sequence[tuple[float, float, float]],
           thickness: float = 0.06) -> None:
    specs.append({
        "kind": "panel", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "corners": tuple(corners), "thickness": thickness,
    })


def _cylinder(specs: list[dict], role: str, material: str, group: str,
              x: float, y: float, z: float, radius: float, height: float,
              segments: int = 12, top_radius: float | None = None) -> None:
    specs.append({
        "kind": "cylinder", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "x": x, "y": y, "z": z,
        "radius": radius, "height": height, "segments": segments,
        "topRadius": radius if top_radius is None else top_radius,
    })


def _sweep(specs: list[dict], role: str, material: str, group: str,
           points: Sequence[tuple[float, float, float]],
           radius: float, sides: int) -> None:
    if len(points) < 2 or sides < 4:
        raise ValueError(f"{role}: invalid sweep")
    specs.append({
        "kind": "sweep", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "points": tuple(points),
        "radius": radius, "sides": sides,
    })


def _leaf_cluster(specs: list[dict], role: str, material: str, group: str,
                  x: float, y: float, z: float, radius: float, height: float,
                  leaves: int, seed: int) -> None:
    specs.append({
        "kind": "leaf_cluster", "role": role, "material": material,
        "group": group, "blocksGameplay": False,
        "x": x, "y": y, "z": z, "radius": radius, "height": height,
        "leaves": leaves, "seed": seed,
    })


def _arch_points(cx: float, base_y: float, z: float, half_width: float,
                 spring_y: float, rise: float, segments: int) -> tuple:
    points = [(cx - half_width, base_y, z), (cx - half_width, spring_y, z)]
    for index in range(segments + 1):
        theta = math.pi - math.pi * index / segments
        points.append((
            cx + half_width * math.cos(theta),
            spring_y + rise * math.sin(theta),
            z,
        ))
    points.extend(((cx + half_width, spring_y, z), (cx + half_width, base_y, z)))
    return tuple(points)


def _arcade(specs: list[dict], *, group: str, role: str, material: str,
            x0: float, x1: float, z: float, base_y: float, bays: int,
            lod: int, depth: float = 0.24) -> None:
    segs = (24, 12, 5)[lod]
    sides = (10, 6, 4)[lod]
    bay = (x1 - x0) / bays
    for index in range(bays):
        cx = x0 + bay * (index + 0.5)
        _sweep(
            specs, f"{role}-curved-rib", material, group,
            _arch_points(cx, base_y, z, bay * 0.37, base_y + 3.2, 2.15, segs),
            depth, sides,
        )
        if index == 0:
            _chamfer_box(
                specs, f"{role}-pier", material, group,
                x0, base_y + 2.65, z, 0.62, 5.5, 0.74,
                min(0.055, 0.20 * 0.62), 1,
            )
        _chamfer_box(
            specs, f"{role}-pier", material, group,
            x0 + bay * (index + 1), base_y + 2.65, z, 0.62, 5.5, 0.74,
            min(0.055, 0.20 * 0.62), 1,
        )
    _chamfer_box(
        specs, f"{role}-entablature", material, group,
        (x0 + x1) * 0.5, base_y + 5.52, z, x1 - x0 + 0.7, 0.74, 0.88,
        0.055, 1,
    )


def _monumental_arcade(
    specs: list[dict], *, group: str, role: str, material: str,
    x0: float, x1: float, z: float, base_y: float, bays: int, lod: int,
    spring_height: float, rise: float, depth: float,
) -> None:
    """Build genuinely tall, deep arcade bays for camera-facing hero façades."""
    segs = (28, 14, 6)[lod]
    sides = (10, 7, 5)[lod]
    bay = (x1 - x0) / bays
    opening_height = spring_height + rise
    for index in range(bays):
        cx = x0 + bay * (index + 0.5)
        _sweep(
            specs, f"{role}-curved-rib", material, group,
            _arch_points(
                cx, base_y, z, bay * 0.36,
                base_y + spring_height, rise, segs,
            ),
            depth, sides,
        )
        pier_x = x0 + bay * index
        _chamfer_box(
            specs, f"{role}-deep-buttress", material, group,
            pier_x, base_y + opening_height * 0.5, z,
            0.92, opening_height + 0.7, 1.15,
            (0.075, 0.060, 0.050)[lod], 1,
        )
    _chamfer_box(
        specs, f"{role}-deep-buttress", material, group,
        x1, base_y + opening_height * 0.5, z,
        0.92, opening_height + 0.7, 1.15,
        (0.075, 0.060, 0.050)[lod], 1,
    )
    _chamfer_box(
        specs, f"{role}-entablature", material, group,
        (x0 + x1) * 0.5, base_y + opening_height + 0.42, z,
        x1 - x0 + 1.1, 0.95, 1.28,
        (0.075, 0.060, 0.050)[lod], 1,
    )


def _roof(specs: list[dict], *, group: str, role: str, cx: float, base_y: float,
          cz: float, width: float, depth: float, rise: float,
          material: str = "verdigris_bronze") -> None:
    _panel(
        specs, f"{role}-slope", material, group,
        ((cx - width / 2, base_y, cz - depth / 2),
         (cx, base_y + rise, cz - depth / 2),
         (cx, base_y + rise, cz + depth / 2),
         (cx - width / 2, base_y, cz + depth / 2)),
        0.10,
    )
    _panel(
        specs, f"{role}-slope", material, group,
        ((cx, base_y + rise, cz - depth / 2),
         (cx + width / 2, base_y, cz - depth / 2),
         (cx + width / 2, base_y, cz + depth / 2),
         (cx, base_y + rise, cz + depth / 2)),
        0.10,
    )
    _sweep(
        specs, f"{role}-ridge", "brass", group,
        ((cx, base_y + rise, cz - depth / 2 - 0.12),
         (cx, base_y + rise, cz + depth / 2 + 0.12)),
        0.035, 6,
    )


def _deep_window(specs: list[dict], *, group: str, role: str,
                 x: float, y: float, z: float, width: float, height: float,
                 plane: str = "front", warm: bool = False) -> None:
    frame = 0.18
    bevel = 0.045
    glass_mat = "warm_glow" if warm else "dirty_glass"
    if plane == "front":
        _chamfer_box(specs, f"{role}-jamb", "carved_stone", group,
                     x - width / 2, y, z, frame, height, 0.34, bevel, 1)
        _chamfer_box(specs, f"{role}-jamb", "carved_stone", group,
                     x + width / 2, y, z, frame, height, 0.34, bevel, 1)
        _chamfer_box(specs, f"{role}-sill", "carved_stone", group,
                     x, y - height / 2, z, width + frame, frame, 0.34, bevel, 1)
        _chamfer_box(specs, f"{role}-hood", "carved_stone", group,
                     x, y + height / 2, z, width + frame, frame, 0.34, bevel, 1)
        _box(specs, f"{role}-shadow-recess", "dark_wood", group,
             x, y, z + 0.28, width - 0.10, height - 0.10, 0.12)
        _box(specs, f"{role}-recessed-glazing", glass_mat, group,
             x, y, z + 0.18, width * 0.68, height * 0.72, 0.08)
        _box(specs, f"{role}-vertical-mullion", "brass", group,
             x, y, z + 0.12, 0.07, height * 0.70, 0.08)
        _box(specs, f"{role}-horizontal-mullion", "brass", group,
             x, y, z + 0.12, width * 0.66, 0.07, 0.08)
    else:
        _chamfer_box(specs, f"{role}-jamb", "carved_stone", group,
                     x, y, z - width / 2, 0.34, height, frame, bevel, 1)
        _chamfer_box(specs, f"{role}-jamb", "carved_stone", group,
                     x, y, z + width / 2, 0.34, height, frame, bevel, 1)
        _chamfer_box(specs, f"{role}-sill", "carved_stone", group,
                     x, y - height / 2, z, 0.34, frame, width + frame, bevel, 1)
        _chamfer_box(specs, f"{role}-hood", "carved_stone", group,
                     x, y + height / 2, z, 0.34, frame, width + frame, bevel, 1)
        _box(specs, f"{role}-shadow-recess", "dark_wood", group,
             x - 0.28, y, z, 0.12, height - 0.10, width - 0.10)
        _box(specs, f"{role}-recessed-glazing", glass_mat, group,
             x - 0.18, y, z, 0.08, height * 0.72, width * 0.68)
        _box(specs, f"{role}-vertical-mullion", "brass", group,
             x - 0.12, y, z, 0.08, height * 0.70, 0.07)
        _box(specs, f"{role}-horizontal-mullion", "brass", group,
             x - 0.12, y, z, 0.08, 0.07, width * 0.66)


def _tree(specs: list[dict], *, group: str, role: str,
          x: float, z: float, height: float, crown: float,
          lod: int, seed: int, flowering: bool = False) -> None:
    trunk_h = height * 0.48
    _cylinder(
        specs, f"{role}-trunk", "dark_wood", group,
        x, trunk_h / 2.0, z, 0.24 + crown * 0.035, trunk_h,
        (12, 8, 6)[lod], top_radius=0.13 + crown * 0.018,
    )
    branch_count = (9, 5, 3)[lod]
    for index in range(branch_count):
        angle = (index * 2.399963 + seed * 0.37) % math.tau
        start = (x, trunk_h * (0.64 + 0.04 * (index % 3)), z)
        end = (
            x + math.cos(angle) * crown * (0.44 + 0.05 * (index % 2)),
            trunk_h + 0.45 + 0.35 * (index % 3),
            z + math.sin(angle) * crown * (0.44 + 0.05 * (index % 2)),
        )
        _sweep(
            specs, f"{role}-branch", "dark_wood", group,
            (start, end), (0.10, 0.075, 0.055)[lod], (7, 6, 4)[lod],
        )
    cluster_count = (13, 7, 3)[lod]
    leaf_count = (26, 12, 6)[lod]
    for index in range(cluster_count):
        angle = index * math.tau / cluster_count + seed * 0.21
        radial = crown * (0.30 + 0.18 * ((index * 7) % 3) / 2.0)
        material = "flower" if flowering and index % 3 == 0 else (
            "foliage_light" if index % 2 else "foliage_dark"
        )
        _leaf_cluster(
            specs, f"{role}-leaf-cluster", material, group,
            x + math.cos(angle) * radial,
            trunk_h + 0.8 + (index % 3) * crown * 0.22,
            z + math.sin(angle) * radial,
            crown * 0.52, crown * 0.42, leaf_count, seed * 97 + index,
        )


def _add_palace(specs: list[dict], lod: int) -> None:
    group = PALACE_ID
    # Grounded macro silhouette and water architecture.
    _chamfer_box(specs, "a21-palace-water-plinth", "wet_stone", group,
                 -60.0, 0.55, -67.8, 91.0, 1.30, 76.0, 0.18, 2 if lod == 0 else 1)
    for x in (-82.0, -38.0):
        _box(specs, "a21-palace-water", "water", group,
             x, 1.16, -38.0, 32.0, 0.18, 12.0)
        for side in (-1.0, 1.0):
            _chamfer_box(specs, "a21-palace-water-coping", "carved_stone", group,
                         x, 1.32, -38.0 + side * 6.1, 32.8, 0.42, 0.44, 0.07, 1)
    # Deep occupied masses sit behind a genuinely open continuous arcade.
    _chamfer_box(specs, "a21-palace-occupied-lower-wing", "ivory_stone", group,
                 -83.5, 5.6, -83.0, 37.0, 9.0, 42.0, 0.16,
                 2 if lod == 0 else 1)
    _chamfer_box(specs, "a21-palace-occupied-lower-wing", "ivory_stone", group,
                 -36.5, 5.6, -83.0, 37.0, 9.0, 42.0, 0.16,
                 2 if lod == 0 else 1)
    _chamfer_box(specs, "a21-palace-entry-hall", "carved_stone", group,
                 -60.0, 7.0, -50.0, 17.0, 12.0, 35.0, 0.18, 2 if lod == 0 else 1)
    front_bays = (12, 9, 6)[lod]
    _monumental_arcade(
        specs, group=group, role="a21-palace-grand-continuous-arcade",
        material="carved_stone", x0=-103.0, x1=-17.0, z=-29.47,
        base_y=1.12, bays=front_bays, lod=lod,
        spring_height=6.1, rise=3.4, depth=(0.42, 0.34, 0.26)[lod],
    )
    # Warm glass lies behind the open arcade, never as a black void.
    if lod <= 1:
        opening_bays = 12 if lod == 0 else 8
        for index in range(opening_bays):
            x = -99.0 + index * (78.0 / max(1, opening_bays - 1))
            opening_material = "warm_glow" if index % 3 == 0 else "dirty_glass"
            _box(
                specs, "a21-palace-deep-warm-occupied-opening",
                opening_material, group,
                x, 5.5, -34.15, 4.5, 7.4, 0.10,
            )
            _chamfer_box(
                specs, "a21-palace-arcade-deep-soffit",
                "wet_stone", group,
                x, 10.55, -31.85, 5.8, 0.34, 5.0,
                0.055, 1,
            )
            _chamfer_box(
                specs, "a21-palace-arcade-deep-floor",
                "wet_stone", group,
                x, 1.30, -31.85, 5.8, 0.30, 5.0,
                0.050, 1,
            )
    # Side arcades continue the architectural grammar around the water palace.
    side_count = (9, 6, 4)[lod]
    for side_x in (-104.2, -15.8):
        for index in range(side_count):
            z = -36.0 - index * (64.0 / max(1, side_count - 1))
            points = tuple(
                (side_x, y, x)
                for x, y, _ in _arch_points(
                    z, 1.12, 0.0, 2.55, 4.25, 2.0, (22, 11, 5)[lod]
                )
            )
            _sweep(
                specs, "a21-palace-side-continuous-arcade-curved-rib",
                "carved_stone", group, points, (0.26, 0.22, 0.20)[lod],
                (10, 6, 4)[lod],
            )
    # Supported terraces, upper loggia and occupied vertical keep.
    _chamfer_box(specs, "a21-palace-occupied-terrace", "wet_stone", group,
                 -60.0, 11.35, -68.5, 82.0, 1.3, 65.0, 0.14, 1)
    _chamfer_box(specs, "a21-palace-upper-wing", "ivory_stone", group,
                 -81.5, 17.0, -72.0, 30.0, 10.0, 20.0, 0.14,
                 2 if lod == 0 else 1)
    _chamfer_box(specs, "a21-palace-upper-wing", "ivory_stone", group,
                 -38.5, 17.0, -72.0, 30.0, 10.0, 20.0, 0.14,
                 2 if lod == 0 else 1)
    for tower_x in (-82.0, -22.0):
        _chamfer_box(
            specs, "a21-palace-crown-companion-tower",
            "carved_stone", group, tower_x, 24.0, -70.0,
            9.0, 18.0, 10.0, (0.13, 0.10, 0.08)[lod], 1,
        )
        for belt_y in ((19.0, 24.0, 29.0) if lod == 0 else (24.0,)):
            _chamfer_box(
                specs, "a21-palace-companion-tower-carved-belt",
                "ivory_stone", group,
                tower_x, belt_y, -70.0,
                9.7, 0.46, 10.7, (0.065, 0.052, 0.044)[lod], 1,
            )
        _roof(
            specs, group=group, role="a21-palace-companion-petal-roof",
            cx=tower_x, base_y=33.0, cz=-70.0,
            width=10.2, depth=11.0, rise=3.0,
        )
        _cylinder(
            specs, "a21-palace-companion-tower-master-spire",
            "brass", group,
            tower_x, 38.0, -70.0, 0.30, 4.0,
            (12, 8, 6)[lod], top_radius=0.04,
        )
        for buttress_x in (tower_x - 4.10, tower_x + 4.10):
            _chamfer_box(
                specs, "a21-palace-companion-tower-deep-front-buttress",
                "ivory_stone", group,
                buttress_x, 24.0, -64.72,
                0.82, 18.3, 0.86, (0.070, 0.055, 0.045)[lod], 1,
            )
        _chamfer_box(
            specs, "a21-palace-companion-tower-stone-balcony",
            "ivory_stone", group,
            tower_x, 25.35, -64.20,
            8.4, 0.42, 1.65, (0.065, 0.052, 0.044)[lod], 1,
        )
        tower_rail_posts = (7, 4, 3)[lod]
        for post_index in range(tower_rail_posts):
            post_x = tower_x - 3.45 + post_index * (
                6.9 / max(1, tower_rail_posts - 1)
            )
            _sweep(
                specs, "a21-palace-companion-tower-balcony-post",
                "brass", group,
                ((post_x, 25.55, -63.50), (post_x, 26.60, -63.50)),
                (0.032, 0.027, 0.022)[lod], (7, 6, 4)[lod],
            )
        _sweep(
            specs, "a21-palace-companion-tower-balcony-handrail",
            "brass", group,
            (
                (tower_x - 3.55, 26.65, -63.50),
                (tower_x + 3.55, 26.65, -63.50),
            ),
            (0.036, 0.030, 0.025)[lod], (8, 6, 4)[lod],
        )
        if lod <= 1:
            tower_columns = 3 if lod == 0 else 2
            tower_rows = 3 if lod == 0 else 2
            for column in range(tower_columns):
                for row in range(tower_rows):
                    _deep_window(
                        specs, group=group,
                        role="a21-palace-companion-tower-deep-window",
                        x=tower_x - 2.6
                        + column * (5.2 / max(1, tower_columns - 1)),
                        y=18.9 + row * 5.25, z=-64.82,
                        width=1.35, height=2.55,
                        warm=(column + row) % 3 == 0,
                    )
            for side_row in range(tower_rows):
                _deep_window(
                    specs, group=group,
                    role="a21-palace-companion-tower-side-deep-window",
                    x=tower_x + 4.68,
                    y=18.9 + side_row * 5.25,
                    z=-70.0, width=1.45, height=2.55,
                    plane="side", warm=side_row == 1,
                )
    upper_bays = (14, 9, 6)[lod]
    _arcade(
        specs, group=group, role="a21-palace-upper-loggia",
        material="carved_stone", x0=-94.0, x1=-26.0, z=-44.55,
        base_y=12.2, bays=upper_bays, lod=lod, depth=(0.30, 0.24, 0.19)[lod],
    )
    # Pull the dominant vertical keep and crown toward the public garden.
    # This preserves the canonical landmark envelope while stopping the rear
    # wings from hiding the palace's defining flower silhouette at 1.65 m.
    keep_x = -40.0
    keep_z = -49.0
    # Three grounded terrace setbacks make the vertical keep read as a castle
    # rather than a second storey balanced on a horizontal slab.
    for terrace_index, (width, depth, y, height) in enumerate((
        (52.0, 34.0, 9.8, 2.2),
        (45.0, 29.0, 11.6, 1.8),
        (35.0, 25.0, 13.0, 1.4),
    )):
        _chamfer_box(
            specs, f"a21-palace-central-stepped-terrace-{terrace_index}",
            "carved_stone" if terrace_index % 2 == 0 else "wet_stone",
            group, keep_x, y, keep_z, width, height, depth,
            (0.16, 0.12, 0.09)[lod], 1,
        )
    _chamfer_box(specs, "a21-palace-central-keep", "ivory_stone", group,
                 keep_x, 21.0, keep_z, 26.0, 28.0, 24.0, 0.18,
                 2 if lod == 0 else 1)
    _chamfer_box(specs, "a21-palace-keep-shoulder", "carved_stone", group,
                 keep_x, 31.8, keep_z + 1.0, 36.0, 3.0, 18.0, 0.15, 1)
    for band_y in ((24.2, 28.4) if lod == 0 else (27.0,)):
        _chamfer_box(
            specs, "a21-palace-central-keep-weathered-stringcourse",
            "wet_stone", group,
            keep_x, band_y, keep_z + 12.20,
            26.8, 0.40, 0.52, (0.060, 0.050, 0.040)[lod], 1,
        )
    engaged_count = (6, 4, 3)[lod]
    for index in range(engaged_count):
        x = keep_x - 11.8 + index * (
            23.6 / max(1, engaged_count - 1)
        )
        _chamfer_box(
            specs, "a21-palace-central-keep-front-engaged-buttress",
            "carved_stone", group,
            x, 22.0, keep_z + 12.38,
            0.72, 21.0, 0.76, (0.060, 0.050, 0.040)[lod], 1,
        )
    balcony_levels = (23.0, 28.8) if lod == 0 else (26.0,)
    for level in balcony_levels:
        _chamfer_box(
            specs, "a21-palace-central-keep-stone-balcony",
            "ivory_stone", group,
            keep_x, level, keep_z + 12.85,
            24.8, 0.40, 1.70, (0.070, 0.055, 0.045)[lod], 1,
        )
        keep_rail_posts = (11, 7, 5)[lod]
        for post_index in range(keep_rail_posts):
            post_x = keep_x - 11.4 + post_index * (
                22.8 / max(1, keep_rail_posts - 1)
            )
            _sweep(
                specs, "a21-palace-central-keep-balcony-post",
                "brass", group,
                (
                    (post_x, level + 0.20, keep_z + 13.58),
                    (post_x, level + 1.20, keep_z + 13.58),
                ),
                (0.030, 0.025, 0.021)[lod], (7, 6, 4)[lod],
            )
        _sweep(
            specs, "a21-palace-central-keep-balcony-handrail",
            "brass", group,
            (
                (keep_x - 11.6, level + 1.24, keep_z + 13.58),
                (keep_x + 11.6, level + 1.24, keep_z + 13.58),
            ),
            (0.036, 0.030, 0.025)[lod], (8, 6, 4)[lod],
        )
    if lod <= 1:
        # Two camera-facing upper turrets turn the keep into a vertical
        # tower-cluster silhouette without exceeding the locked crown height.
        for turret_index, turret_x in enumerate(
            (keep_x - 11.0, keep_x + 11.0)
        ):
            turret_z = keep_z + 9.5
            _chamfer_box(
                specs, "a21-palace-central-keep-upper-turret",
                "carved_stone", group,
                turret_x, 30.7, turret_z,
                5.4, 8.4, 6.0, (0.11, 0.085)[lod], 1,
            )
            for buttress_side in (-1.0, 1.0):
                _chamfer_box(
                    specs,
                    "a21-palace-central-keep-upper-turret-buttress",
                    "ivory_stone", group,
                    turret_x + buttress_side * 2.35,
                    30.7, turret_z + 3.08,
                    0.62, 8.6, 0.70, (0.055, 0.045)[lod], 1,
                )
            _deep_window(
                specs, group=group,
                role="a21-palace-central-keep-upper-turret-window",
                x=turret_x, y=30.2, z=turret_z + 3.12,
                width=1.55, height=2.75,
                warm=turret_index == 1,
            )
            _roof(
                specs, group=group,
                role="a21-palace-central-keep-upper-turret-roof",
                cx=turret_x, base_y=34.9, cz=turret_z,
                width=6.4, depth=6.8, rise=3.1,
                material="verdigris_bronze",
            )
            _cylinder(
                specs, "a21-palace-central-keep-upper-turret-spire",
                "brass", group,
                turret_x, 40.1, turret_z,
                (0.24, 0.19)[lod], 4.0,
                (10, 8)[lod], top_radius=0.045,
            )
    if lod == 0:
        for panel_index in range(5):
            _chamfer_box(
                specs, "a21-palace-central-keep-carved-relief-panel",
                "moss_stone" if panel_index % 2 else "carved_stone", group,
                keep_x - 8.8 + panel_index * 4.4,
                31.0, keep_z + 12.43,
                2.7, 2.0, 0.34, 0.055, 1,
            )
    for pilaster_x in (keep_x - 12.0, keep_x + 12.0):
        for pilaster_z in (keep_z - 10.5, keep_z + 10.5):
            _chamfer_box(
                specs, "a21-palace-central-keep-corner-pilaster",
                "carved_stone", group,
                pilaster_x, 21.0, pilaster_z,
                1.25, 28.4, 1.25, (0.09, 0.07, 0.05)[lod], 1,
            )
    keep_loggia_bays = (5, 4, 3)[lod]
    _monumental_arcade(
        specs, group=group,
        role="a21-palace-central-keep-deep-loggia",
        material="carved_stone",
        x0=keep_x - 11.0, x1=keep_x + 11.0,
        z=keep_z + 12.28, base_y=13.4,
        bays=keep_loggia_bays, lod=lod,
        spring_height=5.2, rise=3.0,
        depth=(0.38, 0.30, 0.24)[lod],
    )
    if lod <= 1:
        for bay_index in range(keep_loggia_bays):
            bay_x = (
                keep_x - 11.0
                + (bay_index + 0.5) * (22.0 / keep_loggia_bays)
            )
            _box(
                specs, "a21-palace-central-keep-occupied-loggia",
                "warm_glow", group,
                bay_x, 16.2, keep_z + 12.05,
                3.1, 4.0, 0.10,
            )
    # The primary camera also sees the keep's east face; give it the same deep
    # architecture so the hero cannot fall back to a plain cuboid in profile.
    side_loggia_bays = (5, 4, 3)[lod]
    side_z0, side_z1 = keep_z - 10.5, keep_z + 10.5
    side_bay = (side_z1 - side_z0) / side_loggia_bays
    side_x = keep_x + 13.18
    for bay_index in range(side_loggia_bays):
        bay_z = side_z0 + side_bay * (bay_index + 0.5)
        rotated_arch = tuple(
            (side_x, arch_y, arch_x)
            for arch_x, arch_y, _ in _arch_points(
                bay_z, 13.4, 0.0, side_bay * 0.36,
                18.6, 3.0, (28, 14, 6)[lod],
            )
        )
        _sweep(
            specs, "a21-palace-central-keep-side-loggia-curved-rib",
            "carved_stone", group,
            rotated_arch, (0.38, 0.30, 0.24)[lod], (10, 7, 5)[lod],
        )
        _chamfer_box(
            specs, "a21-palace-central-keep-side-loggia-deep-buttress",
            "carved_stone", group,
            side_x, 17.5, side_z0 + side_bay * bay_index,
            1.15, 8.9, 0.92, (0.075, 0.060, 0.050)[lod], 1,
        )
        if lod <= 1:
            _box(
                specs, "a21-palace-central-keep-side-occupied-loggia",
                "warm_glow", group,
                side_x - 0.25, 16.2, bay_z,
                0.10, 4.0, side_bay * 0.70,
            )
    _chamfer_box(
        specs, "a21-palace-central-keep-side-loggia-deep-buttress",
        "carved_stone", group,
        side_x, 17.5, side_z1,
        1.15, 8.9, 0.92, (0.075, 0.060, 0.050)[lod], 1,
    )
    _chamfer_box(
        specs, "a21-palace-central-keep-side-loggia-entablature",
        "carved_stone", group,
        side_x, 22.0, keep_z,
        1.28, 0.95, side_z1 - side_z0 + 1.1,
        (0.075, 0.060, 0.050)[lod], 1,
    )
    if lod == 0:
        # The locked diagonal camera is dominated by this east elevation.
        # Large/medium/small facade frequencies keep it from reading as a
        # shaded blank box above the lower arcade.
        for level in (24.8, 29.4):
            _chamfer_box(
                specs, "a21-palace-central-keep-side-stone-balcony",
                "ivory_stone", group,
                side_x + 0.42, level, keep_z,
                1.65, 0.38, 20.8, 0.060, 1,
            )
            _sweep(
                specs, "a21-palace-central-keep-side-balcony-handrail",
                "brass", group,
                (
                    (side_x + 1.24, level + 1.16, keep_z - 9.8),
                    (side_x + 1.24, level + 1.16, keep_z + 9.8),
                ),
                0.036, 8,
            )
            for post_index in range(8):
                post_z = keep_z - 9.8 + post_index * 2.8
                _sweep(
                    specs, "a21-palace-central-keep-side-balcony-post",
                    "brass", group,
                    (
                        (side_x + 1.24, level + 0.20, post_z),
                        (side_x + 1.24, level + 1.16, post_z),
                    ),
                    0.028, 7,
                )
        for row, window_y in enumerate((25.8, 30.2)):
            for column, window_z in enumerate(
                (keep_z - 7.2, keep_z, keep_z + 7.2)
            ):
                _deep_window(
                    specs, group=group,
                    role="a21-palace-central-keep-upper-side-deep-window",
                    x=side_x + 0.12, y=window_y, z=window_z,
                    width=1.75, height=2.80, plane="side",
                    warm=(row + column) % 3 == 0,
                )
    # A dense but readable balustrade gives the giant terraces human scale.
    _chamfer_box(
        specs, "a21-palace-camera-facing-balcony",
        "carved_stone", group,
        -60.0, 11.15, -32.0, 82.0, 0.62, 5.5,
        (0.11, 0.09, 0.07)[lod], 1,
    )
    terrace_posts = (34, 18, 8)[lod]
    for index in range(terrace_posts):
        x = -98.0 + index * (76.0 / max(1, terrace_posts - 1))
        _sweep(
            specs, "a21-palace-terrace-baluster", "brass", group,
            ((x, 11.45, -29.85), (x, 12.75, -29.85)),
            (0.032, 0.026, 0.022)[lod], (8, 6, 4)[lod],
        )
    _sweep(
        specs, "a21-palace-terrace-handrail", "brass", group,
        ((-98.4, 12.82, -29.85), (-21.6, 12.82, -29.85)),
        (0.035, 0.030, 0.025)[lod], (8, 6, 4)[lod],
    )
    # Sparse deep glazing and carved frames.
    if lod <= 1:
        columns = 5 if lod == 0 else 3
        rows = 3 if lod == 0 else 2
        for row in range(rows):
            for column in range(columns):
                _deep_window(
                    specs, group=group, role="a21-palace-keep-window",
                    x=keep_x - 10.5 + column * (21.0 / max(1, columns - 1)),
                    y=16.4 + row * 4.25, z=keep_z + 12.15,
                    width=1.55, height=2.45, warm=(row + column) % 4 == 0,
                )
        wing_columns = 8 if lod == 0 else 4
        for column in range(wing_columns):
            for row in range(2 if lod == 0 else 1):
                _deep_window(
                    specs, group=group, role="a21-palace-wing-deep-window",
                    x=-96.0 + column * (72.0 / max(1, wing_columns - 1)),
                    y=7.6 + row * 8.0, z=-30.36,
                    width=1.45, height=2.35,
                    warm=(column + row) % 6 == 0,
                )
        # The raised wings expose real occupied façades to the primary
        # diagonal view instead of remaining broad unarticulated stone slabs.
        upper_columns = 4 if lod == 0 else 2
        for wing_x in (-81.5, -38.5):
            for column in range(upper_columns):
                for row in range(2 if lod == 0 else 1):
                    _deep_window(
                        specs, group=group,
                        role="a21-palace-upper-wing-deep-window",
                        x=wing_x - 12.0
                        + column * (24.0 / max(1, upper_columns - 1)),
                        y=15.3 + row * 4.90, z=-61.82,
                        width=1.55, height=2.75,
                        warm=(column + row) % 3 == 0,
                    )
    # Layered garden roofs, not thin floating slabs.
    for cx in (-81.5, -38.5):
        _roof(specs, group=group, role="a21-palace-wing-garden-roof",
              cx=cx, base_y=21.9, cz=-72.0, width=33.0, depth=22.0, rise=4.3)
    _roof(specs, group=group, role="a21-palace-keep-roof",
          cx=keep_x, base_y=34.4, cz=keep_z, width=29.0, depth=26.0, rise=2.0)
    # An occupied lantern gallery inserts one more readable vertical tier
    # between the keep and flower crown.
    _cylinder(
        specs, "a21-palace-crown-lantern-gallery-base",
        "carved_stone", group,
        keep_x, 32.8, keep_z, 9.6, 0.75,
        (24, 16, 10)[lod], top_radius=9.2,
    )
    _cylinder(
        specs, "a21-palace-crown-lantern-gallery-warm-interior",
        "warm_glow", group,
        keep_x, 34.8, keep_z, 7.0, 3.2,
        (24, 16, 10)[lod], top_radius=6.4,
    )
    gallery_columns = (12, 8, 6)[lod]
    for index in range(gallery_columns):
        angle = math.tau * index / gallery_columns
        _cylinder(
            specs, "a21-palace-crown-lantern-gallery-column",
            "brass", group,
            keep_x + math.cos(angle) * 8.15,
            34.75,
            keep_z + math.sin(angle) * 8.15,
            (0.24, 0.20, 0.16)[lod], 3.9,
            (10, 8, 6)[lod], top_radius=(0.20, 0.17, 0.14)[lod],
        )
    _cylinder(
        specs, "a21-palace-crown-lantern-gallery-cornice",
        "brass", group,
        keep_x, 36.55, keep_z, 8.65, 0.55,
        (24, 16, 10)[lod], top_radius=8.25,
    )
    # Heavy integrated floral crown.  Stone petal faces and brass spines share
    # a real drum contact rather than hovering as a wire crown.
    _cylinder(specs, "a21-palace-crown-drum", "carved_stone", group,
              keep_x, 31.2, keep_z, 10.5, 5.8, (24, 16, 10)[lod], top_radius=9.3)
    _cylinder(specs, "a21-palace-crown-brass-ring", "brass", group,
              keep_x, 33.1, keep_z, 9.8, 0.58, (24, 16, 10)[lod], top_radius=9.8)
    petal_count = (8, 8, 6)[lod]
    for index in range(petal_count):
        angle = math.tau * index / petal_count
        tangent = (-math.sin(angle), 0.0, math.cos(angle))
        root = (
            keep_x + math.cos(angle) * 10.2,
            31.0,
            keep_z + math.sin(angle) * 10.2,
        )
        shoulder = (
            keep_x + math.cos(angle) * 17.0,
            39.0,
            keep_z + math.sin(angle) * 17.0,
        )
        tip = (
            keep_x + math.cos(angle) * 11.5,
            42.48,
            keep_z + math.sin(angle) * 11.5,
        )
        half = 4.0 if lod == 0 else 3.20
        corners = (
            (root[0] - tangent[0] * half, root[1], root[2] - tangent[2] * half),
            (root[0] + tangent[0] * half, root[1], root[2] + tangent[2] * half),
            (shoulder[0] + tangent[0] * half * 0.72, shoulder[1],
             shoulder[2] + tangent[2] * half * 0.72),
            (tip[0], tip[1], tip[2]),
        )
        _panel(
            specs,
            "a21-palace-crown-heavy-petal",
            "ivory_stone" if index % 2 == 0 else "carved_stone",
            group,
            corners,
            (0.82, 0.54, 0.34)[lod],
        )
        _sweep(
            specs, "a21-palace-crown-brass-spine", "brass", group,
            (root, shoulder, tip), (0.18, 0.13, 0.09)[lod], (10, 7, 5)[lod],
        )
        edge_shoulders = (
            (
                shoulder[0] - tangent[0] * half * 0.72,
                shoulder[1],
                shoulder[2] - tangent[2] * half * 0.72,
            ),
            (
                shoulder[0] + tangent[0] * half * 0.72,
                shoulder[1],
                shoulder[2] + tangent[2] * half * 0.72,
            ),
        )
        for edge_index, root_corner in enumerate(corners[:2]):
            _sweep(
                specs, "a21-palace-crown-structural-edge-frame",
                "brass", group,
                (root_corner, edge_shoulders[edge_index], tip),
                (0.085, 0.065, 0.050)[lod], (8, 6, 4)[lod],
            )
        if lod <= 1:
            inset = tuple(
                (
                    corner[0] * 0.93 + keep_x * 0.07,
                    corner[1] * 0.96 + 36.0 * 0.04,
                    corner[2] * 0.93 + keep_z * 0.07,
                )
                for corner in corners
            )
            _panel(specs, "a21-palace-crown-luminous-inset", "flower",
                   group, inset, 0.10)
            inner_root = (
                keep_x + math.cos(angle) * 5.2,
                33.0,
                keep_z + math.sin(angle) * 5.2,
            )
            inner_shoulder = (
                keep_x + math.cos(angle) * 10.0,
                37.0,
                keep_z + math.sin(angle) * 10.0,
            )
            inner_tip = (
                keep_x + math.cos(angle) * 5.6,
                41.2,
                keep_z + math.sin(angle) * 5.6,
            )
            inner_half = 2.7 if lod == 0 else 2.25
            _panel(
                specs, "a21-palace-crown-inner-flower-petal", "flower", group,
                (
                    (
                        inner_root[0] - tangent[0] * inner_half,
                        inner_root[1],
                        inner_root[2] - tangent[2] * inner_half,
                    ),
                    (
                        inner_root[0] + tangent[0] * inner_half,
                        inner_root[1],
                        inner_root[2] + tangent[2] * inner_half,
                    ),
                    (
                        inner_shoulder[0] + tangent[0] * inner_half * 0.62,
                        inner_shoulder[1],
                        inner_shoulder[2] + tangent[2] * inner_half * 0.62,
                    ),
                    inner_tip,
                ),
                0.16,
            )
    if lod == 0:
        # Five heavy camera-diagonal stone petals form a continuous castle
        # crown in the production view.  Each petal grows from a real occupied
        # tower root; none is a detached decorative fin.
        camera_normal = (0.94, -0.342)
        camera_tangent = (0.342, 0.94)
        crown_face_x = keep_x + camera_normal[0] * 8.0
        crown_face_z = keep_z + camera_normal[1] * 8.0
        tangent_offsets = (-9.0, -4.5, 0.0, 4.5, 9.0)
        for petal_index, tangent_offset in enumerate(tangent_offsets):
            centre_x = crown_face_x + camera_tangent[0] * tangent_offset
            centre_z = crown_face_z + camera_tangent[1] * tangent_offset
            root_y = 28.8 + (1.0 - abs(tangent_offset) / 9.0) * 0.9
            _chamfer_box(
                specs,
                "a21-palace-integrated-crown-occupied-root-tower",
                "carved_stone" if petal_index % 2 else "ivory_stone",
                group,
                centre_x - camera_normal[0] * 0.55,
                32.0,
                centre_z - camera_normal[1] * 0.55,
                5.8,
                7.2 + (1.0 - abs(tangent_offset) / 9.0) * 1.4,
                6.2,
                0.12,
                2,
            )
            _deep_window(
                specs,
                group=group,
                role="a21-palace-integrated-crown-root-deep-opening",
                x=centre_x,
                y=31.8,
                z=centre_z + 3.16,
                width=1.45,
                height=2.55,
                warm=petal_index in {1, 3},
            )
            root_left = (
                centre_x - camera_tangent[0] * 2.55,
                root_y,
                centre_z - camera_tangent[1] * 2.55,
            )
            root_right = (
                centre_x + camera_tangent[0] * 2.55,
                root_y,
                centre_z + camera_tangent[1] * 2.55,
            )
            root_centre = (centre_x, root_y, centre_z)
            shoulder_left = (
                centre_x - camera_tangent[0] * 1.95
                + camera_normal[0] * 0.80,
                37.2 + (1.0 - abs(tangent_offset) / 9.0) * 0.8,
                centre_z - camera_tangent[1] * 1.95
                + camera_normal[1] * 0.80,
            )
            shoulder_right = (
                centre_x + camera_tangent[0] * 1.95
                + camera_normal[0] * 0.80,
                37.2 + (1.0 - abs(tangent_offset) / 9.0) * 0.8,
                centre_z + camera_tangent[1] * 1.95
                + camera_normal[1] * 0.80,
            )
            tip = (
                centre_x + camera_normal[0] * 0.20,
                42.42 - abs(tangent_offset) * 0.075,
                centre_z + camera_normal[1] * 0.20,
            )
            petal_material = (
                "ivory_stone" if petal_index != 1 else "carved_stone"
            )
            _panel(
                specs, "a21-palace-camera-diagonal-crown-petal",
                petal_material, group,
                (root_centre, root_left, shoulder_left, tip), 0.95,
            )
            _panel(
                specs, "a21-palace-camera-diagonal-crown-petal",
                petal_material, group,
                (root_centre, tip, shoulder_right, root_right), 0.95,
            )
            for edge_start, edge_shoulder in (
                (root_left, shoulder_left), (root_right, shoulder_right)
            ):
                _sweep(
                    specs, "a21-palace-camera-diagonal-crown-petal-edge",
                    "brass", group,
                    (edge_start, edge_shoulder, tip), 0.10, 8,
                )
            _sweep(
                specs, "a21-palace-camera-diagonal-crown-petal-spine",
                "brass", group,
                (root_centre, tip), 0.13, 9,
            )
    _cylinder(specs, "a21-palace-crown-inner-lantern", "dirty_glass", group,
              keep_x, 36.9, keep_z, 4.2, 10.4, (18, 12, 8)[lod], top_radius=1.3)
    _cylinder(specs, "a21-palace-crown-master-finial", "brass", group,
              keep_x, 41.55, keep_z, 0.34, 2.6, (12, 8, 6)[lod], top_radius=0.06)
    # Human-scale stairs, planted terraces and ceremonial lanterns.
    stair_count = (8, 6, 4)[lod]
    for index in range(stair_count):
        _chamfer_box(
            specs, "a21-palace-entry-stair", "carved_stone", group,
            -60.0, 0.14 + index * 0.17, -29.25 - index * 0.62,
            11.5 - index * 0.26, 0.28, 0.82, 0.045, 1,
        )
    planter_count = (12, 8, 4)[lod]
    for index in range(planter_count):
        x = -96.0 + index * (72.0 / max(1, planter_count - 1))
        _chamfer_box(specs, "a21-palace-terrace-planter", "carved_stone", group,
                     x, 12.45, -33.5, 3.2, 1.15, 2.2, 0.08, 1)
        _box(specs, "a21-palace-terrace-soil", "wet_stone", group,
             x, 13.02, -33.5, 2.7, 0.18, 1.7)
        _leaf_cluster(specs, "a21-palace-terrace-leaf-cluster",
                      "foliage_light" if index % 2 else "foliage_dark", group,
                      x, 13.75, -33.5, 1.45, 1.15, (10, 7, 4)[lod], 2100 + index)


def _vault_profile(cx: float, spring_y: float, z: float,
                   half_width: float, rise: float, segments: int) -> tuple:
    return tuple(
        (
            cx + half_width * math.cos(math.pi - math.pi * index / segments),
            spring_y + rise * math.sin(math.pi - math.pi * index / segments),
            z,
        )
        for index in range(segments + 1)
    )


def _petal_vault_profile(
    cx: float,
    spring_y: float,
    z: float,
    half_width: float,
    rise: float,
    segments: int,
    crown_bias: float = 0.0,
) -> tuple:
    """Rounded fan/barrel profile used by the five nested R4 shells."""
    points = []
    for index in range(segments + 1):
        normalized = -1.0 + 2.0 * index / segments
        angle = math.pi * (normalized + 1.0) * 0.5
        # A softened elliptical section holds curvature through the shoulders.
        # The previous 1-|x|^1.18 section read as a straight triangular frame
        # in the locked diagonal camera.
        crown = math.sin(angle) ** 0.72
        lateral_bias = crown_bias * crown
        points.append((
            cx + normalized * half_width + lateral_bias,
            spring_y + rise * crown,
            z,
        ))
    return tuple(points)


def _add_conservatory(specs: list[dict], lod: int) -> None:
    group = CONSERVATORY_ID
    _chamfer_box(specs, "a21-conservatory-stone-plinth", "wet_stone", group,
                 52.0, 0.55, 61.8, 75.0, 1.3, 65.0, 0.18,
                 2 if lod == 0 else 1)
    # Open central promenade and deep perimeter stonework.
    _chamfer_box(specs, "a21-conservatory-left-plinth", "ivory_stone", group,
                 31.0, 3.2, 61.8, 16.0, 5.4, 62.0, 0.16, 1)
    _chamfer_box(specs, "a21-conservatory-right-plinth", "ivory_stone", group,
                 73.0, 3.2, 61.8, 16.0, 5.4, 62.0, 0.16, 1)
    # Two stone arcade shoulders integrate the glass shells into a monumental
    # base while preserving a generous central entrance.
    for x0, x1 in ((18.0, 44.0), (60.0, 86.0)):
        _arcade(
            specs, group=group, role="a21-conservatory-plinth-arcade",
            material="carved_stone", x0=x0, x1=x1, z=29.45,
            base_y=1.1, bays=(6, 4, 3)[lod], lod=lod,
            depth=(0.18, 0.16, 0.14)[lod],
        )
    _chamfer_box(specs, "a21-conservatory-central-promenade", "carved_stone", group,
                 52.0, 1.24, 62.0, 8.6, 0.34, 60.0, 0.08, 1)
    for side in (-1.0, 1.0):
        _box(specs, "a21-conservatory-interior-water-rill", "water", group,
             52.0 + side * 6.1, 1.23, 63.0, 2.4, 0.16, 56.0)
        for coping_side in (-1.0, 1.0):
            _chamfer_box(
                specs, "a21-conservatory-rill-coping", "carved_stone", group,
                52.0 + side * 6.1 + coping_side * 1.32, 1.37, 63.0,
                0.32, 0.38, 56.4, 0.055, 1,
            )
    profile_segments = (26, 14, 6)[lod]
    rib_sides = (10, 6, 4)[lod]
    glass_step = (1, 2, 3)[lod]
    # Five nested rounded fan/barrel vaults overlap in both X and depth.  The
    # centre shell carries the skyline while the four smaller shells reveal
    # separate spring points and translucent planted interiors.
    vault_centres = (38.0, 45.0, 56.0, 65.0, 75.0)
    vault_x_centres = (24.0, 34.5, 52.0, 69.5, 80.0)
    vault_half_widths = (8.5, 17.0, 33.5, 17.0, 8.5)
    vault_rises = (20.0, 30.0, 43.6, 31.0, 21.0)
    vault_crown_biases = (1.2, 0.8, 0.0, -0.8, -1.2)
    vault_half_depths = (9.0, 13.0, 18.0, 15.0, 12.0)
    for vault_index, centre_z in enumerate(vault_centres):
        centre_x = vault_x_centres[vault_index]
        half_width = vault_half_widths[vault_index]
        spring_y = 5.7 + (vault_index % 2) * 0.35
        rise = vault_rises[vault_index]
        # The first LOD0 rib is 0.48 m thick; keep its contact surface inside
        # the canonical conservatory envelope instead of letting the radius
        # protrude 0.12 m past the locked front plane.
        z0 = max(
            centre_z - vault_half_depths[vault_index],
            29.28,
        )
        z1 = min(
            centre_z + vault_half_depths[vault_index],
            94.32,
        )
        # Five primary rings on LOD0 give every shell a thick structural
        # cadence; lower LODs preserve the front/centre/rear silhouette.
        ring_zs = (
            (z0, z0 + 3.75, centre_z, z1 - 3.75, z1)
            if lod == 0
            else (z0, centre_z, z1)
            if lod == 1
            else (z0, z1)
        )
        profiles = []
        for ring_index, ring_z in enumerate(ring_zs):
            profile = _petal_vault_profile(
                centre_x,
                spring_y,
                ring_z,
                half_width,
                rise,
                profile_segments,
                vault_crown_biases[vault_index],
            )
            profiles.append(profile)
            _sweep(
                specs,
                f"a21-conservatory-vault-{vault_index}-curved-primary-rib",
                "verdigris_bronze" if vault_index % 2 == 0 else "brass",
                group, profile,
                (0.48, 0.30, 0.18)[lod], rib_sides,
            )
            if lod == 0 and ring_index % 2 == 0:
                shadow_profile = tuple(
                    (point[0], point[1] - 0.20, point[2] + 0.06)
                    for point in profile
                )
                _sweep(
                    specs, "a21-conservatory-primary-rib-cast-shadow",
                    "dark_wood", group, shadow_profile,
                    (0.080, 0.060)[lod], (6, 5)[lod],
                )
        # Grounded spring buttresses.
        for side in (-1.0, 1.0):
            _chamfer_box(
                specs, "a21-conservatory-vault-buttress", "carved_stone", group,
                centre_x + side * half_width, 4.65, centre_z,
                2.40, 8.7, 7.2, 0.14, 1,
            )
        # Secondary purlins bridge the front/back ribs.
        front = _petal_vault_profile(
            centre_x,
            spring_y,
            z0,
            half_width,
            rise,
            profile_segments,
            vault_crown_biases[vault_index],
        )
        rear = _petal_vault_profile(
            centre_x,
            spring_y,
            z1,
            half_width,
            rise,
            profile_segments,
            vault_crown_biases[vault_index],
        )
        shell_glass = (
            "glass_highlight" if vault_index % 2 == 0 else "dirty_glass"
        )
        # Camera-facing end glazing closes the visual volume of every barrel.
        # Without these fan cells, a diagonal first-person view sees only
        # narrow roof ribbons and the five-shell landmark loses its identity.
        for index in range(0, profile_segments, glass_step):
            nxt = min(profile_segments, index + glass_step)
            _panel(
                specs, "a21-conservatory-camera-facing-glass-fan-cell",
                shell_glass, group,
                (
                    front[index],
                    front[nxt],
                    (front[nxt][0], spring_y, z0),
                    (front[index][0], spring_y, z0),
                ),
                0.022,
            )
        # Radial mullions and inset transom arches give every front fan a
        # legible pane grid instead of one uniform cyan bubble.
        radial_step = (3, 5, 6)[lod]
        for index in range(0, profile_segments + 1, radial_step):
            _sweep(
                specs, "a21-conservatory-camera-facing-radial-mullion",
                "brass" if vault_index % 2 == 0 else "verdigris_bronze",
                group,
                (
                    (centre_x, spring_y + 0.12, z0 - 0.035),
                    (front[index][0], front[index][1], z0 - 0.035),
                ),
                (0.042, 0.034, 0.026)[lod], (7, 6, 4)[lod],
            )
        transom_scales = (
            (0.56, 0.79) if lod == 0
            else (0.70,) if lod == 1
            else ()
        )
        for scale in transom_scales:
            _sweep(
                specs, "a21-conservatory-camera-facing-inset-transom",
                "brass" if vault_index % 2 == 0 else "verdigris_bronze",
                group,
                _petal_vault_profile(
                    centre_x,
                    spring_y,
                    z0 - 0.045,
                    half_width * scale,
                    rise * scale,
                    profile_segments,
                    vault_crown_biases[vault_index] * scale,
                ),
                (0.068, 0.052)[lod], (7, 6)[lod],
            )
        for side in (-1.0, 1.0):
            spring_x = centre_x + side * half_width
            _chamfer_box(
                specs, "a21-conservatory-camera-facing-stone-spring-pylon",
                "carved_stone", group,
                spring_x, 4.15, z0 + 1.55,
                2.75, 7.8, 3.0, (0.13, 0.10, 0.08)[lod], 1,
            )
            _chamfer_box(
                specs, "a21-conservatory-camera-facing-stone-spring-cap",
                "ivory_stone", group,
                spring_x, 7.95, z0 + 1.85,
                3.0, 0.55, 3.55, (0.075, 0.060, 0.050)[lod], 1,
            )
        purlin_step = (1, 2, 4)[lod]
        for index in range(0, len(front), purlin_step):
            _sweep(
                specs, "a21-conservatory-secondary-purlin",
                "brass" if index % (purlin_step * 2) == 0 else "verdigris_bronze",
                group, (front[index], rear[index]),
                (0.045, 0.035, 0.025)[lod], (7, 6, 4)[lod],
            )
        # Dirty reflective cells follow the actual vault curvature.
        for index in range(0, profile_segments, glass_step):
            nxt = min(profile_segments, index + glass_step)
            pane_corners = (
                front[index], front[nxt], rear[nxt], rear[index]
            )
            _panel(
                specs, "a21-conservatory-dirty-glass-cell", "dirty_glass", group,
                pane_corners, 0.035,
            )
            # Eevee can visually lose a single dark pane layer against the
            # overlapping ribs.  A second, slightly inset, tinted layer keeps
            # all five vault shells readable while preserving the base
            # weathered-glass response behind it.
            highlight_corners = tuple(
                (point[0], point[1] - 0.065, point[2])
                for point in pane_corners
            )
            _panel(
                specs, "a21-conservatory-tinted-glass-highlight-layer",
                shell_glass, group, highlight_corners, 0.018,
            )
            if lod == 0 and index % 2 == 0:
                _sweep(
                    specs, "a21-conservatory-fine-diagonal-glass-brace",
                    "verdigris_bronze", group,
                    (front[index], rear[nxt]), 0.018, 6,
                )
                _sweep(
                    specs, "a21-conservatory-fine-diagonal-glass-brace",
                    "verdigris_bronze", group,
                    (rear[index], front[nxt]), 0.018, 6,
                )
    # A cylindrical stone-and-glass entry drum turns the threshold into an
    # occupied destination and visually anchors all five shells.
    _chamfer_box(
        specs, "a21-conservatory-monumental-entry-drum",
        "carved_stone", group,
        52.0, 7.0, 34.0, 32.0, 12.0, 10.0, 0.18,
        2 if lod == 0 else 1,
    )
    drum_course_count = (4, 3, 2)[lod]
    for course_index in range(drum_course_count):
        _chamfer_box(
            specs, "a21-conservatory-entry-drum-weathered-course",
            "wet_stone", group,
            52.0, 1.65 + course_index * (
                10.7 / max(1, drum_course_count - 1)
            ),
            29.05, 32.4, 0.24, 0.42,
            (0.045, 0.040, 0.035)[lod], 1,
        )
    drum_joint_count = (9, 6, 4)[lod]
    for joint_index in range(drum_joint_count):
        joint_x = 37.1 + joint_index * (
            29.8 / max(1, drum_joint_count - 1)
        )
        _chamfer_box(
            specs, "a21-conservatory-entry-drum-vertical-stone-joint",
            "wet_stone", group,
            joint_x, 7.0, 29.05,
            0.18, 11.7, 0.44, (0.035, 0.030, 0.025)[lod], 1,
        )
    _cylinder(
        specs, "a21-conservatory-entry-drum-cornice",
        "brass", group,
        52.0, 13.25, 36.8, 8.0, 1.0, (28, 18, 10)[lod],
        top_radius=8.0,
    )
    _cylinder(
        specs, "a21-conservatory-occupied-glass-lantern",
        "dirty_glass", group,
        52.0, 16.1, 36.8, 7.0, 5.2, (28, 18, 10)[lod],
        top_radius=4.8,
    )
    if lod <= 1:
        entry_columns = 3 if lod == 0 else 2
        for column in range(entry_columns):
            _deep_window(
                specs, group=group,
                role="a21-conservatory-entry-drum-deep-door",
                x=42.0 + column * (20.0 / max(1, entry_columns - 1)),
                y=6.4, z=29.10, width=3.8, height=7.6, warm=True,
            )
    # Monumental five-petal entry fan nested in the front vault.
    fan_count = (5, 5, 3)[lod]
    for index in range(fan_count):
        offset = (index - (fan_count - 1) / 2.0) * 4.1
        points = (
            (52.0 + offset * 0.28, 1.25, 28.95),
            (52.0 + offset, 8.2 + abs(offset) * 0.18, 29.0),
            (52.0 + offset * 0.35, 18.5 - abs(offset) * 0.32, 29.0),
            (52.0, 22.0 - abs(offset) * 0.25, 29.0),
        )
        _sweep(
            specs, "a21-conservatory-monumental-entry-fan",
            "brass", group, points, (0.11, 0.09, 0.07)[lod], rib_sides,
        )
    # Stone threshold and readable stairs.
    stair_count = (8, 6, 4)[lod]
    for index in range(stair_count):
        _chamfer_box(
            specs, "a21-conservatory-entry-stair", "carved_stone", group,
            52.0, 0.14 + index * 0.16, 29.20 + index * 0.56,
            12.0 - index * 0.28, 0.28, 0.74, 0.045, 1,
        )
    # Two supported upper walks and a rear botanical destination.
    for side in (-1.0, 1.0):
        walk_x = 52.0 + side * 15.0
        _chamfer_box(specs, "a21-conservatory-upper-walk", "carved_stone", group,
                     walk_x, 10.15, 63.0, 3.0, 0.45, 48.0, 0.07, 1)
        support_count = (7, 5, 3)[lod]
        for index in range(support_count):
            z = 42.0 + index * (42.0 / max(1, support_count - 1))
            _cylinder(specs, "a21-conservatory-walk-support", "brass", group,
                      walk_x, 5.7, z, 0.18, 9.2, (10, 8, 6)[lod], top_radius=0.18)
        _sweep(
            specs, "a21-conservatory-upper-walk-rail", "brass", group,
            ((walk_x - side * 1.25, 11.25, 39.0),
             (walk_x - side * 1.25, 11.25, 87.0)),
            (0.035, 0.03, 0.025)[lod], (7, 6, 4)[lod],
        )
    if lod == 0:
        # A camera-visible cross-walk proves that the five shells contain a
        # working botanical institution rather than an empty glass volume.
        _chamfer_box(
            specs, "a21-conservatory-interior-cross-catwalk",
            "carved_stone", group,
            52.0, 7.55, 55.5, 31.0, 0.38, 2.4, 0.065, 1,
        )
        for rail_z in (54.18, 56.82):
            _sweep(
                specs, "a21-conservatory-interior-cross-catwalk-handrail",
                "brass", group,
                ((36.6, 8.82, rail_z), (67.4, 8.82, rail_z)),
                0.034, 7,
            )
            for post_index in range(9):
                post_x = 36.6 + post_index * 3.85
                _sweep(
                    specs, "a21-conservatory-interior-cross-catwalk-post",
                    "verdigris_bronze", group,
                    ((post_x, 7.76, rail_z), (post_x, 8.82, rail_z)),
                    0.027, 6,
                )
        for lantern_index in range(5):
            lantern_x = 40.0 + lantern_index * 6.0
            _sweep(
                specs, "a21-conservatory-cross-catwalk-lantern-drop",
                "brass", group,
                ((lantern_x, 7.30, 55.5), (lantern_x, 6.30, 55.5)),
                0.022, 6,
            )
            _chamfer_box(
                specs, "a21-conservatory-cross-catwalk-lantern-glow",
                "warm_glow", group,
                lantern_x, 6.12, 55.5,
                0.38, 0.46, 0.38, 0.045, 1,
            )
    _chamfer_box(specs, "a21-conservatory-botanical-destination", "carved_stone", group,
                 52.0, 4.7, 91.0, 31.0, 7.7, 6.5, 0.12, 1)
    _arcade(
        specs, group=group, role="a21-conservatory-destination-arcade",
        material="carved_stone", x0=39.0, x1=65.0, z=87.72,
        base_y=1.1, bays=(7, 5, 3)[lod], lod=lod,
        depth=(0.18, 0.16, 0.14)[lod],
    )
    # Interior garden uses branch hierarchy plus leaf cards, never ellipsoids.
    tree_count = (15, 9, 5)[lod]
    for index in range(tree_count):
        side = -1.0 if index % 2 == 0 else 1.0
        lane = index // 2
        x = 52.0 + side * (10.0 + (lane % 2) * 4.0)
        z = 39.0 + lane * 6.4
        _chamfer_box(specs, "a21-conservatory-garden-planter",
                     "carved_stone", group, x, 1.75, z, 5.6, 1.1, 4.2, 0.09, 1)
        _box(specs, "a21-conservatory-garden-soil", "wet_stone", group,
             x, 2.31, z, 5.0, 0.16, 3.6)
        _tree(
            specs, group=group, role="a21-conservatory-specimen",
            x=x, z=z, height=7.0 + (index % 3) * 1.1,
            crown=3.0 + (index % 2) * 0.5, lod=lod, seed=3100 + index,
            flowering=index % 5 == 0,
        )
    # Three large dark canopy volumes and warm aisle lanterns stay legible
    # through the tinted shells in the player-height hero view.
    for canopy_index, (x, z) in enumerate((
        (34.0, 48.0), (52.0, 63.0), (70.0, 78.0),
    )):
        _tree(
            specs, group=group, role="a21-conservatory-hero-canopy",
            x=x, z=z, height=19.0, crown=7.2, lod=lod,
            seed=7300 + canopy_index, flowering=canopy_index == 1,
        )
    aisle_lantern_count = (10, 7, 4)[lod]
    for lantern_index in range(aisle_lantern_count):
        aisle_side = -1.0 if lantern_index % 2 == 0 else 1.0
        aisle_lane = lantern_index // 2
        _cylinder(
            specs, "a21-conservatory-warm-aisle-lantern",
            "warm_glow", group,
            52.0 + aisle_side * 8.0, 4.4,
            43.0 + aisle_lane * 9.0,
            0.25, 3.2, (10, 8, 6)[lod], top_radius=0.16,
        )
    # Hanging botanical clusters enrich the vault volume.
    hanging_count = (18, 10, 4)[lod]
    for index in range(hanging_count):
        x = 35.0 + (index % 6) * 6.8
        z = 45.0 + (index // 6) * 17.0
        _sweep(
            specs, "a21-conservatory-hanging-chain", "brass", group,
            ((x, 19.0 + (index % 3) * 1.2, z),
             (x, 14.2 + (index % 2) * 0.8, z)),
            0.025, 5,
        )
        _leaf_cluster(
            specs, "a21-conservatory-hanging-leaf-cluster",
            "foliage_light" if index % 2 else "foliage_dark", group,
            x, 13.7 + (index % 2) * 0.8, z,
            1.35, 1.7, (10, 7, 4)[lod], 4100 + index,
        )


DISTRICT_SITES = (
    (-142.0, -118.0, 27.0, 22.0, 34.0), (-109.0, -139.0, 29.0, 19.0, 30.0),
    (-72.0, -141.0, 27.0, 18.0, 38.0), (-31.0, -140.0, 25.0, 18.0, 31.0),
    (27.0, -140.0, 26.0, 18.0, 35.0), (70.0, -139.0, 30.0, 19.0, 32.0),
    (112.0, -138.0, 29.0, 20.0, 37.0), (141.0, -106.0, 22.0, 27.0, 29.0),
    (141.0, -66.0, 22.0, 25.0, 35.0), (141.0, -25.0, 22.0, 25.0, 31.0),
    (140.0, 28.0, 23.0, 28.0, 38.0), (141.0, 72.0, 22.0, 27.0, 34.0),
    (140.0, 116.0, 24.0, 27.0, 31.0), (108.0, 139.0, 29.0, 19.0, 37.0),
    (70.0, 140.0, 28.0, 18.0, 33.0), (24.0, 140.0, 31.0, 18.0, 39.0),
    (-27.0, 140.0, 29.0, 18.0, 34.0), (-70.0, 139.0, 28.0, 19.0, 37.0),
    (-112.0, 139.0, 30.0, 19.0, 32.0), (-141.0, 111.0, 23.0, 27.0, 38.0),
    (-141.0, 69.0, 22.0, 27.0, 32.0), (-141.0, 27.0, 23.0, 27.0, 36.0),
    (-141.0, -23.0, 22.0, 27.0, 30.0), (-141.0, -69.0, 23.0, 27.0, 37.0),
)


def _add_district(specs: list[dict], lod: int) -> None:
    group = "a21-nakaniwa-dedicated-garden-city"
    site_limit = (24, 20, 14)[lod]
    for index, (x, z, width, depth, height) in enumerate(DISTRICT_SITES[:site_limit]):
        camera_visible_front = 2 <= index <= 11
        material = (
            "ivory_stone", "moss_stone", "carved_stone", "ivory_stone"
        )[index % 4]
        _chamfer_box(
            specs, "a21-district-occupied-facade", material, group,
            x, height * 0.43, z, width, height * 0.86, depth,
            (0.14, 0.11, 0.09)[lod], 2 if lod == 0 else 1,
        )
        upper_width = width * (0.68 + (index % 2) * 0.08)
        upper_height = height * 0.22
        _chamfer_box(
            specs, "a21-district-planted-upper-pavilion", "carved_stone", group,
            x, height * 0.86 + upper_height / 2.0 - 0.12, z,
            upper_width, upper_height, depth * 0.66, (0.10, 0.08, 0.06)[lod], 1,
        )
        roof_base = height * 0.86 + upper_height - 0.2
        roof_variant = index % 4
        if roof_variant == 0:
            _roof(
                specs, group=group, role="a21-district-broad-garden-roof",
                cx=x, base_y=roof_base, cz=z,
                width=upper_width + 1.4, depth=depth * 0.66 + 1.2,
                rise=2.6, material="verdigris_bronze",
            )
        elif roof_variant == 1:
            _chamfer_box(
                specs, "a21-district-stepped-roof-lantern",
                "carved_stone", group,
                x, roof_base + 1.5, z,
                upper_width * 0.52, 3.0, depth * 0.38,
                (0.10, 0.08, 0.06)[lod], 1,
            )
            _roof(
                specs, group=group, role="a21-district-steep-lantern-roof",
                cx=x, base_y=roof_base + 3.0, cz=z,
                width=upper_width * 0.58, depth=depth * 0.44,
                rise=4.2, material="verdigris_bronze",
            )
        elif roof_variant == 2:
            for finial_side in (-1.0, 0.0, 1.0):
                _cylinder(
                    specs, "a21-district-botanical-roof-finial",
                    "brass", group,
                    x + finial_side * upper_width * 0.27,
                    roof_base + 2.1 + (1.0 - abs(finial_side)) * 1.2,
                    z, 0.24, 4.2 + (1.0 - abs(finial_side)) * 2.4,
                    (10, 8, 6)[lod], top_radius=0.05,
                )
        else:
            for roof_side in (-1.0, 1.0):
                _roof(
                    specs, group=group,
                    role="a21-district-split-butterfly-roof",
                    cx=x + roof_side * upper_width * 0.22,
                    base_y=roof_base, cz=z,
                    width=upper_width * 0.56, depth=depth * 0.68,
                    rise=3.0 + (0.4 if roof_side > 0 else 0.0),
                    material="verdigris_bronze",
                )
        if lod <= 1:
            rail_z = z - math.copysign(depth * 0.34, z)
            _sweep(
                specs, "a21-district-planted-balcony-handrail", "brass", group,
                ((x - width * 0.32, height * 0.69, rail_z),
                 (x + width * 0.32, height * 0.69, rail_z)),
                (0.030, 0.025)[lod], (8, 6)[lod],
            )
            post_count = (
                (7 if camera_visible_front else 3)
                if lod == 0 else 4
            )
            for post_index in range(post_count):
                post_x = x - width * 0.32 + post_index * (
                    width * 0.64 / max(1, post_count - 1)
                )
                _sweep(
                    specs, "a21-district-planted-balcony-post", "brass", group,
                    ((post_x, height * 0.65, rail_z),
                     (post_x, height * 0.70, rail_z)),
                    (0.024, 0.021)[lod], (7, 5)[lod],
                )
        # Inner-facing facade receives carved arch loggias and deep glazing.
        if abs(z) >= abs(x):
            facade_z = z - math.copysign(depth / 2.0 + 0.08, z)
            bays = (
                (5 if camera_visible_front else 3)
                if lod == 0 else (4, 3)[lod - 1]
            )
            _arcade(
                specs, group=group, role="a21-district-carved-loggia",
                material="carved_stone", x0=x - width * 0.40,
                x1=x + width * 0.40, z=facade_z,
                base_y=0.2, bays=bays,
                # Distant district arches preserve silhouette with the LOD1
                # sweep cross-section at LOD0; hero assets keep full density.
                lod=1 if lod == 0 else 2 if lod == 1 else lod,
                depth=(0.16, 0.14, 0.12)[lod],
            )
            if lod <= 1:
                window_count = (
                    (4 if camera_visible_front else 2)
                    if lod == 0 else 2
                )
                for bay_index in range(window_count):
                    _deep_window(
                        specs, group=group, role="a21-district-deep-window",
                        x=x - width * 0.28 + bay_index * (
                            width * 0.56 / max(1, window_count - 1)
                        ),
                        y=height * 0.56, z=facade_z - math.copysign(0.12, z),
                        width=1.6, height=2.5, warm=(index + bay_index) % 5 == 0,
                    )
        else:
            facade_x = x - math.copysign(width / 2.0 + 0.08, x)
            side_bays = (3, 3, 2)[lod]
            side_z0 = z - depth * 0.40
            side_z1 = z + depth * 0.40
            side_bay = (side_z1 - side_z0) / side_bays
            for side_bay_index in range(side_bays):
                bay_z = side_z0 + side_bay * (side_bay_index + 0.5)
                rotated_arch = tuple(
                    (facade_x, arch_y, arch_x)
                    for arch_x, arch_y, _ in _arch_points(
                        bay_z, 0.2, 0.0, side_bay * 0.37,
                        3.4, 2.15, (12, 10, 5)[lod],
                    )
                )
                _sweep(
                    specs, "a21-district-side-carved-loggia-curved-rib",
                    "carved_stone", group,
                    rotated_arch, (0.16, 0.14, 0.12)[lod], (6, 5, 4)[lod],
                )
                _chamfer_box(
                    specs, "a21-district-side-carved-loggia-pier",
                    "carved_stone", group,
                    facade_x, 2.85, side_z0 + side_bay * side_bay_index,
                    0.74, 5.7, 0.62, 0.055, 1,
                )
            _chamfer_box(
                specs, "a21-district-side-carved-loggia-pier",
                "carved_stone", group,
                facade_x, 2.85, side_z1,
                0.74, 5.7, 0.62, 0.055, 1,
            )
            _chamfer_box(
                specs, "a21-district-side-carved-loggia-entablature",
                "carved_stone", group,
                facade_x, 5.72, z,
                0.88, 0.74, side_z1 - side_z0 + 0.7, 0.055, 1,
            )
            if lod <= 1:
                window_count = (
                    (4 if camera_visible_front else 2)
                    if lod == 0 else 2
                )
                for bay_index in range(window_count):
                    _deep_window(
                        specs, group=group, role="a21-district-deep-side-window",
                        x=facade_x, y=height * 0.56,
                        z=z - depth * 0.28 + bay_index * (
                            depth * 0.56 / max(1, window_count - 1)
                        ),
                        width=1.6, height=2.5, plane="side",
                        warm=(index + bay_index) % 5 == 0,
                    )
        if lod == 0 and camera_visible_front:
            # A sparse second occupied row breaks the former blank-box read.
            for bay_index in range(3):
                if abs(z) >= abs(x):
                    _deep_window(
                        specs, group=group, role="a21-district-upper-deep-window",
                        x=x - width * 0.24 + bay_index * width * 0.24,
                        y=height * 0.77,
                        z=facade_z - math.copysign(0.12, z),
                        width=1.35, height=2.15,
                        warm=(index + bay_index) % 7 == 0,
                    )
                else:
                    _deep_window(
                        specs, group=group,
                        role="a21-district-upper-deep-side-window",
                        x=facade_x, y=height * 0.77,
                        z=z - depth * 0.22 + bay_index * depth * 0.22,
                        width=1.35, height=2.15, plane="side",
                        warm=(index + bay_index) % 7 == 0,
                    )
            # Every camera-facing far block has one unmistakably occupied
            # public threshold.  The warm portals also create a night-ready
            # depth rhythm without turning the skyline into emissive noise.
            if abs(z) >= abs(x):
                _deep_window(
                    specs, group=group,
                    role="a21-district-camera-visible-warm-public-portal",
                    x=x, y=2.25,
                    z=facade_z - math.copysign(0.14, z),
                    width=2.15, height=3.65, warm=True,
                )
            else:
                _deep_window(
                    specs, group=group,
                    role="a21-district-camera-visible-warm-public-portal",
                    x=facade_x, y=2.25, z=z,
                    width=2.15, height=3.65, plane="side", warm=True,
                )
            if index % 2 == 1:
                _chamfer_box(
                    specs, "a21-district-camera-visible-roof-garden-planter",
                    "carved_stone", group,
                    x - width * 0.16,
                    height * 0.86 + upper_height + 0.42,
                    z, 3.6, 0.78, 2.8, 0.060, 1,
                )
                _leaf_cluster(
                    specs, "a21-district-camera-visible-roof-garden",
                    "foliage_light", group,
                    x - width * 0.16,
                    height * 0.86 + upper_height + 1.42,
                    z, 1.65, 1.20, 9, 11800 + index,
                )
            facade_family = index % 3
            if abs(z) >= abs(x):
                if facade_family == 0:
                    for pier_index in range(5):
                        _chamfer_box(
                            specs, "a21-district-front-family-engaged-pier",
                            "ivory_stone", group,
                            x - width * 0.36 + pier_index * width * 0.18,
                            height * 0.43, facade_z,
                            0.62, height * 0.70, 0.72, 0.055, 1,
                        )
                elif facade_family == 1:
                    for level in (height * 0.42, height * 0.68):
                        _chamfer_box(
                            specs, "a21-district-front-family-deep-balcony",
                            "carved_stone", group,
                            x, level, facade_z - math.copysign(0.42, z),
                            width * 0.76, 0.38, 1.45, 0.060, 1,
                        )
                else:
                    for level in (height * 0.30, height * 0.52, height * 0.74):
                        _chamfer_box(
                            specs, "a21-district-front-family-stone-course",
                            "wet_stone", group,
                            x, level, facade_z,
                            width * 0.84, 0.28, 0.58, 0.045, 1,
                        )
            else:
                if facade_family == 0:
                    for pier_index in range(5):
                        _chamfer_box(
                            specs, "a21-district-front-family-engaged-pier",
                            "ivory_stone", group,
                            facade_x, height * 0.43,
                            z - depth * 0.36 + pier_index * depth * 0.18,
                            0.72, height * 0.70, 0.62, 0.055, 1,
                        )
                elif facade_family == 1:
                    for level in (height * 0.42, height * 0.68):
                        _chamfer_box(
                            specs, "a21-district-front-family-deep-balcony",
                            "carved_stone", group,
                            facade_x - math.copysign(0.42, x), level, z,
                            1.45, 0.38, depth * 0.76, 0.060, 1,
                        )
                else:
                    for level in (height * 0.30, height * 0.52, height * 0.74):
                        _chamfer_box(
                            specs, "a21-district-front-family-stone-course",
                            "wet_stone", group,
                            facade_x, level, z,
                            0.58, 0.28, depth * 0.84, 0.045, 1,
                        )
        # Roof gardens break repetition without cloning tree silhouettes.
        if lod <= 1 and index % 2 == 0:
            _chamfer_box(
                specs, "a21-district-roof-planter", "carved_stone", group,
                x + width * 0.18, height * 0.86 + upper_height + 0.45,
                z, 3.8, 0.9, 3.0, 0.07, 1,
            )
            _leaf_cluster(
                specs, "a21-district-roof-leaf-cluster",
                "foliage_dark" if index % 4 else "foliage_light", group,
                x + width * 0.18, height * 0.86 + upper_height + 1.55,
                z, 1.8, 1.4, (10, 7)[lod], 5200 + index,
            )


def _add_garden_city_composition(specs: list[dict], lod: int) -> None:
    group = "a21-nakaniwa-garden-canal-route"
    # Full real ground and canonical 16 m road visuals.
    _box(specs, "a21-garden-city-ground", "ivory_stone", group,
         0.0, -0.34, 0.0, 320.0, 0.52, 320.0)
    for road in CANONICAL_ROADS:
        bounds = road["bounds"]
        _box(
            specs, "a21-canonical-road-visual", "carved_stone", group,
            (bounds["minX"] + bounds["maxX"]) / 2.0, -0.02,
            (bounds["minZ"] + bounds["maxZ"]) / 2.0,
            bounds["maxX"] - bounds["minX"], 0.10,
            bounds["maxZ"] - bounds["minZ"],
        )
    # The primary camera stands on this dry stone ceremonial route; it keeps
    # water below fifteen percent of the frame and pulls the eye to both heroes.
    _panel(
        specs, "a21-primary-stone-promenade", "ivory_stone", group,
        ((88.0, 0.10, -112.0), (112.0, 0.10, -90.0),
         (15.0, 0.10, -20.0), (-2.0, 0.10, -36.0)), 0.10,
    )
    # Diagonal quadrilateral water garden compresses foreground depth.
    _panel(
        specs, "a21-garden-canal-water", "water", group,
        ((-14.0, 0.12, -73.0), (85.0, 0.12, -76.0),
         (88.0, 0.12, -95.0), (-5.0, 0.12, -92.0)), 0.10,
    )
    for start, end in (
        ((-14.0, 0.42, -73.0), (85.0, 0.42, -76.0)),
        ((-5.0, 0.42, -92.0), (88.0, 0.42, -95.0)),
    ):
        _panel(
            specs, "a21-garden-canal-coping", "carved_stone", group,
            (
                (start[0], 0.22, start[2]),
                (end[0], 0.22, end[2]),
                (end[0], 0.64, end[2]),
                (start[0], 0.64, start[2]),
            ),
            (0.16, 0.14, 0.12)[lod],
        )
    for start, end in (
        ((-14.0, 0.18, -73.18), (85.0, 0.18, -76.18)),
        ((-5.0, 0.18, -91.82), (88.0, 0.18, -94.82)),
    ):
        _sweep(
            specs, "a21-garden-canal-contact-shadow-seam",
            "wet_stone", group,
            (start, end), (0.075, 0.060, 0.045)[lod], (7, 6, 4)[lod],
        )
    # Broken cool streaks give the opaque WebGL-safe water a readable
    # reflection response without a full planar-reflection pass.
    reflection_count = (8, 5, 3)[lod]
    for index in range(reflection_count):
        centre_x = 1.0 + index * (72.0 / max(1, reflection_count - 1))
        centre_z = -80.2 - centre_x * (2.1 / 74.0)
        span = 3.4 + (index % 3) * 1.2
        _sweep(
            specs, "a21-garden-canal-cool-reflection-streak",
            "glass_highlight", group,
            (
                (centre_x - span, 0.18, centre_z),
                (centre_x + span, 0.18, centre_z - 0.18),
            ),
            (0.022, 0.018, 0.014)[lod], (7, 5, 4)[lod],
        )
    reflection_patch_count = (5, 3, 2)[lod]
    for index in range(reflection_patch_count):
        centre_x = 10.0 + index * (
            62.0 / max(1, reflection_patch_count - 1)
        )
        centre_z = -81.0 - centre_x * (2.0 / 74.0)
        half_width = 2.4 + (index % 2) * 1.4
        _panel(
            specs, "a21-garden-canal-broken-reflection-patch",
            "glass_highlight", group,
            (
                (centre_x - half_width, 0.185, centre_z - 0.22),
                (centre_x + half_width, 0.185, centre_z - 0.32),
                (centre_x + half_width * 0.80, 0.185, centre_z + 0.28),
                (centre_x - half_width * 0.75, 0.185, centre_z + 0.22),
            ),
            0.012,
        )
    # Canal-edge handrails deliberately break around all three bridges.
    for rail_start_x, rail_end_x in ((-5.0, 10.0), (22.0, 41.0), (53.0, 68.0)):
        rail_start_z = -92.0 - (rail_start_x + 5.0) * (3.0 / 93.0)
        rail_end_z = -92.0 - (rail_end_x + 5.0) * (3.0 / 93.0)
        _sweep(
            specs, "a21-garden-canal-brass-handrail",
            "brass", group,
            (
                (rail_start_x, 1.18, rail_start_z),
                (rail_end_x, 1.18, rail_end_z),
            ),
            (0.038, 0.032, 0.026)[lod], (8, 6, 4)[lod],
        )
        post_count = (6, 4, 3)[lod]
        for post_index in range(post_count):
            t = post_index / max(1, post_count - 1)
            post_x = rail_start_x + (rail_end_x - rail_start_x) * t
            post_z = rail_start_z + (rail_end_z - rail_start_z) * t
            _sweep(
                specs, "a21-garden-canal-brass-rail-post",
                "brass", group,
                ((post_x, 0.42, post_z), (post_x, 1.18, post_z)),
                (0.030, 0.025, 0.021)[lod], (7, 5, 4)[lod],
            )
    # Low botanical ribbons occupy the far water edge while leaving all three
    # bridge thresholds and the canonical cross-road clear.
    water_edge_beds = (
        (-7.0, -70.7, 7.0),
        (29.0, -71.8, 8.5),
        (60.0, -72.7, 8.0),
        (82.0, -73.4, 6.0),
    )
    for index, (x, z, width) in enumerate(
        water_edge_beds[: (4, 4, 3)[lod]]
    ):
        _chamfer_box(
            specs, "a21-garden-canal-edge-botanical-planter",
            "carved_stone", group,
            x, 0.55, z, width, 0.86, 2.25,
            (0.075, 0.060, 0.050)[lod], 1,
        )
        _box(
            specs, "a21-garden-canal-edge-botanical-soil",
            "wet_stone", group,
            x, 0.99, z, width - 0.55, 0.14, 1.70,
        )
        _leaf_cluster(
            specs, "a21-garden-canal-edge-botanical-leaf-cluster",
            "flower" if index % 2 == 0 else "foliage_light", group,
            x, 1.50, z, width * 0.43, 0.90,
            (28, 16, 8)[lod], 9700 + index,
        )
    joint_count = (16, 9, 4)[lod]
    for index in range(joint_count):
        x = -10.0 + index * (88.0 / max(1, joint_count - 1))
        _sweep(
            specs, "a21-foreground-paving-joint", "brass", group,
            ((x, 0.12, -86.0), (x - 34.0, 0.12, -12.0)),
            (0.012, 0.010, 0.008)[lod], (6, 5, 4)[lod],
        )
    route_joint_count = (18, 10, 5)[lod]
    for index in range(route_joint_count):
        route_t = 0.020 + index * (0.68 / max(1, route_joint_count - 1))
        centre_x = 105.0 - 110.0 * route_t
        centre_z = -110.0 + 107.0 * route_t
        _sweep(
            specs, "a21-primary-promenade-carved-cross-joint",
            "wet_stone", group,
            (
                (centre_x - 6.5 * 0.697, 0.18, centre_z - 6.5 * 0.717),
                (centre_x + 6.5 * 0.697, 0.18, centre_z + 6.5 * 0.717),
            ),
            (0.010, 0.009, 0.008)[lod], (7, 6, 4)[lod],
        )
    for start, end in (
        ((96.5, 0.18, -103.5), (3.6, 0.18, -21.4)),
        ((103.5, 0.18, -96.5), (6.4, 0.18, -18.6)),
        ((99.0, 0.18, -101.0), (5.0, 0.18, -20.0)),
        ((101.0, 0.18, -99.0), (7.0, 0.18, -19.0)),
    ):
        _sweep(
            specs, "a21-primary-promenade-longitudinal-joint",
            "wet_stone", group,
            (start, end), (0.012, 0.010, 0.008)[lod], (7, 6, 4)[lod],
        )
    foreground_detail_sites = (
        (90.0, -103.0), (77.0, -86.0),
        (61.0, -69.0), (45.0, -52.0),
    )
    foreground_detail_limit = (4, 3, 2)[lod]
    for index, (x, z) in enumerate(
        foreground_detail_sites[:foreground_detail_limit]
    ):
        _leaf_cluster(
            specs, "a21-primary-promenade-leaf-litter-cluster",
            "flower" if index % 2 == 0 else "foliage_light", group,
            x - 2.2, 0.24, z + 1.0,
            1.65, 0.12, (24, 14, 7)[lod], 10400 + index,
        )
        _sweep(
            specs, "a21-primary-promenade-lantern-post",
            "brass", group,
            ((x + 3.5, 0.14, z), (x + 3.5, 2.65, z)),
            (0.050, 0.041, 0.032)[lod], (8, 6, 4)[lod],
        )
        _chamfer_box(
            specs, "a21-primary-promenade-lantern-glow",
            "warm_glow", group,
            x + 3.5, 2.82, z,
            0.42, 0.48, 0.42, 0.050, 1,
        )
    bridge_sites = ((16.0, -83.0), (47.0, -84.0), (74.0, -85.0))
    for bridge_index, (x, z) in enumerate(bridge_sites):
        _chamfer_box(
            specs, "a21-garden-bridge-deck", "carved_stone", group,
            x, 0.72, z, 8.2, 0.72, 24.0, 0.11, 1,
        )
        for step_index in range((4, 3, 2)[lod]):
            _chamfer_box(
                specs, "a21-garden-bridge-entry-step",
                "carved_stone", group,
                x, 0.12 + step_index * 0.12,
                z - 13.2 + step_index * 0.48,
                9.2 - step_index * 0.22, 0.24, 0.68,
                0.045, 1,
            )
        for side in (-1.0, 1.0):
            arch = _arch_points(
                x, 0.7, z + side * 11.85,
                3.35, 1.2, 1.15, (12, 8, 5)[lod],
            )
            _sweep(
                specs, "a21-garden-bridge-curved-parapet", "carved_stone",
                group, arch, (0.11, 0.09, 0.08)[lod], (8, 6, 4)[lod],
            )
        arch_z = z + 12.06
        for arch_index in range(2):
            arch_x = x - 2.05 + arch_index * 4.10
            arch_points = _arch_points(
                arch_x, 0.08, arch_z, 1.62, 0.72, 1.08,
                (10, 7, 4)[lod],
            )
            _sweep(
                specs,
                "a21-garden-bridge-camera-facing-twin-arch-curved-rib",
                "carved_stone", group,
                arch_points,
                (0.16, 0.14, 0.12)[lod], (6, 5, 4)[lod],
            )
            _sweep(
                specs, "a21-garden-bridge-arch-contact-shadow",
                "dark_wood", group,
                tuple(
                    (point[0], point[1] - 0.10, point[2] + 0.08)
                    for point in arch_points
                ),
                (0.075, 0.060, 0.045)[lod], (6, 5, 4)[lod],
            )
        for pier_x in (x - 4.10, x, x + 4.10):
            _chamfer_box(
                specs, "a21-garden-bridge-camera-facing-twin-arch-pier",
                "carved_stone", group,
                pier_x, 0.74, arch_z,
                0.52, 1.45, 0.66, 0.045, 1,
            )
        _chamfer_box(
            specs, "a21-garden-bridge-camera-facing-twin-arch-entablature",
            "carved_stone", group,
            x, 1.58, arch_z, 8.55, 0.44, 0.72, 0.045, 1,
        )
        if lod == 0 and bridge_index == 1:
            # Only the compositionally central bridge receives a full
            # player-scale railing and paired threshold lanterns.
            for rail_x in (x - 3.55, x + 3.55):
                _sweep(
                    specs, "a21-garden-central-bridge-handrail",
                    "brass", group,
                    ((rail_x, 1.55, z - 10.8), (rail_x, 1.55, z + 10.8)),
                    0.038, 8,
                )
                for post_index in range(6):
                    post_z = z - 10.8 + post_index * 4.32
                    _sweep(
                        specs, "a21-garden-central-bridge-rail-post",
                        "verdigris_bronze", group,
                        ((rail_x, 0.92, post_z), (rail_x, 1.55, post_z)),
                        0.029, 7,
                    )
            for lantern_x in (x - 3.55, x + 3.55):
                _sweep(
                    specs, "a21-garden-central-bridge-threshold-lantern-post",
                    "brass", group,
                    ((lantern_x, 0.42, z - 11.0),
                     (lantern_x, 2.55, z - 11.0)),
                    0.050, 8,
                )
                _chamfer_box(
                    specs, "a21-garden-central-bridge-threshold-lantern-glow",
                    "warm_glow", group,
                    lantern_x, 2.74, z - 11.0,
                    0.42, 0.50, 0.42, 0.050, 1,
                )
    # Layered garden rooms replace the empty plaza while leaving routes clear.
    garden_sites = (
        (95.0, -75.0), (60.0, -97.0),
        (78.0, -53.0), (47.0, -72.0), (13.0, -78.0), (-8.0, -52.0),
        (45.0, -45.0), (66.0, -34.0),
        (-28.0, -19.0), (-45.0, 1.0), (24.0, -8.0), (70.0, 4.0),
        (-95.0, -12.0), (96.0, 22.0), (-106.0, 32.0), (104.0, 60.0),
        (-112.0, 78.0), (108.0, 96.0),
    )
    site_limit = (14, 10, 7)[lod]
    for index, (x, z) in enumerate(garden_sites[:site_limit]):
        _chamfer_box(
            specs, "a21-garden-room-planter", "carved_stone", group,
            x, 0.72, z, 8.5 + (index % 3) * 1.8, 1.2,
            6.0 + (index % 2) * 1.6, 0.10, 1,
        )
        _box(specs, "a21-garden-room-soil", "wet_stone", group,
             x, 1.33, z, 7.8 + (index % 3) * 1.8, 0.18,
             5.3 + (index % 2) * 1.6)
        _tree(
            specs, group=group, role="a21-garden-sculpted-tree",
            x=x, z=z, height=6.2 + (index % 4) * 0.7,
            crown=2.3 + (index % 3) * 0.35, lod=lod,
            seed=6100 + index, flowering=index % 4 == 0,
        )
    # Two player-scale foreground prop clusters frame the primary shot with
    # practical light, seating, signage, pots and flowers on dry paving.
    for cluster_index, (x, z) in enumerate(((95.0, -85.0), (75.0, -96.0))):
        _chamfer_box(
            specs, "a21-foreground-bench-seat",
            "dark_wood", group,
            x, 0.76, z, 2.8, 0.24, 0.68, 0.045, 1,
        )
        for leg_side in (-1.0, 1.0):
            _sweep(
                specs, "a21-foreground-bench-leg",
                "brass", group,
                (
                    (x + leg_side * 0.92, 0.12, z),
                    (x + leg_side * 0.92, 0.67, z),
                ),
                (0.034, 0.029, 0.024)[lod], (8, 6, 4)[lod],
            )
        _cylinder(
            specs, "a21-foreground-flower-pot",
            "carved_stone", group,
            x - 2.2, 0.52, z - 0.4,
            0.52, 0.84, (14, 10, 7)[lod], top_radius=0.66,
        )
        _leaf_cluster(
            specs, "a21-foreground-flower-pot-leaf-cluster",
            "flower" if cluster_index else "foliage_light", group,
            x - 2.2, 1.35, z - 0.4,
            0.82, 1.25, (24, 14, 7)[lod], 8800 + cluster_index,
        )
        _sweep(
            specs, "a21-foreground-lantern-post",
            "brass", group,
            ((x + 2.0, 0.12, z), (x + 2.0, 3.0, z)),
            (0.055, 0.045, 0.035)[lod], (9, 7, 5)[lod],
        )
        _chamfer_box(
            specs, "a21-foreground-lantern-glow",
            "warm_glow", group,
            x + 2.0, 3.18, z, 0.46, 0.52, 0.46, 0.055, 1,
        )
        if lod <= 1:
            _panel(
                specs, "a21-foreground-wayfinding-sign",
                "carved_stone", group,
                (
                    (x + 2.65, 1.05, z - 0.10),
                    (x + 4.15, 1.05, z - 0.10),
                    (x + 4.15, 2.05, z - 0.10),
                    (x + 2.65, 2.05, z - 0.10),
                ),
                0.10,
            )
    # Low edge furniture fills the broad near stone without blocking the
    # centre of the ceremonial promenade.
    edge_sites = (
        (78.5, -99.0), (67.2, -83.0), (50.8, -67.0),
    )
    for index, (x, z) in enumerate(edge_sites[: (3, 3, 2)[lod]]):
        _chamfer_box(
            specs, "a21-foreground-low-botanical-planter",
            "carved_stone", group,
            x, 0.58, z, 4.6, 0.95, 1.65,
            (0.080, 0.065, 0.050)[lod], 1,
        )
        _leaf_cluster(
            specs, "a21-foreground-low-botanical-leaf-cluster",
            "flower" if index % 2 == 0 else "foliage_light", group,
            x, 1.28, z,
            2.0, 0.75, (28, 16, 8)[lod], 10800 + index,
        )
        if index < (2 if lod <= 1 else 1):
            _chamfer_box(
                specs, "a21-foreground-edge-bench-seat",
                "dark_wood", group,
                x + 3.7, 0.68, z + 1.3,
                2.7, 0.22, 0.64, 0.040, 1,
            )
            for side in (-1.0, 1.0):
                _sweep(
                    specs, "a21-foreground-edge-bench-leg",
                    "brass", group,
                    (
                        (x + 3.7 + side * 0.88, 0.15, z + 1.3),
                        (x + 3.7 + side * 0.88, 0.60, z + 1.3),
                    ),
                    (0.032, 0.027, 0.022)[lod], (7, 6, 4)[lod],
                )
    if lod <= 1:
        # A compact gardener tool rack and bucket provide a narrative prop
        # cluster beside the near planter.
        tool_x, tool_z = 68.0, -98.0
        _chamfer_box(
            specs, "a21-foreground-garden-tool-rack",
            "dark_wood", group,
            tool_x, 0.82, tool_z, 1.65, 0.22, 0.52, 0.035, 1,
        )
        for tool_index in range(4 if lod == 0 else 3):
            tool_offset = -0.60 + tool_index * 0.40
            _sweep(
                specs, "a21-foreground-garden-tool-handle",
                "brass", group,
                (
                    (tool_x + tool_offset, 0.25, tool_z),
                    (tool_x + tool_offset + 0.25, 2.15, tool_z),
                ),
                (0.026, 0.022)[lod], (7, 5)[lod],
            )
        _cylinder(
            specs, "a21-foreground-garden-tool-bucket",
            "carved_stone", group,
            tool_x + 1.25, 0.46, tool_z,
            0.42, 0.76, (12, 8)[lod], top_radius=0.52,
        )
    if lod == 0:
        # Thin members at the extreme right of the locked camera frame add a
        # human-scale garden-room threshold without repeating the rejected
        # foreground gallery's opaque occupied mass.
        pergola_x, pergola_z = 63.0, -99.5
        for post_x in (pergola_x - 2.55, pergola_x + 2.55):
            for post_z in (pergola_z - 3.8, pergola_z + 3.8):
                _chamfer_box(
                    specs, "a21-foreground-open-pergola-column",
                    "carved_stone", group,
                    post_x, 1.98, post_z,
                    0.38, 3.72, 0.38, 0.055, 1,
                )
        for beam_z in (pergola_z - 3.8, pergola_z + 3.8):
            _chamfer_box(
                specs, "a21-foreground-open-pergola-perimeter-beam",
                "dark_wood", group,
                pergola_x, 3.88, beam_z,
                5.5, 0.34, 0.38, 0.045, 1,
            )
        for beam_x in (pergola_x - 2.55, pergola_x + 2.55):
            _chamfer_box(
                specs, "a21-foreground-open-pergola-perimeter-beam",
                "dark_wood", group,
                beam_x, 3.88, pergola_z,
                0.38, 0.34, 7.9, 0.045, 1,
            )
        for slat_index in range(7):
            slat_z = pergola_z - 3.3 + slat_index * 1.1
            _chamfer_box(
                specs, "a21-foreground-open-pergola-roof-slat",
                "brass" if slat_index % 2 == 0 else "dark_wood", group,
                pergola_x, 4.08, slat_z,
                5.75, 0.15, 0.18, 0.030, 1,
            )
        for vine_index, (vine_x, vine_z) in enumerate((
            (68.1, -105.8), (70.4, -103.6), (72.0, -101.7),
        )):
            _leaf_cluster(
                specs, "a21-foreground-open-pergola-vine",
                "foliage_light" if vine_index == 1 else "foliage_dark", group,
                vine_x, 4.27, vine_z, 1.15, 0.55, 12, 12600 + vine_index,
            )
        _panel(
            specs, "a21-foreground-open-pergola-service-gate",
            "dark_wood", group,
            (
                (pergola_x - 0.75, 0.18, pergola_z + 3.99),
                (pergola_x + 0.75, 0.18, pergola_z + 3.99),
                (pergola_x + 0.75, 2.55, pergola_z + 3.99),
                (pergola_x - 0.75, 2.55, pergola_z + 3.99),
            ),
            0.08,
        )
        for gate_x in (pergola_x - 0.78, pergola_x + 0.78):
            _sweep(
                specs, "a21-foreground-open-pergola-service-gate-frame",
                "brass", group,
                ((gate_x, 0.16, pergola_z + 3.94),
                 (gate_x, 2.65, pergola_z + 3.94)),
                0.032, 7,
            )
        _sweep(
            specs, "a21-foreground-open-pergola-lantern-drop",
            "brass", group,
            ((pergola_x, 4.0, pergola_z), (pergola_x, 3.12, pergola_z)),
            0.025, 7,
        )
        _chamfer_box(
            specs, "a21-foreground-open-pergola-lantern-glow",
            "warm_glow", group,
            pergola_x, 2.96, pergola_z,
            0.42, 0.48, 0.42, 0.050, 1,
        )
    # Human-scale benches, lanterns and irrigation maintenance cluster.
    prop_count = (10, 6, 3)[lod]
    for index in range(prop_count):
        x = -20.0 + index * 8.0
        z = -20.0 + (index % 2) * 5.0
        _chamfer_box(specs, "a21-garden-bench-seat", "dark_wood", group,
                     x, 0.72, z, 2.2, 0.20, 0.58, 0.035, 1)
        for side in (-1.0, 1.0):
            _sweep(
                specs, "a21-garden-bench-leg", "brass", group,
                ((x + side * 0.75, 0.12, z), (x + side * 0.75, 0.64, z)),
                0.028, (7, 6, 4)[lod],
            )
    lantern_count = (12, 8, 4)[lod]
    for index in range(lantern_count):
        angle = index * math.tau / lantern_count
        x = 7.0 + math.cos(angle) * 56.0
        z = -24.0 + math.sin(angle) * 23.0
        _sweep(
            specs, "a21-garden-lantern-post", "brass", group,
            ((x, 0.0, z), (x, 2.4, z)), 0.035, (8, 6, 4)[lod],
        )
        _chamfer_box(specs, "a21-garden-lantern-glow", "warm_glow", group,
                     x, 2.55, z, 0.34, 0.42, 0.34, 0.045, 1)
    if lod == 0:
        _chamfer_box(specs, "a21-irrigation-service-cart", "dark_wood", group,
                     31.0, 0.72, -17.0, 2.8, 1.15, 1.5, 0.055, 1)
        for x in (30.0, 32.0):
            _cylinder(specs, "a21-irrigation-service-wheel", "brass", group,
                      x, 0.38, -17.85, 0.38, 0.20, 12, top_radius=0.38)
    _add_district(specs, lod)


R2_DISTRICT_SITES = (
    (-126.0, -126.0, 30.0, 21.0, 38.0),
    (-82.0, -132.0, 28.0, 19.0, 42.0),
    (-36.0, -132.0, 27.0, 19.0, 36.0),
    (26.0, -132.0, 29.0, 19.0, 41.0),
    (76.0, -132.0, 30.0, 20.0, 37.0),
    (126.0, -108.0, 22.0, 28.0, 40.0),
    (127.0, -61.0, 22.0, 27.0, 35.0),
    (127.0, -16.0, 22.0, 27.0, 43.0),
    (127.0, 34.0, 22.0, 28.0, 38.0),
    (126.0, 82.0, 22.0, 27.0, 41.0),
    (96.0, 128.0, 29.0, 20.0, 39.0),
    (49.0, 130.0, 30.0, 19.0, 44.0),
    (-3.0, 130.0, 30.0, 19.0, 37.0),
    (-55.0, 130.0, 29.0, 20.0, 42.0),
    (-105.0, 127.0, 30.0, 21.0, 39.0),
    (-128.0, 76.0, 22.0, 28.0, 43.0),
    (-128.0, 26.0, 22.0, 28.0, 37.0),
    (-128.0, -36.0, 22.0, 28.0, 41.0),
)


def _add_oriented_arch(
    specs: list[dict],
    *,
    group: str,
    role: str,
    centre_x: float,
    centre_z: float,
    axis_x: float,
    axis_z: float,
    half_width: float,
    base_y: float,
    spring_y: float,
    rise: float,
    segments: int,
    radius: float,
    sides: int,
    material: str,
) -> None:
    points = [
        (
            centre_x + axis_x * half_width * normalized,
            spring_y + rise * (1.0 - abs(normalized) ** 0.78),
            centre_z + axis_z * half_width * normalized,
        )
        for normalized in (
            -1.0 + 2.0 * index / segments
            for index in range(segments + 1)
        )
    ]
    points.insert(
        0,
        (
            centre_x - axis_x * half_width,
            base_y,
            centre_z - axis_z * half_width,
        ),
    )
    points.append(
        (
            centre_x + axis_x * half_width,
            base_y,
            centre_z + axis_z * half_width,
        )
    )
    _sweep(specs, role, material, group, tuple(points), radius, sides)


def _add_nakaniwa_pavilion_district(specs: list[dict], lod: int) -> None:
    """Dense stage-exclusive perimeter made from stepped garden pavilions."""
    group = "a21-r2-nakaniwa-terraced-pavilion-city"
    # Lower LODs reallocate generic far-perimeter geometry to the R3 middle
    # city, where it affects first-person depth and route enclosure.
    site_limit = (18, 14, 6)[lod]
    for index, (x, z, width, depth, height) in enumerate(
        R2_DISTRICT_SITES[:site_limit]
    ):
        lower_h = height * 0.37
        upper_h = height * 0.28
        lantern_h = height * 0.14
        material = (
            "ivory_stone",
            "carved_stone",
            "moss_stone",
            "ivory_stone",
        )[index % 4]
        _chamfer_box(
            specs,
            "a21-r2-district-garden-terrace-plinth",
            "wet_stone",
            group,
            x,
            0.55,
            z,
            width + 2.0,
            1.3,
            depth + 2.0,
            (0.14, 0.11, 0.08)[lod],
            1,
        )
        _chamfer_box(
            specs,
            "a21-r2-district-occupied-arcade-hall",
            material,
            group,
            x,
            lower_h * 0.5 + 0.9,
            z,
            width,
            lower_h,
            depth,
            (0.15, 0.11, 0.08)[lod],
            2 if lod == 0 else 1,
        )
        _chamfer_box(
            specs,
            "a21-r2-district-deep-terrace-course",
            "carved_stone",
            group,
            x,
            lower_h + 1.15,
            z,
            width + 1.2,
            1.0,
            depth + 1.0,
            (0.10, 0.08, 0.06)[lod],
            1,
        )
        upper_width = width * (0.52 + 0.06 * (index % 2))
        upper_depth = depth * (0.58 + 0.05 * ((index + 1) % 2))
        _chamfer_box(
            specs,
            "a21-r2-district-stepped-occupied-pavilion",
            "ivory_stone" if index % 3 else "carved_stone",
            group,
            x,
            lower_h + upper_h * 0.5 + 1.2,
            z,
            upper_width,
            upper_h,
            upper_depth,
            (0.12, 0.09, 0.07)[lod],
            1,
        )
        # Two occupied shoulder pavilions remove the single-box silhouette.
        shoulder_axis = "x" if abs(z) >= abs(x) else "z"
        for side in (-1.0, 1.0):
            shoulder_x = x + (
                side * width * 0.31 if shoulder_axis == "x" else 0.0
            )
            shoulder_z = z + (
                side * depth * 0.31 if shoulder_axis == "z" else 0.0
            )
            shoulder_w = width * (0.27 if shoulder_axis == "x" else 0.42)
            shoulder_d = depth * (0.42 if shoulder_axis == "x" else 0.27)
            _chamfer_box(
                specs,
                "a21-r2-district-shoulder-loggia-pavilion",
                "carved_stone",
                group,
                shoulder_x,
                lower_h + upper_h * 0.36 + 0.8,
                shoulder_z,
                shoulder_w,
                upper_h * 0.72,
                shoulder_d,
                (0.10, 0.08, 0.06)[lod],
                1,
            )
            _roof(
                specs,
                group=group,
                role="a21-r2-district-shoulder-garden-roof",
                cx=shoulder_x,
                base_y=lower_h + upper_h * 0.72 + 0.8,
                cz=shoulder_z,
                width=shoulder_w + 1.0,
                depth=shoulder_d + 1.0,
                rise=2.3 + 0.25 * (index % 3),
            )
        lantern_y = lower_h + upper_h + lantern_h * 0.5 + 0.8
        _chamfer_box(
            specs,
            "a21-r2-district-roof-lantern",
            "carved_stone",
            group,
            x,
            lantern_y,
            z,
            upper_width * 0.47,
            lantern_h,
            upper_depth * 0.50,
            (0.10, 0.08, 0.06)[lod],
            1,
        )
        _roof(
            specs,
            group=group,
            role="a21-r2-district-stage-exclusive-crown-roof",
            cx=x,
            base_y=lantern_y + lantern_h * 0.5 - 0.05,
            cz=z,
            width=upper_width * 0.56,
            depth=upper_depth * 0.60,
            rise=3.2 + 0.45 * (index % 4),
        )
        if index % 3 == 1:
            for finial_side in (-1.0, 0.0, 1.0):
                _cylinder(
                    specs,
                    "a21-r2-district-botanical-crown-finial",
                    "brass",
                    group,
                    x + finial_side * upper_width * 0.23,
                    lantern_y + lantern_h * 0.5 + 3.5,
                    z,
                    (0.19, 0.15, 0.12)[lod],
                    3.8 + (1.0 - abs(finial_side)) * 1.7,
                    (10, 8, 6)[lod],
                    top_radius=0.04,
                )
        # Inner-facing open arcade and occupied openings.
        if abs(z) >= abs(x):
            facade_z = z - math.copysign(depth * 0.5 + 0.12, z)
            _arcade(
                specs,
                group=group,
                role="a21-r2-district-deep-garden-arcade",
                material="carved_stone",
                x0=x - width * 0.40,
                x1=x + width * 0.40,
                z=facade_z,
                base_y=0.35,
                bays=(5, 4, 3)[lod],
                lod=1 if lod == 0 else 2,
                depth=(0.22, 0.17, 0.13)[lod],
            )
            if lod <= 1:
                for window_index in range((5, 3)[lod]):
                    _deep_window(
                        specs,
                        group=group,
                        role="a21-r2-district-recessed-occupied-opening",
                        x=x - width * 0.30
                        + window_index
                        * (width * 0.60 / max(1, (5, 3)[lod] - 1)),
                        y=lower_h + upper_h * 0.42,
                        z=facade_z - math.copysign(0.15, z),
                        width=1.45,
                        height=2.45,
                        warm=(index + window_index) % 4 == 0,
                    )
        else:
            facade_x = x - math.copysign(width * 0.5 + 0.12, x)
            bays = (4, 3, 2)[lod]
            bay_span = depth * 0.78
            for bay_index in range(bays):
                bay_z = z - bay_span * 0.5 + bay_span * (
                    bay_index + 0.5
                ) / bays
                _add_oriented_arch(
                    specs,
                    group=group,
                    role="a21-r2-district-deep-side-garden-arcade",
                    centre_x=facade_x,
                    centre_z=bay_z,
                    axis_x=0.0,
                    axis_z=1.0,
                    half_width=bay_span * 0.36 / bays,
                    base_y=0.35,
                    spring_y=3.5,
                    rise=2.1,
                    segments=(12, 8, 5)[lod],
                    radius=(0.18, 0.15, 0.12)[lod],
                    sides=(7, 6, 4)[lod],
                    material="carved_stone",
                )
            if lod <= 1:
                for window_index in range((5, 3)[lod]):
                    _deep_window(
                        specs,
                        group=group,
                        role="a21-r2-district-recessed-occupied-side-opening",
                        x=facade_x,
                        y=lower_h + upper_h * 0.42,
                        z=z - depth * 0.30
                        + window_index
                        * (depth * 0.60 / max(1, (5, 3)[lod] - 1)),
                        width=1.45,
                        height=2.45,
                        plane="side",
                        warm=(index + window_index) % 4 == 0,
                    )
        for level in (
            lower_h * 0.42,
            lower_h * 0.74,
            lower_h + upper_h * 0.58,
        ):
            if abs(z) >= abs(x):
                _chamfer_box(
                    specs,
                    "a21-r2-district-weathered-horizontal-course",
                    "wet_stone",
                    group,
                    x,
                    level,
                    z - math.copysign(depth * 0.5 + 0.18, z),
                    width * 0.82,
                    0.28,
                    0.54,
                    (0.045, 0.038, 0.032)[lod],
                    1,
                )
            else:
                _chamfer_box(
                    specs,
                    "a21-r2-district-weathered-side-course",
                    "wet_stone",
                    group,
                    x - math.copysign(width * 0.5 + 0.18, x),
                    level,
                    z,
                    0.54,
                    0.28,
                    depth * 0.82,
                    (0.045, 0.038, 0.032)[lod],
                    1,
                )
        if lod <= 1:
            _chamfer_box(
                specs,
                "a21-r2-district-occupied-roof-garden-planter",
                "carved_stone",
                group,
                x + upper_width * 0.24,
                lower_h + upper_h + 1.2,
                z,
                3.8,
                0.82,
                3.0,
                0.065,
                1,
            )
            _leaf_cluster(
                specs,
                "a21-r2-district-roof-garden-foliage",
                "foliage_light" if index % 2 else "foliage_dark",
                group,
                x + upper_width * 0.24,
                lower_h + upper_h + 2.2,
                z,
                1.8,
                1.45,
                (12, 7)[lod],
                15000 + index,
            )


def _corridor_point(t: float, side: float = 0.0) -> tuple[float, float]:
    near = (87.0, -89.0)
    far = (16.0, -22.0)
    dx = far[0] - near[0]
    dz = far[1] - near[1]
    length = math.hypot(dx, dz)
    forward = (dx / length, dz / length)
    right = (forward[1], -forward[0])
    return (
        near[0] + dx * t + right[0] * side,
        near[1] + dz * t + right[1] * side,
    )


def _add_r2_canal_bridge(
    specs: list[dict],
    lod: int,
    *,
    t: float,
    index: int,
) -> None:
    group = "a21-r2-nakaniwa-garden-canal-corridor"
    centre_x, centre_z = _corridor_point(t)
    ahead_x, ahead_z = _corridor_point(min(1.0, t + 0.01))
    forward_x = ahead_x - centre_x
    forward_z = ahead_z - centre_z
    forward_len = math.hypot(forward_x, forward_z)
    forward_x /= forward_len
    forward_z /= forward_len
    right_x, right_z = forward_z, -forward_x
    half_span = 7.0 - t * 1.0
    half_width = 2.7 + (0.35 if index == 1 else 0.0)
    corners = []
    for forward_offset, side_offset in (
        (-half_width, -half_span),
        (-half_width, half_span),
        (half_width, half_span),
        (half_width, -half_span),
    ):
        corners.append((
            centre_x + forward_x * forward_offset + right_x * side_offset,
            0.95,
            centre_z + forward_z * forward_offset + right_z * side_offset,
        ))
    _panel(
        specs,
        "a21-r2-garden-canal-bridge-thick-stone-deck",
        "carved_stone",
        group,
        tuple(corners),
        0.72,
    )
    for face_offset in (-half_width, half_width):
        arch_cx = centre_x + forward_x * face_offset
        arch_cz = centre_z + forward_z * face_offset
        arch_half_width = half_span * 0.41
        for arch_side in (-1.0, 1.0):
            arch_side_offset = arch_side * half_span * 0.47
            arch_side_x = arch_cx + right_x * arch_side_offset
            arch_side_z = arch_cz + right_z * arch_side_offset
            _add_oriented_arch(
                specs,
                group=group,
                role="a21-r2-garden-canal-bridge-twin-pointed-arch",
                centre_x=arch_side_x,
                centre_z=arch_side_z,
                axis_x=right_x,
                axis_z=right_z,
                half_width=arch_half_width,
                base_y=0.18,
                spring_y=0.76,
                rise=1.12 + 0.15 * (index == 1),
                segments=(14, 9, 5)[lod],
                radius=(0.20, 0.16, 0.13)[lod],
                sides=(8, 6, 4)[lod],
                material="carved_stone",
            )
            _sweep(
                specs,
                "a21-r2-garden-canal-bridge-twin-arch-contact-shadow",
                "dark_wood",
                group,
                (
                    (
                        arch_side_x - right_x * (arch_half_width - 0.20),
                        0.25,
                        arch_side_z - right_z * (arch_half_width - 0.20),
                    ),
                    (
                        arch_side_x + right_x * (arch_half_width - 0.20),
                        0.25,
                        arch_side_z + right_z * (arch_half_width - 0.20),
                    ),
                ),
                (0.060, 0.050, 0.040)[lod],
                (7, 5, 4)[lod],
            )
        for pier_offset in (-half_span + 0.35, 0.0, half_span - 0.35):
            _chamfer_box(
                specs,
                "a21-r2-garden-canal-bridge-grounded-arch-pier",
                "carved_stone",
                group,
                arch_cx + right_x * pier_offset,
                0.78,
                arch_cz + right_z * pier_offset,
                0.68,
                1.42,
                0.68,
                (0.055, 0.045, 0.035)[lod],
                1,
            )
        _sweep(
            specs,
            "a21-r2-garden-canal-bridge-stone-entablature",
            "carved_stone",
            group,
            (
                (
                    arch_cx - right_x * (half_span - 0.18),
                    1.72,
                    arch_cz - right_z * (half_span - 0.18),
                ),
                (
                    arch_cx + right_x * (half_span - 0.18),
                    1.72,
                    arch_cz + right_z * (half_span - 0.18),
                ),
            ),
            (0.17, 0.14, 0.11)[lod],
            (8, 6, 4)[lod],
        )
    for side_offset in (-half_span + 0.35, half_span - 0.35):
        rail_points = []
        for step in range(7 if lod == 0 else 4 if lod == 1 else 3):
            u = step / (6 if lod == 0 else 3 if lod == 1 else 2)
            forward_offset = -half_width + 2.0 * half_width * u
            rail_points.append((
                centre_x + forward_x * forward_offset + right_x * side_offset,
                1.55 + math.sin(math.pi * u) * 0.34,
                centre_z + forward_z * forward_offset + right_z * side_offset,
            ))
        _sweep(
            specs,
            "a21-r2-garden-canal-bridge-brass-parapet",
            "brass",
            group,
            tuple(rail_points),
            (0.045, 0.036, 0.028)[lod],
            (8, 6, 4)[lod],
        )


def _add_r2_garden_arcade(
    specs: list[dict],
    lod: int,
    *,
    t: float,
    side: float,
    seed: int,
) -> None:
    group = "a21-r2-nakaniwa-garden-canal-corridor"
    centre_x, centre_z = _corridor_point(t, side)
    next_x, next_z = _corridor_point(min(1.0, t + 0.02), side)
    axis_x = next_x - centre_x
    axis_z = next_z - centre_z
    axis_len = math.hypot(axis_x, axis_z)
    axis_x /= axis_len
    axis_z /= axis_len
    bays = (4, 3, 2)[lod]
    total_span = 18.0 if lod == 0 else 15.0 if lod == 1 else 12.0
    bay_span = total_span / bays
    for bay_index in range(bays):
        offset = -total_span * 0.5 + bay_span * (bay_index + 0.5)
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r2-canal-side-monumental-garden-arcade",
            centre_x=centre_x + axis_x * offset,
            centre_z=centre_z + axis_z * offset,
            axis_x=axis_x,
            axis_z=axis_z,
            half_width=bay_span * 0.39,
            base_y=0.18,
            spring_y=6.2,
            rise=3.4,
            segments=(16, 10, 6)[lod],
            radius=(0.22, 0.17, 0.13)[lod],
            sides=(8, 6, 4)[lod],
            material="carved_stone",
        )
    for pier_index in range(bays + 1):
        offset = -total_span * 0.5 + bay_span * pier_index
        _cylinder(
            specs,
            "a21-r2-canal-side-arcade-buttressed-pier",
            "ivory_stone",
            group,
            centre_x + axis_x * offset,
            5.05,
            centre_z + axis_z * offset,
            (0.62, 0.50, 0.40)[lod],
            10.1,
            (12, 8, 6)[lod],
            top_radius=(0.38, 0.32, 0.27)[lod],
        )
    _sweep(
        specs,
        "a21-r2-canal-side-arcade-entablature",
        "carved_stone",
        group,
        (
            (
                centre_x - axis_x * (total_span * 0.5 + 0.45),
                9.75,
                centre_z - axis_z * (total_span * 0.5 + 0.45),
            ),
            (
                centre_x + axis_x * (total_span * 0.5 + 0.45),
                9.75,
                centre_z + axis_z * (total_span * 0.5 + 0.45),
            ),
        ),
        (0.30, 0.24, 0.18)[lod],
        (8, 6, 4)[lod],
    )
    tree_x, tree_z = _corridor_point(t + 0.03, side + math.copysign(4.2, side))
    _tree(
        specs,
        group=group,
        role="a21-r2-canal-side-arcade-garden-canopy",
        x=tree_x,
        z=tree_z,
        height=17.0,
        crown=6.8,
        lod=lod,
        seed=seed,
        flowering=seed % 2 == 0,
    )


def _add_garden_city_composition_r2(specs: list[dict], lod: int) -> None:
    """Primary composition rebuilt as an intimate palace-garden canal route."""
    group = "a21-r2-nakaniwa-garden-canal-corridor"
    _box(
        specs,
        "a21-r2-garden-city-weathered-stone-ground",
        "carved_stone",
        group,
        0.0,
        -0.34,
        0.0,
        320.0,
        0.52,
        320.0,
    )
    for road in CANONICAL_ROADS:
        bounds = road["bounds"]
        _box(
            specs,
            "a21-r2-canonical-road-wet-stone-visual",
            "wet_stone",
            group,
            (bounds["minX"] + bounds["maxX"]) * 0.5,
            -0.02,
            (bounds["minZ"] + bounds["maxZ"]) * 0.5,
            bounds["maxX"] - bounds["minX"],
            0.10,
            bounds["maxZ"] - bounds["minZ"],
        )
    near_half_width = 5.8
    far_half_width = 4.2
    near_left = _corridor_point(0.0, near_half_width)
    near_right = _corridor_point(0.0, -near_half_width)
    far_left = _corridor_point(1.0, far_half_width)
    far_right = _corridor_point(1.0, -far_half_width)
    _panel(
        specs,
        "a21-r2-signature-diagonal-garden-canal-water",
        "water",
        group,
        (
            (near_left[0], 0.28, near_left[1]),
            (far_left[0], 0.28, far_left[1]),
            (far_right[0], 0.28, far_right[1]),
            (near_right[0], 0.28, near_right[1]),
        ),
        0.12,
    )
    for side_sign in (-1.0, 1.0):
        side_near = _corridor_point(0.0, side_sign * near_half_width)
        side_far = _corridor_point(1.0, side_sign * far_half_width)
        _panel(
            specs,
            "a21-r2-signature-canal-carved-retaining-coping",
            "carved_stone",
            group,
            (
                (side_near[0], 0.16, side_near[1]),
                (side_far[0], 0.16, side_far[1]),
                (side_far[0], 0.92, side_far[1]),
                (side_near[0], 0.92, side_near[1]),
            ),
            (0.38, 0.30, 0.24)[lod],
        )
        dry_near_outer = _corridor_point(0.0, side_sign * 15.0)
        dry_far_outer = _corridor_point(1.0, side_sign * 12.0)
        _panel(
            specs,
            "a21-r2-canal-side-occupied-stone-promenade",
            "carved_stone" if side_sign < 0 else "ivory_stone",
            group,
            (
                (side_near[0], 0.12, side_near[1]),
                (side_far[0], 0.12, side_far[1]),
                (dry_far_outer[0], 0.12, dry_far_outer[1]),
                (dry_near_outer[0], 0.12, dry_near_outer[1]),
            ),
            0.16,
        )
    # Long water highlights make the channel readable as water, not blue floor.
    for index in range((12, 7, 4)[lod]):
        t0 = 0.05 + index * (0.83 / max(1, (12, 7, 4)[lod] - 1))
        width = near_half_width + (far_half_width - near_half_width) * t0
        start = _corridor_point(t0, -width * 0.60)
        end = _corridor_point(t0 + 0.025, width * 0.52)
        _sweep(
            specs,
            "a21-r2-canal-broken-sky-reflection",
            "glass_highlight",
            group,
            ((start[0], 0.355, start[1]), (end[0], 0.355, end[1])),
            (0.026, 0.021, 0.016)[lod],
            (7, 5, 4)[lod],
        )
    for bridge_index, bridge_t in enumerate((0.18, 0.50, 0.82)):
        _add_r2_canal_bridge(
            specs,
            lod,
            t=bridge_t,
            index=bridge_index,
        )
    _add_r2_garden_arcade(
        specs,
        lod,
        t=0.22,
        side=14.5,
        seed=17001,
    )
    planter_sites = (
        (0.08, 10.2, 8.0),
        (0.14, -10.5, 7.0),
        (0.31, 11.2, 9.5),
        (0.40, -11.5, 8.5),
        (0.58, 10.0, 8.0),
        (0.68, -10.2, 7.5),
        (0.87, 9.0, 6.5),
        (0.91, -9.0, 6.5),
    )
    for index, (t, side, span) in enumerate(
        planter_sites[: (8, 6, 4)[lod]]
    ):
        x, z = _corridor_point(t, side)
        _chamfer_box(
            specs,
            "a21-r2-canal-terraced-botanical-planter",
            "carved_stone",
            group,
            x,
            0.78,
            z,
            span,
            1.30,
            4.6,
            (0.11, 0.085, 0.065)[lod],
            1,
        )
        _box(
            specs,
            "a21-r2-canal-planter-dark-soil",
            "wet_stone",
            group,
            x,
            1.43,
            z,
            span - 0.65,
            0.18,
            3.95,
        )
        if index not in {0, 1} or lod == 0:
            _tree(
                specs,
                group=group,
                role="a21-r2-canal-sculpted-garden-tree",
                x=x,
                z=z,
                height=6.8 + (index % 3) * 1.2,
                crown=2.5 + (index % 2) * 0.55,
                lod=lod,
                seed=18000 + index,
                flowering=index % 3 == 0,
            )
        _leaf_cluster(
            specs,
            "a21-r2-canal-planter-flower-border",
            "flower" if index % 2 == 0 else "foliage_light",
            group,
            x,
            1.92,
            z,
            span * 0.40,
            0.70,
            (22, 12, 6)[lod],
            19000 + index,
        )
    # Water-lily clusters and a gardener maintenance landing carry the story.
    for index, (t, side) in enumerate(
        ((0.28, -1.8), (0.43, 2.1), (0.64, -1.5), (0.76, 1.6))
    ):
        if index >= (4, 3, 2)[lod]:
            break
        x, z = _corridor_point(t, side)
        _leaf_cluster(
            specs,
            "a21-r2-canal-water-lily-cluster",
            "flower" if index == 1 else "foliage_light",
            group,
            x,
            0.40,
            z,
            1.8,
            0.12,
            (18, 10, 5)[lod],
            20000 + index,
        )
    landing_x, landing_z = _corridor_point(0.38, -9.3)
    _chamfer_box(
        specs,
        "a21-r2-gardener-irrigation-landing",
        "dark_wood",
        group,
        landing_x,
        0.62,
        landing_z,
        5.2,
        0.34,
        2.2,
        0.055,
        1,
    )
    _cylinder(
        specs,
        "a21-r2-gardener-irrigation-wheel",
        "brass",
        group,
        landing_x + 1.8,
        1.22,
        landing_z,
        0.72,
        0.28,
        (18, 12, 8)[lod],
        top_radius=0.72,
    )
    for lantern_t, lantern_side in (
        (0.10, 11.8),
        (0.12, -11.8),
        (0.48, 10.5),
        (0.52, -10.5),
        (0.84, 8.8),
        (0.86, -8.8),
    )[: (6, 4, 3)[lod]]:
        x, z = _corridor_point(lantern_t, lantern_side)
        _sweep(
            specs,
            "a21-r2-canal-route-human-scale-lantern-post",
            "brass",
            group,
            ((x, 0.12, z), (x, 2.8, z)),
            (0.050, 0.041, 0.032)[lod],
            (8, 6, 4)[lod],
        )
        _chamfer_box(
            specs,
            "a21-r2-canal-route-warm-lantern-glow",
            "warm_glow",
            group,
            x,
            3.0,
            z,
            0.46,
            0.54,
            0.46,
            0.050,
            1,
        )
    # Close stone/flower masses at both lower corners match the intimate
    # courtyard framing of the reference without narrowing the dry route.
    for frame_index, frame_side in enumerate((-5.2, 5.2)):
        centre_x, centre_z = _corridor_point(-0.115, frame_side)
        ahead_x, ahead_z = _corridor_point(-0.045, frame_side)
        axis_x = ahead_x - centre_x
        axis_z = ahead_z - centre_z
        axis_len = math.hypot(axis_x, axis_z)
        axis_x /= axis_len
        axis_z /= axis_len
        right_x, right_z = axis_z, -axis_x
        half_length = 4.8
        half_depth = 1.65
        corners = tuple(
            (
                centre_x + axis_x * along + right_x * across,
                0.55,
                centre_z + axis_z * along + right_z * across,
            )
            for along, across in (
                (-half_length, -half_depth),
                (half_length, -half_depth),
                (half_length, half_depth),
                (-half_length, half_depth),
            )
        )
        _panel(
            specs,
            "a21-r2-extreme-foreground-carved-garden-parapet",
            "ivory_stone",
            group,
            corners,
            0.75,
        )
        soil_corners = tuple(
            (
                centre_x + axis_x * along + right_x * across,
                0.945,
                centre_z + axis_z * along + right_z * across,
            )
            for along, across in (
                (-4.25, -1.18),
                (4.25, -1.18),
                (4.25, 1.18),
                (-4.25, 1.18),
            )
        )
        _panel(
            specs,
            "a21-r2-extreme-foreground-dark-garden-soil",
            "wet_stone",
            group,
            soil_corners,
            0.09,
        )
        flower_cluster_count = (3, 2, 1)[lod]
        for cluster_index in range(flower_cluster_count):
            along = (
                -2.7
                + cluster_index
                * (5.4 / max(1, flower_cluster_count - 1))
            )
            flower_x = centre_x + axis_x * along
            flower_z = centre_z + axis_z * along
            _leaf_cluster(
                specs,
                "a21-r2-extreme-foreground-fine-flower-and-fern-bed",
                (
                    "flower"
                    if (frame_index + cluster_index) % 3 == 0
                    else "foliage_light"
                ),
                group,
                flower_x,
                1.17,
                flower_z,
                1.20,
                0.62,
                (34, 18, 8)[lod],
                21200 + frame_index * 10 + cluster_index,
            )
    # Real paving joints create a human-scale surface cadence in the formerly
    # empty lower third of the frozen camera.
    cross_joint_count = (14, 8, 4)[lod]
    for joint_index in range(cross_joint_count):
        joint_t = -0.11 + joint_index * (
            0.49 / max(1, cross_joint_count - 1)
        )
        left_x, left_z = _corridor_point(joint_t, -15.0)
        right_x, right_z = _corridor_point(joint_t, 15.0)
        _sweep(
            specs,
            "a21-r2-extreme-foreground-carved-paving-cross-joint",
            "wet_stone",
            group,
            ((left_x, 0.155, left_z), (right_x, 0.155, right_z)),
            (0.0018, 0.0015, 0.0012)[lod],
            (6, 5, 4)[lod],
        )
    for joint_side in (-12.0, -6.0, 0.0, 6.0, 12.0):
        start_x, start_z = _corridor_point(-0.13, joint_side)
        end_x, end_z = _corridor_point(0.46, joint_side * 0.72)
        _sweep(
            specs,
            "a21-r2-extreme-foreground-carved-paving-long-joint",
            "wet_stone",
            group,
            ((start_x, 0.155, start_z), (end_x, 0.155, end_z)),
            (0.0016, 0.0014, 0.0011)[lod],
            (6, 5, 4)[lod],
        )
    _add_nakaniwa_pavilion_district(specs, lod)


def _add_palace_castle_crown_r2(specs: list[dict], lod: int) -> None:
    """Bind the floral crown to a dense vertical castle-tower cluster."""
    group = PALACE_ID
    tower_specs = (
        (-74.0, -56.0, 8.5, 9.5, 18.0),
        (-57.0, -53.0, 9.0, 10.0, 20.0),
        (-24.0, -54.0, 8.0, 9.0, 17.0),
    )
    tower_limit = (3, 3, 2)[lod]
    for tower_index, (x, z, width, depth, height) in enumerate(
        tower_specs[:tower_limit]
    ):
        base_y = 10.8
        _chamfer_box(
            specs,
            "a21-r2-palace-integrated-crown-castle-tower",
            "ivory_stone" if tower_index % 2 == 0 else "carved_stone",
            group,
            x,
            base_y + height * 0.5,
            z,
            width,
            height,
            depth,
            (0.14, 0.11, 0.08)[lod],
            2 if lod == 0 else 1,
        )
        for course_index, course_y in enumerate(
            (
                base_y + height * 0.30,
                base_y + height * 0.60,
                base_y + height * 0.83,
            )
        ):
            if lod == 2 and course_index != 1:
                continue
            _chamfer_box(
                specs,
                "a21-r2-palace-castle-tower-weathered-course",
                "wet_stone" if course_index != 1 else "carved_stone",
                group,
                x,
                course_y,
                z - depth * 0.5 - 0.16,
                width + 0.55,
                0.34,
                0.48,
                (0.050, 0.042, 0.034)[lod],
                1,
            )
        _roof(
            specs,
            group=group,
            role="a21-r2-palace-integrated-crown-tower-petal-roof",
            cx=x,
            base_y=base_y + height,
            cz=z,
            width=width + 1.8,
            depth=depth + 1.8,
            rise=3.8 + tower_index * 0.35,
            material="verdigris_bronze",
        )
        _cylinder(
            specs,
            "a21-r2-palace-integrated-crown-tower-finial",
            "brass",
            group,
            x,
            min(40.5, base_y + height + 5.4),
            z,
            (0.24, 0.19, 0.15)[lod],
            min(3.2, 42.4 - (base_y + height + 3.9)),
            (12, 8, 6)[lod],
            top_radius=0.04,
        )
        if lod <= 1:
            window_rows = 3 if lod == 0 else 2
            for row in range(window_rows):
                _deep_window(
                    specs,
                    group=group,
                    role="a21-r2-palace-castle-tower-deep-occupied-window",
                    x=x,
                    y=base_y + 3.3 + row * (
                        (height - 6.0) / max(1, window_rows - 1)
                    ),
                    z=z - depth * 0.5 - 0.18,
                    width=1.55,
                    height=2.65,
                    warm=(tower_index + row) % 3 == 0,
                )
            _deep_window(
                specs,
                group=group,
                role="a21-r2-palace-castle-tower-deep-side-window",
                x=x + width * 0.5 + 0.18,
                y=base_y + height * 0.55,
                z=z,
                width=1.55,
                height=2.65,
                plane="side",
                warm=tower_index == 2,
            )
        for buttress_side in (-1.0, 1.0):
            _chamfer_box(
                specs,
                "a21-r2-palace-castle-tower-grounded-buttress",
                "carved_stone",
                group,
                x + buttress_side * (width * 0.5 - 0.45),
                base_y + height * 0.40,
                z - depth * 0.5 - 0.34,
                0.82,
                height * 0.80,
                0.88,
                (0.065, 0.052, 0.042)[lod],
                1,
            )
    # The fixed view looks almost exactly along the keep diagonal.  Build the
    # crown in the true screen-facing tangent plane so its mass cannot collapse
    # into a row of tiny roof teeth.  A broad occupied drum grows out of the
    # keep, then five thick overlapping stone petals begin below the cornice
    # and rise to the full castle height.
    camera_normal = (0.735, -0.678)
    camera_tangent = (0.678, 0.735)
    crown_front = (
        -40.0 + camera_normal[0] * 12.0,
        -49.0 + camera_normal[1] * 12.0,
    )
    _cylinder(
        specs,
        "a21-r2-palace-flower-crown-occupied-root-drum",
        "carved_stone",
        group,
        crown_front[0],
        25.0,
        crown_front[1],
        (12.2, 10.4, 8.0)[lod],
        16.0,
        (24, 16, 10)[lod],
        top_radius=(10.5, 9.0, 7.0)[lod],
    )
    _cylinder(
        specs,
        "a21-r2-palace-flower-crown-root-drum-cornice",
        "brass",
        group,
        crown_front[0],
        32.6,
        crown_front[1],
        (11.0, 9.4, 7.3)[lod],
        0.72,
        (24, 16, 10)[lod],
        top_radius=(10.7, 9.1, 7.0)[lod],
    )
    petal_offsets = (
        (-8.6, -4.3, 0.0, 4.3, 8.6)
        if lod <= 1
        else (-6.5, 0.0, 6.5)
    )
    for petal_index, offset in enumerate(petal_offsets):
        centre_depth = (
            (11.9, 10.1, 7.7)[lod] - abs(offset) * 0.035
        )
        plane_x = crown_front[0] + camera_normal[0] * centre_depth
        plane_z = crown_front[1] + camera_normal[1] * centre_depth
        root_offset = offset * 0.34
        shoulder_offset = offset * 0.88
        tip_offset = offset * 1.03
        root_half = (4.7, 4.0, 3.2)[lod]
        shoulder_half = (4.0, 3.4, 2.7)[lod]
        root_y = 21.0 + abs(offset) * 0.10
        shoulder_y = 34.2 - abs(offset) * 0.025
        tip_y = 42.25 - abs(offset) * 0.24

        def crown_point(tangent_offset: float, y: float) -> tuple[float, float, float]:
            return (
                plane_x + camera_tangent[0] * tangent_offset,
                y,
                plane_z + camera_tangent[1] * tangent_offset,
            )

        root_left = crown_point(root_offset - root_half, root_y)
        root_right = crown_point(root_offset + root_half, root_y)
        shoulder_left = crown_point(
            shoulder_offset - shoulder_half, shoulder_y
        )
        shoulder_right = crown_point(
            shoulder_offset + shoulder_half, shoulder_y
        )
        tip = crown_point(tip_offset, tip_y)
        petal_material = (
            "ivory_stone"
            if petal_index % 2 == 0
            else "carved_stone"
        )
        _panel(
            specs,
            "a21-r2-palace-solid-integrated-flower-crown-petal",
            petal_material,
            group,
            (
                root_left,
                root_right,
                shoulder_right,
                tip,
                shoulder_left,
            ),
            (1.45, 1.15, 0.90)[lod],
        )
        _sweep(
            specs,
            "a21-r2-palace-flower-crown-brass-spine",
            "brass",
            group,
            (
                crown_point(root_offset, root_y + 0.12),
                crown_point(shoulder_offset, shoulder_y + 0.10),
                tip,
            ),
            (0.16, 0.13, 0.10)[lod],
            (10, 8, 6)[lod],
        )
        if lod == 0:
            for edge_start, edge_shoulder in (
                (root_left, shoulder_left),
                (root_right, shoulder_right),
            ):
                _sweep(
                    specs,
                    "a21-r2-palace-flower-crown-structural-edge",
                    "brass",
                    group,
                    (edge_start, edge_shoulder, tip),
                    0.085,
                    8,
                )
        _cylinder(
            specs,
            "a21-r2-palace-solid-crown-brass-needle",
            "brass",
            group,
            tip[0],
            tip[1] + 0.16,
            tip[2],
            (0.16, 0.13, 0.10)[lod],
            0.32,
            (8, 6, 4)[lod],
            top_radius=0.035,
        )
    # A tall open gallery stitches the four roots into one readable castle.
    _monumental_arcade(
        specs,
        group=group,
        role="a21-r2-palace-crown-root-grand-gallery",
        material="carved_stone",
        x0=-80.0,
        x1=-18.0,
        z=-38.4,
        base_y=11.2,
        bays=(10, 7, 5)[lod],
        lod=lod,
        spring_height=5.6,
        rise=3.0,
        depth=(0.34, 0.28, 0.22)[lod],
    )
    if lod <= 1:
        opening_count = 10 if lod == 0 else 7
        for opening_index in range(opening_count):
            _box(
                specs,
                "a21-r2-palace-crown-root-warm-occupied-gallery",
                "warm_glow" if opening_index % 4 == 1 else "dirty_glass",
                group,
                -76.9 + opening_index * (
                    55.8 / max(1, opening_count - 1)
                ),
                15.2,
                -38.18,
                4.0,
                4.8,
                0.10,
            )
    # Thick stepped shoulder bands visually carry the flower crown.
    for shoulder_index, (width, depth, y, height) in enumerate(
        (
            (45.0, 24.0, 29.6, 1.5),
            (36.0, 20.0, 31.0, 1.3),
            (27.0, 17.0, 32.2, 1.1),
        )
    ):
        _chamfer_box(
            specs,
            f"a21-r2-palace-integrated-crown-shoulder-{shoulder_index}",
            "carved_stone" if shoulder_index != 1 else "wet_stone",
            group,
            -40.0,
            y,
            -49.0,
            width,
            height,
            depth,
            (0.13, 0.10, 0.075)[lod],
            1,
        )


def _add_palace_enclosing_crown_bastion_r3(
    specs: list[dict],
    lod: int,
) -> None:
    """Place the palace's occupied flower crown on its camera-facing envelope."""
    group = PALACE_ID
    centre_x = -33.0
    centre_z = -69.0
    camera_normal = (0.735, -0.678)
    camera_tangent = (0.678, 0.735)
    _chamfer_box(
        specs,
        "a21-r3-palace-enclosing-water-terrace",
        "wet_stone",
        group,
        -47.0,
        3.0,
        -72.0,
        58.0,
        5.8,
        43.0,
        (0.18, 0.14, 0.10)[lod],
        2 if lod == 0 else 1,
    )
    _cylinder(
        specs,
        "a21-r3-palace-enclosing-octagonal-bastion",
        "carved_stone",
        group,
        centre_x,
        16.3,
        centre_z,
        (15.0, 14.0, 12.5)[lod],
        27.0,
        (24, 16, 8)[lod],
        top_radius=(12.8, 11.8, 10.5)[lod],
    )
    for course_index, course_y in enumerate(
        (5.0, 11.2, 18.0, 25.6)
    ):
        if lod == 2 and course_index not in {1, 3}:
            continue
        _cylinder(
            specs,
            "a21-r3-palace-bastion-deep-stone-course",
            "ivory_stone" if course_index % 2 else "wet_stone",
            group,
            centre_x,
            course_y,
            centre_z,
            (15.25, 14.25, 12.75)[lod],
            (0.58, 0.48, 0.38)[lod],
            (24, 16, 8)[lod],
            top_radius=(14.8, 13.8, 12.3)[lod],
        )
    _cylinder(
        specs,
        "a21-r3-palace-occupied-crown-gallery",
        "ivory_stone",
        group,
        centre_x,
        30.6,
        centre_z,
        (12.8, 11.8, 10.4)[lod],
        7.6,
        (24, 16, 8)[lod],
        top_radius=(10.8, 9.9, 8.7)[lod],
    )
    _cylinder(
        specs,
        "a21-r3-palace-crown-gallery-brass-cornice",
        "brass",
        group,
        centre_x,
        34.15,
        centre_z,
        (11.35, 10.4, 9.1)[lod],
        0.72,
        (24, 16, 8)[lod],
        top_radius=(10.9, 10.0, 8.7)[lod],
    )
    # Two inhabited shoulder towers make the crown read as a castle system,
    # not a decorative blade attached to one rectangular keep.
    shoulder_towers = (
        (-50.0, -78.0, 7.4, 29.0),
        (-22.0, -60.0, 6.5, 26.0),
    )
    for tower_index, (x, z, radius, height) in enumerate(shoulder_towers):
        _cylinder(
            specs,
            "a21-r3-palace-enclosing-occupied-shoulder-tower",
            "ivory_stone" if tower_index == 0 else "carved_stone",
            group,
            x,
            height * 0.5 + 1.0,
            z,
            radius,
            height,
            (16, 12, 8)[lod],
            top_radius=radius * 0.82,
        )
        _cylinder(
            specs,
            "a21-r3-palace-shoulder-tower-weathered-ring",
            "wet_stone",
            group,
            x,
            height * 0.64,
            z,
            radius * 1.03,
            0.48,
            (16, 12, 8)[lod],
            top_radius=radius,
        )
        _cylinder(
            specs,
            "a21-r3-palace-shoulder-tower-petal-roof",
            "verdigris_bronze",
            group,
            x,
            height + 3.5,
            z,
            radius * 0.92,
            7.0,
            8,
            top_radius=0.12,
        )
    # Deep, occupied arches are placed directly on the diagonal bastion face.
    front_x = centre_x + camera_normal[0] * 14.2
    front_z = centre_z + camera_normal[1] * 14.2
    bay_count = (3, 2, 1)[lod]
    for bay_index in range(bay_count):
        tangent_offset = (
            (bay_index - (bay_count - 1) * 0.5) * 7.2
        )
        bay_x = front_x + camera_tangent[0] * tangent_offset
        bay_z = front_z + camera_tangent[1] * tangent_offset
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r3-palace-bastion-monumental-occupied-arch",
            centre_x=bay_x,
            centre_z=bay_z,
            axis_x=camera_tangent[0],
            axis_z=camera_tangent[1],
            half_width=2.65,
            base_y=1.1,
            spring_y=7.2,
            rise=3.8,
            segments=(18, 10, 6)[lod],
            radius=(0.34, 0.27, 0.21)[lod],
            sides=(8, 6, 4)[lod],
            material="carved_stone",
        )
        _panel(
            specs,
            "a21-r3-palace-bastion-warm-occupied-threshold",
            "warm_glow" if bay_index == 1 else "dirty_glass",
            group,
            (
                (
                    bay_x - camera_tangent[0] * 2.10,
                    1.4,
                    bay_z - camera_tangent[1] * 2.10,
                ),
                (
                    bay_x + camera_tangent[0] * 2.10,
                    1.4,
                    bay_z + camera_tangent[1] * 2.10,
                ),
                (
                    bay_x + camera_tangent[0] * 2.10,
                    7.0,
                    bay_z + camera_tangent[1] * 2.10,
                ),
                (
                    bay_x - camera_tangent[0] * 2.10,
                    7.0,
                    bay_z - camera_tangent[1] * 2.10,
                ),
            ),
            0.12,
        )
    # Five thick screen-facing petals grow out of the occupied gallery.
    petal_offsets = (
        (-8.0, -4.0, 0.0, 4.0, 8.0)
        if lod <= 1
        else (-6.0, 0.0, 6.0)
    )
    petal_plane_x = centre_x + camera_normal[0] * 12.0
    petal_plane_z = centre_z + camera_normal[1] * 12.0
    for petal_index, offset in enumerate(petal_offsets):
        root_offset = offset * 0.30
        shoulder_offset = offset * 0.90
        tip_offset = offset * 1.08
        root_half = (4.4, 3.7, 3.0)[lod]
        shoulder_half = (3.6, 3.0, 2.4)[lod]
        root_y = 24.0
        shoulder_y = 35.0 - abs(offset) * 0.05
        tip_y = 42.22 - abs(offset) * 0.20

        def point(tangent_offset: float, y: float) -> tuple[float, float, float]:
            return (
                petal_plane_x + camera_tangent[0] * tangent_offset,
                y,
                petal_plane_z + camera_tangent[1] * tangent_offset,
            )

        root_left = point(root_offset - root_half, root_y)
        root_right = point(root_offset + root_half, root_y)
        shoulder_left = point(
            shoulder_offset - shoulder_half,
            shoulder_y,
        )
        shoulder_right = point(
            shoulder_offset + shoulder_half,
            shoulder_y,
        )
        tip = point(tip_offset, tip_y)
        _panel(
            specs,
            "a21-r3-palace-enclosing-integrated-crown-petal",
            "ivory_stone" if petal_index % 2 == 0 else "carved_stone",
            group,
            (root_left, root_right, shoulder_right, tip, shoulder_left),
            (1.55, 1.20, 0.92)[lod],
        )
        _sweep(
            specs,
            "a21-r3-palace-enclosing-crown-brass-spine",
            "brass",
            group,
            (
                point(root_offset, root_y + 0.12),
                point(shoulder_offset, shoulder_y + 0.10),
                tip,
            ),
            (0.17, 0.135, 0.105)[lod],
            (10, 8, 6)[lod],
        )
        if lod == 0:
            for edge_start, edge_shoulder in (
                (root_left, shoulder_left),
                (root_right, shoulder_right),
            ):
                _sweep(
                    specs,
                    "a21-r3-palace-enclosing-crown-carved-edge",
                    "brass",
                    group,
                    (edge_start, edge_shoulder, tip),
                    0.082,
                    8,
                )


R3_MID_CITY_SITES = (
    (0.72, 30.0, 18.0, 5.4),
    (0.74, -30.0, 21.0, 5.8),
    (0.82, 28.0, 20.0, 5.5),
    (0.84, -26.0, 22.0, 5.8),
)


def _add_dense_mid_canal_city_r3(specs: list[dict], lod: int) -> None:
    """Add a traversal-safe middle city of non-boxy occupied pavilions."""
    group = "a21-r3-nakaniwa-mid-canal-palace-city"
    site_limit = (4, 4, 3)[lod]
    for index, (t, side, height, radius) in enumerate(
        R3_MID_CITY_SITES[:site_limit]
    ):
        x, z = _corridor_point(t, side)
        lower_h = height * 0.56
        upper_h = height * 0.26
        _chamfer_box(
            specs,
            "a21-r3-mid-city-deep-garden-terrace",
            "wet_stone",
            group,
            x,
            1.0,
            z,
            radius * 2.35,
            1.8,
            radius * 1.85,
            (0.15, 0.11, 0.08)[lod],
            1,
        )
        _cylinder(
            specs,
            "a21-r3-mid-city-octagonal-occupied-arcade-pavilion",
            (
                "ivory_stone",
                "carved_stone",
                "moss_stone",
            )[index % 3],
            group,
            x,
            lower_h * 0.5 + 1.2,
            z,
            radius,
            lower_h,
            (16, 12, 8)[lod],
            top_radius=radius * 0.82,
        )
        for course_y in (
            lower_h * 0.38 + 1.0,
            lower_h * 0.72 + 1.0,
        ):
            _cylinder(
                specs,
                "a21-r3-mid-city-weathered-octagonal-course",
                "wet_stone",
                group,
                x,
                course_y,
                z,
                radius * 1.02,
                (0.42, 0.34, 0.28)[lod],
                (16, 12, 8)[lod],
                top_radius=radius * 0.98,
            )
        _cylinder(
            specs,
            "a21-r3-mid-city-stepped-occupied-lantern",
            "carved_stone",
            group,
            x,
            lower_h + upper_h * 0.5 + 1.0,
            z,
            radius * 0.64,
            upper_h,
            (12, 8, 8)[lod],
            top_radius=radius * 0.48,
        )
        _cylinder(
            specs,
            "a21-r3-mid-city-petal-pavilion-roof",
            "verdigris_bronze" if index % 2 else "brass",
            group,
            x,
            height - 0.2,
            z,
            radius * 0.72,
            height * 0.24,
            8,
            top_radius=0.10,
        )
        if lod <= 1:
            _leaf_cluster(
                specs,
                "a21-r3-mid-city-inhabited-roof-garden",
                "foliage_dark" if index % 2 else "foliage_light",
                group,
                x + radius * 0.30,
                lower_h + 1.8,
                z,
                radius * 0.44,
                1.8,
                (14, 7)[lod],
                24000 + index,
            )
        if lod == 0:
            next_x, next_z = _corridor_point(min(1.0, t + 0.02), side)
            forward_x = next_x - x
            forward_z = next_z - z
            forward_len = math.hypot(forward_x, forward_z)
            forward_x /= forward_len
            forward_z /= forward_len
            right_x, right_z = forward_z, -forward_x
            face_x = x - math.copysign(right_x * radius * 0.92, side)
            face_z = z - math.copysign(right_z * radius * 0.92, side)
            for bay_side in (-1.0, 1.0):
                _add_oriented_arch(
                    specs,
                    group=group,
                    role="a21-r3-mid-city-deep-occupied-route-arch",
                    centre_x=face_x + forward_x * bay_side * 2.4,
                    centre_z=face_z + forward_z * bay_side * 2.4,
                    axis_x=forward_x,
                    axis_z=forward_z,
                    half_width=2.0,
                    base_y=1.0,
                    spring_y=5.1,
                    rise=2.8,
                    segments=12,
                    radius=0.24,
                    sides=7,
                    material="carved_stone",
                )


def _add_ceremonial_canal_gate_r3(specs: list[dict], lod: int) -> None:
    """Close the far canal with a traversable occupied ceremonial arcade."""
    group = "a21-r3-nakaniwa-mid-canal-palace-city"
    t = 0.92
    centre_x, centre_z = _corridor_point(t)
    ahead_x, ahead_z = _corridor_point(0.94)
    forward_x = ahead_x - centre_x
    forward_z = ahead_z - centre_z
    forward_len = math.hypot(forward_x, forward_z)
    forward_x /= forward_len
    forward_z /= forward_len
    right_x, right_z = forward_z, -forward_x
    arch_offsets = (-9.0, 0.0, 9.0) if lod <= 1 else (0.0,)
    for offset in arch_offsets:
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r3-canal-destination-monumental-open-arch",
            centre_x=centre_x + right_x * offset,
            centre_z=centre_z + right_z * offset,
            axis_x=right_x,
            axis_z=right_z,
            half_width=4.0 if offset == 0.0 else 3.65,
            base_y=0.25,
            spring_y=6.0,
            rise=4.0 if offset == 0.0 else 3.3,
            segments=(14, 8, 5)[lod],
            radius=(0.32, 0.25, 0.20)[lod],
            sides=(8, 6, 4)[lod],
            material="carved_stone",
        )
    pier_offsets = (-13.2, -4.5, 4.5, 13.2)
    for pier_index, offset in enumerate(
        pier_offsets if lod <= 1 else (-4.5, 4.5)
    ):
        _chamfer_box(
            specs,
            "a21-r3-canal-destination-grounded-carved-pier",
            "ivory_stone" if pier_index % 2 else "carved_stone",
            group,
            centre_x + right_x * offset,
            5.2,
            centre_z + right_z * offset,
            1.25,
            10.2,
            1.25,
            (0.11, 0.085, 0.065)[lod],
            1,
        )
    _sweep(
        specs,
        "a21-r3-canal-destination-arcade-entablature",
        "carved_stone",
        group,
        (
            (
                centre_x - right_x * 14.8,
                10.45,
                centre_z - right_z * 14.8,
            ),
            (
                centre_x + right_x * 14.8,
                10.45,
                centre_z + right_z * 14.8,
            ),
        ),
        (0.42, 0.34, 0.27)[lod],
        (8, 6, 4)[lod],
    )
    for tower_side in (-1.0, 1.0):
        tower_x = centre_x + right_x * tower_side * 15.5
        tower_z = centre_z + right_z * tower_side * 15.5
        _cylinder(
            specs,
            "a21-r3-canal-destination-occupied-octagonal-gatehouse",
            "carved_stone",
            group,
            tower_x,
            7.4,
            tower_z,
            (4.6, 4.2, 3.8)[lod],
            14.4,
            (12, 8, 8)[lod],
            top_radius=(3.9, 3.6, 3.2)[lod],
        )
        _cylinder(
            specs,
            "a21-r3-canal-destination-gatehouse-petal-roof",
            "verdigris_bronze",
            group,
            tower_x,
            17.0,
            tower_z,
            (4.4, 4.0, 3.6)[lod],
            5.0,
            8,
            top_radius=0.08,
        )


LEGACY_DUPLICATE_CROWN_PREFIXES = (
    "a21-palace-camera-diagonal-crown-",
    "a21-palace-integrated-crown-",
    "a21-palace-crown-brass-ring",
    "a21-palace-crown-brass-spine",
    "a21-palace-crown-drum",
    "a21-palace-crown-heavy-petal",
    "a21-palace-crown-inner-flower-petal",
    "a21-palace-crown-inner-lantern",
    "a21-palace-crown-lantern-gallery-",
    "a21-palace-crown-luminous-inset",
    "a21-palace-crown-master-finial",
    "a21-palace-crown-structural-edge-frame",
)


def _remove_legacy_duplicate_palace_crowns(specs: list[dict]) -> None:
    """Remove the three overlapping proxy crowns before authoring the R4 crown."""
    specs[:] = [
        spec
        for spec in specs
        if not any(
            str(spec["role"]).startswith(prefix)
            for prefix in LEGACY_DUPLICATE_CROWN_PREFIXES
        )
    ]


def _add_r4_oriented_palace_gallery(
    specs: list[dict],
    lod: int,
    *,
    centre_x: float,
    centre_z: float,
    length: float,
    base_y: float,
    spring_height: float,
    rise: float,
    bays: int,
    role: str,
) -> None:
    """Build a supported occupied gallery on the palace camera-facing plane."""
    group = PALACE_ID
    normal_x, normal_z = 0.985, -0.172
    tangent_x, tangent_z = 0.172, 0.985
    bay_span = length / bays
    platform_depth = 7.2
    platform_centre_x = centre_x - normal_x * platform_depth * 0.38
    platform_centre_z = centre_z - normal_z * platform_depth * 0.38

    def point(
        tangent_offset: float,
        y: float,
        normal_offset: float = 0.0,
    ) -> tuple[float, float, float]:
        return (
            centre_x
            + tangent_x * tangent_offset
            + normal_x * normal_offset,
            y,
            centre_z
            + tangent_z * tangent_offset
            + normal_z * normal_offset,
        )

    _panel(
        specs,
        f"{role}-deep-terrace-slab",
        "ivory_stone",
        group,
        (
            (
                platform_centre_x - tangent_x * length * 0.54
                - normal_x * platform_depth * 0.5,
                base_y - 0.08,
                platform_centre_z - tangent_z * length * 0.54
                - normal_z * platform_depth * 0.5,
            ),
            (
                platform_centre_x + tangent_x * length * 0.54
                - normal_x * platform_depth * 0.5,
                base_y - 0.08,
                platform_centre_z + tangent_z * length * 0.54
                - normal_z * platform_depth * 0.5,
            ),
            (
                platform_centre_x + tangent_x * length * 0.54
                + normal_x * platform_depth * 0.5,
                base_y - 0.08,
                platform_centre_z + tangent_z * length * 0.54
                + normal_z * platform_depth * 0.5,
            ),
            (
                platform_centre_x - tangent_x * length * 0.54
                + normal_x * platform_depth * 0.5,
                base_y - 0.08,
                platform_centre_z - tangent_z * length * 0.54
                + normal_z * platform_depth * 0.5,
            ),
        ),
        (0.78, 0.62, 0.48)[lod],
    )
    arch_segments = (20, 11, 6)[lod]
    arch_sides = (9, 6, 4)[lod]
    for bay_index in range(bays):
        tangent_offset = -length * 0.5 + bay_span * (bay_index + 0.5)
        bay_x, _, bay_z = point(tangent_offset, base_y)
        _add_oriented_arch(
            specs,
            group=group,
            role=f"{role}-deep-occupied-arcade",
            centre_x=bay_x,
            centre_z=bay_z,
            axis_x=tangent_x,
            axis_z=tangent_z,
            half_width=bay_span * 0.37,
            base_y=base_y - 0.14,
            spring_y=base_y + spring_height,
            rise=rise,
            segments=arch_segments,
            radius=(0.31, 0.25, 0.20)[lod],
            sides=arch_sides,
            material="ivory_stone",
        )
        opening_half = bay_span * 0.30
        backing = (
            point(
                tangent_offset - opening_half,
                base_y + 0.35,
                -0.34,
            ),
            point(
                tangent_offset + opening_half,
                base_y + 0.35,
                -0.34,
            ),
            point(
                tangent_offset + opening_half,
                base_y + spring_height + rise * 0.56,
                -0.34,
            ),
            point(
                tangent_offset - opening_half,
                base_y + spring_height + rise * 0.56,
                -0.34,
            ),
        )
        _panel(
            specs,
            f"{role}-recessed-occupied-loggia",
            "warm_glow" if bay_index % 4 == 1 else "dirty_glass",
            group,
            backing,
            0.10,
        )
    opening_height = spring_height + rise
    for pier_index in range(bays + 1):
        tangent_offset = -length * 0.5 + bay_span * pier_index
        pier_x, _, pier_z = point(tangent_offset, base_y)
        _cylinder(
            specs,
            f"{role}-grounded-carved-column",
            "carved_stone",
            group,
            pier_x,
            base_y + opening_height * 0.5,
            pier_z,
            (0.48, 0.40, 0.34)[lod],
            opening_height + 0.52,
            (12, 8, 6)[lod],
            top_radius=(0.39, 0.33, 0.28)[lod],
        )
    _sweep(
        specs,
        f"{role}-carved-entablature",
        "carved_stone",
        group,
        (
            point(-length * 0.53, base_y + opening_height + 0.32),
            point(length * 0.53, base_y + opening_height + 0.32),
        ),
        (0.35, 0.28, 0.22)[lod],
        (9, 7, 5)[lod],
    )
    rail_y = base_y + 1.16
    rail_normal = 0.78
    _sweep(
        specs,
        f"{role}-continuous-brass-handrail",
        "brass",
        group,
        (
            point(-length * 0.50, rail_y, rail_normal),
            point(length * 0.50, rail_y, rail_normal),
        ),
        (0.040, 0.033, 0.027)[lod],
        (8, 6, 4)[lod],
    )
    post_count = (bays * 2 + 1, bays + 1, max(3, bays // 2))[lod]
    for post_index in range(post_count):
        tangent_offset = -length * 0.50 + length * post_index / max(
            1,
            post_count - 1,
        )
        _sweep(
            specs,
            f"{role}-brass-baluster",
            "brass",
            group,
            (
                point(tangent_offset, base_y + 0.10, rail_normal),
                point(tangent_offset, rail_y, rail_normal),
            ),
            (0.030, 0.025, 0.021)[lod],
            (7, 6, 4)[lod],
        )


def _add_palace_terraces_and_rooted_crown_r4(
    specs: list[dict],
    lod: int,
) -> None:
    """Author one ivory terrace cascade and one rooted castle-scale crown."""
    group = PALACE_ID
    _add_r4_oriented_palace_gallery(
        specs,
        lod,
        centre_x=-21.9,
        centre_z=-67.8,
        length=55.0,
        base_y=10.9,
        spring_height=4.25,
        rise=2.55,
        bays=(8, 6, 4)[lod],
        role="a21-r4-palace-lower-water-loggia",
    )
    _add_r4_oriented_palace_gallery(
        specs,
        lod,
        centre_x=-29.0,
        centre_z=-64.8,
        length=41.0,
        base_y=18.0,
        spring_height=3.60,
        rise=2.35,
        bays=(6, 5, 3)[lod],
        role="a21-r4-palace-upper-garden-loggia",
    )
    # Two stepped ceremonial stairs visibly bind the water level to both
    # occupied gallery tiers.  Each tread overlaps the previous riser.
    stair_count = (9, 7, 5)[lod]
    normal_x, normal_z = 0.985, -0.172
    for stair_index in range(stair_count):
        progress = stair_index / max(1, stair_count - 1)
        _chamfer_box(
            specs,
            "a21-r4-palace-ceremonial-gallery-stair",
            "ivory_stone",
            group,
            -29.0 + normal_x * (3.8 - progress * 5.8),
            1.15 + progress * 9.55,
            -44.0 + normal_z * (3.8 - progress * 5.8),
            7.4 - progress * 0.9,
            0.34,
            1.10,
            (0.050, 0.043, 0.036)[lod],
            1,
        )
    # The crown root grows through the keep shoulder and is occupied before
    # the petal structure begins; it is not a detached row of roof teeth.
    root_x, root_z = -28.0, -68.0
    _cylinder(
        specs,
        "a21-r4-palace-rooted-crown-occupied-drum",
        "ivory_stone",
        group,
        root_x,
        29.0,
        root_z,
        (11.0, 10.0, 8.8)[lod],
        12.0,
        (24, 16, 10)[lod],
        top_radius=(9.4, 8.6, 7.5)[lod],
    )
    for ring_index, ring_y in enumerate((23.3, 27.0, 31.0, 34.6)):
        if lod == 2 and ring_index not in {1, 3}:
            continue
        _cylinder(
            specs,
            "a21-r4-palace-rooted-crown-carved-course",
            "wet_stone" if ring_index in {0, 2} else "carved_stone",
            group,
            root_x,
            ring_y,
            root_z,
            (11.15, 10.15, 8.95)[lod],
            (0.46, 0.38, 0.31)[lod],
            (24, 16, 10)[lod],
            top_radius=(10.7, 9.7, 8.5)[lod],
        )
    _cylinder(
        specs,
        "a21-r4-palace-rooted-crown-brass-cornice",
        "brass",
        group,
        root_x,
        35.0,
        root_z,
        (9.9, 9.0, 7.8)[lod],
        0.68,
        (24, 16, 10)[lod],
        top_radius=(9.5, 8.6, 7.5)[lod],
    )
    camera_normal = (0.985, -0.172)
    camera_tangent = (0.172, 0.985)
    face_x = root_x + camera_normal[0] * 9.0
    face_z = root_z + camera_normal[1] * 9.0
    root_bays = (5, 4, 3)[lod]
    for bay_index in range(root_bays):
        offset = (bay_index - (root_bays - 1) * 0.5) * 3.65
        bay_x = face_x + camera_tangent[0] * offset
        bay_z = face_z + camera_tangent[1] * offset
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r4-palace-rooted-crown-occupied-loggia",
            centre_x=bay_x,
            centre_z=bay_z,
            axis_x=camera_tangent[0],
            axis_z=camera_tangent[1],
            half_width=1.45,
            base_y=23.5,
            spring_y=29.7,
            rise=2.65,
            segments=(16, 10, 6)[lod],
            radius=(0.25, 0.21, 0.17)[lod],
            sides=(8, 6, 4)[lod],
            material="carved_stone",
        )
        _panel(
            specs,
            "a21-r4-palace-rooted-crown-warm-loggia",
            "warm_glow" if bay_index % 2 else "dirty_glass",
            group,
            (
                (
                    bay_x - camera_tangent[0] * 1.10,
                    24.0,
                    bay_z - camera_tangent[1] * 1.10,
                ),
                (
                    bay_x + camera_tangent[0] * 1.10,
                    24.0,
                    bay_z + camera_tangent[1] * 1.10,
                ),
                (
                    bay_x + camera_tangent[0] * 1.10,
                    29.8,
                    bay_z + camera_tangent[1] * 1.10,
                ),
                (
                    bay_x - camera_tangent[0] * 1.10,
                    29.8,
                    bay_z - camera_tangent[1] * 1.10,
                ),
            ),
            0.10,
        )
    petal_offsets = (
        (-8.4, -4.2, 0.0, 4.2, 8.4)
        if lod <= 1
        else (-6.0, 0.0, 6.0)
    )
    petal_plane_x = root_x + camera_normal[0] * 8.6
    petal_plane_z = root_z + camera_normal[1] * 8.6

    def petal_point(
        tangent_offset: float,
        y: float,
        depth_offset: float = 0.0,
    ) -> tuple[float, float, float]:
        return (
            petal_plane_x
            + camera_tangent[0] * tangent_offset
            + camera_normal[0] * depth_offset,
            y,
            petal_plane_z
            + camera_tangent[1] * tangent_offset
            + camera_normal[1] * depth_offset,
        )

    for petal_index, offset in enumerate(petal_offsets):
        root_offset = offset * 0.28
        shoulder_offset = offset * 0.92
        tip_offset = offset * 1.06
        root_half = (4.35, 3.70, 3.00)[lod]
        shoulder_half = (3.45, 2.95, 2.35)[lod]
        root_y = 30.0
        shoulder_y = 38.0 - abs(offset) * 0.045
        tip_y = 42.20 - abs(offset) * 0.115
        root_left = petal_point(root_offset - root_half, root_y)
        root_right = petal_point(root_offset + root_half, root_y)
        shoulder_left = petal_point(
            shoulder_offset - shoulder_half,
            shoulder_y,
            0.30,
        )
        shoulder_right = petal_point(
            shoulder_offset + shoulder_half,
            shoulder_y,
            0.30,
        )
        tip = petal_point(tip_offset, tip_y, 0.12)
        _panel(
            specs,
            "a21-r4-palace-rooted-five-petal-crown",
            "ivory_stone" if petal_index % 2 == 0 else "carved_stone",
            group,
            (root_left, root_right, shoulder_right, tip, shoulder_left),
            (0.96, 0.78, 0.62)[lod],
        )
        _sweep(
            specs,
            "a21-r4-palace-rooted-crown-brass-spine",
            "brass",
            group,
            (
                petal_point(root_offset, root_y + 0.10),
                petal_point(shoulder_offset, shoulder_y, 0.32),
                tip,
            ),
            (0.15, 0.12, 0.095)[lod],
            (9, 7, 5)[lod],
        )
        if lod <= 1:
            inset = (
                petal_point(root_offset - root_half * 0.55, root_y + 0.65, 0.50),
                petal_point(root_offset + root_half * 0.55, root_y + 0.65, 0.50),
                petal_point(
                    shoulder_offset + shoulder_half * 0.45,
                    shoulder_y - 0.55,
                    0.52,
                ),
                petal_point(tip_offset, tip_y - 0.50, 0.30),
                petal_point(
                    shoulder_offset - shoulder_half * 0.45,
                    shoulder_y - 0.55,
                    0.52,
                ),
            )
            _panel(
                specs,
                "a21-r4-palace-rooted-crown-luminous-relief",
                "flower",
                group,
                inset,
                0.10,
            )
        if lod == 0:
            for edge_start, edge_shoulder in (
                (root_left, shoulder_left),
                (root_right, shoulder_right),
            ):
                _sweep(
                    specs,
                    "a21-r4-palace-rooted-crown-carved-edge",
                    "brass",
                    group,
                    (edge_start, edge_shoulder, tip),
                    0.078,
                    7,
                )
    # Occupied planting and a grounded water-maintenance cluster give the
    # terraces ceremonial, botanical and service narratives.
    planter_count = (6, 4, 2)[lod]
    for planter_index in range(planter_count):
        offset = -19.0 + planter_index * 38.0 / max(1, planter_count - 1)
        planter_x = -27.0 + 0.172 * offset
        planter_z = -65.5 + 0.985 * offset
        _chamfer_box(
            specs,
            "a21-r4-palace-occupied-loggia-planter",
            "carved_stone",
            group,
            planter_x,
            19.0,
            planter_z,
            2.2,
            0.82,
            2.0,
            (0.065, 0.052, 0.042)[lod],
            1,
        )
        _leaf_cluster(
            specs,
            "a21-r4-palace-loggia-botanical-spill",
            "flower" if planter_index % 3 == 1 else "foliage_light",
            group,
            planter_x,
            19.75,
            planter_z,
            1.25,
            0.95,
            (18, 10, 5)[lod],
            28400 + planter_index,
        )
    wheel_points = tuple(
        (
            -23.8,
            2.2 + math.sin(math.tau * index / 16) * 1.25,
            -43.0 + math.cos(math.tau * index / 16) * 1.25,
        )
        for index in range(17)
    )
    _sweep(
        specs,
        "a21-r4-palace-water-maintenance-valve-wheel",
        "brass",
        group,
        wheel_points,
        (0.055, 0.046, 0.038)[lod],
        (8, 6, 4)[lod],
    )
    _sweep(
        specs,
        "a21-r4-palace-water-maintenance-grounded-stand",
        "verdigris_bronze",
        group,
        ((-23.8, 0.25, -43.0), (-23.8, 2.2, -43.0)),
        (0.090, 0.075, 0.060)[lod],
        (8, 6, 4)[lod],
    )


def _add_bridge_join_story_r4(specs: list[dict], lod: int) -> None:
    """Make bridge/coping contacts and the canal maintenance story explicit."""
    group = "a21-r4-nakaniwa-canal-contact-story"
    for bridge_index, bridge_t in enumerate((0.18, 0.50, 0.82)):
        centre_x, centre_z = _corridor_point(bridge_t)
        ahead_x, ahead_z = _corridor_point(min(1.0, bridge_t + 0.01))
        forward_x = ahead_x - centre_x
        forward_z = ahead_z - centre_z
        forward_len = math.hypot(forward_x, forward_z)
        forward_x /= forward_len
        forward_z /= forward_len
        for threshold_side in (-1.0, 1.0):
            offset = threshold_side * (3.0 + (0.35 if bridge_index == 1 else 0.0))
            _chamfer_box(
                specs,
                "a21-r4-bridge-coping-contact-key",
                "wet_stone",
                group,
                centre_x + forward_x * offset,
                0.64,
                centre_z + forward_z * offset,
                0.42,
                0.68,
                12.2 - bridge_t,
                (0.055, 0.045, 0.036)[lod],
                1,
            )
    if lod == 0:
        landing_x, landing_z = _corridor_point(0.38, -9.3)
        for tool_index, tool_offset in enumerate((-0.7, 0.0, 0.7)):
            _sweep(
                specs,
                "a21-r4-canal-maintenance-hand-tool",
                "brass" if tool_index == 1 else "dark_wood",
                group,
                (
                    (landing_x + tool_offset, 0.72, landing_z - 0.62),
                    (
                        landing_x + tool_offset + 0.18,
                        2.12,
                        landing_z - 0.62,
                    ),
                ),
                0.028,
                6,
            )


def _add_foreground_occupied_loggia_r4(
    specs: list[dict],
    lod: int,
) -> None:
    """Frame the dry promenade with a close inhabited garden building."""
    group = "a21-r4-nakaniwa-foreground-occupied-loggia"
    centre_x, centre_z = 98.0, -40.0
    _chamfer_box(
        specs,
        "a21-r4-foreground-loggia-grounded-hall",
        "ivory_stone",
        group,
        centre_x,
        8.15,
        centre_z,
        14.0,
        16.0,
        30.0,
        (0.18, 0.14, 0.10)[lod],
        2 if lod == 0 else 1,
    )
    _chamfer_box(
        specs,
        "a21-r4-foreground-loggia-wet-contact-plinth",
        "wet_stone",
        group,
        centre_x,
        0.72,
        centre_z,
        15.2,
        1.35,
        31.2,
        (0.14, 0.11, 0.08)[lod],
        1,
    )
    front_bays = (4, 3, 1)[lod]
    _monumental_arcade(
        specs,
        group=group,
        role="a21-r4-foreground-loggia-deep-front-arcade",
        material="carved_stone",
        x0=92.0,
        x1=104.0,
        z=-55.12,
        base_y=0.65,
        bays=front_bays,
        lod=lod,
        spring_height=6.0,
        rise=3.0,
        depth=(0.34, 0.28, 0.22)[lod],
    )
    for bay_index in range(front_bays):
        bay_x = 92.0 + (bay_index + 0.5) * 12.0 / front_bays
        _box(
            specs,
            "a21-r4-foreground-loggia-front-occupied-threshold",
            "warm_glow" if bay_index % 3 == 1 else "dirty_glass",
            group,
            bay_x,
            4.7,
            -54.65,
            2.1,
            6.9,
            0.12,
        )
    side_bays = (5, 4, 2)[lod]
    side_z0, side_z1 = -51.0, -29.0
    side_span = side_z1 - side_z0
    for bay_index in range(side_bays):
        bay_z = side_z0 + side_span * (bay_index + 0.5) / side_bays
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r4-foreground-loggia-deep-side-arcade",
            centre_x=105.05,
            centre_z=bay_z,
            axis_x=0.0,
            axis_z=1.0,
            half_width=side_span * 0.36 / side_bays,
            base_y=0.65,
            spring_y=6.65,
            rise=3.0,
            segments=(18, 10, 6)[lod],
            radius=(0.32, 0.26, 0.21)[lod],
            sides=(9, 6, 4)[lod],
            material="carved_stone",
        )
        _box(
            specs,
            "a21-r4-foreground-loggia-side-occupied-threshold",
            "warm_glow" if bay_index % 3 == 2 else "dirty_glass",
            group,
            104.70,
            4.7,
            bay_z,
            0.12,
            6.9,
            side_span * 0.58 / side_bays,
        )
    for pier_index in range(side_bays + 1):
        pier_z = side_z0 + side_span * pier_index / side_bays
        _chamfer_box(
            specs,
            "a21-r4-foreground-loggia-side-buttressed-pier",
            "ivory_stone",
            group,
            105.0,
            5.0,
            pier_z,
            1.08,
            9.8,
            1.08,
            (0.075, 0.060, 0.050)[lod],
            1,
        )
    _chamfer_box(
        specs,
        "a21-r4-foreground-loggia-side-entablature",
        "carved_stone",
        group,
        105.0,
        10.0,
        (side_z0 + side_z1) * 0.5,
        1.28,
        0.92,
        side_span + 1.2,
        (0.075, 0.060, 0.050)[lod],
        1,
    )
    # Upper occupied tier, deep windows and continuous supported balcony.
    _chamfer_box(
        specs,
        "a21-r4-foreground-loggia-upper-occupied-tier",
        "carved_stone",
        group,
        centre_x,
        13.2,
        centre_z,
        11.0,
        5.7,
        26.0,
        (0.14, 0.11, 0.08)[lod],
        1,
    )
    upper_window_count = (5, 3, 0)[lod]
    for window_index in range(upper_window_count):
        window_z = -49.0 + window_index * 18.0 / max(
            1,
            upper_window_count - 1,
        )
        _deep_window(
            specs,
            group=group,
            role="a21-r4-foreground-loggia-upper-deep-window",
            x=103.62,
            y=13.5,
            z=window_z,
            width=2.15,
            height=3.05,
            plane="side",
            warm=window_index in {1, 4},
        )
    _chamfer_box(
        specs,
        "a21-r4-foreground-loggia-supported-balcony",
        "ivory_stone",
        group,
        105.25,
        11.05,
        centre_z,
        1.6,
        0.42,
        25.0,
        (0.065, 0.052, 0.042)[lod],
        1,
    )
    _sweep(
        specs,
        "a21-r4-foreground-loggia-balcony-handrail",
        "brass",
        group,
        ((106.05, 12.22, -52.0), (106.05, 12.22, -28.0)),
        (0.040, 0.033, 0.027)[lod],
        (8, 6, 4)[lod],
    )
    post_count = (11, 7, 4)[lod]
    for post_index in range(post_count):
        post_z = -52.0 + post_index * 24.0 / max(1, post_count - 1)
        _sweep(
            specs,
            "a21-r4-foreground-loggia-balcony-post",
            "brass",
            group,
            ((106.05, 11.18, post_z), (106.05, 12.22, post_z)),
            (0.030, 0.025, 0.021)[lod],
            (7, 6, 4)[lod],
        )
    _roof(
        specs,
        group=group,
        role="a21-r4-foreground-loggia-deep-garden-roof",
        cx=centre_x,
        base_y=16.1,
        cz=centre_z,
        width=16.0,
        depth=32.0,
        rise=3.6,
        material="verdigris_bronze",
    )
    # A close planted ledge and pruned tree replace empty paving with a
    # human-scale inhabited edge while remaining outside the canonical route.
    _chamfer_box(
        specs,
        "a21-r4-foreground-loggia-botanical-planter",
        "carved_stone",
        group,
        90.5,
        1.0,
        -52.0,
        6.8,
        1.55,
        5.0,
        (0.10, 0.08, 0.06)[lod],
        1,
    )
    _box(
        specs,
        "a21-r4-foreground-loggia-botanical-soil",
        "wet_stone",
        group,
        90.5,
        1.78,
        -52.0,
        6.1,
        0.18,
        4.3,
    )
    _tree(
        specs,
        group=group,
        role="a21-r4-foreground-loggia-pruned-tree",
        x=90.5,
        z=-52.0,
        height=14.0,
        crown=5.0,
        lod=lod,
        seed=29510,
        flowering=True,
    )
    stair_count = (6, 5, 4)[lod]
    for stair_index in range(stair_count):
        _chamfer_box(
            specs,
            "a21-r4-foreground-loggia-arcade-entry-stair",
            "ivory_stone",
            group,
            98.0,
            0.12 + stair_index * 0.16,
            -56.0 - stair_index * 0.42,
            8.5 - stair_index * 0.30,
            0.24,
            0.72,
            (0.040, 0.034, 0.028)[lod],
            1,
        )


def build_specs(lod: int = 0) -> list[dict]:
    """Return a deterministic macro-first A21 plan without importing Blender."""
    if lod not in (0, 1, 2):
        raise ValueError(f"unsupported LOD: {lod}")
    specs: list[dict] = []
    _add_garden_city_composition_r2(specs, lod)
    _add_dense_mid_canal_city_r3(specs, lod)
    _add_ceremonial_canal_gate_r3(specs, lod)
    _add_bridge_join_story_r4(specs, lod)
    _add_foreground_occupied_loggia_r4(specs, lod)
    _add_palace(specs, lod)
    _remove_legacy_duplicate_palace_crowns(specs)
    _add_palace_terraces_and_rooted_crown_r4(specs, lod)
    _add_conservatory(specs, lod)
    return specs


def spec_bounds(spec: Mapping[str, object]) -> tuple[float, float, float, float, float, float]:
    kind = spec["kind"]
    if kind in {"box", "chamfer_box", "cylinder", "leaf_cluster"}:
        if kind == "cylinder":
            rx = rz = max(float(spec["radius"]), float(spec["topRadius"]))
            ry = float(spec["height"]) / 2.0
        elif kind == "leaf_cluster":
            rx = rz = float(spec["radius"])
            ry = float(spec["height"]) / 2.0
        else:
            rx, ry, rz = (
                float(spec["w"]) / 2.0,
                float(spec["h"]) / 2.0,
                float(spec["d"]) / 2.0,
            )
        return (
            float(spec["x"]) - rx, float(spec["y"]) - ry, float(spec["z"]) - rz,
            float(spec["x"]) + rx, float(spec["y"]) + ry, float(spec["z"]) + rz,
        )
    if kind == "panel":
        points = spec["corners"]
        thickness = float(spec["thickness"]) * 0.5
    elif kind == "sweep":
        points = spec["points"]
        thickness = float(spec["radius"])
    else:
        raise ValueError(f"unsupported spec kind: {kind}")
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    zs = [float(point[2]) for point in points]
    return (
        min(xs) - thickness, min(ys) - thickness, min(zs) - thickness,
        max(xs) + thickness, max(ys) + thickness, max(zs) + thickness,
    )


def estimated_triangles(specs: Sequence[Mapping[str, object]]) -> int:
    total = 0
    for spec in specs:
        kind = spec["kind"]
        if kind == "cylinder":
            total += int(spec["segments"]) * 4
        elif kind == "chamfer_box":
            # Blender's baked one-segment cube bevel triangulates to 44 faces;
            # two segments add the second edge band and rounded corners.
            total += 44 if int(spec["segments"]) == 1 else 92
        elif kind == "sweep":
            total += (
                2 * int(spec["sides"]) * (len(spec["points"]) - 1)
                + 2 * int(spec["sides"])
            )
        elif kind == "leaf_cluster":
            total += int(spec["leaves"]) * 4
        elif kind == "panel":
            corner_count = len(spec["corners"])
            total += corner_count * 4 - 4
        else:
            total += 12
    return total


def _camera_basis(camera: Mapping[str, object]):
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
            bounds = spec_bounds(spec)
            points.extend(
                (x, y, z)
                for x in (bounds[0], bounds[3])
                for y in (bounds[1], bounds[4])
                for z in (bounds[2], bounds[5])
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
        visible = (
            max(0.0, min(xs)), max(0.0, min(ys)),
            min(1.0, max(xs)), min(1.0, max(ys)),
        )
        heroes.append({
            "id": landmark["id"],
            "rawFrameBounds": (min(xs), min(ys), max(xs), max(ys)),
            "visibleFrameBounds": visible,
            "visibleFrameWidthRatio": max(0.0, visible[2] - visible[0]),
            "visibleFrameHeightRatio": max(0.0, visible[3] - visible[1]),
        })
    return {
        "camera": copy.deepcopy(camera),
        "heroes": heroes,
        "passed": (
            all(hero["visibleFrameWidthRatio"] >= 0.30 for hero in heroes)
            and all(hero["visibleFrameHeightRatio"] >= 0.32 for hero in heroes)
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


def locked_r3_scorecard_report() -> dict:
    """Report the immutable independent R3 score without rewriting it."""
    exists = INDEPENDENT_SCORECARD_R3_PATH.is_file()
    actual_sha256 = (
        hashlib.sha256(INDEPENDENT_SCORECARD_R3_PATH.read_bytes()).hexdigest()
        if exists
        else None
    )
    return {
        "path": str(INDEPENDENT_SCORECARD_R3_PATH),
        "expectedSha256": INDEPENDENT_SCORECARD_R3_SHA256,
        "actualSha256": actual_sha256,
        "exists": exists,
        "matched": exists and actual_sha256 == INDEPENDENT_SCORECARD_R3_SHA256,
        "writeAttempted": False,
    }


def gameplay_intrusion_report(lod: int = 0) -> dict:
    """Prove that the art shell remains non-blocking at routes and spawns."""
    specs = build_specs(lod)
    blocking = [spec for spec in specs if bool(spec["blocksGameplay"])]
    camera_point = tuple(float(value) for value in MAIN_REFERENCE_CAMERA["location"])
    camera_hits = []
    for spec in specs:
        bounds = spec_bounds(spec)
        if (
            bounds[0] <= camera_point[0] <= bounds[3]
            and bounds[1] <= camera_point[1] <= bounds[4]
            and bounds[2] <= camera_point[2] <= bounds[5]
        ):
            camera_hits.append(str(spec["role"]))

    def point_hits_blocking(point: Sequence[float]) -> bool:
        x = float(point[0])
        z = float(point[-1])
        return any(
            (bounds := spec_bounds(spec))[0] <= x <= bounds[3]
            and bounds[2] <= z <= bounds[5]
            for spec in blocking
        )

    player_spawn_hits = sum(
        point_hits_blocking(point) for point in CANONICAL_PLAYER_SPAWNS
    )
    bot_spawn_hits = sum(
        point_hits_blocking(point) for point in CANONICAL_BOT_SPAWNS
    )
    return {
        "lod": lod,
        "blockingSpecCount": len(blocking),
        "playerSpawnIntrusions": player_spawn_hits,
        "botSpawnIntrusions": bot_spawn_hits,
        "approachRouteIntrusions": 0 if not blocking else len(LANDMARKS),
        "cameraIntrusions": len(camera_hits),
        "cameraHitRoles": sorted(camera_hits),
        "passed": (
            not blocking
            and player_spawn_hits == 0
            and bot_spawn_hits == 0
            and not camera_hits
        ),
    }


INDEPENDENT_BASELINE_SCORES = {
    "composition": 5.0,
    "hero silhouettes": 5.5,
    "architectural grammar": 4.1,
    "human scale": 4.8,
    "material realism": 2.9,
    "near/mid/far density": 3.8,
    "gameplay readability": 6.5,
    "props and environmental storytelling": 3.9,
    "lighting and atmosphere": 3.9,
    "reference identity": 4.6,
}


def independent_baseline_scorecard(evidence_paths: Sequence[str] = ()) -> dict:
    """Carry the lower independent baseline; never self-rescore the rebuild."""
    scores = [
        {"category": category, "score": INDEPENDENT_BASELINE_SCORES[category]}
        for category in FIXED_SCORE_CATEGORIES
    ]
    values = [item["score"] for item in scores]
    return {
        "schemaVersion": 1,
        "audit": "hibana-independent-r3-baseline-carry-forward-v2",
        "stageId": STAGE_ID,
        "candidate": KIT_VERSION,
        "reviewer": "independent-baseline-carry-forward-no-self-rescore",
        "sourceScorecard": str(INDEPENDENT_SCORECARD_R3_PATH),
        "sourceScorecardSha256": INDEPENDENT_SCORECARD_R3_SHA256,
        "reference": {"path": str(REFERENCE_PATH), "sha256": REFERENCE_SHA256},
        "namedLandmarks": [item["referenceName"] for item in LANDMARKS],
        "scores": scores,
        "arithmeticMean": round(sum(values) / len(values), 2),
        "minimumCategoryScore": min(values),
        "evidencePaths": list(evidence_paths),
        "strongestRemainingMismatch": (
            "The fixed independent R3 4.50 baseline controls until a different "
            "reviewer compares the R4 candidate at original resolution."
        ),
        "genericBlockoutBaseline": True,
        "rebuildSelfCertified": False,
        "referencePassClaimed": False,
        "verdict": "NO-SHIP_PENDING_NEW_INDEPENDENT_REVIEW",
    }


def producer_provisional_scorecard(evidence_paths: Sequence[str] = ()) -> dict:
    """Backward-compatible API returning the controlling independent baseline."""
    return independent_baseline_scorecard(evidence_paths)


def canonical_contract_report(layout_path: Path = CANONICAL_LAYOUT_DEFAULT) -> dict:
    return A20.canonical_contract_report(layout_path)


class A21MeshBuilder:
    """Bake role-specific geometry before material batching."""

    def __init__(self, collection, materials):
        self.collection = collection
        self.materials = materials
        self.parts: dict[str, dict[str, list]] = defaultdict(
            lambda: {"verts": [], "faces": []}
        )

    @staticmethod
    def _rv(point):
        return (float(point[0]), float(point[2]), float(point[1]))

    def _part(self, key):
        return self.parts[key]

    def add_box(self, x, y, z, w, h, d, key="wet_stone"):
        part = self._part(key)
        base = len(part["verts"])
        hx, hy, hz = w / 2.0, h / 2.0, d / 2.0
        runtime = (
            (x-hx, y-hy, z-hz), (x+hx, y-hy, z-hz),
            (x+hx, y-hy, z+hz), (x-hx, y-hy, z+hz),
            (x-hx, y+hy, z-hz), (x+hx, y+hy, z-hz),
            (x+hx, y+hy, z+hz), (x-hx, y+hy, z+hz),
        )
        part["verts"].extend(self._rv(point) for point in runtime)
        part["faces"].extend(
            (base+a, base+b, base+c, base+d)
            for a, b, c, d in (
                (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
            )
        )

    def add_chamfer_box(self, x, y, z, w, h, d, bevel, segments,
                        key="carved_stone"):
        import bmesh  # type: ignore
        from mathutils import Vector  # type: ignore

        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector((w, d, h)), verts=list(bm.verts))
        bmesh.ops.bevel(
            bm, geom=list(bm.edges), offset=bevel, segments=segments,
            affect="EDGES", clamp_overlap=True,
        )
        bm.verts.ensure_lookup_table()
        part = self._part(key)
        base = len(part["verts"])
        mapping = {}
        # bmesh was built directly in Blender X/Y-plan/Z-up.
        for index, vertex in enumerate(bm.verts):
            mapping[vertex] = base + index
            part["verts"].append((
                float(vertex.co.x + x),
                float(vertex.co.y + z),
                float(vertex.co.z + y),
            ))
        for face in bm.faces:
            part["faces"].append(tuple(mapping[vertex] for vertex in face.verts))
        bm.free()

    def add_cylinder(self, x, y, z, radius, height, key="brass",
                     segments=12, top_radius=None):
        top_radius = radius if top_radius is None else top_radius
        part = self._part(key)
        base = len(part["verts"])
        for ring_radius, yy in ((radius, y-height/2), (top_radius, y+height/2)):
            for index in range(segments):
                angle = math.tau * index / segments
                part["verts"].append(self._rv((
                    x + math.cos(angle) * ring_radius,
                    yy,
                    z + math.sin(angle) * ring_radius,
                )))
        part["verts"].extend((self._rv((x, y-height/2, z)), self._rv((x, y+height/2, z))))
        bottom, top = base + segments * 2, base + segments * 2 + 1
        for index in range(segments):
            nxt = (index + 1) % segments
            part["faces"].append((
                base+index, base+nxt, base+segments+nxt, base+segments+index
            ))
            part["faces"].append((bottom, base+nxt, base+index))
            part["faces"].append((top, base+segments+index, base+segments+nxt))

    def add_surface_panel(self, corners, thickness, key="dirty_glass"):
        part = self._part(key)
        base = len(part["verts"])
        corners = tuple(tuple(float(value) for value in point) for point in corners)
        # Newell's method remains stable when the first three polygon corners
        # are intentionally collinear (several crown petals use that layout).
        normal = [0.0, 0.0, 0.0]
        for index, point in enumerate(corners):
            nxt = corners[(index + 1) % len(corners)]
            normal[0] += (point[1] - nxt[1]) * (point[2] + nxt[2])
            normal[1] += (point[2] - nxt[2]) * (point[0] + nxt[0])
            normal[2] += (point[0] - nxt[0]) * (point[1] + nxt[1])
        normal = tuple(normal)
        normal_length = math.sqrt(sum(value * value for value in normal))
        if normal_length <= 1e-9:
            raise ValueError("surface panel corners must span a non-zero plane")
        normal = tuple(value / normal_length for value in normal)
        half = thickness * 0.5
        front = tuple(
            tuple(point[axis] + normal[axis] * half for axis in range(3))
            for point in corners
        )
        back = tuple(
            tuple(point[axis] - normal[axis] * half for axis in range(3))
            for point in corners
        )
        part["verts"].extend(self._rv(point) for point in front)
        part["verts"].extend(self._rv(point) for point in back)
        corner_count = len(corners)
        part["faces"].append(
            tuple(base + index for index in range(corner_count))
        )
        part["faces"].append(
            tuple(
                base + corner_count + index
                for index in reversed(range(corner_count))
            )
        )
        for index in range(corner_count):
            nxt = (index + 1) % corner_count
            part["faces"].append((
                base + index,
                base + nxt,
                base + corner_count + nxt,
                base + corner_count + index,
            ))

    def add_sweep(self, points, radius, sides, key="brass"):
        points = [tuple(float(value) for value in point) for point in points]
        part = self._part(key)
        base = len(part["verts"])

        def sub(a, b):
            return tuple(a[index] - b[index] for index in range(3))

        def cross(a, b):
            return (
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            )

        def unit(value):
            length = math.sqrt(sum(component * component for component in value))
            return tuple(component / length for component in value)

        for index, point in enumerate(points):
            if index == 0:
                tangent = unit(sub(points[1], point))
            elif index == len(points) - 1:
                tangent = unit(sub(point, points[index - 1]))
            else:
                tangent = unit(sub(points[index + 1], points[index - 1]))
            reference = (0.0, 0.0, 1.0)
            if abs(sum(tangent[i] * reference[i] for i in range(3))) > 0.94:
                reference = (0.0, 1.0, 0.0)
            normal_a = unit(cross(tangent, reference))
            normal_b = unit(cross(tangent, normal_a))
            for side in range(sides):
                angle = math.tau * side / sides
                offset = tuple(
                    radius * (
                        normal_a[axis] * math.cos(angle)
                        + normal_b[axis] * math.sin(angle)
                    )
                    for axis in range(3)
                )
                part["verts"].append(self._rv(tuple(
                    point[axis] + offset[axis] for axis in range(3)
                )))
        for ring in range(len(points) - 1):
            for side in range(sides):
                nxt = (side + 1) % sides
                a = base + ring * sides + side
                b = base + ring * sides + nxt
                c = base + (ring + 1) * sides + nxt
                d = base + (ring + 1) * sides + side
                part["faces"].append((a, b, c, d))
        start_center = len(part["verts"])
        part["verts"].append(self._rv(points[0]))
        end_center = len(part["verts"])
        part["verts"].append(self._rv(points[-1]))
        for side in range(sides):
            nxt = (side + 1) % sides
            part["faces"].append((start_center, base+nxt, base+side))
            last = base + (len(points) - 1) * sides
            part["faces"].append((end_center, last+side, last+nxt))

    def add_leaf_cluster(self, x, y, z, radius, height, leaves, seed,
                         key="foliage_dark"):
        rng = random.Random(seed)
        part = self._part(key)
        for leaf_index in range(leaves):
            theta = rng.random() * math.tau
            radial = radius * (0.05 + 0.45 * rng.random())
            centre = (
                x + math.cos(theta) * radial,
                y + (rng.random() - 0.5) * height * 0.62,
                z + math.sin(theta) * radial,
            )
            yaw = theta + (rng.random() - 0.5) * 1.4
            leaf_len = radius * (0.075 + 0.055 * rng.random())
            leaf_w = leaf_len * (0.50 + 0.18 * rng.random())
            direction = (
                math.cos(yaw) * 0.74,
                0.38 + rng.random() * 0.42,
                math.sin(yaw) * 0.74,
            )
            dlen = math.sqrt(sum(value * value for value in direction))
            direction = tuple(value / dlen for value in direction)
            right = (-math.sin(yaw), 0.0, math.cos(yaw))
            base_point = tuple(
                centre[i] - direction[i] * leaf_len * 0.42
                for i in range(3)
            )
            tip_point = tuple(
                centre[i] + direction[i] * leaf_len * 0.68
                for i in range(3)
            )
            points = (
                base_point,
                tuple(centre[i] - right[i] * leaf_w for i in range(3)),
                tip_point,
                tuple(centre[i] + right[i] * leaf_w for i in range(3)),
                base_point,
                (
                    centre[0],
                    centre[1] - leaf_w * 0.72,
                    centre[2],
                ),
                tip_point,
                (
                    centre[0],
                    centre[1] + leaf_w * 0.72,
                    centre[2],
                ),
            )
            base = len(part["verts"])
            part["verts"].extend(self._rv(point) for point in points)
            part["faces"].extend((
                (base, base+1, base+2),
                (base, base+2, base+3),
                (base+4, base+5, base+6),
                (base+4, base+6, base+7),
            ))

    def flush(self):
        import bpy  # type: ignore

        objects = []
        for key, part in sorted(self.parts.items()):
            mesh = bpy.data.meshes.new(f"HB_NAKANIWA_A21_{key}_MESH")
            mesh.from_pydata(part["verts"], [], part["faces"])
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new(f"HB_NAKANIWA_A21_{key}", mesh)
            self.collection.objects.link(obj)
            obj.data.materials.append(self.materials[key])
            obj["hibanaStageId"] = STAGE_ID
            obj["hibanaKitVersion"] = KIT_VERSION
            obj["hibanaMaterialRole"] = key
            obj["hibanaBakedRoleGeometry"] = True
            objects.append(obj)
        return objects


def emit_specs_to_builder(builder, specs: Iterable[dict],
                          material_map: Mapping[str, str] | None = None) -> list[dict]:
    specs = list(specs)
    mapping = DEFAULT_INTEGRATION_MATERIAL_MAP if material_map is None else material_map
    for spec in specs:
        key = mapping.get(spec["material"], spec["material"])
        kind = spec["kind"]
        if kind == "box":
            builder.add_box(spec["x"], spec["y"], spec["z"],
                            spec["w"], spec["h"], spec["d"], key)
        elif kind == "chamfer_box":
            builder.add_chamfer_box(
                spec["x"], spec["y"], spec["z"], spec["w"], spec["h"], spec["d"],
                spec["bevel"], spec["segments"], key,
            )
        elif kind == "cylinder":
            builder.add_cylinder(
                spec["x"], spec["y"], spec["z"], spec["radius"], spec["height"],
                key, spec["segments"], spec["topRadius"],
            )
        elif kind == "panel":
            builder.add_surface_panel(spec["corners"], spec["thickness"], key)
        elif kind == "sweep":
            builder.add_sweep(spec["points"], spec["radius"], spec["sides"], key)
        elif kind == "leaf_cluster":
            builder.add_leaf_cluster(
                spec["x"], spec["y"], spec["z"], spec["radius"], spec["height"],
                spec["leaves"], spec["seed"], key,
            )
        else:
            raise ValueError(f"unsupported spec kind: {kind}")
    return specs


def emit_to_builder(builder, lod: int = 0,
                    material_map: Mapping[str, str] | None = None) -> list[dict]:
    return emit_specs_to_builder(builder, build_specs(lod), material_map)


def _make_blender_materials():
    import bpy  # type: ignore

    materials = {}
    for role, recipe in MATERIALS.items():
        material = bpy.data.materials.new(f"MAT_Nakaniwa_A21_{role}")
        material.use_nodes = True
        material.use_backface_culling = False
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        texcoord = nodes.new("ShaderNodeTexCoord")
        macro = nodes.new("ShaderNodeTexNoise")
        detail = nodes.new("ShaderNodeTexNoise")
        mix = nodes.new("ShaderNodeMixRGB")
        ramp = nodes.new("ShaderNodeValToRGB")
        roughness = nodes.new("ShaderNodeMapRange")
        bump = nodes.new("ShaderNodeBump")
        base = recipe["color"]
        macro.inputs["Scale"].default_value = recipe["noiseScale"]
        macro.inputs["Detail"].default_value = 3.0
        macro.inputs["Roughness"].default_value = 0.68
        detail.inputs["Scale"].default_value = recipe["detailScale"]
        detail.inputs["Detail"].default_value = 2.0
        detail.inputs["Roughness"].default_value = 0.58
        mix.blend_type = "MULTIPLY"
        stone_like = "stone" in role
        pale_stone = role in {"ivory_stone", "carved_stone", "moss_stone"}
        mix.inputs["Fac"].default_value = 0.42 if stone_like else 0.29
        ramp.color_ramp.elements[0].position = 0.19
        ramp.color_ramp.elements[1].position = 0.82
        ramp.color_ramp.elements[0].color = tuple(
            max(
                0.0,
                value * (
                    0.66 if pale_stone else 0.52 if stone_like else 0.72
                ),
            )
            for value in base[:3]
        ) + (base[3],)
        ramp.color_ramp.elements[1].color = tuple(
            min(
                1.0,
                value * (1.22 if stone_like else 1.10)
                + (0.035 if pale_stone else 0.020),
            )
            for value in base[:3]
        ) + (base[3],)
        roughness.inputs["To Min"].default_value = recipe["roughness"][0]
        roughness.inputs["To Max"].default_value = recipe["roughness"][1]
        bump.inputs["Strength"].default_value = recipe.get("bump", 0.0)
        bump.inputs["Distance"].default_value = (
            0.045 if stone_like else 0.020
        )
        links.new(texcoord.outputs["Object"], macro.inputs["Vector"])
        links.new(texcoord.outputs["Object"], detail.inputs["Vector"])
        links.new(macro.outputs["Fac"], mix.inputs[1])
        links.new(detail.outputs["Fac"], mix.inputs[2])
        links.new(mix.outputs["Color"], ramp.inputs["Fac"])
        links.new(macro.outputs["Fac"], roughness.inputs["Value"])
        base_color_output = ramp.outputs["Color"]
        bump_height_output = detail.outputs["Fac"]
        if role in {"ivory_stone", "carved_stone", "moss_stone"}:
            brick = nodes.new("ShaderNodeTexBrick")
            brick_mix = nodes.new("ShaderNodeMixRGB")
            brick_mix.blend_type = "MULTIPLY"
            brick_mix.inputs["Fac"].default_value = {
                "ivory_stone": 0.24,
                "carved_stone": 0.30,
                "moss_stone": 0.22,
            }[role]
            brick.inputs["Color1"].default_value = (0.98, 0.96, 0.91, 1.0)
            brick.inputs["Color2"].default_value = (0.89, 0.85, 0.77, 1.0)
            brick.inputs["Mortar"].default_value = (0.32, 0.29, 0.24, 1.0)
            brick.inputs["Scale"].default_value = (
                0.34
                if role == "ivory_stone"
                else 0.40
                if role == "moss_stone"
                else 0.46
            )
            brick.inputs["Mortar Size"].default_value = 0.022
            brick.inputs["Mortar Smooth"].default_value = 0.012
            brick.inputs["Bias"].default_value = 0.035
            if role == "ivory_stone":
                brick_mapping = nodes.new("ShaderNodeMapping")
                brick_mapping.inputs["Rotation"].default_value[0] = (
                    math.pi * 0.5
                )
                links.new(
                    texcoord.outputs["Object"],
                    brick_mapping.inputs["Vector"],
                )
                links.new(
                    brick_mapping.outputs["Vector"],
                    brick.inputs["Vector"],
                )
            else:
                links.new(texcoord.outputs["Object"], brick.inputs["Vector"])
            links.new(ramp.outputs["Color"], brick_mix.inputs[1])
            links.new(brick.outputs["Color"], brick_mix.inputs[2])
            base_color_output = brick_mix.outputs["Color"]
            bump_height_output = brick.outputs["Fac"]
        elif "glass" in role:
            layer_weight = nodes.new("ShaderNodeLayerWeight")
            glass_reflection = nodes.new("ShaderNodeMixRGB")
            glass_reflection.blend_type = "SCREEN"
            glass_reflection.inputs[2].default_value = (0.13, 0.36, 0.39, 1.0)
            layer_weight.inputs["Blend"].default_value = 0.20
            links.new(
                layer_weight.outputs["Fresnel"],
                glass_reflection.inputs["Fac"],
            )
            links.new(ramp.outputs["Color"], glass_reflection.inputs[1])
            base_color_output = glass_reflection.outputs["Color"]
        links.new(base_color_output, shader.inputs["Base Color"])
        links.new(roughness.outputs["Result"], shader.inputs["Roughness"])
        if recipe.get("bump", 0.0) > 0.0:
            links.new(bump_height_output, bump.inputs["Height"])
            links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        shader.inputs["Metallic"].default_value = recipe["metallic"]
        transmission = shader.inputs.get("Transmission Weight") or shader.inputs.get("Transmission")
        if transmission is not None:
            transmission.default_value = recipe.get("transmission", 0.0)
        if shader.inputs.get("IOR") is not None:
            shader.inputs["IOR"].default_value = recipe.get("ior", 1.45)
        ior_level = shader.inputs.get("IOR Level")
        if ior_level is not None:
            if role == "water":
                ior_level.default_value = 0.32
            elif "glass" in role:
                ior_level.default_value = 0.46
        coat = shader.inputs.get("Coat Weight") or shader.inputs.get("Coat")
        if coat is not None:
            if "glass" in role:
                coat.default_value = 0.52
            elif role == "water":
                coat.default_value = 0.38
        coat_roughness = shader.inputs.get("Coat Roughness")
        if coat_roughness is not None:
            if "glass" in role:
                coat_roughness.default_value = 0.045
            elif role == "water":
                coat_roughness.default_value = 0.075
        if shader.inputs.get("Alpha") is not None:
            shader.inputs["Alpha"].default_value = recipe.get("alpha", base[3])
        subsurface = shader.inputs.get("Subsurface Weight") or shader.inputs.get("Subsurface")
        if subsurface is not None:
            subsurface.default_value = recipe.get("subsurface", 0.0)
        emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if emission is not None and recipe.get("emission"):
            emission.default_value = recipe["emission"]
            strength = shader.inputs.get("Emission Strength")
            if strength is not None:
                strength.default_value = recipe.get("emissionStrength", 1.0)
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        material.diffuse_color = base
        material["a21PbrChannels"] = (
            "baseColor,macroVariation,largeAshlarMortar,detailBump,"
            "roughness,fresnelReflection,wetCoat"
        )
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
    camera["a21EyeHeightM"] = float(spec["eyeHeightM"])
    camera["a21Intent"] = str(spec["intent"])
    return camera


def _reset_scene():
    import bpy  # type: ignore

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        if material.users == 0:
            bpy.data.materials.remove(material)


def _configure_scene():
    import bpy  # type: ignore

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
    scene.view_settings.exposure = -0.24
    return scene


def _add_world_and_lights(lighting):
    import bpy  # type: ignore

    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("HB_NAKANIWA_A21_WORLD")
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
    sky.sun_elevation = math.radians(11.5)
    sky.sun_rotation = math.radians(228.0)
    sky.air_density = 1.28
    if hasattr(sky, "dust_density"):
        sky.dust_density = 5.4
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.13
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(sky.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])

    sun_data = bpy.data.lights.new("LGT_Nakaniwa_A21_Sun_DATA", "SUN")
    sun_data.energy = 5.60
    sun_data.angle = math.radians(1.65)
    sun_data.color = (1.0, 0.48, 0.22)
    sun_data.use_shadow = True
    sun = bpy.data.objects.new("LGT_Nakaniwa_A21_Sun", sun_data)
    lighting.objects.link(sun)
    sun.location = _runtime_to_blender((112.0, 120.0, -132.0))
    sun.rotation_euler = (
        _runtime_to_blender((-8.0, 8.0, -2.0)) - sun.location
    ).to_track_quat("-Z", "Y").to_euler()

    fill_data = bpy.data.lights.new("LGT_Nakaniwa_A21_CoolFill_DATA", "AREA")
    fill_data.energy = 48.0
    fill_data.shape = "DISK"
    fill_data.size = 78.0
    fill_data.color = (0.46, 0.58, 0.74)
    fill_data.use_shadow = True
    fill = bpy.data.objects.new("LGT_Nakaniwa_A21_CoolFill", fill_data)
    lighting.objects.link(fill)
    fill.location = _runtime_to_blender((-20.0, 90.0, 80.0))
    fill.rotation_euler = (
        _runtime_to_blender((-4.0, 10.0, 0.0)) - fill.location
    ).to_track_quat("-Z", "Y").to_euler()

    bounce_data = bpy.data.lights.new(
        "LGT_Nakaniwa_A21_WarmGardenBounce_DATA",
        "AREA",
    )
    bounce_data.energy = 430.0
    bounce_data.shape = "DISK"
    bounce_data.size = 64.0
    bounce_data.color = (1.0, 0.42, 0.12)
    bounce_data.use_shadow = True
    bounce = bpy.data.objects.new(
        "LGT_Nakaniwa_A21_WarmGardenBounce",
        bounce_data,
    )
    lighting.objects.link(bounce)
    bounce.location = _runtime_to_blender((92.0, 34.0, -78.0))
    bounce.rotation_euler = (
        _runtime_to_blender((-5.0, 8.0, -5.0)) - bounce.location
    ).to_track_quat("-Z", "Y").to_euler()

    practicals = (
        ("PalaceGate", (-60.0, 4.8, -28.5), 560.0, 7.0),
        ("PalaceCrown", (-40.0, 36.5, -49.0), 720.0, 9.0),
        ("ConservatoryEntry", (52.0, 7.0, 30.0), 620.0, 8.0),
        ("ConservatoryGarden", (52.0, 10.0, 64.0), 860.0, 11.0),
        ("GardenBridge", (47.0, 3.0, -84.0), 410.0, 6.0),
    )
    for name, location, energy, radius in practicals:
        data = bpy.data.lights.new(f"LGT_Nakaniwa_A21_{name}_DATA", "POINT")
        data.energy = energy * 1.08
        data.color = (1.0, 0.48, 0.12)
        data.shadow_soft_size = radius
        data.use_shadow = True
        light = bpy.data.objects.new(f"LGT_Nakaniwa_A21_{name}", data)
        lighting.objects.link(light)
        light.location = _runtime_to_blender(location)


def _triangle_count(objects) -> int:
    import bpy  # type: ignore

    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        total += sum(max(1, len(poly.vertices) - 2) for poly in mesh.polygons)
        evaluated.to_mesh_clear()
    return total


def _write_sha_artifact(path: Path) -> dict:
    payload = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def build_private_production(
    output_dir: Path = PRIVATE_PRODUCTION_DEFAULT,
    layout_path: Path = CANONICAL_LAYOUT_DEFAULT,
    view_indices: Sequence[int] | None = None,
) -> dict:
    import bpy  # type: ignore

    output_dir = output_dir.expanduser().resolve()
    approved = PRIVATE_PRODUCTION_DEFAULT.resolve()
    if output_dir != approved and approved not in output_dir.parents:
        raise ValueError(f"A21 output must stay below {approved}: {output_dir}")
    if str(output_dir).startswith(str(REPO_ROOT.resolve())):
        raise ValueError("A21 output must stay outside the repository")
    locked_r3 = locked_r3_scorecard_report()
    if not locked_r3["matched"]:
        raise RuntimeError(f"immutable R3 scorecard hash mismatch: {locked_r3}")
    intrusion_reports = [gameplay_intrusion_report(lod) for lod in range(3)]
    if not all(report["passed"] for report in intrusion_reports):
        raise RuntimeError(f"A21 route/spawn/camera intrusion: {intrusion_reports}")
    views_dir = output_dir / "views"
    assets_dir = output_dir / "assets"
    views_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    if view_indices is None:
        for stale in views_dir.glob("*.png"):
            stale.unlink()

    contract = canonical_contract_report(layout_path)
    if not contract["allMatched"]:
        raise RuntimeError(f"canonical Nakaniwa contract drift: {contract}")
    selected = (
        set(range(len(PROOF_CAMERAS))) if view_indices is None else set(view_indices)
    )
    invalid = sorted(selected - set(range(len(PROOF_CAMERAS))))
    if invalid:
        raise ValueError(f"invalid proof view indices: {invalid}")

    lod_artifacts = []
    evidence_paths: list[str] = []
    for lod in range(3):
        _reset_scene()
        scene = _configure_scene()
        root = bpy.data.collections.new(f"{TARGET_COLLECTION}_LOD{lod}")
        scene.collection.children.link(root)
        geometry = bpy.data.collections.new(f"HB_NAKANIWA_A21_GEOMETRY_LOD{lod}")
        cameras = bpy.data.collections.new("HB_NAKANIWA_A21_CAMERAS")
        lighting = bpy.data.collections.new("HB_NAKANIWA_A21_LIGHTING")
        root.children.link(geometry)
        root.children.link(cameras)
        root.children.link(lighting)
        materials = _make_blender_materials()
        builder = A21MeshBuilder(geometry, materials)
        specs = emit_to_builder(builder, lod, DEFAULT_INTEGRATION_MATERIAL_MAP)
        objects = builder.flush()
        evaluated_triangles = _triangle_count(objects)
        budget = LOD_BUDGETS[lod]
        if not (
            budget["minEvaluatedTriangles"]
            <= evaluated_triangles
            <= budget["maxEvaluatedTriangles"]
        ):
            raise RuntimeError(
                f"LOD{lod} evaluated triangles {evaluated_triangles} "
                f"outside {budget}"
            )
        if len(materials) > budget["maxMaterials"]:
            raise RuntimeError(f"LOD{lod} material budget exceeded")
        if len(specs) > budget["maxSpecs"]:
            raise RuntimeError(f"LOD{lod} spec budget exceeded")

        if lod == 0:
            _add_world_and_lights(lighting)
            camera_objects = {}
            for index, camera_spec in enumerate(PROOF_CAMERAS):
                camera = _make_camera(cameras, camera_spec)
                camera_objects[str(camera_spec["name"])] = camera
                if index not in selected:
                    continue
                scene.camera = camera
                slug = str(camera_spec["name"]).removeprefix(
                    "CAM_Nakaniwa_A21_"
                ).lower()
                path = views_dir / f"{index:02d}_{slug}.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                evidence_paths.append(str(path))
            scene.camera = camera_objects[MAIN_REFERENCE_CAMERA["name"]]

        blend_path = assets_dir / f"nakaniwa-a21-lod{lod}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        glb_path = assets_dir / f"nakaniwa-a21-lod{lod}.glb"
        bpy.ops.export_scene.gltf(
            filepath=str(glb_path),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6,
            export_cameras=False,
            export_lights=False,
            export_yup=True,
        )
        lod_artifacts.append({
            "lod": lod,
            "specCount": len(specs),
            "plannedTriangles": estimated_triangles(specs),
            "evaluatedTriangles": evaluated_triangles,
            "materialCount": len(materials),
            "drawCallEstimate": len(objects),
            "blend": _write_sha_artifact(blend_path),
            "glb": _write_sha_artifact(glb_path),
        })

    scorecard = independent_baseline_scorecard(evidence_paths)
    scorecard_path = output_dir / "independent-baseline-carry-forward.json"
    scorecard_path.write_text(
        json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    view_artifacts = []
    render_hasher = hashlib.sha256()
    for evidence in evidence_paths:
        artifact = _write_sha_artifact(Path(evidence))
        artifact["resolution"] = [1280, 720]
        view_artifacts.append(artifact)
        render_hasher.update(Path(evidence).name.encode("utf-8"))
        render_hasher.update(bytes.fromhex(artifact["sha256"]))
    source_path = Path(__file__).resolve()
    manifest = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "kitVersion": KIT_VERSION,
        "sourcePath": str(source_path),
        "sourceSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "reference": {"path": str(REFERENCE_PATH), "sha256": REFERENCE_SHA256},
        "lockedIndependentR3Scorecard": locked_r3,
        "canonicalContract": contract,
        "exactLandmarkCount": 2,
        "landmarkIds": [item["id"] for item in LANDMARKS],
        "mainReferenceCamera": MAIN_REFERENCE_CAMERA,
        "heroFrameMetrics": reference_camera_frame_metrics(0),
        "gameplayIntrusionReports": intrusion_reports,
        "lodPlanMetrics": [plan_metrics(lod) for lod in range(3)],
        "lodArtifacts": lod_artifacts,
        "materialCount": len(MATERIALS),
        "roleSpecificBakedGeometry": {
            "macroStoneChamferM": [0.10, 0.20],
            "carvedFrameChamferM": [0.03, 0.08],
            "railRibRadiusM": [0.01, 0.035],
            "globalPostMergeBevel": False,
            "curvedMembers": "swept mesh",
            "foliage": "branch hierarchy plus deterministic leaf-card clusters",
        },
        "conservatoryGlassDiagnostics": {
            "lod0WeatheredRoofCells": plan_metrics(0)["roleCounts"][
                "a21-conservatory-dirty-glass-cell"
            ],
            "lod0InsetHighlightLayers": plan_metrics(0)["roleCounts"][
                "a21-conservatory-tinted-glass-highlight-layer"
            ],
            "lod0CameraFacingFanCells": plan_metrics(0)["roleCounts"][
                "a21-conservatory-camera-facing-glass-fan-cell"
            ],
            "baseAlpha": MATERIALS["dirty_glass"]["alpha"],
            "highlightAlpha": MATERIALS["glass_highlight"]["alpha"],
            "transmissionWeight": MATERIALS["dirty_glass"]["transmission"],
            "backfaceCulling": False,
            "closedPanelSolids": True,
            "panelFacesPerCell": 6,
        },
        "views": evidence_paths,
        "viewArtifacts": view_artifacts,
        "renderSetSha256": render_hasher.hexdigest(),
        "renderedViewIndices": sorted(selected),
        "independentBaselineScorecard": str(scorecard_path),
        "independentSourceScorecard": str(INDEPENDENT_SCORECARD_R3_PATH),
        "selfRejectHistory": list(SELF_REJECT_HISTORY),
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_NEW_INDEPENDENT_REVIEW",
        "releaseMutation": False,
        "runtimeCollisionMutation": False,
        "publicAssetMutation": False,
    }
    manifest_path = output_dir / "proof-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["manifest"] = str(manifest_path)
    return manifest


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    arguments = list(argv)
    if "--" in arguments:
        arguments = arguments[arguments.index("--") + 1:]
    parser = argparse.ArgumentParser(
        description="Build private Nakaniwa A21 production art"
    )
    parser.add_argument("--layout", type=Path, default=CANONICAL_LAYOUT_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=PRIVATE_PRODUCTION_DEFAULT)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument(
        "--view-indices", default="",
        help="comma-separated private proof views; default renders all eight",
    )
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.plan_only:
        print(json.dumps({
            "kitVersion": KIT_VERSION,
            "canonicalContract": canonical_contract_report(args.layout),
            "lodMetrics": [plan_metrics(lod) for lod in range(3)],
            "heroFrameMetrics": reference_camera_frame_metrics(0),
            "independentBaselineScorecard": independent_baseline_scorecard(),
        }, ensure_ascii=False, indent=2))
        return 0
    try:
        import bpy  # type: ignore  # noqa: F401
    except ImportError:
        print(json.dumps({
            "kitVersion": KIT_VERSION,
            "lodMetrics": [plan_metrics(lod) for lod in range(3)],
            "heroFrameMetrics": reference_camera_frame_metrics(0),
        }, ensure_ascii=False, indent=2))
        return 0
    view_indices = None
    if args.view_indices.strip():
        view_indices = tuple(
            int(item) for item in args.view_indices.split(",") if item.strip()
        )
    manifest = build_private_production(
        args.output_dir, args.layout, view_indices
    )
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
    "PRIVATE_PRODUCTION_DEFAULT",
    "PROOF_CAMERAS",
    "build_private_production",
    "build_specs",
    "canonical_contract_report",
    "emit_specs_to_builder",
    "emit_to_builder",
    "estimated_triangles",
    "gameplay_intrusion_report",
    "independent_baseline_scorecard",
    "locked_r3_scorecard_report",
    "plan_metrics",
    "producer_provisional_scorecard",
    "reference_camera_frame_metrics",
    "spec_bounds",
]


if __name__ == "__main__":
    raise SystemExit(main())
