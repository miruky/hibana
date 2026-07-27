from __future__ import annotations

"""Run the reviewed Kouwan batching/UV/LOD exporter for the R10 private candidate.

The geometry reduction and export algorithm is intentionally identical to the
previous Khronos-passing R7.2/R9.5 path.  Only artifact identity and the audited
R9 glazing sources/classification are substituted.
"""

import os
from pathlib import Path


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
BASE = Path(
    os.environ.get("HIBANA_KOUWAN_R10_OPTIMIZER_BASE", ROOT / "optimize_export_r7_2.py")
).expanduser().resolve()
if not BASE.is_file():
    raise RuntimeError(
        "missing inherited optimizer source; set HIBANA_KOUWAN_R10_OPTIMIZER_BASE "
        f"to the reviewed optimize_export_r7_2.py: {BASE}"
    )
source = BASE.read_text(encoding="utf-8")

# The inherited R7.2 source predates configurable candidate roots. Keep the
# reviewed algorithm intact while redirecting its artifact root without
# embedding the earlier machine-local path in this repository wrapper.
root_lines = [line for line in source.splitlines() if line.startswith("ROOT = Path(")]
if len(root_lines) != 1:
    raise RuntimeError(f"expected one inherited ROOT declaration, found {len(root_lines)}")
source = source.replace(root_lines[0], f"ROOT = Path({str(ROOT)!r})", 1)


def replace_once(old: str, new: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one optimizer token, found {count}: {old!r}")
    source = source.replace(old, new, 1)


source = source.replace("optimized-r7-2", "optimized-r10")
source = source.replace("kouwan-r7-2", "kouwan-r10")
source = source.replace("R7_2", "R10")
source = source.replace("R72", "R10")
source = source.replace("R7_EXPORT", "R10_EXPORT")
source = source.replace("HB_R7_LOD0_DECIMATE", "HB_R10_LOD0_DECIMATE")
source = source.replace("HB_R7_LOD1_DECIMATE", "HB_R10_LOD1_DECIMATE")
source = source.replace("HB_R7_LOD1_GATE_DECIMATE", "HB_R10_LOD1_GATE_DECIMATE")
source = source.replace("HB_R7_LOD2_GATE_DECIMATE", "HB_R10_LOD2_GATE_DECIMATE")

replace_once(
    'glass = clone_material("MAT_KOUWAN_STRUCTURAL_GLASS", "MAT_KOUWAN_R10_EXPORT_GLASS")',
    'glass = clone_material("MAT_KOUWAN_R9_SMOKED_GLASS", "MAT_KOUWAN_R10_EXPORT_GLASS")',
)
replace_once(
    'warm_glass = clone_material("MAT_KOUWAN_WARM_INTERIOR_GLASS", "MAT_KOUWAN_R10_EXPORT_WARM_GLASS")',
    'warm_glass = clone_material("MAT_KOUWAN_R9_WARM_OCCUPIED_GLASS", "MAT_KOUWAN_R10_EXPORT_WARM_GLASS")',
)
replace_once(
    '    if "STRUCTURAL_GLASS" in name or "BLUE_GLASS" in name:\n        return glass, None',
    '    if "STRUCTURAL_GLASS" in name or "BLUE_GLASS" in name or "SMOKED_GLASS" in name:\n'
    '        return glass, None\n'
    '    if "FADED_YELLOW" in name:\n'
    '        return atlas, "road_marking"\n'
    '    if "OXIDE_GREEN" in name:\n'
    '        return atlas, "painted_harbor_blue"',
)

compiled = compile(source, str(BASE) + "::r10-reviewed-substitution", "exec")
exec(compiled, {"__name__": "__main__", "__file__": str(BASE)})
