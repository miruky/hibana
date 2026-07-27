"""A23 material-palette transforms: palette-slot repurposing, ground/wall
separation, and the small geometry treatments that make a material change
actually read (an occupied interior behind glazing, extra volume on near
foliage).

Promoted from the private study:
  - the material-FAMILY split (bright/cool hero stone vs. warm/rough town
    limestone vs. wet dark paving vs. dark bronze ribs, widened foliage
    tones): ``..._h5/run_a23_h5_material_hierarchy.py``, desaturated once
    more at ``..._h6/run_a23_h6_ground_split.py``
  - ground remap + the tuned ground palette recipe:
    ``/private/tmp/hibana-blender/claude-a23-nakaniwa-h7/run_a23_h7_ground_plane.py``
    and ``..._h8/run_a23_h8_ground_tuned.py`` (H8's ``MATERIAL_OVERRIDES`` is
    a ``copy.deepcopy`` of H7's, which is a deepcopy of H6's, which is a
    deepcopy of H5's -- the fully-resolved dict actually used by the
    production chain carries every one of those four rounds' changes
    forward, which is why this module keeps H5/H6's family split as its own
    preset rather than only H7/H8's ground-specific delta)
  - conservatory (hero interior) glazing + occupancy:
    ``..._h13/run_a23_h13_conservatory.py``
  - near-field foliage thickening:
    ``..._h15/run_a23_h15_near_foliage.py``

Why these four live in one module
-----------------------------------
Each is the same shape: a material-recipe change (``apply_material_overrides``)
paired with a geometry transform that makes the new recipe legible instead of
cosmetic. H7/H8 found that recolouring the ground alone was not enough —
the ground and the walls shared one material slot, so no palette edit could
separate them until specs were also *reassigned* to a different slot
(``remap_ground``). H13 found that a transmissive glazing recipe alone still
reads as sky at range unless something occupied is placed behind it
(``build_hero_interior``). H15 found that raising leaf *count* alone still
reads as a flat card unless a second, offset, differently-toned cluster is
nested inside it (``thicken_near_volumetrics``). None of the four passes in
``reclamation.py`` nor the placement logic in ``districts.py`` cover this
kind of "surface + what stands behind the surface" transform, so they are
grouped here instead of invented as a sixth module.

Every function below is a transform over "any kit's MATERIALS dict and
ground role": ``apply_material_overrides`` never assumes which material key
it is touching, ``remap_ground`` takes its source/target slots and matching
role fragments as parameters, and the two nakaniwa recipes at the bottom of
this module are kept only as named, reusable presets/examples — nothing in
the transform functions depends on them.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from tools.blender.a23.kit import SpecKit, Spec, spec_center


# ---------------------------------------------------------------------------
# 1. Palette-slot repurposing: a pure dict transform, no kit needed.
# ---------------------------------------------------------------------------
def apply_material_overrides(materials: Mapping[str, dict], overrides: Mapping[str, dict]) -> dict:
    """Return a deep copy of ``materials`` with each ``overrides[key]`` dict
    shallow-merged into ``materials[key]``. This is how the round repurposed
    an underused material slot (nakaniwa's dead ``moss_stone``) into a new
    role (ground granite) without raising the material count past the
    budget cap: the slot already existed and was already wired into the
    kit's draw-call batching, so overriding its recipe costs nothing.
    """
    result = copy.deepcopy(dict(materials))
    for key, patch in overrides.items():
        if key not in result:
            raise KeyError(f"material override target {key!r} not in materials dict")
        result[key].update(patch)
    return result


# ---------------------------------------------------------------------------
# 2. Ground / wall separation: reassign matching ground-role specs to a
#    different material slot than the walls that used to share it.
# ---------------------------------------------------------------------------
def remap_ground(
    specs: Sequence[Spec],
    *,
    kit: SpecKit,
    source_materials: frozenset,
    role_fragments: Sequence[str],
    target_material: str,
    max_top_y: float,
) -> tuple[list[dict], dict[str, int]]:
    """Reassign every spec whose ``material`` is in ``source_materials`` AND
    whose ``role`` contains one of ``role_fragments`` AND whose top height is
    at or below ``max_top_y`` (i.e. it is a ground-level surface, not a wall
    that happens to share the same stone material) to ``target_material``.

    Root cause this exists to fix: a single very large ground plane sharing
    its material with every wall in the stage (nakaniwa's case: one
    102,400 sq m plane on ``carved_stone``, the same slot the palace walls
    use) reads as one continuous, undifferentiated surface no matter how
    much detail is added on top of it — floor and wall need to be visually
    different materials before any further ground detail can register.
    Returns a new list (originals untouched, matching every other pass in
    this package's "never mutate a spec" contract) and a per-role remap
    count for reporting.
    """
    remapped: list[dict] = []
    changed: dict[str, int] = {}
    for spec in specs:
        if spec["material"] in source_materials and any(
            fragment in spec["role"] for fragment in role_fragments
        ):
            bounds = kit.spec_bounds(spec)
            if bounds[4] <= max_top_y:
                spec = dict(spec)
                spec["material"] = target_material
                changed[spec["role"]] = changed.get(spec["role"], 0) + 1
        remapped.append(spec)
    return remapped, changed


# Nakaniwa's own material-FAMILY split (H5, "four separated families": bright
# cool palace stone / warm ochre town limestone / wet dark granite paving /
# dark bronze ribs instead of candy teal, plus widened foliage tones),
# desaturated once more at H6 (carved_stone). This is the palette-separation
# half of "the palette split" this module promotes -- the ground-role
# reassignment below is the other half; a stage's walls and its ground
# needed to stop sharing one flat tan value before either could register.
# Kept as a named preset for the same reason as the ground/glazing presets
# below: reproduce nakaniwa exactly on request, not a generic default.
NAKANIWA_MATERIAL_FAMILY_OVERRIDE: dict = {
    "ivory_stone": {"color": (0.7, 0.682, 0.636, 1.0), "roughness": (0.19, 0.38), "bump": 0.085},
    "carved_stone": {"color": (0.3, 0.262, 0.208, 1.0), "roughness": (0.62, 0.88), "noiseScale": 0.92, "bump": 0.135},
    "wet_stone": {"color": (0.082, 0.086, 0.09, 1.0), "roughness": (0.09, 0.24), "bump": 0.075},
    "verdigris_bronze": {"color": (0.136, 0.098, 0.052, 1.0), "roughness": (0.27, 0.46), "metallic": 0.88},
    "dark_wood": {"color": (0.112, 0.054, 0.026, 1.0), "roughness": (0.52, 0.7), "bump": 0.1},
    "foliage_dark": {"color": (0.013, 0.072, 0.021, 1.0), "roughness": (0.5, 0.72)},
    "foliage_light": {"color": (0.104, 0.412, 0.072, 1.0), "roughness": (0.4, 0.62)},
    "brass": {"color": (0.436, 0.276, 0.086, 1.0), "roughness": (0.12, 0.29)},
}

# Nakaniwa's own tuned ground recipe (H8's final values: warm mid
# sandstone-granite with strong procedural relief). Kept as a named preset —
# other stages should measure their own value/saturation targets rather than
# reuse these numbers verbatim; see the H7/H8 round-state entries for the
# measured reasoning (a too-neutral first attempt went flatter than the
# control it was trying to improve on).
NAKANIWA_GROUND_MATERIAL_OVERRIDE: dict = {
    "moss_stone": {
        "color": (0.214, 0.190, 0.156, 1.0),
        "roughness": (0.30, 0.72),
        "metallic": 0.0,
        "noiseScale": 3.4,
        "detailScale": 58.0,
        "bump": 0.145,
    },
}
NAKANIWA_GROUND_SOURCE_MATERIALS = frozenset({"carved_stone", "ivory_stone"})
# H7's own two additions on top of the fragment list H6 (the round's first
# ground/wall split attempt) already established; H8 inherits H7's list
# unchanged. Both generations of fragments are kept together here because
# that is the exact set the production chain (H8 -> H13 -> H15 -> pass 4)
# remaps -- dropping the inherited H6 half would silently leave paving
# slabs, canal coping, bridge steps and plaza paving on the wall material.
NAKANIWA_GROUND_ROLE_FRAGMENTS = (
    "paving-slab",
    "canal-carved-coping-line",
    "fine-masonry-cross-joint",
    "depth-break-stone-sill",
    "bridge-shallow-approach-step",
    "bridge-approach-step",
    "bridge-approach-wet-landing",
    "route-inlay-band",
    "route-inlay-fillet",
    "plaza",
    "ground-paving",
    "garden-city-weathered-stone-ground",
    "canal-side-occupied-stone-promenade",
)
NAKANIWA_GROUND_TARGET_MATERIAL = "moss_stone"
NAKANIWA_GROUND_MAX_TOP_Y = 1.25


# ---------------------------------------------------------------------------
# 3. Hero-interior occupancy: give a transmissive/glazed hero mass something
#    behind the glass so a stronger glazing recipe reads as a building
#    rather than staying an empty rib cage.
# ---------------------------------------------------------------------------
def hero_interior_bounds(specs: Sequence[Spec], *, kit: SpecKit, role_token: str) -> tuple:
    """AABB union of every spec whose role contains ``role_token`` (e.g. the
    hero's own group name fragment). Raises if nothing matches — an empty
    hero footprint is a caller bug, not a silent zero-volume interior.
    """
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for spec in specs:
        if role_token not in spec["role"]:
            continue
        b = kit.spec_bounds(spec)
        xs += [b[0], b[3]]
        ys += [b[1], b[4]]
        zs += [b[2], b[5]]
    if not xs:
        raise RuntimeError(f"no specs matched role_token={role_token!r}")
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


@dataclass(frozen=True)
class HeroInteriorLevel:
    y: float
    inset: float


# Nakaniwa's own two-mezzanine conservatory interior (H13). Kept as the
# default so build_hero_interior() reproduces H13 exactly when called with
# no override; other stages' heroes will have their own floor heights.
NAKANIWA_INTERIOR_LEVELS: tuple[HeroInteriorLevel, ...] = (
    HeroInteriorLevel(y=8.4, inset=1.00),
    HeroInteriorLevel(y=15.6, inset=0.74),
)
NAKANIWA_LAMP_LEVELS: tuple[float, ...] = (9.6, 16.8)


def build_hero_interior(
    specs: list,
    bounds: tuple,
    *,
    kit: SpecKit,
    group: str,
    role_prefix: str = "a23-hero-interior",
    planting_role_prefix: Optional[str] = None,
    levels: Sequence[HeroInteriorLevel] = NAKANIWA_INTERIOR_LEVELS,
    lamp_levels: Sequence[float] = NAKANIWA_LAMP_LEVELS,
    mezzanine_material: str = "ivory_stone",
    rail_material: str = "brass",
    column_material: str = "verdigris_bronze",
    lamp_material: str = "warm_glow",
    foliage_materials: tuple[str, str] = ("foliage_dark", "foliage_light"),
    footprint_x: float = 0.30,
    footprint_z: float = 0.26,
    column_inset: float = 0.82,
    planting_count_per_edge: int = 5,
    planting_inset: float = 0.86,
) -> dict:
    """Append occupied mezzanine floors + support columns + edge planting +
    a warm interior light per level, seated inside ``bounds`` (see
    ``hero_interior_bounds``). Mutates ``specs`` in place (matching every
    ``_box``/``_panel``/... primitive's own append-in-place convention) and
    returns per-kind counts for reporting. Reproduces H13's exact geometry
    when called with the nakaniwa defaults above (including H13's own
    inconsistent role naming, kept faithfully rather than "cleaned up":
    mezzanine/rail/column use ``role_prefix`` directly, planting/lamp use
    ``planting_role_prefix`` -- default ``role_prefix`` if not given, so a
    fresh caller gets one consistent prefix unless it deliberately wants
    H13's historical split).
    """
    planting_prefix = role_prefix if planting_role_prefix is None else planting_role_prefix
    x0, y0, z0, x1, y1, z1 = bounds
    cx, cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
    half_x = (x1 - x0) * footprint_x
    half_z = (z1 - z0) * footprint_z
    counts = {"mezzanine": 0, "support": 0, "planting": 0, "rail": 0}

    for level, entry in enumerate(levels):
        y, inset = entry.y, entry.inset
        hx, hz = half_x * inset, half_z * inset
        kit.panel(
            specs, f"{role_prefix}-mezzanine-{level}", mezzanine_material, group,
            ((cx - hx, y, cz - hz), (cx + hx, y, cz - hz),
             (cx + hx, y, cz + hz), (cx - hx, y, cz + hz)), 0.42,
        )
        counts["mezzanine"] += 1
        kit.panel(
            specs, f"{role_prefix}-mezzanine-rail-{level}", rail_material, group,
            ((cx - hx, y + 0.95, cz - hz), (cx + hx, y + 0.95, cz - hz),
             (cx + hx, y + 0.95, cz + hz), (cx - hx, y + 0.95, cz + hz)), 0.10,
        )
        counts["rail"] += 1
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                kit.cylinder(
                    specs, f"{role_prefix}-mezzanine-column-{level}", column_material, group,
                    cx + sx * hx * column_inset, y / 2.0, cz + sz * hz * column_inset,
                    0.34, y, 8,
                )
                counts["support"] += 1
        for index in range(planting_count_per_edge):
            t = (index + 0.5) / planting_count_per_edge
            px = cx - hx + 2.0 * hx * t
            for sz in (-1.0, 1.0):
                material = foliage_materials[(index + level) % 2]
                kit.leaf_cluster(
                    specs, f"{planting_prefix}-planting-{level}", material, group,
                    px, y + 1.35, cz + sz * hz * planting_inset,
                    1.55, 1.15, 26, 71000 + level * 20 + index * 2 + int(sz),
                )
                counts["planting"] += 1

    for level, y in enumerate(lamp_levels):
        kit.cylinder(specs, f"{planting_prefix}-lamp-{level}", lamp_material, group, cx, y, cz, 0.55, 0.70, 10)
        counts["support"] += 1

    return counts


# Nakaniwa's own glazing recipe (H13): the stock dirty_glass/glass_highlight
# transmission was tuned to render as sky at ~100 m; this makes it read.
NAKANIWA_GLAZING_MATERIAL_OVERRIDE: dict = {
    "dirty_glass": {
        "color": (0.075, 0.168, 0.176, 0.46),
        "roughness": (0.045, 0.16),
        "transmission": 0.68,
        "alpha": 0.46,
        "emission": (0.0, 0.012, 0.016, 1.0),
        "emissionStrength": 0.03,
    },
    "glass_highlight": {
        "color": (0.128, 0.300, 0.312, 0.26),
        "roughness": (0.025, 0.095),
        "transmission": 0.70,
        "alpha": 0.26,
    },
}


# ---------------------------------------------------------------------------
# 4. Near-field volumetric thickening: give near ``leaf_cluster`` specs
#    enough density (plus a nested, offset, differently-toned companion) to
#    read as a canopy volume instead of a single flat card.
# ---------------------------------------------------------------------------
def thicken_near_volumetrics(
    specs: Sequence[Spec],
    *,
    kit: SpecKit,
    camera_point: Sequence[float],
    near_range_m: float = 10.5,
    near_leaf_count: int = 40,
    companion_leaf_count: int = 26,
    companion_scale: float = 0.72,
    companion_offset: float = 0.34,
    companion_group: Optional[str] = None,
    companion_role_suffix: str = "-inner-layer",
) -> tuple[list[dict], dict]:
    """Raise ``leaves`` on every ``leaf_cluster`` spec within
    ``near_range_m`` of ``camera_point`` to at least ``near_leaf_count``, and
    add a second, smaller (``companion_scale``), offset
    (``companion_offset``), tonally-opposite (foliage_light<->foliage_dark)
    cluster nested inside each one. The overlap between the two clusters —
    not the raised leaf count alone — is what reads as canopy depth rather
    than a denser single card; see the H15 round-state entry for the
    measured before/after (strict green-dominance foliage pixel count, not
    the loose HSV count later found to inflate it — see measure.py).
    """
    out: list[dict] = []
    thickened = 0
    companions = 0
    for spec in specs:
        if spec["kind"] != "leaf_cluster":
            out.append(spec)
            continue
        cx, cy, cz = spec_center(kit, spec)
        distance = math.dist((cx, cy, cz), tuple(camera_point))
        if distance > near_range_m:
            out.append(spec)
            continue
        dense = dict(spec)
        dense["leaves"] = max(int(spec["leaves"]), near_leaf_count)
        out.append(dense)
        thickened += 1

        companion = dict(spec)
        companion["group"] = companion_group if companion_group is not None else spec["group"]
        companion["role"] = f"{spec['role']}{companion_role_suffix}"
        companion["leaves"] = companion_leaf_count
        companion["radius"] = float(spec["radius"]) * companion_scale
        companion["height"] = float(spec["height"]) * companion_scale
        companion["seed"] = int(spec["seed"]) * 7 + 13
        companion["y"] = float(spec["y"]) + companion_offset
        companion["x"] = float(spec["x"]) + companion_offset * 0.6
        companion["material"] = (
            "foliage_dark" if spec["material"] == "foliage_light" else "foliage_light"
        )
        out.append(companion)
        companions += 1

    return out, {
        "thickened": thickened, "companionsAdded": companions,
        "nearRangeM": near_range_m, "nearLeafCount": near_leaf_count,
    }
