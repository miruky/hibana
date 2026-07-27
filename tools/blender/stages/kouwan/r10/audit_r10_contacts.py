from __future__ import annotations

"""Deterministic R10 contact, bounds, and nonblocking-art audit."""

import json
import os
from pathlib import Path

import bpy
from mathutils import Vector


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
OUT = ROOT / "kouwan-r10-contact-audit.json"
R10_COLLECTION = "HB_V5_R10_HARBOR_SHIP_GATE"
EXPECTED_LAYOUT_SHA = "b0e1b9c0b7377dc4978ba2d74a01703677d38fda24d83aef38d59a73b1b9d482"


def bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    corners = [obj.matrix_world @ Vector(value) for value in obj.bound_box]
    xs = [float(value.x) for value in corners]
    ys = [float(value.z) for value in corners]
    zs = [float(-value.y) for value in corners]
    return {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]}


def separation(a: dict[str, list[float]], b: dict[str, list[float]], axis: str) -> float:
    aa = a[axis]
    bb = b[axis]
    if aa[1] < bb[0]:
        return bb[0] - aa[1]
    if bb[1] < aa[0]:
        return aa[0] - bb[1]
    return 0.0


def contact(first_name: str, second_name: str, tolerance: float = 0.25) -> dict:
    first = bpy.data.objects.get(first_name)
    second = bpy.data.objects.get(second_name)
    if first is None or second is None:
        return {"first": first_name, "second": second_name, "pass": False, "reason": "missing object"}
    first_bounds = bounds(first)
    second_bounds = bounds(second)
    gaps = {axis: separation(first_bounds, second_bounds, axis) for axis in ("x", "y", "z")}
    return {
        "first": first_name,
        "second": second_name,
        "pass": all(gap <= tolerance for gap in gaps.values()),
        "tolerance": tolerance,
        "axisGaps": {axis: round(value, 4) for axis, value in gaps.items()},
        "firstBounds": {axis: [round(value, 3) for value in values] for axis, values in first_bounds.items()},
        "secondBounds": {axis: [round(value, 3) for value in values] for axis, values in second_bounds.items()},
    }


baseline_pairs: list[tuple[str, str, float]] = [
    ("HB_R7_SHIP_MAIN_DECK", "HB_R7_SHIP_HOUSE_LOWER", 0.25),
    ("HB_R7_SHIP_HOUSE_LOWER", "HB_R7_SHIP_HOUSE_MID", 0.25),
    ("HB_R7_SHIP_HOUSE_MID", "HB_R7_SHIP_BRIDGE", 0.25),
    ("HB_R7_SHIP_BRIDGE", "HB_R7_SHIP_BRIDGE_ROOF", 0.25),
    ("HB_R7_SHIP_BRIDGE_ROOF", "HB_R7_SHIP_RADAR_MAST", 0.30),
    ("HB_R7_SHIP_RADAR_MAST", "HB_R7_SHIP_RADAR_YARD", 0.30),
    ("HB_R7_SHIP_DECK_CRANE_MAST", "HB_R7_SHIP_DECK_CRANE_BOOM", 0.35),
    ("HB_R7_SHIP_DECK_CRANE_MAST", "HB_R85_SHIP_DECK_CRANE_PEDESTAL", 0.25),
    ("HB_R85_SHIP_DECK_CRANE_PEDESTAL", "HB_R85_SHIP_DECK_CRANE_BASE_PLATE", 0.25),
    ("HB_R85_SHIP_DECK_CRANE_BASE_PLATE", "HB_R7_SHIP_MAIN_DECK", 0.25),
    ("HB_R82_TUG_LOWER_HULL", "HB_R82_TUG_UPPER_HULL", 0.25),
    ("HB_R82_TUG_UPPER_HULL", "HB_R82_TUG_DECK", 0.25),
    ("HB_R82_TUG_DECK", "HB_R82_TUG_WHEELHOUSE", 0.25),
    ("HB_R82_TUG_WHEELHOUSE", "HB_R82_TUG_CAB_ROOF", 0.25),
    ("HB_R82_TUG_CAB_ROOF", "HB_R82_TUG_MAST", 0.30),
    ("HB_R82_TUG_DECK", "HB_R82_TUG_CRANE_PEDESTAL", 0.30),
    ("HB_R80_FAR_QUAY_WALL", "HB_R82_FAR_QUAY_FENDER_4", 0.30),
    ("HB_R75_MID_BULK_SHED", "HB_R82_BULK_FRONT_PILASTER_3", 0.30),
    ("HB_R84_TOWER_STAIR_CORE", "HB_R84_TOWER_STAIR_BRIDGE_0", 0.35),
    ("HB_R84_TOWER_STAIR_CORE", "HB_R84_TOWER_STAIR_BRIDGE_1", 0.35),
    ("HB_R95_BRIDGE_FRONT_LOWER_RAIL", "HB_R93_CONTROL_BRIDGE_DECK", 0.08),
    ("HB_R95_BRIDGE_BACK_LOWER_RAIL", "HB_R93_CONTROL_BRIDGE_DECK", 0.08),
    ("HB_R95_BRIDGE_FRONT_LOWER_RAIL", "HB_R93_CONTROL_BRIDGE_FRONT_CAVITY", 0.08),
    ("HB_R95_BRIDGE_BACK_LOWER_RAIL", "HB_R93_CONTROL_BRIDGE_BACK_CAVITY", 0.08),
    ("HB_R95_BRIDGE_FRONT_UPPER_RAIL", "HB_R93_CONTROL_BRIDGE_FRONT_CAVITY", 0.08),
    ("HB_R95_BRIDGE_BACK_UPPER_RAIL", "HB_R93_CONTROL_BRIDGE_BACK_CAVITY", 0.08),
    ("HB_R95_BRIDGE_FRONT_UPPER_RAIL", "HB_R93_CONTROL_BRIDGE_ROOF", 0.08),
    ("HB_R95_BRIDGE_BACK_UPPER_RAIL", "HB_R93_CONTROL_BRIDGE_ROOF", 0.08),
    ("HB_R93_CONTROL_BRIDGE_DECK", "HB_R93_WEST_SERVICE_CORE", 0.10),
    ("HB_R93_CONTROL_BRIDGE_DECK", "HB_R93_EAST_SERVICE_CORE", 0.10),
    ("HB_R93_WEST_SERVICE_CORE", "HB_R94_WEST_SERVICE_PLINTH", 0.10),
    ("HB_R93_EAST_SERVICE_CORE", "HB_R94_EAST_SERVICE_PLINTH", 0.10),
]

