import ast
import json
import math
import os
from pathlib import Path
import unittest


GENERATOR_PATH = Path(__file__).with_name("build_all_stages.py")
CANONICAL_LAYOUT_ENV = "HIBANA_CANONICAL_STAGE_LAYOUT"


def load_helpers():
    names = {
        "_landmark_face_frame",
        "souko_tower_face_specs",
        "nakaniwa_conservatory_face_specs",
        "stage_central_camera_views",
        "stage_authoritative_wayfinding_specs",
        "stage_asset_min_tier",
    }
    tree = ast.parse(GENERATOR_PATH.read_text(encoding="utf-8"), filename=str(GENERATOR_PATH))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {"math": math}
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(GENERATOR_PATH), "exec"),
        namespace,
    )
    return namespace


class HeroFacadeSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()

    def canonical_stage(self, stage_id):
        layout_path = os.environ.get(CANONICAL_LAYOUT_ENV)
        if not layout_path:
            self.skipTest(f"{CANONICAL_LAYOUT_ENV} is not set")
        document = json.loads(Path(layout_path).read_text(encoding="utf-8"))
        return next(stage for stage in document["stages"] if stage["id"] == stage_id)

    def test_all_four_souko_towers_keep_relief_inside_face_budget(self):
        placement_pairs = (
            (
                {"id": "souko-shiosai-stackhouse", "cx": 80.8, "cz": 96, "width": 104, "depth": 66, "height": 58, "entrance": [28, 96]},
                (
                    {"x": 49.6, "y": 23.04, "z": 96, "w": 7, "h": 46.08, "d": 7, "landmarkPart": "tower"},
                    {"x": 112, "y": 23.04, "z": 96, "w": 7, "h": 46.08, "d": 7, "landmarkPart": "tower"},
                ),
            ),
            (
                {"id": "souko-amakado-customs-terminal", "cx": -68, "cz": -67.8, "width": 92, "depth": 78, "height": 42, "entrance": [-68, -28]},
                (
                    {"x": -99.28, "y": 15.51, "z": -45.96, "w": 7, "h": 31.02, "d": 7, "landmarkPart": "tower"},
                    {"x": -36.72, "y": 15.51, "z": -45.96, "w": 7, "h": 31.02, "d": 7, "landmarkPart": "tower"},
                ),
            ),
        )
        build = self.helpers["souko_tower_face_specs"]
        frame = self.helpers["_landmark_face_frame"]
        tower_count = 0
        for placement, towers in placement_pairs:
            for tower in towers:
                tower_count += 1
                specs = build(placement, tower, 0)
                roles = [item["role"] for item in specs]
                self.assertEqual(roles.count("rail"), 2)
                self.assertEqual(roles.count("collar"), 4)
                self.assertEqual(roles.count("service-spine"), 1)
                self.assertEqual(roles.count("id-light"), 1)
                self.assertGreaterEqual(roles.count("bay-number-segment"), 2)
                self.assertIn(
                    "hoist-header" if "stackhouse" in placement["id"] else "customs-header",
                    roles,
                )
                if "stackhouse" in placement["id"]:
                    self.assertEqual(roles.count("cable-guide"), 1)
                    self.assertEqual(roles.count("hoist-carriage"), 1)
                    self.assertEqual(roles.count("hoist-door"), 1)
                    self.assertEqual(roles.count("pulley-datum"), 1)
                    self.assertEqual(roles.count("cable-chevron-block"), 5)
                    self.assertNotIn("vent-louver", roles)
                else:
                    self.assertEqual(roles.count("vent-louver"), 6)
                    self.assertEqual(roles.count("customs-scan-datum"), 1)
                    self.assertEqual(roles.count("customs-scan-panel"), 1)
                    self.assertEqual(roles.count("customs-scan-frame"), 4)
                    self.assertEqual(roles.count("customs-vent-block"), 1)
                    self.assertEqual(roles.count("customs-inspection-field"), 1)
                    self.assertEqual(roles.count("customs-inspection-frame"), 4)
                    self.assertEqual(roles.count("customs-intake-blade"), 4)
                    self.assertNotIn("cable-guide", roles)
                self.assertEqual(roles.count("bay-number-backing"), 1)
                projected = frame(placement, tower)
                face = projected["forward"] + projected["forwardExtent"]
                base = tower["y"] - tower["h"] / 2
                top = tower["y"] + tower["h"] / 2
                for item in specs:
                    self.assertGreaterEqual(item["y"] - item["h"] / 2, base)
                    self.assertLessEqual(item["y"] + item["h"] / 2, top)
                    if item["role"] == "id-light":
                        self.assertAlmostEqual(face - (item["forward"] - item["d"] / 2), 0.02)
                        self.assertAlmostEqual(item["forward"] + item["d"] / 2 - face, 0.04)
                    elif item["role"] in {"bay-number-backing", "hoist-door"}:
                        self.assertAlmostEqual(face - (item["forward"] - item["d"] / 2), 0.06)
                        self.assertAlmostEqual(item["forward"] + item["d"] / 2 - face, 0.02)
                    elif item["role"] in {
                        "customs-scan-panel", "customs-vent-block",
                        "customs-inspection-field",
                    }:
                        self.assertAlmostEqual(face - (item["forward"] - item["d"] / 2), 0.12)
                        self.assertAlmostEqual(item["forward"] + item["d"] / 2 - face, 0.04)
                    elif item["role"] in {
                        "customs-scan-frame", "customs-inspection-frame",
                        "customs-intake-blade",
                    }:
                        self.assertAlmostEqual(face - (item["forward"] - item["d"] / 2), 0.14)
                        self.assertAlmostEqual(item["forward"] + item["d"] / 2 - face, 0.04)
                    else:
                        self.assertAlmostEqual(face - (item["forward"] - item["d"] / 2), 0.08)
                        self.assertAlmostEqual(item["forward"] + item["d"] / 2 - face, 0.04)
                lod1 = build(placement, tower, 1)
                self.assertEqual(sum(item["role"] == "rail" for item in lod1), 2)
                self.assertEqual(sum(item["role"] == "collar" for item in lod1), 2)
                self.assertGreaterEqual(sum(item["role"] == "bay-number-segment" for item in lod1), 2)
                if "customs" in placement["id"]:
                    self.assertEqual(sum(item["role"] == "vent-louver" for item in lod1), 3)
                    self.assertEqual(sum(item["role"] == "customs-scan-frame" for item in lod1), 4)
                    self.assertEqual(sum(item["role"] == "customs-inspection-frame" for item in lod1), 4)
                    self.assertEqual(sum(item["role"] == "customs-intake-blade" for item in lod1), 3)
                    for specs in (specs, lod1):
                        number = next(item for item in specs if item["role"] == "bay-number-backing")
                        badge = next(item for item in specs if item["role"] == "customs-inspection-field")
                        number_interval = (
                            number["lateral"] - number["w"] / 2,
                            number["lateral"] + number["w"] / 2,
                        )
                        badge_interval = (
                            badge["lateral"] - badge["w"] / 2,
                            badge["lateral"] + badge["w"] / 2,
                        )
                        gap = max(
                            number_interval[0] - badge_interval[1],
                            badge_interval[0] - number_interval[1],
                        )
                        self.assertGreaterEqual(gap, 0.10)
                        self.assertGreaterEqual(
                            badge["y"] - badge["h"] / 2,
                            base + float(tower["h"]) * 0.60,
                        )
                self.assertEqual(build(placement, tower, 2), [])
        self.assertEqual(tower_count, 4)

    def test_conservatory_glass_is_seated_on_front_walls_and_high_portal(self):
        placement = {
            "cx": 52, "cz": 61.8, "width": 76, "depth": 66,
            "height": 50, "entrance": [52, 28],
        }
        shell = [
            {"x": 26, "y": 5.25, "z": 28.8, "w": 24, "h": 10.5, "d": 1.4, "landmarkPart": "wall"},
            {"x": 78, "y": 5.25, "z": 28.8, "w": 24, "h": 10.5, "d": 1.4, "landmarkPart": "wall"},
            {"x": 26, "y": 5.25, "z": 94.8, "w": 24, "h": 10.5, "d": 1.4, "landmarkPart": "wall"},
            {"x": 78, "y": 5.25, "z": 94.8, "w": 24, "h": 10.5, "d": 1.4, "landmarkPart": "wall"},
        ]
        roof_base = 10.34
        fan_rear = -19.80
        fan_front = 18.48
        fan_width = 59.28
        fan_height = 39.21
        build = self.helpers["nakaniwa_conservatory_face_specs"]
        frame = self.helpers["_landmark_face_frame"]
        specs = build(placement, shell, 0, roof_base, fan_rear, fan_front, fan_width, fan_height)
        wall_glass = [item for item in specs if item["scope"] == "wall-glass"]
        portal_glass = [item for item in specs if item["scope"].startswith("portal-glass-")]
        self.assertEqual(len(wall_glass), 6)
        self.assertEqual(len(portal_glass), 8)
        front_face = max(
            frame(placement, wall)["forward"] + frame(placement, wall)["forwardExtent"]
            for wall in shell[:2]
        )
        for item in wall_glass:
            self.assertAlmostEqual(front_face - (item["forward"] - item["d"] / 2), 0.06)
            self.assertAlmostEqual(item["forward"] + item["d"] / 2 - front_face, 0.04)
        for portal_side in ("rear", "front"):
            side_glass = [item for item in portal_glass if item["portalSide"] == portal_side]
            first_portal_bottom = min(item["y"] - item["h"] / 2 for item in side_glass)
            self.assertLessEqual(first_portal_bottom, roof_base + 0.28)
            self.assertGreaterEqual(first_portal_bottom, roof_base)
            widths = [item["w"] for item in side_glass]
            self.assertTrue(all(a > b for a, b in zip(widths, widths[1:])))
        self.assertLess(len(build(placement, shell, 1, roof_base, fan_rear, fan_front, fan_width, fan_height)), len(specs))
        self.assertEqual(build(placement, shell, 2, roof_base, fan_rear, fan_front, fan_width, fan_height), [])

    def test_central_wayfinding_uses_tagged_solid_wall_and_never_lod2(self):
        build = self.helpers["stage_authoritative_wayfinding_specs"]
        fixtures = {
            "kunren": ("arena", {"x": 0, "y": 5, "z": -14, "w": 20, "h": 10, "d": 1}),
            "souko": ("hangar", {"x": -16, "y": 5, "z": 28, "w": 1, "h": 10, "d": 22}),
            "nakaniwa": ("villa", {"x": 25, "y": 4, "z": -18.5, "w": 18, "h": 8, "d": 1}),
        }
        for stage_id, (district, wall) in fixtures.items():
            tagged_wall = {**wall, "district": district}
            decoy = {
                "x": 1, "y": 5, "z": 1, "w": 10, "h": 10, "d": 1,
                "district": "wrong-district",
            }
            boxes = [decoy, tagged_wall]
            if stage_id == "kunren":
                boxes.append({**tagged_wall, "z": 14})
            stage = {"id": stage_id, "size": 200, "boxes": boxes}
            lod0 = build(stage, 0)
            expected_roles = (
                {
                    "sign", "direction-glyph-shaft",
                    "direction-glyph-tip", "direction-glyph-head", "stage-trim",
                }
                if stage_id == "kunren"
                else {"sign", "emissive-slit", "stage-trim"}
            )
            self.assertEqual({item["role"] for item in lod0}, expected_roles)
            self.assertEqual(
                {item["wallIndex"] for item in lod0},
                {1, 2} if stage_id == "kunren" else {1},
            )
            self.assertTrue(all(min(item["w"], item["d"]) <= 0.10 for item in lod0))
            lod1 = build(stage, 1)
            expected_lod1_roles = expected_roles - {"stage-trim"}
            self.assertEqual({item["role"] for item in lod1}, expected_lod1_roles)
            self.assertEqual(len(lod0), 12 if stage_id == "kunren" else 3)
            self.assertEqual(len(lod1), 10 if stage_id == "kunren" else 2)
            if stage_id == "kunren":
                self.assertEqual(sum(item["role"].startswith("direction-glyph") for item in lod0), 8)
                self.assertTrue(all(item["key"] == "emissive" for item in lod0 if item["role"] == "sign"))
                self.assertTrue(all(item["w"] == 9.0 and item["h"] == 4.0 for item in lod0 if item["role"] == "sign"))
            self.assertEqual(build(stage, 2), [])

    def test_kunren_wayfinding_faces_each_canonical_camera_and_fits_its_frustum(self):
        build = self.helpers["stage_authoritative_wayfinding_specs"]
        views = self.helpers["stage_central_camera_views"]
        stage = {
            "id": "kunren",
            "size": 200,
            "boxes": [
                # This is nearer the north camera but entirely outside the
                # horizontal view.  A centre-distance selector would fail.
                {"x": -35, "y": 5, "z": 18, "w": 20, "h": 10, "d": 1, "district": "arena"},
                {"x": -8, "y": 5, "z": -15, "w": 20, "h": 10, "d": 1, "district": "arena"},
                {"x": 7, "y": 5, "z": 16, "w": 24, "h": 10, "d": 1, "district": "arena"},
            ],
        }
        specs = build(stage, 0)
        signs = [item for item in specs if item["role"] == "sign"]
        self.assertEqual({item["viewId"] for item in signs}, {
            "central-street-north", "central-street-south",
        })
        view_by_id = {item["viewId"]: item for item in views(stage)}
        half_fov_tangent = 36.0 / (2.0 * 31.0)
        for sign in signs:
            view = view_by_id[sign["viewId"]]
            wall = stage["boxes"][sign["wallIndex"]]
            forward_x = view["targetX"] - view["cameraX"]
            forward_z = view["targetZ"] - view["cameraZ"]
            forward_length = math.hypot(forward_x, forward_z)
            forward_x /= forward_length
            forward_z /= forward_length
            right_x, right_z = -forward_z, forward_x
            to_x = sign["x"] - view["cameraX"]
            to_z = sign["z"] - view["cameraZ"]
            forward_distance = to_x * forward_x + to_z * forward_z
            lateral_distance = to_x * right_x + to_z * right_z
            lateral_half = abs(right_x) * sign["w"] / 2 + abs(right_z) * sign["d"] / 2
            self.assertGreater(forward_distance, 0)
            self.assertLessEqual(
                abs(lateral_distance) + lateral_half,
                forward_distance * half_fov_tangent + 1e-9,
            )
            # The chosen physical face normal points back to the camera.
            self.assertGreater(
                sign["faceSign"] * (view["cameraZ"] - float(wall["z"])),
                0,
            )
            self.assertGreaterEqual(sign["y"] - sign["h"] / 2, 1.65)
            self.assertGreaterEqual(sign["w"], 8.8)

        # Reordering the authoritative array may change only metadata indices,
        # never which physical wall/face is chosen.
        reversed_stage = {**stage, "boxes": list(reversed(stage["boxes"]))}
        reversed_signs = [
            item for item in build(reversed_stage, 0) if item["role"] == "sign"
        ]
        geometry = lambda item: (
            item["viewId"], round(item["x"], 6), round(item["y"], 6),
            round(item["z"], 6), round(item["w"], 6), round(item["h"], 6),
            item["faceSign"],
        )
        self.assertEqual(sorted(map(geometry, signs)), sorted(map(geometry, reversed_signs)))

    def test_frozen_canonical_souko_tower_relief_policy(self):
        stage = self.canonical_stage("souko")
        placements = {item["id"]: item for item in stage["landmarkPlacements"]}
        towers = [
            item for item in stage["boxes"]
            if item.get("landmarkPart") == "tower"
            and item.get("landmarkId") in placements
        ]
        self.assertEqual(len(towers), 4)

        build = self.helpers["souko_tower_face_specs"]
        frame = self.helpers["_landmark_face_frame"]
        for tower in towers:
            placement = placements[tower["landmarkId"]]
            projected = frame(placement, tower)
            face = projected["forward"] + projected["forwardExtent"]
            base = float(tower["y"]) - float(tower["h"]) / 2
            top = float(tower["y"]) + float(tower["h"]) / 2
            lateral_min = projected["lateral"] - projected["lateralExtent"]
            lateral_max = projected["lateral"] + projected["lateralExtent"]
            if abs(projected["forwardX"]) >= abs(projected["forwardZ"]):
                placement_lateral_span = float(placement["depth"])
                placement_forward_span = float(placement["width"])
            else:
                placement_lateral_span = float(placement["width"])
                placement_forward_span = float(placement["depth"])

            for lod, expected_roles in (
                (0, {"rail": 2, "collar": 4, "service-spine": 1, "id-light": 1}),
                (1, {"rail": 2, "collar": 2, "service-spine": 1, "id-light": 1}),
            ):
                specs = build(placement, tower, lod)
                for role, expected in expected_roles.items():
                    self.assertEqual(sum(item["role"] == role for item in specs), expected)
                bay_numbers = {item.get("bayNumber") for item in specs if item["role"] == "bay-number-segment"}
                expected_bay_numbers = {1, 2} if "stackhouse" in placement["id"] else {3, 4}
                self.assertEqual(len(bay_numbers), 1)
                self.assertTrue(bay_numbers.issubset(expected_bay_numbers))
                if "stackhouse" in placement["id"]:
                    self.assertEqual(sum(item["role"] == "hoist-header" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "cable-guide" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "hoist-carriage" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "hoist-door" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "pulley-datum" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "cable-chevron-block" for item in specs), 5)
                    self.assertEqual(sum(item["role"] == "vent-louver" for item in specs), 0)
                else:
                    self.assertEqual(sum(item["role"] == "customs-header" for item in specs), 1)
                    self.assertEqual(
                        sum(item["role"] == "vent-louver" for item in specs),
                        6 if lod == 0 else 3,
                    )
                    self.assertEqual(sum(item["role"] == "customs-scan-datum" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "customs-scan-panel" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "customs-scan-frame" for item in specs), 4)
                    self.assertEqual(sum(item["role"] == "customs-vent-block" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "customs-inspection-field" for item in specs), 1)
                    self.assertEqual(sum(item["role"] == "customs-inspection-frame" for item in specs), 4)
                    self.assertEqual(
                        sum(item["role"] == "customs-intake-blade" for item in specs),
                        4 if lod == 0 else 3,
                    )
                    self.assertEqual(sum(item["role"] == "cable-guide" for item in specs), 0)
                    number = next(item for item in specs if item["role"] == "bay-number-backing")
                    badge = next(item for item in specs if item["role"] == "customs-inspection-field")
                    number_interval = (
                        number["lateral"] - number["w"] / 2,
                        number["lateral"] + number["w"] / 2,
                    )
                    badge_interval = (
                        badge["lateral"] - badge["w"] / 2,
                        badge["lateral"] + badge["w"] / 2,
                    )
                    self.assertGreaterEqual(
                        max(
                            number_interval[0] - badge_interval[1],
                            badge_interval[0] - number_interval[1],
                        ),
                        0.10,
                    )
                    self.assertGreaterEqual(badge["y"] - badge["h"] / 2, base + float(tower["h"]) * 0.60)
                self.assertEqual(sum(item["role"] == "bay-number-backing" for item in specs), 1)
                for item in specs:
                    inside = face - (item["forward"] - item["d"] / 2)
                    outside = item["forward"] + item["d"] / 2 - face
                    self.assertGreaterEqual(inside, -1e-9)
                    self.assertLessEqual(inside, 0.140000001)
                    self.assertGreaterEqual(outside, -1e-9)
                    self.assertLessEqual(outside, 0.040000001)
                    self.assertGreaterEqual(item["lateral"] - item["w"] / 2, lateral_min)
                    self.assertLessEqual(item["lateral"] + item["w"] / 2, lateral_max)
                    self.assertGreaterEqual(item["y"] - item["h"] / 2, base)
                    self.assertLessEqual(item["y"] + item["h"] / 2, top)
                    self.assertGreaterEqual(item["y"] - item["h"] / 2, 1.65)
                    self.assertGreaterEqual(
                        item["lateral"] - item["w"] / 2,
                        -placement_lateral_span / 2,
                    )
                    self.assertLessEqual(
                        item["lateral"] + item["w"] / 2,
                        placement_lateral_span / 2,
                    )
                    self.assertGreaterEqual(
                        item["forward"] - item["d"] / 2,
                        -placement_forward_span / 2,
                    )
                    self.assertLessEqual(
                        item["forward"] + item["d"] / 2,
                        placement_forward_span / 2,
                    )
            self.assertEqual(build(placement, tower, 2), [])

    def test_frozen_canonical_nakaniwa_glazing_contacts_supported_faces(self):
        stage = self.canonical_stage("nakaniwa")
        placement = next(
            item for item in stage["landmarkPlacements"]
            if item["id"] == "nakaniwa-kakou-conservatory-citadel"
        )
        shell = [
            item for item in stage["boxes"]
            if item.get("landmarkId") == placement["id"]
        ]
        frame = self.helpers["_landmark_face_frame"]
        projected = [(item, frame(placement, item)) for item in shell]
        support_parts = {"wall", "interior", "tower", "upper-walk"}
        fan_width = float(placement["width"]) * 0.78
        fan_rear = -float(placement["depth"]) * 0.30
        fan_front = float(placement["depth"]) * 0.28
        fan_depth = fan_front - fan_rear

        supports = []
        for item, item_frame in projected:
            if item.get("landmarkPart") not in support_parts:
                continue
            lateral_overlap = fan_width / 2 + item_frame["lateralExtent"] - abs(item_frame["lateral"])
            forward_overlap = fan_depth / 2 + item_frame["forwardExtent"] - abs(
                (fan_rear + fan_front) / 2 - item_frame["forward"]
            )
            if lateral_overlap >= 0.20 and forward_overlap >= 0.20:
                supports.append(item)
        self.assertTrue(supports)
        roof_base = max(float(item["y"]) + float(item["h"]) / 2 for item in supports) - 0.16
        fan_height = max(12.0, float(placement["height"]) - roof_base - 0.45)

        walls = [(item, item_frame) for item, item_frame in projected if item.get("landmarkPart") == "wall"]
        front = max(item_frame["forward"] for _, item_frame in walls)
        front_walls = [
            (item, item_frame) for item, item_frame in walls
            if front - item_frame["forward"] <= 0.25
            and item_frame["lateralExtent"] >= item_frame["forwardExtent"] * 2
        ]
        self.assertEqual(len(front_walls), 2)

        build = self.helpers["nakaniwa_conservatory_face_specs"]
        for lod, expected_wall_glass, expected_portal_glass in ((0, 6, 4), (1, 4, 2)):
            specs = build(placement, shell, lod, roof_base, fan_rear, fan_front, fan_width, fan_height)
            wall_specs = [item for item in specs if item["scope"].startswith("wall-")]
            wall_glass = [item for item in specs if item["scope"] == "wall-glass"]
            portal_glass = [item for item in specs if item["scope"].startswith("portal-glass-")]
            portal_mullions = [item for item in specs if item["scope"].startswith("portal-mullion-")]
            side_glass = [item for item in specs if item["scope"].startswith("side-glass-")]
            side_mullions = [item for item in specs if item["scope"].startswith("side-mullion-")]
            side_transoms = [item for item in specs if item["scope"].startswith("side-transom-")]
            side_eaves = [item for item in specs if item["scope"].startswith("side-eave-")]
            vestibule_glass = [item for item in specs if item["scope"] == "vestibule-glass"]
            vestibule_mullions = [item for item in specs if item["scope"] == "vestibule-mullion"]
            vestibule_crossbars = [item for item in specs if item["scope"] == "vestibule-crossbar"]
            vestibule_ties = [item for item in specs if item["scope"] == "vestibule-top-tie"]
            vestibule_returns = [item for item in specs if item["scope"] == "vestibule-return"]
            recess_mullions = [item for item in specs if item["scope"] == "vestibule-recess-mullion"]
            recess_crossbars = [item for item in specs if item["scope"] == "vestibule-recess-crossbar"]
            recess_fins = [item for item in specs if item["scope"] == "vestibule-recess-fin"]
            self.assertEqual(len(wall_glass), expected_wall_glass)
            self.assertEqual(len(portal_glass), expected_portal_glass * 2)
            self.assertEqual(len(side_glass), 24 if lod == 0 else 8)
            self.assertEqual(len(side_mullions), 10 if lod == 0 else 6)
            self.assertEqual(len(side_transoms), 4 if lod == 0 else 2)
            self.assertEqual(len(side_eaves), 2)
            self.assertEqual(len(vestibule_glass), 12 if lod == 0 else 4)
            self.assertEqual(len(vestibule_mullions), 5 if lod == 0 else 3)
            self.assertEqual(len(vestibule_crossbars), 2 if lod == 0 else 1)
            self.assertEqual(len(vestibule_ties), 1)
            self.assertEqual(len(vestibule_returns), 2)
            self.assertEqual(len(recess_mullions), 5 if lod == 0 else 3)
            self.assertEqual(len(recess_crossbars), 2 if lod == 0 else 1)
            self.assertEqual(len(recess_fins), 3 if lod == 0 else 2)
            self.assertEqual(
                {item["key"] for item in vestibule_glass},
                {"glass", "water"},
            )

            for item in wall_specs:
                owner = next(
                    (
                        (wall, wall_frame) for wall, wall_frame in front_walls
                        if item["lateral"] - item["w"] / 2
                        >= wall_frame["lateral"] - wall_frame["lateralExtent"] - 1e-9
                        and item["lateral"] + item["w"] / 2
                        <= wall_frame["lateral"] + wall_frame["lateralExtent"] + 1e-9
                        and item["y"] - item["h"] / 2
                        >= float(wall["y"]) - float(wall["h"]) / 2 - 1e-9
                        and item["y"] + item["h"] / 2
                        <= float(wall["y"]) + float(wall["h"]) / 2 + 1e-9
                    ),
                    None,
                )
                self.assertIsNotNone(owner)
                wall, wall_frame = owner
                face = wall_frame["forward"] + wall_frame["forwardExtent"]
                self.assertAlmostEqual(face - (item["forward"] - item["d"] / 2), 0.06)
                self.assertAlmostEqual(item["forward"] + item["d"] / 2 - face, 0.04)

            portal_beam_bottom = roof_base + 0.28 - 0.26
            portal_beam_top = roof_base + 0.28 + 0.26
            for portal_side, portal_forward, face_sign in (
                ("rear", fan_rear, -1.0),
                ("front", fan_front, 1.0),
            ):
                portal_side_glass = sorted(
                    (item for item in portal_glass if item["portalSide"] == portal_side),
                    key=lambda item: item["y"],
                )
                first_bottom = portal_side_glass[0]["y"] - portal_side_glass[0]["h"] / 2
                self.assertLess(first_bottom, portal_beam_top)
                self.assertGreater(portal_side_glass[0]["y"] + portal_side_glass[0]["h"] / 2, portal_beam_bottom)
                for lower, upper in zip(portal_side_glass, portal_side_glass[1:]):
                    self.assertLessEqual(
                        upper["y"] - upper["h"] / 2,
                        lower["y"] + lower["h"] / 2 + 1e-9,
                    )
                for glass in portal_side_glass:
                    half_width = glass["w"] / 2
                    same_course = [
                        item for item in portal_mullions
                        if item["portalSide"] == portal_side
                        and math.isclose(item["y"], glass["y"], abs_tol=1e-9)
                    ]
                    self.assertEqual(len(same_course), 3)
                    self.assertEqual(
                        [round(item["lateral"], 9) for item in same_course],
                        [round(-half_width, 9), 0.0, round(half_width, 9)],
                    )
                    rise = (glass["y"] - roof_base) / fan_height
                    gable_half_width = fan_width * 0.50 * (1.0 - rise)
                    edge_mullion = max(same_course, key=lambda item: item["lateral"])
                    gable_contact_gap = (
                        gable_half_width
                        - (edge_mullion["lateral"] + edge_mullion["w"] / 2)
                    )
                    self.assertGreaterEqual(gable_contact_gap, -0.27)
                    self.assertLessEqual(gable_contact_gap, 0.27)
                    self.assertGreaterEqual(glass["y"] - glass["h"] / 2, roof_base)
                    self.assertLessEqual(glass["y"] + glass["h"] / 2, roof_base + fan_height)
                    self.assertLessEqual(half_width, fan_width / 2)
                    inner = face_sign * (
                        portal_forward - (glass["forward"] - face_sign * glass["d"] / 2)
                    )
                    outside = face_sign * (
                        glass["forward"] + face_sign * glass["d"] / 2 - portal_forward
                    )
                    self.assertAlmostEqual(inner, 0.06)
                    self.assertAlmostEqual(outside, 0.04)
                    self.assertGreaterEqual(glass["y"] - glass["h"] / 2, 1.65)

            rear_walk = min(
                (
                    (item, item_frame) for item, item_frame in projected
                    if item.get("landmarkPart") == "upper-walk"
                    and abs(item_frame["lateral"]) <= 0.25
                    and item_frame["lateralExtent"] >= fan_width * 0.25
                ),
                key=lambda pair: abs(pair[1]["forward"] - fan_rear),
            )
            front_walk = min(
                (
                    (item, item_frame) for item, item_frame in projected
                    if item.get("landmarkPart") == "upper-walk"
                    and abs(item_frame["lateral"]) <= 0.25
                    and item_frame["lateralExtent"] >= fan_width * 0.25
                ),
                key=lambda pair: abs(pair[1]["forward"] - fan_front),
            )
            sill_top = min(
                float(rear_walk[0]["y"]) + float(rear_walk[0]["h"]) / 2,
                float(front_walk[0]["y"]) + float(front_walk[0]["h"]) / 2,
            )
            for side_sign in (-1.0, 1.0):
                side_items = [item for item in side_glass if item["sideSign"] == side_sign]
                side_frames = [item["lateral"] for item in side_items]
                self.assertEqual(len({round(value, 9) for value in side_frames}), 1)
                side_lateral = side_frames[0]
                self.assertEqual(math.copysign(1.0, side_lateral), side_sign)
                self.assertGreaterEqual(
                    min(item["y"] - item["h"] / 2 for item in side_items),
                    sill_top - 0.10,
                )
                self.assertGreaterEqual(
                    min(item["y"] - item["h"] / 2 for item in side_items),
                    6.5,
                )
                side_tower_frames = [
                    item_frame for item, item_frame in projected
                    if item.get("landmarkPart") == "tower"
                    and item_frame["lateral"] * side_sign > 0
                ]
                self.assertTrue(any(
                    abs(side_lateral - item_frame["lateral"])
                    <= item_frame["lateralExtent"] + 1e-9
                    for item_frame in side_tower_frames
                ))
                roof_contact_y = roof_base + fan_height * (
                    1.0 - abs(side_lateral) / (fan_width / 2)
                )
                side_eave = next(item for item in side_eaves if item["sideSign"] == side_sign)
                self.assertAlmostEqual(side_eave["y"], roof_contact_y)
                side_mullion_top = max(
                    item["y"] + item["h"] / 2
                    for item in side_mullions if item["sideSign"] == side_sign
                )
                self.assertAlmostEqual(side_mullion_top - roof_contact_y, 0.06)

            vestibule_bottom = min(
                item["y"] - item["h"] / 2
                for item in vestibule_glass + vestibule_mullions
            )
            self.assertGreaterEqual(vestibule_bottom, 4.0)
            front_interiors = [
                (item, item_frame) for item, item_frame in projected
                if item.get("landmarkPart") == "interior"
                and item_frame["forward"] <= fan_front + 0.25
                and item_frame["lateralExtent"] >= item_frame["forwardExtent"] * 2
            ]
            left_interior = max(
                (pair for pair in front_interiors if pair[1]["lateral"] < 0),
                key=lambda pair: pair[1]["forward"],
            )[1]
            right_interior = max(
                (pair for pair in front_interiors if pair[1]["lateral"] > 0),
                key=lambda pair: pair[1]["forward"],
            )[1]
            left_inner = left_interior["lateral"] + left_interior["lateralExtent"]
            right_inner = right_interior["lateral"] - right_interior["lateralExtent"]
            vestibule_left = min(
                item["lateral"] - item["w"] / 2
                for item in vestibule_mullions + vestibule_crossbars
            )
            vestibule_right = max(
                item["lateral"] + item["w"] / 2
                for item in vestibule_mullions + vestibule_crossbars
            )
            self.assertLessEqual(vestibule_left, left_inner - 0.099)
            self.assertGreaterEqual(vestibule_right, right_inner + 0.099)
            tie = vestibule_ties[0]
            self.assertLessEqual(tie["forward"] - tie["d"] / 2, vestibule_glass[0]["forward"] - 0.119)
            self.assertGreaterEqual(tie["forward"] + tie["d"] / 2, fan_front + 0.119)
            recess_forward = recess_mullions[0]["forward"]
            self.assertGreaterEqual(vestibule_glass[0]["forward"] - recess_forward, 2.4)
            self.assertTrue(all(
                math.isclose(item["forward"], recess_forward, abs_tol=1e-9)
                for item in recess_mullions + recess_crossbars
            ))
            for item in vestibule_returns:
                self.assertLessEqual(
                    item["forward"] - item["d"] / 2,
                    recess_forward - 0.099,
                )
                self.assertGreaterEqual(
                    item["forward"] + item["d"] / 2,
                    vestibule_glass[0]["forward"] + 0.099,
                )
                self.assertGreaterEqual(item["y"] - item["h"] / 2, 4.0)
            self.assertTrue(all(item["w"] <= 1.34 for item in recess_fins))
        self.assertEqual(build(placement, shell, 2, roof_base, fan_rear, fan_front, fan_width, fan_height), [])

    def test_frozen_canonical_wayfinding_is_collision_seated_and_bounded(self):
        build = self.helpers["stage_authoritative_wayfinding_specs"]
        expected_district = {"kunren": "arena", "souko": "hangar", "nakaniwa": "villa"}
        for stage_id, district in expected_district.items():
            stage = self.canonical_stage(stage_id)
            for lod, expected_count in (
                (0, 12 if stage_id == "kunren" else 3),
                (1, 10 if stage_id == "kunren" else 2),
            ):
                specs = build(stage, lod)
                self.assertEqual(len(specs), expected_count)
                wall_indices = {item["wallIndex"] for item in specs}
                self.assertEqual(len(wall_indices), 2 if stage_id == "kunren" else 1)
                eligible = [
                    (math.hypot(float(box["x"]), float(box["z"])), index, box)
                    for index, box in enumerate(stage["boxes"])
                    if box.get("district") == district
                    and not box.get("landmarkId")
                    and not box.get("visualReplacement")
                    and float(box["h"]) >= 4.0
                    and min(float(box["w"]), float(box["d"])) <= 1.25
                    and max(float(box["w"]), float(box["d"])) >= 8.0
                ]
                if stage_id != "kunren":
                    self.assertEqual(wall_indices, {min(eligible, key=lambda item: (item[0], item[1]))[1]})

                for item in specs:
                    wall = stage["boxes"][item["wallIndex"]]
                    self.assertEqual(wall.get("district"), district)
                    self.assertFalse(wall.get("landmarkId"))
                    self.assertFalse(wall.get("visualReplacement"))
                    long_x = float(wall["w"]) >= float(wall["d"])
                    thickness = float(wall["d"] if long_x else wall["w"])
                    normal_coordinate = float(wall["z"] if long_x else wall["x"])
                    if stage_id == "kunren":
                        side = 1.0 if (
                            item["cameraZ"] if long_x else item["cameraX"]
                        ) >= normal_coordinate else -1.0
                    else:
                        side = -1.0 if normal_coordinate > 0 else 1.0
                    face = normal_coordinate + side * thickness / 2
                    face_projected = side * face
                    tangent_centre = float(wall["x"] if long_x else wall["z"])
                    tangent_extent = float(wall["w"] if long_x else wall["d"]) / 2
                    base = float(wall["y"]) - float(wall["h"]) / 2
                    top = float(wall["y"]) + float(wall["h"]) / 2
                    normal_centre = float(item["z"] if long_x else item["x"])
                    normal_half = float(item["d"] if long_x else item["w"]) / 2
                    tangent = float(item["x"] if long_x else item["z"])
                    tangent_half = float(item["w"] if long_x else item["d"]) / 2
                    centre_projected = side * normal_centre
                    inside = face_projected - (centre_projected - normal_half)
                    outside = centre_projected + normal_half - face_projected
                    if stage_id == "kunren":
                        expected_outside = (
                            0.04
                            if item["role"] in {"sign", "stage-trim"}
                            else 0.06
                        )
                        self.assertAlmostEqual(outside, expected_outside)
                        self.assertAlmostEqual(
                            inside,
                            0.06
                            if item["role"] == "sign"
                            else 0.04 if item["role"] == "stage-trim"
                            else 0.02,
                        )
                    else:
                        self.assertAlmostEqual(inside, 0.06)
                        self.assertAlmostEqual(outside, 0.04)
                    self.assertGreaterEqual(tangent - tangent_half, tangent_centre - tangent_extent)
                    self.assertLessEqual(tangent + tangent_half, tangent_centre + tangent_extent)
                    self.assertGreaterEqual(float(item["y"]) - float(item["h"]) / 2, base)
                    self.assertLessEqual(float(item["y"]) + float(item["h"]) / 2, top)
                    self.assertGreaterEqual(float(item["y"]) - float(item["h"]) / 2, 1.65)
                    self.assertLessEqual(abs(normal_centre) + normal_half, float(stage["size"]) / 2)
                    self.assertLessEqual(abs(tangent) + tangent_half, float(stage["size"]) / 2)
                    if stage_id == "kunren":
                        forward_x = item["targetX"] - item["cameraX"]
                        forward_z = item["targetZ"] - item["cameraZ"]
                        length = math.hypot(forward_x, forward_z)
                        forward_x, forward_z = forward_x / length, forward_z / length
                        right_x, right_z = -forward_z, forward_x
                        to_x = item["x"] - item["cameraX"]
                        to_z = item["z"] - item["cameraZ"]
                        distance = to_x * forward_x + to_z * forward_z
                        lateral_distance = to_x * right_x + to_z * right_z
                        lateral_half = abs(right_x) * item["w"] / 2 + abs(right_z) * item["d"] / 2
                        self.assertGreater(distance, 0)
                        self.assertLessEqual(
                            abs(lateral_distance) + lateral_half,
                            distance * 36.0 / (2.0 * 31.0) + 1e-9,
                        )
            self.assertEqual(build(stage, 2), [])

    def test_dense_stage_manifest_keeps_runtime_lod1_medium_path(self):
        self.assertEqual(self.helpers["stage_asset_min_tier"](), "medium")


if __name__ == "__main__":
    unittest.main()
