"""Kunren A22 macro-first private production-art rebuild.

This module is intentionally isolated from public assets and runtime source.
It preserves the canonical 310 m stage, routes, spawns, collision shell and
exact two landmark identities while replacing A21's weak visual read with:

* a stepped, buttressed and occupied Command Bastion;
* a double-shell working Aerostat Vault Hangar;
* a compressed high-rise military district with connected roof language;
* real vehicle silhouettes, an inhabited checkpoint and service crews;
* dense, non-wedge alpine ridge meshes and evening atmospheric separation;
* physically plausible procedural concrete, steel, asphalt and rock response.

Connection map (declared before Blender geometry emission):

* command glacis/buttresses -> canonical command plinth: 0.18-0.30 m;
* command deep portals -> plinth/keep backing mass: 0.10-0.18 m;
* command galleries/crown -> keep/crown: 0.10-0.20 m;
* hangar portal shells -> canonical hall floor: 0.20-0.30 m;
* hangar ribs/cladding -> adjacent ribs/service towers: 0.10-0.18 m;
* docking arms/crane rails -> shell/aerostat envelope: 0.08-0.16 m;
* district exoskeletons/roofs -> solver-anchored district masses: 0.10-0.18 m;
* vehicle body/cabin/wheels -> chassis/axles: 0.08-0.14 m;
* checkpoint walls/roof/fixtures -> grounded slab: 0.08-0.14 m.

The producer score remains provisional.  A22 is always NO-SHIP until a
different reviewer performs the fixed ten-category original-resolution gate.
"""

from __future__ import annotations

from dataclasses import asdict, replace
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable, Mapping, Sequence


_FALLBACK_SCRIPT_PATH = Path(
    "/Users/h_miruky/Library/Mobile Documents/com~apple~CloudDocs/develop/"
    "100リポジトリ作成計画トップ/hibana/tools/blender/stage_kits/"
    "kunren_reference_a22.py"
)
SCRIPT_PATH = Path(globals().get("__file__", _FALLBACK_SCRIPT_PATH)).resolve()
REPO_ROOT = SCRIPT_PATH.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import kunren_reference_a19 as a19  # noqa: E402
from tools.blender.stage_kits import kunren_reference_a20 as a20  # noqa: E402
from tools.blender.stage_kits import kunren_reference_a21 as a21  # noqa: E402
from tools.blender.stage_kits.kunren_reference_a18 import (  # noqa: E402
    ApproachSpec,
    COMMAND_ID,
    HANGAR_ID,
    KunrenPlan,
    LODBudget,
    MeshBuilderProtocol,
    REFERENCE_IMAGE_SHA256,
    constraints_from_authoritative_layout,
    load_authoritative_kunren_layout,
)
from tools.blender.stage_kits.kunren_reference_a19 import (  # noqa: E402
    FIXED_SCORE_CATEGORIES,
    ReferenceCamera,
    camera_hero_frame_metrics,
)


KIT_VERSION = "kunren-reference-a22-v4-a"
PRIVATE_PROOF_DEFAULT = Path("/private/tmp/hibana-blender/a22-kunren-production-art")
CANONICAL_LAYOUT_DEFAULT = Path(
    "/private/tmp/hibana-blender/canonical-stage-layouts.json"
)
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/kunren-reference-v1.png"
A21_IMAGEGEN_REFERENCE_PATH = Path(
    "/private/tmp/hibana-blender/a21-kunren-production-art/concepts/"
    "kunren-a21-imagegen-reference.png"
)
IMAGEGEN_REFERENCE_PATH = (
    PRIVATE_PROOF_DEFAULT / "concepts/kunren-a22-imagegen-reference.png"
)
IMAGEGEN_REFERENCE_SHA256 = a21.IMAGEGEN_REFERENCE_SHA256
Point3 = tuple[float, float, float]


A22_LOD_BUDGETS: dict[int, LODBudget] = {
    0: LODBudget(2_520, 240_000, 12),
    1: LODBudget(1_520, 85_000, 12),
    2: LODBudget(720, 25_000, 12),
}

A22_EVALUATED_TRIANGLE_TARGETS: dict[int, tuple[int, int]] = {
    0: (160_000, 240_000),
    1: (45_000, 85_000),
    2: (12_000, 25_000),
}

REFERENCE_HERO_OCCUPANCY_TARGETS = {
    COMMAND_ID: {
        "screenWidth": 0.28,
        "screenHeight": 0.58,
        "tolerance": 0.12,
    },
    HANGAR_ID: {
        "screenWidth": 0.41,
        "screenHeight": 0.58,
        "tolerance": 0.14,
    },
}

REFERENCE_DEPTH_DENSITY_TARGET = {
    "near": 0.25,
    "mid": 0.50,
    "far": 0.25,
}

SUPPRESSED_A21_PREFIXES = (
    "a20.story.foreground-vehicle.",
    "a20.hall.vehicle.",
    "a19.hall.maintenance-cart.",
    "a21.story.foreground-vehicle.",
    "cmd.aperture.",
    "cmd.facade.bay.",
    "a19.cmd.facade.bay.",
    "a19.cmd.forward-keep.aperture.",
    "a20.cmd.hero-citadel.aperture.",
    "a20.cmd.aperture.south.",
    "a21.cmd.south.service-bay.",
    # Visual-only inherited route furniture that sat directly between the
    # fixed proof cameras and the Command portal.  Gameplay collision and the
    # authoritative approach remain untouched.
    "a19.route.retaining.right.1",
    "a19.route.lower-service-rail.",
    "city.block.6.",
    "a20.district.terrace-building.2",
    "a20.district.terrace-building.4",
)


MAIN_REFERENCE_CAMERA = ReferenceCamera(
    name="CAM_Kunren_A22_ReferenceDual_1p65",
    location=(177.4, 1.65, -185.1),
    target=(-6.0, 31.0, -8.0),
    lens_mm=22.0,
    resolution_x=1280,
    resolution_y=720,
    eye_height_m=1.65,
    intent="compressed-evening-command-left-vault-hangar-right",
)

COMMAND_HERO_CAMERA = ReferenceCamera(
    name="CAM_Kunren_A22_CommandApproach_1p65",
    location=(-45.0, 1.65, 84.0),
    target=(73.0, 36.0, 84.0),
    lens_mm=24.0,
    resolution_x=1280,
    resolution_y=720,
    eye_height_m=1.65,
    intent="route-front-diagnostic-of-keep-gate-towers-and-radar-crown",
)

DUAL_LATERAL_DIAGNOSTIC_CAMERAS = {
    "dual-lateral-21a": ReferenceCamera(
        name="CAM_Kunren_A22_DualLateral21A_1p65",
        location=(120.0, 1.65, -140.0),
        target=(-6.0, 22.0, -8.0),
        lens_mm=21.0,
        resolution_x=1280,
        resolution_y=720,
        eye_height_m=1.65,
        intent="lateral-route-trial-a-command-gate-and-vault",
    ),
    "dual-lateral-21b": ReferenceCamera(
        name="CAM_Kunren_A22_DualLateral21B_1p65",
        location=(125.0, 1.65, -135.0),
        target=(-2.0, 22.0, -6.0),
        lens_mm=21.0,
        resolution_x=1280,
        resolution_y=720,
        eye_height_m=1.65,
        intent="lateral-route-trial-b-command-gate-and-vault",
    ),
    "hero-up-22a": ReferenceCamera(
        name="CAM_Kunren_A22_HeroUp22A_1p65",
        location=(140.0, 1.65, -140.0),
        target=(-6.0, 32.0, -8.0),
        lens_mm=22.0,
        resolution_x=1280,
        resolution_y=720,
        eye_height_m=1.65,
        intent="raised-aim-trial-reducing-empty-foreground",
    ),
    "hero-up-21b": ReferenceCamera(
        name="CAM_Kunren_A22_HeroUp21B_1p65",
        location=(136.0, 1.65, -145.0),
        target=(-6.0, 35.0, -8.0),
        lens_mm=21.0,
        resolution_x=1280,
        resolution_y=720,
        eye_height_m=1.65,
        intent="raised-aim-wide-trial-for-dual-castle-occupancy",
    ),
    "hero-frame-20c": ReferenceCamera(
        name="CAM_Kunren_A22_HeroFrame20C_1p65",
        location=(136.0, 1.65, -145.0),
        target=(-6.0, 31.0, -8.0),
        lens_mm=20.0,
        resolution_x=1280,
        resolution_y=720,
        eye_height_m=1.65,
        intent="wide-dense-foreground-trial-with-complete-dual-heroes",
    ),
}


PRODUCER_PROVISIONAL_SCORES: dict[str, float] = {
    "composition": 7.8,
    "hero silhouettes": 8.0,
    "architectural grammar": 7.9,
    "human scale": 7.7,
    "material realism": 7.6,
    "near/mid/far density": 7.8,
    "gameplay readability": 7.8,
    "props and environmental storytelling": 7.7,
    "lighting and atmosphere": 7.7,
    "reference identity": 7.9,
}


def _connect(
    assembler: a20._A20Assembler,
    name: str,
    parent: str,
    child: str,
    kind: str,
    axis: str,
    overlap: float,
    note: str = "",
) -> None:
    assembler.connect(
        name,
        parent,
        child,
        kind,
        axis,
        overlap,
        note,
    )


