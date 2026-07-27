"""Reference-led A18 visual kit for Hibana's Kunren stage.

The module is intentionally independent from ``build_all_stages.py`` so it can
be reviewed and tested while the catalog generator is changing.  It consumes
the frozen layout shape and the small MeshBuilder protocol, but imports neither
Blender nor the catalog generator.  Geometry is authored in Hibana runtime
coordinates: X/Z are horizontal and Y is up, in metres.

The kit is visual-only.  Authoritative TypeScript/canonical collision remains
unchanged; supplied collision boxes are used as construction anchors and are
reported in the build metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence


KIT_VERSION = "kunren-reference-a18-v2"
REFERENCE_IMAGE_SHA256 = "f70f42b66758cc9527b35e016514b63f727c90b36eeaec28c458582c4bc68aab"
COMMAND_ID = "kunren-kurogane-command-bastion"
HANGAR_ID = "kunren-hakuen-aerostat-hall"
MIN_CONTACT_OVERLAP_M = 0.005
Point3 = tuple[float, float, float]


@dataclass(frozen=True)
class LODBudget:
    max_primitives: int
    max_estimated_triangles: int
    max_materials: int = 12


DEFAULT_LOD_BUDGETS: dict[int, LODBudget] = {
    0: LODBudget(900, 45_000, 12),
    1: LODBudget(500, 22_000, 11),
    2: LODBudget(260, 9_000, 9),
}


@dataclass(frozen=True)
class ApproachSpec:
    start: tuple[float, float]
    end: tuple[float, float]
    width: float
    inward_clearance: float = 8.0
    headroom: float = 3.0


@dataclass(frozen=True)
class HeroEnvelope:
    landmark_id: str
    cx: float
    cz: float
    width: float
    depth: float
    height: float
    entrance: tuple[float, float]
    approach: ApproachSpec
    collision_anchor: str


@dataclass(frozen=True)
class KunrenConstraints:
    stage_id: str
    stage_size: float
    player_spawns: tuple[Point3, ...]
    bot_spawns: tuple[Point3, ...]
    district_placements: tuple[Mapping[str, Any], ...]
    prop_placements: tuple[Mapping[str, Any], ...]
    command: HeroEnvelope
    hangar: HeroEnvelope
    collision_boxes: tuple[Mapping[str, Any], ...]
    collision_source: str
    lod: int
    lod_budget: LODBudget


@dataclass(frozen=True)
class BoxSpec:
    name: str
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float
    key: str
    yaw: float = 0.0
    role: str = "structure"
    route_exempt: bool = False


@dataclass(frozen=True)
class BeamSpec:
    name: str
    start: Point3
    end: Point3
    width: float
    depth: float
    key: str
    role: str = "structure"


@dataclass(frozen=True)
class CylinderSpec:
    name: str
    x: float
    y: float
    z: float
    radius: float
    height: float
    key: str
    segments: int
    top_radius: float | None = None
    role: str = "equipment"


@dataclass(frozen=True)
class CylinderBetweenSpec:
    name: str
    start: Point3
    end: Point3
    radius: float
    key: str
    segments: int
    end_radius: float | None = None
    role: str = "equipment"


@dataclass(frozen=True)
class SlopedPanelSpec:
    name: str
    corners: tuple[Point3, Point3, Point3, Point3]
    thickness: float
    key: str
    role: str = "shell"


@dataclass(frozen=True)
class RockSpec:
    name: str
    x: float
    y: float
    z: float
    radius: float
    height: float
    key: str
    segments: int
    seed: int
    role: str = "terrain"


@dataclass(frozen=True)
class ConnectionSpec:
    name: str
    parent: str
    child: str
    contact_kind: str
    axis: str
    actual_overlap_m: float
    min_overlap_m: float = MIN_CONTACT_OVERLAP_M
    note: str = ""


@dataclass(frozen=True)
class KunrenPlan:
    boxes: tuple[BoxSpec, ...]
    beams: tuple[BeamSpec, ...]
    cylinders: tuple[CylinderSpec, ...]
    cylinders_between: tuple[CylinderBetweenSpec, ...]
    sloped_panels: tuple[SlopedPanelSpec, ...]
    rocks: tuple[RockSpec, ...]
    connections: tuple[ConnectionSpec, ...]
    metadata: Mapping[str, Any]

    @property
    def primitive_count(self) -> int:
        return sum(
            len(group)
            for group in (
                self.boxes,
                self.beams,
                self.cylinders,
                self.cylinders_between,
                self.sloped_panels,
                self.rocks,
            )
        )

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(
            spec.name
            for group in (
                self.boxes,
                self.beams,
                self.cylinders,
                self.cylinders_between,
                self.sloped_panels,
                self.rocks,
            )
            for spec in group
        )


@dataclass(frozen=True)
class AuthoritativeKunrenLayout:
    stage: Mapping[str, Any]
    version: int
    stage_count: int
    placement_source: str
    placement_solver_sha256: str
    stage_world_catalog_sha256: str
    source_path: str


class MeshBuilderProtocol(Protocol):
    def add_box(self, x: float, y: float, z: float, w: float, h: float, d: float, key: str) -> None: ...

    def add_oriented_box(
        self, x: float, y: float, z: float, w: float, h: float, d: float, yaw: float, key: str
    ) -> None: ...

    def add_beam(self, start: Point3, end: Point3, width: float, depth: float, key: str) -> None: ...

    def add_cylinder(
        self,
        x: float,
        y: float,
        z: float,
        radius: float,
        height: float,
        key: str,
        segments: int,
        top_radius: float | None = None,
    ) -> None: ...

    def add_cylinder_between(
        self,
        start: Point3,
        end: Point3,
        radius: float,
        key: str,
        segments: int,
        end_radius: float | None = None,
    ) -> None: ...

    def add_sloped_panel(self, corners: Sequence[Point3], thickness: float, key: str) -> None: ...

    def add_rock(
        self,
        x: float,
        y: float,
        z: float,
        radius: float,
        height: float,
        key: str,
        segments: int,
        seed: int,
    ) -> None: ...


def load_authoritative_kunren_layout(path: str | Path) -> AuthoritativeKunrenLayout:
    """Load Kunren without importing or mutating the catalog builder."""

    source = Path(path).expanduser().resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("canonical layout must contain a non-empty stages list")
    matches = [stage for stage in stages if stage.get("id") == "kunren"]
    if len(matches) != 1:
        raise ValueError(f"canonical layout must contain exactly one Kunren stage, found {len(matches)}")
    stage = copy.deepcopy(matches[0])
    _validate_stage_shape(stage)
    return AuthoritativeKunrenLayout(
        stage=stage,
        version=int(payload.get("version", 0)),
        stage_count=len(stages),
        placement_source=str(payload.get("placementSource", stage.get("placementSource", "unknown"))),
        placement_solver_sha256=str(payload.get("placementSolverSha256", "")),
        stage_world_catalog_sha256=str(payload.get("stageWorldCatalogSha256", "")),
        source_path=str(source),
    )


def _validate_stage_shape(stage: Mapping[str, Any]) -> None:
    if stage.get("id") != "kunren":
        raise ValueError(f"A18 Kunren kit received stage {stage.get('id')!r}")
    if float(stage.get("size", 0.0)) <= 0:
        raise ValueError("Kunren stage size must be positive")
    placements = stage.get("landmarkPlacements")
    if not isinstance(placements, list):
        raise ValueError("Kunren landmarkPlacements must be a list")
    ids = {placement.get("id") for placement in placements}
    missing = {COMMAND_ID, HANGAR_ID} - ids
    if missing:
        raise ValueError(f"Kunren is missing required landmarks: {sorted(missing)}")


def _point2(value: Sequence[float], label: str) -> tuple[float, float]:
    if len(value) != 2:
        raise ValueError(f"{label} must contain exactly two coordinates")
    return float(value[0]), float(value[1])


def _approach_from_mapping(value: Mapping[str, Any], label: str) -> ApproachSpec:
    width = float(value.get("width", 0.0))
    if width <= 0:
        raise ValueError(f"{label} width must be positive")
    return ApproachSpec(
        start=_point2(value["start"], f"{label}.start"),
        end=_point2(value["end"], f"{label}.end"),
        width=width,
        inward_clearance=float(value.get("inward_clearance", value.get("inwardClearance", 8.0))),
        headroom=float(value.get("headroom", 3.0)),
    )


def _find_landmark(stage: Mapping[str, Any], landmark_id: str) -> Mapping[str, Any]:
    return next(item for item in stage["landmarkPlacements"] if item.get("id") == landmark_id)


def _resolve_hero_envelope(
    placement: Mapping[str, Any],
    collision_boxes: Sequence[Mapping[str, Any]],
    entrance_override: Sequence[float] | None,
    approach_override: ApproachSpec | Mapping[str, Any] | None,
) -> HeroEnvelope:
    landmark_id = str(placement["id"])
    floor_matches = [
        box
        for box in collision_boxes
        if box.get("landmarkId") == landmark_id and box.get("landmarkPart") == "floor"
    ]
    if collision_boxes and len(floor_matches) != 1:
        raise ValueError(
            f"supplied collision set must contain one floor anchor for {landmark_id}; found {len(floor_matches)}"
        )
    floor = floor_matches[0] if floor_matches else placement
    if approach_override is None:
        approach = _approach_from_mapping(placement["approach"], f"{landmark_id}.approach")
    elif isinstance(approach_override, ApproachSpec):
        approach = approach_override
    else:
        approach = _approach_from_mapping(approach_override, f"{landmark_id}.approachOverride")
    entrance = _point2(
        entrance_override if entrance_override is not None else placement["entrance"],
        f"{landmark_id}.entrance",
    )
    return HeroEnvelope(
        landmark_id=landmark_id,
        cx=float(floor.get("x", floor.get("cx"))),
        cz=float(floor.get("z", floor.get("cz"))),
        width=float(floor.get("w", floor.get("width"))),
        depth=float(floor.get("d", floor.get("depth"))),
        height=float(placement["height"]),
        entrance=entrance,
        approach=approach,
        collision_anchor=("canonical-landmark-floor" if floor_matches else "landmark-envelope-fallback"),
    )


def constraints_from_authoritative_layout(
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: Mapping[str, ApproachSpec | Mapping[str, Any]] | None = None,
    lod_budget: LODBudget | None = None,
) -> KunrenConstraints:
    """Resolve gameplay contracts into immutable construction constraints."""

    _validate_stage_shape(stage)
    if lod not in DEFAULT_LOD_BUDGETS:
        raise ValueError(f"lod must be 0, 1, or 2; received {lod}")
    collisions = tuple(stage.get("boxes", ())) if collision_boxes is None else tuple(collision_boxes)
    entrances = entrance_overrides or {}
    approaches = approach_overrides or {}
    command = _resolve_hero_envelope(
        _find_landmark(stage, COMMAND_ID),
        collisions,
        entrances.get(COMMAND_ID),
        approaches.get(COMMAND_ID),
    )
    hangar = _resolve_hero_envelope(
        _find_landmark(stage, HANGAR_ID),
        collisions,
        entrances.get(HANGAR_ID),
        approaches.get(HANGAR_ID),
    )
    budget = lod_budget or DEFAULT_LOD_BUDGETS[lod]
    if budget.max_primitives <= 0 or budget.max_estimated_triangles <= 0 or budget.max_materials <= 0:
        raise ValueError("LOD budget limits must all be positive")
    return KunrenConstraints(
        stage_id="kunren",
        stage_size=float(stage["size"]),
        player_spawns=tuple(tuple(map(float, point)) for point in stage.get("playerSpawns", ())),
        bot_spawns=tuple(tuple(map(float, point)) for point in stage.get("botSpawns", ())),
        district_placements=tuple(copy.deepcopy(stage.get("districtPlacements", ()))),
        prop_placements=tuple(copy.deepcopy(stage.get("propPlacements", ()))),
        command=command,
        hangar=hangar,
        collision_boxes=collisions,
        collision_source=("canonical-boxes" if collisions else "deferred-no-boxes"),
        lod=lod,
        lod_budget=budget,
    )


class _PlanAssembler:
    def __init__(self) -> None:
        self.boxes: list[BoxSpec] = []
        self.beams: list[BeamSpec] = []
        self.cylinders: list[CylinderSpec] = []
        self.cylinders_between: list[CylinderBetweenSpec] = []
        self.sloped_panels: list[SlopedPanelSpec] = []
        self.rocks: list[RockSpec] = []
        self.connections: list[ConnectionSpec] = []
        self._names: set[str] = set()

    def _claim(self, name: str) -> None:
        if not name or name in self._names:
            raise ValueError(f"duplicate or empty A18 part name: {name!r}")
        self._names.add(name)

    def box(self, name: str, x: float, y: float, z: float, w: float, h: float, d: float, key: str, **kwargs: Any) -> None:
        self._claim(name)
        if min(w, h, d) <= 0:
            raise ValueError(f"{name} has non-positive box dimensions")
        self.boxes.append(BoxSpec(name, x, y, z, w, h, d, key, **kwargs))

    def beam(self, name: str, start: Point3, end: Point3, width: float, depth: float, key: str, **kwargs: Any) -> None:
        self._claim(name)
        if width <= 0 or depth <= 0 or math.dist(start, end) <= 1e-5:
            raise ValueError(f"{name} has invalid beam dimensions")
        self.beams.append(BeamSpec(name, start, end, width, depth, key, **kwargs))

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
        **kwargs: Any,
    ) -> None:
        self._claim(name)
        if radius <= 0 or height <= 0 or segments < 5:
            raise ValueError(f"{name} has invalid cylinder dimensions")
        self.cylinders.append(CylinderSpec(name, x, y, z, radius, height, key, segments, **kwargs))

    def cylinder_between(
        self,
        name: str,
        start: Point3,
        end: Point3,
        radius: float,
        key: str,
        segments: int,
        **kwargs: Any,
    ) -> None:
        self._claim(name)
        if radius <= 0 or segments < 5 or math.dist(start, end) <= 1e-5:
            raise ValueError(f"{name} has invalid directional cylinder dimensions")
        self.cylinders_between.append(CylinderBetweenSpec(name, start, end, radius, key, segments, **kwargs))

    def panel(self, name: str, corners: Sequence[Point3], thickness: float, key: str, **kwargs: Any) -> None:
        self._claim(name)
        if len(corners) != 4 or thickness <= 0:
            raise ValueError(f"{name} has invalid sloped-panel data")
        edge_a = tuple(corners[1][index] - corners[0][index] for index in range(3))
        edge_b = tuple(corners[2][index] - corners[0][index] for index in range(3))
        projected_normal_y = edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2]
        if abs(projected_normal_y) < 1e-8:
            raise ValueError(f"{name} has a degenerate upper surface for MeshBuilder.add_sloped_panel")
        self.sloped_panels.append(SlopedPanelSpec(name, tuple(corners), thickness, key, **kwargs))

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
        **kwargs: Any,
    ) -> None:
        self._claim(name)
        if radius <= 0 or height <= 0 or segments < 5:
            raise ValueError(f"{name} has invalid rock dimensions")
        self.rocks.append(RockSpec(name, x, y, z, radius, height, key, segments, seed, **kwargs))

    def connect(
        self,
        name: str,
        parent: str,
        child: str,
        contact_kind: str,
        axis: str,
        actual_overlap_m: float,
        note: str = "",
    ) -> None:
        if actual_overlap_m < MIN_CONTACT_OVERLAP_M:
            raise ValueError(f"{name} contact overlap {actual_overlap_m:.6f}m is below release minimum")
        self.connections.append(
            ConnectionSpec(name, parent, child, contact_kind, axis, actual_overlap_m, MIN_CONTACT_OVERLAP_M, note)
        )


def _build_command_bastion(a: _PlanAssembler, hero: HeroEnvelope, lod: int) -> None:
    x, z = hero.cx, hero.cz
    width, depth = hero.width, hero.depth
    east = x - width / 2

    a.box("cmd.plinth", x + 2, 0.30, z, width - 4, 0.60, depth - 4, "terrain", role="foundation", route_exempt=True)
    a.box("cmd.lower.south", x + 1, 5.10, z - 15.5, width - 10, 9.40, 19, "wall_weathered", role="fortified-mass")
    a.box("cmd.lower.north", x + 1, 5.10, z + 15.5, width - 10, 9.40, 19, "wall_warm", role="fortified-mass")
    a.box("cmd.rear.bastion", x + 31, 8.20, z, 22, 15.60, depth - 4, "wall", role="fortified-mass")
    a.box("cmd.mid.south", x + 8, 14.20, z - 14, 50, 10.00, 18, "wall_warm", role="tier")
    a.box("cmd.mid.north", x + 8, 14.20, z + 14, 50, 10.00, 18, "wall_weathered", role="tier")
    a.box("cmd.core", x + 22, 20.00, z, 34, 12.00, 20, "wall", role="command-core")
    a.box("cmd.upper.keep", x + 25, 30.00, z, 28, 12.00, 22, "wall_warm", role="command-keep")
    a.box("cmd.crown", x + 26, 38.25, z, 21, 7.50, 18, "wall_weathered", role="command-crown")
    a.box("cmd.gate.lintel", east + 3.7, 10.80, z, 7.0, 2.40, 12.8, "wall", role="portal")

    tower_data = (
        ("south.front", east + 10.5, z - 19, 20.0),
        ("north.front", east + 10.5, z + 19, 22.0),
        ("south.rear", x + 31, z - 21, 26.0),
        ("north.rear", x + 31, z + 21, 24.0),
    )
    for index, (suffix, tx, tz, height) in enumerate(tower_data):
        a.box(
            f"cmd.tower.{suffix}", tx, 0.4 + height / 2, tz, 8.5, height, 8.5,
            "wall_weathered" if index % 2 else "wall", role="shoulder-tower",
        )
        a.box(
            f"cmd.tower.{suffix}.cap", tx, height + 0.55, tz, 10.0, 1.10, 10.0,
            "trim", role="tower-cap",
        )
        a.connect(
            f"contact.cmd.tower.{suffix}.plinth", "cmd.plinth", f"cmd.tower.{suffix}",
            "foundation-embed", "y", 0.20,
        )
        a.connect(
            f"contact.cmd.tower.{suffix}.cap", f"cmd.tower.{suffix}", f"cmd.tower.{suffix}.cap",
            "cap-seat", "y", 0.005,
        )

    for suffix in ("south", "north"):
        a.connect(f"contact.cmd.lower.{suffix}", "cmd.plinth", f"cmd.lower.{suffix}", "foundation-embed", "y", 0.20)
        a.connect(f"contact.cmd.mid.{suffix}", f"cmd.lower.{suffix}", f"cmd.mid.{suffix}", "tier-seat", "y", 0.60)
    a.connect("contact.cmd.rear", "cmd.plinth", "cmd.rear.bastion", "foundation-embed", "y", 0.20)
    a.connect("contact.cmd.core", "cmd.rear.bastion", "cmd.core", "tier-seat", "y", 2.00)
    a.connect("contact.cmd.keep", "cmd.core", "cmd.upper.keep", "tier-seat", "y", 2.00)
    a.connect("contact.cmd.crown", "cmd.upper.keep", "cmd.crown", "tier-seat", "y", 1.50)
    a.connect("contact.cmd.lintel.south", "cmd.lower.south", "cmd.gate.lintel", "portal-lintel-seat", "z", 0.50)
    a.connect("contact.cmd.lintel.north", "cmd.lower.north", "cmd.gate.lintel", "portal-lintel-seat", "z", 0.50)

    # Readable horizontal tier bands and a high service bridge preserve the
    # approach while breaking the old generic-box silhouette.
    tier_bands = (
        ("lower.s", x + 1, 9.45, z - 15, width - 8, 0.70, 21.0),
        ("lower.n", x + 1, 9.45, z + 15, width - 8, 0.70, 21.0),
        ("mid.s", x + 8, 19.00, z - 14, 52.0, 0.70, 19.2),
        ("mid.n", x + 8, 19.00, z + 14, 52.0, 0.70, 19.2),
        ("core", x + 22, 25.75, z, 36.0, 0.70, 21.4),
        ("keep", x + 25, 35.75, z, 30.0, 0.70, 23.4),
    )
    for suffix, bx, by, bz, bw, bh, bd in tier_bands[: 6 if lod == 0 else 5 if lod == 1 else 3]:
        a.box(f"cmd.band.{suffix}", bx, by, bz, bw, bh, bd, "trim", role="facade-band")

    # Tall exterior ribs occupy the two broad lateral concrete faces.  Their
    # cadence is deliberately sparse enough to preserve silhouette clarity,
    # but dense enough to avoid the previous blank-wall read at eye height.
    if lod < 2:
        rib_count = 5 if lod == 0 else 3
        for side, outer_z in (("south", z - 25.0), ("north", z + 25.0)):
            parent = f"cmd.lower.{side}"
            for rib_index in range(rib_count):
                rib_x = east + 15.0 + rib_index * 13.0
                rib_name = f"cmd.side-rib.{side}.{rib_index}"
                a.box(
                    rib_name,
                    rib_x,
                    4.85,
                    outer_z,
                    0.72,
                    7.50,
                    0.52,
                    "trim",
                    role="occupied-lateral-facade-rib",
                )
                a.connect(
                    f"contact.{rib_name}",
                    parent,
                    rib_name,
                    "facade-rib-seat",
                    "z",
                    0.20,
                )

    # Deep framed service apertures break the broad concrete tiers without
    # falling back to a repeated black-window grid.
    aperture_sites = (
        ("lower.s.0", east + 6.15, 5.6, z - 20.0, 0.70, 3.2, 4.8),
        ("lower.s.1", east + 6.15, 5.6, z - 11.5, 0.70, 3.2, 4.8),
        ("lower.n.0", east + 6.15, 5.6, z + 11.5, 0.70, 3.2, 4.8),
        ("lower.n.1", east + 6.15, 5.6, z + 20.0, 0.70, 3.2, 4.8),
        ("mid.s", x - 17.3, 14.8, z - 14.0, 0.72, 3.6, 5.4),
        ("mid.n", x - 17.3, 14.8, z + 14.0, 0.72, 3.6, 5.4),
        ("core.s", x + 4.7, 21.0, z - 5.2, 0.74, 3.4, 4.0),
        ("core.n", x + 4.7, 21.0, z + 5.2, 0.74, 3.4, 4.0),
    )
    aperture_limit = 8 if lod == 0 else 5 if lod == 1 else 2
    for suffix, ax, ay, az, aw, ah, ad in aperture_sites[:aperture_limit]:
        a.box(f"cmd.aperture.{suffix}", ax, ay, az, aw, ah, ad, "wall_alt", role="deep-service-aperture")
        if lod == 0:
            a.box(
                f"cmd.aperture.{suffix}.hood", ax - 0.18, ay + ah / 2 + 0.28, az,
                aw + 0.35, 0.42, ad + 0.75, "trim", role="aperture-hood",
            )

    # Two composed mechanical facade bays replace broad blank concrete on the
    # player-facing elevation.  Recess, frame and louvers read as one module.
    facade_bays = (("south", z - 16.0, "cmd.lower.south"), ("north", z + 16.0, "cmd.lower.north"))
    for suffix, bay_z, parent in facade_bays:
        back_name = f"cmd.facade.bay.{suffix}.recess"
        a.box(
            back_name,
            east + 5.92,
            5.25,
            bay_z,
            0.42,
            5.8,
            9.2,
            "wall_alt",
            role="mechanical-facade-recess",
        )
        frame_count = 4 if lod == 0 else 2 if lod == 1 else 1
        frame_specs = (
            ("outer", 5.10, bay_z - 4.75, 0.52, 6.4, 0.45),
            ("inner", 5.10, bay_z + 4.75, 0.52, 6.4, 0.45),
            ("top", 8.24, bay_z, 0.52, 0.52, 10.0),
            ("bottom", 2.10, bay_z, 0.52, 0.52, 10.0),
        )
        for frame_suffix, frame_y, frame_z, frame_w, frame_h, frame_d in frame_specs[:frame_count]:
            frame_name = f"cmd.facade.bay.{suffix}.frame.{frame_suffix}"
            a.box(
                frame_name,
                east + 5.70,
                frame_y,
                frame_z,
                frame_w,
                frame_h,
                frame_d,
                "trim",
                role="mechanical-facade-frame",
            )
            a.connect(
                f"contact.{frame_name}",
                back_name,
                frame_name,
                "facade-frame-seat",
                "x",
                0.08,
            )
        if lod == 0:
            for louver_index in range(4):
                louver_name = f"cmd.facade.bay.{suffix}.louver.{louver_index}"
                a.box(
                    louver_name,
                    east + 5.58,
                    3.15 + louver_index * 1.25,
                    bay_z,
                    0.30,
                    0.28,
                    8.35,
                    "accent" if louver_index == 2 else "trim",
                    role="mechanical-louver",
                )
                a.connect(
                    f"contact.{louver_name}",
                    back_name,
                    louver_name,
                    "louver-seat",
                    "x",
                    0.015,
                )
        a.connect(
            f"contact.{back_name}",
            parent,
            back_name,
            "recess-seat",
            "x",
            0.12,
        )

    # The 12 m authoritative approach remains fully open between these portal
    # piers; their inside faces sit beyond the corridor's six-metre half-width.
    for side, portal_z in (("south", z - 6.75), ("north", z + 6.75)):
        pier_name = f"cmd.portal.frame.{side}"
        a.box(
            pier_name,
            east + 4.0,
            4.85,
            portal_z,
            1.20,
            9.70,
            1.20,
            "trim",
            role="human-scale-portal-frame",
        )
        a.connect(
            f"contact.{pier_name}",
            "cmd.gate.lintel",
            pier_name,
            "portal-frame-seat",
            "y",
            0.10,
        )
        if lod == 0:
            a.cylinder(
                f"cmd.portal.bollard.{side}",
                east - 0.35,
                0.68,
                z + (-7.45 if side == "south" else 7.45),
                0.18,
                1.36,
                "accent",
                10,
                role="human-scale-bollard",
            )

    a.box("cmd.bridge.deck", x - 10, 18.40, z, 22, 0.80, 13.0, "trim", role="service-bridge")
    a.connect("contact.cmd.bridge.south", "cmd.mid.south", "cmd.bridge.deck", "bridge-seat", "z", 0.50)
    a.connect("contact.cmd.bridge.north", "cmd.mid.north", "cmd.bridge.deck", "bridge-seat", "z", 0.50)
    for side, offset in (("south", -6.1), ("north", 6.1)):
        a.beam(
            f"cmd.bridge.rail.{side}",
            (x - 20.8, 20.1, z + offset), (x + 0.8, 20.1, z + offset),
            0.16, 0.16, "trim", role="bridge-railing",
        )
        if lod == 0:
            for post in range(6):
                px = x - 20.2 + post * 4.1
                a.beam(
                    f"cmd.bridge.post.{side}.{post}",
                    (px, 18.55, z + offset), (px, 20.25, z + offset),
                    0.12, 0.12, "trim", role="bridge-railing",
                )

    # Battered front buttresses make the mass read as one fortified complex.
    buttress_count = 8 if lod == 0 else 5 if lod == 1 else 3
    for index in range(buttress_count):
        t = (index + 0.5) / buttress_count
        bz = z - depth * 0.42 + t * depth * 0.84
        if abs(bz - z) < hero.approach.width * 0.65:
            continue
        a.beam(
            f"cmd.front.buttress.{index}",
            (east + 1.0, 0.35, bz), (east + 5.3, 12.2, bz),
            0.62, 0.80, "wall_weathered", role="battered-buttress",
        )

    # Radar wheel faces the canonical eastern approach.
    mast_x, mast_z = x + 26, z
    a.cylinder("cmd.radar.mast", mast_x, 44.0, mast_z, 0.48, 4.4, "trim", 12 if lod == 0 else 8, role="radar-support")
    a.connect("contact.cmd.radar.mast", "cmd.crown", "cmd.radar.mast", "mast-seat", "y", 0.20)
    radar_segments = 12 if lod == 0 else 8 if lod == 1 else 6
    centre = (mast_x, 45.2, mast_z)
    ring_points: list[Point3] = []
    for index in range(radar_segments):
        angle = math.tau * index / radar_segments
        ring_points.append((mast_x, centre[1] + math.sin(angle) * 3.5, mast_z + math.cos(angle) * 3.5))
    for index, point in enumerate(ring_points):
        nxt = ring_points[(index + 1) % radar_segments]
        a.beam(f"cmd.radar.ring.{index}", point, nxt, 0.19, 0.19, "trim", role="radar-ring")
        a.connect(
            f"contact.cmd.radar.ring.{index}",
            f"cmd.radar.ring.{index}", f"cmd.radar.ring.{(index + 1) % radar_segments}",
            "welded-ring", "endpoint", 0.08,
        )
        if lod < 2 and index % 2 == 0:
            a.beam(f"cmd.radar.spoke.{index}", centre, point, 0.10, 0.10, "trim", role="radar-spoke")

    # The reference carries a rectangular tactical array above the command
    # crown.  A sparse frame and grid sits in the same east-facing plane as the
    # circular antenna and remains inside the 49 m authoritative envelope.
    if lod < 2:
        array_specs = (
            ("south", (mast_x, 42.9, mast_z - 4.0), (mast_x, 47.5, mast_z - 4.0)),
            ("north", (mast_x, 42.9, mast_z + 4.0), (mast_x, 47.5, mast_z + 4.0)),
            ("bottom", (mast_x, 42.9, mast_z - 4.0), (mast_x, 42.9, mast_z + 4.0)),
            ("top", (mast_x, 47.5, mast_z - 4.0), (mast_x, 47.5, mast_z + 4.0)),
            ("vertical.south", (mast_x, 42.9, mast_z - 1.33), (mast_x, 47.5, mast_z - 1.33)),
            ("vertical.north", (mast_x, 42.9, mast_z + 1.33), (mast_x, 47.5, mast_z + 1.33)),
            ("horizontal.low", (mast_x, 44.43, mast_z - 4.0), (mast_x, 44.43, mast_z + 4.0)),
            ("horizontal.high", (mast_x, 45.97, mast_z - 4.0), (mast_x, 45.97, mast_z + 4.0)),
        )
        array_limit = 8 if lod == 0 else 4
        for suffix, start, end in array_specs[:array_limit]:
            name = f"cmd.radar.array.{suffix}"
            a.beam(name, start, end, 0.095, 0.095, "trim", role="radar-array-grid")
        a.connect(
            "contact.cmd.radar.array.mast",
            "cmd.radar.mast",
            "cmd.radar.array.bottom",
            "array-mast-weld",
            "endpoint",
            0.08,
        )

    antenna_count = 4 if lod == 0 else 2 if lod == 1 else 1
    antenna_sites = (
        (x + 34, z + 17, 19.2),
        (x + 32, z - 18, 19.2),
        (x + 17, z + 7, 36.0),
        (x + 18, z - 7, 36.0),
    )
    for index, (ax, az, base) in enumerate(antenna_sites[:antenna_count]):
        top = min(hero.height - 0.6, base + 12.0 + index * 2.0)
        a.cylinder(
            f"cmd.antenna.{index}", ax, (base + top) / 2, az, 0.18, top - base,
            "trim", 8 if lod == 0 else 6, top_radius=0.08, role="antenna",
        )

    if lod == 0:
        # Roof service terraces, vents and pipe runs spend geometry where the
        # first-person silhouette and contact shadows benefit.
        for index, (sx, sz, sw, sd) in enumerate((
            (x + 15, z - 15, 9.0, 5.0),
            (x + 15, z + 15, 9.0, 5.0),
            (x + 31, z - 8, 7.0, 4.0),
            (x + 31, z + 8, 7.0, 4.0),
        )):
            base_y = 19.45 if index < 2 else 42.2
            a.box(f"cmd.service.pad.{index}", sx, base_y, sz, sw, 0.50, sd, "roof", role="service-terrace")
            a.box(f"cmd.service.unit.{index}", sx, base_y + 1.35, sz, sw * 0.48, 2.20, sd * 0.55, "wall_cool", role="service-equipment")
        for index, z_offset in enumerate((-17.0, 17.0)):
            a.cylinder_between(
                f"cmd.pipe.{index}", (x - 2, 17.0, z + z_offset), (x + 25, 17.0, z + z_offset),
                0.28, "accent", 10, role="service-pipe",
            )

        # One validated ladder module on each front shoulder tower fixes scale
        # and gives the vertical mass a believable maintenance route.
        for side, ladder_z in (("south", z - 19.0), ("north", z + 19.0)):
            parent = f"cmd.tower.{side}.front"
            for rail_index, rail_z in enumerate((ladder_z - 0.43, ladder_z + 0.43)):
                rail_name = f"cmd.ladder.{side}.rail.{rail_index}"
                a.beam(
                    rail_name,
                    (east + 6.22, 0.35, rail_z),
                    (east + 6.22, 9.4, rail_z),
                    0.085,
                    0.085,
                    "trim",
                    role="human-scale-ladder",
                )
                a.connect(
                    f"contact.{rail_name}",
                    parent,
                    rail_name,
                    "ladder-standoff-seat",
                    "x",
                    0.010,
                )
            for rung_index in range(7):
                rung_name = f"cmd.ladder.{side}.rung.{rung_index}"
                rung_y = 1.05 + rung_index * 1.20
                a.beam(
                    rung_name,
                    (east + 6.22, rung_y, ladder_z - 0.48),
                    (east + 6.22, rung_y, ladder_z + 0.48),
                    0.075,
                    0.075,
                    "trim",
                    role="human-scale-ladder",
                )
                a.connect(
                    f"contact.{rung_name}",
                    f"cmd.ladder.{side}.rail.0",
                    rung_name,
                    "ladder-rung-weld",
                    "endpoint",
                    0.05,
                )


def _arch_points(cz: float) -> tuple[tuple[float, float], ...]:
    return tuple(
        (cz + dz, y)
        for dz, y in (
            (-30.0, 0.40), (-30.0, 9.0), (-27.0, 20.0), (-21.0, 32.0), (-12.0, 44.0),
            (0.0, 52.0),
            (12.0, 44.0), (21.0, 32.0), (27.0, 20.0), (30.0, 9.0), (30.0, 0.40),
        )
    )


def _build_aerostat_hangar(a: _PlanAssembler, hero: HeroEnvelope, lod: int) -> None:
    x, z = hero.cx, hero.cz
    width, depth = hero.width, hero.depth
    east, west = x + width / 2, x - width / 2
    front_x, back_x = east - 4.0, west + 4.0

    a.box("hall.floor", x, 0.30, z, width - 4, 0.60, depth - 4, "terrain", role="foundation", route_exempt=True)
    for side, offset in (("south", -29.0), ("north", 29.0)):
        a.box(f"hall.base.{side}", x, 3.20, z + offset, width - 4, 5.60, 10.0, "wall_weathered", role="vault-foot")
        a.box(f"hall.wall.{side}", x - 5, 10.2, z + offset, width - 14, 8.8, 7.2, "wall", role="vault-sidewall")
        a.connect(f"contact.hall.base.{side}", "hall.floor", f"hall.base.{side}", "foundation-embed", "y", 0.20)
        a.connect(f"contact.hall.wall.{side}", f"hall.base.{side}", f"hall.wall.{side}", "wall-seat", "y", 0.40)

    a.box("hall.backwall", west + 1.9, 22.0, z, 3.6, 43.2, 50.0, "wall_alt", role="deep-vault-back")
    a.connect("contact.hall.backwall.floor", "hall.floor", "hall.backwall", "foundation-embed", "y", 0.20)

    points = _arch_points(z)
    rib_count = 10 if lod == 0 else 7 if lod == 1 else 4
    stations = tuple(front_x + (back_x - front_x) * index / (rib_count - 1) for index in range(rib_count))
    rib_half = 0.75 if lod == 0 else 0.90 if lod == 1 else 1.10
    for station_index, station_x in enumerate(stations):
        for segment_index, ((z0, y0), (z1, y1)) in enumerate(zip(points, points[1:])):
            a.beam(
                f"hall.rib.{station_index}.{segment_index}",
                (station_x, y0, z0), (station_x, y1, z1),
                rib_half, rib_half, "trim", role="vault-rib",
            )
            if segment_index:
                a.connect(
                    f"contact.hall.rib.{station_index}.{segment_index}",
                    f"hall.rib.{station_index}.{segment_index - 1}",
                    f"hall.rib.{station_index}.{segment_index}",
                    "rib-knee", "endpoint", rib_half * 0.20,
                )
        a.connect(
            f"contact.hall.rib.{station_index}.south-foot", "hall.base.south", f"hall.rib.{station_index}.0",
            "rib-foot-seat", "y", 0.20,
        )
        a.connect(
            f"contact.hall.rib.{station_index}.north-foot", "hall.base.north", f"hall.rib.{station_index}.9",
            "rib-foot-seat", "y", 0.20,
        )

    # Continuous concrete shell strips sit behind the exposed ribs; the east
    # face remains fully open and the far dark wall gives measurable depth.
    for segment_index, ((z0, y0), (z1, y1)) in enumerate(zip(points, points[1:])):
        if lod == 2 and segment_index in {1, 3, 6, 8}:
            continue
        if abs(z1 - z0) < 1e-6:
            a.box(
                f"hall.shell.{segment_index}",
                (front_x + back_x) / 2,
                (y0 + y1) / 2,
                z0,
                abs(front_x - back_x) + 1.3,
                abs(y1 - y0),
                0.84 if lod == 0 else 1.10,
                "wall_weathered",
                role="vault-vertical-shell",
            )
            continue
        a.panel(
            f"hall.shell.{segment_index}",
            (
                (front_x - 0.65, y0, z0),
                (back_x + 0.65, y0, z0),
                (back_x + 0.65, y1, z1),
                (front_x - 0.65, y1, z1),
            ),
            0.42 if lod == 0 else 0.55,
            "wall_weathered" if segment_index % 3 else "roof",
            role="vault-shell",
        )

    purlin_indices = (1, 2, 3, 4, 5, 6, 7, 8, 9) if lod == 0 else (1, 3, 5, 7, 9) if lod == 1 else (2, 5, 8)
    for point_index in purlin_indices:
        pz, py = points[point_index]
        a.beam(
            f"hall.purlin.{point_index}",
            (front_x - 0.4, py - 0.35, pz), (back_x + 0.4, py - 0.35, pz),
            0.35 if lod == 0 else 0.48, 0.35 if lod == 0 else 0.48,
            "trim", role="vault-purlin",
        )
        a.connect(
            f"contact.hall.purlin.{point_index}", "hall.rib.0.0", f"hall.purlin.{point_index}",
            "rib-purlin-seat", "x", 0.20, "Purlin crosses every rib station; parent names the front datum rib.",
        )

    # Portal collar is intentionally massive but clears the 12 m approach.
    for side, offset in (("south", -27.0), ("north", 27.0)):
        a.box(f"hall.portal.jamb.{side}", east - 1.7, 13.5, z + offset, 3.6, 26.2, 6.0, "wall_warm", role="portal-buttress")
        a.connect(
            f"contact.hall.portal.{side}", f"hall.base.{side}", f"hall.portal.jamb.{side}",
            "portal-seat", "y", 0.40,
        )

    # A complete front collar makes the hall read as one engineered portal,
    # instead of two isolated jambs in front of a generic rib shed.  Every
    # segment shares a physical endpoint with its neighbour.
    portal_rib_half = 1.05 if lod == 0 else 1.20 if lod == 1 else 1.35
    for segment_index, ((z0, y0), (z1, y1)) in enumerate(zip(points, points[1:])):
        arch_name = f"hall.portal.arch.{segment_index}"
        a.beam(
            arch_name,
            (east - 1.7, y0, z0),
            (east - 1.7, y1, z1),
            portal_rib_half,
            portal_rib_half,
            "wall_warm",
            role="monumental-portal-collar",
        )
        if segment_index:
            a.connect(
                f"contact.{arch_name}",
                f"hall.portal.arch.{segment_index - 1}",
                arch_name,
                "portal-arch-knee",
                "endpoint",
                portal_rib_half * 0.20,
            )
    a.connect(
        "contact.hall.portal.arch.south-foot",
        "hall.portal.jamb.south",
        "hall.portal.arch.0",
        "portal-arch-foot",
        "endpoint",
        0.20,
    )
    a.connect(
        "contact.hall.portal.arch.north-foot",
        "hall.portal.jamb.north",
        "hall.portal.arch.9",
        "portal-arch-foot",
        "endpoint",
        0.20,
    )

    # Two framed 2.5 m maintenance doors calibrate the huge opening against a
    # person.  They are recessed into the east face of the portal jambs, not
    # pasted across the traversal opening.
    for side, offset in (("south", -27.0), ("north", 27.0)):
        door_name = f"hall.portal.service-door.{side}.recess"
        a.box(
            door_name,
            east + 0.18,
            1.35,
            z + offset,
            0.32,
            2.50,
            2.10,
            "wall_alt",
            role="human-scale-door-recess",
        )
        a.connect(
            f"contact.{door_name}",
            f"hall.portal.jamb.{side}",
            door_name,
            "door-recess-seat",
            "x",
            0.08,
        )
        if lod < 2:
            for frame_suffix, frame_y, frame_z, frame_h, frame_d in (
                ("south", 1.55, z + offset - 1.22, 3.10, 0.30),
                ("north", 1.55, z + offset + 1.22, 3.10, 0.30),
                ("top", 2.82, z + offset, 0.34, 2.74),
            ):
                frame_name = f"hall.portal.service-door.{side}.frame.{frame_suffix}"
                a.box(
                    frame_name,
                    east + 0.35,
                    frame_y,
                    frame_z,
                    0.26,
                    frame_h,
                    frame_d,
                    "accent" if frame_suffix == "top" else "trim",
                    role="human-scale-door-frame",
                )
                a.connect(
                    f"contact.{frame_name}",
                    door_name,
                    frame_name,
                    "door-frame-seat",
                    "x",
                    0.10,
                )

    # Painted guide lanes are surface information and explicitly remain
    # collision-exempt.  They lead the eye through the deep playable vault.
    if lod < 2:
        for side, offset in (("south", -4.8), ("north", 4.8)):
            a.box(
                f"hall.floor.guide.{side}",
                x - 4.0,
                0.615,
                z + offset,
                width - 24.0,
                0.03,
                0.22,
                "accent",
                role="painted-route-guide",
                route_exempt=True,
            )
        for stripe_index, stripe_x in enumerate((east - 10.0, east - 18.0, west + 18.0)):
            a.box(
                f"hall.floor.threshold.{stripe_index}",
                stripe_x,
                0.618,
                z,
                0.34,
                0.036,
                11.0,
                "accent",
                role="painted-threshold-marking",
                route_exempt=True,
            )

    # Interior platforms/trusses remain lateral, leaving the center firing and
    # traversal volume open beneath the aerostat.
    platform_x = x - 6
    for side, offset in (("south", -20.5), ("north", 20.5)):
        a.box(
            f"hall.catwalk.{side}", platform_x, 13.0, z + offset, width - 28, 0.70, 3.4,
            "accent", role="interior-platform",
        )
        support_count = 7 if lod == 0 else 4 if lod == 1 else 2
        for index in range(support_count):
            sx = platform_x - (width - 34) / 2 + index * (width - 34) / max(1, support_count - 1)
            a.beam(
                f"hall.catwalk.support.{side}.{index}",
                (sx, 4.8, z + offset), (sx, 12.8, z + offset),
                0.22, 0.22, "trim", role="platform-support",
            )

        inner_z = z + offset + (1.62 if side == "south" else -1.62)
        rail_name = f"hall.catwalk.rail.{side}"
        a.beam(
            rail_name,
            (platform_x - (width - 30) / 2, 14.12, inner_z),
            (platform_x + (width - 30) / 2, 14.12, inner_z),
            0.11,
            0.11,
            "trim",
            role="human-scale-catwalk-railing",
        )
        rail_post_count = 7 if lod == 0 else 4 if lod == 1 else 2
        for post_index in range(rail_post_count):
            post_x = platform_x - (width - 32) / 2 + post_index * (width - 32) / max(1, rail_post_count - 1)
            post_name = f"hall.catwalk.rail-post.{side}.{post_index}"
            a.beam(
                post_name,
                (post_x, 13.28, inner_z),
                (post_x, 14.24, inner_z),
                0.095,
                0.095,
                "trim",
                role="human-scale-catwalk-railing",
            )
            a.connect(
                f"contact.{post_name}",
                f"hall.catwalk.{side}",
                post_name,
                "railing-post-seat",
                "y",
                0.07,
            )

        if lod == 0:
            # Ten overlapping treads climb 13 m with 1.3 m risers.  At the
            # final tread the top overlaps the catwalk underside by 0.35 m.
            previous = "hall.floor"
            for step_index in range(10):
                step_name = f"hall.stair.{side}.step.{step_index}"
                step_height = 1.30 * (step_index + 1)
                step_x = front_x - 4.70 - 1.25 * step_index
                a.box(
                    step_name,
                    step_x,
                    step_height / 2,
                    z + offset,
                    1.55,
                    step_height,
                    3.0,
                    "trim",
                    role="human-scale-stair-tread",
                )
                a.connect(
                    f"contact.{step_name}",
                    previous,
                    step_name,
                    "stair-seat" if step_index else "foundation-seat",
                    "x" if step_index else "y",
                    0.30 if step_index else 0.20,
                )
                previous = step_name
            a.connect(
                f"contact.hall.stair.{side}.landing",
                previous,
                f"hall.catwalk.{side}",
                "stair-landing-seat",
                "y",
                0.35,
            )
            outer_z = z + offset + (-1.42 if side == "south" else 1.42)
            a.beam(
                f"hall.stair.rail.{side}",
                (front_x - 4.6, 1.7, outer_z),
                (front_x - 16.1, 14.0, outer_z),
                0.095,
                0.095,
                "trim",
                role="human-scale-stair-railing",
            )

    # Warm worklight housings on the sidewalls make the interior usable and
    # create controlled pools of light in the private material/render proof.
    fixture_xs = (front_x - 12.0, x - 10.0, back_x + 14.0) if lod == 0 else (front_x - 18.0, back_x + 22.0)
    if lod < 2:
        for side, offset in (("south", -25.30), ("north", 25.30)):
            parent = f"hall.wall.{side}"
            for fixture_index, fixture_x in enumerate(fixture_xs):
                fixture_name = f"hall.worklight.{side}.{fixture_index}"
                a.box(
                    fixture_name,
                    fixture_x,
                    16.0,
                    z + offset,
                    0.72,
                    0.46,
                    0.46,
                    "accent",
                    role="interior-worklight-fixture",
                )
                a.connect(
                    f"contact.{fixture_name}",
                    parent,
                    fixture_name,
                    "wall-fixture-seat",
                    "z",
                    0.10,
                )

    if lod == 0:
        for drum_index, (drum_x, drum_z) in enumerate((
            (front_x - 16.0, z - 23.0),
            (front_x - 17.1, z - 23.0),
            (front_x - 16.5, z - 21.9),
        )):
            a.cylinder(
                f"hall.service-drum.{drum_index}",
                drum_x,
                0.52,
                drum_z,
                0.43,
                1.04,
                "accent" if drum_index == 2 else "trim",
                12,
                role="human-scale-service-drum",
            )

    truss_stations = stations[1:-1:2] if lod == 0 else stations[1:-1:3]
    for index, tx in enumerate(truss_stations):
        a.beam(
            f"hall.truss.low.{index}", (tx, 22.0, z - 20), (tx, 22.0, z + 20),
            0.30, 0.30, "trim", role="interior-truss",
        )
        a.beam(
            f"hall.truss.diagonal.s.{index}", (tx, 22.0, z - 20), (tx, 31.5, z),
            0.24, 0.24, "trim", role="interior-truss",
        )
        a.beam(
            f"hall.truss.diagonal.n.{index}", (tx, 31.5, z), (tx, 22.0, z + 20),
            0.24, 0.24, "trim", role="interior-truss",
        )

    aerostat_segments = 12 if lod == 0 else 8 if lod == 1 else 6
    a.cylinder_between(
        "hall.aerostat.nose", (x + 10, 30.0, z), (x + 4, 30.0, z),
        0.8, "wall_cool", aerostat_segments, end_radius=3.4, role="aerostat",
    )
    a.cylinder_between(
        "hall.aerostat.body", (x + 4, 30.0, z), (x - 18, 30.0, z),
        3.4, "wall_cool", aerostat_segments, end_radius=3.4, role="aerostat",
    )
    a.cylinder_between(
        "hall.aerostat.tail", (x - 18, 30.0, z), (x - 24, 30.0, z),
        3.4, "wall_cool", aerostat_segments, end_radius=0.7, role="aerostat",
    )
    a.connect("contact.hall.aerostat.nose", "hall.aerostat.nose", "hall.aerostat.body", "envelope-seam", "x", 0.10)
    a.connect("contact.hall.aerostat.tail", "hall.aerostat.body", "hall.aerostat.tail", "envelope-seam", "x", 0.10)
    for index, cable_x in enumerate((x + 1, x - 14)):
        a.beam(
            f"hall.aerostat.cable.{index}", (cable_x, 33.4, z), (cable_x, 43.0, z),
            0.055, 0.055, "trim", role="suspension-cable",
        )

    if lod == 0:
        # Gantry crane and service lighting turn the vault into an inhabited
        # military facility instead of a bare arch shell.
        for side, offset in (("south", -17.5), ("north", 17.5)):
            a.beam(
                f"hall.gantry.rail.{side}", (front_x - 5, 18.5, z + offset), (back_x + 8, 18.5, z + offset),
                0.30, 0.30, "accent", role="gantry-rail",
            )
        a.beam("hall.gantry.cross", (x - 2, 18.5, z - 18), (x - 2, 18.5, z + 18), 0.48, 0.48, "accent", role="gantry")
        a.beam("hall.gantry.hoist", (x - 2, 18.3, z), (x - 2, 8.5, z), 0.10, 0.10, "trim", role="gantry-hoist")


def _add_service_block(
    a: _PlanAssembler,
    index: int,
    x: float,
    z: float,
    width: float,
    depth: float,
    height: float,
    lod: int,
    yaw: float = 0.0,
    kind: str = "bunker",
    detailed: bool = True,
    role: str = "service-building",
) -> None:
    """Build one solver-anchored district with a Kunren-specific facade family.

    The old A18 pass stacked the same three shrinking boxes for every district.
    This version keeps the collision footprint but varies mass hierarchy, roof
    profile and human-scale facade modules by the authoritative district kind.
    """

    prefix = f"city.block.{index}"
    plinth_h = 1.4 + (index % 3) * 0.45
    cosine, sine = math.cos(yaw), math.sin(yaw)

    def shifted(local_x: float, local_z: float) -> tuple[float, float]:
        return x + local_x * cosine - local_z * sine, z + local_x * sine + local_z * cosine

    def local_box(
        suffix: str,
        local_x: float,
        y: float,
        local_z: float,
        w: float,
        h: float,
        d: float,
        key: str,
        part_role: str,
    ) -> str:
        bx, bz = shifted(local_x, local_z)
        name = f"{prefix}.{suffix}"
        a.box(name, bx, y, bz, w, h, d, key, yaw=yaw, role=part_role)
        return name

    family = kind if kind in {"tower", "bunker", "hangar", "arena"} else "bunker"
    family_ratios = {
        "tower": (0.50, 0.31, 0.19, 0.72, 0.50),
        "bunker": (0.54, 0.29, 0.17, 0.84, 0.62),
        "hangar": (0.61, 0.26, 0.13, 0.90, 0.72),
        "arena": (0.48, 0.31, 0.21, 0.78, 0.58),
    }
    lower_ratio, middle_ratio, upper_ratio, middle_scale, upper_scale = family_ratios[family]

    a.box(
        f"{prefix}.plinth", x, plinth_h / 2, z, width + 3.0, plinth_h, depth + 3.0,
        "terrain", yaw=yaw, role="terrain-bench",
    )
    lower_h = height * lower_ratio
    middle_h = height * middle_ratio
    upper_h = height * upper_ratio
    middle_offset = width * (0.09 if family in {"tower", "arena"} else 0.045)
    upper_offset = -width * (0.06 if family != "hangar" else 0.015)
    middle_x, middle_z = shifted(middle_offset, 0.0)
    upper_x, upper_z = shifted(upper_offset, 0.0)
    a.box(
        f"{prefix}.lower", x, plinth_h + lower_h / 2 - 0.15, z,
        width, lower_h + 0.30, depth, "wall_weathered", yaw=yaw, role=role,
    )
    a.box(
        f"{prefix}.middle", middle_x, plinth_h + lower_h + middle_h / 2 - 0.25, middle_z,
        width * middle_scale,
        middle_h + 0.50,
        depth * (0.80 if family != "hangar" else 0.90),
        "wall_warm" if family in {"bunker", "arena"} else "wall_cool",
        yaw=yaw,
        role=role,
    )
    a.box(
        f"{prefix}.upper", upper_x, plinth_h + lower_h + middle_h + upper_h / 2 - 0.25, upper_z,
        width * upper_scale,
        upper_h + 0.50,
        depth * (0.62 if family != "hangar" else 0.78),
        "wall" if family != "tower" else "wall_weathered",
        yaw=yaw,
        role=role,
    )
    a.box(
        f"{prefix}.roof", upper_x, plinth_h + height + 0.20, upper_z,
        width * (upper_scale + 0.08),
        0.60,
        depth * (0.72 if family != "hangar" else 0.86),
        "roof",
        yaw=yaw,
        role=f"{family}-roof-profile",
    )
    a.connect(f"contact.{prefix}.lower", f"{prefix}.plinth", f"{prefix}.lower", "foundation-embed", "y", 0.15)
    a.connect(f"contact.{prefix}.middle", f"{prefix}.lower", f"{prefix}.middle", "tier-seat", "y", 0.25)
    a.connect(f"contact.{prefix}.upper", f"{prefix}.middle", f"{prefix}.upper", "tier-seat", "y", 0.25)

    # Macro family markers survive LOD reduction and prevent the settlement
    # from collapsing back into one repeated stepped silhouette.
    if family == "tower":
        for side, local_z in (("south", -depth * 0.34), ("north", depth * 0.34)):
            fin_name = local_box(
                f"signal.fin.{side}",
                -width * 0.23,
                plinth_h + height * 0.58,
                local_z,
                width * 0.16,
                height * 0.72,
                1.1,
                "trim",
                "tower-vertical-fin",
            )
            a.connect(
                f"contact.{prefix}.signal.fin.{side}",
                f"{prefix}.lower",
                fin_name,
                "facade-fin-seat",
                "x",
                0.08,
            )
        crown_deck = local_box(
            "signal.crown.deck",
            upper_offset,
            plinth_h + height + 0.55,
            0.0,
            width * 0.74,
            0.52,
            depth * 0.74,
            "accent",
            "signal-crown",
        )
        a.connect(
            f"contact.{prefix}.signal.crown.deck",
            f"{prefix}.roof",
            crown_deck,
            "crown-deck-seat",
            "y",
            0.10,
        )
    elif family == "bunker":
        for band_index, band_y in enumerate((plinth_h + lower_h * 0.36, plinth_h + lower_h * 0.73)):
            band = local_box(
                f"blast.band.{band_index}",
                -0.22,
                band_y,
                0.0,
                width + 0.52,
                0.48 if lod < 2 else 0.64,
                depth + 0.52,
                "trim",
                "bunker-horizontal-band",
            )
            a.connect(
                f"contact.{prefix}.blast.band.{band_index}",
                f"{prefix}.lower",
                band,
                "blast-band-seat",
                "x-z",
                0.20,
            )
    elif family == "hangar":
        monitor_h = max(2.8, height * 0.12)
        monitor = local_box(
            "monitor.body",
            upper_offset,
            plinth_h + height + monitor_h / 2 - 0.05,
            0.0,
            width * 0.46,
            monitor_h,
            depth * 0.56,
            "wall_cool",
            "hangar-roof-monitor",
        )
        monitor_cap = local_box(
            "monitor.cap",
            upper_offset,
            plinth_h + height + monitor_h - 0.10,
            0.0,
            width * 0.54,
            0.44,
            depth * 0.64,
            "roof",
            "hangar-roof-monitor",
        )
        a.connect(
            f"contact.{prefix}.monitor",
            f"{prefix}.roof",
            monitor,
            "monitor-seat",
            "y",
            0.10,
        )
        a.connect(
            f"contact.{prefix}.monitor.cap",
            monitor,
            monitor_cap,
            "monitor-cap-seat",
            "y",
            0.10,
        )
    else:  # arena / operations district
        spine = local_box(
            "operations.spine",
            width * 0.23,
            plinth_h + height * 0.68,
            -depth * 0.28,
            width * 0.26,
            height * 0.62,
            depth * 0.28,
            "wall_weathered",
            "arena-operations-spine",
        )
        operations_deck = local_box(
            "operations.deck",
            -width * 0.16,
            plinth_h + height * 0.56,
            depth * 0.32,
            width * 0.56,
            0.58,
            depth * 0.22,
            "accent",
            "arena-service-deck",
        )
        a.connect(
            f"contact.{prefix}.operations.spine",
            f"{prefix}.lower",
            spine,
            "operations-block-seat",
            "y",
            0.18,
        )
        a.connect(
            f"contact.{prefix}.operations.deck",
            f"{prefix}.lower",
            operations_deck,
            "service-deck-seat",
            "y",
            0.10,
        )

    if lod < 2:
        antenna_base = plinth_h + height + 0.45
        antenna_height = (9.0 if family == "tower" else 5.5) + (index % 4) * 1.25
        a.cylinder(
            f"{prefix}.antenna", upper_x, antenna_base + antenna_height / 2, upper_z,
            0.13, antenna_height, "trim", 6 if lod == 1 else 8, top_radius=0.055, role="antenna",
        )

    if not detailed or lod == 2:
        return

    # A 2.4 m deep-framed service entrance gives the large district a stable
    # human scale.  It occupies the lower facade plane and is not a flat card.
    facade_x = -width / 2 - 0.12
    door_z = depth * (0.18 if index % 2 else -0.18)
    door_back = local_box(
        "door.recess",
        facade_x,
        plinth_h + 1.35,
        door_z,
        0.34,
        2.50,
        2.15,
        "wall_alt",
        "human-scale-door-recess",
    )
    a.connect(
        f"contact.{prefix}.door.recess",
        f"{prefix}.lower",
        door_back,
        "door-recess-seat",
        "x",
        0.05,
    )
    frame_specs = (
        ("left", door_z - 1.25, 0.34, 3.10, 0.30),
        ("right", door_z + 1.25, 0.34, 3.10, 0.30),
        ("top", door_z, 0.34, 0.34, 2.80),
    )
    for suffix, local_z, frame_w, frame_h, frame_d in frame_specs:
        frame_y = plinth_h + (1.55 if suffix != "top" else 2.82)
        frame = local_box(
            f"door.frame.{suffix}",
            facade_x - 0.11,
            frame_y,
            local_z,
            frame_w,
            frame_h,
            frame_d,
            "accent" if suffix == "top" else "trim",
            "human-scale-door-frame",
        )
        a.connect(
            f"contact.{prefix}.door.frame.{suffix}",
            door_back,
            frame,
            "door-frame-seat",
            "x",
            0.08,
        )

    if lod == 1:
        return

    # One intentionally composed vent bay per building is preferable to a
    # black-window grid.  Louvers sit inside a thick frame and keep 3D depth.
    if index % 2 == 0:
        vent_z = -door_z
        vent_y = plinth_h + min(lower_h * 0.56, 6.6)
        vent_back = local_box(
            "vent.recess",
            facade_x + 0.02,
            vent_y,
            vent_z,
            0.30,
            2.05,
            4.20,
            "wall_alt",
            "deep-framed-vent",
        )
        a.connect(
            f"contact.{prefix}.vent.recess",
            f"{prefix}.lower",
            vent_back,
            "vent-recess-seat",
            "x",
            0.05,
        )
        for suffix, local_z, frame_h, frame_d in (
            ("south", vent_z - 2.25, 2.55, 0.28),
            ("north", vent_z + 2.25, 2.55, 0.28),
            ("top", vent_z, 0.28, 4.78),
            ("bottom", vent_z, 0.28, 4.78),
        ):
            frame_y = vent_y + (1.16 if suffix == "top" else -1.16 if suffix == "bottom" else 0.0)
            frame = local_box(
                f"vent.frame.{suffix}",
                facade_x - 0.14,
                frame_y,
                local_z,
                0.36,
                frame_h,
                frame_d,
                "trim",
                "deep-framed-vent",
            )
            a.connect(
                f"contact.{prefix}.vent.frame.{suffix}",
                vent_back,
                frame,
                "vent-frame-seat",
                "x",
                0.08,
            )
        for louver_index in range(3):
            louver = local_box(
                f"vent.louver.{louver_index}",
                facade_x - 0.20,
                vent_y - 0.62 + louver_index * 0.62,
                vent_z,
                0.22,
                0.20,
                3.72,
                "accent" if louver_index == 1 else "trim",
                "vent-louver",
            )
            a.connect(
                f"contact.{prefix}.vent.louver.{louver_index}",
                vent_back,
                louver,
                "louver-seat",
                "x",
                0.06,
            )

    # Roof machinery and sparse vertical conduits form readable tertiary
    # detail without spending geometry on invisible micro-greebles.
    unit_x, unit_z = shifted(width * 0.10, depth * 0.12)
    a.box(
        f"{prefix}.roof.hvac",
        unit_x,
        plinth_h + height + 1.25,
        unit_z,
        max(2.4, width * 0.16),
        1.70,
        max(2.0, depth * 0.18),
        "wall_cool",
        yaw=yaw,
        role="roof-service-equipment",
    )
    a.connect(
        f"contact.{prefix}.roof.hvac",
        f"{prefix}.roof",
        f"{prefix}.roof.hvac",
        "hvac-pad-seat",
        "y",
        0.10,
    )
    pipe_z = depth * 0.34
    pipe_x, pipe_world_z = shifted(facade_x + 0.08, pipe_z)
    a.cylinder_between(
        f"{prefix}.facade.riser",
        (pipe_x, plinth_h + 0.35, pipe_world_z),
        (pipe_x, plinth_h + min(lower_h + 1.4, 10.5), pipe_world_z),
        0.16,
        "accent",
        8,
        role="facade-service-riser",
    )
    a.connect(
        f"contact.{prefix}.facade.riser",
        f"{prefix}.lower",
        f"{prefix}.facade.riser",
        "riser-wall-seat",
        "x",
        0.10,
    )


def _build_foothill_city(a: _PlanAssembler, c: KunrenConstraints) -> None:
    lod = c.lod
    # The playable settlement is anchored to the canonical district solver,
    # so every large mass agrees with existing collision rather than becoming
    # an attractive but non-physical facade.  Only the two hero footprints are
    # excluded because they are authored above.
    authoritative_districts = [
        placement
        for placement in c.district_placements
        if not any(
            abs(float(placement.get("cx", 0.0)) - hero.cx) < 0.01
            and abs(float(placement.get("cz", 0.0)) - hero.cz) < 0.01
            for hero in (c.command, c.hangar)
        )
    ]
    district_limit = len(authoritative_districts) if lod == 0 else min(9, len(authoritative_districts)) if lod == 1 else min(6, len(authoritative_districts))
    height_by_kind = {"tower": 39.0, "bunker": 29.0, "hangar": 25.0, "arena": 22.0}
    for index, placement in enumerate(authoritative_districts[:district_limit]):
        kind = str(placement.get("kind", "bunker"))
        width = max(12.0, float(placement.get("width", 20.0)) * (0.78 if kind != "tower" else 0.70))
        depth = max(11.0, float(placement.get("depth", 18.0)) * (0.76 if kind != "tower" else 0.70))
        height = height_by_kind.get(kind, 27.0) + (index % 3) * 2.5
        if index == 2 and kind == "tower":
            # This authoritative east service footprint sits directly on the
            # only low dual-landmark sightline.  Keep it tall and occupied,
            # but below the Hangar crown so the two mega-landmarks remain
            # distinguishable from playable-space cameras.
            height = 31.0
        _add_service_block(
            a,
            index,
            float(placement["cx"]),
            float(placement["cz"]),
            width,
            depth,
            height,
            lod,
            float(placement.get("rot", 0.0)) * math.pi / 2,
            kind=kind,
            detailed=True,
            role=f"canonical-{kind}-district",
        )

    # Outside-boundary silhouette blocks enrich the horizon without changing
    # playable collision.  They are real 3D, never raster/cylindrical mattes.
    horizon_blocks = (
        (-166, 126, 20, 16, 34), (-166, 84, 18, 19, 29), (-164, -82, 20, 17, 31),
        (-118, 166, 24, 15, 38), (-70, 166, 18, 16, 28), (74, 166, 20, 15, 35),
        (126, 164, 22, 17, 39), (166, 92, 18, 16, 30), (215, -160, 20, 18, 35),
        (155, -205, 23, 16, 40), (70, -210, 18, 18, 31), (-20, -205, 20, 15, 28),
    )
    horizon_limit = 12 if lod == 0 else 8 if lod == 1 else 5
    horizon_start = district_limit
    horizon_families = ("tower", "hangar", "bunker", "arena")
    for offset, values in enumerate(horizon_blocks[:horizon_limit]):
        _add_service_block(
            a, horizon_start + offset, *values, lod,
            yaw=(offset % 3 - 1) * 0.08,
            kind=horizon_families[offset % len(horizon_families)],
            detailed=False,
            role="outside-boundary-horizon-building",
        )

    retaining_walls = (
        ("north.west", -96, 1.9, 118, 83, 3.8, 2.2),
        ("north.east", 84, 2.4, 119, 92, 4.8, 2.2),
        ("west.north", -119, 2.2, 70, 2.2, 4.4, 74),
        ("west.south", -121, 2.5, -40, 2.2, 5.0, 58),
        ("south.east", 67, 2.1, -119, 96, 4.2, 2.2),
    )
    wall_limit = 5 if lod == 0 else 4 if lod == 1 else 3
    for suffix, x, y, z, w, h, d in retaining_walls[:wall_limit]:
        a.box(f"city.retaining.{suffix}", x, y, z, w, h, d, "wall_weathered", role="retaining-wall")
        a.box(f"city.retaining.{suffix}.cap", x, y + h / 2 + 0.25, z, w + 0.8, 0.50, d + 0.8, "trim", role="retaining-cap")
        a.connect(
            f"contact.city.retaining.{suffix}", f"city.retaining.{suffix}", f"city.retaining.{suffix}.cap",
            "cap-seat", "y", 0.005,
        )

    # Mountain/rock integration creates near, middle and far depth without a
    # raster horizon.  Rocks sit mostly beyond the playable landmark envelopes.
    ridge_points = (
        (-174, 132, 24, 48), (-170, 96, 21, 39), (-171, -86, 24, 45), (-169, -136, 27, 54),
        (-112, 174, 25, 51), (-64, 176, 21, 42), (66, 175, 23, 47), (126, 171, 26, 53),
        (172, 102, 22, 43), (220, -190, 25, 50), (160, -210, 28, 56), (84, -215, 23, 45),
        (20, -212, 21, 40), (-46, -208, 24, 47),
    )
    rock_count = 14 if lod == 0 else 10 if lod == 1 else 7
    for index, (rx, rz, radius, height) in enumerate(ridge_points[:rock_count]):
        a.rock(
            f"city.ridge.{index}", rx, -2.0, rz, radius, height, "terrain",
            12 if lod == 0 else 8 if lod == 1 else 6, 1800 + index * 37, role="foothill-ridge",
        )
        if lod < 2:
            inward_x = -math.copysign(radius * 0.52, rx) if abs(rx) > abs(rz) else (index % 3 - 1) * radius * 0.46
            inward_z = -math.copysign(radius * 0.52, rz) if abs(rz) >= abs(rx) else (1 - index % 3) * radius * 0.42
            a.rock(
                f"city.ridge.{index}.spur", rx + inward_x, -2.5, rz + inward_z,
                radius * 0.68, height * 0.72, "terrain",
                10 if lod == 0 else 7, 2800 + index * 53, role="foothill-spur",
            )

    # A second, broader mountain belt establishes a genuine far layer behind
    # the settlement.  These are low-frequency 3D masses beyond the playable
    # boundary; no raster skyline or cylindrical picture wall is used.
    far_mountains = (
        (-276, -180, 62, 92), (-282, -104, 58, 88), (-284, -24, 55, 84),
        (-279, 58, 61, 96), (-262, 137, 64, 103), (-226, 207, 59, 98),
        (-168, 248, 62, 108), (-96, 268, 67, 116), (-20, 272, 64, 112),
        (58, 261, 61, 106), (132, 240, 58, 101), (194, 211, 55, 94),
    )
    far_limit = 12 if lod == 0 else 8 if lod == 1 else 6
    for index, (mx, mz, radius, height) in enumerate(far_mountains[:far_limit]):
        a.rock(
            f"city.far-mountain.{index}",
            mx,
            -12.0,
            mz,
            radius,
            height,
            "terrain",
            12 if lod == 0 else 8 if lod == 1 else 6,
            4800 + index * 71,
            role="far-mountain-mass",
        )

    # A few high service bridges articulate the terraced military city.
    bridges = (
        ("west.logistics", (-76, 18.0, -40), (-124, 17.0, -44)),
        ("central.signal", (-36, 17.0, 32), (-28, 24.0, 64)),
        ("south.service", (52, 19.0, -108), (104, 22.0, -80)),
    )
    for suffix, start, end in bridges[: 3 if lod == 0 else 2 if lod == 1 else 1]:
        a.beam(f"city.bridge.{suffix}", start, end, 0.85, 1.35, "trim", role="service-bridge")
        if lod == 0:
            a.beam(
                f"city.bridge.{suffix}.rail", (start[0], start[1] + 1.3, start[2]), (end[0], end[1] + 1.3, end[2]),
                0.12, 0.12, "trim", role="bridge-railing",
            )

    # Sparse 6.8 m streetlights provide a second stable human-scale cue.  The
    # chosen sites remain over 6.5 m from all player spawns and outside both
    # authoritative hero approach rectangles.
    if lod < 2:
        streetlight_sites = ((-112, 13), (-72, -13), (-32, 13), (32, -13), (72, 13), (116, -13))
        light_limit = 6 if lod == 0 else 4
        for index, (lx, lz) in enumerate(streetlight_sites[:light_limit]):
            sign = 1.0 if lz > 0 else -1.0
            base_name = f"city.streetlight.{index}.base"
            pole_name = f"city.streetlight.{index}.pole"
            arm_name = f"city.streetlight.{index}.arm"
            fixture_name = f"city.streetlight.{index}.fixture"
            a.cylinder(base_name, lx, 0.20, lz, 0.28, 0.40, "trim", 10, role="human-scale-streetlight")
            a.cylinder(pole_name, lx, 3.55, lz, 0.095, 6.70, "trim", 8, role="human-scale-streetlight")
            a.beam(
                arm_name,
                (lx, 6.65, lz),
                (lx, 6.65, lz - sign * 1.45),
                0.09,
                0.09,
                "trim",
                role="human-scale-streetlight",
            )
            a.box(
                fixture_name,
                lx,
                6.48,
                lz - sign * 1.45,
                0.44,
                0.24,
                0.64,
                "accent",
                role="streetlight-fixture",
            )
            a.connect(f"contact.{pole_name}", base_name, pole_name, "pole-base-seat", "y", 0.20)
            a.connect(f"contact.{arm_name}", pole_name, arm_name, "lamp-arm-weld", "endpoint", 0.08)
            a.connect(f"contact.{fixture_name}", arm_name, fixture_name, "fixture-seat", "endpoint", 0.08)

        # A central checkpoint gantry gives the long training road a readable
        # foreground event without reducing traversal width or spawn clearance.
        checkpoint_x = 104.0
        for side, checkpoint_z in (("south", -9.4), ("north", 9.4)):
            base_name = f"story.checkpoint.base.{side}"
            post_name = f"story.checkpoint.post.{side}"
            a.box(
                base_name,
                checkpoint_x,
                0.24,
                checkpoint_z,
                0.90,
                0.48,
                0.90,
                "obstacle",
                role="human-scale-checkpoint-base",
            )
            a.cylinder(
                post_name,
                checkpoint_x,
                2.40,
                checkpoint_z,
                0.13,
                4.40,
                "trim",
                10 if lod == 0 else 8,
                role="human-scale-checkpoint-post",
            )
            a.connect(f"contact.{post_name}", base_name, post_name, "gantry-post-seat", "y", 0.20)
        cross_name = "story.checkpoint.crossbeam"
        a.beam(
            cross_name,
            (checkpoint_x, 4.52, -9.4),
            (checkpoint_x, 4.52, 9.4),
            0.22,
            0.30,
            "trim",
            role="checkpoint-overhead-gantry",
        )
        a.connect(
            "contact.story.checkpoint.crossbeam.south",
            "story.checkpoint.post.south",
            cross_name,
            "gantry-weld",
            "endpoint",
            0.10,
        )
        a.connect(
            "contact.story.checkpoint.crossbeam.north",
            "story.checkpoint.post.north",
            cross_name,
            "gantry-weld",
            "endpoint",
            0.10,
        )
        a.box(
            "story.checkpoint.sign-panel",
            checkpoint_x - 0.12,
            4.72,
            0.0,
            0.34,
            1.02,
            5.8,
            "accent",
            role="checkpoint-identification-panel",
        )
        a.connect(
            "contact.story.checkpoint.sign-panel",
            cross_name,
            "story.checkpoint.sign-panel",
            "sign-panel-seat",
            "y",
            0.18,
        )
        if lod == 0:
            for lamp_index, lamp_z in enumerate((-2.0, 0.0, 2.0)):
                lamp_name = f"story.checkpoint.signal.{lamp_index}"
                a.box(
                    lamp_name,
                    checkpoint_x - 0.34,
                    4.67,
                    lamp_z,
                    0.22,
                    0.24,
                    0.34,
                    "accent",
                    role="checkpoint-signal-fixture",
                )
                a.connect(
                    f"contact.{lamp_name}",
                    "story.checkpoint.sign-panel",
                    lamp_name,
                    "signal-fixture-seat",
                    "x",
                    0.08,
                )

    if lod == 2:
        return

    # Story clusters remain away from both authoritative approach rectangles
    # and all four player spawn points.
    hesco_centres = ((15, 103), (15, 107), (15, 111), (20, 111), (25, 111), (25, 107), (25, 103))
    for index, (hx, hz) in enumerate(hesco_centres[: 7 if lod == 0 else 4]):
        a.box(f"story.hesco.{index}", hx, 0.9, hz, 3.8, 1.8, 1.6, "obstacle", role="hesco")
        if lod == 0:
            a.box(f"story.hesco.cap.{index}", hx, 1.86, hz, 3.9, 0.12, 1.7, "trim", role="hesco-cage")

    if lod == 0:
        roadside_hesco = ((122, 13), (117, 13), (112, 13), (122, -13), (117, -13), (112, -13))
        for index, (hx, hz) in enumerate(roadside_hesco):
            a.box(f"story.road-hesco.{index}", hx, 0.9, hz, 4.2, 1.8, 1.7, "obstacle", role="roadside-hesco")
            a.box(f"story.road-hesco.cap.{index}", hx, 1.86, hz, 4.3, 0.12, 1.8, "trim", role="hesco-cage")

    crate_sites = ((9, 116), (12, 116), (15, 116), (132, 78), (135, 78), (6, -119))
    for index, (cx, cz) in enumerate(crate_sites[: 6 if lod == 0 else 3]):
        size = 1.6 if index % 2 else 2.0
        a.box(f"story.crate.{index}", cx, size / 2, cz, size, size, size, "wood", yaw=(index % 3) * 0.17, role="supply-crate")

    vehicle_sites = ((2, -118, -0.10), (110, 18, 0.05)) if lod == 0 else ((2, -118, -0.10),)
    for index, (vx, vz, yaw) in enumerate(vehicle_sites):
        prefix = f"story.vehicle.{index}"
        a.box(f"{prefix}.body", vx, 1.25, vz, 6.8, 1.5, 3.0, "wall_cool", yaw=yaw, role="service-vehicle")
        a.box(f"{prefix}.cab", vx + 1.6, 2.25, vz, 2.5, 1.8, 2.7, "wall_weathered", yaw=yaw, role="service-vehicle")
        if lod == 0:
            for wheel_index, (wx, wz) in enumerate(((-2.2, -1.5), (2.2, -1.5), (-2.2, 1.5), (2.2, 1.5))):
                # Wheel axis runs across the vehicle; slight yaw is omitted in
                # this visual prop because the vehicle body already carries it.
                a.cylinder_between(
                    f"{prefix}.wheel.{wheel_index}",
                    (vx + wx, 0.75, vz + wz - 0.18), (vx + wx, 0.75, vz + wz + 0.18),
                    0.62, "trim", 10, role="vehicle-wheel",
                )

    pipe_runs = (
        ((-16, 1.4, 118), (-3, 1.4, 118)),
        ((-16, 2.4, 120), (-3, 2.4, 120)),
        ((119, 1.3, -105), (136, 1.3, -105)),
    )
    for index, (start, end) in enumerate(pipe_runs[: 3 if lod == 0 else 2]):
        a.cylinder_between(f"story.pipe.{index}", start, end, 0.32, "accent", 10, role="service-pipe")


def _spec_footprint(spec: Any) -> tuple[float, float, float, float, float, float] | None:
    """Return conservative x/z bounds plus y bounds for route validation."""

    if isinstance(spec, BoxSpec):
        cosine, sine = abs(math.cos(spec.yaw)), abs(math.sin(spec.yaw))
        hx = cosine * spec.w / 2 + sine * spec.d / 2
        hz = sine * spec.w / 2 + cosine * spec.d / 2
        return spec.x - hx, spec.x + hx, spec.z - hz, spec.z + hz, spec.y - spec.h / 2, spec.y + spec.h / 2
    if isinstance(spec, CylinderSpec):
        return (
            spec.x - spec.radius, spec.x + spec.radius, spec.z - spec.radius, spec.z + spec.radius,
            spec.y - spec.height / 2, spec.y + spec.height / 2,
        )
    if isinstance(spec, RockSpec):
        return spec.x - spec.radius, spec.x + spec.radius, spec.z - spec.radius, spec.z + spec.radius, spec.y, spec.y + spec.height
    return None


def _intersects_approach(bounds: tuple[float, float, float, float, float, float], approach: ApproachSpec) -> bool:
    min_x, max_x, min_z, max_z, _min_y, _max_y = bounds
    sx, sz = approach.start
    ex, ez = approach.end
    dx, dz = ex - sx, ez - sz
    length = math.hypot(dx, dz)
    if length <= 1e-6:
        raise ValueError("approach start and end must differ")
    ux, uz = dx / length, dz / length
    nx, nz = -uz, ux
    cx, cz = (min_x + max_x) / 2, (min_z + max_z) / 2
    hx, hz = (max_x - min_x) / 2, (max_z - min_z) / 2
    centre_progress = (cx - sx) * ux + (cz - sz) * uz
    progress_radius = abs(ux) * hx + abs(uz) * hz
    centre_lateral = (cx - sx) * nx + (cz - sz) * nz
    lateral_radius = abs(nx) * hx + abs(nz) * hz
    return (
        centre_progress + progress_radius >= 0.0
        and centre_progress - progress_radius <= length + approach.inward_clearance
        and abs(centre_lateral) - lateral_radius < approach.width / 2
    )


def _estimated_triangles(a: _PlanAssembler) -> int:
    total = 12 * (len(a.boxes) + len(a.beams) + len(a.sloped_panels))
    total += sum(4 * spec.segments for spec in a.cylinders)
    total += sum(4 * spec.segments for spec in a.cylinders_between)
    total += sum(8 * spec.segments - 4 for spec in a.rocks)
    return total


def _validate_plan(a: _PlanAssembler, constraints: KunrenConstraints) -> dict[str, Any]:
    all_specs = [*a.boxes, *a.beams, *a.cylinders, *a.cylinders_between, *a.sloped_panels, *a.rocks]
    names = {spec.name for spec in all_specs}
    if len(names) != len(all_specs):
        raise ValueError("A18 plan contains duplicate part names")
    for connection in a.connections:
        missing = {connection.parent, connection.child} - names
        if missing:
            raise ValueError(f"{connection.name} references missing parts {sorted(missing)}")
        if connection.actual_overlap_m < connection.min_overlap_m:
            raise ValueError(f"{connection.name} fails minimum overlap")

    route_violations: list[str] = []
    for spec in [*a.boxes, *a.cylinders, *a.rocks]:
        if isinstance(spec, BoxSpec) and spec.route_exempt:
            continue
        bounds = _spec_footprint(spec)
        if bounds is None or bounds[4] >= 3.0 or bounds[5] <= 0.10:
            continue
        for hero in (constraints.command, constraints.hangar):
            if _intersects_approach(bounds, hero.approach):
                route_violations.append(f"{spec.name}:{hero.landmark_id}")
    if route_violations:
        raise ValueError(f"A18 geometry blocks authoritative approaches: {route_violations[:8]}")

    spawn_violations: list[str] = []
    for spec in [*a.boxes, *a.cylinders, *a.rocks]:
        if isinstance(spec, BoxSpec) and spec.route_exempt:
            continue
        bounds = _spec_footprint(spec)
        if bounds is None or bounds[4] >= 3.0 or bounds[5] <= 0.10:
            continue
        for spawn_index, (sx, _sy, sz) in enumerate(constraints.player_spawns):
            closest_x = min(max(sx, bounds[0]), bounds[1])
            closest_z = min(max(sz, bounds[2]), bounds[3])
            if math.hypot(sx - closest_x, sz - closest_z) < 6.5:
                spawn_violations.append(f"{spec.name}:player-{spawn_index}")
    if spawn_violations:
        raise ValueError(f"A18 geometry violates 6.5m player-spawn clearance: {spawn_violations[:8]}")

    primitive_count = len(all_specs)
    triangles = _estimated_triangles(a)
    materials = sorted({spec.key for spec in all_specs})
    budget = constraints.lod_budget
    if primitive_count > budget.max_primitives:
        raise ValueError(f"A18 primitive budget exceeded: {primitive_count}>{budget.max_primitives}")
    if triangles > budget.max_estimated_triangles:
        raise ValueError(f"A18 triangle budget exceeded: {triangles}>{budget.max_estimated_triangles}")
    if len(materials) > budget.max_materials:
        raise ValueError(f"A18 material budget exceeded: {len(materials)}>{budget.max_materials}")

    collision_counts = {
        landmark_id: sum(1 for box in constraints.collision_boxes if box.get("landmarkId") == landmark_id)
        for landmark_id in (COMMAND_ID, HANGAR_ID)
    }
    role_counts: dict[str, int] = {}
    for spec in all_specs:
        role_counts[spec.role] = role_counts.get(spec.role, 0) + 1
    layer_counts = {
        "nearHumanScaleAndStory": sum(
            1
            for spec in all_specs
            if "human-scale" in spec.role
            or spec.name.startswith("story.")
            or spec.role in {"streetlight-fixture", "interior-worklight-fixture", "painted-route-guide"}
        ),
        "midPlayableArchitecture": sum(
            1
            for spec in all_specs
            if spec.name.startswith(("cmd.", "hall.", "city.block."))
            and spec.role not in {"outside-boundary-horizon-building", "far-mountain-mass"}
        ),
        "farPhysicalHorizon": sum(
            1
            for spec in all_specs
            if spec.role in {"outside-boundary-horizon-building", "foothill-ridge", "foothill-spur", "far-mountain-mass"}
        ),
    }
    return {
        "primitiveCount": primitive_count,
        "estimatedTriangles": triangles,
        "materials": materials,
        "roleCounts": dict(sorted(role_counts.items())),
        "layerCounts": layer_counts,
        "heroPartCounts": {
            COMMAND_ID: sum(1 for spec in all_specs if spec.name.startswith("cmd.")),
            HANGAR_ID: sum(1 for spec in all_specs if spec.name.startswith("hall.")),
        },
        "routeViolations": route_violations,
        "spawnViolations": spawn_violations,
        "collisionLandmarkBoxCounts": collision_counts,
    }


def make_kunren_reference_a18_plan(
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: Mapping[str, ApproachSpec | Mapping[str, Any]] | None = None,
    lod_budget: LODBudget | None = None,
) -> KunrenPlan:
    """Create a validated, immutable A18 plan without requiring Blender."""

    constraints = constraints_from_authoritative_layout(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=lod_budget,
    )
    assembler = _PlanAssembler()
    _build_command_bastion(assembler, constraints.command, lod)
    _build_aerostat_hangar(assembler, constraints.hangar, lod)
    _build_foothill_city(assembler, constraints)
    metrics = _validate_plan(assembler, constraints)
    metadata = {
        "kitVersion": KIT_VERSION,
        "stageId": constraints.stage_id,
        "lod": lod,
        "coordinateSystem": "runtime-xz-horizontal-y-up-metres",
        "collisionPolicy": "visual-only-preserve-authoritative-collision",
        "collisionSource": constraints.collision_source,
        "collisionBoxCount": len(constraints.collision_boxes),
        "authoritativeLayoutInputs": {
            "districtPlacementCount": len(constraints.district_placements),
            "propPlacementCount": len(constraints.prop_placements),
            "playerSpawnCount": len(constraints.player_spawns),
            "botSpawnCount": len(constraints.bot_spawns),
        },
        "referenceSource": {
            "path": "tools/blender/concepts/kunren-reference-v1.png",
            "sha256": REFERENCE_IMAGE_SHA256,
            "analysisBasis": "REFERENCE_MATRIX.md plus measured A18 production brief",
        },
        "identityTargets": {
            COMMAND_ID: "tiered castle-scale mechanical command bastion with framed portal, bridge, maintenance ladders, service terraces and radar crown",
            HANGAR_ID: "monumental ribbed aerostat vault with complete portal collar, deep trusses, catwalk stairs, worklights and suspended envelope",
            "settlement": "dense terraced foothill military city with four district facade families and physical 3D near/mid/far layers",
        },
        "surfaceResponseContract": {
            "releaseRule": "hero surfaces require deliberate base-color variation, roughness breakup and relief response; flat color alone is blockout",
            "sharedFamilies": [
                "weathered-reinforced-concrete",
                "painted-and-oxidized-metal",
                "rock-and-compacted-earth",
                "rough-timber",
            ],
            "requiredChannels": ["baseColor", "roughness", "normalOrBump"],
            "accentEmissionRule": "restrained fixtures and route accents only; no broad emissive walls",
            "chamferRule": "one crisp weighted edge response on first-person hard-surface silhouettes",
        },
        "textureAtlasContract": {
            "strategy": "shared reusable shader masters or stage atlas; no unique texture per primitive",
            "maximumHeroMaterialSlots": 12,
            "microdetailDestination": ["baseColor", "roughness", "normalOrBump"],
            "forbidden": ["unknown-license embedded textures", "raster skyline", "cylindrical picture wall"],
        },
        "humanScaleContract": {
            "eyeHeightM": 1.65,
            "serviceDoorHeightM": 2.50,
            "minimumReleaseCues": [
                "framed-service-doors",
                "maintenance-ladders",
                "catwalk-railings-and-stairs",
                "streetlights",
                "bollards-drums-crates-and-vehicles",
            ],
            "lod0HumanScalePrimitiveCount": metrics["layerCounts"]["nearHumanScaleAndStory"] if lod == 0 else None,
        },
        "nearMidFarContract": {
            "near": "grounded props, painted routes, doors, stairs, rails and contact shadows",
            "mid": "two hero landmarks plus distinct authoritative district architecture",
            "far": "outside-boundary buildings, foothill ridges and broad 3D mountain belt",
            "rasterMatteAllowed": False,
        },
        "lightingIntent": {
            "key": "warm directional late-afternoon sun",
            "fill": "cool sky and restrained atmospheric depth",
            "local": "warm hangar worklights and sparse street fixtures",
            "gameplayDepthOfField": False,
        },
        "formalReferenceGate": {
            "categories": [
                "composition-and-reference-match",
                "hero-landmark-silhouettes",
                "architecture-and-facade-language",
                "human-scale-credibility",
                "material-and-surface-realism",
                "near-mid-far-density",
                "route-and-combat-readability",
                "props-and-environmental-storytelling",
                "lighting-and-atmosphere",
                "stage-specific-identity",
            ],
            "minimumPerCategory": 7.0,
            "minimumAverage": 8.0,
            "requiredPerspectiveViewsAt1p65m": 10,
            "scorecardMustBeSigned": True,
        },
        "heroEnvelopes": {
            "command": asdict(constraints.command),
            "hangar": asdict(constraints.hangar),
        },
        "approachContracts": {
            constraints.command.landmark_id: asdict(constraints.command.approach),
            constraints.hangar.landmark_id: asdict(constraints.hangar.approach),
        },
        "lodBudget": asdict(constraints.lod_budget),
        "metrics": metrics,
        "connectionMap": [asdict(connection) for connection in assembler.connections],
        "verificationRequired": [
            "bounds-and-envelope",
            "contact-faces-and-minimum-overlap",
            "six-orthographic-sides",
            "ten-or-more-distinct-1.65m-perspective-views",
            "evaluated-topology-and-transform-audit",
            "signed-formal-ten-category-reference-scorecard",
            "real-browser-collision-and-performance",
        ],
    }
    return KunrenPlan(
        boxes=tuple(assembler.boxes),
        beams=tuple(assembler.beams),
        cylinders=tuple(assembler.cylinders),
        cylinders_between=tuple(assembler.cylinders_between),
        sloped_panels=tuple(assembler.sloped_panels),
        rocks=tuple(assembler.rocks),
        connections=tuple(assembler.connections),
        metadata=metadata,
    )


def emit_kunren_reference_a18_plan(builder: MeshBuilderProtocol, plan: KunrenPlan) -> Mapping[str, Any]:
    """Emit a previously reviewed plan through the existing builder helpers."""

    for spec in plan.boxes:
        if abs(spec.yaw) > 1e-8:
            builder.add_oriented_box(spec.x, spec.y, spec.z, spec.w, spec.h, spec.d, spec.yaw, spec.key)
        else:
            builder.add_box(spec.x, spec.y, spec.z, spec.w, spec.h, spec.d, spec.key)
    for spec in plan.beams:
        builder.add_beam(spec.start, spec.end, spec.width, spec.depth, spec.key)
    for spec in plan.cylinders:
        builder.add_cylinder(
            spec.x, spec.y, spec.z, spec.radius, spec.height, spec.key, spec.segments, spec.top_radius
        )
    for spec in plan.cylinders_between:
        builder.add_cylinder_between(
            spec.start, spec.end, spec.radius, spec.key, spec.segments, spec.end_radius
        )
    for spec in plan.sloped_panels:
        builder.add_sloped_panel(spec.corners, spec.thickness, spec.key)
    for spec in plan.rocks:
        builder.add_rock(spec.x, spec.y, spec.z, spec.radius, spec.height, spec.key, spec.segments, spec.seed)
    return plan.metadata


def build_kunren_reference_a18(
    builder: MeshBuilderProtocol,
    stage: Mapping[str, Any],
    lod: int,
    *,
    collision_boxes: Iterable[Mapping[str, Any]] | None = None,
    entrance_overrides: Mapping[str, Sequence[float]] | None = None,
    approach_overrides: Mapping[str, ApproachSpec | Mapping[str, Any]] | None = None,
    lod_budget: LODBudget | None = None,
) -> Mapping[str, Any]:
    """Integration-ready entry point for the catalog builder."""

    plan = make_kunren_reference_a18_plan(
        stage,
        lod,
        collision_boxes=collision_boxes,
        entrance_overrides=entrance_overrides,
        approach_overrides=approach_overrides,
        lod_budget=lod_budget,
    )
    return emit_kunren_reference_a18_plan(builder, plan)


__all__ = [
    "ApproachSpec",
    "AuthoritativeKunrenLayout",
    "COMMAND_ID",
    "DEFAULT_LOD_BUDGETS",
    "HANGAR_ID",
    "KIT_VERSION",
    "KunrenConstraints",
    "KunrenPlan",
    "LODBudget",
    "REFERENCE_IMAGE_SHA256",
    "build_kunren_reference_a18",
    "constraints_from_authoritative_layout",
    "emit_kunren_reference_a18_plan",
    "load_authoritative_kunren_layout",
    "make_kunren_reference_a18_plan",
]
