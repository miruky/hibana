import ast
import math
from pathlib import Path
import unittest


GENERATOR_PATH = Path(__file__).with_name("build_all_stages.py")
ARRIVAL_FUNCTIONS = {
    "landmark_arrival_frame_specs",
    "add_landmark_arrival_frame",
    "add_landmark_approach_guidance",
}


def load_arrival_namespace():
    tree = ast.parse(GENERATOR_PATH.read_text(encoding="utf-8"), filename=str(GENERATOR_PATH))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name.startswith("ARRIVAL_FRAME_") for name in names):
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in ARRIVAL_FUNCTIONS:
            selected.append(node)
    namespace = {"math": math}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(GENERATOR_PATH), "exec"), namespace)
    return namespace


ARRIVAL = load_arrival_namespace()


def make_gate_case(stage_id, landmark_index, axis, wall_top, wall_length):
    entrance_x, entrance_z = 7.0, -11.0
    normal = (1.0, 0.0) if axis == "x" else (0.0, 1.0)
    tangent = (-normal[1], normal[0])
    placement = {
        "id": f"{stage_id}-arrival-{landmark_index}",
        "cx": entrance_x + normal[0] * 44.0,
        "cz": entrance_z + normal[1] * 44.0,
        "entrance": [entrance_x, entrance_z],
        "approach": {
            "start": [entrance_x - normal[0] * 20.0, entrance_z - normal[1] * 20.0],
            "end": [entrance_x, entrance_z],
            "width": 12.0,
        },
    }
    walls = []
    for side in (-1.0, 1.0):
        tangent_center = side * (14.0 + wall_length / 2)
        x = entrance_x + tangent[0] * tangent_center + normal[0] * 0.8
        z = entrance_z + tangent[1] * tangent_center + normal[1] * 0.8
        walls.append({
            "x": x,
            "y": wall_top / 2,
            "z": z,
            "w": wall_length if abs(tangent[0]) > 0.5 else 1.4,
            "h": wall_top,
            "d": wall_length if abs(tangent[1]) > 0.5 else 1.4,
            "landmarkPart": "wall",
        })
    return placement, walls


class RecordingBuilder:
    def __init__(self):
        self.oriented_boxes = []

    def add_oriented_box(self, *args):
        self.oriented_boxes.append(args)


