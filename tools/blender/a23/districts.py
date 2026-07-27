"""A23 district placement: scanline lot packing, plain/articulated terrace
blocks, contract-derived window rhythm, and occlusion-aware articulation
priority.

Promoted from the private study under
``/private/tmp/hibana-blender/claude-a23-districts3/district_infill_v3.py``,
the fourth revision of the district-infill planner (three prior rounds'
findings are folded in — see the round-state log for h19/h23/h24/h25):

  - h19: the map was 17.11% built against a 24.5-34% contract, and every
    player spawn stood in empty terrain (measure.py's
    ``built_footprint_report`` is the fix that first quantified this).
  - h23: a fixed small column count clustered all of a facade's windows into
    one narrow band, reading as a signboard. The fix (below) derives column
    count from a fixed bay pitch over the wall's own usable span, so wider
    walls legitimately get denser fenestration.
  - h24: end walls (the block's short sides) were never windowed regardless
    of camera visibility; now tested and articulated like any other face.
  - h25: articulation priority was ranked by frustum containment alone,
    which does not distinguish "onscreen" from "onscreen but hidden behind
    this camera's own hero colonnade" — a camera standing inside a hero
    structure sees mostly its own hero, not the district beyond it. The fix
    reuses ``reclamation.build_occlusion_grid`` (the exact occlusion test
    the reclamation passes already trust) against the reconciled base as
    occluder mass, so a block only gets full articulation spend if it is
    genuinely visible, not merely inside a frustum.

Camera contract
----------------
``plan_district`` takes the safety/visibility cameras as an explicit
``cameras`` parameter (the same "however many cameras this stage defines"
contract reclamation.py uses) plus an optional ``focus_camera`` — the one
camera whose otherwise-empty view first exposed the built-footprint defect
(nakaniwa's GardenBridge camera) and therefore gets first claim on site
priority. A stage with no such asymmetric "problem view" can omit it and
every site ranks purely on general multi-camera visibility.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from tools.blender.a23 import reclamation
from tools.blender.a23.kit import Spec, SpecKit, frame_cells


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DistrictConfig:
    map_half_m: float = 160.0
    cell_m: float = 2.0
    map_edge_margin_m: float = 3.0
    existing_mass_margin_m: float = 2.0
    road_placement_margin_m: float = 2.0
    substantial_extent_m: float = 0.30
    ground_role_tokens: tuple = (
        "weathered-stone-ground", "ground-behind-canal", "ground-beyond-canal",
        "ground-left-of-canal", "ground-right-of-canal", "canonical-road",
    )

    row_depth_m: float = 18.0
    street_gap_m: float = 14.0
    alley_gap_m: float = 6.0
    scan_step_m: float = 2.0
    width_choices: tuple = (30.0, 38.0, 44.0, 50.0)
    height_choices: tuple = (5.5, 6.5, 7.5, 8.5, 9.5)
    focus_height_choices: tuple = (24.0, 27.0)

    base_h: float = 0.6
    roof_h: float = 1.1
    ground_top_y: float = -0.08

    wall_materials: tuple = ("ivory_stone", "carved_stone", "wet_stone", "moss_stone")
    roof_materials: tuple = ("verdigris_bronze", "brass")
    base_materials: tuple = ("carved_stone", "wet_stone")
    window_materials: tuple = ("dirty_glass", "warm_glow", "glass_highlight")
    frame_material_preference: tuple = ("carved_stone", "wet_stone", "moss_stone", "ivory_stone")
    cornice_material: str = "brass"
    ledge_material: str = "brass"
    ridge_material: str = "brass"

    # h23 aggregate-failure fix (see reclamation.py's own note on the same
    # defect class): a 0.75 m cornice overhang was safe when at most 4 of 18
    # blocks were ever articulated, but once every alley-adjacent pair can
    # have both cornices overhanging at once, the worst-case gap must be
    # checked against the contract floor directly. 0.35 m keeps a 0.30 m
    # cushion above a 5.0 m alley floor at the 6.0 m nominal gap used here.
    cornice_overhang_m: float = 0.35
    cornice_h: float = 0.65
    recess_depth_m: float = 0.5
    parapet_height_choices: tuple = (0.9, 1.3)
    roof_forms: tuple = ("pitched", "parapet")

    player_spawn_clearance_m: float = 30.0
    bot_spawn_clearance_m: float = 8.0
    road_half_m: float = 8.0
    road_top_limit_m: float = 0.35

    visibility_px_threshold: float = 4.0
    margin_reserve_triangles: int = 300
    occlusion_depth_margin_m: float = 1.0

    always_protect_groups: frozenset = field(default_factory=frozenset)
    always_protect_role_prefix: Optional[str] = None

    contract_alley_band_m: tuple = (5.0, 9.0)
    contract_street_band_m: tuple = (10.0, 18.0)

    @property
    def base_bottom_y(self) -> float:
        return self.ground_top_y - 0.10

    @property
    def row_pitch_z(self) -> float:
        return self.row_depth_m + self.street_gap_m


@dataclass(frozen=True)
class WindowRhythm:
    """A block's window grid, derived from the stage contract rather than
    fit to the wall. ``floor_to_floor_m``/``sill_height_m`` are
    contract-informed choices (nakaniwa: the 2.8-4.0 m floor-to-floor band
    and the 0.9-1.2 m railing band respectively); ``opening_h_m`` is
    *exactly* derived from them (see the property below) so a caller cannot
    accidentally desync the two. ``opening_w_m`` is deliberately kept below
    a door-width band so a window can never read as a door at any distance.
    """

    floor_to_floor_m: float = 3.2
    sill_height_m: float = 1.0
    head_clearance_m: float = 0.4
    opening_w_m: float = 1.5
    mullion_w_m: float = 0.4
    bay_pitch_target_m: float = 7.5
    edge_margin_m: float = 2.0
    min_columns: int = 2
    end_wall_columns: int = 1

    @property
    def opening_h_m(self) -> float:
        return self.floor_to_floor_m - self.sill_height_m - self.head_clearance_m


# ---------------------------------------------------------------------------
# Exclusion grid / scanline site enumeration
# ---------------------------------------------------------------------------
def _cell_range(cfg: DistrictConfig, lo: float, hi: float, margin: float, grid_n: int) -> tuple[int, int]:
    a = int(math.floor((lo - margin + cfg.map_half_m) / cfg.cell_m))
    b = int(math.ceil((hi + margin + cfg.map_half_m) / cfg.cell_m))
    return max(0, a), min(grid_n, b)


def build_exclusion_grid(
    existing_specs: Sequence[Spec],
    *,
    kit: SpecKit,
    canonical_roads: Sequence[Mapping[str, object]],
    player_spawns: Sequence[Sequence[float]],
    bot_spawns: Sequence[Sequence[float]],
    config: DistrictConfig = DistrictConfig(),
):
    grid_n = int(round(2 * config.map_half_m / config.cell_m))
    grid = [[False] * grid_n for _ in range(grid_n)]

    def mark(x0, x1, z0, z1, margin):
        ix0, ix1 = _cell_range(config, x0, x1, margin, grid_n)
        iz0, iz1 = _cell_range(config, z0, z1, margin, grid_n)
        for iz in range(iz0, iz1):
            row = grid[iz]
            for ix in range(ix0, ix1):
                row[ix] = True

    for spec in existing_specs:
        role = str(spec["role"])
        if any(token in role for token in config.ground_role_tokens):
            continue
        group = str(spec["group"])
        always = (
            group in config.always_protect_groups
            or (config.always_protect_role_prefix is not None and group.startswith(config.always_protect_role_prefix))
            or spec["material"] == "water"
        )
        b = kit.spec_bounds(spec)
        if not always:
            extent = b[4] - b[1]
            if extent < config.substantial_extent_m:
                continue
        mark(b[0], b[3], b[2], b[5], config.existing_mass_margin_m)

    for road in canonical_roads:
        rb = road["bounds"]
        mark(rb["minX"], rb["maxX"], rb["minZ"], rb["maxZ"], config.road_placement_margin_m)

    spawn_safety = config.cornice_overhang_m + 0.5
    for (sx, _sy, sz) in player_spawns:
        mark(sx - config.player_spawn_clearance_m, sx + config.player_spawn_clearance_m,
             sz - config.player_spawn_clearance_m, sz + config.player_spawn_clearance_m, spawn_safety)
    for (sx, _sy, sz) in bot_spawns:
        mark(sx - config.bot_spawn_clearance_m, sx + config.bot_spawn_clearance_m,
             sz - config.bot_spawn_clearance_m, sz + config.bot_spawn_clearance_m, spawn_safety)

    return grid, grid_n


def _lot_clear(cfg: DistrictConfig, grid, grid_n, cx, cz, w, d) -> bool:
    x0, x1 = cx - w / 2.0, cx + w / 2.0
    z0, z1 = cz - d / 2.0, cz + d / 2.0
    if x0 < -cfg.map_half_m + cfg.map_edge_margin_m or x1 > cfg.map_half_m - cfg.map_edge_margin_m:
        return False
    if z0 < -cfg.map_half_m + cfg.map_edge_margin_m or z1 > cfg.map_half_m - cfg.map_edge_margin_m:
        return False
    ix0, ix1 = _cell_range(cfg, x0, x1, 0.0, grid_n)
    iz0, iz1 = _cell_range(cfg, z0, z1, 0.0, grid_n)
    for iz in range(iz0, iz1):
        row = grid[iz]
        for ix in range(ix0, ix1):
            if row[ix]:
                return False
    return True


def _occupy(cfg: DistrictConfig, grid, grid_n, cx, cz, w, d, margin=0.0):
    x0, x1 = cx - w / 2.0, cx + w / 2.0
    z0, z1 = cz - d / 2.0, cz + d / 2.0
    ix0, ix1 = _cell_range(cfg, x0, x1, margin, grid_n)
    iz0, iz1 = _cell_range(cfg, z0, z1, margin, grid_n)
    for iz in range(iz0, iz1):
        row = grid[iz]
        for ix in range(ix0, ix1):
            row[ix] = True


def _scanline_sites(cfg: DistrictConfig, grid, grid_n):
    sites = []
    z = -cfg.map_half_m + cfg.map_edge_margin_m + cfg.row_depth_m / 2.0
    row_index = 0
    while z <= cfg.map_half_m - cfg.map_edge_margin_m - cfg.row_depth_m / 2.0:
        x = -cfg.map_half_m + cfg.map_edge_margin_m
        width_cycle = row_index
        placed_in_row = 0
        while x <= cfg.map_half_m - cfg.map_edge_margin_m:
            w = cfg.width_choices[width_cycle % len(cfg.width_choices)]
            cx = x + w / 2.0
            if cx + w / 2.0 > cfg.map_half_m - cfg.map_edge_margin_m:
                break
            if _lot_clear(cfg, grid, grid_n, cx, z, w, cfg.row_depth_m):
                sites.append({"row": row_index, "index": placed_in_row, "cx": cx, "cz": z, "w": w, "d": cfg.row_depth_m})
                x = cx + w / 2.0 + cfg.alley_gap_m
                width_cycle += 1
                placed_in_row += 1
            else:
                x += cfg.scan_step_m
        z += cfg.row_pitch_z
        row_index += 1
    return sites


# ---------------------------------------------------------------------------
# Camera scoring
# ---------------------------------------------------------------------------
def _camera_forward_xz(camera: Mapping[str, object]) -> tuple[float, float]:
    loc, tgt = camera["location"], camera["target"]
    dx, dz = tgt[0] - loc[0], tgt[2] - loc[2]
    length = math.hypot(dx, dz) or 1.0
    return dx / length, dz / length


def _half_fov_rad(camera: Mapping[str, object]) -> float:
    sensor = float(camera.get("sensorWidthMm", 36.0))
    lens = float(camera["lensMm"])
    return math.atan(sensor / (2.0 * lens))


def frustum_score(cx: float, cz: float, camera: Mapping[str, object], *, max_range_m: float) -> float:
    loc = camera["location"]
    fx, fz = _camera_forward_xz(camera)
    dx, dz = cx - loc[0], cz - loc[2]
    dist = math.hypot(dx, dz)
    if dist < 1e-6 or dist > max_range_m:
        return -1.0
    cos_angle = (dx * fx + dz * fz) / dist
    half_fov = _half_fov_rad(camera)
    if cos_angle < math.cos(half_fov * 1.35):
        return -1.0
    return cos_angle * (1.0 - dist / max_range_m)


def _best_frustum_score(cx: float, cz: float, cameras: Sequence[Mapping[str, object]], *, max_range_m: float) -> float:
    return max(frustum_score(cx, cz, camera, max_range_m=max_range_m) for camera in cameras)


# ---------------------------------------------------------------------------
# Terrace block geometry
# ---------------------------------------------------------------------------
def _terrace_block(specs, *, kit: SpecKit, cfg: DistrictConfig, group: str, role: str,
                    cx: float, cz: float, w: float, d: float, h: float,
                    base_material: str, wall_material: str, roof_material: str,
                    detailed: bool, chamfer_base: bool = False) -> None:
    base_center_y = cfg.base_bottom_y + cfg.base_h / 2.0
    if chamfer_base:
        kit.chamfer_box(specs, f"{role}-base-plinth", base_material, group,
                         cx, base_center_y, cz, w + 0.5, cfg.base_h, d + 0.5,
                         min(0.16, 0.45 * cfg.base_h), 1)
    else:
        kit.box(specs, f"{role}-base-plinth", base_material, group,
                cx, base_center_y, cz, w + 0.5, cfg.base_h, d + 0.5)
    wall_bottom = cfg.base_bottom_y + cfg.base_h
    kit.box(specs, f"{role}-wall-mass", wall_material, group, cx, wall_bottom + h / 2.0, cz, w, h, d)
    wall_top = wall_bottom + h
    kit.box(specs, f"{role}-roof-band", roof_material, group,
            cx, wall_top + cfg.roof_h / 2.0, cz, w + 0.35, cfg.roof_h, d + 0.35)
    if not detailed:
        return
    kit.box(specs, f"{role}-cornice", cfg.cornice_material, group,
            cx, wall_top - 0.10, cz, w + 0.12, 0.20, d + 0.12)


def _block_triangle_cost(kit: SpecKit, cfg: DistrictConfig, detailed: bool) -> int:
    specs: list[dict] = []
    _terrace_block(specs, kit=kit, cfg=cfg, group="a23-districts-cost-probe", role="cost-probe",
                    cx=0.0, cz=0.0, w=44.0, d=18.0, h=7.0,
                    base_material="carved_stone", wall_material="ivory_stone", roof_material="brass",
                    detailed=detailed, chamfer_base=detailed)
    return kit.estimated_triangles(specs)


def _pitched_roof(specs, *, kit: SpecKit, cfg: DistrictConfig, group: str, role: str,
                   cx: float, cz: float, base_y: float, w: float, d: float, rise: float,
                   material: str, ridge_along_x: bool) -> None:
    if ridge_along_x:
        kit.panel(specs, f"{role}-roof-slope-a", material, group,
                  ((cx - w / 2, base_y, cz - d / 2), (cx + w / 2, base_y, cz - d / 2),
                   (cx + w / 2, base_y + rise, cz), (cx - w / 2, base_y + rise, cz)), 0.10)
        kit.panel(specs, f"{role}-roof-slope-b", material, group,
                  ((cx - w / 2, base_y + rise, cz), (cx + w / 2, base_y + rise, cz),
                   (cx + w / 2, base_y, cz + d / 2), (cx - w / 2, base_y, cz + d / 2)), 0.10)
        kit.sweep(specs, f"{role}-roof-ridge", cfg.ridge_material, group,
                  ((cx - w / 2 - 0.12, base_y + rise, cz), (cx + w / 2 + 0.12, base_y + rise, cz)), 0.035, 6)
    else:
        kit.panel(specs, f"{role}-roof-slope-a", material, group,
                  ((cx - w / 2, base_y, cz - d / 2), (cx, base_y + rise, cz - d / 2),
                   (cx, base_y + rise, cz + d / 2), (cx - w / 2, base_y, cz + d / 2)), 0.10)
        kit.panel(specs, f"{role}-roof-slope-b", material, group,
                  ((cx, base_y + rise, cz - d / 2), (cx + w / 2, base_y, cz - d / 2),
                   (cx + w / 2, base_y, cz + d / 2), (cx, base_y + rise, cz + d / 2)), 0.10)
        kit.sweep(specs, f"{role}-roof-ridge", cfg.ridge_material, group,
                  ((cx, base_y + rise, cz - d / 2 - 0.12), (cx, base_y + rise, cz + d / 2 + 0.12)), 0.035, 6)


def _parapet_roof(specs, *, kit: SpecKit, group: str, role: str, cx: float, cz: float,
                   base_y: float, w: float, d: float, parapet_h: float, material: str) -> None:
    kit.box(specs, f"{role}-roof-deck", material, group, cx, base_y + 0.06, cz, w + 0.2, 0.12, d + 0.2)
    kit.box(specs, f"{role}-roof-parapet", material, group,
            cx, base_y + 0.12 + parapet_h / 2.0, cz, w + 0.3, parapet_h, d + 0.3)


def _contrasting_frame_material(wall_material: str, preference_order: Sequence[str]) -> str:
    for material in preference_order:
        if material != wall_material:
            return material
    return preference_order[0] if preference_order else wall_material


def _window_columns_for_span(span: float, *, rhythm: WindowRhythm) -> int:
    usable = span - 2 * rhythm.edge_margin_m
    if usable < rhythm.opening_w_m:
        return 0
    gaps = max(1, round(usable / rhythm.bay_pitch_target_m))
    return max(rhythm.min_columns, gaps + 1)


def _floor_count_for(h: float, *, rhythm: WindowRhythm) -> int:
    return max(1, int(h // rhythm.floor_to_floor_m))


def _window_wall_grid(specs, *, kit: SpecKit, cfg: DistrictConfig, rhythm: WindowRhythm, group: str,
                       role: str, span_center: float, wall_bottom: float, span: float, h: float,
                       face_pos: float, recessed_face_pos: float, facade_side: float,
                       frame_material: str, window_material: str, axis: str, columns: int) -> None:
    """One articulated wall face: a recessed grid of window openings, one
    ROW per storey, with ``columns`` openings spread EVENLY across
    (span - 2*edge_margin_m) rather than clustered in one small band (see
    module docstring, h24). Sill/lintel/drip-ledge bands are continuous
    across the full spread span (a box costs 12 triangles at any size, so
    this stays a flat 3-box cost regardless of span or column count).
    """
    n_floors = _floor_count_for(h, rhythm=rhythm)
    usable = span - 2 * rhythm.edge_margin_m
    step = usable / (columns - 1) if columns > 1 else 0.0
    start = span_center - usable / 2.0
    shell_d = cfg.recess_depth_m
    shell_pos = face_pos - facade_side * (shell_d / 2.0)
    glazing_pos = recessed_face_pos + facade_side * 0.05
    band_span = usable + rhythm.opening_w_m
    if axis == "z":
        side_tag = "n" if facade_side > 0 else "s"
    else:
        side_tag = "e" if facade_side > 0 else "w"

    for floor in range(n_floors):
        row_bottom = wall_bottom + rhythm.sill_height_m + floor * rhythm.floor_to_floor_m
        row_top = row_bottom + rhythm.opening_h_m
        row_cy = (row_bottom + row_top) / 2.0
        frow = f"{role}-win-{side_tag}-f{floor}"

        if axis == "z":
            kit.box(specs, f"{frow}-sill", frame_material, group, span_center, row_bottom - 0.07, shell_pos, band_span, 0.14, shell_d)
            kit.box(specs, f"{frow}-lintel", frame_material, group, span_center, row_top + 0.07, shell_pos, band_span, 0.14, shell_d)
            kit.box(specs, f"{frow}-ledge", cfg.ledge_material, group,
                    span_center, row_bottom - 0.10, face_pos + facade_side * 0.12, band_span, 0.10, 0.24)
        else:
            kit.box(specs, f"{frow}-sill", frame_material, group, shell_pos, row_bottom - 0.07, span_center, shell_d, 0.14, band_span)
            kit.box(specs, f"{frow}-lintel", frame_material, group, shell_pos, row_top + 0.07, span_center, shell_d, 0.14, band_span)
            kit.box(specs, f"{frow}-ledge", cfg.ledge_material, group,
                    face_pos + facade_side * 0.12, row_bottom - 0.10, span_center, 0.24, 0.10, band_span)

        for i in range(columns):
            pos = start + i * step if columns > 1 else span_center
            if axis == "z":
                kit.box(specs, f"{frow}-glazing-{i}", window_material, group,
                        pos, row_cy, glazing_pos, rhythm.opening_w_m * 0.92, rhythm.opening_h_m * 0.88, 0.08)
            else:
                kit.box(specs, f"{frow}-glazing-{i}", window_material, group,
                        glazing_pos, row_cy, pos, 0.08, rhythm.opening_h_m * 0.88, rhythm.opening_w_m * 0.92)


def _terrace_block_articulated(specs, *, kit: SpecKit, cfg: DistrictConfig, rhythm: WindowRhythm,
                                group: str, role: str, cx: float, cz: float, w: float, d: float, h: float,
                                base_material: str, wall_material: str, roof_material: str, window_material: str,
                                roof_form: str, roof_param: float, ridge_along_x: bool,
                                facade_sides: tuple, end_wall_sides: tuple = ()) -> None:
    base_center_y = cfg.base_bottom_y + cfg.base_h / 2.0
    kit.box(specs, f"{role}-base-plinth", base_material, group, cx, base_center_y, cz, w + 0.5, cfg.base_h, d + 0.5)

    wall_bottom = cfg.base_bottom_y + cfg.base_h
    wall_top = wall_bottom + h

    if len(facade_sides) >= 2:
        core_d = d - 2 * cfg.recess_depth_m
        core_cz = cz
    else:
        core_d = d - cfg.recess_depth_m
        core_cz = cz - facade_sides[0] * (cfg.recess_depth_m / 2.0) if facade_sides else cz

    if len(end_wall_sides) >= 2:
        core_w = w - 2 * cfg.recess_depth_m
        core_cx = cx
    elif end_wall_sides:
        core_w = w - cfg.recess_depth_m
        core_cx = cx - end_wall_sides[0] * (cfg.recess_depth_m / 2.0)
    else:
        core_w = w
        core_cx = cx

    kit.box(specs, f"{role}-wall-core", wall_material, group, core_cx, wall_bottom + h / 2.0, core_cz, core_w, h, core_d)

    frame_material = _contrasting_frame_material(wall_material, cfg.frame_material_preference)
    for facade_side in facade_sides:
        face_z = cz + facade_side * (d / 2.0)
        recessed_face_z = face_z - facade_side * cfg.recess_depth_m
        side_role = f"{role}-{'n' if facade_side > 0 else 's'}"
        _window_wall_grid(specs, kit=kit, cfg=cfg, rhythm=rhythm, group=group, role=side_role,
                           span_center=cx, wall_bottom=wall_bottom, span=w, h=h, face_pos=face_z,
                           recessed_face_pos=recessed_face_z, facade_side=facade_side,
                           frame_material=frame_material, window_material=window_material,
                           axis="z", columns=_window_columns_for_span(w, rhythm=rhythm))
    for end_side in end_wall_sides:
        face_x = cx + end_side * (w / 2.0)
        recessed_face_x = face_x - end_side * cfg.recess_depth_m
        side_role = f"{role}-{'e' if end_side > 0 else 'w'}"
        _window_wall_grid(specs, kit=kit, cfg=cfg, rhythm=rhythm, group=group, role=side_role,
                           span_center=cz, wall_bottom=wall_bottom, span=d, h=h, face_pos=face_x,
                           recessed_face_pos=recessed_face_x, facade_side=end_side,
                           frame_material=frame_material, window_material=window_material,
                           axis="x", columns=rhythm.end_wall_columns)

    kit.box(specs, f"{role}-cornice", cfg.cornice_material, group,
            cx, wall_top + cfg.cornice_h / 2.0, cz, w + 2 * cfg.cornice_overhang_m, cfg.cornice_h, d + 2 * cfg.cornice_overhang_m)

    roof_base_y = wall_top + cfg.cornice_h
    if roof_form == "pitched":
        _pitched_roof(specs, kit=kit, cfg=cfg, group=group, role=f"{role}-roof", cx=cx, cz=cz,
                      base_y=roof_base_y, w=w, d=d, rise=roof_param, material=roof_material, ridge_along_x=ridge_along_x)
    else:
        _parapet_roof(specs, kit=kit, group=group, role=f"{role}-roof", cx=cx, cz=cz,
                      base_y=roof_base_y, w=w, d=d, parapet_h=roof_param, material=roof_material)


_ARTICULATED_COST_CACHE: dict[tuple, int] = {}


def _articulated_triangle_cost(kit: SpecKit, cfg: DistrictConfig, rhythm: WindowRhythm,
                                w: float, h: float, roof_form: str, facade_sides: tuple,
                                end_wall_sides: tuple = ()) -> int:
    key = (id(kit), w, h, roof_form, facade_sides, end_wall_sides)
    cached = _ARTICULATED_COST_CACHE.get(key)
    if cached is not None:
        return cached
    specs: list[dict] = []
    _terrace_block_articulated(
        specs, kit=kit, cfg=cfg, rhythm=rhythm, group="a23-districts-cost-probe", role="cost-probe",
        cx=0.0, cz=0.0, w=w, d=cfg.row_depth_m, h=h, base_material="carved_stone",
        wall_material="ivory_stone", roof_material="brass", window_material="dirty_glass",
        roof_form=roof_form, roof_param=2.0 if roof_form == "pitched" else 1.0,
        ridge_along_x=True, facade_sides=facade_sides, end_wall_sides=end_wall_sides,
    )
    cost = kit.estimated_triangles(specs)
    _ARTICULATED_COST_CACHE[key] = cost
    return cost


# ---------------------------------------------------------------------------
# Occlusion-aware visibility (h25): reuses reclamation.build_occlusion_grid.
# ---------------------------------------------------------------------------
def _envelope_height_estimate(h: float, *, cfg: DistrictConfig) -> float:
    return cfg.base_h + h + cfg.cornice_h + cfg.roof_h + 3.2


def build_occlusion_grids_for_cameras(
    kit: SpecKit, cameras: Sequence[Mapping[str, object]], occluder_specs: Optional[Sequence[Spec]],
    *, reclamation_config: reclamation.ReclamationConfig = reclamation.ReclamationConfig(),
) -> dict:
    """One ``reclamation.build_occlusion_grid`` per camera, built once and
    reused for every candidate site. ``occluder_specs`` should be the
    reconciled reclamation-chain base (hero geometry + surviving
    background); ``None`` disables occlusion-awareness (frustum-only,
    matching the pre-h25 behaviour).
    """
    if not occluder_specs:
        return {}
    return {
        str(camera["name"]): reclamation.build_occlusion_grid(kit, camera, occluder_specs, config=reclamation_config)
        for camera in cameras
    }


def _onscreen_px_and_occluded(kit: SpecKit, spec: Spec, camera: Mapping[str, object],
                               grid: Optional[Mapping], *, resolution: tuple, px_threshold: float,
                               occlusion_depth_margin_m: float) -> tuple[bool, float, float, bool]:
    aspect = resolution[0] / resolution[1]
    frame = kit.project_spec_frame(spec, camera, aspect)
    if frame is None:
        return False, 0.0, 0.0, False
    x0, y0, x1, y1 = frame["bounds"]
    onscreen = not (x1 <= 0.0 or y1 <= 0.0 or x0 >= 1.0 or y0 >= 1.0)
    if not onscreen:
        return False, 0.0, 0.0, False
    px_w = max(0.0, min(x1, 1.0) - max(x0, 0.0)) * resolution[0]
    px_h = max(0.0, min(y1, 1.0) - max(y0, 0.0)) * resolution[1]
    if px_w < px_threshold or px_h < px_threshold:
        return onscreen, px_w, px_h, False
    if not grid:
        return onscreen, px_w, px_h, False
    near_depth = float(frame["nearDepthM"])
    cells = list(frame_cells(frame["bounds"], 160, 90))
    if not cells:
        return onscreen, px_w, px_h, False
    covered = sum(
        1 for cell in cells
        if (occ := grid.get(cell)) is not None and occ + occlusion_depth_margin_m < near_depth
    )
    return onscreen, px_w, px_h, covered == len(cells)


def visible_facade_sides(cx: float, cz: float, w: float, d: float, h: float, *, kit: SpecKit,
                          cfg: DistrictConfig, cameras: Sequence[Mapping[str, object]],
                          occlusion_grids: Optional[dict] = None, resolution: tuple = (1280, 720),
                          px_threshold: Optional[float] = None) -> dict:
    """Real multi-camera projection+occlusion test for a block's two
    z-facing facades: which side(s) actually face a camera that resolves
    the envelope at more than a few pixels AND is not occluded. Returns both
    the occlusion-aware ``camerasVisibleIn``/``facadeSides`` and the
    frustum-only count, so the gap between them (what occlusion-awareness
    caught) can be reported.
    """
    px_threshold = cfg.visibility_px_threshold if px_threshold is None else px_threshold
    envelope_h = _envelope_height_estimate(h, cfg=cfg)
    spec = {
        "kind": "box", "x": cx, "y": cfg.ground_top_y + envelope_h / 2.0, "z": cz,
        "w": w + 2 * cfg.cornice_overhang_m, "h": envelope_h, "d": d + 2 * cfg.cornice_overhang_m,
    }
    sides: set = set()
    cams_hit: list[str] = []
    frustum_only_hits = 0
    best_px = 0.0
    for camera in cameras:
        grid = occlusion_grids.get(str(camera["name"])) if occlusion_grids else None
        onscreen, px_w, px_h, occluded = _onscreen_px_and_occluded(
            kit, spec, camera, grid, resolution=resolution, px_threshold=px_threshold,
            occlusion_depth_margin_m=cfg.occlusion_depth_margin_m)
        if onscreen and px_w >= px_threshold and px_h >= px_threshold:
            frustum_only_hits += 1
        if not onscreen or occluded or px_w < px_threshold or px_h < px_threshold:
            continue
        side = 1.0 if camera["location"][2] >= cz else -1.0
        sides.add(side)
        cams_hit.append(str(camera["name"]))
        best_px = max(best_px, px_w)
    return {
        "facadeSides": tuple(sorted(sides)), "camerasVisibleIn": len(cams_hit),
        "camerasFrustumOnly": frustum_only_hits, "cameraNames": cams_hit,
        "bestOnscreenPxW": round(best_px, 1),
    }


def visible_end_wall_sides(cx: float, cz: float, w: float, d: float, h: float, *, kit: SpecKit,
                            cfg: DistrictConfig, cameras: Sequence[Mapping[str, object]],
                            occlusion_grids: Optional[dict] = None, resolution: tuple = (1280, 720),
                            px_threshold: Optional[float] = None) -> dict:
    """The same test as ``visible_facade_sides`` for a block's d-wide
    x-normal END walls (h24: these were previously never windowed
    regardless of camera visibility).
    """
    px_threshold = cfg.visibility_px_threshold if px_threshold is None else px_threshold
    envelope_h = _envelope_height_estimate(h, cfg=cfg)
    sides: set = set()
    cams_hit: list[str] = []
    frustum_only_hits = 0
    best_px = 0.0
    for end_side, sx in ((-1.0, cx - w / 2.0), (1.0, cx + w / 2.0)):
        spec = {"kind": "box", "x": sx, "y": cfg.ground_top_y + envelope_h / 2.0, "z": cz, "w": 0.2, "h": envelope_h, "d": d}
        side_hit = False
        for camera in cameras:
            grid = occlusion_grids.get(str(camera["name"])) if occlusion_grids else None
            onscreen, px_w, px_h, occluded = _onscreen_px_and_occluded(
                kit, spec, camera, grid, resolution=resolution, px_threshold=px_threshold,
                occlusion_depth_margin_m=cfg.occlusion_depth_margin_m)
            if onscreen and px_w >= px_threshold and px_h >= px_threshold:
                frustum_only_hits += 1
            if not onscreen or occluded or px_w < px_threshold or px_h < px_threshold:
                continue
            side_hit = True
            cams_hit.append(str(camera["name"]))
            best_px = max(best_px, px_w)
        if side_hit:
            sides.add(end_side)
    return {
        "endWallSides": tuple(sorted(sides)), "camerasVisibleIn": len(cams_hit),
        "camerasFrustumOnly": frustum_only_hits, "cameraNames": cams_hit,
        "bestOnscreenPxW": round(best_px, 1),
    }


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------
def plan_district(
    existing_specs: Sequence[Spec], *, tri_budget: int, kit: SpecKit,
    canonical_roads: Sequence[Mapping[str, object]], player_spawns: Sequence[Sequence[float]],
    bot_spawns: Sequence[Sequence[float]], cameras: Sequence[Mapping[str, object]],
    config: DistrictConfig = DistrictConfig(), rhythm: WindowRhythm = WindowRhythm(),
    group: str = "a23-districts-townscape-infill", role_prefix: str = "a23-districts-terrace-block",
    focus_camera: Optional[Mapping[str, object]] = None, focus_max_range_m: float = 140.0,
    any_camera_max_range_m: float = 140.0, occluder_specs: Optional[Sequence[Spec]] = None,
    resolution: tuple = (1280, 720),
) -> dict:
    """Place terrace blocks by scanline packing over ``existing_specs``'
    exclusion footprint, then rank every reserved site by measured,
    occlusion-aware multi-camera visibility and spend ``tri_budget`` on full
    articulation (recessed window grid, cornice, roof form) in that order.
    ``occluder_specs`` (the reconciled reclamation-chain base) makes
    articulation priority occlusion-aware rather than frustum-only —
    passing ``None`` reproduces the pre-h25 frustum-only behaviour.
    ``focus_camera`` (nakaniwa: GardenBridge) is optional first-priority
    weighting for the one view that first exposed an empty built footprint;
    omit it for a stage with no such asymmetric problem view.
    """
    grid, grid_n = build_exclusion_grid(
        existing_specs, kit=kit, canonical_roads=canonical_roads,
        player_spawns=player_spawns, bot_spawns=bot_spawns, config=config,
    )
    occlusion_grids = build_occlusion_grids_for_cameras(kit, cameras, occluder_specs)

    candidates = []
    for site in _scanline_sites(config, grid, grid_n):
        cx, cz, w, d = site["cx"], site["cz"], site["w"], site["d"]
        candidates.append({
            "i": site["index"], "j": site["row"], "cx": cx, "cz": cz, "w": w, "d": d,
            "focusScore": frustum_score(cx, cz, focus_camera, max_range_m=focus_max_range_m) if focus_camera else -1.0,
            "anyCameraScore": _best_frustum_score(cx, cz, cameras, max_range_m=any_camera_max_range_m),
        })

    def sort_key(c):
        if c["focusScore"] > 0:
            return (0, -c["focusScore"])
        if c["anyCameraScore"] > 0:
            return (1, -c["anyCameraScore"])
        return (2, c["j"], c["i"])

    candidates.sort(key=sort_key)

    plain_cost = _block_triangle_cost(kit, config, False)
    reserved: list[dict] = []
    used = 0
    skipped_budget = 0
    for c in candidates:
        if used + plain_cost > tri_budget:
            skipped_budget += 1
            continue
        reserved.append(c)
        used += plain_cost

    height_cycle = wall_cycle = roof_cycle = window_cycle = base_cycle = 0
    focus_seen = 0
    for c in reserved:
        if c["focusScore"] > 0:
            c["h"] = config.focus_height_choices[focus_seen % len(config.focus_height_choices)]
            focus_seen += 1
            c["focusBlock"] = True
        else:
            c["h"] = config.height_choices[height_cycle % len(config.height_choices)]
            height_cycle += 1
            c["focusBlock"] = False
        c["wallMaterial"] = config.wall_materials[wall_cycle % len(config.wall_materials)]
        wall_cycle += 1
        c["roofMaterial"] = config.roof_materials[roof_cycle % len(config.roof_materials)]
        roof_cycle += 1
        c["baseMaterial"] = config.base_materials[base_cycle % len(config.base_materials)]
        base_cycle += 1
        c["windowMaterial"] = config.window_materials[window_cycle % len(config.window_materials)]
        window_cycle += 1

    for c in reserved:
        facade = visible_facade_sides(c["cx"], c["cz"], c["w"], c["d"], c["h"], kit=kit, cfg=config,
                                       cameras=cameras, occlusion_grids=occlusion_grids, resolution=resolution)
        end_wall = visible_end_wall_sides(c["cx"], c["cz"], c["w"], c["d"], c["h"], kit=kit, cfg=config,
                                           cameras=cameras, occlusion_grids=occlusion_grids, resolution=resolution)
        c["facade"] = facade
        c["endWall"] = end_wall
        truly_visible_cams = set(facade["cameraNames"]) | set(end_wall["cameraNames"])
        c["camerasTrulyVisible"] = len(truly_visible_cams)
        c["camerasFrustumOnly"] = max(facade["camerasFrustumOnly"], end_wall["camerasFrustumOnly"])
        c["bestOnscreenPxW"] = max(facade["bestOnscreenPxW"], end_wall["bestOnscreenPxW"])
        c["wastedByFrustumOnly"] = c["camerasFrustumOnly"] > 0 and c["camerasTrulyVisible"] == 0

    priority_order = sorted(
        range(len(reserved)),
        key=lambda i: (-reserved[i]["camerasTrulyVisible"], -reserved[i]["bestOnscreenPxW"], i),
    )

    upgrade_flags = [False] * len(reserved)
    roof_form_by_index: list = [None] * len(reserved)
    roof_param_by_index: list = [None] * len(reserved)
    ridge_along_x_by_index: list = [None] * len(reserved)
    facade_sides_by_index: list = [None] * len(reserved)
    end_wall_sides_by_index: list = [()] * len(reserved)
    cost_by_index: list = [plain_cost] * len(reserved)
    skip_reason_by_index: list = [None] * len(reserved)

    articulated_index = 0
    remaining = tri_budget - used

    def _try_upgrade(idx: int) -> bool:
        nonlocal articulated_index, remaining, used
        c = reserved[idx]
        if c["camerasTrulyVisible"] == 0:
            skip_reason_by_index[idx] = "occluded-in-every-camera"
            return False
        sides = c["facade"]["facadeSides"] or (1.0,)
        end_sides = c["endWall"]["endWallSides"]
        roof_form = config.roof_forms[articulated_index % len(config.roof_forms)]
        natural_ridge_along_x = c["w"] >= c["d"]
        ridge_along_x = natural_ridge_along_x if articulated_index % 2 == 0 else not natural_ridge_along_x
        roof_param = (
            (2.0 if articulated_index % 2 == 0 else 2.6) if roof_form == "pitched"
            else config.parapet_height_choices[articulated_index % len(config.parapet_height_choices)]
        )
        full_cost = _articulated_triangle_cost(kit, config, rhythm, c["w"], c["h"], roof_form, sides, end_sides)
        incremental = full_cost - plain_cost
        if incremental + config.margin_reserve_triangles > remaining:
            skip_reason_by_index[idx] = "budget-exhausted-before-this-priority-rank"
            return False
        remaining -= incremental
        used += incremental
        upgrade_flags[idx] = True
        roof_form_by_index[idx] = roof_form
        roof_param_by_index[idx] = roof_param
        ridge_along_x_by_index[idx] = ridge_along_x
        facade_sides_by_index[idx] = sides
        end_wall_sides_by_index[idx] = end_sides
        cost_by_index[idx] = full_cost
        articulated_index += 1
        return True

    for idx in priority_order:
        _try_upgrade(idx)

    placed: list[dict] = []
    new_specs: list[dict] = []
    for idx, c in enumerate(reserved):
        want_full = upgrade_flags[idx]
        role = f"{role_prefix}-{len(placed):03d}"
        h = c["h"]
        wall_material, roof_material, base_material, window_material = (
            c["wallMaterial"], c["roofMaterial"], c["baseMaterial"], c["windowMaterial"],
        )

        if want_full:
            roof_form = roof_form_by_index[idx]
            sides = facade_sides_by_index[idx]
            end_sides = end_wall_sides_by_index[idx]
            _terrace_block_articulated(
                new_specs, kit=kit, cfg=config, rhythm=rhythm, group=group, role=role,
                cx=c["cx"], cz=c["cz"], w=c["w"], d=c["d"], h=h,
                base_material=base_material, wall_material=wall_material, roof_material=roof_material,
                window_material=window_material, roof_form=roof_form, roof_param=roof_param_by_index[idx],
                ridge_along_x=ridge_along_x_by_index[idx], facade_sides=sides, end_wall_sides=end_sides,
            )
            cost = cost_by_index[idx]
        else:
            roof_form, sides, end_sides = None, (), ()
            _terrace_block(
                new_specs, kit=kit, cfg=config, group=group, role=role, cx=c["cx"], cz=c["cz"],
                w=c["w"], d=c["d"], h=h, base_material=base_material, wall_material=wall_material,
                roof_material=roof_material, detailed=False, chamfer_base=False,
            )
            cost = plain_cost

        _occupy(config, grid, grid_n, c["cx"], c["cz"], c["w"], c["d"])
        placed.append({
            "role": role, "cx": c["cx"], "cz": c["cz"], "w": c["w"], "d": c["d"], "h": h,
            "articulated": want_full, "roofForm": roof_form if want_full else "flat",
            "cornice": want_full, "cornice_overhang_m": config.cornice_overhang_m if want_full else 0.0,
            "triangles": cost, "facadeSides": list(sides), "facadeCount": len(sides),
            "endWallSides": list(end_sides), "endWallCount": len(end_sides),
            "camerasVisibleIn": c["camerasTrulyVisible"], "camerasFrustumOnly": c["camerasFrustumOnly"],
            "wastedByFrustumOnly": c["wastedByFrustumOnly"], "bestOnscreenPxW": c["bestOnscreenPxW"],
            "focusBlock": c["focusBlock"], "anyCameraFocus": c["anyCameraScore"] > 0,
            "skipReason": skip_reason_by_index[idx],
        })

    return {
        "specs": new_specs, "placed": placed, "triBudget": tri_budget, "triUsed": used,
        "marginReserveTriangles": config.margin_reserve_triangles, "remainingAfterMargin": remaining,
        "blockCount": len(placed), "articulatedBlockCount": sum(1 for p in placed if p["articulated"]),
        "plainBlockCount": sum(1 for p in placed if not p["articulated"]),
        "plainRoles": [p["role"] for p in placed if not p["articulated"]],
        "articulatedRoles": [p["role"] for p in placed if p["articulated"]],
        "multiFacadeRoles": [p["role"] for p in placed if p["facadeCount"] >= 2],
        "endWallArticulatedRoles": [p["role"] for p in placed if p["endWallCount"] > 0],
        "occlusionExcludedRoles": [p["role"] for p in placed if p["skipReason"] == "occluded-in-every-camera"],
        "wastedByFrustumOnlyRoles": [p["role"] for p in placed if p["wastedByFrustumOnly"]],
        "focusBlocks": sum(1 for p in placed if p["focusBlock"]),
        "anyCameraFocusBlocks": sum(1 for p in placed if p["anyCameraFocus"]),
        "candidateSitesTotal": len(candidates), "candidateSitesSkippedForBudget": skipped_budget,
        "plainCostTriangles": plain_cost,
    }


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------
def road_overlap_audit(new_specs: Sequence[Spec], *, kit: SpecKit, config: DistrictConfig = DistrictConfig()) -> dict:
    violations = []
    for spec in new_specs:
        b = kit.spec_bounds(spec)
        if b[4] <= config.road_top_limit_m:
            continue
        x_overlaps_ns_road = b[0] < config.road_half_m and b[3] > -config.road_half_m
        z_overlaps_ew_road = b[2] < config.road_half_m and b[5] > -config.road_half_m
        if x_overlaps_ns_road or z_overlaps_ew_road:
            violations.append({
                "role": spec["role"], "bounds": [round(v, 2) for v in b],
                "roads": (["primary-north-south"] if x_overlaps_ns_road else [])
                + (["primary-east-west"] if z_overlaps_ew_road else []),
            })
    return {"violationCount": len(violations), "violations": violations[:50], "passed": not violations}


def _point_to_aabb_dist_xz(px, pz, b) -> float:
    dx = max(b[0] - px, 0.0, px - b[3])
    dz = max(b[2] - pz, 0.0, pz - b[5])
    return math.hypot(dx, dz)


def spawn_clearance_audit(
    new_specs: Sequence[Spec], *, kit: SpecKit, player_spawns: Sequence[Sequence[float]],
    bot_spawns: Sequence[Sequence[float]], config: DistrictConfig = DistrictConfig(),
) -> dict:
    player_min = math.inf
    bot_min = math.inf
    player_violations = []
    bot_violations = []
    for spec in new_specs:
        b = kit.spec_bounds(spec)
        for (sx, _sy, sz) in player_spawns:
            dist = _point_to_aabb_dist_xz(sx, sz, b)
            player_min = min(player_min, dist)
            if dist < config.player_spawn_clearance_m:
                player_violations.append({"role": spec["role"], "spawn": [sx, sz], "distanceM": round(dist, 2)})
        for (sx, _sy, sz) in bot_spawns:
            dist = _point_to_aabb_dist_xz(sx, sz, b)
            bot_min = min(bot_min, dist)
            if dist < config.bot_spawn_clearance_m:
                bot_violations.append({"role": spec["role"], "spawn": [sx, sz], "distanceM": round(dist, 2)})
    return {
        "playerSpawnClearanceRequiredM": config.player_spawn_clearance_m,
        "botSpawnClearanceRequiredM": config.bot_spawn_clearance_m,
        "minPlayerSpawnDistanceM": None if player_min == math.inf else round(player_min, 2),
        "minBotSpawnDistanceM": None if bot_min == math.inf else round(bot_min, 2),
        "playerSpawnViolations": player_violations[:50], "botSpawnViolations": bot_violations[:50],
        "passed": not player_violations and not bot_violations,
    }


def gap_audit(placed: Sequence[dict], *, config: DistrictConfig = DistrictConfig()) -> dict:
    def half_extent(p, dim_key):
        return p[dim_key] / 2.0 + p.get("cornice_overhang_m", 0.0)

    alley_gaps = []
    street_gaps = []
    by_row: dict[float, list[dict]] = {}
    for p in placed:
        by_row.setdefault(round(p["cz"], 1), []).append(p)
    for row in by_row.values():
        row.sort(key=lambda p: p["cx"])
        for a, b in zip(row, row[1:]):
            alley_gaps.append((b["cx"] - half_extent(b, "w")) - (a["cx"] + half_extent(a, "w")))
    rows_sorted = sorted(by_row.items(), key=lambda kv: kv[0])
    for (za, blocks_a), (zb, blocks_b) in zip(rows_sorted, rows_sorted[1:]):
        max_half_d_a = max(half_extent(p, "d") for p in blocks_a)
        max_half_d_b = max(half_extent(p, "d") for p in blocks_b)
        street_gaps.append((zb - max_half_d_b) - (za + max_half_d_a))
    alley_lo, _alley_hi = config.contract_alley_band_m
    street_lo, _street_hi = config.contract_street_band_m
    return {
        "alleyGapsM": {"count": len(alley_gaps), "min": round(min(alley_gaps), 2) if alley_gaps else None,
                       "max": round(max(alley_gaps), 2) if alley_gaps else None},
        "streetGapsM": {"count": len(street_gaps), "min": round(min(street_gaps), 2) if street_gaps else None,
                        "max": round(max(street_gaps), 2) if street_gaps else None},
        "contractAlleyBandM": list(config.contract_alley_band_m),
        "contractStreetBandM": list(config.contract_street_band_m),
        "passed": (
            (not alley_gaps or min(alley_gaps) >= alley_lo)
            and (not street_gaps or min(street_gaps) >= street_lo)
        ),
    }