def _add_command_macro_rebuild(
    assembler: a20._A20Assembler,
    hero: Any,
    lod: int,
) -> None:
    """Give the command hero a fortress silhouette and real opening depth."""

    x, z = hero.cx, hero.cz
    west_face = x - hero.width / 2.0

    # The canonical approach reaches the west face at (28, 84).  Every
    # entrance-defining mass therefore uses west-face depth along X and
    # facade width along Z.  A21/A20's south-facing gate grammar was the root
    # cause of the route-front view reading as one blank side wall.
    glacis_panels = (
        (
            "south",
            (
                (west_face - 7.2, 0.12, z - 43.0),
                (west_face - 7.2, 0.12, z - 11.0),
                (west_face + 1.0, 19.5, z - 8.0),
                (west_face + 1.0, 19.5, z - 34.0),
            ),
        ),
        (
            "north",
            (
                (west_face - 7.2, 0.12, z + 11.0),
                (west_face - 7.2, 0.12, z + 43.0),
                (west_face + 1.0, 19.5, z + 34.0),
                (west_face + 1.0, 19.5, z + 8.0),
            ),
        ),
    )
    for label, corners in glacis_panels:
        name = f"a22.cmd.glacis.{label}"
        assembler.panel(
            name,
            corners,
            0.92,
            "wall_weathered",
            role="command-castle-scale-sloped-glacis",
        )
        _connect(
            assembler,
            f"contact.{name}",
            "a20.cmd.hero-citadel.plinth",
            name,
            "glacis-plinth-seat",
            "z",
            0.24,
        )

    # The central portal is a 5 m-deep open geometric bay aligned to the
    # canonical west approach.  Its cool backing wall sits behind a real
    # jamb/header volume rather than acting as a near-coplanar black card.
    portal_back = "a22.cmd.main-portal.interior-back"
    assembler.box(
        portal_back,
        west_face + 9.8,
        6.2,
        z,
        0.64,
        11.8,
        12.4,
        "wall_warm",
        role="command-deep-portal-interior-back-wall",
        route_exempt=True,
    )
    portal_parts = (
        ("south-jamb", z - 7.1, 6.4, 2.0, 12.8, 6.6),
        ("north-jamb", z + 7.1, 6.4, 2.0, 12.8, 6.6),
        ("header", z, 12.4, 16.2, 1.6, 6.6),
    )
    for label, pz, py, depth, height, width in portal_parts:
        name = f"a22.cmd.main-portal.{label}"
        assembler.box(
            name,
            west_face + 2.9,
            py,
            pz,
            width,
            height,
            depth,
            "trim" if label != "header" else "wall_warm",
            role="command-deep-portal-load-bearing-frame",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{name}",
            portal_back,
            name,
            "portal-volume-seat",
            "z",
            0.14,
        )
    portal_floor = "a22.cmd.main-portal.floor"
    assembler.box(
        portal_floor,
        west_face + 4.7,
        0.12,
        z,
        10.0,
        0.24,
        12.4,
        "road",
        role="command-grounded-deep-portal-floor",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{portal_floor}",
        portal_back,
        portal_floor,
        "portal-floor-back-seat",
        "z",
        0.12,
    )
    for index, offset in enumerate((-3.5, 0.0, 3.5)):
        light = f"a22.cmd.main-portal.practical.{index}"
        assembler.box(
            light,
            west_face + 9.25,
            10.7,
            z + offset,
            0.30,
            0.22,
            2.8,
            "accent",
            role="command-portal-motivated-practical-fixture",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{light}",
            portal_back,
            light,
            "fixture-back-wall-seat",
            "z",
            0.08,
        )

    # Four upper occupied bays use visible jamb depth and warm inner backing.
    bay_count = 4 if lod == 0 else 3 if lod == 1 else 2
    for index in range(bay_count):
        bay_z = z - 18.0 + index * (36.0 / max(1, bay_count - 1))
        base_y = 25.0 + (index % 2) * 5.0
        prefix = f"a22.cmd.occupied-bay.{index}"
        back = f"{prefix}.back"
        assembler.box(
            back,
            west_face + 5.4,
            base_y,
            bay_z,
            0.48,
            4.8,
            7.2,
            "wall_warm",
            role="command-recessed-occupied-room-back",
            route_exempt=True,
        )
        for label, pz, py, depth, height in (
            ("south", bay_z - 4.2, base_y, 0.72, 5.8),
            ("north", bay_z + 4.2, base_y, 0.72, 5.8),
            ("header", bay_z, base_y + 2.7, 9.0, 0.62),
            ("sill", bay_z, base_y - 2.7, 9.0, 0.52),
        ):
            name = f"{prefix}.frame.{label}"
            assembler.box(
                name,
                west_face + 2.6,
                py,
                pz,
                5.8,
                height,
                depth,
                "trim",
                role="command-deep-opening-structural-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{name}",
                back,
                name,
                "deep-bay-frame-seat",
                "z",
                0.12,
            )
        interior = f"{prefix}.interior-light"
        assembler.box(
            interior,
            west_face + 4.95,
            base_y - 1.7,
            bay_z,
            0.30,
            0.24,
            5.4,
            "wall_warm",
            role="command-occupied-bay-motivated-interior-light",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{interior}",
            back,
            interior,
            "interior-light-back-seat",
            "z",
            0.08,
        )

    # A new three-tier monumental keep rises above the surrounding district.
    # The broad lower mass, narrower command tier and asymmetric radar tower
    # produce one castle-scale load path instead of a low collection of boxes.
    lower_keep = "a22.cmd.monumental-keep.lower-core"
    assembler.box(
        lower_keep,
        west_face + 33.0,
        15.2,
        z,
        40.0,
        30.0,
        54.0,
        "wall_weathered",
        role="command-monumental-grounded-lower-keep",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{lower_keep}",
        "a20.cmd.hero-citadel.plinth",
        lower_keep,
        "monumental-keep-foundation-embed",
        "y",
        0.28,
    )
    middle_keep = "a22.cmd.monumental-keep.middle-operations-tier"
    assembler.box(
        middle_keep,
        west_face + 48.0,
        44.0,
        z,
        24.0,
        28.0,
        40.0,
        "wall",
        role="command-monumental-stepped-operations-tier",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{middle_keep}",
        lower_keep,
        middle_keep,
        "command-tier-structural-seat",
        "y",
        0.22,
    )
    upper_keep = "a22.cmd.monumental-keep.asymmetric-radar-tower"
    assembler.box(
        upper_keep,
        west_face + 57.0,
        70.0,
        z + 8.0,
        18.0,
        24.0,
        22.0,
        "wall_weathered",
        role="command-monumental-asymmetric-radar-tower",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{upper_keep}",
        middle_keep,
        upper_keep,
        "radar-tower-operations-tier-seat",
        "y",
        0.20,
    )
    crown_deck = "a22.cmd.monumental-keep.armoured-crown-deck"
    assembler.box(
        crown_deck,
        west_face + 57.0,
        82.2,
        z + 8.0,
        22.0,
        0.72,
        27.0,
        "roof",
        role="command-monumental-armoured-crown-deck",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{crown_deck}",
        upper_keep,
        crown_deck,
        "armoured-crown-tower-seat",
        "y",
        0.12,
    )
    keep_fin_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(keep_fin_count):
        fin_z = z - 20.0 + index * (40.0 / max(1, keep_fin_count - 1))
        fin = f"a22.cmd.monumental-keep.west-load-fin.{index}"
        assembler.beam(
            fin,
            (west_face + 12.2, 0.20, fin_z),
            (west_face + 14.0, 29.8, fin_z),
            0.92,
            1.20,
            "trim",
            role="command-keep-readable-west-vertical-load-fin",
        )
        _connect(
            assembler,
            f"contact.{fin}",
            lower_keep,
            fin,
            "command-keep-load-fin-wall-seat",
            "endpoint",
            0.14,
        )
    tier_bay_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index in range(tier_bay_count):
        bay_z = z - 10.0 + index * (20.0 / max(1, tier_bay_count - 1))
        bay_back = f"a22.cmd.monumental-keep.operations-bay.{index}.back"
        assembler.box(
            bay_back,
            west_face + 36.6,
            45.0,
            bay_z,
            0.40,
            4.4,
            5.4,
            "wall_warm",
            role="command-keep-deep-occupied-operations-bay-back",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{bay_back}",
            middle_keep,
            bay_back,
            "command-keep-operations-bay-wall-recess",
            "x",
            0.10,
        )
        hood = f"a22.cmd.monumental-keep.operations-bay.{index}.hood"
        assembler.box(
            hood,
            west_face + 35.6,
            47.5,
            bay_z,
            2.2,
            0.42,
            6.4,
            "roof",
            role="command-keep-operations-bay-armoured-hood",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{hood}",
            bay_back,
            hood,
            "command-keep-bay-hood-back-seat",
            "x",
            0.08,
        )
    # The main dual-hero camera sees the south flank.  Deep operations bays
    # and true battered load fins make that view read as the same fortress,
    # while the immutable gameplay entrance remains on the west face.
    south_face = z - 27.0
    south_buttress_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(south_buttress_count):
        buttress_x = (
            west_face + 17.0 + index * (34.0 / max(1, south_buttress_count - 1))
        )
        buttress = f"a22.cmd.monumental-keep.south-buttress.{index}"
        assembler.beam(
            buttress,
            (buttress_x, 0.20, south_face - 2.2),
            (buttress_x, 29.8, south_face + 3.2),
            0.88,
            1.22,
            "trim",
            role="command-keep-south-battered-load-buttress",
        )
        _connect(
            assembler,
            f"contact.{buttress}",
            lower_keep,
            buttress,
            "command-keep-south-buttress-wall-seat",
            "endpoint",
            0.14,
        )
    south_bay_count = 4 if lod == 0 else 3 if lod == 1 else 2
    for index in range(south_bay_count):
        bay_x = west_face + 19.0 + index * (30.0 / max(1, south_bay_count - 1))
        bay_y = 16.0 + (index % 2) * 6.0
        back = f"a22.cmd.monumental-keep.south-operations-bay.{index}.back"
        assembler.box(
            back,
            bay_x,
            bay_y,
            south_face + 1.65,
            6.0,
            4.2,
            0.42,
            "wall_warm",
            role="command-south-flank-deep-occupied-operations-bay-back",
            route_exempt=True,
        )
        for frame_label, frame_x, frame_y, frame_width, frame_height in (
            ("west", bay_x - 3.7, bay_y, 0.54, 5.2),
            ("east", bay_x + 3.7, bay_y, 0.54, 5.2),
            ("header", bay_x, bay_y + 2.45, 8.0, 0.46),
            ("sill", bay_x, bay_y - 2.45, 8.0, 0.42),
        ):
            frame = (
                f"a22.cmd.monumental-keep.south-operations-bay."
                f"{index}.frame.{frame_label}"
            )
            assembler.box(
                frame,
                frame_x,
                frame_y,
                south_face + 0.55,
                frame_width,
                frame_height,
                1.8,
                "trim",
                role="command-south-flank-deep-operations-bay-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{frame}",
                back,
                frame,
                "command-south-operations-bay-frame-seat",
                "z",
                0.10,
            )

    # Camera-facing reinforced-concrete panel hierarchy on the lower keep.
    # These are shallow real joints and service attachments, not texture-only
    # lines, so the large south wall keeps scale at the frozen 1.65 m view.
    seam_levels = (6.0, 12.0, 18.0, 24.0) if lod < 2 else ()
    for index, seam_y in enumerate(seam_levels):
        seam = f"a22.cmd.monumental-keep.south-panel-seam.horizontal.{index}"
        assembler.box(
            seam,
            west_face + 33.0,
            seam_y,
            south_face - 0.28,
            39.0,
            0.16,
            0.48,
            "trim",
            role="command-south-keep-recessed-formwork-panel-seam",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{seam}",
            lower_keep,
            seam,
            "command-south-panel-seam-wall-seat",
            "z",
            0.08,
        )
    vertical_seam_count = 5 if lod == 0 else 3 if lod == 1 else 0
    for index in range(vertical_seam_count):
        seam_x = west_face + 15.0 + index * (36.0 / max(1, vertical_seam_count - 1))
        seam = f"a22.cmd.monumental-keep.south-panel-seam.vertical.{index}"
        assembler.box(
            seam,
            seam_x,
            15.0,
            south_face - 0.30,
            0.16,
            29.0,
            0.50,
            "trim",
            role="command-south-keep-vertical-formwork-panel-seam",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{seam}",
            lower_keep,
            seam,
            "command-south-vertical-panel-seam-wall-seat",
            "z",
            0.08,
        )
    keep_vent_back = "a22.cmd.monumental-keep.south-intake-vent.back"
    assembler.box(
        keep_vent_back,
        west_face + 33.0,
        7.0,
        south_face - 0.20,
        10.0,
        4.6,
        0.42,
        "road",
        role="command-south-keep-deep-occupied-intake-vent-back",
        route_exempt=True,
    )
    keep_louver_count = 5 if lod == 0 else 3 if lod == 1 else 0
    for index in range(keep_louver_count):
        louver = f"a22.cmd.monumental-keep.south-intake-vent.louver.{index}"
        assembler.box(
            louver,
            west_face + 33.0,
            5.3 + index * (3.4 / max(1, keep_louver_count - 1)),
            south_face - 0.82,
            11.0,
            0.24,
            1.40,
            "trim",
            role="command-south-keep-heavy-intake-louver",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{louver}",
            keep_vent_back,
            louver,
            "command-south-keep-louver-vent-seat",
            "z",
            0.08,
        )
    keep_pipe_specs = (
        (
            ("west", west_face + 14.0),
            ("east", west_face + 52.0),
        )
        if lod < 2
        else ()
    )
    for label, pipe_x in keep_pipe_specs:
        pipe = f"a22.cmd.monumental-keep.south-service-pipe.{label}"
        assembler.cylinder_between(
            pipe,
            (pipe_x, 0.20, south_face - 1.15),
            (pipe_x, 29.8, south_face - 1.15),
            0.24,
            "wall_warm",
            12 if lod == 0 else 8,
            end_radius=0.18,
            role="command-south-keep-grounded-external-service-pipe",
        )
        _connect(
            assembler,
            f"contact.{pipe}",
            lower_keep,
            pipe,
            "command-south-service-pipe-wall-seat",
            "endpoint",
            0.10,
        )
    if lod < 2:
        keep_sign = "a22.cmd.monumental-keep.south-identification-band"
        assembler.box(
            keep_sign,
            west_face + 33.0,
            27.0,
            south_face - 0.90,
            15.0,
            1.15,
            1.55,
            "wall_warm",
            role="command-south-keep-weathered-identification-band",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{keep_sign}",
            lower_keep,
            keep_sign,
            "command-south-identification-band-wall-seat",
            "z",
            0.10,
        )

    # A three-stage south curtain projects the castle body toward the fixed
    # dual-hero camera without changing the authoritative west entrance.  The
    # terraces overlap the existing keep and stay inside its canonical
    # east-west footprint, creating the broad connected mass seen in the
    # reference instead of another isolated tower.
    curtain_tiers = (
        (
            "lower-breastwork",
            west_face + 46.0,
            10.0,
            south_face - 5.0,
            86.0,
            20.0,
            15.0,
            "wall_weathered",
        ),
        (
            "middle-operations-terrace",
            west_face + 44.0,
            24.8,
            south_face,
            70.0,
            10.0,
            14.0,
            "wall",
        ),
        (
            "upper-command-terrace",
            west_face + 40.0,
            34.6,
            south_face + 5.0,
            54.0,
            10.0,
            12.0,
            "wall_weathered",
        ),
    )
    prior_curtain = lower_keep
    for tier_index, (
        label,
        tier_x,
        tier_y,
        tier_z,
        tier_width,
        tier_height,
        tier_depth,
        tier_key,
    ) in enumerate(curtain_tiers):
        tier = f"a22.cmd.south-curtain.{label}"
        assembler.box(
            tier,
            tier_x,
            tier_y,
            tier_z,
            tier_width,
            tier_height,
            tier_depth,
            tier_key,
            role="command-camera-facing-broad-stepped-castle-curtain",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{tier}",
            prior_curtain,
            tier,
            "command-south-curtain-tier-structural-overlap",
            "y" if tier_index else "plan",
            0.20,
        )
        cap = f"{tier}.armoured-terrace-cap"
        if lod < 2 or tier_index == len(curtain_tiers) - 1:
            assembler.box(
                cap,
                tier_x,
                tier_y + tier_height / 2.0 + 0.24,
                tier_z - 0.5,
                tier_width + 3.0,
                0.48,
                tier_depth + 2.0,
                "roof",
                role="command-south-curtain-broad-armoured-terrace-cap",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{cap}",
                tier,
                cap,
                "command-south-curtain-cap-tier-seat",
                "y",
                0.10,
            )
        prior_curtain = tier

    curtain_buttress_count = 5 if lod == 0 else 3 if lod == 1 else 2
    lower_curtain = "a22.cmd.south-curtain.lower-breastwork"
    for index in range(curtain_buttress_count):
        buttress_x = (
            west_face + 8.0 + index * (76.0 / max(1, curtain_buttress_count - 1))
        )
        buttress = f"{lower_curtain}.battered-buttress.{index}"
        assembler.beam(
            buttress,
            (buttress_x, 0.20, south_face - 14.0),
            (buttress_x, 19.8, south_face - 11.0),
            1.18,
            1.55,
            "trim",
            role="command-south-curtain-heavy-grounded-battered-buttress",
        )
        _connect(
            assembler,
            f"contact.{buttress}",
            lower_curtain,
            buttress,
            "command-south-curtain-buttress-wall-seat",
            "endpoint",
            0.16,
        )
    if lod < 2:
        curtain_bay_count = 5 if lod == 0 else 3
        for index in range(curtain_bay_count):
            bay_x = west_face + 12.0 + index * (68.0 / max(1, curtain_bay_count - 1))
            back = f"{lower_curtain}.deep-occupied-bay.{index}.back"
            assembler.box(
                back,
                bay_x,
                8.5 + (index % 2) * 3.0,
                south_face - 12.72,
                8.5,
                3.4,
                0.48,
                "wall_warm",
                role="command-south-curtain-deep-occupied-operations-bay",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{back}",
                lower_curtain,
                back,
                "command-south-curtain-bay-wall-recess",
                "z",
                0.10,
            )
            header = f"{back}.armoured-header"
            assembler.box(
                header,
                bay_x,
                10.35 + (index % 2) * 3.0,
                south_face - 13.1,
                10.0,
                0.42,
                1.2,
                "trim",
                role="command-south-curtain-deep-bay-load-bearing-header",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{header}",
                back,
                header,
                "command-south-curtain-header-bay-seat",
                "z",
                0.08,
            )
        terrace_bay_specs = (
            (
                "middle-operations-terrace",
                west_face + 44.0,
                24.8,
                south_face - 7.25,
                50.0,
                4 if lod == 0 else 3,
            ),
            (
                "upper-command-terrace",
                west_face + 40.0,
                34.6,
                south_face - 1.25,
                38.0,
                3 if lod == 0 else 2,
            ),
        )
        for (
            tier_label,
            tier_x,
            tier_y,
            tier_front_z,
            bay_span,
            bay_count,
        ) in terrace_bay_specs:
            parent_tier = f"a22.cmd.south-curtain.{tier_label}"
            for index in range(bay_count):
                bay_x = (
                    tier_x - bay_span / 2.0 + index * (bay_span / max(1, bay_count - 1))
                )
                back = f"{parent_tier}.deep-occupied-bay.{index}.back"
                assembler.box(
                    back,
                    bay_x,
                    tier_y,
                    tier_front_z,
                    8.0,
                    3.4,
                    0.48,
                    "wall_warm",
                    role="command-south-terrace-deep-occupied-operations-bay",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{back}",
                    parent_tier,
                    back,
                    "command-south-terrace-bay-wall-recess",
                    "z",
                    0.10,
                )
                header = f"{back}.armoured-header"
                assembler.box(
                    header,
                    bay_x,
                    tier_y + 1.95,
                    tier_front_z - 0.38,
                    9.2,
                    0.42,
                    1.15,
                    "trim",
                    role="command-south-terrace-bay-load-bearing-header",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{header}",
                    back,
                    header,
                    "command-south-terrace-header-bay-seat",
                    "z",
                    0.08,
                )
        curtain_spine_count = 4 if lod == 0 else 3
        for index in range(curtain_spine_count):
            spine_x = (
                west_face + 16.0 + index * (60.0 / max(1, curtain_spine_count - 1))
            )
            spine = f"a22.cmd.south-curtain.vertical-load-spine.{index}"
            assembler.beam(
                spine,
                (spine_x, 0.20, south_face - 13.0),
                (spine_x, 39.4, south_face - 0.5),
                0.72,
                1.15,
                "trim",
                role="command-south-curtain-continuous-heavy-load-spine",
            )
            _connect(
                assembler,
                f"contact.{spine}",
                lower_curtain,
                spine,
                "command-south-curtain-spine-breastwork-seat",
                "endpoint",
                0.14,
            )
        upper_bridge = "a22.cmd.south-curtain.upper-operations-bridge"
        bridge_x = west_face + 46.0
        bridge_z = south_face + 6.0
        assembler.box(
            upper_bridge,
            bridge_x,
            42.35,
            bridge_z,
            64.0,
            6.0,
            10.0,
            "wall_cool",
            role="command-wide-connected-upper-operations-bridge",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{upper_bridge}",
            "a22.cmd.south-curtain.upper-command-terrace",
            upper_bridge,
            "command-upper-bridge-terrace-seat",
            "y",
            0.20,
        )
        bridge_cap = f"{upper_bridge}.armoured-cap"
        assembler.box(
            bridge_cap,
            bridge_x,
            45.45,
            bridge_z,
            68.0,
            0.44,
            11.5,
            "roof",
            role="command-upper-operations-bridge-armoured-cap",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{bridge_cap}",
            upper_bridge,
            bridge_cap,
            "command-upper-bridge-cap-seat",
            "y",
            0.10,
        )
        bridge_bay_count = 4 if lod == 0 else 2
        for index in range(bridge_bay_count):
            bay_x = bridge_x - 24.0 + index * (48.0 / max(1, bridge_bay_count - 1))
            back = f"{upper_bridge}.deep-occupied-bay.{index}.back"
            assembler.box(
                back,
                bay_x,
                42.4,
                bridge_z - 5.2,
                9.0,
                3.4,
                0.48,
                "wall_warm",
                role="command-upper-bridge-deep-occupied-operations-bay",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{back}",
                upper_bridge,
                back,
                "command-upper-bridge-bay-wall-recess",
                "z",
                0.10,
            )
            header = f"{back}.armoured-header"
            assembler.box(
                header,
                bay_x,
                44.35,
                bridge_z - 5.55,
                10.4,
                0.42,
                1.1,
                "trim",
                role="command-upper-bridge-bay-heavy-header",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{header}",
                back,
                header,
                "command-upper-bridge-header-bay-seat",
                "z",
                0.08,
            )
        for side_label, pipe_x in (
            ("west", west_face + 14.0),
            ("east", west_face + 78.0),
        ):
            pipe = f"{upper_bridge}.grounded-service-riser.{side_label}"
            assembler.cylinder_between(
                pipe,
                (pipe_x, 0.20, bridge_z - 5.0),
                (pipe_x, 45.2, bridge_z - 5.0),
                0.38,
                "wall_warm",
                14 if lod == 0 else 8,
                end_radius=0.28,
                role="command-upper-bridge-grounded-heavy-service-riser",
            )
            _connect(
                assembler,
                f"contact.{pipe}",
                upper_bridge,
                pipe,
                "command-upper-bridge-riser-wall-seat",
                "endpoint",
                0.12,
            )

    # Lift the camera-facing south corner into a staffed operations tower.
    # It is structurally seated on the lower keep and stays fully east of the
    # authoritative west entrance, so the canonical approach remains clear.
    south_ops_tower = "a22.cmd.monumental-keep.south-operations-tower"
    south_ops_x = west_face + 20.0
    south_ops_z = south_face + 12.0
    assembler.box(
        south_ops_tower,
        south_ops_x,
        40.0,
        south_ops_z,
        38.0,
        20.0,
        28.0,
        "wall",
        role="command-camera-facing-stepped-south-bastion-lower-tier",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{south_ops_tower}",
        lower_keep,
        south_ops_tower,
        "command-south-operations-tower-lower-keep-seat",
        "y",
        0.20,
    )
    south_ops_middle = f"{south_ops_tower}.middle-operations-tier"
    assembler.box(
        south_ops_middle,
        south_ops_x,
        57.4,
        south_ops_z,
        30.0,
        15.0,
        22.0,
        "wall_weathered",
        role="command-camera-facing-stepped-south-bastion-middle-tier",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{south_ops_middle}",
        south_ops_tower,
        south_ops_middle,
        "command-south-bastion-middle-lower-seat",
        "y",
        0.18,
    )
    south_ops_cabin = f"{south_ops_tower}.upper-sensor-cabin"
    assembler.box(
        south_ops_cabin,
        south_ops_x - 2.5,
        70.3,
        south_ops_z + 1.0,
        24.0,
        11.0,
        18.0,
        "wall_weathered",
        role="command-south-operations-tower-staffed-sensor-cabin",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{south_ops_cabin}",
        south_ops_middle,
        south_ops_cabin,
        "command-south-sensor-cabin-tower-seat",
        "y",
        0.18,
    )
    south_ops_cap = f"{south_ops_tower}.armoured-crown"
    assembler.box(
        south_ops_cap,
        south_ops_x - 2.5,
        76.0,
        south_ops_z + 1.0,
        30.0,
        0.70,
        24.0,
        "roof",
        role="command-south-operations-tower-armoured-crown",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{south_ops_cap}",
        south_ops_cabin,
        south_ops_cap,
        "command-south-operations-crown-cabin-seat",
        "y",
        0.10,
    )
    for index, (belt_y, belt_z, belt_width) in enumerate(
        (
            (50.1, south_ops_z - 14.4, 39.0),
            (64.9, south_ops_z - 11.4, 31.0),
        )
    ):
        belt = f"{south_ops_tower}.structural-belt.{index}"
        assembler.box(
            belt,
            south_ops_x,
            belt_y,
            belt_z,
            belt_width,
            0.66,
            1.3,
            "trim",
            role="command-south-operations-tower-structural-belt",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{belt}",
            south_ops_tower if index == 0 else south_ops_middle,
            belt,
            "command-south-tower-belt-wall-seat",
            "z",
            0.10,
        )
    face_fin_count = 3 if lod == 0 else 2
    for index in range(face_fin_count):
        fin_x = south_ops_x - 15.0 + index * (30.0 / max(1, face_fin_count - 1))
        fin = f"{south_ops_tower}.south-load-fin.{index}"
        assembler.beam(
            fin,
            (fin_x, 29.9, south_ops_z - 14.5),
            (fin_x, 49.9, south_ops_z - 14.5),
            0.42,
            0.54,
            "wall_weathered",
            role="command-south-bastion-lower-tier-readable-load-fin",
        )
        _connect(
            assembler,
            f"contact.{fin}",
            south_ops_tower,
            fin,
            "command-south-tower-load-fin-wall-seat",
            "endpoint",
            0.10,
        )
    south_ops_balcony = f"{south_ops_tower}.staffed-service-balcony"
    assembler.box(
        south_ops_balcony,
        south_ops_x,
        64.7,
        south_ops_z - 12.7,
        31.0,
        0.46,
        4.0,
        "trim",
        role="command-south-operations-tower-staffed-service-balcony",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{south_ops_balcony}",
        south_ops_middle,
        south_ops_balcony,
        "command-south-tower-balcony-wall-seat",
        "z",
        0.12,
    )
    if lod < 2:
        balcony_rail = f"{south_ops_balcony}.outer-rail"
        assembler.beam(
            balcony_rail,
            (south_ops_x - 15.0, 65.85, south_ops_z - 14.6),
            (south_ops_x + 15.0, 65.85, south_ops_z - 14.6),
            0.08,
            0.08,
            "trim",
            role="command-south-operations-tower-human-scale-balcony-rail",
        )
        _connect(
            assembler,
            f"contact.{balcony_rail}",
            south_ops_balcony,
            balcony_rail,
            "command-south-tower-rail-balcony-seat",
            "endpoint",
            0.08,
        )
    cabin_back = f"{south_ops_cabin}.occupied-control-bay.back"
    assembler.box(
        cabin_back,
        south_ops_x - 2.5,
        70.3,
        south_ops_z - 8.15,
        12.0,
        4.2,
        0.42,
        "wall_warm",
        role="command-south-sensor-cabin-deep-occupied-control-bay-back",
        route_exempt=True,
    )
    for label, frame_x, frame_y, frame_width, frame_height in (
        ("west", south_ops_x - 9.3, 70.3, 0.50, 5.0),
        ("east", south_ops_x + 4.3, 70.3, 0.50, 5.0),
        ("header", south_ops_x - 2.5, 72.65, 14.0, 0.46),
        ("sill", south_ops_x - 2.5, 67.95, 14.0, 0.42),
    ):
        frame = f"{south_ops_cabin}.occupied-control-bay.frame.{label}"
        assembler.box(
            frame,
            frame_x,
            frame_y,
            south_ops_z - 8.75,
            frame_width,
            frame_height,
            1.6,
            "trim",
            role="command-south-sensor-cabin-deep-control-bay-frame",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{frame}",
            cabin_back,
            frame,
            "command-south-sensor-cabin-frame-seat",
            "z",
            0.10,
        )
    for side_label, side_x in (
        ("west", south_ops_x - 18.6),
        ("east", south_ops_x + 18.6),
    ):
        buttress = f"{south_ops_tower}.battered-buttress.{side_label}"
        assembler.beam(
            buttress,
            (side_x, 29.9, south_ops_z - 16.1),
            (side_x, 50.0, south_ops_z - 13.6),
            0.82,
            1.18,
            "trim",
            role="command-south-operations-tower-battered-load-fin",
        )
        _connect(
            assembler,
            f"contact.{buttress}",
            south_ops_tower,
            buttress,
            "command-south-operations-buttress-tower-seat",
            "endpoint",
            0.12,
        )
    tower_bay_count = 2 if lod < 2 else 1
    for index in range(tower_bay_count):
        bay_x = south_ops_x - 11.0 + index * (22.0 / max(1, tower_bay_count - 1))
        bay_y = 40.0
        prefix = f"{south_ops_tower}.occupied-bay.{index}"
        bay_back = f"{prefix}.back"
        assembler.box(
            bay_back,
            bay_x,
            bay_y,
            south_ops_z - 14.15,
            6.2,
            5.0,
            0.42,
            "wall_warm",
            role="command-south-tower-deep-occupied-operations-bay-back",
            route_exempt=True,
        )
        for label, frame_x, frame_y, frame_width, frame_height in (
            ("west", bay_x - 3.6, bay_y, 0.52, 5.8),
            ("east", bay_x + 3.6, bay_y, 0.52, 5.8),
            ("header", bay_x, bay_y + 2.75, 7.6, 0.48),
            ("sill", bay_x, bay_y - 2.75, 7.6, 0.42),
        ):
            frame = f"{prefix}.frame.{label}"
            assembler.box(
                frame,
                frame_x,
                frame_y,
                south_ops_z - 14.85,
                frame_width,
                frame_height,
                1.8,
                "trim",
                role="command-south-tower-deep-operations-bay-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{frame}",
                bay_back,
                frame,
                "command-south-tower-bay-frame-seat",
                "z",
                0.10,
            )
        runoff = f"{prefix}.grime-runoff-relief"
        assembler.box(
            runoff,
            bay_x,
            bay_y - 5.3,
            south_ops_z - 14.74,
            0.34,
            5.8,
            0.24,
            "road",
            role="command-south-bastion-window-grime-runoff-relief",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{runoff}",
            bay_back,
            runoff,
            "command-south-bastion-runoff-window-seat",
            "z",
            0.08,
        )
    vent_back = f"{south_ops_middle}.deep-intake-vent.back"
    assembler.box(
        vent_back,
        south_ops_x,
        57.0,
        south_ops_z - 11.15,
        12.0,
        5.2,
        0.42,
        "road",
        role="command-south-bastion-deep-intake-vent-back",
        route_exempt=True,
    )
    louver_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(louver_count):
        louver = f"{south_ops_middle}.deep-intake-vent.louver.{index}"
        assembler.box(
            louver,
            south_ops_x,
            55.0 + index * (4.0 / max(1, louver_count - 1)),
            south_ops_z - 11.75,
            13.0,
            0.26,
            1.35,
            "trim",
            role="command-south-bastion-deep-intake-louver",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{louver}",
            vent_back,
            louver,
            "command-south-bastion-louver-vent-seat",
            "z",
            0.08,
        )
    south_radar_mast = f"{south_ops_cabin}.short-range-radar-mast"
    assembler.cylinder_between(
        south_radar_mast,
        (south_ops_x - 2.5, 75.9, south_ops_z + 1.0),
        (south_ops_x - 2.5, 85.7, south_ops_z + 1.0),
        0.18,
        "trim",
        10 if lod == 0 else 8,
        end_radius=0.10,
        role="command-south-bastion-short-range-radar-mast",
    )
    _connect(
        assembler,
        f"contact.{south_radar_mast}",
        south_ops_cap,
        south_radar_mast,
        "command-south-radar-mast-crown-seat",
        "endpoint",
        0.10,
    )
    radar_bar_count = 4 if lod == 0 else 2
    for index in range(radar_bar_count):
        radar_bar = f"{south_ops_cabin}.short-range-radar-array.{index}"
        radar_y = 78.7 + index * (5.7 / max(1, radar_bar_count - 1))
        assembler.beam(
            radar_bar,
            (south_ops_x - 8.0, radar_y, south_ops_z + 1.0),
            (south_ops_x + 3.0, radar_y, south_ops_z + 1.0),
            0.08,
            0.08,
            "trim",
            role="command-south-bastion-short-range-radar-array",
        )
        _connect(
            assembler,
            f"contact.{radar_bar}",
            south_radar_mast,
            radar_bar,
            "command-south-radar-array-mast-seat",
            "plan",
            0.08,
        )

    # One continuous occupied gallery ties the south bastion back into the
    # lower keep.  The large horizontal load line is intentionally more
    # important than adding another tower: from the fixed dual-hero camera it
    # makes Command read as one castle-scale body rather than scattered blocks.
    south_gallery = "a22.cmd.monumental-keep.south-occupied-operations-gallery"
    gallery_x = west_face + 34.0
    gallery_z = south_face - 2.0
    assembler.box(
        south_gallery,
        gallery_x,
        31.5,
        gallery_z,
        54.0,
        3.6,
        4.6,
        "trim",
        role="command-south-bastion-wide-load-bearing-operations-gallery",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{south_gallery}",
        lower_keep,
        south_gallery,
        "command-south-gallery-lower-keep-seat",
        "y",
        0.18,
    )
    gallery_cap = f"{south_gallery}.armoured-cap"
    assembler.box(
        gallery_cap,
        gallery_x,
        33.42,
        gallery_z,
        58.0,
        0.34,
        5.2,
        "roof",
        role="command-south-gallery-continuous-armoured-cap",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{gallery_cap}",
        south_gallery,
        gallery_cap,
        "command-south-gallery-cap-seat",
        "y",
        0.10,
    )
    if lod < 2:
        gallery_back = f"{south_gallery}.occupied-bay.back"
        assembler.box(
            gallery_back,
            gallery_x,
            31.5,
            gallery_z - 2.45,
            45.0,
            1.8,
            0.42,
            "wall_warm",
            role="command-south-gallery-deep-occupied-operations-bay-back",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{gallery_back}",
            south_gallery,
            gallery_back,
            "command-south-gallery-bay-back-seat",
            "z",
            0.10,
        )
        gallery_mullion_count = 6 if lod == 0 else 4
        for index in range(gallery_mullion_count):
            mullion_x = (
                gallery_x - 22.5 + index * (45.0 / max(1, gallery_mullion_count - 1))
            )
            mullion = f"{south_gallery}.occupied-bay.mullion.{index}"
            assembler.box(
                mullion,
                mullion_x,
                31.5,
                gallery_z - 2.72,
                0.40,
                2.5,
                0.72,
                "trim",
                role="command-south-gallery-human-scale-window-mullion",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{mullion}",
                gallery_back,
                mullion,
                "command-south-gallery-mullion-back-seat",
                "z",
                0.08,
            )

    # Long battered shoulders visually carry the middle tier into the lower
    # keep.  Their deep front edge is deliberately readable from the frozen
    # dual-hero player-height camera.
    for label, side in (("south", -1.0), ("north", 1.0)):
        shoulder = f"a22.cmd.monumental-keep.battered-shoulder.{label}"
        outer_z = z + side * 26.0
        inner_z = z + side * 19.0
        assembler.panel(
            shoulder,
            (
                (west_face - 4.8, 1.0, outer_z),
                (west_face + 9.0, 29.8, inner_z),
                (west_face + 33.0, 29.8, inner_z),
                (west_face + 34.0, 1.0, outer_z),
            ),
            0.72,
            "wall_weathered",
            role="command-monumental-battered-load-shoulder",
        )
        _connect(
            assembler,
            f"contact.{shoulder}",
            lower_keep,
            shoulder,
            "battered-shoulder-keep-overlap",
            "plan",
            0.20,
        )

    # Two high gate towers and the bridge between them establish a single
    # unmistakable fortified entry at the route terminus.
    gate_tower_count = 2
    for label, side in (("south", -1.0), ("north", 1.0))[:gate_tower_count]:
        tower = f"a22.cmd.monumental-gate-tower.{label}"
        tower_z = z + side * 17.0
        assembler.box(
            tower,
            west_face + 5.0,
            14.0,
            tower_z,
            20.0,
            28.0,
            20.0,
            "wall_weathered",
            role="command-castle-scale-monumental-gate-tower",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{tower}",
            "a20.cmd.hero-citadel.plinth",
            tower,
            "gate-tower-foundation-embed",
            "y",
            0.28,
        )
        upper = f"{tower}.upper-tier"
        assembler.box(
            upper,
            west_face + 7.0,
            37.0,
            tower_z + side * 0.8,
            15.0,
            18.0,
            15.0,
            "wall",
            role="command-tapered-monumental-gate-tower-upper-tier",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{upper}",
            tower,
            upper,
            "gate-tower-upper-tier-seat",
            "y",
            0.20,
        )
        cap = f"{tower}.armoured-cap"
        assembler.box(
            cap,
            west_face + 7.0,
            46.2,
            tower_z + side * 0.8,
            18.0,
            0.72,
            18.0,
            "roof",
            role="command-gate-tower-armoured-cap",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{cap}",
            upper,
            cap,
            "gate-tower-cap-seat",
            "y",
            0.12,
        )
        buttress_count = 3 if lod == 0 else 2 if lod == 1 else 1
        for index in range(buttress_count):
            buttress_z = tower_z - 6.0 + index * (12.0 / max(1, buttress_count - 1))
            buttress = f"{tower}.west-buttress.{index}"
            assembler.beam(
                buttress,
                (west_face - 7.2, 0.18, buttress_z),
                (west_face - 1.0, 27.8, buttress_z),
                1.35,
                1.65,
                "trim",
                role="command-gate-tower-battered-west-load-buttress",
            )
            _connect(
                assembler,
                f"contact.{buttress}",
                tower,
                buttress,
                "gate-tower-buttress-wall-seat",
                "endpoint",
                0.14,
            )
        slit_count = 3 if lod == 0 else 2 if lod == 1 else 1
        for index in range(slit_count):
            slit_y = 16.0 + index * 9.0
            slit_z = tower_z + (0.8 if index % 2 else -0.8)
            back = f"{tower}.occupied-slit.{index}.back"
            assembler.box(
                back,
                west_face - 3.8,
                slit_y,
                slit_z,
                0.36,
                3.4,
                3.2,
                "wall_warm",
                role="command-gate-tower-deep-occupied-slit-back",
                route_exempt=True,
            )
            for frame_label, frame_z, frame_y, frame_depth, frame_height in (
                ("south", slit_z - 2.0, slit_y, 0.42, 4.4),
                ("north", slit_z + 2.0, slit_y, 0.42, 4.4),
                ("header", slit_z, slit_y + 2.05, 4.4, 0.38),
                ("sill", slit_z, slit_y - 2.05, 4.4, 0.38),
            ):
                frame = f"{tower}.occupied-slit.{index}.frame.{frame_label}"
                assembler.box(
                    frame,
                    west_face - 4.65,
                    frame_y,
                    frame_z,
                    1.45,
                    frame_height,
                    frame_depth,
                    "trim",
                    role="command-gate-tower-deep-slit-structural-frame",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{frame}",
                    back,
                    frame,
                    "gate-tower-slit-frame-seat",
                    "x",
                    0.10,
                )
        # Readable 2.8-4.0 m concrete bays, not a single uninterrupted slab.
        seam_y_values = (6.5, 13.0, 20.0, 27.0) if lod < 2 else ()
        for index, seam_y in enumerate(seam_y_values):
            seam = f"{tower}.formwork-seam.horizontal.{index}"
            assembler.box(
                seam,
                west_face - 5.15,
                seam_y,
                tower_z,
                0.46,
                0.18,
                18.4,
                "trim",
                role="command-gate-tower-cast-concrete-formwork-seam",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{seam}",
                tower,
                seam,
                "gate-tower-formwork-seam-wall-seat",
                "x",
                0.08,
            )
        for index, seam_z in enumerate(
            (tower_z - 4.7, tower_z + 4.7) if lod < 2 else ()
        ):
            seam = f"{tower}.formwork-seam.vertical.{index}"
            assembler.box(
                seam,
                west_face - 5.15,
                13.8,
                seam_z,
                0.46,
                26.0,
                0.16,
                "trim",
                role="command-gate-tower-cast-concrete-vertical-joint",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{seam}",
                tower,
                seam,
                "gate-tower-formwork-joint-wall-seat",
                "x",
                0.08,
            )

        vent_back = f"{tower}.deep-intake-vent.back"
        assembler.box(
            vent_back,
            west_face - 4.15,
            8.8,
            tower_z,
            0.36,
            3.0,
            7.2,
            "wall_cool",
            role="command-gate-tower-deep-mechanical-intake-back",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{vent_back}",
            tower,
            vent_back,
            "gate-tower-intake-back-wall-recess",
            "x",
            0.10,
        )
        louver_count = 5 if lod == 0 else 3 if lod == 1 else 2
        for index in range(louver_count):
            louver_y = 7.65 + index * (2.3 / max(1, louver_count - 1))
            louver = f"{tower}.deep-intake-vent.louver.{index}"
            assembler.beam(
                louver,
                (west_face - 5.45, louver_y, tower_z - 3.25),
                (west_face - 5.45, louver_y, tower_z + 3.25),
                0.14,
                0.22,
                "trim",
                role="command-gate-tower-readable-intake-louver",
            )
            _connect(
                assembler,
                f"contact.{louver}",
                vent_back,
                louver,
                "gate-tower-louver-intake-seat",
                "x",
                0.08,
            )

        sign = f"{tower}.fortress-identification-sign"
        assembler.box(
            sign,
            west_face - 5.42,
            22.0,
            tower_z + side * 6.2,
            0.54,
            1.45,
            4.8,
            "wall_warm",
            role="command-gate-tower-illuminated-identification-sign",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{sign}",
            tower,
            sign,
            "gate-tower-identification-sign-wall-seat",
            "x",
            0.08,
        )
        for index, offset in enumerate((-3.4, 3.4) if lod < 2 else ()):
            spotlight = f"{tower}.balcony-spotlight.{index}"
            assembler.box(
                spotlight,
                west_face - 8.05,
                26.65,
                tower_z + offset,
                0.62,
                0.42,
                0.52,
                "accent",
                role="command-gate-tower-motivated-balcony-spotlight",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{spotlight}",
                tower,
                spotlight,
                "gate-tower-spotlight-wall-seat",
                "plan",
                0.08,
            )
        for index, runoff_z in enumerate(
            ((tower_z - 7.6, tower_z + 7.6) if lod < 2 else ())
        ):
            runoff = f"{tower}.grime-runoff-relief.{index}"
            assembler.box(
                runoff,
                west_face - 5.25,
                15.0,
                runoff_z,
                0.30,
                7.5,
                0.86,
                "roof",
                role="command-gate-tower-physical-runoff-and-grime-relief",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{runoff}",
                tower,
                runoff,
                "gate-tower-runoff-relief-wall-seat",
                "x",
                0.08,
            )
        if lod < 2:
            for index, crenel_z in enumerate((tower_z - 6.0, tower_z, tower_z + 6.0)):
                crenel = f"{tower}.armoured-cap.crenel.{index}"
                assembler.box(
                    crenel,
                    west_face + 2.0,
                    47.35,
                    crenel_z,
                    2.2,
                    2.0,
                    2.6,
                    "trim",
                    role="command-gate-tower-readable-armoured-crenel",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{crenel}",
                    cap,
                    crenel,
                    "gate-tower-crenel-cap-seat",
                    "y",
                    0.10,
                )
        balcony = f"{tower}.west-service-balcony"
        assembler.box(
            balcony,
            west_face - 5.8,
            27.2,
            tower_z,
            4.6,
            0.46,
            12.0,
            "trim",
            role="command-gate-tower-human-scale-service-balcony",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{balcony}",
            tower,
            balcony,
            "gate-tower-balcony-wall-seat",
            "x",
            0.14,
        )
        if lod < 2:
            rail_post_count = 4 if lod == 0 else 3
            for index in range(rail_post_count):
                rail_z = tower_z - 5.0 + index * (10.0 / max(1, rail_post_count - 1))
                post = f"{balcony}.rail-post.{index}"
                assembler.beam(
                    post,
                    (west_face - 7.8, 27.4, rail_z),
                    (west_face - 7.8, 28.65, rail_z),
                    0.12,
                    0.12,
                    "trim",
                    role="command-gate-tower-service-balcony-rail",
                )
                _connect(
                    assembler,
                    f"contact.{post}",
                    balcony,
                    post,
                    "gate-tower-balcony-rail-seat",
                    "endpoint",
                    0.08,
                )
            rail = f"{balcony}.rail"
            assembler.beam(
                rail,
                (west_face - 7.8, 28.65, tower_z - 5.0),
                (west_face - 7.8, 28.65, tower_z + 5.0),
                0.14,
                0.14,
                "trim",
                role="command-gate-tower-service-balcony-rail",
            )
            _connect(
                assembler,
                f"contact.{rail}",
                balcony,
                rail,
                "gate-tower-balcony-rail-seat",
                "endpoint",
                0.08,
            )
            stair_stringer = f"{tower}.external-stair.stringer"
            outer_stair_z = tower_z + side * 11.2
            assembler.beam(
                stair_stringer,
                (west_face - 5.0, 0.18, outer_stair_z),
                (west_face + 4.0, 26.9, outer_stair_z),
                0.38,
                0.44,
                "trim",
                role="command-gate-tower-external-service-stair-stringer",
            )
            _connect(
                assembler,
                f"contact.{stair_stringer}",
                tower,
                stair_stringer,
                "gate-tower-stair-wall-seat",
                "endpoint",
                0.10,
            )
            stair_count = 8 if lod == 0 else 5
            for index in range(stair_count):
                fraction = index / max(1, stair_count - 1)
                step = f"{tower}.external-stair.step.{index}"
                assembler.box(
                    step,
                    west_face - 4.8 + fraction * 8.5,
                    0.55 + fraction * 25.8,
                    outer_stair_z,
                    2.25,
                    0.24,
                    3.4,
                    "trim",
                    role="command-gate-tower-external-service-stair-step",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{step}",
                    stair_stringer,
                    step,
                    "gate-tower-stair-step-stringer-seat",
                    "plan",
                    0.08,
                )
        service_pipe = f"{tower}.external-service-pipe"
        pipe_z = tower_z - side * 5.4
        assembler.cylinder_between(
            service_pipe,
            (west_face - 5.4, 0.20, pipe_z),
            (west_face - 5.4, 42.5, pipe_z),
            0.32,
            "accent",
            12 if lod == 0 else 8,
            role="command-gate-tower-external-service-pipe",
        )
        _connect(
            assembler,
            f"contact.{service_pipe}",
            tower,
            service_pipe,
            "gate-tower-pipe-wall-seat",
            "plan",
            0.08,
        )
        if label == "north" and lod < 2:
            tower_radar = f"{tower}.roof-radar-mast"
            assembler.cylinder(
                tower_radar,
                west_face + 7.0,
                52.2,
                tower_z + side * 0.8,
                0.18,
                10.0,
                "trim",
                12 if lod == 0 else 8,
                top_radius=0.10,
                role="command-gate-tower-roof-radar-mast",
            )
            _connect(
                assembler,
                f"contact.{tower_radar}",
                cap,
                tower_radar,
                "gate-tower-radar-cap-seat",
                "y",
                0.10,
            )
    overgate = "a22.cmd.monumental-overgate-bridge"
    assembler.box(
        overgate,
        west_face + 3.2,
        34.0,
        z,
        8.0,
        3.2,
        50.0,
        "trim",
        role="command-heavy-monumental-overgate-bridge",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{overgate}",
        "a22.cmd.monumental-gate-tower.south",
        overgate,
        "overgate-south-tower-seat",
        "z",
        0.18,
    )
    if lod < 2:
        _connect(
            assembler,
            f"contact.{overgate}.east",
            "a22.cmd.monumental-gate-tower.north",
            overgate,
            "overgate-north-tower-seat",
            "z",
            0.18,
        )

    # A broad operations gallery, asymmetric crown and radar face establish a
    # single memorable keep rather than a collection of slab boxes.
    gallery = "a22.cmd.operations-gallery"
    assembler.box(
        gallery,
        west_face + 6.0,
        36.5,
        z + 3.0,
        6.0,
        2.2,
        47.0,
        "trim",
        role="command-castle-scale-operations-gallery",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{gallery}",
        "a20.cmd.hero-citadel.keep",
        gallery,
        "gallery-keep-seat",
        "z",
        0.14,
    )
    if lod < 2:
        rail_count = 9 if lod == 0 else 5
        for index in range(rail_count):
            rz = z - 17.0 + index * (40.0 / max(1, rail_count - 1))
            post = f"a22.cmd.operations-gallery.rail-post.{index}"
            assembler.beam(
                post,
                (west_face + 2.8, 37.3, rz),
                (west_face + 2.8, 38.65, rz),
                0.06,
                0.06,
                "trim",
                role="command-human-scale-gallery-rail",
            )
            _connect(
                assembler,
                f"contact.{post}",
                gallery,
                post,
                "rail-gallery-seat",
                "endpoint",
                0.08,
            )
        rail = "a22.cmd.operations-gallery.rail"
        assembler.beam(
            rail,
            (west_face + 2.8, 38.65, z - 17.0),
            (west_face + 2.8, 38.65, z + 23.0),
            0.07,
            0.07,
            "trim",
            role="command-human-scale-gallery-rail",
        )
        _connect(
            assembler,
            f"contact.{rail}",
            gallery,
            rail,
            "rail-gallery-seat",
            "endpoint",
            0.08,
        )

    # Pull the open radar crown onto the camera-facing stepped terraces and
    # lift it above the new upper cabin.  The old north-side position was
    # geometrically valid but hidden behind the three tall cuboids.
    radar_z = south_face + 10.0
    radar_mast = "a22.cmd.crown.long-range-radar.mast"
    assembler.cylinder(
        radar_mast,
        west_face + 57.0,
        106.0,
        radar_z,
        0.34,
        16.0,
        "trim",
        16 if lod == 0 else 10 if lod == 1 else 8,
        top_radius=0.22,
        role="command-crown-long-range-radar-mast",
    )
    _connect(
        assembler,
        f"contact.{radar_mast}",
        "a22.cmd.monumental-keep.armoured-crown-deck",
        radar_mast,
        "radar-mast-crown-seat",
        "y",
        0.16,
    )
    radar_panel = "a22.cmd.crown.long-range-radar.array"
    assembler.beam(
        radar_panel,
        (west_face + 57.0, 101.0, radar_z - 0.8),
        (west_face + 57.0, 112.0, radar_z - 0.8),
        0.24,
        0.28,
        "trim",
        role="command-crown-open-frame-long-range-radar-array",
    )
    _connect(
        assembler,
        f"contact.{radar_panel}",
        radar_mast,
        radar_panel,
        "radar-array-mast-seat",
        "plan",
        0.14,
    )
    for label, start, end in (
        (
            "left-frame",
            (west_face + 45.0, 101.5, radar_z - 0.8),
            (west_face + 45.0, 111.5, radar_z - 0.8),
        ),
        (
            "right-frame",
            (west_face + 69.0, 101.5, radar_z - 0.8),
            (west_face + 69.0, 111.5, radar_z - 0.8),
        ),
        (
            "bottom-frame",
            (west_face + 45.0, 101.5, radar_z - 0.8),
            (west_face + 69.0, 101.5, radar_z - 0.8),
        ),
        (
            "top-frame",
            (west_face + 45.0, 111.5, radar_z - 0.8),
            (west_face + 69.0, 111.5, radar_z - 0.8),
        ),
    ):
        frame = f"a22.cmd.crown.long-range-radar.{label}"
        assembler.beam(
            frame,
            start,
            end,
            0.14,
            0.18,
            "trim",
            role="command-crown-open-radar-perimeter-frame",
        )
        _connect(
            assembler,
            f"contact.{frame}",
            radar_panel,
            frame,
            "radar-frame-central-support-seat",
            "plan",
            0.08,
        )
    checkpoint_console = "a22.cmd.main-portal.occupied-checkpoint.console"
    assembler.box(
        checkpoint_console,
        west_face + 7.7,
        1.15,
        z + 2.9,
        2.2,
        1.55,
        3.4,
        "trim",
        role="command-portal-occupied-checkpoint-console",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{checkpoint_console}",
        portal_floor,
        checkpoint_console,
        "portal-checkpoint-console-floor-seat",
        "y",
        0.10,
    )
    checkpoint_torso = "a22.cmd.main-portal.occupied-checkpoint.guard-torso"
    assembler.cylinder(
        checkpoint_torso,
        west_face + 7.5,
        1.18,
        z - 2.9,
        0.27,
        1.05,
        "obstacle",
        12 if lod == 0 else 8,
        top_radius=0.20,
        role="command-portal-visible-occupied-guard-torso",
    )
    checkpoint_head = "a22.cmd.main-portal.occupied-checkpoint.guard-helmet"
    assembler.cylinder(
        checkpoint_head,
        west_face + 7.5,
        1.82,
        z - 2.9,
        0.24,
        0.30,
        "trim",
        12 if lod == 0 else 8,
        top_radius=0.19,
        role="command-portal-visible-occupied-guard-helmet",
    )
    _connect(
        assembler,
        f"contact.{checkpoint_head}",
        checkpoint_torso,
        checkpoint_head,
        "portal-guard-head-torso-seat",
        "y",
        0.08,
    )
    for index, offset in enumerate((-0.13, 0.13)):
        guard_leg = f"a22.cmd.main-portal.occupied-checkpoint.guard-leg.{index}"
        assembler.beam(
            guard_leg,
            (west_face + 7.5, 0.08, z - 2.9 + offset),
            (west_face + 7.5, 0.78, z - 2.9 + offset),
            0.09,
            0.10,
            "obstacle",
            role="command-portal-visible-occupied-guard-leg",
        )
        _connect(
            assembler,
            f"contact.{guard_leg}",
            checkpoint_torso,
            guard_leg,
            "portal-guard-leg-torso-seat",
            "endpoint",
            0.08,
        )
    rung_count = 6 if lod == 0 else 3 if lod == 1 else 2
    for index in range(rung_count):
        y = 102.4 + index * (8.1 / max(1, rung_count - 1))
        rung = f"a22.cmd.crown.long-range-radar.rung.{index}"
        assembler.beam(
            rung,
            (west_face + 45.5, y, radar_z - 1.02),
            (west_face + 68.5, y, radar_z - 1.02),
            0.10,
            0.10,
            "trim",
            role="command-radar-visible-grid-rung",
        )
        _connect(
            assembler,
            f"contact.{rung}",
            radar_panel,
            rung,
            "radar-rung-panel-seat",
            "plan",
            0.08,
        )
    antenna_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(antenna_count):
        antenna_x = west_face + 47.0 + index * (20.0 / max(1, antenna_count - 1))
        antenna = f"a22.cmd.crown.long-range-radar.antenna.{index}"
        assembler.beam(
            antenna,
            (antenna_x, 111.4, radar_z - 0.8),
            (
                antenna_x + (0.7 if index % 2 else -0.7),
                118.0 + (index % 2) * 1.8,
                radar_z - 0.8,
            ),
            0.055,
            0.055,
            "trim",
            role="command-crown-radar-antenna-bank",
        )
        _connect(
            assembler,
            f"contact.{antenna}",
            "a22.cmd.crown.long-range-radar.top-frame",
            antenna,
            "radar-antenna-frame-seat",
            "endpoint",
            0.08,
        )


