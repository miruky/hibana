#!/usr/bin/env python3
"""Fail fast when generated PBR texture files contain no usable signal.

Blender's ``Image.pixels.foreach_set`` writes into an in-memory image buffer.
Saving before ``Image.update()`` can produce valid PNG files whose pixels are
entirely black.  Those files load without errors, so geometry/render validators
do not catch the failure.  This gate inspects the encoded files themselves.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageStat


SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}


def texture_kind(path: Path) -> str | None:
    stem = path.stem.lower().replace("-", "_")
    if any(token in stem for token in ("basecolor", "base_color", "albedo", "diffuse")) or stem.endswith("_bc"):
        return "baseColor"
    if "normal" in stem or stem.endswith("_n"):
        return "normal"
    if "orm" in stem or "roughness" in stem or stem.endswith("_rma"):
        return "orm"
    return None


def iter_texture_paths(inputs: Iterable[str]) -> list[Path]:
    found: set[Path] = set()
    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            found.update(
                child
                for child in path.rglob("*")
                if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES and texture_kind(child)
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and texture_kind(path):
            found.add(path)
    return sorted(found)


def _finite(value: float) -> float:
    return round(value if math.isfinite(value) else 0.0, 3)


def inspect_texture(path: Path) -> dict:
    kind = texture_kind(path)
    assert kind is not None
    with Image.open(path) as source:
        image = source.convert("RGB")
        extrema = image.getextrema()
        stat = ImageStat.Stat(image)

    minimum = [int(pair[0]) for pair in extrema]
    maximum = [int(pair[1]) for pair in extrema]
    mean = [_finite(value) for value in stat.mean]
    stddev = [_finite(value) for value in stat.stddev]
    spans = [maximum[i] - minimum[i] for i in range(3)]
    issues: list[str] = []

    if max(maximum) <= 2:
        issues.append("all-black texture")
    elif min(minimum) >= 253:
        issues.append("all-white texture")
    elif kind != "normal" and max(spans) <= 2 and max(stddev) <= 1.0:
        issues.append("near-uniform texture")

    if kind == "baseColor" and not issues:
        luminance_span = max(maximum) - min(minimum)
        if luminance_span < 8 or max(stddev) < 2.0:
            issues.append("base-color has insufficient tonal signal")
    elif kind == "normal" and not issues:
        # Tangent-space normals need a positive blue component. A low value is
        # commonly an uninitialised/incorrectly encoded normal map.
        if mean[2] < 96:
            issues.append("normal map has invalid blue-channel baseline")
    elif kind == "orm" and not issues:
        # glTF ORM convention stores roughness in G. Either extreme produces a
        # visually dead surface and usually signals a failed procedural bake.
        if mean[1] <= 2 or mean[1] >= 253:
            issues.append("ORM roughness channel is empty or clipped")

    return {
        "path": str(path),
        "kind": kind,
        "size": list(image.size),
        "minimum": minimum,
        "maximum": maximum,
        "mean": mean,
        "stddev": stddev,
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
    }


def validate(inputs: Iterable[str]) -> dict:
    paths = iter_texture_paths(inputs)
    results = [inspect_texture(path) for path in paths]
    failures = [result for result in results if result["status"] == "FAIL"]
    return {
        "status": "FAIL" if failures or not results else "PASS",
        "textureCount": len(results),
        "failureCount": len(failures),
        "reason": "no recognised PBR textures found" if not results else None,
        "textures": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Texture files or directories to inspect")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = validate(args.inputs)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
