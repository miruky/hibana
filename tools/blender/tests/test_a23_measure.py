import unittest

from tools.blender.a23 import measure
from tools.blender.a23.kit import SpecKit
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6

try:
    import cv2  # noqa: F401
    import numpy as np
    HAVE_CV2 = True
except ImportError:
    HAVE_CV2 = False

KIT = SpecKit.from_module(R6)


class BuiltFootprintReportTests(unittest.TestCase):
    def test_a_single_built_block_is_measured_and_passes_a_generous_contract(self):
        specs: list = []
        # One 20x20m built block on a 40x40m map (map_half=20) -> exactly 25%
        # of the grid, comfortably inside a wide contract band.
        KIT.box(specs, "block", "carved_stone", "g", 0.0, 3.0, 0.0, 20.0, 6.0, 20.0)
        config = measure.FootprintConfig(map_half_m=20.0, cell_m=2.0, built_min_height_m=2.5)
        report = measure.built_footprint_report(
            specs, kit=KIT, canonical_roads=(), contract_band_pct=(20.0, 30.0), config=config,
        )
        self.assertAlmostEqual(report["measured"]["builtPct"], 25.0, delta=0.5)
        self.assertEqual(report["verdict"], "PASS")

    def test_short_specs_do_not_count_as_built(self):
        specs: list = []
        KIT.box(specs, "furniture", "carved_stone", "g", 0.0, 0.1, 0.0, 20.0, 0.2, 20.0)
        config = measure.FootprintConfig(map_half_m=20.0, cell_m=2.0, built_min_height_m=2.5)
        report = measure.built_footprint_report(specs, kit=KIT, canonical_roads=(), config=config)
        self.assertEqual(report["measured"]["builtPct"], 0.0)

    def test_water_material_is_classified_as_water_not_built(self):
        specs: list = []
        KIT.box(specs, "canal", "water", "g", 0.0, 0.0, 0.0, 10.0, 5.0, 10.0)
        config = measure.FootprintConfig(map_half_m=20.0, cell_m=2.0)
        report = measure.built_footprint_report(specs, kit=KIT, canonical_roads=(), config=config)
        self.assertGreater(report["measured"]["waterPct"], 0.0)
        self.assertEqual(report["measured"]["builtPct"], 0.0)

    def test_ground_role_tokens_are_excluded_even_if_tall(self):
        specs: list = []
        config = measure.FootprintConfig(map_half_m=20.0, cell_m=2.0, ground_role_tokens=("ground-plane",))
        KIT.box(specs, "ground-plane-slab", "carved_stone", "g", 0.0, 5.0, 0.0, 40.0, 10.0, 40.0)
        report = measure.built_footprint_report(specs, kit=KIT, canonical_roads=(), config=config)
        self.assertEqual(report["measured"]["builtPct"], 0.0)


class HeroFrameOccupancyTests(unittest.TestCase):
    CAMERA = {
        "name": "cam", "location": (0.0, 1.65, -30.0), "target": (0.0, 5.0, 0.0),
        "lensMm": 24.0, "sensorWidthMm": 36.0, "resolution": (1280, 720),
    }

    def test_unoccluded_hero_has_matching_raw_and_visible_width(self):
        specs: list = []
        KIT.box(specs, "hero-tower", "brass", "hero", 0.0, 5.0, 0.0, 10.0, 10.0, 10.0)
        report = measure.hero_frame_occupancy(specs, self.CAMERA, kit=KIT, group_id="hero")
        self.assertGreater(report["visible"]["widthPct"], 0.0)
        self.assertAlmostEqual(report["visible"]["widthPct"], report["raw"]["widthPct"], delta=2.0)
        self.assertEqual(report["occlusionRatio"], 0.0)

    def test_full_occluder_in_front_raises_occlusion_ratio(self):
        specs: list = []
        KIT.box(specs, "hero-tower", "brass", "hero", 0.0, 5.0, 0.0, 10.0, 10.0, 10.0)
        KIT.box(specs, "occluder-wall", "brass", "occluders", 0.0, 5.0, -20.0, 40.0, 20.0, 1.0)
        report = measure.hero_frame_occupancy(specs, self.CAMERA, kit=KIT, group_id="hero")
        self.assertGreater(report["occlusionRatio"], 0.9)
        self.assertGreater(report["raw"]["widthPct"], report["visible"]["widthPct"])

    def test_low_occluder_below_floor_height_does_not_count(self):
        specs: list = []
        KIT.box(specs, "hero-tower", "brass", "hero", 0.0, 5.0, 0.0, 10.0, 10.0, 10.0)
        config = measure.HeroOcclusionConfig(occluder_min_top_height_m=2.8)
        KIT.box(specs, "curb", "brass", "occluders", 0.0, 0.1, -20.0, 40.0, 0.2, 1.0)
        report = measure.hero_frame_occupancy(specs, self.CAMERA, kit=KIT, group_id="hero", config=config)
        self.assertEqual(report["occlusionRatio"], 0.0)


@unittest.skipUnless(HAVE_CV2, "opencv not installed")
class StrictFoliageTests(unittest.TestCase):
    def test_green_dominant_pixel_is_foliage(self):
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        bgr[0, 0] = (10, 200, 10)  # B, G, R -- strongly green
        mask = measure.foliage_mask_strict(bgr)
        self.assertTrue(bool(mask[0, 0]))

    def test_grey_pixel_is_not_foliage(self):
        bgr = np.full((1, 1, 3), 128, dtype=np.uint8)
        mask = measure.foliage_mask_strict(bgr)
        self.assertFalse(bool(mask[0, 0]))

    def test_shadowed_stone_does_not_trigger_loose_hsv_style_false_positive(self):
        # A desaturated dark grey-green (what a loose HSV-only test can
        # mistake for foliage in shadow); this must fail the strict
        # green-dominance requirement.
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        bgr[0, 0] = (40, 46, 42)  # only marginally green-tinted
        mask = measure.foliage_mask_strict(bgr)
        self.assertFalse(bool(mask[0, 0]))

    def test_sky_mask_flags_blue_dominant_pixel(self):
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        bgr[0, 0] = (220, 180, 140)  # blue dominant
        mask = measure.sky_mask(bgr)
        self.assertTrue(bool(mask[0, 0]))


if __name__ == "__main__":
    unittest.main()