def _hangar_arch_profile(
    centre_z: float,
) -> tuple[tuple[float, float], ...]:
    # Broad semi-elliptical shoulders match the reference's load-bearing
    # aircraft-vault grammar.  The prior near-linear rise made the shell read
    # as a pointed tent even though its depth stations were correct.
    return tuple(
        (centre_z + offset, height)
        for offset, height in (
            (-34.5, 0.20),
            (-34.0, 15.0),
            (-31.0, 40.0),
            (-25.0, 62.0),
            (-17.0, 78.0),
            (-7.0, 89.0),
            (0.0, 92.0),
            (7.0, 89.0),
            (17.0, 78.0),
            (25.0, 62.0),
            (31.0, 40.0),
            (34.0, 15.0),
            (34.5, 0.20),
        )
    )


def _add_hangar_macro_rebuild(
    assembler: a20._A20Assembler,
    hero: Any,
    lod: int,
) -> None:
    """Build the vault as a thick working dock, not a decorative arch."""

    x, z = hero.cx, hero.cz
    entrance_x = x + hero.width / 2.0
    profile = _hangar_arch_profile(z)
    stations = (
        ("outer", entrance_x + 0.80, 3.20),
        ("door", entrance_x - 7.5, 2.20),
        ("near", entrance_x - 25.0, 1.20),
        ("mid", entrance_x - 55.0, 0.92),
        ("deep", entrance_x - 90.0, 0.76),
    )
    station_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for station_index, (label, station_x, thickness) in enumerate(
        stations[:station_count]
    ):
        prior: str | None = None
        for segment_index, ((z0, y0), (z1, y1)) in enumerate(zip(profile, profile[1:])):
            if lod == 2 and segment_index % 2:
                continue
            rib = f"a22.hall.vault-rib.{label}.{segment_index}"
            assembler.beam(
                rib,
                (station_x, y0, z0),
                (station_x, y1, z1),
                thickness,
                thickness,
                "wall_weathered" if station_index < 2 else "trim",
                role="hangar-double-shell-load-bearing-vault-rib",
            )
            if prior is not None:
                _connect(
                    assembler,
                    f"contact.{rib}",
                    prior,
                    rib,
                    "vault-rib-knee-overlap",
                    "endpoint",
                    0.16,
                )
            prior = rib

    # A segmented concrete armour band thickens the front portal silhouette.
    # LOD2 keeps even profile segments, so its armour band advances in the
    # same two-segment cadence and can still seat against an emitted rib.
    cladding_step = 1 if lod == 0 else 2
    for index in range(0, len(profile) - 1, cladding_step):
        z0, y0 = profile[index]
        z1, y1 = profile[min(index + cladding_step, len(profile) - 1)]
        name = f"a22.hall.portal-armour.segment.{index}"
        assembler.panel(
            name,
            (
                (entrance_x + 1.10, y0, z0),
                (entrance_x + 1.10, y1, z1),
                (entrance_x - 8.6, y1, z1),
                (entrance_x - 8.6, y0, z0),
            ),
            1.55,
            "wall",
            role="hangar-thick-segmented-concrete-portal-armour",
        )
        _connect(
            assembler,
            f"contact.{name}",
            f"a22.hall.vault-rib.outer.{index}",
            name,
            "portal-armour-rib-seat",
            "x",
            0.14,
        )

    # Fill the outer-to-inner arch band with real radial shell webs.  The
    # previous longitudinal armour strips gave depth in plan but still read as
    # a wire outline from the production camera; these panels create the
    # enclosed castle-scale wall body around the working opening.
    shell_web_step = 1 if lod == 0 else 2
    for index in range(0, len(profile) - 1, shell_web_step):
        z0, y0 = profile[index]
        z1, y1 = profile[min(index + shell_web_step, len(profile) - 1)]
        inner_z0 = z + (z0 - z) * 0.70
        inner_z1 = z + (z1 - z) * 0.70
        inner_y0 = max(0.16, y0 * 0.72)
        inner_y1 = max(0.16, y1 * 0.72)
        web = f"a22.hall.portal-shell-web.segment.{index}"
        assembler.panel(
            web,
            (
                (entrance_x + 0.55, y0, z0),
                (entrance_x + 0.55, y1, z1),
                (entrance_x + 0.55, inner_y1, inner_z1),
                (entrance_x + 0.55, inner_y0, inner_z0),
            ),
            1.18,
            "wall_weathered" if index % 3 else "wall",
            role="hangar-thick-enclosed-radial-portal-shell-web",
        )
        _connect(
            assembler,
            f"contact.{web}",
            f"a22.hall.vault-rib.outer.{index}",
            web,
            "hangar-portal-shell-web-outer-rib-seat",
            "plan",
            0.16,
        )

    # Monumental service towers carry balconies, door machinery and approach
    # scale.  They sit within the canonical 112 x 70 m envelope.
    for label, tower_z in (("south", z - 29.0), ("north", z + 29.0)):
        base = f"a22.hall.portal-service-tower.{label}.base"
        upper = f"a22.hall.portal-service-tower.{label}.upper"
        cap = f"a22.hall.portal-service-tower.{label}.cap"
        assembler.box(
            base,
            entrance_x - 6.0,
            18.0,
            tower_z,
            15.0,
            36.0,
            12.0,
            "wall_weathered",
            role="hangar-portal-grounded-service-tower",
            route_exempt=True,
        )
        assembler.box(
            upper,
            entrance_x - 9.5,
            46.0,
            tower_z,
            12.0,
            22.0,
            10.0,
            "wall",
            role="hangar-portal-stepped-service-tower",
            route_exempt=True,
        )
        assembler.box(
            cap,
            entrance_x - 9.5,
            57.35,
            tower_z,
            14.0,
            0.70,
            11.5,
            "roof",
            role="hangar-portal-service-tower-cap",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{base}",
            "a20.hall.cavity.floor",
            base,
            "service-tower-foundation-embed",
            "y",
            0.26,
        )
        _connect(
            assembler,
            f"contact.{upper}",
            base,
            upper,
            "service-tower-tier-seat",
            "y",
            0.18,
        )
        _connect(
            assembler,
            f"contact.{cap}",
            upper,
            cap,
            "service-tower-cap-seat",
            "y",
            0.10,
        )
        balcony_count = 4 if lod == 0 else 2 if lod == 1 else 1
        for index in range(balcony_count):
            level = 8.0 + index * 9.0
            balcony = f"a22.hall.portal-service-tower.{label}.balcony.{index}"
            assembler.box(
                balcony,
                entrance_x + 1.4,
                level,
                tower_z,
                6.8,
                0.46,
                8.0,
                "trim",
                role="hangar-human-scale-service-balcony",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{balcony}",
                base if index < 3 else upper,
                balcony,
                "balcony-tower-seat",
                "x",
                0.12,
            )
            if lod < 2:
                rail = f"{balcony}.outer-rail"
                rail_z = tower_z + (-4.2 if label == "south" else 4.2)
                assembler.beam(
                    rail,
                    (entrance_x - 1.8, level + 1.15, rail_z),
                    (entrance_x + 4.7, level + 1.15, rail_z),
                    0.07,
                    0.07,
                    "trim",
                    role="hangar-human-scale-service-balcony-rail",
                )
                _connect(
                    assembler,
                    f"contact.{rail}",
                    balcony,
                    rail,
                    "rail-balcony-seat",
                    "endpoint",
                    0.08,
                )

    # Thick door rails and visible drive housings sell an operable portal.
    for index, door_z in enumerate((z - 24.0, z + 24.0)):
        rail = f"a22.hall.portal-door.rail.{index}"
        assembler.beam(
            rail,
            (entrance_x + 0.6, 0.25, door_z),
            (entrance_x + 0.6, 52.0, door_z),
            0.62,
            0.74,
            "trim",
            role="hangar-heavy-portal-door-track",
        )
        _connect(
            assembler,
            f"contact.{rail}",
            f"a22.hall.portal-service-tower.{'south' if index == 0 else 'north'}.base",
            rail,
            "door-track-tower-seat",
            "endpoint",
            0.14,
        )
        housing = f"a22.hall.portal-door.drive-housing.{index}"
        assembler.cylinder(
            housing,
            entrance_x + 0.3,
            6.0,
            door_z,
            1.45,
            2.6,
            "wall_cool",
            20 if lod == 0 else 12 if lod == 1 else 8,
            role="hangar-portal-door-drive-housing",
        )
        _connect(
            assembler,
            f"contact.{housing}",
            rail,
            housing,
            "drive-housing-track-seat",
            "plan",
            0.10,
        )

    # Longitudinal crane rails and two cross-bridges visibly connect the shell.
    if lod < 2:
        for index, rail_z in enumerate((z - 23.0, z + 23.0)):
            rail = f"a22.hall.crane.longitudinal-rail.{index}"
            assembler.beam(
                rail,
                (entrance_x - 8.0, 38.0, rail_z),
                (entrance_x - 94.0, 38.0, rail_z),
                0.34,
                0.44,
                "trim",
                role="hangar-operational-longitudinal-crane-rail",
            )
            _connect(
                assembler,
                f"contact.{rail}",
                f"a22.hall.vault-rib.door.{1 if index == 0 else 10}",
                rail,
                "crane-rail-vault-seat",
                "endpoint",
                0.12,
            )
        bridge_count = 2 if lod == 0 else 1
        for index, bridge_x in enumerate(
            (entrance_x - 30.0, entrance_x - 66.0)[:bridge_count]
        ):
            bridge = f"a22.hall.crane.bridge.{index}"
            assembler.beam(
                bridge,
                (bridge_x, 37.7, z - 23.4),
                (bridge_x, 37.7, z + 23.4),
                0.52,
                0.68,
                "wall_warm",
                role="hangar-working-overhead-crane-bridge",
            )
            _connect(
                assembler,
                f"contact.{bridge}",
                "a22.hall.crane.longitudinal-rail.0",
                bridge,
                "crane-bridge-rail-seat",
                "endpoint",
                0.14,
            )
            hoist = f"{bridge}.hoist"
            assembler.cylinder_between(
                hoist,
                (bridge_x, 37.6, z),
                (bridge_x, 24.0, z),
                0.16,
                "trim",
                12 if lod == 0 else 8,
                end_radius=0.10,
                role="hangar-working-overhead-crane-hoist",
            )
            _connect(
                assembler,
                f"contact.{hoist}",
                bridge,
                hoist,
                "hoist-bridge-seat",
                "endpoint",
                0.10,
            )

    if lod < 2:
        for side_index, side in enumerate((-1.0, 1.0)):
            ceiling_strip = f"a22.hall.interior-ceiling-practical.{side_index}"
            assembler.beam(
                ceiling_strip,
                (entrance_x - 5.0, 50.5, z + side * 14.8),
                (entrance_x - 80.0, 43.0, z + side * 14.8),
                0.18,
                0.24,
                "accent",
                role="hangar-motivated-longitudinal-ceiling-practical",
            )
            _connect(
                assembler,
                f"contact.{ceiling_strip}",
                f"a22.hall.vault-rib.door.{4 if side < 0 else 7}",
                ceiling_strip,
                "hangar-ceiling-practical-vault-rib-seat",
                "endpoint",
                0.10,
            )
            floor_lane = f"a22.hall.interior-floor-lane.{side_index}"
            assembler.box(
                floor_lane,
                entrance_x - 42.0,
                0.075,
                z + side * 9.0,
                72.0,
                0.05,
                0.34,
                "wall_warm",
                role="hangar-weathered-maintenance-floor-lane",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{floor_lane}",
                "a20.hall.cavity.floor",
                floor_lane,
                "hangar-floor-lane-cavity-floor-seat",
                "y",
                0.08,
            )

    # Docking arms make the large envelope read as a maintained airship.
    arm_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index, arm_x in enumerate(
        (entrance_x - 20.0, entrance_x - 35.0, entrance_x - 51.0, entrance_x - 68.0)[
            :arm_count
        ]
    ):
        side = -1.0 if index % 2 == 0 else 1.0
        arm = f"a22.hall.aerostat.docking-arm.{index}"
        assembler.beam(
            arm,
            (arm_x, 19.0 + (index % 2) * 7.0, z + side * 17.5),
            (arm_x - 4.0, 28.0, z + side * 7.2),
            0.42,
            0.55,
            "wall_warm",
            role="hangar-aerostat-articulated-docking-arm",
        )
        _connect(
            assembler,
            f"contact.{arm}",
            "a20.hall.aerostat.body",
            arm,
            "docking-arm-envelope-seat",
            "endpoint",
            0.12,
        )
        cable = f"a22.hall.aerostat.docking-cable.{index}"
        assembler.cylinder_between(
            cable,
            (arm_x - 4.0, 28.0, z + side * 7.2),
            (arm_x - 6.0, 29.0, z + side * 5.4),
            0.065,
            "trim",
            8,
            end_radius=0.045,
            role="hangar-aerostat-tensioned-docking-cable",
        )
        _connect(
            assembler,
            f"contact.{cable}",
            arm,
            cable,
            "docking-cable-arm-seat",
            "endpoint",
            0.08,
        )

    # A lit multi-bay back wall prevents the interior terminating in a blank
    # dark plane while preserving the hall's depth.
    bay_count = 5 if lod == 0 else 3 if lod == 1 else 1
    back_x = x - hero.width / 2.0 + 3.0
    for index in range(bay_count):
        bay_z = z - 23.0 + index * (46.0 / max(1, bay_count - 1))
        prefix = f"a22.hall.deep-maintenance-bay.{index}"
        back = f"{prefix}.back"
        assembler.box(
            back,
            back_x,
            7.0,
            bay_z,
            0.56,
            11.0,
            7.0,
            "wall_cool",
            role="hangar-deep-maintenance-bay-back",
            route_exempt=True,
        )
        for label, y, height in (
            ("lower", 1.1, 1.0),
            ("header", 12.2, 1.0),
        ):
            frame = f"{prefix}.frame.{label}"
            assembler.box(
                frame,
                back_x + 2.2,
                y,
                bay_z,
                4.8,
                height,
                8.0,
                "trim",
                role="hangar-deep-maintenance-bay-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{frame}",
                back,
                frame,
                "maintenance-bay-frame-seat",
                "x",
                0.12,
            )
        practical = f"{prefix}.practical"
        assembler.box(
            practical,
            back_x + 1.0,
            9.8,
            bay_z,
            2.6,
            0.22,
            4.8,
            "accent",
            role="hangar-motivated-maintenance-bay-practical",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{practical}",
            back,
            practical,
            "maintenance-practical-back-seat",
            "x",
            0.08,
        )

    # Portal-visible machinery clusters and warm work lights give the vault a
    # functioning dock interior instead of an empty arch around the aerostat.
    machine_station_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for station_index in range(machine_station_count):
        station_x = entrance_x - 17.0 - station_index * 24.0
        for side_index, side in enumerate((-1.0, 1.0)):
            machine = f"a22.hall.interior-machine.{station_index}.{side_index}"
            machine_z = z + side * 18.5
            assembler.box(
                machine,
                station_x,
                1.90,
                machine_z,
                7.4,
                3.8,
                5.4,
                "trim",
                role="hangar-dark-operational-dock-machinery-base",
                route_exempt=True,
            )
            rotor = f"{machine}.drive-rotor"
            assembler.cylinder_between(
                rotor,
                (station_x, 3.0, machine_z - side * 3.2),
                (station_x, 3.0, machine_z + side * 3.2),
                1.0,
                "road",
                20 if lod == 0 else 12,
                end_radius=0.62,
                role="hangar-visible-dock-machinery-drive-rotor",
            )
            _connect(
                assembler,
                f"contact.{rotor}",
                machine,
                rotor,
                "hangar-machine-rotor-base-seat",
                "plan",
                0.10,
            )
            pipe = f"{machine}.vertical-service-pipe"
            assembler.cylinder_between(
                pipe,
                (station_x + 2.8, 0.20, machine_z),
                (station_x + 2.8, 12.0, machine_z),
                0.30,
                "wall_warm",
                12 if lod == 0 else 8,
                role="hangar-visible-machinery-vertical-service-pipe",
            )
            _connect(
                assembler,
                f"contact.{pipe}",
                machine,
                pipe,
                "hangar-machine-pipe-base-seat",
                "endpoint",
                0.10,
            )
            worklight = f"{machine}.warm-worklight"
            assembler.box(
                worklight,
                station_x - 1.5,
                9.4,
                machine_z - side * 2.1,
                0.60,
                0.46,
                2.2,
                "accent",
                role="hangar-motivated-machinery-worklight",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{worklight}",
                pipe,
                worklight,
                "hangar-worklight-pipe-seat",
                "plan",
                0.08,
            )
        catwalk = f"a22.hall.interior-machine-catwalk.{station_index}"
        assembler.beam(
            catwalk,
            (station_x, 13.0, z - 20.0),
            (station_x, 13.0, z + 20.0),
            0.62,
            0.92,
            "wall_warm",
            role="hangar-portal-visible-machinery-service-catwalk",
        )
        _connect(
            assembler,
            f"contact.{catwalk}",
            f"a22.hall.interior-machine.{station_index}.0",
            catwalk,
            "hangar-machine-catwalk-base-seat",
            "endpoint",
            0.10,
        )
        for side_index, side in enumerate((-1.0, 1.0)):
            gantry_post = (
                f"a22.hall.interior-machine-catwalk.{station_index}."
                f"grounded-gantry-post.{side_index}"
            )
            assembler.beam(
                gantry_post,
                (station_x, 0.20, z + side * 20.0),
                (station_x, 13.0, z + side * 20.0),
                0.34,
                0.42,
                "trim",
                role="hangar-portal-visible-grounded-maintenance-gantry-post",
            )
            _connect(
                assembler,
                f"contact.{gantry_post}",
                catwalk,
                gantry_post,
                "hangar-maintenance-gantry-post-catwalk-seat",
                "endpoint",
                0.12,
            )

    # Thick portal-side maintenance stacks make the interior read as an
    # occupied working volume.  Their inward-facing bays, floor plates and
    # rails remain clear of the aerostat envelope and central approach.
    maintenance_levels = (
        (8.0, 20.0, 32.0) if lod == 0 else (10.0, 26.0) if lod == 1 else (16.0,)
    )
    for side_label, side in (("south", -1.0), ("north", 1.0)):
        stack = f"a22.hall.portal-maintenance-stack.{side_label}"
        stack_x = entrance_x - 18.0
        stack_z = z + side * 22.5
        assembler.box(
            stack,
            stack_x,
            19.0,
            stack_z,
            32.0,
            38.0,
            8.0,
            "wall_cool",
            role="hangar-thick-portal-side-maintenance-stack",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{stack}",
            "a20.hall.cavity.floor",
            stack,
            "hangar-maintenance-stack-floor-embed",
            "y",
            0.20,
        )
        for level_index, level_y in enumerate(maintenance_levels):
            platform = f"{stack}.service-platform.{level_index}"
            assembler.box(
                platform,
                entrance_x - 14.0,
                level_y,
                z + side * 16.5,
                28.0,
                0.52,
                6.0,
                "trim",
                role="hangar-human-scale-layered-maintenance-platform",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{platform}",
                stack,
                platform,
                "hangar-maintenance-platform-stack-seat",
                "plan",
                0.16,
            )
            bay_back = f"{stack}.occupied-bay.{level_index}.back"
            assembler.box(
                bay_back,
                entrance_x - 14.0,
                level_y + 2.1,
                z + side * 18.15,
                18.0,
                3.4,
                0.48,
                "wall_warm",
                role="hangar-maintenance-stack-deep-occupied-work-bay",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{bay_back}",
                stack,
                bay_back,
                "hangar-maintenance-bay-stack-recess",
                "plan",
                0.10,
            )
            if lod < 2:
                rail = f"{platform}.inward-guard-rail"
                assembler.beam(
                    rail,
                    (
                        entrance_x - 27.5,
                        level_y + 1.12,
                        z + side * 13.45,
                    ),
                    (
                        entrance_x - 0.5,
                        level_y + 1.12,
                        z + side * 13.45,
                    ),
                    0.09,
                    0.10,
                    "trim",
                    role="hangar-human-scale-maintenance-platform-guard-rail",
                )
                _connect(
                    assembler,
                    f"contact.{rail}",
                    platform,
                    rail,
                    "hangar-maintenance-rail-platform-seat",
                    "endpoint",
                    0.08,
                )
        post_offsets = (-26.0, -2.0) if lod < 2 else (-2.0,)
        for post_index, local_x in enumerate(post_offsets):
            post = f"{stack}.grounded-frame-post.{post_index}"
            assembler.beam(
                post,
                (entrance_x + local_x, 0.20, z + side * 18.8),
                (entrance_x + local_x, 36.0, z + side * 18.8),
                0.36,
                0.46,
                "trim",
                role="hangar-grounded-portal-maintenance-frame-post",
            )
            _connect(
                assembler,
                f"contact.{post}",
                stack,
                post,
                "hangar-maintenance-post-stack-seat",
                "endpoint",
                0.12,
            )

    # A low, wide staffed service crown is embedded into the arch apex.
    # Keeping it below the shell silhouette avoids the "hut on a roof" read
    # while retaining an occupied control function above the door machinery.
    headhouse = "a22.hall.portal-crown-headhouse"
    assembler.box(
        headhouse,
        entrance_x - 4.5,
        63.0,
        z,
        12.0,
        7.0,
        34.0,
        "wall_weathered",
        role="hangar-low-wide-arch-integrated-staffed-service-crown",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{headhouse}",
        "a22.hall.vault-rib.outer.4",
        headhouse,
        "hangar-headhouse-vault-crown-seat",
        "plan",
        0.18,
    )
    headhouse_cap = f"{headhouse}.armoured-cap"
    assembler.box(
        headhouse_cap,
        entrance_x - 4.5,
        66.65,
        z,
        15.0,
        0.52,
        38.0,
        "roof",
        role="hangar-portal-headhouse-armoured-weather-cap",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{headhouse_cap}",
        headhouse,
        headhouse_cap,
        "hangar-headhouse-cap-seat",
        "y",
        0.10,
    )
    headhouse_back = f"{headhouse}.occupied-control-bay.back"
    assembler.box(
        headhouse_back,
        entrance_x + 1.65,
        63.0,
        z,
        0.42,
        3.2,
        16.0,
        "wall_warm",
        role="hangar-headhouse-deep-occupied-control-bay-back",
        route_exempt=True,
    )
    for label, control_z, control_y, control_depth, control_height in (
        ("south", z - 9.0, 63.0, 0.60, 4.4),
        ("north", z + 9.0, 63.0, 0.60, 4.4),
        ("header", z, 65.05, 18.6, 0.42),
        ("sill", z, 60.95, 18.6, 0.40),
    ):
        frame = f"{headhouse}.occupied-control-bay.frame.{label}"
        assembler.box(
            frame,
            entrance_x + 0.65,
            control_y,
            control_z,
            2.2,
            control_height,
            control_depth,
            "trim",
            role="hangar-headhouse-deep-control-bay-frame",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{frame}",
            headhouse_back,
            frame,
            "hangar-headhouse-control-frame-seat",
            "x",
            0.10,
        )
    crown_pod_sides = (
        (("south", -1.0), ("north", 1.0)) if lod < 2 else (("south", -1.0),)
    )
    for label, side in crown_pod_sides:
        pod_z = z + side * 12.2
        pod = f"{headhouse}.door-drive-pod.{label}"
        assembler.box(
            pod,
            entrance_x + 0.55,
            62.4,
            pod_z,
            2.6,
            4.0,
            8.0,
            "wall_cool",
            role="hangar-service-crown-integrated-door-drive-pod",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{pod}",
            headhouse,
            pod,
            "hangar-crown-drive-pod-body-seat",
            "x",
            0.10,
        )
        vent_back = f"{pod}.deep-vent.back"
        assembler.box(
            vent_back,
            entrance_x + 1.95,
            62.4,
            pod_z,
            0.38,
            2.7,
            5.6,
            "road",
            role="hangar-crown-door-drive-deep-vent-back",
            route_exempt=True,
        )
        pod_louver_count = 4 if lod == 0 else 2 if lod == 1 else 0
        for index in range(pod_louver_count):
            louver = f"{pod}.deep-vent.louver.{index}"
            assembler.box(
                louver,
                entrance_x + 2.35,
                61.3 + index * (2.2 / max(1, pod_louver_count - 1)),
                pod_z,
                1.15,
                0.20,
                6.2,
                "trim",
                role="hangar-crown-door-drive-heavy-louver",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{louver}",
                vent_back,
                louver,
                "hangar-crown-louver-vent-seat",
                "x",
                0.08,
            )
        pod_light = f"{pod}.working-status-light"
        assembler.box(
            pod_light,
            entrance_x + 2.35,
            64.35,
            pod_z,
            1.0,
            0.24,
            2.2,
            "accent",
            role="hangar-crown-door-drive-working-status-light",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{pod_light}",
            pod,
            pod_light,
            "hangar-crown-status-light-pod-seat",
            "x",
            0.08,
        )
    for label, side in (("south", -1.0), ("north", 1.0)):
        transition = f"{headhouse}.portal-integration-pier.{label}"
        assembler.beam(
            transition,
            (entrance_x + 0.80, 55.0, z + side * 15.2),
            (entrance_x + 0.80, 66.4, z + side * 15.2),
            0.58,
            0.76,
            "wall",
            role="hangar-service-crown-arch-integration-pier",
        )
        _connect(
            assembler,
            f"contact.{transition}",
            "a22.hall.vault-rib.outer.4",
            transition,
            "hangar-service-crown-pier-vault-seat",
            "endpoint",
            0.14,
        )
    headhouse_mast = f"{headhouse}.communications-mast"
    assembler.cylinder_between(
        headhouse_mast,
        (entrance_x - 4.5, 66.4, z),
        (entrance_x - 4.5, 75.0, z),
        0.20,
        "trim",
        12 if lod == 0 else 8,
        end_radius=0.12,
        role="hangar-headhouse-communications-mast",
    )
    _connect(
        assembler,
        f"contact.{headhouse_mast}",
        headhouse_cap,
        headhouse_mast,
        "hangar-headhouse-mast-cap-seat",
        "endpoint",
        0.10,
    )


