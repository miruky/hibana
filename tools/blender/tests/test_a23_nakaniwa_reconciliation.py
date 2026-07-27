"""Tests for tools/blender/stage_kits/nakaniwa_a23_reconciliation.py -- the
Phase 4a port of the A23 round's private nakaniwa-specific fix chain
(H3 near-field garden, H4 true near-field frame, H26 hero-defect fixes, and
the Tier 1 palace-occlusion fix) into the repository, plus the composer
(``build_nakaniwa_a23_specs``) that reproduces
``build_all_stages.py``'s production nakaniwa LOD0 build.

These are fast, deterministic, pure-Python checks (no bpy, no
``/private/tmp``). The one-time proof that this module reproduces
``claude-a23-tier1``'s build spec-for-spec (0 mismatches across 5,373 specs)
and pixel-for-pixel (0.0% changed pixels, all five proof cameras) against
the private study lives in the Phase 4a reconciliation report, not here --
that comparison depends on private-study modules under
``/private/tmp/hibana-blender`` that will not exist in every environment
this test suite runs in.
"""
import unittest

from tools.blender.stage_kits import nakaniwa_a23_reconciliation as REC
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6


class ReclamationPolicyTests(unittest.TestCase):
    def test_hero_groups_are_the_two_landmark_ids(self):
        self.assertEqual(REC.HERO_GROUPS, frozenset({R6.PALACE_ID, R6.CONSERVATORY_ID}))

    def test_policy_group_sets_are_disjoint(self):
        self.assertEqual(REC.HERO_GROUPS & REC.PROTECTED_GROUPS, frozenset())
        self.assertEqual(REC.HERO_GROUPS & REC.SAFE_BACKGROUND_GROUPS, frozenset())
        self.assertEqual(REC.PROTECTED_GROUPS & REC.SAFE_BACKGROUND_GROUPS, frozenset())

    def test_vegetation_thin_roles_have_modulus_at_least_two(self):
        self.assertTrue(REC.VEGETATION_THIN_ROLES)
        for role, modulus in REC.VEGETATION_THIN_ROLES.items():
            self.assertGreaterEqual(modulus, 2, role)


class FiveCameraContractTests(unittest.TestCase):
    def test_five_cameras_present(self):
        self.assertEqual(len(REC.FIVE_CAMERAS), 5)

    def test_dual_hero_uses_the_y14_iteration21_target_not_the_kit_default(self):
        # R6.MAIN_REFERENCE_CAMERA targets y=30; the round's actual proof
        # camera (and the tier1 comparison target) targets y=14.
        self.assertNotEqual(
            REC.DUAL_HERO_CAMERA["target"], R6.MAIN_REFERENCE_CAMERA["target"],
        )
        self.assertEqual(REC.DUAL_HERO_CAMERA["target"], (-5.0, 14.0, -4.0))
        self.assertEqual(REC.DUAL_HERO_CAMERA["location"], R6.MAIN_REFERENCE_CAMERA["location"])

    def test_camera_names_match_r6_proof_cameras_where_shared(self):
        r6_names = {str(cam["name"]) for cam in R6.PROOF_CAMERAS}
        for camera in REC.FIVE_CAMERAS:
            if camera is REC.DUAL_HERO_CAMERA:
                continue  # deliberately a distinct, Y14-targeted variant name.
            self.assertIn(camera["name"], r6_names)


