import unittest

from tools.blender import a23_bridge as bridge
from tools.blender.a23 import districts
from tools.blender.stage_kits import nakaniwa_reference_a21_r6 as R6


CAMERA = {
    "name": "cam", "location": (0.0, 1.65, -40.0), "target": (0.0, 5.0, 0.0),
    "lensMm": 24.0, "sensorWidthMm": 36.0,
}


class SpecKitFidelityTests(unittest.TestCase):
    """The bridge reimplements R6's own pure primitive/measurement contract
    independently (see a23_bridge.py's module docstring on why it must not
    import the frozen nakaniwa kit module). These tests prove the
    reimplementation is behaviourally identical to R6's own functions for
    the same inputs, rather than merely "a plausible-looking copy".
    """

    def test_box_spec_matches_r6(self):
        mine, theirs = [], []
        bridge._box(mine, "r", "wall", "g", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        R6._box(theirs, "r", "wall", "g", 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        self.assertEqual(mine, theirs)

    def test_chamfer_box_matches_r6(self):
        mine, theirs = [], []
        bridge._chamfer_box(mine, "r", "wall", "g", 0.0, 0.0, 0.0, 2.0, 2.0, 2.0, 0.1, 1)
        R6._chamfer_box(theirs, "r", "wall", "g", 0.0, 0.0, 0.0, 2.0, 2.0, 2.0, 0.1, 1)
        self.assertEqual(mine, theirs)

    def test_panel_matches_r6(self):
        corners = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))
        mine, theirs = [], []
        bridge._panel(mine, "r", "glass", "g", corners, 0.05)
        R6._panel(theirs, "r", "glass", "g", corners, 0.05)
        self.assertEqual(mine, theirs)

    def test_cylinder_matches_r6(self):
        mine, theirs = [], []
        bridge._cylinder(mine, "r", "trim", "g", 0.0, 1.0, 0.0, 0.3, 2.0, 8)
        R6._cylinder(theirs, "r", "trim", "g", 0.0, 1.0, 0.0, 0.3, 2.0, 8)
        self.assertEqual(mine, theirs)

    def test_sweep_matches_r6(self):
        points = ((0, 1, 0), (5, 1, 0))
        mine, theirs = [], []
        bridge._sweep(mine, "r", "brass", "g", points, 0.04, 6)
        R6._sweep(theirs, "r", "brass", "g", points, 0.04, 6)
        self.assertEqual(mine, theirs)

    def test_spec_bounds_matches_r6_for_every_kind(self):
        specs = []
        bridge._box(specs, "b", "wall", "g", 1, 2, 3, 4, 5, 6)
        bridge._chamfer_box(specs, "cb", "wall", "g", 0, 0, 0, 2, 2, 2, 0.1, 1)
        bridge._cylinder(specs, "c", "trim", "g", 0, 1, 0, 0.3, 2.0, 8)
        bridge._panel(specs, "p", "glass", "g", ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), 0.05)
        bridge._sweep(specs, "s", "brass", "g", ((0, 1, 0), (5, 1, 0)), 0.04, 6)
        for spec in specs:
            self.assertEqual(bridge.spec_bounds(spec), R6.spec_bounds(spec))

    def test_estimated_triangles_matches_r6(self):
        specs = []
        bridge._box(specs, "b", "wall", "g", 1, 2, 3, 4, 5, 6)
        bridge._chamfer_box(specs, "cb", "wall", "g", 0, 0, 0, 2, 2, 2, 0.1, 1)
        bridge._cylinder(specs, "c", "trim", "g", 0, 1, 0, 0.3, 2.0, 8)
        bridge._sweep(specs, "s", "brass", "g", ((0, 1, 0), (5, 1, 0)), 0.04, 6)
        self.assertEqual(bridge.estimated_triangles(specs), R6.estimated_triangles(specs))

    def test_project_spec_frame_matches_r6(self):
        specs = []
        bridge._box(specs, "b", "wall", "g", 0.0, 1.5, 10.0, 4.0, 3.0, 4.0)
        mine = bridge.project_spec_frame(specs[0], CAMERA, 16.0 / 9.0)
        theirs = R6._project_spec_frame(specs[0], CAMERA, 16.0 / 9.0)
        self.assertIsNotNone(mine)
        self.assertEqual(mine["bounds"], theirs["bounds"])
        self.assertAlmostEqual(mine["nearDepthM"], theirs["nearDepthM"])
        self.assertAlmostEqual(mine["farDepthM"], theirs["farDepthM"])

    def test_generic_spec_kit_is_a_valid_speckit(self):
        specs: list = []
        bridge.GENERIC_SPEC_KIT.box(specs, "r", "wall", "g", 0, 1, 0, 2, 2, 2)
        self.assertEqual(bridge.GENERIC_SPEC_KIT.estimated_triangles(specs), 12)


