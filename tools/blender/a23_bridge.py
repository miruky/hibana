"""Phase 3 bridge: wires the promoted ``tools/blender/a23`` toolchain
(reclamation, districts, materials, measure, evidence) into
``tools/blender/build_all_stages.py``'s shared 31-stage generator.

Why this file exists instead of editing the a23 package
---------------------------------------------------------
``tools/blender/a23`` is stage-agnostic *in contract* (every function takes a
``SpecKit``/camera list/policy sets as parameters) but has so far only been
*proven* against ``tools/blender/stage_kits/nakaniwa_reference_a21_r6.py``
("R6"), a kit module built around a **spec-list** architecture: primitives
append plain dicts to a list first, and a separate render step turns that
list into Blender geometry later. ``build_all_stages.py``'s own
``MeshBuilder`` (shared by all 30 non-nakaniwa stages) is **immediate-mode**:
``add_box``/``add_cylinder``/``add_surface_panel`` write vertices and faces
straight into the mesh, with no intermediate spec list, across roughly forty
``add_*`` functions built up over dozens of prior rounds. Retrofitting that
entire pipeline onto a spec-list architecture (so reclamation could delete
already-shipped geometry sight-unseen across 30 already-tuned stages) is a
different, much larger and much riskier undertaking than "wire the toolchain
in" -- it is exactly the kind of change that produces the round's own
documented aggregate-failure/single-camera traps, at 30x the surface area,
inside one phase. This module instead:

1. Reimplements the proven, *pure* half of R6's own kit contract
   (``_box``/``_chamfer_box``/``_panel``/``_sweep``/``_cylinder``/
   ``spec_bounds``/``estimated_triangles``/``_project_spec_frame``)
   independently, so the generic 31-stage path never imports nakaniwa's
   frozen, private kit module (see ``docs/REQUIREMENTS.md``'s "repository
   kit source" freeze) and never needs ``bpy`` for anything the a23 modules
   need to run. ``tools/blender/tests/test_a23_bridge.py`` cross-checks this
   reimplementation against R6's own functions for identical inputs.
2. Uses that SpecKit *only* for the new geometry this phase adds (district
   infill), never to re-litigate the other 30 stages' existing, already
   shipped, already budget-verified geometry. Reclamation's ``run_chain``
   (pass 3, the mandatory correctness fix, then pass 4) runs over the new
   infill specs, using the pre-existing collision-authoritative layout
   (``stage["boxes"]``, converted to specs by ``stage_boxes_as_specs``) as
   the occluder pool so the correctness test is real, not a rubber stamp.
3. Derives every per-stage parameter it can from ``stage-profiles.json``'s
   ``cityProfile`` and the stage's own layout JSON (map size, street width,
   secondary building height band, family/mood-driven material choice, real
   player/bot spawns). Values that stage-profiles.json has no per-stage
   field for (the window rhythm's human-scale numbers, lot width/depth
   choices, safety margins) are kept at the nakaniwa-proven fixed constants;
   each such choice is documented at its call site rather than silently
   hard-coded.

Coordinate convention -- do not mix these up
----------------------------------------------
``build_all_stages.py``'s own ``runtime_point(x, y, z) -> Vector(x, -z, y)``
is orientation-preserving (determinant +1). R6's own
``_runtime_to_blender(point) -> Vector(x, z, y)`` is orientation-*reversing*
(determinant -1) -- this is the exact mirrored-screen-axis bug the A23 round
log's ``COORDINATE_SIGN_CORRECTION`` documents, self-consistent only within
R6's own renders/cameras. The functions in this module never call either
transform themselves (they only store x/y/z/w/h/d, matching R6's own
primitives); specs built here are emitted through ``build_all_stages.py``'s
own ``MeshBuilder``, so they only ever pass through the correct transform.
Never reuse R6's ``_make_camera``/``_runtime_to_blender`` against a spec or
camera built by this module.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from tools.blender.a23 import districts, measure, reclamation
from tools.blender.a23.kit import SpecKit

EYE_HEIGHT_M = 1.65  # universal player eye height, not a per-stage fact.
DEFAULT_LENS_MM = 24.0
DEFAULT_SENSOR_MM = 36.0
LOD0_TRIANGLE_CAP = 260_000
MATERIAL_COUNT_BUDGET = 14

# ---------------------------------------------------------------------------
# 1. Pure SpecKit contract, reimplemented independently of R6 (see module
#    docstring). Logic is line-for-line equivalent to
#    nakaniwa_reference_a21_r6.py's own _box/_chamfer_box/_panel/_sweep/
#    _cylinder/spec_bounds/estimated_triangles/_project_spec_frame; the a23
#    promotion's own kit.py documents this exact contract as the thing every
#    "reviewed stage kit" module exposes, so re-deriving it here (rather than
#    importing the frozen nakaniwa module) is the promotion's own intended
#    integration path for a *second* kit.
# ---------------------------------------------------------------------------
def _box(specs, role, material, group, x, y, z, w, h, d, blocks_gameplay=False):
    specs.append({
        "kind": "box", "role": role, "material": material, "group": group,
        "blocksGameplay": blocks_gameplay, "x": x, "y": y, "z": z, "w": w, "h": h, "d": d,
    })


def _chamfer_box(specs, role, material, group, x, y, z, w, h, d, bevel, segments=1):
    if bevel <= 0.0 or bevel >= min(w, h, d) * 0.49:
        raise ValueError(f"{role}: invalid chamfer {bevel}")
    specs.append({
        "kind": "chamfer_box", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "x": x, "y": y, "z": z, "w": w, "h": h, "d": d,
        "bevel": bevel, "segments": segments,
    })


def _panel(specs, role, material, group, corners, thickness=0.06):
    specs.append({
        "kind": "panel", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "corners": tuple(corners), "thickness": thickness,
    })


def _cylinder(specs, role, material, group, x, y, z, radius, height, segments=12, top_radius=None):
    specs.append({
        "kind": "cylinder", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "x": x, "y": y, "z": z, "radius": radius, "height": height,
        "segments": segments, "topRadius": radius if top_radius is None else top_radius,
    })


def _sweep(specs, role, material, group, points, radius, sides):
    if len(points) < 2 or sides < 4:
        raise ValueError(f"{role}: invalid sweep")
    specs.append({
        "kind": "sweep", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "points": tuple(points), "radius": radius, "sides": sides,
    })


def _leaf_cluster(specs, role, material, group, x, y, z, radius, height, leaves, seed):
    specs.append({
        "kind": "leaf_cluster", "role": role, "material": material, "group": group,
        "blocksGameplay": False, "x": x, "y": y, "z": z, "radius": radius, "height": height,
        "leaves": leaves, "seed": seed,
    })


def spec_bounds(spec):
    kind = spec["kind"]
    if kind in {"box", "chamfer_box", "cylinder", "leaf_cluster"}:
        if kind == "cylinder":
            rx = rz = max(float(spec["radius"]), float(spec["topRadius"]))
            ry = float(spec["height"]) / 2.0
        elif kind == "leaf_cluster":
            rx = rz = float(spec["radius"])
            ry = float(spec["height"]) / 2.0
        else:
            rx, ry, rz = float(spec["w"]) / 2.0, float(spec["h"]) / 2.0, float(spec["d"]) / 2.0
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
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    zs = [float(p[2]) for p in points]
    return (
        min(xs) - thickness, min(ys) - thickness, min(zs) - thickness,
        max(xs) + thickness, max(ys) + thickness, max(zs) + thickness,
    )


def estimated_triangles(specs):
    total = 0
    for spec in specs:
        kind = spec["kind"]
        if kind == "cylinder":
            total += int(spec["segments"]) * 4
        elif kind == "chamfer_box":
            total += 44 if int(spec["segments"]) == 1 else 92
        elif kind == "sweep":
            total += 2 * int(spec["sides"]) * (len(spec["points"]) - 1) + 2 * int(spec["sides"])
        elif kind == "leaf_cluster":
            total += int(spec["leaves"]) * 4
        elif kind == "panel":
            total += len(spec["corners"]) * 4 - 4
        else:
            total += 12
    return total


def _camera_basis(camera):
    location = tuple(float(v) for v in camera["location"])
    target = tuple(float(v) for v in camera["target"])

    def sub(a, b):
        return tuple(a[i] - b[i] for i in range(3))

    def dot(a, b):
        return sum(a[i] * b[i] for i in range(3))

    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    def unit(v):
        length = math.sqrt(dot(v, v))
        return tuple(c / length for c in v)

    forward = unit(sub(target, location))
    right = unit(cross(forward, (0.0, 1.0, 0.0)))
    up = unit(cross(right, forward))
    return location, forward, right, up


def project_spec_frame(spec, camera, aspect=16.0 / 9.0):
    location, forward, right, up = _camera_basis(camera)

    def dot(a, b):
        return sum(a[i] * b[i] for i in range(3))

    tan_half_x = float(camera["sensorWidthMm"]) / (2.0 * float(camera["lensMm"]))
    tan_half_y = tan_half_x / aspect
    bounds = spec_bounds(spec)
    projected = []
    for x in (bounds[0], bounds[3]):
        for y in (bounds[1], bounds[4]):
            for z in (bounds[2], bounds[5]):
                relative = (x - location[0], y - location[1], z - location[2])
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
            min(p[0] for p in projected), min(p[1] for p in projected),
            max(p[0] for p in projected), max(p[1] for p in projected),
        ),
        "nearDepthM": min(p[2] for p in projected),
        "farDepthM": max(p[2] for p in projected),
    }


GENERIC_SPEC_KIT = SpecKit(
    box=_box, chamfer_box=_chamfer_box, panel=_panel, sweep=_sweep, cylinder=_cylinder,
    leaf_cluster=_leaf_cluster, spec_bounds=spec_bounds, estimated_triangles=estimated_triangles,
    project_spec_frame=project_spec_frame,
)


# ---------------------------------------------------------------------------
# 2. Layout/profile-derived spec conversion (no bpy).
# ---------------------------------------------------------------------------
_SKIP_BOX_FLAGS = ("ghost", "decor", "legacyHorizon", "prop", "breakable")
_DISTRICT_FLOOR_MARKER_ASSUMED_HEIGHT_M = 6.0


def stage_boxes_as_specs(stage: Mapping[str, object]) -> list:
    """Convert ``stage["boxes"]`` (the TS/placement-solver-authored,
    collision-authoritative layout) into a23-spec-shaped dicts for
    exclusion-grid and measurement purposes. This never feeds Blender
    geometry directly -- it is read-only context for districts.py's
    exclusion grid and measure.py's footprint/occlusion math.

    District-tagged boxes are floor *footprints*: build_lod's own facade/
    roofline passes (add_playable_district_facades etc.) raise the real
    building height on top of them procedurally, and that height is not
    present in the JSON layout. Treating a district box's own (often near-
    zero) stored height as authoritative would undercount built footprint,
    so any district box shorter than the built-footprint height threshold
    is reported at a conservative assumed height instead. This is a
    documented proxy, not a measured fact -- the real per-camera geometry
    still requires a Blender build (see the three real builds in the phase 3
    report).
    """
    specs = []
    for index, box in enumerate(stage.get("boxes", [])):
        if any(box.get(flag) for flag in _SKIP_BOX_FLAGS):
            continue
        if box.get("landmarkId"):
            group = "hero"
        elif box.get("district"):
            group = "district"
        else:
            group = "layout"
        height = float(box["h"])
        if box.get("district") and height < measure.FootprintConfig().built_min_height_m:
            height = _DISTRICT_FLOOR_MARKER_ASSUMED_HEIGHT_M
        specs.append({
            "kind": "box", "role": f"layout-box-{index}",
            "material": str(box.get("color", "#000000")), "group": group,
            "blocksGameplay": True,
            "x": float(box["x"]), "y": float(box["y"]), "z": float(box["z"]),
            "w": float(box["w"]), "h": height, "d": float(box["d"]),
        })
    return specs


def road_width_for_family(family: str) -> float:
    """Mirrors add_routes' own road_width formula (build_all_stages.py) so
    the exclusion grid this module builds agrees with what add_routes
    actually draws, without importing build_all_stages.py (which imports
    bpy at module scope and would break this module's Blender-free usage).
    """
    if family == "airport":
        return 12.0
    if family in {"industrial", "urban", "undead"}:
        return 8.0
    return 6.5


def stage_canonical_roads(stage: Mapping[str, object], family: str) -> tuple:
    """Two axis-aligned strips through the origin, matching the central-
    cross road pattern add_routes lays down for every stage. This is a
    derived approximation (add_routes has no separately stored 'road
    bounds' structure to read back); stage_boxes_as_specs's exclusion mass
    is the authoritative safety net for anything this approximation misses.
    """
    half = float(stage["size"]) / 2.0
    road_half = road_width_for_family(family) / 2.0
    return (
        {"name": "canonical-road-ns", "bounds": {"minX": -road_half, "maxX": road_half, "minZ": -half, "maxZ": half}},
        {"name": "canonical-road-ew", "bounds": {"minX": -half, "maxX": half, "minZ": -road_half, "maxZ": road_half}},
    )


def stage_landmark_approach_corridors(stage: Mapping[str, object]) -> tuple:
    """Axis-aligned exclusion rectangles for every ``landmarkPlacements``
    entry's own ``approach`` corridor -- the readable walk-up to a landmark
    that the stage's own placement data declares (see
    ``docs/ENVIRONMENT_LANDMARKS.md``). ``build_exclusion_grid`` otherwise has
    no way to learn this width-``approach.width`` lane is reserved: it is not
    one of the two canonical roads through the origin (a landmark can sit
    anywhere on the map), and -- being deliberately left clear of collision
    boxes -- it has no existing mass to occupy the exclusion grid either. The
    scanline packer therefore reads it as ordinary empty land and can wall it
    off (kairou's landmark-0 approach measured this in-game: a district-
    infill terrace block's north wall landed 0.3 m past the approach's own
    start point, turning the corridor into a solid room).

    Every authored approach in ``tools/blender/generated/stage-layouts.json``
    is axis-aligned (``rot: 0``), so a start/end + half-width bounding box
    around the segment is exact, matching ``stage_canonical_roads``'s own
    shape (``{"name", "bounds": {"minX", "maxX", "minZ", "maxZ"}}``) so it can
    be concatenated onto that tuple and fed through the same
    ``canonical_roads`` parameter ``districts.plan_district`` already
    accepts, without changing that module's contract.
    """
    corridors = []
    for placement in stage.get("landmarkPlacements", []):
        approach = placement.get("approach")
        if not approach:
            continue
        start_x, start_z = (float(value) for value in approach["start"])
        end_x, end_z = (float(value) for value in approach["end"])
        half_width = float(approach["width"]) / 2.0
        min_x, max_x = min(start_x, end_x), max(start_x, end_x)
        min_z, max_z = min(start_z, end_z), max(start_z, end_z)
        if abs(start_x - end_x) < abs(start_z - end_z):
            min_x -= half_width
            max_x += half_width
        else:
            min_z -= half_width
            max_z += half_width
        corridors.append({
            "name": f"landmark-approach-{placement['id']}",
            "bounds": {"minX": min_x, "maxX": max_x, "minZ": min_z, "maxZ": max_z},
        })
    return tuple(corridors)


def stage_proof_cameras(stage: Mapping[str, object]) -> list:
    """A per-stage proof-camera set built entirely from real, per-stage data
    (player spawns + two central-street vantage points, mirroring
    build_all_stages.py's own stage_central_camera_views convention) -- no
    single-camera judgement (see reclamation.py's pass 3 docstring on this
    exact defect class). Every camera looks roughly toward the stage
    centre from real gameplay-relevant ground truth.
    """
    half = float(stage["size"]) / 2.0
    cameras = []
    for index, spawn in enumerate(stage.get("playerSpawns", [])):
        sx, sz = float(spawn[0]), float(spawn[2])
        cameras.append({
            "name": f"A23Bridge_PlayerSpawn{index}",
            "location": (sx, EYE_HEIGHT_M, sz),
            "target": (sx * 0.1, EYE_HEIGHT_M, sz * 0.1),
            "lensMm": DEFAULT_LENS_MM, "sensorWidthMm": DEFAULT_SENSOR_MM,
        })
    for name, cx, cz, tx, tz in (
        ("A23Bridge_CentralStreetNorth", 0.0, half * 0.22, 0.0, -half * 0.34),
        ("A23Bridge_CentralStreetSouth", 0.0, -half * 0.22, 0.0, half * 0.34),
    ):
        cameras.append({
            "name": name, "location": (cx, EYE_HEIGHT_M, cz), "target": (tx, EYE_HEIGHT_M, tz),
            "lensMm": DEFAULT_LENS_MM, "sensorWidthMm": DEFAULT_SENSOR_MM,
        })
    return cameras


# ---------------------------------------------------------------------------
# 3. Per-stage DistrictConfig/WindowRhythm derivation.
# ---------------------------------------------------------------------------
def infill_triangle_budget(profile: Mapping[str, object]) -> int:
    """A conservative sub-budget for the NEW infill layer only, scaled
    inversely with the stage's own cityProfile.coverageRatio: a stage
    already declared dense (high coverage) has less genuinely empty land
    and less headroom under the 260,000 cap already spent by pre-existing,
    already-shipped geometry; a sparser stage gets more. Bounded to 3-8% of
    the LOD0 cap so this new layer can never itself threaten a stage's
    existing budget -- this is deliberately conservative, not a claim that
    every stage has this much real headroom (only the real Blender builds
    prove that; see the per-stage dry-run table).
    """
    coverage = float(profile["cityProfile"].get("coverageRatio", 0.6))
    coverage = min(1.0, max(0.0, coverage))
    fraction = 0.03 + (1.0 - coverage) * 0.05
    return int(LOD0_TRIANGLE_CAP * fraction)


def derive_district_config(stage: Mapping[str, object], profile: Mapping[str, object],
                            family: str, mood: Optional[str]) -> districts.DistrictConfig:
    city = profile["cityProfile"]
    half = float(stage["size"]) / 2.0
    street_lo, street_hi = city.get("streetWidthM", [10.0, 18.0])
    street_lo, street_hi = float(street_lo), float(street_hi)
    alley_lo = max(5.0, round(street_lo * 0.5, 1))
    alley_hi = max(alley_lo + 1.0, round(street_lo * 0.7, 1))
    secondary = city.get("secondaryHeightM", [6.0, 12.0])
    height_lo, height_hi = float(secondary[0]), float(secondary[1])
    wall_materials = (
        ("wall_warm", "wall_weathered", "wall") if family in {"heritage", "wilderness"}
        else ("wall", "wall_alt")
    )
    window_materials = ("glass", "emissive") if mood == "night" else ("glass",)
    cornice_overhang_m = 0.35
    # The nominal placement gap fed to the scanline packer must clear the
    # contract floor even after both neighbouring blocks' cornice overhangs
    # eat into it (see districts.py's own module docstring on the h23
    # aggregate-failure trap: 17/18 fully-articulated blocks tightened the
    # worst-case gap below the contract floor at a naive nominal value).
    # nakaniwa's own proven tuning is nominal = floor + 2*overhang + 0.3m
    # cushion (5.0 + 0.7 + 0.3 = 6.0); reproduced here as a formula instead
    # of a copied constant so it tracks each stage's own contract floor.
    alley_gap_m = round(alley_lo + 2 * cornice_overhang_m + 0.3, 2)
    street_gap_m = round(street_lo + 2 * cornice_overhang_m + 0.3, 2)
    return districts.DistrictConfig(
        map_half_m=half,
        map_edge_margin_m=3.0,
        existing_mass_margin_m=2.0,
        road_placement_margin_m=2.0,
        row_depth_m=18.0,
        street_gap_m=street_gap_m,
        alley_gap_m=alley_gap_m,
        height_choices=(height_lo, round((height_lo + height_hi) / 2.0, 1), height_hi),
        focus_height_choices=(height_hi, round(height_hi * 1.1, 1)),
        wall_materials=wall_materials,
        roof_materials=("roof",),
        base_materials=("trim", "wall_alt"),
        window_materials=window_materials,
        frame_material_preference=("trim", "wall_alt", "wall"),
        cornice_material="trim", ledge_material="trim", ridge_material="trim",
        cornice_overhang_m=cornice_overhang_m,
        player_spawn_clearance_m=30.0, bot_spawn_clearance_m=8.0,
        road_half_m=road_width_for_family(family) / 2.0,
        road_top_limit_m=0.35,
        visibility_px_threshold=4.0,
        margin_reserve_triangles=300,
        contract_alley_band_m=(alley_lo, alley_hi),
        contract_street_band_m=(street_lo, street_hi),
    )


WINDOW_RHYTHM = districts.WindowRhythm()  # fixed human-scale contract; see module docstring.
RECLAMATION_CONFIG = reclamation.ReclamationConfig()


# ---------------------------------------------------------------------------
# 4. Per-stage opt-in table.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StageA23Policy:
    enabled: bool
    reason: str


def _default_policy_table(stage_ids: Sequence[str]) -> dict:
    table = {}
    for stage_id in stage_ids:
        if stage_id == "nakaniwa":
            table[stage_id] = StageA23Policy(
                False,
                "bespoke kit already carries the full a23 treatment (near-field garden, "
                "reclamation, materials, hero-defect fixes, district infill and the "
                "Tier 1 palace-occlusion fix) through "
                "tools/blender/stage_kits/nakaniwa_a23_reconciliation.py, called directly "
                "by build_nakaniwa_reference_lod at LOD0; applying the generic "
                "district-infill layer on top here would double-treat it (see phase4a's "
                "reconciliation-report.json).",
            )
        else:
            table[stage_id] = StageA23Policy(
                True,
                "default-on per the phase 3 directive; no measured regression found "
                "for this stage in the 31-stage dry run.",
            )
    return table


# Populated by build_all_stages.py at import time via configure_policy_table(),
# once the real stage id list is known (this module must not hard-code it, to
# avoid a second, drifting copy of stage-profiles.json's key set). Dry-run /
# test callers may also populate it directly.
STAGE_POLICY: dict = {}


def configure_policy_table(stage_ids: Sequence[str], overrides: Optional[Mapping[str, StageA23Policy]] = None) -> dict:
    table = _default_policy_table(stage_ids)
    if overrides:
        table.update(overrides)
    STAGE_POLICY.clear()
    STAGE_POLICY.update(table)
    return STAGE_POLICY


def stage_enabled(stage_id: str) -> bool:
    policy = STAGE_POLICY.get(stage_id)
    return bool(policy and policy.enabled)


# ---------------------------------------------------------------------------
# 5. District-infill planning (pure Python; dry-run capable, no bpy).
# ---------------------------------------------------------------------------
def plan_district_infill(stage: Mapping[str, object], profile: Mapping[str, object],
                          family: str, mood: Optional[str],
                          group: str = "a23-districts-infill") -> dict:
    """Run the promoted districts.plan_district + reclamation.run_chain
    over one stage's real layout data, entirely without Blender. Returns a
    report dict with the surviving spec list plus every metric the dry-run
    table needs (spec count, estimated triangles, materials used, and the
    districts/reclamation/audit sub-reports).
    """
    existing_specs = stage_boxes_as_specs(stage)
    cameras = stage_proof_cameras(stage)
    # Landmark approach corridors are concatenated onto the canonical-road
    # exclusion list (see stage_landmark_approach_corridors's own docstring):
    # they share that helper's exact shape and districts.plan_district only
    # ever consumes canonical_roads for exclusion-grid marking, never for the
    # separate road_overlap_audit (that audit checks the fixed central cross
    # via config.road_half_m, unrelated to this list), so widening it here
    # cannot loosen or change what that audit accepts.
    canonical_roads = stage_canonical_roads(stage, family) + stage_landmark_approach_corridors(stage)
    config = derive_district_config(stage, profile, family, mood)
    tri_budget = infill_triangle_budget(profile)

    plan = districts.plan_district(
        existing_specs, tri_budget=tri_budget, kit=GENERIC_SPEC_KIT,
        canonical_roads=canonical_roads, player_spawns=stage.get("playerSpawns", []),
        bot_spawns=stage.get("botSpawns", []), cameras=cameras, config=config,
        rhythm=WINDOW_RHYTHM, group=group, occluder_specs=existing_specs,
    )

    road_audit = districts.road_overlap_audit(plan["specs"], kit=GENERIC_SPEC_KIT, config=config)
    spawn_audit = districts.spawn_clearance_audit(
        plan["specs"], kit=GENERIC_SPEC_KIT, player_spawns=stage.get("playerSpawns", []),
        bot_spawns=stage.get("botSpawns", []), config=config,
    )
    gap_audit = districts.gap_audit(plan["placed"], config=config)

    reclamation_record: list = []
    reclaimed_specs = reclamation.run_chain(
        plan["specs"], (), existing_specs, kit=GENERIC_SPEC_KIT, cameras=cameras,
        safe_background_groups=frozenset({group}), vegetation_thin_roles={},
        thin_accent_drop_roles=frozenset(), config=RECLAMATION_CONFIG, record=reclamation_record,
    )

    materials_used = sorted({str(spec["material"]) for spec in reclaimed_specs})
    triangles = GENERIC_SPEC_KIT.estimated_triangles(reclaimed_specs)

    return {
        "stageId": stage["id"],
        "family": family, "mood": mood,
        "triBudget": tri_budget,
        "specsBeforeReclamation": len(plan["specs"]),
        "specsAfterReclamation": len(reclaimed_specs),
        "estimatedTriangles": triangles,
        "materialsUsed": materials_used,
        "materialCount": len(materials_used),
        "withinTriBudget": triangles <= tri_budget,
        "districtPlan": {
            "blockCount": plan["blockCount"], "articulatedBlockCount": plan["articulatedBlockCount"],
            "plainBlockCount": plan["plainBlockCount"], "triUsed": plan["triUsed"],
            "candidateSitesTotal": plan["candidateSitesTotal"],
            "candidateSitesSkippedForBudget": plan["candidateSitesSkippedForBudget"],
            "occlusionExcludedRoles": plan["occlusionExcludedRoles"],
        },
        "reclamationDropped": len(plan["specs"]) - len(reclaimed_specs),
        "audits": {
            "roadOverlap": road_audit["passed"], "spawnClearance": spawn_audit["passed"],
            "gap": gap_audit["passed"], "minPlayerSpawnDistanceM": spawn_audit["minPlayerSpawnDistanceM"],
            "minBotSpawnDistanceM": spawn_audit["minBotSpawnDistanceM"],
            "alleyGapsM": gap_audit["alleyGapsM"], "streetGapsM": gap_audit["streetGapsM"],
        },
        "auditsPassed": road_audit["passed"] and spawn_audit["passed"] and gap_audit["passed"],
        "specs": reclaimed_specs,
    }


# ---------------------------------------------------------------------------
# 6. Blender-side emission (bpy required; only called from build_all_stages.py).
# ---------------------------------------------------------------------------
def emit_specs_to_mesh_builder(builder, specs: Sequence[Mapping[str, object]]) -> dict:
    """Emit an a23 spec list into build_all_stages.py's own MeshBuilder.
    districts.py's terrace-block builders only ever emit box/panel/sweep(2-pt)
    in practice (verified by reading every kit.* call site in districts.py);
    chamfer_box/cylinder are supported defensively for forward-compatibility
    but are not exercised by the current district-infill plan.
    """
    counts = {"box": 0, "chamfer_box": 0, "panel": 0, "sweep": 0, "cylinder": 0, "leaf_cluster": 0}
    for spec in specs:
        kind = spec["kind"]
        key = spec["material"]
        if kind == "box":
            builder.add_box(spec["x"], spec["y"], spec["z"], spec["w"], spec["h"], spec["d"], key)
        elif kind == "chamfer_box":
            # MeshBuilder has no baked-bevel primitive; downgrading to a
            # plain box mirrors reclamation pass 4's own chamfer_box->box
            # sub-pixel-bevel precedent rather than inventing a new device.
            builder.add_box(spec["x"], spec["y"], spec["z"], spec["w"], spec["h"], spec["d"], key)
        elif kind == "panel":
            builder.add_surface_panel(spec["corners"], spec["thickness"], key)
        elif kind == "sweep":
            points = spec["points"]
            if len(points) != 2:
                raise ValueError("emit_specs_to_mesh_builder: only 2-point sweeps are supported "
                                  "(matches every sweep districts.py's block builders emit)")
            builder.add_cylinder_between(points[0], points[1], spec["radius"], key, spec["sides"])
        elif kind == "cylinder":
            builder.add_cylinder(spec["x"], spec["y"], spec["z"], spec["radius"], spec["height"],
                                  key, spec["segments"], spec["topRadius"])
        elif kind == "leaf_cluster":
            raise ValueError("emit_specs_to_mesh_builder: leaf_cluster has no MeshBuilder "
                              "equivalent and district-infill plans never emit one")
        else:
            raise ValueError(f"emit_specs_to_mesh_builder: unsupported kind {kind!r}")
        counts[kind] += 1
    return counts