class H3H4GeometryTests(unittest.TestCase):
    def test_a23_h3_specs_are_all_tagged_with_the_h3_group(self):
        specs = REC.a23_h3_specs(0)
        self.assertTrue(specs)
        self.assertTrue(all(s["group"] == REC.H3_GROUP for s in specs))

    def test_a23_h4_specs_stay_clear_of_the_canonical_roads(self):
        specs = REC.a23_h4_specs(0)
        self.assertTrue(specs)
        for spec in specs:
            bounds = R6.spec_bounds(spec)
            if bounds[4] < 0.35:
                continue  # flush-to-ground paving/inlay never blocks a route.
            for road in R6.CANONICAL_ROADS:
                rb = road["bounds"]
                overlaps = (
                    bounds[0] < rb["maxX"] and bounds[3] > rb["minX"]
                    and bounds[2] < rb["maxZ"] and bounds[5] > rb["minZ"]
                )
                self.assertFalse(overlaps, f"{spec['role']} intrudes on {road['id']}")

    def test_a23_h4_specs_never_enclose_the_dual_hero_camera(self):
        specs = REC.a23_h4_specs(0)
        cam = R6.MAIN_REFERENCE_CAMERA["location"]
        for spec in specs:
            b = R6.spec_bounds(spec)
            hit = b[0] <= cam[0] <= b[3] and b[1] <= cam[1] <= b[4] and b[2] <= cam[2] <= b[5]
            self.assertFalse(hit, f"{spec['role']} encloses the camera")

    def test_pergola_produces_matched_post_rows_per_bay(self):
        specs: list = []
        REC._pergola(specs, 1.0, 1, bay_t=0.05, start_t=-0.4, end_t=-0.2, vine_every=100)
        posts = [s for s in specs if s["role"] == "a23-h3-pergola-post"]
        # Two post rows (inner/outer) per bay.
        self.assertEqual(len(posts) % 2, 0)
        self.assertGreater(len(posts), 0)


class HeroDefectFixTests(unittest.TestCase):
    def test_apply_all_hero_fixes_on_the_real_composition_passes_hard_gates(self):
        base = R6.build_specs(0) + REC.a23_h4_specs(0)
        fixed, report = REC.apply_all_hero_fixes(base)
        self.assertTrue(report["orphanEmissiveAssertion"]["passed"])
        self.assertTrue(report["unsupportedWingWindowAssertion"]["passed"])
        self.assertGreater(len(fixed), 0)

    def test_arcade_glazing_rebuild_replaces_oversized_panes_with_capped_grid(self):
        base = R6.build_specs(0)
        fixed, report = REC.rebuild_arcade_glazing_bays(base)
        rebuild = report["fix"]
        self.assertEqual(rebuild, "arcade-oversized-glazing-card-rebuild")
        self.assertGreater(report["baysRebuilt"], 0)
        remaining_oversized_panes = [
            s for s in fixed
            if s["role"] == REC._ARCADE_OPENING_ROLE and s["kind"] == "box"
        ]
        self.assertEqual(remaining_oversized_panes, [])

    def test_recover_dual_hero_composition_shrinks_urns_below_eye_height(self):
        base = R6.build_specs(0) + REC.a23_h4_specs(0)
        fixed, report = REC.recover_dual_hero_composition(base)
        for height in report["urnHeightAfterM"].values():
            self.assertLess(height, 1.65)


class TierOnePalaceFixTests(unittest.TestCase):
    def test_clear_palace_moves_only_the_documented_populations(self):
        base = R6.build_specs(0) + REC.a23_h4_specs(0)
        fixed, report = REC.clear_palace(base)
        moved = report["specsMoved"]
        self.assertEqual(set(moved), {"pergola", "tree", "cornerTree", "lantern"})
        self.assertGreater(moved["pergola"], 0)
        self.assertGreater(moved["tree"], 0)
        self.assertGreater(moved["cornerTree"], 0)
        self.assertGreater(moved["lantern"], 0)
        self.assertEqual(report["totalSpecsMoved"], sum(moved.values()))

    def test_clear_palace_leaves_non_offending_specs_untouched(self):
        base = R6.build_specs(0) + REC.a23_h4_specs(0)
        fixed, _report = REC.clear_palace(base)
        # Palace/conservatory hero geometry itself is never a match target.
        untouched_hero = [s for s in fixed if s["group"] in (R6.PALACE_ID, R6.CONSERVATORY_ID)]
        original_hero = [s for s in base if s["group"] in (R6.PALACE_ID, R6.CONSERVATORY_ID)]
        self.assertEqual(untouched_hero, original_hero)


