"""Nakaniwa A23 reconciliation: the stage-specific composition chain that
makes ``build_all_stages.py``'s production path reproduce the A23 round's
proven best Nakaniwa build (``/private/tmp/hibana-blender/claude-a23-tier1``)
without depending on anything under ``/private/tmp``.

Why this module exists
-----------------------
The A23 round (26 iterations, see the round-state log carried in project
memory) discovered and proved, against
``tools/blender/stage_kits/nakaniwa_reference_a21_r6.py`` ("R6"):

  - a vertical near-field garden (pergolas, promenade trees, tall lanterns,
    planting beds, a paving inlay) -- originally "H3"
  - a true 0-7 m near-field frame (foreground urns, near balustrades, corner
    canopy trees) built on top of H3's helpers -- originally "H4"
  - four defect fixes in the R6 kit itself plus H4's own composition
    (crown-tower window reposition, unsupported wing-window removal, an
    oversized arcade-glazing rebuild, and an initial dual-hero composition
    recovery: urn shrink + one pergola run moved off-axis) -- originally the
    "H26 hero_defect_fixes" pass
  - the Tier 1 palace-occlusion fix: four additional, independently verified
    ``_RIGHT``-axis translations that clear the Crowned Water Palace's
    screen column (91.17% occluded -> 8.46%) -- originally "pergola_fix"

``tools/blender/a23/{reclamation,districts,materials,measure,evidence}.py``
already promoted the stage-agnostic *mechanism* half of this round (the four
reclamation passes, the district placement planner, the material-family/
ground-remap/glazing/foliage transforms, and the five-camera render
harness) -- see each module's own docstring for its private-study
provenance and fidelity proof. What was still missing, and is what this
module ports, is the nakaniwa-*specific* geometry and policy those
mechanisms were proven against: the H3/H4 near-field generators, the H26/
Tier-1 fix chain, and the exact group/role policy sets and five-camera
safety contract nakaniwa's own reclamation passes use.

Every function below is a line-for-line port of its private-study source
(geometry, magnitudes and role/group names are unchanged); only the loading
mechanics changed (no more ``/private/tmp`` file-path imports, no more a
``bpy`` stub package, no more per-round ``sys.path`` mutation). See
``build_nakaniwa_a23_specs`` for the composer that reproduces
``claude-a23-promotion/verify_specs.py``'s ``promoted_after_specs()`` exactly.

One deliberate simplification: ``district_seed``
---------------------------------------------------
The private chain's reclamation pass 3 took a third occluder population
(``district_seed``) alongside the near-field props: a *rough, cheap,
best-effort* pre-estimate of where district infill blocks would eventually
land, read from an early (H19-era) district-infill iteration, used only to
let pass 3 additionally reclaim background geometry that the *real*,
final district plan (computed afterwards) would also hide. That reader
returned 80 real specs when tested against today's private tree, but
substituting an empty list in its place and re-running the full composition
produced a **byte-for-byte identical** 5,373-spec result (verified directly,
2026-07-27: both spec lists compare equal element-for-element). Since the
final district plan is computed later in this same chain from the
*reconciled* base with real occlusion-aware priority (not from this rough
seed), an empty seed can only ever make pass 3 *keep* something it might
otherwise have dropped -- never drop something wrongly -- so this is safe
by construction, not merely safe by this one measurement. This module
therefore passes an empty list rather than porting the ~1,000-line early
iteration whose only remaining job was to feed that seed.
"""
from __future__ import annotations

import math
import sys
from typing import Sequence

from tools.blender.a23 import districts, materials, reclamation
from tools.blender.a23.kit import SpecKit
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6

# H3/H4's original sources `import bpy` unconditionally (their own studies
# render through Blender); this module is pure Python (like every other a23
# module) and must import cleanly under plain python3 too. Match the
# guarded-stub convention every other ported private module already uses.
if "bpy" not in sys.modules:
    try:
        import bpy  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        import types

        sys.modules["bpy"] = types.ModuleType("bpy")

KIT = SpecKit.from_module(R6)

# ---------------------------------------------------------------------------
# H3: vertical near-field garden (pergolas, promenade trees, tall lanterns,
# edge runs, planting beds, paving inlay). Ported verbatim from
# ``/private/tmp/hibana-blender/claude-a23-nakaniwa-h3/run_a23_h3_vertical_garden.py``.
# ---------------------------------------------------------------------------
H3_GROUP = "a23-h3-vertical-near-field-garden"

INNER_SIDE = 9.2
OUTER_SIDE = 12.6
EDGE_START_T = -0.47
EDGE_END_T = 0.02
SEGMENT_T = 0.035
CORRIDOR_LENGTH_M = 97.6
POST_HEIGHT = 3.62
BEAM_Y = 3.58


def _vertical_quad(t0, t1, side, y0, y1):
    x0, z0 = R6._corridor_point(t0, side)
    x1, z1 = R6._corridor_point(t1, side)
    return ((x0, y0, z0), (x1, y0, z1), (x1, y1, z1), (x0, y1, z0))


def _cross_quad(t, side_a, side_b, y, half_forward):
    """A quad spanning laterally between two side offsets at one station."""
    ax, az = R6._corridor_point(t, side_a)
    bx, bz = R6._corridor_point(t, side_b)
    fx, fz, _rx, _rz = R6._r5_corridor_basis(t)
    return (
        (ax - fx * half_forward, y, az - fz * half_forward),
        (bx - fx * half_forward, y, bz - fz * half_forward),
        (bx + fx * half_forward, y, bz + fz * half_forward),
        (ax + fx * half_forward, y, az + fz * half_forward),
    )


def _close_range_tree(specs, *, x, z, height, crown, seed, flowering, role):
    trunk_h = height * 0.52
    R6._cylinder(
        specs, f"{role}-trunk", "dark_wood", H3_GROUP,
        x, trunk_h / 2.0, z, 0.30 + crown * 0.045, trunk_h, 12,
        top_radius=0.19 + crown * 0.024,
    )
    tips = []
    for index in range(6):
        angle = (index * 2.399963 + seed * 0.37) % math.tau
        radial = crown * (0.30 + 0.07 * (index % 3))
        tip = (
            x + math.cos(angle) * radial,
            trunk_h + 0.55 + 0.30 * (index % 2),
            z + math.sin(angle) * radial,
        )
        R6._sweep(
            specs, f"{role}-branch", "dark_wood", H3_GROUP,
            ((x, trunk_h * 0.80, z), tip), 0.13, 7,
        )
        tips.append(tip)
    R6._leaf_cluster(
        specs, f"{role}-canopy-core", "foliage_dark", H3_GROUP,
        x, trunk_h + 0.95, z, crown * 0.78, crown * 0.52, 34, seed,
    )
    for index, tip in enumerate(tips):
        material = "flower" if flowering and index % 3 == 0 else (
            "foliage_light" if index % 2 else "foliage_dark"
        )
        R6._leaf_cluster(
            specs, f"{role}-canopy-lobe", material, H3_GROUP,
            tip[0], tip[1] + 0.34, tip[2],
            crown * 0.60, crown * 0.44, 30, seed * 31 + index,
        )
    R6._panel(
        specs, f"{role}-soil", "wet_stone", H3_GROUP,
        ((x - 1.25, 0.16, z - 1.25), (x + 1.25, 0.16, z - 1.25),
         (x + 1.25, 0.16, z + 1.25), (x - 1.25, 0.16, z + 1.25)), 0.14,
    )
    R6._panel(
        specs, f"{role}-retaining-edge", "carved_stone", H3_GROUP,
        ((x - 1.55, 0.32, z - 1.55), (x + 1.55, 0.32, z - 1.55),
         (x + 1.55, 0.32, z + 1.55), (x - 1.55, 0.32, z + 1.55)), 0.34,
    )


def _edge_run(specs, side, seed_base, *, coping, baluster_step):
    t = EDGE_START_T
    while t < EDGE_END_T:
        t_next = min(t + SEGMENT_T, EDGE_END_T)
        mid = (t + t_next) / 2.0
        half_forward = (t_next - t) * CORRIDOR_LENGTH_M / 2.0
        R6._panel(
            specs, "a23-h3-edge-plinth", "carved_stone", H3_GROUP,
            R6._r5_corridor_quad(mid, side, 0.36, half_forward, 0.66), 0.72,
        )
        R6._panel(
            specs, "a23-h3-edge-coping", coping, H3_GROUP,
            R6._r5_corridor_quad(mid, side, 1.10, half_forward, 0.76), 0.18,
        )
        R6._panel(
            specs, "a23-h3-edge-rail-face", coping, H3_GROUP,
            _vertical_quad(t, t_next, side, 0.72, 1.02), 0.12,
        )
        t = t_next
    step_t = baluster_step / CORRIDOR_LENGTH_M
    t = EDGE_START_T + step_t * 0.5
    while t < EDGE_END_T:
        px, pz = R6._corridor_point(t, side)
        R6._cylinder(
            specs, "a23-h3-edge-baluster", "ivory_stone", H3_GROUP,
            px, 0.87, pz, 0.125, 0.66, 10, top_radius=0.092,
        )
        t += step_t


