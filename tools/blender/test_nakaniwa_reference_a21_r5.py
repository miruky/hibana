import copy
import hashlib
from pathlib import Path
import unittest

from tools.blender.stage_kits import nakaniwa_reference_a20 as A20
from tools.blender.stage_kits import nakaniwa_reference_a21_r5 as NAKANIWA


class RecordingBuilder:
    def __init__(self):
        self.calls = []

    def add_box(self, *args):
        self.calls.append(("box", args))

    def add_chamfer_box(self, *args):
        self.calls.append(("chamfer_box", args))

    def add_cylinder(self, *args):
        self.calls.append(("cylinder", args))

    def add_surface_panel(self, *args):
        self.calls.append(("panel", args))

    def add_sweep(self, *args):
        self.calls.append(("sweep", args))

    def add_leaf_cluster(self, *args):
        self.calls.append(("leaf_cluster", args))


def role_count(specs, role):
    return sum(spec["role"] == role for spec in specs)


class NakaniwaReferenceA21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lods = tuple(NAKANIWA.build_specs(lod) for lod in range(3))

    def test_canonical_contract_and_exact_two_landmarks_are_frozen(self):
        self.assertEqual(NAKANIWA.MAP_SIZE_M, 320.0)
        self.assertEqual(
            NAKANIWA.CANONICAL_BOUNDS,
            {"min_x": -160.0, "max_x": 160.0, "min_z": -160.0, "max_z": 160.0},
        )
        self.assertEqual(NAKANIWA.CANONICAL_ROADS, A20.CANONICAL_ROADS)
        self.assertEqual(NAKANIWA.CANONICAL_PLAYER_SPAWNS, A20.CANONICAL_PLAYER_SPAWNS)
        self.assertEqual(NAKANIWA.CANONICAL_BOT_SPAWNS, A20.CANONICAL_BOT_SPAWNS)
        self.assertEqual(
            [
                (
                    landmark["id"], landmark["cx"], landmark["cz"],
                    landmark["width"], landmark["depth"], landmark["height"],
                    landmark["entrance"], landmark["approach"],
                    landmark["collisionTemplate"],
                )
                for landmark in NAKANIWA.LANDMARKS
            ],
            [
                (
                    landmark["id"], landmark["cx"], landmark["cz"],
                    landmark["width"], landmark["depth"], landmark["height"],
                    landmark["entrance"], landmark["approach"],
                    landmark["collisionTemplate"],
                )
                for landmark in A20.LANDMARKS
            ],
        )
        self.assertEqual(len(NAKANIWA.LANDMARKS), 2)

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

    def test_a21_plan_does_not_mutate_a20(self):
        before = copy.deepcopy(A20.build_specs(0))
        NAKANIWA.build_specs(0)
        self.assertEqual(A20.build_specs(0), before)

    def test_heroes_are_fresh_a21_macro_rebuilds(self):
        for lod, specs in enumerate(self.lods):
            hero_specs = [
                spec for spec in specs
                if spec["group"] in {NAKANIWA.PALACE_ID, NAKANIWA.CONSERVATORY_ID}
            ]
            self.assertTrue(hero_specs, f"LOD{lod}")
            self.assertTrue(
                all(spec["role"].startswith("a21-") for spec in hero_specs),
                f"LOD{lod} retained an older hero part",
            )
            self.assertFalse(any(spec["role"].startswith("a20-") for spec in specs))

    def test_palace_is_tall_layered_arcaded_and_heavily_crowned(self):
        specs = self.lods[0]
        self.assertEqual(role_count(specs, "a21-palace-occupied-lower-wing"), 2)
        self.assertEqual(role_count(specs, "a21-palace-central-keep"), 1)
        central_keep = next(
            spec for spec in specs if spec["role"] == "a21-palace-central-keep"
        )
        self.assertGreaterEqual(central_keep["h"], 28.0)
        self.assertEqual(
            sum(
                spec["role"].startswith("a21-palace-central-stepped-terrace-")
                for spec in specs
            ),
            3,
        )
        self.assertGreaterEqual(
            role_count(specs, "a21-palace-grand-continuous-arcade-curved-rib"), 12
        )
        self.assertGreaterEqual(
            role_count(specs, "a21-palace-side-continuous-arcade-curved-rib"), 18
        )
        self.assertGreaterEqual(role_count(specs, "a21-palace-upper-loggia-curved-rib"), 14)
        self.assertGreaterEqual(
            role_count(
                specs, "a21-palace-central-keep-side-loggia-curved-rib"
            ),
            5,
        )
        self.assertGreaterEqual(
            role_count(
                specs, "a21-palace-central-keep-deep-loggia-curved-rib"
            ),
            5,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-lower-water-loggia-deep-occupied-arcade",
            ),
            10,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-middle-garden-loggia-deep-occupied-arcade",
            ),
            8,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-upper-sky-loggia-deep-occupied-arcade",
            ),
            6,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-continuous-supported-balcony",
            ),
            3,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-rooted-crown-keep-shoulder",
            ),
            1,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-overlapping-vertical-petal",
            ),
            7,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-palace-fine-petal-spine"),
            7,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-palace-fine-petal-edge"),
            14,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-rooted-keep-occupied-loggia",
            ),
            5,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-broad-ceremonial-gallery-stair",
            ),
            10,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-palace-occupied-loggia-planter"),
            7,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-palace-occupied-connection-bridge-deck",
            ),
            1,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r4-palace-water-maintenance-valve-wheel",
            ),
            1,
        )
        self.assertFalse(
            any(
                any(
                    spec["role"].startswith(prefix)
                    for prefix in NAKANIWA.LEGACY_DUPLICATE_CROWN_PREFIXES
                )
                for spec in specs
            )
        )
        self.assertFalse(
            any(
                any(
                    spec["role"].startswith(prefix)
                    for prefix in NAKANIWA.R5_VISUAL_BLOCKER_PREFIXES
                )
                for spec in specs
            )
        )
        self.assertEqual(role_count(specs, "a21-palace-water"), 2)
        palace_bounds = [
            NAKANIWA.spec_bounds(spec)
            for spec in specs if spec["group"] == NAKANIWA.PALACE_ID
        ]
        self.assertGreaterEqual(max(bound[4] for bound in palace_bounds), 42.5)
        self.assertLessEqual(max(bound[4] for bound in palace_bounds), 43.0)

    def test_conservatory_is_exactly_five_large_overlapping_vaults(self):
        specs = self.lods[0]
        vault_roles = {
            spec["role"].split("-curved-primary-rib")[0]
            for spec in specs
            if "a21-conservatory-vault-" in spec["role"]
            and spec["role"].endswith("-curved-primary-rib")
        }
        self.assertEqual(len(vault_roles), 5)
        self.assertEqual(
            role_count(specs, "a21-conservatory-vault-buttress"), 10
        )
        self.assertGreaterEqual(
            role_count(specs, "a21-conservatory-secondary-purlin"), 45
        )
        self.assertGreaterEqual(
            role_count(specs, "a21-conservatory-dirty-glass-cell"), 80
        )
        self.assertGreaterEqual(
            role_count(
                specs,
                "a21-conservatory-camera-facing-glass-fan-cell",
            ),
            80,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-conservatory-tinted-glass-highlight-layer",
            ),
            role_count(specs, "a21-conservatory-dirty-glass-cell"),
        )
        self.assertGreaterEqual(
            role_count(
                specs,
                "a21-conservatory-camera-facing-radial-mullion",
            ),
            40,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-conservatory-camera-facing-inset-transom",
            ),
            10,
        )
        self.assertEqual(
            {
                spec["material"]
                for spec in specs
                if spec["role"]
                == "a21-conservatory-camera-facing-inset-transom"
            },
            {"brass", "verdigris_bronze"},
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-conservatory-camera-facing-stone-spring-pylon",
            ),
            10,
        )
        self.assertEqual(
            role_count(specs, "a21-conservatory-primary-rib-cast-shadow"),
            15,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-conservatory-open-entry-base"),
            1,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-conservatory-transparent-warm-entry-bay-recessed-glazing",
            ),
            7,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-conservatory-open-entry-slender-stone-pier",
            ),
            3,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-conservatory-broad-readable-entry-stair",
            ),
            8,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-conservatory-interior-botanical-mezzanine",
            ),
            2,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-conservatory-interior-warm-depth-lantern",
            ),
            10,
        )
        self.assertFalse(
            any(
                spec["role"].startswith(
                    (
                        "a21-conservatory-monumental-entry-drum",
                        "a21-conservatory-entry-drum",
                        "a21-conservatory-occupied-glass-lantern",
                        "a21-conservatory-monumental-entry-fan",
                    )
                )
                for spec in specs
            )
        )
        self.assertEqual(role_count(specs, "a21-conservatory-upper-walk"), 2)
        self.assertEqual(
            role_count(specs, "a21-conservatory-interior-cross-catwalk"),
            1,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-conservatory-interior-cross-catwalk-post",
            ),
            18,
        )
        self.assertGreaterEqual(
            role_count(specs, "a21-conservatory-specimen-leaf-cluster"), 100
        )
        vault_apexes = [
            max(
                max(point[1] for point in spec["points"])
                for spec in specs
                if spec["role"]
                == f"a21-conservatory-vault-{index}-curved-primary-rib"
            )
            for index in range(5)
        ]
        self.assertGreater(vault_apexes[2], 47.0)
        self.assertGreater(vault_apexes[1], vault_apexes[0] + 7.0)
        self.assertGreater(vault_apexes[2], vault_apexes[1] + 7.0)
        self.assertGreater(vault_apexes[3], vault_apexes[4] + 7.0)
        centre_ribs = [
            spec
            for spec in specs
            if spec["role"]
            == "a21-conservatory-vault-2-curved-primary-rib"
        ]
        front_profile = min(
            centre_ribs,
            key=lambda spec: min(point[2] for point in spec["points"]),
        )["points"]
        quarter = front_profile[len(front_profile) // 4]
        spring_y = min(point[1] for point in front_profile)
        apex_y = max(point[1] for point in front_profile)
        self.assertGreater(
            quarter[1],
            spring_y + (apex_y - spring_y) * 0.72,
        )
        self.assertGreater(
            max(max(point[2] for point in spec["points"]) for spec in centre_ribs)
            - min(min(point[2] for point in spec["points"]) for spec in centre_ribs),
            30.0,
        )

    def test_no_black_holes_or_faceted_primitive_trees(self):
        specs = self.lods[0]
        self.assertNotIn("warm_window", NAKANIWA.MATERIALS)
        self.assertFalse(any(spec["kind"] == "ellipsoid" for spec in specs))
        self.assertFalse(any("black" in spec["material"] for spec in specs))
        self.assertGreaterEqual(
            role_count(specs, "a21-palace-deep-warm-occupied-opening"), 8
        )
        self.assertGreaterEqual(
            sum(
                1
                for spec in specs
                if spec["role"].endswith("-shadow-recess")
            ),
            100,
        )
        self.assertGreaterEqual(
            sum(
                1
                for spec in specs
                if spec["role"].endswith("-vertical-mullion")
            ),
            100,
        )
        self.assertGreaterEqual(
            sum(spec["kind"] == "leaf_cluster" for spec in specs), 150
        )

    def test_role_specific_baked_chamfers_and_curves_replace_global_bevel(self):
        specs = self.lods[0]
        chamfers = [spec for spec in specs if spec["kind"] == "chamfer_box"]
        sweeps = [spec for spec in specs if spec["kind"] == "sweep"]
        self.assertTrue(any(0.10 <= spec["bevel"] <= 0.20 for spec in chamfers))
        self.assertTrue(any(0.03 <= spec["bevel"] <= 0.08 for spec in chamfers))
        self.assertTrue(any(0.01 <= spec["radius"] <= 0.035 for spec in sweeps))
        self.assertGreaterEqual(len(sweeps), 180)

    def test_near_mid_far_density_boundary_and_story_are_real_geometry(self):
        specs = self.lods[0]
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-signature-diagonal-garden-canal-water",
            ),
            1,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-signature-canal-carved-retaining-coping",
            ),
            2,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-garden-canal-bridge-thick-stone-deck",
            ),
            3,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-garden-canal-bridge-twin-pointed-arch",
            ),
            12,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-garden-canal-bridge-grounded-arch-pier",
            ),
            18,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-garden-canal-bridge-brass-parapet",
            ),
            6,
        )
        self.assertEqual(
            role_count(specs, "a21-r2-canal-broken-sky-reflection"),
            12,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-canal-water-lily-cluster",
            ),
            4,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-canal-terraced-botanical-planter",
            ),
            8,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-canal-side-monumental-garden-arcade",
            ),
            4,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-canal-side-arcade-buttressed-pier",
            ),
            5,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-extreme-foreground-carved-garden-parapet",
            ),
            2,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-extreme-foreground-dark-garden-soil",
            ),
            2,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-extreme-foreground-fine-flower-and-fern-bed",
            ),
            6,
        )
        self.assertEqual(
            role_count(specs, "a21-r2-gardener-irrigation-landing"), 1
        )
        self.assertEqual(
            role_count(specs, "a21-r2-gardener-irrigation-wheel"), 1
        )
        self.assertEqual(
            role_count(specs, "a21-r4-bridge-coping-contact-key"),
            6,
        )
        self.assertEqual(
            role_count(specs, "a21-r4-canal-maintenance-hand-tool"),
            3,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-bridge-approach-step"),
            7,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-bridge-approach-wet-landing"),
            1,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-foreground-layered-limestone-planter",
            ),
            3,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-foreground-layered-flower-and-fern",
            ),
            9,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-gardener-bench-seat"),
            1,
        )
        self.assertEqual(
            role_count(specs, "a21-r5-gardener-hand-tool"),
            3,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-first-bridge-warm-lantern",
            ),
            2,
        )
        self.assertEqual(
            role_count(specs, "a21-r2-district-occupied-arcade-hall"),
            18,
        )
        self.assertEqual(
            role_count(specs, "a21-r2-district-shoulder-loggia-pavilion"),
            0,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-district-stage-exclusive-crown-roof-slope",
            ),
            36,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-district-deep-garden-arcade-curved-rib",
            ),
            0,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r2-district-deep-side-garden-arcade",
            ),
            0,
        )
        self.assertEqual(
            role_count(specs, "a21-r2-district-roof-garden-foliage"),
            18,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r3-mid-city-octagonal-occupied-arcade-pavilion",
            ),
            0,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r3-canal-destination-monumental-open-arch",
            ),
            0,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r3-canal-destination-occupied-octagonal-gatehouse",
            ),
            0,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-garden-city-occupied-limestone-house",
            ),
            10,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-garden-city-stepped-occupied-upper-loggia",
            ),
            10,
        )
        self.assertEqual(
            role_count(
                specs,
                "a21-r5-garden-city-deep-occupied-arcade-curved-rib",
            ),
            30,
        )
        self.assertGreaterEqual(
            role_count(
                specs,
                "a21-r5-garden-city-layered-canopy-leaf-cluster",
            ),
            100,
        )
        self.assertFalse(any(spec["role"].startswith("a21-district-") for spec in specs))
        self.assertFalse(any("matte" in spec["role"] for spec in specs))
        water = next(
            spec
            for spec in specs
            if spec["role"]
            == "a21-r2-signature-diagonal-garden-canal-water"
        )
        promenade = next(
            spec
            for spec in specs
            if spec["role"]
            == "a21-r2-canal-side-occupied-stone-promenade"
        )
        self.assertGreater(
            NAKANIWA.spec_bounds(water)[4],
            NAKANIWA.spec_bounds(promenade)[4],
        )

    def test_locked_player_height_camera_shows_both_heroes_large(self):
        camera = NAKANIWA.MAIN_REFERENCE_CAMERA
        self.assertEqual(camera["location"][1], 1.65)
        self.assertEqual(camera["eyeHeightM"], 1.65)
        self.assertEqual(camera["resolution"], (1280, 720))
        metrics = NAKANIWA.reference_camera_frame_metrics(0)
        self.assertTrue(metrics["passed"], metrics)
        for hero in metrics["heroes"]:
            self.assertGreaterEqual(hero["visibleFrameWidthRatio"], 0.30)
            self.assertGreaterEqual(hero["visibleFrameHeightRatio"], 0.32)

    def test_connection_map_has_unique_measured_contacts(self):
        self.assertGreaterEqual(len(NAKANIWA.CONNECTION_MAP), 18)
        ids = [connection["id"] for connection in NAKANIWA.CONNECTION_MAP]
        self.assertEqual(len(ids), len(set(ids)))
        for connection in NAKANIWA.CONNECTION_MAP:
            self.assertGreaterEqual(connection["overlapM"], 0.02)
            self.assertTrue(connection["a"])
            self.assertTrue(connection["b"])

    def test_all_lods_fit_stage_and_landmark_envelopes(self):
        for lod, specs in enumerate(self.lods):
            bounds = [NAKANIWA.spec_bounds(spec) for spec in specs]
            self.assertGreaterEqual(min(item[0] for item in bounds), -160.001, lod)
            self.assertLessEqual(max(item[3] for item in bounds), 160.001, lod)
            self.assertGreaterEqual(min(item[2] for item in bounds), -160.001, lod)
            self.assertLessEqual(max(item[5] for item in bounds), 160.001, lod)
            self.assertGreaterEqual(min(item[1] for item in bounds), -0.61, lod)
            for landmark in NAKANIWA.LANDMARKS:
                hero = [
                    NAKANIWA.spec_bounds(spec)
                    for spec in specs if spec["group"] == landmark["id"]
                ]
                self.assertLessEqual(max(item[4] for item in hero), landmark["height"] + 1e-6)
                self.assertGreaterEqual(min(item[0] for item in hero), landmark["cx"] - landmark["width"] / 2 - 1e-6)
                self.assertLessEqual(max(item[3] for item in hero), landmark["cx"] + landmark["width"] / 2 + 1e-6)
                self.assertGreaterEqual(min(item[2] for item in hero), landmark["cz"] - landmark["depth"] / 2 - 1e-6)
                self.assertLessEqual(max(item[5] for item in hero), landmark["cz"] + landmark["depth"] / 2 + 1e-6)

    def test_visual_shell_never_redefines_gameplay_collision(self):
        for lod, specs in enumerate(self.lods):
            self.assertFalse(any(spec["blocksGameplay"] for spec in specs), lod)

    def test_route_spawn_and_camera_intrusions_remain_zero(self):
        for lod in range(3):
            report = NAKANIWA.gameplay_intrusion_report(lod)
            self.assertTrue(report["passed"], report)
            self.assertEqual(report["blockingSpecCount"], 0)
            self.assertEqual(report["playerSpawnIntrusions"], 0)
            self.assertEqual(report["botSpawnIntrusions"], 0)
            self.assertEqual(report["approachRouteIntrusions"], 0)
            self.assertEqual(report["cameraIntrusions"], 0)

    def test_lod_costs_fit_exact_production_targets(self):
        triangle_counts = []
        for lod, specs in enumerate(self.lods):
            count = NAKANIWA.estimated_triangles(specs)
            triangle_counts.append(count)
            budget = NAKANIWA.LOD_BUDGETS[lod]
            self.assertGreaterEqual(count, budget["minEvaluatedTriangles"])
            self.assertLessEqual(count, budget["maxEvaluatedTriangles"])
            self.assertLessEqual(len(specs), budget["maxSpecs"])
            self.assertLessEqual(
                len({spec["material"] for spec in specs}), budget["maxMaterials"]
            )
        self.assertGreater(triangle_counts[0], triangle_counts[1])
        self.assertGreater(triangle_counts[1], triangle_counts[2])
        self.assertLessEqual(triangle_counts[1] / triangle_counts[0], 0.50)
        self.assertLessEqual(triangle_counts[2] / triangle_counts[0], 0.16)

    def test_materials_are_shared_pbr_and_realistically_bounded(self):
        self.assertGreaterEqual(len(NAKANIWA.MATERIALS), 8)
        self.assertLessEqual(len(NAKANIWA.MATERIALS), 14)
        self.assertEqual(
            set(NAKANIWA.MATERIALS),
            set(NAKANIWA.DEFAULT_INTEGRATION_MATERIAL_MAP),
        )
        for recipe in NAKANIWA.MATERIALS.values():
            self.assertIn("color", recipe)
            self.assertIn("roughness", recipe)
            self.assertIn("metallic", recipe)
            self.assertIn("noiseScale", recipe)
            self.assertIn("detailScale", recipe)
            self.assertIn("bump", recipe)
        self.assertAlmostEqual(NAKANIWA.MATERIALS["dirty_glass"]["ior"], 1.45)
        self.assertGreater(
            NAKANIWA.MATERIALS["dirty_glass"]["transmission"], 0.5
        )
        self.assertGreater(
            NAKANIWA.MATERIALS["dirty_glass"]["alpha"], 0.15
        )
        self.assertLess(
            NAKANIWA.MATERIALS["dirty_glass"]["alpha"], 0.35
        )
        self.assertGreaterEqual(
            NAKANIWA.MATERIALS["glass_highlight"]["alpha"], 0.10
        )
        self.assertLessEqual(
            NAKANIWA.MATERIALS["glass_highlight"]["alpha"], 0.35
        )
        self.assertGreater(
            NAKANIWA.MATERIALS["glass_highlight"]["transmission"], 0.4
        )
        ivory = NAKANIWA.MATERIALS["ivory_stone"]["color"]
        carved = NAKANIWA.MATERIALS["carved_stone"]["color"]
        self.assertLess(max(ivory[:3]) - min(ivory[:3]), 0.10)
        self.assertLess(max(carved[:3]) - min(carved[:3]), 0.06)
        self.assertAlmostEqual(NAKANIWA.MATERIALS["water"]["ior"], 1.333)
        self.assertGreater(NAKANIWA.MATERIALS["water"]["transmission"], 0.0)
        self.assertGreater(NAKANIWA.MATERIALS["brass"]["metallic"], 0.8)
        self.assertGreater(NAKANIWA.MATERIALS["foliage_light"]["subsurface"], 0.0)

    def test_builder_emitter_covers_every_custom_spec_kind(self):
        builder = RecordingBuilder()
        specs = NAKANIWA.emit_to_builder(
            builder, 2, {key: key for key in NAKANIWA.MATERIALS}
        )
        self.assertEqual(len(builder.calls), len(specs))
        self.assertEqual(
            {kind for kind, _ in builder.calls},
            {"box", "chamfer_box", "cylinder", "panel", "sweep", "leaf_cluster"},
        )

    def test_output_and_scorecard_remain_private_no_ship(self):
        scorecard = NAKANIWA.independent_baseline_scorecard(
            ("private-proof.png",)
        )
        self.assertEqual(
            tuple(item["category"] for item in scorecard["scores"]),
            NAKANIWA.FIXED_SCORE_CATEGORIES,
        )
        self.assertEqual(
            scorecard["reviewer"],
            "independent-baseline-carry-forward-no-self-rescore",
        )
        self.assertEqual(scorecard["arithmeticMean"], 4.22)
        self.assertEqual(scorecard["minimumCategoryScore"], 2.9)
        self.assertEqual(
            scorecard["sourceScorecard"],
            str(NAKANIWA.R4_INDEPENDENT_REVIEW_PATH),
        )
        self.assertEqual(
            scorecard["sourceScorecardSha256"],
            NAKANIWA.R4_INDEPENDENT_REVIEW_SHA256,
        )
        self.assertTrue(scorecard["genericBlockoutBaseline"])
        self.assertFalse(scorecard["rebuildSelfCertified"])
        self.assertFalse(scorecard["referencePassClaimed"])
        self.assertEqual(
            scorecard["verdict"],
            "NO-SHIP_PENDING_NEW_INDEPENDENT_REVIEW",
        )
        self.assertEqual(scorecard["evidencePaths"], ["private-proof.png"])
        self.assertTrue(str(NAKANIWA.PRIVATE_PRODUCTION_DEFAULT).startswith("/private/tmp/"))
        self.assertTrue(str(NAKANIWA.PRIVATE_PRODUCTION_DEFAULT).endswith("-r5"))
        self.assertGreaterEqual(len(NAKANIWA.SELF_REJECT_HISTORY), 4)
        self.assertEqual(
            NAKANIWA.SELF_REJECT_HISTORY[0]["verdict"],
            "REJECTED_GENERIC_BLOCKOUT",
        )
        self.assertEqual(
            NAKANIWA.SELF_REJECT_HISTORY[3]["arithmeticMean"],
            4.50,
        )

    @unittest.skipUnless(
        NAKANIWA.INDEPENDENT_SCORECARD_R3_PATH.is_file()
        and NAKANIWA.R4_SOURCE_PATH.is_file()
        and NAKANIWA.R4_CANDIDATE_PATH.is_file()
        and NAKANIWA.R4_MANIFEST_PATH.is_file()
        and NAKANIWA.R4_INDEPENDENT_REVIEW_PATH.is_file(),
        "immutable private R3/R4 evidence is unavailable",
    )
    def test_independent_source_evidence_is_hash_locked_and_untouched(self):
        report = NAKANIWA.locked_r3_scorecard_report()
        self.assertTrue(report["matched"], report)
        self.assertFalse(report["writeAttempted"])
        self.assertEqual(
            hashlib.sha256(
                NAKANIWA.INDEPENDENT_SCORECARD_R3_PATH.read_bytes()
            ).hexdigest(),
            NAKANIWA.INDEPENDENT_SCORECARD_R3_SHA256,
        )
        r4_report = NAKANIWA.locked_r4_report()
        self.assertTrue(r4_report["matched"], r4_report)
        self.assertFalse(r4_report["writeAttempted"])
        self.assertEqual(len(r4_report["artifacts"]), 4)
        for artifact in r4_report["artifacts"]:
            self.assertTrue(artifact["matched"], artifact)
            self.assertEqual(
                hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest(),
                artifact["expectedSha256"],
            )


if __name__ == "__main__":
    unittest.main()
