"""Reviewed Blender entry point for the private Nakaniwa A21 R6 main view."""

import sys
from pathlib import Path

REPO_ROOT = Path(
    "/Users/h_miruky/Library/Mobile Documents/"
    "com~apple~CloudDocs/develop/100リポジトリ作成計画トップ/hibana"
).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6  # noqa: E402


manifest = R6.build_private_production(
    output_dir=R6.PRIVATE_PRODUCTION_DEFAULT,
    layout_path=R6.CANONICAL_LAYOUT_DEFAULT,
    view_indices=(0,),
)

__result__ = {
    "kitVersion": manifest["kitVersion"],
    "manifest": manifest["manifest"],
    "views": manifest["views"],
    "lodArtifacts": [
        {
            "lod": artifact["lod"],
            "evaluatedTriangles": artifact["evaluatedTriangles"],
            "drawCallEstimate": artifact["drawCallEstimate"],
        }
        for artifact in manifest["lodArtifacts"]
    ],
}
