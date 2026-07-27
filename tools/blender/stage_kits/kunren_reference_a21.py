"""Kunren A21 isolated production-art pass built from the immutable A20 proof.

A21 never integrates with ``build_all_stages.py`` and never writes public
assets, source manifests, TypeScript, Git state, or UI.  It keeps A20's
authoritative stage bounds, exact two landmark identities, canonical landmark
centres, approaches, spawns, visual-only collision policy, and WebGL LOD
strategy.  This pass spends its budget on visible first-person finish:

* fixed 1.65 m compressed dual composition matching the focused ImageGen guide;
* a load-bearing, castle-scale Command Bastion rather than stacked boxes;
* a monumental working Aerostat Vault Hangar with docking and maintenance;
* connected terraces, checkpoints, service bridges, vehicles and story;
* layered jagged alpine geometry rather than a matte or coarse mountain wall;
* procedural concrete, steel, asphalt and terrain response with weathering;
* directional alpine daylight, contact shadows and restrained practicals.

Connection map (declared before any Blender geometry is emitted):

* command facade armour -> A20 monolithic plinth/keep: 0.10-0.18 m seat;
* command galleries -> south facade and vertical piers: 0.10-0.16 m seat;
* command crown radar/masts -> A20 crown: 0.10-0.16 m seat;
* hangar service towers -> canonical hangar foundation: 0.20 m embed;
* hangar balconies/door tracks -> tower or portal shell: 0.10-0.16 m seat;
* hangar crane rails -> portal ribs/service towers: 0.12-0.18 m seat;
* aerostat docking cables -> roof truss/aerostat envelope: 0.08-0.14 m seat;
* checkpoint booths/barriers/lights -> route shoulders: 0.08-0.12 m seat;
* service bridges -> connected district roofs/walls: 0.12-0.18 m seat;
* crates, drums, generators and signs -> floor/pallet/frame: >= 0.08 m.

The proof scorecard is producer-provisional and deliberately remains NO-SHIP
until a different reviewer inspects the original-resolution 1280 evidence.
"""

from __future__ import annotations

from dataclasses import asdict
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
    "kunren_reference_a21.py"
)
SCRIPT_PATH = Path(globals().get("__file__", _FALLBACK_SCRIPT_PATH)).resolve()
REPO_ROOT = SCRIPT_PATH.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import kunren_reference_a20 as a20  # noqa: E402
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


KIT_VERSION = "kunren-reference-a21-v1"
PRIVATE_PROOF_DEFAULT = Path("/private/tmp/hibana-blender/a21-kunren-production-art")
CANONICAL_LAYOUT_DEFAULT = Path("/private/tmp/hibana-blender/canonical-stage-layouts.json")
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/kunren-reference-v1.png"
A20_IMAGEGEN_REFERENCE_PATH = Path(
    "/private/tmp/hibana-blender/a20-kunren-art-rebuild/concepts/"
    "kunren-a20-imagegen-reference.png"
)
IMAGEGEN_REFERENCE_PATH = (
    PRIVATE_PROOF_DEFAULT / "concepts/kunren-a21-imagegen-reference.png"
)
IMAGEGEN_REFERENCE_SHA256 = a20.IMAGEGEN_REFERENCE_SHA256
Point3 = tuple[float, float, float]


A21_LOD_BUDGETS: dict[int, LODBudget] = {
    0: LODBudget(2_180, 140_000, 12),
    1: LODBudget(1_260, 64_000, 12),
    2: LODBudget(590, 28_000, 12),
}


MAIN_REFERENCE_CAMERA = ReferenceCamera(
    name="CAM_Kunren_A21_ReferenceDual_1p65",
    location=(170.0, 1.65, -110.0),
    target=(-25.0, 18.0, 25.0),
    lens_mm=20.0,
    resolution_x=1280,
    resolution_y=720,
    eye_height_m=1.65,
    intent="focused-imagegen-compressed-command-left-hangar-right",
)

COMMAND_HERO_CAMERA = ReferenceCamera(
    "CAM_Kunren_A21_CommandHeroSouth_1p65",
    (82.0, 1.65, -14.0),
    (74.0, 25.0, 82.0),
    27.0,
    resolution_x=1280,
    resolution_y=720,
    eye_height_m=1.65,
    intent="castle-scale-command-structure-and-human-threshold",
)