def _pergola(specs, sign, seed_base, *, bay_t, start_t, end_t, vine_every):
    """Open timber pergola over the garden strip outside the promenade edge."""
    inner = INNER_SIDE * sign
    outer = OUTER_SIDE * sign
    bay_index = 0
    t = start_t
    while t <= end_t + 1e-6:
        for side in (inner, outer):
            px, pz = R6._corridor_point(t, side)
            R6._cylinder(
                specs, "a23-h3-pergola-post", "dark_wood", H3_GROUP,
                px, POST_HEIGHT / 2.0, pz, 0.17, POST_HEIGHT, 8,
                top_radius=0.145,
            )
            R6._cylinder(
                specs, "a23-h3-pergola-post-base", "carved_stone", H3_GROUP,
                px, 0.22, pz, 0.30, 0.44, 8, top_radius=0.24,
            )
        # Cross beam ties the two post rows together at every bay.
        R6._panel(
            specs, "a23-h3-pergola-cross-beam", "dark_wood", H3_GROUP,
            _cross_quad(t, inner, outer, BEAM_Y, 0.20), 0.30,
        )
        if bay_index % vine_every == 0:
            vx, vz = R6._corridor_point(t, (inner + outer) / 2.0)
            R6._leaf_cluster(
                specs, "a23-h3-pergola-climbing-vine",
                "foliage_light" if bay_index % 2 else "foliage_dark", H3_GROUP,
                vx, BEAM_Y + 0.34, vz, 1.55, 0.78, 28, seed_base + bay_index,
            )
            R6._leaf_cluster(
                specs, "a23-h3-pergola-hanging-flower", "flower", H3_GROUP,
                vx, BEAM_Y - 0.42, vz, 0.72, 0.62, 18, seed_base + 40 + bay_index,
            )
        bay_index += 1
        t += bay_t
    # Two longitudinal rafters running the whole length, one per post row.
    for side in (inner, outer):
        t0, t1 = start_t, end_t
        R6._panel(
            specs, "a23-h3-pergola-rafter", "dark_wood", H3_GROUP,
            _vertical_quad(t0, t1, side, BEAM_Y - 0.26, BEAM_Y - 0.02), 0.16,
        )


def _tall_lantern(specs, t, side, seed):
    px, pz = R6._corridor_point(t, side)
    R6._cylinder(
        specs, "a23-h3-lantern-plinth", "carved_stone", H3_GROUP,
        px, 0.30, pz, 0.30, 0.60, 10,
    )
    R6._cylinder(
        specs, "a23-h3-lantern-post", "verdigris_bronze", H3_GROUP,
        px, 2.00, pz, 0.09, 2.80, 8,
    )
    R6._cylinder(
        specs, "a23-h3-lantern-head", "warm_glow", H3_GROUP,
        px, 3.62, pz, 0.26, 0.44, 8, top_radius=0.12,
    )
    R6._cylinder(
        specs, "a23-h3-lantern-cap", "verdigris_bronze", H3_GROUP,
        px, 3.92, pz, 0.30, 0.16, 8, top_radius=0.05,
    )


def _planting_bed(specs, t, side, seed, *, length_t, clusters):
    half_forward = length_t * CORRIDOR_LENGTH_M / 2.0
    outer = side + (1.9 if side > 0 else -1.9)
    R6._panel(
        specs, "a23-h3-bed-kerb", "carved_stone", H3_GROUP,
        R6._r5_corridor_quad(t, outer, 0.44, half_forward, 1.45), 0.88,
    )
    R6._panel(
        specs, "a23-h3-bed-soil", "wet_stone", H3_GROUP,
        R6._r5_corridor_quad(t, outer, 0.94, half_forward - 0.30, 1.15), 0.10,
    )
    for index in range(clusters):
        offset = (index / max(1, clusters - 1) - 0.5) * length_t * 0.9
        lateral = outer + ((index % 3) - 1) * 0.62
        px, pz = R6._corridor_point(t + offset, lateral)
        material = "flower" if index % 3 == 0 else (
            "foliage_light" if index % 2 else "foliage_dark"
        )
        R6._leaf_cluster(
            specs, "a23-h3-bed-planting", material, H3_GROUP,
            px, 1.44, pz, 1.15, 0.86, 26, seed + index,
        )


def _paving_inlay(specs):
    """Flush paving pattern in the dead near route; zero gameplay effect."""
    axis_side = 5.3  # measured centre of the existing bridge-axis paving
    t = -0.56
    index = 0
    while t < -0.06:
        t_next = t + 0.026
        mid = (t + t_next) / 2.0
        half_forward = (t_next - t) * CORRIDOR_LENGTH_M / 2.0
        R6._panel(
            specs, "a23-h3-route-inlay-band",
            "ivory_stone" if index % 2 else "wet_stone", H3_GROUP,
            R6._r5_corridor_quad(mid, axis_side, 0.021, half_forward, 3.10), 0.02,
        )
        R6._panel(
            specs, "a23-h3-route-inlay-fillet", "carved_stone", H3_GROUP,
            R6._r5_corridor_quad(mid, axis_side, 0.024, half_forward * 0.22, 3.35),
            0.02,
        )
        index += 1
        t = t_next


def a23_h3_specs(lod: int) -> list:
    """The standalone H3 study composition (edge runs, symmetric pergolas,
    six promenade trees, four lanterns, three planting beds, paving inlay,
    one maintenance bench/water point). Superseded by H4's asymmetric
    near-field frame for the production chain (see ``a23_h4_specs``) --
    kept here only for fidelity with the private study and for tests.
    """
    specs: list = []
    _edge_run(specs, -INNER_SIDE, 53010, coping="ivory_stone", baluster_step=2.2)
    _edge_run(specs, INNER_SIDE, 53110, coping="carved_stone", baluster_step=2.8)

    _pergola(specs, -1.0, 53210, bay_t=0.042, start_t=-0.44, end_t=-0.06, vine_every=2)
    _pergola(specs, 1.0, 53310, bay_t=0.055, start_t=-0.36, end_t=-0.08, vine_every=3)

    for t, side, height, crown, seed, flowering in (
        (-0.41, -13.6, 8.6, 3.4, 53410, True),
        (-0.19, -14.2, 7.2, 2.9, 53420, False),
        (-0.34, 13.9, 7.8, 3.0, 53510, False),
        (-0.09, 14.6, 6.6, 2.6, 53520, True),
        (-0.50, -14.8, 9.1, 3.6, 53430, False),
        (-0.26, 15.2, 7.0, 2.8, 53530, True),
    ):
        x, z = R6._corridor_point(t, side)
        _close_range_tree(
            specs, x=x, z=z, height=height, crown=crown, seed=seed,
            flowering=flowering, role="a23-h3-promenade-tree",
        )

    for t, side, seed in (
        (-0.40, -INNER_SIDE, 53610), (-0.22, -INNER_SIDE, 53620),
        (-0.31, INNER_SIDE, 53710), (-0.11, INNER_SIDE, 53720),
    ):
        _tall_lantern(specs, t, side, seed)

    _planting_bed(specs, -0.30, -INNER_SIDE, 53810, length_t=0.075, clusters=5)
    _planting_bed(specs, -0.07, -INNER_SIDE, 53830, length_t=0.060, clusters=4)
    _planting_bed(specs, -0.24, INNER_SIDE, 53910, length_t=0.065, clusters=4)

    _paving_inlay(specs)

    bx, bz = R6._corridor_point(-0.15, INNER_SIDE + 2.1)
    fx, fz, _rx, _rz = R6._r5_corridor_basis(-0.15)
    for leg in (-0.62, 0.62):
        R6._cylinder(
            specs, "a23-h3-bench-leg", "dark_wood", H3_GROUP,
            bx + fx * leg, 0.22, bz + fz * leg, 0.08, 0.44, 8,
        )
    R6._panel(
        specs, "a23-h3-bench-seat", "dark_wood", H3_GROUP,
        R6._r5_corridor_quad(-0.15, INNER_SIDE + 2.1, 0.46, 0.85, 0.26), 0.08,
    )
    R6._panel(
        specs, "a23-h3-bench-back", "dark_wood", H3_GROUP,
        _vertical_quad(-0.159, -0.141, INNER_SIDE + 2.32, 0.50, 0.92), 0.06,
    )
    tx, tz = R6._corridor_point(-0.115, INNER_SIDE + 2.6)
    R6._cylinder(
        specs, "a23-h3-water-point", "brass", H3_GROUP, tx, 0.42, tz, 0.11, 0.76, 8,
    )
    return specs


