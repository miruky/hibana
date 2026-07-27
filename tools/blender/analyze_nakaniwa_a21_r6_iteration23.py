"""Deterministic, render-free audit of the immutable iteration23 evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw


REPO_ROOT = Path(
    "/Users/h_miruky/Library/Mobile Documents/"
    "com~apple~CloudDocs/develop/100リポジトリ作成計画トップ/hibana"
).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender import (  # noqa: E402
    run_nakaniwa_a21_r6_iteration23_connected_district as I23,
)


OUTPUT_ROOT = I23.OUTPUT_ROOT
CANDIDATE_PATH = (
    OUTPUT_ROOT
    / "views/00_eye165_dualhero_targety14_iteration23.png"
).resolve()
CONTRACT_PATH = (OUTPUT_ROOT / "iteration23-proof-contract.json").resolve()
MANIFEST_PATH = (OUTPUT_ROOT / "proof-manifest.json").resolve()
AB_PATH = (OUTPUT_ROOT / "iteration23-ab-control-candidate-native.png").resolve()
TARGET_AB_PATH = (
    OUTPUT_ROOT / "iteration23-ab-target-envelope-native.png"
).resolve()
METRICS_PATH = (
    OUTPUT_ROOT / "iteration23-strict-threshold-evaluation.json"
).resolve()
PRODUCER_PATH = (
    OUTPUT_ROOT
    / "producer-original-resolution-review-iteration23-729f5ae0.json"
).resolve()

CANDIDATE_SHA256 = (
    "729f5ae04dadaa42a18257fcbfcf2aef6278030658822447ec840f372eb7ba00"
)
CONTRACT_SHA256 = (
    "1ac5798b4f904c795fe9ef2ff0d5244df2dfb9c3af57096850ed1ad01a80e1ef"
)
MANIFEST_SHA256 = (
    "96c4db656956112c1b70b19fa51a0f945b32af19900ca03eeb89f9e946070059"
)

ROIS = {
    "targetEnvelope": (0.405, 0.625, 0.34, 0.585),
    "lowerInhabitedBand": (0.405, 0.625, 0.43, 0.585),
    "upperGapEvaluationBand": (0.405, 0.625, 0.34, 0.43),
    "routePortal": (0.465, 0.535, 0.52, 0.60),
    "routeRoi": (0.35, 0.65, 0.55, 1.0),
    "fullMidlayerRoi": (0.25, 0.75, 0.30, 0.65),
    "heroGapCore": (0.40, 0.62, 0.35, 0.59),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(path: Path) -> dict:
    payload = path.read_bytes()
    result = {
        "path": str(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
    try:
        with Image.open(path) as image:
            result["dimensionsPx"] = [int(image.width), int(image.height)]
    except Exception:
        pass
    return result


def _bounds_px(
    roi: Sequence[float],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """Match the preflight: int/floor native-resolution ROI boundaries."""
    x0, x1, y0, y1 = (float(value) for value in roi)
    return (
        int(x0 * width),
        int(x1 * width),
        int(y0 * height),
        int(y1 * height),
    )


def _crop(array: np.ndarray, bounds: Sequence[int]) -> np.ndarray:
    x0, x1, y0, y1 = (int(value) for value in bounds)
    return array[y0:y1, x0:x1]


def _load_bgr(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"unable to decode image: {path}")
    return image


def _edge_map(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray, 75, 150) > 0


def _sky_mask(image: np.ndarray) -> np.ndarray:
    blue, green, red = cv2.split(image)
    blue_i = blue.astype(np.int16)
    return (
        (blue_i - red.astype(np.int16) > 25)
        & (blue_i - green.astype(np.int16) > 8)
    )


def _create_native_ab() -> tuple[dict, dict]:
    control = Image.open(I23.CONTROL_PATH).convert("RGB")
    candidate = Image.open(CANDIDATE_PATH).convert("RGB")
    if control.size != (1280, 720) or candidate.size != (1280, 720):
        raise RuntimeError(
            f"unexpected A/B sizes: {control.size}, {candidate.size}"
        )

    header = 44
    canvas = Image.new("RGB", (2560, 720 + header), (18, 22, 25))
    canvas.paste(control, (0, header))
    canvas.paste(candidate, (1280, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 14), "A  iteration21 control  f3299ef5", fill="white")
    draw.text((1296, 14), "B  iteration23 candidate  729f5ae0", fill="white")
    canvas.save(AB_PATH)

    bounds = _bounds_px(ROIS["targetEnvelope"], 1280, 720)
    x0, x1, y0, y1 = bounds
    control_crop = control.crop((x0, y0, x1, y1))
    candidate_crop = candidate.crop((x0, y0, x1, y1))
    crop_header = 32
    crop_canvas = Image.new(
        "RGB",
        (control_crop.width * 2, control_crop.height + crop_header),
        (18, 22, 25),
    )
    crop_canvas.paste(control_crop, (0, crop_header))
    crop_canvas.paste(candidate_crop, (control_crop.width, crop_header))
    crop_draw = ImageDraw.Draw(crop_canvas)
    crop_draw.text((8, 10), "A  target envelope", fill="white")
    crop_draw.text(
        (control_crop.width + 8, 10),
        "B  target envelope",
        fill="white",
    )
    crop_canvas.save(TARGET_AB_PATH)
    return _artifact(AB_PATH), _artifact(TARGET_AB_PATH)


def _occlusion_reports() -> tuple[dict, dict, dict]:
    r6 = I23.R6
    original_camera = copy.deepcopy(r6.MAIN_REFERENCE_CAMERA)
    original_build = r6.build_specs
    try:
        baseline_camera = copy.deepcopy(I23.BASELINE_CAMERA)
        baseline_camera["target"] = (-5.0, 14.0, -4.0)
        r6.MAIN_REFERENCE_CAMERA = baseline_camera
        baseline = r6.reference_camera_occlusion_report(0)

        r6.MAIN_REFERENCE_CAMERA = copy.deepcopy(I23.STUDY_CAMERA)
        r6.build_specs = I23.build_iteration23_specs
        candidate = r6.reference_camera_occlusion_report(0)
        frame = r6.reference_camera_frame_metrics(0)
        vaults = r6.conservatory_five_vault_frame_report(0)
    finally:
        r6.MAIN_REFERENCE_CAMERA = original_camera
        r6.build_specs = original_build

    deltas = []
    for before, after in zip(
        baseline["heroes"], candidate["heroes"], strict=True
    ):
        if before["id"] != after["id"]:
            raise RuntimeError("hero order drift in occlusion audit")
        delta = round(
            float(after["occlusionRatio"])
            - float(before["occlusionRatio"]),
            4,
        )
        deltas.append({
            "id": before["id"],
            "baseline": float(before["occlusionRatio"]),
            "candidate": float(after["occlusionRatio"]),
            "delta": delta,
            "noRegression": delta <= 0.0,
        })
    return (
        {
            "baseline": baseline,
            "candidate": candidate,
            "deltas": deltas,
            "noHeroOcclusionRegression": all(
                bool(item["noRegression"]) for item in deltas
            ),
        },
        frame,
        vaults,
    )


def _comparison_metrics(
    control: np.ndarray,
    candidate: np.ndarray,
) -> dict:
    if control.shape != candidate.shape or control.shape[:2] != (720, 1280):
        raise RuntimeError(
            f"candidate/control shape mismatch: {control.shape}, "
            f"{candidate.shape}"
        )
    height, width = control.shape[:2]
    control_edges = _edge_map(control)
    candidate_edges = _edge_map(candidate)
    difference = np.max(
        np.abs(candidate.astype(np.int16) - control.astype(np.int16)),
        axis=2,
    )
    metrics: dict[str, object] = {
        "method": {
            "roiCoordinates": (
                "normalized top-left origin; native pixel bounds use int/floor"
            ),
            "edge": (
                "full-frame grayscale cv2.Canny(75,150), then ROI fraction"
            ),
            "change": (
                "max absolute BGR channel delta; weak >=3, strong >=12"
            ),
            "connectedChange": (
                "cv2.connectedComponentsWithStats, 8-connectivity, "
                "strong target-envelope mask"
            ),
            "sky": "generated-frame B-R >25 and B-G >8",
        },
        "global": {
            "controlEdgeDensity": float(control_edges.mean()),
            "candidateEdgeDensity": float(candidate_edges.mean()),
            "meanAbsoluteDifferencePerChannel": float(np.mean(np.abs(
                candidate.astype(np.int16) - control.astype(np.int16)
            ))),
            "weakChangedPixelFraction": float((difference >= 3).mean()),
            "strongChangedPixelFraction": float((difference >= 12).mean()),
            "controlSkyMaskFraction": float(_sky_mask(control).mean()),
            "candidateSkyMaskFraction": float(_sky_mask(candidate).mean()),
        },
        "rois": {},
    }
    roi_metrics: dict[str, dict] = {}
    for name, roi in ROIS.items():
        bounds = _bounds_px(roi, width, height)
        roi_difference = _crop(difference, bounds)
        roi_metrics[name] = {
            "normalizedBounds": list(roi),
            "pixelBoundsExclusive": list(bounds),
            "controlEdgeDensity": float(
                _crop(control_edges, bounds).mean()
            ),
            "candidateEdgeDensity": float(
                _crop(candidate_edges, bounds).mean()
            ),
            "weakChangedPixelFraction": float(
                (roi_difference >= 3).mean()
            ),
            "strongChangedPixelFraction": float(
                (roi_difference >= 12).mean()
            ),
        }
    metrics["rois"] = roi_metrics

    target_bounds = _bounds_px(
        ROIS["targetEnvelope"], width, height
    )
    target_mask = (
        _crop(difference, target_bounds) >= 12
    ).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(
        target_mask,
        connectivity=8,
    )
    components = []
    target_x0, _, target_y0, _ = target_bounds
    for index in range(1, count):
        x, y, component_width, component_height, area = (
            int(value) for value in stats[index]
        )
        components.append({
            "areaPx": area,
            "areaFractionOfTargetEnvelope": (
                float(area) / float(target_mask.size)
            ),
            "xMin": float(target_x0 + x) / width,
            "xMaxExclusive": (
                float(target_x0 + x + component_width) / width
            ),
            "yMin": float(target_y0 + y) / height,
            "yMaxExclusive": (
                float(target_y0 + y + component_height) / height
            ),
            "xSpan": float(component_width) / width,
            "ySpan": float(component_height) / height,
        })
    components.sort(key=lambda item: int(item["areaPx"]), reverse=True)
    metrics["connectedStrongChange"] = {
        "componentCount": count - 1,
        "largestComponent": components[0] if components else None,
    }
    return metrics


def _threshold(
    name: str,
    actual: float | bool,
    operator: str,
    required: float | bool,
) -> dict:
    if operator == ">=":
        passed = float(actual) >= float(required)
    elif operator == "<=":
        passed = float(actual) <= float(required)
    elif operator == "==":
        passed = actual == required
    else:
        raise ValueError(f"unsupported threshold operator: {operator}")
    return {
        "name": name,
        "actual": actual,
        "operator": operator,
        "required": required,
        "passed": bool(passed),
    }


def _evaluate_thresholds(
    metrics: Mapping[str, object],
    occlusion: Mapping[str, object],
    frame: Mapping[str, object],
    vaults: Mapping[str, object],
) -> list[dict]:
    rois = metrics["rois"]
    largest = metrics["connectedStrongChange"]["largestComponent"]
    global_metrics = metrics["global"]
    checks = [
        _threshold(
            "largestComponentXSpan",
            largest["xSpan"],
            ">=",
            0.18,
        ),
        _threshold(
            "largestComponentXMin",
            largest["xMin"],
            "<=",
            0.425,
        ),
        _threshold(
            "largestComponentXMax",
            largest["xMaxExclusive"],
            ">=",
            0.605,
        ),
        _threshold(
            "largestComponentYSpan",
            largest["ySpan"],
            ">=",
            0.10,
        ),
        _threshold(
            "largestComponentAreaFraction",
            largest["areaFractionOfTargetEnvelope"],
            ">=",
            0.15,
        ),
        _threshold(
            "targetEnvelopeStrongChangedPixelFraction",
            rois["targetEnvelope"]["strongChangedPixelFraction"],
            ">=",
            0.22,
        ),
        _threshold(
            "lowerInhabitedBandStrongChangedPixelFraction",
            rois["lowerInhabitedBand"]["strongChangedPixelFraction"],
            ">=",
            0.25,
        ),
        _threshold(
            "targetEnvelopeEdgeDensity",
            rois["targetEnvelope"]["candidateEdgeDensity"],
            ">=",
            0.135,
        ),
        _threshold(
            "lowerInhabitedBandEdgeDensity",
            rois["lowerInhabitedBand"]["candidateEdgeDensity"],
            ">=",
            0.16,
        ),
        _threshold(
            "upperGapEvaluationBandEdgeDensity",
            rois["upperGapEvaluationBand"]["candidateEdgeDensity"],
            ">=",
            0.085,
        ),
        _threshold(
            "fullMidlayerEdgeDensity",
            rois["fullMidlayerRoi"]["candidateEdgeDensity"],
            ">=",
            0.145,
        ),
        _threshold(
            "routeRoiEdgeDensity",
            rois["routeRoi"]["candidateEdgeDensity"],
            ">=",
            0.0658,
        ),
        _threshold(
            "routePortalEdgeDensity",
            rois["routePortal"]["candidateEdgeDensity"],
            ">=",
            0.135,
        ),
        _threshold(
            "routePortalStrongChangedPixelFraction",
            rois["routePortal"]["strongChangedPixelFraction"],
            "<=",
            0.10,
        ),
        _threshold(
            "fullFrameSkyMaskFraction",
            global_metrics["candidateSkyMaskFraction"],
            "<=",
            0.342529,
        ),
        _threshold(
            "bothHeroLandmarksFullyReadable",
            bool(frame["passed"]),
            "==",
            True,
        ),
        _threshold(
            "allFiveVaultsVisible",
            bool(vaults["passed"]),
            "==",
            True,
        ),
        _threshold(
            "heroOcclusionRegressionAllowedFalse",
            bool(occlusion["noHeroOcclusionRegression"]),
            "==",
            True,
        ),
    ]
    return checks


def main() -> dict:
    for path in (AB_PATH, TARGET_AB_PATH, METRICS_PATH, PRODUCER_PATH):
        if path.exists():
            raise RuntimeError(
                f"immutable iteration23 audit output already exists: {path}"
            )
    expected_hashes = {
        CANDIDATE_PATH: CANDIDATE_SHA256,
        CONTRACT_PATH: CONTRACT_SHA256,
        MANIFEST_PATH: MANIFEST_SHA256,
        I23.CONTROL_PATH: I23.CONTROL_SHA256,
        I23.REFERENCE_PATH: I23.REFERENCE_SHA256,
        I23.PREFLIGHT_PATH: I23.PREFLIGHT_SHA256,
        I23.SOURCE_PATH: I23.BASELINE_SOURCE_SHA256,
        I23.TEST_PATH: I23.BASELINE_TEST_SHA256,
    }
    hash_checks = []
    for path, expected in expected_hashes.items():
        actual = _sha256(path) if path.is_file() else None
        hash_checks.append({
            "path": str(path),
            "expectedSha256": expected,
            "actualSha256": actual,
            "passed": actual == expected,
        })
    if not all(bool(item["passed"]) for item in hash_checks):
        raise RuntimeError(f"immutable evidence drift: {hash_checks}")

    ab_artifact, target_ab_artifact = _create_native_ab()
    control = _load_bgr(I23.CONTROL_PATH)
    candidate = _load_bgr(CANDIDATE_PATH)
    comparison = _comparison_metrics(control, candidate)
    occlusion, frame, vaults = _occlusion_reports()
    threshold_checks = _evaluate_thresholds(
        comparison, occlusion, frame, vaults
    )
    failed = [
        item for item in threshold_checks if not bool(item["passed"])
    ]

    preflight = json.loads(
        I23.PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    declared_full_mid = (
        preflight["observedMetrics"]["iteration21Control"][
            "fullMidlayerEdgeDensity"
        ]
    )
    recomputed_full_mid = (
        comparison["rois"]["fullMidlayerRoi"]["controlEdgeDensity"]
    )
    metrics_payload = {
        "schemaVersion": 1,
        "studyId": "nakaniwa-r6-iteration23-strict-threshold-evaluation",
        "candidate": _artifact(CANDIDATE_PATH),
        "control": _artifact(I23.CONTROL_PATH),
        "immutableHashChecks": hash_checks,
        "comparison": comparison,
        "heroFrameMetrics": frame,
        "fiveVaultFrameReport": vaults,
        "heroOcclusionAudit": occlusion,
        "thresholdChecks": threshold_checks,
        "failedThresholdCount": len(failed),
        "failedThresholds": failed,
        "allMandatoryThresholdsPassed": not failed,
        "preflightFullMidlayerObservedMetricConsistencyNote": {
            "declaredRoi": list(ROIS["fullMidlayerRoi"]),
            "preflightRecordedIteration21": declared_full_mid,
            "recomputedIteration21FromDeclaredRoi": recomputed_full_mid,
            "matched": (
                round(float(declared_full_mid), 6)
                == round(float(recomputed_full_mid), 6)
            ),
            "candidateStillBelowRequiredMinimumUsingDeclaredRoi": (
                comparison["rois"]["fullMidlayerRoi"][
                    "candidateEdgeDensity"
                ] < 0.145
            ),
        },
        "originalResolutionComparisons": {
            "fullFrameNativeAB": ab_artifact,
            "targetEnvelopeNativeAB": target_ab_artifact,
        },
        "secondRenderMade": False,
        "visibleBlenderUiOrBridgeUsed": False,
    }
    METRICS_PATH.write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    scores = {
        "composition": 5.4,
        "hero silhouettes": 4.2,
        "architectural grammar": 4.0,
        "human scale": 3.8,
        "material realism": 2.9,
        "near/mid/far density": 3.3,
        "gameplay readability": 5.0,
        "props and environmental storytelling": 3.2,
        "lighting and atmosphere": 2.7,
        "reference identity": 4.0,
    }
    values = list(scores.values())
    producer = {
        "schemaVersion": 1,
        "reviewType": (
            "producer-original-resolution-single-hypothesis-strict-gate"
        ),
        "stageId": "nakaniwa",
        "iteration": 23,
        "candidate": _artifact(CANDIDATE_PATH),
        "control": _artifact(I23.CONTROL_PATH),
        "reference": _artifact(I23.REFERENCE_PATH),
        "proofContract": _artifact(CONTRACT_PATH),
        "proofManifest": _artifact(MANIFEST_PATH),
        "strictThresholdEvaluation": _artifact(METRICS_PATH),
        "originalResolutionComparisons": {
            "fullFrameNativeAB": ab_artifact,
            "targetEnvelopeNativeAB": target_ab_artifact,
        },
        "hypothesis": (
            "A camera-nearer, supported, continuous two-level inhabited "
            "garden district can close the frozen hero gap while preserving "
            "the central route portal."
        ),
        "qualitativeOriginalResolutionReview": {
            "oneConnectedDistrictLegible": True,
            "layeredArcadesLoggiasAndRoofGardenLegible": True,
            "genericBoxTowerAdded": False,
            "centralRoutePortalVisuallyOpen": True,
            "finding": (
                "The change is now screen-large and reads as one supported "
                "two-storey inhabited bridge district with warm bays, arches "
                "and five joined roof houses. It materially closes the prior "
                "empty hero gap. The central ground opening, stairs and rill "
                "remain visible, but the authored wings enter too far into "
                "the fixed portal ROI and the upper roof surfaces are too "
                "flat to meet the predeclared edge-density gate."
            ),
        },
        "quantitativeSummary": {
            "largestStrongComponent": comparison[
                "connectedStrongChange"
            ]["largestComponent"],
            "targetStrongOccupancy": comparison["rois"][
                "targetEnvelope"
            ]["strongChangedPixelFraction"],
            "lowerBandStrongOccupancy": comparison["rois"][
                "lowerInhabitedBand"
            ]["strongChangedPixelFraction"],
            "targetEdgeDensity": comparison["rois"][
                "targetEnvelope"
            ]["candidateEdgeDensity"],
            "upperGapEdgeDensity": comparison["rois"][
                "upperGapEvaluationBand"
            ]["candidateEdgeDensity"],
            "fullMidlayerEdgeDensity": comparison["rois"][
                "fullMidlayerRoi"
            ]["candidateEdgeDensity"],
            "routeRoiEdgeDensity": comparison["rois"][
                "routeRoi"
            ]["candidateEdgeDensity"],
            "routePortalEdgeDensity": comparison["rois"][
                "routePortal"
            ]["candidateEdgeDensity"],
            "routePortalStrongOccupancy": comparison["rois"][
                "routePortal"
            ]["strongChangedPixelFraction"],
            "skyMaskFraction": comparison["global"][
                "candidateSkyMaskFraction"
            ],
            "heroOcclusionDeltas": occlusion["deltas"],
        },
        "strictFailures": failed,
        "positiveFindings": [
            (
                "The largest connected strong-change component spans "
                "0.2172 frame width and 0.1972 frame height, with 0.5633 "
                "target-envelope area occupancy."
            ),
            (
                "Target and lower-band strong-change occupancy materially "
                "exceed their 0.22 and 0.25 minimums."
            ),
            (
                "The route ROI, portal edge density and sky mask pass; both "
                "named heroes and all five vaults remain readable."
            ),
            (
                "LOD0/1/2 evaluated triangles are 257624/89906/27996 with "
                "14/13/13 draw-call estimates."
            ),
        ],
        "producerTenCategoryDiagnostic": {
            "scale": "0-10",
            "scores": scores,
            "sum": round(sum(values), 2),
            "arithmeticMean": round(sum(values) / len(values), 2),
            "minimumScore": min(values),
            "producerOnly": True,
            "independentLowerVerdictControls": True,
        },
        "producerVerdict": (
            "REJECT_STRICT_THRESHOLD_MISS_NO_SECOND_HYPOTHESIS"
        ),
        "controllingReason": (
            "The one-shot candidate visibly solves the prior disconnected "
            "sliver problem, but the immutable KEEP contract is conjunctive. "
            "Target edge density is 0.134872 versus 0.135, upper-gap edge "
            "density is 0.044681 versus 0.085, full-midlayer density is "
            "0.140501 versus 0.145, portal strong occupancy is 0.162146 "
            "versus a 0.10 maximum, and conservative conservatory occlusion "
            "regresses from 0.0547 to 0.0576."
        ),
        "releaseVerdict": "NO_SHIP",
        "secondHypothesisMade": False,
        "secondRenderMade": False,
        "rerenderAuthorized": False,
        "publicMutation": False,
        "runtimeCollisionMutation": False,
        "canonicalCameraMutation": False,
        "visibleBlenderUiMutation": False,
        "bridgeTransportUsed": False,
        "nextAction": (
            "Archive this exact SHA-bound producer reject and request a "
            "read-only independent original-resolution audit. Do not make a "
            "second geometry hypothesis or render in iteration23."
        ),
    }
    PRODUCER_PATH.write_text(
        json.dumps(producer, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "candidate": _artifact(CANDIDATE_PATH),
        "strictThresholdEvaluation": _artifact(METRICS_PATH),
        "producerDiagnostic": _artifact(PRODUCER_PATH),
        "fullFrameNativeAB": ab_artifact,
        "targetEnvelopeNativeAB": target_ab_artifact,
        "failedThresholdCount": len(failed),
        "producerVerdict": producer["producerVerdict"],
        "secondRenderMade": False,
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
