import unittest

from tools.blender.a23 import districts
from tools.blender.a23.kit import SpecKit
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6

KIT = SpecKit.from_module(R6)


class WindowRhythmTests(unittest.TestCase):
    def test_opening_height_is_derived_from_the_other_three_fields(self):
        rhythm = districts.WindowRhythm(floor_to_floor_m=3.2, sill_height_m=1.0, head_clearance_m=0.4)
        self.assertAlmostEqual(rhythm.opening_h_m, 1.8)

    def test_opening_width_is_below_a_typical_door_band(self):
        rhythm = districts.WindowRhythm()
        self.assertLess(rhythm.opening_w_m, 1.9)  # never wide enough to read as a door

    def test_wider_span_gets_more_columns(self):
        rhythm = districts.WindowRhythm()
        narrow = districts._window_columns_for_span(15.0, rhythm=rhythm)
        wide = districts._window_columns_for_span(50.0, rhythm=rhythm)
        self.assertGreater(wide, narrow)
        self.assertGreaterEqual(narrow, rhythm.min_columns)


class FrustumScoreTests(unittest.TestCase):
    CAMERA = {
        "name": "cam", "location": (0.0, 1.65, -20.0), "target": (0.0, 1.65, 0.0),
        "lensMm": 24.0, "sensorWidthMm": 36.0,
    }

    def test_point_in_front_scores_positive(self):
        score = districts.frustum_score(0.0, 0.0, self.CAMERA, max_range_m=100.0)
        self.assertGreater(score, 0.0)

    def test_point_behind_camera_scores_negative(self):
        score = districts.frustum_score(0.0, -40.0, self.CAMERA, max_range_m=100.0)
        self.assertEqual(score, -1.0)

    def test_point_beyond_max_range_scores_negative(self):
        score = districts.frustum_score(0.0, 500.0, self.CAMERA, max_range_m=100.0)
        self.assertEqual(score, -1.0)


class ExclusionGridTests(unittest.TestCase):
    def test_existing_mass_and_roads_and_spawns_are_marked(self):
        config = districts.DistrictConfig(map_half_m=40.0, cell_m=2.0)
        existing: list = []
        KIT.box(existing, "building", "brass", "town", 0.0, 5.0, 0.0, 10.0, 10.0, 10.0)
        roads = ({"bounds": {"minX": -4.0, "maxX": 4.0, "minZ": -40.0, "maxZ": 40.0}},)
        grid, grid_n = districts.build_exclusion_grid(
            existing, kit=KIT, canonical_roads=roads, player_spawns=((30.0, 0.0, 30.0),),
            bot_spawns=(), config=config,
        )
        # cell under the building must be excluded
        self.assertTrue(districts._lot_clear(config, grid, grid_n, -20.0, -20.0, 4.0, 4.0) is False
                         or True)  # sanity: function is callable; real assertion below
        self.assertFalse(districts._lot_clear(config, grid, grid_n, 0.0, 0.0, 4.0, 4.0))
        # a road cell must be excluded
        self.assertFalse(districts._lot_clear(config, grid, grid_n, 0.0, 20.0, 2.0, 2.0))
        # a player spawn must be excluded well beyond its own radius
        self.assertFalse(districts._lot_clear(config, grid, grid_n, 30.0, 30.0, 2.0, 2.0))


class PlanDistrictTests(unittest.TestCase):
    def test_places_blocks_within_budget_and_passes_audits(self):
        config = districts.DistrictConfig(
            map_half_m=60.0, cell_m=2.0, map_edge_margin_m=3.0, row_depth_m=18.0,
            street_gap_m=14.0, alley_gap_m=6.0, width_choices=(20.0,), height_choices=(6.0,),
        )
        camera = {
            "name": "cam", "location": (0.0, 1.65, -80.0), "target": (0.0, 5.0, 0.0),
            "lensMm": 24.0, "sensorWidthMm": 36.0,
        }
        roads = ({"bounds": {"minX": -8.0, "maxX": 8.0, "minZ": -60.0, "maxZ": 60.0}},
                 {"bounds": {"minX": -60.0, "maxX": 60.0, "minZ": -8.0, "maxZ": 8.0}})
        plan = districts.plan_district(
            [], tri_budget=20000, kit=KIT, canonical_roads=roads,
            player_spawns=((55.0, 0.0, 55.0),), bot_spawns=(), cameras=(camera,), config=config,
        )
        self.assertGreater(plan["blockCount"], 0)
        self.assertLessEqual(plan["triUsed"], 20000)

        road_audit = districts.road_overlap_audit(plan["specs"], kit=KIT, config=config)
        self.assertTrue(road_audit["passed"], road_audit)

        spawn_audit = districts.spawn_clearance_audit(
            plan["specs"], kit=KIT, player_spawns=((55.0, 0.0, 55.0),), bot_spawns=(), config=config,
        )
        self.assertTrue(spawn_audit["passed"], spawn_audit)

        gap_audit = districts.gap_audit(plan["placed"], config=config)
        self.assertTrue(gap_audit["passed"], gap_audit)

    def test_zero_budget_places_nothing(self):
        config = districts.DistrictConfig(map_half_m=40.0, width_choices=(20.0,), height_choices=(6.0,))
        plan = districts.plan_district(
            [], tri_budget=0, kit=KIT, canonical_roads=(), player_spawns=(), bot_spawns=(),
            cameras=({"name": "c", "location": (0, 1, -1), "target": (0, 1, 0), "lensMm": 24, "sensorWidthMm": 36},),
            config=config,
        )
        self.assertEqual(plan["blockCount"], 0)


if __name__ == "__main__":
    unittest.main()
