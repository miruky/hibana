import unittest

from tools.blender.a23 import reclamation
from tools.blender.a23.kit import SpecKit
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6

KIT = SpecKit.from_module(R6)

CAMERA_A = {
    "name": "CamA", "location": (0.0, 1.65, -20.0), "target": (0.0, 1.65, 0.0),
    "lensMm": 35.0, "sensorWidthMm": 36.0,
}
CAMERA_B = {
    "name": "CamB", "location": (200.0, 1.65, -20.0), "target": (200.0, 1.65, 0.0),
    "lensMm": 35.0, "sensorWidthMm": 36.0,
}

SAFE = frozenset({"safe-bg"})
HERO = frozenset({"hero"})
PROTECTED = frozenset({"protected"})


class Pass1Tests(unittest.TestCase):
    def test_hero_and_protected_groups_are_never_dropped(self):
        specs: list = []
        KIT.box(specs, "hero-thing", "brass", "hero", 0.0, 1.0, -19.99, 0.0001, 0.0001, 0.0001)
        KIT.box(specs, "protected-thing", "brass", "protected", 500.0, 1.0, 500.0, 0.001, 0.001, 0.001)
        kept = reclamation.pass1_strict_invisible_filter(
            specs, kit=KIT, camera=CAMERA_A, hero_groups=HERO, protected_groups=PROTECTED,
            safe_background_groups=SAFE, vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        self.assertEqual(len(kept), 2)

    def test_offscreen_safe_background_spec_is_dropped(self):
        specs: list = []
        KIT.box(specs, "offscreen", "brass", "safe-bg", 5000.0, 1.0, -20.0, 1.0, 1.0, 1.0)
        kept = reclamation.pass1_strict_invisible_filter(
            specs, kit=KIT, camera=CAMERA_A, hero_groups=HERO, protected_groups=PROTECTED,
            safe_background_groups=SAFE, vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        self.assertEqual(kept, [])

    def test_large_onscreen_safe_background_spec_is_kept(self):
        specs: list = []
        KIT.box(specs, "onscreen", "brass", "safe-bg", 0.0, 1.65, -15.0, 3.0, 3.0, 3.0)
        kept = reclamation.pass1_strict_invisible_filter(
            specs, kit=KIT, camera=CAMERA_A, hero_groups=HERO, protected_groups=PROTECTED,
            safe_background_groups=SAFE, vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        self.assertEqual(len(kept), 1)

    def test_thin_accent_drop_role_is_dropped_unconditionally(self):
        specs: list = []
        KIT.box(specs, "mullion", "brass", "safe-bg", 0.0, 1.65, -15.0, 3.0, 3.0, 3.0)
        kept = reclamation.pass1_strict_invisible_filter(
            specs, kit=KIT, camera=CAMERA_A, hero_groups=HERO, protected_groups=PROTECTED,
            safe_background_groups=SAFE, vegetation_thin_roles={},
            thin_accent_drop_roles=frozenset({"mullion"}),
        )
        self.assertEqual(kept, [])

    def test_vegetation_thin_keeps_every_nth_occurrence(self):
        specs: list = []
        for _ in range(6):
            KIT.leaf_cluster(specs, "tree", "foliage_dark", "safe-bg", 0.0, 1.65, -15.0, 1.0, 1.0, 4, 1)
        kept = reclamation.pass1_strict_invisible_filter(
            specs, kit=KIT, camera=CAMERA_A, hero_groups=HERO, protected_groups=PROTECTED,
            safe_background_groups=SAFE, vegetation_thin_roles={"tree": 2}, thin_accent_drop_roles=frozenset(),
        )
        self.assertEqual(len(kept), 3)


class Pass3Tests(unittest.TestCase):
    def test_hidden_requires_every_camera_to_agree(self):
        specs: list = []
        # onscreen and unoccluded from CAMERA_A, but far outside CAMERA_B's frame.
        KIT.box(specs, "spec", "brass", "safe-bg", 0.0, 1.65, -15.0, 2.0, 2.0, 2.0)
        kept = reclamation.pass3_five_camera_correctness_filter(
            specs, [], [], kit=KIT, cameras=(CAMERA_A, CAMERA_B),
            safe_background_groups=SAFE, vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        # Visible (unoccluded, onscreen) in CAMERA_A -> must NOT be hidden in
        # every camera -> kept, even though CAMERA_B cannot see it at all.
        self.assertEqual(len(kept), 1)

    def test_camera_proximity_margin_always_keeps_nearby_spec(self):
        specs: list = []
        near_camera_a = dict(CAMERA_A)
        KIT.box(specs, "near", "brass", "safe-bg", 0.0, 1.65, -19.9, 0.01, 0.01, 0.01)
        kept = reclamation.pass3_five_camera_correctness_filter(
            specs, [], [], kit=KIT, cameras=(near_camera_a,),
            safe_background_groups=SAFE, vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        self.assertEqual(len(kept), 1)

    def test_pass_through_outside_safe_background_groups(self):
        specs: list = []
        KIT.box(specs, "elsewhere", "brass", "hero", 9999.0, 1.65, 9999.0, 1.0, 1.0, 1.0)
        kept = reclamation.pass3_five_camera_correctness_filter(
            specs, [], [], kit=KIT, cameras=(CAMERA_A,),
            safe_background_groups=SAFE, vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        self.assertEqual(kept, specs)


class Pass4SimplifyTests(unittest.TestCase):
    def test_chamfer_box_downgraded_when_bevel_is_subpixel(self):
        specs: list = []
        KIT.chamfer_box(specs, "far-chamfer", "brass", "safe-bg", 0.0, 1.65, -300.0, 4.0, 4.0, 4.0, 0.05, 1)
        before_tri = KIT.estimated_triangles(specs)
        out = reclamation.simplify_specs(specs, kit=KIT, cameras=(CAMERA_A,), safe_background_groups=SAFE)
        self.assertEqual(out[0]["kind"], "box")
        self.assertLess(KIT.estimated_triangles(out), before_tri)

    def test_near_camera_spec_is_never_touched(self):
        specs: list = []
        KIT.chamfer_box(specs, "near-chamfer", "brass", "safe-bg", 0.0, 1.65, -19.9, 4.0, 4.0, 4.0, 0.05, 1)
        out = reclamation.simplify_specs(specs, kit=KIT, cameras=(CAMERA_A,), safe_background_groups=SAFE)
        self.assertEqual(out, specs)

    def test_run_chain_is_pass3_then_pass4(self):
        specs: list = []
        KIT.chamfer_box(specs, "far-chamfer", "brass", "safe-bg", 0.0, 1.65, -300.0, 4.0, 4.0, 4.0, 0.05, 1)
        chained = reclamation.run_chain(
            specs, [], [], kit=KIT, cameras=(CAMERA_A,), safe_background_groups=SAFE,
            vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
        )
        direct = reclamation.simplify_specs(
            reclamation.pass3_five_camera_correctness_filter(
                specs, [], [], kit=KIT, cameras=(CAMERA_A,), safe_background_groups=SAFE,
                vegetation_thin_roles={}, thin_accent_drop_roles=frozenset(),
            ),
            kit=KIT, cameras=(CAMERA_A,), safe_background_groups=SAFE,
        )
        self.assertEqual(chained, direct)


class OcclusionGridTests(unittest.TestCase):
    def test_build_occlusion_grid_ignores_leaf_clusters_and_deep_panels(self):
        occluders: list = []
        KIT.leaf_cluster(occluders, "leaf", "foliage_dark", "safe-bg", 0.0, 1.65, -10.0, 1.0, 1.0, 4, 1)
        grid = reclamation.build_occlusion_grid(KIT, CAMERA_A, occluders)
        self.assertEqual(grid, {})

    def test_build_occlusion_grid_trusts_compact_box(self):
        occluders: list = []
        KIT.box(occluders, "wall", "brass", "safe-bg", 0.0, 1.65, -10.0, 4.0, 4.0, 0.2)
        grid = reclamation.build_occlusion_grid(KIT, CAMERA_A, occluders)
        self.assertGreater(len(grid), 0)


if __name__ == "__main__":
    unittest.main()