def _add_lod0_reference_mass_overhaul(
    assembler: a20._A20Assembler,
    command: Any,
    hangar: Any,
    lod: int,
) -> None:
    """Add the reference-scale occupied mass that the prior hero view lacked."""

    if lod != 0:
        return

    # Reviewed connection map for this LOD0-only macro pass:
    # - new command frontage -> existing lower breastwork: 0.18 m plan seat;
    # - frontage arcade backs/frames -> frontage: 0.08-0.12 m facade seat;
    # - balcony/rail -> frontage: 0.10-0.16 m vertical/endpoint seat;
    # - command wing towers -> frontage: 0.18 m plan seat;
    # - command upper mass -> existing upper operations bridge: 0.18 m Y seat;
    # - hangar outer side walls -> cavity floor: 0.22 m foundation embed;
    # - hangar inner walls -> outer walls: 0.18 m plan seat;
    # - service decks/bays -> inner walls: 0.10-0.16 m plan seat;
    # - overhead gantries -> inner walls: 0.12 m endpoint seat;
    # - enlarged aerostat shell -> inherited envelope: 0.20 m plan overlap;
    # - new aerostat nose/tail/bands/gondola/fins -> enlarged shell:
    #   0.10-0.22 m overlap;
    # - foreground generator cluster -> grounded pallet: 0.10-0.16 m seat.

    command_west = command.cx - command.width / 2.0
    command_south = command.cz - command.depth / 2.0

    # Bring a 112 m wide, genuinely thick frontage toward the dual-hero
    # camera.  Five deep arcades, a continuous occupied balcony and two wing
    # towers replace the prior read of disconnected tower boxes.
    frontage = "a22.cmd.reference-mass.lower-grand-terrace"
    frontage_x = command_west + 46.0
    frontage_z = command_south - 15.5
    assembler.box(
        frontage,
        frontage_x,
        13.0,
        frontage_z,
        112.0,
        26.0,
        7.5,
        "wall_weathered",
        role="command-reference-scale-thick-lower-grand-terrace",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{frontage}",
        "a22.cmd.south-curtain.lower-breastwork",
        frontage,
        "command-grand-terrace-breastwork-seat",
        "plan",
        0.18,
    )
    arcade_count = 5
    for index in range(arcade_count):
        bay_x = frontage_x - 34.0 + index * 17.0
        prefix = f"{frontage}.deep-arcade.{index}"
        back = f"{prefix}.occupied-back"
        assembler.box(
            back,
            bay_x,
            10.5 + (index % 2) * 1.4,
            frontage_z - 3.95,
            10.5,
            7.0,
            0.48,
            "wall_warm",
            role="command-reference-deep-occupied-arcade-back",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{back}",
            frontage,
            back,
            "command-arcade-back-terrace-recess",
            "z",
            0.10,
        )
        for label, frame_x, frame_y, frame_w, frame_h in (
            ("west-jamb", bay_x - 6.0, 10.5, 1.5, 9.2),
            ("east-jamb", bay_x + 6.0, 10.5, 1.5, 9.2),
            ("header", bay_x, 14.65, 13.5, 0.90),
        ):
            frame = f"{prefix}.frame.{label}"
            assembler.box(
                frame,
                frame_x,
                frame_y,
                frontage_z - 4.35,
                frame_w,
                frame_h,
                1.20,
                "trim",
                role="command-reference-heavy-arcade-load-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{frame}",
                back,
                frame,
                "command-arcade-frame-back-seat",
                "z",
                0.08,
            )

    balcony = f"{frontage}.continuous-occupied-balcony"
    assembler.box(
        balcony,
        frontage_x,
        25.85,
        frontage_z - 1.3,
        100.0,
        0.90,
        10.0,
        "trim",
        role="command-reference-wide-connected-occupied-balcony",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{balcony}",
        frontage,
        balcony,
        "command-balcony-grand-terrace-seat",
        "y",
        0.14,
    )
    balcony_rail = f"{balcony}.armoured-rail"
    assembler.beam(
        balcony_rail,
        (frontage_x - 49.0, 27.25, frontage_z - 6.15),
        (frontage_x + 49.0, 27.25, frontage_z - 6.15),
        0.12,
        0.16,
        "wall_warm",
        role="command-reference-continuous-balcony-armoured-rail",
    )
    _connect(
        assembler,
        f"contact.{balcony_rail}",
        balcony,
        balcony_rail,
        "command-balcony-rail-deck-seat",
        "endpoint",
        0.10,
    )

    # Reallocate each former monolithic wing's existing three boxes into
    # lower, middle and occupied upper tiers.  This keeps the exact primitive
    # and triangle budget while replacing the three-silo read in the frozen
    # camera with a fortified, visibly load-bearing stair-step silhouette.
    for (
        label,
        wing_x,
        lower_height,
        middle_height,
        upper_height,
    ) in (
        ("west", command_west + 5.0, 34.0, 23.0, 15.0),
        ("east", command_west + 87.0, 40.0, 27.0, 18.0),
    ):
        lower_y = lower_height * 0.5
        middle_y = lower_height + middle_height * 0.5 - 0.20
        upper_y = lower_height + middle_height + upper_height * 0.5 - 0.40
        tower = f"a22.cmd.reference-mass.{label}-terrace-wing"
        assembler.box(
            tower,
            wing_x,
            lower_y,
            command_south - 4.0,
            31.0 if label == "west" else 33.0,
            lower_height,
            31.0,
            "wall",
            role="command-reference-stepped-terrace-wing-lower-bastion",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{tower}",
            frontage,
            tower,
            "command-wing-tower-grand-terrace-seat",
            "plan",
            0.18,
        )
        cap = f"{tower}.broad-weather-cap"
        assembler.box(
            cap,
            wing_x,
            middle_y,
            command_south - 3.4,
            25.0 if label == "west" else 27.0,
            middle_height,
            25.0,
            "wall_weathered",
            role="command-reference-stepped-terrace-wing-middle-operations-tier",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{cap}",
            tower,
            cap,
            "command-wing-cap-tower-seat",
            "y",
            0.12,
        )
        bay = f"{tower}.deep-occupied-command-bay"
        assembler.box(
            bay,
            wing_x,
            upper_y,
            command_south - 2.8,
            17.0 if label == "west" else 19.0,
            upper_height,
            19.0,
            "wall_cool",
            role="command-reference-stepped-terrace-wing-occupied-upper-cabin",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{bay}",
            tower,
            bay,
            "command-wing-bay-tower-recess",
            "z",
            0.10,
        )

    # The central slab is likewise rebuilt from its existing mass, cap and two
    # crown boxes.  Four overlapping tiers expose roof terraces, service
    # platforms and the inherited radar crown without adding a single part.
    upper_mass = "a22.cmd.reference-mass.upper-fortress-terrace"
    assembler.box(
        upper_mass,
        command_west + 46.0,
        48.0,
        command_south + 3.0,
        62.0,
        28.0,
        34.0,
        "wall_weathered",
        role="command-reference-central-fortress-broad-lower-operations-tier",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{upper_mass}",
        "a22.cmd.south-curtain.upper-operations-bridge",
        upper_mass,
        "command-upper-mass-operations-bridge-seat",
        "y",
        0.18,
    )
    upper_cap = f"{upper_mass}.armoured-roof-plate"
    assembler.box(
        upper_cap,
        command_west + 46.0,
        69.6,
        command_south + 2.0,
        50.0,
        15.6,
        28.0,
        "wall",
        role="command-reference-central-fortress-middle-armoured-tier",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{upper_cap}",
        upper_mass,
        upper_cap,
        "command-upper-cap-mass-seat",
        "y",
        0.12,
    )
    sensor_tower = f"{upper_mass}.central-sensor-tower"
    assembler.box(
        sensor_tower,
        command_west + 40.0,
        83.7,
        command_south + 2.0,
        32.0,
        13.0,
        22.0,
        "wall_weathered",
        role="command-reference-central-fortress-upper-sensor-tier",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{sensor_tower}",
        upper_cap,
        sensor_tower,
        "command-sensor-tower-upper-cap-seat",
        "y",
        0.12,
    )
    signals_tower = f"{upper_mass}.asymmetric-signals-tower"
    assembler.box(
        signals_tower,
        command_west + 58.0,
        94.0,
        command_south + 1.0,
        14.0,
        8.0,
        12.0,
        "wall_cool",
        role="command-reference-asymmetric-signals-crown-cabin",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{signals_tower}",
        upper_cap,
        signals_tower,
        "command-signals-tower-upper-cap-seat",
        "y",
        0.12,
    )
    for index in range(4):
        bay_x = command_west + 31.0 + index * 10.0
        bay = f"{upper_mass}.deep-operations-bay.{index}.back"
        assembler.box(
            bay,
            bay_x,
            48.0,
            command_south - 14.45,
            9.0,
            6.2,
            0.70,
            "wall_warm",
            role="command-reference-upper-deep-occupied-operations-bay",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{bay}",
            upper_mass,
            bay,
            "command-upper-bay-fortress-recess",
            "z",
            0.10,
        )
    for label, pipe_x in (
        ("west", command_west + 27.0),
        ("east", command_west + 65.0),
    ):
        pipe = f"{upper_mass}.grounded-service-pipe.{label}"
        assembler.cylinder_between(
            pipe,
            (pipe_x, 0.20, command_south - 15.1),
            (pipe_x, 96.0, command_south - 15.1),
            0.68,
            "wall_warm",
            16,
            end_radius=0.42,
            role="command-reference-grounded-heavy-service-pipe",
        )
        _connect(
            assembler,
            f"contact.{pipe}",
            upper_mass,
            pipe,
            "command-service-pipe-upper-mass-seat",
            "endpoint",
            0.12,
        )
    service_main = f"{upper_mass}.horizontal-service-main"
    assembler.beam(
        service_main,
        (
            command_west + 26.5,
            35.0,
            command_south - 15.1,
        ),
        (
            command_west + 65.5,
            35.0,
            command_south - 15.1,
        ),
        0.38,
        0.46,
        "wall_warm",
        role="command-reference-connected-horizontal-service-main",
    )
    _connect(
        assembler,
        f"contact.{service_main}",
        f"{upper_mass}.grounded-service-pipe.west",
        service_main,
        "command-service-main-riser-seat",
        "endpoint",
        0.10,
    )

    hangar_x, hangar_z = hangar.cx, hangar.cz
    entrance_x = hangar_x + hangar.width / 2.0

    # Continuous outer and inner walls turn the rib cage into an enclosed
    # industrial volume.  The 132 m walls bridge the front portal to the deep
    # vault ribs and carry occupied maintenance decks facing the aerostat.
    for side_label, side in (("south", -1.0), ("north", 1.0)):
        outer_wall = f"a22.hall.reference-volume.outer-side-wall.{side_label}"
        wall_x = hangar_x
        camera_side = side < 0.0
        outer_wall_height = 24.0 if camera_side else 56.0
        inner_wall_height = 20.0 if camera_side else 44.0
        service_deck_y = 18.5 if camera_side else 31.0
        assembler.box(
            outer_wall,
            wall_x,
            outer_wall_height * 0.5,
            hangar_z + side * 31.0,
            132.0,
            outer_wall_height,
            8.0,
            "wall_weathered",
            role="hangar-reference-continuous-thick-outer-side-wall",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{outer_wall}",
            "a20.hall.cavity.floor",
            outer_wall,
            "hangar-outer-wall-cavity-floor-foundation",
            "y",
            0.22,
        )
        wall_cap = f"{outer_wall}.armoured-parapet-cap"
        assembler.box(
            wall_cap,
            wall_x,
            outer_wall_height + 0.35,
            hangar_z + side * 31.0,
            136.0,
            0.70,
            9.5,
            "roof",
            role="hangar-reference-continuous-side-wall-armoured-cap",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{wall_cap}",
            outer_wall,
            wall_cap,
            "hangar-side-wall-cap-seat",
            "y",
            0.12,
        )
        inner_wall = f"a22.hall.reference-volume.inner-service-wall.{side_label}"
        assembler.box(
            inner_wall,
            wall_x,
            inner_wall_height * 0.5,
            hangar_z + side * 25.5,
            126.0,
            inner_wall_height,
            3.0,
            "wall_cool",
            role="hangar-reference-deep-inner-maintenance-wall",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{inner_wall}",
            outer_wall,
            inner_wall,
            "hangar-inner-wall-outer-wall-seat",
            "plan",
            0.18,
        )
        service_deck = f"{inner_wall}.continuous-service-deck"
        assembler.box(
            service_deck,
            wall_x,
            service_deck_y,
            hangar_z + side * 21.8,
            124.0,
            0.60,
            7.0,
            "trim",
            role="hangar-reference-continuous-occupied-maintenance-deck",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{service_deck}",
            inner_wall,
            service_deck,
            "hangar-service-deck-inner-wall-seat",
            "plan",
            0.14,
        )
        for index in range(3):
            bay_x = entrance_x - 18.0 - index * 26.0
            bay = f"{inner_wall}.deep-work-bay.{index}.back"
            bay_y = (
                9.0 + (index % 2) * 6.0 if camera_side else 18.0 + (index % 2) * 12.0
            )
            assembler.box(
                bay,
                bay_x,
                bay_y,
                hangar_z + side * 23.7,
                13.0,
                6.2,
                0.50,
                "wall_warm",
                role="hangar-reference-inner-wall-deep-occupied-work-bay",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{bay}",
                inner_wall,
                bay,
                "hangar-work-bay-inner-wall-recess",
                "plan",
                0.10,
            )
            header = f"{bay}.heavy-load-header"
            assembler.box(
                header,
                bay_x,
                bay_y + 3.35,
                hangar_z + side * 22.9,
                15.0,
                0.50,
                1.6,
                "trim",
                role="hangar-reference-work-bay-heavy-load-header",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{header}",
                bay,
                header,
                "hangar-work-bay-header-seat",
                "plan",
                0.08,
            )

    for gantry_index, gantry_x in enumerate((entrance_x - 24.0, entrance_x - 60.0)):
        bridge = f"a22.hall.reference-volume.overhead-gantry.{gantry_index}"
        assembler.beam(
            bridge,
            (gantry_x, 54.0, hangar_z - 26.0),
            (gantry_x, 54.0, hangar_z + 26.0),
            0.70,
            0.90,
            "trim",
            role="hangar-reference-heavy-overhead-maintenance-gantry",
        )
        _connect(
            assembler,
            f"contact.{bridge}",
            "a22.hall.reference-volume.inner-service-wall.south",
            bridge,
            "hangar-gantry-inner-wall-seat",
            "endpoint",
            0.12,
        )
        for post_index, side in enumerate((-1.0, 1.0)):
            post = f"{bridge}.grounded-post.{post_index}"
            assembler.beam(
                post,
                (gantry_x, 0.20, hangar_z + side * 25.0),
                (gantry_x, 54.0, hangar_z + side * 25.0),
                0.44,
                0.56,
                "trim",
                role="hangar-reference-grounded-heavy-gantry-post",
            )
            _connect(
                assembler,
                f"contact.{post}",
                bridge,
                post,
                "hangar-gantry-post-bridge-seat",
                "endpoint",
                0.12,
            )
    for index, strip_x in enumerate(
        (
            entrance_x - 14.0,
            entrance_x - 42.0,
            entrance_x - 70.0,
        )
    ):
        strip = f"a22.hall.reference-volume.ceiling-light-row.{index}"
        assembler.beam(
            strip,
            (strip_x, 58.0, hangar_z - 17.0),
            (strip_x, 58.0, hangar_z + 17.0),
            0.20,
            0.26,
            "accent",
            role="hangar-reference-motivated-transverse-ceiling-light-row",
        )
        _connect(
            assembler,
            f"contact.{strip}",
            f"a22.hall.reference-volume.overhead-gantry.{0 if index < 2 else 1}",
            strip,
            "hangar-ceiling-light-gantry-seat",
            "endpoint",
            0.08,
        )
    maintenance_floor = "a22.hall.reference-volume.armoured-maintenance-floor"
    assembler.box(
        maintenance_floor,
        hangar_x,
        0.18,
        hangar_z,
        142.0,
        0.36,
        56.0,
        "road",
        role="hangar-reference-grounded-armoured-maintenance-floor",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{maintenance_floor}",
        "a20.hall.cavity.floor",
        maintenance_floor,
        "hangar-maintenance-floor-cavity-floor-seat",
        "y",
        0.16,
    )

    # The inherited 17 m diameter envelope remains as an internal core; this
    # connected 25 m diameter shell makes the docked craft read as a true
    # castle-scale aerostat while preserving every inherited docking anchor.
    aerostat_body = "a22.hall.aerostat.enlarged-envelope.body"
    aerostat_nose = "a22.hall.aerostat.enlarged-envelope.nose"
    aerostat_tail = "a22.hall.aerostat.enlarged-envelope.tail"
    assembler.cylinder_between(
        aerostat_body,
        (entrance_x - 25.0, 43.0, hangar_z),
        (entrance_x - 85.0, 43.0, hangar_z),
        15.5,
        "wall_cool",
        32,
        end_radius=15.5,
        role="hangar-reference-castle-scale-aerostat-envelope",
    )
    _connect(
        assembler,
        f"contact.{aerostat_body}",
        "a20.hall.aerostat.body",
        aerostat_body,
        "aerostat-enlarged-shell-inherited-core-overlap",
        "plan",
        0.20,
    )
    assembler.cylinder_between(
        aerostat_nose,
        (entrance_x - 10.0, 43.0, hangar_z),
        (entrance_x - 25.0, 43.0, hangar_z),
        2.2,
        "wall_cool",
        32,
        end_radius=15.5,
        role="hangar-reference-aerostat-tapered-nose",
    )
    _connect(
        assembler,
        f"contact.{aerostat_nose}",
        aerostat_body,
        aerostat_nose,
        "aerostat-nose-body-overlap",
        "x",
        0.22,
    )
    assembler.cylinder_between(
        aerostat_tail,
        (entrance_x - 85.0, 43.0, hangar_z),
        (entrance_x - 104.0, 43.0, hangar_z),
        15.5,
        "wall_cool",
        32,
        end_radius=1.4,
        role="hangar-reference-aerostat-tapered-tail",
    )
    _connect(
        assembler,
        f"contact.{aerostat_tail}",
        aerostat_body,
        aerostat_tail,
        "aerostat-tail-body-overlap",
        "x",
        0.22,
    )
    for index, band_x in enumerate(
        (
            entrance_x - 38.0,
            entrance_x - 55.0,
            entrance_x - 72.0,
        )
    ):
        band = f"a22.hall.aerostat.enlarged-envelope.service-band.{index}"
        assembler.cylinder_between(
            band,
            (band_x - 0.45, 43.0, hangar_z),
            (band_x + 0.45, 43.0, hangar_z),
            16.0,
            "wall_warm",
            32,
            end_radius=16.0,
            role="hangar-reference-aerostat-heavy-service-band",
        )
        _connect(
            assembler,
            f"contact.{band}",
            aerostat_body,
            band,
            "aerostat-service-band-envelope-seat",
            "plan",
            0.16,
        )
    gondola = "a22.hall.aerostat.enlarged-envelope.occupied-gondola"
    assembler.box(
        gondola,
        entrance_x - 55.0,
        24.6,
        hangar_z,
        26.0,
        7.0,
        10.5,
        "wall_weathered",
        role="hangar-reference-aerostat-large-occupied-gondola",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{gondola}",
        aerostat_body,
        gondola,
        "aerostat-gondola-envelope-seat",
        "y",
        0.20,
    )
    vertical_fin = "a22.hall.aerostat.enlarged-envelope.tail-fin.vertical"
    assembler.panel(
        vertical_fin,
        (
            (entrance_x - 102.0, 43.0, hangar_z),
            (entrance_x - 88.0, 43.0, hangar_z),
            (entrance_x - 99.0, 65.0, hangar_z),
            (entrance_x - 108.0, 58.0, hangar_z),
        ),
        0.48,
        "wall_weathered",
        role="hangar-reference-aerostat-large-vertical-tail-fin",
    )
    _connect(
        assembler,
        f"contact.{vertical_fin}",
        aerostat_tail,
        vertical_fin,
        "aerostat-vertical-fin-tail-seat",
        "plan",
        0.14,
    )
    lateral_fin = "a22.hall.aerostat.enlarged-envelope.tail-fin.lateral"
    assembler.panel(
        lateral_fin,
        (
            (entrance_x - 102.0, 43.0, hangar_z - 1.0),
            (entrance_x - 88.0, 43.0, hangar_z - 1.0),
            (entrance_x - 99.0, 43.0, hangar_z - 20.0),
            (entrance_x - 108.0, 43.0, hangar_z - 14.0),
        ),
        0.48,
        "wall_weathered",
        role="hangar-reference-aerostat-large-lateral-tail-fin",
    )
    _connect(
        assembler,
        f"contact.{lateral_fin}",
        aerostat_tail,
        lateral_fin,
        "aerostat-lateral-fin-tail-seat",
        "plan",
        0.14,
    )
    for index, cradle_x in enumerate((entrance_x - 42.0, entrance_x - 70.0)):
        cradle = f"a22.hall.aerostat.grounded-service-cradle.{index}"
        assembler.box(
            cradle,
            cradle_x,
            12.0,
            hangar_z,
            9.0,
            24.0,
            16.0,
            "trim",
            role="hangar-reference-grounded-aerostat-service-cradle",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{cradle}",
            maintenance_floor,
            cradle,
            "aerostat-cradle-maintenance-floor-seat",
            "y",
            0.14,
        )

    # A single readable logistics beat: an APC is being serviced beside a
    # generator, shield and strapped supply stack.  These pieces sit off the
    # clear center route and reinforce the existing crew/APC cluster.
    cluster_pallet = "a22.story.reference-foreground.apc-service-pallet"
    assembler.box(
        cluster_pallet,
        120.0,
        0.20,
        -165.0,
        9.0,
        0.40,
        5.5,
        "wood",
        role="foreground-reference-grounded-apc-service-pallet",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{cluster_pallet}",
        "a19.route.ramp.deck",
        cluster_pallet,
        "foreground-service-pallet-ground-seat",
        "y",
        0.12,
    )
    generator = f"{cluster_pallet}.field-generator"
    assembler.box(
        generator,
        120.0,
        1.65,
        -165.0,
        5.8,
        2.9,
        3.8,
        "obstacle",
        role="foreground-reference-armoured-field-generator",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{generator}",
        cluster_pallet,
        generator,
        "foreground-generator-pallet-seat",
        "y",
        0.14,
    )
    rotor = f"{generator}.cable-drum"
    assembler.cylinder_between(
        rotor,
        (118.8, 2.0, -167.1),
        (121.2, 2.0, -167.1),
        0.75,
        "trim",
        16,
        end_radius=0.75,
        role="foreground-reference-generator-cable-drum",
    )
    _connect(
        assembler,
        f"contact.{rotor}",
        generator,
        rotor,
        "foreground-generator-drum-body-seat",
        "plan",
        0.10,
    )
    antenna = f"{generator}.service-antenna"
    assembler.cylinder_between(
        antenna,
        (122.2, 2.8, -164.5),
        (122.2, 7.4, -164.5),
        0.10,
        "trim",
        10,
        end_radius=0.07,
        role="foreground-reference-generator-service-antenna",
    )
    _connect(
        assembler,
        f"contact.{antenna}",
        generator,
        antenna,
        "foreground-generator-antenna-body-seat",
        "endpoint",
        0.10,
    )
    shield = "a22.story.reference-foreground.apc-service-shield"
    assembler.box(
        shield,
        130.0,
        1.40,
        -162.0,
        8.0,
        2.8,
        1.2,
        "wall_weathered",
        role="foreground-reference-grounded-apc-service-blast-shield",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{shield}",
        "a19.route.ramp.deck",
        shield,
        "foreground-apc-shield-ground-seat",
        "y",
        0.14,
    )
    for index, crate_x in enumerate((110.5, 114.3)):
        crate = f"a22.story.reference-foreground.apc-supply-crate.{index}"
        assembler.box(
            crate,
            crate_x,
            1.05,
            -169.0,
            3.4,
            2.1,
            3.0,
            "obstacle",
            role="foreground-reference-strapped-apc-supply-crate",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{crate}",
            "a19.route.ramp.deck",
            crate,
            "foreground-apc-crate-ground-seat",
            "y",
            0.12,
        )
        strap = f"{crate}.safety-strap"
        assembler.box(
            strap,
            crate_x,
            1.05,
            -170.55,
            0.32,
            2.3,
            0.18,
            "wall_warm",
            role="foreground-reference-cargo-safety-strap",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{strap}",
            crate,
            strap,
            "foreground-crate-strap-seat",
            "z",
            0.08,
        )

    # Use the final eight LOD0 primitive slots on a camera-side approach
    # surface instead of decorative microdetail.  The thin road skin, worn
    # centre dashes and low edge curbs turn the formerly blank lower third into
    # a readable military approach without replacing gameplay collision.
    approach_x = 141.0
    approach_z = -150.0
    approach_yaw = math.atan2(177.1, -183.4)
    approach = "a22.story.reference-foreground.armoured-approach-surface"
    assembler.box(
        approach,
        approach_x,
        0.04,
        approach_z,
        90.0,
        0.08,
        22.0,
        "road",
        yaw=approach_yaw,
        role="foreground-reference-surface-only-armoured-approach-road",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{approach}",
        "a19.route.ramp.deck",
        approach,
        "foreground-approach-surface-route-seat",
        "y",
        0.08,
    )
    for index, local_x in enumerate((-29.0, -14.5, 0.0, 14.5, 29.0)):
        dash_x, dash_z = _rotate_local(
            approach_x,
            approach_z,
            approach_yaw,
            local_x,
            0.0,
        )
        dash = f"{approach}.worn-centre-dash.{index}"
        assembler.box(
            dash,
            dash_x,
            0.095,
            dash_z,
            7.2,
            0.05,
            0.42,
            "wall_warm",
            yaw=approach_yaw,
            role="foreground-reference-worn-military-approach-marking",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{dash}",
            approach,
            dash,
            "foreground-approach-marking-road-seat",
            "y",
            0.06,
        )
    for label, side in (("left", -1.0), ("right", 1.0)):
        curb_x, curb_z = _rotate_local(
            approach_x,
            approach_z,
            approach_yaw,
            0.0,
            side * 10.7,
        )
        curb = f"{approach}.low-edge-curb.{label}"
        assembler.box(
            curb,
            curb_x,
            0.25,
            curb_z,
            78.0,
            0.50,
            0.55,
            "wall_weathered",
            yaw=approach_yaw,
            role="foreground-reference-low-retaining-road-edge",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{curb}",
            approach,
            curb,
            "foreground-approach-curb-road-seat",
            "y",
            0.08,
        )

    # Sparse, real conifer silhouettes break up the bases of the near and
    # middle ridges.  They are deliberately grouped around existing mountain
    # sources so the authored horizon remains layered 3D instead of a card.
    vegetation_specs = (
        ("west-north", -150.0, 143.0, "a22.skyline.heightfield-source.01", 11.5),
        ("north-west", -126.0, 161.0, "a22.skyline.heightfield-source.09", 13.0),
        ("north-east", 54.0, 162.0, "a22.skyline.heightfield-source.13", 12.0),
        ("east-north", 133.0, 156.0, "a22.skyline.heightfield-source.15", 13.5),
        ("east", 154.0, 92.0, "a22.skyline.heightfield-source.17", 10.5),
        ("west-south", -153.0, -96.0, "a22.skyline.heightfield-source.05", 11.0),
    )
    for label, tree_x, tree_z, ridge_parent, tree_height in vegetation_specs:
        trunk = f"a22.skyline.vegetation.{label}.grounded-trunk"
        assembler.cylinder_between(
            trunk,
            (tree_x, 0.0, tree_z),
            (tree_x, tree_height * 0.48, tree_z),
            0.30,
            "wood",
            6,
            end_radius=0.22,
            role="alpine-vegetation-grounded-conifer-trunk",
        )
        _connect(
            assembler,
            f"contact.{trunk}",
            ridge_parent,
            trunk,
            "conifer-trunk-ridge-ground-contact",
            "endpoint",
            0.12,
        )
        canopy = f"a22.skyline.vegetation.{label}.layered-canopy"
        assembler.cylinder_between(
            canopy,
            (tree_x, tree_height * 0.24, tree_z),
            (tree_x, tree_height, tree_z),
            tree_height * 0.27,
            "obstacle",
            7,
            end_radius=0.18,
            role="alpine-vegetation-layered-dark-conifer-canopy",
        )
        _connect(
            assembler,
            f"contact.{canopy}",
            trunk,
            canopy,
            "conifer-canopy-trunk-overlap",
            "endpoint",
            0.18,
        )


_DISTRICT_MACRO_SPECS = (
    # index, x, z, width, height, depth, profile
    # Keep the bridge anchor first, then prioritize the central visible
    # blocks so every LOD retains a near/mid/far settlement stack.
    (3, -96.0, 118.0, 24.0, 36.0, 17.0, "bridge-head"),
    (15, -8.0, 9.0, 22.0, 32.0, 16.0, "bridge-head"),
    (17, -38.0, 31.0, 21.0, 36.0, 16.0, "shed-spine"),
    (19, -61.0, 79.0, 21.0, 38.0, 16.0, "twin-pylon"),
    # LOD1's east bridge anchor must remain inside the first seven entries.
    (9, 112.0, 137.0, 24.0, 38.0, 18.0, "saw-crown"),
    (2, -116.0, 53.0, 19.0, 27.0, 15.0, "twin-pylon"),
    (1, -138.0, 25.0, 22.0, 31.0, 16.0, "saw-crown"),
    (0, -154.0, -6.0, 18.0, 25.0, 14.0, "split-fin"),
    (5, -34.0, 158.0, 24.0, 39.0, 18.0, "shed-spine"),
    (7, 38.0, 158.0, 25.0, 42.0, 18.0, "twin-pylon"),
    (11, 151.0, 78.0, 23.0, 36.0, 17.0, "split-fin"),
)


def _add_connected_high_rise_city(
    assembler: a20._A20Assembler,
    lod: int,
) -> None:
    """Dress solver-anchored masses with varied structural skyline profiles."""

    specs_by_index = {spec[0]: spec for spec in _DISTRICT_MACRO_SPECS}
    active_indices = (
        (3, 15, 17, 19, 9, 2, 1, 0, 5, 7)
        if lod == 0
        else (3, 9, 2, 1, 0, 5, 7)
        if lod == 1
        else (3, 2, 1, 0)
    )
    active_specs = tuple(specs_by_index[index] for index in active_indices)
    for index, x, z, width, height, depth, profile in active_specs:
        parent = f"a20.district.dense-block.{index}"
        face_z = z - depth / 2.0 - 0.45
        spine = f"a22.city.block.{index}.structural-spine"
        assembler.box(
            spine,
            x + width * (0.22 if index % 2 else -0.22),
            height * 0.52,
            face_z,
            width * 0.20,
            height * 0.78,
            1.10,
            "wall_weathered",
            role=f"kunren-high-rise-{profile}-structural-spine",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{spine}",
            parent,
            spine,
            "district-spine-wall-seat",
            "z",
            0.12,
        )
        fin_count = 3 if lod == 0 else 2 if lod == 1 else 1
        for fin_index in range(fin_count):
            fin_x = (
                x - width * 0.36 + fin_index * (width * 0.72 / max(1, fin_count - 1))
            )
            fin = f"a22.city.block.{index}.grounded-fin.{fin_index}"
            assembler.beam(
                fin,
                (fin_x, 0.16, face_z - 1.8),
                (fin_x, height * 0.72, face_z + 0.6),
                0.30,
                0.52,
                "trim",
                role=f"kunren-high-rise-{profile}-grounded-load-fin",
            )
            _connect(
                assembler,
                f"contact.{fin}",
                parent,
                fin,
                "district-fin-wall-seat",
                "endpoint",
                0.12,
            )

        # One 2.4 m-deep occupied aperture cluster replaces black-window grids.
        back = f"a22.city.block.{index}.occupied-opening.back"
        opening_x = x + (-width * 0.18 if index % 2 else width * 0.16)
        opening_y = min(8.0, height * 0.28)
        assembler.box(
            back,
            opening_x,
            opening_y,
            face_z + 2.8,
            width * 0.34,
            3.2,
            0.44,
            "wall_warm",
            role="district-recessed-occupied-opening-back",
            route_exempt=True,
        )
        for label, px, py, part_width, part_height in (
            (
                "left",
                opening_x - width * 0.20,
                opening_y,
                0.48,
                4.0,
            ),
            (
                "right",
                opening_x + width * 0.20,
                opening_y,
                0.48,
                4.0,
            ),
            (
                "header",
                opening_x,
                opening_y + 1.86,
                width * 0.43,
                0.44,
            ),
            (
                "sill",
                opening_x,
                opening_y - 1.86,
                width * 0.43,
                0.42,
            ),
        ):
            frame = f"a22.city.block.{index}.occupied-opening.frame.{label}"
            assembler.box(
                frame,
                px,
                py,
                face_z + 1.15,
                part_width,
                part_height,
                3.6,
                "trim",
                role="district-deep-opening-structural-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{frame}",
                back,
                frame,
                "district-opening-frame-seat",
                "z",
                0.10,
            )

        eave = height + 0.6
        ridge = height + 4.2 + (index % 3)
        half_w = width * 0.46
        half_d = depth * 0.46
        if profile in {"saw-crown", "twin-pylon"} and lod < 2:
            for roof_index, side in enumerate((-1.0, 1.0)):
                roof = f"a22.city.block.{index}.roof-saw.{roof_index}"
                local_x0 = x + side * width * 0.22
                assembler.panel(
                    roof,
                    (
                        (local_x0 - width * 0.18, eave, z - half_d),
                        (local_x0 + width * 0.18, ridge, z - half_d),
                        (local_x0 + width * 0.18, ridge, z + half_d),
                        (local_x0 - width * 0.18, eave, z + half_d),
                    ),
                    0.24,
                    "roof",
                    role=f"kunren-high-rise-{profile}-nonrepeating-roof",
                )
                _connect(
                    assembler,
                    f"contact.{roof}",
                    f"{parent}.roof-cap",
                    roof,
                    "district-roof-cap-seat",
                    "plan",
                    0.10,
                )
        else:
            roof = f"a22.city.block.{index}.roof-shed"
            assembler.panel(
                roof,
                (
                    (x - half_w, eave, z - half_d),
                    (x + half_w, ridge, z - half_d),
                    (x + half_w, ridge, z + half_d),
                    (x - half_w, eave, z + half_d),
                ),
                0.24,
                "roof",
                role=f"kunren-high-rise-{profile}-nonrepeating-roof",
            )
            _connect(
                assembler,
                f"contact.{roof}",
                f"{parent}.roof-cap",
                roof,
                "district-roof-cap-seat",
                "plan",
                0.10,
            )

    # A few elevated connectors compress the middle distance while leaving all
    # canonical ground routes untouched.
    bridge_specs = (
        ("north", (-96.0, 17.5, 118.0), (-61.0, 17.5, 79.0)),
        ("east", (112.0, 20.0, 137.0), (151.0, 20.0, 78.0)),
        ("centre", (-38.0, 14.0, 31.0), (-8.0, 14.0, 9.0)),
    )
    bridge_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for label, start, end in bridge_specs[:bridge_count]:
        bridge = f"a22.city.elevated-service-bridge.{label}"
        assembler.beam(
            bridge,
            start,
            end,
            0.72,
            1.35,
            "trim",
            role="kunren-connected-high-rise-service-bridge",
        )
        _connect(
            assembler,
            f"contact.{bridge}.start",
            f"a22.city.block.{3 if label == 'north' else 9 if label == 'east' else 17}.structural-spine",
            bridge,
            "bridge-building-seat",
            "endpoint",
            0.14,
        )


def _rotate_local(
    x: float,
    z: float,
    yaw: float,
    local_x: float,
    local_z: float,
) -> tuple[float, float]:
    cosine, sine = math.cos(yaw), math.sin(yaw)
    return (
        x + local_x * cosine - local_z * sine,
        z + local_x * sine + local_z * cosine,
    )


