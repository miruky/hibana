"""One-shot, headless-only Nakaniwa iteration23 private proof.

This reviewed runner leaves the safe R6 source, canonical targetY30 camera,
materials, lighting, heroes, routes, collision and public assets untouched.
Inside a factory-startup Blender process it replaces only the former R6
hanging-garden spine with one supported, continuous inhabited garden district
and renders exactly one private targetY14 evidence frame.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO_ROOT = Path(
    "/Users/h_miruky/Library/Mobile Documents/"
    "com~apple~CloudDocs/develop/100リポジトリ作成計画トップ/hibana"
).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6  # noqa: E402


BASELINE_SOURCE_SHA256 = (
    "73412e4f687bec985e1e8049c021c7b1661de1acddab6caa473a912afe306b41"
)
BASELINE_TEST_SHA256 = (
    "a58397221b838678f33470783245f6afb30b76e57deb89d0dc5d4fcbc19434df"
)
PREFLIGHT_PATH = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
    "iteration23-read-only-preflight.json"
).resolve()
PREFLIGHT_SHA256 = (
    "12931d89e63050ffb47c6b6a04c2e914bd564653db5fbaf2e23a4c0bc1d97e71"
)
OUTPUT_ROOT = (
    R6.PRIVATE_PRODUCTION_DEFAULT
    / "connected-inhabited-district-iteration23"
).resolve()
RUNNER_PATH = (
    REPO_ROOT
    / "tools/blender/"
    "run_nakaniwa_a21_r6_iteration23_connected_district.py"
).resolve()
TEST_PATH = (
    REPO_ROOT / "tools/blender/test_nakaniwa_reference_a21_r6.py"
).resolve()
SOURCE_PATH = Path(R6.__file__).resolve()

CONTROL_PATH = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6/"
    "camera-study-target-y14-iteration21/views/"
    "00_eye165_dualhero_targety14_iteration21.png"
).resolve()
CONTROL_SHA256 = (
    "f3299ef50ea1321473f55e548969a0f50fef604914c6ec8f175fcaff33bf17e9"
)
REFERENCE_PATH = (
    REPO_ROOT / "tools/blender/concepts/nakaniwa-reference-v1.png"
).resolve()
REFERENCE_SHA256 = (
    "c0b3bec12431c264ebe04a0757ea67eb521eab2c4e32e004da88cf6e6eebe15d"
)

OLD_GROUP = "a21-r6-nakaniwa-midground-hanging-garden-spine"
NEW_GROUP = "a21-r6-nakaniwa-connected-inhabited-garden-district-i23"

# Horizontal basis of the locked targetY14 evidence camera.  S increases
# toward rendered frame-right.  D increases away from the camera.
S_AXIS = (0.7050927223528654, 0.7091151196279946)
D_AXIS = (-0.7091151196279946, 0.7050927223528654)
CENTER_XZ = (-2.5875, -0.7575)

BASELINE_CAMERA = copy.deepcopy(R6.MAIN_REFERENCE_CAMERA)
BASELINE_PROOF_CAMERAS = copy.deepcopy(R6.PROOF_CAMERAS)
STUDY_CAMERA = copy.deepcopy(BASELINE_CAMERA)
STUDY_CAMERA["name"] = (
    "CAM_Nakaniwa_A21_Eye165_DualHero_TargetY14_Iteration23"
)
STUDY_CAMERA["target"] = (
    float(BASELINE_CAMERA["target"][0]),
    14.0,
    float(BASELINE_CAMERA["target"][2]),
)
STUDY_CAMERA["intent"] = (
    "private iteration23 targetY14 evidence for one supported continuous "
    "inhabited garden district; canonical camera remains targetY30"
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

ORIGINAL_BUILD_SPECS = R6.build_specs


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _point(s: float, y: float, depth: float) -> tuple[float, float, float]:
    """Map screen-horizontal/depth construction coordinates to R6 space."""
    return (
        CENTER_XZ[0] + S_AXIS[0] * s + D_AXIS[0] * depth,
        y,
        CENTER_XZ[1] + S_AXIS[1] * s + D_AXIS[1] * depth,
    )


def _vertical_panel(
    specs: list[dict],
    role: str,
    material: str,
    s0: float,
    s1: float,
    y0: float,
    y1: float,
    depth: float,
    thickness: float,
) -> None:
    R6._panel(
        specs,
        role,
        material,
        NEW_GROUP,
        (
            _point(s0, y0, depth),
            _point(s1, y0, depth),
            _point(s1, y1, depth),
            _point(s0, y1, depth),
        ),
        thickness,
    )


def _horizontal_panel(
    specs: list[dict],
    role: str,
    material: str,
    s0: float,
    s1: float,
    y: float,
    depth0: float,
    depth1: float,
    thickness: float,
) -> None:
    R6._panel(
        specs,
        role,
        material,
        NEW_GROUP,
        (
            _point(s0, y, depth0),
            _point(s1, y, depth0),
            _point(s1, y, depth1),
            _point(s0, y, depth1),
        ),
        thickness,
    )


def _roof_panel(
    specs: list[dict],
    role: str,
    material: str,
    s0: float,
    s1: float,
    eave_y: float,
    ridge_y: float,
    front: bool,
    thickness: float,
) -> None:
    eave_depth = -5.2 if front else 5.2
    R6._panel(
        specs,
        role,
        material,
        NEW_GROUP,
        (
            _point(s0, eave_y, eave_depth),
            _point(s1, eave_y, eave_depth),
            _point(s1, ridge_y, 0.0),
            _point(s0, ridge_y, 0.0),
        ),
        thickness,
    )


def _oriented_sweep(
    specs: list[dict],
    role: str,
    material: str,
    points: Iterable[tuple[float, float, float]],
    radius: float,
    sides: int,
) -> None:
    R6._sweep(
        specs,
        role,
        material,
        NEW_GROUP,
        tuple(_point(s, y, depth) for s, y, depth in points),
        radius,
        sides,
    )


def _add_arch(
    specs: list[dict],
    role: str,
    material: str,
    centre_s: float,
    depth: float,
    half_width: float,
    base_y: float,
    spring_y: float,
    rise: float,
    segments: int,
    radius: float,
    sides: int,
) -> None:
    centre = _point(centre_s, 0.0, depth)
    R6._add_oriented_arch(
        specs,
        group=NEW_GROUP,
        role=role,
        centre_x=centre[0],
        centre_z=centre[2],
        axis_x=S_AXIS[0],
        axis_z=S_AXIS[1],
        half_width=half_width,
        base_y=base_y,
        spring_y=spring_y,
        rise=rise,
        segments=segments,
        radius=radius,
        sides=sides,
        material=material,
    )


def _add_lower_wings(specs: list[dict], lod: int) -> None:
    """Two grounded inhabited arcades keep the route portal physically open."""
    for side, s0, s1 in (
        ("left", -29.0, -9.7),
        ("right", 9.7, 29.0),
    ):
        _horizontal_panel(
            specs,
            f"a21-i23-{side}-wing-supported-plinth",
            "wet_stone",
            s0,
            s1,
            0.72,
            -5.6,
            5.6,
            1.10,
        )
        _vertical_panel(
            specs,
            f"a21-i23-{side}-inhabited-arcade-backing",
            "ivory_stone",
            s0,
            s1,
            0.82,
            13.20,
            3.65,
            0.46,
        )
        _vertical_panel(
            specs,
            f"a21-i23-{side}-arcade-weathered-base",
            "carved_stone",
            s0,
            s1,
            0.80,
            2.05,
            -5.25,
            0.34,
        )
        _vertical_panel(
            specs,
            f"a21-i23-{side}-arcade-cornice",
            "carved_stone",
            s0,
            s1,
            11.90,
            13.35,
            -5.20,
            0.38,
        )

    lower_centres = (-25.5, -19.5, -13.5, 13.5, 19.5, 25.5)
    for index, centre_s in enumerate(lower_centres):
        _vertical_panel(
            specs,
            "a21-i23-lower-arcade-occupied-shadow-recess",
            "dark_wood",
            centre_s - 2.25,
            centre_s + 2.25,
            2.05,
            10.35,
            -5.48,
            0.22,
        )
        if lod <= 1:
            _add_arch(
                specs,
                "a21-i23-lower-arcade-supported-garden-arch",
                "verdigris_bronze" if index % 2 == 0 else "carved_stone",
                centre_s,
                -5.70,
                2.58,
                0.85,
                6.45,
                3.75,
                (8, 5)[lod],
                (0.30, 0.24)[lod],
                (5, 4)[lod],
            )
        _vertical_panel(
            specs,
            "a21-i23-lower-arcade-warm-occupied-window",
            "warm_glow",
            centre_s - 0.62,
            centre_s + 0.62,
            3.0,
            5.15,
            -5.64,
            0.16,
        )


def _add_continuous_bridge_and_gallery(
    specs: list[dict],
    lod: int,
) -> None:
    """One overlapping slab/fascia/gallery chain joins both grounded wings."""
    for role, s0, s1 in (
        ("left-upper-terrace", -29.0, -9.70),
        ("open-route-overhead-bridge", -10.10, 10.10),
        ("right-upper-terrace", 9.70, 29.0),
    ):
        _horizontal_panel(
            specs,
            f"a21-i23-{role}-supported-deck",
            "ivory_stone",
            s0,
            s1,
            13.95 if "bridge" not in role else 14.00,
            -5.65,
            5.65,
            0.90,
        )
    _vertical_panel(
        specs,
        "a21-i23-continuous-bridge-deck-front-fascia",
        "carved_stone",
        -29.0,
        29.0,
        13.35,
        14.55,
        -5.72,
        0.34,
    )
    _vertical_panel(
        specs,
        "a21-i23-continuous-inhabited-upper-gallery-backing",
        "ivory_stone",
        -28.0,
        28.0,
        14.25,
        21.80,
        3.40,
        0.42,
    )
    _vertical_panel(
        specs,
        "a21-i23-continuous-upper-gallery-sill",
        "wet_stone",
        -28.3,
        28.3,
        14.20,
        15.10,
        -5.45,
        0.32,
    )
    _vertical_panel(
        specs,
        "a21-i23-continuous-upper-gallery-eave",
        "carved_stone",
        -28.4,
        28.4,
        21.25,
        22.35,
        -5.40,
        0.36,
    )

    upper_centres = (-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0)
    for index, centre_s in enumerate(upper_centres):
        _vertical_panel(
            specs,
            "a21-i23-upper-gallery-inhabited-recess",
            "dark_wood",
            centre_s - 3.05,
            centre_s + 3.05,
            15.10,
            21.15,
            -5.58,
            0.20,
        )
        _vertical_panel(
            specs,
            "a21-i23-upper-gallery-warm-residential-light",
            "warm_glow",
            centre_s - 0.48,
            centre_s + 0.48,
            16.0,
            18.25,
            -5.70,
            0.14,
        )
        if lod <= 1:
            _add_arch(
                specs,
                "a21-i23-upper-gallery-readable-botanical-arch",
                "brass" if index % 2 else "verdigris_bronze",
                centre_s,
                -5.78,
                3.42,
                14.30,
                18.35,
                3.55,
                (8, 5)[lod],
                (0.25, 0.20)[lod],
                (5, 4)[lod],
            )

    support_positions = (-28.0, -20.0, -12.0, -10.0, 10.0, 12.0, 20.0, 28.0)
    for support_s in support_positions:
        _oriented_sweep(
            specs,
            "a21-i23-grounded-deck-and-gallery-support",
            "carved_stone",
            (
                (support_s, 0.82, -5.35),
                (support_s, 14.18, -5.35),
            ),
            (0.30, 0.24, 0.20)[lod],
            (6, 4, 4)[lod],
        )
    for pier_s in (-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0):
        _oriented_sweep(
            specs,
            "a21-i23-upper-gallery-roof-bearing-pilaster",
            "brass" if int(abs(pier_s)) % 8 == 4 else "carved_stone",
            (
                (pier_s, 14.32, -5.52),
                (pier_s, 22.12, -5.52),
            ),
            (0.20, 0.17, 0.14)[lod],
            (6, 4, 4)[lod],
        )


def _add_roof_garden(specs: list[dict], lod: int) -> None:
    """Five joined roof houses, planters and crowns create inhabited relief."""
    roof_bays = (
        (-28.0, -16.5, 28.0),
        (-16.5, -5.5, 30.2),
        (-5.5, 5.5, 32.0),
        (5.5, 16.5, 29.4),
        (16.5, 28.0, 27.4),
    )
    for bay_index, (s0, s1, ridge_y) in enumerate(roof_bays):
        for front in (True, False):
            _roof_panel(
                specs,
                "a21-i23-connected-occupied-garden-roof",
                "verdigris_bronze" if bay_index % 2 == 0 else "wet_stone",
                s0,
                s1,
                22.05,
                ridge_y,
                front,
                (0.28, 0.22, 0.18)[lod],
            )
        if lod <= 1:
            _oriented_sweep(
                specs,
                "a21-i23-connected-roof-brass-ridge",
                "brass",
                (
                    (s0 + 0.25, ridge_y + 0.10, 0.0),
                    (s1 - 0.25, ridge_y + 0.10, 0.0),
                ),
                (0.10, 0.075)[lod],
                (6, 4)[lod],
            )

    if lod == 2:
        return

    planter_sites = (
        (-24.0, 22.65, -4.15),
        (-15.0, 22.65, -4.15),
        (-6.0, 22.65, -4.15),
        (6.0, 22.65, -4.15),
        (15.0, 22.65, -4.15),
        (24.0, 22.65, -4.15),
    )
    for index, (s, y, depth) in enumerate(planter_sites):
        x, world_y, z = _point(s, y, depth)
        R6._chamfer_box(
            specs,
            "a21-i23-supported-roof-garden-planter",
            "carved_stone",
            NEW_GROUP,
            x,
            world_y,
            z,
            2.4,
            0.82,
            1.8,
            (0.055, 0.042)[lod],
            1,
        )
        R6._leaf_cluster(
            specs,
            "a21-i23-readable-inhabited-roof-garden",
            "flower" if index in {1, 4} else (
                "foliage_light" if index % 2 else "foliage_dark"
            ),
            NEW_GROUP,
            x,
            world_y + 1.15,
            z,
            1.28,
            1.85,
            (16, 6)[lod],
            42300 + index,
        )

    tree_sites = (-20.0, 0.0, 20.0) if lod == 0 else (0.0,)
    for index, s in enumerate(tree_sites):
        x, _, z = _point(s, 0.0, 1.4)
        R6._cylinder(
            specs,
            "a21-i23-rooted-gallery-garden-tree-trunk",
            "dark_wood",
            NEW_GROUP,
            x,
            25.0,
            z,
            0.18,
            4.2,
            (7, 5)[lod],
            top_radius=0.10,
        )
        R6._leaf_cluster(
            specs,
            "a21-i23-rooted-gallery-garden-tree-crown",
            "foliage_dark" if index % 2 == 0 else "foliage_light",
            NEW_GROUP,
            x,
            28.0,
            z,
            1.75,
            3.8,
            (14, 5)[lod],
            42400 + index,
        )


def build_iteration23_group(lod: int) -> list[dict]:
    """Return only the one bounded iteration23 hypothesis."""
    if lod not in (0, 1, 2):
        raise ValueError(f"unsupported LOD: {lod}")
    specs: list[dict] = []
    if lod == 2:
        # Exactly two 12-triangle silhouette panels keep LOD2 below 28k.
        _vertical_panel(
            specs,
            "a21-i23-lod2-continuous-inhabited-gallery-silhouette",
            "ivory_stone",
            -28.0,
            28.0,
            14.0,
            22.1,
            1.8,
            0.34,
        )
        _vertical_panel(
            specs,
            "a21-i23-lod2-connected-roof-garden-silhouette",
            "verdigris_bronze",
            -27.5,
            27.5,
            22.0,
            29.0,
            2.0,
            0.30,
        )
        return specs
    _add_lower_wings(specs, lod)
    _add_continuous_bridge_and_gallery(specs, lod)
    _add_roof_garden(specs, lod)
    return specs


def build_iteration23_specs(lod: int = 0) -> list[dict]:
    """Reallocate the old spine without modifying the safe source module."""
    baseline = ORIGINAL_BUILD_SPECS(lod)
    retained = [spec for spec in baseline if spec["group"] != OLD_GROUP]
    return retained + build_iteration23_group(lod)


def _render_bounds(
    specs: Sequence[Mapping[str, object]],
) -> tuple[float, float, float, float]:
    frames = [
        frame
        for spec in specs
        if (frame := R6._project_spec_frame(spec, STUDY_CAMERA)) is not None
    ]
    if not frames:
        raise RuntimeError("iteration23 group has no camera projection")
    # R6's analytic x/y are mirrored relative to the rendered raster.
    return (
        1.0 - max(float(frame["bounds"][2]) for frame in frames),
        1.0 - max(float(frame["bounds"][3]) for frame in frames),
        1.0 - min(float(frame["bounds"][0]) for frame in frames),
        1.0 - min(float(frame["bounds"][1]) for frame in frames),
    )


def connection_report() -> dict:
    """Numerically prove the planned support/contact chain before rendering."""
    contacts = [
        {
            "id": "lower-wall-to-plinth",
            "overlapM": round(1.27 - 0.82, 3),
            "minimumM": 0.10,
        },
        {
            "id": "ground-piers-to-plinth",
            "overlapM": round(1.27 - 0.82, 3),
            "minimumM": 0.10,
        },
        {
            "id": "ground-piers-to-deck-underside",
            "overlapM": round(14.18 - (13.95 - 0.45), 3),
            "minimumM": 0.10,
        },
        {
            "id": "left-wing-deck-to-route-bridge",
            "overlapM": round(-9.70 - (-10.10), 3),
            "minimumM": 0.20,
        },
        {
            "id": "route-bridge-to-right-wing-deck",
            "overlapM": round(10.10 - 9.70, 3),
            "minimumM": 0.20,
        },
        {
            "id": "deck-to-upper-gallery",
            "overlapM": round((14.00 + 0.45) - 14.25, 3),
            "minimumM": 0.10,
        },
        {
            "id": "upper-pilasters-to-gallery-deck",
            "overlapM": round((14.00 + 0.45) - 14.32, 3),
            "minimumM": 0.10,
        },
        {
            "id": "upper-pilasters-to-roof-eave",
            "overlapM": round(22.12 - 22.05, 3),
            "minimumM": 0.05,
        },
        {
            "id": "roof-panels-to-gallery-top",
            "overlapM": round(22.35 - 22.05, 3),
            "minimumM": 0.10,
        },
        {
            "id": "planters-to-roof-eave",
            "overlapM": round((22.65 - 0.41) - 22.05, 3),
            "minimumM": 0.08,
        },
        {
            "id": "foliage-roots-to-planters",
            "overlapM": 0.41,
            "minimumM": 0.08,
        },
    ]
    for contact in contacts:
        contact["passed"] = (
            float(contact["overlapM"]) >= float(contact["minimumM"])
        )
    return {
        "method": "reviewed-local-coordinate-contact-overlap-v1",
        "contacts": contacts,
        "passed": all(bool(item["passed"]) for item in contacts),
    }


def static_preflight() -> dict:
    """Fail closed before Blender creates any output directory or render."""
    required_hashes = {
        str(SOURCE_PATH): BASELINE_SOURCE_SHA256,
        str(TEST_PATH): BASELINE_TEST_SHA256,
        str(PREFLIGHT_PATH): PREFLIGHT_SHA256,
        str(CONTROL_PATH): CONTROL_SHA256,
        str(REFERENCE_PATH): REFERENCE_SHA256,
    }
    hash_checks = []
    for raw_path, expected in required_hashes.items():
        path = Path(raw_path)
        actual = _sha256(path) if path.is_file() else None
        hash_checks.append({
            "path": str(path),
            "expectedSha256": expected,
            "actualSha256": actual,
            "passed": actual == expected,
        })
    if not all(bool(item["passed"]) for item in hash_checks):
        raise RuntimeError(f"iteration23 immutable input drift: {hash_checks}")

    if OUTPUT_ROOT.exists():
        raise RuntimeError(
            "iteration23 one-shot output already exists; refusing a second run: "
            f"{OUTPUT_ROOT}"
        )

    plans = []
    for lod in range(3):
        baseline = ORIGINAL_BUILD_SPECS(lod)
        old = [spec for spec in baseline if spec["group"] == OLD_GROUP]
        new = build_iteration23_group(lod)
        candidate = build_iteration23_specs(lod)
        budget = R6.LOD_BUDGETS[lod]
        planned = R6.estimated_triangles(candidate)
        plans.append({
            "lod": lod,
            "baselineSpecCount": len(baseline),
            "baselinePlannedTriangles": R6.estimated_triangles(baseline),
            "removedSpecCount": len(old),
            "removedPlannedTriangles": R6.estimated_triangles(old),
            "newSpecCount": len(new),
            "newPlannedTriangles": R6.estimated_triangles(new),
            "candidateSpecCount": len(candidate),
            "candidatePlannedTriangles": planned,
            "budget": copy.deepcopy(budget),
            "plannedTriangleBudgetPassed": (
                int(budget["minEvaluatedTriangles"])
                <= planned
                <= int(budget["maxEvaluatedTriangles"])
            ),
            "specBudgetPassed": len(candidate) <= int(budget["maxSpecs"]),
        })
    if not all(
        bool(plan["plannedTriangleBudgetPassed"])
        and bool(plan["specBudgetPassed"])
        for plan in plans
    ):
        raise RuntimeError(f"iteration23 static LOD budget failure: {plans}")

    allowed_materials = set(R6.MATERIALS)
    material_drift = sorted({
        str(spec["material"])
        for lod in range(3)
        for spec in build_iteration23_group(lod)
        if str(spec["material"]) not in allowed_materials
    })
    if material_drift:
        raise RuntimeError(f"iteration23 material drift: {material_drift}")
    if any(
        bool(spec["blocksGameplay"])
        for lod in range(3)
        for spec in build_iteration23_group(lod)
    ):
        raise RuntimeError("iteration23 gameplay-blocking geometry is forbidden")

    projected = _render_bounds(build_iteration23_group(0))
    # Conservative AABB projection may extend a few pixels beyond the authored
    # raster envelope, but it must remain in the hero gap and span its macro.
    projection_passed = (
        projected[0] >= 0.385
        and projected[2] <= 0.645
        and projected[2] - projected[0] >= 0.18
        and projected[1] <= 0.405
        and projected[3] >= 0.57
    )
    contacts = connection_report()
    if not projection_passed or not contacts["passed"]:
        raise RuntimeError(
            "iteration23 projection/contact failure: "
            f"projection={projected}, contacts={contacts}"
        )

    return {
        "schemaVersion": 1,
        "studyId": "nakaniwa-r6-iteration23-connected-inhabited-district",
        "immutableInputs": hash_checks,
        "lodPlans": plans,
        "newGroupProjectedRenderBounds": projected,
        "authoredTargetEnvelope": [0.405, 0.34, 0.625, 0.585],
        "projectionPassed": projection_passed,
        "connectionReport": contacts,
        "materialReuseOnly": True,
        "gameplayBlockingGeometryAdded": False,
        "passed": True,
    }


def _artifact(path: Path) -> dict:
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> dict:
    preflight = static_preflight()
    source_hash_before = _sha256(SOURCE_PATH)
    test_hash_before = _sha256(TEST_PATH)
    runner_hash = _sha256(RUNNER_PATH)

    study_proof_cameras = list(copy.deepcopy(BASELINE_PROOF_CAMERAS))
    study_proof_cameras[0] = STUDY_CAMERA
    R6.MAIN_REFERENCE_CAMERA = STUDY_CAMERA
    R6.PROOF_CAMERAS = tuple(study_proof_cameras)
    R6.build_specs = build_iteration23_specs
    try:
        # Exactly one selected proof view is rendered.  LOD1/LOD2 are saved and
        # exported for budget verification but never rendered.
        manifest = R6.build_private_production(
            output_dir=OUTPUT_ROOT,
            layout_path=R6.CANONICAL_LAYOUT_DEFAULT,
            view_indices=(0,),
        )
    finally:
        R6.build_specs = ORIGINAL_BUILD_SPECS
        R6.MAIN_REFERENCE_CAMERA = BASELINE_CAMERA
        R6.PROOF_CAMERAS = BASELINE_PROOF_CAMERAS

    import bpy  # type: ignore

    if len(manifest["views"]) != 1:
        raise RuntimeError(
            f"iteration23 render-count drift: {manifest['views']}"
        )
    render_path = Path(manifest["views"][0]).resolve()
    render_image = bpy.data.images.load(str(render_path), check_existing=False)
    actual_resolution = [int(render_image.size[0]), int(render_image.size[1])]
    bpy.data.images.remove(render_image)
    if actual_resolution != [1280, 720]:
        raise RuntimeError(
            f"iteration23 render resolution drift: {actual_resolution}"
        )
    if _sha256(SOURCE_PATH) != source_hash_before:
        raise RuntimeError("safe R6 source mutated during private build")
    if _sha256(TEST_PATH) != test_hash_before:
        raise RuntimeError("safe R6 tests mutated during private build")

    manifest_path = Path(manifest["manifest"]).resolve()
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = {
        "schemaVersion": 1,
        "studyId": preflight["studyId"],
        "hypothesis": (
            "Replacing only the detached thin hanging-garden spine with one "
            "ground-supported, overlapping low arcade/bridge/roof-garden "
            "district will create a single readable inhabited connection "
            "between the two frozen heroes while preserving the open route."
        ),
        "strictPreflight": {
            "path": str(PREFLIGHT_PATH),
            "sha256": PREFLIGHT_SHA256,
            "appliedWithoutRelaxation": True,
        },
        "oneHypothesisOnly": True,
        "secondHypothesisRendered": False,
        "renderCount": 1,
        "mutationScope": "headless-private-geometry-evidence-only",
        "privateBuildSpecsMonkeypatch": True,
        "baselineCamera": BASELINE_CAMERA,
        "studyCamera": STUDY_CAMERA,
        "privateWorkingCameraOnly": True,
        "onlyIntentionalCameraDeltaForEvidence": {
            "field": "target[1]",
            "baseline": 30.0,
            "study": 14.0,
        },
        "frozenFields": [
            "namedHeroGeometry",
            "materials",
            "lighting",
            "farField",
            "landmarkHeightContract43m",
            "canonicalGameplayRuntimeData",
            "routes",
            "collision",
            "canonicalCamera",
            "camera.location",
            "camera.lensMm",
            "camera.sensorWidthMm",
            "camera.resolution",
            "camera.eyeHeightM",
            "camera.target[0]",
            "camera.target[2]",
            "visibleBlenderUI",
        ],
        "geometryReallocation": {
            "removedSystem": OLD_GROUP,
            "newSystem": NEW_GROUP,
            "genericBoxTowerAdded": False,
            "lodPlans": preflight["lodPlans"],
            "projectedRenderBounds": (
                preflight["newGroupProjectedRenderBounds"]
            ),
            "connectionReport": preflight["connectionReport"],
        },
        "actualResolution": actual_resolution,
        "render": _artifact(render_path),
        "manifest": _artifact(manifest_path),
        "productionSource": {
            **_artifact(SOURCE_PATH),
            "matchedSafeBaselineBeforeAndAfter": (
                _sha256(SOURCE_PATH) == BASELINE_SOURCE_SHA256
            ),
        },
        "testSource": {
            **_artifact(TEST_PATH),
            "matchedSafeBaselineBeforeAndAfter": (
                _sha256(TEST_PATH) == BASELINE_TEST_SHA256
            ),
        },
        "reviewedRunner": {
            "path": str(RUNNER_PATH),
            "sha256AtExecution": runner_hash,
        },
        "iteration21Control": {
            "path": str(CONTROL_PATH),
            "sha256": CONTROL_SHA256,
        },
        "reference": {
            "path": str(REFERENCE_PATH),
            "sha256": REFERENCE_SHA256,
        },
        "manifestGates": {
            "heroFrameMetrics": manifest_payload["heroFrameMetrics"],
            "heroOcclusionMetrics": manifest_payload[
                "heroOcclusionMetrics"
            ],
            "conservatoryFiveVaultFrameReport": manifest_payload[
                "conservatoryFiveVaultFrameReport"
            ],
            "gameplayIntrusionReports": manifest_payload[
                "gameplayIntrusionReports"
            ],
            "lodArtifacts": manifest_payload["lodArtifacts"],
        },
        "publicMutation": False,
        "runtimeCollisionMutation": False,
        "canonicalCameraReplacement": False,
        "bridgeOrVisibleUISessionUsed": False,
        "releaseDecision": "NO-SHIP_PENDING_THRESHOLD_AND_INDEPENDENT_REVIEW",
    }
    contract_path = OUTPUT_ROOT / "iteration23-proof-contract.json"
    contract_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = {
        "studyId": contract["studyId"],
        "outputRoot": str(OUTPUT_ROOT),
        "render": contract["render"],
        "contract": _artifact(contract_path),
        "manifest": contract["manifest"],
        "actualResolution": actual_resolution,
        "lodArtifacts": [
            {
                "lod": artifact["lod"],
                "specCount": artifact["specCount"],
                "plannedTriangles": artifact["plannedTriangles"],
                "evaluatedTriangles": artifact["evaluatedTriangles"],
                "drawCallEstimate": artifact["drawCallEstimate"],
            }
            for artifact in manifest_payload["lodArtifacts"]
        ],
    }
    result_path = OUTPUT_ROOT / "iteration23-run-result.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    __result__ = main()
    print(json.dumps(__result__, ensure_ascii=False, indent=2))
