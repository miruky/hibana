import ast
from pathlib import Path
import unittest


GENERATOR_PATH = Path(__file__).with_name("build_all_stages.py")


def load_roof_monitor_builder():
    tree = ast.parse(GENERATOR_PATH.read_text(encoding="utf-8"), filename=str(GENERATOR_PATH))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "add_souko_roof_monitor"
    )
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(GENERATOR_PATH), "exec"), namespace)
    return namespace["add_souko_roof_monitor"]


class RecordingBuilder:
    def __init__(self):
        self.boxes = []
        self.gables = []

    def add_box(self, x, y, z, width, height, depth, key):
        self.boxes.append({
            "x": x,
            "y": y,
            "z": z,
            "w": width,
            "h": height,
            "d": depth,
            "key": key,
        })

    def add_gable_roof(self, *args):
        self.gables.append(args)


class SoukoRoofMonitorLod2Tests(unittest.TestCase):
    def test_lod2_matches_all_authoritative_proxy_envelopes(self):
        add_monitor = load_roof_monitor_builder()
        support_sizes = [
            (24, 58), (58, 24), (58, 24),
            (22, 40), (40, 22), (40, 22),
            (24, 12), (24, 12), (12, 24),
            (12, 24), (24, 12), (24, 12),
        ]
        all_boxes = []

        for support_index, (width, depth) in enumerate(support_sizes):
            builder = RecordingBuilder()
            top = 10.0 + support_index
            box = {"x": support_index * 100.0, "z": -support_index * 100.0, "w": width, "d": depth}
            add_monitor(builder, box, top, support_index, 2)

            self.assertEqual(builder.gables, [])
            self.assertEqual(sum(item["key"] == "trim" for item in builder.boxes), 1)
            self.assertEqual(sum(item["key"] == "wall_weathered" for item in builder.boxes), 1)

            variant = support_index % 3
            segment_count = 2 if variant == 2 else 1
            self.assertEqual(sum(item["key"] == "wall_cool" for item in builder.boxes), segment_count)
            self.assertEqual(sum(item["key"] == "roof" for item in builder.boxes), segment_count)

            curb = next(item for item in builder.boxes if item["key"] == "wall_weathered")
            self.assertAlmostEqual(curb["y"] - curb["h"] / 2, top - 0.04)
            self.assertAlmostEqual(curb["y"] + curb["h"] / 2, top + 0.46)

            bodies = [item for item in builder.boxes if item["key"] == "wall_cool"]
            roofs = [item for item in builder.boxes if item["key"] == "roof"]
            for body, roof in zip(bodies, roofs, strict=True):
                self.assertAlmostEqual(body["y"] - body["h"] / 2, top + 0.41)
                self.assertAlmostEqual((curb["y"] + curb["h"] / 2) - (body["y"] - body["h"] / 2), 0.05)
                self.assertAlmostEqual(roof["y"] - roof["h"] / 2, body["y"] + body["h"] / 2 - 0.06)
                long_x = width >= depth
                body_tangent_span = body["w"] if long_x else body["d"]
                body_normal_span = body["d"] if long_x else body["w"]
                roof_tangent_span = roof["w"] if long_x else roof["d"]
                roof_normal_span = roof["d"] if long_x else roof["w"]
                self.assertAlmostEqual(roof_tangent_span, body_tangent_span + 0.50)
                self.assertAlmostEqual(roof_normal_span, body_normal_span + 0.32)

            all_boxes.extend(builder.boxes)

        self.assertEqual(sum(item["key"] == "wall_weathered" for item in all_boxes), 12)
        self.assertEqual(sum(item["key"] == "wall_cool" for item in all_boxes), 16)
        self.assertEqual(sum(item["key"] == "roof" for item in all_boxes), 16)


if __name__ == "__main__":
    unittest.main()