PRODUCER_PROVISIONAL_SCORES: dict[str, float] = {
    "composition": 6.8,
    "hero silhouettes": 6.9,
    "architectural grammar": 6.7,
    "human scale": 6.4,
    "material realism": 6.5,
    "near/mid/far density": 6.7,
    "gameplay readability": 6.9,
    "props and environmental storytelling": 6.6,
    "lighting and atmosphere": 6.7,
    "reference identity": 6.8,
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
    assembler.connect(name, parent, child, kind, axis, overlap, note)


def _add_command_production_finish(
    assembler: a20._A20Assembler,
    hero: Any,
    lod: int,
) -> None:
    """Break the blank south mass into structural, occupied facade layers."""

    x, z = hero.cx, hero.cz
    facade_z = z - 28.86
    pier_offsets = (-28.0, -14.0, 0.0, 14.0, 28.0)
    pier_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index, offset in enumerate(pier_offsets[:pier_count]):
        pier = f"a21.cmd.south.armour-pier.{index}"
        assembler.beam(
            pier,
            (x + offset, 0.20, facade_z - 0.20),
            (x + offset, 22.5 + (index % 2) * 3.5, facade_z + 6.8),
            0.82,
            1.05,
            "wall_weathered",
            role="command-load-bearing-south-armour-pier",
        )
        _connect(
            assembler,
            f"contact.{pier}",
            "a20.cmd.hero-citadel.plinth",
            pier,
            "pier-plinth-and-keep-seat",
            "endpoint",
            0.18,
        )

    deck_levels = (17.5, 27.0, 36.5)
    deck_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, level in enumerate(deck_levels[:deck_count]):
        width = 58.0 - index * 8.0
        deck = f"a21.cmd.south.operations-deck.{index}"
        assembler.box(
            deck,
            x + 6.0,
            level,
            facade_z - 0.92,
            width,
            0.62,
            3.4,
            "trim",
            role="occupied-command-operations-deck",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{deck}",
            "a20.cmd.hero-citadel.keep",
            deck,
            "deck-facade-seat",
            "z",
            0.14,
        )
        if lod < 2:
            rail_y = level + 1.25
            for side_index, side in enumerate((-1.0, 1.0)):
                rail = f"{deck}.rail.{side_index}"
                rail_z = facade_z - 2.42 if side < 0.0 else facade_z + 0.58
                assembler.beam(
                    rail,
                    (x + 6.0 - width / 2.0, rail_y, rail_z),
                    (x + 6.0 + width / 2.0, rail_y, rail_z),
                    0.08,
                    0.08,
                    "accent" if side_index == 0 else "trim",
                    role="human-scale-command-deck-rail",
                )
                _connect(
                    assembler,
                    f"contact.{rail}",
                    deck,
                    rail,
                    "rail-deck-seat",
                    "endpoint",
                    0.10,
                )
            post_count = 7 if lod == 0 else 4
            for post_index in range(post_count):
                px = x + 6.0 - width / 2.0 + post_index * width / max(1, post_count - 1)
                post = f"{deck}.post.{post_index}"
                assembler.beam(
                    post,
                    (px, level + 0.24, facade_z - 2.42),
                    (px, level + 1.40, facade_z - 2.42),
                    0.075,
                    0.075,
                    "trim",
                    role="human-scale-command-deck-post",
                )
                _connect(
                    assembler,
                    f"contact.{post}",
                    deck,
                    post,
                    "post-deck-seat",
                    "endpoint",
                    0.10,
                )

    service_bays = (
        (-20.0, 7.0, 10.5, 8.5),
        (25.0, 7.0, 9.5, 8.0),
        (-9.0, 29.0, 8.0, 5.2),
        (18.0, 33.0, 8.5, 5.4),
    )
    bay_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index, (offset, cy, width, height) in enumerate(service_bays[:bay_count]):
        prefix = f"a21.cmd.south.service-bay.{index}"
        assembler.box(
            f"{prefix}.recess",
            x + offset,
            cy,
            facade_z - 0.55,
            width,
            height,
            0.70,
            "wall_alt",
            role="deep-command-service-recess",
            route_exempt=True,
        )
        for suffix, sx, sy, sw, sh in (
            ("left", x + offset - width / 2.0 - 0.45, cy, 0.90, height + 1.2),
            ("right", x + offset + width / 2.0 + 0.45, cy, 0.90, height + 1.2),
            ("header", x + offset, cy + height / 2.0 + 0.45, width + 1.8, 0.90),
            ("sill", x + offset, cy - height / 2.0 - 0.35, width + 1.8, 0.70),
        ):
            frame = f"{prefix}.frame.{suffix}"
            assembler.box(
                frame,
                sx,
                sy,
                facade_z - 1.06,
                sw,
                sh,
                0.80,
                "trim",
                role="command-service-bay-armoured-frame",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{frame}",
                f"{prefix}.recess",
                frame,
                "frame-recess-seat",
                "z",
                0.10,
            )
        louver_count = 5 if lod == 0 else 3 if lod == 1 else 1
        for louver_index in range(louver_count):
            louver = f"{prefix}.louver.{louver_index}"
            assembler.box(
                louver,
                x + offset,
                cy - height * 0.30 + louver_index * height * 0.15,
                facade_z - 1.50,
                width * 0.72,
                0.22,
                0.25,
                "wall_warm" if louver_index == louver_count // 2 else "trim",
                role="command-service-bay-louver",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{louver}",
                f"{prefix}.recess",
                louver,
                "louver-recess-seat",
                "z",
                0.08,
            )

    pipe_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index in range(pipe_count):
        px = x - 34.0 + index * 22.0
        pipe = f"a21.cmd.south.service-pipe.{index}"
        assembler.cylinder_between(
            pipe,
            (px, 1.0, facade_z - 1.55),
            (px, 14.0 + index * 2.0, facade_z - 1.55),
            0.28,
            "wall_cool",
            12 if lod == 0 else 8,
            role="command-facade-grounded-service-pipe",
        )
        _connect(
            assembler,
            f"contact.{pipe}",
            "a20.cmd.hero-citadel.plinth",
            pipe,
            "pipe-facade-seat",
            "endpoint",
            0.12,
        )

    if lod < 2:
        crown_parent = "a20.cmd.hero-citadel.crown"
        mast = "a21.cmd.crown.primary-radar.mast"
        assembler.cylinder_between(
            mast,
            (x + 11.0, 47.0, z - 15.0),
            (x + 11.0, 58.0, z - 15.0),
            0.28,
            "trim",
            12 if lod == 0 else 8,
            role="command-primary-radar-mast",
        )
        _connect(
            assembler,
            f"contact.{mast}",
            crown_parent,
            mast,
            "mast-crown-seat",
            "endpoint",
            0.14,
        )
        radar = "a21.cmd.crown.primary-radar.array"
        assembler.box(
            radar,
            x + 11.0,
            56.0,
            z - 15.0,
            10.0,
            4.2,
            0.42,
            "wall_cool",
            role="command-primary-radar-array",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{radar}",
            mast,
            radar,
            "radar-mast-bracket",
            "plan",
            0.12,
        )
        rung_count = 7 if lod == 0 else 4
        for rung_index in range(rung_count):
            rung = f"{radar}.rung.{rung_index}"
            assembler.beam(
                rung,
                (
                    x + 6.6 + rung_index * 8.8 / max(1, rung_count - 1),
                    54.2,
                    z - 15.34,
                ),
                (
                    x + 6.6 + rung_index * 8.8 / max(1, rung_count - 1),
                    57.8,
                    z - 15.34,
                ),
                0.07,
                0.07,
                "trim",
                role="command-radar-array-lattice",
            )
            _connect(
                assembler,
                f"contact.{rung}",
                radar,
                rung,
                "radar-lattice-seat",
                "plan",
                0.08,
            )

    # Broad battered skirts replace the remaining sheer lower corners with a
    # visible load-bearing castle profile.  They sit outside the south wall,
    # rise into the operations decks and leave the central occupied bays open.
    if lod < 2:
        skirt_specs = (
            ("west", x - 32.0, x - 17.0),
            ("east", x + 30.0, x + 41.0),
        )
        skirt_count = 2 if lod == 0 else 1
        for index, (label, x0, x1) in enumerate(skirt_specs[:skirt_count]):
            skirt = f"a21.cmd.south.battered-skirt.{label}"
            assembler.panel(
                skirt,
                (
                    (x0, 0.15, facade_z - 4.8),
                    (x1, 0.15, facade_z - 4.8),
                    (x1, 18.5, facade_z - 0.35),
                    (x0, 18.5, facade_z - 0.35),
                ),
                0.48,
                "wall_weathered",
                role="command-castle-scale-battered-armour-skirt",
            )
            _connect(
                assembler,
                f"contact.{skirt}",
                "a20.cmd.hero-citadel.plinth",
                skirt,
                "battered-skirt-plinth-seat",
                "plan",
                0.16,
            )
            shoulder = f"{skirt}.shoulder"
            assembler.beam(
                shoulder,
                (x0, 18.2, facade_z - 0.55),
                (x1, 18.2, facade_z - 0.55),
                0.42,
                0.52,
                "trim",
                role="command-battered-skirt-structural-shoulder",
            )
            _connect(
                assembler,
                f"contact.{shoulder}",
                skirt,
                shoulder,
                "shoulder-skirt-seat",
                "endpoint",
                0.12,
            )
            brace_count = 3 if lod == 0 else 2
            for brace_index in range(brace_count):
                brace_x = x0 + (brace_index + 0.5) * (x1 - x0) / brace_count
                brace = f"{skirt}.rib.{brace_index}"
                assembler.beam(
                    brace,
                    (brace_x, 0.30, facade_z - 4.86),
                    (brace_x, 18.3, facade_z - 0.61),
                    0.22,
                    0.28,
                    "trim",
                    role="command-battered-skirt-grounded-rib",
                )
                _connect(
                    assembler,
                    f"contact.{brace}",
                    skirt,
                    brace,
                    "rib-skirt-seat",
                    "endpoint",
                    0.10,
                )

        # A low asymmetric steel crest interrupts the final rectangular crown
        # without exceeding the canonical 49 m hero envelope.
        for roof_index, (label, outer_z, ridge_z) in enumerate(
            (("south", z - 23.0, z - 15.0), ("north", z - 7.0, z - 15.0))
        ):
            roof = f"a21.cmd.crown.armoured-roof.{label}"
            assembler.panel(
                roof,
                (
                    (x - 6.0, 47.65, outer_z),
                    (x + 28.0, 47.65, outer_z),
                    (x + 25.0, 48.86, ridge_z),
                    (x - 3.0, 48.86, ridge_z),
                ),
                0.22,
                "roof",
                role="command-asymmetric-armoured-crown-roof",
            )
            _connect(
                assembler,
                f"contact.{roof}",
                "a20.cmd.hero-citadel.crown",
                roof,
                "roof-crown-seat",
                "plan",
                0.10,
            )


def _add_hangar_production_finish(
    assembler: a20._A20Assembler,
    hero: Any,
    lod: int,
) -> None:
    """Give the vault a working portal, exterior service mass and docking rig."""

    x, z = hero.cx, hero.cz
    entrance_x = x + hero.width / 2.0
    tower_specs = (("south", z - 32.0), ("north", z + 32.0))
    tower_count = 2 if lod < 2 else 1
    for index, (label, tower_z) in enumerate(tower_specs[:tower_count]):
        lower = f"a21.hall.portal-tower.{label}.lower"
        assembler.box(
            lower,
            entrance_x - 1.5,
            12.0,
            tower_z,
            14.0,
            24.0,
            12.0,
            "wall_weathered",
            role="hangar-portal-load-bearing-service-tower",
            route_exempt=True,
        )
        upper = f"a21.hall.portal-tower.{label}.upper"
        assembler.box(
            upper,
            entrance_x - 4.0,
            29.0,
            tower_z,
            11.0,
            14.0,
            10.0,
            "wall",
            role="hangar-portal-service-tower-upper",
            route_exempt=True,
        )
        cap = f"a21.hall.portal-tower.{label}.cap"
        assembler.box(
            cap,
            entrance_x - 4.0,
            36.2,
            tower_z,
            12.6,
            0.60,
            11.6,
            "roof",
            role="hangar-portal-service-tower-cap",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{lower}",
            "a20.hall.cavity.floor",
            lower,
            "tower-floor-foundation",
            "y",
            0.20,
        )
        _connect(
            assembler,
            f"contact.{upper}",
            lower,
            upper,
            "tower-tier-overlap",
            "y",
            0.18,
        )
        _connect(
            assembler,
            f"contact.{cap}",
            upper,
            cap,
            "tower-cap-seat",
            "y",
            0.10,
        )
        balcony_count = 3 if lod == 0 else 2 if lod == 1 else 1
        for balcony_index in range(balcony_count):
            level = 10.0 + balcony_index * 9.0
            deck = f"a21.hall.portal-tower.{label}.balcony.{balcony_index}"
            assembler.box(
                deck,
                entrance_x + 3.8,
                level,
                tower_z,
                4.0,
                0.52,
                10.0,
                "trim",
                role="hangar-exterior-maintenance-balcony",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{deck}",
                lower if balcony_index < 2 else upper,
                deck,
                "balcony-tower-seat",
                "x",
                0.14,
            )
            if lod < 2:
                rail = f"{deck}.rail"
                assembler.beam(
                    rail,
                    (entrance_x + 5.7, level + 1.2, tower_z - 4.8),
                    (entrance_x + 5.7, level + 1.2, tower_z + 4.8),
                    0.08,
                    0.08,
                    "accent" if balcony_index == 1 else "trim",
                    role="hangar-exterior-balcony-rail",
                )
                _connect(
                    assembler,
                    f"contact.{rail}",
                    deck,
                    rail,
                    "rail-balcony-seat",
                    "endpoint",
                    0.10,
                )

    door_track_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(door_track_count):
        z_offset = -24.0 + index * 48.0 / max(1, door_track_count - 1)
        track = f"a21.hall.portal-door-track.{index}"
        assembler.beam(
            track,
            (entrance_x + 0.8, 0.25, z + z_offset),
            (entrance_x + 0.8, 31.0 - abs(z_offset) * 0.35, z + z_offset),
            0.34,
            0.42,
            "trim",
            role="hangar-monumental-door-track",
        )
        _connect(
            assembler,
            f"contact.{track}",
            "a20.hall.cavity.floor",
            track,
            "door-track-floor-and-shell-seat",
            "endpoint",
            0.14,
        )

    crane_zs = (z - 20.0, z + 20.0)
    crane_count = 2 if lod < 2 else 1
    for index, crane_z in enumerate(crane_zs[:crane_count]):
        rail = f"a21.hall.overhead-crane.rail.{index}"
        assembler.beam(
            rail,
            (entrance_x - 6.0, 40.0, crane_z),
            (x - hero.width / 2.0 + 9.0, 40.0, crane_z),
            0.42,
            0.58,
            "trim",
            role="hangar-heavy-overhead-crane-rail",
        )
        _connect(
            assembler,
            f"contact.{rail}",
            "a20.hall.rib.portal.0",
            rail,
            "crane-rail-rib-seat",
            "endpoint",
            0.16,
        )
    if lod < 2:
        crane_x = x - 14.0
        bridge = "a21.hall.overhead-crane.bridge"
        assembler.beam(
            bridge,
            (crane_x, 39.5, z - 20.0),
            (crane_x, 39.5, z + 20.0),
            0.58,
            0.68,
            "wall_warm",
            role="hangar-working-overhead-crane-bridge",
        )
        _connect(
            assembler,
            f"contact.{bridge}.south",
            "a21.hall.overhead-crane.rail.0",
            bridge,
            "bridge-rail-wheel-seat",
            "endpoint",
            0.16,
        )
        if crane_count > 1:
            _connect(
                assembler,
                f"contact.{bridge}.north",
                "a21.hall.overhead-crane.rail.1",
                bridge,
                "bridge-rail-wheel-seat",
                "endpoint",
                0.16,
            )
        hoist = "a21.hall.overhead-crane.hoist"
        assembler.cylinder_between(
            hoist,
            (crane_x, 39.2, z),
            (crane_x, 25.0, z),
            0.16,
            "trim",
            10,
            role="hangar-working-crane-hoist",
        )
        _connect(
            assembler,
            f"contact.{hoist}",
            bridge,
            hoist,
            "hoist-bridge-seat",
            "endpoint",
            0.12,
        )

    cable_specs = (
        ((x - 10.0, 44.0, z - 18.0), (x - 34.0, 26.0, z - 9.0)),
        ((x - 10.0, 44.0, z + 18.0), (x - 34.0, 26.0, z + 9.0)),
        ((x - 62.0, 44.0, z - 18.0), (x - 54.0, 25.0, z - 9.0)),
        ((x - 62.0, 44.0, z + 18.0), (x - 54.0, 25.0, z + 9.0)),
        ((x - 90.0, 37.0, z - 16.0), (x - 72.0, 22.0, z - 8.0)),
        ((x - 90.0, 37.0, z + 16.0), (x - 72.0, 22.0, z + 8.0)),
    )
    cable_count = 6 if lod == 0 else 4 if lod == 1 else 2
    for index, (start, end) in enumerate(cable_specs[:cable_count]):
        cable = f"a21.hall.aerostat.docking-cable.{index}"
        assembler.cylinder_between(
            cable,
            start,
            end,
            0.11,
            "trim",
            8 if lod < 2 else 6,
            role="aerostat-tensioned-docking-cable",
        )
        _connect(
            assembler,
            f"contact.{cable}",
            "a20.hall.aerostat.body",
            cable,
            "cable-envelope-and-truss-seat",
            "endpoint",
            0.10,
        )

    equipment_count = 6 if lod == 0 else 3 if lod == 1 else 1
    for index in range(equipment_count):
        ex = entrance_x - 22.0 - (index // 2) * 16.0
        ez = z + (-18.0 if index % 2 == 0 else 18.0)
        base = f"a21.hall.service-equipment.{index}"
        assembler.box(
            base,
            ex,
            0.55,
            ez,
            4.6,
            1.1,
            2.8,
            "wall_cool",
            role="hangar-grounded-service-equipment",
            route_exempt=True,
        )
        cabinet = f"{base}.cabinet"
        assembler.box(
            cabinet,
            ex,
            1.65,
            ez,
            2.8,
            1.8,
            2.2,
            "wall_weathered",
            role="hangar-service-equipment-cabinet",
            route_exempt=True,
        )
        face = f"{base}.status-face"
        assembler.box(
            face,
            ex + 1.46,
            1.70,
            ez,
            0.22,
            1.1,
            1.4,
            "accent",
            role="hangar-service-equipment-status",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{cabinet}",
            base,
            cabinet,
            "cabinet-base-seat",
            "y",
            0.10,
        )
        _connect(
            assembler,
            f"contact.{face}",
            cabinet,
            face,
            "status-cabinet-seat",
            "x",
            0.08,
        )

    # Grounded tow tractors turn the interior from a clean display shell into
    # a working military dock.  Their placement stays outside the 12 m portal
    # centreline and reuses the established vehicle material family.
    tractor_specs = (
        (-58.0, z - 17.0, 1.0),
        (-84.0, z + 17.0, -1.0),
        (-111.0, z - 15.0, 1.0),
    )
    tractor_count = 3 if lod == 0 else 1 if lod == 1 else 0
    for index, (tx, tz, facing) in enumerate(tractor_specs[:tractor_count]):
        body = f"a21.hall.dock-tractor.{index}.body"
        assembler.box(
            body,
            tx,
            1.15,
            tz,
            5.4,
            1.50,
            3.0,
            "wall_cool",
            role="hangar-grounded-aerostat-tow-tractor",
            route_exempt=True,
        )
        cab = f"a21.hall.dock-tractor.{index}.cab"
        assembler.box(
            cab,
            tx + facing * 1.15,
            2.35,
            tz,
            2.2,
            1.75,
            2.65,
            "wall_weathered",
            role="hangar-tow-tractor-armoured-cab",
            route_exempt=True,
        )
        window = f"a21.hall.dock-tractor.{index}.window"
        assembler.box(
            window,
            tx + facing * 2.28,
            2.55,
            tz,
            0.24,
            0.88,
            1.72,
            "wall_alt",
            role="hangar-tow-tractor-deep-window",
            route_exempt=True,
        )
        towbar = f"a21.hall.dock-tractor.{index}.towbar"
        assembler.beam(
            towbar,
            (tx - facing * 2.50, 0.82, tz),
            (tx - facing * 5.20, 0.62, tz),
            0.16,
            0.20,
            "trim",
            role="hangar-operational-aerostat-towbar",
        )
        for child, parent, kind, axis, overlap in (
            (body, "a20.hall.cavity.floor", "tractor-floor-seat", "y", 0.12),
            (cab, body, "cab-body-seat", "y", 0.10),
            (window, cab, "window-cab-seat", "plan", 0.08),
            (towbar, body, "towbar-chassis-seat", "endpoint", 0.10),
        ):
            _connect(
                assembler,
                f"contact.{child}",
                parent,
                child,
                kind,
                axis,
                overlap,
            )
        for axle_index, axle_x in enumerate((tx - 1.55, tx + 1.55)):
            for side_index, side in enumerate((-1.0, 1.0)):
                wheel = f"a21.hall.dock-tractor.{index}.wheel.{axle_index}.{side_index}"
                assembler.cylinder_between(
                    wheel,
                    (axle_x, 0.62, tz + side * 1.26),
                    (axle_x, 0.62, tz + side * 1.58),
                    0.52,
                    "trim",
                    12 if lod == 0 else 8,
                    role="hangar-tow-tractor-wheel",
                )
                _connect(
                    assembler,
                    f"contact.{wheel}",
                    body,
                    wheel,
                    "wheel-chassis-seat",
                    "plan",
                    0.10,
                )


def _add_connected_district_and_story(
    assembler: a20._A20Assembler,
    lod: int,
) -> None:
    """Occupy the focused camera route without blocking canonical clearances."""

    checkpoint_clusters = (
        (136.0, -83.0, -1.0),
        (123.0, -65.0, 1.0),
        (108.0, -46.0, -1.0),
    )
    cluster_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, (cx, cz, side) in enumerate(checkpoint_clusters[:cluster_count]):
        booth = f"a21.checkpoint.route-cluster.{index}.booth"
        assembler.box(
            booth,
            cx,
            1.7,
            cz + side * 11.5,
            4.8,
            3.4,
            5.2,
            "wall_weathered",
            yaw=-0.63,
            role="human-scale-occupied-checkpoint-booth",
            route_exempt=True,
        )
        window = f"{booth}.window"
        assembler.box(
            window,
            cx - 1.55,
            2.05,
            cz + side * 11.5 - 1.95,
            2.2,
            1.15,
            0.28,
            "wall_alt",
            yaw=-0.63,
            role="deep-checkpoint-booth-window",
            route_exempt=True,
        )
        roof = f"{booth}.roof"
        assembler.box(
            roof,
            cx,
            3.65,
            cz + side * 11.5,
            5.8,
            0.30,
            6.2,
            "roof",
            yaw=-0.63,
            role="checkpoint-booth-weather-roof",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{window}",
            booth,
            window,
            "window-wall-seat",
            "plan",
            0.08,
        )
        _connect(
            assembler,
            f"contact.{roof}",
            booth,
            roof,
            "roof-booth-seat",
            "y",
            0.10,
        )
        for barrier_index in range(2 if lod < 2 else 1):
            barrier = f"a21.checkpoint.route-cluster.{index}.barrier.{barrier_index}"
            bz = cz + side * (7.0 + barrier_index * 4.5)
            assembler.box(
                barrier,
                cx - 5.5 + barrier_index * 5.0,
                0.62,
                bz,
                4.2,
                1.24,
                1.2,
                "obstacle",
                yaw=-0.63,
                role="grounded-checkpoint-blast-barrier",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{barrier}",
                booth,
                barrier,
                "barrier-booth-route-shoulder",
                "plan",
                0.10,
            )
        light = f"a21.checkpoint.route-cluster.{index}.floodlight"
        assembler.beam(
            light,
            (cx + 3.5, 0.1, cz + side * 11.5),
            (cx + 3.5, 7.2, cz + side * 11.5),
            0.11,
            0.11,
            "trim",
            role="grounded-route-floodlight-mast",
        )
        _connect(
            assembler,
            f"contact.{light}",
            booth,
            light,
            "mast-booth-foundation",
            "endpoint",
            0.10,
        )
        lamp = f"{light}.head"
        assembler.box(
            lamp,
            cx + 3.1,
            7.25,
            cz + side * 11.5,
            1.2,
            0.45,
            0.72,
            "accent",
            yaw=-0.63,
            role="route-floodlight-head",
            route_exempt=True,
        )
        _connect(
            assembler,
            f"contact.{lamp}",
            light,
            lamp,
            "lamp-mast-seat",
            "plan",
            0.08,
        )

    bridge_specs = (
        (
            "a20.district.dense-block.15",
            "a20.district.dense-block.16",
            (-8.0, 13.5, 9.0),
            (18.0, 13.5, 28.0),
        ),
        (
            "a20.district.dense-block.17",
            "a20.district.dense-block.19",
            (-38.0, 16.0, 31.0),
            (-61.0, 16.0, 79.0),
        ),
        (
            "a20.district.dense-block.2",
            "a20.district.dense-block.3",
            (-116.0, 21.0, 53.0),
            (-96.0, 21.0, 118.0),
        ),
    )
    if lod == 1:
        bridge_specs = (
            (
                "a20.district.dense-block.8",
                "a20.district.dense-block.9",
                (76.0, 24.0, 151.0),
                (112.0, 24.0, 137.0),
            ),
            (
                "a20.district.dense-block.10",
                "a20.district.dense-block.11",
                (139.0, 20.0, 111.0),
                (151.0, 20.0, 78.0),
            ),
        )
    bridge_count = 3 if lod == 0 else 2 if lod == 1 else 0
    for index, (parent_a, parent_b, start, end) in enumerate(bridge_specs[:bridge_count]):
        bridge = f"a21.district.service-bridge.{index}"
        assembler.beam(
            bridge,
            start,
            end,
            0.48,
            0.55,
            "trim",
            role="connected-district-utility-bridge",
        )
        _connect(
            assembler,
            f"contact.{bridge}.a",
            parent_a,
            bridge,
            "bridge-building-seat",
            "endpoint",
            0.16,
        )
        _connect(
            assembler,
            f"contact.{bridge}.b",
            parent_b,
            bridge,
            "bridge-building-seat",
            "endpoint",
            0.16,
        )

    # The inherited route vehicles already carry correct wheels and collision-
    # free placement, but their three-box bodies read as proxies at 1.65 m.
    # Layer a recognisable armoured hood, bumper, grille, roof station and
    # antenna onto those same grounded vehicles without changing traversal.
    road_start = (178.0, -116.0)
    road_end = (18.0, 18.0)
    road_dx = road_end[0] - road_start[0]
    road_dz = road_end[1] - road_start[1]
    road_length = math.hypot(road_dx, road_dz)
    road_ux, road_uz = road_dx / road_length, road_dz / road_length
    road_nx, road_nz = -road_uz, road_ux
    road_yaw = math.atan2(road_dz, road_dx)

    def road_point(t: float, lateral: float) -> tuple[float, float]:
        return (
            road_start[0] + road_ux * road_length * t + road_nx * lateral,
            road_start[1] + road_uz * road_length * t + road_nz * lateral,
        )

    vehicle_specs = ((0.17, 15.0, "apc"), (0.27, -15.0, "signals-truck"))
    vehicle_count = 2 if lod == 0 else 1 if lod == 1 else 0
    for index, (t, lateral, kind) in enumerate(vehicle_specs[:vehicle_count]):
        vx, vz = road_point(t, lateral)
        parent = f"a20.story.foreground-vehicle.{index}.{kind}"
        hood = f"a21.story.foreground-vehicle.{index}.armoured-hood"
        assembler.box(
            hood,
            vx + road_ux * 2.45,
            2.05,
            vz + road_uz * 2.45,
            2.55,
            0.78,
            3.18,
            "wall_weathered",
            yaw=road_yaw,
            role="foreground-vehicle-sloped-armour-hood",
            route_exempt=True,
        )
        bumper = f"a21.story.foreground-vehicle.{index}.front-bumper"
        assembler.box(
            bumper,
            vx + road_ux * 3.72,
            0.92,
            vz + road_uz * 3.72,
            0.42,
            0.52,
            3.75,
            "trim",
            yaw=road_yaw,
            role="foreground-vehicle-heavy-bumper",
            route_exempt=True,
        )
        grille = f"a21.story.foreground-vehicle.{index}.recessed-grille"
        assembler.box(
            grille,
            vx + road_ux * 3.77,
            1.52,
            vz + road_uz * 3.77,
            0.24,
            0.82,
            2.45,
            "wall_alt",
            yaw=road_yaw,
            role="foreground-vehicle-deep-grille",
            route_exempt=True,
        )
        hatch = f"a21.story.foreground-vehicle.{index}.roof-hatch"
        assembler.cylinder(
            hatch,
            vx - road_ux * 0.55,
            3.32,
            vz - road_uz * 0.55,
            0.84,
            0.24,
            "trim",
            16 if lod == 0 else 10,
            role="foreground-vehicle-armoured-roof-hatch",
        )
        station = f"a21.story.foreground-vehicle.{index}.roof-station"
        assembler.cylinder(
            station,
            vx - road_ux * 0.55,
            3.72,
            vz - road_uz * 0.55,
            0.48,
            0.62,
            "wall_cool",
            14 if lod == 0 else 8,
            role="foreground-vehicle-observation-station",
        )
        antenna = f"a21.story.foreground-vehicle.{index}.antenna"
        assembler.beam(
            antenna,
            (
                vx - road_ux * 0.80 + road_nx * 0.42,
                3.82,
                vz - road_uz * 0.80 + road_nz * 0.42,
            ),
            (
                vx - road_ux * 1.15 + road_nx * 0.42,
                6.15,
                vz - road_uz * 1.15 + road_nz * 0.42,
            ),
            0.045,
            0.045,
            "trim",
            role="foreground-vehicle-radio-antenna",
        )
        for child, contact_kind, axis, overlap in (
            (hood, "hood-body-seat", "y", 0.12),
            (bumper, "bumper-chassis-seat", "plan", 0.10),
            (grille, "grille-hood-seat", "plan", 0.08),
            (hatch, "hatch-roof-seat", "y", 0.10),
            (station, "station-hatch-seat", "y", 0.10),
            (antenna, "antenna-station-seat", "endpoint", 0.08),
        ):
            _connect(
                assembler,
                f"contact.{child}",
                parent if child in {hood, bumper, hatch} else hood if child == grille else hatch if child == station else station,
                child,
                contact_kind,
                axis,
                overlap,
            )
        headlight_count = 2 if lod == 0 else 1
        for light_index, side in enumerate((-1.0, 1.0)[:headlight_count]):
            light = f"a21.story.foreground-vehicle.{index}.headlight.{light_index}"
            assembler.box(
                light,
                vx + road_ux * 3.92 + road_nx * side * 1.18,
                1.40,
                vz + road_uz * 3.92 + road_nz * side * 1.18,
                0.18,
                0.42,
                0.52,
                "wall_warm",
                yaw=road_yaw,
                role="foreground-vehicle-recessed-headlight",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{light}",
                hood,
                light,
                "headlight-armour-seat",
                "plan",
                0.08,
            )

    # Add vertical load paths, deep apertures and facade belts to the key
    # perimeter towers.  These few high-value modules make the aerial district
    # read as an inhabited fortified system instead of a repeated box grid.
    district_finish = (
        (0, -154.0, -6.0, 18.0, 25.0, 14.0, 0.00),
        (3, -96.0, 118.0, 24.0, 36.0, 17.0, 0.05),
        (5, -34.0, 158.0, 24.0, 39.0, 18.0, 0.04),
        (7, 38.0, 158.0, 25.0, 42.0, 18.0, 0.06),
        (9, 112.0, 137.0, 24.0, 38.0, 18.0, 0.04),
        (11, 151.0, 78.0, 23.0, 36.0, 17.0, 0.05),
        (15, -8.0, 9.0, 18.0, 18.0, 14.0, 0.04),
        (19, -61.0, 79.0, 18.0, 24.0, 14.0, 0.05),
    )
    district_count = 8 if lod == 0 else 4 if lod == 1 else 0
    for index, bx, bz, width, height, depth, yaw in district_finish[:district_count]:
        parent = f"a20.district.dense-block.{index}"
        front_z = bz - depth / 2.0 - 0.32
        bay = f"a21.district.facade-finish.{index}.deep-bay"
        assembler.box(
            bay,
            bx,
            height * 0.30,
            front_z,
            width * 0.34,
            max(2.8, height * 0.17),
            0.42,
            "wall_alt",
            yaw=yaw,
            role="occupied-district-deep-service-bay",
            route_exempt=True,
        )
        belt = f"a21.district.facade-finish.{index}.armour-belt"
        assembler.box(
            belt,
            bx,
            height * 0.61,
            front_z - 0.10,
            width * 0.82,
            0.56,
            0.64,
            "trim",
            yaw=yaw,
            role="district-structural-armour-belt",
            route_exempt=True,
        )
        for fin_index, side in enumerate((-1.0, 1.0)):
            fin = f"a21.district.facade-finish.{index}.load-fin.{fin_index}"
            assembler.box(
                fin,
                bx + side * width * 0.36,
                height * 0.34,
                front_z - 0.04,
                0.58,
                height * 0.68,
                0.68,
                "wall_weathered",
                yaw=yaw,
                role="district-grounded-facade-load-fin",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{fin}",
                parent,
                fin,
                "load-fin-wall-seat",
                "plan",
                0.10,
            )
        for child, contact_kind, axis, overlap in (
            (bay, "bay-wall-seat", "z", 0.08),
            (belt, "belt-wall-seat", "z", 0.10),
        ):
            _connect(
                assembler,
                f"contact.{child}",
                parent,
                child,
                contact_kind,
                axis,
                overlap,
            )
        if lod == 0 and index % 2:
            mast = f"a21.district.facade-finish.{index}.roof-mast"
            assembler.beam(
                mast,
                (bx, height - 0.20, bz),
                (bx + 0.45, height + 5.6, bz - 0.35),
                0.075,
                0.075,
                "trim",
                role="district-rooftop-comms-mast",
            )
            _connect(
                assembler,
                f"contact.{mast}",
                f"{parent}.roof-cap",
                mast,
                "mast-roof-seat",
                "endpoint",
                0.10,
            )

    # Dedicated alternating roof profiles are the highest-read skyline change
    # in the aerial proof.  Keep them below the hero landmarks, but replace the
    # repeated flat caps with broad shed and gable silhouettes.
    dense_roof_specs = (
        (-154.0, -6.0, 18.0, 25.0, 14.0),
        (-138.0, 25.0, 22.0, 31.0, 16.0),
        (-116.0, 53.0, 19.0, 27.0, 15.0),
        (-96.0, 118.0, 24.0, 36.0, 17.0),
        (-66.0, 146.0, 22.0, 30.0, 15.0),
        (-34.0, 158.0, 24.0, 39.0, 18.0),
        (2.0, 160.0, 20.0, 33.0, 15.0),
        (38.0, 158.0, 25.0, 42.0, 18.0),
        (76.0, 151.0, 22.0, 35.0, 16.0),
        (112.0, 137.0, 24.0, 38.0, 18.0),
        (139.0, 111.0, 21.0, 30.0, 15.0),
        (151.0, 78.0, 23.0, 36.0, 17.0),
        (154.0, 43.0, 19.0, 28.0, 14.0),
        (-151.0, 75.0, 20.0, 29.0, 15.0),
        (-128.0, 105.0, 23.0, 34.0, 17.0),
        (-8.0, 9.0, 18.0, 18.0, 14.0),
        (18.0, 28.0, 17.0, 21.0, 13.0),
        (-38.0, 31.0, 19.0, 23.0, 15.0),
        (42.0, 57.0, 16.0, 18.0, 13.0),
        (-61.0, 79.0, 18.0, 24.0, 14.0),
    )
    roof_count = 20 if lod == 0 else 12 if lod == 1 else 4
    for index, (bx, bz, width, height, depth) in enumerate(
        dense_roof_specs[:roof_count]
    ):
        parent = f"a20.district.dense-block.{index}.roof-cap"
        eave_y = height + 0.38
        ridge_y = height + (2.6 if index % 3 else 3.2)
        half_w = width * 0.43
        half_d = depth * 0.43
        if index % 2 == 0:
            roof = f"a21.district.roof-profile.{index}.shed"
            assembler.panel(
                roof,
                (
                    (bx - half_w, eave_y, bz - half_d),
                    (bx + half_w, ridge_y, bz - half_d),
                    (bx + half_w, ridge_y, bz + half_d),
                    (bx - half_w, eave_y, bz + half_d),
                ),
                0.20,
                "roof",
                role="kunren-dedicated-broad-shed-roof-profile",
            )
            _connect(
                assembler,
                f"contact.{roof}",
                parent,
                roof,
                "shed-roof-cap-seat",
                "plan",
                0.10,
            )
        else:
            for side_index, (label, eave_x) in enumerate(
                (("west", bx - half_w), ("east", bx + half_w))
            ):
                roof = f"a21.district.roof-profile.{index}.gable.{label}"
                corners = (
                    (eave_x, eave_y, bz - half_d),
                    (eave_x, eave_y, bz + half_d),
                    (bx, ridge_y, bz + half_d),
                    (bx, ridge_y, bz - half_d),
                )
                assembler.panel(
                    roof,
                    corners,
                    0.20,
                    "roof",
                    role="kunren-dedicated-broad-gable-roof-profile",
                )
                _connect(
                    assembler,
                    f"contact.{roof}",
                    parent,
                    roof,
                    "gable-roof-cap-seat",
                    "plan",
                    0.10,
                )

    story_clusters = (
        (147.0, -126.0),
        (128.0, -105.0),
        (98.0, -72.0),
        (42.0, -24.0),
        (-8.0, 12.0),
    )
    story_count = 5 if lod == 0 else 3 if lod == 1 else 1
    for index, (sx, sz) in enumerate(story_clusters[:story_count]):
        pallet = f"a21.story.route-maintenance.{index}.pallet"
        assembler.box(
            pallet,
            sx,
            0.12,
            sz,
            3.4,
            0.24,
            2.6,
            "wood",
            role="grounded-route-maintenance-pallet",
            route_exempt=True,
        )
        crate_count = 3 if lod == 0 else 2 if lod == 1 else 1
        for crate_index in range(crate_count):
            crate = f"a21.story.route-maintenance.{index}.crate.{crate_index}"
            assembler.box(
                crate,
                sx - 0.9 + crate_index * 0.9,
                0.65 + (crate_index % 2) * 0.55,
                sz,
                1.05,
                1.1,
                1.0,
                "obstacle",
                yaw=0.08 * (crate_index - 1),
                role="military-route-maintenance-crate",
                route_exempt=True,
            )
            _connect(
                assembler,
                f"contact.{crate}",
                pallet,
                crate,
                "crate-pallet-seat",
                "y",
                0.10,
            )
        if lod < 2:
            for drum_index in range(2):
                drum = f"a21.story.route-maintenance.{index}.drum.{drum_index}"
                assembler.cylinder(
                    drum,
                    sx + 2.4,
                    0.58,
                    sz - 0.75 + drum_index * 1.5,
                    0.46,
                    1.16,
                    "wall_warm",
                    12 if lod == 0 else 8,
                    role="grounded-route-service-drum",
                )
                _connect(
                    assembler,
                    f"contact.{drum}",
                    pallet,
                    drum,
                    "drum-floor-seat",
                    "y",
                    0.08,
                )


def _estimate_triangles(plan: KunrenPlan) -> int:
    return a20._estimated_triangles(plan)


def _validate_a21(
    additions: a20._A20Assembler,
    constraints: Any,
    budget: LODBudget,
    merged: KunrenPlan,
) -> dict[str, Any]:
    """Reuse A20 structural validation, then apply A21 release language."""

    metrics = dict(a20._validate_a20(additions, constraints, budget, merged))
    metrics["a21AdditionCount"] = metrics.pop("a20AdditionCount")
    metrics["estimatedTriangles"] = _estimate_triangles(merged)
    metrics["visualFinishPriority"] = (
        "reference composition, landmark structure, surface response, story and light"
    )
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
            "role": "focused fixed 1.65 m production composition guide",
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
            "Only a different reviewer may determine whether the production "
            "concrete, working aerostat hall, terraced military density and "
            "alpine atmosphere reach both original-resolution references"
        ),
        "evidencePaths": list(evidence_paths),
    }