class StageBoxesAsSpecsTests(unittest.TestCase):
    def test_skips_non_authoritative_flags(self):
        stage = {"boxes": [
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2, "ghost": True},
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2, "decor": True},
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2, "legacyHorizon": True},
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2, "prop": True},
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2, "breakable": True},
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2},
        ]}
        specs = bridge.stage_boxes_as_specs(stage)
        self.assertEqual(len(specs), 1)

    def test_landmark_and_district_groups(self):
        stage = {"boxes": [
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2, "landmarkId": "hero-0"},
            {"x": 0, "y": 0, "z": 0, "w": 2, "h": 0.5, "d": 2, "district": "town"},
            {"x": 0, "y": 1, "z": 0, "w": 2, "h": 2, "d": 2},
        ]}
        specs = bridge.stage_boxes_as_specs(stage)
        groups = {spec["role"]: spec["group"] for spec in specs}
        self.assertEqual(groups["layout-box-0"], "hero")
        self.assertEqual(groups["layout-box-1"], "district")
        self.assertEqual(groups["layout-box-2"], "layout")

    def test_short_district_marker_gets_assumed_built_height(self):
        stage = {"boxes": [{"x": 0, "y": 0, "z": 0, "w": 2, "h": 0.5, "d": 2, "district": "town"}]}
        specs = bridge.stage_boxes_as_specs(stage)
        self.assertGreaterEqual(specs[0]["h"], 2.5)  # measure.FootprintConfig.built_min_height_m


class RoadAndCameraDerivationTests(unittest.TestCase):
    def test_road_width_by_family(self):
        self.assertEqual(bridge.road_width_for_family("airport"), 12.0)
        self.assertEqual(bridge.road_width_for_family("industrial"), 8.0)
        self.assertEqual(bridge.road_width_for_family("heritage"), 6.5)

    def test_canonical_roads_are_a_centred_cross(self):
        stage = {"size": 300.0}
        roads = bridge.stage_canonical_roads(stage, "urban")
        ns, ew = roads
        self.assertEqual(ns["bounds"]["minZ"], -150.0)
        self.assertEqual(ew["bounds"]["minX"], -150.0)

    def test_proof_cameras_cover_every_spawn_plus_two_central_views(self):
        stage = {"size": 300.0, "playerSpawns": [[100, 0, 100], [-100, 0, 100], [100, 0, -100], [-100, 0, -100]]}
        cameras = bridge.stage_proof_cameras(stage)
        self.assertEqual(len(cameras), 6)
        names = {cam["name"] for cam in cameras}
        self.assertEqual(len(names), 6)  # no duplicate camera names


class LandmarkApproachCorridorTests(unittest.TestCase):
    """See a23_bridge.py's stage_landmark_approach_corridors docstring: the
    kairou landmark-0 in-game defect (district infill walled off the
    landmark's own approach corridor 0.3 m past its start point, because
    build_exclusion_grid had no concept of a landmark approach at all).
    """

    def test_no_landmarks_produces_no_corridors(self):
        self.assertEqual(bridge.stage_landmark_approach_corridors({"landmarkPlacements": []}), ())
        self.assertEqual(bridge.stage_landmark_approach_corridors({}), ())

    def test_z_running_approach_widens_in_x(self):
        # Reproduces kairou-meridian-hypostyle-sanctuary's own real approach.
        stage = {"landmarkPlacements": [{
            "id": "kairou-meridian-hypostyle-sanctuary",
            "approach": {"start": [-66.0, -13.8], "end": [-66.0, 8.2], "width": 12.0},
        }]}
        (corridor,) = bridge.stage_landmark_approach_corridors(stage)
        self.assertEqual(corridor["name"], "landmark-approach-kairou-meridian-hypostyle-sanctuary")
        bounds = corridor["bounds"]
        self.assertAlmostEqual(bounds["minX"], -72.0)
        self.assertAlmostEqual(bounds["maxX"], -60.0)
        self.assertAlmostEqual(bounds["minZ"], -13.8)
        self.assertAlmostEqual(bounds["maxZ"], 8.2)

    def test_x_running_approach_widens_in_z(self):
        # Reproduces kouwan-umiho-exchange-tower's own real approach.
        stage = {"landmarkPlacements": [{
            "id": "kouwan-umiho-exchange-tower",
            "approach": {"start": [139.8, -74.0], "end": [117.8, -74.0], "width": 12.0},
        }]}
        (corridor,) = bridge.stage_landmark_approach_corridors(stage)
        bounds = corridor["bounds"]
        self.assertAlmostEqual(bounds["minX"], 117.8)
        self.assertAlmostEqual(bounds["maxX"], 139.8)
        self.assertAlmostEqual(bounds["minZ"], -80.0)
        self.assertAlmostEqual(bounds["maxZ"], -68.0)

    def test_two_landmarks_produce_two_corridors(self):
        stage = {"landmarkPlacements": [
            {"id": "a", "approach": {"start": [-66.0, -13.8], "end": [-66.0, 8.2], "width": 12.0}},
            {"id": "b", "approach": {"start": [56.0, -16.8], "end": [56.0, 5.2], "width": 12.0}},
        ]}
        corridors = bridge.stage_landmark_approach_corridors(stage)
        self.assertEqual(len(corridors), 2)
        self.assertEqual({c["name"] for c in corridors}, {"landmark-approach-a", "landmark-approach-b"})


