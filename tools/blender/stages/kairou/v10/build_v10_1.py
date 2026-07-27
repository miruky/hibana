#!/usr/bin/env python3
"""Rebuild Kairou V10.1 from tracked inputs without public writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command(args: list[str], records: list[dict[str, object]]) -> None:
    print("[kairou-v10.1]", " ".join(args), flush=True)
    result = subprocess.run(args, cwd=REPO, check=False)
    records.append({"command": args, "returnCode": result.returncode})
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}")


def verify_tracked_inputs(contract: dict[str, object]) -> None:
    for folder, key in ((HERE / "source", "source"), (HERE / "textures", "textures")):
        for name, expected in contract[key].items():
            path = folder / name
            if not path.is_file():
                raise RuntimeError(f"tracked input missing: {path}")
            actual = sha256(path)
            if actual != expected:
                raise RuntimeError(f"tracked input hash mismatch: {path}: {actual} != {expected}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, default=REPO / "tools/blender/work/kairou-v10.1")
    parser.add_argument("--blender", default=shutil.which("blender") or "/opt/homebrew/bin/blender")
    parser.add_argument("--node", default=shutil.which("node") or "node")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--skip-optimize", action="store_true")
    parser.add_argument(
        "--skip-legacy-upper",
        action="store_true",
        help="Omit the earlier floating upper-hero source when authoring the V6 connected silhouettes.",
    )
    parser.add_argument("--visual-score", type=float)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    work = args.work_dir.expanduser().resolve()
    allowed = (REPO / "tools/blender/work").resolve()
    if work != allowed and allowed not in work.parents:
        raise RuntimeError(f"work-dir must remain below ignored {allowed}: {work}")
    if (REPO / "public").resolve() in (work, *work.parents):
        raise RuntimeError("candidate build must not write below public/")
    screenshots = REPO / "tools/blender/screenshots/077-kairou-v10-repo-integration/repro-v10.1"
    contract = json.loads((HERE / "asset-contract.json").read_text(encoding="utf-8"))
    verify_tracked_inputs(contract)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    screenshots.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []

    contact = work / "contact"
    command([
        args.blender, "--background", "--factory-startup", "--python",
        str(HERE / "build_collision_skeleton.py"), "--", "--repo", str(REPO),
        "--output-root", str(contact),
    ], records)

    pbr_dir = work / "pbr"
    combined_dir = work / "combined"
    raw_dir = work / "raw"
    reports_dir = work / "reports"
    for directory in (pbr_dir, combined_dir, raw_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)

    surface_reports = []
    collision_reports = []
    for lod in (0, 1, 2):
        baseline = contact / "stages" / f"kairou-lod{lod}.glb"
        pbr = pbr_dir / f"kairou-lod{lod}.raw.glb"
        command([
            args.node, str(HERE / "apply_v10_1_pbr.mjs"),
            "--input", str(baseline), "--output", str(pbr),
            "--source-dir", str(HERE / "textures"),
            "--report", str(reports_dir / f"pbr-lod{lod}.json"),
        ], records)
        command([
            sys.executable, str(HERE / "verify_geometry_identity.py"),
            "--baseline", str(baseline), "--candidate", str(pbr),
            "--report", str(reports_dir / f"geometry-lod{lod}.json"),
        ], records)
        combined = combined_dir / f"kairou-lod{lod}.raw.glb"
        if args.skip_legacy_upper:
            shutil.copy2(pbr, combined)
            combine_report = {
                "schemaVersion": 1,
                "status": "PASS",
                "lod": lod,
                "base": str(pbr),
                "output": str(combined),
                "legacyUpperIncluded": False,
                "reason": "V6 replaces the floating ring source with connected, collisionless hero silhouettes",
            }
            (reports_dir / f"combine-lod{lod}.json").write_text(
                json.dumps(combine_report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            records.append({"operation": "copy-pbr-without-legacy-upper", "lod": lod, "returnCode": 0})
        else:
            command([
                args.blender, "--background", "--factory-startup", "--python",
                str(HERE / "integrate_safe_upper_hero.py"), "--",
                "--base", str(pbr),
                "--upper", str(HERE / "source" / f"kairou-v10.1-upper-lod{lod}.raw.glb"),
                "--output", str(combined),
                "--report", str(reports_dir / f"combine-lod{lod}.json"),
                "--lod", str(lod),
            ], records)
        output = raw_dir / f"kairou-lod{lod}.raw.glb"
        surface_report = reports_dir / f"surface-lod{lod}.json"
        command([
            args.blender, "--background", "--factory-startup", "--python",
            str(HERE / "author_v10_1_surface_pass.py"), "--",
            "--input", str(combined),
            "--layouts", str(REPO / "tools/blender/generated/stage-layouts.json"),
            "--output", str(output), "--report", str(surface_report),
            "--lod", str(lod),
        ], records)
        surface_reports.append(json.loads(surface_report.read_text(encoding="utf-8")))
        collision_report = reports_dir / f"collision-lod{lod}.json"
        command([
            sys.executable, str(HERE / "audit_collision_alignment.py"),
            "--glb", str(output),
            "--layouts", str(REPO / "tools/blender/generated/stage-layouts.json"),
            "--mode", "as-authored", "--tolerance", "0.45",
            "--baseline-glb", str(baseline), "--baseline-tolerance", "0.45",
            "--report", str(collision_report),
            "--proof", str(screenshots / f"collision-lod{lod}.png"),
        ], records)
        collision_reports.append(json.loads(collision_report.read_text(encoding="utf-8")))

    if args.render:
        command([
            args.blender, "--background", "--factory-startup", "--python",
            str(HERE / "render_v10_1_candidate.py"), "--",
            "--glb", str(raw_dir / "kairou-lod0.raw.glb"),
            "--output-dir", str(screenshots / "eight-view"),
            "--resolution-x", "960", "--resolution-y", "540",
        ], records)

    release_dir = work / "release-candidate"
    release_dir.mkdir()
    release_files = []
    for lod in (0, 1, 2):
        target = release_dir / f"kairou-lod{lod}.glb"
        shutil.copy2(raw_dir / f"kairou-lod{lod}.raw.glb", target)
        release_files.append(target)
    if not args.skip_optimize:
        command([args.node, str(REPO / "tools/blender/optimize-glbs.mjs"), *map(str, release_files)], records)

    totals = [int(item["totalTriangles"]) for item in surface_reports]
    material_counts = [int(item["materialCount"]) for item in surface_reports]
    gates = contract["releaseGates"]
    technical_failures = []
    if totals[0] > gates["maximumLod0Triangles"]:
        technical_failures.append("lod0-triangles")
    if max(material_counts) > gates["maximumMaterials"]:
        technical_failures.append("materials")
    if totals[1] / totals[0] > gates["maximumLod1Ratio"]:
        technical_failures.append("lod1-ratio")
    if totals[2] / totals[0] > gates["maximumLod2Ratio"]:
        technical_failures.append("lod2-ratio")
    for lod, report in enumerate(collision_reports):
        if report["supportedAreaRatio"] < gates["supportedAreaRatio"]:
            technical_failures.append(f"lod{lod}-support")
        if report["unsupportedSampleCount"] != 0:
            technical_failures.append(f"lod{lod}-unsupported")
        if any(item["unsupportedSampleCount"] for item in report["protectedRoutes"]):
            technical_failures.append(f"lod{lod}-route")

    visual_ok = args.visual_score is not None and args.visual_score >= gates["minimumVisualScore"]
    result = {
        "schemaVersion": 1,
        "status": "PASS" if not technical_failures else "FAIL",
        "shipStatus": "CANDIDATE_READY_FOR_MANUAL_PROMOTION" if not technical_failures and visual_ok else "NO_SHIP",
        "publicWritePerformed": False,
        "trackedInputContract": str(HERE / "asset-contract.json"),
        "workDirectory": str(work),
        "screenshotsDirectory": str(screenshots),
        "triangles": {"lod0": totals[0], "lod1": totals[1], "lod2": totals[2]},
        "lodRatios": {"lod1": totals[1] / totals[0], "lod2": totals[2] / totals[0]},
        "materials": material_counts,
        "visualScore": args.visual_score,
        "minimumVisualScore": gates["minimumVisualScore"],
        "technicalFailures": technical_failures,
        "collisionReports": collision_reports,
        "releaseCandidates": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in release_files
        ],
        "commands": records,
    }
    (work / "build-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if technical_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