for bundle in range(4):
    baseline_pairs.append((f"HB_V5_LIFT_CABLE_BUNDLE_{bundle}", "HB_R85_LIFT_HOIST_CROSSBEAM", 0.30))
for rail in range(4):
    baseline_pairs.append(("HB_R85_LIFT_HOIST_CROSSBEAM", f"HB_R85_LIFT_HOIST_RAIL_{rail}", 0.30))
    baseline_pairs.append((f"HB_R85_LIFT_HOIST_RAIL_{rail}", "HB_V4_SHIPLIFT_TOP_SPAN_38.5", 0.30))
for side in ("W", "E"):
    for z in (84, 92, 100, 108):
        baseline_pairs.append((f"HB_R93_{side}_RACK_POST_{z}", f"HB_R94_{side}_RACK_FOOT_{z}", 0.10))
for x in (80.2, 82.8, 99.2, 101.8):
    for z in (87, 107):
        baseline_pairs.append((f"HB_R93_CATWALK_LEG_{x:.1f}_{z}", f"HB_R94_CATWALK_FOOT_{x:.1f}_{z}", 0.10))
        catwalk = "HB_R93_EDGE_CATWALK_W" if x < 90.0 else "HB_R93_EDGE_CATWALK_E"
        baseline_pairs.append((f"HB_R93_CATWALK_LEG_{x:.1f}_{z}", catwalk, 0.10))
for index in range(8):
    baseline_pairs.append((f"HB_R92_QUAY_FENDER_{index}", "HB_R80_NEAR_QUAY_WALL", 0.15))


new_pairs: list[tuple[str, str, float]] = [
    ("HB_R10_TUG_BOW_LOWER", "HB_R82_TUG_LOWER_HULL", 0.10),
    ("HB_R10_TUG_BOW_UPPER", "HB_R82_TUG_UPPER_HULL", 0.10),
    ("HB_R10_TUG_FOREDECK", "HB_R82_TUG_DECK", 0.10),
    ("HB_R10_TUG_WINDSHIELD_MULLION_2", "HB_R82_TUG_FRONT_GLASS", 0.12),
    ("HB_R10_TUG_WINDSHIELD_BROW", "HB_R82_TUG_FRONT_GLASS", 0.45),
    ("HB_R10_TUG_LIFE_RING_STRAP_PORT", "HB_R82_TUG_WHEELHOUSE", 0.15),
    ("HB_R10_BULK_LOADING_CANOPY", "HB_R82_BULK_FRONT_BELT_2", 0.10),
    ("HB_R10_BULK_LOADING_CANOPY_FASCIA", "HB_R10_BULK_LOADING_CANOPY", 0.10),
    ("HB_R10_BULK_CANOPY_TIE_0", "HB_R10_BULK_LOADING_CANOPY", 0.10),
    ("HB_R10_TOWER_VTS_PEDESTAL", "HB_R74_TOWER_CROWN_MAST", 0.10),
    ("HB_R10_TOWER_CONTROL_GLASS_1", "HB_R73_TOWER_CONTROL_ROOM", 0.20),
    ("HB_R10_DOCK_CRANE_CAB_STAY", "HB_R80_DOCK_CRANE_TROLLEY", 0.15),
    ("HB_R10_DOCK_CRANE_HOOK_BLOCK", "HB_R80_DOCK_CRANE_CABLE", 0.25),
    ("HB_R10_DOCK_CRANE_HOOK_A", "HB_R10_DOCK_CRANE_HOOK_BLOCK", 0.10),
    ("HB_R10_SHIP_PLATE_SEAM_H_4", "HB_V5_SHIP_SIDE_PLATE_+1_4", 0.22),
    ("HB_R10_SHIP_PLATE_SEAM_V_4", "HB_V5_SHIP_SIDE_PLATE_+1_4", 0.22),
    ("HB_R10_SHIP_CRADLE_KNEE_0", "HB_R10_SHIP_CRADLE_PAD_0", 0.10),
    ("HB_R10_FAR_HALL_A_BODY", "HB_R10_FAR_HALL_A_PLINTH", 0.05),
    ("HB_R10_FAR_HALL_A_BODY", "HB_R10_FAR_HALL_A_ROOF", 0.05),
    ("HB_R10_FAR_HALL_B_BODY", "HB_R10_FAR_HALL_B_PLINTH", 0.05),
    ("HB_R10_FAR_HALL_B_BODY", "HB_R10_FAR_HALL_B_ROOF", 0.05),
    ("HB_R10_FAR_SILO_0", "HB_R10_FAR_SILO_CAP_0", 0.10),
    ("HB_R10_FAR_SILO_PIPE_0", "HB_R10_FAR_SILO_CAP_0", 0.10),
]