class DistrictConfigDerivationTests(unittest.TestCase):
    def test_infill_budget_shrinks_as_coverage_grows(self):
        sparse = bridge.infill_triangle_budget({"cityProfile": {"coverageRatio": 0.2}})
        dense = bridge.infill_triangle_budget({"cityProfile": {"coverageRatio": 0.9}})
        self.assertGreater(sparse, dense)
        self.assertLessEqual(dense, int(bridge.LOD0_TRIANGLE_CAP * 0.08))
        self.assertGreaterEqual(sparse, int(bridge.LOD0_TRIANGLE_CAP * 0.03))

    def test_gap_config_clears_contract_floor_after_cornice_overhang(self):
        stage = {"size": 300.0}
        profile = {"cityProfile": {"streetWidthM": [12.0, 20.0], "secondaryHeightM": [8.0, 16.0]}}
        config = bridge.derive_district_config(stage, profile, "military", "day")
        worst_case_alley = config.alley_gap_m - 2 * config.cornice_overhang_m
        worst_case_street = config.street_gap_m - 2 * config.cornice_overhang_m
        self.assertGreaterEqual(worst_case_alley, config.contract_alley_band_m[0])
        self.assertGreaterEqual(worst_case_street, config.contract_street_band_m[0])

    def test_map_half_m_matches_stage_size(self):
        stage = {"size": 280.0}
        profile = {"cityProfile": {"streetWidthM": [10.0, 16.0], "secondaryHeightM": [6.0, 12.0]}}
        config = bridge.derive_district_config(stage, profile, "urban", "night")
        self.assertEqual(config.map_half_m, 140.0)

    def test_night_mood_adds_emissive_window_material(self):
        stage = {"size": 280.0}
        profile = {"cityProfile": {"streetWidthM": [10.0, 16.0], "secondaryHeightM": [6.0, 12.0]}}
        night = bridge.derive_district_config(stage, profile, "urban", "night")
        day = bridge.derive_district_config(stage, profile, "urban", "day")
        self.assertIn("emissive", night.window_materials)
        self.assertNotIn("emissive", day.window_materials)


class PolicyTableTests(unittest.TestCase):
    def test_nakaniwa_defaults_disabled_others_enabled(self):
        bridge.configure_policy_table(["nakaniwa", "kunren", "souko"])
        self.assertFalse(bridge.stage_enabled("nakaniwa"))
        self.assertTrue(bridge.stage_enabled("kunren"))
        self.assertTrue(bridge.stage_enabled("souko"))
        self.assertTrue(bridge.STAGE_POLICY["nakaniwa"].reason)

    def test_override_can_disable_a_stage_with_a_reason(self):
        bridge.configure_policy_table(
            ["kunren", "souko"],
            {"souko": bridge.StageA23Policy(False, "regressed in the 31-stage dry run; excluded pending a fix")},
        )
        self.assertTrue(bridge.stage_enabled("kunren"))
        self.assertFalse(bridge.stage_enabled("souko"))
        self.assertIn("regressed", bridge.STAGE_POLICY["souko"].reason)

    def test_unknown_stage_is_not_enabled(self):
        bridge.configure_policy_table(["kunren"])
        self.assertFalse(bridge.stage_enabled("does-not-exist"))