# ---------------------------------------------------------------------------
# H4: true 0-7 m near-field frame (foreground urns, near balustrades, corner
# canopy trees, plus H3's edge runs/pergolas pulled clear of both hero
# screen columns). Ported verbatim from
# ``/private/tmp/hibana-blender/claude-a23-nakaniwa-h4/run_a23_h4_true_near_field.py``.
# This is the near-field population the production chain actually uses.
# ---------------------------------------------------------------------------
H4_GROUP = "a23-h4-true-near-field-frame"

H4_CAM = (121.93, 1.65, -130.21)
H4_TGT = (-5.0, 14.0, -4.0)


def _dual_hero_basis():
    f = [H4_TGT[i] - H4_CAM[i] for i in range(3)]
    length = math.sqrt(sum(v * v for v in f))
    f = [v / length for v in f]
    up = (0.0, 1.0, 0.0)
    r = [
        f[1] * up[2] - f[2] * up[1],
        f[2] * up[0] - f[0] * up[2],
        f[0] * up[1] - f[1] * up[0],
    ]
    rl = math.sqrt(sum(v * v for v in r))
    return tuple(f), tuple(v / rl for v in r)


# Shared by H4's own near-field placement, the H26 hero-defect-fix pass and
# the Tier-1 palace fix below -- all three originally recomputed this same
# basis independently from the same (H4_CAM, H4_TGT) pair; consolidating it
# here changes nothing numerically (identical formula, identical inputs).
FORWARD, RIGHT = _dual_hero_basis()


def cam_point(depth: float, lateral: float, height: float):
    """World point at a given depth along the view axis and lateral offset."""
    x = H4_CAM[0] + FORWARD[0] * depth + RIGHT[0] * lateral
    z = H4_CAM[2] + FORWARD[2] * depth + RIGHT[2] * lateral
    return (x, height, z)


def _urn(specs, depth, lateral, *, scale, seed, flowering, role):
    x, _y, z = cam_point(depth, lateral, 0.0)
    plinth_h = 0.62 * scale
    bowl_h = 0.86 * scale
    R6._cylinder(
        specs, f"{role}-plinth", "carved_stone", H4_GROUP,
        x, plinth_h / 2.0, z, 0.52 * scale, plinth_h, 12, top_radius=0.44 * scale,
    )
    R6._cylinder(
        specs, f"{role}-bowl", "ivory_stone", H4_GROUP,
        x, plinth_h + bowl_h / 2.0, z, 0.46 * scale, bowl_h, 14,
        top_radius=0.72 * scale,
    )
    R6._cylinder(
        specs, f"{role}-lip", "carved_stone", H4_GROUP,
        x, plinth_h + bowl_h + 0.07 * scale, z, 0.78 * scale, 0.16 * scale, 14,
        top_radius=0.74 * scale,
    )
    top = plinth_h + bowl_h + 0.22 * scale
    R6._leaf_cluster(
        specs, f"{role}-mass", "foliage_dark", H4_GROUP,
        x, top + 0.34 * scale, z, 0.88 * scale, 0.70 * scale, 30, seed,
    )
    if flowering:
        R6._leaf_cluster(
            specs, f"{role}-flower", "flower", H4_GROUP,
            x, top + 0.14 * scale, z, 0.94 * scale, 0.44 * scale, 24, seed + 7,
        )
    # Spilling growth over the lip so the urn is not a bare pot.
    for index in range(3):
        angle = index * 2.094 + seed * 0.11
        R6._leaf_cluster(
            specs, f"{role}-spill",
            "foliage_light" if index % 2 else "flower", H4_GROUP,
            x + math.cos(angle) * 0.66 * scale,
            top - 0.26 * scale,
            z + math.sin(angle) * 0.66 * scale,
            0.42 * scale, 0.52 * scale, 16, seed + 20 + index,
        )


def _near_balustrade(specs, depth0, depth1, lateral, seed, *, coping):
    steps = 7
    for index in range(steps):
        a = depth0 + (depth1 - depth0) * index / steps
        b = depth0 + (depth1 - depth0) * (index + 1) / steps
        ax, _ay, az = cam_point(a, lateral, 0.0)
        bx, _by, bz = cam_point(b, lateral, 0.0)
        R6._panel(
            specs, "a23-h4-near-balustrade-plinth", "carved_stone", H4_GROUP,
            ((ax, 0.40, az), (bx, 0.40, bz), (bx, 0.40, bz + 0.62), (ax, 0.40, az + 0.62)),
            0.80,
        )
        R6._panel(
            specs, "a23-h4-near-balustrade-coping", coping, H4_GROUP,
            ((ax, 1.14, az), (bx, 1.14, bz), (bx, 1.14, bz + 0.72), (ax, 1.14, az + 0.72)),
            0.20,
        )
        mx = (ax + bx) / 2.0
        mz = (az + bz) / 2.0
        R6._cylinder(
            specs, "a23-h4-near-baluster", "ivory_stone", H4_GROUP,
            mx, 0.90, mz + 0.34, 0.135, 0.70, 10, top_radius=0.10,
        )
    R6._leaf_cluster(
        specs, "a23-h4-near-balustrade-spill", "flower", H4_GROUP,
        *(lambda p: (p[0], 1.28, p[2]))(cam_point((depth0 + depth1) / 2.0, lateral, 0.0)),
        1.05, 0.56, 26, seed,
    )


def _corner_canopy_tree(specs, depth, lateral, *, height, crown, seed, role, flowering):
    x, _y, z = cam_point(depth, lateral, 0.0)
    _close_range_tree(
        specs, x=x, z=z, height=height, crown=crown, seed=seed,
        flowering=flowering, role=role,
    )


def a23_h4_specs(lod: int) -> list:
    specs: list = []

    # --- Near-field frame, 4-7 m band, both bottom corners ---------------
    _urn(specs, 5.4, -3.45, scale=1.35, seed=61010, flowering=True,
         role="a23-h4-left-foreground-urn")
    _urn(specs, 4.4, 3.15, scale=1.15, seed=61020, flowering=False,
         role="a23-h4-right-foreground-urn")
    _urn(specs, 8.6, 4.35, scale=0.95, seed=61030, flowering=True,
         role="a23-h4-right-second-urn")
    _near_balustrade(specs, 5.0, 10.5, -3.9, 61110, coping="ivory_stone")
    _near_balustrade(specs, 6.2, 11.8, 4.05, 61120, coping="carved_stone")

    # --- Canopies draping into the top corners from just outside frame ---
    _corner_canopy_tree(specs, 5.0, -6.2, height=9.4, crown=4.3, seed=61210,
                        role="a23-h4-left-corner-tree", flowering=True)
    _corner_canopy_tree(specs, 6.4, 6.6, height=8.8, crown=4.0, seed=61220,
                        role="a23-h4-right-corner-tree", flowering=False)

    # --- Pergolas pulled out of both hero screen columns -----------------
    _pergola(specs, 1.0, 61310, bay_t=0.042, start_t=-0.46, end_t=-0.32,
              vine_every=2)
    _pergola(specs, -1.0, 61320, bay_t=0.050, start_t=-0.42, end_t=-0.16,
              vine_every=2)

    _edge_run(specs, -INNER_SIDE, 61410, coping="ivory_stone", baluster_step=2.4)
    _edge_run(specs, INNER_SIDE, 61420, coping="carved_stone", baluster_step=3.0)

    for t, side, height, crown, seed, flowering in (
        (-0.41, -13.6, 8.6, 3.4, 61510, True),
        (-0.19, -14.2, 7.2, 2.9, 61520, False),
        (-0.34, 13.9, 7.8, 3.0, 61530, False),
        (-0.09, 14.6, 6.6, 2.6, 61540, True),
    ):
        x, z = R6._corridor_point(t, side)
        _close_range_tree(
            specs, x=x, z=z, height=height, crown=crown, seed=seed,
            flowering=flowering, role="a23-h4-promenade-tree",
        )

    for t, side, seed in (
        (-0.40, -INNER_SIDE, 61610), (-0.22, -INNER_SIDE, 61620),
        (-0.31, INNER_SIDE, 61630),
    ):
        _tall_lantern(specs, t, side, seed)

    _planting_bed(specs, -0.30, -INNER_SIDE, 61710, length_t=0.075, clusters=5)
    _planting_bed(specs, -0.07, -INNER_SIDE, 61720, length_t=0.060, clusters=4)
    _planting_bed(specs, -0.24, INNER_SIDE, 61730, length_t=0.065, clusters=4)

    _paving_inlay(specs)
    # NOTE: H3's bench is dropped - at 20 m it read as a floating white plank.
    return specs