def make_kunren_reference_a21_plan(
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: Mapping[str, ApproachSpec | Mapping[str, Any]] | None = None,
    lod_budget: LODBudget | None = None,
) -> KunrenPlan:
    """Build the isolated A21 plan without mutating authoritative stage data."""

    if lod not in A21_LOD_BUDGETS:
        raise ValueError(f"unsupported A21 LOD {lod}")
    before = copy.deepcopy(stage)
    budget = lod_budget or A21_LOD_BUDGETS[lod]
    constraints = constraints_from_authoritative_layout(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=budget,
    )
    base = a20.make_kunren_reference_a20_plan(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=budget,
    )
    additions = a20._A20Assembler(base.names)
    _add_command_production_finish(additions, constraints.command, lod)
    _add_hangar_production_finish(additions, constraints.hangar, lod)
    _add_connected_district_and_story(additions, lod)

    provisional = KunrenPlan(
        boxes=(*base.boxes, *additions.boxes),
        beams=(*base.beams, *additions.beams),
        cylinders=(*base.cylinders, *additions.cylinders),
        cylinders_between=(*base.cylinders_between, *additions.cylinders_between),
        sloped_panels=(*base.sloped_panels, *additions.sloped_panels),
        rocks=(*base.rocks, *additions.rocks),
        connections=(*base.connections, *additions.connections),
        metadata={},
    )
    metrics = _validate_a21(additions, constraints, budget, provisional)
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
        raise ValueError(f"A21 proof cameras are embedded in solid geometry: {blocked}")
    command_frame = camera_hero_frame_metrics(
        MAIN_REFERENCE_CAMERA,
        constraints.command,
    )
    hangar_frame = camera_hero_frame_metrics(
        MAIN_REFERENCE_CAMERA,
        constraints.hangar,
    )
    metadata = {
        **base.metadata,
        "kitVersion": KIT_VERSION,
        "baseVisualKit": base.metadata["kitVersion"],
        "lod": lod,
        "constructionOrder": [
            "focused-imagegen-and-repository-reference-lock",
            "fixed-1p65m-dual-camera-lock",
            "authoritative-contract-freeze",
            "connection-mapped-command-production-finish",
            "connection-mapped-hangar-production-finish",
            "connected-terraces-and-military-story",
            "procedural-pbr-weathering-and-directional-alpine-light",
            "private-1280-proof-and-producer-provisional-no-ship",
        ],
        "productionBrief": {
            "focalHierarchy": [
                "left castle-scale structurally credible Command Bastion",
                "right monumental working Aerostat Vault Hangar",
                "foreground checkpoint and split-height service routes",
                "connected terraced military district and layered alpine boundary",
            ],
            "camera": (
                "fixed playable 1.65 m, 20 mm, compressed dual-landmark "
                "composition from focused ImageGen"
            ),
            "style": (
                "photoreal weathered reinforced concrete, oxidized steel, "
                "worked asphalt, dusty rock and restrained safety orange"
            ),
            "gameplay": (
                "canonical routes, spawns and TypeScript collision remain "
                "authoritative; Blender shell is visual-only"
            ),
            "forbidden": (
                "generic box grid, proxy vehicles, flat clay materials, "
                "floating caps, sparse plaza, raster or cylindrical matte"
            ),
        },
        "mainReferenceCamera": asdict(MAIN_REFERENCE_CAMERA),
        "commandHeroInspectionCamera": asdict(COMMAND_HERO_CAMERA),
        "proofCameraClearance": camera_clearance,
        "heroFrameMetrics": {
            COMMAND_ID: command_frame,
            HANGAR_ID: hangar_frame,
        },
        "imageGenReference": {
            "privatePath": str(IMAGEGEN_REFERENCE_PATH),
            "sha256": IMAGEGEN_REFERENCE_SHA256,
            "sourceReferenceSha256": REFERENCE_IMAGE_SHA256,
            "usedBeforeModeling": True,
        },
        "landmarkIdentityContract": {
            "exactCount": 2,
            "ids": [COMMAND_ID, HANGAR_ID],
            "thirdLandmarkAllowed": False,
        },
        "authoritativeContracts": {
            "stageBounds": {"size": stage["size"], "changed": False},
            "placementPolicy": "unchanged-canonical-centres-widths-depths-heights",
            "approaches": {
                COMMAND_ID: asdict(constraints.command.approach),
                HANGAR_ID: asdict(constraints.hangar.approach),
            },
            "playerSpawns": [list(point) for point in constraints.player_spawns],
            "botSpawns": [list(point) for point in constraints.bot_spawns],
            "collisionPolicy": (
                "visual-only; canonical gameplay collision remains authoritative"
            ),
        },
        "surfaceResponseContract": {
            "families": [
                "weathered-reinforced-concrete",
                "oxidized-dark-structural-steel",
                "painted-safety-metal",
                "worked-asphalt-with-patches",
                "dusty-jagged-alpine-rock",
                "service-wood-rubber-and-equipment",
            ],
            "requiredChannels": ["baseColor", "roughness", "normalOrBump"],
            "proceduralVariation": [
                "large-scale staining",
                "fine aggregate",
                "object-scale variation",
                "roughness breakup",
                "contact dirt and restrained emissive response",
            ],
            "flatColorAloneIsBlockout": True,
            "deepOpeningsAreGeometry": True,
            "proofMaterialLimit": 12,
        },
        "lodContract": {
            "levels": [0, 1, 2],
            "reductionOrder": [
                "minor story clusters and maintenance props",
                "rails, secondary bays, service cables and small equipment",
                "district connectors, aperture count and mountain segments",
            ],
            "heroSilhouettesPreservedAtAllLods": True,
            "mergeByMaterialForWebGL": True,
            "primitiveCountIsNotAVisualQualityGate": True,
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
            "publicAssetWritesAllowed": False,
            "repoBuildIntegrationAllowed": False,
            "manifestWritesAllowed": False,
            "sourceWritesAllowed": False,
            "headlessOrSafeLocalhostMcpOnly": True,
        },
        "lodBudget": asdict(budget),
        "metrics": metrics,
        "connectionMap": [
            asdict(connection) for connection in provisional.connections
        ],
        "producerProvisionalScorecard": producer_provisional_scorecard(),
    }
    if stage != before:
        raise RuntimeError("A21 planning mutated authoritative stage input")
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