class LandmarkArrivalFrameTests(unittest.TestCase):
    CASES = (
        ("kunren", 0, "x", 10.29, 14.0),
        ("kunren", 1, "x", 11.55, 21.0),
        ("souko", 0, "x", 13.00, 19.0),
        ("souko", 1, "z", 9.87, 32.0),
        ("nakaniwa", 0, "z", 9.03, 32.0),
        ("nakaniwa", 1, "z", 10.50, 24.0),
    )

    def test_all_six_frames_preserve_the_authoritative_opening_and_wall_contact(self):
        derive = ARRIVAL["landmark_arrival_frame_specs"]
        for stage_id, landmark_index, axis, wall_top, wall_length in self.CASES:
            with self.subTest(stage=stage_id, landmark=landmark_index):
                placement, walls = make_gate_case(
                    stage_id, landmark_index, axis, wall_top, wall_length,
                )
                specs = derive(placement, list(reversed(walls)))
                self.assertAlmostEqual(specs["openingWidth"], 28.0)
                self.assertAlmostEqual(specs["approachLength"], 20.0)
                self.assertEqual(len(specs["posts"]), 2)
                for post in specs["posts"]:
                    self.assertAlmostEqual(post["w"], 1.48)
                    self.assertAlmostEqual(post["d"], 1.48)
                    self.assertAlmostEqual(post["normalOutset"], 0.04)
                    self.assertAlmostEqual(post["routeFaceOutset"], 0.0)
                    # A post's closest face remains 46cm inside the solid wall;
                    # no player-height geometry enters the exact 28m opening.
                    self.assertAlmostEqual(post["openingClearance"], 14.46)
                    self.assertAlmostEqual(post["y"] - post["h"] / 2, 0.0)
                header = specs["header"]
                self.assertAlmostEqual(header["h"], 0.50)
                self.assertAlmostEqual(header["bottom"], wall_top - 0.10)
                self.assertAlmostEqual(header["top"], wall_top + 0.40)
                self.assertTrue(all(abs(post["h"] - header["top"]) < 1e-9 for post in specs["posts"]))

    def test_frame_components_keep_ground_wall_and_header_support_chains(self):
        derive = ARRIVAL["landmark_arrival_frame_specs"]
        for stage_id, landmark_index, axis, wall_top, wall_length in self.CASES:
            with self.subTest(stage=stage_id, landmark=landmark_index):
                placement, walls = make_gate_case(
                    stage_id, landmark_index, axis, wall_top, wall_length,
                )
                specs = derive(placement, walls)
                header = specs["header"]
                # Both posts are grounded and pass through the complete header
                # height; the header itself overlaps the real wall tops by 10cm.
                for post in specs["posts"]:
                    self.assertLessEqual(post["y"] - post["h"] / 2, 1e-9)
                    self.assertGreaterEqual(post["y"] + post["h"] / 2, header["top"])
                self.assertAlmostEqual(specs["gateTop"] - header["bottom"], 0.10)

                # Plan bounds stay inside the two long wall solids. The 4cm
                # half-thickness delta is shifted inward, so the frame cannot
                # inflate hibanaLandmarkBounds toward the route. The approach
                # floor is emitted by the ordinary LOD builder as well.
                self.assertGreaterEqual(header["w"], 28.0)
                self.assertLessEqual(header["w"], 28.0 + 2 * 1.20 + 1.48 + 1e-9)
                outer_wall_edge = 14.0 + wall_length
                for post in specs["posts"]:
                    self.assertLessEqual(abs(post["tangent"]) + post["w"] / 2, outer_wall_edge)
                    self.assertAlmostEqual(post["routeFaceOutset"], 0.0)

    def test_lod_policy_keeps_frame_in_zero_and_one_and_lamps_only_in_zero(self):
        add_frame = ARRIVAL["add_landmark_arrival_frame"]
        placement, walls = make_gate_case("kunren", 0, "x", 10.29, 14.0)
        stage = {"id": "kunren"}
        counts = []
        for lod in (0, 1, 2):
            builder = RecordingBuilder()
            add_frame(builder, stage, lod, placement, walls)
            counts.append(len(builder.oriented_boxes))
        self.assertEqual(counts, [5, 3, 0])
        self.assertEqual(
            sum(box[-1] == "emissive" for box in RecordingAndRun(add_frame, stage, 0, placement, walls)),
            2,
        )

    def test_stage_material_language_and_vertical_lamp_contract(self):
        add_frame = ARRIVAL["add_landmark_arrival_frame"]
        derive = ARRIVAL["landmark_arrival_frame_specs"]
        expected_materials = {
            "kunren": ("wall_cool", "accent"),
            "souko": ("wall_alt", "accent"),
            "nakaniwa": ("wood", "roof"),
        }
        for stage_id, landmark_index, axis, wall_top, wall_length in self.CASES:
            with self.subTest(stage=stage_id, landmark=landmark_index):
                placement, walls = make_gate_case(
                    stage_id, landmark_index, axis, wall_top, wall_length,
                )
                specs = derive(placement, walls)
                boxes = RecordingAndRun(add_frame, {"id": stage_id}, 0, placement, walls)
                post_key, header_key = expected_materials[stage_id]
                self.assertEqual([box[-1] for box in boxes[:2]], [post_key, post_key])
                self.assertEqual(boxes[2][-1], header_key)
                self.assertEqual([box[-1] for box in boxes[3:]], ["emissive", "emissive"])

                entrance_x, entrance_z = placement["entrance"]
                normal_x, normal_z = specs["normal"]
                tangent_x, tangent_z = specs["tangent"]
                for lamp, post in zip(boxes[3:], specs["posts"]):
                    x, y, z, width, height, depth, _yaw, _key = lamp
                    self.assertAlmostEqual(width, 0.24)
                    self.assertAlmostEqual(height, 1.80)
                    self.assertAlmostEqual(depth, 0.10)
                    self.assertAlmostEqual(y, 2.60)
                    relative_x, relative_z = x - entrance_x, z - entrance_z
                    self.assertAlmostEqual(relative_x * tangent_x + relative_z * tangent_z, post["tangent"])
                    expected_normal = post["normal"] - (post["d"] / 2 + depth / 2 - 0.02)
                    self.assertAlmostEqual(relative_x * normal_x + relative_z * normal_z, expected_normal)

    def test_twenty_metre_approach_guides_show_direction_and_stay_inside_lane(self):
        add_guidance = ARRIVAL["add_landmark_approach_guidance"]
        placements = [
            make_gate_case("souko", 0, "x", 13.0, 19.0)[0],
            make_gate_case("souko", 1, "z", 9.87, 32.0)[0],
        ]
        stage = {"id": "souko", "landmarkPlacements": placements}
        for lod, expected in ((0, 8), (1, 8), (2, 0)):
            with self.subTest(lod=lod):
                builder = RecordingBuilder()
                add_guidance(builder, stage, lod)
                self.assertEqual(len(builder.oriented_boxes), expected)
                if lod == 2:
                    continue
                for placement_index, placement in enumerate(placements):
                    boxes = builder.oriented_boxes[placement_index * 4:(placement_index + 1) * 4]
                    centreline = boxes[0]
                    _x, y, _z, length, height, width, _yaw, material = centreline
                    self.assertAlmostEqual(length, 20.0)
                    self.assertAlmostEqual(width, 0.18)
                    self.assertAlmostEqual(y - height / 2, 0.026)
                    self.assertEqual(material, "accent")

                    start_x, start_z = placement["approach"]["start"]
                    end_x, end_z = placement["approach"]["end"]
                    dx, dz = end_x - start_x, end_z - start_z
                    route_length = math.hypot(dx, dz)
                    normal_x, normal_z = dx / route_length, dz / route_length
                    for cross, expected_progress in zip(boxes[1:], (0.18, 0.55, 0.90)):
                        x, cross_y, z, cross_length, cross_height, cross_width, _yaw, cross_material = cross
                        progress = ((x - start_x) * normal_x + (z - start_z) * normal_z) / route_length
                        self.assertAlmostEqual(progress, expected_progress)
                        self.assertAlmostEqual(cross_length, 10.6)
                        self.assertLessEqual(cross_length, placement["approach"]["width"] - 0.4)
                        self.assertAlmostEqual(cross_width, 0.18)
                        self.assertAlmostEqual(cross_y - cross_height / 2, 0.026)
                        self.assertEqual(cross_material, "accent")

    def test_nakaniwa_approach_guides_use_the_roof_material_family(self):
        add_guidance = ARRIVAL["add_landmark_approach_guidance"]
        placement = make_gate_case("nakaniwa", 0, "z", 9.03, 32.0)[0]
        boxes = RecordingAndRun(
            add_guidance,
            {"id": "nakaniwa", "landmarkPlacements": [placement]},
            0,
        )
        self.assertEqual(len(boxes), 4)
        self.assertTrue(all(box[-1] == "roof" for box in boxes))


def RecordingAndRun(function, *args):
    builder = RecordingBuilder()
    function(builder, *args)
    return builder.oriented_boxes


if __name__ == "__main__":
    unittest.main()
