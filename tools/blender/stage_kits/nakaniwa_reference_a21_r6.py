#!/usr/bin/env python3
"""Private A21 R6 production-art rebuild for Nakaniwa.

Production brief
----------------
Nakaniwa is a dense palace-garden city at one Blender metre per runtime metre.
The immutable 320 m bounds, 16 m cross roads, spawns, landmark footprints,
entrances, approaches and collision templates remain sourced from A20's
canonical contract.  The ImageGen concept is a modelling reference only.

The locked 1.65 m view composes a low, open bridge/canal progression axis,
the complete Crowned Water Palace on frame-left, all five Fan-Glass
Conservatory vaults on frame-right, and a tall real-geometry garden district
behind both.  Near trees, lamps and planters are restricted to the frame edges.

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
``/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6``.  It never
edits public assets, runtime source, manifests, A20, the immutable R3 proof,
the immutable R4/R5 source/evidence, or a visible Blender session.  The
independently fixed R4 score of 4.22/10 remains controlling after this rebuild;
the release decision remains NO-SHIP until a different reviewer signs a new
fixed ten-category scorecard.
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
KIT_VERSION = "nakaniwa-reference-a21-production-r6"
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/nakaniwa-reference-v1.png"
REFERENCE_SHA256 = "c0b3bec12431c264ebe04a0757ea67eb521eab2c4e32e004da88cf6e6eebe15d"
R3_PRODUCTION_ROOT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art"
)
PRIVATE_PRODUCTION_DEFAULT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6"
)
R4_SOURCE_PATH = (
    REPO_ROOT / "tools/blender/stage_kits/nakaniwa_reference_a21.py"
)
R4_SOURCE_SHA256 = (
    "0525f614f0c4953a1dfae48093ef1401cccb4f75557bca817dff539b91b13b5b"
)
R4_PRODUCTION_ROOT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r4"
)
R4_CANDIDATE_PATH = R4_PRODUCTION_ROOT / "views/00_eye165_dualhero.png"
R4_CANDIDATE_SHA256 = (
    "f1c33f545c68e394bca9b0eab0beb93793f022066fbcad377b92d23a38635556"
)
R4_MANIFEST_PATH = R4_PRODUCTION_ROOT / "proof-manifest.json"
R4_MANIFEST_SHA256 = (
    "4db6c9d4d827e9de5bf36f2fe6b65b53eb1bfa8f4e03554c23acb9016270abd4"
)
R4_INDEPENDENT_REVIEW_PATH = (
    R4_PRODUCTION_ROOT / "independent-original-resolution-review.json"
)
R4_INDEPENDENT_REVIEW_SHA256 = (
    "8e360e66b8799f58e737f9cd031aeacc5a20a2073ff5b68dd2b356a1840823fd"
)
R5_SOURCE_PATH = (
    REPO_ROOT / "tools/blender/stage_kits/nakaniwa_reference_a21_r5.py"
)
R5_SOURCE_SHA256 = (
    "2005db9653850cfa9837f22fb82435d11cec48bebb3724a154c460da1f6b9593"
)
R5_TEST_PATH = REPO_ROOT / "tools/blender/test_nakaniwa_reference_a21_r5.py"
R5_TEST_SHA256 = (
    "7df190f799a305d535e3213b90b9ef1085ea4f465096128a5fab1844b0e30437"
)
R5_PRODUCTION_ROOT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r5"
)
R5_CANDIDATE_PATH = R5_PRODUCTION_ROOT / "views/00_eye165_dualhero.png"
R5_CANDIDATE_SHA256 = (
    "7cc5ffa407efd3a60a0c22b8fa0e85a5912971ede4628961c33412858f8ffd24"
)
R5_MANIFEST_PATH = R5_PRODUCTION_ROOT / "proof-manifest.json"
R5_MANIFEST_SHA256 = (
    "72f1b5d9ee329b856370093eee21cdf8abe890057a171a81f58669bbc0d45a64"
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
        "color": (0.040, 0.048, 0.044, 1.0),
        "roughness": (0.10, 0.30), "metallic": 0.03,
        "noiseScale": 1.15, "detailScale": 30.0, "bump": 0.065,
    },
    "ivory_stone": {
        "color": (0.56, 0.48, 0.38, 1.0),
        "roughness": (0.28, 0.56), "metallic": 0.0,
        "noiseScale": 0.34, "detailScale": 33.0, "bump": 0.105,
    },
    "carved_stone": {
        "color": (0.25, 0.22, 0.18, 1.0),
        "roughness": (0.38, 0.72), "metallic": 0.0,
        "noiseScale": 0.68, "detailScale": 43.0, "bump": 0.115,
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
        "color": (0.060, 0.180, 0.185, 0.22),
        "roughness": (0.025, 0.10), "metallic": 0.02,
        "transmission": 0.92, "alpha": 0.22, "ior": 1.45,
        "emission": (0.0, 0.010, 0.013, 1.0), "emissionStrength": 0.035,
        "noiseScale": 1.6, "detailScale": 56.0, "bump": 0.012,
    },
    "glass_highlight": {
        "color": (0.10, 0.30, 0.31, 0.10),
        "roughness": (0.018, 0.075), "metallic": 0.03,
        "transmission": 0.90, "alpha": 0.10, "ior": 1.45,
        "emission": (0.0, 0.018, 0.022, 1.0), "emissionStrength": 0.045,
        "noiseScale": 3.2, "detailScale": 62.0, "bump": 0.007,
    },
    "water": {
        "color": (0.002, 0.020, 0.030, 1.0),
        "roughness": (0.28, 0.48), "metallic": 0.02,
        "transmission": 0.01, "alpha": 1.0, "ior": 1.333,
        "noiseScale": 0.62, "detailScale": 46.0, "bump": 0.055,
    },
    "dark_wood": {
        "color": (0.075, 0.030, 0.014, 1.0),
        "roughness": (0.35, 0.62), "metallic": 0.0,
        "noiseScale": 4.0, "detailScale": 45.0, "bump": 0.08,
    },
    "foliage_dark": {
        "color": (0.016, 0.120, 0.030, 1.0),
        "roughness": (0.46, 0.68), "metallic": 0.0,
        "noiseScale": 5.0, "detailScale": 30.0, "bump": 0.035,
        "subsurface": 0.15,
    },
    "foliage_light": {
        "color": (0.075, 0.335, 0.055, 1.0),
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
    {"id": "a21-r5-palace-keep-crown", "a": "palace-central-keep",
     "aFace": "shoulder",
     "b": "a21-r5-palace-rooted-crown-keep-shoulder", "bFace": "inside",
     "axis": "volume", "overlapM": 5.20},
    {"id": "a21-r5-palace-keep-petal",
     "a": "a21-r5-palace-rooted-crown-keep-shoulder",
     "aFace": "front-shoulder",
     "b": "a21-r5-palace-overlapping-vertical-petal", "bFace": "root",
     "axis": "surface", "overlapM": 1.10},
    {"id": "a21-r5-palace-petal-spine",
     "a": "a21-r5-palace-overlapping-vertical-petal", "aFace": "centre",
     "b": "a21-r5-palace-fine-petal-spine", "bFace": "inside",
     "axis": "surface", "overlapM": 0.09},
    {"id": "a21-r5-palace-terrace-loggia",
     "a": "a21-r5-palace-lower-water-loggia-deep-terrace-slab",
     "aFace": "top",
     "b": "a21-r5-palace-lower-water-loggia-grounded-carved-column",
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
    {"id": "a21-r5-bridge-step-deck",
     "a": "a21-r5-bridge-approach-step", "aFace": "top",
     "b": "garden-bridge-deck", "bFace": "threshold",
     "axis": "route", "overlapM": 0.24},
    {"id": "a21-r5-conservatory-base-rib",
     "a": "a21-r5-conservatory-open-entry-base", "aFace": "top",
     "b": "conservatory-curved-primary-rib", "bFace": "spring",
     "axis": "surface", "overlapM": 0.12},
    {"id": "a21-district-roof", "a": "district-occupied-facade", "aFace": "top",
     "b": "district-garden-roof", "bFace": "bottom", "axis": "y", "overlapM": 0.10},
)

MAIN_REFERENCE_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_DualHero",
    "location": (121.93, PLAYER_EYE_M, -130.21),
    "target": (-5.0, 30.0, -4.0),
    "lensMm": 23.0,
    "sensorWidthMm": 36.0,
    "resolution": (1280, 720),
    "eyeHeightM": PLAYER_EYE_M,
    "intent": (
        "uncropped palace and five vaults above an open bridge-canal axis; "
        "foreground vertical mass below thirty percent"
    ),
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
    {
        "iteration": 10,
        "evidence": str(R4_CANDIDATE_PATH),
        "sha256": R4_CANDIDATE_SHA256,
        "verdict": "PRODUCER_REJECTED_R4_PRIMARY_BELOW_VISUAL_THRESHOLD",
        "reasons": [
            "low-information paving occupied roughly the lower 45 percent",
            "palace still read as wood-coloured cylinders and stacked boxes",
            "its crown read as a paper tooth row rather than rooted petals",
            "conservatory shells were hidden by cylindrical foreground turrets",
            "far horizon ended in open sky instead of dense garden-city depth",
        ],
        "correctiveActions": [
            "compose foreground from canal, bridge, steps, planting and story",
            "replace visible palace proxies with white occupied terrace architecture",
            "build one rooted overlapping vertical-petal crown with fine spires",
            "clear the five shells and expose ribs, glass, trees and warm walks",
            "close the horizon with real layered arcades, towers and vegetation",
        ],
    },
    {
        "iteration": 11,
        "evidence": str(R5_CANDIDATE_PATH),
        "sha256": R5_CANDIDATE_SHA256,
        "verdict": "PRODUCER_REJECTED_R5_FOREGROUND_OCCLUSION",
        "reasons": [
            "a giant central planter wall and tree hid the palace terraces",
            "near lanterns and foliage dominated more than half the lower frame",
            "R3 pavilion roofs floated in front of the conservatory glazing",
            "coverage-only metrics ignored foreground occlusion and hero cropping",
            "pale stone and broad fill erased bevel, roughness and contact response",
        ],
        "correctiveActions": [
            "move the player-height camera back and use a 23 mm lens",
            "reserve the centre for the bridge, canal and complete hero silhouettes",
            "remove the R3 pavilion roof family and all near central tree masses",
            "measure full-frame containment and depth-aware hero occlusion",
            "restore warm directional shadow, darker stone and visible relief",
        ],
    },
    {
        "iteration": 12,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-0/views/00_eye165_dualhero.png"
        ),
        "sha256": "f274818da36706fb26fee5820e7e178245345843af2ba8d6f29b8998f22d2106",
        "verdict": "PRODUCER_REJECTED_R6_SMALL_CROWN_COOL_LIGHT",
        "reasons": [
            "the central route and both landmarks were finally unobstructed",
            "the palace flower crown remained too short against the sky",
            "foreground paving still exceeded the thirty-percent visual target",
            "neutral light weakened limestone relief and late-afternoon identity",
        ],
        "correctiveActions": [
            "fill the rooted seven-petal crown to the canonical 43 m envelope",
            "tilt the 1.65 m camera upward while retaining the 23 mm lens",
            "move only five metres forward to keep hero detail readable",
            "warm the stone palette and strengthen the low directional sun",
        ],
    },
    {
        "iteration": 13,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-1/views/00_eye165_dualhero.png"
        ),
        "sha256": "ab05a67826157617def5459c3b4f3cd1d50ac3119999d39f1641551df3ad8c6c",
        "verdict": "PRODUCER_REJECTED_R6_EMPTY_PAVING_TOOTH_CROWN",
        "reasons": [
            "both exclusive heroes and the open centre route read clearly",
            "the lower frame remained dominated by undifferentiated paving",
            "the palace crown still read as opaque teeth over block masses",
            "canal, bridge, vegetation and occupied edge story remained weak",
            "stone relief and warm atmospheric separation stayed below reference",
        ],
        "correctiveActions": [
            "keep the complete dual-hero framing and clear centre sightline",
            "fill only the lower edges with low gardens, flowers and balustrades",
            "extend paired reflecting canals and a readable bridge to the camera",
            "open the crown into a tall transparent seven-petal lattice",
            "increase limestone relief, glass-metal separation and warm key light",
        ],
    },
    {
        "iteration": 14,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-2/views/00_eye165_dualhero.png"
        ),
        "sha256": "aab5310e134b35582d122ff1f7972c966424741cd237140590337ee9852cdec0",
        "verdict": "PRODUCER_REJECTED_R6_WHITE_WATER_INVISIBLE_CROWN",
        "reasons": [
            "low planted edges now framed the route without blocking either hero",
            "paired foreground basins read as flat white slabs rather than water",
            "the crossing remained a thin threshold instead of a garden bridge",
            "transparent petals disappeared because their structural ribs were thin",
            "the crown base remained a rectangular mass behind the open lattice",
        ],
        "correctiveActions": [
            "darken water, reduce sky coat and add a visible submerged stone bed",
            "raise the crossing slightly and articulate its edge with three arches",
            "thicken crown stone and brass edges and add transverse petal ribs",
            "replace the single crown-base box with stepped occupied ledges",
            "make the two edge trees fuller while keeping them outside the centre",
        ],
    },
    {
        "iteration": 15,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-3/views/00_eye165_dualhero.png"
        ),
        "sha256": "30e5b711f751555bc4bbd3db6914c995ad0d0e4b70d14aaf27abb2fcb56091c2",
        "verdict": "PRODUCER_REJECTED_R6_WIREFRAME_CROWN_FLAT_WATER",
        "reasons": [
            "segmented canals, bridge stairs and the clear route now composed well",
            "water remained pale and flat instead of dark and reflective",
            "five petals read as wire outlines rather than monumental shells",
            "blank sky and low palace mass weakened castle-scale hierarchy",
            "district material, vegetation and occupied lighting stayed blockout-like",
        ],
        "correctiveActions": [
            "use thick opaque stone-metal petal shells around internal glass",
            "add a supported vertical tower, deeper terraces and warm window rhythm",
            "lower water specular response and strengthen contact-dark stone banks",
            "layer real roofed façades and planted silhouettes through the midground",
            "increase edge-only canopy density and directional warm-shadow contrast",
        ],
    },
    {
        "iteration": 16,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-4/views/00_eye165_dualhero.png"
        ),
        "sha256": "0b805ac8316d4749024d07f5432d9285b0af2c2f8d640baf26c746574b65643c",
        "verdict": "PRODUCER_REJECTED_R6_THIN_CROWN_SPARSE_SKYLINE",
        "reasons": [
            "dark segmented water and bridge depth finally read from eye height",
            "the conservatory carried a strong five-vault silhouette",
            "palace petals remained skeletal trusses instead of massive shells",
            "short generic background blocks left an oversized blank sky field",
            "the palace and district still lacked castle-city vertical hierarchy",
        ],
        "correctiveActions": [
            "wrap each petal in paired opaque stone wings around a glass core",
            "retain brass inlays while thickening the crown silhouette",
            "raise the existing occupied garden-city houses and roof rhythm",
            "add taller planted gables and balcony bands behind the clear route",
            "preserve the locked player-height camera and both hero envelopes",
        ],
    },
    {
        "iteration": 17,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-5/views/00_eye165_dualhero.png"
        ),
        "sha256": "34d96e55af54e5a30f838ba4cf4765a96665470d2144decf640a1dc6355a0bef",
        "verdict": "PRODUCER_REJECTED_R6_PALE_MATERIAL_LOW_PALACE_HIERARCHY",
        "reasons": [
            "opaque petal wings and taller occupied roofs improved the skyline",
            "the palace still read lower and less massive than the conservatory",
            "broad pale stone faces flattened carved relief and terrace depth",
            "cool broad fill weakened the intended late-afternoon hierarchy",
            "roof gardens and planted skyline silhouettes remained too small",
        ],
        "correctiveActions": [
            "narrow the crown glass cores so paired stone wings carry the silhouette",
            "strengthen petal perimeter thickness without exceeding the 43 m lock",
            "darken and separate ivory, carved and wet stone material values",
            "lower the sun and rebalance warm key against reduced cool fill",
            "enlarge grounded roof gardens behind the two clear hero envelopes",
        ],
    },
    {
        "iteration": 18,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-6/views/00_eye165_dualhero.png"
        ),
        "sha256": "64d803dcf8c9371bd5ccd8bc8628ed9849d3b0e774c0b827c19bcbad64b2902f",
        "verdict": "PRODUCER_REJECTED_R6_TRIANGULAR_CROWN_EMPTY_SKY",
        "reasons": [
            "grounded side towers finally gave the palace vertical hierarchy",
            "warm light and darker stone improved terrace and water separation",
            "the pointed crown still read as triangular roof trusses",
            "straight four-point edges prevented a botanical petal silhouette",
            "the uniform upper sky retained too much low-information area",
        ],
        "correctiveActions": [
            "replace straight petal shoulders with broader multi-point curves",
            "make the main petal shells opaque around narrow inset glass cores",
            "add a third structural cross-rib without increasing LOD2 cost",
            "retain the new side towers, water, bridge and clear dual-hero view",
            "add procedural directional cloud breakup without a raster matte",
        ],
    },
    {
        "iteration": 19,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-7/views/00_eye165_dualhero.png"
        ),
        "sha256": "c526d97cfa6cb0de246140250ea80a3404f3f6745c8f41ec6f9f3db612f022da",
        "verdict": "PRODUCER_REJECTED_R6_OCCLUDED_PETAL_ROOTS_GENERIC_MIDGROUND",
        "reasons": [
            "nine-point opaque petals improved the crown edge silhouette",
            "the petal roots remained hidden behind the forward keep facade",
            "the crown therefore still read as small roof ornamentation",
            "freestanding midground towers retained a generic box cadence",
            "procedural world noise produced haze but no readable cloud layers",
        ],
        "correctiveActions": [
            "bring the monumental petal shell in front of the occupied keep",
            "retain narrow glass cores and all warm occupied loggia depth",
            "join midground towers into garden terraces and inhabited bridges",
            "shape directional procedural cloud bands with stronger contrast",
            "preserve both hero sightlines, the canal axis and all production gates",
        ],
    },
    {
        "iteration": 20,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-8/views/00_eye165_dualhero.png"
        ),
        "sha256": "b1ba964e5132cc107a6cdf56798fecf5876731a1b6714ec7c3b8776b03e9a178",
        "verdict": "PRODUCER_REJECTED_R6_OVERPOWERING_DARK_CLOUDS_GREEN_MONOLITHS",
        "reasons": [
            "forward petal roots created the first castle-scale crown silhouette",
            "transparent cores retained glimpses of the occupied keep",
            "garden skybridges began to connect the middle district",
            "the procedural cloud mix rendered as dominant near-black bands",
            "moss-colored lower houses still read as generic green monoliths",
        ],
        "correctiveActions": [
            "retain the forward five-petal fan and its clear landmark silhouette",
            "lighten cloud bands with additive warm dusk breakup",
            "replace moss structural walls with deliberately contrasted stone",
            "add vertical occupied bays and planted relief to lower houses",
            "keep water, conservatory, bridge axis and performance locks unchanged",
        ],
    },
    {
        "iteration": 21,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-9/views/00_eye165_dualhero.png"
        ),
        "sha256": "101ba32c5b9688935218bfa483a12ba22a18bd008e89f325871579c370f930d5",
        "verdict": "PRODUCER_REJECTED_R6_BLANK_PALACE_MIDDLE_FACADE",
        "reasons": [
            "soft horizontal dusk layers restored readable atmospheric depth",
            "stone lower houses and occupied windows removed the green monoliths",
            "the forward lotus fan retained a strong stage-exclusive silhouette",
            "the palace middle wall remained a broad unoccupied striped block",
            "foreground planting stayed too small to balance the hard canal planes",
        ],
        "correctiveActions": [
            "spend reclaimed distant bridge triangles on the palace hero facade",
            "add deep vertical occupied windows and carved structural buttresses",
            "add planted window sills without narrowing the clear route",
            "retain the current sky, water, conservatory and connected skyline",
            "verify the facade at both full frame and palace crop scale",
        ],
    },
    {
        "iteration": 22,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-10/views/00_eye165_dualhero.png"
        ),
        "sha256": "c07a1d0afb6821f76617011559ac3fd68c48f0a1c660bcafb95f1423f4b5ecd2",
        "verdict": "PRODUCER_REJECTED_R6_INVISIBLE_FACADE_DETAIL_DEPTH",
        "reasons": [
            "all static and evaluated production budgets remained valid",
            "the intended occupied middle facade was unchanged in the render",
            "projection inspection located the new windows behind the legacy wing",
            "the nearest blank upper-wing face was roughly thirty metres forward",
            "spending geometry behind an opaque hero wall added no visible quality",
        ],
        "correctiveActions": [
            "bind the windows directly to the measured visible upper-wing face",
            "use the camera-facing positive-X wall at the verified depth",
            "retain the same triangle allocation and planted sill rhythm",
            "confirm visibility in a palace crop before any further detail pass",
            "preserve the immutable corrected dusk snapshot and all technical gates",
        ],
    },
    {
        "iteration": 23,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-11/views/00_eye165_dualhero.png"
        ),
        "sha256": "9a78843c43b9c0a5a0a6eb910554a8746fb195343811eb42a8bce07bc97ea763",
        "verdict": "PRODUCER_REJECTED_R6_SQUAT_FAN_CROWN_REFERENCE_SILHOUETTE",
        "reasons": [
            "measured facade placement made the occupied middle windows visible",
            "the palace crop gained human-scale vertical rhythm and warm interiors",
            "the reference palace remains a tall centralized occupied castle",
            "the candidate petals spread laterally into a low folded fan",
            "the broad fan weakened the hero hierarchy and preserved excess sky",
        ],
        "correctiveActions": [
            "apply one reference-first macro hypothesis to the petal placement",
            "reduce lateral lean and aggregate crown width without changing count",
            "retain the 43 metre top lock and the forward rooted shell",
            "judge the fixed-camera preview before any material or garden change",
            "compare frame ratio, both heroes and identity directly to the reference",
        ],
    },
    {
        "iteration": 24,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-12/views/00_eye165_dualhero.png"
        ),
        "sha256": "4478131c986584418bfbf3418415c883876d49f2f27369785c3b2f4d111339ce",
        "verdict": "PRODUCER_REJECTED_R6_NARROW_PETALS_DENSE_SLAB_CLUSTER",
        "reasons": [
            "the crown became narrower and marginally more vertical",
            "frame occupancy and the excessive sky ratio barely changed",
            "overlapping opaque petals collapsed into a dense slab cluster",
            "the occupied central tower remained visually subordinate",
            "architectural grammar and human scale did not improve",
        ],
        "correctiveActions": [
            "restore the prior wider rooted petal baseline",
            "test only the measured camera-side upper-wing occluder",
            "reveal the existing detailed twenty-eight metre central keep",
            "remove the occluder's dependent facade decoration with it",
            "render and judge this single macro change before any other work",
        ],
    },
    {
        "iteration": 25,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-13/views/00_eye165_dualhero.png"
        ),
        "sha256": "afe4230281418c6e54e43b570cf308290d54edbac6b65fddad855322a694c104",
        "verdict": "PRODUCER_REJECTED_R6_REMOVED_WING_EXPOSED_SKELETON",
        "reasons": [
            "the camera-facing upper wing was confirmed as a major foreground mass",
            "its removal exposed warm occupied framework and reduced triangles",
            "the existing central keep still failed to dominate the fixed frame",
            "the palace lost solidity and read as a low open skeleton",
            "sky ratio, hero height and reference identity did not improve",
        ],
        "correctiveActions": [
            "retain the exposed space for one controlled macro mass test",
            "place only a three-tier central keep directly below the crown",
            "avoid windows, material tuning and garden detail in this iteration",
            "judge continuous vertical silhouette before adding any microdetail",
            "archive immediately if the three-tier mass remains generic or squat",
        ],
    },
    {
        "iteration": 26,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-14/views/00_eye165_dualhero.png"
        ),
        "sha256": "0c38c078f9dc3b08a77ba088f1c05478e774d193629f398b3181590aaa52bb63",
        "verdict": "PRODUCER_REJECTED_R6_SOLID_BOX_KEEP_OCCLUDED_CROWN",
        "reasons": [
            "the three-tier keep increased central vertical frame occupancy",
            "the new mass aligned beneath the lotus crown as intended",
            "its solid carved faces read as one dominant blank brown box",
            "the forward mass obscured crown roots and occupied framework",
            "architectural grammar, material value and identity regressed",
        ],
        "correctiveActions": [
            "preserve the tested height and footprint only",
            "replace solid tiers with an open load-bearing frame",
            "use three piers, four floor bands and recessed occupied planes",
            "leave lighting, materials, gardens and all other geometry untouched",
            "judge the single open-frame hypothesis in the fixed camera",
        ],
    },
    {
        "iteration": 27,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-15/views/00_eye165_dualhero.png"
        ),
        "sha256": "13b7472455d206037cd799ccd44f4ee0ac5f443aef301984e25f246eee52649a",
        "verdict": "PRODUCER_REJECTED_R6_OPEN_FRAME_ABSORBED_BY_LOW_FAN",
        "reasons": [
            "the open frame removed the prior blank-box occlusion",
            "the recessed occupied planes remained subordinate in the fixed view",
            "the frame was visually absorbed by the broad low lotus fan",
            "the palace still lacked a tall centralized occupied silhouette",
            "all eight reference-comparison aspects remained below the target",
        ],
        "correctiveActions": [
            "restore the last known visible-facade baseline before a new batch",
            "measure projected palace and conservatory envelopes in camera space",
            "solve the tall central occupied silhouette as one isolated hypothesis",
            "do not spend triangles on materials, lighting or garden microdetail",
            "render immediately and retain only a measurable macro improvement",
        ],
    },
    {
        "iteration": 28,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-17/views/00_eye165_dualhero.png"
        ),
        "sha256": "23c82e3a81ea9e14f2d39733846235fdb82a0d5d26b2b70ff29212427b203ce2",
        "verdict": "PRODUCER_REJECTED_R6_COMPACT_CROWN_FLOATING_ORIGAMI",
        "reasons": [
            "the compact petal spacing removed the prior oversized lateral fan",
            "the canonical top and forward camera-space advantage were retained",
            "thin stone wings collapsed into a small folded-origami bundle",
            "the crown floated above a dark shelf instead of completing a tower",
            "palace mass, occupied scale and stage-exclusive identity weakened",
        ],
        "correctiveActions": [
            "restore the accepted iteration-16 broad forward crown parameters",
            "retain the forward root position and fixed camera-space hierarchy",
            "solve only the occupied vertical base beneath the broad crown",
            "use stepped arcaded mass with visible warm windows and real contact",
            "judge the palace connection before any crown or material change",
        ],
    },
    {
        "iteration": 29,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-19/views/00_eye165_dualhero.png"
        ),
        "sha256": "eae11bf02329530f62044569de29ec4243bd3f2167aa6e0e48019ca268bc9e3f",
        "independentReview": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "independent-original-resolution-review-r6-iteration19-"
            "eae11bf0.json"
        ),
        "independentReviewSha256": (
            "d343b978d88f0f415f1b98a3c1a2d446785be351300390df5abd5591c48eebe5"
        ),
        "arithmeticMean": 2.99,
        "minimumScore": 2.4,
        "verdict": "INDEPENDENT_REJECTED_R6_VERTICAL_PALACE_OCCUPANCY",
        "reasons": [
            "the producer saw incremental crown support and spacing improvements",
            "the independent lower score therefore controls the release decision",
            "candidate sky occupancy was 43.4 percent versus 16.4 percent",
            "palace height was 36.4 percent versus the reference 56.9 percent",
            "the left core still read as a low fan over an open scaffold",
        ],
        "correctiveActions": [
            "replace only the palace central core with one vertical occupied stack",
            "broaden its lower tiers into the existing palace base",
            "move its top toward the nearest feasible palace-footprint envelope",
            "freeze camera, conservatory, materials, lighting and other geometry",
            "render and submit the next macro candidate to independent review",
        ],
    },
    {
        "iteration": 30,
        "evidence": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "self-reject/iteration-20/views/00_eye165_dualhero.png"
        ),
        "sha256": "eb33cba5dc67858eea488a4fa7eed6aaa42bdab3b025bc81e2bb1b03a799ba7a",
        "independentReview": (
            "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
            "independent-metric-review-r6-iteration20-eb33cba5.json"
        ),
        "independentReviewSha256": (
            "05089d2773b7f48f1b885da972de7601ea6c4e11bee2b53402e54669d79a35e9"
        ),
        "verdict": "INDEPENDENT_REJECTED_R6_VERTICAL_AMPLITUDE_INSUFFICIENT",
        "reasons": [
            "the new core lifted the palace apex by fifteen pixels",
            "palace height improved from 36.4 to 38.6 percent of the frame",
            "sky occupancy regressed from 43.38 to 43.91 percent",
            "global edge density regressed from 6.53 to 6.45 percent",
            "the core remained a detached edge tower rather than a central castle",
        ],
        "correctiveActions": [
            "stop repeating geometry-only height changes under the same constraints",
            "retain the immutable evidence for both bounded macro experiments",
            "request an explicit proof-camera or height-contract decision",
            "do not alter the live Blender UI while that decision is pending",
            "resume one-hypothesis work only after the governing constraint is chosen",
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
    vault_centres = (39.0, 46.0, 56.0, 66.0, 76.0)
    vault_x_centres = (25.0, 35.5, 52.0, 68.5, 79.0)
    vault_half_widths = (10.0, 17.5, 33.0, 18.0, 10.0)
    vault_rises = (23.0, 32.0, 43.2, 34.0, 25.0)
    vault_crown_biases = (1.2, 0.8, 0.0, -0.8, -1.2)
    vault_half_depths = (9.5, 13.0, 18.0, 14.0, 11.0)
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
                1.88, 8.7, 7.2, 0.14, 1,
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
                1.92, 7.8, 3.0, (0.13, 0.10, 0.08)[lod], 1,
            )
            _chamfer_box(
                specs, "a21-conservatory-camera-facing-stone-spring-cap",
                "ivory_stone", group,
                spring_x, 7.95, z0 + 1.85,
                1.82, 0.55, 3.55, (0.075, 0.060, 0.050)[lod], 1,
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
    # At lod == 0, nakaniwa_a23_reconciliation.materials.remap_ground retargets
    # this exact ground plate onto NAKANIWA_GROUND_TARGET_MATERIAL
    # ("moss_stone", which build_nakaniwa_reference_lod then maps to the
    # builder's "terrain" material) as part of its own lod==0-only pass -- see
    # that module's build_nakaniwa_a23_specs docstring. LOD1/2 never go
    # through that reconciliation pass and previously kept this plate on
    # "carved_stone" untouched, so build_all_stages.py's terrain-node release
    # gate (every LOD must own real "terrain"-tagged mesh; see
    # validate_dense_stage_assets.py's missing-real-mesh-horizon-terrain
    # check) failed at LOD1/2, and the ground silently changed material at the
    # LOD0->LOD1 transition distance. Tagging it "moss_stone" directly at the
    # source for lod > 0 reaches the identical "terrain" material through the
    # same city_material_map override build_nakaniwa_reference_lod already
    # applies unconditionally at every LOD, closing both gaps without
    # touching lod == 0's byte-identical reconciled output.
    _box(
        specs,
        "a21-r2-garden-city-weathered-stone-ground",
        "carved_stone" if lod == 0 else "moss_stone",
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


R5_VISUAL_BLOCKER_PREFIXES = (
    "a21-palace-companion",
    "a21-palace-crown-companion",
    "a21-palace-central-keep-upper-turret",
    "a21-palace-wing-garden-roof",
    "a21-palace-keep-roof",
    "a21-r4-palace-lower-water-loggia",
    "a21-r4-palace-upper-garden-loggia",
    "a21-r4-palace-rooted",
    "a21-r4-palace-ceremonial-gallery-stair",
    "a21-r4-palace-occupied-loggia-planter",
    "a21-r4-foreground-loggia",
    "a21-r3-mid-city-octagonal",
    "a21-r3-canal-destination",
    "a21-r2-district-deep-garden-arcade",
    "a21-r2-district-deep-side-garden-arcade",
    "a21-r2-district-shoulder",
    "a21-conservatory-monumental-entry-drum",
    "a21-conservatory-entry-drum",
    "a21-conservatory-occupied-glass-lantern",
    "a21-conservatory-monumental-entry-fan",
)


def _remove_r5_visual_blockers(specs: list[dict]) -> None:
    """Clear the R4 proxy silhouettes that hid the two final hero systems."""
    specs[:] = [
        spec
        for spec in specs
        if not any(
            str(spec["role"]).startswith(prefix)
            for prefix in R5_VISUAL_BLOCKER_PREFIXES
        )
    ]


def _r5_corridor_basis(t: float) -> tuple[float, float, float, float]:
    centre_x, centre_z = _corridor_point(t)
    ahead_x, ahead_z = _corridor_point(min(1.0, t + 0.01))
    forward_x = ahead_x - centre_x
    forward_z = ahead_z - centre_z
    forward_length = math.hypot(forward_x, forward_z)
    forward_x /= forward_length
    forward_z /= forward_length
    return forward_x, forward_z, forward_z, -forward_x


def _r5_corridor_quad(
    t: float,
    side: float,
    y: float,
    half_forward: float,
    half_side: float,
) -> tuple[tuple[float, float, float], ...]:
    centre_x, centre_z = _corridor_point(t, side)
    forward_x, forward_z, right_x, right_z = _r5_corridor_basis(t)
    return tuple(
        (
            centre_x + forward_x * along + right_x * across,
            y,
            centre_z + forward_z * along + right_z * across,
        )
        for along, across in (
            (-half_forward, -half_side),
            (half_forward, -half_side),
            (half_forward, half_side),
            (-half_forward, half_side),
        )
    )


def _add_r5_foreground_canal_route(specs: list[dict], lod: int) -> None:
    """Replace the paving-first foreground with water, steps and garden life."""
    group = "a21-r5-nakaniwa-bridge-first-foreground"
    stair_count = (7, 5, 4)[lod]
    for stair_index in range(stair_count):
        progress = stair_index / max(1, stair_count - 1)
        _panel(
            specs,
            "a21-r5-bridge-approach-step",
            "ivory_stone" if stair_index % 2 else "carved_stone",
            group,
            _r5_corridor_quad(
                0.158,
                -10.45 + progress * 4.55,
                0.23 + progress * 0.67,
                2.75 - progress * 0.22,
                0.72,
            ),
            (0.27, 0.23, 0.19)[lod],
        )
    _panel(
        specs,
        "a21-r5-bridge-approach-wet-landing",
        "wet_stone",
        group,
        _r5_corridor_quad(0.172, -5.65, 0.91, 2.65, 0.95),
        (0.24, 0.20, 0.16)[lod],
    )
    # Low beds hug the promenade edge, keeping the water and bridge visible.
    planter_sites = (
        (0.085, -14.25, 4.4),
        (0.205, -14.65, 5.1),
        (0.305, -13.55, 4.2),
    )
    for planter_index, (t, side, half_forward) in enumerate(
        planter_sites[: (3, 3, 2)[lod]]
    ):
        _panel(
            specs,
            "a21-r5-foreground-layered-limestone-planter",
            "carved_stone",
            group,
            _r5_corridor_quad(t, side, 0.70, half_forward, 1.65),
            (1.10, 0.92, 0.74)[lod],
        )
        _panel(
            specs,
            "a21-r5-foreground-wet-botanical-soil",
            "wet_stone",
            group,
            _r5_corridor_quad(t, side, 1.28, half_forward - 0.38, 1.30),
            0.12,
        )
        plant_count = (3, 2, 1)[lod]
        for plant_index in range(plant_count):
            centre_x, centre_z = _corridor_point(
                t - 0.022
                + plant_index * 0.044 / max(1, plant_count - 1),
                side,
            )
            _leaf_cluster(
                specs,
                "a21-r5-foreground-layered-flower-and-fern",
                (
                    "flower"
                    if (planter_index + plant_index) % 3 == 0
                    else "foliage_light"
                ),
                group,
                centre_x,
                1.68,
                centre_z,
                1.45,
                0.82,
                (30, 16, 8)[lod],
                34100 + planter_index * 10 + plant_index,
            )
    tree_x, tree_z = _corridor_point(0.235, -15.0)
    _tree(
        specs,
        group=group,
        role="a21-r5-foreground-pruned-flowering-tree",
        x=tree_x,
        z=tree_z,
        height=7.3,
        crown=3.0,
        lod=lod,
        seed=34220,
        flowering=True,
    )
    # An occupied maintenance bench and hand tools provide first-person scale.
    bench_x, bench_z = _corridor_point(0.115, -13.0)
    forward_x, forward_z, right_x, right_z = _r5_corridor_basis(0.115)
    _panel(
        specs,
        "a21-r5-gardener-bench-seat",
        "dark_wood",
        group,
        tuple(
            (
                bench_x + forward_x * along + right_x * across,
                0.88,
                bench_z + forward_z * along + right_z * across,
            )
            for along, across in (
                (-1.45, -0.34),
                (1.45, -0.34),
                (1.45, 0.34),
                (-1.45, 0.34),
            )
        ),
        0.16,
    )
    for along in (-1.15, 1.15):
        leg_x = bench_x + forward_x * along
        leg_z = bench_z + forward_z * along
        _sweep(
            specs,
            "a21-r5-gardener-bench-grounded-leg",
            "brass",
            group,
            (
                (
                    leg_x - right_x * 0.27,
                    0.14,
                    leg_z - right_z * 0.27,
                ),
                (
                    leg_x + right_x * 0.27,
                    0.86,
                    leg_z + right_z * 0.27,
                ),
            ),
            (0.055, 0.046, 0.037)[lod],
            (8, 6, 4)[lod],
        )
    for tool_index, along in enumerate((-0.68, 0.0, 0.68)):
        tool_x = bench_x + forward_x * along - right_x * 0.62
        tool_z = bench_z + forward_z * along - right_z * 0.62
        _sweep(
            specs,
            "a21-r5-gardener-hand-tool",
            "brass" if tool_index == 1 else "dark_wood",
            group,
            (
                (tool_x, 0.32, tool_z),
                (
                    tool_x + forward_x * 0.18,
                    1.82,
                    tool_z + forward_z * 0.18,
                ),
            ),
            (0.030, 0.025, 0.021)[lod],
            (7, 6, 4)[lod],
        )
    # Bridge lamps and lilies make the immediate foreground read as wet life.
    for bridge_side in (-5.75, 5.75):
        lamp_x, lamp_z = _corridor_point(0.18, bridge_side)
        _sweep(
            specs,
            "a21-r5-first-bridge-human-scale-lantern-post",
            "brass",
            group,
            ((lamp_x, 0.76, lamp_z), (lamp_x, 3.20, lamp_z)),
            (0.052, 0.043, 0.034)[lod],
            (8, 6, 4)[lod],
        )
        _chamfer_box(
            specs,
            "a21-r5-first-bridge-warm-lantern",
            "warm_glow",
            group,
            lamp_x,
            3.36,
            lamp_z,
            0.48,
            0.62,
            0.48,
            0.050,
            1,
        )
    for lily_index, (t, side) in enumerate(
        ((0.07, -1.7), (0.12, 1.4), (0.23, -1.1))
    ):
        if lily_index >= (3, 2, 1)[lod]:
            break
        lily_x, lily_z = _corridor_point(t, side)
        _leaf_cluster(
            specs,
            "a21-r5-foreground-water-lily-and-reflection",
            "flower" if lily_index == 1 else "foliage_light",
            group,
            lily_x,
            0.39,
            lily_z,
            1.45,
            0.10,
            (20, 11, 6)[lod],
            34300 + lily_index,
        )


def _add_r5_palace_system(specs: list[dict], lod: int) -> None:
    """Author the white occupied terrace palace and rooted petal keep."""
    group = PALACE_ID
    _add_r4_oriented_palace_gallery(
        specs,
        lod,
        centre_x=-24.0,
        centre_z=-67.0,
        length=63.0,
        base_y=1.35,
        spring_height=4.55,
        rise=2.65,
        bays=(10, 7, 5)[lod],
        role="a21-r5-palace-lower-water-loggia",
    )
    _add_r4_oriented_palace_gallery(
        specs,
        lod,
        centre_x=-29.0,
        centre_z=-64.0,
        length=53.0,
        base_y=9.05,
        spring_height=4.05,
        rise=2.55,
        bays=(8, 6, 4)[lod],
        role="a21-r5-palace-middle-garden-loggia",
    )
    _add_r4_oriented_palace_gallery(
        specs,
        lod,
        centre_x=-34.0,
        centre_z=-60.5,
        length=43.0,
        base_y=16.35,
        spring_height=3.55,
        rise=2.45,
        bays=(6, 5, 3)[lod],
        role="a21-r5-palace-upper-sky-loggia",
    )
    normal_x, normal_z = 0.985, -0.172
    tangent_x, tangent_z = 0.172, 0.985

    def palace_point(
        centre_x: float,
        centre_z: float,
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

    # Continuous supported balconies and broad stairs make every tier usable.
    for balcony_index, (centre_x, centre_z, length, y) in enumerate(
        (
            (-24.0, -67.0, 61.0, 8.95),
            (-29.0, -64.0, 51.0, 16.20),
            (-34.0, -60.5, 41.0, 22.55),
        )
    ):
        _panel(
            specs,
            "a21-r5-palace-continuous-supported-balcony",
            "ivory_stone",
            group,
            (
                palace_point(centre_x, centre_z, -length * 0.5, y, 0.20),
                palace_point(centre_x, centre_z, length * 0.5, y, 0.20),
                palace_point(centre_x, centre_z, length * 0.5, y, 1.85),
                palace_point(centre_x, centre_z, -length * 0.5, y, 1.85),
            ),
            (0.42, 0.34, 0.27)[lod],
        )
        _sweep(
            specs,
            "a21-r5-palace-continuous-balcony-handrail",
            "brass",
            group,
            (
                palace_point(
                    centre_x,
                    centre_z,
                    -length * 0.5,
                    y + 1.22,
                    1.72,
                ),
                palace_point(
                    centre_x,
                    centre_z,
                    length * 0.5,
                    y + 1.22,
                    1.72,
                ),
            ),
            (0.040, 0.033, 0.027)[lod],
            (8, 6, 4)[lod],
        )
        post_count = ((13, 10, 8), (9, 7, 5), (6, 5, 4))[lod][
            balcony_index
        ]
        for post_index in range(post_count):
            tangent_offset = -length * 0.5 + length * post_index / max(
                1,
                post_count - 1,
            )
            _sweep(
                specs,
                "a21-r5-palace-balcony-human-scale-baluster",
                "brass",
                group,
                (
                    palace_point(
                        centre_x,
                        centre_z,
                        tangent_offset,
                        y + 0.18,
                        1.72,
                    ),
                    palace_point(
                        centre_x,
                        centre_z,
                        tangent_offset,
                        y + 1.22,
                        1.72,
                    ),
                ),
                (0.029, 0.024, 0.020)[lod],
                (7, 6, 4)[lod],
            )
    stair_count = (10, 7, 5)[lod]
    for stair_index in range(stair_count):
        progress = stair_index / max(1, stair_count - 1)
        _chamfer_box(
            specs,
            "a21-r5-palace-broad-ceremonial-gallery-stair",
            "ivory_stone" if stair_index % 2 else "carved_stone",
            group,
            -26.0 + normal_x * (6.0 - progress * 8.0),
            0.22 + progress * 8.50,
            -42.0 + normal_z * (6.0 - progress * 8.0),
            9.4 - progress * 1.1,
            0.34,
            1.28,
            (0.050, 0.043, 0.036)[lod],
            1,
        )
    # A chamfered keep shoulder replaces the R4 cylinder and roots the crown.
    # Reference-first macro test: keep the complete occupied crown tower
    # connected as one assembly, but move it to the camera-facing limit of
    # the immutable palace footprint.  The fixed player camera then reads the
    # canonical 43 m top as a true hero height without changing the camera,
    # the gameplay layout, the conservatory, lighting, or material language.
    root_x, root_z = -36.0, -91.0
    shoulder_tiers = (
        (25.5, 34.0, 2.4, 22.0, "ivory_stone"),
        (28.7, 29.0, 2.1, 18.5, "carved_stone"),
        (31.6, 23.5, 1.9, 15.0, "ivory_stone"),
    )
    for tier_y, tier_width, tier_height, tier_depth, tier_material in (
        shoulder_tiers
    ):
        _chamfer_box(
            specs,
            "a21-r5-palace-rooted-crown-keep-shoulder",
            tier_material,
            group,
            root_x,
            tier_y,
            root_z,
            tier_width,
            tier_height,
            tier_depth,
            (0.18, 0.14, 0.10)[lod],
            2 if lod == 0 else 1,
        )
    if lod <= 1:
        for tower_index, tangent_offset in enumerate((-7.5, 7.5)):
            tower_x, _, tower_z = palace_point(
                root_x,
                root_z,
                tangent_offset,
                0.0,
                2.2,
            )
            _chamfer_box(
                specs,
                "a21-r6-palace-grounded-vertical-buttress-tower-lower",
                "carved_stone" if tower_index == 0 else "ivory_stone",
                group,
                tower_x,
                13.8,
                tower_z,
                10.5,
                27.6,
                10.5,
                (0.18, 0.13)[lod],
                2 if lod == 0 else 1,
            )
            _chamfer_box(
                specs,
                "a21-r6-palace-grounded-vertical-buttress-tower-upper",
                "ivory_stone" if tower_index == 0 else "carved_stone",
                group,
                tower_x,
                29.55,
                tower_z,
                8.7,
                5.1,
                8.7,
                (0.15, 0.11)[lod],
                2 if lod == 0 else 1,
            )
            _chamfer_box(
                specs,
                "a21-r6-palace-grounded-vertical-buttress-tower-lantern",
                "carved_stone",
                group,
                tower_x,
                34.05,
                tower_z,
                6.8,
                4.8,
                6.8,
                (0.13, 0.095)[lod],
                1,
            )
            facade_x = tower_x + normal_x * 5.34
            facade_z = tower_z + normal_z * 5.34
            for window_index, window_y in enumerate(
                (7.8, 16.1, 24.4, 33.9)[: (4, 3)[lod]]
            ):
                _deep_window(
                    specs,
                    group=group,
                    role="a21-r6-palace-vertical-tower-deep-occupied-window",
                    x=facade_x,
                    y=window_y,
                    z=facade_z + tangent_z * (
                        -1.45 if window_index % 2 == 0 else 1.45
                    ),
                    width=1.55,
                    height=2.75,
                    plane="side",
                    warm=(tower_index + window_index) % 2 == 0,
                )
            for ledge_y in (19.7, 27.2, 32.5):
                _chamfer_box(
                    specs,
                    "a21-r6-palace-vertical-tower-deep-terrace-band",
                    "wet_stone" if ledge_y < 30.0 else "brass",
                    group,
                    tower_x,
                    ledge_y,
                    tower_z,
                    11.0 if ledge_y < 30.0 else 9.2,
                    0.38,
                    11.0 if ledge_y < 30.0 else 9.2,
                    (0.055, 0.042)[lod],
                    1,
                )
            roof_base_y = 36.45
            _roof(
                specs,
                group=group,
                role="a21-r6-palace-vertical-tower-petal-gable",
                cx=tower_x,
                base_y=roof_base_y,
                cz=tower_z,
                width=8.0,
                depth=8.0,
                rise=4.05,
                material=(
                    "verdigris_bronze"
                    if tower_index == 0
                    else "wet_stone"
                ),
            )
            _sweep(
                specs,
                "a21-r6-palace-vertical-tower-brass-finial",
                "brass",
                group,
                (
                    (tower_x, roof_base_y + 4.0, tower_z),
                    (tower_x, 42.15, tower_z),
                ),
                (0.12, 0.085)[lod],
                (8, 6)[lod],
            )
    _chamfer_box(
        specs,
        "a21-r5-palace-rooted-crown-stepped-lantern-keep",
        "carved_stone",
        group,
        root_x,
        33.3,
        root_z,
        17.5,
        1.35,
        11.0,
        (0.14, 0.11, 0.08)[lod],
        1,
    )
    face_x = root_x + normal_x * 17.0
    face_z = root_z + normal_z * 17.0
    root_loggia_bays = (7, 5, 3)[lod]
    for bay_index in range(root_loggia_bays):
        tangent_offset = (
            bay_index - (root_loggia_bays - 1) * 0.5
        ) * 2.65
        bay_x = face_x + tangent_x * tangent_offset
        bay_z = face_z + tangent_z * tangent_offset
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r5-palace-rooted-keep-occupied-loggia",
            centre_x=bay_x,
            centre_z=bay_z,
            axis_x=tangent_x,
            axis_z=tangent_z,
            half_width=1.42,
            base_y=24.2,
            spring_y=30.5,
            rise=2.25,
            segments=(18, 11, 6)[lod],
            radius=(0.26, 0.21, 0.17)[lod],
            sides=(8, 6, 4)[lod],
            material="carved_stone",
        )
        _panel(
            specs,
            "a21-r5-palace-rooted-keep-warm-loggia-depth",
            "warm_glow" if bay_index % 2 else "dirty_glass",
            group,
            (
                (
                    bay_x - tangent_x * 1.18,
                    24.65,
                    bay_z - tangent_z * 1.18,
                ),
                (
                    bay_x + tangent_x * 1.18,
                    24.65,
                    bay_z + tangent_z * 1.18,
                ),
                (
                    bay_x + tangent_x * 1.18,
                    30.65,
                    bay_z + tangent_z * 1.18,
                ),
                (
                    bay_x - tangent_x * 1.18,
                    30.65,
                    bay_z - tangent_z * 1.18,
                ),
            ),
            0.10,
        )
    for support_index, tangent_offset in enumerate(
        (-8.0, -4.0, 0.0, 4.0, 8.0)
    ):
        support_x = face_x + tangent_x * tangent_offset
        support_z = face_z + tangent_z * tangent_offset
        _sweep(
            specs,
            "a21-r6-palace-crown-tower-vertical-structural-pier",
            "ivory_stone" if support_index % 2 == 0 else "carved_stone",
            group,
            (
                (support_x, 23.4, support_z),
                (support_x, 34.45, support_z),
            ),
            (0.42, 0.34, 0.26)[lod],
            (10, 7, 5)[lod],
        )
        if lod <= 1:
            _chamfer_box(
                specs,
                "a21-r6-palace-crown-tower-grounded-pier-foot",
                "carved_stone",
                group,
                support_x,
                23.82,
                support_z,
                1.28,
                0.84,
                1.28,
                (0.075, 0.060, 0.045)[lod],
                1,
            )
    _sweep(
        specs,
        "a21-r6-palace-crown-tower-deep-cornice",
        "ivory_stone",
        group,
        (
            (
                face_x - tangent_x * 12.5,
                34.48,
                face_z - tangent_z * 12.5,
            ),
            (
                face_x + tangent_x * 12.5,
                34.48,
                face_z + tangent_z * 12.5,
            ),
        ),
        (0.44, 0.34, 0.26)[lod],
        (10, 7, 5)[lod],
    )

    petal_offsets = (
        (-8.0, -4.0, 0.0, 4.0, 8.0)
        if lod == 0
        else (-7.0, -3.5, 0.0, 3.5, 7.0)
        if lod == 1
        else (-5.0, 0.0, 5.0)
    )
    # The shell sits just in front of the occupied loggia.  Earlier iterations
    # placed it behind the 17 m facade offset, hiding every petal root and
    # reducing the castle-scale crown to a row of small roof ornaments.
    petal_plane_x = root_x + normal_x * 18.6
    petal_plane_z = root_z + normal_z * 18.6

    def petal_point(
        tangent_offset: float,
        y: float,
        normal_offset: float = 0.0,
    ) -> tuple[float, float, float]:
        return (
            petal_plane_x
            + tangent_x * tangent_offset
            + normal_x * normal_offset,
            y,
            petal_plane_z
            + tangent_z * tangent_offset
            + normal_z * normal_offset,
        )

    for petal_index, offset in enumerate(petal_offsets):
        root_centre = offset * 0.24
        waist_centre = offset * 0.62
        shoulder_centre = offset * 0.92
        tip_centre = offset * 0.86
        root_y = 23.6
        waist_y = 31.2 - abs(offset) * 0.055
        shoulder_y = 37.0 - abs(offset) * 0.120
        upper_y = 40.15 - abs(offset) * 0.235
        tip_y = 42.46 - abs(offset) * 0.390
        root_half = (7.30, 5.90, 4.15)[lod]
        waist_half = (6.10, 4.90, 3.45)[lod]
        shoulder_half = (4.80, 3.75, 2.45)[lod]
        upper_half = (3.00, 2.25, 1.42)[lod]
        petal_corners = (
            petal_point(root_centre - root_half, root_y),
            petal_point(root_centre + root_half, root_y),
            petal_point(
                waist_centre + waist_half,
                waist_y,
                0.32,
            ),
            petal_point(
                shoulder_centre + shoulder_half,
                shoulder_y,
                0.54,
            ),
            petal_point(
                tip_centre + upper_half,
                upper_y,
                0.62,
            ),
            petal_point(tip_centre, tip_y, 0.30),
            petal_point(
                tip_centre - upper_half,
                upper_y,
                0.62,
            ),
            petal_point(
                shoulder_centre - shoulder_half,
                shoulder_y,
                0.54,
            ),
            petal_point(
                waist_centre - waist_half,
                waist_y,
                0.32,
            ),
        )
        _panel(
            specs,
            "a21-r5-palace-overlapping-vertical-petal",
            "dirty_glass",
            group,
            petal_corners,
            (0.72, 0.58, 0.46)[lod],
        )
        inner_root_left = petal_point(
            root_centre - root_half * 0.20,
            root_y + 0.35,
            0.82,
        )
        inner_root_right = petal_point(
            root_centre + root_half * 0.20,
            root_y + 0.35,
            0.82,
        )
        inner_waist_left = petal_point(
            waist_centre - waist_half * 0.22,
            waist_y,
            0.94,
        )
        inner_waist_right = petal_point(
            waist_centre + waist_half * 0.22,
            waist_y,
            0.94,
        )
        inner_shoulder_left = petal_point(
            shoulder_centre - shoulder_half * 0.18,
            shoulder_y,
            1.06,
        )
        inner_shoulder_right = petal_point(
            shoulder_centre + shoulder_half * 0.18,
            shoulder_y,
            1.06,
        )
        inner_upper_left = petal_point(
            tip_centre - upper_half * 0.16,
            upper_y,
            1.10,
        )
        inner_upper_right = petal_point(
            tip_centre + upper_half * 0.16,
            upper_y,
            1.10,
        )
        inner_tip = petal_point(
            tip_centre,
            tip_y - 0.62,
            0.92,
        )
        _panel(
            specs,
            "a21-r6-palace-petal-opaque-stone-shell-wing",
            "ivory_stone",
            group,
            (
                petal_corners[0],
                inner_root_left,
                inner_waist_left,
                inner_shoulder_left,
                inner_upper_left,
                inner_tip,
                petal_corners[5],
                petal_corners[6],
                petal_corners[7],
                petal_corners[8],
            ),
            (0.38, 0.31, 0.25)[lod],
        )
        _panel(
            specs,
            "a21-r6-palace-petal-opaque-stone-shell-wing",
            "carved_stone" if petal_index % 2 else "ivory_stone",
            group,
            (
                petal_corners[1],
                petal_corners[2],
                petal_corners[3],
                petal_corners[4],
                petal_corners[5],
                inner_tip,
                inner_upper_right,
                inner_shoulder_right,
                inner_waist_right,
                inner_root_right,
            ),
            (0.38, 0.31, 0.25)[lod],
        )
        _sweep(
            specs,
            "a21-r5-palace-fine-petal-spine",
            "carved_stone",
            group,
            (
                petal_point(root_centre, root_y + 0.10, 0.38),
                petal_point(waist_centre, waist_y, 0.70),
                petal_point(shoulder_centre, shoulder_y, 0.82),
                petal_point(tip_centre, tip_y, 0.52),
                petal_point(tip_centre, min(42.60, tip_y + 0.18), 0.52),
            ),
            (0.220, 0.185, 0.145)[lod],
            (8, 6, 4)[lod],
        )
        _sweep(
            specs,
            "a21-r6-palace-petal-brass-inlay-spine",
            "brass",
            group,
            (
                petal_point(root_centre, root_y + 0.18, 0.72),
                petal_point(waist_centre, waist_y, 0.96),
                petal_point(shoulder_centre, shoulder_y, 1.08),
                petal_point(tip_centre, tip_y, 0.78),
            ),
            (0.095, 0.074, 0.054)[lod],
            (8, 6, 4)[lod],
        )
        for rib_index, rib_points in enumerate(
            (
                (petal_corners[8], petal_corners[2]),
                (petal_corners[7], petal_corners[3]),
                (petal_corners[6], petal_corners[4]),
            )
        ):
            # The opaque shell and centre spine retain the silhouette at LOD2;
            # transverse ribs are reserved for the two presentation LODs.
            if lod == 2:
                continue
            _sweep(
                specs,
                "a21-r6-palace-petal-transverse-structural-rib",
                "ivory_stone" if rib_index == 0 else "brass",
                group,
                rib_points,
                (0.235, 0.175, 0.125)[lod],
                (8, 6, 4)[lod],
            )
        if lod <= 1:
            inset = (
                inner_root_left,
                inner_root_right,
                inner_waist_right,
                inner_shoulder_right,
                inner_upper_right,
                inner_tip,
                inner_upper_left,
                inner_shoulder_left,
                inner_waist_left,
            )
            _panel(
                specs,
                "a21-r5-palace-petal-carved-inner-relief",
                "glass_highlight",
                group,
                inset,
                0.10,
            )
        if lod == 0:
            for edge_points in (
                (
                    petal_corners[0],
                    petal_corners[8],
                    petal_corners[7],
                    petal_corners[6],
                    petal_corners[5],
                ),
                (
                    petal_corners[1],
                    petal_corners[2],
                    petal_corners[3],
                    petal_corners[4],
                    petal_corners[5],
                ),
            ):
                _sweep(
                    specs,
                    "a21-r5-palace-fine-petal-edge",
                    "ivory_stone",
                    group,
                    edge_points,
                    0.380,
                    9,
                )
                _sweep(
                    specs,
                    "a21-r6-palace-petal-brass-inlay-edge",
                    "brass",
                    group,
                    tuple(
                        (
                            point[0] + normal_x * 0.34,
                            point[1],
                            point[2] + normal_z * 0.34,
                        )
                        for point in edge_points
                    ),
                    0.105,
                    7,
                )
    for planter_index in range((7, 5, 3)[lod]):
        tangent_offset = -18.0 + planter_index * (
            36.0 / max(1, (7, 5, 3)[lod] - 1)
        )
        planter_x, _, planter_z = palace_point(
            -31.0,
            -61.0,
            tangent_offset,
            0.0,
            2.1,
        )
        _chamfer_box(
            specs,
            "a21-r5-palace-occupied-loggia-planter",
            "carved_stone",
            group,
            planter_x,
            17.45,
            planter_z,
            2.3,
            0.86,
            1.9,
            (0.065, 0.052, 0.042)[lod],
            1,
        )
        _leaf_cluster(
            specs,
            "a21-r5-palace-loggia-botanical-spill",
            "flower" if planter_index % 3 == 1 else "foliage_light",
            group,
            planter_x,
            18.18,
            planter_z,
            1.2,
            0.88,
            (18, 10, 5)[lod],
            34500 + planter_index,
        )

    # A slender occupied garden bridge visibly connects palace and city.
    bridge_group = "a21-r5-nakaniwa-palace-garden-connection"
    bridge_start = (-16.4, 11.35, -46.5)
    bridge_end = (3.8, 11.35, -35.0)
    bridge_dx = bridge_end[0] - bridge_start[0]
    bridge_dz = bridge_end[2] - bridge_start[2]
    bridge_length = math.hypot(bridge_dx, bridge_dz)
    bridge_forward = (bridge_dx / bridge_length, bridge_dz / bridge_length)
    bridge_right = (bridge_forward[1], -bridge_forward[0])
    bridge_centre = (
        (bridge_start[0] + bridge_end[0]) * 0.5,
        bridge_start[1],
        (bridge_start[2] + bridge_end[2]) * 0.5,
    )
    _panel(
        specs,
        "a21-r5-palace-occupied-connection-bridge-deck",
        "ivory_stone",
        bridge_group,
        tuple(
            (
                bridge_centre[0]
                + bridge_forward[0] * along
                + bridge_right[0] * across,
                bridge_centre[1],
                bridge_centre[2]
                + bridge_forward[1] * along
                + bridge_right[1] * across,
            )
            for along, across in (
                (-bridge_length * 0.5, -2.0),
                (bridge_length * 0.5, -2.0),
                (bridge_length * 0.5, 2.0),
                (-bridge_length * 0.5, 2.0),
            )
        ),
        (0.48, 0.38, 0.30)[lod],
    )
    for rail_side in (-1.0, 1.0):
        rail_offset = 1.82 * rail_side
        _sweep(
            specs,
            "a21-r5-palace-connection-bridge-brass-handrail",
            "brass",
            bridge_group,
            (
                (
                    bridge_start[0] + bridge_right[0] * rail_offset,
                    12.62,
                    bridge_start[2] + bridge_right[1] * rail_offset,
                ),
                (
                    bridge_end[0] + bridge_right[0] * rail_offset,
                    12.62,
                    bridge_end[2] + bridge_right[1] * rail_offset,
                ),
            ),
            (0.040, 0.033, 0.027)[lod],
            (8, 6, 4)[lod],
        )
    support_count = (5, 4, 3)[lod]
    for support_index in range(support_count):
        progress = support_index / max(1, support_count - 1)
        support_x = bridge_start[0] + bridge_dx * progress
        support_z = bridge_start[2] + bridge_dz * progress
        _chamfer_box(
            specs,
            "a21-r5-palace-connection-bridge-grounded-pier",
            "carved_stone",
            bridge_group,
            support_x,
            5.75,
            support_z,
            0.82,
            11.4,
            0.82,
            (0.070, 0.055, 0.045)[lod],
            1,
        )


def _add_r5_conservatory_open_base(specs: list[dict], lod: int) -> None:
    """Expose the five shells over a low transparent inhabited threshold."""
    group = CONSERVATORY_ID
    _chamfer_box(
        specs,
        "a21-r5-conservatory-open-entry-base",
        "ivory_stone",
        group,
        52.0,
        1.35,
        31.15,
        36.0,
        1.8,
        4.1,
        (0.14, 0.11, 0.08)[lod],
        2 if lod == 0 else 1,
    )
    portal_count = (7, 5, 3)[lod]
    portal_span = 27.0
    portal_width = portal_span / portal_count
    for portal_index in range(portal_count):
        portal_x = 52.0 - portal_span * 0.5 + portal_width * (
            portal_index + 0.5
        )
        _deep_window(
            specs,
            group=group,
            role="a21-r5-conservatory-transparent-warm-entry-bay",
            x=portal_x,
            y=5.1,
            z=29.18,
            width=portal_width * 0.72,
            height=6.8,
            warm=portal_index in {1, portal_count - 2},
        )
    for column_x in (
        52.0 - portal_span * 0.5,
        52.0,
        52.0 + portal_span * 0.5,
    ):
        _chamfer_box(
            specs,
            "a21-r5-conservatory-open-entry-slender-stone-pier",
            "carved_stone",
            group,
            column_x,
            5.15,
            29.45,
            0.74,
            7.7,
            0.80,
            (0.060, 0.050, 0.040)[lod],
            1,
        )
    _chamfer_box(
        specs,
        "a21-r5-conservatory-open-entry-continuous-canopy",
        "ivory_stone",
        group,
        52.0,
        9.0,
        31.05,
        31.0,
        0.66,
        4.5,
        (0.075, 0.060, 0.050)[lod],
        1,
    )
    stair_count = (8, 6, 4)[lod]
    for stair_index in range(stair_count):
        _chamfer_box(
            specs,
            "a21-r5-conservatory-broad-readable-entry-stair",
            "carved_stone" if stair_index % 2 == 0 else "ivory_stone",
            group,
            52.0,
            0.12 + stair_index * 0.12,
            29.15 + stair_index * 0.48,
            15.0 - stair_index * 0.32,
            0.22,
            0.66,
            (0.040, 0.034, 0.028)[lod],
            1,
        )
    # Two transparent mezzanines and warm lanterns read behind the front fan.
    for mezzanine_z, mezzanine_y, width in (
        (40.5, 7.6, 30.0),
        (48.0, 10.4, 25.0),
    )[: (2, 2, 1)[lod]]:
        _chamfer_box(
            specs,
            "a21-r5-conservatory-interior-botanical-mezzanine",
            "carved_stone",
            group,
            52.0,
            mezzanine_y,
            mezzanine_z,
            width,
            0.38,
            2.25,
            (0.060, 0.050, 0.040)[lod],
            1,
        )
        for rail_z in (mezzanine_z - 1.20, mezzanine_z + 1.20):
            _sweep(
                specs,
                "a21-r5-conservatory-interior-mezzanine-handrail",
                "brass",
                group,
                (
                    (52.0 - width * 0.49, mezzanine_y + 1.18, rail_z),
                    (52.0 + width * 0.49, mezzanine_y + 1.18, rail_z),
                ),
                (0.034, 0.028, 0.023)[lod],
                (7, 6, 4)[lod],
            )
            post_count = (9, 6, 4)[lod]
            for post_index in range(post_count):
                post_x = 52.0 - width * 0.48 + post_index * (
                    width * 0.96 / max(1, post_count - 1)
                )
                _sweep(
                    specs,
                    "a21-r5-conservatory-interior-mezzanine-post",
                    "verdigris_bronze",
                    group,
                    (
                        (post_x, mezzanine_y + 0.18, rail_z),
                        (post_x, mezzanine_y + 1.18, rail_z),
                    ),
                    (0.026, 0.022, 0.018)[lod],
                    (7, 6, 4)[lod],
                )
        lantern_count = (5, 3, 2)[lod]
        for lantern_index in range(lantern_count):
            lantern_x = 52.0 - width * 0.36 + lantern_index * (
                width * 0.72 / max(1, lantern_count - 1)
            )
            _chamfer_box(
                specs,
                "a21-r5-conservatory-interior-warm-depth-lantern",
                "warm_glow",
                group,
                lantern_x,
                mezzanine_y + 1.72,
                mezzanine_z,
                0.42,
                0.58,
                0.42,
                0.045,
                1,
            )
    for planter_x in (36.0, 68.0):
        _chamfer_box(
            specs,
            "a21-r5-conservatory-open-entry-botanical-planter",
            "carved_stone",
            group,
            planter_x,
            1.25,
            32.2,
            5.6,
            1.4,
            4.2,
            (0.090, 0.070, 0.055)[lod],
            1,
        )
        _leaf_cluster(
            specs,
            "a21-r5-conservatory-entry-botanical-spill",
            "foliage_light",
            group,
            planter_x,
            2.25,
            32.2,
            2.35,
            1.40,
            (24, 13, 7)[lod],
            34700 + int(planter_x),
        )


def _add_r5_garden_city_depth(specs: list[dict], lod: int) -> None:
    """Close the horizon with real occupied near/mid/far garden architecture."""
    group = "a21-r5-nakaniwa-layered-garden-city-depth"
    sites = (
        (-116.0, 12.0, 24.0, 18.0, 34.0),
        (-89.0, 34.0, 22.0, 17.0, 37.0),
        (-60.0, 50.0, 23.0, 18.0, 33.0),
        (-29.0, 65.0, 24.0, 18.0, 39.0),
        (0.0, 80.0, 21.0, 17.0, 32.0),
        (25.0, 105.0, 24.0, 18.0, 36.0),
        (53.0, 118.0, 20.0, 17.0, 35.0),
        (82.0, 112.0, 22.0, 18.0, 38.0),
        (107.0, 95.0, 23.0, 19.0, 34.0),
        (122.0, 64.0, 22.0, 18.0, 37.0),
    )
    site_count = (10, 8, 5)[lod]
    for site_index, (x, z, width, depth, height) in enumerate(
        sites[:site_count]
    ):
        # Moss remains vegetation and inset weathering; it is no longer used
        # as the full structural wall of a distant rectangular house.
        material = "ivory_stone" if site_index % 2 == 0 else "carved_stone"
        lower_height = height * 0.68
        _chamfer_box(
            specs,
            "a21-r5-garden-city-occupied-limestone-house",
            material,
            group,
            x,
            lower_height * 0.5,
            z,
            width,
            lower_height,
            depth,
            (0.14, 0.11, 0.085)[lod],
            2 if lod == 0 else 1,
        )
        upper_width = width * (0.62 + 0.08 * (site_index % 2))
        upper_depth = depth * (0.58 + 0.07 * ((site_index + 1) % 2))
        upper_height = height - lower_height
        _chamfer_box(
            specs,
            "a21-r5-garden-city-stepped-occupied-upper-loggia",
            "ivory_stone" if site_index % 2 else "carved_stone",
            group,
            x,
            lower_height + upper_height * 0.5 - 0.12,
            z,
            upper_width,
            upper_height,
            upper_depth,
            (0.10, 0.08, 0.06)[lod],
            1,
        )
        facade_z = z - depth * 0.5 - 0.08
        detailed_lower_sites = (
            range(2, 8)
            if lod == 0
            else range(2, 6)
            if lod == 1
            else ()
        )
        if site_index in detailed_lower_sites:
            lower_bay_count = (4, 2)[lod]
            for bay_index in range(lower_bay_count):
                bay_x = (
                    x
                    - width * 0.32
                    + bay_index
                    * width
                    * 0.64
                    / max(1, lower_bay_count - 1)
                )
                _deep_window(
                    specs,
                    group=group,
                    role="a21-r6-garden-city-lower-tall-occupied-window",
                    x=bay_x,
                    y=lower_height * 0.64,
                    z=facade_z - 0.18,
                    width=1.90,
                    height=4.65,
                    warm=(site_index + bay_index) % 3 == 0,
                )
            for pier_index in range(lower_bay_count + 1):
                pier_x = (
                    x
                    - width * 0.40
                    + pier_index
                    * width
                    * 0.80
                    / lower_bay_count
                )
                _chamfer_box(
                    specs,
                    "a21-r6-garden-city-lower-vertical-carved-buttress",
                    "carved_stone" if pier_index % 2 else "ivory_stone",
                    group,
                    pier_x,
                    lower_height * 0.54,
                    facade_z - 0.25,
                    0.52,
                    lower_height * 0.82,
                    0.72,
                    (0.050, 0.040)[lod],
                    1,
                )
        _arcade(
            specs,
            group=group,
            role="a21-r5-garden-city-deep-occupied-arcade",
            material="carved_stone",
            x0=x - width * 0.40,
            x1=x + width * 0.40,
            z=facade_z,
            base_y=0.15,
            bays=(3, 3, 2)[lod],
            lod=1 if lod == 0 else 2 if lod == 1 else 2,
            depth=(0.17, 0.14, 0.12)[lod],
        )
        if lod <= 1:
            window_count = (4, 3)[lod]
            for window_index in range(window_count):
                window_x = x - width * 0.30 + window_index * (
                    width * 0.60 / max(1, window_count - 1)
                )
                _deep_window(
                    specs,
                    group=group,
                    role="a21-r5-garden-city-upper-deep-window",
                    x=window_x,
                    y=lower_height + upper_height * 0.50,
                    z=facade_z - 0.12,
                    width=1.45,
                    height=2.45,
                    warm=(site_index + window_index) % 4 == 0,
                )
        for balcony_level in (
            lower_height * 0.56,
            lower_height * 0.82,
        )[: (2, 1, 1)[lod]]:
            _chamfer_box(
                specs,
                "a21-r5-garden-city-wet-stone-balcony",
                "wet_stone",
                group,
                x,
                balcony_level,
                facade_z - 0.46,
                width * 0.76,
                0.34,
                1.38,
                (0.055, 0.045, 0.036)[lod],
                1,
            )
        roof_y = lower_height + upper_height - 0.15
        if site_index not in {2, 6, 9}:
            _roof(
                specs,
                group=group,
                role="a21-r5-garden-city-broad-botanical-roof",
                cx=x,
                base_y=roof_y,
                cz=z,
                width=upper_width + 1.0,
                depth=upper_depth + 1.0,
                rise=3.0 + 0.55 * (site_index % 3),
                material=(
                    "verdigris_bronze"
                    if site_index % 2 == 0
                    else "wet_stone"
                ),
            )
        else:
            _chamfer_box(
                specs,
                "a21-r5-garden-city-planted-flat-roof",
                "carved_stone",
                group,
                x,
                roof_y + 0.30,
                z,
                upper_width + 1.0,
                0.55,
                upper_depth + 1.0,
                (0.065, 0.052, 0.042)[lod],
                1,
            )
        if lod <= 1:
            planter_x = x + (-0.18 if site_index % 2 else 0.18) * upper_width
            _chamfer_box(
                specs,
                "a21-r5-garden-city-roof-planter",
                "carved_stone",
                group,
                planter_x,
                roof_y + 0.85,
                z,
                3.4,
                0.78,
                2.7,
                (0.060, 0.050, 0.040)[lod],
                1,
            )
            _leaf_cluster(
                specs,
                "a21-r5-garden-city-roof-garden",
                "foliage_light" if site_index % 2 else "foliage_dark",
                group,
                planter_x,
                roof_y + 2.15,
                z,
                (2.65, 2.25)[lod],
                (2.45, 1.90)[lod],
                (32, 16)[lod],
                34900 + site_index,
            )
    tree_sites = (
        (-103.0, 22.0),
        (-75.0, 43.0),
        (-44.0, 59.0),
        (-14.0, 73.0),
        (13.0, 94.0),
        (39.0, 112.0),
        (68.0, 116.0),
        (96.0, 103.0),
        (117.0, 80.0),
    )
    for tree_index, (x, z) in enumerate(
        tree_sites[: (9, 7, 5)[lod]]
    ):
        _tree(
            specs,
            group=group,
            role="a21-r5-garden-city-layered-canopy",
            x=x,
            z=z,
            height=11.0 + (tree_index % 3) * 1.8,
            crown=4.2 + (tree_index % 2) * 0.7,
            lod=lod,
            seed=35100 + tree_index,
            flowering=tree_index % 4 == 0,
        )


R6_VISUAL_BLOCKER_PREFIXES = (
    "a21-r2-extreme-foreground-",
    "a21-r2-canal-terraced-botanical-planter",
    "a21-r2-canal-planter-",
    "a21-r2-canal-sculpted-garden-tree",
    "a21-r2-canal-route-human-scale-lantern",
    "a21-r2-canal-route-warm-lantern",
    "a21-r2-canal-side-monumental-garden-arcade",
    "a21-r2-canal-side-arcade-buttressed-pier",
    "a21-r2-canal-side-arcade-entablature",
    "a21-r2-canal-side-arcade-garden-canopy",
    "a21-r2-district-",
    "a21-r3-mid-city-",
    "a21-r5-foreground-layered-",
    "a21-r5-foreground-wet-",
    "a21-r5-foreground-pruned-",
    "a21-r5-gardener-bench-",
    "a21-r5-gardener-hand-tool",
    "a21-r5-first-bridge-",
    "a21-r5-palace-occupied-connection-bridge",
    "a21-r5-palace-connection-bridge-",
)


def _remove_r6_visual_blockers(specs: list[dict]) -> None:
    """Remove the near masses and floating pavilion roofs rejected in R5."""
    specs[:] = [
        spec
        for spec in specs
        if not any(
            str(spec["role"]).startswith(prefix)
            for prefix in R6_VISUAL_BLOCKER_PREFIXES
        )
    ]


def _add_r6_palace_hero_scale(specs: list[dict], lod: int) -> None:
    """Stack broad occupied arcades so the palace reads at castle scale."""
    gallery_specs = (
        (
            -52.0,
            -66.0,
            67.0,
            4.0,
            5.0,
            3.0,
            (11, 8, 5)[lod],
            "a21-r6-palace-monumental-lower-water-loggia",
        ),
        (
            -51.0,
            -63.0,
            60.0,
            13.0,
            4.7,
            2.8,
            (9, 7, 4)[lod],
            "a21-r6-palace-monumental-middle-garden-loggia",
        ),
        (
            -50.0,
            -60.0,
            52.0,
            21.0,
            4.4,
            2.7,
            (7, 5, 3)[lod],
            "a21-r6-palace-monumental-upper-crown-loggia",
        ),
    )
    for (
        centre_x,
        centre_z,
        length,
        base_y,
        spring_height,
        rise,
        bays,
        role,
    ) in gallery_specs:
        _add_r4_oriented_palace_gallery(
            specs,
            lod,
            centre_x=centre_x,
            centre_z=centre_z,
            length=length,
            base_y=base_y,
            spring_height=spring_height,
            rise=rise,
            bays=bays,
            role=role,
        )

    # Wide planted ledges keep the added height occupied and visually bind
    # each tier to the next without introducing a detached roof silhouette.
    normal_x, normal_z = 0.985, -0.172
    tangent_x, tangent_z = 0.172, 0.985
    ledges = (
        (-52.0, -66.0, 62.0, 12.62),
        (-51.0, -63.0, 55.0, 20.12),
        (-50.0, -60.0, 46.0, 28.32),
    )
    for ledge_index, (centre_x, centre_z, length, ledge_y) in enumerate(ledges):
        half_length = length * 0.5
        _panel(
            specs,
            "a21-r6-palace-broad-occupied-terrace-ledge",
            "ivory_stone",
            PALACE_ID,
            tuple(
                (
                    centre_x
                    + tangent_x * along
                    + normal_x * outward,
                    ledge_y,
                    centre_z
                    + tangent_z * along
                    + normal_z * outward,
                )
                for along, outward in (
                    (-half_length, -1.0),
                    (half_length, -1.0),
                    (half_length, 2.1),
                    (-half_length, 2.1),
                )
            ),
            (0.38, 0.31, 0.25)[lod],
        )
        planter_count = ((7, 6, 5), (5, 4, 3), (3, 3, 2))[lod][
            ledge_index
        ]
        for planter_index in range(planter_count):
            progress = planter_index / max(1, planter_count - 1)
            along = -half_length * 0.82 + progress * half_length * 1.64
            planter_x = (
                centre_x + tangent_x * along + normal_x * 1.48
            )
            planter_z = (
                centre_z + tangent_z * along + normal_z * 1.48
            )
            _chamfer_box(
                specs,
                "a21-r6-palace-terrace-human-scale-planter",
                "carved_stone",
                PALACE_ID,
                planter_x,
                ledge_y + 0.44,
                planter_z,
                1.55,
                0.72,
                1.25,
                (0.050, 0.042, 0.034)[lod],
                1,
            )
            if lod <= 1:
                _leaf_cluster(
                    specs,
                    "a21-r6-palace-terrace-flower-spill",
                    "flower" if (ledge_index + planter_index) % 3 == 1
                    else "foliage_light",
                    PALACE_ID,
                    planter_x,
                    ledge_y + 1.02,
                    planter_z,
                    0.74,
                    0.58,
                    (14, 8, 4)[lod],
                    36300 + ledge_index * 20 + planter_index,
                )

    # One reference-first occupied tower fills the previously dark shelf
    # directly below the accepted forward crown.  Its three arcade tiers
    # narrow upward and the final entablature contacts the 23.6 m petal roots.
    crown_root_x, crown_root_z = -36.0, -91.0
    crown_face_x = crown_root_x + normal_x * 17.0
    crown_face_z = crown_root_z + normal_z * 17.0
    if lod <= 1:
        tower_gallery_specs = (
            (24.0, 10.0, 1.35, 4.40, 2.45, (3, 2)[lod], "lower"),
            (22.0, 8.5, 8.35, 4.20, 2.55, (3, 2)[lod], "middle"),
            (20.0, 7.0, 15.25, 4.00, 4.00, (3, 2)[lod], "upper"),
        )

        def tower_point(
            tangent_offset: float,
            y: float,
            normal_offset: float = 0.0,
        ) -> tuple[float, float, float]:
            return (
                crown_face_x
                + tangent_x * tangent_offset
                + normal_x * normal_offset,
                y,
                crown_face_z
                + tangent_z * tangent_offset
                + normal_z * normal_offset,
            )

        for (
            tower_length,
            tower_depth,
            tower_base_y,
            tower_spring_height,
            tower_rise,
            tower_bays,
            tower_tier,
        ) in tower_gallery_specs:
            tower_top_y = (
                tower_base_y + tower_spring_height + tower_rise
            )
            tower_bay_span = tower_length / tower_bays
            tower_half_length = tower_length * 0.5
            tier_material = (
                "ivory_stone"
                if tower_tier in {"lower", "upper"}
                else "carved_stone"
            )
            for tangent_side in (-tower_half_length, tower_half_length):
                _panel(
                    specs,
                    (
                        "a21-r6-palace-forward-crown-tower-"
                        f"{tower_tier}-solid-return-wall"
                    ),
                    tier_material,
                    PALACE_ID,
                    (
                        tower_point(tangent_side, tower_base_y, 0.0),
                        tower_point(
                            tangent_side,
                            tower_base_y,
                            -tower_depth,
                        ),
                        tower_point(
                            tangent_side,
                            tower_top_y,
                            -tower_depth,
                        ),
                        tower_point(tangent_side, tower_top_y, 0.0),
                    ),
                    (0.42, 0.32)[lod],
                )
            _panel(
                specs,
                (
                    "a21-r6-palace-forward-crown-tower-"
                    f"{tower_tier}-occupied-floor-contact"
                ),
                tier_material,
                PALACE_ID,
                (
                    tower_point(-tower_half_length, tower_top_y, 0.0),
                    tower_point(tower_half_length, tower_top_y, 0.0),
                    tower_point(
                        tower_half_length,
                        tower_top_y,
                        -tower_depth,
                    ),
                    tower_point(
                        -tower_half_length,
                        tower_top_y,
                        -tower_depth,
                    ),
                ),
                (0.46, 0.35)[lod],
            )
            for bay_index in range(tower_bays):
                tangent_offset = (
                    -tower_length * 0.5
                    + tower_bay_span * (bay_index + 0.5)
                )
                bay_x, _, bay_z = tower_point(
                    tangent_offset,
                    tower_base_y,
                )
                _add_oriented_arch(
                    specs,
                    group=PALACE_ID,
                    role=(
                        "a21-r6-palace-forward-crown-tower-"
                        f"{tower_tier}-deep-occupied-arcade"
                    ),
                    centre_x=bay_x,
                    centre_z=bay_z,
                    axis_x=tangent_x,
                    axis_z=tangent_z,
                    half_width=tower_bay_span * 0.37,
                    base_y=tower_base_y,
                    spring_y=tower_base_y + tower_spring_height,
                    rise=tower_rise,
                    segments=(12, 8)[lod],
                    radius=(0.29, 0.22)[lod],
                    sides=(6, 4)[lod],
                    material="ivory_stone",
                )
                opening_half = tower_bay_span * 0.30
                _panel(
                    specs,
                    (
                        "a21-r6-palace-forward-crown-tower-"
                        f"{tower_tier}-recessed-occupied-depth"
                    ),
                    (
                        "warm_glow"
                        if (bay_index + len(tower_tier)) % 3 == 1
                        else "dirty_glass"
                    ),
                    PALACE_ID,
                    (
                        tower_point(
                            tangent_offset - opening_half,
                            tower_base_y + 0.38,
                            -0.42,
                        ),
                        tower_point(
                            tangent_offset + opening_half,
                            tower_base_y + 0.38,
                            -0.42,
                        ),
                        tower_point(
                            tangent_offset + opening_half,
                            tower_top_y - 0.55,
                            -0.42,
                        ),
                        tower_point(
                            tangent_offset - opening_half,
                            tower_top_y - 0.55,
                            -0.42,
                        ),
                    ),
                    0.12,
                )
            for pier_index in range(tower_bays + 1):
                tangent_offset = (
                    -tower_length * 0.5
                    + tower_length * pier_index / tower_bays
                )
                pier_x, _, pier_z = tower_point(
                    tangent_offset,
                    tower_base_y,
                    0.08,
                )
                _chamfer_box(
                    specs,
                    (
                        "a21-r6-palace-forward-crown-tower-"
                        f"{tower_tier}-grounded-pier"
                    ),
                    "carved_stone",
                    PALACE_ID,
                    pier_x,
                    (tower_base_y + tower_top_y) * 0.5,
                    pier_z,
                    (1.18, 1.00)[lod],
                    tower_top_y - tower_base_y + 0.34,
                    (1.08, 0.90)[lod],
                    (0.070, 0.052)[lod],
                    1,
                )
            _sweep(
                specs,
                (
                    "a21-r6-palace-forward-crown-tower-"
                    f"{tower_tier}-contact-cornice"
                ),
                "carved_stone",
                PALACE_ID,
                (
                    tower_point(-tower_length * 0.53, tower_top_y + 0.20),
                    tower_point(tower_length * 0.53, tower_top_y + 0.20),
                ),
                (0.33, 0.25)[lod],
                (7, 5)[lod],
            )

def _add_r6_midground_roofed_facade_layers(
    specs: list[dict],
    lod: int,
) -> None:
    """Layer occupied roofed towers behind the clear dual-hero corridor."""
    group = "a21-r6-nakaniwa-midground-roofed-facade-layers"
    sites = (
        (-60.0, 50.0, 14.5, 12.0, 23.5, 17.5),
        (-29.0, 65.0, 14.0, 12.0, 26.0, 16.5),
        (0.0, 80.0, 13.5, 11.5, 23.0, 18.0),
        (25.0, 105.0, 14.5, 12.0, 26.0, 18.5),
        (53.0, 118.0, 13.0, 11.5, 25.0, 17.0),
        (82.0, 112.0, 14.0, 12.0, 27.0, 19.5),
    )
    for site_index, (
        x,
        z,
        width,
        depth,
        base_y,
        tower_height,
    ) in enumerate(sites[: (6, 4, 2)[lod]]):
        _chamfer_box(
            specs,
            "a21-r6-midground-stepped-occupied-skyline-tower",
            "ivory_stone" if site_index % 2 else "carved_stone",
            group,
            x,
            base_y + tower_height * 0.5,
            z,
            width,
            tower_height,
            depth,
            (0.13, 0.105, 0.080)[lod],
            2 if lod == 0 else 1,
        )
        facade_z = z - depth * 0.5 - 0.10
        if lod <= 1:
            for pier_side in (-1.0, 1.0):
                pier_x = x + pier_side * width * 0.40
                _sweep(
                    specs,
                    "a21-r6-midground-stage-specific-vertical-facade-buttress",
                    (
                        "ivory_stone"
                        if (site_index + int(pier_side)) % 2
                        else "carved_stone"
                    ),
                    group,
                    (
                        (pier_x, base_y + 0.25, facade_z - 0.24),
                        (
                            pier_x,
                            base_y + tower_height - 0.25,
                            facade_z - 0.24,
                        ),
                    ),
                    (0.20, 0.14)[lod],
                    (7, 6)[lod],
                )
            _chamfer_box(
                specs,
                "a21-r6-midground-stage-specific-deep-cornice",
                "wet_stone",
                group,
                x,
                base_y + tower_height - 0.18,
                z,
                width + 1.1,
                0.52,
                depth + 1.0,
                (0.060, 0.046)[lod],
                1,
            )
        window_count = (3, 2, 1)[lod]
        for window_index in range(window_count):
            window_x = (
                x
                - width * 0.28
                + window_index
                * width
                * 0.56
                / max(1, window_count - 1)
            )
            _deep_window(
                specs,
                group=group,
                role="a21-r6-midground-tall-warm-window-rhythm",
                x=window_x,
                y=base_y + tower_height * 0.52,
                z=facade_z,
                width=1.55,
                height=3.25,
                warm=(site_index + window_index) % 2 == 0,
            )
            _box(
                specs,
                "a21-r6-midground-upper-warm-window-rhythm",
                (
                    "warm_glow"
                    if (site_index + window_index) % 3 == 0
                    else "dark_wood"
                ),
                group,
                window_x,
                base_y + tower_height * 0.78,
                facade_z - 0.08,
                1.25,
                2.15,
                0.16,
            )
        if lod <= 1:
            _chamfer_box(
                specs,
                "a21-r6-midground-occupied-balcony-shadow-band",
                "wet_stone",
                group,
                x,
                base_y + tower_height * 0.60,
                facade_z - 0.42,
                width * 0.90,
                0.42,
                1.15,
                (0.055, 0.044, 0.035)[lod],
                1,
            )
        roof_y = base_y + tower_height
        roof_base_y = roof_y
        if lod <= 1 and site_index % 2 == 1:
            _chamfer_box(
                specs,
                "a21-r6-midground-stage-specific-stepped-roof-lantern",
                "carved_stone",
                group,
                x,
                roof_y + 1.05,
                z,
                width * 0.62,
                2.1,
                depth * 0.62,
                (0.10, 0.075)[lod],
                1,
            )
            roof_base_y = roof_y + 2.10
        _roof(
            specs,
            group=group,
            role="a21-r6-midground-stage-specific-petal-gable",
            cx=x,
            base_y=roof_base_y,
            cz=z,
            width=width + 1.1,
            depth=depth + 1.0,
            rise=4.2 + (site_index % 4) * 0.55,
            material=(
                "verdigris_bronze"
                if site_index % 2 == 0
                else "wet_stone"
            ),
        )
        planter_x = x + (-1.8 if site_index % 2 else 1.8)
        _chamfer_box(
            specs,
            "a21-r6-midground-roof-garden-planter",
            "carved_stone",
            group,
            planter_x,
            roof_y + 0.72,
            z - depth * 0.22,
            2.8,
            0.72,
            2.1,
            (0.055, 0.044, 0.035)[lod],
            1,
        )
        if lod <= 1:
            _cylinder(
                specs,
                "a21-r6-midground-roof-garden-slender-tree-trunk",
                "dark_wood",
                group,
                planter_x - 0.85 if site_index % 2 else planter_x + 0.85,
                roof_y + 2.05,
                z - depth * 0.10,
                0.18,
                3.2,
                (10, 7)[lod],
                top_radius=0.10,
            )
            _leaf_cluster(
                specs,
                "a21-r6-midground-readable-roof-garden",
                "foliage_light" if site_index % 2 else "foliage_dark",
                group,
                planter_x,
                roof_y + 2.25,
                z - depth * 0.22,
                2.20,
                2.40,
                (32, 16)[lod],
                36500 + site_index,
            )
            _leaf_cluster(
                specs,
                "a21-r6-midground-readable-roof-tree-crown",
                "foliage_dark" if site_index % 2 else "foliage_light",
                group,
                planter_x - 0.85 if site_index % 2 else planter_x + 0.85,
                roof_y + 4.10,
                z - depth * 0.10,
                1.65,
                3.50,
                (22, 11)[lod],
                36580 + site_index,
            )


def _add_r6_midground_hanging_garden_spine(
    specs: list[dict],
    lod: int,
) -> None:
    """Join the skyline towers into one inhabited botanical district."""
    if lod == 2:
        return
    group = "a21-r6-nakaniwa-midground-hanging-garden-spine"
    sites = (
        (-60.0, 50.0, 23.5),
        (-29.0, 65.0, 26.0),
        (0.0, 80.0, 23.0),
        (25.0, 105.0, 26.0),
        (53.0, 118.0, 25.0),
        (82.0, 112.0, 27.0),
    )
    connection_count = (5, 3)[lod]
    for connection_index in range(connection_count):
        start_x, start_z, start_base_y = sites[connection_index]
        end_x, end_z, end_base_y = sites[connection_index + 1]
        delta_x = end_x - start_x
        delta_z = end_z - start_z
        length = math.hypot(delta_x, delta_z)
        axis_x = delta_x / length
        axis_z = delta_z / length
        side_x = -axis_z
        side_z = axis_x
        tower_trim = 7.0
        bridge_start = (
            start_x + axis_x * tower_trim,
            start_z + axis_z * tower_trim,
        )
        bridge_end = (
            end_x - axis_x * tower_trim,
            end_z - axis_z * tower_trim,
        )
        bridge_length = length - tower_trim * 2.0
        centre_x = (bridge_start[0] + bridge_end[0]) * 0.5
        centre_z = (bridge_start[1] + bridge_end[1]) * 0.5
        deck_y = max(start_base_y, end_base_y) + 4.7
        half_width = (2.35, 2.05)[lod]
        _panel(
            specs,
            "a21-r6-midground-inhabited-hanging-garden-bridge-deck",
            "ivory_stone",
            group,
            (
                (
                    bridge_start[0] - side_x * half_width,
                    deck_y,
                    bridge_start[1] - side_z * half_width,
                ),
                (
                    bridge_end[0] - side_x * half_width,
                    deck_y,
                    bridge_end[1] - side_z * half_width,
                ),
                (
                    bridge_end[0] + side_x * half_width,
                    deck_y,
                    bridge_end[1] + side_z * half_width,
                ),
                (
                    bridge_start[0] + side_x * half_width,
                    deck_y,
                    bridge_start[1] + side_z * half_width,
                ),
            ),
            (0.52, 0.40)[lod],
        )
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r6-midground-botanical-skybridge-grand-arch",
            centre_x=centre_x,
            centre_z=centre_z,
            axis_x=axis_x,
            axis_z=axis_z,
            half_width=bridge_length * 0.5,
            base_y=deck_y - 7.6,
            spring_y=deck_y - 2.55,
            rise=2.25,
            segments=(22, 14)[lod],
            radius=(0.32, 0.24)[lod],
            sides=(8, 6)[lod],
            material=(
                "verdigris_bronze"
                if connection_index % 2 == 0
                else "carved_stone"
            ),
        )
        for rail_side in (-1.0, 1.0):
            rail_offset_x = side_x * half_width * rail_side
            rail_offset_z = side_z * half_width * rail_side
            _sweep(
                specs,
                "a21-r6-midground-hanging-garden-brass-handrail",
                "brass",
                group,
                (
                    (
                        bridge_start[0] + rail_offset_x,
                        deck_y + 1.20,
                        bridge_start[1] + rail_offset_z,
                    ),
                    (
                        bridge_end[0] + rail_offset_x,
                        deck_y + 1.20,
                        bridge_end[1] + rail_offset_z,
                    ),
                ),
                (0.050, 0.040)[lod],
                (8, 6)[lod],
            )
            post_count = (3, 4)[lod]
            for post_index in range(post_count):
                progress = post_index / max(1, post_count - 1)
                post_x = (
                    bridge_start[0]
                    + (bridge_end[0] - bridge_start[0]) * progress
                    + rail_offset_x
                )
                post_z = (
                    bridge_start[1]
                    + (bridge_end[1] - bridge_start[1]) * progress
                    + rail_offset_z
                )
                _sweep(
                    specs,
                    "a21-r6-midground-hanging-garden-brass-baluster",
                    "brass",
                    group,
                    (
                        (post_x, deck_y + 0.12, post_z),
                        (post_x, deck_y + 1.20, post_z),
                    ),
                    (0.034, 0.028)[lod],
                    (7, 5)[lod],
                )
        planter_count = (2, 2)[lod]
        for planter_index in range(planter_count):
            progress = (planter_index + 1) / (planter_count + 1)
            planter_x = (
                bridge_start[0]
                + (bridge_end[0] - bridge_start[0]) * progress
            )
            planter_z = (
                bridge_start[1]
                + (bridge_end[1] - bridge_start[1]) * progress
            )
            _chamfer_box(
                specs,
                "a21-r6-midground-hanging-garden-deep-planter",
                "carved_stone",
                group,
                planter_x,
                deck_y + 0.48,
                planter_z,
                2.1,
                0.78,
                1.75,
                (0.060, 0.045)[lod],
                1,
            )
            _leaf_cluster(
                specs,
                "a21-r6-midground-hanging-garden-readable-cascade",
                (
                    "flower"
                    if (connection_index + planter_index) % 3 == 1
                    else "foliage_light"
                ),
                group,
                planter_x,
                deck_y + 1.28,
                planter_z,
                1.25,
                1.45,
                (24, 12)[lod],
                36700 + connection_index * 20 + planter_index,
            )
            _box(
                specs,
                "a21-r6-midground-hanging-garden-warm-lantern",
                "warm_glow",
                group,
                planter_x + side_x * 1.35,
                deck_y + 1.62,
                planter_z + side_z * 1.35,
                0.34,
                1.05,
                0.34,
            )


def _add_r6_open_bridge_axis(specs: list[dict], lod: int) -> None:
    """Build a low, story-rich approach without occupying the hero sightline."""
    group = "a21-r6-nakaniwa-open-bridge-axis"
    slab_count = (11, 8, 5)[lod]
    for slab_index in range(slab_count):
        progress = slab_index / max(1, slab_count - 1)
        t = -0.475 + progress * 0.575
        _panel(
            specs,
            "a21-r6-bridge-axis-weathered-paving-slab",
            (
                "carved_stone"
                if slab_index % 3 == 0
                else "ivory_stone"
                if slab_index % 3 == 1
                else "wet_stone"
            ),
            group,
            _r5_corridor_quad(t, 0.0, 0.17, 3.05, 4.25),
            (0.18, 0.15, 0.12)[lod],
        )
        if slab_index < slab_count - 1:
            left_x, left_z = _corridor_point(t + 0.031, -4.15)
            right_x, right_z = _corridor_point(t + 0.031, 4.15)
            _sweep(
                specs,
                "a21-r6-bridge-axis-fine-masonry-cross-joint",
                "wet_stone",
                group,
                ((left_x, 0.275, left_z), (right_x, 0.275, right_z)),
                (0.014, 0.011, 0.009)[lod],
                (7, 6, 4)[lod],
            )
    # Twin drainage rills and brass edge lines pull the eye to the first
    # bridge.  They are flush to the paving and cannot become foreground bars.
    for side in (-5.05, 5.05):
        _panel(
            specs,
            "a21-r6-bridge-axis-shallow-water-rill",
            "water",
            group,
            _r5_corridor_quad(-0.180, side, 0.245, 28.2, 0.25),
            (0.055, 0.045, 0.035)[lod],
        )
        rill_start = _corridor_point(-0.485, side + math.copysign(0.34, side))
        rill_end = _corridor_point(0.125, side + math.copysign(0.34, side))
        _sweep(
            specs,
            "a21-r6-bridge-axis-rill-brass-edge",
            "brass",
            group,
            (
                (rill_start[0], 0.305, rill_start[1]),
                (rill_end[0], 0.305, rill_end[1]),
            ),
            (0.025, 0.021, 0.017)[lod],
            (7, 6, 4)[lod],
        )

    # Low edge gardens replace R5's central wall.  Their small trees sit at
    # alternating frame edges and never cross the bridge/canal centreline.
    planter_sites = (
        (-0.22, -31.5, 3.5, True),
        (-0.06, 31.5, 3.2, False),
        (0.16, -19.4, 3.8, False),
        (0.34, 18.8, 3.0, True),
    )
    for planter_index, (t, side, half_forward, flowering) in enumerate(
        planter_sites[: (4, 3, 2)[lod]]
    ):
        _panel(
            specs,
            "a21-r6-edge-garden-low-chamfered-planter",
            "carved_stone",
            group,
            _r5_corridor_quad(t, side, 0.49, half_forward, 1.15),
            (0.52, 0.44, 0.36)[lod],
        )
        _panel(
            specs,
            "a21-r6-edge-garden-wet-soil",
            "wet_stone",
            group,
            _r5_corridor_quad(t, side, 0.79, half_forward - 0.30, 0.86),
            0.10,
        )
        centre_x, centre_z = _corridor_point(t, side)
        if planter_index == 0:
            _tree(
                specs,
                group=group,
                role="a21-r6-edge-garden-pruned-tree",
                x=centre_x,
                z=centre_z,
                height=3.35 + 0.20 * (planter_index % 2),
                crown=1.08 + 0.08 * (planter_index % 2),
                lod=lod,
                seed=36100 + planter_index,
                flowering=flowering,
            )
        for flower_index in range((3, 2, 1)[lod]):
            flower_t = t + (flower_index - 1) * 0.018
            flower_x, flower_z = _corridor_point(flower_t, side)
            _leaf_cluster(
                specs,
                "a21-r6-edge-garden-flower-border",
                "flower" if (planter_index + flower_index) % 3 == 0
                else "foliage_light",
                group,
                flower_x,
                1.02,
                flower_z,
                0.80,
                0.42,
                (18, 10, 5)[lod],
                36200 + planter_index * 10 + flower_index,
            )

    # A compact gardener station occupies the right edge only.
    bench_x, bench_z = _corridor_point(-0.115, 12.9)
    forward_x, forward_z, right_x, right_z = _r5_corridor_basis(-0.115)
    _panel(
        specs,
        "a21-r6-edge-story-gardener-bench",
        "dark_wood",
        group,
        tuple(
            (
                bench_x + forward_x * along + right_x * across,
                0.74,
                bench_z + forward_z * along + right_z * across,
            )
            for along, across in (
                (-1.25, -0.28),
                (1.25, -0.28),
                (1.25, 0.28),
                (-1.25, 0.28),
            )
        ),
        0.14,
    )
    for along in (-0.92, 0.92):
        leg_x = bench_x + forward_x * along
        leg_z = bench_z + forward_z * along
        _sweep(
            specs,
            "a21-r6-edge-story-grounded-bench-leg",
            "brass",
            group,
            (
                (
                    leg_x - right_x * 0.22,
                    0.14,
                    leg_z - right_z * 0.22,
                ),
                (
                    leg_x + right_x * 0.22,
                    0.70,
                    leg_z + right_z * 0.22,
                ),
            ),
            (0.045, 0.037, 0.030)[lod],
            (7, 6, 4)[lod],
        )
    bucket_x = bench_x - right_x * 0.86
    bucket_z = bench_z - right_z * 0.86
    _cylinder(
        specs,
        "a21-r6-edge-story-gardener-bucket",
        "carved_stone",
        group,
        bucket_x,
        0.40,
        bucket_z,
        0.36,
        0.68,
        (12, 8, 6)[lod],
        top_radius=0.44,
    )

    # Small paired threshold lamps mark the bridge but remain below the palace
    # terrace base and outside the centre twenty percent of the image.
    for side in (-8.25, 8.25):
        lamp_x, lamp_z = _corridor_point(0.115, side)
        _sweep(
            specs,
            "a21-r6-bridge-edge-slender-lantern-post",
            "brass",
            group,
            ((lamp_x, 0.28, lamp_z), (lamp_x, 2.30, lamp_z)),
            (0.038, 0.032, 0.026)[lod],
            (8, 6, 4)[lod],
        )
        _chamfer_box(
            specs,
            "a21-r6-bridge-edge-warm-lantern",
            "warm_glow",
            group,
            lamp_x,
            2.43,
            lamp_z,
            0.36,
            0.44,
            0.36,
            0.045,
            1,
        )


def _add_r6_foreground_edge_gardens_and_water(
    specs: list[dict],
    lod: int,
) -> None:
    """Fill the lower edges with low gardens while preserving the centre."""
    group = "a21-r6-nakaniwa-foreground-edge-gardens-water"

    # Broad parallel reflecting basins make the canal legible from eye height.
    # Their inner banks leave a nine-metre dry route through the centre.
    basin_half_width = 3.10
    for basin_side in (-9.6, 9.6):
        basin_quad = _r5_corridor_quad(
            -0.18,
            basin_side,
            0.06,
            28.2,
            basin_half_width,
        )
        _panel(
            specs,
            "a21-r6-foreground-submerged-dark-stone-canal-bed",
            "wet_stone",
            group,
            basin_quad,
            (0.12, 0.10, 0.08)[lod],
        )
        _panel(
            specs,
            "a21-r6-foreground-long-reflecting-canal-basin",
            "water",
            group,
            _r5_corridor_quad(
                -0.18,
                basin_side,
                0.17,
                28.2,
                basin_half_width,
            ),
            (0.070, 0.055, 0.043)[lod],
        )
        for bank_side in (
            basin_side - math.copysign(3.32, basin_side),
            basin_side + math.copysign(3.32, basin_side),
        ):
            bank_start = _corridor_point(-0.485, bank_side)
            bank_end = _corridor_point(0.125, bank_side)
            _sweep(
                specs,
                "a21-r6-foreground-canal-carved-coping-line",
                "carved_stone",
                group,
                (
                    (bank_start[0], 0.34, bank_start[1]),
                    (bank_end[0], 0.34, bank_end[1]),
                ),
                (0.080, 0.065, 0.052)[lod],
                (8, 6, 4)[lod],
            )
        for sill_index, sill_t in enumerate((-0.345, -0.225, -0.015)):
            if lod == 2 and sill_index == 1:
                continue
            _panel(
                specs,
                "a21-r6-foreground-canal-three-depth-break-stone-sill",
                "ivory_stone" if sill_index == 1 else "carved_stone",
                group,
                _r5_corridor_quad(
                    sill_t,
                    basin_side,
                    0.31 + 0.03 * sill_index,
                    0.48,
                    basin_half_width + 0.18,
                ),
                (0.18, 0.15, 0.12)[lod],
            )
    lily_sites = (
        (-0.34, 9.4),
        (-0.26, -10.2),
        (-0.12, 8.8),
        (0.02, -9.5),
    )
    for lily_index, (t, side) in enumerate(
        lily_sites[: (4, 3, 2)[lod]]
    ):
        lily_x, lily_z = _corridor_point(t, side)
        _leaf_cluster(
            specs,
            "a21-r6-foreground-water-lily-reflection-cluster",
            "flower" if lily_index % 2 else "foliage_light",
            group,
            lily_x,
            0.29,
            lily_z,
            1.35,
            0.22,
            (20, 11, 6)[lod],
            36600 + lily_index,
        )

    # A low transverse deck explains the water crossing.  The centre remains
    # unobstructed; its posts and lamps are restricted to the outer thirds.
    _panel(
        specs,
        "a21-r6-foreground-readable-garden-bridge-deck",
        "ivory_stone",
        group,
        _r5_corridor_quad(-0.105, 0.0, 1.30, 2.75, 15.4),
        (0.38, 0.31, 0.25)[lod],
    )
    bridge_forward_x, bridge_forward_z, bridge_right_x, bridge_right_z = (
        _r5_corridor_basis(-0.105)
    )
    bridge_centre_x, bridge_centre_z = _corridor_point(-0.105)
    for forward_sign in (-1.0, 1.0):
        edge_x = bridge_centre_x + bridge_forward_x * 2.60 * forward_sign
        edge_z = bridge_centre_z + bridge_forward_z * 2.60 * forward_sign
        _sweep(
            specs,
            "a21-r6-foreground-bridge-carved-threshold-edge",
            "carved_stone",
            group,
            (
                (
                    edge_x - bridge_right_x * 15.0,
                    1.42,
                    edge_z - bridge_right_z * 15.0,
                ),
                (
                    edge_x + bridge_right_x * 15.0,
                    1.42,
                    edge_z + bridge_right_z * 15.0,
                ),
            ),
            (0.085, 0.068, 0.052)[lod],
            (8, 6, 4)[lod],
        )
    near_edge_x = bridge_centre_x - bridge_forward_x * 2.76
    near_edge_z = bridge_centre_z - bridge_forward_z * 2.76
    for arch_index, side_offset in enumerate((-9.4, 0.0, 9.4)):
        arch_x = near_edge_x + bridge_right_x * side_offset
        arch_z = near_edge_z + bridge_right_z * side_offset
        _add_oriented_arch(
            specs,
            group=group,
            role="a21-r6-foreground-bridge-three-readable-arches",
            centre_x=arch_x,
            centre_z=arch_z,
            axis_x=bridge_right_x,
            axis_z=bridge_right_z,
            half_width=3.35,
            base_y=0.08,
            spring_y=0.72,
            rise=0.52,
            segments=(16, 10, 6)[lod],
            radius=(0.18, 0.14, 0.11)[lod],
            sides=(8, 6, 4)[lod],
            material=(
                "carved_stone"
                if arch_index != 1
                else "ivory_stone"
            ),
        )
    for stair_index in range((5, 4, 3)[lod]):
        progress = stair_index / max(1, (5, 4, 3)[lod] - 1)
        _panel(
            specs,
            "a21-r6-foreground-bridge-shallow-approach-step",
            "carved_stone" if stair_index % 2 == 0 else "ivory_stone",
            group,
            _r5_corridor_quad(
                -0.185 + progress * 0.060,
                0.0,
                0.24 + progress * 0.82,
                1.38,
                4.45 - progress * 0.30,
            ),
            (0.22, 0.18, 0.15)[lod],
        )
    for side in (-13.8, 13.8):
        post_x, post_z = _corridor_point(-0.105, side)
        _sweep(
            specs,
            "a21-r6-foreground-bridge-outer-balustrade-post",
            "brass",
            group,
            ((post_x, 1.24, post_z), (post_x, 2.28, post_z)),
            (0.055, 0.045, 0.036)[lod],
            (8, 6, 4)[lod],
        )
        _chamfer_box(
            specs,
            "a21-r6-foreground-bridge-outer-warm-lantern",
            "warm_glow",
            group,
            post_x,
            2.42,
            post_z,
            0.38,
            0.45,
            0.38,
            0.045,
            1,
        )

    # Low, asymmetrical edge gardens occupy the two lower corners.  They frame
    # the heroes but never enter the centre twenty-two to seventy-eight percent.
    garden_sites = (
        (-0.345, 7.8, 7.8, 2.45, True),
        (-0.325, -19.2, 7.1, 2.35, False),
    )
    for garden_index, (t, side, half_forward, half_side, flowering) in enumerate(
        garden_sites
    ):
        _panel(
            specs,
            "a21-r6-foreground-edge-layered-stone-planter",
            "carved_stone",
            group,
            _r5_corridor_quad(t, side, 0.62, half_forward, half_side),
            (0.76, 0.62, 0.50)[lod],
        )
        _panel(
            specs,
            "a21-r6-foreground-edge-dark-garden-soil",
            "wet_stone",
            group,
            _r5_corridor_quad(
                t,
                side,
                1.04,
                half_forward - 0.38,
                half_side - 0.34,
            ),
            0.12,
        )
        centre_x, centre_z = _corridor_point(t, side)
        tree_t = t + (0.028 if garden_index == 0 else -0.012)
        tree_side = side + (6.5 if garden_index == 0 else -4.2)
        tree_x, tree_z = _corridor_point(tree_t, tree_side)
        _tree(
            specs,
            group=group,
            role="a21-r6-foreground-edge-small-flowering-tree",
            x=tree_x,
            z=tree_z,
            height=5.65 + garden_index * 0.40,
            crown=2.25 + garden_index * 0.20,
            lod=lod,
            seed=36700 + garden_index,
            flowering=flowering,
        )
        for canopy_index, (offset_forward, offset_side, material) in enumerate(
            (
                (-0.75, -0.35, "foliage_dark"),
                (0.55, 0.45, "foliage_light"),
                (0.10, -0.10, "flower" if flowering else "foliage_dark"),
            )
        ):
            tree_forward_x, tree_forward_z, tree_right_x, tree_right_z = (
                _r5_corridor_basis(tree_t)
            )
            canopy_x = (
                tree_x
                + tree_forward_x * offset_forward
                + tree_right_x * offset_side
            )
            canopy_z = (
                tree_z
                + tree_forward_z * offset_forward
                + tree_right_z * offset_side
            )
            _leaf_cluster(
                specs,
                "a21-r6-foreground-edge-readable-dense-canopy",
                material,
                group,
                canopy_x,
                4.55 + canopy_index * 0.32 + garden_index * 0.18,
                canopy_z,
                (
                    2.05 + 0.18 * canopy_index
                    if garden_index == 0
                    else 2.35 + 0.20 * canopy_index
                ),
                1.85,
                (88, 42, 6)[lod],
                36950 + garden_index * 10 + canopy_index,
            )
        for flower_index in range((7, 5, 3)[lod]):
            along = (
                -half_forward * 0.72
                + flower_index
                * half_forward
                * 1.44
                / max(1, (7, 5, 3)[lod] - 1)
            )
            forward_x, forward_z, right_x, right_z = _r5_corridor_basis(t)
            flower_x = (
                centre_x
                + forward_x * along
                + right_x * (-0.35 if garden_index == 0 else 0.40)
            )
            flower_z = (
                centre_z
                + forward_z * along
                + right_z * (-0.35 if garden_index == 0 else 0.40)
            )
            _leaf_cluster(
                specs,
                "a21-r6-foreground-edge-dense-flower-border",
                "flower" if (flower_index + garden_index) % 3 == 0
                else "foliage_light",
                group,
                flower_x,
                1.32,
                flower_z,
                0.88,
                0.66,
                (20, 11, 6)[lod],
                36800 + garden_index * 20 + flower_index,
            )

        # An outer low stone balustrade gives a near/mid-scale ruler without
        # producing a parapet across the player's centre route.
        rail_side = side + (2.55 if side > 0.0 else -2.55)
        rail_start = _corridor_point(t - 0.085, rail_side)
        rail_end = _corridor_point(t + 0.085, rail_side)
        _sweep(
            specs,
            "a21-r6-foreground-edge-low-stone-balustrade-rail",
            "ivory_stone",
            group,
            (
                (rail_start[0], 1.72, rail_start[1]),
                (rail_end[0], 1.72, rail_end[1]),
            ),
            (0.105, 0.085, 0.065)[lod],
            (8, 6, 4)[lod],
        )
        for post_index in range((6, 4, 3)[lod]):
            progress = post_index / max(1, (6, 4, 3)[lod] - 1)
            post_t = t - 0.085 + progress * 0.17
            post_x, post_z = _corridor_point(post_t, rail_side)
            _chamfer_box(
                specs,
                "a21-r6-foreground-edge-low-stone-baluster",
                "carved_stone",
                group,
                post_x,
                1.20,
                post_z,
                0.34,
                1.18,
                0.34,
                (0.042, 0.034, 0.028)[lod],
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
    _remove_r5_visual_blockers(specs)
    _add_r5_foreground_canal_route(specs, lod)
    _add_r5_palace_system(specs, lod)
    _add_r5_conservatory_open_base(specs, lod)
    _add_r5_garden_city_depth(specs, lod)
    _remove_r6_visual_blockers(specs)
    _add_r6_palace_hero_scale(specs, lod)
    _add_r6_midground_roofed_facade_layers(specs, lod)
    _add_r6_midground_hanging_garden_spine(specs, lod)
    _add_r6_open_bridge_axis(specs, lod)
    _add_r6_foreground_edge_gardens_and_water(specs, lod)
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


def _project_spec_frame(
    spec: Mapping[str, object],
    camera: Mapping[str, object],
    aspect: float = 16.0 / 9.0,
) -> dict | None:
    """Project a spec AABB into the locked camera with conservative depth."""
    location, forward, right, up = _camera_basis(camera)

    def dot(a, b):
        return sum(a[index] * b[index] for index in range(3))

    tan_half_x = float(camera["sensorWidthMm"]) / (
        2.0 * float(camera["lensMm"])
    )
    tan_half_y = tan_half_x / aspect
    bounds = spec_bounds(spec)
    projected = []
    for x in (bounds[0], bounds[3]):
        for y in (bounds[1], bounds[4]):
            for z in (bounds[2], bounds[5]):
                relative = (
                    x - location[0],
                    y - location[1],
                    z - location[2],
                )
                depth = dot(relative, forward)
                if depth <= 0.01:
                    continue
                projected.append((
                    0.5 + dot(relative, right) / depth / (2.0 * tan_half_x),
                    0.5 + dot(relative, up) / depth / (2.0 * tan_half_y),
                    depth,
                ))
    if not projected:
        return None
    return {
        "bounds": (
            min(point[0] for point in projected),
            min(point[1] for point in projected),
            max(point[0] for point in projected),
            max(point[1] for point in projected),
        ),
        "nearDepthM": min(point[2] for point in projected),
        "farDepthM": max(point[2] for point in projected),
    }


def reference_camera_frame_metrics(lod: int = 0,
                                   aspect: float = 16.0 / 9.0) -> dict:
    camera = MAIN_REFERENCE_CAMERA
    specs = build_specs(lod)
    heroes = []
    for landmark in LANDMARKS:
        frames = [
            frame
            for spec in specs
            if spec["group"] == landmark["id"]
            if (frame := _project_spec_frame(spec, camera, aspect)) is not None
        ]
        xs = [
            value
            for frame in frames
            for value in (frame["bounds"][0], frame["bounds"][2])
        ]
        ys = [
            value
            for frame in frames
            for value in (frame["bounds"][1], frame["bounds"][3])
        ]
        raw = (min(xs), min(ys), max(xs), max(ys))
        visible = (
            max(0.0, min(xs)), max(0.0, min(ys)),
            min(1.0, max(xs)), min(1.0, max(ys)),
        )
        fully_framed = (
            raw[0] >= -0.02
            and raw[1] >= -0.02
            and raw[2] <= 1.02
            and raw[3] <= 1.02
        )
        heroes.append({
            "id": landmark["id"],
            "rawFrameBounds": raw,
            "visibleFrameBounds": visible,
            "visibleFrameWidthRatio": max(0.0, visible[2] - visible[0]),
            "visibleFrameHeightRatio": max(0.0, visible[3] - visible[1]),
            "fullyFramed": fully_framed,
        })
    return {
        "camera": copy.deepcopy(camera),
        "heroes": heroes,
        "passed": (
            all(hero["visibleFrameWidthRatio"] >= 0.30 for hero in heroes)
            and all(hero["visibleFrameHeightRatio"] >= 0.30 for hero in heroes)
            and all(hero["fullyFramed"] for hero in heroes)
        ),
    }


def conservatory_five_vault_frame_report(lod: int = 0) -> dict:
    """Prove that every shell, rather than only their union, is in frame."""
    specs = build_specs(lod)
    vaults = []
    for vault_index in range(5):
        role = f"a21-conservatory-vault-{vault_index}-curved-primary-rib"
        frames = [
            frame
            for spec in specs
            if spec["role"] == role
            if (frame := _project_spec_frame(spec, MAIN_REFERENCE_CAMERA))
            is not None
        ]
        x0 = min(frame["bounds"][0] for frame in frames)
        y0 = min(frame["bounds"][1] for frame in frames)
        x1 = max(frame["bounds"][2] for frame in frames)
        y1 = max(frame["bounds"][3] for frame in frames)
        vaults.append({
            "index": vault_index,
            "rawFrameBounds": (x0, y0, x1, y1),
            "widthRatio": x1 - x0,
            "heightRatio": y1 - y0,
            "fullyFramed": (
                x0 >= -0.02 and y0 >= -0.02
                and x1 <= 1.02 and y1 <= 1.02
            ),
        })
    legacy_blockers = [
        str(spec["role"])
        for spec in specs
        if str(spec["role"]).startswith("a21-r3-mid-city-")
    ]
    return {
        "vaults": vaults,
        "legacyOpaqueBlockerCount": len(legacy_blockers),
        "legacyOpaqueBlockerRoles": sorted(set(legacy_blockers)),
        "passed": (
            len(vaults) == 5
            and all(item["fullyFramed"] for item in vaults)
            and all(item["widthRatio"] >= 0.04 for item in vaults)
            and all(item["heightRatio"] >= 0.10 for item in vaults)
            and not legacy_blockers
        ),
    }


def reference_camera_occlusion_report(lod: int = 0) -> dict:
    """Conservative depth-aware screen-grid estimate of hero occlusion."""
    specs = build_specs(lod)
    grid_w, grid_h = 96, 54

    def cells(frame_bounds):
        x0, y0, x1, y1 = frame_bounds
        ix0 = max(0, min(grid_w - 1, math.floor(x0 * grid_w)))
        iy0 = max(0, min(grid_h - 1, math.floor(y0 * grid_h)))
        ix1 = max(0, min(grid_w - 1, math.ceil(x1 * grid_w) - 1))
        iy1 = max(0, min(grid_h - 1, math.ceil(y1 * grid_h) - 1))
        if x1 <= 0.0 or y1 <= 0.0 or x0 >= 1.0 or y0 >= 1.0:
            return ()
        return (
            (ix, iy)
            for iy in range(iy0, iy1 + 1)
            for ix in range(ix0, ix1 + 1)
        )

    projected = [
        (spec, frame)
        for spec in specs
        if (frame := _project_spec_frame(spec, MAIN_REFERENCE_CAMERA))
        is not None
    ]
    heroes = []
    for landmark in LANDMARKS:
        target_depth: dict[tuple[int, int], float] = {}
        for spec, frame in projected:
            if spec["group"] != landmark["id"]:
                continue
            if spec_bounds(spec)[4] <= 4.0:
                continue
            for cell in cells(frame["bounds"]):
                target_depth[cell] = min(
                    target_depth.get(cell, math.inf),
                    float(frame["nearDepthM"]),
                )
        blocked = set()
        blocker_roles = set()
        for spec, frame in projected:
            if spec["group"] == landmark["id"]:
                continue
            if spec_bounds(spec)[4] <= 2.8:
                continue
            for cell in cells(frame["bounds"]):
                hero_depth = target_depth.get(cell)
                if hero_depth is None:
                    continue
                if float(frame["nearDepthM"]) + 0.75 < hero_depth:
                    blocked.add(cell)
                    blocker_roles.add(str(spec["role"]))
        ratio = len(blocked) / max(1, len(target_depth))
        heroes.append({
            "id": landmark["id"],
            "sampledHeroPixels": len(target_depth),
            "occludedPixels": len(blocked),
            "occlusionRatio": round(ratio, 4),
            "blockingRoles": sorted(blocker_roles),
            "passed": ratio <= 0.18,
        })
    return {
        "method": "conservative-aabb-depth-grid-96x54",
        "heroes": heroes,
        "passed": all(hero["passed"] for hero in heroes),
    }


def r6_foreground_occupancy_report(lod: int = 0) -> dict:
    """Measure central vertical foreground mass; low paving is excluded."""
    specs = build_specs(lod)
    grid_w, grid_h = 96, 54
    occupied = set()
    top = 0.0
    roles = set()
    for spec in specs:
        if spec_bounds(spec)[4] <= 1.25:
            continue
        frame = _project_spec_frame(spec, MAIN_REFERENCE_CAMERA)
        if frame is None or float(frame["nearDepthM"]) >= 65.0:
            continue
        x0, y0, x1, y1 = frame["bounds"]
        x0 = max(0.22, x0)
        x1 = min(0.78, x1)
        y0 = max(0.0, y0)
        y1 = min(1.0, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        roles.add(str(spec["role"]))
        top = max(top, y1)
        ix0 = max(0, math.floor(x0 * grid_w))
        ix1 = min(grid_w - 1, math.ceil(x1 * grid_w) - 1)
        iy0 = max(0, math.floor(y0 * grid_h))
        iy1 = min(grid_h - 1, math.ceil(y1 * grid_h) - 1)
        occupied.update(
            (ix, iy)
            for iy in range(iy0, iy1 + 1)
            for ix in range(ix0, ix1 + 1)
        )
    forbidden = [
        str(spec["role"])
        for spec in specs
        if any(
            str(spec["role"]).startswith(prefix)
            for prefix in R6_VISUAL_BLOCKER_PREFIXES
        )
    ]
    central_area_ratio = len(occupied) / (grid_w * grid_h)
    return {
        "method": "central-screen-depth-filtered-grid-96x54",
        "centralAreaRatio": round(central_area_ratio, 4),
        "maximumCentralVerticalTopRatio": round(top, 4),
        "contributingRoles": sorted(roles),
        "forbiddenRoleCount": len(forbidden),
        "forbiddenRoles": sorted(set(forbidden)),
        "passed": central_area_ratio <= 0.06 and not forbidden,
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


def locked_r4_report() -> dict:
    """Prove that the complete R4 source and primary evidence remain immutable."""
    artifacts = (
        ("source", R4_SOURCE_PATH, R4_SOURCE_SHA256),
        ("candidate", R4_CANDIDATE_PATH, R4_CANDIDATE_SHA256),
        ("manifest", R4_MANIFEST_PATH, R4_MANIFEST_SHA256),
        (
            "independent-review",
            R4_INDEPENDENT_REVIEW_PATH,
            R4_INDEPENDENT_REVIEW_SHA256,
        ),
    )
    reports = []
    for role, path, expected_sha256 in artifacts:
        exists = path.is_file()
        actual_sha256 = (
            hashlib.sha256(path.read_bytes()).hexdigest() if exists else None
        )
        reports.append({
            "role": role,
            "path": str(path),
            "expectedSha256": expected_sha256,
            "actualSha256": actual_sha256,
            "exists": exists,
            "matched": exists and actual_sha256 == expected_sha256,
        })
    return {
        "artifacts": reports,
        "matched": all(item["matched"] for item in reports),
        "writeAttempted": False,
    }


def locked_r5_report() -> dict:
    """Prove that the complete rejected R5 branch and evidence are immutable."""
    artifacts = (
        ("source", R5_SOURCE_PATH, R5_SOURCE_SHA256),
        ("test", R5_TEST_PATH, R5_TEST_SHA256),
        ("candidate", R5_CANDIDATE_PATH, R5_CANDIDATE_SHA256),
        ("manifest", R5_MANIFEST_PATH, R5_MANIFEST_SHA256),
    )
    reports = []
    for role, path, expected_sha256 in artifacts:
        exists = path.is_file()
        actual_sha256 = (
            hashlib.sha256(path.read_bytes()).hexdigest() if exists else None
        )
        reports.append({
            "role": role,
            "path": str(path),
            "expectedSha256": expected_sha256,
            "actualSha256": actual_sha256,
            "exists": exists,
            "matched": exists and actual_sha256 == expected_sha256,
        })
    return {
        "artifacts": reports,
        "matched": all(item["matched"] for item in reports),
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
    "composition": 4.8,
    "hero silhouettes": 5.2,
    "architectural grammar": 4.0,
    "human scale": 4.4,
    "material realism": 2.9,
    "near/mid/far density": 3.8,
    "gameplay readability": 6.0,
    "props and environmental storytelling": 3.6,
    "lighting and atmosphere": 3.1,
    "reference identity": 4.4,
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
        "audit": "hibana-independent-r4-baseline-carry-forward-v1",
        "stageId": STAGE_ID,
        "candidate": KIT_VERSION,
        "reviewer": "independent-baseline-carry-forward-no-self-rescore",
        "sourceScorecard": str(R4_INDEPENDENT_REVIEW_PATH),
        "sourceScorecardSha256": R4_INDEPENDENT_REVIEW_SHA256,
        "reference": {"path": str(REFERENCE_PATH), "sha256": REFERENCE_SHA256},
        "namedLandmarks": [item["referenceName"] for item in LANDMARKS],
        "scores": scores,
        "arithmeticMean": round(sum(values) / len(values), 2),
        "minimumCategoryScore": min(values),
        "evidencePaths": list(evidence_paths),
        "strongestRemainingMismatch": (
            "The fixed independent R4 4.22 baseline controls until a different "
            "reviewer compares the R6 candidate at original resolution."
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
            0.068 if pale_stone else 0.048 if stone_like else 0.020
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
                "ivory_stone": 0.34,
                "carved_stone": 0.40,
                "moss_stone": 0.28,
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
                ior_level.default_value = 0.08
            elif "glass" in role:
                ior_level.default_value = 0.46
        coat = shader.inputs.get("Coat Weight") or shader.inputs.get("Coat")
        if coat is not None:
            if "glass" in role:
                coat.default_value = 0.52
            elif role == "water":
                coat.default_value = 0.0
        coat_roughness = shader.inputs.get("Coat Roughness")
        if coat_roughness is not None:
            if "glass" in role:
                coat_roughness.default_value = 0.045
            elif role == "water":
                coat_roughness.default_value = 0.14
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
    sky.sun_elevation = math.radians(8.0)
    sky.sun_rotation = math.radians(228.0)
    sky.air_density = 1.28
    if hasattr(sky, "dust_density"):
        sky.dust_density = 4.0
    sky_coordinates = nodes.new("ShaderNodeTexCoord")
    cloud_mapping = nodes.new("ShaderNodeMapping")
    # Compress the world-normal texture along Blender Z so the breakup reads
    # as broad horizontal dusk layers instead of the previous vertical haze.
    cloud_mapping.inputs["Scale"].default_value = (1.35, 1.10, 5.40)
    cloud_noise = nodes.new("ShaderNodeTexNoise")
    cloud_noise.inputs["Scale"].default_value = 2.10
    cloud_noise.inputs["Detail"].default_value = 4.2
    cloud_noise.inputs["Roughness"].default_value = 0.56
    cloud_noise.inputs["Distortion"].default_value = 0.16
    cloud_ramp = nodes.new("ShaderNodeValToRGB")
    cloud_ramp.color_ramp.elements[0].position = 0.50
    cloud_ramp.color_ramp.elements[1].position = 0.68
    cloud_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    cloud_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    cloud_mix = nodes.new("ShaderNodeMixRGB")
    cloud_mix.blend_type = "SCREEN"
    cloud_mix.inputs[2].default_value = (0.62, 0.36, 0.20, 1.0)
    links.new(
        sky_coordinates.outputs["Normal"],
        cloud_mapping.inputs["Vector"],
    )
    links.new(
        cloud_mapping.outputs["Vector"],
        cloud_noise.inputs["Vector"],
    )
    links.new(cloud_noise.outputs["Fac"], cloud_ramp.inputs["Fac"])
    links.new(cloud_ramp.outputs["Color"], cloud_mix.inputs["Fac"])
    links.new(sky.outputs["Color"], cloud_mix.inputs[1])
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.08
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(cloud_mix.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])

    sun_data = bpy.data.lights.new("LGT_Nakaniwa_A21_Sun_DATA", "SUN")
    sun_data.energy = 5.40
    sun_data.angle = math.radians(0.45)
    sun_data.color = (1.0, 0.62, 0.32)
    sun_data.use_shadow = True
    sun = bpy.data.objects.new("LGT_Nakaniwa_A21_Sun", sun_data)
    lighting.objects.link(sun)
    sun.location = _runtime_to_blender((112.0, 120.0, -132.0))
    sun.rotation_euler = (
        _runtime_to_blender((-8.0, 8.0, -2.0)) - sun.location
    ).to_track_quat("-Z", "Y").to_euler()

    fill_data = bpy.data.lights.new("LGT_Nakaniwa_A21_CoolFill_DATA", "AREA")
    fill_data.energy = 2.2
    fill_data.shape = "DISK"
    fill_data.size = 78.0
    fill_data.color = (0.30, 0.40, 0.60)
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
    bounce_data.energy = 130.0
    bounce_data.shape = "DISK"
    bounce_data.size = 52.0
    bounce_data.color = (1.0, 0.40, 0.14)
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
        ("PalaceCrown", (-45.0, 36.5, -55.0), 820.0, 9.0),
        ("ConservatoryEntry", (52.0, 7.0, 30.0), 620.0, 8.0),
        ("ConservatoryGarden", (52.0, 10.0, 64.0), 860.0, 11.0),
        ("GardenBridge", (47.0, 3.0, -84.0), 410.0, 6.0),
    )
    for name, location, energy, radius in practicals:
        data = bpy.data.lights.new(f"LGT_Nakaniwa_A21_{name}_DATA", "POINT")
        data.energy = energy * 0.86
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
    locked_r4 = locked_r4_report()
    if not locked_r4["matched"]:
        raise RuntimeError(f"immutable R4 evidence hash mismatch: {locked_r4}")
    locked_r5 = locked_r5_report()
    if not locked_r5["matched"]:
        raise RuntimeError(f"immutable R5 evidence hash mismatch: {locked_r5}")
    intrusion_reports = [gameplay_intrusion_report(lod) for lod in range(3)]
    if not all(report["passed"] for report in intrusion_reports):
        raise RuntimeError(f"A21 route/spawn/camera intrusion: {intrusion_reports}")
    composition_reports = {
        "frame": reference_camera_frame_metrics(0),
        "occlusion": reference_camera_occlusion_report(0),
        "fiveVaults": conservatory_five_vault_frame_report(0),
        "foreground": r6_foreground_occupancy_report(0),
    }
    if not all(report["passed"] for report in composition_reports.values()):
        raise RuntimeError(f"A21 R6 composition gate failed: {composition_reports}")
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
        "lockedR4": locked_r4,
        "lockedR5": locked_r5,
        "canonicalContract": contract,
        "exactLandmarkCount": 2,
        "landmarkIds": [item["id"] for item in LANDMARKS],
        "mainReferenceCamera": MAIN_REFERENCE_CAMERA,
        "heroFrameMetrics": reference_camera_frame_metrics(0),
        "heroOcclusionMetrics": reference_camera_occlusion_report(0),
        "conservatoryFiveVaultFrameReport": (
            conservatory_five_vault_frame_report(0)
        ),
        "foregroundOccupancyReport": r6_foreground_occupancy_report(0),
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
            "heroOcclusionMetrics": reference_camera_occlusion_report(0),
            "conservatoryFiveVaultFrameReport": (
                conservatory_five_vault_frame_report(0)
            ),
            "foregroundOccupancyReport": r6_foreground_occupancy_report(0),
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
            "heroOcclusionMetrics": reference_camera_occlusion_report(0),
            "conservatoryFiveVaultFrameReport": (
                conservatory_five_vault_frame_report(0)
            ),
            "foregroundOccupancyReport": r6_foreground_occupancy_report(0),
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
    "conservatory_five_vault_frame_report",
    "emit_specs_to_builder",
    "emit_to_builder",
    "estimated_triangles",
    "gameplay_intrusion_report",
    "independent_baseline_scorecard",
    "locked_r3_scorecard_report",
    "locked_r4_report",
    "locked_r5_report",
    "plan_metrics",
    "producer_provisional_scorecard",
    "reference_camera_frame_metrics",
    "reference_camera_occlusion_report",
    "r6_foreground_occupancy_report",
    "spec_bounds",
]


if __name__ == "__main__":
    raise SystemExit(main())
