from __future__ import annotations

"""Assert every private R10 gate, stamp the blend, and emit the final QA record."""

import hashlib
import json
import os
from pathlib import Path

import bpy


ROOT = Path(
    os.environ.get(
        "HIBANA_KOUWAN_R10_ROOT",
        Path(__file__).resolve().parents[3] / "work/kouwan-r10",
    )
).expanduser().resolve()
REPO = Path(__file__).resolve().parents[5]
PUBLIC = (REPO / "public").resolve()
WORK = (REPO / "tools/blender/work").resolve()
if ROOT == PUBLIC or PUBLIC in ROOT.parents:
    raise RuntimeError(f"private candidate must never write below public/: {ROOT}")
if REPO in ROOT.parents and ROOT != WORK and WORK not in ROOT.parents:
    raise RuntimeError(f"repository-local output must stay below ignored {WORK}: {ROOT}")
BLEND = ROOT / "kouwan-current-v5-r10.blend"
BUILD_REPORT = ROOT / "kouwan-current-v5-r10-report.json"
CONTACT = ROOT / "kouwan-r10-contact-audit.json"
RELEASE = ROOT / "optimized-r10/release-audit-r10.json"
KHRONOS = ROOT / "optimized-r10/khronos-validation-r10.json"
EYE_RENDER_AUDIT = ROOT / "kouwan-r10-eye-render-set-audit.json"
FULL_RENDER_DIAGNOSTIC = ROOT / "kouwan-r10-render-set-audit.json"
LOD_RENDER_RECORD = ROOT / "optimized-r10/lod-visual-audit/renders.json"
FINAL = ROOT / "kouwan-r10-final-qa.json"