class ComposerTests(unittest.TestCase):
    """Regression pins against the round's own proven, measured build. If any
    of these numbers change, the production render will also change --
    re-verify against claude-a23-tier1/views/*.png before updating them.
    """

    @classmethod
    def setUpClass(cls):
        cls.specs, cls.info = REC.build_nakaniwa_a23_specs(0)

    def test_triangle_budget(self):
        # info["estimatedTotal"] is the coarse per-spec Python formula
        # (kit.estimated_triangles), not the real Blender-evaluated mesh
        # count -- the round's own reports keep these two numbers distinct
        # throughout (e.g. round-state's "pass4FixedEstimated" vs. a real
        # render's "candidateEvaluated"). The *real* Blender-evaluated count
        # for this exact composition is 258,258 -- verified in
        # claude-a23-phase4a/production-render-fidelity-report.json,
        # matching claude-a23-tier1's own real evaluated count exactly.
        cap = R6.LOD_BUDGETS[0]["maxEvaluatedTriangles"]
        self.assertLessEqual(self.info["estimatedTotal"], cap)
        self.assertEqual(self.info["estimatedTotal"], 259282)

    def test_spec_count_matches_the_proven_build(self):
        self.assertEqual(len(self.specs), 5373)

    def test_palace_fix_was_applied(self):
        self.assertEqual(self.info["palaceFix"]["fix"], "a23-tier1-clear-palace")
        self.assertGreater(self.info["palaceFix"]["totalSpecsMoved"], 0)

    def test_district_infill_placed_real_blocks(self):
        self.assertGreater(self.info["districtPlan"]["blockCount"], 0)

    def test_hero_groups_still_present_after_full_composition(self):
        groups = {s["group"] for s in self.specs}
        self.assertIn(R6.PALACE_ID, groups)
        self.assertIn(R6.CONSERVATORY_ID, groups)

    def test_composition_is_deterministic(self):
        specs2, info2 = REC.build_nakaniwa_a23_specs(0)
        self.assertEqual(self.specs, specs2)
        self.assertEqual(self.info["estimatedTotal"], info2["estimatedTotal"])


class DistrictSeedEquivalenceTests(unittest.TestCase):
    """The module docstring documents that an empty ``district_seed`` was
    proven (2026-07-27, against the private study) to produce a
    byte-identical composed spec list to the private study's real 80-spec
    best-effort seed for this build's actual inputs. This test pins the
    *reason* that holds in general: pass 3's unified test only ever *keeps*
    a background spec that fails to hide behind whatever occluder
    population it is given, so a smaller (or empty) occluder population can
    only keep MORE, never drop something an eventual larger population
    would also have kept hidden.
    """

    def test_empty_district_seed_never_drops_more_than_a_populated_one(self):
        from tools.blender.a23 import reclamation

        base_kit = R6.build_specs(0)
        near_field = REC.a23_h4_specs(0)
        config = reclamation.ReclamationConfig()
        common_kwargs = dict(
            kit=REC.KIT, cameras=REC.FIVE_CAMERAS,
            safe_background_groups=REC.SAFE_BACKGROUND_GROUPS,
            vegetation_thin_roles=REC.VEGETATION_THIN_ROLES,
            thin_accent_drop_roles=REC.THIN_ACCENT_DROP_ROLES,
            config=config,
        )
        empty_seed_kept = reclamation.pass3_five_camera_correctness_filter(
            base_kit, near_field, [], **common_kwargs,
        )
        # A synthetic extra occluder far from everything else can only ever
        # hide MORE background geometry than an empty seed, never less.
        populated_kept = reclamation.pass3_five_camera_correctness_filter(
            base_kit, near_field, near_field, **common_kwargs,
        )
        self.assertGreaterEqual(len(empty_seed_kept), len(populated_kept))


if __name__ == "__main__":
    unittest.main()
