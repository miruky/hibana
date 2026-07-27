from __future__ import annotations

"""Run the reviewed release audit with R10 identity and triangle budget."""

import os
from pathlib import Path


root = Path(
    os.environ.get(
        "HIBANA_KOUWAN_R10_ROOT",
        Path(__file__).resolve().parents[3] / "work/kouwan-r10",
    )
).expanduser().resolve()
repo = Path(__file__).resolve().parents[5]
public = (repo / "public").resolve()
work = (repo / "tools/blender/work").resolve()
if root == public or public in root.parents:
    raise RuntimeError(f"private candidate must never write below public/: {root}")
if repo in root.parents and root != work and work not in root.parents:
    raise RuntimeError(f"repository-local output must stay below ignored {work}: {root}")
base = Path(
    os.environ.get(
        "HIBANA_KOUWAN_R10_RELEASE_AUDIT_BASE",
        root / "optimized-r7-2/audit_release_r7_2.py",
    )
).expanduser().resolve()
if not base.is_file():
    raise RuntimeError(
        "missing inherited release-audit source; set "
        "HIBANA_KOUWAN_R10_RELEASE_AUDIT_BASE to the reviewed "
        f"audit_release_r7_2.py: {base}"
    )
source = base.read_text(encoding="utf-8")
root_lines = [line for line in source.splitlines() if line.startswith("ROOT = Path(")]
if len(root_lines) != 1:
    raise RuntimeError(f"expected one inherited ROOT declaration, found {len(root_lines)}")
source = source.replace(root_lines[0], f"ROOT = Path({str(root / 'optimized-r10')!r})", 1)
source = source.replace("optimized-r7-2", "optimized-r10")
source = source.replace("kouwan-r7-2", "kouwan-r10")
source = source.replace("release-audit-r7-2.json", "release-audit-r10.json")
source = source.replace(
    "LOD0_SIZE_LIMIT = 5_500_000",
    "LOD0_SIZE_LIMIT = 5_500_000\nLOD0_TRIANGLE_LIMIT = 260_000",
)
source = source.replace(
    'if rows[0]["bytes"] > LOD0_SIZE_LIMIT: issues.append("lod0-size-budget")',
    'if rows[0]["bytes"] > LOD0_SIZE_LIMIT: issues.append("lod0-size-budget")\n'
    'if rows[0]["triangles"] > LOD0_TRIANGLE_LIMIT: issues.append("lod0-triangle-budget")',
)
source = source.replace(
    '"lod0SizeLimit": LOD0_SIZE_LIMIT,',
    '"lod0SizeLimit": LOD0_SIZE_LIMIT,\n    "lod0TriangleLimit": LOD0_TRIANGLE_LIMIT,',
)
compiled = compile(source, str(base) + "::r10", "exec")
exec(compiled, {"__name__": "__main__", "__file__": str(base)})