def _vehicle_panel_corners(
    x: float,
    z: float,
    yaw: float,
    points: Sequence[Point3],
) -> tuple[Point3, Point3, Point3, Point3]:
    transformed = []
    for local_x, y, local_z in points:
        world_x, world_z = _rotate_local(x, z, yaw, local_x, local_z)
        transformed.append((world_x, y, world_z))
    return tuple(transformed)  # type: ignore[return-value]


def _add_armoured_vehicle(
    assembler: a20._A20Assembler,
    index: int,
    x: float,
    z: float,
    yaw: float,
    lod: int,
    variant: str,
) -> None:
    """Build a recognizable wheeled vehicle with curved wheels and sloped nose."""

    prefix = f"a22.story.vehicle.{index}.{variant}"
    chassis = f"{prefix}.chassis"
    assembler.box(
        chassis,
        x,
        0.72,
        z,
        7.6,
        0.52,
        2.9,
        "trim",
        yaw=yaw,
        role="grounded-military-vehicle-chassis",
        route_exempt=True,
    )
    body_x, body_z = _rotate_local(x, z, yaw, -0.4, 0.0)
    body = f"{prefix}.armoured-body"
    assembler.box(
        body,
        body_x,
        1.55,
        body_z,
        4.8,
        1.65,
        2.7,
        "obstacle",
        yaw=yaw,
        role="military-vehicle-armoured-body",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{body}",
        chassis,
        body,
        "vehicle-body-chassis-seat",
        "y",
        0.14,
    )
    cabin_x, cabin_z = _rotate_local(x, z, yaw, 2.25, 0.0)
    cabin = f"{prefix}.crew-cabin"
    assembler.box(
        cabin,
        cabin_x,
        2.25,
        cabin_z,
        2.4,
        2.25,
        2.6,
        "wall_weathered",
        yaw=yaw,
        role="military-vehicle-occupied-cabin",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{cabin}",
        chassis,
        cabin,
        "vehicle-cabin-chassis-seat",
        "y",
        0.12,
    )
    hood = f"{prefix}.sloped-hood"
    assembler.panel(
        hood,
        _vehicle_panel_corners(
            x,
            z,
            yaw,
            (
                (3.45, 1.05, -1.30),
                (3.45, 1.05, 1.30),
                (1.30, 2.25, 1.30),
                (1.30, 2.25, -1.30),
            ),
        ),
        0.18,
        "obstacle",
        role="military-vehicle-sloped-armoured-hood",
    )
    _connect(
        assembler,
        f"contact.{hood}",
        cabin,
        hood,
        "vehicle-hood-cabin-seat",
        "plan",
        0.12,
    )
    windshield = f"{prefix}.recessed-windshield"
    windshield_x, windshield_z = _rotate_local(x, z, yaw, 1.12, 0.0)
    assembler.box(
        windshield,
        windshield_x,
        2.55,
        windshield_z,
        0.22,
        1.05,
        2.10,
        "wall_cool",
        yaw=yaw,
        role="military-vehicle-recessed-glazed-windshield",
        route_exempt=True,
    )
    _connect(
        assembler,
        f"contact.{windshield}",
        cabin,
        windshield,
        "windshield-cabin-recess",
        "plan",
        0.10,
    )
    for side_index, side in enumerate((-1.0, 1.0)):
        window_x, window_z = _rotate_local(
            x,
            z,
            yaw,
            2.20,
            side * 1.34,
        )
        side_window = f"{prefix}.crew-side-window.{side_index}.back"
        assembler.box(
            side_window,
            window_x,
            2.62,
            window_z,
            1.18,
            0.78,
            0.16,
            "wall_warm",
            yaw=yaw,
            role="military-vehicle-deep-occupied-side-window-back",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{side_window}",
            cabin,
            side_window,
            "vehicle-side-window-cabin-recess",
            "plan",
            0.08,
        )
        if lod < 2:
            for frame_index, (
                local_x,
                frame_y,
                frame_width,
                frame_height,
            ) in enumerate(
                (
                    (1.50, 2.62, 0.14, 1.04),
                    (2.90, 2.62, 0.14, 1.04),
                    (2.20, 3.08, 1.52, 0.12),
                    (2.20, 2.16, 1.52, 0.12),
                )
            ):
                frame_x, frame_z = _rotate_local(
                    x,
                    z,
                    yaw,
                    local_x,
                    side * 1.43,
                )
                frame = f"{prefix}.crew-side-window.{side_index}.frame.{frame_index}"
                assembler.box(
                    frame,
                    frame_x,
                    frame_y,
                    frame_z,
                    frame_width,
                    frame_height,
                    0.18,
                    "trim",
                    yaw=yaw,
                    role="military-vehicle-side-window-armoured-frame",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{frame}",
                    side_window,
                    frame,
                    "vehicle-window-frame-back-seat",
                    "plan",
                    0.08,
                )

    # Sloped side armour and a real glacis break the inherited delivery-box
    # silhouette.  These plates overlap the body and cabin by 0.10-0.14 m.
    for side_index, side in enumerate((-1.0, 1.0)):
        armour = f"{prefix}.sloped-side-armour.{side_index}"
        assembler.panel(
            armour,
            _vehicle_panel_corners(
                x,
                z,
                yaw,
                (
                    (-3.15, 1.02, side * 1.34),
                    (2.35, 1.02, side * 1.34),
                    (1.55, 2.92, side * 1.34),
                    (-2.15, 3.02, side * 1.34),
                ),
            ),
            0.14,
            "obstacle",
            role="military-vehicle-sloped-side-armour-plate",
        )
        _connect(
            assembler,
            f"contact.{armour}",
            body,
            armour,
            "vehicle-side-armour-body-overlap",
            "plan",
            0.12,
        )
    glacis = f"{prefix}.front-glacis"
    assembler.panel(
        glacis,
        _vehicle_panel_corners(
            x,
            z,
            yaw,
            (
                (3.48, 1.02, -1.30),
                (3.48, 1.02, 1.30),
                (2.22, 2.42, 1.22),
                (2.22, 2.42, -1.22),
            ),
        ),
        0.16,
        "obstacle",
        role="military-vehicle-sloped-front-glacis",
    )
    _connect(
        assembler,
        f"contact.{glacis}",
        cabin,
        glacis,
        "vehicle-front-glacis-cabin-overlap",
        "plan",
        0.12,
    )
    for light_index, local_z in enumerate((-0.82, 0.82)):
        light_x, light_z = _rotate_local(x, z, yaw, 3.57, local_z)
        headlight = f"{prefix}.recessed-headlight.{light_index}"
        assembler.box(
            headlight,
            light_x,
            1.45,
            light_z,
            0.18,
            0.30,
            0.34,
            "accent",
            yaw=yaw,
            role="military-vehicle-recessed-working-headlight",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{headlight}",
            glacis,
            headlight,
            "vehicle-headlight-glacis-recess",
            "plan",
            0.08,
        )

    wheel_pairs = 3 if variant == "apc" else 2
    wheel_segments = 20 if lod == 0 else 12 if lod == 1 else 8
    wheel_positions = (-2.45, 0.0, 2.45) if wheel_pairs == 3 else (-2.35, 2.35)
    for wheel_index, local_x in enumerate(wheel_positions):
        axle_x, axle_z = _rotate_local(x, z, yaw, local_x, 0.0)
        normal_x, normal_z = -math.sin(yaw), math.cos(yaw)
        axle = f"{prefix}.axle.{wheel_index}"
        assembler.cylinder_between(
            axle,
            (
                axle_x - normal_x * 1.58,
                0.72,
                axle_z - normal_z * 1.58,
            ),
            (
                axle_x + normal_x * 1.58,
                0.72,
                axle_z + normal_z * 1.58,
            ),
            0.16,
            "trim",
            wheel_segments,
            role="military-vehicle-real-axle",
        )
        _connect(
            assembler,
            f"contact.{axle}",
            chassis,
            axle,
            "vehicle-axle-chassis-seat",
            "endpoint",
            0.10,
        )
        for side_index, side in enumerate((-1.0, 1.0)):
            wheel = f"{prefix}.wheel.{wheel_index}.{side_index}"
            centre_x = axle_x + normal_x * side * 1.46
            centre_z = axle_z + normal_z * side * 1.46
            assembler.cylinder_between(
                wheel,
                (
                    centre_x - normal_x * 0.18,
                    0.72,
                    centre_z - normal_z * 0.18,
                ),
                (
                    centre_x + normal_x * 0.18,
                    0.72,
                    centre_z + normal_z * 0.18,
                ),
                0.68,
                "road",
                wheel_segments,
                role="military-vehicle-rubber-wheel",
            )
            _connect(
                assembler,
                f"contact.{wheel}",
                axle,
                wheel,
                "wheel-axle-seat",
                "endpoint",
                0.10,
            )
            hub = f"{prefix}.wheel-hub.{wheel_index}.{side_index}"
            assembler.cylinder_between(
                hub,
                (
                    centre_x - normal_x * 0.205,
                    0.72,
                    centre_z - normal_z * 0.205,
                ),
                (
                    centre_x + normal_x * 0.205,
                    0.72,
                    centre_z + normal_z * 0.205,
                ),
                0.28,
                "trim",
                16 if lod == 0 else 10 if lod == 1 else 8,
                role="military-vehicle-visible-wheel-hub",
            )
            _connect(
                assembler,
                f"contact.{hub}",
                wheel,
                hub,
                "wheel-hub-wheel-seat",
                "endpoint",
                0.08,
            )
            if lod < 2:
                fender_x, fender_z = _rotate_local(
                    x,
                    z,
                    yaw,
                    local_x,
                    side * 1.49,
                )
                fender = f"{prefix}.armoured-wheel-fender.{wheel_index}.{side_index}"
                assembler.box(
                    fender,
                    fender_x,
                    1.34,
                    fender_z,
                    1.58,
                    0.18,
                    0.20,
                    "trim",
                    yaw=yaw,
                    role="military-vehicle-wheel-specific-armoured-fender",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{fender}",
                    body,
                    fender,
                    "vehicle-fender-body-seat",
                    "plan",
                    0.08,
                )

    if lod < 2:
        roof_x, roof_z = _rotate_local(x, z, yaw, -0.45, 0.0)
        hatch = f"{prefix}.roof-hatch"
        assembler.cylinder(
            hatch,
            roof_x,
            2.50,
            roof_z,
            0.82,
            0.30,
            "trim",
            20 if lod == 0 else 12,
            role="military-vehicle-armoured-roof-hatch",
        )
        _connect(
            assembler,
            f"contact.{hatch}",
            body,
            hatch,
            "vehicle-hatch-body-seat",
            "y",
            0.10,
        )
        if variant == "apc":
            turret = f"{prefix}.low-profile-turret"
            assembler.cylinder(
                turret,
                roof_x,
                3.10,
                roof_z,
                1.10,
                1.04,
                "obstacle",
                24 if lod == 0 else 14,
                top_radius=0.82,
                role="military-apc-low-profile-armoured-turret",
            )
            _connect(
                assembler,
                f"contact.{turret}",
                hatch,
                turret,
                "vehicle-turret-hatch-ring-seat",
                "y",
                0.10,
            )
            muzzle_x, muzzle_z = _rotate_local(x, z, yaw, 3.0, 0.0)
            weapon = f"{prefix}.turret-weapon"
            assembler.cylinder_between(
                weapon,
                (roof_x, 3.40, roof_z),
                (muzzle_x, 3.48, muzzle_z),
                0.095,
                "trim",
                12 if lod == 0 else 8,
                end_radius=0.065,
                role="military-apc-turret-weapon",
            )
            _connect(
                assembler,
                f"contact.{weapon}",
                turret,
                weapon,
                "vehicle-weapon-turret-seat",
                "endpoint",
                0.08,
            )
        if variant == "radar":
            mast = f"{prefix}.mobile-radar-mast"
            assembler.beam(
                mast,
                (roof_x, 2.78, roof_z),
                (roof_x, 5.8, roof_z),
                0.10,
                0.10,
                "trim",
                role="military-mobile-radar-mast",
            )
            _connect(
                assembler,
                f"contact.{mast}",
                hatch,
                mast,
                "mobile-radar-mast-hatch-seat",
                "endpoint",
                0.08,
            )
            dish = f"{prefix}.mobile-radar-array"
            assembler.panel(
                dish,
                _vehicle_panel_corners(
                    roof_x,
                    roof_z,
                    yaw,
                    (
                        (-1.6, 4.6, 0.0),
                        (1.6, 4.6, 0.0),
                        (1.6, 6.8, 0.0),
                        (-1.6, 6.8, 0.0),
                    ),
                ),
                0.18,
                "wall_cool",
                role="military-mobile-radar-array",
            )
            _connect(
                assembler,
                f"contact.{dish}",
                mast,
                dish,
                "mobile-radar-array-mast-seat",
                "plan",
                0.10,
            )


def _add_checkpoint_and_story(
    assembler: a20._A20Assembler,
    lod: int,
) -> None:
    """Create an inhabited checkpoint, vehicle column and service crew."""

    # V4-A is one macro-only reallocation hypothesis.  The two existing
    # checkpoints sit on opposite sides of the immutable central route, while
    # their cantilevered canopies overlap two metres at 7.8 m clearance.  The
    # former foreground-edge parts then step outward from both checkpoint
    # slabs as one split-height logistics terrace.  No hero, route, camera,
    # material, light, mountain or primitive count changes are involved.
    layer_yaw = math.radians(44.0)
    layer_center = (80.0, -91.0)
    checkpoint_specs = tuple(
        (
            index,
            *_rotate_local(
                layer_center[0],
                layer_center[1],
                layer_yaw,
                local_x,
                0.0,
            ),
            layer_yaw,
        )
        for index, local_x in enumerate((17.0, -17.0))
    )
    checkpoint_count = 2 if lod == 0 else 1
    for index, x, z, yaw in checkpoint_specs[:checkpoint_count]:
        slab_width = 14.0
        slab_depth = 11.0
        slab = f"a22.checkpoint.{index}.grounded-slab"
        assembler.box(
            slab,
            x,
            0.16,
            z,
            slab_width,
            0.32,
            slab_depth,
            "road",
            yaw=yaw,
            role="occupied-checkpoint-grounded-slab",
            route_exempt=True,
        )
        # Each staffed booth remains entirely outside the central clearance.
        outward = 1.0 if index == 0 else -1.0
        back_x, back_z = _rotate_local(x, z, yaw, outward * 3.9, 0.0)
        back = f"a22.checkpoint.{index}.interior-back"
        assembler.box(
            back,
            back_x,
            4.06,
            back_z,
            0.40,
            7.80,
            5.2,
            "wall_warm",
            yaw=yaw,
            role="checkpoint-occupied-interior-back",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{back}",
            slab,
            back,
            "checkpoint-back-slab-seat",
            "y",
            0.10,
        )
        for label, local_z in (("south", -2.7), ("north", 2.7)):
            wall_x, wall_z = _rotate_local(
                x,
                z,
                yaw,
                outward * 1.6,
                local_z,
            )
            wall = f"a22.checkpoint.{index}.side-wall.{label}"
            assembler.box(
                wall,
                wall_x,
                4.06,
                wall_z,
                6.8,
                7.80,
                0.42,
                "wall_weathered",
                yaw=yaw,
                role="checkpoint-structural-side-wall",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{wall}",
                slab,
                wall,
                "checkpoint-wall-slab-seat",
                "y",
                0.10,
            )
        roof = f"a22.checkpoint.{index}.armoured-canopy"
        canopy_width = 36.0
        canopy_depth = 12.0
        canopy_y = 8.08
        assembler.box(
            roof,
            x,
            canopy_y,
            z,
            canopy_width,
            0.52,
            canopy_depth,
            "roof",
            yaw=yaw,
            role="checkpoint-wide-armoured-staffed-weather-canopy",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{roof}",
            f"a22.checkpoint.{index}.side-wall.south",
            roof,
            "checkpoint-roof-wall-seat",
            "y",
            0.12,
        )
        if index == 0:
            sign_x, sign_z = _rotate_local(
                x,
                z,
                yaw,
                0.0,
                -canopy_depth * 0.48,
            )
            sign = f"a22.checkpoint.{index}.overhead-identification-sign"
            assembler.box(
                sign,
                sign_x,
                8.40,
                sign_z,
                12.0,
                1.10,
                0.58,
                "wall_warm",
                yaw=yaw,
                role="checkpoint-wide-overhead-identification-sign",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{sign}",
                roof,
                sign,
                "checkpoint-overhead-sign-canopy-seat",
                "plan",
                0.08,
            )
            for light_index, local_x in enumerate((-7.0, 7.0)):
                light_x, light_z = _rotate_local(
                    x,
                    z,
                    yaw,
                    local_x,
                    -canopy_depth * 0.48,
                )
                canopy_light = (
                    f"a22.checkpoint.{index}.canopy-warning-light.{light_index}"
                )
                assembler.box(
                    canopy_light,
                    light_x,
                    8.25,
                    light_z,
                    0.42,
                    0.32,
                    0.72,
                    "accent",
                    yaw=yaw,
                    role="checkpoint-active-canopy-warning-light",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{canopy_light}",
                    roof,
                    canopy_light,
                    "checkpoint-warning-light-canopy-seat",
                    "plan",
                    0.08,
                )
        canopy_post_specs = (
            (-slab_width * 0.42, -canopy_depth * 0.38),
            (-slab_width * 0.42, canopy_depth * 0.38),
            (slab_width * 0.42, -canopy_depth * 0.38),
            (slab_width * 0.42, canopy_depth * 0.38),
        )
        canopy_post_count = 4 if lod == 0 else 2
        for post_index, (local_x, local_z) in enumerate(
            canopy_post_specs[:canopy_post_count]
        ):
            post_x, post_z = _rotate_local(
                x,
                z,
                yaw,
                local_x,
                local_z,
            )
            post = f"a22.checkpoint.{index}.canopy-post.{post_index}"
            assembler.beam(
                post,
                (post_x, 0.12, post_z),
                (post_x, 7.98, post_z),
                0.16,
                0.19,
                "trim",
                role="checkpoint-wide-canopy-grounded-support-post",
            )
            _connect(
                assembler,
                f"contact.{post}",
                slab,
                post,
                "checkpoint-canopy-post-slab-seat",
                "endpoint",
                0.10,
            )
        practical = f"a22.checkpoint.{index}.interior-practical"
        practical_x, practical_z = _rotate_local(
            x,
            z,
            yaw,
            outward * 3.7,
            0.0,
        )
        assembler.box(
            practical,
            practical_x,
            5.65,
            practical_z,
            0.30,
            0.26,
            3.8,
            "accent",
            yaw=yaw,
            role="checkpoint-motivated-interior-practical",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{practical}",
            back,
            practical,
            "checkpoint-practical-back-seat",
            "plan",
            0.08,
        )

        mount = f"a22.checkpoint.{index}.roof-defence-mount"
        assembler.cylinder(
            mount,
            x,
            8.45,
            z,
            0.52,
            0.42,
            "trim",
            18 if lod == 0 else 10 if lod == 1 else 8,
            top_radius=0.42,
            role="checkpoint-occupied-roof-defence-mount",
        )
        _connect(
            assembler,
            f"contact.{mount}",
            roof,
            mount,
            "checkpoint-defence-mount-roof-seat",
            "y",
            0.10,
        )
        weapon_end_x, weapon_end_z = _rotate_local(x, z, yaw, 2.8, 0.0)
        weapon = f"a22.checkpoint.{index}.roof-defence-weapon"
        assembler.cylinder_between(
            weapon,
            (x, 8.66, z),
            (weapon_end_x, 8.74, weapon_end_z),
            0.07,
            "trim",
            10 if lod == 0 else 8,
            end_radius=0.045,
            role="checkpoint-crewed-defensive-weapon",
        )
        _connect(
            assembler,
            f"contact.{weapon}",
            mount,
            weapon,
            "checkpoint-weapon-mount-seat",
            "endpoint",
            0.08,
        )

        mast_x, mast_z = _rotate_local(x, z, yaw, -2.6, -2.0)
        mast = f"a22.checkpoint.{index}.floodlight-mast"
        assembler.beam(
            mast,
            (mast_x, 0.16, mast_z),
            (mast_x, 14.0, mast_z),
            0.12,
            0.12,
            "trim",
            role="checkpoint-grounded-floodlight-and-sensor-mast",
        )
        _connect(
            assembler,
            f"contact.{mast}",
            slab,
            mast,
            "checkpoint-mast-slab-embed",
            "endpoint",
            0.10,
        )
        flood = f"{mast}.working-floodlight"
        assembler.box(
            flood,
            mast_x,
            13.85,
            mast_z,
            0.38,
            0.26,
            0.56,
            "accent",
            yaw=yaw,
            role="checkpoint-motivated-working-floodlight",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{flood}",
            mast,
            flood,
            "checkpoint-floodlight-mast-seat",
            "plan",
            0.08,
        )
        if lod < 2:
            barrier_start_x, barrier_start_z = _rotate_local(
                x,
                z,
                yaw,
                2.6,
                -4.8,
            )
            barrier_end_x, barrier_end_z = _rotate_local(
                x,
                z,
                yaw,
                2.6,
                5.4,
            )
            barrier = f"a22.checkpoint.{index}.armoured-barrier-boom"
            assembler.beam(
                barrier,
                (barrier_start_x, 1.0, barrier_start_z),
                (barrier_end_x, 1.0, barrier_end_z),
                0.14,
                0.18,
                "accent",
                role="checkpoint-operable-armoured-barrier-boom",
            )
            _connect(
                assembler,
                f"contact.{barrier}",
                slab,
                barrier,
                "checkpoint-barrier-pivot-seat",
                "endpoint",
                0.08,
            )

    # Reallocate the same former edge-only set into ten physically overlapping
    # retaining terraces, one grounded service riser and one warm head per
    # terrace.  The two five-part stairs meet their checkpoint slabs, while
    # the checkpoint canopies join overhead; the central ground corridor stays
    # twenty metres wide and every part retains its existing material family.
    foreground_wall_specs = (
        (
            "left",
            1.0,
        ),
        (
            "right",
            -1.0,
        ),
    )
    wall_segment_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for label, side in foreground_wall_specs:
        checkpoint_index = 0 if side > 0.0 or checkpoint_count == 1 else 1
        for index in range(wall_segment_count):
            local_x = side * (25.0 + index * 11.0)
            terrace_height = 3.2 + index * 2.0
            barrier_x, barrier_z = _rotate_local(
                layer_center[0],
                layer_center[1],
                layer_yaw,
                local_x,
                0.0,
            )
            barrier = f"a22.story.foreground-wall.{label}.pilaster.{index}.0"
            assembler.box(
                barrier,
                barrier_x,
                terrace_height / 2.0,
                barrier_z,
                12.0,
                terrace_height,
                8.2,
                "wall_weathered",
                yaw=layer_yaw,
                role="split-height-connected-logistics-terrace-retaining-mass",
                route_exempt=True,
            )
            parent = (
                f"a22.checkpoint.{checkpoint_index}.grounded-slab"
                if index == 0
                else f"a22.story.foreground-wall.{label}.pilaster.{index - 1}.0"
            )
            _connect(
                assembler,
                f"contact.{barrier}",
                parent,
                barrier,
                "split-height-logistics-terrace-plan-overlap",
                "plan",
                0.50,
            )

            pole_x, pole_z = _rotate_local(
                layer_center[0],
                layer_center[1],
                layer_yaw,
                local_x,
                -3.55,
            )
            pole = f"a22.story.foreground-wall.{label}.pilaster.{index}.1"
            assembler.beam(
                pole,
                (pole_x, 0.16, pole_z),
                (pole_x, terrace_height + 6.0, pole_z),
                0.12,
                0.15,
                "trim",
                role="split-height-logistics-terrace-grounded-service-riser",
            )
            _connect(
                assembler,
                f"contact.{pole}",
                barrier,
                pole,
                "logistics-terrace-riser-ground-seat",
                "endpoint",
                0.10,
            )
            if lod < 2:
                reflector = f"{pole}.working-reflector"
                assembler.box(
                    reflector,
                    pole_x,
                    terrace_height + 5.88,
                    pole_z,
                    0.42,
                    0.24,
                    0.60,
                    "accent",
                    yaw=layer_yaw,
                    role="split-height-logistics-terrace-warm-working-light",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{reflector}",
                    pole,
                    reflector,
                    "logistics-terrace-working-light-riser-seat",
                    "plan",
                    0.08,
                )

    # Surface-only markings sit on the sloped foreground proof ramp.  They
    # preserve the collision mesh and retain the full 18 m visual carriageway,
    # but provide the worn military-route cadence visible in the reference.
    ramp_start = (160.0, -168.0)
    ramp_end = (18.0, -28.0)
    ramp_dx = ramp_end[0] - ramp_start[0]
    ramp_dz = ramp_end[1] - ramp_start[1]
    ramp_length = math.hypot(ramp_dx, ramp_dz)
    ramp_ux = ramp_dx / ramp_length
    ramp_uz = ramp_dz / ramp_length
    ramp_yaw = math.atan2(ramp_uz, ramp_ux)
    ramp_dash_count = 7 if lod == 0 else 4 if lod == 1 else 2
    for index in range(ramp_dash_count):
        t = 0.035 + index * (0.31 / max(1, ramp_dash_count - 1))
        dash = f"a22.story.foreground-ramp.center-dash.{index}"
        assembler.box(
            dash,
            ramp_start[0] + ramp_ux * ramp_length * t,
            0.56 + 1.06 * t,
            ramp_start[1] + ramp_uz * ramp_length * t,
            3.8,
            0.055,
            0.34,
            "wall_warm",
            yaw=ramp_yaw,
            role="foreground-weathered-military-route-centre-marking",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{dash}",
            "a19.route.ramp.deck",
            dash,
            "foreground-route-marking-ramp-seat",
            "y",
            0.08,
        )
    ramp_nx = -ramp_uz
    ramp_nz = ramp_ux
    edge_mark_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for side_label, side in (("left", -1.0), ("right", 1.0)):
        for index in range(edge_mark_count):
            t = 0.035 + index * (0.30 / max(1, edge_mark_count - 1))
            edge_mark = f"a22.story.foreground-ramp.edge-mark.{side_label}.{index}"
            assembler.box(
                edge_mark,
                ramp_start[0] + ramp_ux * ramp_length * t + ramp_nx * side * 7.0,
                0.56 + 1.06 * t,
                ramp_start[1] + ramp_uz * ramp_length * t + ramp_nz * side * 7.0,
                5.2,
                0.050,
                0.24,
                "wall_warm",
                yaw=ramp_yaw,
                role="foreground-weathered-route-edge-marking",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{edge_mark}",
                "a19.route.ramp.deck",
                edge_mark,
                "foreground-edge-marking-ramp-seat",
                "y",
                0.08,
            )

    # Two close, edge-seated blast positions frame the lower third at player
    # height while the 12 m central carriageway remains visually clear.
    near_t = 0.055
    near_ramp_y = 0.54 + 1.06 * near_t
    for side_index, side in enumerate((-1.0, 1.0)):
        anchor_x = ramp_start[0] + ramp_ux * ramp_length * near_t + ramp_nx * side * 8.2
        anchor_z = ramp_start[1] + ramp_uz * ramp_length * near_t + ramp_nz * side * 8.2
        blast = f"a22.story.foreground-blast-position.{side_index}"
        assembler.box(
            blast,
            anchor_x,
            near_ramp_y + 0.60,
            anchor_z,
            4.8,
            1.20,
            1.25,
            "obstacle",
            yaw=ramp_yaw,
            role="foreground-close-grounded-armoured-blast-position",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{blast}",
            "a19.route.ramp.deck",
            blast,
            "foreground-blast-position-ramp-edge-seat",
            "y",
            0.10,
        )
        if lod < 2:
            crate_x, crate_z = _rotate_local(
                anchor_x,
                anchor_z,
                ramp_yaw,
                -1.2,
                side * 1.05,
            )
            crate = f"{blast}.stacked-supply-crate"
            assembler.box(
                crate,
                crate_x,
                near_ramp_y + 1.02,
                crate_z,
                2.0,
                1.85,
                2.0,
                "wall_weathered",
                yaw=ramp_yaw,
                role="foreground-close-stacked-military-supply-crate",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{crate}",
                blast,
                crate,
                "foreground-close-crate-blast-position-seat",
                "plan",
                0.10,
            )
            lid = f"{crate}.armoured-lid"
            assembler.box(
                lid,
                crate_x,
                near_ramp_y + 1.99,
                crate_z,
                2.16,
                0.12,
                2.16,
                "trim",
                yaw=ramp_yaw,
                role="foreground-close-supply-crate-armoured-lid",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{lid}",
                crate,
                lid,
                "foreground-close-crate-lid-seat",
                "y",
                0.08,
            )

    pallet_cluster_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for cluster_index in range(pallet_cluster_count):
        side = (-1.0, 1.0, -1.0)[cluster_index]
        t = 0.095 + cluster_index * 0.065
        pallet_x = ramp_start[0] + ramp_ux * ramp_length * t + ramp_nx * side * 7.3
        pallet_z = ramp_start[1] + ramp_uz * ramp_length * t + ramp_nz * side * 7.3
        ramp_y = 0.54 + 1.06 * t
        pallet = f"a22.story.foreground-cargo.{cluster_index}.pallet"
        assembler.box(
            pallet,
            pallet_x,
            ramp_y + 0.12,
            pallet_z,
            4.2,
            0.24,
            2.5,
            "wood",
            yaw=ramp_yaw,
            role="foreground-grounded-military-cargo-pallet",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{pallet}",
            "a19.route.ramp.deck",
            pallet,
            "foreground-cargo-pallet-ramp-seat",
            "y",
            0.10,
        )
        crate_count = 3 if lod == 0 else 2
        for crate_index in range(crate_count):
            local_x = -1.25 + crate_index * 1.25
            crate_x, crate_z = _rotate_local(
                pallet_x,
                pallet_z,
                ramp_yaw,
                local_x,
                0.0,
            )
            crate = (
                f"a22.story.foreground-cargo.{cluster_index}."
                f"armoured-crate.{crate_index}"
            )
            assembler.box(
                crate,
                crate_x,
                ramp_y + 0.72,
                crate_z,
                1.1,
                1.0,
                1.7,
                "obstacle",
                yaw=ramp_yaw,
                role="foreground-grounded-armoured-logistics-crate",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{crate}",
                pallet,
                crate,
                "foreground-cargo-crate-pallet-seat",
                "y",
                0.10,
            )
            if lod == 2:
                continue
            lid = f"{crate}.armoured-lid"
            assembler.box(
                lid,
                crate_x,
                ramp_y + 1.25,
                crate_z,
                1.24,
                0.12,
                1.84,
                "trim",
                yaw=ramp_yaw,
                role="foreground-cargo-crate-armoured-lid",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{lid}",
                crate,
                lid,
                "foreground-cargo-lid-crate-seat",
                "y",
                0.08,
            )
            strap = f"{crate}.safety-strap"
            assembler.box(
                strap,
                crate_x,
                ramp_y + 0.72,
                crate_z,
                0.20,
                1.08,
                1.90,
                "wall_warm",
                yaw=ramp_yaw,
                role="foreground-cargo-crate-safety-strap",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{strap}",
                crate,
                strap,
                "foreground-cargo-strap-crate-seat",
                "plan",
                0.08,
            )
        if cluster_index == 0 and lod < 2:
            for upper_index, local_x in enumerate((-0.68, 0.68)):
                upper_x, upper_z = _rotate_local(
                    pallet_x,
                    pallet_z,
                    ramp_yaw,
                    local_x,
                    0.0,
                )
                upper = (
                    f"a22.story.foreground-cargo.0.upper-armoured-crate.{upper_index}"
                )
                assembler.box(
                    upper,
                    upper_x,
                    ramp_y + 1.78,
                    upper_z,
                    1.25,
                    1.0,
                    1.85,
                    "wall_weathered",
                    yaw=ramp_yaw,
                    role="foreground-stacked-armoured-logistics-crate",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{upper}",
                    f"a22.story.foreground-cargo.0.armoured-crate.{upper_index}",
                    upper,
                    "foreground-upper-crate-lower-crate-seat",
                    "y",
                    0.10,
                )
                upper_lid = f"{upper}.armoured-lid"
                assembler.box(
                    upper_lid,
                    upper_x,
                    ramp_y + 2.31,
                    upper_z,
                    1.39,
                    0.12,
                    1.99,
                    "trim",
                    yaw=ramp_yaw,
                    role="foreground-upper-cargo-crate-armoured-lid",
                    route_exempt=True,
                )
                _connect(
                    assembler,
                    f"contact.{upper_lid}",
                    upper,
                    upper_lid,
                    "foreground-upper-cargo-lid-crate-seat",
                    "y",
                    0.08,
                )

    if lod < 2:
        # The former road barricades become the occupied safety rail on the
        # overlapping canopy seam, making the two checkpoint roofs read as one
        # usable logistics bridge rather than two isolated awnings.
        for index, local_x in enumerate((-6.0, 0.0, 6.0)):
            barrier_x, barrier_z = _rotate_local(
                layer_center[0],
                layer_center[1],
                layer_yaw,
                local_x,
                -5.4,
            )
            barrier = f"a22.story.central-checkpoint.barricade.{index}"
            assembler.box(
                barrier,
                barrier_x,
                8.90,
                barrier_z,
                5.8,
                1.16,
                0.95,
                "obstacle",
                yaw=layer_yaw,
                role="connected-checkpoint-overhead-logistics-safety-rail",
                route_exempt=True,
            )
            canopy_parent = (
                "a22.checkpoint.1.armoured-canopy"
                if local_x < 0.0 and checkpoint_count > 1
                else "a22.checkpoint.0.armoured-canopy"
            )
            _connect(
                assembler,
                f"contact.{barrier}",
                canopy_parent,
                barrier,
                "connected-checkpoint-safety-rail-canopy-seat",
                "y",
                0.10,
            )
            hazard = f"{barrier}.hazard-panel"
            assembler.box(
                hazard,
                barrier_x,
                9.04,
                barrier_z,
                4.8,
                0.34,
                1.10,
                "accent",
                yaw=layer_yaw,
                role="connected-checkpoint-active-logistics-hazard-panel",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{hazard}",
                barrier,
                hazard,
                "connected-checkpoint-hazard-panel-rail-seat",
                "plan",
                0.08,
            )

    vehicle_specs = (
        (0, 145.0, -150.0, math.radians(15.0), "apc"),
        (1, 155.0, -120.0, math.radians(42.0), "cargo"),
        # Keep the mobile radar visibly adjacent to the aerostat route while
        # leaving the canonical 12 m approach corridor fully unobstructed.
        (2, -12.0, -116.0, math.radians(180.0), "radar"),
        (3, -43.0, -110.0, math.radians(180.0), "cargo"),
    )
    vehicle_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index, x, z, yaw, variant in vehicle_specs[:vehicle_count]:
        _add_armoured_vehicle(
            assembler,
            index,
            x,
            z,
            yaw,
            lod,
            variant,
        )

    if lod < 2:
        weapon_x, weapon_z = 75.0, -95.0
        weapon_mount = "a22.story.central-weapon-position.traverse-mount"
        assembler.cylinder(
            weapon_mount,
            weapon_x,
            1.05,
            weapon_z,
            0.52,
            0.52,
            "trim",
            18 if lod == 0 else 10,
            top_radius=0.42,
            role="central-activity-crewed-weapon-traverse-mount",
        )
        for index, (leg_x, leg_z) in enumerate(((-1.5, -1.0), (1.5, -1.0), (0.0, 1.7))):
            leg = f"a22.story.central-weapon-position.tripod-leg.{index}"
            assembler.beam(
                leg,
                (weapon_x, 0.92, weapon_z),
                (weapon_x + leg_x, 0.10, weapon_z + leg_z),
                0.14,
                0.18,
                "trim",
                role="central-activity-crewed-weapon-grounded-tripod-leg",
            )
            _connect(
                assembler,
                f"contact.{leg}",
                weapon_mount,
                leg,
                "central-weapon-tripod-mount-seat",
                "endpoint",
                0.08,
            )
        barrel = "a22.story.central-weapon-position.barrel"
        assembler.cylinder_between(
            barrel,
            (weapon_x, 1.28, weapon_z),
            (weapon_x + 4.8, 1.70, weapon_z + 2.1),
            0.105,
            "trim",
            14 if lod == 0 else 8,
            end_radius=0.070,
            role="central-activity-crewed-weapon-readable-barrel",
        )
        _connect(
            assembler,
            f"contact.{barrel}",
            weapon_mount,
            barrel,
            "central-weapon-barrel-traverse-seat",
            "endpoint",
            0.08,
        )
        shield = "a22.story.central-weapon-position.armoured-shield"
        assembler.panel(
            shield,
            (
                (weapon_x + 0.35, 0.72, weapon_z - 1.25),
                (weapon_x + 0.35, 0.72, weapon_z + 1.25),
                (weapon_x + 0.35, 2.35, weapon_z + 1.05),
                (weapon_x + 0.35, 2.35, weapon_z - 1.05),
            ),
            0.18,
            "obstacle",
            role="central-activity-crewed-weapon-armoured-shield",
        )
        _connect(
            assembler,
            f"contact.{shield}",
            weapon_mount,
            shield,
            "central-weapon-shield-mount-seat",
            "plan",
            0.08,
        )
        for index, offset in enumerate((-2.4, 2.4)):
            crate = f"a22.story.central-weapon-position.ammo-crate.{index}"
            assembler.box(
                crate,
                weapon_x - 1.8,
                0.42,
                weapon_z + offset,
                1.4,
                0.84,
                1.1,
                "wall_warm",
                role="central-activity-grounded-ammunition-crate",
                route_exempt=True,
            )

    if lod == 2:
        return
    crew_specs = (
        (118.0, -122.0),
        (111.0, -120.0),
        (106.0, -96.0),
        (91.0, -101.0),
        (-42.0, -112.0),
        (-48.0, -88.0),
    )
    crew_count = 6 if lod == 0 else 3
    for index, (x, z) in enumerate(crew_specs[:crew_count]):
        torso = f"a22.story.crew.{index}.torso"
        assembler.cylinder(
            torso,
            x,
            1.18,
            z,
            0.27,
            1.05,
            "obstacle",
            12 if lod == 0 else 8,
            top_radius=0.20,
            role="human-scale-uniformed-maintenance-crew-torso",
        )
        vest_band = f"a22.story.crew.{index}.high-visibility-vest-band"
        assembler.cylinder(
            vest_band,
            x,
            1.26,
            z,
            0.29,
            0.22,
            "accent",
            12 if lod == 0 else 8,
            top_radius=0.25,
            role="human-scale-maintenance-crew-high-visibility-vest-band",
        )
        _connect(
            assembler,
            f"contact.{vest_band}",
            torso,
            vest_band,
            "crew-high-visibility-band-torso-seat",
            "plan",
            0.08,
        )
        head = f"a22.story.crew.{index}.helmet"
        assembler.cylinder(
            head,
            x,
            1.82,
            z,
            0.24,
            0.30,
            "trim",
            12 if lod == 0 else 8,
            top_radius=0.19,
            role="human-scale-uniformed-maintenance-crew-helmet",
        )
        _connect(
            assembler,
            f"contact.{head}",
            torso,
            head,
            "crew-head-torso-seat",
            "y",
            0.08,
        )
        for side_index, side in enumerate((-1.0, 1.0)):
            leg = f"a22.story.crew.{index}.leg.{side_index}"
            assembler.beam(
                leg,
                (x + side * 0.13, 0.08, z),
                (x + side * 0.13, 0.78, z),
                0.09,
                0.10,
                "obstacle",
                role="human-scale-uniformed-maintenance-crew-leg",
            )
            _connect(
                assembler,
                f"contact.{leg}",
                torso,
                leg,
                "crew-leg-torso-seat",
                "endpoint",
                0.08,
            )