class PlanDistrictInfillTests(unittest.TestCase):
    def test_end_to_end_plan_holds_budget_and_passes_audits(self):
        stage = {
            "id": "test-stage", "size": 300.0,
            "palette": {"mood": "day"},
            "playerSpawns": [[130.0, 0.0, 130.0], [-130.0, 0.0, -130.0]],
            "botSpawns": [[100.0, 0.0, 0.0]],
            "boxes": [
                {"x": 0, "y": 5, "z": 0, "w": 20, "h": 10, "d": 20, "landmarkId": "hero-0"},
            ],
        }
        profile = {"cityProfile": {"streetWidthM": [10.0, 18.0], "secondaryHeightM": [6.0, 12.0], "coverageRatio": 0.5}}
        report = bridge.plan_district_infill(stage, profile, "urban", "day")
        self.assertTrue(report["withinTriBudget"])
        self.assertTrue(report["auditsPassed"])
        self.assertLessEqual(report["estimatedTriangles"], report["triBudget"])
        self.assertEqual(
            bridge.GENERIC_SPEC_KIT.estimated_triangles(report["specs"]), report["estimatedTriangles"],
        )

    def test_no_room_produces_an_empty_but_valid_plan(self):
        # A tiny map fully covered by one huge landmark: no candidate sites,
        # not an error.
        stage = {
            "id": "tiny", "size": 40.0, "palette": {"mood": "day"},
            "playerSpawns": [[15.0, 0.0, 15.0]], "botSpawns": [],
            "boxes": [{"x": 0, "y": 5, "z": 0, "w": 60, "h": 10, "d": 60, "landmarkId": "hero-0"}],
        }
        profile = {"cityProfile": {"streetWidthM": [10.0, 18.0], "secondaryHeightM": [6.0, 12.0], "coverageRatio": 0.9}}
        report = bridge.plan_district_infill(stage, profile, "urban", "day")
        self.assertEqual(report["districtPlan"]["blockCount"], 0)
        self.assertEqual(report["estimatedTriangles"], 0)
        self.assertTrue(report["withinTriBudget"])

    def test_infill_never_occupies_a_landmark_approach_corridor(self):
        # Regression test for the kairou landmark-0 in-game defect: district
        # infill walled off the readable approach to a landmark because
        # build_exclusion_grid had no notion of landmarkPlacements at all.
        #
        # The map is otherwise empty (no boxes), so the scanline packer's own
        # deterministic first site -- row 0, index 0, using DistrictConfig's
        # default row_depth_m=18.0, map_edge_margin_m=3.0 and
        # width_choices[0]=30.0 -- lands at cx = -half + edge + w/2,
        # cz = -half + edge + row_depth/2. For a 300 m stage that is
        # (-132, -138). A landmark approach corridor is authored to sit
        # exactly on that footprint (kept far from the centred canonical-road
        # cross and the map edge so neither of those exclusions is what's
        # under test).
        half = 150.0
        site_cx, site_cz, site_w, site_d = -132.0, -138.0, 30.0, 18.0
        landmark_stage = {
            "id": "corridor-test", "size": 2 * half, "palette": {"mood": "day"},
            "playerSpawns": [[130.0, 0.0, 130.0]], "botSpawns": [],
            "boxes": [],
            "landmarkPlacements": [{
                "id": "test-landmark",
                "approach": {
                    "start": [site_cx, site_cz - site_d / 2.0],
                    "end": [site_cx, site_cz + site_d / 2.0],
                    "width": site_w,
                },
            }],
        }
        profile = {"cityProfile": {"streetWidthM": [10.0, 18.0], "secondaryHeightM": [6.0, 12.0], "coverageRatio": 0.3}}

        def overlaps_site(spec):
            b = bridge.spec_bounds(spec)
            return not (
                b[3] < site_cx - site_w / 2.0 or b[0] > site_cx + site_w / 2.0
                or b[5] < site_cz - site_d / 2.0 or b[2] > site_cz + site_d / 2.0
            )

        # Sanity check: without any landmark-approach awareness, this exact
        # site is exactly what districts.plan_district picks first -- proving
        # the scenario is real, not vacuous.
        roads_only = bridge.stage_canonical_roads(landmark_stage, "urban")
        config = bridge.derive_district_config(landmark_stage, profile, "urban", "day")
        unaware_plan = districts.plan_district(
            [], tri_budget=bridge.infill_triangle_budget(profile), kit=bridge.GENERIC_SPEC_KIT,
            canonical_roads=roads_only, player_spawns=landmark_stage["playerSpawns"],
            bot_spawns=[], cameras=bridge.stage_proof_cameras(landmark_stage), config=config,
            rhythm=bridge.WINDOW_RHYTHM,
        )
        self.assertTrue(any(overlaps_site(spec) for spec in unaware_plan["specs"]))

        # The real (landmark-approach-aware) entry point must never place
        # infill mass over the approach.
        report = bridge.plan_district_infill(landmark_stage, profile, "urban", "day")
        offending = [spec for spec in report["specs"] if overlaps_site(spec)]
        self.assertEqual(offending, [])