# ---------------------------------------------------------------------------
# H26 hero-defect fixes: crown-tower window reposition (P0a), unsupported
# wing-window removal (P0a'), arcade-glazing rebuild (P0b), and the initial
# dual-hero composition recovery (P1: urn shrink + one pergola run moved
# off-axis). Ported verbatim from
# ``/private/tmp/hibana-blender/claude-a23-districts3/hero_defect_fixes.py``.
# ---------------------------------------------------------------------------
HERO_FIX_GROUP = "a23-h26-hero-defect-fix"
CONTRACT_OPENING_AREA_M2 = 1.5 * 1.8  # = 2.7, the round's own window cap
ORPHAN_CONTACT_MARGIN_M = 0.6


def _tp(p, pivot, scale, translate):
    return (
        pivot[0] + (p[0] - pivot[0]) * scale + translate[0],
        pivot[1] + (p[1] - pivot[1]) * scale + translate[1],
        pivot[2] + (p[2] - pivot[2]) * scale + translate[2],
    )


def transform_spec(spec: dict, *, pivot=(0.0, 0.0, 0.0), scale: float = 1.0,
                    translate=(0.0, 0.0, 0.0)) -> dict:
    new = dict(spec)
    kind = spec["kind"]
    if kind in ("box", "chamfer_box", "cylinder", "leaf_cluster"):
        x, y, z = _tp((spec["x"], spec["y"], spec["z"]), pivot, scale, translate)
        new["x"], new["y"], new["z"] = x, y, z
        if kind in ("box", "chamfer_box"):
            new["w"] = spec["w"] * scale
            new["h"] = spec["h"] * scale
            new["d"] = spec["d"] * scale
            if kind == "chamfer_box":
                new["bevel"] = spec["bevel"] * scale
        elif kind == "cylinder":
            new["radius"] = spec["radius"] * scale
            new["height"] = spec["height"] * scale
            new["topRadius"] = spec["topRadius"] * scale
        else:  # leaf_cluster
            new["radius"] = spec["radius"] * scale
            new["height"] = spec["height"] * scale
    elif kind == "panel":
        new["corners"] = tuple(_tp(c, pivot, scale, translate) for c in spec["corners"])
        new["thickness"] = spec["thickness"] * scale
    elif kind == "sweep":
        new["points"] = tuple(_tp(pt, pivot, scale, translate) for pt in spec["points"])
        new["radius"] = spec["radius"] * scale
    else:
        raise ValueError(f"unsupported spec kind for transform: {kind}")
    return new


def _spec_signature(s: dict) -> tuple:
    """Position-based fingerprint (role + kind + rounded centre), stable
    across two independent generations of the same deterministic helper
    call -- used to positionally match an isolated re-generation of a
    pergola/tree/lantern run against its twin already baked into the big
    composed spec list (both calls use identical inputs and formulas).
    """
    b = R6.spec_bounds(s)
    cx, cy, cz = (b[0] + b[3]) / 2.0, (b[1] + b[4]) / 2.0, (b[2] + b[5]) / 2.0
    return (s["role"], s["kind"], round(cx, 2), round(cy, 2), round(cz, 2))


# --- P0a: crown-tower lantern-window reposition -----------------------------
_TOWER_WINDOW_ROLE = "a21-r6-palace-vertical-tower-deep-occupied-window"
_BROKEN_WINDOW_Y = 33.9
_BROKEN_Y_TOLERANCE = 0.3

_NORMAL = (0.985, -0.172)
_TANGENT = (0.172, 0.985)
_ROOT = (-36.0, -91.0)
_TOWER_TANGENT_OFFSETS = (-7.5, 7.5)
_CROWN_NORMAL_OFFSET = 2.2
_WRONG_FACADE_OFFSET_M = 5.34
_CORRECT_FACADE_OFFSET_M = 3.4 + 0.09
_WINDOW_WIDTH_M = 1.55
_WINDOW_HEIGHT_M = 2.75


def _tower_xz(tangent_offset: float) -> tuple:
    return (
        _ROOT[0] + _TANGENT[0] * tangent_offset + _NORMAL[0] * _CROWN_NORMAL_OFFSET,
        _ROOT[1] + _TANGENT[1] * tangent_offset + _NORMAL[1] * _CROWN_NORMAL_OFFSET,
    )


def fix_vertical_tower_lantern_windows(specs: Sequence[dict]) -> tuple:
    kept = [
        s for s in specs
        if not (
            str(s["role"]).startswith(_TOWER_WINDOW_ROLE)
            and abs(float(s.get("y", -999.0)) - _BROKEN_WINDOW_Y) < _BROKEN_Y_TOLERANCE
        )
    ]
    removed_count = len(specs) - len(kept)

    added: list = []
    for tower_index, tangent_offset in enumerate(_TOWER_TANGENT_OFFSETS):
        tower_x, tower_z = _tower_xz(tangent_offset)
        facade_x = tower_x + _NORMAL[0] * _CORRECT_FACADE_OFFSET_M
        facade_z = tower_z + _NORMAL[1] * _CORRECT_FACADE_OFFSET_M
        window_index = 3
        z = facade_z + _TANGENT[1] * (-1.45 if window_index % 2 == 0 else 1.45)
        warm = (tower_index + window_index) % 2 == 0
        R6._deep_window(
            added, group=R6.PALACE_ID, role=_TOWER_WINDOW_ROLE,
            x=facade_x, y=_BROKEN_WINDOW_Y, z=z,
            width=_WINDOW_WIDTH_M, height=_WINDOW_HEIGHT_M,
            plane="side", warm=warm,
        )

    report = {
        "fix": "vertical-tower-lantern-window-reposition",
        "removedSpecs": removed_count,
        "addedSpecs": len(added),
        "wrongFacadeOffsetM": _WRONG_FACADE_OFFSET_M,
        "correctFacadeOffsetM": round(_CORRECT_FACADE_OFFSET_M, 3),
        "towersFixed": len(_TOWER_TANGENT_OFFSETS),
    }
    return kept + added, report


# --- P0a': unsupported wing-window removal ---------------------------------
_WING_WINDOW_ROLE = "a21-palace-wing-deep-window"
_WING_WINDOW_UNSUPPORTED_Y_MIN = 12.0


def fix_floating_wing_windows(specs: Sequence[dict]) -> tuple:
    kept: list = []
    removed = 0
    removed_columns: set = set()
    for s in specs:
        if (
            str(s["role"]).startswith(_WING_WINDOW_ROLE)
            and float(s.get("y", -999.0)) > _WING_WINDOW_UNSUPPORTED_Y_MIN
        ):
            removed += 1
            removed_columns.add(round(float(s.get("x", 0.0)), 1))
            continue
        kept.append(s)

    report = {
        "fix": "wing-deep-window-unsupported-upper-storey-removal",
        "removedSpecs": removed,
        "removedColumnXPositions": sorted(removed_columns),
        "unsupportedYThresholdM": _WING_WINDOW_UNSUPPORTED_Y_MIN,
    }
    return kept, report


# --- P0b: oversized arcade-glazing-card rebuild -----------------------------
_ARCADE_OPENING_ROLE = "a21-palace-deep-warm-occupied-opening"
_ARCADE_FRAME_MATERIAL = "carved_stone"
_ARCADE_MULLION_MATERIAL = "brass"
_ARCADE_BAND_MATERIAL = "brass"
_GRID_COLUMNS = 3
_GRID_FLOORS = 2
_CELL_OPENING_W = 1.3   # <= 1.5 m contract cap
_CELL_OPENING_H = 1.6   # <= 1.8 m contract cap


