"""A23 triangle-budget reclamation: four composable passes over a spec list.

Promoted from the private study under
``/private/tmp/hibana-blender/claude-a23-triangle-reclaim/`` (
``reclamation_filter.py`` / ``_pass2.py`` / ``_pass3.py`` / ``_pass4.py``),
which built and proved this against nakaniwa's kit only. The mechanism in
every pass below is stage-agnostic; what is stage-specific is the *policy* —
which groups are "hero" or "protected", which roles are vegetation, which
camera(s) define the safety contract — so every stage-specific fact is now a
parameter (a ``SpecKit``, a camera or camera list, and a handful of group/role
sets) instead of an ``import nakaniwa_reference_a21_r6 as R6`` at module
scope.

Why four passes, and why pass 3 is mandatory
---------------------------------------------
Passes 1 and 2 each proved their drops safe against a single evidence
camera. The round's own five-camera audit (H20) found that was not enough:
"invisible" and "occluded" are camera-relative facts, and a spec judged safe
to drop from one viewpoint can be squarely onscreen and unoccluded from
another. That is measurement defect #1 in the round log
("single-camera judgement") — the round shipped a build with a hidden
correctness debt (an open archway) for several iterations before it was
caught.

Pass 3 exists specifically to close that hole: it re-decides every
strict-invisibility/occlusion drop using a *unified test across every camera
in the safety contract*, restoring anything that fails in even one of them.
It reuses (unchanged) pass 1's mullion rule and vegetation-thin-round-1 rule,
and pass 2's vegetation-thin-round-2 rule, because those three were bisected
and independently confirmed safe across all cameras (<=0.03% pixel delta
each) — only the two single-camera rules were replaced. **A caller must
never treat pass 3 as an optional optimisation pass to skip for speed: it is
the correctness fix for passes 1/2's drop decisions, and any chain that
drops background geometry without it inherits the same single-camera bug.**

Pass 4 is a different kind of pass: instead of deleting more geometry (pass
3's own search found nothing further was safe to delete outright), it
*simplifies in place* — chamfer-bevel downgrade, sweep/cylinder segment
reduction, sub-pixel member removal — using a worst-case-across-every-camera
projection so a feature is only simplified if it is sub-pixel from every
angle it is ever seen from. Pass 4 also names measurement defect #2 in the
round log ("aggregate failure"): many individually-safe simplifications can
still fail together when they all land in the same frame at once (the round
found this at a naive 1.5 px bevel threshold; retuning to 0.6 px fixed it).
See ``simplify_specs`` below.

Camera contract
----------------
Every function that decides visibility/occlusion takes the camera(s) it
must be safe against as an explicit parameter — a single ``camera: dict`` for
passes 1/2 (matching the private study's proven single-camera scope for
those two rules) and a ``cameras: Sequence[dict]`` for pass 3/4 (the round's
five-camera safety contract, generalised here to "however many cameras the
caller's stage defines" rather than nakaniwa's five hard-coded dicts).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from tools.blender.a23.kit import (
    SpecKit,
    Spec,
    distance_to_camera,
    frame_cells,
    is_onscreen,
)

DEFAULT_RESOLUTION = (1280, 720)
DEFAULT_OCCLUDER_ELIGIBLE_KINDS = frozenset({"box", "chamfer_box", "cylinder", "panel", "sweep"})


@dataclass(frozen=True)
class ReclamationConfig:
    """Every numeric threshold the four passes use. Defaults are the values
    the A23 round measured safe for nakaniwa; override per stage once a new
    stage's own geometry density/camera framing has been measured.
    """

    resolution: tuple[int, int] = DEFAULT_RESOLUTION
    px_threshold: float = 2.0
    frame_edge_margin: float = 0.05
    camera_proximity_margin_m: float = 12.0
    occlusion_depth_margin_m: float = 1.0
    max_occluder_depth_extent_m: float = 2.5
    occluder_eligible_kinds: frozenset = field(default_factory=lambda: DEFAULT_OCCLUDER_ELIGIBLE_KINDS)
    grid: tuple[int, int] = (160, 90)
    vegetation_round2_keep_modulus: int = 2
    bevel_px_threshold: float = 0.6
    diameter_px_threshold: float = 3.0
    subpixel_width_px_threshold: float = 1.5
    sweep_min_sides: int = 4
    cylinder_min_segments: int = 6


def _aspect(resolution: Sequence[float]) -> float:
    return float(resolution[0]) / float(resolution[1])


def _drop_entry(kit: SpecKit, spec: Spec, rule: str, evidence: Optional[dict] = None) -> dict:
    return {
        "role": spec["role"], "group": spec["group"], "material": spec["material"],
        "kind": spec["kind"], "tri": kit.estimated_triangles([spec]),
        "rule": rule, "evidence": evidence or {},
    }


# ---------------------------------------------------------------------------
# Pass 1: mullion drop + vegetation thin (round 1) + single-camera strict
# invisibility. Kept standalone for composability and for stages that want a
# cheap first cut; SUPERSEDED for the strict-invisibility rule by pass 3 (see
# module docstring) — do not use this pass alone as a final safety gate.
# ---------------------------------------------------------------------------
def _is_strictly_invisible(
    kit: SpecKit, spec: Spec, camera: Mapping[str, object], *, config: ReclamationConfig,
) -> tuple[bool, dict]:
    frame = kit.project_spec_frame(spec, camera, _aspect(config.resolution))
    if frame is None:
        return True, {"behindOrOffscreen": True, "reason": "behind-camera"}
    x0, y0, x1, y1 = frame["bounds"]
    margin = config.frame_edge_margin
    comfortably_offscreen = (
        x1 <= -margin or x0 >= 1.0 + margin or y1 <= -margin or y0 >= 1.0 + margin
    )
    if comfortably_offscreen:
        return True, {
            "behindOrOffscreen": True, "bounds": frame["bounds"],
            "reason": "offscreen-beyond-edge-margin",
        }
    if not is_onscreen(frame):
        return False, {
            "behindOrOffscreen": True, "bounds": frame["bounds"],
            "reason": "within-edge-margin-kept",
        }
    res_w, res_h = config.resolution
    px_w = max(0.0, x1 - x0) * res_w
    px_h = max(0.0, y1 - y0) * res_h
    invisible = max(px_w, px_h) < config.px_threshold
    return invisible, {
        "behindOrOffscreen": False, "pxW": round(px_w, 3), "pxH": round(px_h, 3),
        "nearDepthM": round(float(frame["nearDepthM"]), 2),
    }


def pass1_strict_invisible_filter(
    specs: Sequence[Spec],
    *,
    kit: SpecKit,
    camera: Mapping[str, object],
    safe_background_groups: frozenset,
    vegetation_thin_roles: Mapping[str, int],
    thin_accent_drop_roles: frozenset,
    hero_groups: frozenset = frozenset(),
    protected_groups: frozenset = frozenset(),
    config: ReclamationConfig = ReclamationConfig(),
    record: Optional[list] = None,
) -> list[dict]:
    """Drop specs from ``safe_background_groups`` only, via three rules:
    vegetation-thin (index-parity), mullion/thin-accent (unconditional), and
    strict single-camera invisibility. Everything in ``hero_groups`` /
    ``protected_groups`` (or outside ``safe_background_groups`` entirely) is
    always kept. Pure filter: every returned spec is the same object (by
    identity) as one already in ``specs``.
    """
    role_position: dict[str, int] = defaultdict(int)
    kept: list[dict] = []
    for spec in specs:
        group = spec["group"]
        role = spec["role"]
        drop = False
        reason = None
        evidence: dict = {}

        if group in hero_groups or group in protected_groups:
            drop = False
        elif group in safe_background_groups:
            if role in vegetation_thin_roles:
                index = role_position[role]
                role_position[role] = index + 1
                keep_modulus = vegetation_thin_roles[role]
                if index % keep_modulus != 0:
                    drop = True
                    reason = "vegetation-thin-positional"
                    evidence = {"roleOccurrenceIndex": index, "keepModulus": keep_modulus}
            elif role in thin_accent_drop_roles:
                drop = True
                reason = "sub-pixel-width-mullion-accent"
            else:
                invisible, ev = _is_strictly_invisible(kit, spec, camera, config=config)
                evidence = ev
                if invisible:
                    drop = True
                    reason = "strict-invisible-evidence-camera"

        if drop:
            if record is not None:
                record.append(_drop_entry(kit, spec, reason, evidence))
        else:
            kept.append(spec)
    return kept


# ---------------------------------------------------------------------------
# Pass 2: occlusion-by-new-foreground + vegetation thin (round 2), scoped to
# whatever pass 1 already kept. SUPERSEDED for the occlusion rule by pass 3.
# ---------------------------------------------------------------------------
def build_occlusion_grid(
    kit: SpecKit,
    camera: Mapping[str, object],
    occluder_specs: Sequence[Spec],
    *,
    config: ReclamationConfig = ReclamationConfig(),
) -> dict[tuple[int, int], float]:
    """Screen grid cell -> nearest *trusted* occluder depth (metres), for one
    camera. Only compact occluders (small camera-depth extent, never a
    ``leaf_cluster``) are trusted — an elongated or gappy object's screen
    AABB is a safe *superset* for proving something invisible (pass 1) but
    an unsafe superset for proving something else is covered (this
    function); see ``ReclamationConfig.max_occluder_depth_extent_m`` and
    ``occluder_eligible_kinds``. Reused unchanged by pass 3 and by
    districts.py's occlusion-aware articulation priority.
    """
    grid: dict[tuple[int, int], float] = {}
    aspect = _aspect(config.resolution)
    for spec in occluder_specs:
        if spec["kind"] not in config.occluder_eligible_kinds:
            continue
        frame = kit.project_spec_frame(spec, camera, aspect)
        if frame is None:
            continue
        depth = float(frame["nearDepthM"])
        extent = float(frame["farDepthM"]) - depth
        if extent > config.max_occluder_depth_extent_m:
            continue
        for cell in frame_cells(frame["bounds"], *config.grid):
            prev = grid.get(cell)
            if prev is None or depth < prev:
                grid[cell] = depth
    return grid


def _is_occluded(
    kit: SpecKit, spec: Spec, camera: Mapping[str, object],
    grid: Mapping[tuple[int, int], float], *, config: ReclamationConfig,
) -> tuple[bool, dict]:
    frame = kit.project_spec_frame(spec, camera, _aspect(config.resolution))
    if frame is None:
        return False, {"reason": "behind-camera-not-applicable"}
    if not is_onscreen(frame):
        return False, {"reason": "already-offscreen-not-this-rule"}
    near_depth = float(frame["nearDepthM"])
    cells = list(frame_cells(frame["bounds"], *config.grid))
    if not cells:
        return False, {"reason": "no-cells"}
    covered = sum(
        1 for cell in cells
        if (occ := grid.get(cell)) is not None
        and occ + config.occlusion_depth_margin_m < near_depth
    )
    fully_covered = covered == len(cells)
    return fully_covered, {
        "cellCount": len(cells), "coveredCount": covered, "nearDepthM": round(near_depth, 2),
    }


def pass2_occlusion_filter(
    pass1_kept_specs: Sequence[Spec],
    *,
    kit: SpecKit,
    camera: Mapping[str, object],
    occluder_specs: Sequence[Spec],
    safe_background_groups: frozenset,
    vegetation_thin_roles: Mapping[str, int],
    config: ReclamationConfig = ReclamationConfig(),
    record: Optional[list] = None,
) -> list[dict]:
    """Take pass 1's output and drop more: specs in ``safe_background_groups``
    whose full conservative screen AABB is covered by ``occluder_specs``
    (new near-field mass), plus a second, coarser vegetation thin over
    pass 1's survivors. Never touches anything within
    ``config.camera_proximity_margin_m`` of ``camera``.
    """
    grid = build_occlusion_grid(kit, camera, occluder_specs, config=config)
    role_position: dict[str, int] = defaultdict(int)
    kept: list[dict] = []
    for spec in pass1_kept_specs:
        group = spec["group"]
        role = spec["role"]
        drop = False
        reason = None
        evidence: dict = {}

        if group in safe_background_groups:
            if distance_to_camera(kit, spec, camera) < config.camera_proximity_margin_m:
                drop = False
            else:
                occluded, ev = _is_occluded(kit, spec, camera, grid, config=config)
                if occluded:
                    drop = True
                    reason = "occluded-by-new-near-field-foreground"
                    evidence = ev
                elif role in vegetation_thin_roles:
                    index = role_position[role]
                    role_position[role] = index + 1
                    modulus = config.vegetation_round2_keep_modulus
                    if index % modulus == (modulus - 1):
                        drop = True
                        reason = "vegetation-thin-round2"
                        evidence = {"roleOccurrenceIndex": index}

        if drop:
            if record is not None:
                record.append(_drop_entry(kit, spec, reason, evidence))
        else:
            kept.append(spec)
    return kept


# ---------------------------------------------------------------------------
# Pass 3: the correctness fix. Unified five(-or-however-many)-camera test
# replaces pass 1's strict-invisibility and pass 2's occlusion rule; mullion
# and both vegetation-thin rounds are carried over unchanged (independently
# re-verified safe per camera in the round that produced this).
# ---------------------------------------------------------------------------
def _is_strictly_invisible_for_camera(kit, spec, camera, *, config):
    frame = kit.project_spec_frame(spec, camera, _aspect(config.resolution))
    if frame is None:
        return True, {"reason": "behind-camera"}
    x0, y0, x1, y1 = frame["bounds"]
    margin = config.frame_edge_margin
    if x1 <= -margin or x0 >= 1.0 + margin or y1 <= -margin or y0 >= 1.0 + margin:
        return True, {"reason": "offscreen-beyond-edge-margin"}
    if not is_onscreen(frame):
        return False, {"reason": "within-edge-margin-kept"}
    res_w, res_h = config.resolution
    px_w = max(0.0, x1 - x0) * res_w
    px_h = max(0.0, y1 - y0) * res_h
    return max(px_w, px_h) < config.px_threshold, {"pxW": round(px_w, 3), "pxH": round(px_h, 3)}


def _is_occluded_for_camera(kit, spec, camera, grid, *, config):
    frame = kit.project_spec_frame(spec, camera, _aspect(config.resolution))
    if frame is None or not is_onscreen(frame):
        return False, {}
    near_depth = float(frame["nearDepthM"])
    cells = list(frame_cells(frame["bounds"], *config.grid))
    if not cells:
        return False, {}
    covered = sum(
        1 for cell in cells
        if (occ := grid.get(cell)) is not None
        and occ + config.occlusion_depth_margin_m < near_depth
    )
    return covered == len(cells), {"cellCount": len(cells), "coveredCount": covered}


def is_hidden_in_every_camera(
    kit: SpecKit, spec: Spec, cameras: Sequence[Mapping[str, object]],
    grids: Mapping[str, Mapping[tuple[int, int], float]], *, config: ReclamationConfig,
) -> tuple[bool, dict]:
    """The pass-3 unified test: hidden (invisible-or-occluded) in *every*
    camera in the safety contract, and never within
    ``config.camera_proximity_margin_m`` of any of them. This is what fixes
    measurement defect #1 (single-camera judgement) — pass 1/2 each asked
    this question of one camera; this asks it of all of them.
    """
    if any(
        distance_to_camera(kit, spec, cam) < config.camera_proximity_margin_m
        for cam in cameras
    ):
        return False, {"reason": "within-camera-proximity-margin"}
    evidence: dict = {}
    for cam in cameras:
        name = str(cam["name"])
        invisible, inv_ev = _is_strictly_invisible_for_camera(kit, spec, cam, config=config)
        if invisible:
            evidence[name] = {"how": "invisible", **inv_ev}
            continue
        occluded, occ_ev = _is_occluded_for_camera(kit, spec, cam, grids[name], config=config)
        if occluded:
            evidence[name] = {"how": "occluded", **occ_ev}
            continue
        return False, {"failedCamera": name, "why": "visible-and-unoccluded"}
    return True, evidence


def pass3_five_camera_correctness_filter(
    base_specs: Sequence[Spec],
    near_field_specs: Sequence[Spec],
    district_specs: Sequence[Spec],
    *,
    kit: SpecKit,
    cameras: Sequence[Mapping[str, object]],
    safe_background_groups: frozenset,
    vegetation_thin_roles: Mapping[str, int],
    thin_accent_drop_roles: frozenset,
    config: ReclamationConfig = ReclamationConfig(),
    record: Optional[list] = None,
) -> list[dict]:
    """Re-decide KEEP/DROP for every ``safe_background_groups`` spec in the
    raw kit build, using: pass 1's mullion + vegetation-thin-round-1 rules
    unchanged; ``is_hidden_in_every_camera`` in place of pass 1's
    strict-invisible rule and pass 2's occlusion rule; then pass 2's
    vegetation-thin-round-2 unchanged, applied to whatever the unified test
    still keeps. Everything outside ``safe_background_groups`` passes
    through untouched. ``near_field_specs`` + ``district_specs`` are the
    occluder population (near-field props and any placed district massing);
    both are safety-relevant mass that a spec can legitimately hide behind.
    """
    occluders = list(near_field_specs) + list(district_specs)
    grids = {
        str(cam["name"]): build_occlusion_grid(kit, cam, occluders, config=config)
        for cam in cameras
    }

    role_position_v1: dict[str, int] = {}
    role_position_v2: dict[str, int] = {}
    kept: list[dict] = []
    stage_a_survivors: list[dict] = []

    for spec in base_specs:
        group = spec["group"]
        role = spec["role"]
        if group not in safe_background_groups:
            kept.append(spec)
            continue

        if role in thin_accent_drop_roles:
            if record is not None:
                record.append(_drop_entry(kit, spec, "mullion-unconditional-unchanged"))
            continue

        if role in vegetation_thin_roles:
            index = role_position_v1.get(role, 0)
            role_position_v1[role] = index + 1
            keep_modulus = vegetation_thin_roles[role]
            if index % keep_modulus != 0:
                if record is not None:
                    record.append(_drop_entry(kit, spec, "vegetation-thin-round1-unchanged"))
                continue
            stage_a_survivors.append(spec)
            continue

        hidden, evidence = is_hidden_in_every_camera(kit, spec, cameras, grids, config=config)
        if hidden:
            if record is not None:
                record.append(_drop_entry(kit, spec, "five-camera-safe", evidence))
            continue
        stage_a_survivors.append(spec)

    round2_modulus = config.vegetation_round2_keep_modulus
    for spec in stage_a_survivors:
        role = spec["role"]
        if role in vegetation_thin_roles:
            index = role_position_v2.get(role, 0)
            role_position_v2[role] = index + 1
            if index % round2_modulus != (round2_modulus - 1):
                kept.append(spec)
            elif record is not None:
                record.append(_drop_entry(kit, spec, "vegetation-thin-round2-unchanged"))
        else:
            kept.append(spec)

    return kept


# ---------------------------------------------------------------------------
# Pass 4: in-place simplification. Never deletes a spec from the safe
# background groups outright (technique 3 aside — see docstring); replaces
# it with a cheaper primitive that renders the same silhouette, only where a
# per-camera worst-case projection proves the difference is sub-pixel in
# EVERY camera the spec is ever onscreen in.
# ---------------------------------------------------------------------------
def _cam_tan_half_x(camera: Mapping[str, object]) -> float:
    return float(camera["sensorWidthMm"]) / (2.0 * float(camera["lensMm"]))


def _onscreen_near_depths(kit, spec, cameras, *, config) -> dict[str, float]:
    out = {}
    aspect = _aspect(config.resolution)
    for cam in cameras:
        frame = kit.project_spec_frame(spec, cam, aspect)
        if frame is not None and is_onscreen(frame):
            out[str(cam["name"])] = float(frame["nearDepthM"])
    return out


def _worst_case_true_width_px(kit, width_m, spec, cameras, *, config) -> float:
    """Project a physical width (independent of the spec's own AABB — a
    bevel or a tube diameter) at each camera the spec is actually onscreen
    in, using that camera's real near depth; return the worst (largest,
    most-magnifying) case. A camera the spec is invisible in cannot make the
    feature look bigger than it is in a camera where it actually appears.
    """
    worst = 0.0
    by_name = {str(c["name"]): c for c in cameras}
    for cam_name, depth in _onscreen_near_depths(kit, spec, cameras, config=config).items():
        if depth <= 0:
            continue
        cam = by_name[cam_name]
        tan_half_x = _cam_tan_half_x(cam)
        px = (width_m / depth) / (2.0 * tan_half_x) * config.resolution[0]
        worst = max(worst, px)
    return worst


def _dist_to_any_camera_under(kit, spec, cameras, margin) -> bool:
    return any(distance_to_camera(kit, spec, cam) < margin for cam in cameras)


def _min_dimension_px_worst(kit, spec, cameras, *, config) -> Optional[float]:
    worst = None
    aspect = _aspect(config.resolution)
    res_w, res_h = config.resolution
    for cam in cameras:
        frame = kit.project_spec_frame(spec, cam, aspect)
        if frame is None or not is_onscreen(frame):
            continue
        x0, y0, x1, y1 = frame["bounds"]
        small_dim = min(max(0.0, x1 - x0) * res_w, max(0.0, y1 - y0) * res_h)
        worst = small_dim if worst is None else max(worst, small_dim)
    return worst


def simplify_specs(
    specs: Sequence[Spec],
    *,
    kit: SpecKit,
    cameras: Sequence[Mapping[str, object]],
    safe_background_groups: frozenset,
    config: ReclamationConfig = ReclamationConfig(),
    record: Optional[list] = None,
) -> list[dict]:
    """Return a new list: specs outside ``safe_background_groups``, or within
    ``config.camera_proximity_margin_m`` of any camera, pass through
    unchanged. Everything else may be replaced by an original-object-free
    dict with the identical role/group/material/position/size and a cheaper
    ``kind``/segment-count, or dropped outright (technique 3 only), wherever
    the worst-case-across-every-camera projection proves it safe. See the
    module docstring for measurement defect #2 (aggregate failure) — this is
    why every threshold here is tuned conservatively per-camera rather than
    per-instance.
    """
    out: list[dict] = []
    for spec in specs:
        group = spec["group"]
        if group not in safe_background_groups:
            out.append(spec)
            continue
        if _dist_to_any_camera_under(kit, spec, cameras, config.camera_proximity_margin_m):
            out.append(spec)
            continue

        kind = spec["kind"]

        if kind == "chamfer_box":
            bevel_px = _worst_case_true_width_px(kit, float(spec["bevel"]), spec, cameras, config=config)
            if bevel_px < config.bevel_px_threshold:
                new_spec = {
                    "kind": "box", "role": spec["role"], "material": spec["material"],
                    "group": spec["group"], "blocksGameplay": spec["blocksGameplay"],
                    "x": spec["x"], "y": spec["y"], "z": spec["z"],
                    "w": spec["w"], "h": spec["h"], "d": spec["d"],
                }
                if record is not None:
                    record.append({
                        "role": spec["role"], "group": group, "material": spec["material"],
                        "kind": "chamfer_box->box", "triBefore": kit.estimated_triangles([spec]),
                        "triAfter": kit.estimated_triangles([new_spec]),
                        "rule": "chamfer-bevel-downgrade",
                        "evidence": {"bevelWorstCasePx": round(bevel_px, 4)},
                    })
                out.append(new_spec)
                continue
            out.append(spec)
            continue

        if kind == "box":
            small_dim = _min_dimension_px_worst(kit, spec, cameras, config=config)
            if small_dim is not None and small_dim < config.subpixel_width_px_threshold:
                if record is not None:
                    record.append({
                        "role": spec["role"], "group": group, "material": spec["material"],
                        "kind": "box-dropped", "triBefore": kit.estimated_triangles([spec]),
                        "triAfter": 0, "rule": "subpixel-width-member",
                        "evidence": {"minDimWorstCasePx": round(small_dim, 4)},
                    })
                continue
            out.append(spec)
            continue

        if kind == "sweep":
            diameter_px = _worst_case_true_width_px(kit, 2.0 * float(spec["radius"]), spec, cameras, config=config)
            if diameter_px < config.diameter_px_threshold and spec["sides"] > config.sweep_min_sides:
                new_spec = dict(spec)
                new_spec["sides"] = config.sweep_min_sides
                if record is not None:
                    record.append({
                        "role": spec["role"], "group": group, "material": spec["material"],
                        "kind": "sweep-sides-reduced",
                        "triBefore": kit.estimated_triangles([spec]),
                        "triAfter": kit.estimated_triangles([new_spec]),
                        "rule": "sweep-diameter-subpixel",
                        "evidence": {
                            "diameterWorstCasePx": round(diameter_px, 4),
                            "sidesBefore": spec["sides"], "sidesAfter": config.sweep_min_sides,
                        },
                    })
                out.append(new_spec)
                continue
            out.append(spec)
            continue

        if kind == "cylinder":
            diameter_m = 2.0 * max(float(spec["radius"]), float(spec["topRadius"]))
            diameter_px = _worst_case_true_width_px(kit, diameter_m, spec, cameras, config=config)
            if diameter_px < config.diameter_px_threshold and spec["segments"] > config.cylinder_min_segments:
                new_spec = dict(spec)
                new_spec["segments"] = config.cylinder_min_segments
                if record is not None:
                    record.append({
                        "role": spec["role"], "group": group, "material": spec["material"],
                        "kind": "cylinder-segments-reduced",
                        "triBefore": kit.estimated_triangles([spec]),
                        "triAfter": kit.estimated_triangles([new_spec]),
                        "rule": "cylinder-diameter-subpixel",
                        "evidence": {
                            "diameterWorstCasePx": round(diameter_px, 4),
                            "segmentsBefore": spec["segments"], "segmentsAfter": config.cylinder_min_segments,
                        },
                    })
                out.append(new_spec)
                continue
            out.append(spec)
            continue

        out.append(spec)

    return out


def run_chain(
    base_specs: Sequence[Spec],
    near_field_specs: Sequence[Spec],
    district_specs: Sequence[Spec],
    *,
    kit: SpecKit,
    cameras: Sequence[Mapping[str, object]],
    safe_background_groups: frozenset,
    vegetation_thin_roles: Mapping[str, int],
    thin_accent_drop_roles: frozenset,
    config: ReclamationConfig = ReclamationConfig(),
    record: Optional[list] = None,
) -> list[dict]:
    """The validated production chain: pass 3 (correctness) then pass 4
    (simplify). This is what the round actually shipped — pass 1/2's own
    top-level composers are not part of it (superseded, see module
    docstring) but remain exported above for standalone/historical use.
    """
    reclaimed = pass3_five_camera_correctness_filter(
        base_specs, near_field_specs, district_specs,
        kit=kit, cameras=cameras, safe_background_groups=safe_background_groups,
        vegetation_thin_roles=vegetation_thin_roles,
        thin_accent_drop_roles=thin_accent_drop_roles, config=config, record=record,
    )
    return simplify_specs(
        reclaimed, kit=kit, cameras=cameras,
        safe_background_groups=safe_background_groups, config=config, record=record,
    )
