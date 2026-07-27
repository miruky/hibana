import unittest

from tools.blender.a23.kit import (
    RenderKit,
    SpecKit,
    distance_to_camera,
    distance_to_point,
    frame_cells,
    is_onscreen,
    spec_center,
)
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6


class SpecKitAdapterTests(unittest.TestCase):
    def test_from_module_binds_every_primitive(self):
        kit = SpecKit.from_module(R6)
        self.assertIs(kit.box, R6._box)
        self.assertIs(kit.chamfer_box, R6._chamfer_box)
        self.assertIs(kit.panel, R6._panel)
        self.assertIs(kit.sweep, R6._sweep)
        self.assertIs(kit.cylinder, R6._cylinder)
        self.assertIs(kit.leaf_cluster, R6._leaf_cluster)
        self.assertIs(kit.spec_bounds, R6.spec_bounds)
        self.assertIs(kit.estimated_triangles, R6.estimated_triangles)
        self.assertIs(kit.project_spec_frame, R6._project_spec_frame)

    def test_render_kit_from_module_binds_every_helper(self):
        render_kit = RenderKit.from_module(R6)
        self.assertIs(render_kit.reset_scene, R6._reset_scene)
        self.assertIs(render_kit.mesh_builder, R6.A21MeshBuilder)
        self.assertIs(render_kit.emit_specs_to_builder, R6.emit_specs_to_builder)


class GeometryHelperTests(unittest.TestCase):
    def setUp(self):
        self.kit = SpecKit.from_module(R6)

    def test_spec_center_and_distance(self):
        specs: list = []
        self.kit.box(specs, "t", "brass", "g", 10.0, 0.0, 0.0, 2.0, 2.0, 2.0)
        cx, cy, cz = spec_center(self.kit, specs[0])
        self.assertAlmostEqual(cx, 10.0)
        self.assertAlmostEqual(cy, 0.0)
        self.assertAlmostEqual(cz, 0.0)
        self.assertAlmostEqual(distance_to_point(self.kit, specs[0], (0.0, 0.0, 0.0)), 10.0)

    def test_distance_to_camera_uses_camera_location(self):
        specs: list = []
        self.kit.box(specs, "t", "brass", "g", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        camera = {"location": (3.0, 4.0, 0.0)}
        self.assertAlmostEqual(distance_to_camera(self.kit, specs[0], camera), 5.0)

    def test_is_onscreen_none_is_false(self):
        self.assertFalse(is_onscreen(None))

    def test_is_onscreen_true_for_frame_straddling_edge(self):
        frame = {"bounds": (-0.1, -0.1, 0.2, 0.2), "nearDepthM": 5.0, "farDepthM": 6.0}
        self.assertTrue(is_onscreen(frame))

    def test_is_onscreen_false_for_frame_fully_offscreen(self):
        frame = {"bounds": (1.5, 1.5, 2.0, 2.0), "nearDepthM": 5.0, "farDepthM": 6.0}
        self.assertFalse(is_onscreen(frame))

    def test_frame_cells_rasterises_within_bounds(self):
        cells = set(frame_cells((0.0, 0.0, 0.5, 0.5), 10, 10))
        self.assertIn((0, 0), cells)
        self.assertNotIn((9, 9), cells)
        # every cell must be inside the grid
        for ix, iy in cells:
            self.assertTrue(0 <= ix < 10)
            self.assertTrue(0 <= iy < 10)

    def test_frame_cells_empty_when_fully_offscreen(self):
        self.assertEqual(tuple(frame_cells((1.2, 1.2, 1.5, 1.5), 10, 10)), ())


if __name__ == "__main__":
    unittest.main()