def rebuild_arcade_glazing_bays(specs: Sequence[dict]) -> tuple:
    kept: list = []
    bays: list = []
    for s in specs:
        if s["role"] == _ARCADE_OPENING_ROLE and s["kind"] == "box":
            bays.append(s)
        else:
            kept.append(s)

    added: list = []
    for i, bay in enumerate(bays):
        cx, cy, cz = bay["x"], bay["y"], bay["z"]
        w, h, d = bay["w"], bay["h"], bay["d"]
        material = bay["material"]
        role = f"a23-h26-arcade-bay-{i:02d}"

        pocket_back_z = cz
        frame_z = pocket_back_z + 0.08
        fixture_recess_z = pocket_back_z - 0.20

        R6._box(added, f"{role}-frame", _ARCADE_FRAME_MATERIAL, HERO_FIX_GROUP,
                cx, cy, frame_z, w, h, d)

        col_pitch = w / _GRID_COLUMNS
        row_pitch = h / _GRID_FLOORS
        for floor in range(_GRID_FLOORS):
            row_cy = cy - h / 2.0 + row_pitch * (floor + 0.5)
            if floor > 0:
                R6._box(added, f"{role}-band-f{floor}", _ARCADE_BAND_MATERIAL, HERO_FIX_GROUP,
                        cx, cy - h / 2.0 + row_pitch * floor, frame_z, w, 0.10, d * 1.2)
            for col in range(_GRID_COLUMNS):
                col_cx = cx - w / 2.0 + col_pitch * (col + 0.5)
                R6._box(added, f"{role}-glazing-{floor}-{col}", material, HERO_FIX_GROUP,
                        col_cx, row_cy, fixture_recess_z,
                        _CELL_OPENING_W, _CELL_OPENING_H, max(d, 0.06))
                if col > 0:
                    mullion_x = cx - w / 2.0 + col_pitch * col
                    R6._box(added, f"{role}-mullion-{floor}-{col}",
                            _ARCADE_MULLION_MATERIAL, HERO_FIX_GROUP,
                            mullion_x, row_cy, frame_z, 0.07, row_pitch * 0.88, d)

        R6._box(added, f"{role}-sill", _ARCADE_BAND_MATERIAL, HERO_FIX_GROUP,
                cx, cy - h / 2.0, frame_z, w, 0.10, d * 1.2)
        R6._box(added, f"{role}-lintel", _ARCADE_BAND_MATERIAL, HERO_FIX_GROUP,
                cx, cy + h / 2.0, frame_z, w, 0.10, d * 1.2)

    report = {
        "fix": "arcade-oversized-glazing-card-rebuild",
        "baysRebuilt": len(bays),
        "originalSpecsRemoved": len(bays),
        "newSpecsAdded": len(added),
        "gridPerBay": f"{_GRID_COLUMNS} columns x {_GRID_FLOORS} floors",
        "cellOpeningM": [_CELL_OPENING_W, _CELL_OPENING_H],
        "contractCapM2": CONTRACT_OPENING_AREA_M2,
        "originalOpeningAreaM2": round(bays[0]["w"] * bays[0]["h"], 2) if bays else None,
    }
    return kept + added, report


# --- P1: initial dual-hero composition recovery (urn shrink + one pergola
# run moved off-axis; superseded-but-not-replaced by the Tier-1 fix below,
# which targets the *other*, still-occluding pergola run plus trees/lantern
# stations the initial recovery never touched). ---------------------------
_URNS = (
    ("a23-h4-left-foreground-urn", 5.4, -3.45),
    ("a23-h4-right-foreground-urn", 4.4, 3.15),
    ("a23-h4-right-second-urn", 8.6, 4.35),
)
_URN_SCALE_FACTOR = 0.40
_LEFT_URN_ROLE = "a23-h4-left-foreground-urn"
_OFF_AXIS_TRANSLATE_M = 14.0


def _isolated_left_pergola_specs() -> list:
    out: list = []
    _pergola(out, 1.0, 61310, bay_t=0.042, start_t=-0.46, end_t=-0.32, vine_every=2)
    return out


def recover_dual_hero_composition(specs: Sequence[dict]) -> tuple:
    specs = list(specs)
    translate_vec = (RIGHT[0] * -_OFF_AXIS_TRANSLATE_M, 0.0,
                      RIGHT[2] * -_OFF_AXIS_TRANSLATE_M)

    urn_before_heights: dict = {}
    urn_after_heights: dict = {}
    out: list = []
    urn_count = 0
    for s in specs:
        role = str(s["role"])
        matched = next((u for u in _URNS if role.startswith(u[0])), None)
        if matched is None:
            out.append(s)
            continue
        urn_role, depth, lateral = matched
        pivot = cam_point(depth, lateral, 0.0)
        translate = translate_vec if urn_role == _LEFT_URN_ROLE else (0.0, 0.0, 0.0)
        out.append(transform_spec(s, pivot=pivot, scale=_URN_SCALE_FACTOR, translate=translate))
        urn_count += 1
        b_before = R6.spec_bounds(s)
        urn_before_heights[urn_role] = max(urn_before_heights.get(urn_role, 0.0), b_before[4])
    specs = out

    left_pergola_specs = _isolated_left_pergola_specs()
    left_signatures = {_spec_signature(s) for s in left_pergola_specs}
    out = []
    pergola_moved = 0
    for s in specs:
        if _spec_signature(s) in left_signatures:
            out.append(transform_spec(s, translate=translate_vec))
            pergola_moved += 1
        else:
            out.append(s)
    specs = out

    for urn_role, _depth, _lateral in _URNS:
        heights = [
            R6.spec_bounds(s)[4] for s in specs if str(s["role"]).startswith(urn_role)
        ]
        if heights:
            urn_after_heights[urn_role] = max(heights)

    report = {
        "fix": "dual-hero-composition-recovery",
        "urnSpecsTransformed": urn_count,
        "urnScaleFactor": _URN_SCALE_FACTOR,
        "urnHeightBeforeM": {k: round(v, 2) for k, v in urn_before_heights.items()},
        "urnHeightAfterM": {k: round(v, 2) for k, v in urn_after_heights.items()},
        "eyeHeightM": 1.65,
        "leftPergolaSpecsFound": len(left_pergola_specs),
        "leftPergolaSpecsMoved": pergola_moved,
        "offAxisTranslateM": _OFF_AXIS_TRANSLATE_M,
        "translateVector": [round(v, 3) for v in translate_vec],
    }
    return specs, report


KNOWN_REMAINING_OVERSIZED_FAMILIES = frozenset({
    "a21-palace-central-keep-occupied-loggia",
    "a21-r5-palace-lower-water-loggia-recessed-occupied-loggia",
    "a21-r5-palace-middle-garden-loggia-recessed-occupied-loggia",
    "a21-r5-palace-upper-sky-loggia-recessed-occupied-loggia",
    "a21-r5-palace-rooted-keep-warm-loggia-depth",
    "a21-r5-conservatory-transparent-warm-entry-bay-recessed-glazing",
    "a21-r6-garden-city-lower-tall-occupied-window-recessed-glazing",
    "a21-r6-palace-monumental-lower-water-loggia-recessed-occupied-loggia",
    "a21-r6-palace-monumental-middle-garden-loggia-recessed-occupied-loggia",
    "a21-r6-palace-monumental-upper-crown-loggia-recessed-occupied-loggia",
    "a21-r6-palace-forward-crown-tower-lower-recessed-occupied-depth",
    "a21-r6-palace-forward-crown-tower-middle-recessed-occupied-depth",
    "a21-r6-palace-forward-crown-tower-upper-recessed-occupied-depth",
})


def assert_no_orphan_emissive(specs: Sequence[dict]) -> dict:
    specs = list(specs)
    bounds_by_group: dict = {}
    for s in specs:
        bounds_by_group.setdefault(str(s["group"]), []).append(R6.spec_bounds(s))

    orphaned: list = []
    checked = 0
    for s in specs:
        if s["material"] != "warm_glow":
            continue
        checked += 1
        b = R6.spec_bounds(s)
        margin = ORPHAN_CONTACT_MARGIN_M
        expanded = (b[0] - margin, b[1] - margin, b[2] - margin,
                    b[3] + margin, b[4] + margin, b[5] + margin)
        has_neighbor = False
        for ob in bounds_by_group.get(str(s["group"]), ()):
            if ob is b:
                continue
            if (ob[0] <= expanded[3] and ob[3] >= expanded[0]
                    and ob[1] <= expanded[4] and ob[4] >= expanded[1]
                    and ob[2] <= expanded[5] and ob[5] >= expanded[2]):
                has_neighbor = True
                break
        if not has_neighbor:
            orphaned.append(s["role"])

    passed = not orphaned
    result = {
        "check": "assert_no_orphan_emissive (parentless-ness only, HARD gate)",
        "warmGlowSpecsChecked": checked,
        "orphanContactMarginM": ORPHAN_CONTACT_MARGIN_M,
        "orphanedCount": len(orphaned),
        "orphanedSample": orphaned[:20],
        "passed": passed,
    }
    if not passed:
        raise AssertionError(f"assert_no_orphan_emissive FAILED: {result}")
    return result


