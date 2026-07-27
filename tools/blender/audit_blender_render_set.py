#!/usr/bin/env python3
"""Reject incomplete or camera-occluded Blender QA render sets.

This is a technical pre-gate, not an art-quality classifier. It catches
missing views, duplicate frames, blank/near-uniform renders, and cameras buried
inside a wall before a human performs the mandatory reference scorecard.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

from PIL import Image

try:
    from tools.blender.audit_stage_reference_match import image_metrics
except ModuleNotFoundError:  # Direct `python tools/blender/...py` execution.
    from audit_stage_reference_match import image_metrics


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dominant_coarse_color_ratio(path: Path) -> float:
    """Return the largest 5-bit RGB bucket share after deterministic resize."""
    with Image.open(path) as source:
        rgb = source.convert("RGB").resize((256, 144), Image.Resampling.LANCZOS)
    counts: dict[tuple[int, int, int], int] = {}
    pixels = rgb.get_flattened_data()
    for red, green, blue in pixels:
        key = (red // 32, green // 32, blue // 32)
        counts[key] = counts.get(key, 0) + 1
    return round(max(counts.values(), default=0) / max(1, rgb.width * rgb.height), 6)


def border_connected_void_ratios(path: Path) -> tuple[float, float]:
    """Measure flat black/white voids connected to the lower image border.

    A failed set extension or a camera outside a generated island commonly
    renders as a perfectly black (transparent-film) or white plane occupying
    the bottom of an otherwise detailed frame. Global near-black ratios miss
    smaller but still blatant wedges, while a night map can legitimately be
    dark. Restricting the flood fill to almost-neutral extreme values that
    connect to the *lower* border catches the missing-world failure without
    classifying a dark, textured sky as void.
    """
    with Image.open(path) as source:
        rgb = source.convert("RGB").resize((256, 144), Image.Resampling.LANCZOS)
    width, height = rgb.size
    pixels = list(rgb.get_flattened_data())

    def largest_lower_border_component(predicate) -> float:
        mask = bytearray(1 if predicate(pixel) else 0 for pixel in pixels)
        visited = bytearray(width * height)
        largest = 0
        # Seed only the bottom border and the lower half of both side borders.
        # A bright/dark sky touching the top edge is not missing ground.
        seeds = [(x, height - 1) for x in range(width)]
        seeds.extend((0, y) for y in range(height // 2, height - 1))
        seeds.extend((width - 1, y) for y in range(height // 2, height - 1))
        for seed_x, seed_y in seeds:
            seed_index = seed_y * width + seed_x
            if not mask[seed_index] or visited[seed_index]:
                continue
            visited[seed_index] = 1
            stack = [seed_index]
            area = 0
            while stack:
                index = stack.pop()
                area += 1
                x, y = index % width, index // width
                for neighbour in (
                    index - 1 if x > 0 else -1,
                    index + 1 if x + 1 < width else -1,
                    index - width if y > 0 else -1,
                    index + width if y + 1 < height else -1,
                ):
                    if neighbour >= 0 and mask[neighbour] and not visited[neighbour]:
                        visited[neighbour] = 1
                        stack.append(neighbour)
            largest = max(largest, area)
        return round(largest / max(1, width * height), 6)

    near_black = largest_lower_border_component(
        lambda pixel: max(pixel) <= 10 and max(pixel) - min(pixel) <= 6
    )
    near_white = largest_lower_border_component(
        lambda pixel: min(pixel) >= 247 and max(pixel) - min(pixel) <= 5
    )
    return near_black, near_white


def dark_facade_grid_metrics(path: Path) -> dict[str, int]:
    """Find repeated, high-contrast near-black rectangles in the rendered scene.

    This is deliberately conservative and only reports components that are
    compact, mostly rectangular, surrounded by a substantially brighter
    surface, and disconnected from the image border. A single doorway or deep
    shadow remains valid; a row/grid of copied black window holes does not.
    The independent GLB gate remains authoritative for shipped geometry, while
    this render check also protects isolated Blender candidates before export.
    """
    with Image.open(path) as source:
        rgb = source.convert("RGB").resize((256, 144), Image.Resampling.LANCZOS)
    width, height = rgb.size
    pixels = list(rgb.get_flattened_data())
    luminances = [0.2126 * red + 0.7152 * green + 0.0722 * blue for red, green, blue in pixels]
    mask = bytearray(
        1 if max(pixel) <= 52 and max(pixel) - min(pixel) <= 22 else 0
        for pixel in pixels
    )
    visited = bytearray(width * height)
    rectangles: list[tuple[int, int, int, int]] = []
    for seed in range(width * height):
        if not mask[seed] or visited[seed]:
            continue
        visited[seed] = 1
        stack = [seed]
        component: list[int] = []
        while stack:
            index = stack.pop()
            component.append(index)
            x, y = index % width, index // width
            for neighbour in (
                index - 1 if x > 0 else -1,
                index + 1 if x + 1 < width else -1,
                index - width if y > 0 else -1,
                index + width if y + 1 < height else -1,
            ):
                if neighbour >= 0 and mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
        xs = [index % width for index in component]
        ys = [index // width for index in component]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        box_width, box_height = x1 - x0 + 1, y1 - y0 + 1
        area = len(component)
        fill_ratio = area / max(1, box_width * box_height)
        aspect = box_width / max(1, box_height)
        if not (
            6 <= area <= 500
            and 3 <= box_width <= 24
            and 3 <= box_height <= 30
            and 0.35 <= aspect <= 2.2
            and fill_ratio >= 0.68
            and x0 > 1
            and x1 < width - 2
            and y0 > 1
            and y1 < height - 2
        ):
            continue
        surround = []
        for y in range(max(0, y0 - 2), min(height, y1 + 3)):
            for x in range(max(0, x0 - 2), min(width, x1 + 3)):
                if x0 <= x <= x1 and y0 <= y <= y1:
                    continue
                surround.append(luminances[y * width + x])
        if not surround:
            continue
        inside_luminance = sum(luminances[index] for index in component) / area
        surround_luminance = sum(surround) / len(surround)
        if surround_luminance >= 60 and surround_luminance - inside_luminance >= 30:
            rectangles.append((x0, y0, box_width, box_height))

    # Windows in the rejected assets align within one or two downsampled
    # pixels. Three-pixel bins tolerate perspective while not grouping random
    # texture specks. Size bins similarly catch a copied 4x3 / 5x3 family.
    rows: dict[int, int] = {}
    sizes: dict[tuple[int, int], int] = {}
    for _, y, box_width, box_height in rectangles:
        row = round(y / 3)
        rows[row] = rows.get(row, 0) + 1
        size = (round(box_width / 2), round(box_height / 2))
        sizes[size] = sizes.get(size, 0) + 1
    return {
        "candidateCount": len(rectangles),
        "maxAlignedRowCount": max(rows.values(), default=0),
        "maxRepeatedSizeCount": max(sizes.values(), default=0),
    }


def inspect_render(path: Path) -> dict:
    metrics = image_metrics(path)
    dominant = dominant_coarse_color_ratio(path)
    black_void, white_void = border_connected_void_ratios(path)
    dark_grid = dark_facade_grid_metrics(path)
    findings: list[str] = []
    if metrics.edgeDensity < 0.012:
        findings.append("near-blank-frame")
    if metrics.entropy < 2.2:
        findings.append("near-uniform-frame")
    if dominant > 0.78:
        findings.append("dominant-flat-surface")
    if dominant > 0.62 and metrics.edgeDensity < 0.035:
        findings.append("probable-camera-inside-or-facing-wall")
    if metrics.highlightRatio > 0.45:
        findings.append("severe-highlight-clipping")
    if metrics.nearBlackRatio > 0.55:
        findings.append("severe-shadow-crush")
    if black_void > 0.10:
        findings.append("large-border-connected-black-void")
    if white_void > 0.15:
        findings.append("large-border-connected-white-void")
    if dark_grid["candidateCount"] >= 8 and (
        dark_grid["maxAlignedRowCount"] >= 4
        or dark_grid["maxRepeatedSizeCount"] >= 5
    ):
        findings.append("repeated-near-black-facade-grid")
    return {
        "path": str(path),
        "sha256": sha256(path),
        "metrics": {
            **metrics.__dict__,
            "dominantCoarseColorRatio": dominant,
            "borderConnectedNearBlackVoidRatio": black_void,
            "borderConnectedNearWhiteVoidRatio": white_void,
            "darkFacadeGrid": dark_grid,
        },
        "findings": findings,
        "ok": not findings,
    }


def audit_render_set(
    render_dir: Path,
    expected_count: int = 8,
    minimum_eye_height_views: int = 4,
) -> dict:
    paths = sorted(
        path for path in render_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    renders = [inspect_render(path) for path in paths]
    set_findings: list[str] = []
    if len(paths) != expected_count:
        set_findings.append(f"render-count:{len(paths)}:{expected_count}")
    eye_height_count = sum(
        "eye165" in path.stem.lower()
        or "player165" in path.stem.lower()
        or "eye-165" in path.stem.lower()
        for path in paths
    )
    if eye_height_count < minimum_eye_height_views:
        set_findings.append(
            f"insufficient-eye-height-views:{eye_height_count}:{minimum_eye_height_views}"
        )
    hashes = [item["sha256"] for item in renders]
    if len(hashes) != len(set(hashes)):
        set_findings.append("duplicate-render-frame")
    failed_views = [item["path"] for item in renders if not item["ok"]]
    return {
        "schemaVersion": 1,
        "gate": {
            "expectedRenderCount": expected_count,
            "minimumEyeHeightViews": minimum_eye_height_views,
            "technicalPreGateOnly": True,
            "humanReferenceReviewStillRequired": True,
        },
        "summary": {
            "renderCount": len(renders),
            "eyeHeightViewCount": eye_height_count,
            "failedViewCount": len(failed_views),
        },
        "setFindings": set_findings,
        "failedViews": failed_views,
        "renders": renders,
        "ok": not set_findings and not failed_views,
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expect-count", type=int, default=8)
    parser.add_argument("--minimum-eye-height-views", type=int, default=4)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_render_set(
        args.render_dir,
        expected_count=args.expect_count,
        minimum_eye_height_views=args.minimum_eye_height_views,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
