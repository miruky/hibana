#!/usr/bin/env python3
"""Fail closed until every Kouwan R10 input is repository reproducible."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
CONTRACT = HERE / "reproduction-contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(path: Path, expected: str) -> dict[str, object]:
    actual = sha256(path) if path.is_file() else None
    return {
        "path": str(path),
        "exists": path.is_file(),
        "expectedSha256": expected,
        "actualSha256": actual,
        "pass": actual == expected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=REPO / "tools/blender/work/kouwan-r10",
        help="candidate input/output root; defaults to the ignored repository work tree",
    )
    parser.add_argument(
        "--require-known-outputs",
        action="store_true",
        help="also verify the exact previously reviewed R10 outputs",
    )
    args = parser.parse_args()
    root = args.artifact_root.expanduser().resolve()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    layout = contract["layout"]
    layout_result = inspect(REPO / layout["path"], layout["sha256"])
    inputs = [inspect(root / row["path"], row["sha256"]) for row in contract["externalInputs"]]
    outputs = (
        [inspect(root / row["path"], row["sha256"]) for row in contract["knownPrivateOutputs"]]
        if args.require_known_outputs
        else []
    )

    source_files = sorted(
        path
        for suffix in ("*.py", "*.mjs")
        for path in HERE.glob(suffix)
        if path.name != Path(__file__).name
    )
    machine_local_literals = []
    forbidden_fragment = "/" + "private/tmp"
    for path in source_files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if forbidden_fragment in line:
                machine_local_literals.append({"path": str(path), "line": line_number})

    payload = {
        "candidate": contract["candidate"],
        "artifactRoot": str(root),
        "layout": layout_result,
        "externalInputs": inputs,
        "knownPrivateOutputs": outputs,
        "machineLocalPathLiterals": machine_local_literals,
        "semanticBlockers": contract["semanticBlockers"],
    }
    payload["repositorySelfContained"] = (
        not contract["externalInputs"] and not contract["semanticBlockers"]
    )
    payload["suppliedArtifactSetValid"] = (
        layout_result["pass"]
        and all(row["pass"] for row in inputs)
        and all(row["pass"] for row in outputs)
        and not machine_local_literals
    )
    payload["integrationReady"] = payload["repositorySelfContained"] and payload["suppliedArtifactSetValid"]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["integrationReady"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
