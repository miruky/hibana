import copy
from pathlib import Path
import unittest

from tools.blender.stage_kits import nakaniwa_reference_a18 as R11
from tools.blender.stage_kits import nakaniwa_reference_a20 as NAKANIWA


class RecordingBuilder:
    def __init__(self):
        self.calls = []

    def add_box(self, *args):
        self.calls.append(("box", args))

    def add_beam(self, *args):
        self.calls.append(("beam", args))

    def add_cylinder(self, *args):
        self.calls.append(("cylinder", args))

    def add_sloped_panel(self, *args):
        self.calls.append(("panel", args))

    def add_ellipsoid(self, *args):
        self.calls.append(("ellipsoid", args))


def role_count(specs, role):
    return sum(spec["role"] == role for spec in specs)


def plan_intersects(bounds, min_x, max_x, min_z, max_z):
    return not (
        bounds[3] <= min_x
        or bounds[0] >= max_x
        or bounds[5] <= min_z
        or bounds[2] >= max_z
    )


class NakaniwaReferenceA20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lods = tuple(NAKANIWA.build_specs(lod) for lod in range(3))

    def test_canonical_contract_and_exact_two_landmarks_are_frozen(self):
        self.assertEqual(NAKANIWA.MAP_SIZE_M, 320.0)
        self.assertEqual(
            NAKANIWA.CANONICAL_BOUNDS,
            {"min_x": -160.0, "max_x": 160.0, "min_z": -160.0, "max_z": 160.0},
        )
        self.assertEqual(len(NAKANIWA.CANONICAL_ROADS), 2)
        self.assertEqual([road["width"] for road in NAKANIWA.CANONICAL_ROADS], [16.0, 16.0])
        self.assertEqual(len(NAKANIWA.CANONICAL_PLAYER_SPAWNS), 4)
        self.assertEqual(len(NAKANIWA.CANONICAL_BOT_SPAWNS), 32)
        self.assertEqual(
            [
                (
                    landmark["id"], landmark["cx"], landmark["cz"],
                    landmark["width"], landmark["depth"], landmark["height"],
                )
                for landmark in NAKANIWA.LANDMARKS
            ],
            [
                ("nakaniwa-suiren-crown-palace", -60.0, -67.8, 92.0, 78.0, 43.0),
                ("nakaniwa-kakou-conservatory-citadel", 52.0, 61.8, 76.0, 66.0, 50.0),
            ],
        )
        self.assertEqual(NAKANIWA.LANDMARKS[0]["entrance"], (-60.0, -28.0))
        self.assertEqual(NAKANIWA.LANDMARKS[1]["entrance"], (52.0, 28.0))

    @unittest.skipUnless(
        Path("/private/tmp/hibana-blender/canonical-stage-layouts.json").is_file(),
        "private canonical layout snapshot is unavailable",
    )
    def test_private_canonical_snapshot_matches_every_locked_value(self):
        report = NAKANIWA.canonical_contract_report(
            Path("/private/tmp/hibana-blender/canonical-stage-layouts.json")
        )
        self.assertTrue(report["allMatched"], report)
        self.assertEqual(report["exactLandmarkCount"], 2)

    def test_a20_derivation_does_not_mutate_the_r11_source_specs(self):
        before = copy.deepcopy(R11.build_specs(0))
        NAKANIWA.build_specs(0)
        after = R11.build_specs(0)
        self.assertEqual(after, before)

    def test_both_r11_hero_groups_are_completely_rebuilt(self):
        for lod, specs in enumerate(self.lods):
            hero_specs = [
                spec for spec in specs
                if spec["group"] in {NAKANIWA.PALACE_ID, NAKANIWA.CONSERVATORY_ID}
            ]
            self.assertTrue(hero_specs, f"LOD{lod}")
            self.assertTrue(
                all(spec["role"].startswith("a20-") for spec in hero_specs),
                f"LOD{lod} retained an r11 hero part",
            )
            self.assertFalse(any(spec["material"] == "warm_window" for spec in R11.build_specs(lod)
                                 if spec in hero_specs))

    def test_palace_is_layered_occupied_supported_and_crowned(self):
        specs = self.lods[0]
        self.assertEqual(role_count(specs, "a20-palace-occupied-lower-mass"), 3)
        self.assertEqual(role_count(specs, "a20-palace-occupied-keep"), 1)
        self.assertEqual(role_count(specs, "a20-palace-occupied-side-tower"), 2)
        self.assertGreaterEqual(role_count(specs, "a20-palace-grand-arcade-arch-rib"), 120)
        self.assertGreaterEqual(role_count(specs, "a20-palace-upper-loggia-arch-rib"), 60)
        self.assertEqual(role_count(specs, "a20-palace-supported-column"), 12)
        self.assertEqual(role_count(specs, "a20-palace-supported-terrace"), 1)
        self.assertGreaterEqual(role_count(specs, "a20-palace-tiered-roof-slope"), 12)
        self.assertEqual(role_count(specs, "a20-palace-crown-petal-glass"), 9)
        self.assertEqual(role_count(specs, "a20-palace-crown-petal-frame"), 36)
        self.assertEqual(role_count(specs, "a20-palace-crown-petal-spine"), 9)
        self.assertEqual(role_count(specs, "a20-palace-crown-inner-lantern"), 1)
        self.assertGreaterEqual(role_count(specs, "a20-palace-crown-inner-mullion"), 8)
        self.assertGreaterEqual(role_count(specs, "a20-palace-crown-petal-lattice"), 18)
        self.assertEqual(role_count(specs, "a20-palace-lower-crown-petal"), 8)
        self.assertEqual(role_count(specs, "a20-palace-lower-crown-frame"), 32)
        self.assertEqual(role_count(specs, "a20-palace-lower-crown-glass-inset"), 8)
        self.assertEqual(role_count(specs, "a20-palace-crown-gate-buttress"), 4)
        self.assertEqual(role_count(specs, "a20-palace-crown-companion-spire"), 4)
        self.assertGreaterEqual(role_count(specs, "a20-palace-arcade-deep-opening"), 12)
        self.assertEqual(role_count(specs, "a20-palace-side-lantern-pavilion"), 2)
        self.assertEqual(role_count(specs, "a20-palace-projecting-gate-tier"), 2)
        self.assertGreaterEqual(role_count(specs, "a20-palace-projecting-loggia-arch-rib"), 50)
        self.assertEqual(role_count(specs, "a20-palace-side-belvedere"), 2)
        self.assertEqual(role_count(specs, "a20-palace-master-spire"), 1)
        self.assertEqual(role_count(specs, "a20-palace-entry-stair"), 7)
        self.assertEqual(role_count(specs, "a20-palace-water-court"), 2)
        self.assertGreaterEqual(role_count(specs, "a20-palace-deep-window-recess"), 15)
        self.assertGreaterEqual(role_count(specs, "a20-palace-window-stone-frame"), 45)

    def test_conservatory_has_exactly_five_grounded_fan_vaults(self):
        specs = self.lods[0]
        buttresses = [
            spec for spec in specs
            if spec["role"] == "a20-conservatory-vault-buttress"
        ]
        spring_xs = sorted({round(spec["x"], 3) for spec in buttresses})
        # Each of the five compound shells has a distinct left/right spring.
        self.assertEqual(len(spring_xs), 10, spring_xs)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-fan-vault-rib"), 360)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-vault-purlin"), 55)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-glass-cell"), 300)
        for buttress in buttresses:
            bounds = NAKANIWA.spec_bounds(buttress)
            self.assertLessEqual(bounds[1], 0.0 + 1e-6)

    def test_conservatory_is_deep_planted_and_traversable(self):
        specs = self.lods[0]
        self.assertEqual(role_count(specs, "a20-conservatory-upper-walk"), 2)
        self.assertEqual(role_count(specs, "a20-conservatory-rear-crosswalk"), 1)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-walk-support"), 10)
        self.assertEqual(role_count(specs, "a20-conservatory-interior-stair"), 30)
        self.assertEqual(role_count(specs, "a20-conservatory-central-promenade"), 1)
        self.assertEqual(role_count(specs, "a20-conservatory-botanical-destination"), 1)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-botanical-planter"), 16)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-dense-planting"), 48)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-specimen-trunk"), 8)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-specimen-canopy"), 32)
        self.assertGreaterEqual(
            role_count(specs, "a20-conservatory-specimen-broadleaf-canopy"), 40
        )
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-broadleaf-cluster"), 48)
        self.assertEqual(role_count(specs, "a20-conservatory-deep-soil-bed"), 2)
        self.assertEqual(role_count(specs, "a20-conservatory-hanging-chain"), 8)
        self.assertEqual(role_count(specs, "a20-conservatory-hanging-pot"), 8)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-hanging-foliage"), 24)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-flowering-understory"), 28)
        self.assertEqual(role_count(specs, "a20-conservatory-interior-water"), 2)
        self.assertEqual(role_count(specs, "a20-conservatory-promenade-water-inlay"), 1)
        self.assertEqual(role_count(specs, "a20-conservatory-promenade-stepping-stone"), 10)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-destination-arcade-arch-rib"), 30)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-potting-bench"), 4)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-irrigation-valve"), 4)
        self.assertGreaterEqual(role_count(specs, "a20-conservatory-climbing-vine"), 8)
        self.assertGreaterEqual(
            role_count(specs, "a20-conservatory-climbing-vine-leaf"), 48
        )
        self.assertGreaterEqual(
            role_count(specs, "a20-conservatory-monumental-fan-spoke"), 9
        )

        portal_piers = sorted(
            (spec for spec in specs if spec["role"] == "a20-conservatory-portal-pier"),
            key=lambda spec: spec["x"],
        )
        self.assertEqual(len(portal_piers), 2)
        opening = (
            portal_piers[1]["x"] - portal_piers[1]["radius"]
            - portal_piers[0]["x"] - portal_piers[0]["radius"]
        )
        self.assertGreaterEqual(opening, 7.8)
        promenade = next(
            spec for spec in specs
            if spec["role"] == "a20-conservatory-central-promenade"
        )
        self.assertGreaterEqual(promenade["w"], 7.5)
        self.assertGreaterEqual(promenade["d"], 64.0)
        foundations = [
            spec for spec in specs
            if spec["role"] == "a20-conservatory-perimeter-foundation"
        ]
        self.assertEqual(len(foundations), 2)
        self.assertTrue(all(spec["w"] <= 1.6 for spec in foundations))
        self.assertEqual(role_count(specs, "a20-conservatory-interior-floor"), 1)

    def test_near_mid_far_layers_and_human_story_are_present(self):
        specs = self.lods[0]
        self.assertGreaterEqual(role_count(specs, "a20-near-pergola-post"), 10)
        self.assertGreaterEqual(role_count(specs, "a20-near-pergola-slat"), 16)
        self.assertEqual(role_count(specs, "a20-midground-bridge-deck"), 1)
        self.assertEqual(role_count(specs, "a20-midground-bridge-parapet"), 2)
        self.assertEqual(role_count(specs, "a20-far-occupied-tower"), 10)
        self.assertGreaterEqual(role_count(specs, "a20-far-layered-roof-slope"), 20)
        self.assertGreaterEqual(role_count(specs, "a20-human-cover-planter"), 8)
        self.assertGreaterEqual(role_count(specs, "a20-garden-bench-seat"), 8)
        self.assertEqual(role_count(specs, "a20-irrigation-service-cart"), 1)
        self.assertGreaterEqual(role_count(specs, "a20-city-deep-window"), 84)
        self.assertGreaterEqual(role_count(specs, "a20-city-facade-pilaster"), 105)
        self.assertGreaterEqual(role_count(specs, "a20-city-planted-balcony"), 21)
        self.assertGreaterEqual(role_count(specs, "a20-city-south-deep-window"), 168)
        self.assertGreaterEqual(role_count(specs, "a20-city-east-deep-window"), 168)
        self.assertGreaterEqual(role_count(specs, "a20-near-botanical-plant"), 14)
        self.assertEqual(role_count(specs, "a20-reference-corridor-water"), 1)
        self.assertEqual(role_count(specs, "a20-reference-corridor-bridge"), 3)
        self.assertEqual(role_count(specs, "a20-near-corridor-pavilion-base"), 2)
        self.assertEqual(role_count(specs, "a20-layered-garden-court"), 8)

    def test_locked_player_height_camera_frames_and_separates_both_heroes(self):
        camera = NAKANIWA.MAIN_REFERENCE_CAMERA
        self.assertEqual(camera["location"][1], 1.65)
        self.assertEqual(camera["eyeHeightM"], 1.65)
        self.assertEqual(camera["lensMm"], 15.0)
        self.assertEqual(camera["resolution"], (1280, 720))
        metrics = NAKANIWA.reference_camera_frame_metrics(0)
        self.assertTrue(metrics["passed"], metrics)
        palace, conservatory = metrics["heroes"]
        self.assertGreaterEqual(palace["visibleFrameHeightRatio"], 0.26)
        self.assertGreaterEqual(conservatory["visibleFrameHeightRatio"], 0.32)
        self.assertGreaterEqual(palace["visibleFrameWidthRatio"], 0.34)
        self.assertGreaterEqual(conservatory["visibleFrameWidthRatio"], 0.34)
        # The runtime-to-Blender handedness mirrors projection X; this order
        # yields palace-left / conservatory-right in the proof render.
        self.assertGreater(
            palace["rawFrameBounds"][0] - conservatory["rawFrameBounds"][2],
            0.20,
        )

    def test_connection_map_has_unique_explicit_positive_contacts(self):
        self.assertGreaterEqual(len(NAKANIWA.CONNECTION_MAP), 35)
        ids = [connection["id"] for connection in NAKANIWA.CONNECTION_MAP]
        self.assertEqual(len(ids), len(set(ids)))
        for connection in NAKANIWA.CONNECTION_MAP:
            self.assertTrue(connection["a"])
            self.assertTrue(connection["b"])
            self.assertTrue(connection["aFace"])
            self.assertTrue(connection["bFace"])
            self.assertGreaterEqual(connection["overlapM"], 0.02)

    def test_all_lods_fit_stage_and_landmark_height_envelopes(self):
        for lod, specs in enumerate(self.lods):
            with self.subTest(lod=lod):
                bounds = [NAKANIWA.spec_bounds(spec) for spec in specs]
                self.assertGreaterEqual(min(item[0] for item in bounds), -160.001)
                self.assertLessEqual(max(item[3] for item in bounds), 160.001)
                self.assertGreaterEqual(min(item[2] for item in bounds), -160.001)
                self.assertLessEqual(max(item[5] for item in bounds), 160.001)
                self.assertGreaterEqual(min(item[1] for item in bounds), -0.61)
                self.assertLessEqual(max(item[4] for item in bounds), 50.0)
                for landmark in NAKANIWA.LANDMARKS:
                    hero_bounds = [
                        NAKANIWA.spec_bounds(spec) for spec in specs
                        if spec["group"] == landmark["id"]
                    ]
                    self.assertLessEqual(
                        max(item[4] for item in hero_bounds), landmark["height"] + 1e-6
                    )

    def test_blockers_leave_approaches_and_every_spawn_clear(self):
        spawns = NAKANIWA.CANONICAL_PLAYER_SPAWNS + NAKANIWA.CANONICAL_BOT_SPAWNS
        for lod, specs in enumerate(self.lods):
            blockers = [spec for spec in specs if spec["blocksGameplay"]]
            for landmark in NAKANIWA.LANDMARKS:
                approach = landmark["approach"]
                half = approach["width"] / 2.0
                min_x = min(approach["start"][0], approach["end"][0]) - half
                max_x = max(approach["start"][0], approach["end"][0]) + half
                min_z = min(approach["start"][1], approach["end"][1]) - half
                max_z = max(approach["start"][1], approach["end"][1]) + half
                intrusions = [
                    spec["role"] for spec in blockers
                    if plan_intersects(
                        NAKANIWA.spec_bounds(spec), min_x, max_x, min_z, max_z
                    )
                ]
                self.assertEqual(intrusions, [], f"LOD{lod} {landmark['id']}")
            for spawn_x, _, spawn_z in spawns:
                hits = []
                for spec in blockers:
                    bounds = NAKANIWA.spec_bounds(spec)
                    if (
                        bounds[0] - 0.5 <= spawn_x <= bounds[3] + 0.5
                        and bounds[2] - 0.5 <= spawn_z <= bounds[5] + 0.5
                    ):
                        hits.append(spec["role"])
                self.assertEqual(hits, [], f"LOD{lod} spawn {(spawn_x, spawn_z)}")

    def test_lod_costs_decrease_and_stay_inside_declared_budgets(self):
        triangle_counts = []
        spec_counts = []
        for lod, specs in enumerate(self.lods):
            triangle_count = NAKANIWA.estimated_triangles(specs)
            triangle_counts.append(triangle_count)
            spec_counts.append(len(specs))
            budget = NAKANIWA.LOD_BUDGETS[lod]
            self.assertLessEqual(triangle_count, budget["maxEstimatedTriangles"])
            self.assertLessEqual(len(specs), budget["maxSpecs"])
            self.assertLessEqual(len({spec["material"] for spec in specs}), budget["maxMaterials"])
            self.assertGreaterEqual(role_count(specs, "a20-palace-crown-petal-glass"), 5)
            self.assertGreaterEqual(role_count(specs, "a20-conservatory-fan-vault-rib"), 90)
            self.assertEqual(role_count(specs, "a20-conservatory-upper-walk"), 2)
            self.assertEqual(role_count(specs, "a20-conservatory-botanical-destination"), 1)
        self.assertGreater(triangle_counts[0], triangle_counts[1])
        self.assertGreater(triangle_counts[1], triangle_counts[2])
        self.assertGreater(spec_counts[0], spec_counts[1])
        self.assertGreater(spec_counts[1], spec_counts[2])
        self.assertLess(triangle_counts[1] / triangle_counts[0], 0.50)
        self.assertLess(triangle_counts[2] / triangle_counts[0], 0.20)

    def test_materials_are_shared_pbr_and_webgl_bounded(self):
        self.assertEqual(len(NAKANIWA.MATERIALS), 12)
        self.assertEqual(
            set(NAKANIWA.MATERIALS),
            set(NAKANIWA.DEFAULT_INTEGRATION_MATERIAL_MAP),
        )
        for recipe in NAKANIWA.MATERIALS.values():
            self.assertIn("color", recipe)
            self.assertIn("roughness", recipe)
            self.assertIn("metallic", recipe)
            self.assertIn("noiseScale", recipe)
            self.assertIn("bump", recipe)
        glass = NAKANIWA.MATERIALS["glass"]
        water = NAKANIWA.MATERIALS["water"]
        self.assertGreaterEqual(glass["transmission"], 0.85)
        self.assertAlmostEqual(glass["ior"], 1.45)
        self.assertLessEqual(max(glass["roughness"]), 0.12)
        self.assertAlmostEqual(water["ior"], 1.333)
        self.assertGreater(NAKANIWA.MATERIALS["verdigris_bronze"]["metallic"], 0.80)
        self.assertGreater(NAKANIWA.MATERIALS["foliage_dark"]["subsurface"], 0.0)

    def test_builder_emitter_covers_every_spec_kind(self):
        builder = RecordingBuilder()
        specs = NAKANIWA.emit_to_builder(builder, 2, {key: key for key in NAKANIWA.MATERIALS})
        self.assertEqual(len(builder.calls), len(specs))
        self.assertEqual(
            {kind for kind, _ in builder.calls},
            {"box", "beam", "cylinder", "panel", "ellipsoid"},
        )

    def test_scorecard_is_explicitly_provisional_no_ship(self):
        scorecard = NAKANIWA.producer_provisional_scorecard(("private-proof.png",))
        self.assertEqual(
            tuple(item["category"] for item in scorecard["scores"]),
            NAKANIWA.FIXED_SCORE_CATEGORIES,
        )
        self.assertEqual(scorecard["reviewer"], "producer-self-review-only")
        self.assertFalse(scorecard["referencePassClaimed"])
        self.assertEqual(scorecard["verdict"], "NO-SHIP_PENDING_INDEPENDENT_REVIEW")
        self.assertEqual(scorecard["evidencePaths"], ["private-proof.png"])
        self.assertTrue(str(NAKANIWA.PRIVATE_PROOF_DEFAULT).startswith("/private/tmp/"))


if __name__ == "__main__":
    unittest.main()