def emit_kunren_reference_a21_plan(
    builder: MeshBuilderProtocol,
    plan: KunrenPlan,
) -> Mapping[str, Any]:
    """Emit A21 through the reviewed A19/A20 geometry builder surface."""

    return a20.emit_kunren_reference_a20_plan(builder, plan)


def build_kunren_reference_a21(
    builder: MeshBuilderProtocol,
    stage: Mapping[str, Any],
    lod: int,
    **kwargs: Any,
) -> Mapping[str, Any]:
    plan = make_kunren_reference_a21_plan(stage, lod, **kwargs)
    return emit_kunren_reference_a21_plan(builder, plan)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_private_reference(output_dir: Path) -> Path:
    if not A20_IMAGEGEN_REFERENCE_PATH.exists():
        raise FileNotFoundError(
            f"missing focused A20 ImageGen reference: {A20_IMAGEGEN_REFERENCE_PATH}"
        )
    actual = _sha256(A20_IMAGEGEN_REFERENCE_PATH)
    if actual != IMAGEGEN_REFERENCE_SHA256:
        raise ValueError(
            f"focused ImageGen reference hash mismatch: "
            f"{actual} != {IMAGEGEN_REFERENCE_SHA256}"
        )
    target = output_dir / "concepts/kunren-a21-imagegen-reference.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(A20_IMAGEGEN_REFERENCE_PATH, target)
    return target


