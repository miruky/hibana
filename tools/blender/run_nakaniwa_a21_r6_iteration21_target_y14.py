"""Reviewed headless-only Nakaniwa iteration21 proof-camera study.

This script leaves the source camera contract and visible Blender session
untouched.  Inside this factory-startup process only, it copies proof camera 0
and changes targetY from 30 m to 14 m.  All output stays in a dedicated child
of the private R6 production root.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy  # type: ignore


REPO_ROOT = Path(
    "/Users/h_miruky/Library/Mobile Documents/"
    "com~apple~CloudDocs/develop/100リポジトリ作成計画トップ/hibana"
).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6  # noqa: E402


OUTPUT_ROOT = (
    R6.PRIVATE_PRODUCTION_DEFAULT
    / "camera-study-target-y14-iteration21"
).resolve()
BASELINE_CAMERA = copy.deepcopy(R6.MAIN_REFERENCE_CAMERA)
BASELINE_PROOF_CAMERAS = copy.deepcopy(R6.PROOF_CAMERAS)
STUDY_CAMERA = copy.deepcopy(BASELINE_CAMERA)
STUDY_CAMERA["name"] = (
    "CAM_Nakaniwa_A21_Eye165_DualHero_TargetY14_Iteration21"
)
STUDY_CAMERA["target"] = (
    float(BASELINE_CAMERA["target"][0]),
    14.0,
    float(BASELINE_CAMERA["target"][2]),
)
STUDY_CAMERA["intent"] = (
    "private iteration21 targetY14 proof-camera study; "
    "geometry, materials, lighting, location, lens and gameplay frozen"
)

assert tuple(BASELINE_CAMERA["target"]) == (-5.0, 30.0, -4.0)
assert tuple(STUDY_CAMERA["location"]) == tuple(BASELINE_CAMERA["location"])
assert float(STUDY_CAMERA["lensMm"]) == float(BASELINE_CAMERA["lensMm"])
assert float(STUDY_CAMERA["sensorWidthMm"]) == float(
    BASELINE_CAMERA["sensorWidthMm"]
)
assert tuple(STUDY_CAMERA["resolution"]) == (1280, 720)
assert float(STUDY_CAMERA["eyeHeightM"]) == float(
    BASELINE_CAMERA["eyeHeightM"]
)
assert (
    float(STUDY_CAMERA["target"][0]),
    float(STUDY_CAMERA["target"][2]),
) == (
    float(BASELINE_CAMERA["target"][0]),
    float(BASELINE_CAMERA["target"][2]),
)

study_proof_cameras = list(copy.deepcopy(BASELINE_PROOF_CAMERAS))
study_proof_cameras[0] = STUDY_CAMERA
R6.MAIN_REFERENCE_CAMERA = STUDY_CAMERA
R6.PROOF_CAMERAS = tuple(study_proof_cameras)

try:
    manifest = R6.build_private_production(
        output_dir=OUTPUT_ROOT,
        layout_path=R6.CANONICAL_LAYOUT_DEFAULT,
        view_indices=(0,),
    )
finally:
    R6.MAIN_REFERENCE_CAMERA = BASELINE_CAMERA
    R6.PROOF_CAMERAS = BASELINE_PROOF_CAMERAS

render_path = Path(manifest["views"][0]).resolve()
render_image = bpy.data.images.load(str(render_path), check_existing=False)
actual_resolution = [int(render_image.size[0]), int(render_image.size[1])]
bpy.data.images.remove(render_image)
if actual_resolution != [1280, 720]:
    raise RuntimeError(
        f"iteration21 render resolution drift: {actual_resolution}"
    )

source_path = Path(R6.__file__).resolve()
runner_path = (
    REPO_ROOT
    / "tools/blender/run_nakaniwa_a21_r6_iteration21_target_y14.py"
).resolve()
camera_contract = {
    "schemaVersion": 1,
    "studyId": "nakaniwa-r6-iteration21-proof-camera-target-y14",
    "mutationScope": "headless-process-memory-only",
    "baselineProductionRoot": str(R6.PRIVATE_PRODUCTION_DEFAULT),
    "studyOutputRoot": str(OUTPUT_ROOT),
    "baselineCamera": BASELINE_CAMERA,
    "studyCamera": STUDY_CAMERA,
    "onlyIntentionalCameraDelta": {
        "field": "target[1]",
        "baseline": 30.0,
        "study": 14.0,
    },
    "frozenFields": [
        "geometry",
        "materials",
        "lighting",
        "canonicalGameplayRuntimeData",
        "landmarkHeightContract43m",
        "camera.location",
        "camera.lensMm",
        "camera.sensorWidthMm",
        "camera.resolution",
        "camera.eyeHeightM",
        "camera.target[0]",
        "camera.target[2]",
        "visibleBlenderUI",
    ],
    "actualResolution": actual_resolution,
    "render": {
        "path": str(render_path),
        "sha256": hashlib.sha256(render_path.read_bytes()).hexdigest(),
        "bytes": render_path.stat().st_size,
    },
    "manifest": {
        "path": str(manifest["manifest"]),
        "sha256": hashlib.sha256(
            Path(manifest["manifest"]).read_bytes()
        ).hexdigest(),
    },
    "productionSource": {
        "path": str(source_path),
        "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    },
    "reviewedRunner": {
        "path": str(runner_path),
        "sha256": hashlib.sha256(runner_path.read_bytes()).hexdigest(),
    },
    "publicMutation": False,
    "baselineReplacement": False,
    "bridgeOrVisibleUISessionUsed": False,
}
contract_path = OUTPUT_ROOT / "iteration21-camera-contract.json"
contract_path.write_text(
    json.dumps(camera_contract, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

__result__ = {
    "studyId": camera_contract["studyId"],
    "outputRoot": str(OUTPUT_ROOT),
    "render": camera_contract["render"],
    "cameraContract": {
        "path": str(contract_path),
        "sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
    },
    "manifest": camera_contract["manifest"],
    "actualResolution": actual_resolution,
    "lodArtifacts": [
        {
            "lod": artifact["lod"],
            "evaluatedTriangles": artifact["evaluatedTriangles"],
            "drawCallEstimate": artifact["drawCallEstimate"],
        }
        for artifact in manifest["lodArtifacts"]
    ],
}