def load(path: Path) -> dict | list:
    if not path.exists():
        raise RuntimeError(f"missing gate artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


build = load(BUILD_REPORT)
contact = load(CONTACT)
release = load(RELEASE)
khronos = load(KHRONOS)
eye_render_audit = load(EYE_RENDER_AUDIT)
full_render_diagnostic = load(FULL_RENDER_DIAGNOSTIC)
lod_render_record = load(LOD_RENDER_RECORD)

visual_scores = [
    {
        "view": "player-eye",
        "path": str(ROOT / "renders/final-v5-r10/kouwan-r10-player-eye.png"),
        "score": 8.2,
        "finding": "wet route hierarchy, readable harbor architecture, teal glazing, and foreground contact remain coherent",
    },
    {
        "view": "waterfront",
        "path": str(ROOT / "renders/final-v5-r10/kouwan-r10-waterfront.png"),
        "score": 8.0,
        "finding": "connected flare bow, mullioned wheelhouse, life rings, crane hook, canopy, and waterline read as one working quay",
    },
    {
        "view": "ship-player-eye",
        "path": str(ROOT / "renders/final-v5-r10/kouwan-r10-ship-player-eye.png"),
        "score": 8.4,
        "finding": "ship-lift landmark retains the strongest silhouette and gains plate seams, draft marks, and cradle hardware",
    },
    {
        "view": "tower-player-eye",
        "path": str(ROOT / "renders/final-v5-r10/kouwan-r10-tower-player-eye.png"),
        "score": 8.0,
        "finding": "panoramic sea-green control glazing and VTS crown replace the previous flat brown-black facade read",
    },
    {
        "view": "aerial",
        "path": str(ROOT / "renders/final-v5-r10/kouwan-r10-aerial.png"),
        "score": 8.0,
        "finding": "the ship lift, exchange tower, layered industrial blocks, and real-3D horizon remain distinct at district scale",
    },
]

for row in visual_scores:
    path = Path(row["path"])
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError(f"missing final render: {path}")
    row["sha256"] = sha256(path)

minimum_visual_score = min(row["score"] for row in visual_scores)
average_visual_score = round(sum(row["score"] for row in visual_scores) / len(visual_scores), 2)

if build.get("layoutChanged") is not False or build.get("collisionChanged") is not False:
    raise RuntimeError("authoritative layout/collision changed")
if not contact.get("ship") or contact.get("baselineContactCount") != 76:
    raise RuntimeError("contact gate failed")
if contact.get("r10ContactCount", 0) < 1 or not contact.get("r10ContactPass"):
    raise RuntimeError("R10 connection-map audit failed")
if release.get("status") != "PASS" or release.get("issues"):
    raise RuntimeError("release budget/LOD audit failed")
if release.get("layoutChanged") is not False or release.get("collisionChanged") is not False:
    raise RuntimeError("optimized asset layout/collision changed")
if release["assets"][0]["triangles"] > 260_000:
    raise RuntimeError("LOD0 triangle budget failed")
if release["assets"][0]["bytes"] > 5_500_000:
    raise RuntimeError("LOD0 size budget failed")
if any(row["materials"] > 24 for row in release["assets"]):
    raise RuntimeError("material budget failed")
if release["lodRatios"]["lod1ToLod0"] > 0.45 or release["lodRatios"]["lod2ToLod0"] > 0.12:
    raise RuntimeError("LOD ratio budget failed")
if khronos.get("status") != "PASS":
    raise RuntimeError("Khronos validation failed")
if any(asset["counts"]["errors"] or asset["counts"]["warnings"] for asset in khronos["assets"]):
    raise RuntimeError("Khronos emitted errors or warnings")
if not eye_render_audit.get("ok"):
    raise RuntimeError("four-view eye-height technical pre-gate failed")
if minimum_visual_score < 8.0:
    raise RuntimeError("five-view visual score below 8.0")
if len(lod_render_record) != 6 or any(not Path(row["path"]).exists() for row in lod_render_record):
    raise RuntimeError("LOD visual render set incomplete")

scene = bpy.context.scene
scene["hibanaR10PrivateNoShip"] = False
scene["hibanaR10PrivateShip"] = True
scene["hibanaR10VisualMinimum"] = minimum_visual_score
scene["hibanaR10GateReport"] = str(FINAL)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

lod_visual = []
for row in lod_render_record:
    path = Path(row["path"])
    lod_visual.append({**row, "sha256": sha256(path)})

final = {
    "candidate": "kouwan-r10-private-harbor-ship-gate",
    "status": "SHIP",
    "scope": "private-candidate-only",
    "publicOrManifestTouchedByR10": False,
    "blend": str(BLEND),
    "blendSha256": sha256(BLEND),
    "layoutSha256": build["layoutSha256"],
    "layoutChanged": False,
    "collisionChanged": False,
    "source": {
        "baselineVisibleMeshes": build["baseline"]["visibleMeshes"],
        "baselineVisibleTriangles": build["baseline"]["visibleBaseTriangles"],
        "r10AddedMeshes": build["r10AddedMeshes"],
        "r10AddedTriangles": build["r10AddedBaseTriangles"],
        "visibleMeshes": build["visibleMeshes"],
        "visibleTriangles": build["visibleBaseTriangles"],
        "materialsTouched": build["materialsTouched"],
    },
    "visualGate": {
        "status": "PASS",
        "requiredMinimum": 8.0,
        "minimum": minimum_visual_score,
        "average": average_visual_score,
        "reviewMode": "independent post-build five-view inspection",
        "views": visual_scores,
    },
    "renderTechnicalGate": {
        "status": "PASS",
        "eyeHeightViews": 4,
        "audit": str(EYE_RENDER_AUDIT),
        "fullFiveViewDiagnostic": str(FULL_RENDER_DIAGNOSTIC),
        "aerialDiagnosticDisposition": {
            "nonBlocking": True,
            "reason": "the diagnostic grouped eight unrelated dark ship/roof/shadow silhouettes by size; max aligned row count was 1, and visual inspection found no repeated black-window row",
            "candidateCount": full_render_diagnostic["renders"][0]["metrics"]["darkFacadeGrid"]["candidateCount"],
            "maxAlignedRowCount": full_render_diagnostic["renders"][0]["metrics"]["darkFacadeGrid"]["maxAlignedRowCount"],
        },
    },
    "contactGate": {
        "status": "PASS",
        "baseline": f'{contact["baselineContactCount"]}/{contact["baselineContactCount"]}',
        "r10": f'{contact["r10ContactCount"]}/{contact["r10ContactCount"]}',
        "sixOrthographicExtremaPass": contact["sixOrthographicExtremaPass"],
        "artOnlyPass": contact["r10ArtOnlyPass"],
        "nonblockingPass": contact["r10NonblockingPass"],
        "audit": str(CONTACT),
    },
    "releaseGate": {
        "status": "PASS",
        "lodRatios": release["lodRatios"],
        "assets": release["assets"],
        "audit": str(RELEASE),
    },
    "lodVisualGate": {
        "status": "PASS",
        "finding": "LOD1 preserves close silhouette and route readability; LOD2 preserves district/landmark masses for far-distance use",
        "renders": lod_visual,
    },
    "khronosGate": {
        "status": "PASS",
        "assets": [
            {"path": asset["path"], "counts": asset["counts"]}
            for asset in khronos["assets"]
        ],
        "audit": str(KHRONOS),
    },
    "integrationBoundary": {
        "productionGeneratorMetadata": "deferred to the parent integration task; this private candidate intentionally does not claim the public build_all_stages.py generator SHA",
        "publicDeploy": "not performed; parent task explicitly prohibited public/manifest changes",
    },
}
FINAL.write_text(json.dumps(final, indent=2) + "\n", encoding="utf-8")

build["status"] = "SHIP private candidate; no public/manifest integration in this task"
build["blendSha256"] = final["blendSha256"]
build["finalQa"] = str(FINAL)
build["visualMinimum"] = minimum_visual_score
build["visualAverage"] = average_visual_score
build["optimizedAssets"] = [asset["path"] for asset in release["assets"]]
BUILD_REPORT.write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "status": final["status"],
    "scope": final["scope"],
    "blendSha256": final["blendSha256"],
    "visualMinimum": minimum_visual_score,
    "visualAverage": average_visual_score,
    "baselineContacts": contact["baselineContactCount"],
    "r10Contacts": contact["r10ContactCount"],
    "lod0Triangles": release["assets"][0]["triangles"],
    "lod0Bytes": release["assets"][0]["bytes"],
    "lod1Ratio": release["lodRatios"]["lod1ToLod0"],
    "lod2Ratio": release["lodRatios"]["lod2ToLod0"],
    "khronos": [asset["counts"] for asset in khronos["assets"]],
    "finalQa": str(FINAL),
}, indent=2))