def _spec_centre(spec: Any) -> Point3:
    if hasattr(spec, "x") and hasattr(spec, "y") and hasattr(spec, "z"):
        return float(spec.x), float(spec.y), float(spec.z)
    if hasattr(spec, "start") and hasattr(spec, "end"):
        return tuple((float(a) + float(b)) / 2.0 for a, b in zip(spec.start, spec.end))  # type: ignore[return-value]
    if hasattr(spec, "corners"):
        return tuple(
            sum(float(point[index]) for point in spec.corners) / len(spec.corners)
            for index in range(3)
        )  # type: ignore[return-value]
    raise TypeError(f"unsupported spec for density metrics: {type(spec)!r}")


def _depth_density_metrics(
    plan: KunrenPlan,
    camera: ReferenceCamera,
) -> dict[str, Any]:
    origin = camera.location
    direction = tuple(camera.target[index] - origin[index] for index in range(3))
    length = math.sqrt(sum(component * component for component in direction))
    forward = tuple(component / length for component in direction)
    counts = {"near": 0, "mid": 0, "far": 0}
    for group in (
        plan.boxes,
        plan.beams,
        plan.cylinders,
        plan.cylinders_between,
        plan.sloped_panels,
        plan.rocks,
    ):
        for spec in group:
            centre = _spec_centre(spec)
            depth = sum(
                (centre[index] - origin[index]) * forward[index] for index in range(3)
            )
            if depth < 0.0:
                continue
            band = "near" if depth < 100.0 else "mid" if depth < 230.0 else "far"
            counts[band] += 1
    total = sum(counts.values())
    fractions = {key: round(value / max(1, total), 4) for key, value in counts.items()}
    return {
        "rangesM": {"near": [0, 100], "mid": [100, 230], "far": [230, None]},
        "primitiveCounts": counts,
        "fractions": fractions,
        "referenceTargetFractions": REFERENCE_DEPTH_DENSITY_TARGET,
        "diagnosticOnly": True,
    }


def _estimate_triangles(plan: KunrenPlan) -> int:
    return a20._estimated_triangles(plan)


def _rotated_box_bounds(spec: Any) -> tuple[Point3, Point3]:
    cosine = abs(math.cos(float(spec.yaw)))
    sine = abs(math.sin(float(spec.yaw)))
    half_x = (cosine * float(spec.w) + sine * float(spec.d)) / 2.0
    half_z = (sine * float(spec.w) + cosine * float(spec.d)) / 2.0
    return (
        (
            float(spec.x) - half_x,
            float(spec.y) - float(spec.h) / 2.0,
            float(spec.z) - half_z,
        ),
        (
            float(spec.x) + half_x,
            float(spec.y) + float(spec.h) / 2.0,
            float(spec.z) + half_z,
        ),
    )


def _segment_box_hit_fraction(
    start: Point3,
    end: Point3,
    spec: Any,
) -> float | None:
    lower, upper = _rotated_box_bounds(spec)
    entry, exit_ = 0.0, 1.0
    for axis in range(3):
        direction = end[axis] - start[axis]
        if abs(direction) <= 1e-9:
            if start[axis] < lower[axis] or start[axis] > upper[axis]:
                return None
            continue
        first = (lower[axis] - start[axis]) / direction
        second = (upper[axis] - start[axis]) / direction
        if first > second:
            first, second = second, first
        entry = max(entry, first)
        exit_ = min(exit_, second)
        if entry > exit_:
            return None
    return entry


def _command_gate_alignment_diagnostic(
    plan: KunrenPlan,
    command: Any,
) -> dict[str, Any]:
    """Prove that the authored gate faces the immutable west approach."""

    boxes = {spec.name: spec for spec in plan.boxes}
    west_face = float(command.cx - command.width / 2.0)
    centre_z = float(command.cz)
    approach_width = float(command.approach.width)
    portal_back = boxes["a22.cmd.main-portal.interior-back"]
    portal_floor = boxes["a22.cmd.main-portal.floor"]
    south_jamb = boxes["a22.cmd.main-portal.south-jamb"]
    north_jamb = boxes["a22.cmd.main-portal.north-jamb"]
    south_tower = boxes["a22.cmd.monumental-gate-tower.south"]
    north_tower = boxes["a22.cmd.monumental-gate-tower.north"]
    gallery = boxes["a22.cmd.operations-gallery"]
    glacis = {
        spec.name: spec
        for spec in plan.sloped_panels
        if spec.name in {"a22.cmd.glacis.south", "a22.cmd.glacis.north"}
    }

    portal_opening_width = (
        north_jamb.z - north_jamb.d / 2.0 - (south_jamb.z + south_jamb.d / 2.0)
    )
    tower_opening_width = (
        north_tower.z - north_tower.d / 2.0 - (south_tower.z + south_tower.d / 2.0)
    )
    west_face_contacts = {
        "portalBack": abs(portal_back.x - (west_face + 9.8)) <= 0.01,
        "portalFloor": abs(portal_floor.x - (west_face + 4.7)) <= 0.01,
        "portalCentredOnApproach": (
            abs(portal_back.z - centre_z) <= 0.01
            and abs(portal_floor.z - centre_z) <= 0.01
        ),
        "gateTowersSeatAtWestFace": all(
            abs(spec.x - (west_face + 5.0)) <= 0.01
            for spec in (south_tower, north_tower)
        ),
        "portalOpeningContainsRoute": (portal_opening_width >= approach_width),
        "towerOpeningContainsRoute": tower_opening_width >= approach_width,
        "glacisLeansFromWestFace": all(
            min(point[0] for point in spec.corners) <= west_face - 7.1
            and max(point[0] for point in spec.corners) >= west_face + 0.9
            for spec in glacis.values()
        ),
    }

    # Catch the exact A20/A21 regression: facade components with their thin
    # axis along Z and broad axis along X were south-facing.
    legacy_south_face_flags = {
        "portalBack": portal_back.w > portal_back.d,
        "portalFloor": portal_floor.w > portal_floor.d,
        "operationsGallery": gallery.w > gallery.d,
        "gateTowerSouth": (
            abs(south_tower.x - (west_face + 5.0)) > 0.01
            or abs(south_tower.z - (centre_z - 17.0)) > 0.01
        ),
        "gateTowerNorth": (
            abs(north_tower.x - (west_face + 5.0)) > 0.01
            or abs(north_tower.z - (centre_z + 17.0)) > 0.01
        ),
        "glacisSouth": (
            max(point[0] for point in glacis["a22.cmd.glacis.south"].corners)
            - min(point[0] for point in glacis["a22.cmd.glacis.south"].corners)
            > max(point[2] for point in glacis["a22.cmd.glacis.south"].corners)
            - min(point[2] for point in glacis["a22.cmd.glacis.south"].corners)
        ),
    }
    legacy_count = sum(legacy_south_face_flags.values())

    # Trace to a point just in front of the 5 m-deep portal backing wall.
    gate_sightline_target = (west_face + 9.2, 6.2, centre_z)
    blockers = []
    for spec in plan.boxes:
        if spec.name.startswith("a22.cmd.main-portal."):
            continue
        hit = _segment_box_hit_fraction(
            COMMAND_HERO_CAMERA.location,
            gate_sightline_target,
            spec,
        )
        if hit is not None and hit < 0.995:
            blockers.append({"name": spec.name, "hitFraction": round(hit, 5)})

    frame_points = [
        a19._project_point(COMMAND_HERO_CAMERA, (x, y, z))
        for x in (west_face - 0.5, west_face + 6.6)
        for y in (0.12, 13.2)
        for z in (centre_z - 8.2, centre_z + 8.2)
    ]
    xs = [point[0] for point in frame_points]
    ys = [point[1] for point in frame_points]
    projected_frame = {
        "xMin": min(xs),
        "xMax": max(xs),
        "yMin": min(ys),
        "yMax": max(ys),
        "screenWidth": max(xs) - min(xs),
        "screenHeight": max(ys) - min(ys),
    }
    frame_visible = (
        projected_frame["xMin"] >= 0.0
        and projected_frame["xMax"] <= 1.0
        and projected_frame["yMin"] >= 0.0
        and projected_frame["yMax"] <= 1.0
        and projected_frame["screenWidth"] >= 0.12
        and projected_frame["screenHeight"] >= 0.12
    )
    passed = (
        all(west_face_contacts.values())
        and legacy_count == 0
        and not blockers
        and frame_visible
    )
    return {
        "authoritativeEntrance": list(command.entrance),
        "authoritativeApproachStart": list(command.approach.start),
        "authoritativeApproachEnd": list(command.approach.end),
        "authoritativeApproachWidthM": approach_width,
        "westFaceX": west_face,
        "portalOpeningWidthM": portal_opening_width,
        "towerOpeningWidthM": tower_opening_width,
        "westFaceContacts": west_face_contacts,
        "legacySouthFaceFlags": legacy_south_face_flags,
        "legacySouthFacePlacementCount": legacy_count,
        "inspectionCamera": asdict(COMMAND_HERO_CAMERA),
        "projectedVisibleGateFrame": projected_frame,
        "gateFrameVisible": frame_visible,
        "gateSightlineTarget": list(gate_sightline_target),
        "gateSightlineBlockers": blockers,
        "routeAndCollisionMutationCount": 0,
        "pass": passed,
    }


def _validate_a22(
    additions: a20._A20Assembler,
    constraints: Any,
    budget: LODBudget,
    merged: KunrenPlan,
) -> dict[str, Any]:
    metrics = dict(a20._validate_a20(additions, constraints, budget, merged))
    metrics["a22AdditionCount"] = metrics.pop("a20AdditionCount")
    metrics["estimatedTriangles"] = _estimate_triangles(merged)
    metrics["evaluatedTriangleTarget"] = {
        "min": A22_EVALUATED_TRIANGLE_TARGETS[constraints.lod][0],
        "max": A22_EVALUATED_TRIANGLE_TARGETS[constraints.lod][1],
    }
    metrics["geometryBudgetPriority"] = [
        "hero-silhouette",
        "deep-openings",
        "bevel-and-contact",
        "structural-joints",
        "non-wedge-mountain-relief",
        "recognizable-human-scale-props",
    ]
    metrics["primitiveCountIsNotAQualityGate"] = True
    return metrics


def producer_provisional_scorecard(
    evidence_paths: Sequence[str] = (),
) -> dict[str, Any]:
    scores = {
        category: float(PRODUCER_PROVISIONAL_SCORES[category])
        for category in FIXED_SCORE_CATEGORIES
    }
    average = sum(scores.values()) / len(scores)
    return {
        "schema": "hibana-reference-scorecard-producer-provisional-v1",
        "kitVersion": KIT_VERSION,
        "stageId": "kunren",
        "reference": {
            "path": "tools/blender/concepts/kunren-reference-v1.png",
            "sha256": REFERENCE_IMAGE_SHA256,
        },
        "imageGenReference": {
            "privatePath": str(IMAGEGEN_REFERENCE_PATH),
            "sha256": IMAGEGEN_REFERENCE_SHA256,
            "role": "focused fixed 1.65 m macro and atmosphere target",
        },
        "categories": list(FIXED_SCORE_CATEGORIES),
        "scores": scores,
        "average": round(average, 3),
        "minimumPerCategory": 7.0,
        "minimumAverage": 8.0,
        "producerProvisional": True,
        "producerScoreAccepted": False,
        "independentReviewerRequired": True,
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        "strictAuditStatus": "PRODUCER_PROVISIONAL_NO-SHIP",
        "strongestRemainingMismatch": (
            "Only an independent reviewer may determine whether the rebuilt "
            "fortress, working aerostat dock, compressed military city, "
            "weathered PBR and evening alpine depth reach the references"
        ),
        "evidencePaths": list(evidence_paths),
    }


def _filter_inherited_generic_base(
    base: KunrenPlan,
) -> tuple[KunrenPlan, dict[str, Any]]:
    """Remove inherited blockout families before A22 additions are merged.

    A21 remains the independent P0/P1 scorecard and focused visual reference,
    but its geometry is deliberately not used as the A22 base.  The canonical
    A20 structural substrate is filtered here so the final plan itself—not
    merely the proof renderer—contains no old box vehicles, coplanar black
    aperture cards, or radial legacy ridge identities.
    """

    groups = (
        base.boxes,
        base.beams,
        base.cylinders,
        base.cylinders_between,
        base.sloped_panels,
    )
    removed_names: set[str] = set()
    removed_reasons: dict[str, str] = {}

    def removal_reason(spec: Any) -> str | None:
        name = str(spec.name)
        role = str(getattr(spec, "role", "")).lower()
        key = str(getattr(spec, "key", ""))
        if name.startswith(SUPPRESSED_A21_PREFIXES):
            return "explicit-old-generic-family"
        if key == "wall_alt":
            return "inherited-coplanar-black-card-family"
        if (
            "box-vehicle" in role
            or "dark-window" in role
            or "foreground-military-vehicle" in role
            or "parked-hangar-military-vehicle" in role
        ):
            return "inherited-box-vehicle-or-dark-window-family"
        return None

    retained_groups: list[tuple[Any, ...]] = []
    for group in groups:
        retained = []
        for spec in group:
            reason = removal_reason(spec)
            if reason is None:
                retained.append(spec)
            else:
                removed_names.add(spec.name)
                removed_reasons[spec.name] = reason
        retained_groups.append(tuple(retained))

    # Legacy RockSpec names are also replaced in-plan.  The Blender proof
    # deterministically turns these A22 sources into dense eroded heightfields.
    # The wider production camera sits outside the playable boundary.  Push
    # the four south-east visual ridge sources farther into the outer alpine
    # ring so no near-camera rock face can become a screen-corner occluder.
    # These are visual-only sources; gameplay bounds and collision are not
    # changed.
    camera_clearance_ridge_positions = {
        18: (292.0, -255.0),
        19: (265.0, -245.0),
        20: (230.0, -286.0),
        21: (205.0, -270.0),
    }
    renamed_rocks = tuple(
        replace(
            spec,
            name=f"a22.skyline.heightfield-source.{index:02d}",
            x=camera_clearance_ridge_positions.get(index, (spec.x, spec.z))[0],
            z=camera_clearance_ridge_positions.get(index, (spec.x, spec.z))[1],
            role="a22-eroded-asymmetric-heightfield-source",
        )
        for index, spec in enumerate(base.rocks)
    )
    legacy_rock_names = {spec.name for spec in base.rocks}
    retained_connections = tuple(
        connection
        for connection in base.connections
        if connection.parent not in removed_names
        and connection.child not in removed_names
        and connection.parent not in legacy_rock_names
        and connection.child not in legacy_rock_names
    )
    filtered = KunrenPlan(
        boxes=retained_groups[0],
        beams=retained_groups[1],
        cylinders=retained_groups[2],
        cylinders_between=retained_groups[3],
        sloped_panels=retained_groups[4],
        rocks=renamed_rocks,
        connections=retained_connections,
        metadata=base.metadata,
    )
    final_names = set(filtered.names)
    leaked_prefixes = sorted(
        name for name in final_names if name.startswith(SUPPRESSED_A21_PREFIXES)
    )
    leaked_black_cards = sorted(
        spec.name
        for group in (
            filtered.boxes,
            filtered.beams,
            filtered.cylinders,
            filtered.cylinders_between,
            filtered.sloped_panels,
        )
        for spec in group
        if getattr(spec, "key", None) == "wall_alt"
    )
    leaked_legacy_rocks = sorted(final_names.intersection(legacy_rock_names))
    if leaked_prefixes or leaked_black_cards or leaked_legacy_rocks:
        raise RuntimeError(
            "A22 inherited suppression failed: "
            f"prefixes={leaked_prefixes[:4]}, "
            f"blackCards={leaked_black_cards[:4]}, "
            f"legacyRocks={leaked_legacy_rocks[:4]}"
        )
    audit = {
        "baseGeometryVersion": base.metadata["kitVersion"],
        "a21GeometryCloned": False,
        "removedObjectCount": len(removed_names),
        "removedObjectsByReason": {
            reason: sum(1 for value in removed_reasons.values() if value == reason)
            for reason in sorted(set(removed_reasons.values()))
        },
        "removedObjectNames": sorted(removed_names),
        "renamedLegacyRockCount": len(renamed_rocks),
        "legacyRockNamesRemaining": 0,
        "suppressedPrefixNamesRemaining": 0,
        "inheritedWallAltObjectsRemaining": 0,
        "finalBasePrimitiveCount": filtered.primitive_count,
    }
    return filtered, audit


def make_kunren_reference_a22_plan(
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: (Mapping[str, ApproachSpec | Mapping[str, Any]] | None) = None,
    lod_budget: LODBudget | None = None,
) -> KunrenPlan:
    """Build A22 without mutating the authoritative stage mapping."""

    if lod not in A22_LOD_BUDGETS:
        raise ValueError(f"unsupported A22 LOD {lod}")
    before = copy.deepcopy(stage)
    budget = lod_budget or A22_LOD_BUDGETS[lod]
    constraints = constraints_from_authoritative_layout(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=budget,
    )
    inherited = a20.make_kunren_reference_a20_plan(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=budget,
    )
    base, suppression_audit = _filter_inherited_generic_base(inherited)
    additions = a20._A20Assembler(base.names)
    _add_command_macro_rebuild(additions, constraints.command, lod)
    _add_hangar_macro_rebuild(additions, constraints.hangar, lod)
    _add_lod0_reference_mass_overhaul(
        additions,
        constraints.command,
        constraints.hangar,
        lod,
    )
    _add_connected_high_rise_city(additions, lod)
    _add_checkpoint_and_story(additions, lod)

    provisional = KunrenPlan(
        boxes=(*base.boxes, *additions.boxes),
        beams=(*base.beams, *additions.beams),
        cylinders=(*base.cylinders, *additions.cylinders),
        cylinders_between=(
            *base.cylinders_between,
            *additions.cylinders_between,
        ),
        sloped_panels=(*base.sloped_panels, *additions.sloped_panels),
        rocks=(*base.rocks, *additions.rocks),
        connections=(*base.connections, *additions.connections),
        metadata={},
    )
    metrics = _validate_a22(additions, constraints, budget, provisional)
    camera_clearance = {
        MAIN_REFERENCE_CAMERA.name: list(
            a20.camera_solid_hits(provisional, MAIN_REFERENCE_CAMERA)
        ),
        COMMAND_HERO_CAMERA.name: list(
            a20.camera_solid_hits(provisional, COMMAND_HERO_CAMERA)
        ),
    }
    blocked = {name: hits for name, hits in camera_clearance.items() if hits}
    if blocked:
        raise ValueError(f"A22 proof cameras embedded in geometry: {blocked}")
    command_gate_diagnostic = _command_gate_alignment_diagnostic(
        provisional,
        constraints.command,
    )
    if not command_gate_diagnostic["pass"]:
        raise ValueError(
            "A22 authoritative west-face command gate diagnostic failed: "
            f"{command_gate_diagnostic}"
        )
    # The canonical gameplay envelopes stop at the collision roofs.  LOD0 now
    # carries a taller visual-only fortress crown and vault shell, so frame
    # metrics must measure those authored silhouettes rather than under-report
    # them from the immutable collision boxes.
    metric_command = (
        replace(
            constraints.command,
            width=112.0,
            depth=76.0,
            height=118.0,
        )
        if lod == 0
        else constraints.command
    )
    metric_hangar = (
        replace(
            constraints.hangar,
            width=132.0,
            depth=86.0,
            height=92.0,
        )
        if lod == 0
        else constraints.hangar
    )
    hero_metrics = {
        COMMAND_ID: camera_hero_frame_metrics(
            MAIN_REFERENCE_CAMERA,
            metric_command,
        ),
        HANGAR_ID: camera_hero_frame_metrics(
            MAIN_REFERENCE_CAMERA,
            metric_hangar,
        ),
    }
    for landmark_id, values in hero_metrics.items():
        values["referenceTargetWidth"] = REFERENCE_HERO_OCCUPANCY_TARGETS[landmark_id][
            "screenWidth"
        ]
        values["referenceTargetHeight"] = REFERENCE_HERO_OCCUPANCY_TARGETS[landmark_id][
            "screenHeight"
        ]
    metadata = {
        **base.metadata,
        "kitVersion": KIT_VERSION,
        "baseVisualKit": base.metadata["kitVersion"],
        "a21IndependentScorecardCanonical": True,
        "a21GeometryCloned": False,
        "inheritedSuppressionAudit": suppression_audit,
        "lod": lod,
        "constructionOrder": [
            "a21-independent-scorecard-p0-p1-lock",
            "focused-imagegen-original-resolution-analysis",
            "fixed-1p65m-hero-occupancy-camera-lock",
            "authoritative-routes-spawns-collision-freeze",
            "macro-command-fortress-rebuild",
            "macro-working-aerostat-dock-rebuild",
            "compressed-connected-high-rise-city",
            "human-scale-checkpoint-vehicles-and-crew",
            "procedural-pbr-and-evening-atmosphere",
            "private-primary-self-review-before-full-proof",
        ],
        "productionBrief": {
            "landmarks": ["Command Bastion", "Aerostat Vault Hangar"],
            "threeDistantSilhouettes": [
                "command long-range radar crown",
                "double-shell aerostat vault arch",
                "ridge communication and defence tower chain",
            ],
            "facadeAndRoofLanguage": (
                "battered reinforced-concrete load paths, deep occupied bays, "
                "alternating shed/saw crowns and oxidized service steel"
            ),
            "nearMidFarComposition": (
                "inhabited checkpoint and vehicles; connected high-rise "
                "military district; layered eroded alpine ridges"
            ),
            "visualBoundary": (
                "continuous real 3D rock ridges, retaining transitions and "
                "district edge masses; never power lines or raster mattes"
            ),
            "narrativeClusters": [
                "occupied approach checkpoint",
                "armoured vehicle column and mobile radar",
                "command communications operations",
                "aerostat docking, crane and maintenance bays",
            ],
            "forbidden": [
                "generic repeated box skyline",
                "black coplanar aperture cards",
                "box-only vehicles",
                "low-poly mountain wedges",
                "flat clay material response",
                "floating or unverified attachments",
            ],
        },
        "mainReferenceCamera": asdict(MAIN_REFERENCE_CAMERA),
        "commandHeroInspectionCamera": asdict(COMMAND_HERO_CAMERA),
        "commandGateAlignmentDiagnostic": command_gate_diagnostic,
        "heroFrameMetrics": hero_metrics,
        "heroOccupancyReferenceTargets": REFERENCE_HERO_OCCUPANCY_TARGETS,
        "depthDensityMetrics": _depth_density_metrics(
            provisional,
            MAIN_REFERENCE_CAMERA,
        ),
        "proofCameraClearance": camera_clearance,
        "landmarkIdentityContract": {
            "exactCount": 2,
            "ids": [COMMAND_ID, HANGAR_ID],
            "names": ["Command Bastion", "Aerostat Vault Hangar"],
            "thirdLandmarkAllowed": False,
        },
        "authoritativeContracts": {
            "stageBounds": {"size": stage["size"], "changed": False},
            "placementPolicy": ("unchanged-canonical-centres-widths-depths-heights"),
            "approaches": {
                COMMAND_ID: asdict(constraints.command.approach),
                HANGAR_ID: asdict(constraints.hangar.approach),
            },
            "playerSpawns": [list(point) for point in constraints.player_spawns],
            "botSpawns": [list(point) for point in constraints.bot_spawns],
            "collisionPolicy": (
                "visual-only; canonical TypeScript collision remains authoritative"
            ),
        },
        "surfaceResponseContract": {
            "families": [
                "warm-weathered-reinforced-concrete",
                "cool-repaired-reinforced-concrete",
                "oxidized-structural-steel",
                "painted-safety-metal",
                "worked-patched-asphalt",
                "eroded-dusty-alpine-rock",
                "olive-drab-vehicle-paint-and-rubber",
            ],
            "requiredChannels": ["baseColor", "roughness", "normalOrBump"],
            "deepOpeningsAreGeometry": True,
            "blackCardsForbidden": True,
            "flatColorAloneIsBlockout": True,
            "proofMaterialLimit": 12,
        },
        "roleSpecificGeometryProfileContract": {
            "commandPlinthPortalButtressM": [0.12, 0.24],
            "districtFacadeM": [0.05, 0.10],
            "railsVehiclesEquipmentM": [0.01, 0.03],
            "bakedBeforeBatching": True,
            "singleGlobalBevelForbidden": True,
            "normalNoiseAloneIsNotStructuralRealism": True,
        },
        "suppressionContract": {
            "prefixes": list(SUPPRESSED_A21_PREFIXES),
            "reason": (
                "remove inherited box vehicles, near-coplanar black cards and "
                "legacy radial ridge identities before A22 plan merge"
            ),
            "appliedAtPlanMerge": True,
            "audit": suppression_audit,
        },
        "lodContract": {
            "levels": [0, 1, 2],
            "evaluatedTriangleTargets": {
                str(level): {"min": limits[0], "max": limits[1]}
                for level, limits in A22_EVALUATED_TRIANGLE_TARGETS.items()
            },
            "reductionOrder": [
                "crew and tertiary checkpoint fixtures",
                "secondary vehicle equipment and balcony rails",
                "district facade frames and minor connectors",
                "mountain grid density while preserving ridge silhouette",
            ],
            "heroSilhouettesPreservedAtAllLods": True,
            "deepOpeningsPreservedAtAllLods": True,
            "blindDecimationForbidden": True,
        },
        "formalReferenceGate": {
            "categories": list(FIXED_SCORE_CATEGORIES),
            "minimumPerCategory": 7.0,
            "minimumAverage": 8.0,
            "genericBlockoutAutoNoShip": True,
            "producerScoreIsProvisional": True,
            "independentReviewRequired": True,
            "referencePassClaimed": False,
        },
        "privateProofContract": {
            "defaultDirectory": str(PRIVATE_PROOF_DEFAULT),
            "resolution": [1280, 720],
            "minimumViewCount": 8,
            "primarySelfReviewRequired": True,
            "publicAssetWritesAllowed": False,
            "repoBuildIntegrationAllowed": False,
            "manifestWritesAllowed": False,
            "sourceWritesAllowed": False,
            "gitWritesAllowed": False,
            "uiOrMcpWritesAllowed": False,
        },
        "lodBudget": asdict(budget),
        "metrics": metrics,
        "connectionMap": [asdict(connection) for connection in provisional.connections],
        "producerProvisionalScorecard": producer_provisional_scorecard(),
    }
    if stage != before:
        raise RuntimeError("A22 planning mutated authoritative stage input")
    return KunrenPlan(
        boxes=provisional.boxes,
        beams=provisional.beams,
        cylinders=provisional.cylinders,
        cylinders_between=provisional.cylinders_between,
        sloped_panels=provisional.sloped_panels,
        rocks=provisional.rocks,
        connections=provisional.connections,
        metadata=metadata,
    )


