#!/usr/bin/env python3
"""Audit Blender stage renders against private ImageGen references.

Pixel metrics are diagnostic only: they may identify an empty blockout, crushed
shadows, or a materially flat render, but they cannot prove architectural or
artistic equivalence.  A release PASS therefore also requires a signed human
scorecard with every category >= 7 and an average >= 8.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageFilter


HUMAN_CATEGORIES = (
    "composition",
    "heroSilhouettes",
    "architecturalGrammar",
    "facadeOpeningQuality",
    "humanScale",
    "materialRealism",
    "nearMidFarDensity",
    "terrainAndWorldContinuity",
    "landmarkInteriorLegibility",
    "gameplayReadability",
    "propsAndStorytelling",
    "lightingAndAtmosphere",
    "referenceIdentity",
)
MIN_HUMAN_CATEGORY = 7.0
MIN_HUMAN_AVERAGE = 8.0
ANALYSIS_SIZE = (512, 288)


@dataclass(frozen=True)
class ImageMetrics:
    width: int
    height: int
    edgeDensity: float
    middleEdgeDensity: float
    luminanceMean: float
    luminanceStdDev: float
    nearBlackRatio: float
    highlightRatio: float
    entropy: float
    occupiedColorBins: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ratio(value: float) -> float:
    return round(float(value), 6)


def image_metrics(path: Path) -> ImageMetrics:
    with Image.open(path) as source:
        rgb = source.convert("RGB")
        width, height = rgb.size
        sample = rgb.resize(ANALYSIS_SIZE, Image.Resampling.LANCZOS)

    array = np.asarray(sample, dtype=np.float32)
    luminance = (
        array[:, :, 0] * 0.2126
        + array[:, :, 1] * 0.7152
        + array[:, :, 2] * 0.0722
    )
    edges = np.asarray(
        sample.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32
    )
    # Threshold deliberately ignores texture-compression noise while retaining
    # facade, prop and skyline structure.
    edge_mask = edges >= 28.0
    middle = edge_mask[ANALYSIS_SIZE[1] // 4 : ANALYSIS_SIZE[1] * 3 // 4, :]

    hist, _ = np.histogram(luminance, bins=64, range=(0.0, 256.0))
    probability = hist.astype(np.float64) / max(1, hist.sum())
    probability = probability[probability > 0]
    entropy = -float(np.sum(probability * np.log2(probability)))

    # Coarse RGB occupancy is a stable proxy for palette diversity, not quality.
    coarse = np.floor(array / 32.0).astype(np.int16)
    codes = coarse[:, :, 0] * 64 + coarse[:, :, 1] * 8 + coarse[:, :, 2]
    counts = np.bincount(codes.reshape(-1), minlength=512)
    occupied = int(np.count_nonzero(counts >= max(4, codes.size * 0.001)))

    return ImageMetrics(
        width=width,
        height=height,
        edgeDensity=_ratio(np.mean(edge_mask)),
        middleEdgeDensity=_ratio(np.mean(middle)),
        luminanceMean=round(float(np.mean(luminance)), 3),
        luminanceStdDev=round(float(np.std(luminance)), 3),
        nearBlackRatio=_ratio(np.mean(luminance < 18.0)),
        highlightRatio=_ratio(np.mean(luminance > 245.0)),
        entropy=round(entropy, 4),
        occupiedColorBins=occupied,
    )


def diagnostic_findings(reference: ImageMetrics, render: ImageMetrics) -> list[str]:
    findings: list[str] = []
    if render.edgeDensity < reference.edgeDensity * 0.55:
        findings.append("low-full-frame-structural-density")
    if render.middleEdgeDensity < reference.middleEdgeDensity * 0.55:
        findings.append("low-play-space-structural-density")
    if render.occupiedColorBins < max(8, round(reference.occupiedColorBins * 0.45)):
        findings.append("material-palette-collapse")
    if render.luminanceStdDev < reference.luminanceStdDev * 0.55:
        findings.append("flat-tonal-response")
    if render.nearBlackRatio > max(0.18, reference.nearBlackRatio * 3.0):
        findings.append("crushed-dark-regions")
    if render.highlightRatio > max(0.12, reference.highlightRatio * 4.0):
        findings.append("clipped-highlights")
    if render.entropy < reference.entropy * 0.72:
        findings.append("low-image-information")
    return findings


def load_human_scorecard(path: Path, stage_id: str, reference_sha: str, render_sha: str) -> dict:
    if not path.exists():
        return {
            "present": False,
            "ok": False,
            "errors": ["missing-human-scorecard"],
            "scores": {},
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if raw.get("stageId") != stage_id:
        errors.append("stage-id-mismatch")
    if raw.get("referenceSha256") != reference_sha:
        errors.append("reference-sha-mismatch")
    if raw.get("renderSha256") != render_sha:
        errors.append("render-sha-mismatch")
    if not str(raw.get("reviewer", "")).strip():
        errors.append("missing-reviewer")
    if not str(raw.get("notes", "")).strip():
        errors.append("missing-notes")

    scores = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    normalized: dict[str, float] = {}
    for category in HUMAN_CATEGORIES:
        value = scores.get(category)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"missing-score:{category}")
            continue
        number = float(value)
        if not math.isfinite(number) or number < 0 or number > 10:
            errors.append(f"invalid-score:{category}")
            continue
        normalized[category] = number
        if number < MIN_HUMAN_CATEGORY:
            errors.append(f"below-category-gate:{category}")

    average = statistics.fmean(normalized.values()) if len(normalized) == len(HUMAN_CATEGORIES) else 0.0
    if average < MIN_HUMAN_AVERAGE:
        errors.append("below-average-gate")
    if raw.get("verdict") != "SHIP":
        errors.append("human-verdict-not-ship")
    return {
        "present": True,
        "ok": not errors,
        "errors": errors,
        "reviewer": raw.get("reviewer"),
        "notes": raw.get("notes"),
        "verdict": raw.get("verdict"),
        "scores": normalized,
        "average": round(average, 3),
    }


def catalog_stage_ids(catalog_path: Path) -> list[str]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    stages = catalog.get("stages")
    if not isinstance(stages, list):
        raise ValueError("catalog.stages must be an array")
    ids = [stage.get("id") for stage in stages]
    if any(not isinstance(stage_id, str) or not stage_id for stage_id in ids):
        raise ValueError("every catalog stage must have a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("catalog stage IDs must be unique")
    return ids


def _find_image(directory: Path, stage_id: str, suffix: str) -> Path:
    exact = directory / f"{stage_id}{suffix}"
    if exact.exists():
        return exact
    candidates = sorted(directory.glob(f"{stage_id}.*"))
    candidates = [path for path in candidates if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"expected exactly one render for {stage_id} in {directory}; found {len(candidates)}"
        )
    return candidates[0]


def audit_stage(stage_id: str, reference: Path, render: Path, scorecard: Path) -> dict:
    reference_sha = _sha256(reference)
    render_sha = _sha256(render)
    reference_metrics = image_metrics(reference)
    render_metrics = image_metrics(render)
    findings = diagnostic_findings(reference_metrics, render_metrics)
    human = load_human_scorecard(scorecard, stage_id, reference_sha, render_sha)
    return {
        "stageId": stage_id,
        "ok": human["ok"] and not findings,
        "reference": {"path": str(reference), "sha256": reference_sha, "metrics": asdict(reference_metrics)},
        "render": {"path": str(render), "sha256": render_sha, "metrics": asdict(render_metrics)},
        "diagnosticFindings": findings,
        "humanReview": human,
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("tools/blender/stage-world.catalog.json"))
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--render-dir", type=Path, required=True)
    parser.add_argument("--scorecard-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", action="append", dest="stages")
    parser.add_argument("--render-suffix", default=".png")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    catalog_ids = catalog_stage_ids(args.catalog)
    requested = args.stages or catalog_ids
    unknown = sorted(set(requested) - set(catalog_ids))
    if unknown:
        raise ValueError(f"unknown stages: {', '.join(unknown)}")

    stages: list[dict] = []
    failures: list[dict] = []
    for stage_id in requested:
        try:
            reference = _find_image(args.reference_dir, f"{stage_id}-reference-v1", ".png")
            render = _find_image(args.render_dir, stage_id, args.render_suffix)
            scorecard = args.scorecard_dir / f"{stage_id}.json"
            result = audit_stage(stage_id, reference, render, scorecard)
            stages.append(result)
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as error:
            failures.append({"stageId": stage_id, "error": str(error)})

    report = {
        "schemaVersion": 1,
        "gate": {
            "humanCategories": list(HUMAN_CATEGORIES),
            "minimumCategory": MIN_HUMAN_CATEGORY,
            "minimumAverage": MIN_HUMAN_AVERAGE,
            "pixelMetricsAreDiagnosticOnly": True,
        },
        "summary": {
            "requested": len(requested),
            "audited": len(stages),
            "passed": sum(1 for stage in stages if stage["ok"]),
            "failed": sum(1 for stage in stages if not stage["ok"]) + len(failures),
        },
        "ok": not failures and all(stage["ok"] for stage in stages),
        "stages": stages,
        "loadFailures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