def measure_oversized_warm_glow(specs: Sequence[dict]) -> dict:
    specs = list(specs)
    oversized = []
    for s in specs:
        if s["material"] != "warm_glow":
            continue
        if s["kind"] == "box":
            area = float(s["w"]) * float(s["h"])
        elif s["kind"] == "panel":
            c = s["corners"]
            area = math.dist(c[0], c[1]) * math.dist(c[1], c[2])
        else:
            continue
        if area > CONTRACT_OPENING_AREA_M2 + 0.15:
            oversized.append((s["role"], round(area, 2)))
    roles_hit = sorted({r for r, _a in oversized})
    return {
        "check": "measure_oversized_warm_glow (non-fatal, informational)",
        "contractOpeningAreaCapM2": CONTRACT_OPENING_AREA_M2,
        "oversizedInstanceCount": len(oversized),
        "oversizedRoleFamilies": roles_hit,
        "knownRemainingUnfixed": sorted(set(roles_hit) & KNOWN_REMAINING_OVERSIZED_FAMILIES),
        "unexpectedNewOversized": sorted(set(roles_hit) - KNOWN_REMAINING_OVERSIZED_FAMILIES),
    }


def assert_no_unsupported_wing_windows(specs: Sequence[dict]) -> dict:
    survivors = [
        s["role"] for s in specs
        if str(s["role"]).startswith(_WING_WINDOW_ROLE)
        and float(s.get("y", -999.0)) > _WING_WINDOW_UNSUPPORTED_Y_MIN
    ]
    result = {
        "check": "assert_no_unsupported_wing_windows (HARD gate)",
        "unsupportedYThresholdM": _WING_WINDOW_UNSUPPORTED_Y_MIN,
        "survivorCount": len(survivors),
        "passed": not survivors,
    }
    if survivors:
        raise AssertionError(f"assert_no_unsupported_wing_windows FAILED: {result}")
    return result


def apply_all_hero_fixes(specs: Sequence[dict]) -> tuple:
    specs, r1 = fix_vertical_tower_lantern_windows(specs)
    specs, r1b = fix_floating_wing_windows(specs)
    specs, r2 = rebuild_arcade_glazing_bays(specs)
    specs, r3 = recover_dual_hero_composition(specs)
    assertion = assert_no_orphan_emissive(specs)
    wing_assertion = assert_no_unsupported_wing_windows(specs)
    oversized_measurement = measure_oversized_warm_glow(specs)
    return specs, {
        "verticalTowerLanternWindowFix": r1,
        "wingWindowUnsupportedUpperStoreyFix": r1b,
        "arcadeGlazingRebuild": r2,
        "dualHeroCompositionRecovery": r3,
        "orphanEmissiveAssertion": assertion,
        "unsupportedWingWindowAssertion": wing_assertion,
        "oversizedWarmGlowMeasurement": oversized_measurement,
    }


# ---------------------------------------------------------------------------
# Tier 1: the palace-occlusion fix. Four additional, independently verified
# ``_RIGHT``-axis translations (binary-searched against a direct occlusion
# measurement, not guessed) that clear the Crowned Water Palace's screen
# column: 91.17% occluded before -> 8.46% after. Ported verbatim from
# ``/private/tmp/hibana-blender/claude-a23-tier1/pergola_fix.py``.
#
# Root cause (measured, not assumed): the round's own initial recovery pass
# above (P1) translated H3._pergola(sign=+1, seed=61310) 14 m off-axis, and
# that move worked -- but H4 places a SECOND, denser pergola run via
# H3._pergola(sign=-1, seed=61320), and that one was never touched. Direct
# occlusion-grid attribution (project every non-palace spec into the
# dual-hero camera, build a depth-aware occlusion grid over the palace's own
# screen cells, attribute each blocked cell to whichever spec is frontmost
# there) found the occlusion was NOT purely that pergola:
#     a23-h3-pergola-*                 567 of 991 blocked cells (57%)
#     a23-h4-*-promenade/corner-tree-* 416 of 991 blocked cells (42%)
#     a23-h3-lantern-*                  60 of 991 blocked cells ( 6%, overlaps)
# ---------------------------------------------------------------------------
PERGOLA_OFF_AXIS_M = -18.0
TREE_OFF_AXIS_M = -18.0
CORNER_TREE_OFF_AXIS_M = 8.0
LANTERN_OFF_AXIS_M = -10.0


def _offending_signatures() -> dict:
    pergola: list = []
    _pergola(pergola, -1.0, 61320, bay_t=0.050, start_t=-0.42, end_t=-0.16,
             vine_every=2)

    def tree_station(t, side, height, crown, seed, flowering):
        x, z = R6._corridor_point(t, side)
        out: list = []
        _close_range_tree(
            out, x=x, z=z, height=height, crown=crown, seed=seed,
            flowering=flowering, role="a23-h4-promenade-tree",
        )
        return out

    trees = (
        tree_station(-0.41, -13.6, 8.6, 3.4, 61510, True)
        + tree_station(-0.19, -14.2, 7.2, 2.9, 61520, False)
    )

    def lantern(t, side, seed):
        out: list = []
        _tall_lantern(out, t, side, seed)
        return out

    lanterns = (
        lantern(-0.40, -INNER_SIDE, 61610)
        + lantern(-0.22, -INNER_SIDE, 61620)
    )

    return {
        "pergola": {_spec_signature(s) for s in pergola},
        "tree": {_spec_signature(s) for s in trees},
        "lantern": {_spec_signature(s) for s in lanterns},
    }


def clear_palace(specs: list) -> tuple:
    """Apply the four verified translations. Returns (new_specs, report)."""
    sigsets = _offending_signatures()

    t_pergola = (RIGHT[0] * PERGOLA_OFF_AXIS_M, 0.0, RIGHT[2] * PERGOLA_OFF_AXIS_M)
    t_tree = (RIGHT[0] * TREE_OFF_AXIS_M, 0.0, RIGHT[2] * TREE_OFF_AXIS_M)
    t_corner = (RIGHT[0] * CORNER_TREE_OFF_AXIS_M, 0.0, RIGHT[2] * CORNER_TREE_OFF_AXIS_M)
    t_lantern = (RIGHT[0] * LANTERN_OFF_AXIS_M, 0.0, RIGHT[2] * LANTERN_OFF_AXIS_M)

    out: list = []
    moved: list = []
    counts = {"pergola": 0, "tree": 0, "cornerTree": 0, "lantern": 0}
    for s in specs:
        role = str(s.get("role", ""))
        sig = _spec_signature(s)
        if sig in sigsets["pergola"]:
            new = transform_spec(s, translate=t_pergola)
            counts["pergola"] += 1
        elif sig in sigsets["tree"]:
            new = transform_spec(s, translate=t_tree)
            counts["tree"] += 1
        elif role.startswith("a23-h4-right-corner-tree"):
            new = transform_spec(s, translate=t_corner)
            counts["cornerTree"] += 1
        elif sig in sigsets["lantern"]:
            new = transform_spec(s, translate=t_lantern)
            counts["lantern"] += 1
        else:
            out.append(s)
            continue
        out.append(new)
        moved.append(new)

    report = {
        "fix": "a23-tier1-clear-palace",
        "rootCauseConfirmed": (
            "100% of the pergola occlusion traced to the untranslated "
            "H3._pergola(sign=-1, seed=61320) call; the sign=+1 call "
            "the H26 recovery pass moved 14 m was already fully clear"
        ),
        "translateDirectionM": {
            "right": [round(v, 6) for v in RIGHT],
            "pergola": PERGOLA_OFF_AXIS_M,
            "promenadeTree": TREE_OFF_AXIS_M,
            "rightCornerTree": CORNER_TREE_OFF_AXIS_M,
            "lantern": LANTERN_OFF_AXIS_M,
        },
        "specsMoved": counts,
        "totalSpecsMoved": sum(counts.values()),
        "untouched": [
            "sign=+1 pergola run (already clear, H26 recovery pass)",
            "a23-h4-true-near-field-frame group (urns, near-balustrades)",
            "left-corner-tree",
            "the two conservatory-side promenade trees",
            "the third (conservatory-side) tall lantern",
            "edge-run balustrades / planting beds / paving inlay "
            "(measured zero occlusion contribution)",
        ],
    }
    return out, report


