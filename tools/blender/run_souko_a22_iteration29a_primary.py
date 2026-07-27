"""Reviewed headless MCP entry point for Souko iteration29-A primary proof."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(
    "/Users/h_miruky/Library/Mobile Documents/"
    "com~apple~CloudDocs/develop/100リポジトリ作成計画トップ/hibana"
).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import souko_reference_a22 as A22  # noqa: E402

import bpy  # noqa: E402


EXEC_ARGS = globals().get("args", {})
width = int(EXEC_ARGS.get("width", 1280))
height = int(EXEC_ARGS.get("height", 720))
view_id = str(EXEC_ARGS.get("view", "primary"))

A22.PRIVATE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
input_records = A22._verify_inputs()
source_sha = A22._sha256(A22.MODULE_PATH)
proof = A22._render_proof(
    bpy,
    argparse.Namespace(
        action="proof",
        views=view_id,
        width=width,
        height=height,
    ),
    source_sha=source_sha,
    input_records=input_records,
)
producer = A22._write_producer_summary(
    proof, None, None, input_records,
)
manifest = A22._write_proof_manifest()
primary = proof["renders"][0]

__result__ = {
    "stageId": A22.STAGE_ID,
    "version": A22.REFERENCE_MATCH_VERSION,
    "sourceSha256": source_sha,
    "view": primary,
    "blendPath": proof["blendPath"],
    "blendSha256": proof["blendSha256"],
    "metrics": {
        "specCount": proof["metrics"]["specCount"],
        "estimatedTriangles": proof["metrics"]["estimatedTriangles"],
        "materialCount": proof["metrics"]["materialCount"],
        "connectionCount": proof["metrics"]["connectionCount"],
    },
    "routeIntrusions": A22.route_intrusions(A22.build_plan(0)),
    "shoreRouteIntrusions": A22.shore_route_intrusions(A22.build_plan(0)),
    "producerVerdict": producer["verdict"],
    "manifestArtifacts": manifest["artifactCount"],
}