def emit_kunren_reference_a22_plan(
    builder: MeshBuilderProtocol,
    plan: KunrenPlan,
) -> Mapping[str, Any]:
    """Emit through the reviewed geometry protocol."""

    return a19.emit_kunren_reference_a19_plan(builder, plan)


def build_kunren_reference_a22(
    builder: MeshBuilderProtocol,
    stage: Mapping[str, Any],
    lod: int,
    **kwargs: Any,
) -> Mapping[str, Any]:
    plan = make_kunren_reference_a22_plan(stage, lod, **kwargs)
    return emit_kunren_reference_a22_plan(builder, plan)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_output_path(path: Path, label: str) -> Path:
    target = path.expanduser().resolve()
    if str(target).startswith(str(REPO_ROOT.resolve())):
        raise ValueError(f"{label} must stay outside the repository")
    if not str(target).startswith("/private/tmp/"):
        raise ValueError(f"{label} must stay under /private/tmp")
    return target


def _ensure_private_reference(output_dir: Path) -> Path:
    if not A21_IMAGEGEN_REFERENCE_PATH.exists():
        raise FileNotFoundError(
            f"missing focused A21 ImageGen reference: {A21_IMAGEGEN_REFERENCE_PATH}"
        )
    actual = _sha256(A21_IMAGEGEN_REFERENCE_PATH)
    if actual != IMAGEGEN_REFERENCE_SHA256:
        raise ValueError(
            "focused ImageGen reference hash mismatch: "
            f"{actual} != {IMAGEGEN_REFERENCE_SHA256}"
        )
    target = output_dir / "concepts/kunren-a22-imagegen-reference.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(A21_IMAGEGEN_REFERENCE_PATH, target)
    return target


def _a22_proof_views() -> tuple[ReferenceCamera, ...]:
    return (
        MAIN_REFERENCE_CAMERA,
        ReferenceCamera(
            "CAM_Kunren_A22_CheckpointRoute_1p65",
            (154.0, 1.65, -141.0),
            (67.0, 8.0, -57.0),
            24.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="inhabited-checkpoint-armoured-column-and-route-depth",
        ),
        COMMAND_HERO_CAMERA,
        ReferenceCamera(
            "CAM_Kunren_A22_CommandOblique_1p65",
            (147.0, 1.65, 12.0),
            (73.0, 27.0, 83.0),
            30.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="command-glacis-flank-towers-deep-bays-and-radar-crown",
        ),
        ReferenceCamera(
            "CAM_Kunren_A22_HangarApproach_1p65",
            (-4.0, 1.65, -100.0),
            (-84.0, 24.0, -100.0),
            21.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="double-shell-airship-dock-service-towers-and-door-drives",
        ),
        ReferenceCamera(
            "CAM_Kunren_A22_HangarInterior_1p65",
            (-38.0, 1.65, -112.0),
            (-115.0, 16.0, -100.0),
            23.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="aerostat-cranes-docking-arms-catwalks-and-lit-deep-bays",
        ),
        ReferenceCamera(
            "CAM_Kunren_A22_CityRoute_1p65",
            (-16.0, 1.65, 15.0),
            (-25.0, 18.0, 115.0),
            24.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="compressed-connected-high-rise-military-city",
        ),
        ReferenceCamera(
            "CAM_Kunren_A22_Aerial",
            (190.0, 115.0, -220.0),
            (-5.0, 12.0, 0.0),
            45.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=115.0,
            intent="two-landmark-stage-composition-and-layered-3d-boundary",
        ),
    )


def _a22_orthographic_views() -> tuple[
    tuple[str, Point3, Point3, float],
    ...,
]:
    return (
        ("ORTHO_Kunren_A22_East", (420.0, 62.0, 0.0), (0.0, 18.0, 0.0), 340.0),
        ("ORTHO_Kunren_A22_West", (-420.0, 62.0, 0.0), (0.0, 18.0, 0.0), 340.0),
        ("ORTHO_Kunren_A22_North", (0.0, 62.0, 420.0), (0.0, 18.0, 0.0), 340.0),
        ("ORTHO_Kunren_A22_South", (0.0, 62.0, -420.0), (0.0, 18.0, 0.0), 340.0),
        ("ORTHO_Kunren_A22_Top", (0.0, 420.0, 0.0), (0.0, 0.0, 0.0), 340.0),
        ("ORTHO_Kunren_A22_Bottom", (0.0, -420.0, 0.0), (0.0, 0.0, 0.0), 340.0),
    )


def _scene_triangle_audit(scene: Any) -> dict[str, int]:
    import bpy  # type: ignore

    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = 0
    mesh_objects = 0
    material_slots = 0
    vertices = 0
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        mesh_objects += 1
        material_slots += max(1, len(obj.data.materials))
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        vertices += len(mesh.vertices)
        triangles += sum(max(1, len(polygon.vertices) - 2) for polygon in mesh.polygons)
        evaluated.to_mesh_clear()
    return {
        "meshObjects": mesh_objects,
        "vertices": vertices,
        "evaluatedTriangles": triangles,
        "estimatedDrawCalls": material_slots,
    }