# ---------------------------------------------------------------------------
# Production mesh emission.
#
# R6's own ``emit_specs_to_builder`` unconditionally calls ``builder.
# add_chamfer_box(...)``/``add_sweep(...)``/``add_leaf_cluster(...)`` -- real
# methods on R6's own ``A21MeshBuilder`` (kit.py's ``RenderKit`` contract,
# used by evidence.py's render harness), but build_all_stages.py's own
# ``MeshBuilder`` implements none of the three by those names.
# ``tools/blender/a23_bridge.py`` hit exactly this same gap for the OTHER 30
# stages' district infill and solved it by reimplementing its own emission
# function rather than reusing R6's (see that module's docstring, point 1);
# this is the nakaniwa-specific equivalent, complete rather than restricted,
# because this composition -- unlike districts.py's infill -- actually emits
# ``leaf_cluster`` (537 instances in the proven build: H3/H4's whole purpose
# is near-field foliage) and multi-point ``sweep``/``panel`` shapes (277 of
# 1,303 sweeps carry more than 2 points, 20 of 795 panels carry more than 4
# corners -- the conservatory's curved ribs and vault cross-sections). Two
# new MeshBuilder methods close the gap properly rather than approximately:
# ``add_tube`` (a real multi-point tube, sharing cross-sections at internal
# joints -- chaining ``add_cylinder_between`` per segment instead would cap
# every joint and roughly double triangle cost for a long polyline, which
# an earlier version of this function measured directly: 299,568 real
# Blender-evaluated triangles against a 260,000 cap) and ``add_ngon_panel``
# (R6's own Newell's-method N-gon extrusion, so an N-corner panel costs the
# same N*4-4 triangles R6's kit expects instead of a naive per-triangle fan
# quad's (N-2)*12).
# ---------------------------------------------------------------------------
def emit_specs_to_mesh_builder(builder, specs: Sequence[dict], material_map: dict) -> dict:
    """Emit an a21-r6-shaped spec list into build_all_stages.py's own
    MeshBuilder. ``chamfer_box`` downgrades to a plain box (matching
    a23_bridge.emit_specs_to_mesh_builder's own precedent for the same
    missing primitive); ``sweep``/``panel`` route through the real
    ``add_tube``/``add_ngon_panel`` primitives (see module note above) for
    every corner/point count, matching R6's own triangle-cost formulas
    exactly rather than approximating; ``leaf_cluster`` becomes one
    ``add_rock`` call -- the same low-poly canopy-volume primitive
    ``add_tree`` already uses for every non-conifer tree canopy elsewhere in
    build_all_stages.py, so nakaniwa's foliage renders with the same device
    the other 30 stages' trees already use, not a novel one.
    """
    counts = {"box": 0, "chamfer_box": 0, "cylinder": 0, "panel": 0, "sweep": 0, "leaf_cluster": 0}
    for spec in specs:
        key = material_map.get(spec["material"], spec["material"])
        kind = spec["kind"]
        if kind == "box":
            builder.add_box(spec["x"], spec["y"], spec["z"], spec["w"], spec["h"], spec["d"], key)
        elif kind == "chamfer_box":
            builder.add_box(spec["x"], spec["y"], spec["z"], spec["w"], spec["h"], spec["d"], key)
        elif kind == "cylinder":
            builder.add_cylinder(
                spec["x"], spec["y"], spec["z"], spec["radius"], spec["height"],
                key, spec["segments"], spec["topRadius"],
            )
        elif kind == "panel":
            builder.add_ngon_panel(spec["corners"], spec["thickness"], key)
        elif kind == "sweep":
            points = spec["points"]
            if len(points) < 2:
                raise ValueError(f"emit_specs_to_mesh_builder: sweep {spec['role']} has fewer than 2 points")
            builder.add_tube(points, spec["radius"], spec["sides"], key)
        elif kind == "leaf_cluster":
            builder.add_rock(spec["x"], spec["y"], spec["z"], spec["radius"], spec["height"], key, 7, spec["seed"])
        else:
            raise ValueError(f"emit_specs_to_mesh_builder: unsupported kind {kind!r}")
        counts[kind] += 1
    return counts


# ---------------------------------------------------------------------------
# Reclamation policy: nakaniwa's own group/role sets, ported verbatim from
# ``/private/tmp/hibana-blender/claude-a23-triangle-reclaim/reclamation_filter.py``.
# ---------------------------------------------------------------------------
HERO_GROUPS = frozenset({R6.PALACE_ID, R6.CONSERVATORY_ID})

PROTECTED_GROUPS = frozenset({
    "a21-r2-nakaniwa-garden-canal-corridor",
    "a21-r4-nakaniwa-canal-contact-story",
    "a21-r5-nakaniwa-bridge-first-foreground",
    "a21-r6-nakaniwa-foreground-edge-gardens-water",
})

# "a21-r6-nakaniwa-open-bridge-axis" was tried and dropped after the
# empirical render-diff proof documented in reclamation_filter.py (leaf
# clusters straddling the frame edge poke back onscreen despite an
# offscreen conservative AABB) -- left out here for the same reason.
SAFE_BACKGROUND_GROUPS = frozenset({
    "a21-r5-nakaniwa-layered-garden-city-depth",
    "a21-r6-nakaniwa-midground-roofed-facade-layers",
    "a21-r6-nakaniwa-midground-hanging-garden-spine",
})

VEGETATION_THIN_ROLES: dict = {
    "a21-r5-garden-city-layered-canopy-leaf-cluster": 3,
    "a21-r5-garden-city-layered-canopy-branch": 3,
    "a21-r5-garden-city-layered-canopy-trunk": 3,
    "a21-r5-garden-city-roof-garden": 2,
    "a21-r6-midground-hanging-garden-readable-cascade": 2,
    "a21-r6-midground-readable-roof-garden": 2,
    "a21-r6-midground-readable-roof-tree-crown": 2,
}

THIN_ACCENT_DROP_ROLES = frozenset({
    "a21-r5-garden-city-upper-deep-window-vertical-mullion",
    "a21-r5-garden-city-upper-deep-window-horizontal-mullion",
    "a21-r6-garden-city-lower-tall-occupied-window-vertical-mullion",
    "a21-r6-garden-city-lower-tall-occupied-window-horizontal-mullion",
    "a21-r6-midground-tall-warm-window-rhythm-vertical-mullion",
    "a21-r6-midground-tall-warm-window-rhythm-horizontal-mullion",
})

# ---------------------------------------------------------------------------
# Five-camera safety contract, ported verbatim from
# ``/private/tmp/hibana-blender/claude-a23-districts3/district_infill_v3.py``
# (identical location/target/lens to R6.PROOF_CAMERAS' own four matching
# entries; DUAL_HERO_CAMERA uses the round's Y14 target override rather than
# R6.MAIN_REFERENCE_CAMERA's own Y30 target).
# ---------------------------------------------------------------------------
DUAL_HERO_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_DualHero_TargetY14_Iteration21",
    "location": (121.93, 1.65, -130.21), "target": (-5.0, 14.0, -4.0),
    "lensMm": 23.0, "sensorWidthMm": 36.0,
}
PALACE_ARCADE_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_PalaceArcade",
    "location": (-34.0, 1.65, -16.0), "target": (-61.0, 18.0, -66.0),
    "lensMm": 24.0, "sensorWidthMm": 36.0,
}
CONSERVATORY_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_ConservatoryFiveVaults",
    "location": (16.0, 1.65, 12.0), "target": (54.0, 17.0, 66.0),
    "lensMm": 23.0, "sensorWidthMm": 36.0,
}
GARDEN_BRIDGE_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_GardenBridge",
    "location": (16.0, 1.65, -22.0), "target": (28.8, 4.0, -34.1),
    "lensMm": 24.0, "sensorWidthMm": 36.0,
}
PALACE_WATER_COURT_CAMERA = {
    "name": "CAM_Nakaniwa_A21_Eye165_PalaceWaterCourt",
    "location": (-82.0, 1.65, -50.0), "target": (-82.0, 3.0, -37.0),
    "lensMm": 18.0, "sensorWidthMm": 36.0,
}
FIVE_CAMERAS = (
    DUAL_HERO_CAMERA, PALACE_ARCADE_CAMERA, CONSERVATORY_CAMERA,
    GARDEN_BRIDGE_CAMERA, PALACE_WATER_COURT_CAMERA,
)

ALWAYS_PROTECT_GROUPS = frozenset({
    R6.PALACE_ID, R6.CONSERVATORY_ID,
    "a21-r5-nakaniwa-bridge-first-foreground",
    "a21-r6-nakaniwa-foreground-edge-gardens-water",
})