def _run_blender_private_proof(
    plan: KunrenPlan,
    output_dir: Path,
) -> dict[str, Any]:
    """Build A20-reviewed geometry, apply A21 lookdev, render, and save."""

    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    output_dir = output_dir.expanduser().resolve()
    repo_root = REPO_ROOT.resolve()
    if str(output_dir).startswith(str(repo_root)):
        raise ValueError("A21 proof output must stay outside the repository")
    if not str(output_dir).startswith("/private/tmp/"):
        raise ValueError("A21 proof output must stay under /private/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    views_dir = output_dir / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir = output_dir / "_a20-reviewed-builder-scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    imagegen_reference = _ensure_private_reference(output_dir)

    # Preserve the user's currently visible Blender work before A20's reviewed
    # builder replaces the temporary scene.  copy=True leaves the active file
    # path untouched while giving this isolated production pass a recovery file.
    prebuild_backup = output_dir / "visible-scene-pre-a21.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(prebuild_backup), copy=True)

    # A20 owns the safe, connection-aware Blender primitive implementation.
    # It writes only into the private scratch directory and leaves the complete
    # A21 plan in the current scene for the material/light/terrain finish below.
    scratch_manifest = a20._run_blender_private_proof(plan, scratch_dir)

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
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.12

    root = bpy.data.collections.get("HB_kunren_A19_ROOT")
    if root is not None:
        root.name = "HB_kunren_A21_ROOT"
    for collection in bpy.data.collections:
        if collection.name.startswith("HB_kunren_"):
            collection["a21KitVersion"] = KIT_VERSION
    # Repeated live-bridge rebuilds retain old A21 datablocks even though the
    # reviewed A20 builder has now replaced the scene with A20 materials.
    # Remove only that superseded A21 namespace before rebuilding the twelve
    # current A21 families.
    for material in list(bpy.data.materials):
        if material.name.startswith("A21_MAT_"):
            bpy.data.materials.remove(material)

    palette = {
        "wall": (0.22, 0.205, 0.180, 1.0),
        "wall_alt": (0.010, 0.014, 0.017, 1.0),
        "wall_cool": (0.045, 0.060, 0.066, 1.0),
        "wall_warm": (0.20, 0.120, 0.045, 1.0),
        "wall_weathered": (0.16, 0.145, 0.115, 1.0),
        "roof": (0.025, 0.034, 0.038, 1.0),
        "trim": (0.020, 0.028, 0.032, 1.0),
        "accent": (0.24, 0.032, 0.004, 1.0),
        "terrain": (0.115, 0.085, 0.050, 1.0),
        "obstacle": (0.20, 0.115, 0.033, 1.0),
        "wood": (0.135, 0.065, 0.020, 1.0),
        "road": (0.022, 0.027, 0.030, 1.0),
    }

    def rebuild_material(key: str, base: tuple[float, float, float, float]) -> Any:
        material = bpy.data.materials.get(f"A20_MAT_{key}")
        if material is None:
            material = bpy.data.materials.get(f"A19_MAT_{key}")
        if material is None:
            raise RuntimeError(f"missing inherited material family {key}")
        material.name = f"A21_MAT_{key}"
        material.diffuse_color = base
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        texcoord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        coarse = nodes.new("ShaderNodeTexNoise")
        fine = nodes.new("ShaderNodeTexNoise")
        ramp = nodes.new("ShaderNodeValToRGB")
        roughness = nodes.new("ShaderNodeMapRange")
        bump_mix = nodes.new("ShaderNodeMixRGB")
        bump = nodes.new("ShaderNodeBump")
        coarse.inputs["Scale"].default_value = {
            "terrain": 2.2,
            "road": 5.0,
            "wall": 3.4,
            "wall_weathered": 3.0,
        }.get(key, 7.0)
        coarse.inputs["Detail"].default_value = 7.0 if key in {
            "wall",
            "wall_weathered",
            "terrain",
        } else 4.0
        coarse.inputs["Roughness"].default_value = 0.72
        fine.inputs["Scale"].default_value = 52.0 if key in {
            "wall",
            "wall_weathered",
            "terrain",
            "road",
        } else 24.0
        fine.inputs["Detail"].default_value = 3.5
        fine.inputs["Roughness"].default_value = 0.82
        low_factor = 0.48 if key not in {"wall_alt", "road"} else 0.70
        high_factor = 1.30 if key not in {"accent", "wall_alt"} else 1.08
        ramp.color_ramp.elements[0].position = 0.30
        ramp.color_ramp.elements[0].color = tuple(
            max(0.0, value * low_factor) for value in base[:3]
        ) + (1.0,)
        ramp.color_ramp.elements[1].position = 0.76
        ramp.color_ramp.elements[1].color = tuple(
            min(1.0, value * high_factor) for value in base[:3]
        ) + (1.0,)
        if key in {"wall", "wall_weathered", "terrain", "road"}:
            middle = ramp.color_ramp.elements.new(0.53)
            middle.color = tuple(
                min(1.0, value * 0.88) for value in base[:3]
            ) + (1.0,)
        roughness.inputs["To Min"].default_value = (
            0.34 if key in {"trim", "roof", "wall_cool"} else 0.66
        )
        roughness.inputs["To Max"].default_value = (
            0.62 if key in {"trim", "roof", "wall_cool"} else 0.95
        )
        bump_mix.blend_type = "MULTIPLY"
        bump_mix.inputs[0].default_value = 0.38
        bump.inputs["Strength"].default_value = (
            0.34 if key in {"wall", "wall_weathered", "terrain", "road"} else 0.12
        )
        bump.inputs["Distance"].default_value = (
            0.075 if key in {"wall", "wall_weathered"} else 0.035
        )
        metallic = 0.0
        if key == "trim":
            metallic = 0.78
        elif key == "roof":
            metallic = 0.42
        elif key == "wall_cool":
            metallic = 0.52
        shader.inputs["Metallic"].default_value = metallic
        if "Coat Weight" in shader.inputs:
            shader.inputs["Coat Weight"].default_value = 0.08 if key in {
                "roof",
                "wall_cool",
                "obstacle",
            } else 0.0
        if key == "accent":
            emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
            strength = shader.inputs.get("Emission Strength")
            if emission is not None:
                emission.default_value = (0.32, 0.022, 0.002, 1.0)
            if strength is not None:
                strength.default_value = 0.10
        links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], coarse.inputs["Vector"])
        links.new(mapping.outputs["Vector"], fine.inputs["Vector"])
        links.new(coarse.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
        links.new(coarse.outputs["Fac"], roughness.inputs["Value"])
        links.new(roughness.outputs["Result"], shader.inputs["Roughness"])
        links.new(coarse.outputs["Fac"], bump_mix.inputs[1])
        links.new(fine.outputs["Fac"], bump_mix.inputs[2])
        links.new(bump_mix.outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        material["a21RequiredChannels"] = "baseColor,roughness,normalOrBump"
        material["a21SurfaceFamily"] = key
        material["a21ProceduralWeathering"] = True
        return material

    materials = {key: rebuild_material(key, base) for key, base in palette.items()}

    # Improve visible structural contacts without changing canonical placement.
    for obj in bpy.data.objects:
        part_name = obj.get("a20PartName") or obj.get("a19PartName")
        if not isinstance(part_name, str) or obj.type != "MESH":
            continue
        obj["a21PartName"] = part_name
        obj["a21KitVersion"] = KIT_VERSION
        if part_name.startswith(("a20.cmd.", "a20.hall.", "a21.cmd.", "a21.hall.")):
            bevel = next(
                (modifier for modifier in obj.modifiers if modifier.type == "BEVEL"),
                None,
            )
            if bevel is not None:
                bevel.width = min(0.14, max(0.045, float(bevel.width)))
                bevel.segments = 2

    # Replace every radial mountain proxy with a deterministic asymmetric
    # multi-peak heightfield.  The old ring/summit construction still read as
    # repeated cones from the locked cameras; this creates long broken ridges,
    # secondary saddles and a grounded broad alpine boundary.
    mountain_specs = {
        spec.name: spec
        for spec in plan.rocks
        if "mountain" in spec.role or "ridge" in spec.role or "foothill" in spec.role
    }
    terrain_material = materials["terrain"]
    mountain_mesh_count = 0
    for obj in list(bpy.data.objects):
        part_name = obj.get("a21PartName")
        spec = mountain_specs.get(part_name)
        if spec is None or obj.type != "MESH":
            continue
        columns = 17 if plan.metadata["lod"] == 0 else 13 if plan.metadata["lod"] == 1 else 9
        rows = 13 if plan.metadata["lod"] == 0 else 9 if plan.metadata["lod"] == 1 else 7
        vertices: list[tuple[float, float, float]] = []
        phase = spec.seed * 0.071
        peak_specs = (
            (-0.38 + 0.06 * math.sin(phase), -0.08, 0.92, 0.58, 0.52),
            (0.16, 0.16 + 0.04 * math.cos(phase), 0.74, 0.62, 0.48),
            (0.48, -0.20, 0.52, 0.46, 0.42),
            (-0.06, -0.36, 0.42, 0.66, 0.38),
        )
        for row in range(rows):
            ny = -1.0 + 2.0 * row / max(1, rows - 1)
            for column in range(columns):
                nx = -1.0 + 2.0 * column / max(1, columns - 1)
                elliptical_radius = math.sqrt(nx * nx + ny * ny)
                edge = max(0.0, 1.0 - elliptical_radius ** 1.55)
                peak_sum = 0.0
                for px, py, amplitude, spread_x, spread_y in peak_specs:
                    dx = (nx - px) / spread_x
                    dy = (ny - py) / spread_y
                    peak_sum += amplitude * math.exp(-(dx * dx + dy * dy))
                broken_ridge = (
                    0.92
                    + 0.08 * math.sin(nx * 7.0 + phase)
                    + 0.055 * math.sin(ny * 9.0 - phase * 1.7)
                    + 0.035 * math.sin((nx + ny) * 13.0 + phase * 0.7)
                )
                height_factor = min(
                    1.0,
                    edge ** 0.30
                    * (0.42 + min(0.58, peak_sum * 0.48))
                    * max(0.70, broken_ridge),
                )
                vertices.append(
                    (
                        nx * spec.radius * (1.12 + 0.05 * math.sin(phase)),
                        ny * spec.radius * (0.72 + 0.07 * math.cos(phase)),
                        -spec.height * 0.50 + spec.height * height_factor,
                    )
                )
        faces: list[tuple[int, ...]] = []
        for row in range(rows - 1):
            for column in range(columns - 1):
                lower_left = row * columns + column
                lower_right = lower_left + 1
                upper_left = lower_left + columns
                upper_right = upper_left + 1
                if (row + column + spec.seed) % 2:
                    faces.extend(
                        (
                            (lower_left, lower_right, upper_left),
                            (lower_right, upper_right, upper_left),
                        )
                    )
                else:
                    faces.extend(
                        (
                            (lower_left, lower_right, upper_right),
                            (lower_left, upper_right, upper_left),
                        )
                    )
        mesh = bpy.data.meshes.new(f"A21_MOUNTAIN_{part_name.replace('.', '_')}")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(terrain_material)
        old_mesh = obj.data
        obj.data = mesh
        obj["a21TerrainKind"] = "deterministic-asymmetric-multi-peak-alpine-heightfield"
        if old_mesh is not None and old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        mountain_mesh_count += 1

    # The aerostat is a pressure envelope rather than a faceted prop.  Keep
    # service rings and fins hard-edged, but smooth the three envelope shells.
    for obj in bpy.data.objects:
        part_name = obj.get("a21PartName")
        if part_name not in {
            "a20.hall.aerostat.nose",
            "a20.hall.aerostat.body",
            "a20.hall.aerostat.tail",
        } or obj.type != "MESH":
            continue
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj["a21EnvelopeShading"] = "smooth-pressure-envelope"

    # Remove inherited proof cameras/lights, then install the A21 art-directed rig.
    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    lighting_collection = bpy.data.collections.get("HB_kunren_70_LIGHTING")
    guide_collection = bpy.data.collections.get("HB_kunren_00_GUIDES")
    if lighting_collection is None or guide_collection is None:
        raise RuntimeError("reviewed builder did not create expected proof collections")

    def runtime_point(point: Point3) -> Vector:
        return Vector((point[0], -point[2], point[1]))

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("A21_WORLD")
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
    sky.sun_elevation = math.radians(28.0)
    sky.sun_rotation = math.radians(132.0)
    sky.air_density = 1.05
    if hasattr(sky, "dust_density"):
        sky.dust_density = 2.1
    background.inputs["Strength"].default_value = 0.20
    world_output = world_nodes.new("ShaderNodeOutputWorld")
    world_links.new(sky.outputs["Color"], background.inputs["Color"])
    world_links.new(background.outputs["Background"], world_output.inputs["Surface"])

    sun_data = bpy.data.lights.new("LGT_Kunren_A21_AlpineSun_DATA", "SUN")
    sun_data.energy = 4.0
    sun_data.angle = math.radians(1.15)
    sun_data.color = (1.0, 0.88, 0.76)
    sun = bpy.data.objects.new("LGT_Kunren_A21_AlpineSun", sun_data)
    sun.rotation_euler = (
        math.radians(44.0),
        math.radians(-7.0),
        math.radians(-38.0),
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
        "LGT_Kunren_A21_CoolSkyFill",
        (15.0, 105.0, -30.0),
        (0.0, 8.0, 10.0),
        (0.44, 0.62, 0.90),
        520.0,
        110.0,
    )
    add_area(
        "LGT_Kunren_A21_HangarPortalBounce",
        (-24.0, 24.0, -100.0),
        (-72.0, 18.0, -100.0),
        (1.0, 0.47, 0.20),
        1_100.0,
        24.0,
    )
    add_area(
        "LGT_Kunren_A21_CommandBounce",
        (74.0, 32.0, 40.0),
        (74.0, 18.0, 68.0),
        (1.0, 0.55, 0.25),
        620.0,
        20.0,
    )
    for index, x in enumerate((-48.0, -74.0, -100.0, -126.0)):
        add_point(
            f"LGT_Kunren_A21_HangarPractical_{index}",
            (x, 15.0 + (index % 2) * 9.0, -100.0 + (-18.0 if index % 2 else 18.0)),
            (1.0, 0.30, 0.08),
            650.0,
            3.2,
        )
    for index, location in enumerate(
        ((54.0, 18.0, 56.0), (74.0, 28.0, 55.0), (92.0, 38.0, 57.0))
    ):
        add_point(
            f"LGT_Kunren_A21_CommandPractical_{index}",
            location,
            (1.0, 0.25, 0.055),
            360.0,
            2.0,
        )

    def make_camera(spec: ReferenceCamera) -> Any:
        data = bpy.data.cameras.new(spec.name + "_DATA")
        data.lens = spec.lens_mm
        data.sensor_width = spec.sensor_width_mm
        data.dof.use_dof = False
        data.clip_start = 0.08
        data.clip_end = 2_000.0
        camera = bpy.data.objects.new(spec.name, data)
        guide_collection.objects.link(camera)
        camera.location = runtime_point(spec.location)
        direction = runtime_point(spec.target) - camera.location
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        camera["a21EyeHeightM"] = spec.eye_height_m
        camera["a21Intent"] = spec.intent
        return camera

    proof_views = (
        MAIN_REFERENCE_CAMERA,
        ReferenceCamera(
            "CAM_Kunren_A21_CheckpointRoute_1p65",
            (154.0, 1.65, -141.0),
            (55.0, 9.0, -34.0),
            25.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="occupied-checkpoint-split-height-service-route",
        ),
        COMMAND_HERO_CAMERA,
        ReferenceCamera(
            "CAM_Kunren_A21_CommandOblique_1p65",
            (146.0, 1.65, 5.0),
            (73.0, 25.0, 81.0),
            29.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="command-buttress-galleries-radar-and-threshold",
        ),
        ReferenceCamera(
            "CAM_Kunren_A21_HangarApproach_1p65",
            (-7.0, 1.65, -100.0),
            (-83.0, 24.0, -100.0),
            22.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="monumental-working-hangar-portal-and-aerostat",
        ),
        ReferenceCamera(
            "CAM_Kunren_A21_HangarInterior_1p65",
            (-45.0, 1.65, -108.0),
            (-112.0, 14.0, -96.0),
            23.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=1.65,
            intent="aerostat-docking-cranes-gantries-vehicles-and-depth",
        ),
        ReferenceCamera(
            "CAM_Kunren_A21_Aerial",
            (190.0, 108.0, -218.0),
            (-3.0, 14.0, 10.0),
            48.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=108.0,
            intent="compressed-connected-district-two-landmarks-and-alpine-boundary",
        ),
    )

    evidence_paths: list[str] = []
    evidence: list[dict[str, Any]] = []
    for index, spec in enumerate(proof_views, start=1):
        camera = make_camera(spec)
        scene.camera = camera
        filename = f"{index:02d}_{spec.name.removeprefix('CAM_Kunren_A21_')}.png"
        target = views_dir / filename
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        evidence_paths.append(str(target))
        evidence.append(
            {
                "path": str(target),
                "sha256": _sha256(target),
                "bytes": target.stat().st_size,
                "camera": asdict(spec),
            }
        )

    blend_path = output_dir / "kunren-a21-production-art.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    scorecard = producer_provisional_scorecard(evidence_paths)
    scorecard_path = output_dir / "producer-provisional-scorecard.json"
    scorecard_path.write_text(
        json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    evaluated_triangles = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in mesh_objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        evaluated_triangles += sum(max(1, len(poly.vertices) - 2) for poly in mesh.polygons)
        evaluated.to_mesh_clear()
    manifest = {
        "schema": "hibana-private-blender-proof-v1",
        "kitVersion": KIT_VERSION,
        "stageId": "kunren",
        "lod": plan.metadata["lod"],
        "blend": {
            "path": str(blend_path),
            "sha256": _sha256(blend_path),
            "bytes": blend_path.stat().st_size,
        },
        "views": evidence,
        "resolution": [1280, 720],
        "sourceReference": {
            "path": str(REFERENCE_PATH),
            "sha256": _sha256(REFERENCE_PATH),
        },
        "imageGenReference": {
            "path": str(imagegen_reference),
            "sha256": _sha256(imagegen_reference),
        },
        "planMetrics": plan.metadata["metrics"],
        "lodBudget": plan.metadata["lodBudget"],
        "mainReferenceCamera": plan.metadata["mainReferenceCamera"],
        "heroFrameMetrics": plan.metadata["heroFrameMetrics"],
        "proofCameraClearance": plan.metadata["proofCameraClearance"],
        "landmarkIdentityContract": plan.metadata["landmarkIdentityContract"],
        "authoritativeContracts": plan.metadata["authoritativeContracts"],
        "surfaceResponseContract": plan.metadata["surfaceResponseContract"],
        "lodContract": plan.metadata["lodContract"],
        "sceneAudit": {
            "meshObjects": len(mesh_objects),
            "evaluatedTriangles": evaluated_triangles,
            "asymmetricAlpineMountainMeshes": mountain_mesh_count,
            "materialCount": len(
                [
                    material
                    for material in bpy.data.materials
                    if material.name.startswith("A21_MAT_")
                ]
            ),
            "publicWrites": 0,
            "sourceWrites": 0,
            "manifestWrites": 0,
            "gitWrites": 0,
            "uiWrites": 0,
        },
        "reviewedBuilderScratch": {
            "directory": str(scratch_dir),
            "kitVersion": scratch_manifest["kitVersion"],
            "currentEvidence": False,
            "note": (
                "A20 construction scratch only; authoritative A21 proof is "
                "the top-level seven-view set"
            ),
        },
        "prebuildVisibleSceneBackup": str(prebuild_backup),
        "producerScorecard": str(scorecard_path),
        "producerProvisional": True,
        "producerScoreAccepted": False,
        "independentReviewerRequired": True,
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
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
        description="Build the isolated private Kunren A21 production-art proof"
    )
    parser.add_argument("--layout", type=Path, default=CANONICAL_LAYOUT_DEFAULT)
    parser.add_argument("--proof-dir", type=Path, default=PRIVATE_PROOF_DEFAULT)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--plan-json", type=Path)
    parser.add_argument("--no-proof", action="store_true")
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_blender_args(sys.argv if argv is None else argv)
    layout = load_authoritative_kunren_layout(args.layout)
    plan = make_kunren_reference_a21_plan(layout.stage, args.lod)
    if args.plan_json is not None:
        target = args.plan_json.expanduser().resolve()
        if str(target).startswith(str(REPO_ROOT.resolve())):
            raise ValueError("A21 plan JSON must stay outside the repository")
        if not str(target).startswith("/private/tmp/"):
            raise ValueError("A21 plan JSON must stay under /private/tmp")
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
    manifest = _run_blender_private_proof(plan, args.proof_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


__all__ = [
    "A21_LOD_BUDGETS",
    "A20_IMAGEGEN_REFERENCE_PATH",
    "COMMAND_HERO_CAMERA",
    "IMAGEGEN_REFERENCE_PATH",
    "IMAGEGEN_REFERENCE_SHA256",
    "KIT_VERSION",
    "MAIN_REFERENCE_CAMERA",
    "PRIVATE_PROOF_DEFAULT",
    "PRODUCER_PROVISIONAL_SCORES",
    "build_kunren_reference_a21",
    "emit_kunren_reference_a21_plan",
    "make_kunren_reference_a21_plan",
    "producer_provisional_scorecard",
]


if __name__ == "__main__":
    raise SystemExit(main())
elif "__file__" not in globals():
    __result__ = main()
