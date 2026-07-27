"""Kunren A20 private art rebuild, based on the immutable A19 plan.

A20 is intentionally isolated from ``build_all_stages.py`` and every public
asset path.  It preserves the authoritative Kunren bounds, landmark anchors,
approaches and spawns while rebuilding what the locked reference camera sees:

* LEFT: a stepped, occupied, castle-scale Command Bastion;
* RIGHT: a deep, operational Aerostat Vault Hangar;
* foreground/mid/far: checkpoint, retaining terraces, service settlement and
  real three-dimensional mountain layers.

Runtime coordinates are X/Z horizontal, Y up, metres.  The optional Blender
proof converts runtime Z to Blender -Y.

Connection map (declared before Blender geometry is emitted):

* command lower tiers -> canonical command floor: 0.30 m vertical overlap;
* command tier -> next tier/crown: 0.24-0.30 m vertical overlap;
* command buttress -> tier faces: 0.16 m endpoint/face overlap;
* command bridge -> crown towers: 0.14 m endpoint overlap;
* deep aperture frames -> recess planes: 0.08-0.10 m face overlap;
* hangar portal/rib feet -> canonical hall floor: 0.20 m foundation embed;
* adjacent portal/rib segments -> each other: 0.16 m knee overlap;
* hangar gantry posts -> floor: 0.18 m embed; beams -> posts: 0.14 m;
* aerostat service bands/fins/gondola -> envelope: 0.16-0.22 m overlap;
* terrace caps -> retaining bodies: 0.10 m seating overlap;
* stairs/ramps -> previous tread or terrace: 0.10-0.14 m overlap;
* carts, consoles, pallets and lights -> supporting floor/frame: >= 0.08 m.

All proof scores emitted here are producer-provisional and always NO-SHIP
pending an independent review at original resolution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import kunren_reference_a19 as a19  # noqa: E402
from tools.blender.stage_kits.kunren_reference_a18 import (  # noqa: E402
    ApproachSpec,
    BoxSpec,
    COMMAND_ID,
    HANGAR_ID,
    KunrenPlan,
    LODBudget,
    MeshBuilderProtocol,
    REFERENCE_IMAGE_SHA256,
    RockSpec,
    constraints_from_authoritative_layout,
    load_authoritative_kunren_layout,
)
from tools.blender.stage_kits.kunren_reference_a19 import (  # noqa: E402
    FIXED_SCORE_CATEGORIES,
    ReferenceCamera,
    camera_hero_frame_metrics,
)


KIT_VERSION = "kunren-reference-a20-v1"
PRIVATE_PROOF_DEFAULT = Path("/private/tmp/hibana-blender/a20-kunren-art-rebuild")
CANONICAL_LAYOUT_DEFAULT = Path("/private/tmp/hibana-blender/canonical-stage-layouts.json")
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/kunren-reference-v1.png"
IMAGEGEN_REFERENCE_PATH = PRIVATE_PROOF_DEFAULT / "concepts/kunren-a20-imagegen-reference.png"
IMAGEGEN_REFERENCE_SHA256 = "b1e5d1874918e03d018ac7d70c8d102a3615d8fee26f2c7807ee391975b9a144"
Point3 = tuple[float, float, float]


A20_LOD_BUDGETS: dict[int, LODBudget] = {
    0: LODBudget(1_850, 96_000, 12),
    1: LODBudget(1_060, 48_000, 12),
    2: LODBudget(500, 18_000, 12),
}


@dataclass(frozen=True)
class SightlineTreatment:
    prefix: str
    vertical_scale: float
    intent: str


# These are visual-only A19/A18 objects on the two hero rays.  Their canonical
# X/Z placement and identifiers remain intact; only the proof Y profile is
# compressed into occupied terraces.  Gameplay collision is untouched.
A20_SIGHTLINE_TREATMENTS = (
    SightlineTreatment("city.block.2.", 0.08, "foreground tower -> command-base terrace"),
    SightlineTreatment("city.block.3.", 0.24, "mid hangar block -> stepped command district"),
    SightlineTreatment("city.block.4.", 0.34, "far arena -> low occupied terrace"),
    SightlineTreatment("city.block.7.", 0.38, "far hangar -> low skyline shoulder"),
    SightlineTreatment("city.block.1.", 0.46, "hangar-edge bunker -> service terrace"),
    SightlineTreatment("a19.foreground.service-frame.", 0.28, "near occluder -> human-scale service bay"),
    SightlineTreatment("a19.foreground.pipe.", 0.42, "near pipe frame -> waist/overhead route detail"),
    SightlineTreatment("a19.route.retaining.right.0", 0.58, "near retaining wall -> readable route edge"),
)


# A slightly wider, fully-contained dual-hero composition.  It remains exactly
# 1.65 m above the runtime ground and does not move a gameplay spawn.
MAIN_REFERENCE_CAMERA = ReferenceCamera(
    name="CAM_Kunren_A20_ReferenceDual_1p65",
    location=(170.0, 1.65, -110.0),
    target=(-40.0, 8.0, 35.0),
    lens_mm=20.0,
    resolution_x=1280,
    resolution_y=720,
    eye_height_m=1.65,
    intent="imagegen-locked-dual-hero-left-command-right-hangar",
)

COMMAND_APPROACH_CAMERA = ReferenceCamera(
    "CAM_Kunren_A20_CommandHeroSouth_1p65",
    (80.0, 1.65, -10.0),
    (75.0, 22.0, 84.0),
    28.0,
    resolution_x=1280,
    resolution_y=720,
    intent="clear-south-command-hero-inspection",
)


PRODUCER_PROVISIONAL_SCORES: dict[str, float] = {
    "composition": 6.3,
    "hero silhouettes": 6.4,
    "architectural grammar": 6.2,
    "human scale": 5.8,
    "material realism": 5.5,
    "near/mid/far density": 6.0,
    "gameplay readability": 6.6,
    "props and environmental storytelling": 5.9,
    "lighting and atmosphere": 6.0,
    "reference identity": 6.2,
}


def _name_treatment(name: str) -> SightlineTreatment | None:
    for treatment in A20_SIGHTLINE_TREATMENTS:
        if name.startswith(treatment.prefix):
            return treatment
    return None


def _scale_point_y(point: Point3, scale: float) -> Point3:
    return point[0], point[1] * scale, point[2]


def _reshape_locked_camera_occluders(base: KunrenPlan) -> KunrenPlan:
    """Compress only visual Y profiles that occlude the locked hero rays."""

    def scale_for(name: str) -> float | None:
        treatment = _name_treatment(name)
        return treatment.vertical_scale if treatment else None

    boxes = tuple(
        replace(spec, y=spec.y * scale, h=max(0.02, spec.h * scale))
        if (scale := scale_for(spec.name)) is not None
        else spec
        for spec in base.boxes
    )
    beams = tuple(
        replace(
            spec,
            start=_scale_point_y(spec.start, scale),
            end=_scale_point_y(spec.end, scale),
        )
        if (scale := scale_for(spec.name)) is not None
        else spec
        for spec in base.beams
    )
    cylinders = tuple(
        replace(spec, y=spec.y * scale, height=max(0.02, spec.height * scale))
        if (scale := scale_for(spec.name)) is not None
        else spec
        for spec in base.cylinders
    )
    cylinders_between = tuple(
        replace(
            spec,
            start=_scale_point_y(spec.start, scale),
            end=_scale_point_y(spec.end, scale),
        )
        if (scale := scale_for(spec.name)) is not None
        else spec
        for spec in base.cylinders_between
    )
    panels = tuple(
        replace(
            spec,
            corners=tuple(_scale_point_y(point, scale) for point in spec.corners),
        )
        if (scale := scale_for(spec.name)) is not None
        else spec
        for spec in base.sloped_panels
    )
    rocks = tuple(
        replace(spec, y=spec.y * scale, height=max(0.02, spec.height * scale))
        if (scale := scale_for(spec.name)) is not None
        else spec
        for spec in base.rocks
    )
    connections = []
    for connection in base.connections:
        scales = [
            treatment.vertical_scale
            for name in (connection.parent, connection.child)
            if (treatment := _name_treatment(name)) is not None
        ]
        if scales:
            connection = replace(
                connection,
                actual_overlap_m=max(
                    connection.min_overlap_m,
                    connection.actual_overlap_m * min(scales),
                ),
            )
        connections.append(connection)
    return KunrenPlan(
        boxes=boxes,
        beams=beams,
        cylinders=cylinders,
        cylinders_between=cylinders_between,
        sloped_panels=panels,
        rocks=rocks,
        connections=tuple(connections),
        metadata={
            **base.metadata,
            "a20SightlineTreatments": [asdict(value) for value in A20_SIGHTLINE_TREATMENTS],
        },
    )


class _A20Assembler(a19._AddonAssembler):
    """A19 reviewed spec surface plus deterministic terrain rocks."""

    def rock(
        self,
        name: str,
        x: float,
        y: float,
        z: float,
        radius: float,
        height: float,
        key: str,
        segments: int,
        seed: int,
        *,
        role: str = "mountain-terrain",
    ) -> None:
        self._claim(name)
        if min(radius, height) <= 0.0 or segments < 4:
            raise ValueError(f"{name} has invalid rock dimensions")
        self.rocks.append(RockSpec(name, x, y, z, radius, height, key, segments, seed, role))


def _connect(
    a: _A20Assembler,
    name: str,
    parent: str,
    child: str,
    kind: str,
    axis: str,
    overlap: float,
    note: str = "",
) -> None:
    a.connect(name, parent, child, kind, axis, overlap, note)


def _add_command_bastion_rebuild(a: _A20Assembler, hero: Any, lod: int) -> None:
    """Build a readable stepped fortress inside the canonical hero envelope."""

    x, z = hero.cx, hero.cz

    # Split lower tier leaves the canonical 12 m west approach open.
    for side, offset in (("south", -16.5), ("north", 16.5)):
        lower = f"a20.cmd.tier.lower.{side}"
        a.box(
            lower,
            x + 1.0,
            4.0,
            z + offset,
            84.0,
            8.0,
            21.0,
            "wall_weathered",
            role="command-bastion-lower-tier",
        )
        _connect(a, f"contact.{lower}", "cmd.plinth", lower, "tier-foundation-overlap", "y", 0.30)

    tier_specs = (
        ("mid", x + 3.0, 15.0, z, 72.0, 14.0, 46.0, "wall_weathered"),
        ("upper", x + 5.0, 27.6, z + 1.0, 56.0, 12.0, 36.0, "wall"),
        ("keep", x + 7.0, 38.2, z + 1.0, 40.0, 10.0, 27.0, "wall_weathered"),
    )
    previous = "a20.cmd.tier.lower.south"
    for index, (label, cx, cy, cz, w, h, d, key) in enumerate(tier_specs):
        name = f"a20.cmd.tier.{label}"
        a.box(name, cx, cy, cz, w, h, d, key, role=f"command-bastion-{label}-tier")
        _connect(
            a,
            f"contact.{name}",
            previous,
            name,
            "stepped-tier-overlap",
            "y",
            0.30 if index == 0 else 0.24,
        )
        previous = name

    # A continuous south-east citadel face is the principal camera read.  It
    # binds the inherited small masses into one castle-scale silhouette rather
    # than another settlement cluster.
    a.box(
        "a20.cmd.hero-citadel.plinth",
        x + 7.0,
        10.0,
        z - 21.0,
        70.0,
        20.0,
        14.0,
        "wall_warm",
        role="command-hero-monolithic-plinth",
    )
    a.box(
        "a20.cmd.hero-citadel.keep",
        x + 9.0,
        28.0,
        z - 15.0,
        50.0,
        24.0,
        20.0,
        "wall_weathered",
        role="command-hero-monolithic-keep",
    )
    a.box(
        "a20.cmd.hero-citadel.crown",
        x + 11.0,
        43.0,
        z - 15.0,
        30.0,
        12.0,
        16.0,
        "wall",
        role="command-hero-castle-crown",
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.plinth",
        "a20.cmd.tier.lower.south",
        "a20.cmd.hero-citadel.plinth",
        "hero-plinth-tier-overlap",
        "plan",
        0.30,
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.keep",
        "a20.cmd.hero-citadel.plinth",
        "a20.cmd.hero-citadel.keep",
        "hero-keep-plinth-overlap",
        "y",
        0.30,
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.crown",
        "a20.cmd.hero-citadel.keep",
        "a20.cmd.hero-citadel.crown",
        "hero-crown-keep-overlap",
        "y",
        0.24,
    )
    shoulder_specs = (
        ("west", x - 29.0, 16.0, 38.0),
        ("east", x + 36.0, 14.0, 42.0),
    )
    shoulder_count = 2 if lod < 2 else 1
    for label, sx, sw, sh in shoulder_specs[:shoulder_count]:
        shoulder = f"a20.cmd.hero-citadel.shoulder.{label}"
        a.box(
            shoulder,
            sx,
            sh / 2.0,
            z - 16.0,
            sw,
            sh,
            20.0,
            "wall_weathered",
            role="command-hero-shoulder-tower",
        )
        cap = f"{shoulder}.cap"
        a.box(
            cap,
            sx,
            sh - 0.25,
            z - 16.0,
            sw + 1.6,
            0.50,
            21.6,
            "roof",
            role="command-hero-shoulder-cap",
        )
        _connect(a, f"contact.{shoulder}", "a20.cmd.hero-citadel.plinth", shoulder, "shoulder-plinth-overlap", "plan", 0.30)
        _connect(a, f"contact.{cap}", shoulder, cap, "shoulder-cap-seat", "y", 0.10)

    # Battered camera-facing armour planes distinguish the Bastion from the
    # rectilinear district kit and visibly transfer the upper keep to grade.
    a.panel(
        "a20.cmd.hero-citadel.battered-south-face",
        (
            (x - 40.0, 0.15, z - 28.0),
            (x + 43.0, 0.15, z - 28.0),
            (x + 33.0, 19.5, z - 20.0),
            (x - 31.0, 19.5, z - 20.0),
        ),
        0.82,
        "wall_weathered",
        role="command-hero-battered-armour-face",
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.battered-south-face",
        "a20.cmd.hero-citadel.plinth",
        "a20.cmd.hero-citadel.battered-south-face",
        "battered-face-plinth-seat",
        "z",
        0.18,
    )
    a.panel(
        "a20.cmd.hero-citadel.battered-east-face",
        (
            (x + 43.0, 0.15, z - 28.0),
            (x + 43.0, 0.15, z + 26.0),
            (x + 32.0, 19.5, z + 20.0),
            (x + 32.0, 19.5, z - 20.0),
        ),
        0.82,
        "wall_weathered",
        role="command-hero-battered-armour-face",
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.battered-east-face",
        "a20.cmd.hero-citadel.plinth",
        "a20.cmd.hero-citadel.battered-east-face",
        "battered-face-plinth-seat",
        "x",
        0.18,
    )

    hero_aperture_count = 5 if lod == 0 else 3 if lod == 1 else 1
    for index in range(hero_aperture_count):
        ax = x - 7.0 + index * (35.0 / max(1, hero_aperture_count - 1))
        recess = f"a20.cmd.hero-citadel.aperture.{index}"
        a.box(
            recess,
            ax,
            30.0 + (index % 2) * 4.0,
            z - 25.18,
            5.2,
            4.4,
            0.46,
            "wall_alt",
            role="command-hero-deep-occupied-aperture",
        )
        hood = f"{recess}.hood"
        a.box(
            hood,
            ax,
            32.45 + (index % 2) * 4.0,
            z - 25.58,
            6.4,
            0.40,
            1.25,
            "roof",
            role="command-hero-aperture-hood",
        )
        light = f"{recess}.warm-interior"
        a.box(
            light,
            ax,
            30.0 + (index % 2) * 4.0,
            z - 25.48,
            3.8,
            0.30,
            0.22,
            "accent",
            role="occupied-command-warm-interior",
        )
        _connect(a, f"contact.{recess}", "a20.cmd.hero-citadel.keep", recess, "hero-aperture-wall-seat", "z", 0.08)
        _connect(a, f"contact.{hood}", recess, hood, "hero-aperture-hood-seat", "z", 0.08)
        _connect(a, f"contact.{light}", recess, light, "hero-aperture-light-seat", "z", 0.08)

    # Massive lower command gate, armoured frame and load-bearing fins break
    # the formerly blank plinth at the human/combat scale.
    a.box(
        "a20.cmd.hero-citadel.lower-gate.deep-recess",
        x + 7.0,
        7.0,
        z - 28.35,
        18.0,
        12.0,
        0.62,
        "wall_alt",
        role="command-hero-lower-gate-deep-recess",
    )
    for side_name, gate_x in (("west", x - 3.0), ("east", x + 17.0)):
        frame = f"a20.cmd.hero-citadel.lower-gate.frame.{side_name}"
        a.box(
            frame,
            gate_x,
            7.0,
            z - 28.72,
            2.0,
            14.0,
            1.0,
            "trim",
            role="command-hero-lower-gate-armoured-frame",
        )
        _connect(a, f"contact.{frame}", "a20.cmd.hero-citadel.lower-gate.deep-recess", frame, "gate-frame-seat", "z", 0.10)
    a.box(
        "a20.cmd.hero-citadel.lower-gate.header",
        x + 7.0,
        13.6,
        z - 28.72,
        22.0,
        1.2,
        1.0,
        "wall_warm",
        role="command-hero-lower-gate-header",
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.lower-gate.header",
        "a20.cmd.hero-citadel.lower-gate.deep-recess",
        "a20.cmd.hero-citadel.lower-gate.header",
        "gate-header-seat",
        "z",
        0.10,
    )
    a.box(
        "a20.cmd.hero-citadel.lower-gate.status",
        x + 7.0,
        10.8,
        z - 29.30,
        12.0,
        0.42,
        0.22,
        "accent",
        role="occupied-command-gate-status-light",
    )
    _connect(
        a,
        "contact.a20.cmd.hero-citadel.lower-gate.status",
        "a20.cmd.hero-citadel.lower-gate.deep-recess",
        "a20.cmd.hero-citadel.lower-gate.status",
        "gate-status-seat",
        "z",
        0.08,
    )
    fin_count = 6 if lod == 0 else 4 if lod == 1 else 2
    for index in range(fin_count):
        fin_x = x - 30.0 + index * (68.0 / max(1, fin_count - 1))
        if x - 5.0 < fin_x < x + 19.0:
            continue
        fin = f"a20.cmd.hero-citadel.lower-fin.{index}"
        a.beam(
            fin,
            (fin_x, 0.20, z - 29.0),
            (fin_x, 19.0, z - 21.0),
            0.82,
            1.15,
            "wall_weathered",
            role="command-hero-lower-load-bearing-fin",
        )
        _connect(a, f"contact.{fin}", "a20.cmd.hero-citadel.plinth", fin, "lower-fin-plinth-seat", "endpoint", 0.16)
    stain_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index in range(stain_count):
        stain_x = x - 22.0 + index * (54.0 / max(1, stain_count - 1))
        stain = f"a20.cmd.hero-citadel.weather-stain.{index}"
        a.box(
            stain,
            stain_x,
            16.4,
            z - 28.18,
            3.2 + (index % 2) * 1.3,
            5.8,
            0.20,
            "wall_alt",
            role="command-facade-weather-and-runoff-stain",
        )
        _connect(a, f"contact.{stain}", "a20.cmd.hero-citadel.plinth", stain, "stain-facade-seat", "z", 0.08)

    crenel_count = 7 if lod == 0 else 4 if lod == 1 else 2
    for index in range(crenel_count):
        cx = x - 1.0 + index * (24.0 / max(1, crenel_count - 1))
        crenel = f"a20.cmd.hero-citadel.crown-crenel.{index}"
        a.box(
            crenel,
            cx,
            48.35,
            z - 15.0,
            2.6,
            1.30,
            3.6,
            "trim",
            role="command-crown-armoured-crenellation",
        )
        _connect(a, f"contact.{crenel}", "a20.cmd.hero-citadel.crown", crenel, "crenel-crown-seat", "y", 0.10)

    # Three asymmetric crown elements form a recognisable military crest.
    crown_specs = (
        ("south", x - 4.0, z - 8.5, 12.0, 8.0),
        ("central", x + 9.0, z + 1.0, 15.0, 9.0),
        ("north", x + 23.0, z + 9.0, 10.0, 7.0),
    )
    crown_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, (label, cx, cz, w, h) in enumerate(crown_specs[:crown_count]):
        crown = f"a20.cmd.crown.{label}"
        y = 49.0 - h / 2.0 - index * 0.35
        a.box(crown, cx, y, cz, w, h, 10.0, "wall_weathered", role="command-bastion-crown-tower")
        cap = f"{crown}.cap"
        cap_y = y + h / 2.0 - 0.20
        a.box(cap, cx, cap_y, cz, w + 1.4, 0.40, 11.4, "roof", role="command-crown-weather-cap")
        _connect(a, f"contact.{crown}", "a20.cmd.tier.keep", crown, "crown-keep-overlap", "y", 0.24)
        _connect(a, f"contact.{cap}", crown, cap, "crown-cap-seat", "y", 0.10)

    if lod < 2:
        bridge = "a20.cmd.crown.operations-bridge"
        a.beam(
            bridge,
            (x - 4.0, 45.2, z - 3.5),
            (x + 9.0, 45.0, z - 1.0),
            0.52,
            0.62,
            "trim",
            role="command-crown-occupied-bridge",
        )
        _connect(a, f"contact.{bridge}.south", "a20.cmd.crown.south", bridge, "bridge-tower-seat", "endpoint", 0.14)
        _connect(a, f"contact.{bridge}.central", "a20.cmd.crown.central", bridge, "bridge-tower-seat", "endpoint", 0.14)

    # Battered south/east buttresses visibly transfer the upper mass to grade.
    buttress_count = 6 if lod == 0 else 4 if lod == 1 else 2
    for index in range(buttress_count):
        bx = x - 32.0 + index * (64.0 / max(1, buttress_count - 1))
        name = f"a20.cmd.buttress.south.{index}"
        a.beam(
            name,
            (bx, 0.25, z - 27.1),
            (bx, 22.0, z - 18.0),
            1.15,
            1.35,
            "wall_weathered",
            role="castle-scale-battered-buttress",
        )
        _connect(a, f"contact.{name}", "a20.cmd.tier.mid", name, "buttress-tier-seat", "endpoint", 0.16)
    east_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index in range(east_count):
        bz = z - 17.0 + index * (34.0 / max(1, east_count - 1))
        name = f"a20.cmd.buttress.east.{index}"
        a.beam(
            name,
            (x + 43.2, 0.25, bz),
            (x + 31.0, 20.0, bz),
            1.05,
            1.25,
            "wall_weathered",
            role="castle-scale-battered-buttress",
        )
        _connect(a, f"contact.{name}", "a20.cmd.tier.mid", name, "buttress-tier-seat", "endpoint", 0.16)

    # Deep occupied south apertures: black depth plane, thick frame, hood,
    # warm status strip.  They read at the main camera distance.
    aperture_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(aperture_count):
        ax = x - 22.0 + index * (44.0 / max(1, aperture_count - 1))
        prefix = f"a20.cmd.aperture.south.{index}"
        recess = f"{prefix}.deep-recess"
        a.box(recess, ax, 17.0 + (index % 2) * 5.0, z - 23.25, 7.4, 5.2, 0.58, "wall_alt", role="deep-occupied-command-aperture")
        for suffix, fx, fy, fw, fh in (
            ("left", ax - 4.05, 17.0 + (index % 2) * 5.0, 0.70, 6.2),
            ("right", ax + 4.05, 17.0 + (index % 2) * 5.0, 0.70, 6.2),
            ("header", ax, 19.9 + (index % 2) * 5.0, 8.8, 0.64),
            ("sill", ax, 14.1 + (index % 2) * 5.0, 8.8, 0.46),
        ):
            frame = f"{prefix}.frame.{suffix}"
            a.box(frame, fx, fy, z - 23.62, fw, fh, 0.72, "trim", role="armored-aperture-frame")
            _connect(a, f"contact.{frame}", recess, frame, "aperture-frame-seat", "z", 0.10)
        strip = f"{prefix}.occupied-light"
        a.box(strip, ax, 17.0 + (index % 2) * 5.0, z - 24.03, 5.4, 0.32, 0.24, "accent", role="occupied-command-interior-light")
        _connect(a, f"contact.{strip}", recess, strip, "aperture-light-seat", "z", 0.08)

    # East-side operations galleries strengthen the oblique silhouette.
    gallery_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index in range(gallery_count):
        gy = 13.0 + index * 8.0
        gallery = f"a20.cmd.gallery.east.{index}"
        a.box(gallery, x + 31.8, gy, z + 1.0, 1.0, 3.0, 24.0 - index * 3.0, "trim", role="occupied-command-operations-gallery")
        _connect(a, f"contact.{gallery}", "a20.cmd.tier.mid", gallery, "gallery-wall-seat", "x", 0.12)
        if lod < 2:
            for post_index, gz in enumerate((z - 8.0, z, z + 8.0)):
                post = f"{gallery}.rail-post.{post_index}"
                a.beam(post, (x + 32.5, gy + 1.2, gz), (x + 32.5, gy + 2.35, gz), 0.07, 0.07, "accent", role="human-scale-command-safety-rail")
                _connect(a, f"contact.{post}", gallery, post, "rail-gallery-seat", "endpoint", 0.08)

    # Human-scale portal on the canonical west face, split around the approach.
    portal_x = x - hero.width / 2.0 + 0.35
    a.box(
        "a20.cmd.west-portal.deep-shadow",
        portal_x + 0.30,
        3.2,
        z,
        0.60,
        6.2,
        10.8,
        "wall_alt",
        role="command-approach-deep-portal",
        route_exempt=True,
    )
    for side, offset in (("south", -6.1), ("north", 6.1)):
        frame = f"a20.cmd.west-portal.frame.{side}"
        a.box(frame, portal_x - 0.18, 3.3, z + offset, 0.92, 6.6, 1.10, "trim", role="command-approach-armored-frame", route_exempt=True)
        _connect(a, f"contact.{frame}", "a20.cmd.west-portal.deep-shadow", frame, "portal-frame-seat", "x", 0.10)
    a.box("a20.cmd.west-portal.canopy", portal_x - 0.9, 7.0, z, 2.9, 0.70, 14.2, "roof", role="command-portal-weather-canopy", route_exempt=True)
    _connect(
        a,
        "contact.a20.cmd.west-portal.canopy",
        "a20.cmd.west-portal.deep-shadow",
        "a20.cmd.west-portal.canopy",
        "canopy-wall-seat",
        "x",
        0.10,
    )
    a.box(
        "a20.route.command-approach-surface",
        14.0,
        0.08,
        z,
        28.0,
        0.16,
        10.5,
        "road",
        role="canonical-command-approach-visual-surface",
        route_exempt=True,
    )
    _connect(
        a,
        "contact.a20.route.command-approach-surface",
        "a20.cmd.west-portal.deep-shadow",
        "a20.route.command-approach-surface",
        "approach-portal-surface-seat",
        "x",
        0.10,
    )
    for side_name, offset in (("south", -4.7), ("north", 4.7)):
        marking = f"a20.route.command-approach-marking.{side_name}"
        a.box(
            marking,
            14.0,
            0.19,
            z + offset,
            27.0,
            0.10,
            0.24,
            "wall_warm",
            role="weathered-command-approach-marking",
            route_exempt=True,
        )
        _connect(
            a,
            f"contact.{marking}",
            "a20.route.command-approach-surface",
            marking,
            "marking-road-seat",
            "y",
            0.08,
        )

    mast_count = 3 if lod == 0 else 2 if lod == 1 else 1
    mast_data = ((x - 4.0, z - 8.5, 48.2), (x + 9.0, z + 1.0, 47.8), (x + 23.0, z + 9.0, 47.0))
    for index, (mx, mz, start_y) in enumerate(mast_data[:mast_count]):
        mast = f"a20.cmd.crown.antenna.{index}.mast"
        a.beam(mast, (mx, start_y, mz), (mx, 48.9, mz), 0.10, 0.10, "trim", role="command-crown-antenna")
        parent = ("a20.cmd.crown.south", "a20.cmd.crown.central", "a20.cmd.crown.north")[index]
        _connect(a, f"contact.{mast}", parent, mast, "antenna-crown-seat", "endpoint", 0.10)


def _hangar_arch_profile(cz: float) -> tuple[tuple[float, float], ...]:
    return tuple(
        (cz + offset, height)
        for offset, height in (
            (-29.0, 0.4),
            (-29.0, 10.0),
            (-25.0, 22.0),
            (-18.0, 34.0),
            (-9.5, 45.0),
            (0.0, 52.5),
            (9.5, 45.0),
            (18.0, 34.0),
            (25.0, 22.0),
            (29.0, 10.0),
            (29.0, 0.4),
        )
    )


def _add_hangar_operational_rebuild(a: _A20Assembler, hero: Any, lod: int) -> None:
    """Create a thick portal, dark cavity, huge aerostat and live maintenance."""

    x, z = hero.cx, hero.cz
    east = x + hero.width / 2.0
    west = x - hero.width / 2.0

    # Deep cavity and traversable service floor.  The floor is explicitly
    # visual/route-exempt because TypeScript collision remains authoritative.
    a.box(
        "a20.hall.cavity.back-wall",
        west + 1.1,
        23.0,
        z,
        0.70,
        46.0,
        58.0,
        "wall_alt",
        role="hangar-deep-dark-cavity",
        route_exempt=True,
    )
    a.box(
        "a20.hall.cavity.floor",
        x,
        0.16,
        z,
        hero.width - 3.0,
        0.32,
        54.0,
        "road",
        role="hangar-operational-floor",
        route_exempt=True,
    )
    for index, offset in enumerate((-10.5, 10.5)):
        line = f"a20.hall.cavity.floor-marking.{index}"
        a.box(line, x, 0.35, z + offset, hero.width - 7.0, 0.10, 0.32, "accent", role="hangar-floor-marking", route_exempt=True)
        _connect(a, f"contact.{line}", "a20.hall.cavity.floor", line, "marking-floor-seat", "y", 0.08)

    # Thick repeated ribs reveal depth, not merely a front outline.
    stations = (
        (east - 0.8, "portal"),
        (east - 18.0, "near"),
        (east - 42.0, "mid"),
        (east - 70.0, "deep"),
        (west + 3.0, "back"),
    )
    station_count = 5 if lod == 0 else 3 if lod == 1 else 2
    profile = _hangar_arch_profile(z)
    for station_index, (station_x, label) in enumerate(stations[:station_count]):
        prior: str | None = None
        for segment_index, ((z0, y0), (z1, y1)) in enumerate(zip(profile, profile[1:])):
            if lod == 2 and segment_index % 2:
                continue
            rib = f"a20.hall.rib.{label}.{segment_index}"
            width = 1.65 if station_index == 0 else 0.72
            a.beam(
                rib,
                (station_x, y0, z0),
                (station_x, y1, z1),
                width,
                width,
                "wall_weathered" if station_index == 0 else "trim",
                role="hangar-depth-rib",
            )
            if prior is not None:
                _connect(a, f"contact.{rib}", prior, rib, "rib-knee-overlap", "endpoint", 0.16)
            prior = rib
        if station_index > 0:
            for side, rail_z in (("south", z - 28.4), ("north", z + 28.4)):
                rail = f"a20.hall.depth-rail.{label}.{side}"
                a.beam(
                    rail,
                    (station_x, 9.8, rail_z),
                    (stations[station_index - 1][0], 9.8, rail_z),
                    0.24,
                    0.30,
                    "trim",
                    role="hangar-longitudinal-depth-rail",
                )
                _connect(a, f"contact.{rail}", f"a20.hall.rib.{label}.0", rail, "depth-rail-rib-seat", "endpoint", 0.12)

    # Larger aerostat corrects A19's small capsule.  It remains wholly inside
    # the canonical hangar volume.
    body_segments = 24 if lod == 0 else 14 if lod == 1 else 8
    nose = "a20.hall.aerostat.nose"
    body = "a20.hall.aerostat.body"
    tail = "a20.hall.aerostat.tail"
    a.cylinder_between(nose, (east - 27.0, 29.0, z), (east - 36.0, 29.0, z), 1.2, "wall_cool", body_segments, end_radius=8.6, role="huge-maintained-aerostat")
    a.cylinder_between(body, (east - 36.0, 29.0, z), (east - 72.0, 29.0, z), 8.6, "wall_cool", body_segments, end_radius=8.6, role="huge-maintained-aerostat")
    a.cylinder_between(tail, (east - 72.0, 29.0, z), (east - 84.0, 29.0, z), 8.6, "wall_cool", body_segments, end_radius=1.0, role="huge-maintained-aerostat")
    _connect(a, "contact.a20.hall.aerostat.nose", body, nose, "aerostat-shell-overlap", "x", 0.22)
    _connect(a, "contact.a20.hall.aerostat.tail", body, tail, "aerostat-shell-overlap", "x", 0.22)

    band_positions = (east - 41.0, east - 53.0, east - 65.0)
    band_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, band_x in enumerate(band_positions[:band_count]):
        band = f"a20.hall.aerostat.service-band.{index}"
        a.cylinder_between(
            band,
            (band_x - 0.34, 29.0, z),
            (band_x + 0.34, 29.0, z),
            9.0,
            "wall_warm" if index == 1 else "trim",
            body_segments,
            role="aerostat-maintenance-band",
        )
        _connect(a, f"contact.{band}", body, band, "aerostat-band-overlap", "x", 0.18)

    a.box("a20.hall.aerostat.gondola", east - 55.0, 18.8, z, 17.0, 4.0, 6.2, "wall_weathered", role="occupied-aerostat-gondola")
    a.box("a20.hall.aerostat.gondola.window", east - 46.3, 19.2, z, 0.42, 1.8, 4.4, "wall_alt", role="aerostat-gondola-dark-window")
    _connect(a, "contact.a20.hall.aerostat.gondola", body, "a20.hall.aerostat.gondola", "gondola-envelope-seat", "y", 0.22)
    _connect(
        a,
        "contact.a20.hall.aerostat.gondola.window",
        "a20.hall.aerostat.gondola",
        "a20.hall.aerostat.gondola.window",
        "gondola-window-seat",
        "x",
        0.08,
    )
    if lod < 2:
        a.panel(
            "a20.hall.aerostat.fin.vertical",
            ((east - 73.0, 29.0, z), (east - 85.0, 29.0, z), (east - 81.0, 42.0, z), (east - 70.0, 35.0, z)),
            0.24,
            "wall_cool",
            role="aerostat-tail-fin",
        )
        a.panel(
            "a20.hall.aerostat.fin.lateral",
            ((east - 72.0, 29.0, z - 1.0), (east - 83.0, 29.0, z - 12.0), (east - 83.0, 29.0, z + 12.0), (east - 72.0, 29.0, z + 1.0)),
            0.24,
            "wall_cool",
            role="aerostat-tail-fin",
        )
        _connect(a, "contact.a20.hall.aerostat.fin.vertical", tail, "a20.hall.aerostat.fin.vertical", "tail-fin-seat", "plan", 0.16)
        _connect(a, "contact.a20.hall.aerostat.fin.lateral", tail, "a20.hall.aerostat.fin.lateral", "tail-fin-seat", "plan", 0.16)

    # Operational gantries and equipment remain outside the central 12 m lane.
    gantry_stations = (east - 15.0, east - 43.0, east - 72.0)
    gantry_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, gx in enumerate(gantry_stations[:gantry_count]):
        for side, gz in (("south", z - 19.0), ("north", z + 19.0)):
            post = f"a20.hall.gantry.{index}.post.{side}"
            a.beam(post, (gx, 0.20, gz), (gx, 15.5, gz), 0.30, 0.30, "trim", role="hangar-maintenance-gantry")
            _connect(a, f"contact.{post}", "a20.hall.cavity.floor", post, "gantry-floor-embed", "endpoint", 0.18)
        beam = f"a20.hall.gantry.{index}.crossbeam"
        a.beam(beam, (gx, 15.3, z - 19.0), (gx, 15.3, z + 19.0), 0.38, 0.44, "wall_warm", role="hangar-maintenance-gantry")
        _connect(a, f"contact.{beam}.south", f"a20.hall.gantry.{index}.post.south", beam, "gantry-beam-seat", "endpoint", 0.14)
        _connect(a, f"contact.{beam}.north", f"a20.hall.gantry.{index}.post.north", beam, "gantry-beam-seat", "endpoint", 0.14)

    # Continuous occupied catwalks, access stairs and safety rails make the
    # vault read as a maintained military workspace at human scale.
    catwalk_sides = (("south", z - 24.0), ("north", z + 24.0))
    catwalk_station_count = 7 if lod == 0 else 4 if lod == 1 else 1
    for side_name, catwalk_z in catwalk_sides:
        deck = f"a20.hall.catwalk.{side_name}.deck"
        a.box(
            deck,
            x,
            8.2,
            catwalk_z,
            hero.width - 14.0,
            0.55,
            3.6,
            "wall_cool",
            role="occupied-hangar-catwalk-deck",
        )
        _connect(a, f"contact.{deck}", "a20.hall.cavity.floor", deck, "catwalk-supported-over-floor", "y", 0.12)
        for index in range(catwalk_station_count):
            px = east - 8.0 - index * ((hero.width - 24.0) / max(1, catwalk_station_count - 1))
            support = f"a20.hall.catwalk.{side_name}.support.{index}"
            a.beam(
                support,
                (px, 0.20, catwalk_z),
                (px, 8.15, catwalk_z),
                0.22,
                0.22,
                "trim",
                role="hangar-catwalk-grounded-support",
            )
            _connect(a, f"contact.{support}.floor", "a20.hall.cavity.floor", support, "catwalk-support-floor-embed", "endpoint", 0.18)
            _connect(a, f"contact.{support}.deck", deck, support, "catwalk-support-deck-seat", "endpoint", 0.12)
            rail_post = f"a20.hall.catwalk.{side_name}.rail-post.{index}"
            inner_z = catwalk_z + (1.55 if side_name == "south" else -1.55)
            a.beam(
                rail_post,
                (px, 8.35, inner_z),
                (px, 10.1, inner_z),
                0.075,
                0.075,
                "accent",
                role="human-scale-hangar-safety-rail",
            )
            _connect(a, f"contact.{rail_post}", deck, rail_post, "rail-deck-seat", "endpoint", 0.08)
        rail_z = catwalk_z + (1.55 if side_name == "south" else -1.55)
        for rail_index, rail_y in enumerate((9.15, 10.0) if lod < 2 else (9.6,)):
            rail = f"a20.hall.catwalk.{side_name}.rail.{rail_index}"
            a.beam(
                rail,
                (west + 7.0, rail_y, rail_z),
                (east - 7.0, rail_y, rail_z),
                0.075,
                0.075,
                "accent",
                role="human-scale-hangar-safety-rail",
            )
            _connect(a, f"contact.{rail}", f"a20.hall.catwalk.{side_name}.rail-post.0", rail, "rail-post-weld", "plan", 0.08)

        step_count = 9 if lod == 0 else 5 if lod == 1 else 3
        previous_step = "a20.hall.cavity.floor"
        for step_index in range(step_count):
            sx = east - 9.0 - step_index * 0.82
            sy = 0.45 + step_index * (7.4 / max(1, step_count - 1))
            step = f"a20.hall.catwalk.{side_name}.access-step.{step_index}"
            a.box(
                step,
                sx,
                sy / 2.0,
                catwalk_z,
                1.15,
                sy,
                3.0,
                "trim",
                role="human-scale-hangar-access-stair",
            )
            _connect(a, f"contact.{step}", previous_step, step, "stair-tread-overlap", "plan", 0.10)
            previous_step = step

    # Overhead crane rails, bridge and hook occupy the upper void around the
    # aerostat without closing the portal.
    if lod < 2:
        for side_name, crane_z in (("south", z - 13.5), ("north", z + 13.5)):
            rail = f"a20.hall.overhead-crane.rail.{side_name}"
            a.beam(
                rail,
                (west + 8.0, 39.0, crane_z),
                (east - 9.0, 39.0, crane_z),
                0.34,
                0.42,
                "wall_warm",
                role="hangar-overhead-crane-rail",
            )
            _connect(a, f"contact.{rail}", "a20.hall.rib.mid.4", rail, "crane-rib-seat", "plan", 0.14)
        bridge_count = 2 if lod == 0 else 1
        for index, crane_x in enumerate((east - 32.0, east - 70.0)[:bridge_count]):
            bridge = f"a20.hall.overhead-crane.bridge.{index}"
            a.beam(
                bridge,
                (crane_x, 38.7, z - 13.5),
                (crane_x, 38.7, z + 13.5),
                0.42,
                0.48,
                "wall_warm",
                role="hangar-overhead-crane-bridge",
            )
            _connect(a, f"contact.{bridge}.south", "a20.hall.overhead-crane.rail.south", bridge, "crane-bridge-rail-seat", "endpoint", 0.14)
            _connect(a, f"contact.{bridge}.north", "a20.hall.overhead-crane.rail.north", bridge, "crane-bridge-rail-seat", "endpoint", 0.14)
            trolley = f"{bridge}.trolley"
            a.box(trolley, crane_x, 37.9, z + (4.0 if index else -4.0), 2.8, 1.2, 2.2, "trim", role="hangar-overhead-crane-trolley")
            _connect(a, f"contact.{trolley}", bridge, trolley, "trolley-bridge-seat", "y", 0.10)
            hook = f"{bridge}.hook-cable"
            a.beam(
                hook,
                (crane_x, 37.4, z + (4.0 if index else -4.0)),
                (crane_x, 22.0, z + (4.0 if index else -4.0)),
                0.07,
                0.07,
                "trim",
                role="hangar-overhead-crane-hook-cable",
            )
            _connect(a, f"contact.{hook}", trolley, hook, "hook-trolley-seat", "endpoint", 0.08)

    # Parked maintenance vehicles and forklifts make scale and operation
    # unmistakable while preserving the central aircraft-width lane.
    vehicle_specs = (
        (east - 23.0, z - 15.0, "tow-tractor"),
        (east - 46.0, z + 15.0, "maintenance-truck"),
        (east - 70.0, z - 15.0, "fuel-cart"),
        (east - 91.0, z + 15.0, "forklift"),
    )
    vehicle_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index, (vehicle_x, vehicle_z, vehicle_kind) in enumerate(vehicle_specs[:vehicle_count]):
        vehicle = f"a20.hall.vehicle.{index}.{vehicle_kind}"
        a.box(vehicle, vehicle_x, 1.35, vehicle_z, 6.6, 1.7, 3.2, "wall_cool", role="parked-hangar-military-vehicle")
        cabin = f"{vehicle}.cabin"
        a.box(cabin, vehicle_x + 1.45, 2.65, vehicle_z, 2.8, 1.8, 2.8, "wall_weathered", role="occupied-hangar-vehicle-cabin")
        window = f"{vehicle}.cabin-window"
        a.box(window, vehicle_x + 2.88, 2.85, vehicle_z, 0.28, 1.0, 2.0, "wall_alt", role="hangar-vehicle-dark-window")
        _connect(a, f"contact.{cabin}", vehicle, cabin, "vehicle-cabin-body-seat", "y", 0.12)
        _connect(a, f"contact.{window}", cabin, window, "vehicle-window-seat", "x", 0.08)
        for axle_index, axle_x in enumerate((vehicle_x - 2.0, vehicle_x + 2.0)):
            for side_name, wheel_z in (("south", vehicle_z - 1.55), ("north", vehicle_z + 1.55)):
                wheel = f"{vehicle}.wheel.{axle_index}.{side_name}"
                a.cylinder_between(
                    wheel,
                    (axle_x, 0.68, wheel_z - 0.30),
                    (axle_x, 0.68, wheel_z + 0.30),
                    0.58,
                    "trim",
                    12 if lod == 0 else 8,
                    role="hangar-vehicle-wheel",
                )
                _connect(a, f"contact.{wheel}", vehicle, wheel, "wheel-chassis-seat", "plan", 0.10)
        status = f"{vehicle}.service-light"
        a.box(status, vehicle_x + 3.42, 1.45, vehicle_z, 0.18, 0.34, 2.2, "accent", role="active-hangar-vehicle-light")
        _connect(a, f"contact.{status}", vehicle, status, "vehicle-light-seat", "x", 0.08)

    tank_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index in range(tank_count):
        tank_x = west + 16.0 + index * 18.0
        tank_z = z + (-21.0 if index % 2 == 0 else 21.0)
        tank = f"a20.hall.service-tank.{index}"
        a.cylinder(tank, tank_x, 3.1, tank_z, 1.65, 6.2, "wall_weathered", 16 if lod == 0 else 10, role="hangar-fluid-service-tank")
        _connect(a, f"contact.{tank}", "a20.hall.cavity.floor", tank, "tank-floor-seat", "y", 0.12)

    equipment_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(equipment_count):
        side = -1.0 if index % 2 == 0 else 1.0
        ex = east - 19.0 - (index // 2) * 22.0
        ez = z + side * 22.5
        equipment = f"a20.hall.equipment.{index}"
        a.box(equipment, ex, 2.25, ez, 8.0, 4.5, 4.2, "wall_weathered", role="hangar-operational-equipment-bank")
        a.box(f"{equipment}.service-face", ex + 4.12, 2.5, ez, 0.32, 2.8, 3.0, "wall_alt", role="hangar-equipment-dark-service-face")
        a.box(f"{equipment}.status", ex + 4.31, 3.1, ez, 0.18, 0.34, 2.2, "accent", role="hangar-equipment-active-status")
        _connect(a, f"contact.{equipment}", "a20.hall.cavity.floor", equipment, "equipment-floor-seat", "y", 0.12)
        _connect(a, f"contact.{equipment}.face", equipment, f"{equipment}.service-face", "equipment-face-seat", "x", 0.08)
        _connect(a, f"contact.{equipment}.status", f"{equipment}.service-face", f"{equipment}.status", "status-face-seat", "x", 0.08)

    light_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(light_count):
        lx = east - 8.0 - index * ((hero.width - 20.0) / max(1, light_count - 1))
        lz = z - 11.5 if index % 2 == 0 else z + 11.5
        light = f"a20.hall.worklight.{index}"
        a.box(light, lx, 17.2, lz, 2.8, 0.28, 0.42, "accent", role="active-hangar-worklight")
        parent = f"a20.hall.gantry.{min(index // 3, gantry_count - 1)}.crossbeam"
        _connect(a, f"contact.{light}", parent, light, "worklight-gantry-seat", "y", 0.08)


def _add_terraced_world_and_story(a: _A20Assembler, lod: int) -> None:
    """Add grounded near/mid/far terrain, settlement and human-scale story."""

    # A dark, explicitly visual approach surface replaces the empty proof
    # foreground and points toward the two heroes.  It does not alter runtime
    # collision.  Continuous shoulders survive every LOD; centre dashes reduce.
    road_start = (178.0, -116.0)
    road_end = (18.0, 18.0)
    road_dx, road_dz = road_end[0] - road_start[0], road_end[1] - road_start[1]
    road_length = math.hypot(road_dx, road_dz)
    road_ux, road_uz = road_dx / road_length, road_dz / road_length
    road_nx, road_nz = -road_uz, road_ux
    road_x = (road_start[0] + road_end[0]) / 2.0
    road_z = (road_start[1] + road_end[1]) / 2.0
    road_yaw = math.atan2(road_dz, road_dx)
    a.box(
        "a20.route.hero-approach-road",
        road_x,
        0.08,
        road_z,
        road_length,
        0.16,
        21.0,
        "road",
        yaw=road_yaw,
        role="visual-first-person-asphalt-approach",
        route_exempt=True,
    )
    _connect(
        a,
        "contact.a20.route.hero-approach-road",
        "a19.route.ramp.deck",
        "a20.route.hero-approach-road",
        "road-ramp-surface-overlap",
        "y",
        0.10,
    )
    for side_name, lateral in (("left", 8.7), ("right", -8.7)):
        stripe = f"a20.route.hero-approach-road.shoulder.{side_name}"
        a.box(
            stripe,
            road_x + road_nx * lateral,
            0.19,
            road_z + road_nz * lateral,
            road_length - 5.0,
            0.10,
            0.32,
            "wall_warm",
            yaw=road_yaw,
            role="weathered-route-shoulder-marking",
            route_exempt=True,
        )
        _connect(
            a,
            f"contact.{stripe}",
            "a20.route.hero-approach-road",
            stripe,
            "marking-road-seat",
            "y",
            0.08,
        )
    dash_count = 10 if lod == 0 else 5 if lod == 1 else 2
    for index in range(dash_count):
        t = 0.08 + index * (0.82 / max(1, dash_count - 1))
        dash = f"a20.route.hero-approach-road.center-dash.{index}"
        a.box(
            dash,
            road_start[0] + road_ux * road_length * t,
            0.19,
            road_start[1] + road_uz * road_length * t,
            5.2,
            0.10,
            0.30,
            "wall_warm",
            yaw=road_yaw,
            role="weathered-route-centre-marking",
            route_exempt=True,
        )
        _connect(
            a,
            f"contact.{dash}",
            "a20.route.hero-approach-road",
            dash,
            "marking-road-seat",
            "y",
            0.08,
        )

    def road_point(t: float, lateral: float = 0.0) -> tuple[float, float]:
        return (
            road_start[0] + road_ux * road_length * t + road_nx * lateral,
            road_start[1] + road_uz * road_length * t + road_nz * lateral,
        )

    # A second, camera-aligned defensive checkpoint and staffed logistics
    # cluster occupy the road edges, replacing the empty lower frame while
    # retaining an 11 m central traversal lane.
    checkpoint_t = 0.38
    checkpoint_posts: dict[str, tuple[float, float]] = {}
    for side_name, lateral in (("left", 11.5), ("right", -11.5)):
        px, pz = road_point(checkpoint_t, lateral)
        checkpoint_posts[side_name] = (px, pz)
        base = f"a20.checkpoint.hero-road.base.{side_name}"
        post = f"a20.checkpoint.hero-road.post.{side_name}"
        a.box(base, px, 0.40, pz, 1.8, 0.80, 1.8, "obstacle", yaw=road_yaw, role="grounded-checkpoint-blast-base", route_exempt=True)
        a.beam(post, (px, 0.30, pz), (px, 7.2, pz), 0.28, 0.28, "trim", role="armoured-checkpoint-gantry-post")
        _connect(a, f"contact.{post}", base, post, "checkpoint-post-base-seat", "endpoint", 0.18)
        signal = f"a20.checkpoint.hero-road.signal.{side_name}"
        a.box(signal, px, 4.9, pz, 0.62, 0.88, 0.48, "accent", yaw=road_yaw, role="active-checkpoint-signal", route_exempt=True)
        _connect(a, f"contact.{signal}", post, signal, "checkpoint-signal-post-seat", "plan", 0.08)
    crossbeam = "a20.checkpoint.hero-road.crossbeam"
    a.beam(
        crossbeam,
        (checkpoint_posts["left"][0], 7.0, checkpoint_posts["left"][1]),
        (checkpoint_posts["right"][0], 7.0, checkpoint_posts["right"][1]),
        0.42,
        0.50,
        "wall_warm",
        role="armoured-checkpoint-overhead-gantry",
    )
    _connect(a, f"contact.{crossbeam}.left", "a20.checkpoint.hero-road.post.left", crossbeam, "gantry-post-weld", "endpoint", 0.14)
    _connect(a, f"contact.{crossbeam}.right", "a20.checkpoint.hero-road.post.right", crossbeam, "gantry-post-weld", "endpoint", 0.14)

    booth_x, booth_z = road_point(checkpoint_t - 0.04, 15.2)
    a.box("a20.checkpoint.hero-road.guard-booth", booth_x, 1.8, booth_z, 5.0, 3.6, 4.2, "wall_weathered", yaw=road_yaw, role="occupied-checkpoint-guard-booth", route_exempt=True)
    a.box("a20.checkpoint.hero-road.guard-booth.window", booth_x - road_nx * 2.18, 2.25, booth_z - road_nz * 2.18, 3.2, 1.45, 0.36, "wall_alt", yaw=road_yaw, role="occupied-checkpoint-dark-window", route_exempt=True)
    a.box("a20.checkpoint.hero-road.guard-booth.roof", booth_x, 3.82, booth_z, 5.8, 0.44, 5.0, "roof", yaw=road_yaw, role="checkpoint-weather-roof", route_exempt=True)
    _connect(a, "contact.a20.checkpoint.hero-road.guard-booth.window", "a20.checkpoint.hero-road.guard-booth", "a20.checkpoint.hero-road.guard-booth.window", "booth-window-seat", "plan", 0.08)
    _connect(a, "contact.a20.checkpoint.hero-road.guard-booth.roof", "a20.checkpoint.hero-road.guard-booth", "a20.checkpoint.hero-road.guard-booth.roof", "booth-roof-seat", "y", 0.10)

    barrier_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(barrier_count):
        t = 0.10 + index * (0.38 / max(1, barrier_count - 1))
        lateral = 10.4 if index % 2 == 0 else -10.4
        bx, bz = road_point(t, lateral)
        barrier = f"a20.checkpoint.hero-road.blast-barrier.{index}"
        a.box(barrier, bx, 0.58, bz, 4.2, 1.16, 1.0, "obstacle", yaw=road_yaw, role="foreground-military-blast-barrier", route_exempt=True)
        _connect(a, f"contact.{barrier}", "a20.route.hero-approach-road", barrier, "barrier-road-seat", "y", 0.08)

    road_vehicle_specs = ((0.17, 15.0, "apc"), (0.27, -15.0, "signals-truck"))
    road_vehicle_count = 2 if lod == 0 else 1 if lod == 1 else 0
    for index, (t, lateral, vehicle_kind) in enumerate(road_vehicle_specs[:road_vehicle_count]):
        vx, vz = road_point(t, lateral)
        vehicle = f"a20.story.foreground-vehicle.{index}.{vehicle_kind}"
        a.box(vehicle, vx, 1.35, vz, 7.2, 1.8, 3.4, "wall_cool", yaw=road_yaw, role="parked-foreground-military-vehicle", route_exempt=True)
        cabin = f"{vehicle}.cabin"
        a.box(cabin, vx + road_ux * 1.7, 2.75, vz + road_uz * 1.7, 3.0, 2.0, 3.0, "wall_weathered", yaw=road_yaw, role="foreground-vehicle-armoured-cabin", route_exempt=True)
        window = f"{vehicle}.window"
        a.box(window, vx + road_ux * 3.25, 2.95, vz + road_uz * 3.25, 0.30, 1.1, 2.1, "wall_alt", yaw=road_yaw, role="foreground-vehicle-dark-window", route_exempt=True)
        _connect(a, f"contact.{cabin}", vehicle, cabin, "vehicle-cabin-body-seat", "y", 0.12)
        _connect(a, f"contact.{window}", cabin, window, "vehicle-window-seat", "plan", 0.08)
        for axle_index, axle_progress in enumerate((-2.2, 2.2)):
            axle_x = vx + road_ux * axle_progress
            axle_z = vz + road_uz * axle_progress
            for side_name, side in (("left", -1.65), ("right", 1.65)):
                wx = axle_x + road_nx * side
                wz = axle_z + road_nz * side
                wheel = f"{vehicle}.wheel.{axle_index}.{side_name}"
                a.cylinder_between(
                    wheel,
                    (wx - road_nx * 0.28, 0.68, wz - road_nz * 0.28),
                    (wx + road_nx * 0.28, 0.68, wz + road_nz * 0.28),
                    0.62,
                    "trim",
                    12 if lod == 0 else 8,
                    role="foreground-vehicle-wheel",
                )
                _connect(a, f"contact.{wheel}", vehicle, wheel, "wheel-chassis-seat", "plan", 0.10)

    # Mid settlement occupies the deliberate gap between hero silhouettes.
    settlement = (
        (-18.0, 48.0, 22.0, 17.0, 14.0),
        (-48.0, 64.0, 18.0, 23.0, 13.0),
        (8.0, 74.0, 20.0, 28.0, 16.0),
        (-68.0, 98.0, 26.0, 19.0, 15.0),
        (20.0, 118.0, 22.0, 26.0, 14.0),
        (-24.0, 130.0, 28.0, 32.0, 17.0),
        (126.0, 42.0, 16.0, 24.0, 13.0),
        (-142.0, 18.0, 22.0, 26.0, 14.0),
    )
    building_count = 8 if lod == 0 else 5 if lod == 1 else 3
    for index, (bx, bz, w, h, d) in enumerate(settlement[:building_count]):
        base = f"a20.district.terrace-building.{index}"
        a.box(base, bx, h * 0.28, bz, w, h * 0.56, d, "wall_weathered", role="dense-terraced-support-building", route_exempt=True)
        upper = f"{base}.upper"
        a.box(upper, bx + (2.0 if index % 2 else -2.0), h * 0.73, bz, w * 0.72, h * 0.42, d * 0.78, "wall", role="dense-terraced-support-building", route_exempt=True)
        cap = f"{base}.cap"
        a.box(cap, bx, h + 0.18, bz, w * 0.82, 0.36, d * 0.88, "roof", role="dedicated-kunren-roof-profile", route_exempt=True)
        _connect(a, f"contact.{upper}", base, upper, "building-tier-overlap", "y", 0.20)
        _connect(a, f"contact.{cap}", upper, cap, "roof-seat", "y", 0.10)
        recess_count = 3 if lod == 0 else 1
        for recess_index in range(recess_count):
            recess = f"{base}.recess.{recess_index}"
            rx = bx - w * 0.24 + recess_index * w * 0.24
            a.box(recess, rx, h * 0.30, bz - d / 2.0 - 0.16, w * 0.15, 2.8, 0.34, "wall_alt", role="occupied-district-deep-aperture", route_exempt=True)
            _connect(a, f"contact.{recess}", base, recess, "district-recess-seat", "z", 0.08)

    # A perimeter of tall, varied support blocks creates a dense settlement
    # while preserving the central roads/plaza and the two hero identities.
    dense_settlement = (
        (-154.0, -6.0, 18.0, 25.0, 14.0, 0.00),
        (-138.0, 25.0, 22.0, 31.0, 16.0, 0.08),
        (-116.0, 53.0, 19.0, 27.0, 15.0, -0.06),
        (-96.0, 118.0, 24.0, 36.0, 17.0, 0.05),
        (-66.0, 146.0, 22.0, 30.0, 15.0, -0.08),
        (-34.0, 158.0, 24.0, 39.0, 18.0, 0.04),
        (2.0, 160.0, 20.0, 33.0, 15.0, -0.04),
        (38.0, 158.0, 25.0, 42.0, 18.0, 0.06),
        (76.0, 151.0, 22.0, 35.0, 16.0, -0.06),
        (112.0, 137.0, 24.0, 38.0, 18.0, 0.04),
        (139.0, 111.0, 21.0, 30.0, 15.0, -0.08),
        (151.0, 78.0, 23.0, 36.0, 17.0, 0.05),
        (154.0, 43.0, 19.0, 28.0, 14.0, -0.04),
        (-151.0, 75.0, 20.0, 29.0, 15.0, 0.06),
        (-128.0, 105.0, 23.0, 34.0, 17.0, -0.05),
        (-8.0, 9.0, 18.0, 18.0, 14.0, 0.04),
        (18.0, 28.0, 17.0, 21.0, 13.0, -0.05),
        (-38.0, 31.0, 19.0, 23.0, 15.0, 0.06),
        (42.0, 57.0, 16.0, 18.0, 13.0, -0.04),
        (-61.0, 79.0, 18.0, 24.0, 14.0, 0.05),
    )
    dense_count = 20 if lod == 0 else 12 if lod == 1 else 4
    for index, (bx, bz, w, h, d, yaw) in enumerate(dense_settlement[:dense_count]):
        base = f"a20.district.dense-block.{index}"
        lower_h = h * 0.46
        a.box(
            base,
            bx,
            lower_h / 2.0,
            bz,
            w,
            lower_h,
            d,
            "wall_weathered",
            yaw=yaw,
            role="kunren-dense-terraced-district-lower",
            route_exempt=True,
        )
        mid = f"{base}.mid"
        a.box(
            mid,
            bx + (1.3 if index % 2 else -1.3),
            lower_h + h * 0.24,
            bz,
            w * 0.78,
            h * 0.48,
            d * 0.82,
            "wall",
            yaw=yaw,
            role="kunren-dense-terraced-district-mid",
            route_exempt=True,
        )
        crown = f"{base}.crown"
        crown_h = h * 0.22
        a.box(
            crown,
            bx + (-1.8 if index % 3 else 1.8),
            h - crown_h / 2.0,
            bz + (0.8 if index % 2 else -0.8),
            w * 0.46,
            crown_h,
            d * 0.58,
            "wall_cool" if index % 3 == 0 else "wall_weathered",
            yaw=yaw,
            role="kunren-dedicated-facade-crown",
            route_exempt=True,
        )
        cap = f"{base}.roof-cap"
        a.box(
            cap,
            bx,
            h + 0.22,
            bz,
            w * 0.72,
            0.44,
            d * 0.74,
            "roof",
            yaw=yaw,
            role="kunren-dedicated-stepped-roof-profile",
            route_exempt=True,
        )
        _connect(a, f"contact.{mid}", base, mid, "district-tier-overlap", "y", 0.20)
        _connect(a, f"contact.{crown}", mid, crown, "district-crown-overlap", "y", 0.16)
        _connect(a, f"contact.{cap}", crown, cap, "district-roof-seat", "y", 0.10)
        if lod < 2:
            service = f"{base}.service-stack"
            a.box(
                service,
                bx + w * 0.38,
                h * 0.38,
                bz - d * 0.34,
                2.2,
                h * 0.56,
                2.2,
                "trim",
                yaw=yaw,
                role="kunren-district-service-stack",
                route_exempt=True,
            )
            _connect(a, f"contact.{service}", base, service, "service-stack-wall-seat", "plan", 0.10)
        if lod == 0:
            for aperture_index in range(2):
                aperture = f"{base}.occupied-aperture.{aperture_index}"
                aperture_x = bx - w * 0.20 + aperture_index * w * 0.40
                a.box(
                    aperture,
                    aperture_x,
                    lower_h * 0.55,
                    bz - d / 2.0 - 0.18,
                    w * 0.16,
                    2.6,
                    0.36,
                    "wall_alt",
                    yaw=yaw,
                    role="occupied-district-deep-aperture",
                    route_exempt=True,
                )
                _connect(a, f"contact.{aperture}", base, aperture, "district-aperture-seat", "z", 0.08)
        if lod < 2:
            variant = index % 4
            if variant == 0:
                for side_index, side in enumerate((-1.0, 1.0)):
                    tower = f"{base}.variant-shoulder.{side_index}"
                    a.box(
                        tower,
                        bx + side * w * 0.34,
                        h * 0.62,
                        bz,
                        w * 0.26,
                        h * 0.76,
                        d * 0.62,
                        "wall_weathered",
                        yaw=yaw,
                        role="kunren-district-twin-shoulder-silhouette",
                        route_exempt=True,
                    )
                    _connect(a, f"contact.{tower}", base, tower, "shoulder-building-overlap", "plan", 0.14)
            elif variant == 1:
                for side_name, side in (("west", -1.0), ("east", 1.0)):
                    roof = f"{base}.variant-pitched-roof.{side_name}"
                    a.panel(
                        roof,
                        (
                            (bx, h + 3.6, bz - d * 0.38),
                            (bx + side * w * 0.40, h + 0.35, bz - d * 0.38),
                            (bx + side * w * 0.40, h + 0.35, bz + d * 0.38),
                            (bx, h + 3.6, bz + d * 0.38),
                        ),
                        0.30,
                        "roof",
                        role="kunren-district-pitched-armour-roof",
                    )
                    _connect(a, f"contact.{roof}", crown, roof, "pitched-roof-crown-seat", "y", 0.10)
            elif variant == 2:
                for side_index, side in enumerate((-1.0, 1.0)):
                    turret = f"{base}.variant-split-crown.{side_index}"
                    a.box(
                        turret,
                        bx + side * w * 0.20,
                        h + 2.4,
                        bz,
                        w * 0.22,
                        4.8,
                        d * 0.42,
                        "wall_cool",
                        yaw=yaw,
                        role="kunren-district-split-roof-crown",
                        route_exempt=True,
                    )
                    _connect(a, f"contact.{turret}", crown, turret, "split-crown-seat", "y", 0.12)
            else:
                mast = f"{base}.variant-comms-mast"
                a.beam(
                    mast,
                    (bx, h - 0.10, bz),
                    (bx, h + 7.5, bz),
                    0.09,
                    0.09,
                    "trim",
                    role="kunren-district-comms-mast",
                )
                crossbar = f"{base}.variant-comms-crossbar"
                a.beam(
                    crossbar,
                    (bx - 2.2, h + 5.8, bz),
                    (bx + 2.2, h + 5.8, bz),
                    0.07,
                    0.07,
                    "trim",
                    role="kunren-district-comms-array",
                )
                _connect(a, f"contact.{mast}", crown, mast, "mast-roof-seat", "endpoint", 0.10)
                _connect(a, f"contact.{crossbar}", mast, crossbar, "mast-crossbar-weld", "plan", 0.08)

    # Grounded terraces and retaining walls support the settlement.
    terraces = (
        (-34.0, 0.9, 50.0, 74.0, 1.8, 34.0),
        (-28.0, 2.0, 102.0, 54.0, 4.0, 18.0),
        (-16.0, 3.5, 124.0, 116.0, 7.0, 25.0),
        (126.0, 1.4, 62.0, 54.0, 2.8, 38.0),
        (-136.0, 1.8, 30.0, 64.0, 3.6, 34.0),
    )
    terrace_count = 5 if lod == 0 else 4 if lod == 1 else 3
    for index, (tx, ty, tz, w, h, d) in enumerate(terraces[:terrace_count]):
        terrace = f"a20.terrain.terrace.{index}"
        a.box(terrace, tx, ty, tz, w, h, d, "terrain", role="grounded-mountain-terrace", route_exempt=True)
        wall = f"{terrace}.retaining"
        a.box(wall, tx, h + 0.4, tz - d / 2.0 + 0.5, w, max(0.8, h * 0.55), 1.0, "wall_weathered", role="terrace-retaining-structure", route_exempt=True)
        cap = f"{wall}.cap"
        a.box(cap, tx, h + max(0.8, h * 0.55) / 2.0 + 0.55, tz - d / 2.0 + 0.5, w + 0.4, 0.30, 1.4, "trim", role="retaining-weather-cap", route_exempt=True)
        _connect(a, f"contact.{wall}", terrace, wall, "retaining-terrain-overlap", "y", 0.16)
        _connect(a, f"contact.{cap}", wall, cap, "retaining-cap-seat", "y", 0.10)

    # Real three-dimensional mountain skyline; no raster/cylindrical matte.
    mountain_specs = (
        (-205.0, 178.0, 68.0, 92.0, 101),
        (-142.0, 206.0, 76.0, 118.0, 113),
        (-64.0, 222.0, 82.0, 132.0, 127),
        (22.0, 226.0, 86.0, 142.0, 139),
        (112.0, 202.0, 78.0, 122.0, 151),
        (194.0, 164.0, 68.0, 96.0, 163),
        (-228.0, 92.0, 54.0, 74.0, 173),
        (220.0, 82.0, 52.0, 70.0, 181),
    )
    mountain_count = 8 if lod == 0 else 6 if lod == 1 else 4
    mountain_segments = 16 if lod == 0 else 10 if lod == 1 else 6
    for index, (mx, mz, radius, height, seed) in enumerate(mountain_specs[:mountain_count]):
        a.rock(
            f"a20.terrain.mountain.{index}",
            mx,
            -1.0,
            mz,
            radius,
            height,
            "terrain",
            mountain_segments,
            seed,
            role="layered-rugged-mountain-silhouette",
        )

    # Human-scale route story: sentry position, pallets, comms cabinet, lights.
    prop_count = 6 if lod == 0 else 3 if lod == 1 else 2
    for index in range(prop_count):
        px = 128.0 - index * 8.5
        pz = -142.0 + (index % 2) * 15.0
        pallet = f"a20.story.resupply-pallet.{index}"
        a.box(pallet, px, 0.12, pz, 3.2, 0.24, 2.4, "wood", role="grounded-resupply-pallet", route_exempt=True)
        crate = f"{pallet}.crate"
        a.box(crate, px, 0.85, pz, 2.3, 1.45, 1.7, "obstacle", role="military-resupply-crate", route_exempt=True)
        _connect(a, f"contact.{crate}", pallet, crate, "crate-pallet-seat", "y", 0.10)

    if lod < 2:
        a.box("a20.story.comms-cabinet", 118.0, 1.7, -111.0, 3.0, 3.4, 2.4, "wall_cool", role="active-route-comms-cabinet", route_exempt=True)
        a.box("a20.story.comms-cabinet.face", 116.42, 1.8, -111.0, 0.24, 2.2, 1.6, "wall_alt", role="comms-cabinet-service-face", route_exempt=True)
        a.box("a20.story.comms-cabinet.status", 116.26, 2.5, -111.0, 0.18, 0.32, 1.1, "accent", role="active-route-status-light", route_exempt=True)
        _connect(a, "contact.a20.story.comms-cabinet.face", "a20.story.comms-cabinet", "a20.story.comms-cabinet.face", "cabinet-face-seat", "x", 0.08)
        _connect(a, "contact.a20.story.comms-cabinet.status", "a20.story.comms-cabinet.face", "a20.story.comms-cabinet.status", "status-face-seat", "x", 0.08)


def _estimated_triangles(plan: KunrenPlan) -> int:
    total = 12 * (len(plan.boxes) + len(plan.beams) + len(plan.sloped_panels))
    total += sum(4 * spec.segments for spec in plan.cylinders)
    total += sum(4 * spec.segments for spec in plan.cylinders_between)
    total += sum(8 * spec.segments - 4 for spec in plan.rocks)
    return total


def camera_solid_hits(plan: KunrenPlan, camera: ReferenceCamera) -> tuple[str, ...]:
    """Return solid plan boxes containing the 1.65 m camera point."""

    px, py, pz = camera.location
    hits: list[str] = []
    for spec in plan.boxes:
        if spec.h <= 0.30:
            continue
        dx, dz = px - spec.x, pz - spec.z
        cosine, sine = math.cos(-spec.yaw), math.sin(-spec.yaw)
        local_x = dx * cosine - dz * sine
        local_z = dx * sine + dz * cosine
        if (
            abs(local_x) <= spec.w / 2.0
            and abs(local_z) <= spec.d / 2.0
            and abs(py - spec.y) <= spec.h / 2.0
        ):
            hits.append(spec.name)
    return tuple(hits)


def _validate_a20(
    additions: _A20Assembler,
    constraints: Any,
    budget: LODBudget,
    merged: KunrenPlan,
) -> dict[str, Any]:
    names = set(merged.names)
    if len(names) != merged.primitive_count:
        raise ValueError("A20 plan contains duplicate names")
    for connection in merged.connections:
        missing = {connection.parent, connection.child} - names
        if missing:
            raise ValueError(f"{connection.name} references missing parts {sorted(missing)}")
        if connection.actual_overlap_m < connection.min_overlap_m:
            raise ValueError(f"{connection.name} contact overlap is below release minimum")

    route_violations: list[str] = []
    spawn_violations: list[str] = []
    all_spawns = (*constraints.player_spawns, *constraints.bot_spawns)
    for spec in (*additions.boxes, *additions.cylinders):
        if isinstance(spec, BoxSpec) and spec.route_exempt:
            continue
        bounds = a19._spec_bounds(spec)
        if bounds is None or bounds[4] >= 3.0 or bounds[5] <= 0.10:
            continue
        for hero in (constraints.command, constraints.hangar):
            if a19._intersects_approach(bounds, hero.approach):
                route_violations.append(f"{spec.name}:{hero.landmark_id}")
        for spawn_index, (sx, _sy, sz) in enumerate(all_spawns):
            closest_x = min(max(sx, bounds[0]), bounds[1])
            closest_z = min(max(sz, bounds[2]), bounds[3])
            if math.hypot(sx - closest_x, sz - closest_z) < 5.0:
                spawn_violations.append(f"{spec.name}:spawn-{spawn_index}")
    if route_violations:
        raise ValueError(f"A20 additions block authoritative approaches: {route_violations[:8]}")
    if spawn_violations:
        raise ValueError(f"A20 additions violate 5 m spawn clearance: {spawn_violations[:8]}")

    triangles = _estimated_triangles(merged)
    materials = sorted(
        {
            spec.key
            for group in (
                merged.boxes,
                merged.beams,
                merged.cylinders,
                merged.cylinders_between,
                merged.sloped_panels,
                merged.rocks,
            )
            for spec in group
        }
    )
    if merged.primitive_count > budget.max_primitives:
        raise ValueError(f"A20 primitive budget exceeded: {merged.primitive_count}>{budget.max_primitives}")
    if triangles > budget.max_estimated_triangles:
        raise ValueError(f"A20 triangle budget exceeded: {triangles}>{budget.max_estimated_triangles}")
    if len(materials) > budget.max_materials:
        raise ValueError(f"A20 material budget exceeded: {len(materials)}>{budget.max_materials}")
    return {
        "primitiveCount": merged.primitive_count,
        "estimatedTriangles": triangles,
        "materials": materials,
        "routeViolations": route_violations,
        "spawnViolations": spawn_violations,
        "a20AdditionCount": sum(
            len(group)
            for group in (
                additions.boxes,
                additions.beams,
                additions.cylinders,
                additions.cylinders_between,
                additions.sloped_panels,
                additions.rocks,
            )
        ),
        "webglBatchIntent": {
            "mergeByMaterial": True,
            "targetDrawCalls": len(materials),
            "textureFamilies": len(materials),
            "privateProofOnly": True,
        },
    }


def producer_provisional_scorecard(evidence_paths: Sequence[str] = ()) -> dict[str, Any]:
    scores = {category: float(PRODUCER_PROVISIONAL_SCORES[category]) for category in FIXED_SCORE_CATEGORIES}
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
            "role": "focused production composition guide",
        },
        "categories": list(FIXED_SCORE_CATEGORIES),
        "scores": scores,
        "average": round(average, 3),
        "minimumPerCategory": 7.0,
        "minimumAverage": 8.0,
        "producerProvisional": True,
        "producerScoreAccepted": False,
        "strictAuditStatus": "NO-SHIP_REWORKED_PENDING_NEW_INDEPENDENT_REVIEW",
        "independentReviewerRequired": True,
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        "strongestRemainingMismatch": (
            "A20 improves the dual-hero macro read and operational depth, but original-resolution "
            "independent review must still judge material specificity, mountain naturalism and "
            "first-person density against the source concept"
        ),
        "evidencePaths": list(evidence_paths),
    }


def make_kunren_reference_a20_plan(
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: Mapping[str, ApproachSpec | Mapping[str, Any]] | None = None,
    lod_budget: LODBudget | None = None,
) -> KunrenPlan:
    """Build the isolated A20 visual plan without mutating canonical data."""

    if lod not in A20_LOD_BUDGETS:
        raise ValueError(f"unsupported A20 LOD {lod}")
    before = copy.deepcopy(stage)
    budget = lod_budget or A20_LOD_BUDGETS[lod]
    constraints = constraints_from_authoritative_layout(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=budget,
    )
    base = _reshape_locked_camera_occluders(
        a19.make_kunren_reference_a19_plan(
            stage,
            lod,
            collision_boxes=collision_boxes,
            entrance_overrides=entrance_overrides,
            approach_overrides=approach_overrides,
            lod_budget=budget,
        )
    )
    additions = _A20Assembler(base.names)
    _add_command_bastion_rebuild(additions, constraints.command, lod)
    _add_hangar_operational_rebuild(additions, constraints.hangar, lod)
    _add_terraced_world_and_story(additions, lod)

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
    metrics = _validate_a20(additions, constraints, budget, provisional)
    camera_clearance = {
        MAIN_REFERENCE_CAMERA.name: list(camera_solid_hits(provisional, MAIN_REFERENCE_CAMERA)),
        COMMAND_APPROACH_CAMERA.name: list(camera_solid_hits(provisional, COMMAND_APPROACH_CAMERA)),
    }
    blocked_cameras = {name: hits for name, hits in camera_clearance.items() if hits}
    if blocked_cameras:
        raise ValueError(f"A20 proof cameras are embedded in solid geometry: {blocked_cameras}")
    command_frame = camera_hero_frame_metrics(MAIN_REFERENCE_CAMERA, constraints.command)
    hangar_frame = camera_hero_frame_metrics(MAIN_REFERENCE_CAMERA, constraints.hangar)
    metadata = {
        "kitVersion": KIT_VERSION,
        "baseVisualKit": base.metadata["kitVersion"],
        "stageId": "kunren",
        "lod": lod,
        "coordinateSystem": "runtime-xz-horizontal-y-up-metres",
        "constructionOrder": [
            "imagegen-reference-lock",
            "reference-camera-lock",
            "authoritative-contract-freeze",
            "command-tier-connection-map",
            "hangar-rib-and-operations-map",
            "terraced-near-mid-far-world",
            "private-proof-and-provisional-no-ship",
        ],
        "productionBrief": {
            "focalHierarchy": [
                "left castle-scale Command Bastion",
                "right huge Aerostat Vault Hangar",
                "foreground checkpoint and route",
                "terraced settlement and layered mountains",
            ],
            "camera": "playable 1.65 m, 20 mm, both heroes wholly in frame",
            "style": "weathered tan concrete, dark steel, restrained warm practicals",
            "gameplay": "preserve routes/spawns/collision; visual-only geometry",
            "hardFail": "generic sparse boxes, shallow hangar, raster horizon, third landmark",
        },
        "mainReferenceCamera": asdict(MAIN_REFERENCE_CAMERA),
        "commandHeroInspectionCamera": asdict(COMMAND_APPROACH_CAMERA),
        "proofCameraClearance": camera_clearance,
        "heroFrameMetrics": {COMMAND_ID: command_frame, HANGAR_ID: hangar_frame},
        "imageGenReference": {
            "privatePath": str(IMAGEGEN_REFERENCE_PATH),
            "sha256": IMAGEGEN_REFERENCE_SHA256,
            "sourceReferenceSha256": REFERENCE_IMAGE_SHA256,
            "usedBeforeModeling": True,
        },
        "sightlineTreatments": [asdict(value) for value in A20_SIGHTLINE_TREATMENTS],
        "heroEnvelopes": {
            "command": asdict(constraints.command),
            "hangar": asdict(constraints.hangar),
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
            "collisionPolicy": "visual-only; canonical gameplay collision remains authoritative",
        },
        "artTargets": {
            "command": "stepped battered fortress, crown bridge, deep occupied apertures and human-scale west portal",
            "hangar": "thick repeated vault ribs, deep dark cavity, large serviced aerostat, gantries and equipment",
            "world": "checkpoint foreground, terraced support district and real 3D mountain layers",
            "story": "active command watch, resupply checkpoint and aerostat maintenance cycle",
        },
        "surfaceResponseContract": {
            "families": [
                "weathered-tan-concrete",
                "oxidized-dark-steel",
                "rough-route-asphalt",
                "dusty-mountain-ground",
                "service-wood-and-painted-equipment",
            ],
            "requiredChannels": ["baseColor", "roughness", "normalOrBump"],
            "flatColorAloneIsBlockout": True,
            "deepOpeningsAreGeometry": True,
            "proofMaterialLimit": 12,
        },
        "lodContract": {
            "levels": [0, 1, 2],
            "reductionOrder": [
                "micro props and minor rails",
                "secondary apertures and service ribs",
                "settlement tiers and mountain segment density",
            ],
            "heroSilhouettesPreservedAtAllLods": True,
            "mergeByMaterialForWebGL": True,
        },
        "formalReferenceGate": {
            "categories": list(FIXED_SCORE_CATEGORIES),
            "minimumPerCategory": 7.0,
            "minimumAverage": 8.0,
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
            "headless": True,
        },
        "lodBudget": asdict(budget),
        "metrics": metrics,
        "connectionMap": [asdict(connection) for connection in provisional.connections],
        "producerProvisionalScorecard": producer_provisional_scorecard(),
    }
    if stage != before:
        raise RuntimeError("A20 planning mutated authoritative stage input")
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


def emit_kunren_reference_a20_plan(builder: MeshBuilderProtocol, plan: KunrenPlan) -> Mapping[str, Any]:
    """Emit A20 through the same reviewed builder surface used by A19."""

    return a19.emit_kunren_reference_a19_plan(builder, plan)


def build_kunren_reference_a20(
    builder: MeshBuilderProtocol,
    stage: Mapping[str, Any],
    lod: int,
    **kwargs: Any,
) -> Mapping[str, Any]:
    plan = make_kunren_reference_a20_plan(stage, lod, **kwargs)
    return emit_kunren_reference_a20_plan(builder, plan)


# ---------------------------------------------------------------------------
# Optional private Blender proof.  A19's reviewed geometry builder is reused
# to avoid a second primitive implementation; A20 then performs its own
# material/lighting/camera pass and writes only under /private/tmp.
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_blender_private_proof(plan: KunrenPlan, output_dir: Path) -> dict[str, Any]:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    output_dir = output_dir.expanduser().resolve()
    if str(output_dir).startswith(str(REPO_ROOT.resolve())):
        raise ValueError("A20 proof output must stay outside the repository")
    if not str(output_dir).startswith("/private/tmp/"):
        raise ValueError("A20 proof output must stay under /private/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    views_dir = output_dir / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir = output_dir / "_a19-reviewed-builder-scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    if not IMAGEGEN_REFERENCE_PATH.exists():
        raise FileNotFoundError(f"missing private ImageGen reference: {IMAGEGEN_REFERENCE_PATH}")
    actual_imagegen_sha = _sha256(IMAGEGEN_REFERENCE_PATH)
    if actual_imagegen_sha != IMAGEGEN_REFERENCE_SHA256:
        raise ValueError(
            f"ImageGen reference hash mismatch: {actual_imagegen_sha} != {IMAGEGEN_REFERENCE_SHA256}"
        )

    # A19 owns the reviewed primitive construction implementation.  Patch only
    # its proof camera/version for this isolated call, then restore immediately.
    old_camera = a19.MAIN_REFERENCE_CAMERA
    old_version = a19.KIT_VERSION
    try:
        a19.MAIN_REFERENCE_CAMERA = MAIN_REFERENCE_CAMERA
        a19.KIT_VERSION = KIT_VERSION
        scratch_manifest = a19._run_blender_private_proof(plan, scratch_dir)
    finally:
        a19.MAIN_REFERENCE_CAMERA = old_camera
        a19.KIT_VERSION = old_version

    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.05

    # Weathered tan/steel PBR: retain A19's procedural BaseColor/Roughness/Bump
    # graph but tune its response to the ImageGen production reference.
    palette = {
        "wall": (0.22, 0.155, 0.085, 1.0),
        "wall_alt": (0.004, 0.007, 0.009, 1.0),
        "wall_cool": (0.040, 0.060, 0.072, 1.0),
        "wall_warm": (0.28, 0.135, 0.040, 1.0),
        "wall_weathered": (0.265, 0.175, 0.085, 1.0),
        "roof": (0.022, 0.032, 0.036, 1.0),
        "trim": (0.012, 0.022, 0.027, 1.0),
        "accent": (0.72, 0.16, 0.015, 1.0),
        "terrain": (0.105, 0.080, 0.042, 1.0),
        "obstacle": (0.19, 0.105, 0.036, 1.0),
        "wood": (0.115, 0.050, 0.014, 1.0),
        "road": (0.016, 0.021, 0.024, 1.0),
    }
    for key, base in palette.items():
        material = bpy.data.materials.get(f"A19_MAT_{key}")
        if material is None or not material.use_nodes:
            continue
        material.name = f"A20_MAT_{key}"
        material.diffuse_color = base
        nodes = material.node_tree.nodes
        ramp = next((node for node in nodes if node.bl_idname == "ShaderNodeValToRGB"), None)
        noise = next((node for node in nodes if node.bl_idname == "ShaderNodeTexNoise"), None)
        shader = next((node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        bump = next((node for node in nodes if node.bl_idname == "ShaderNodeBump"), None)
        if ramp is not None:
            low_factor = 0.30 if key in {"wall", "wall_weathered", "terrain"} else 0.48
            ramp.color_ramp.elements[0].color = tuple(max(0.0, value * low_factor) for value in base[:3]) + (1.0,)
            ramp.color_ramp.elements[1].color = tuple(min(1.0, value * 1.34) for value in base[:3]) + (1.0,)
            if len(ramp.color_ramp.elements) == 2 and key in {"wall", "wall_weathered", "terrain"}:
                middle = ramp.color_ramp.elements.new(0.56)
                middle.color = tuple(min(1.0, value * 0.72) for value in base[:3]) + (1.0,)
        if noise is not None:
            noise.inputs["Scale"].default_value = 5.5 if "wall" in key else 10.0
            noise.inputs["Detail"].default_value = 6.0 if key in {"wall", "wall_weathered", "terrain"} else 3.5
            noise.inputs["Roughness"].default_value = 0.78
        if shader is not None:
            shader.inputs["Metallic"].default_value = 0.62 if key in {"trim", "roof"} else 0.28 if key == "wall_cool" else 0.0
            shader.inputs["Roughness"].default_value = 0.88 if key in {"wall", "wall_weathered", "terrain"} else 0.68
            if key == "accent":
                emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
                strength = shader.inputs.get("Emission Strength")
                if emission is not None:
                    emission.default_value = (1.0, 0.19, 0.025, 1.0)
                if strength is not None:
                    strength.default_value = 4.2
        if bump is not None:
            bump.inputs["Strength"].default_value = 0.32 if key in {"wall", "wall_weathered", "terrain"} else 0.09
            bump.inputs["Distance"].default_value = 0.10 if key in {"wall", "wall_weathered"} else 0.045
        material["a20RequiredChannels"] = "baseColor,roughness,normalOrBump"
        material["a20SurfaceFamily"] = key

    # Replace every inherited spherical rock proxy in the mountain system with
    # a deterministic multi-ring ridge mesh.  The base remains grounded at the
    # same runtime anchor, while irregular shoulders and offset summits create
    # actual layered terrain silhouettes.
    mountain_specs = {
        spec.name: spec
        for spec in plan.rocks
        if spec.role
        in {
            "foothill-ridge",
            "foothill-spur",
            "far-mountain-mass",
            "layered-rugged-mountain-silhouette",
        }
    }
    mountain_mesh_count = 0
    terrain_material = bpy.data.materials.get("A20_MAT_terrain")
    for obj in list(bpy.data.objects):
        part_name = obj.get("a19PartName")
        spec = mountain_specs.get(part_name)
        if spec is None:
            continue
        segments = max(10, min(24, int(spec.segments) + 4))
        ring_data = (
            (-0.50, 1.12),
            (-0.28, 1.00),
            (0.02, 0.78),
            (0.27, 0.52),
            (0.43, 0.25),
        )
        vertices: list[tuple[float, float, float]] = []
        for ring_index, (height_factor, radius_factor) in enumerate(ring_data):
            for segment_index in range(segments):
                angle = math.tau * segment_index / segments
                phase = spec.seed * 0.173 + ring_index * 0.79
                irregularity = (
                    1.0
                    + 0.13 * math.sin(angle * 3.0 + phase)
                    + 0.08 * math.sin(angle * 7.0 + phase * 1.7)
                )
                ridge_bias = 0.82 + 0.18 * abs(math.sin(angle + phase * 0.31))
                radius = spec.radius * radius_factor * irregularity
                vertices.append(
                    (
                        math.cos(angle) * radius,
                        math.sin(angle) * radius * ridge_bias,
                        spec.height * height_factor
                        + spec.height * 0.035 * math.sin(angle * 5.0 + phase),
                    )
                )
        summit_index = len(vertices)
        vertices.append(
            (
                spec.radius * 0.11 * math.sin(spec.seed * 0.37),
                spec.radius * 0.09 * math.cos(spec.seed * 0.29),
                spec.height * 0.50,
            )
        )
        faces: list[tuple[int, ...]] = []
        for ring_index in range(len(ring_data) - 1):
            ring_start = ring_index * segments
            next_start = (ring_index + 1) * segments
            for segment_index in range(segments):
                nxt = (segment_index + 1) % segments
                faces.append(
                    (
                        ring_start + segment_index,
                        ring_start + nxt,
                        next_start + nxt,
                        next_start + segment_index,
                    )
                )
        top_start = (len(ring_data) - 1) * segments
        for segment_index in range(segments):
            nxt = (segment_index + 1) % segments
            faces.append((top_start + segment_index, top_start + nxt, summit_index))
        faces.append(tuple(reversed(range(segments))))
        mesh = bpy.data.meshes.new(f"A20_MOUNTAIN_{part_name.replace('.', '_')}")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        if terrain_material is not None:
            mesh.materials.append(terrain_material)
        old_mesh = obj.data
        obj.data = mesh
        obj["a20TerrainKind"] = "deterministic-jagged-multi-ring-ridge"
        if old_mesh is not None and old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        mountain_mesh_count += 1

    # Promote A20 hero parts into the landmark collection for a readable scene.
    landmark_collection = bpy.data.collections.get("HB_kunren_30_LANDMARK")
    for obj in bpy.data.objects:
        part_name = obj.get("a19PartName")
        if not isinstance(part_name, str):
            continue
        obj["a20PartName"] = part_name
        obj["a20KitVersion"] = KIT_VERSION
        if landmark_collection is not None and part_name.startswith(("a20.cmd.", "a20.hall.")):
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            landmark_collection.objects.link(obj)

    lighting_collection = bpy.data.collections.get("HB_kunren_70_LIGHTING")
    guide_collection = bpy.data.collections.get("HB_kunren_00_GUIDES")
    if lighting_collection is None or guide_collection is None:
        raise RuntimeError("A19 reviewed builder did not create expected proof collections")

    def runtime_point(point: Point3) -> Vector:
        return Vector((point[0], -point[2], point[1]))

    # Rebalance the inherited sun/world into a hard mountain daylight with cool
    # sky fill and warm occupied practicals.
    world = scene.world
    if world is not None and world.use_nodes:
        background = next(
            (node for node in world.node_tree.nodes if node.bl_idname == "ShaderNodeBackground"),
            None,
        )
        if background is not None:
            background.inputs["Strength"].default_value = 0.24
    sun = bpy.data.objects.get("LGT_Kunren_A19_Sun")
    if sun is not None and getattr(sun, "data", None) is not None:
        sun.data.energy = 3.8
        sun.data.angle = math.radians(1.4)
        sun.data.color = (1.0, 0.82, 0.67)
        sun.rotation_euler = (math.radians(42.0), math.radians(-8.0), math.radians(-36.0))
        sun.name = "LGT_Kunren_A20_HardMountainSun"

    def add_point_light(
        name: str,
        location: Point3,
        color: tuple[float, float, float],
        energy: float,
        radius: float,
    ) -> None:
        data = bpy.data.lights.new(f"{name}_DATA", "POINT")
        data.color = color
        data.energy = energy
        data.shadow_soft_size = radius
        obj = bpy.data.objects.new(name, data)
        obj.location = runtime_point(location)
        lighting_collection.objects.link(obj)

    def add_area_light(
        name: str,
        location: Point3,
        target: Point3,
        color: tuple[float, float, float],
        energy: float,
        size: float,
    ) -> None:
        data = bpy.data.lights.new(f"{name}_DATA", "AREA")
        data.color = color
        data.energy = energy
        data.shape = "RECTANGLE"
        data.size = size
        data.size_y = size * 0.55
        obj = bpy.data.objects.new(name, data)
        obj.location = runtime_point(location)
        direction = runtime_point(target) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        lighting_collection.objects.link(obj)

    add_area_light(
        "LGT_Kunren_A20_HangarPortalWarm",
        (-46.0, 24.0, -100.0),
        (-20.0, 18.0, -100.0),
        (1.0, 0.42, 0.13),
        2_600.0,
        24.0,
    )
    add_area_light(
        "LGT_Kunren_A20_CommandWarm",
        (73.0, 28.0, 60.0),
        (125.0, 15.0, 20.0),
        (1.0, 0.34, 0.09),
        1_700.0,
        18.0,
    )
    for index, x in enumerate((-52.0, -82.0, -112.0)):
        add_point_light(
            f"LGT_Kunren_A20_HangarPractical_{index}",
            (x, 17.0, -100.0 + (-12.0 if index % 2 == 0 else 12.0)),
            (1.0, 0.30, 0.065),
            1_100.0,
            4.5,
        )
    for index, x in enumerate((54.0, 72.0, 90.0)):
        add_point_light(
            f"LGT_Kunren_A20_CommandPractical_{index}",
            (x, 19.0 + index * 5.0, 59.0),
            (1.0, 0.24, 0.045),
            520.0,
            2.4,
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
        camera["a20EyeHeightM"] = spec.eye_height_m
        camera["a20Intent"] = spec.intent
        return camera

    proof_views = (
        MAIN_REFERENCE_CAMERA,
        ReferenceCamera(
            "CAM_Kunren_A20_CheckpointRoute_1p65",
            (150.0, 1.65, -145.0),
            (74.0, 8.0, -66.0),
            27.0,
            resolution_x=1280,
            resolution_y=720,
            intent="foreground-checkpoint-route",
        ),
        COMMAND_APPROACH_CAMERA,
        ReferenceCamera(
            "CAM_Kunren_A20_CommandOblique_1p65",
            (148.0, 1.65, 8.0),
            (74.0, 23.0, 82.0),
            30.0,
            resolution_x=1280,
            resolution_y=720,
            intent="command-tier-and-crown",
        ),
        ReferenceCamera(
            "CAM_Kunren_A20_HangarApproach_1p65",
            (-8.0, 1.65, -100.0),
            (-88.0, 25.0, -100.0),
            22.0,
            resolution_x=1280,
            resolution_y=720,
            intent="canonical-hangar-approach",
        ),
        ReferenceCamera(
            "CAM_Kunren_A20_HangarInterior_1p65",
            (-48.0, 1.65, -104.0),
            (-106.0, 11.0, -92.0),
            24.0,
            resolution_x=1280,
            resolution_y=720,
            intent="operational-aerostat-gantry-depth",
        ),
        ReferenceCamera(
            "CAM_Kunren_A20_Aerial",
            (190.0, 156.0, -205.0),
            (-4.0, 6.0, 8.0),
            44.0,
            resolution_x=1280,
            resolution_y=720,
            eye_height_m=156.0,
            intent="aerial-bounds-and-two-landmarks",
        ),
    )

    evidence_paths: list[str] = []
    evidence: list[dict[str, Any]] = []
    for index, spec in enumerate(proof_views, start=1):
        camera = make_camera(spec)
        scene.camera = camera
        filename = f"{index:02d}_{spec.name.removeprefix('CAM_Kunren_A20_')}.png"
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

    blend_path = output_dir / "kunren-a20-art-rebuild.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    scorecard = producer_provisional_scorecard(evidence_paths)
    scorecard_path = output_dir / "producer-provisional-scorecard.json"
    scorecard_path.write_text(
        json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    mesh_polygon_count = sum(len(obj.data.polygons) for obj in mesh_objects)
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
            "path": str(IMAGEGEN_REFERENCE_PATH),
            "sha256": actual_imagegen_sha,
        },
        "planMetrics": plan.metadata["metrics"],
        "lodBudget": plan.metadata["lodBudget"],
        "mainReferenceCamera": plan.metadata["mainReferenceCamera"],
        "heroFrameMetrics": plan.metadata["heroFrameMetrics"],
        "proofCameraClearance": plan.metadata["proofCameraClearance"],
        "landmarkIdentityContract": plan.metadata["landmarkIdentityContract"],
        "authoritativeContracts": plan.metadata["authoritativeContracts"],
        "sceneAudit": {
            "meshObjects": len(mesh_objects),
            "meshPolygonsBeforeModifierEvaluation": mesh_polygon_count,
            "jaggedMountainMeshes": mountain_mesh_count,
            "materialCount": len([material for material in bpy.data.materials if material.name.startswith("A20_MAT_")]),
            "publicWrites": 0,
            "sourceWrites": 0,
            "manifestWrites": 0,
        },
        "reviewedBuilderScratch": {
            "directory": str(scratch_dir),
            "kitVersion": scratch_manifest["kitVersion"],
            "currentEvidence": False,
            "note": "construction scratch only; authoritative proof is the top-level seven-view set",
        },
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
    parser = argparse.ArgumentParser(description="Build the private headless Kunren A20 art proof")
    parser.add_argument("--layout", type=Path, default=CANONICAL_LAYOUT_DEFAULT)
    parser.add_argument("--proof-dir", type=Path, default=PRIVATE_PROOF_DEFAULT)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--plan-json", type=Path)
    parser.add_argument("--no-proof", action="store_true")
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_blender_args(sys.argv if argv is None else argv)
    layout = load_authoritative_kunren_layout(args.layout)
    plan = make_kunren_reference_a20_plan(layout.stage, args.lod)
    if args.plan_json is not None:
        target = args.plan_json.expanduser().resolve()
        if str(target).startswith(str(REPO_ROOT.resolve())):
            raise ValueError("A20 plan JSON must stay outside the repository")
        if not str(target).startswith("/private/tmp/"):
            raise ValueError("A20 plan JSON must stay under /private/tmp")
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
    "A20_LOD_BUDGETS",
    "A20_SIGHTLINE_TREATMENTS",
    "COMMAND_APPROACH_CAMERA",
    "IMAGEGEN_REFERENCE_SHA256",
    "KIT_VERSION",
    "MAIN_REFERENCE_CAMERA",
    "PRIVATE_PROOF_DEFAULT",
    "PRODUCER_PROVISIONAL_SCORES",
    "SightlineTreatment",
    "build_kunren_reference_a20",
    "camera_solid_hits",
    "emit_kunren_reference_a20_plan",
    "make_kunren_reference_a20_plan",
    "producer_provisional_scorecard",
]


if __name__ == "__main__":
    raise SystemExit(main())