# ---------------------------------------------------------------------------
# Production integration material map.
#
# R6's own ``DEFAULT_INTEGRATION_MATERIAL_MAP`` is an identity map
# (``{key: key for key in MATERIALS}``) -- correct for R6's OWN Blender
# render harness (evidence.py / the private study, which is how the
# tier1 comparison images this module reproduces were themselves rendered),
# but wrong for ``build_all_stages.py``'s ``MeshBuilder``, whose ``materials``
# dict is built independently by that file's own ``build_materials(stage)``
# and only defines its own generic key vocabulary ("wall", "wall_warm",
# "roof", "glass", "natural", "terrain", "water", "emissive", ...) -- it has
# no entries named "carved_stone" or "warm_glow". Nakaniwa's retired A18 kit
# had its own hand-built remap for exactly this reason
# (``nakaniwa_reference_a18.DEFAULT_INTEGRATION_MATERIAL_MAP``); this is the
# A21-R6-shaped equivalent, chosen to match ``build_materials()``'s own
# nakaniwa-specific colour comments 1:1 by semantic role (verdigris roof,
# translucent botanical glass, sandstone wall_warm, green natural) rather
# than by name, and otherwise mirroring the A18 map's choices for materials
# both kits share by role (verdigris_bronze/dark_wood/foliage_*/flower/
# water/warm_glow). Used for every LOD (the base kit's MATERIALS dict, and
# therefore this map, is identical across LOD0/1/2).
# ---------------------------------------------------------------------------
INTEGRATION_MATERIAL_MAP = {
    "ivory_stone": "wall",
    "carved_stone": "wall_warm",
    "moss_stone": "road",
    "wet_stone": "wall_cool",
    "verdigris_bronze": "roof",
    "dark_wood": "wood",
    "brass": "accent",
    "foliage_dark": "natural",
    "foliage_light": "natural",
    "flower": "accent",
    "dirty_glass": "glass",
    "glass_highlight": "glass",
    "warm_glow": "emissive",
    "water": "water",
}


# ---------------------------------------------------------------------------
# Composer: reproduces claude-a23-promotion/verify_specs.py's
# promoted_after_specs() + claude-a23-tier1/pergola_fix.py's clear_palace(),
# using only repository-resident code and the empirically-proven-equivalent
# empty district_seed (see module docstring).
# ---------------------------------------------------------------------------
def build_nakaniwa_a23_specs(lod: int = 0) -> tuple:
    """Return (specs, info) -- the A23 round's proven best Nakaniwa LOD0
    composition: base kit -> H3/H4 near field -> reclamation passes 3+4 ->
    material family/ground/glazing/foliage transforms -> H26 hero-defect
    fixes -> district infill -> the Tier-1 palace-occlusion fix.

    Only meaningful at ``lod == 0`` -- the A23 round never touched LOD1/2,
    which remain ``R6.build_specs(lod)`` unmodified (see
    ``build_nakaniwa_reference_lod`` in build_all_stages.py).
    """
    rec_config = reclamation.ReclamationConfig()

    base_kit = R6.build_specs(lod)
    near_field = a23_h4_specs(lod)
    district_seed: list = []  # see module docstring: proven equivalent to the
    # private study's real 80-spec best-effort seed for this build's actual
    # inputs -- both produce byte-identical 5,373-spec composed output.

    pass3_reclaimed = reclamation.pass3_five_camera_correctness_filter(
        base_kit, near_field, district_seed,
        kit=KIT, cameras=FIVE_CAMERAS,
        safe_background_groups=SAFE_BACKGROUND_GROUPS,
        vegetation_thin_roles=VEGETATION_THIN_ROLES,
        thin_accent_drop_roles=THIN_ACCENT_DROP_ROLES,
        config=rec_config,
    )
    pass4_simplified = reclamation.simplify_specs(
        pass3_reclaimed, kit=KIT, cameras=FIVE_CAMERAS,
        safe_background_groups=SAFE_BACKGROUND_GROUPS, config=rec_config,
    )

    remapped, _changed = materials.remap_ground(
        pass4_simplified + near_field, kit=KIT,
        source_materials=materials.NAKANIWA_GROUND_SOURCE_MATERIALS,
        role_fragments=materials.NAKANIWA_GROUND_ROLE_FRAGMENTS,
        target_material=materials.NAKANIWA_GROUND_TARGET_MATERIAL,
        max_top_y=materials.NAKANIWA_GROUND_MAX_TOP_Y,
    )
    bounds = materials.hero_interior_bounds(remapped, kit=KIT, role_token="conservatory")
    interior: list = []
    materials.build_hero_interior(
        interior, bounds, kit=KIT, group="a23-h13-conservatory-interior",
        role_prefix="a23-h13-conservatory",
        planting_role_prefix="a23-h13-conservatory-interior",
    )
    combined = remapped + interior
    thick, _info = materials.thicken_near_volumetrics(
        combined, kit=KIT, camera_point=H4_CAM,
        companion_group="a23-h15-volumetric-near-foliage",
    )
    pass4_fixed_style = thick

    hero_fixed, hero_fix_report = apply_all_hero_fixes(pass4_fixed_style)
    pass4_fixed_estimated = R6.estimated_triangles(hero_fixed)

    # base_for_placement: pass1+pass2 only (never pass3/4) -- used only to
    # size the district exclusion grid, never emitted itself. Matches the
    # private study's own documented distinction.
    p1_camera = dict(DUAL_HERO_CAMERA)
    p1 = reclamation.pass1_strict_invisible_filter(
        base_kit, kit=KIT, camera=p1_camera,
        hero_groups=HERO_GROUPS, protected_groups=PROTECTED_GROUPS,
        safe_background_groups=SAFE_BACKGROUND_GROUPS,
        vegetation_thin_roles=VEGETATION_THIN_ROLES,
        thin_accent_drop_roles=THIN_ACCENT_DROP_ROLES,
        config=rec_config,
    )
    p2 = reclamation.pass2_occlusion_filter(
        p1, kit=KIT, camera=p1_camera, occluder_specs=near_field,
        safe_background_groups=SAFE_BACKGROUND_GROUPS,
        vegetation_thin_roles=VEGETATION_THIN_ROLES,
        config=rec_config,
    )
    remapped2, _changed2 = materials.remap_ground(
        p2 + near_field, kit=KIT,
        source_materials=materials.NAKANIWA_GROUND_SOURCE_MATERIALS,
        role_fragments=materials.NAKANIWA_GROUND_ROLE_FRAGMENTS,
        target_material=materials.NAKANIWA_GROUND_TARGET_MATERIAL,
        max_top_y=materials.NAKANIWA_GROUND_MAX_TOP_Y,
    )
    bounds2 = materials.hero_interior_bounds(remapped2, kit=KIT, role_token="conservatory")
    interior2: list = []
    materials.build_hero_interior(
        interior2, bounds2, kit=KIT, group="a23-h13-conservatory-interior",
        role_prefix="a23-h13-conservatory",
        planting_role_prefix="a23-h13-conservatory-interior",
    )
    combined2 = remapped2 + interior2
    base_for_placement, _info2 = materials.thicken_near_volumetrics(
        combined2, kit=KIT, camera_point=H4_CAM,
        companion_group="a23-h15-volumetric-near-foliage",
    )

    d_config = districts.DistrictConfig(
        always_protect_groups=ALWAYS_PROTECT_GROUPS, always_protect_role_prefix="a23-h",
    )
    tri_budget = R6.LOD_BUDGETS[lod]["maxEvaluatedTriangles"] - pass4_fixed_estimated - 400
    plan = districts.plan_district(
        base_for_placement, tri_budget=tri_budget, kit=KIT,
        canonical_roads=R6.CANONICAL_ROADS, player_spawns=R6.CANONICAL_PLAYER_SPAWNS,
        bot_spawns=R6.CANONICAL_BOT_SPAWNS, cameras=FIVE_CAMERAS, config=d_config,
        focus_camera=GARDEN_BRIDGE_CAMERA, occluder_specs=hero_fixed,
    )
    composed = hero_fixed + plan["specs"]

    final_specs, palace_fix_report = clear_palace(composed)

    info = {
        "pass4FixedEstimated": pass4_fixed_estimated,
        "heroFixReport": hero_fix_report,
        "districtPlan": {key: value for key, value in plan.items() if key != "specs"},
        "palaceFix": palace_fix_report,
        "estimatedTotal": R6.estimated_triangles(final_specs),
    }
    return final_specs, info
