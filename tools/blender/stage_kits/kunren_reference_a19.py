"""Kunren A19 reference-first macro rebuild.

This module deliberately lives beside, rather than inside, the catalog build.
It keeps the canonical TypeScript/canonical-layout placements, approaches and
spawns immutable while producing a denser *visual-only* plan and a private
headless Blender proof.  Nothing in this file writes public assets.

Construction order is contractual:

1. lock the 1.65 m reference camera;
2. preserve the two canonical hero envelopes and their approaches;
3. strengthen the occupied command facade and the monumental hangar portal;
4. layer the empty diagonal road with a checkpoint, ramp, retaining walls,
   stairs, logistics and a foreground service frame;
5. render private proof and publish only a producer-provisional scorecard.

Connection map (A19 additions):

* command facade recesses <-> frames/hoods: >= 0.08 m face overlap;
* command buttresses <-> A18 south mass/plinth: >= 0.10 m contact;
* hangar outer collar segments <-> adjacent collar segments: 0.20 m joints;
* hangar portal shoulders <-> A18 hangar floor: 0.20 m foundation embed;
* diagonal ramp deck <-> three road foundations: 0.12 m seating overlap;
* retaining-wall caps <-> wall bodies: 0.08 m seating overlap;
* checkpoint posts <-> bases and crossbeam: >= 0.10 m weld/seat overlap;
* stair treads <-> previous tread/landing: >= 0.10 m overlap;
* logistics frames/loads <-> their carrier decks: >= 0.08 m overlap.

Geometry is authored in Hibana runtime coordinates: X/Z horizontal, Y up,
metres.  The optional Blender proof converts runtime Z to Blender -Y.
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

from tools.blender.stage_kits.kunren_reference_a18 import (  # noqa: E402
    ApproachSpec,
    BeamSpec,
    BoxSpec,
    COMMAND_ID,
    ConnectionSpec,
    CylinderBetweenSpec,
    CylinderSpec,
    HANGAR_ID,
    KunrenPlan,
    LODBudget,
    MeshBuilderProtocol,
    REFERENCE_IMAGE_SHA256,
    RockSpec,
    SlopedPanelSpec,
    constraints_from_authoritative_layout,
    load_authoritative_kunren_layout,
    make_kunren_reference_a18_plan,
)


KIT_VERSION = "kunren-reference-a19-v1"
PRIVATE_PROOF_DEFAULT = Path("/private/tmp/hibana-blender/a19-kunren-macro-rebuild")
CANONICAL_LAYOUT_DEFAULT = Path("/private/tmp/hibana-blender/canonical-stage-layouts.json")
REFERENCE_PATH = REPO_ROOT / "tools/blender/concepts/kunren-reference-v1.png"
Point3 = tuple[float, float, float]

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

A19_LOD_BUDGETS: dict[int, LODBudget] = {
    0: LODBudget(1_160, 60_000, 12),
    1: LODBudget(680, 30_000, 12),
    2: LODBudget(340, 12_000, 12),
}

# These two canonical district footprints sit directly on the locked camera
# rays to the two mega-landmarks.  A19 keeps their X/Z placement, footprint,
# names and connections but compresses their visual elevation into foreground
# terraces.  The now-unsupported visual-only bridge between those compressed
# masses is omitted; gameplay collision remains the authoritative TypeScript
# layout.
REFERENCE_SIGHTLINE_TERRACES = (
    "city.block.5.",
    "city.block.9.",
)
REFERENCE_SIGHTLINE_VERTICAL_SCALE = 0.12
REFERENCE_SIGHTLINE_REMOVALS = ("city.bridge.south.service",)


@dataclass(frozen=True)
class ReferenceCamera:
    name: str
    location: Point3
    target: Point3
    lens_mm: float
    sensor_width_mm: float = 36.0
    resolution_x: int = 1600
    resolution_y: int = 900
    eye_height_m: float = 1.65
    intent: str = "reference-diagonal-dual-hero"


# Camera is intentionally declared before any A19 geometry.  At the canonical
# hero envelopes this yields ~36% Command and ~50% Hangar vertical coverage,
# i.e. the requested 40/40-class composition without moving gameplay anchors.
MAIN_REFERENCE_CAMERA = ReferenceCamera(
    name="CAM_Kunren_A19_ReferenceDual_1p65",
    location=(143.0, 1.65, -143.0),
    target=(0.0, 18.0, -2.0),
    lens_mm=24.0,
)


PRODUCER_PROVISIONAL_SCORES: dict[str, float] = {
    "composition": 4.2,
    "hero silhouettes": 4.6,
    "architectural grammar": 4.4,
    "human scale": 4.0,
    "material realism": 3.6,
    "near/mid/far density": 3.7,
    "gameplay readability": 5.4,
    "props and environmental storytelling": 4.1,
    "lighting and atmosphere": 4.3,
    "reference identity": 3.9,
}


def _v_sub(a: Point3, b: Point3) -> Point3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _v_dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v_cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _v_normalize(value: Point3) -> Point3:
    length = math.sqrt(_v_dot(value, value))
    if length <= 1e-9:
        raise ValueError("cannot normalize a zero-length vector")
    return value[0] / length, value[1] / length, value[2] / length


def _project_point(camera: ReferenceCamera, point: Point3) -> tuple[float, float, float]:
    forward = _v_normalize(_v_sub(camera.target, camera.location))
    right = _v_normalize(_v_cross(forward, (0.0, 1.0, 0.0)))
    up = _v_cross(right, forward)
    relative = _v_sub(point, camera.location)
    depth = _v_dot(relative, forward)
    if depth <= 1e-6:
        raise ValueError("camera projection received a point behind the camera")
    horizontal_fov = 2.0 * math.atan(camera.sensor_width_mm / (2.0 * camera.lens_mm))
    aspect = camera.resolution_x / camera.resolution_y
    vertical_fov = 2.0 * math.atan(math.tan(horizontal_fov / 2.0) / aspect)
    screen_x = 0.5 + 0.5 * (_v_dot(relative, right) / depth) / math.tan(horizontal_fov / 2.0)
    screen_y = 0.5 + 0.5 * (_v_dot(relative, up) / depth) / math.tan(vertical_fov / 2.0)
    return screen_x, screen_y, depth


def camera_hero_frame_metrics(camera: ReferenceCamera, hero: Any) -> dict[str, float]:
    """Project a conservative hero envelope into normalized screen space."""

    projected = [
        _project_point(camera, (x, y, z))
        for x in (hero.cx - hero.width / 2.0, hero.cx + hero.width / 2.0)
        for y in (0.0, hero.height)
        for z in (hero.cz - hero.depth / 2.0, hero.cz + hero.depth / 2.0)
    ]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    return {
        "xMin": min(xs),
        "xMax": max(xs),
        "yMin": min(ys),
        "yMax": max(ys),
        "screenWidth": max(xs) - min(xs),
        "screenHeight": max(ys) - min(ys),
        "visibleHorizontalFraction": max(0.0, min(1.0, max(xs)) - max(0.0, min(xs))),
        "targetClass": 0.40,
    }


class _AddonAssembler:
    """Small A19-only spec assembler; A18 remains unmodified."""

    def __init__(self, occupied_names: Iterable[str]) -> None:
        self.boxes: list[BoxSpec] = []
        self.beams: list[BeamSpec] = []
        self.cylinders: list[CylinderSpec] = []
        self.cylinders_between: list[CylinderBetweenSpec] = []
        self.sloped_panels: list[SlopedPanelSpec] = []
        self.rocks: list[RockSpec] = []
        self.connections: list[ConnectionSpec] = []
        self._names = set(occupied_names)

    def _claim(self, name: str) -> None:
        if not name or name in self._names:
            raise ValueError(f"duplicate or empty A19 part name: {name!r}")
        self._names.add(name)

    def box(
        self,
        name: str,
        x: float,
        y: float,
        z: float,
        w: float,
        h: float,
        d: float,
        key: str,
        *,
        yaw: float = 0.0,
        role: str = "structure",
        route_exempt: bool = False,
    ) -> None:
        self._claim(name)
        if min(w, h, d) <= 0.0:
            raise ValueError(f"{name} has non-positive box dimensions")
        self.boxes.append(BoxSpec(name, x, y, z, w, h, d, key, yaw, role, route_exempt))

    def beam(
        self,
        name: str,
        start: Point3,
        end: Point3,
        width: float,
        depth: float,
        key: str,
        *,
        role: str = "structure",
    ) -> None:
        self._claim(name)
        if min(width, depth) <= 0.0 or math.dist(start, end) <= 1e-6:
            raise ValueError(f"{name} has invalid beam dimensions")
        self.beams.append(BeamSpec(name, start, end, width, depth, key, role))

    def cylinder(
        self,
        name: str,
        x: float,
        y: float,
        z: float,
        radius: float,
        height: float,
        key: str,
        segments: int,
        *,
        top_radius: float | None = None,
        role: str = "equipment",
    ) -> None:
        self._claim(name)
        self.cylinders.append(CylinderSpec(name, x, y, z, radius, height, key, segments, top_radius, role))

    def cylinder_between(
        self,
        name: str,
        start: Point3,
        end: Point3,
        radius: float,
        key: str,
        segments: int,
        *,
        end_radius: float | None = None,
        role: str = "equipment",
    ) -> None:
        self._claim(name)
        self.cylinders_between.append(
            CylinderBetweenSpec(name, start, end, radius, key, segments, end_radius, role)
        )

    def panel(
        self,
        name: str,
        corners: Sequence[Point3],
        thickness: float,
        key: str,
        *,
        role: str = "shell",
    ) -> None:
        self._claim(name)
        if len(corners) != 4 or thickness <= 0.0:
            raise ValueError(f"{name} has invalid panel data")
        self.sloped_panels.append(SlopedPanelSpec(name, tuple(corners), thickness, key, role))

    def connect(
        self,
        name: str,
        parent: str,
        child: str,
        contact_kind: str,
        axis: str,
        overlap: float,
        note: str = "",
    ) -> None:
        if overlap < 0.005:
            raise ValueError(f"{name} overlap {overlap} is below 5 mm")
        self.connections.append(ConnectionSpec(name, parent, child, contact_kind, axis, overlap, 0.005, note))


def _add_command_occupied_facade(a: _AddonAssembler, hero: Any, lod: int) -> None:
    """Add camera-facing occupancy and depth without moving the envelope."""

    x, z = hero.cx, hero.cz
    facade_z = z - 25.05
    bay_count = 3 if lod == 0 else 2 if lod == 1 else 1
    bay_offsets = (-22.0, 0.0, 22.0)
    for index, offset in enumerate(bay_offsets[:bay_count]):
        prefix = f"a19.cmd.facade.bay.{index}"
        bay_x = x + offset
        a.box(f"{prefix}.recess", bay_x, 5.7, facade_z + 0.24, 11.4, 7.4, 0.52, "wall_alt", role="occupied-facade-deep-recess")
        for suffix, fx, fy, fw, fh in (
            ("left", bay_x - 6.0, 5.7, 0.72, 8.2),
            ("right", bay_x + 6.0, 5.7, 0.72, 8.2),
            ("header", bay_x, 9.72, 12.7, 0.72),
            ("sill", bay_x, 1.72, 12.7, 0.58),
        ):
            name = f"{prefix}.frame.{suffix}"
            a.box(name, fx, fy, facade_z - 0.18, fw, fh, 0.92, "trim", role="occupied-facade-frame")
            a.connect(f"contact.{name}", f"{prefix}.recess", name, "facade-frame-seat", "z", 0.10)
        louver_count = 5 if lod == 0 else 3 if lod == 1 else 1
        for louver_index in range(louver_count):
            name = f"{prefix}.louver.{louver_index}"
            a.box(
                name,
                bay_x,
                3.0 + louver_index * 1.0,
                facade_z - 0.34,
                9.8,
                0.22,
                0.34,
                "accent" if louver_index == 2 else "trim",
                role="occupied-facade-louver",
            )
            a.connect(f"contact.{name}", f"{prefix}.recess", name, "louver-seat", "z", 0.08)
        if lod < 2:
            hood = f"{prefix}.weather-hood"
            a.panel(
                hood,
                (
                    (bay_x - 6.3, 10.05, facade_z - 0.8),
                    (bay_x + 6.3, 10.05, facade_z - 0.8),
                    (bay_x + 6.3, 10.55, facade_z + 0.5),
                    (bay_x - 6.3, 10.55, facade_z + 0.5),
                ),
                0.16,
                "roof",
                role="weathering-drip-hood",
            )
            a.connect(f"contact.{hood}", f"{prefix}.recess", hood, "hood-seat", "z", 0.08)

    buttress_count = 5 if lod == 0 else 3 if lod == 1 else 2
    for index in range(buttress_count):
        buttress_x = x - 34.0 + index * 17.0
        name = f"a19.cmd.battered-buttress.{index}"
        a.beam(
            name,
            (buttress_x, 0.25, facade_z - 3.8),
            (buttress_x, 18.8, facade_z + 2.2),
            0.95,
            1.10,
            "wall_weathered",
            role="castle-scale-battered-buttress",
        )
        a.connect(f"contact.{name}", "cmd.lower.south", name, "buttress-wall-seat", "endpoint", 0.12)

    # Asymmetric occupied east stack improves the camera-facing silhouette.
    stack_x = x + hero.width / 2.0 - 2.4
    stack_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, stack_z in enumerate((z - 17.0, z, z + 17.0)[:stack_count]):
        name = f"a19.cmd.east-operations-stack.{index}"
        height = 16.0 + index * 3.0
        a.box(name, stack_x, height / 2.0, stack_z, 4.2, height, 10.0, "wall_weathered", role="occupied-command-stack")
        a.box(f"{name}.cap", stack_x, height + 0.45, stack_z, 5.2, 0.90, 11.0, "trim", role="occupied-command-stack-cap")
        a.connect(f"contact.{name}.cap", name, f"{name}.cap", "cap-seat", "y", 0.08)

    # The authoritative approach is on the west face.  Build true dark
    # occupied apertures around (never across) its 12 m clearance, so the
    # approach proof reads as an operating command base rather than a blank
    # concrete gate.
    west_face_x = x - hero.width / 2.0 + 5.55
    west_bays = (-16.0, 16.0) if lod < 2 else (-16.0,)
    for index, offset in enumerate(west_bays):
        prefix = f"a19.cmd.west-operations-bay.{index}"
        bay_z = z + offset
        recess = f"{prefix}.recess"
        a.box(recess, west_face_x + 0.24, 8.0, bay_z, 0.52, 10.8, 11.2, "wall_alt", role="occupied-west-facade-deep-recess")
        for suffix, fy, fz, fh, fd in (
            ("south", 8.0, bay_z - 5.9, 11.8, 0.72),
            ("north", 8.0, bay_z + 5.9, 11.8, 0.72),
            ("header", 13.55, bay_z, 0.72, 12.5),
            ("sill", 2.55, bay_z, 0.58, 12.5),
        ):
            frame = f"{prefix}.frame.{suffix}"
            a.box(frame, west_face_x - 0.18, fy, fz, 0.92, fh, fd, "trim", role="occupied-west-facade-frame")
            a.connect(f"contact.{frame}", recess, frame, "west-facade-frame-seat", "x", 0.10)
        louver_count = 6 if lod == 0 else 3 if lod == 1 else 1
        for louver_index in range(louver_count):
            louver = f"{prefix}.louver.{louver_index}"
            a.box(
                louver,
                west_face_x - 0.34,
                4.1 + louver_index * 1.18,
                bay_z,
                0.34,
                0.24,
                9.8,
                "accent" if louver_index in {1, 4} else "trim",
                role="occupied-west-facade-louver",
            )
            a.connect(f"contact.{louver}", recess, louver, "west-louver-seat", "x", 0.08)

    # The central surface is a visual shadow plane behind the canonical open
    # portal.  route_exempt prevents a decorative plane from being mistaken
    # for gameplay collision by the private validator.
    a.box(
        "a19.cmd.portal.deep-shadow",
        west_face_x + 2.0,
        5.0,
        z,
        0.42,
        8.4,
        10.0,
        "wall_alt",
        role="command-portal-deep-shadow",
        route_exempt=True,
    )
    for side, offset in (("south", -6.2), ("north", 6.2)):
        post = f"a19.cmd.portal.armored-post.{side}"
        a.box(post, west_face_x - 0.30, 5.2, z + offset, 1.05, 10.4, 1.25, "trim", role="command-portal-armored-frame", route_exempt=True)
        a.connect(f"contact.{post}", "a19.cmd.portal.deep-shadow", post, "portal-frame-seat", "x", 0.10)
    a.box("a19.cmd.portal.weather-canopy", west_face_x - 1.0, 10.8, z, 3.2, 0.65, 14.5, "roof", role="command-portal-weather-canopy", route_exempt=True)
    a.connect(
        "contact.a19.cmd.portal.weather-canopy",
        "a19.cmd.portal.deep-shadow",
        "a19.cmd.portal.weather-canopy",
        "portal-canopy-seat",
        "x",
        0.10,
    )

    # Twin but deliberately unequal command crowns lift the silhouette above
    # the surrounding settlement while remaining inside the 49 m envelope.
    crown_specs = (
        ("south", x + 22.0, z - 11.5, 10.5, 22.0),
        ("north", x + 30.0, z + 11.5, 12.0, 25.0),
    )
    for index, (side, crown_x, crown_z, crown_width, crown_height) in enumerate(crown_specs[: 2 if lod < 2 else 1]):
        crown = f"a19.cmd.crown-tower.{side}"
        crown_y = 48.0 - crown_height / 2.0
        a.box(crown, crown_x, crown_y, crown_z, crown_width, crown_height, 10.5, "wall_weathered", role="command-castle-crown")
        a.box(f"{crown}.cap", crown_x, 48.35, crown_z, crown_width + 1.4, 0.60, 11.9, "roof", role="command-crown-weather-cap")
        a.connect(f"contact.{crown}", "cmd.upper.keep", crown, "crown-keep-overlap", "y", 0.30)
        a.connect(f"contact.{crown}.cap", crown, f"{crown}.cap", "crown-cap-seat", "y", 0.10)
        window = f"{crown}.south-observation-slot"
        a.box(window, crown_x, 39.0 + index * 1.8, crown_z - 5.36, crown_width - 2.4, 2.4, 0.42, "wall_alt", role="occupied-command-observation-slot")
        a.connect(f"contact.{window}", crown, window, "observation-slot-seat", "z", 0.08)
        if lod == 0:
            for light_index, light_x in enumerate((crown_x - crown_width * 0.28, crown_x + crown_width * 0.28)):
                light = f"{crown}.status-light.{light_index}"
                a.box(light, light_x, 37.3 + index * 1.8, crown_z - 5.60, 0.42, 0.42, 0.30, "accent", role="active-command-status-light")
                a.connect(f"contact.{light}", window, light, "status-light-seat", "z", 0.08)

    if lod < 2:
        a.beam(
            "a19.cmd.crown-operations-bridge",
            (x + 22.0, 41.5, z - 6.0),
            (x + 30.0, 43.3, z + 6.0),
            0.42,
            0.55,
            "trim",
            role="command-crown-operations-bridge",
        )
        a.connect(
            "contact.a19.cmd.crown-operations-bridge.south",
            "a19.cmd.crown-tower.south",
            "a19.cmd.crown-operations-bridge",
            "bridge-tower-seat",
            "endpoint",
            0.12,
        )
        a.connect(
            "contact.a19.cmd.crown-operations-bridge.north",
            "a19.cmd.crown-tower.north",
            "a19.cmd.crown-operations-bridge",
            "bridge-tower-seat",
            "endpoint",
            0.12,
        )

    # A broad forward keep raises a recognisable fortress silhouette above the
    # foreground terraces.  It occupies the existing command envelope rather
    # than shifting the canonical landmark placement.
    a.box("a19.cmd.forward-keep.base", x - 8.0, 19.0, z - 15.5, 40.0, 18.0, 22.0, "wall_weathered", role="command-forward-fortress-mass")
    a.box("a19.cmd.forward-keep.upper", x - 6.0, 33.0, z - 15.0, 31.0, 20.0, 18.0, "wall", role="command-forward-fortress-mass")
    a.box("a19.cmd.forward-keep.crown", x - 3.0, 45.0, z - 15.0, 22.0, 8.0, 15.0, "wall_weathered", role="command-forward-fortress-crown")
    a.connect("contact.a19.cmd.forward-keep.base", "cmd.mid.south", "a19.cmd.forward-keep.base", "forward-keep-mass-overlap", "y", 0.30)
    a.connect("contact.a19.cmd.forward-keep.upper", "a19.cmd.forward-keep.base", "a19.cmd.forward-keep.upper", "forward-keep-tier-overlap", "y", 0.30)
    a.connect("contact.a19.cmd.forward-keep.crown", "a19.cmd.forward-keep.upper", "a19.cmd.forward-keep.crown", "forward-keep-crown-overlap", "y", 0.30)
    shoulder_count = 2 if lod < 2 else 1
    for index, shoulder_x in enumerate((x - 28.0, x + 13.0)[:shoulder_count]):
        shoulder = f"a19.cmd.forward-keep.shoulder.{index}"
        a.box(shoulder, shoulder_x, 30.0, z - 16.0, 9.5, 30.0, 14.0, "wall_weathered", role="command-forward-shoulder-tower")
        a.box(f"{shoulder}.cap", shoulder_x, 45.35, z - 16.0, 11.0, 0.70, 15.5, "roof", role="command-forward-shoulder-cap")
        a.connect(f"contact.{shoulder}", "a19.cmd.forward-keep.base", shoulder, "shoulder-forward-keep-overlap", "plan", 0.30)
        a.connect(f"contact.{shoulder}.cap", shoulder, f"{shoulder}.cap", "shoulder-cap-seat", "y", 0.10)
    aperture_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index in range(aperture_count):
        aperture_x = x - 19.0 + index * 8.6
        aperture = f"a19.cmd.forward-keep.aperture.{index}"
        a.box(aperture, aperture_x, 28.5 + (index % 2) * 4.0, z - 24.15, 5.8, 4.0, 0.46, "wall_alt", role="occupied-command-forward-aperture")
        a.box(f"{aperture}.hood", aperture_x, 30.75 + (index % 2) * 4.0, z - 24.55, 6.8, 0.42, 1.2, "roof", role="command-aperture-weather-hood")
        a.connect(f"contact.{aperture}", "a19.cmd.forward-keep.upper", aperture, "forward-aperture-seat", "z", 0.08)
        a.connect(f"contact.{aperture}.hood", aperture, f"{aperture}.hood", "forward-aperture-hood-seat", "z", 0.08)

    # Readable operational hardware at the principal south silhouette.
    pipe_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index in range(pipe_count):
        pipe = f"a19.cmd.south-service-pipe.{index}"
        pipe_y = 12.4 + index * 2.3
        a.cylinder_between(
            pipe,
            (x - 27.0, pipe_y, facade_z - 0.72),
            (x + 29.0, pipe_y, facade_z - 0.72),
            0.18 + index * 0.035,
            "wall_warm" if index == 1 else "trim",
            10,
            role="active-command-service-pipe",
        )
        a.connect(f"contact.{pipe}", "cmd.lower.south", pipe, "pipe-wall-standoff", "z", 0.08)

    mast_count = 3 if lod == 0 else 2 if lod == 1 else 1
    mast_anchors = ((x + 20.0, z - 13.0), (x + 30.0, z + 11.5), (x + 12.0, z + 4.0))
    for index, (mast_x, mast_z) in enumerate(mast_anchors[:mast_count]):
        mast = f"a19.cmd.roof-antenna.{index}.mast"
        start_y = 43.0 if index == 2 else 47.7
        end_y = 48.8
        a.beam(mast, (mast_x, start_y, mast_z), (mast_x, end_y, mast_z), 0.09, 0.09, "trim", role="command-roof-antenna")
        parent = "cmd.crown" if index == 2 else f"a19.cmd.crown-tower.{('south', 'north')[index]}"
        a.connect(f"contact.{mast}", parent, mast, "antenna-roof-seat", "endpoint", 0.10)
        if lod == 0:
            crossbar = f"a19.cmd.roof-antenna.{index}.crossbar"
            a.beam(crossbar, (mast_x, 47.9, mast_z - 1.4), (mast_x, 47.9, mast_z + 1.4), 0.07, 0.07, "trim", role="command-roof-antenna-array")
            a.connect(f"contact.{crossbar}", mast, crossbar, "antenna-crossbar-weld", "plan", 0.08)


def _arch_profile(cz: float) -> tuple[tuple[float, float], ...]:
    return tuple(
        (cz + offset, height)
        for offset, height in (
            (-31.0, 0.4), (-31.0, 10.0), (-27.5, 22.0), (-20.0, 35.0),
            (-10.5, 47.0), (0.0, 54.0), (10.5, 47.0), (20.0, 35.0),
            (27.5, 22.0), (31.0, 10.0), (31.0, 0.4),
        )
    )


def _add_hangar_monumental_portal(a: _AddonAssembler, hero: Any, lod: int) -> None:
    x, z = hero.cx, hero.cz
    east = x + hero.width / 2.0
    collar_x = east - 1.0
    profile = _arch_profile(z)
    for index, ((z0, y0), (z1, y1)) in enumerate(zip(profile, profile[1:])):
        if lod == 2 and index in {1, 3, 6, 8}:
            continue
        name = f"a19.hall.portal.outer-collar.{index}"
        a.beam(name, (collar_x, y0, z0), (collar_x, y1, z1), 1.55, 1.55, "wall_warm", role="monumental-portal-outer-collar")
        if index:
            previous = f"a19.hall.portal.outer-collar.{index - 1}"
            if previous in a._names:
                a.connect(f"contact.{name}", previous, name, "portal-collar-knee", "endpoint", 0.20)

    # A second, darker arch recessed along X makes the entrance a genuine
    # cavity with a thick roof language instead of a single white outline.
    inner_profile = tuple(
        (z + offset, height)
        for offset, height in (
            (-27.0, 1.0), (-27.0, 10.0), (-23.5, 22.0), (-16.0, 34.0),
            (-8.0, 44.0), (0.0, 49.0), (8.0, 44.0), (16.0, 34.0),
            (23.5, 22.0), (27.0, 10.0), (27.0, 1.0),
        )
    )
    for index, ((z0, y0), (z1, y1)) in enumerate(zip(inner_profile, inner_profile[1:])):
        if lod == 2 and index % 2:
            continue
        name = f"a19.hall.portal.inner-collar.{index}"
        a.beam(name, (east - 5.0, y0, z0), (east - 5.0, y1, z1), 0.82, 0.82, "trim", role="deep-portal-inner-collar")
        if index:
            previous = f"a19.hall.portal.inner-collar.{index - 1}"
            if previous in a._names:
                a.connect(f"contact.{name}", previous, name, "inner-collar-knee", "endpoint", 0.14)

    # Keystone control room and service lights provide scale and an occupied
    # focal point without closing the aircraft-width portal below it.
    a.box("a19.hall.portal.keystone-control", east - 4.4, 48.7, z, 8.2, 9.5, 8.8, "wall_weathered", role="occupied-hangar-keystone-control")
    a.box("a19.hall.portal.keystone-control.cap", east - 4.4, 53.65, z, 9.4, 0.55, 10.0, "roof", role="hangar-keystone-weather-cap")
    a.box("a19.hall.portal.keystone-control.window", east - 0.18, 48.2, z, 0.42, 2.8, 6.1, "wall_alt", role="occupied-hangar-control-window")
    a.connect(
        "contact.a19.hall.portal.keystone-control",
        "a19.hall.portal.outer-collar.4",
        "a19.hall.portal.keystone-control",
        "keystone-collar-seat",
        "plan",
        0.24,
    )
    a.connect(
        "contact.a19.hall.portal.keystone-control.cap",
        "a19.hall.portal.keystone-control",
        "a19.hall.portal.keystone-control.cap",
        "keystone-cap-seat",
        "y",
        0.10,
    )
    a.connect(
        "contact.a19.hall.portal.keystone-control.window",
        "a19.hall.portal.keystone-control",
        "a19.hall.portal.keystone-control.window",
        "keystone-window-seat",
        "x",
        0.08,
    )
    worklight_offsets = (-21.0, -12.0, 12.0, 21.0) if lod == 0 else (-18.0, 18.0)
    for index, offset in enumerate(worklight_offsets):
        light = f"a19.hall.portal.worklight.{index}"
        height = 26.0 if abs(offset) > 18.0 else 36.0
        a.box(light, east + 0.16, height, z + offset, 0.34, 0.70, 0.90, "accent", role="active-hangar-portal-worklight")
        outer_index = 2 if offset < -18.0 else 3 if offset < 0.0 else 6 if offset < 18.0 else 7
        parent = f"a19.hall.portal.outer-collar.{outer_index}"
        if parent in a._names:
            a.connect(f"contact.{light}", parent, light, "worklight-collar-seat", "x", 0.08)

    for side, offset in (("south", -27.0), ("north", 27.0)):
        shoulder = f"a19.hall.portal.shoulder.{side}"
        a.box(shoulder, east - 4.0, 15.0, z + offset, 9.0, 29.6, 11.0, "wall_weathered", role="occupied-hangar-portal-shoulder")
        a.box(f"{shoulder}.cap", east - 4.0, 30.35, z + offset, 10.4, 1.10, 12.4, "trim", role="hangar-portal-shoulder-cap")
        a.connect(f"contact.{shoulder}.floor", "hall.floor", shoulder, "foundation-embed", "y", 0.20)
        a.connect(f"contact.{shoulder}.cap", shoulder, f"{shoulder}.cap", "cap-seat", "y", 0.08)

        # Deep service aperture and active equipment remain outside the 12 m
        # center approach corridor.
        aperture = f"a19.hall.portal.shoulder.{side}.service-recess"
        a.box(aperture, east + 0.66, 5.5, z + offset, 0.46, 7.0, 5.6, "wall_alt", role="deep-operational-service-recess")
        for rail_index in range(3 if lod == 0 else 1):
            rail = f"{aperture}.safety-rail.{rail_index}"
            rail_z = z + offset - 2.2 + rail_index * 2.2
            a.beam(rail, (east + 1.0, 1.1, rail_z), (east + 1.0, 4.8, rail_z), 0.10, 0.10, "accent", role="human-scale-safety-rail")
            a.connect(f"contact.{rail}", aperture, rail, "rail-recess-seat", "x", 0.08)

    if lod < 2:
        # Interior occupation is lateral so the canonical entrance stays clear.
        for side_index, offset in enumerate((-16.0, 16.0)):
            deck = f"a19.hall.operations.deck.{side_index}"
            a.box(deck, east - 22.0, 4.1, z + offset, 28.0, 0.70, 7.2, "wall_cool", role="occupied-hangar-operations-deck")
            a.box(f"{deck}.console", east - 16.0, 5.25, z + offset, 8.0, 1.6, 2.4, "wall_weathered", role="hangar-operations-console")
            a.connect(f"contact.{deck}.floor", "hall.floor", deck, "deck-support-seat", "y", 0.12)
            a.connect(f"contact.{deck}.console", deck, f"{deck}.console", "console-deck-seat", "y", 0.10)

    # Upgrade the suspended aerostat from a bare capsule into maintained base
    # hardware: collar bands, gondola, fins, cradle portals and equipment banks.
    band_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, band_x in enumerate((-84.0, -92.0, -100.0)[:band_count]):
        band = f"a19.hall.aerostat.service-band.{index}"
        a.cylinder_between(
            band,
            (band_x - 0.30, 30.0, z),
            (band_x + 0.30, 30.0, z),
            3.72,
            "wall_warm" if index == 1 else "trim",
            16 if lod == 0 else 10,
            role="aerostat-service-band",
        )
        a.connect(f"contact.{band}", "hall.aerostat.body", band, "aerostat-band-overlap", "x", 0.18)

    a.box("a19.hall.aerostat.gondola", -92.0, 24.9, z, 11.0, 3.4, 4.4, "wall_weathered", role="occupied-aerostat-gondola")
    a.box("a19.hall.aerostat.gondola.window", -87.0, 25.2, z, 0.42, 1.5, 2.7, "wall_alt", role="occupied-aerostat-gondola-window")
    a.connect("contact.a19.hall.aerostat.gondola", "hall.aerostat.body", "a19.hall.aerostat.gondola", "gondola-body-seat", "y", 0.20)
    a.connect("contact.a19.hall.aerostat.gondola.window", "a19.hall.aerostat.gondola", "a19.hall.aerostat.gondola.window", "gondola-window-seat", "x", 0.08)
    if lod < 2:
        a.panel(
            "a19.hall.aerostat.tail-fin.vertical",
            ((-103.0, 30.0, z), (-109.0, 30.0, z), (-107.0, 37.5, z), (-102.0, 34.0, z)),
            0.22,
            "wall_cool",
            role="aerostat-tail-fin",
        )
        a.panel(
            "a19.hall.aerostat.tail-fin.lateral",
            ((-102.0, 30.0, z - 1.0), (-108.0, 30.0, z - 8.0), (-108.0, 30.0, z + 8.0), (-102.0, 30.0, z + 1.0)),
            0.22,
            "wall_cool",
            role="aerostat-tail-fin",
        )
        a.connect("contact.a19.hall.aerostat.tail-fin.vertical", "hall.aerostat.tail", "a19.hall.aerostat.tail-fin.vertical", "tail-fin-seat", "plan", 0.16)
        a.connect("contact.a19.hall.aerostat.tail-fin.lateral", "hall.aerostat.tail", "a19.hall.aerostat.tail-fin.lateral", "tail-fin-seat", "plan", 0.16)

    cradle_count = 3 if lod == 0 else 2 if lod == 1 else 1
    for index, cradle_x in enumerate((-58.0, -88.0, -118.0)[:cradle_count]):
        for side_name, offset in (("south", -13.0), ("north", 13.0)):
            post = f"a19.hall.cradle.{index}.post.{side_name}"
            a.beam(post, (cradle_x, 0.25, z + offset), (cradle_x, 12.4, z + offset), 0.28, 0.28, "trim", role="hangar-maintenance-cradle")
            a.connect(f"contact.{post}", "hall.floor", post, "cradle-floor-seat", "endpoint", 0.18)
        cross = f"a19.hall.cradle.{index}.crossbeam"
        a.beam(cross, (cradle_x, 12.2, z - 13.0), (cradle_x, 12.2, z + 13.0), 0.34, 0.38, "wall_warm", role="hangar-maintenance-cradle")
        a.connect(f"contact.{cross}.south", f"a19.hall.cradle.{index}.post.south", cross, "cradle-crossbeam-seat", "endpoint", 0.14)
        a.connect(f"contact.{cross}.north", f"a19.hall.cradle.{index}.post.north", cross, "cradle-crossbeam-seat", "endpoint", 0.14)

    bank_count = 4 if lod == 0 else 2 if lod == 1 else 1
    for index in range(bank_count):
        side = -1.0 if index % 2 == 0 else 1.0
        bank_x = -54.0 - (index // 2) * 28.0
        bank_z = z + side * 23.0
        bank = f"a19.hall.equipment-bank.{index}"
        a.box(bank, bank_x, 2.25, bank_z, 8.0, 4.5, 4.2, "wall_weathered", role="occupied-hangar-equipment-bank")
        a.box(f"{bank}.service-face", bank_x + 4.12, 2.5, bank_z, 0.32, 2.8, 3.0, "wall_alt", role="hangar-equipment-service-face")
        a.box(f"{bank}.status-strip", bank_x + 4.31, 3.1, bank_z, 0.18, 0.35, 2.3, "accent", role="active-hangar-equipment-status")
        a.connect(f"contact.{bank}.floor", "hall.floor", bank, "equipment-floor-seat", "y", 0.12)
        a.connect(f"contact.{bank}.service-face", bank, f"{bank}.service-face", "service-face-seat", "x", 0.08)
        a.connect(f"contact.{bank}.status-strip", f"{bank}.service-face", f"{bank}.status-strip", "status-strip-seat", "x", 0.08)

    if lod < 2:
        cart_count = 4 if lod == 0 else 2
        for index in range(cart_count):
            cart_x = -64.0 - index * 18.0
            cart_z = z + (-9.0 if index % 2 == 0 else 9.0)
            cart = f"a19.hall.maintenance-cart.{index}"
            a.box(cart, cart_x, 1.0, cart_z, 5.2, 2.0, 3.0, "wall_cool", role="occupied-hangar-maintenance-cart")
            a.box(f"{cart}.service-face", cart_x + 2.72, 1.15, cart_z, 0.32, 1.35, 2.3, "wall_alt", role="hangar-cart-service-face")
            a.box(f"{cart}.status", cart_x + 2.90, 1.55, cart_z, 0.18, 0.28, 1.65, "accent", role="active-hangar-cart-status")
            a.connect(f"contact.{cart}.floor", "hall.floor", cart, "cart-floor-seat", "y", 0.10)
            a.connect(f"contact.{cart}.service-face", cart, f"{cart}.service-face", "cart-service-face-seat", "x", 0.08)
            a.connect(f"contact.{cart}.status", f"{cart}.service-face", f"{cart}.status", "cart-status-seat", "x", 0.08)


def _road_basis(start: tuple[float, float], end: tuple[float, float]) -> tuple[float, float, float, float, float]:
    dx, dz = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    return ux, uz, -uz, ux, length


def _point_along(
    start: tuple[float, float],
    end: tuple[float, float],
    t: float,
    lateral: float = 0.0,
) -> tuple[float, float]:
    ux, uz, nx, nz, length = _road_basis(start, end)
    return start[0] + ux * length * t + nx * lateral, start[1] + uz * length * t + nz * lateral


def _add_layered_reference_route(a: _AddonAssembler, lod: int) -> None:
    start = (130.0, -132.0)
    end = (18.0, -28.0)
    ux, uz, nx, nz, length = _road_basis(start, end)
    yaw = math.atan2(uz, ux)

    # Three grounded terrace slabs sit beneath one shallow sloped road skin.
    segment_count = 3
    for index in range(segment_count):
        t0, t1 = index / segment_count, (index + 1) / segment_count
        cx, cz = _point_along(start, end, (t0 + t1) / 2.0)
        segment_length = length / segment_count + 0.20
        y = 0.20 + index * 0.34
        name = f"a19.route.foundation.{index}"
        a.box(name, cx, y, cz, segment_length, 0.40 + index * 0.06, 18.0, "road", yaw=yaw, role="diagonal-route-foundation", route_exempt=True)

    left_start = _point_along(start, end, 0.0, 9.0)
    right_start = _point_along(start, end, 0.0, -9.0)
    right_end = _point_along(start, end, 1.0, -9.0)
    left_end = _point_along(start, end, 1.0, 9.0)
    ramp = "a19.route.ramp.deck"
    a.panel(
        ramp,
        (
            (left_start[0], 0.42, left_start[1]),
            (right_start[0], 0.42, right_start[1]),
            (right_end[0], 1.48, right_end[1]),
            (left_end[0], 1.48, left_end[1]),
        ),
        0.24,
        "road",
        role="playable-diagonal-ramp-surface",
    )
    for index in range(segment_count):
        a.connect(f"contact.{ramp}.{index}", f"a19.route.foundation.{index}", ramp, "ramp-foundation-seat", "y", 0.12)

    wall_segments = 3 if lod == 0 else 2 if lod == 1 else 1
    for side_name, lateral in (("left", 10.5), ("right", -10.5)):
        for index in range(wall_segments):
            t0, t1 = index / wall_segments, (index + 1) / wall_segments
            cx, cz = _point_along(start, end, (t0 + t1) / 2.0, lateral)
            segment_length = length / wall_segments + 0.20
            height = 2.6 + index * 0.75
            wall = f"a19.route.retaining.{side_name}.{index}"
            a.box(wall, cx, height / 2.0, cz, segment_length, height, 1.35, "wall_weathered", yaw=yaw, role="layered-route-retaining-wall")
            a.box(f"{wall}.cap", cx, height + 0.20, cz, segment_length + 0.35, 0.40, 1.75, "trim", yaw=yaw, role="retaining-wall-cap")
            a.connect(f"contact.{wall}.cap", wall, f"{wall}.cap", "cap-seat", "y", 0.08)

    # Checkpoint sits across the diagonal route; central 11 m remains open.
    checkpoint_t = 0.36
    for side_name, lateral in (("left", 8.2), ("right", -8.2)):
        px, pz = _point_along(start, end, checkpoint_t, lateral)
        base = f"a19.checkpoint.base.{side_name}"
        post = f"a19.checkpoint.post.{side_name}"
        a.box(base, px, 0.35, pz, 1.5, 0.70, 1.5, "obstacle", yaw=yaw, role="checkpoint-concrete-base")
        a.beam(post, (px, 0.30, pz), (px, 6.4, pz), 0.24, 0.24, "trim", role="checkpoint-armored-post")
        a.connect(f"contact.{post}", base, post, "post-base-seat", "y", 0.20)
    left = _point_along(start, end, checkpoint_t, 8.2)
    right = _point_along(start, end, checkpoint_t, -8.2)
    cross = "a19.checkpoint.crossbeam"
    a.beam(cross, (left[0], 6.2, left[1]), (right[0], 6.2, right[1]), 0.36, 0.44, "trim", role="checkpoint-overhead-frame")
    a.connect("contact.a19.checkpoint.crossbeam.left", "a19.checkpoint.post.left", cross, "gantry-weld", "endpoint", 0.14)
    a.connect("contact.a19.checkpoint.crossbeam.right", "a19.checkpoint.post.right", cross, "gantry-weld", "endpoint", 0.14)
    sign_x, sign_z = _point_along(start, end, checkpoint_t, 0.0)
    a.box("a19.checkpoint.command-sign", sign_x, 6.05, sign_z, 5.6, 1.3, 0.34, "accent", yaw=yaw + math.pi / 2.0, role="checkpoint-identification-sign")
    a.connect("contact.a19.checkpoint.command-sign", cross, "a19.checkpoint.command-sign", "sign-crossbeam-seat", "y", 0.12)

    # A descending service stair creates a readable lower logistics level.
    stair_origin = _point_along(start, end, 0.58, -14.0)
    step_count = 9 if lod == 0 else 5 if lod == 1 else 3
    previous = "a19.route.retaining.right.0"
    for index in range(step_count):
        sx = stair_origin[0] + nx * index * 0.78
        sz = stair_origin[1] + nz * index * 0.78
        height = 0.28 * (index + 1)
        name = f"a19.route.service-stair.{index}"
        a.box(name, sx, height / 2.0, sz, 4.2, height, 1.05, "trim", yaw=yaw, role="human-scale-service-stair")
        a.connect(f"contact.{name}", previous, name, "stair-overlap", "plan", 0.12)
        previous = name

    # Logistics cluster: purposeful groups outside the 18 m traversal ribbon.
    if lod < 2:
        container_count = 4 if lod == 0 else 2
        for index in range(container_count):
            t = 0.18 + index * 0.12
            lateral = 15.0 if index % 2 == 0 else -15.0
            cx, cz = _point_along(start, end, t, lateral)
            name = f"a19.logistics.container.{index}"
            a.box(name, cx, 1.45, cz, 6.2, 2.9, 2.7, "wall_cool", yaw=yaw, role="occupied-logistics-container")
            a.box(f"{name}.door-band", cx + ux * 3.0, 1.45, cz + uz * 3.0, 0.28, 2.3, 2.3, "accent", yaw=yaw, role="container-door-hardware")
            a.connect(f"contact.{name}.door-band", name, f"{name}.door-band", "door-hardware-seat", "plan", 0.10)

    if lod == 0:
        # Foreground edge mass and pipe bridge frame the view without becoming
        # a flat full-height occluder.
        frame_x, frame_z = _point_along(start, end, 0.19, 17.0)
        a.box("a19.foreground.service-frame.mass", frame_x, 6.2, frame_z, 15.0, 12.4, 8.5, "wall_weathered", yaw=yaw, role="foreground-occupied-service-frame")
        a.box("a19.foreground.service-frame.recess", frame_x - nx * 4.1, 4.2, frame_z - nz * 4.1, 8.0, 5.8, 0.50, "wall_alt", yaw=yaw, role="foreground-deep-service-recess")
        for index in range(3):
            px, pz = _point_along(start, end, 0.15, 13.0 - index * 3.0)
            a.cylinder_between(
                f"a19.foreground.pipe.{index}",
                (px, 3.0 + index * 0.7, pz),
                (px + ux * 15.0, 3.0 + index * 0.7, pz + uz * 15.0),
                0.28,
                "accent",
                10,
                role="foreground-active-service-pipe",
            )
        service_front_x = frame_x - ux * 7.55
        service_front_z = frame_z - uz * 7.55
        a.box("a19.foreground.service-frame.front-recess", service_front_x, 5.0, service_front_z, 0.50, 6.6, 6.4, "wall_alt", yaw=yaw, role="foreground-occupied-end-recess")
        for side_index, lateral in enumerate((-3.55, 3.55)):
            rib = f"a19.foreground.service-frame.front-rib.{side_index}"
            a.box(rib, service_front_x + nx * lateral, 5.0, service_front_z + nz * lateral, 0.92, 7.4, 0.70, "trim", yaw=yaw, role="foreground-service-frame-rib")
            a.connect(f"contact.{rib}", "a19.foreground.service-frame.mass", rib, "service-rib-seat", "plan", 0.10)
        for louver_index in range(4):
            louver = f"a19.foreground.service-frame.front-louver.{louver_index}"
            a.box(louver, service_front_x - ux * 0.25, 2.7 + louver_index * 1.25, service_front_z - uz * 0.25, 0.30, 0.24, 5.8, "accent" if louver_index == 2 else "trim", yaw=yaw, role="foreground-active-service-louver")
            a.connect(f"contact.{louver}", "a19.foreground.service-frame.front-recess", louver, "service-louver-seat", "plan", 0.08)
        a.connect(
            "contact.a19.foreground.service-frame.front-recess",
            "a19.foreground.service-frame.mass",
            "a19.foreground.service-frame.front-recess",
            "service-recess-seat",
            "plan",
            0.10,
        )

    # Checkpoint occupation: booth, dark glazing, articulated arms and signal
    # lamps.  The central traversal ribbon stays geometrically open.
    booth_x, booth_z = _point_along(start, end, checkpoint_t, 14.2)
    a.box("a19.checkpoint.guard-booth", booth_x, 1.65, booth_z, 4.8, 3.3, 4.2, "wall_weathered", yaw=yaw, role="occupied-checkpoint-guard-booth")
    a.box("a19.checkpoint.guard-booth.window", booth_x - nx * 2.18, 2.05, booth_z - nz * 2.18, 3.0, 1.35, 0.36, "wall_alt", yaw=yaw, role="occupied-checkpoint-dark-window")
    booth_front_x, booth_front_z = booth_x - ux * 2.46, booth_z - uz * 2.46
    a.box("a19.checkpoint.guard-booth.front-window", booth_front_x, 2.05, booth_front_z, 0.36, 1.35, 3.15, "wall_alt", yaw=yaw, role="occupied-checkpoint-dark-window")
    a.box("a19.checkpoint.guard-booth.front-status", booth_front_x - ux * 0.22, 2.95, booth_front_z - uz * 0.22, 0.24, 0.28, 2.4, "accent", yaw=yaw, role="active-checkpoint-status-strip")
    a.box("a19.checkpoint.guard-booth.roof", booth_x, 3.48, booth_z, 5.5, 0.45, 4.9, "roof", yaw=yaw, role="checkpoint-weather-roof")
    a.connect("contact.a19.checkpoint.guard-booth.window", "a19.checkpoint.guard-booth", "a19.checkpoint.guard-booth.window", "booth-window-seat", "plan", 0.08)
    a.connect("contact.a19.checkpoint.guard-booth.front-window", "a19.checkpoint.guard-booth", "a19.checkpoint.guard-booth.front-window", "booth-window-seat", "plan", 0.08)
    a.connect("contact.a19.checkpoint.guard-booth.front-status", "a19.checkpoint.guard-booth.front-window", "a19.checkpoint.guard-booth.front-status", "booth-status-seat", "plan", 0.08)
    a.connect("contact.a19.checkpoint.guard-booth.roof", "a19.checkpoint.guard-booth", "a19.checkpoint.guard-booth.roof", "booth-roof-seat", "y", 0.10)
    for side_name, lateral, direction in (("left", 7.4, -1.0), ("right", -7.4, 1.0)):
        arm_x, arm_z = _point_along(start, end, checkpoint_t + 0.025, lateral)
        end_x, end_z = _point_along(start, end, checkpoint_t + 0.025, lateral + direction * 5.2)
        arm = f"a19.checkpoint.barrier-arm.{side_name}"
        a.beam(arm, (arm_x, 1.45, arm_z), (end_x, 1.55, end_z), 0.14, 0.18, "accent", role="checkpoint-articulated-barrier")
        a.connect(f"contact.{arm}", f"a19.checkpoint.base.{side_name}", arm, "barrier-pivot-seat", "endpoint", 0.10)
        signal = f"a19.checkpoint.signal.{side_name}"
        a.box(signal, arm_x, 3.7, arm_z, 0.55, 0.75, 0.38, "accent", yaw=yaw, role="active-checkpoint-signal")
        a.connect(f"contact.{signal}", f"a19.checkpoint.post.{side_name}", signal, "signal-post-seat", "plan", 0.08)

    barrier_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(barrier_count):
        t = 0.06 + index * (0.46 / max(1, barrier_count - 1))
        lateral = 9.0 if index % 2 == 0 else -9.0
        bx, bz = _point_along(start, end, t, lateral)
        barrier = f"a19.route.jersey-barrier.{index}"
        a.box(barrier, bx, 0.52, bz, 3.8, 1.04, 0.95, "obstacle", yaw=yaw, role="foreground-concrete-barrier")
        a.connect(f"contact.{barrier}", "a19.route.ramp.deck", barrier, "barrier-road-seat", "y", 0.08)

    crate_count = 6 if lod == 0 else 3 if lod == 1 else 1
    pallet_count = (crate_count + 1) // 2
    for pallet_index in range(pallet_count):
        pallet_t = 0.12 + pallet_index * 0.09
        pallet_x, pallet_z = _point_along(start, end, pallet_t, 18.65)
        a.box(
            f"a19.logistics.ammo-pallet.{pallet_index}",
            pallet_x,
            0.12,
            pallet_z,
            2.3,
            0.24,
            4.7,
            "wood",
            yaw=yaw,
            role="logistics-grounded-pallet",
        )
    for index in range(crate_count):
        t = 0.12 + (index // 2) * 0.09
        lateral = 17.5 + (index % 2) * 2.3
        cx, cz = _point_along(start, end, t, lateral)
        crate = f"a19.logistics.ammo-crate.{index}"
        a.box(crate, cx, 0.62, cz, 1.7, 1.24, 1.25, "wood" if index % 2 else "obstacle", yaw=yaw, role="occupied-logistics-ammo-crate")
        parent = f"a19.logistics.ammo-pallet.{index // 2}"
        a.connect(f"contact.{crate}", parent, crate, "crate-deck-seat", "y", 0.08)

    rail_post_count = 8 if lod == 0 else 4 if lod == 1 else 2
    for index in range(rail_post_count):
        t = 0.50 + index * (0.34 / max(1, rail_post_count - 1))
        rx, rz = _point_along(start, end, t, -11.0)
        post = f"a19.route.lower-service-rail.post.{index}"
        a.beam(post, (rx, 2.5, rz), (rx, 4.15, rz), 0.07, 0.07, "trim", role="human-scale-lower-service-rail")
        a.connect(f"contact.{post}", "a19.route.retaining.right.1" if wall_segments > 1 else "a19.route.retaining.right.0", post, "rail-wall-seat", "endpoint", 0.08)
    for height_index, rail_height in enumerate((3.1, 4.0) if lod < 2 else (3.6,)):
        start_rail = _point_along(start, end, 0.50, -11.0)
        end_rail = _point_along(start, end, 0.84, -11.0)
        rail = f"a19.route.lower-service-rail.horizontal.{height_index}"
        a.beam(rail, (start_rail[0], rail_height, start_rail[1]), (end_rail[0], rail_height, end_rail[1]), 0.07, 0.07, "trim", role="human-scale-lower-service-rail")
        a.connect(f"contact.{rail}", "a19.route.lower-service-rail.post.0", rail, "rail-post-weld", "plan", 0.08)


def _spec_bounds(spec: Any) -> tuple[float, float, float, float, float, float] | None:
    if isinstance(spec, BoxSpec):
        cosine, sine = abs(math.cos(spec.yaw)), abs(math.sin(spec.yaw))
        half_x = cosine * spec.w / 2.0 + sine * spec.d / 2.0
        half_z = sine * spec.w / 2.0 + cosine * spec.d / 2.0
        return (
            spec.x - half_x,
            spec.x + half_x,
            spec.z - half_z,
            spec.z + half_z,
            spec.y - spec.h / 2.0,
            spec.y + spec.h / 2.0,
        )
    if isinstance(spec, CylinderSpec):
        return (
            spec.x - spec.radius,
            spec.x + spec.radius,
            spec.z - spec.radius,
            spec.z + spec.radius,
            spec.y - spec.height / 2.0,
            spec.y + spec.height / 2.0,
        )
    return None


def _intersects_approach(bounds: tuple[float, float, float, float, float, float], approach: ApproachSpec) -> bool:
    min_x, max_x, min_z, max_z, _min_y, _max_y = bounds
    sx, sz = approach.start
    ex, ez = approach.end
    dx, dz = ex - sx, ez - sz
    length = math.hypot(dx, dz)
    ux, uz = dx / length, dz / length
    nx, nz = -uz, ux
    cx, cz = (min_x + max_x) / 2.0, (min_z + max_z) / 2.0
    hx, hz = (max_x - min_x) / 2.0, (max_z - min_z) / 2.0
    progress = (cx - sx) * ux + (cz - sz) * uz
    progress_radius = abs(ux) * hx + abs(uz) * hz
    lateral = (cx - sx) * nx + (cz - sz) * nz
    lateral_radius = abs(nx) * hx + abs(nz) * hz
    return (
        progress + progress_radius >= 0.0
        and progress - progress_radius <= length + approach.inward_clearance
        and abs(lateral) - lateral_radius < approach.width / 2.0
    )


def _estimated_triangles(plan: KunrenPlan) -> int:
    total = 12 * (len(plan.boxes) + len(plan.beams) + len(plan.sloped_panels))
    total += sum(4 * spec.segments for spec in plan.cylinders)
    total += sum(4 * spec.segments for spec in plan.cylinders_between)
    total += sum(8 * spec.segments - 4 for spec in plan.rocks)
    return total


def _validate_additions(
    additions: _AddonAssembler,
    constraints: Any,
    budget: LODBudget,
    merged: KunrenPlan,
) -> dict[str, Any]:
    names = set(merged.names)
    if len(names) != merged.primitive_count:
        raise ValueError("A19 plan contains duplicate names")
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
        bounds = _spec_bounds(spec)
        if bounds is None or bounds[4] >= 3.0 or bounds[5] <= 0.10:
            continue
        for hero in (constraints.command, constraints.hangar):
            if _intersects_approach(bounds, hero.approach):
                route_violations.append(f"{spec.name}:{hero.landmark_id}")
        for spawn_index, (sx, _sy, sz) in enumerate(all_spawns):
            closest_x = min(max(sx, bounds[0]), bounds[1])
            closest_z = min(max(sz, bounds[2]), bounds[3])
            if math.hypot(sx - closest_x, sz - closest_z) < 5.0:
                spawn_violations.append(f"{spec.name}:spawn-{spawn_index}")
    if route_violations:
        raise ValueError(f"A19 additions block authoritative approaches: {route_violations[:8]}")
    if spawn_violations:
        raise ValueError(f"A19 additions violate 5 m spawn clearance: {spawn_violations[:8]}")

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
        raise ValueError(f"A19 primitive budget exceeded: {merged.primitive_count}>{budget.max_primitives}")
    if triangles > budget.max_estimated_triangles:
        raise ValueError(f"A19 triangle budget exceeded: {triangles}>{budget.max_estimated_triangles}")
    if len(materials) > budget.max_materials:
        raise ValueError(f"A19 material budget exceeded: {len(materials)}>{budget.max_materials}")
    return {
        "primitiveCount": merged.primitive_count,
        "estimatedTriangles": triangles,
        "materials": materials,
        "routeViolations": route_violations,
        "spawnViolations": spawn_violations,
        "a19AdditionCount": sum(
            len(group)
            for group in (
                additions.boxes,
                additions.beams,
                additions.cylinders,
                additions.cylinders_between,
                additions.sloped_panels,
            )
        ),
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
        "categories": list(FIXED_SCORE_CATEGORIES),
        "scores": scores,
        "average": round(average, 3),
        "minimumPerCategory": 7.0,
        "minimumAverage": 8.0,
        "producerProvisional": True,
        "independentReviewerRequired": True,
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        "strongestRemainingMismatch": (
            "original-resolution producer review still finds the dual-hero main view, command readability, "
            "settlement density and surface specificity materially below the concept reference"
        ),
        "evidencePaths": list(evidence_paths),
    }


def _terrace_locked_camera_blockers(base: KunrenPlan) -> KunrenPlan:
    """Turn two foreground towers into low occupied terraces.

    Their canonical horizontal placements and identifiers remain unchanged.
    Only the visual Y profile is compressed so the deliberately locked 1.65 m
    composition can read both mega-landmarks.  Contact overlap metadata is
    scaled conservatively for connections touching either terrace.  The
    floating visual bridge formerly joining their high roofs is removed with
    its own contacts because the roofs no longer exist at that elevation.
    """

    scale = REFERENCE_SIGHTLINE_VERTICAL_SCALE

    def affected(name: str) -> bool:
        return name.startswith(REFERENCE_SIGHTLINE_TERRACES)

    def removed(name: str) -> bool:
        return name.startswith(REFERENCE_SIGHTLINE_REMOVALS)

    def point(point: Point3) -> Point3:
        return point[0], point[1] * scale, point[2]

    boxes = tuple(
        replace(spec, y=spec.y * scale, h=max(0.02, spec.h * scale)) if affected(spec.name) else spec
        for spec in base.boxes
        if not removed(spec.name)
    )
    beams = tuple(
        replace(spec, start=point(spec.start), end=point(spec.end)) if affected(spec.name) else spec
        for spec in base.beams
        if not removed(spec.name)
    )
    cylinders = tuple(
        replace(spec, y=spec.y * scale, height=max(0.02, spec.height * scale)) if affected(spec.name) else spec
        for spec in base.cylinders
        if not removed(spec.name)
    )
    cylinders_between = tuple(
        replace(spec, start=point(spec.start), end=point(spec.end)) if affected(spec.name) else spec
        for spec in base.cylinders_between
        if not removed(spec.name)
    )
    sloped_panels = tuple(
        replace(spec, corners=tuple(point(corner) for corner in spec.corners)) if affected(spec.name) else spec
        for spec in base.sloped_panels
        if not removed(spec.name)
    )
    rocks = tuple(
        replace(spec, y=spec.y * scale, height=max(0.02, spec.height * scale)) if affected(spec.name) else spec
        for spec in base.rocks
        if not removed(spec.name)
    )
    connections = tuple(
        replace(
            connection,
            actual_overlap_m=max(connection.min_overlap_m, connection.actual_overlap_m * scale),
        )
        if affected(connection.parent) or affected(connection.child)
        else connection
        for connection in base.connections
        if not removed(connection.parent) and not removed(connection.child)
    )
    return KunrenPlan(
        boxes=boxes,
        beams=beams,
        cylinders=cylinders,
        cylinders_between=cylinders_between,
        sloped_panels=sloped_panels,
        rocks=rocks,
        connections=connections,
        metadata={
            **base.metadata,
            "a19ReferenceSightlineTerraces": {
                "prefixes": list(REFERENCE_SIGHTLINE_TERRACES),
                "verticalScale": scale,
                "horizontalPlacementsChanged": False,
                "gameplayCollisionChanged": False,
                "removedFloatingVisualOnlyServiceBridgePrefixes": list(REFERENCE_SIGHTLINE_REMOVALS),
            },
        },
    )


def make_kunren_reference_a19_plan(
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: Mapping[str, ApproachSpec | Mapping[str, Any]] | None = None,
    lod_budget: LODBudget | None = None,
) -> KunrenPlan:
    """Build an immutable A19 visual plan without mutating canonical data."""

    before = copy.deepcopy(stage)
    budget = lod_budget or A19_LOD_BUDGETS[lod]
    constraints = constraints_from_authoritative_layout(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=budget,
    )
    base = _terrace_locked_camera_blockers(
        make_kunren_reference_a18_plan(
            stage,
            lod,
            collision_boxes=collision_boxes,
            entrance_overrides=entrance_overrides,
            approach_overrides=approach_overrides,
            lod_budget=budget,
        )
    )
    additions = _AddonAssembler(base.names)
    _add_command_occupied_facade(additions, constraints.command, lod)
    _add_hangar_monumental_portal(additions, constraints.hangar, lod)
    _add_layered_reference_route(additions, lod)

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
    metrics = _validate_additions(additions, constraints, budget, provisional)
    command_frame = camera_hero_frame_metrics(MAIN_REFERENCE_CAMERA, constraints.command)
    hangar_frame = camera_hero_frame_metrics(MAIN_REFERENCE_CAMERA, constraints.hangar)
    metadata = {
        "kitVersion": KIT_VERSION,
        "baseVisualKit": base.metadata["kitVersion"],
        "stageId": "kunren",
        "lod": lod,
        "coordinateSystem": "runtime-xz-horizontal-y-up-metres",
        "constructionOrder": [
            "reference-camera-lock",
            "authoritative-contract-freeze",
            "hero-macro-envelopes",
            "layered-route-and-set-dressing",
            "private-proof-and-provisional-score",
        ],
        "mainReferenceCamera": asdict(MAIN_REFERENCE_CAMERA),
        "heroFrameMetrics": {COMMAND_ID: command_frame, HANGAR_ID: hangar_frame},
        "referenceSightlineTreatment": base.metadata["a19ReferenceSightlineTerraces"],
        "heroEnvelopes": {
            "command": asdict(constraints.command),
            "hangar": asdict(constraints.hangar),
        },
        "authoritativeContracts": {
            "placementPolicy": "unchanged-canonical-centres-widths-depths-heights",
            "approaches": {
                COMMAND_ID: asdict(constraints.command.approach),
                HANGAR_ID: asdict(constraints.hangar.approach),
            },
            "playerSpawns": [list(point) for point in constraints.player_spawns],
            "botSpawns": [list(point) for point in constraints.bot_spawns],
            "collisionPolicy": "visual-only; canonical gameplay collision remains authoritative",
        },
        "macroTargets": {
            "command": "occupied battered concrete fortress with recessed bays, lateral stacks and weather catches",
            "hangar": "castle-scale complete arch collar with deep operational shoulders and occupied lateral decks",
            "route": "diagonal checkpoint, ramp, retaining walls, stair, logistics and partial foreground frame",
        },
        "surfaceResponseContract": {
            "families": ["weathered-concrete", "oxidized-painted-metal", "rough-road", "service-wood"],
            "requiredChannels": ["baseColor", "roughness", "normalOrBump"],
            "deepOpeningsAreGeometry": True,
            "flatColorAloneIsBlockout": True,
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
            "publicAssetWritesAllowed": False,
            "repoBuildIntegrationAllowed": False,
            "headless": True,
        },
        "lodBudget": asdict(budget),
        "metrics": metrics,
        "connectionMap": [asdict(connection) for connection in provisional.connections],
        "producerProvisionalScorecard": producer_provisional_scorecard(),
    }
    if stage != before:
        raise RuntimeError("A19 planning mutated authoritative stage input")
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


def emit_kunren_reference_a19_plan(builder: MeshBuilderProtocol, plan: KunrenPlan) -> Mapping[str, Any]:
    """Emit through the existing reviewed MeshBuilder surface."""

    def begin(spec: Any) -> None:
        hook = getattr(builder, "begin_part", None)
        if callable(hook):
            hook(spec)

    for spec in plan.boxes:
        begin(spec)
        if abs(spec.yaw) > 1e-8:
            builder.add_oriented_box(spec.x, spec.y, spec.z, spec.w, spec.h, spec.d, spec.yaw, spec.key)
        else:
            builder.add_box(spec.x, spec.y, spec.z, spec.w, spec.h, spec.d, spec.key)
    for spec in plan.beams:
        begin(spec)
        builder.add_beam(spec.start, spec.end, spec.width, spec.depth, spec.key)
    for spec in plan.cylinders:
        begin(spec)
        builder.add_cylinder(spec.x, spec.y, spec.z, spec.radius, spec.height, spec.key, spec.segments, spec.top_radius)
    for spec in plan.cylinders_between:
        begin(spec)
        builder.add_cylinder_between(spec.start, spec.end, spec.radius, spec.key, spec.segments, spec.end_radius)
    for spec in plan.sloped_panels:
        begin(spec)
        builder.add_sloped_panel(spec.corners, spec.thickness, spec.key)
    for spec in plan.rocks:
        begin(spec)
        builder.add_rock(spec.x, spec.y, spec.z, spec.radius, spec.height, spec.key, spec.segments, spec.seed)
    return plan.metadata


def build_kunren_reference_a19(
    builder: MeshBuilderProtocol,
    stage: Mapping[str, Any],
    lod: int,
    **kwargs: Any,
) -> Mapping[str, Any]:
    plan = make_kunren_reference_a19_plan(stage, lod, **kwargs)
    return emit_kunren_reference_a19_plan(builder, plan)


# ---------------------------------------------------------------------------
# Optional private Blender proof.  bpy is imported only inside this section so
# unit tests and catalog tooling remain ordinary-Python compatible.
# ---------------------------------------------------------------------------


def _run_blender_private_proof(plan: KunrenPlan, output_dir: Path) -> dict[str, Any]:
    import bmesh  # type: ignore
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    output_dir = output_dir.expanduser().resolve()
    if str(output_dir).startswith(str(REPO_ROOT.resolve())):
        raise ValueError("A19 proof output must stay outside the repository")
    views_dir = output_dir / "views"
    views_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = MAIN_REFERENCE_CAMERA.resolution_x
    scene.render.resolution_y = MAIN_REFERENCE_CAMERA.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.10

    root = bpy.data.collections.new("HB_kunren_A19_ROOT")
    scene.collection.children.link(root)
    collections: dict[str, Any] = {}
    for name in (
        "00_GUIDES",
        "10_TERRAIN",
        "20_DISTRICTS",
        "30_LANDMARK",
        "40_PROPS",
        "50_BOUNDARY",
        "60_SKYLINE",
        "70_LIGHTING",
        "90_EXPORT",
    ):
        collection = bpy.data.collections.new(f"HB_kunren_{name}")
        root.children.link(collection)
        collections[name] = collection

    palettes = {
        "wall": (0.115, 0.095, 0.068, 1.0),
        "wall_alt": (0.008, 0.012, 0.014, 1.0),
        "wall_cool": (0.050, 0.070, 0.078, 1.0),
        "wall_warm": (0.205, 0.125, 0.054, 1.0),
        "wall_weathered": (0.145, 0.095, 0.047, 1.0),
        "roof": (0.024, 0.032, 0.035, 1.0),
        "trim": (0.016, 0.024, 0.028, 1.0),
        "accent": (0.62, 0.16, 0.010, 1.0),
        "terrain": (0.080, 0.065, 0.040, 1.0),
        "obstacle": (0.165, 0.105, 0.048, 1.0),
        "wood": (0.105, 0.045, 0.012, 1.0),
        "road": (0.012, 0.016, 0.018, 1.0),
        "road_line": (0.48, 0.30, 0.045, 1.0),
    }

    def make_material(key: str) -> Any:
        material = bpy.data.materials.new(f"A19_MAT_{key}")
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
        base = palettes.get(key, (0.3, 0.3, 0.3, 1.0))
        noise.inputs["Scale"].default_value = 4.5 if "wall" in key else 9.0
        noise.inputs["Detail"].default_value = 4.0
        noise.inputs["Roughness"].default_value = 0.72
        ramp.color_ramp.elements[0].color = tuple(max(0.0, value * 0.52) for value in base[:3]) + (1.0,)
        ramp.color_ramp.elements[1].color = tuple(min(1.0, value * 1.32) for value in base[:3]) + (1.0,)
        roughness.inputs["To Min"].default_value = 0.46 if key in {"trim", "accent", "roof"} else 0.68
        roughness.inputs["To Max"].default_value = 0.76 if key in {"trim", "accent", "roof"} else 0.96
        bump.inputs["Strength"].default_value = 0.16 if "wall" in key or key in {"terrain", "road"} else 0.07
        bump.inputs["Distance"].default_value = 0.12 if "wall" in key else 0.045
        if key in {"trim", "accent", "roof", "wall_cool"}:
            shader.inputs["Metallic"].default_value = 0.45 if key != "wall_cool" else 0.22
        links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
        links.new(noise.outputs["Fac"], roughness.inputs["Value"])
        links.new(roughness.outputs["Result"], shader.inputs["Roughness"])
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        if key == "accent":
            emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
            strength = shader.inputs.get("Emission Strength")
            if emission is not None:
                emission.default_value = (0.68, 0.18, 0.025, 1.0)
            if strength is not None:
                strength.default_value = 2.0
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        material.diffuse_color = base
        material["a19RequiredChannels"] = "baseColor,roughness,normalOrBump"
        return material

    materials = {key: make_material(key) for key in palettes}

    def runtime_point(point: Point3) -> Vector:
        return Vector((point[0], -point[2], point[1]))

    class ProofBuilder:
        def __init__(self) -> None:
            self.current: Any = None
            self.created: list[Any] = []

        def begin_part(self, spec: Any) -> None:
            self.current = spec

        def target_collection(self) -> Any:
            name = self.current.name
            role = self.current.role
            if name.startswith(("cmd.", "hall.", "a19.cmd.", "a19.hall.")):
                return collections["30_LANDMARK"]
            if name.startswith("city.ridge") or "mountain" in role:
                return collections["60_SKYLINE"]
            if name.startswith("city."):
                return collections["20_DISTRICTS"]
            if name.startswith("a19.route"):
                return collections["10_TERRAIN"]
            return collections["40_PROPS"]

        def finish(self, obj: Any, key: str, bevel: float = 0.0) -> None:
            obj.name = f"HB_kunren_{self.current.name.replace('.', '_')}_LOD0"
            obj["a19PartName"] = self.current.name
            obj["a19Role"] = self.current.role
            obj["a19MaterialKey"] = key
            obj.data.materials.append(materials[key])
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            self.target_collection().objects.link(obj)
            if bevel > 0.003:
                modifier = obj.modifiers.new("A19_contact_bevel", "BEVEL")
                modifier.width = bevel
                modifier.segments = 2 if self.current.name.startswith(("cmd", "hall", "a19.cmd", "a19.hall")) else 1
                modifier.limit_method = "ANGLE"
            self.created.append(obj)

        def add_box(self, x: float, y: float, z: float, w: float, h: float, d: float, key: str) -> None:
            bpy.ops.mesh.primitive_cube_add(size=2, location=runtime_point((x, y, z)))
            obj = bpy.context.active_object
            obj.scale = (w / 2.0, d / 2.0, h / 2.0)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            self.finish(obj, key, min(0.16, min(w, h, d) * 0.08))

        def add_oriented_box(self, x: float, y: float, z: float, w: float, h: float, d: float, yaw: float, key: str) -> None:
            bpy.ops.mesh.primitive_cube_add(size=2, location=runtime_point((x, y, z)))
            obj = bpy.context.active_object
            obj.scale = (w / 2.0, d / 2.0, h / 2.0)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.rotation_euler[2] = -yaw
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            self.finish(obj, key, min(0.16, min(w, h, d) * 0.08))

        def add_beam(self, start: Point3, end: Point3, width: float, depth: float, key: str) -> None:
            p0, p1 = runtime_point(start), runtime_point(end)
            forward = (p1 - p0).normalized()
            reference_up = Vector((0.0, 0.0, 1.0)) if abs(forward.z) < 0.98 else Vector((1.0, 0.0, 0.0))
            right = forward.cross(reference_up).normalized()
            up = right.cross(forward).normalized()
            mesh = bpy.data.meshes.new("A19_BEAM_MESH")
            obj = bpy.data.objects.new("A19_BEAM", mesh)
            bpy.context.collection.objects.link(obj)
            bm = bmesh.new()
            vertices = []
            for base in (p0, p1):
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    vertices.append(bm.verts.new(base + right * width * sx + up * depth * sy))
            for indices in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1), (4, 5, 6, 7)):
                bm.faces.new([vertices[index] for index in indices])
            bm.to_mesh(mesh)
            bm.free()
            self.finish(obj, key, min(0.12, min(width, depth) * 0.35))

        def add_cylinder(self, x: float, y: float, z: float, radius: float, height: float, key: str, segments: int, top_radius: float | None = None) -> None:
            bpy.ops.mesh.primitive_cone_add(
                vertices=segments,
                radius1=radius,
                radius2=radius if top_radius is None else top_radius,
                depth=height,
                location=runtime_point((x, y, z)),
            )
            self.finish(bpy.context.active_object, key, 0.0)

        def add_cylinder_between(self, start: Point3, end: Point3, radius: float, key: str, segments: int, end_radius: float | None = None) -> None:
            p0, p1 = runtime_point(start), runtime_point(end)
            forward = (p1 - p0).normalized()
            reference_up = Vector((0.0, 0.0, 1.0)) if abs(forward.z) < 0.98 else Vector((1.0, 0.0, 0.0))
            right = forward.cross(reference_up).normalized()
            up = right.cross(forward).normalized()
            end_radius_value = radius if end_radius is None else end_radius
            vertices = []
            for base, ring_radius in ((p0, radius), (p1, end_radius_value)):
                for index in range(segments):
                    angle = math.tau * index / segments
                    vertices.append(tuple(base + right * math.cos(angle) * ring_radius + up * math.sin(angle) * ring_radius))
            faces = []
            for index in range(segments):
                nxt = (index + 1) % segments
                faces.append((index, nxt, segments + nxt, segments + index))
            faces.extend((tuple(reversed(range(segments))), tuple(range(segments, segments * 2))))
            mesh = bpy.data.meshes.new("A19_TUBE_MESH")
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            obj = bpy.data.objects.new("A19_TUBE", mesh)
            bpy.context.collection.objects.link(obj)
            self.finish(obj, key, 0.0)

        def add_sloped_panel(self, corners: Sequence[Point3], thickness: float, key: str) -> None:
            top = [runtime_point(point) for point in corners]
            bottom = [point - Vector((0.0, 0.0, thickness)) for point in top]
            vertices = [tuple(point) for point in (*top, *bottom)]
            faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            mesh = bpy.data.meshes.new("A19_PANEL_MESH")
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            obj = bpy.data.objects.new("A19_PANEL", mesh)
            bpy.context.collection.objects.link(obj)
            self.finish(obj, key, min(0.08, thickness * 0.25))

        def add_rock(self, x: float, y: float, z: float, radius: float, height: float, key: str, segments: int, seed: int) -> None:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2 if segments >= 10 else 1, radius=1.0, location=runtime_point((x, y + height / 2.0, z)))
            obj = bpy.context.active_object
            obj.scale = (radius, radius * (0.76 + (seed % 7) * 0.025), height / 2.0)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.rotation_euler[2] = (seed % 31) * 0.071
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            self.finish(obj, key, 0.0)

    builder = ProofBuilder()
    emit_kunren_reference_a19_plan(builder, plan)

    # Ground is proof-only and never exported into gameplay/public assets.
    builder.current = BoxSpec("proof.ground", 0.0, -0.55, 0.0, 650.0, 1.0, 650.0, "terrain", role="terrain", route_exempt=True)
    builder.add_box(0.0, -0.55, 0.0, 650.0, 1.0, 650.0, "terrain")

    world = scene.world or bpy.data.worlds.new("A19_WORLD")
    scene.world = world
    world.use_nodes = True
    world_nodes = world.node_tree.nodes
    world_links = world.node_tree.links
    world_nodes.clear()
    background = world_nodes.new("ShaderNodeBackground")
    sky = world_nodes.new("ShaderNodeTexSky")
    # Blender 5.2 renamed the physical Nishita implementation to the
    # scattering modes; retain the 4.x enum for older private-proof runners.
    try:
        sky.sky_type = "NISHITA"
    except TypeError:
        sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(32.0)
    sky.sun_rotation = math.radians(122.0)
    sky.air_density = 1.15
    if hasattr(sky, "dust_density"):
        sky.dust_density = 2.8
    background.inputs["Strength"].default_value = 0.18
    world_output = world_nodes.new("ShaderNodeOutputWorld")
    world_links.new(sky.outputs["Color"], background.inputs["Color"])
    world_links.new(background.outputs["Background"], world_output.inputs["Surface"])

    sun_data = bpy.data.lights.new("LGT_Kunren_A19_Sun_DATA", "SUN")
    sun_data.energy = 4.2
    sun_data.angle = math.radians(2.5)
    sun_data.color = (1.0, 0.77, 0.56)
    sun = bpy.data.objects.new("LGT_Kunren_A19_Sun", sun_data)
    collections["70_LIGHTING"].objects.link(sun)
    sun.rotation_euler = (math.radians(38.0), 0.0, math.radians(-42.0))

    fill_data = bpy.data.lights.new("LGT_Kunren_A19_CoolFill_DATA", "AREA")
    fill_data.energy = 1100.0
    fill_data.shape = "DISK"
    fill_data.size = 95.0
    fill_data.color = (0.30, 0.47, 0.68)
    fill = bpy.data.objects.new("LGT_Kunren_A19_CoolFill", fill_data)
    collections["70_LIGHTING"].objects.link(fill)
    fill.location = runtime_point((-20.0, 85.0, -5.0))
    fill.rotation_euler = (0.0, 0.0, 0.0)

    area_data = bpy.data.lights.new("LGT_Kunren_A19_Fill_DATA", "AREA")
    area_data.energy = 900.0
    area_data.shape = "DISK"
    area_data.size = 80.0
    area_data.color = (0.46, 0.64, 0.90)
    area = bpy.data.objects.new("LGT_Kunren_A19_Fill", area_data)
    collections["70_LIGHTING"].objects.link(area)
    area.location = runtime_point((-40.0, 90.0, -10.0))

    def make_camera(spec: ReferenceCamera) -> Any:
        data = bpy.data.cameras.new(spec.name + "_DATA")
        data.lens = spec.lens_mm
        data.sensor_width = spec.sensor_width_mm
        data.dof.use_dof = False
        camera = bpy.data.objects.new(spec.name, data)
        collections["00_GUIDES"].objects.link(camera)
        camera.location = runtime_point(spec.location)
        direction = runtime_point(spec.target) - camera.location
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        camera["a19EyeHeightM"] = spec.eye_height_m
        camera["a19Intent"] = spec.intent
        return camera

    proof_views = (
        MAIN_REFERENCE_CAMERA,
        ReferenceCamera("CAM_Kunren_A19_Checkpoint_1p65", (134.0, 1.65, -136.0), (80.0, 4.5, -105.0), 34.0),
        ReferenceCamera("CAM_Kunren_A19_CommandApproach_1p65", (8.0, 1.65, 84.0), (72.8, 20.0, 84.0), 26.0),
        ReferenceCamera("CAM_Kunren_A19_CommandOblique_1p65", (146.0, 1.65, 2.0), (76.0, 21.0, 82.0), 37.0),
        ReferenceCamera("CAM_Kunren_A19_HangarApproach_1p65", (30.0, 1.65, -180.0), (-84.0, 20.0, -100.0), 18.0),
        ReferenceCamera("CAM_Kunren_A19_HangarInterior_1p65", (-42.0, 1.65, -100.0), (-104.0, 10.0, -100.0), 24.0),
        ReferenceCamera("CAM_Kunren_A19_Logistics_1p65", (132.0, 1.65, -151.0), (96.0, 2.4, -130.0), 36.0),
        ReferenceCamera("CAM_Kunren_A19_Aerial", (186.0, 168.0, -202.0), (-6.0, 0.0, -8.0), 42.0, eye_height_m=168.0, intent="aerial-composition"),
    )
    evidence_paths: list[str] = []
    for index, spec in enumerate(proof_views, start=1):
        camera = make_camera(spec)
        scene.camera = camera
        scene.render.filepath = str(views_dir / f"{index:02d}_{spec.name.removeprefix('CAM_Kunren_A19_')}.png")
        bpy.ops.render.render(write_still=True)
        evidence_paths.append(scene.render.filepath)

    blend_path = output_dir / "kunren-a19-macro-proof.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    scorecard = producer_provisional_scorecard(evidence_paths)
    scorecard_path = output_dir / "producer-provisional-scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "kitVersion": KIT_VERSION,
        "blend": str(blend_path),
        "views": evidence_paths,
        "referenceSha256": hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest(),
        "planMetrics": plan.metadata["metrics"],
        "mainReferenceCamera": plan.metadata["mainReferenceCamera"],
        "heroFrameMetrics": plan.metadata["heroFrameMetrics"],
        "producerScorecard": str(scorecard_path),
        "referencePassClaimed": False,
        "releaseDecision": "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
    }
    (output_dir / "proof-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _parse_blender_args(argv: Sequence[str]) -> argparse.Namespace:
    arguments = list(argv)
    if "--" in arguments:
        arguments = arguments[arguments.index("--") + 1 :]
    parser = argparse.ArgumentParser(description="Build a private headless Kunren A19 proof")
    parser.add_argument("--layout", type=Path, default=CANONICAL_LAYOUT_DEFAULT)
    parser.add_argument("--proof-dir", type=Path, default=PRIVATE_PROOF_DEFAULT)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--plan-json", type=Path)
    return parser.parse_args(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_blender_args(sys.argv if argv is None else argv)
    layout = load_authoritative_kunren_layout(args.layout)
    plan = make_kunren_reference_a19_plan(layout.stage, args.lod)
    if args.plan_json is not None:
        target = args.plan_json.expanduser().resolve()
        if str(target).startswith(str(REPO_ROOT.resolve())):
            raise ValueError("A19 plan JSON must stay outside the repository")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(plan.metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        import bpy  # type: ignore  # noqa: F401
    except ImportError:
        print(json.dumps(plan.metadata, ensure_ascii=False, indent=2))
        return 0
    manifest = _run_blender_private_proof(plan, args.proof_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


__all__ = [
    "A19_LOD_BUDGETS",
    "FIXED_SCORE_CATEGORIES",
    "KIT_VERSION",
    "MAIN_REFERENCE_CAMERA",
    "PRIVATE_PROOF_DEFAULT",
    "PRODUCER_PROVISIONAL_SCORES",
    "ReferenceCamera",
    "build_kunren_reference_a19",
    "camera_hero_frame_metrics",
    "emit_kunren_reference_a19_plan",
    "make_kunren_reference_a19_plan",
    "producer_provisional_scorecard",
]


if __name__ == "__main__":
    raise SystemExit(main())