baseline_results = [contact(*pair) for pair in baseline_pairs]
new_results = [contact(*pair) for pair in new_pairs]
collection = bpy.data.collections.get(R10_COLLECTION)
r10_objects = list(collection.objects) if collection is not None else []

object_audit = []
for obj in sorted(r10_objects, key=lambda value: value.name):
    if obj.type != "MESH":
        continue
    value = bounds(obj)
    dimensions = {axis: value[axis][1] - value[axis][0] for axis in ("x", "y", "z")}
    object_audit.append(
        {
            "name": obj.name,
            "bounds": {axis: [round(item, 3) for item in values] for axis, values in value.items()},
            "dimensions": {axis: round(item, 4) for axis, item in dimensions.items()},
            "positiveDimensions": all(item > 0.0 for item in dimensions.values()),
            "artOnly": obj.get("hibanaArtOnly") is True,
            "walkBlocker": bool(obj.get("hbWalkBlocker", True)),
            "hidden": bool(obj.hide_render),
        }
    )

scene = bpy.context.scene
payload = {
    "candidate": "kouwan-r10-private-contact-audit",
    "baselineContactCount": len(baseline_results),
    "baselineContacts": baseline_results,
    "baselineContactPass": len(baseline_results) == 76 and all(item["pass"] for item in baseline_results),
    "r10ContactCount": len(new_results),
    "r10Contacts": new_results,
    "r10ContactPass": all(item["pass"] for item in new_results),
    "sixOrthographicExtremaPass": bool(object_audit) and all(item["positiveDimensions"] for item in object_audit),
    "r10ArtOnlyPass": bool(object_audit) and all(item["artOnly"] for item in object_audit),
    "r10NonblockingPass": bool(object_audit) and not any(item["walkBlocker"] for item in object_audit),
    "layoutSha256": scene.get("hibanaLayoutSha256"),
    "layoutUnchangedPass": scene.get("hibanaLayoutSha256") == EXPECTED_LAYOUT_SHA and scene.get("hibanaLayoutChanged") is False,
    "collisionUnchangedPass": scene.get("hibanaCollisionChanged") is False,
    "objects": object_audit,
}
payload["ship"] = all(
    payload[key]
    for key in (
        "baselineContactPass",
        "r10ContactPass",
        "sixOrthographicExtremaPass",
        "r10ArtOnlyPass",
        "r10NonblockingPass",
        "layoutUnchangedPass",
        "collisionUnchangedPass",
    )
)
OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "baselineContacts": len(baseline_results),
            "baselineContactPass": payload["baselineContactPass"],
            "r10Contacts": len(new_results),
            "r10ContactPass": payload["r10ContactPass"],
            "failedBaseline": [
                f'{item["first"]} <> {item["second"]}: {item.get("axisGaps", item.get("reason"))}'
                for item in baseline_results
                if not item["pass"]
            ],
            "failedR10": [
                f'{item["first"]} <> {item["second"]}: {item.get("axisGaps", item.get("reason"))}'
                for item in new_results
                if not item["pass"]
            ],
            "sixOrthographicExtremaPass": payload["sixOrthographicExtremaPass"],
            "r10ArtOnlyPass": payload["r10ArtOnlyPass"],
            "r10NonblockingPass": payload["r10NonblockingPass"],
            "layoutUnchangedPass": payload["layoutUnchangedPass"],
            "collisionUnchangedPass": payload["collisionUnchangedPass"],
            "ship": payload["ship"],
        },
        indent=2,
    )
)