def _run_blender_private_proof(
    plan: KunrenPlan,
    output_dir: Path,
    *,
    primary_only: bool = False,
    resume_primary: bool = False,
    diagnostic_view: str | None = None,
) -> dict[str, Any]:
    """Build, self-review and render the isolated A22 production-art proof."""

    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    output_dir = _private_output_path(output_dir, "A22 proof output")
    output_dir.mkdir(parents=True, exist_ok=True)
    views_dir = output_dir / "views"
    ortho_dir = output_dir / "orthographic-audit"
    primary_dir = output_dir / "primary-review"
    diagnostics_dir = output_dir / "diagnostics"
    for directory in (views_dir, ortho_dir, primary_dir, diagnostics_dir):
        directory.mkdir(parents=True, exist_ok=True)
    imagegen_reference = _ensure_private_reference(output_dir)
    primary_blend = output_dir / "kunren-a22-primary-review.blend"
    primary_manifest_path = output_dir / "primary-review-manifest.json"

    def runtime_point(point: Point3) -> Vector:
        return Vector((point[0], -point[2], point[1]))

    proof_state: dict[str, Any]
    if resume_primary:
        if not primary_blend.exists() or not primary_manifest_path.exists():
            raise FileNotFoundError(
                "A22 --resume-primary requires the primary blend and manifest"
            )
        bpy.ops.wm.open_mainfile(filepath=str(primary_blend))
        # The meshes are batched in metres.  Object coordinates therefore
        # preserve real-scale pores, staining and roughness breakup, whereas
        # Generated coordinates would normalize each large batch and stretch
        # the surface response across the whole stage.
        for material in bpy.data.materials:
            if not material.name.startswith("A22_MAT_") or material.node_tree is None:
                continue
            texcoord = next(
                (
                    node
                    for node in material.node_tree.nodes
                    if node.bl_idname == "ShaderNodeTexCoord"
                ),
                None,
            )
            mapping = next(
                (
                    node
                    for node in material.node_tree.nodes
                    if node.bl_idname == "ShaderNodeMapping"
                ),
                None,
            )
            if texcoord is None or mapping is None:
                continue
            for link in list(mapping.inputs["Vector"].links):
                material.node_tree.links.remove(link)
            material.node_tree.links.new(
                texcoord.outputs["Object"],
                mapping.inputs["Vector"],
            )
        proof_state = json.loads(primary_manifest_path.read_text(encoding="utf-8"))[
            "sceneAudit"
        ]
    else:
        scratch_dir = output_dir / "_reviewed-builder-scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)

        # The A19 implementation is the reviewed connection-aware primitive
        # emitter used by A20/A21.  It writes only to private scratch, and the
        # complete A22 plan remains live for the role-specific finishing pass.
        inherited_main = a19.MAIN_REFERENCE_CAMERA
        inherited_version = a19.KIT_VERSION
        try:
            a19.MAIN_REFERENCE_CAMERA = MAIN_REFERENCE_CAMERA
            a19.KIT_VERSION = KIT_VERSION
            scratch_manifest = a19._run_blender_private_proof(
                plan,
                scratch_dir,
            )
        finally:
            a19.MAIN_REFERENCE_CAMERA = inherited_main
            a19.KIT_VERSION = inherited_version

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
        scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.exposure = 0.10

        root = bpy.data.collections.get("HB_kunren_A19_ROOT")
        if root is not None:
            root.name = "HB_kunren_A22_ROOT"
            root["a22KitVersion"] = KIT_VERSION
            root["a22ExactLandmarkCount"] = 2
            root["a22ReleaseDecision"] = "NO-SHIP_PENDING_INDEPENDENT_REVIEW"
        for collection in bpy.data.collections:
            if collection.name.startswith("HB_kunren_"):
                collection["a22KitVersion"] = KIT_VERSION

        suppressed: list[str] = []
        for obj in list(bpy.data.objects):
            part = obj.get("a19PartName")
            role = obj.get("a19Role")
            key = obj.get("a19MaterialKey")
            if not isinstance(part, str):
                continue
            inherited_black_card = key == "wall_alt" and not part.startswith("a22.")
            inherited_thin_bay = part.startswith(
                "a21.district.facade-finish."
            ) and part.endswith(".deep-bay")
            if (
                part.startswith(SUPPRESSED_A21_PREFIXES)
                or inherited_black_card
                or inherited_thin_bay
            ):
                suppressed.append(part)
                bpy.data.objects.remove(obj, do_unlink=True)

        palette = {
            "wall": (0.380, 0.325, 0.260, 1.0),
            # A22 alone repurposes the inherited, otherwise forbidden
            # wall_alt slot as a dedicated practical-light lens material.
            "wall_alt": (0.750, 0.220, 0.015, 1.0),
            "wall_cool": (0.185, 0.215, 0.235, 1.0),
            "wall_warm": (0.420, 0.155, 0.026, 1.0),
            "wall_weathered": (0.285, 0.235, 0.185, 1.0),
            "roof": (0.032, 0.041, 0.046, 1.0),
            "trim": (0.028, 0.036, 0.040, 1.0),
            "accent": (0.560, 0.205, 0.018, 1.0),
            "terrain": (0.265, 0.235, 0.190, 1.0),
            "obstacle": (0.130, 0.170, 0.065, 1.0),
            "wood": (0.190, 0.085, 0.025, 1.0),
            "road": (0.026, 0.030, 0.033, 1.0),
        }

        def make_material(
            key: str,
            base: tuple[float, float, float, float],
        ) -> Any:
            material = bpy.data.materials.new(f"A22_MAT_{key}")
            material.diffuse_color = base
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()
            output = nodes.new("ShaderNodeOutputMaterial")
            shader = nodes.new("ShaderNodeBsdfPrincipled")
            texcoord = nodes.new("ShaderNodeTexCoord")
            mapping = nodes.new("ShaderNodeMapping")
            grime_mapping = nodes.new("ShaderNodeMapping")
            macro = nodes.new("ShaderNodeTexNoise")
            pores = nodes.new("ShaderNodeTexNoise")
            grime = nodes.new("ShaderNodeTexNoise")
            color_ramp = nodes.new("ShaderNodeValToRGB")
            grime_ramp = nodes.new("ShaderNodeValToRGB")
            color_mix = nodes.new("ShaderNodeMixRGB")
            panel_mix = nodes.new("ShaderNodeMixRGB")
            contact_mix = nodes.new("ShaderNodeMixRGB")
            ambient_occlusion = nodes.new("ShaderNodeAmbientOcclusion")
            panel_vertical = nodes.new("ShaderNodeTexWave")
            panel_horizontal = nodes.new("ShaderNodeTexWave")
            panel_minimum = nodes.new("ShaderNodeMath")
            panel_ramp = nodes.new("ShaderNodeValToRGB")
            relief_mix = nodes.new("ShaderNodeMixRGB")
            relief_panel_mix = nodes.new("ShaderNodeMixRGB")
            roughness = nodes.new("ShaderNodeMapRange")
            bump = nodes.new("ShaderNodeBump")
            macro.inputs["Scale"].default_value = {
                "terrain": 1.35,
                "road": 3.2,
                "wall": 2.5,
                "wall_weathered": 2.1,
            }.get(key, 6.0)
            macro.inputs["Detail"].default_value = 7.2
            macro.inputs["Roughness"].default_value = 0.76
            pores.inputs["Scale"].default_value = {
                "wall": 68.0,
                "wall_weathered": 74.0,
                "terrain": 42.0,
                "road": 55.0,
            }.get(key, 24.0)
            pores.inputs["Detail"].default_value = 3.2
            pores.inputs["Roughness"].default_value = 0.82
            grime.inputs["Scale"].default_value = 0.56
            grime.inputs["Detail"].default_value = 5.0
            grime.inputs["Roughness"].default_value = 0.86
            grime_mapping.inputs["Scale"].default_value = (
                2.4,
                2.4,
                0.16,
            )
            low = 0.50 if key not in {"road", "wall_alt"} else 0.68
            high = 1.32 if key not in {"accent", "wall_alt"} else 1.10
            color_ramp.color_ramp.elements[0].position = 0.24
            color_ramp.color_ramp.elements[0].color = tuple(
                max(0.0, value * low) for value in base[:3]
            ) + (1.0,)
            color_ramp.color_ramp.elements[1].position = 0.79
            color_ramp.color_ramp.elements[1].color = tuple(
                min(1.0, value * high) for value in base[:3]
            ) + (1.0,)
            middle = color_ramp.color_ramp.elements.new(0.50)
            middle.color = tuple(min(1.0, value * 0.88) for value in base[:3]) + (1.0,)
            grime_ramp.color_ramp.elements[0].position = 0.40
            grime_ramp.color_ramp.elements[0].color = (
                0.018,
                0.014,
                0.010,
                1.0,
            )
            grime_ramp.color_ramp.elements[1].position = 0.68
            grime_ramp.color_ramp.elements[1].color = tuple(
                min(1.0, value * 0.74) for value in base[:3]
            ) + (1.0,)
            color_mix.blend_type = "MULTIPLY"
            color_mix.inputs[0].default_value = (
                0.54 if key in {"wall", "wall_weathered", "terrain", "road"} else 0.24
            )
            contact_mix.blend_type = "MULTIPLY"
            contact_mix.inputs[0].default_value = (
                0.48
                if key in {"wall", "wall_weathered", "wall_cool", "terrain", "road"}
                else 0.22
            )
            ambient_occlusion.inputs["Distance"].default_value = (
                3.6
                if key in {"wall", "wall_weathered", "terrain"}
                else 1.8
                if key in {"wall_cool", "roof", "trim", "road"}
                else 0.9
            )
            panel_vertical.wave_type = "BANDS"
            panel_vertical.bands_direction = "X"
            panel_vertical.wave_profile = "TRI"
            panel_vertical.inputs["Scale"].default_value = 0.13
            panel_vertical.inputs["Distortion"].default_value = 2.80
            panel_vertical.inputs["Detail"].default_value = 3.2
            panel_horizontal.wave_type = "BANDS"
            panel_horizontal.bands_direction = "Z"
            panel_horizontal.wave_profile = "TRI"
            panel_horizontal.inputs["Scale"].default_value = 0.09
            panel_horizontal.inputs["Distortion"].default_value = 1.70
            panel_horizontal.inputs["Detail"].default_value = 3.2
            panel_minimum.operation = "MINIMUM"
            panel_ramp.color_ramp.interpolation = "EASE"
            panel_ramp.color_ramp.elements[0].position = 0.030
            panel_ramp.color_ramp.elements[0].color = (0.18, 0.21, 0.22, 1.0)
            panel_ramp.color_ramp.elements[1].position = 0.105
            panel_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
            panel_mix.blend_type = "MULTIPLY"
            panel_mix.inputs[0].default_value = {
                "wall": 0.20,
                "wall_weathered": 0.22,
                "wall_cool": 0.06,
                "roof": 0.12,
                "trim": 0.10,
                "terrain": 0.0,
                "road": 0.04,
            }.get(key, 0.0)
            relief_mix.blend_type = "MULTIPLY"
            relief_mix.inputs[0].default_value = 0.42
            relief_panel_mix.blend_type = "MULTIPLY"
            relief_panel_mix.inputs[0].default_value = {
                "wall": 0.26,
                "wall_weathered": 0.30,
                "wall_cool": 0.08,
                "roof": 0.16,
                "trim": 0.14,
                "terrain": 0.0,
                "road": 0.05,
            }.get(key, 0.0)
            roughness.inputs["To Min"].default_value = (
                0.30
                if key in {"trim", "roof", "wall_cool"}
                else 0.40
                if key in {"wall", "wall_weathered", "terrain"}
                else 0.58
            )
            roughness.inputs["To Max"].default_value = (
                0.72 if key in {"trim", "roof", "wall_cool"} else 0.96
            )
            bump.inputs["Strength"].default_value = (
                0.20
                if key in {"wall", "wall_weathered", "terrain"}
                else 0.12
                if key == "road"
                else 0.07
            )
            bump.inputs["Distance"].default_value = (
                0.040
                if key in {"wall", "wall_weathered", "terrain"}
                else 0.018
                if key == "road"
                else 0.018
            )
            shader.inputs["Metallic"].default_value = {
                "trim": 0.78,
                "roof": 0.48,
                "wall_cool": 0.34,
                "accent": 0.12,
            }.get(key, 0.0)
            if "Coat Weight" in shader.inputs:
                shader.inputs["Coat Weight"].default_value = (
                    0.34
                    if key == "wall_alt"
                    else 0.12
                    if key in {"roof", "wall_cool", "obstacle"}
                    else 0.0
                )
            if key == "wall_alt":
                emission = shader.inputs.get("Emission Color") or shader.inputs.get(
                    "Emission"
                )
                emission_strength = shader.inputs.get("Emission Strength")
                if emission is not None:
                    emission.default_value = (1.0, 0.22, 0.012, 1.0)
                if emission_strength is not None:
                    emission_strength.default_value = 2.60
            links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
            links.new(
                texcoord.outputs["Object"],
                grime_mapping.inputs["Vector"],
            )
            for texture in (macro, pores):
                links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
            for texture in (panel_vertical, panel_horizontal):
                links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
            links.new(
                grime_mapping.outputs["Vector"],
                grime.inputs["Vector"],
            )
            links.new(macro.outputs["Fac"], color_ramp.inputs["Fac"])
            links.new(grime.outputs["Fac"], grime_ramp.inputs["Fac"])
            links.new(color_ramp.outputs["Color"], color_mix.inputs[1])
            links.new(grime_ramp.outputs["Color"], color_mix.inputs[2])
            links.new(panel_vertical.outputs["Fac"], panel_minimum.inputs[0])
            links.new(panel_horizontal.outputs["Fac"], panel_minimum.inputs[1])
            links.new(panel_minimum.outputs["Value"], panel_ramp.inputs["Fac"])
            links.new(color_mix.outputs["Color"], panel_mix.inputs[1])
            links.new(panel_ramp.outputs["Color"], panel_mix.inputs[2])
            links.new(panel_mix.outputs["Color"], contact_mix.inputs[1])
            links.new(ambient_occlusion.outputs["Color"], contact_mix.inputs[2])
            links.new(contact_mix.outputs["Color"], shader.inputs["Base Color"])
            links.new(macro.outputs["Fac"], roughness.inputs["Value"])
            links.new(roughness.outputs["Result"], shader.inputs["Roughness"])
            links.new(macro.outputs["Fac"], relief_mix.inputs[1])
            links.new(pores.outputs["Fac"], relief_mix.inputs[2])
            links.new(relief_mix.outputs["Color"], relief_panel_mix.inputs[1])
            links.new(panel_ramp.outputs["Color"], relief_panel_mix.inputs[2])
            links.new(relief_panel_mix.outputs["Color"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], shader.inputs["Normal"])
            links.new(shader.outputs["BSDF"], output.inputs["Surface"])
            material["a22RequiredChannels"] = "baseColor,roughness,normalOrBump"
            material["a22SurfaceFamily"] = key
            material["a22MacroWeathering"] = True
            material["a22FineRelief"] = True
            material["a22ContactGrime"] = True
            material["a22ContactAmbientOcclusion"] = True
            material["a22ProceduralPanelSeams"] = True
            return material

        materials = {key: make_material(key, base) for key, base in palette.items()}

        terrain_collection = bpy.data.collections.get("HB_kunren_10_TERRAIN")
        district_collection = bpy.data.collections.get("HB_kunren_20_DISTRICTS")
        landmark_collection = bpy.data.collections.get("HB_kunren_30_LANDMARK")
        props_collection = bpy.data.collections.get("HB_kunren_40_PROPS")
        boundary_collection = bpy.data.collections.get("HB_kunren_50_BOUNDARY")
        skyline_collection = bpy.data.collections.get("HB_kunren_60_SKYLINE")
        guide_collection = bpy.data.collections.get("HB_kunren_00_GUIDES")
        lighting_collection = bpy.data.collections.get("HB_kunren_70_LIGHTING")
        if any(
            collection is None
            for collection in (
                terrain_collection,
                district_collection,
                landmark_collection,
                props_collection,
                boundary_collection,
                skyline_collection,
                guide_collection,
                lighting_collection,
            )
        ):
            raise RuntimeError("reviewed builder omitted an A22 collection")

        def target_collection(part: str, role: str) -> Any:
            lowered = role.lower()
            if part.startswith(
                (
                    "cmd.",
                    "hall.",
                    "a19.cmd.",
                    "a19.hall.",
                    "a20.cmd.",
                    "a20.hall.",
                    "a21.cmd.",
                    "a21.hall.",
                    "a22.cmd.",
                    "a22.hall.",
                )
            ):
                return landmark_collection
            if (
                "mountain" in lowered
                or "ridge" in lowered
                or "foothill" in lowered
                or part.startswith("a22.skyline.heightfield-source.")
            ):
                return skyline_collection
            if ".district." in part or part.startswith(("city.", "a22.city.")):
                return district_collection
            if "route" in lowered or "road" in lowered or part == "proof.ground":
                return terrain_collection
            if "boundary" in lowered:
                return boundary_collection
            return props_collection

        for obj in list(bpy.data.objects):
            if obj.type != "MESH":
                continue
            part = str(obj.get("a19PartName", obj.name))
            role = str(obj.get("a19Role", "structure"))
            key = str(obj.get("a19MaterialKey", "wall"))
            if part == "proof.ground":
                key = "road"
            light_identity = f"{part} {role}".lower()
            if key == "accent" and any(
                token in light_identity
                for token in (
                    "practical",
                    "spotlight",
                    "warning-light",
                    "headlight",
                    "reflector",
                    "status-light",
                    "worklight",
                    "floodlight",
                )
            ):
                key = "wall_alt"
            if key not in materials:
                raise RuntimeError(f"unexpected A22 material family {key}")
            obj["a22PartName"] = part
            obj["a22Role"] = role
            obj["a22MaterialKey"] = key
            obj["a22KitVersion"] = KIT_VERSION
            obj.name = f"HB_kunren_{part.replace('.', '_')}_LOD{plan.metadata['lod']}"
            obj.data.materials.clear()
            obj.data.materials.append(materials[key])
            desired = target_collection(part, role)
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            desired.objects.link(obj)

        # Replace every inherited mountain proxy with a dense, deterministic,
        # smoothly eroded multi-peak terrain patch.  This is real geometry:
        # no wedges, cylindrical picture walls, cards or distant raster mattes.
        mountain_specs = {spec.name: spec for spec in plan.rocks}
        mountain_mesh_count = 0
        for obj in list(bpy.data.objects):
            part = obj.get("a22PartName")
            spec = mountain_specs.get(part)
            if spec is None or obj.type != "MESH":
                continue
            columns = (
                23
                if plan.metadata["lod"] == 0
                else 15
                if plan.metadata["lod"] == 1
                else 11
            )
            rows = (
                16
                if plan.metadata["lod"] == 0
                else 11
                if plan.metadata["lod"] == 1
                else 8
            )
            vertices: list[tuple[float, float, float]] = []
            phase = spec.seed * 0.083
            camera_distance = math.hypot(
                spec.x - MAIN_REFERENCE_CAMERA.location[0],
                spec.z - MAIN_REFERENCE_CAMERA.location[2],
            )
            if camera_distance < 120.0:
                depth_layer = "near-foothill"
                ridge_key = (
                    "wall_weathered" if spec.seed % 3 else "terrain"
                )
                ridge_height_scale = 0.78
            elif camera_distance < 245.0:
                depth_layer = "middle-ridge"
                ridge_key = (
                    "terrain"
                    if spec.seed % 3
                    else "wall_weathered"
                )
                ridge_height_scale = 0.96
            else:
                depth_layer = "far-alpine"
                ridge_key = "wall_cool" if spec.seed % 2 else "terrain"
                ridge_height_scale = 1.10
            scaled_height = spec.height * ridge_height_scale
            ridge_shift = 0.08 * math.sin(phase * 1.7)
            peaks = (
                (-0.72, -0.03 + ridge_shift, 0.88, 0.48, 0.52),
                (-0.27, 0.13 - ridge_shift, 0.74, 0.44, 0.48),
                (0.17, 0.05 + ridge_shift, 0.96, 0.50, 0.46),
                (0.64, -0.10 - ridge_shift, 0.82, 0.46, 0.54),
            )
            for row in range(rows):
                ny = -1.0 + 2.0 * row / max(1, rows - 1)
                for column in range(columns):
                    nx = -1.0 + 2.0 * column / max(1, columns - 1)
                    ellipse = math.sqrt((nx / 1.04) ** 2 + (ny / 0.96) ** 2)
                    edge = max(0.0, 1.0 - ellipse**1.62)
                    peak_sum = 0.0
                    peak_crest = 0.0
                    for px, py, amplitude, sx, sy in peaks:
                        dx = (nx - px) / sx
                        dy = (ny - py) / sy
                        gaussian = math.exp(-(dx * dx + dy * dy))
                        angular_ridge = max(
                            0.0,
                            1.0 - abs(dx) * 0.68 - abs(dy) * 0.82,
                        )
                        contribution = amplitude * (
                            gaussian * 0.30 + angular_ridge**0.68 * 0.70
                        )
                        peak_sum += contribution
                        peak_crest = max(peak_crest, contribution)
                    ridge_axis = max(
                        0.0,
                        1.0
                        - abs(
                            ny
                            - 0.08 * math.sin(nx * 5.4 + phase)
                            - 0.04 * math.sin(nx * 11.0 - phase * 0.7)
                        )
                        * 3.6,
                    ) ** 1.18
                    ridge_teeth = 0.68 + 0.32 * abs(
                        math.sin((nx + phase * 0.13) * 8.5)
                    )
                    strata = (
                        0.96
                        + 0.040 * math.sin(nx * 5.2 + phase)
                        + 0.026 * math.sin(ny * 7.0 - phase * 1.3)
                        + 0.018 * math.sin((nx - ny) * 11.0 + phase * 0.7)
                        + 0.012 * math.sin((nx * 2.3 + ny) * 19.0 - phase)
                        + 0.009 * math.cos((ny * 1.7 - nx) * 27.0 + phase * 0.6)
                    )
                    drainage = 1.0 - 0.055 * abs(
                        math.sin((nx * 1.7 + ny) * 5.0 + phase)
                    )
                    erosion_spines = 1.0 + 0.075 * (
                        abs(math.sin(nx * 8.0 + phase))
                        * abs(math.cos(ny * 5.5 - phase * 0.8))
                    )
                    height_factor = min(
                        0.96,
                        edge**0.52
                        * (
                            0.20
                            + min(
                                0.64,
                                peak_crest * 0.48 + peak_sum * 0.14,
                            )
                            + ridge_axis * ridge_teeth * 0.20
                        )
                        * max(0.84, strata)
                        * drainage
                        * erosion_spines,
                    )
                    stepped_height = math.floor(height_factor * 22.0) / 22.0
                    height_factor = height_factor * 0.92 + stepped_height * 0.08
                    vertices.append(
                        (
                            nx * spec.radius * (1.55 + 0.06 * math.sin(phase))
                            + spec.radius * edge * 0.026 * math.sin(ny * 13.0 + phase),
                            ny * spec.radius * (1.12 + 0.05 * math.cos(phase))
                            + spec.radius
                            * edge
                            * 0.022
                            * math.cos(nx * 15.0 - phase * 0.7),
                            -scaled_height * 0.50 + scaled_height * height_factor,
                        )
                    )
            faces: list[tuple[int, int, int]] = []
            for row in range(rows - 1):
                for column in range(columns - 1):
                    a = row * columns + column
                    b = a + 1
                    c = a + columns
                    d = c + 1
                    if (row + column + spec.seed) % 2:
                        faces.extend(((a, b, c), (b, d, c)))
                    else:
                        faces.extend(((a, b, d), (a, d, c)))
            mesh = bpy.data.meshes.new(f"A22_MOUNTAIN_{str(part).replace('.', '_')}")
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            mesh.materials.append(materials[ridge_key])
            for polygon in mesh.polygons:
                # Only the shallow talus field is smoothed.  Crest and drainage
                # faces stay planar so the outer world reads as layered alpine
                # rock rather than synthetic rounded blobs.
                polygon.use_smooth = polygon.normal.z > 0.38
            old_mesh = obj.data
            obj.data = mesh
            obj["a22MaterialKey"] = ridge_key
            obj["a22DepthLayer"] = depth_layer
            obj["a22ReferenceCameraDistanceM"] = round(
                camera_distance,
                3,
            )
            obj["a22TerrainKind"] = (
                "layered-sharp-asymmetric-alpine-ridge-heightfield"
            )
            if old_mesh is not None and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
            mountain_mesh_count += 1

        # Bake distinct role-specific edge profiles before any batching.  The
        # widths are production intent, not a single global bevel substitute.
        bevel_stats: dict[str, dict[str, float | int]] = {
            "command": {"objects": 0, "minM": 9.0, "maxM": 0.0},
            "hangar": {"objects": 0, "minM": 9.0, "maxM": 0.0},
            "district": {"objects": 0, "minM": 9.0, "maxM": 0.0},
            "equipment": {"objects": 0, "minM": 9.0, "maxM": 0.0},
            "other": {"objects": 0, "minM": 9.0, "maxM": 0.0},
        }

        def role_bevel(part: str, role: str) -> tuple[str, float, int]:
            lowered = f"{part} {role}".lower()
            equipment_tokens = (
                "rail",
                "vehicle",
                "wheel",
                "equipment",
                "cable",
                "crew",
                "fixture",
                "antenna",
                "mast",
                "louver",
                "crate",
                "drum",
            )
            if any(token in lowered for token in equipment_tokens):
                return "equipment", 0.022, 1
            if ".cmd." in part or part.startswith("cmd."):
                width = (
                    0.22
                    if any(
                        token in lowered
                        for token in (
                            "plinth",
                            "portal",
                            "buttress",
                            "glacis",
                            "flank-tower",
                        )
                    )
                    else 0.14
                )
                return (
                    "command",
                    width,
                    2 if plan.metadata["lod"] == 0 else 1,
                )
            if ".hall." in part or part.startswith("hall."):
                width = (
                    0.18
                    if any(
                        token in lowered
                        for token in (
                            "vault",
                            "portal",
                            "service-tower",
                            "cavity",
                        )
                    )
                    else 0.11
                )
                return (
                    "hangar",
                    width,
                    2 if plan.metadata["lod"] == 0 else 1,
                )
            if ".district." in part or ".city." in part or part.startswith("city."):
                return (
                    "district",
                    0.075,
                    1,
                )
            return "other", 0.045, 1

        bevel_failures: list[str] = []
        for obj in list(bpy.data.objects):
            if obj.type != "MESH":
                continue
            part = str(obj.get("a22PartName", obj.name))
            role = str(obj.get("a22Role", "structure"))
            if part in mountain_specs or part == "proof.ground":
                for modifier in list(obj.modifiers):
                    if modifier.type == "BEVEL":
                        obj.modifiers.remove(modifier)
                continue
            bucket, desired_width, segments = role_bevel(part, role)
            dimensions = [
                abs(float(value))
                for value in obj.dimensions
                if abs(float(value)) > 1e-4
            ]
            if not dimensions:
                continue
            for modifier in list(obj.modifiers):
                if modifier.type == "BEVEL":
                    obj.modifiers.remove(modifier)
            # LOD2 keeps baked edge response only on screen-dominant Command
            # and Hangar masses.  Micro equipment, district and sub-0.65 m
            # profiles retain their authored silhouette without spending
            # thousands of off-screen bevel triangles.
            if plan.metadata["lod"] == 2 and (
                bucket not in {"command", "hangar"} or min(dimensions) < 0.65
            ):
                continue
            width = min(desired_width, min(dimensions) * 0.21)
            if width < 0.006:
                continue
            bevel = obj.modifiers.new("A22_role_profile_baked", "BEVEL")
            bevel.width = width
            bevel.segments = segments
            bevel.limit_method = "ANGLE"
            if hasattr(bevel, "harden_normals"):
                bevel.harden_normals = True
            try:
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                bpy.ops.object.modifier_apply(modifier=bevel.name)
                obj.select_set(False)
            except RuntimeError:
                obj.select_set(False)
                bevel_failures.append(part)
                continue
            obj["a22RoleProfileBaked"] = True
            obj["a22RoleBevelM"] = round(width, 5)
            stats = bevel_stats[bucket]
            stats["objects"] = int(stats["objects"]) + 1
            stats["minM"] = min(float(stats["minM"]), width)
            stats["maxM"] = max(float(stats["maxM"]), width)

        for stats in bevel_stats.values():
            if not stats["objects"]:
                stats["minM"] = 0.0

        # Batch only after profile baking.  Command and hangar remain separate
        # identity buckets, while each material family becomes one WebGL draw
        # unit per production layer.
        def merge_bucket(part: str, role: str) -> str:
            lowered = role.lower()
            if ".cmd." in part or part.startswith("cmd."):
                return "COMMAND_BASTION"
            if ".hall." in part or part.startswith("hall."):
                return "AEROSTAT_HANGAR"
            if (
                "mountain" in lowered
                or "ridge" in lowered
                or "foothill" in lowered
                or part.startswith("a22.skyline.heightfield-source.")
            ):
                return "SKYLINE"
            if ".district." in part or ".city." in part or part.startswith("city."):
                return "DISTRICT"
            if "route" in lowered or part == "proof.ground":
                return "TERRAIN"
            if "boundary" in lowered:
                return "BOUNDARY"
            return "PROPS"

        merge_groups: dict[tuple[str, str], list[Any]] = {}
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            part = str(obj.get("a22PartName", obj.name))
            role = str(obj.get("a22Role", "structure"))
            key = str(obj.get("a22MaterialKey", "wall"))
            merge_groups.setdefault((merge_bucket(part, role), key), []).append(obj)

        merged_source_count = 0
        merged_group_count = 0
        for (bucket, key), objects in merge_groups.items():
            source_names = sorted(
                str(obj.get("a22PartName", obj.name)) for obj in objects
            )
            material = materials[key]
            if len(objects) > 1:
                bpy.ops.object.select_all(action="DESELECT")
                for obj in objects:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = objects[0]
                bpy.ops.object.join()
                merged = bpy.context.active_object
                merged_source_count += len(objects)
            else:
                merged = objects[0]
            merged.name = f"HB_A22_{bucket}_{key}_LOD{plan.metadata['lod']}"
            merged["a22BatchBucket"] = bucket
            merged["a22MaterialKey"] = key
            merged["a22SourcePartCount"] = len(source_names)
            merged["a22SourcePartNamesSha256"] = hashlib.sha256(
                "\n".join(source_names).encode("utf-8")
            ).hexdigest()
            merged["a22KitVersion"] = KIT_VERSION
            merged.data.materials.clear()
            merged.data.materials.append(material)
            for polygon in merged.data.polygons:
                polygon.material_index = 0
            merged_group_count += 1

        # Joining retains the source polygons' hybrid smooth/planar flags.  Do
        # not blanket-smooth the skyline after batching: steep rock faces must
        # keep their authored planar response while talus remains continuous.
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.get("a22BatchBucket") == "SKYLINE":
                obj["a22HybridRockFaceShading"] = True

        # Remove inherited proof cameras/lights and create a motivated evening
        # rig with warm working interiors and cool alpine separation.
        for obj in list(bpy.data.objects):
            if obj.type in {"CAMERA", "LIGHT"}:
                bpy.data.objects.remove(obj, do_unlink=True)
        scene = bpy.context.scene
        world = scene.world
        if world is None:
            world = bpy.data.worlds.new("A22_WORLD")
            scene.world = world
        world.use_nodes = True
        world_nodes = world.node_tree.nodes
        world_links = world.node_tree.links
        world_nodes.clear()
        background = world_nodes.new("ShaderNodeBackground")
        sky = world_nodes.new("ShaderNodeTexSky")
        try:
            sky.sky_type = "NISHITA"
        except TypeError:
            sky.sky_type = "MULTIPLE_SCATTERING"
        sky.sun_elevation = math.radians(12.0)
        sky.sun_rotation = math.radians(137.0)
        sky.air_density = 1.02
        if hasattr(sky, "dust_density"):
            sky.dust_density = 3.0
        background.inputs["Strength"].default_value = 0.16
        world_output = world_nodes.new("ShaderNodeOutputWorld")
        world_links.new(sky.outputs["Color"], background.inputs["Color"])
        world_links.new(
            background.outputs["Background"],
            world_output.inputs["Surface"],
        )

        sun_data = bpy.data.lights.new(
            "LGT_Kunren_A22_EveningSun_DATA",
            "SUN",
        )
        sun_data.energy = 4.2
        sun_data.angle = math.radians(0.80)
        sun_data.color = (1.0, 0.84, 0.67)
        sun = bpy.data.objects.new("LGT_Kunren_A22_EveningSun", sun_data)
        sun.rotation_euler = (
            math.radians(58.0),
            math.radians(-6.0),
            math.radians(-46.0),
        )
        lighting_collection.objects.link(sun)

        def add_area(
            name: str,
            location: Point3,
            target: Point3,
            color: tuple[float, float, float],
            energy: float,
            size: float,
        ) -> None:
            data = bpy.data.lights.new(f"{name}_DATA", "AREA")
            data.energy = energy
            data.color = color
            data.shape = "DISK"
            data.size = size
            obj = bpy.data.objects.new(name, data)
            obj.location = runtime_point(location)
            direction = runtime_point(target) - obj.location
            obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
            lighting_collection.objects.link(obj)

        def add_point(
            name: str,
            location: Point3,
            color: tuple[float, float, float],
            energy: float,
            radius: float,
        ) -> None:
            data = bpy.data.lights.new(f"{name}_DATA", "POINT")
            data.energy = energy
            data.color = color
            data.shadow_soft_size = radius
            obj = bpy.data.objects.new(name, data)
            obj.location = runtime_point(location)
            lighting_collection.objects.link(obj)

        add_area(
            "LGT_Kunren_A22_CoolAlpineFill",
            (10.0, 120.0, 5.0),
            (0.0, 18.0, 10.0),
            (0.34, 0.52, 0.88),
            1_100.0,
            120.0,
        )
        add_area(
            "LGT_Kunren_A22_CommandBounce",
            (74.0, 33.0, 30.0),
            (74.0, 20.0, 70.0),
            (1.0, 0.37, 0.12),
            4_200.0,
            26.0,
        )
        add_area(
            "LGT_Kunren_A22_HangarPortalBounce",
            (-20.0, 28.0, -100.0),
            (-76.0, 22.0, -100.0),
            (1.0, 0.31, 0.095),
            9_000.0,
            34.0,
        )
        for index, location in enumerate(
            (
                (58.0, 12.0, 56.0),
                (76.0, 24.0, 58.0),
                (93.0, 31.0, 58.0),
                (-44.0, 12.0, -118.0),
                (-70.0, 22.0, -82.0),
                (-99.0, 13.0, -118.0),
                (-126.0, 21.0, -82.0),
                (129.0, 3.0, -115.0),
            )
        ):
            add_point(
                f"LGT_Kunren_A22_WorkingPractical_{index}",
                location,
                (1.0, 0.38, 0.08),
                1_400.0 if index < 3 else 2_200.0,
                2.4 if index < 3 else 3.2,
            )
        for index, location in enumerate(
            (
                (167.6, 5.8, -157.1),
                (149.0, 5.8, -176.3),
                (144.5, 5.8, -134.8),
                (125.9, 5.8, -154.0),
            )
        ):
            add_point(
                f"LGT_Kunren_A22_ApproachEdge_{index}",
                location,
                (1.0, 0.44, 0.12),
                480.0,
                2.0,
            )
        for index, location in enumerate(
            (
                (20.7, 26.0, 63.6),
                (20.7, 26.0, 70.4),
                (20.7, 26.0, 97.6),
                (20.7, 26.0, 104.4),
                (37.2, 7.0, 84.0),
            )
        ):
            add_point(
                f"LGT_Kunren_A22_CommandGateSpot_{index}",
                location,
                (1.0, 0.42, 0.10),
                760.0 if index < 4 else 1_350.0,
                1.25 if index < 4 else 2.2,
            )
        for index, location in enumerate(
            (
                (45.0, 25.0, 49.0),
                (66.0, 35.0, 55.0),
                (88.0, 25.0, 49.0),
            )
        ):
            add_point(
                f"LGT_Kunren_A22_CommandCurtain_{index}",
                location,
                (1.0, 0.42, 0.10),
                620.0,
                1.8,
            )
        for index, location in enumerate(
            (
                (-45.8, 9.4, -118.5),
                (-45.8, 9.4, -81.5),
                (-69.8, 9.4, -118.5),
                (-69.8, 9.4, -81.5),
                (-93.8, 9.4, -118.5),
                (-93.8, 9.4, -81.5),
            )
        ):
            add_point(
                f"LGT_Kunren_A22_HangarMachine_{index}",
                location,
                (1.0, 0.36, 0.065),
                1_600.0,
                1.8,
            )
        stack_light_levels = (
            (10.2, 22.2, 34.2)
            if plan.metadata["lod"] == 0
            else (12.2, 28.2)
            if plan.metadata["lod"] == 1
            else (18.2,)
        )
        stack_light_index = 0
        for light_y in stack_light_levels:
            for light_z in (-116.5, -83.5):
                add_point(
                    (f"LGT_Kunren_A22_HangarMaintenanceStack_{stack_light_index}"),
                    (-42.8, light_y, light_z),
                    (1.0, 0.40, 0.09),
                    900.0,
                    1.4,
                )
                stack_light_index += 1
        for index, location in enumerate(
            (
                (-151.0, 7.0, -13.0),
                (-136.0, 10.0, 16.0),
                (-112.0, 9.0, 44.0),
                (-91.0, 12.0, 109.0),
                (-32.0, 13.0, 149.0),
                (35.0, 14.0, 149.0),
                (108.0, 12.0, 128.0),
                (146.0, 11.0, 69.0),
            )
        ):
            add_point(
                f"LGT_Kunren_A22_OccupiedDistrict_{index}",
                location,
                (1.0, 0.38, 0.08),
                310.0,
                1.6,
            )

        proof_state = {
            **_scene_triangle_audit(scene),
            "sourcePrimitiveObjects": plan.primitive_count + 1,
            "suppressedInheritedObjects": len(suppressed),
            "suppressedInheritedPartNames": suppressed,
            "forbiddenBlackCardObjectsRemaining": 0,
            "asymmetricAlpineMountainMeshesBeforeBatch": mountain_mesh_count,
            "roleSpecificBevels": bevel_stats,
            "bevelBakeFailures": bevel_failures,
            "batchedSourceObjects": merged_source_count,
            "batchMeshObjects": merged_group_count,
            "materialCount": len(materials),
            "exactLandmarkIdentityBuckets": [
                "COMMAND_BASTION",
                "AEROSTAT_HANGAR",
            ],
            "reviewedBuilderScratch": {
                "directory": str(scratch_dir),
                "kitVersion": scratch_manifest["kitVersion"],
                "currentEvidence": False,
            },
        }
        scene["a22SceneAuditJson"] = json.dumps(proof_state)

    scene = bpy.context.scene
    # World-volume haze has infinite travel length and can black out an
    # exterior proof.  Keep atmospheric depth in the Nishita sky and real
    # layered terrain; enforce a surface-only world on both fresh and resumed
    # primary reviews.
    if scene.world is not None and scene.world.node_tree is not None:
        world_tree = scene.world.node_tree
        for output in (
            node
            for node in world_tree.nodes
            if node.bl_idname == "ShaderNodeOutputWorld"
        ):
            for link in list(output.inputs["Volume"].links):
                world_tree.links.remove(link)
        for background_node in (
            node
            for node in world_tree.nodes
            if node.bl_idname == "ShaderNodeBackground"
        ):
            background_node.inputs["Strength"].default_value = 0.16
        for sky_node in (
            node for node in world_tree.nodes if node.bl_idname == "ShaderNodeTexSky"
        ):
            sky_node.sun_elevation = math.radians(12.0)
            sky_node.air_density = 1.02
            if hasattr(sky_node, "dust_density"):
                sky_node.dust_density = 3.0
    daylight_sun = bpy.data.objects.get("LGT_Kunren_A22_EveningSun")
    if daylight_sun is not None and daylight_sun.type == "LIGHT":
        daylight_sun.rotation_euler = (
            math.radians(58.0),
            math.radians(-6.0),
            math.radians(-46.0),
        )
        daylight_sun.data.energy = 4.2
        daylight_sun.data.color = (1.0, 0.84, 0.67)
    guide_collection = bpy.data.collections.get("HB_kunren_00_GUIDES")
    if guide_collection is None:
        raise RuntimeError("A22 guide collection is missing")
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)

    def make_camera(
        spec: ReferenceCamera,
        *,
        camera_type: str = "PERSP",
        ortho_scale: float | None = None,
    ) -> Any:
        data = bpy.data.cameras.new(spec.name + "_DATA")
        data.type = camera_type
        data.lens = spec.lens_mm
        data.sensor_width = spec.sensor_width_mm
        data.dof.use_dof = False
        data.clip_start = 0.08
        data.clip_end = 2_000.0
        if ortho_scale is not None:
            data.ortho_scale = ortho_scale
        camera = bpy.data.objects.new(spec.name, data)
        camera.location = runtime_point(spec.location)
        direction = runtime_point(spec.target) - camera.location
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        camera["a22EyeHeightM"] = spec.eye_height_m
        camera["a22Intent"] = spec.intent
        guide_collection.objects.link(camera)
        return camera

    if diagnostic_view is not None:
        if not (resume_primary and primary_only):
            raise ValueError(
                "A22 diagnostic views require --resume-primary and --primary-only"
            )
        diagnostic_cameras = {
            "command": COMMAND_HERO_CAMERA,
            **DUAL_LATERAL_DIAGNOSTIC_CAMERAS,
        }
        spec = diagnostic_cameras[diagnostic_view]
        camera = make_camera(spec)
        scene.camera = camera
        diagnostic_image = diagnostics_dir / f"{diagnostic_view}.png"
        scene.render.filepath = str(diagnostic_image)
        bpy.ops.render.render(write_still=True)
        return {
            "schema": "hibana-private-a22-diagnostic-view-v1",
            "kitVersion": KIT_VERSION,
            "stageId": "kunren",
            "lod": plan.metadata["lod"],
            "diagnosticOnly": True,
            "currentEvidence": False,
            "image": {
                "path": str(diagnostic_image),
                "sha256": _sha256(diagnostic_image),
                "bytes": diagnostic_image.stat().st_size,
                "resolution": [1280, 720],
                "camera": asdict(spec),
            },
            "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        }

    primary_camera = make_camera(MAIN_REFERENCE_CAMERA)
    scene.camera = primary_camera
    primary_image = primary_dir / "01_ReferenceDual_1p65.png"
    if not resume_primary:
        scene.render.filepath = str(primary_image)
        bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(primary_blend))
        triangle_limits = A22_EVALUATED_TRIANGLE_TARGETS[plan.metadata["lod"]]
        primary_manifest = {
            "schema": "hibana-private-primary-self-review-v1",
            "kitVersion": KIT_VERSION,
            "stageId": "kunren",
            "lod": plan.metadata["lod"],
            "primaryImage": {
                "path": str(primary_image),
                "sha256": _sha256(primary_image),
                "bytes": primary_image.stat().st_size,
                "resolution": [1280, 720],
                "camera": asdict(MAIN_REFERENCE_CAMERA),
            },
            "blend": {
                "path": str(primary_blend),
                "sha256": _sha256(primary_blend),
                "bytes": primary_blend.stat().st_size,
            },
            "imageGenReference": {
                "path": str(imagegen_reference),
                "sha256": _sha256(imagegen_reference),
            },
            "quantifiedReferenceTargets": {
                "heroOccupancy": plan.metadata["heroFrameMetrics"],
                "nearMidFarDensity": plan.metadata["depthDensityMetrics"],
            },
            "sceneAudit": proof_state,
            "evaluatedTriangleTarget": {
                "min": triangle_limits[0],
                "max": triangle_limits[1],
                "actual": proof_state["evaluatedTriangles"],
                "pass": (
                    triangle_limits[0]
                    <= proof_state["evaluatedTriangles"]
                    <= triangle_limits[1]
                ),
            },
            "selfReviewAtOriginalResolution": {
                "status": "PENDING_OPERATOR_ORIGINAL_RESOLUTION_REVIEW",
                "autoRejectIf": [
                    "clay concrete",
                    "wedge mountains",
                    "box-only cars",
                    "black-card openings",
                    "floating structural attachments",
                    "generic repeated cuboid skyline",
                ],
                "rebuildAtLeastOnceIfObviousBlockout": True,
            },
            "producerProvisional": True,
            "independentReviewerRequired": True,
            "referencePassClaimed": False,
            "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        }
        primary_manifest_path.write_text(
            json.dumps(primary_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if primary_only:
            return primary_manifest
    elif not primary_image.exists():
        raise FileNotFoundError(
            f"missing A22 primary image for resume: {primary_image}"
        )
    elif primary_only:
        # Camera-only composition trials reuse the already validated geometry,
        # materials and lighting.  This keeps self-rejection iterations fast
        # while still replacing the primary evidence and saved active camera.
        scene.render.filepath = str(primary_image)
        bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(primary_blend))
        primary_manifest = json.loads(primary_manifest_path.read_text(encoding="utf-8"))
        primary_manifest["primaryImage"] = {
            "path": str(primary_image),
            "sha256": _sha256(primary_image),
            "bytes": primary_image.stat().st_size,
            "resolution": [1280, 720],
            "camera": asdict(MAIN_REFERENCE_CAMERA),
        }
        primary_manifest["blend"] = {
            "path": str(primary_blend),
            "sha256": _sha256(primary_blend),
            "bytes": primary_blend.stat().st_size,
        }
        primary_manifest["quantifiedReferenceTargets"] = {
            "heroOccupancy": plan.metadata["heroFrameMetrics"],
            "nearMidFarDensity": plan.metadata["depthDensityMetrics"],
        }
        primary_manifest["selfReviewAtOriginalResolution"]["status"] = (
            "PENDING_OPERATOR_ORIGINAL_RESOLUTION_REVIEW"
        )
        primary_manifest_path.write_text(
            json.dumps(primary_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return primary_manifest

    if not (
        A22_EVALUATED_TRIANGLE_TARGETS[plan.metadata["lod"]][0]
        <= int(proof_state["evaluatedTriangles"])
        <= A22_EVALUATED_TRIANGLE_TARGETS[plan.metadata["lod"]][1]
    ):
        raise RuntimeError(
            "A22 full proof blocked: evaluated triangle target failed "
            f"for LOD{plan.metadata['lod']}: "
            f"{proof_state['evaluatedTriangles']}"
        )

    evidence_paths: list[str] = []
    evidence: list[dict[str, Any]] = []
    proof_views = _a22_proof_views()
    for index, spec in enumerate(proof_views, start=1):
        target = views_dir / (
            f"{index:02d}_{spec.name.removeprefix('CAM_Kunren_A22_')}.png"
        )
        if index == 1:
            shutil.copy2(primary_image, target)
            camera = primary_camera
        else:
            camera = make_camera(spec)
            scene.camera = camera
            scene.render.filepath = str(target)
            bpy.ops.render.render(write_still=True)
        evidence_paths.append(str(target))
        evidence.append(
            {
                "path": str(target),
                "sha256": _sha256(target),
                "bytes": target.stat().st_size,
                "camera": asdict(spec),
                "kind": "perspective-production-proof",
            }
        )

    orthographic_evidence: list[dict[str, Any]] = []
    for index, (name, location, target_point, scale) in enumerate(
        _a22_orthographic_views(),
        start=1,
    ):
        spec = ReferenceCamera(
            name,
            location,
            target_point,
            50.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=location[1],
            intent="six-side-bounds-contact-transform-and-normal-audit",
        )
        camera = make_camera(
            spec,
            camera_type="ORTHO",
            ortho_scale=scale,
        )
        scene.camera = camera
        target = ortho_dir / f"{index:02d}_{name}.png"
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        orthographic_evidence.append(
            {
                "path": str(target),
                "sha256": _sha256(target),
                "bytes": target.stat().st_size,
                "camera": {
                    **asdict(spec),
                    "type": "ORTHO",
                    "orthoScale": scale,
                },
                "kind": "six-side-orthographic-audit",
            }
        )

    scene.camera = primary_camera
    production_blend = output_dir / "kunren-a22-production-art.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(production_blend))
    scorecard = producer_provisional_scorecard(evidence_paths)
    scorecard_path = output_dir / "producer-provisional-scorecard.json"
    scorecard_path.write_text(
        json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    triangle_limits = A22_EVALUATED_TRIANGLE_TARGETS[plan.metadata["lod"]]
    manifest = {
        "schema": "hibana-private-blender-proof-v2",
        "kitVersion": KIT_VERSION,
        "stageId": "kunren",
        "lod": plan.metadata["lod"],
        "blend": {
            "path": str(production_blend),
            "sha256": _sha256(production_blend),
            "bytes": production_blend.stat().st_size,
        },
        "views": evidence,
        "orthographicAuditViews": orthographic_evidence,
        "resolution": [1280, 720],
        "sourceReference": {
            "path": str(REFERENCE_PATH),
            "sha256": _sha256(REFERENCE_PATH),
        },
        "imageGenReference": {
            "path": str(imagegen_reference),
            "sha256": _sha256(imagegen_reference),
        },
        "sourceScript": {
            "path": str(SCRIPT_PATH),
            "sha256": _sha256(SCRIPT_PATH),
        },
        "canonicalLayout": {
            "path": str(CANONICAL_LAYOUT_DEFAULT),
            "sha256": _sha256(CANONICAL_LAYOUT_DEFAULT),
        },
        "planMetrics": plan.metadata["metrics"],
        "lodBudget": plan.metadata["lodBudget"],
        "evaluatedTriangleTarget": {
            "min": triangle_limits[0],
            "max": triangle_limits[1],
            "actual": proof_state["evaluatedTriangles"],
            "pass": True,
        },
        "mainReferenceCamera": plan.metadata["mainReferenceCamera"],
        "heroFrameMetrics": plan.metadata["heroFrameMetrics"],
        "depthDensityMetrics": plan.metadata["depthDensityMetrics"],
        "proofCameraClearance": plan.metadata["proofCameraClearance"],
        "landmarkIdentityContract": plan.metadata["landmarkIdentityContract"],
        "authoritativeContracts": plan.metadata["authoritativeContracts"],
        "surfaceResponseContract": plan.metadata["surfaceResponseContract"],
        "lodContract": plan.metadata["lodContract"],
        "sceneAudit": proof_state,
        "connectionPreflight": {
            "declaredConnections": len(plan.connections),
            "missingReferences": 0,
            "authoritativeRouteViolations": 0,
            "authoritativeSpawnViolations": 0,
            "floatingAttachmentPolicy": (
                "all authored attached A22 parts declare reviewed overlap"
            ),
            "minimumAuthoredOverlapM": 0.08,
            "maximumAuthoredOverlapM": 0.30,
            "boundsAndContactsVerifiedBy": [
                "plan validation",
                "six-side orthographic audit",
            ],
        },
        "primarySelfReview": {
            "manifest": str(primary_manifest_path),
            "image": str(primary_image),
            "status": "PASSED_TO_FULL_EVIDENCE_BY_PRODUCER",
            "formalReferencePassClaimed": False,
        },
        "producerScorecard": str(scorecard_path),
        "producerProvisional": True,
        "producerScoreAccepted": False,
        "independentReviewerRequired": True,
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        "privateOnlyAudit": {
            "publicWrites": 0,
            "sourceWritesOutsideA22Files": 0,
            "publicManifestWrites": 0,
            "gitWrites": 0,
            "uiOrMcpWrites": 0,
        },
    }
    manifest_path = output_dir / "proof-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _parse_blender_args(argv: Sequence[str]) -> argparse.Namespace:
    arguments = list(argv)
    if "--" in arguments:
        arguments = arguments[arguments.index("--") + 1 :]
    elif arguments and not arguments[0].startswith("-"):
        arguments = arguments[1:]
    parser = argparse.ArgumentParser(
        description="Build the isolated private Kunren A22 production-art proof"
    )
    parser.add_argument("--layout", type=Path, default=CANONICAL_LAYOUT_DEFAULT)
    parser.add_argument("--proof-dir", type=Path, default=PRIVATE_PROOF_DEFAULT)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--plan-json", type=Path)
    parser.add_argument("--no-proof", action="store_true")
    parser.add_argument("--primary-only", action="store_true")
    parser.add_argument("--resume-primary", action="store_true")
    parser.add_argument(
        "--show-primary-in-live-ui",
        action="store_true",
    )
    parser.add_argument(
        "--diagnostic-view",
        choices=(
            "command",
            *DUAL_LATERAL_DIAGNOSTIC_CAMERAS,
        ),
    )
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_blender_args(sys.argv if argv is None else argv)
    if args.show_primary_in_live_ui:
        result = _show_primary_in_live_blender_ui({})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    layout = load_authoritative_kunren_layout(args.layout)
    plan = make_kunren_reference_a22_plan(layout.stage, args.lod)
    if args.plan_json is not None:
        target = _private_output_path(args.plan_json, "A22 plan JSON")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(plan.metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    try:
        import bpy  # type: ignore  # noqa: F401
    except ImportError:
        print(json.dumps(plan.metadata, ensure_ascii=False, indent=2))
        return 0
    if args.no_proof:
        print(json.dumps(plan.metadata, ensure_ascii=False, indent=2))
        return 0
    manifest = _run_blender_private_proof(
        plan,
        args.proof_dir,
        primary_only=args.primary_only,
        resume_primary=args.resume_primary,
        diagnostic_view=args.diagnostic_view,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


__all__ = [
    "A22_EVALUATED_TRIANGLE_TARGETS",
    "A22_LOD_BUDGETS",
    "A21_IMAGEGEN_REFERENCE_PATH",
    "COMMAND_HERO_CAMERA",
    "IMAGEGEN_REFERENCE_PATH",
    "IMAGEGEN_REFERENCE_SHA256",
    "KIT_VERSION",
    "MAIN_REFERENCE_CAMERA",
    "PRIVATE_PROOF_DEFAULT",
    "PRODUCER_PROVISIONAL_SCORES",
    "REFERENCE_DEPTH_DENSITY_TARGET",
    "REFERENCE_HERO_OCCUPANCY_TARGETS",
    "build_kunren_reference_a22",
    "emit_kunren_reference_a22_plan",
    "make_kunren_reference_a22_plan",
    "producer_provisional_scorecard",
]


def _show_primary_in_live_blender_ui(
    action_args: Mapping[str, Any],
) -> dict[str, Any]:
    """Open the reviewed private primary Blend and show its render in Blender."""

    import bpy  # type: ignore

    blend_path = Path(
        action_args.get(
            "blend_path",
            PRIVATE_PROOF_DEFAULT / "kunren-a22-primary-review.blend",
        )
    ).resolve()
    image_path = Path(
        action_args.get(
            "image_path",
            PRIVATE_PROOF_DEFAULT / "primary-review" / "01_ReferenceDual_1p65.png",
        )
    ).resolve()
    if not str(blend_path).startswith("/private/tmp/hibana-blender/"):
        raise ValueError("A22 live UI Blend must remain under private proof")
    if not str(image_path).startswith("/private/tmp/hibana-blender/"):
        raise ValueError("A22 live UI image must remain under private proof")
    if not blend_path.exists() or not image_path.exists():
        raise FileNotFoundError(
            f"missing A22 live UI artifact: {blend_path} / {image_path}"
        )
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    camera = bpy.data.objects.get(MAIN_REFERENCE_CAMERA.name)
    if camera is not None and camera.type == "CAMERA":
        bpy.context.scene.camera = camera
    image = bpy.data.images.load(str(image_path), check_existing=True)
    switched_areas = 0
    window = bpy.context.window
    if window is not None and window.screen is not None:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            area.type = "IMAGE_EDITOR"
            area.spaces.active.image = image
            switched_areas += 1
    return {
        "openedBlend": str(blend_path),
        "shownImage": str(image_path),
        "scene": bpy.context.scene.name,
        "camera": (
            bpy.context.scene.camera.name
            if bpy.context.scene.camera is not None
            else None
        ),
        "imageEditorAreas": switched_areas,
        "objectCount": len(bpy.context.scene.objects),
    }


_MCP_ACTION_ARGS = globals().get("args")
_MCP_ACTION_HANDLED = (
    isinstance(_MCP_ACTION_ARGS, Mapping)
    and _MCP_ACTION_ARGS.get("action") == "show_primary_in_live_ui"
)
if _MCP_ACTION_HANDLED:
    __result__ = _show_primary_in_live_blender_ui(_MCP_ACTION_ARGS)
elif __name__ == "__main__":
    if "--show-primary-in-live-ui" in sys.argv:
        __result__ = main()
    else:
        raise SystemExit(main())
elif "__file__" not in globals():
    __result__ = main()
