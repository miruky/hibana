import unittest

from tools.blender.a23 import materials
from tools.blender.a23.kit import SpecKit
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6

KIT = SpecKit.from_module(R6)


class ApplyMaterialOverridesTests(unittest.TestCase):
    def test_merges_without_mutating_input(self):
        base = {"stone": {"color": (1.0, 1.0, 1.0, 1.0), "roughness": (0.1, 0.2)}}
        result = materials.apply_material_overrides(base, {"stone": {"roughness": (0.5, 0.9)}})
        self.assertEqual(result["stone"]["roughness"], (0.5, 0.9))
        self.assertEqual(result["stone"]["color"], (1.0, 1.0, 1.0, 1.0))
        # input untouched
        self.assertEqual(base["stone"]["roughness"], (0.1, 0.2))

    def test_unknown_override_key_raises(self):
        with self.assertRaises(KeyError):
            materials.apply_material_overrides({"stone": {}}, {"missing": {}})

    def test_nakaniwa_presets_apply_cleanly_to_the_real_kit(self):
        merged = {
            **materials.NAKANIWA_MATERIAL_FAMILY_OVERRIDE,
            **materials.NAKANIWA_GROUND_MATERIAL_OVERRIDE,
            **materials.NAKANIWA_GLAZING_MATERIAL_OVERRIDE,
        }
        result = materials.apply_material_overrides(R6.MATERIALS, merged)
        self.assertEqual(result["moss_stone"]["noiseScale"], 3.4)
        self.assertEqual(result["dirty_glass"]["alpha"], 0.46)
        # every material the kit ships must still be present
        self.assertEqual(set(result.keys()), set(R6.MATERIALS.keys()))


class RemapGroundTests(unittest.TestCase):
    def test_only_matching_role_and_material_and_height_are_remapped(self):
        specs: list = []
        KIT.box(specs, "plaza-floor", "carved_stone", "g", 0.0, 0.05, 0.0, 4.0, 0.1, 4.0)  # matches
        KIT.box(specs, "plaza-wall", "carved_stone", "g", 0.0, 5.0, 0.0, 4.0, 10.0, 4.0)  # too tall
        KIT.box(specs, "other-floor", "brass", "g", 0.0, 0.05, 0.0, 4.0, 0.1, 4.0)  # wrong material
        KIT.box(specs, "unrelated-role", "carved_stone", "g", 0.0, 0.05, 0.0, 4.0, 0.1, 4.0)  # no fragment match

        remapped, changed = materials.remap_ground(
            specs, kit=KIT, source_materials=frozenset({"carved_stone"}),
            role_fragments=("plaza",), target_material="moss_stone", max_top_y=1.0,
        )
        materials_by_role = {s["role"]: s["material"] for s in remapped}
        self.assertEqual(materials_by_role["plaza-floor"], "moss_stone")
        self.assertEqual(materials_by_role["plaza-wall"], "carved_stone")
        self.assertEqual(materials_by_role["other-floor"], "brass")
        self.assertEqual(materials_by_role["unrelated-role"], "carved_stone")
        self.assertEqual(changed, {"plaza-floor": 1})

    def test_originals_are_not_mutated(self):
        specs: list = []
        KIT.box(specs, "plaza-floor", "carved_stone", "g", 0.0, 0.05, 0.0, 4.0, 0.1, 4.0)
        original = dict(specs[0])
        materials.remap_ground(
            specs, kit=KIT, source_materials=frozenset({"carved_stone"}),
            role_fragments=("plaza",), target_material="moss_stone", max_top_y=1.0,
        )
        self.assertEqual(specs[0], original)


class HeroInteriorTests(unittest.TestCase):
    def test_hero_interior_bounds_raises_without_a_match(self):
        with self.assertRaises(RuntimeError):
            materials.hero_interior_bounds([], kit=KIT, role_token="conservatory")

    def test_build_hero_interior_matches_h13_counts_and_role_naming(self):
        specs: list = []
        KIT.box(specs, "conservatory-shell", "dirty_glass", "conservatory-hero", 50.0, 0.0, 50.0, 40.0, 20.0, 40.0)
        bounds = materials.hero_interior_bounds(specs, kit=KIT, role_token="conservatory")
        interior: list = []
        counts = materials.build_hero_interior(
            interior, bounds, kit=KIT, group="a23-h13-conservatory-interior",
            role_prefix="a23-h13-conservatory", planting_role_prefix="a23-h13-conservatory-interior",
        )
        self.assertEqual(counts, {"mezzanine": 2, "support": 10, "planting": 20, "rail": 2})
        roles = {s["role"] for s in interior}
        self.assertIn("a23-h13-conservatory-mezzanine-0", roles)
        self.assertIn("a23-h13-conservatory-interior-planting-0", roles)
        self.assertIn("a23-h13-conservatory-interior-lamp-0", roles)

    def test_planting_material_alternates_dark_then_light(self):
        specs: list = []
        KIT.box(specs, "conservatory-shell", "dirty_glass", "conservatory-hero", 50.0, 0.0, 50.0, 40.0, 20.0, 40.0)
        bounds = materials.hero_interior_bounds(specs, kit=KIT, role_token="conservatory")
        interior: list = []
        materials.build_hero_interior(interior, bounds, kit=KIT, group="g", role_prefix="p")
        planting = [s for s in interior if s["kind"] == "leaf_cluster"]
        first_two_at_level0 = [s["material"] for s in planting if "-planting-0" in s["role"]][:2]
        self.assertEqual(first_two_at_level0[0], "foliage_dark")


class ThickenNearVolumetricsTests(unittest.TestCase):
    def test_near_cluster_is_thickened_and_gains_a_companion(self):
        specs: list = []
        KIT.leaf_cluster(specs, "tree-a", "foliage_light", "g", 0.0, 1.0, -5.0, 1.0, 1.0, 8, 1)
        out, info = materials.thicken_near_volumetrics(specs, kit=KIT, camera_point=(0.0, 1.0, 0.0), near_range_m=10.0)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["leaves"], 40)
        self.assertEqual(out[1]["role"], "tree-a-inner-layer")
        self.assertEqual(out[1]["material"], "foliage_dark")
        self.assertEqual(info["thickened"], 1)
        self.assertEqual(info["companionsAdded"], 1)

    def test_far_cluster_is_untouched(self):
        specs: list = []
        KIT.leaf_cluster(specs, "tree-b", "foliage_light", "g", 0.0, 1.0, -500.0, 1.0, 1.0, 8, 1)
        out, info = materials.thicken_near_volumetrics(specs, kit=KIT, camera_point=(0.0, 1.0, 0.0), near_range_m=10.0)
        self.assertEqual(out, specs)
        self.assertEqual(info["thickened"], 0)

    def test_non_leaf_cluster_specs_pass_through(self):
        specs: list = []
        KIT.box(specs, "wall", "brass", "g", 0.0, 1.0, -1.0, 1.0, 1.0, 1.0)
        out, info = materials.thicken_near_volumetrics(specs, kit=KIT, camera_point=(0.0, 1.0, 0.0))
        self.assertEqual(out, specs)


if __name__ == "__main__":
    unittest.main()