class EmitSpecsToMeshBuilderTests(unittest.TestCase):
    class _FakeBuilder:
        def __init__(self):
            self.calls = []

        def add_box(self, x, y, z, w, h, d, key):
            self.calls.append(("box", key))

        def add_surface_panel(self, corners, thickness, key):
            self.calls.append(("panel", key))

        def add_cylinder_between(self, start, end, radius, key, segments):
            self.calls.append(("sweep", key))

        def add_cylinder(self, x, y, z, radius, height, key, segments, top_radius):
            self.calls.append(("cylinder", key))

    def test_dispatches_every_kind_districts_actually_emits(self):
        specs = []
        bridge._box(specs, "b", "wall", "g", 0, 1, 0, 2, 2, 2)
        bridge._panel(specs, "p", "glass", "g", ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), 0.05)
        bridge._sweep(specs, "s", "brass", "g", ((0, 1, 0), (5, 1, 0)), 0.04, 6)
        builder = self._FakeBuilder()
        counts = bridge.emit_specs_to_mesh_builder(builder, specs)
        self.assertEqual([kind for kind, _ in builder.calls], ["box", "panel", "sweep"])
        self.assertEqual(counts["box"], 1)
        self.assertEqual(counts["panel"], 1)
        self.assertEqual(counts["sweep"], 1)

    def test_chamfer_box_downgrades_to_box(self):
        specs = []
        bridge._chamfer_box(specs, "cb", "wall", "g", 0, 0, 0, 2, 2, 2, 0.1, 1)
        builder = self._FakeBuilder()
        bridge.emit_specs_to_mesh_builder(builder, specs)
        self.assertEqual(builder.calls, [("box", "wall")])

    def test_multi_point_sweep_is_rejected(self):
        specs = []
        bridge._sweep(specs, "s", "brass", "g", ((0, 1, 0), (2, 1, 0), (5, 1, 0)), 0.04, 6)
        builder = self._FakeBuilder()
        with self.assertRaises(ValueError):
            bridge.emit_specs_to_mesh_builder(builder, specs)

    def test_leaf_cluster_is_rejected(self):
        specs = []
        bridge._leaf_cluster(specs, "l", "foliage_dark", "g", 0, 1, 0, 1.0, 2.0, 10, 1)
        builder = self._FakeBuilder()
        with self.assertRaises(ValueError):
            bridge.emit_specs_to_mesh_builder(builder, specs)


class DistrictsModuleStillWorksAgainstTheBridgeKit(unittest.TestCase):
    """Sanity check that districts.plan_district (imported, not reimplemented)
    genuinely accepts GENERIC_SPEC_KIT as a drop-in SpecKit -- this is the
    contract the a23 promotion's kit.py documents as the intended shape for
    a *second* kit module.
    """

    def test_plan_district_runs_against_the_bridge_kit(self):
        config = districts.DistrictConfig(
            map_half_m=60.0, cell_m=2.0, map_edge_margin_m=3.0, row_depth_m=18.0,
            street_gap_m=14.0, alley_gap_m=6.0, width_choices=(20.0,), height_choices=(6.0,),
        )
        plan = districts.plan_district(
            [], tri_budget=20000, kit=bridge.GENERIC_SPEC_KIT,
            canonical_roads=({"bounds": {"minX": -8.0, "maxX": 8.0, "minZ": -60.0, "maxZ": 60.0}},),
            player_spawns=((55.0, 0.0, 55.0),), bot_spawns=(), cameras=(CAMERA,), config=config,
        )
        self.assertGreater(plan["blockCount"], 0)


if __name__ == "__main__":
    unittest.main()
