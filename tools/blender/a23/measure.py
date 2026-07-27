"""A23 measurement: built footprint, hero occlusion-aware frame occupancy,
the strict green-dominance foliage test, and the per-camera image metric
table.

Promoted from the private study:
  - built footprint + largest-empty-square:
    ``/private/tmp/hibana-blender/claude-a23-nakaniwa-h18/measure_built_footprint.py``
  - hero (palace/conservatory) occlusion-aware frame occupancy:
    ``.../claude-a23-tier1/measure_palace.py``
  - the per-camera image metric table incl. the strict foliage test:
    ``.../claude-a23-tier1/measure_image_metrics_tier1.py``

Every function here measures something *directly from geometry or pixels*,
never by diffing two renders. That is deliberate: the round log's
``measurementDefect3`` ("change-detection blindness to static defects")
found orphan emissive geometry that a pure before/after pixel diff could
never have caught, because a defect present in *both* frames produces zero
delta and is invisible to a diff by construction. ``hero_frame_occupancy``
and ``built_footprint_report`` are the direct-measurement answer to that —
they compute an absolute fact about one build, not a delta against another.
``per_camera_metric_table`` still offers an optional pixel diff (useful
evidence, e.g. this promotion's own fidelity check), but every metric next
to it is computed per-frame first.

``foliage_mask_strict`` exists to fix a second, separate measurement defect
named in the round log (H19): a loose HSV-range foliage classifier counted
shadowed stone as foliage, inflating a real 723 px measurement into a
reported 7,269 px (an order-of-magnitude overstatement of a real, much
smaller improvement). The fix is a green-dominance requirement
(``g > r + 12 and g > b + 12``) layered on top of the HSV mask; this module
only implements the strict version, kept as the sole/authoritative test.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from tools.blender.a23.kit import Spec, SpecKit, frame_cells


# ---------------------------------------------------------------------------
# Built footprint (direct geometric raster measurement, no rendering).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FootprintConfig:
    map_half_m: float = 160.0
    cell_m: float = 2.0
    built_min_height_m: float = 2.5
    ground_role_tokens: tuple = (
        "weathered-stone-ground", "ground-behind-canal", "ground-beyond-canal",
        "ground-left-of-canal", "ground-right-of-canal", "canonical-road",
    )
    foliage_materials: frozenset = field(
        default_factory=lambda: frozenset({"foliage_dark", "foliage_light", "flower"})
    )


def built_footprint_report(
    specs: Sequence[Spec],
    *,
    kit: SpecKit,
    canonical_roads: Sequence[Mapping[str, object]],
    contract_band_pct: tuple[float, float] = (24.5, 34.0),
    config: FootprintConfig = FootprintConfig(),
    largest_empty_square: bool = True,
    coarse_map_cells: int = 16,
) -> dict:
    """Rasterise every spec's world AABB onto a ``config.cell_m`` grid over a
    ``2 * config.map_half_m`` square map and classify each cell as built,
    canopy, water, road or empty by the tallest thing standing on it. This
    is the direct measurement that found nakaniwa's H17 "one polished
    corridor in an otherwise empty 320 x 320 m map" defect (17.11% built
    against a 24.5-34% contract) — a defect that was invisible to every
    single-camera pixel metric the round had been using until then.
    """
    import numpy as np

    map_half = config.map_half_m
    cell_m = config.cell_m
    grid = int(round(2 * map_half / cell_m))

    def cell_range(lo: float, hi: float) -> tuple[int, int]:
        a = int(math.floor((lo + map_half) / cell_m))
        b = int(math.ceil((hi + map_half) / cell_m))
        return max(0, a), min(grid, b)

    height = np.zeros((grid, grid), dtype=np.float32)
    canopy = np.zeros((grid, grid), dtype=bool)
    water = np.zeros((grid, grid), dtype=bool)

    for spec in specs:
        role = str(spec["role"])
        if any(token in role for token in config.ground_role_tokens):
            continue
        b = kit.spec_bounds(spec)
        x0, x1 = cell_range(b[0], b[3])
        z0, z1 = cell_range(b[2], b[5])
        if x0 >= x1 or z0 >= z1:
            continue
        top = float(b[4])
        material = spec["material"]
        if material == "water":
            water[z0:z1, x0:x1] = True
            continue
        if material in config.foliage_materials:
            if top >= config.built_min_height_m:
                canopy[z0:z1, x0:x1] = True
            continue
        if top >= config.built_min_height_m:
            np.maximum(height[z0:z1, x0:x1], top, out=height[z0:z1, x0:x1])

    built = height >= config.built_min_height_m
    road = np.zeros_like(built)
    for entry in canonical_roads:
        rb = entry["bounds"]
        x0, x1 = cell_range(rb["minX"], rb["maxX"])
        z0, z1 = cell_range(rb["minZ"], rb["maxZ"])
        road[z0:z1, x0:x1] = True

    empty = ~(built | water | road | canopy)
    total = grid * grid

    report = {
        "schema": "hibana.a23.measure.built-footprint.v1",
        "mapSizeM": 2 * map_half,
        "cellM": cell_m,
        "builtMinHeightM": config.built_min_height_m,
        "contract": {"builtFootprintTargetPct": list(contract_band_pct)},
        "measured": {
            "builtPct": round(float(built.mean()) * 100, 2),
            "canopyPct": round(float(canopy.mean()) * 100, 2),
            "waterPct": round(float(water.mean()) * 100, 2),
            "roadPct": round(float(road.mean()) * 100, 2),
            "emptyPct": round(float(empty.mean()) * 100, 2),
            "cells": total,
            "builtCells": int(built.sum()),
        },
        "verdict": "PASS" if contract_band_pct[0] <= float(built.mean()) * 100 <= contract_band_pct[1] else "FAIL",
    }

    if largest_empty_square:
        integral = np.cumsum(np.cumsum(empty.astype(np.int32), axis=0), axis=1)

        def empty_count(z0, x0, size):
            z1, x1 = z0 + size, x0 + size
            total_ = integral[z1 - 1, x1 - 1]
            if z0 > 0:
                total_ -= integral[z0 - 1, x1 - 1]
            if x0 > 0:
                total_ -= integral[z1 - 1, x0 - 1]
            if z0 > 0 and x0 > 0:
                total_ += integral[z0 - 1, x0 - 1]
            return total_

        best = {"sizeCells": 0, "z": 0, "x": 0}
        for size in range(4, grid + 1, 2):
            found = None
            for z0 in range(0, grid - size + 1, 2):
                for x0 in range(0, grid - size + 1, 2):
                    if empty_count(z0, x0, size) == size * size:
                        found = (z0, x0)
                        break
                if found:
                    break
            if found is None:
                break
            best = {"sizeCells": size, "z": found[0], "x": found[1]}

        def to_world(cell_index):
            return round(cell_index * cell_m - map_half, 1)

        report["largestEmptySquare"] = {
            "sizeM": best["sizeCells"] * cell_m,
            "minX": to_world(best["x"]), "minZ": to_world(best["z"]),
            "maxX": to_world(best["x"] + best["sizeCells"]),
            "maxZ": to_world(best["z"] + best["sizeCells"]),
        }

    if coarse_map_cells:
        block = grid // coarse_map_cells
        coarse = []
        if block > 0:
            for bz in range(coarse_map_cells):
                row = ""
                for bx in range(coarse_map_cells):
                    sub = built[bz * block:(bz + 1) * block, bx * block:(bx + 1) * block]
                    frac = float(sub.mean()) if sub.size else 0.0
                    row += " .:-=+*#@"[min(8, int(frac * 9))]
                coarse.append(row)
        report["coarseBuiltMap"] = coarse
        report["coarseBuiltMapLegend"] = "' ' empty ... '@' fully built"

    return report


# ---------------------------------------------------------------------------
# Hero occlusion-aware frame occupancy (direct geometric measurement).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HeroOcclusionConfig:
    grid: tuple[int, int] = (128, 72)
    hero_min_top_height_m: float = 4.0
    occluder_min_top_height_m: float = 2.8
    depth_margin_m: float = 0.75


def _span_pct(indices, count) -> float:
    if not indices:
        return 0.0
    return (max(indices) - min(indices) + 1) / count * 100.0


def hero_frame_occupancy(
    specs: Sequence[Spec],
    camera: Mapping[str, object],
    *,
    kit: SpecKit,
    group_id: str,
    config: HeroOcclusionConfig = HeroOcclusionConfig(),
) -> dict:
    """Direct geometric measurement of one hero group's frame occupancy at
    ``camera``: project every hero spec's AABB, build a depth-aware
    occlusion grid from everything else in the scene, and report both the
    RAW envelope (the hero's own unoccluded footprint — fixed given frozen
    hero geometry and camera) and the occlusion-aware VISIBLE envelope
    (what actually answers "is the hero in the frame"). This is what
    replaced pixel-diffing renders for judging hero composition — a caged,
    fully-occluded hero and an open, well-framed one can render nearly
    identical PALETTE statistics while having opposite occlusion ratios;
    only a direct per-spec depth comparison tells them apart.

    Reuses the same convention the kit's own
    ``reference_camera_occlusion_report`` established (hero specs under
    ``hero_min_top_height_m`` dropped from the target surface, occluders
    under ``occluder_min_top_height_m`` dropped from the occluder pool, a
    ``depth_margin_m`` cushion before a nearer spec counts as a real
    occluder), generalised to any composed scene and any camera rather than
    only the frozen kit specs at the kit's own main reference camera.
    """
    aspect = camera["resolution"][0] / camera["resolution"][1] if "resolution" in camera else 16.0 / 9.0
    grid_w, grid_h = config.grid

    hero_specs = [s for s in specs if s.get("group") == group_id]
    other_specs = [s for s in specs if s.get("group") != group_id]

    raw_frames = []
    for s in hero_specs:
        frame = kit.project_spec_frame(s, camera, aspect)
        if frame is not None:
            raw_frames.append(frame)
    if raw_frames:
        raw_x0 = min(f["bounds"][0] for f in raw_frames)
        raw_y0 = min(f["bounds"][1] for f in raw_frames)
        raw_x1 = max(f["bounds"][2] for f in raw_frames)
        raw_y1 = max(f["bounds"][3] for f in raw_frames)
    else:
        raw_x0 = raw_y0 = raw_x1 = raw_y1 = 0.0
    raw_visible_x0 = max(0.0, raw_x0)
    raw_visible_x1 = min(1.0, raw_x1)
    raw_width_pct = max(0.0, raw_visible_x1 - raw_visible_x0) * 100.0
    raw_top_margin_pct = max(0.0, (1.0 - min(1.0, raw_y1))) * 100.0

    target_depth: dict[tuple[int, int], float] = {}
    for s in hero_specs:
        if kit.spec_bounds(s)[4] <= config.hero_min_top_height_m:
            continue
        frame = kit.project_spec_frame(s, camera, aspect)
        if frame is None:
            continue
        for cell in frame_cells(frame["bounds"], grid_w, grid_h):
            target_depth[cell] = min(target_depth.get(cell, float("inf")), float(frame["nearDepthM"]))

    blocked: dict[tuple[int, int], float] = {}
    blocked_role: dict[tuple[int, int], str] = {}
    blocker_spec_count: dict[str, int] = {}
    for s in other_specs:
        if kit.spec_bounds(s)[4] <= config.occluder_min_top_height_m:
            continue
        frame = kit.project_spec_frame(s, camera, aspect)
        if frame is None:
            continue
        near = float(frame["nearDepthM"])
        cells = list(frame_cells(frame["bounds"], grid_w, grid_h))
        role = str(s.get("role", "?"))
        hit_any = False
        for cell in cells:
            hero_depth = target_depth.get(cell)
            if hero_depth is None:
                continue
            if near + config.depth_margin_m < hero_depth:
                prev = blocked.get(cell)
                if prev is None or near < prev:
                    blocked[cell] = near
                    blocked_role[cell] = role
                hit_any = True
        if hit_any:
            blocker_spec_count[role] = blocker_spec_count.get(role, 0) + 1

    blocked_cells_by_role: dict[str, int] = {}
    for role in blocked_role.values():
        blocked_cells_by_role[role] = blocked_cells_by_role.get(role, 0) + 1

    visible_cells = [c for c in target_depth if c not in blocked]
    xs = [c[0] for c in visible_cells]
    ys = [c[1] for c in visible_cells]
    visible_width_pct = _span_pct(xs, grid_w)
    if ys:
        top_iy = max(ys)
        top_v = (top_iy + 1) / grid_h
        visible_top_margin_pct = max(0.0, (1.0 - top_v)) * 100.0
    else:
        visible_top_margin_pct = 100.0

    n_hero_cells = len(target_depth)
    n_blocked = len(blocked)
    occlusion_ratio = (n_blocked / n_hero_cells) if n_hero_cells else 1.0

    return {
        "method": f"direct-geometric-projection-occlusion-grid-{grid_w}x{grid_h}",
        "raw": {
            "note": "hero's own envelope, ignores occluders -- fixed given frozen hero geometry+camera",
            "widthPct": round(raw_width_pct, 2), "topMarginPct": round(raw_top_margin_pct, 2),
            "boundsNDC": [round(raw_x0, 4), round(raw_y0, 4), round(raw_x1, 4), round(raw_y1, 4)],
        },
        "visible": {
            "note": "occlusion-aware: only screen cells where no nearer non-hero spec covers the hero surface",
            "widthPct": round(visible_width_pct, 2), "topMarginPct": round(visible_top_margin_pct, 2),
        },
        "sampledHeroCells": n_hero_cells, "occludedCells": n_blocked,
        "occlusionRatio": round(occlusion_ratio, 4),
        "blockingRolesBySpecCount": dict(sorted(blocker_spec_count.items(), key=lambda kv: -kv[1])),
        "blockingRolesByCellArea": dict(sorted(blocked_cells_by_role.items(), key=lambda kv: -kv[1])),
        "gridW": grid_w, "gridH": grid_h,
    }


# ---------------------------------------------------------------------------
# Per-camera pixel metric table (needs OpenCV/numpy/PIL against rendered
# PNGs -- not guaranteed inside Blender's bundled interpreter, so these are
# meant to run under plain python3 after evidence.py has produced renders).
# ---------------------------------------------------------------------------
def edge_density(bgr) -> float:
    import cv2
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 75, 150) > 0
    return float(edges.mean())


def sky_mask(bgr):
    import cv2
    blue, green, red = cv2.split(bgr)
    blue_i = blue.astype("int16")
    return (blue_i - red.astype("int16") > 25) & (blue_i - green.astype("int16") > 8)


def foliage_mask_strict(bgr):
    """The authoritative foliage test (round-state ``metricCorrection``):
    green-dominance (``g > r + 12`` AND ``g > b + 12``) on top of an implicit
    HSV-green range. A prior loose HSV-only mask counted shadowed stone as
    foliage, inflating a real 723 px control measurement into a reported
    7,269 px (10x). Every foliage pixel count in this package's docs and
    tests uses this strict test only; do not reintroduce the loose one.
    """
    import cv2
    blue, green, red = cv2.split(bgr)
    green_i = green.astype("int16")
    return (green_i - red.astype("int16") > 12) & (green_i - blue.astype("int16") > 12)


def value_spread(bgr) -> float:
    import cv2
    import numpy as np
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    return float(np.std(value.astype(np.float64)))


def metrics_for(path: Path) -> dict:
    import cv2
    import hashlib
    from PIL import Image

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise RuntimeError(f"unable to decode {path}")
    foliage_strict = foliage_mask_strict(bgr)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "resolution": list(Image.open(path).size),
        "edgeDensity": round(edge_density(bgr), 6),
        "skyPct": round(float(sky_mask(bgr).mean()) * 100, 2),
        "foliagePixelsStrict": int(foliage_strict.sum()),
        "valueSpread": round(value_spread(bgr), 3),
    }


def pixel_diff(before_path: Path, after_path: Path, *, changed_threshold: int = 15) -> Optional[dict]:
    """Absolute BGR-sum pixel diff between two equally-sized renders, plus
    the largest 8-connected changed component. Provided as visual evidence
    only; per ``measurementDefect3`` (see module docstring) this must never
    be the *only* check for a static defect, only a supplement to the
    direct measurements above.
    """
    import cv2
    import numpy as np

    if not Path(before_path).exists():
        return None
    a = cv2.imread(str(before_path), cv2.IMREAD_COLOR)
    b = cv2.imread(str(after_path), cv2.IMREAD_COLOR)
    if a is None or b is None or a.shape != b.shape:
        return None
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).sum(axis=2)
    changed = diff > changed_threshold
    changed_pct = float(changed.mean()) * 100
    num, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        changed.astype("uint8"), connectivity=8
    )
    largest = int(stats[1:, cv2.CC_STAT_AREA].max()) if num > 1 else 0
    return {"changedPct": round(changed_pct, 4), "largestComponentPx": largest}


def per_camera_metric_table(
    camera_pngs: Mapping[str, Path], *, before_pngs: Optional[Mapping[str, Path]] = None,
) -> dict:
    """One row per camera: edge density, sky%, strict-foliage pixel count,
    value spread, and (if ``before_pngs`` supplies a matching path) a pixel
    diff against a prior render of the same camera. This is the "per-camera
    metric table" this promotion's own fidelity check (see the promotion
    report) is built from.
    """
    rows = []
    for name, path in camera_pngs.items():
        metrics = metrics_for(Path(path))
        before_path = before_pngs.get(name) if before_pngs else None
        diff = pixel_diff(Path(before_path), Path(path)) if before_path else None
        rows.append({"camera": name, **metrics, "pixelDiffVsBefore": diff})
    return {
        "schema": "hibana.a23.measure.per-camera-metric-table.v1",
        "method": {
            "edge": "OpenCV grayscale Canny(75,150), fraction of edge pixels over the frame",
            "sky": "blue-dominance heuristic (blue-red>25 and blue-green>8), fraction of frame",
            "foliageStrict": "green-dominance test (g>r+12 and g>b+12) -- see foliage_mask_strict",
            "valueSpread": "std-dev of HSV value channel over the whole frame",
            "pixelDiffVsBefore": "abs BGR diff sum > 15 counted as changed; largest 8-connected component reported",
        },
        "perCamera": rows,
    }
