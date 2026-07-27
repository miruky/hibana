import importlib.util
import math
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parent / "stage_kits/nakaniwa_reference_a18.py"
SPEC = importlib.util.spec_from_file_location("nakaniwa_reference_a18", MODULE_PATH)
NAKANIWA = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(NAKANIWA)


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


def role_count(specs, role):
    return sum(spec["role"] == role for spec in specs)


def plan_intersects(bounds, min_x, max_x, min_z, max_z):
    return not (
        bounds[3] <= min_x
        or bounds[0] >= max_x
        or bounds[5] <= min_z
        or bounds[2] >= max_z
    )


class NakaniwaReferenceA18Tests(unittest.TestCase):
    def test_canonical_bounds_roads_landmarks_and_arrivals_are_frozen(self):
        self.assertEqual(NAKANIWA.MAP_SIZE_M, 320.0)
        self.assertEqual(
            NAKANIWA.CANONICAL_BOUNDS,
            {"min_x": -160.0, "max_x": 160.0, "min_z": -160.0, "max_z": 160.0},
        )
        self.assertEqual(len(NAKANIWA.CANONICAL_ROADS), 2)
        self.assertEqual([road["width"] for road in NAKANIWA.CANONICAL_ROADS], [16.0, 16.0])
        self.assertEqual(
            [(item["id"], item["cx"], item["cz"], item["width"], item["depth"], item["height"])
             for item in NAKANIWA.LANDMARKS],
            [
                ("nakaniwa-suiren-crown-palace", -60.0, -67.8, 92.0, 78.0, 43.0),
                ("nakaniwa-kakou-conservatory-citadel", 52.0, 61.8, 76.0, 66.0, 50.0),
            ],
        )
        self.assertEqual(NAKANIWA.CANONICAL_PLAYER_SPAWNS, (
            (0.0, 0.0, 148.0), (148.0, 0.0, 0.0),
            (0.0, 0.0, -148.0), (-148.0, 0.0, 0.0),
        ))
        self.assertEqual(NAKANIWA.LANDMARKS[0]["entrance"], (-60.0, -28.0))
        self.assertEqual(NAKANIWA.LANDMARKS[0]["approach"], {
            "start": (-60.0, -8.0), "end": (-60.0, -28.0), "width": 12.0,
        })
        self.assertEqual(NAKANIWA.LANDMARKS[1]["entrance"], (52.0, 28.0))
        self.assertEqual(NAKANIWA.LANDMARKS[1]["approach"], {
            "start": (52.0, 8.0), "end": (52.0, 28.0), "width": 12.0,
        })

    def test_connection_map_has_explicit_faces_and_positive_overlap(self):
        self.assertGreaterEqual(len(NAKANIWA.CONNECTION_MAP), 20)
        ids = {item["id"] for item in NAKANIWA.CONNECTION_MAP}
        self.assertEqual(len(ids), len(NAKANIWA.CONNECTION_MAP))
        for connection in NAKANIWA.CONNECTION_MAP:
            self.assertTrue(connection["a"])
            self.assertTrue(connection["b"])
            self.assertTrue(connection["aFace"])
            self.assertTrue(connection["bFace"])
            self.assertGreaterEqual(connection["overlapM"], 0.02)

    def test_lod0_reconstructs_all_failed_reference_vocabulary(self):
        specs = NAKANIWA.build_specs(0)
        self.assertGreaterEqual(role_count(specs, "palace-crown-spire"), 9)
        self.assertGreaterEqual(role_count(specs, "palace-crown-petal-glass"), 7)
        self.assertGreaterEqual(role_count(specs, "palace-crown-petal-frame"), 28)
        self.assertGreaterEqual(role_count(specs, "palace-master-spire"), 1)
        self.assertGreaterEqual(role_count(specs, "palace-lower-arcade-arch-rib"), 72)
        self.assertGreaterEqual(role_count(specs, "palace-upper-arcade-arch-rib"), 60)
        self.assertGreaterEqual(role_count(specs, "palace-lower-wing"), 2)
        self.assertGreaterEqual(role_count(specs, "palace-upper-loggia-arch-rib"), 50)
        self.assertGreaterEqual(role_count(specs, "palace-rear-crown-petal-glass"), 5)
        self.assertGreaterEqual(role_count(specs, "conservatory-vault-rib"), 300)
        self.assertGreaterEqual(role_count(specs, "conservatory-curved-glass-panel"), 250)
        self.assertGreaterEqual(role_count(specs, "conservatory-upper-walk"), 2)
        self.assertGreaterEqual(role_count(specs, "conservatory-side-arcade-arch-rib"), 100)
        self.assertEqual(role_count(specs, "conservatory-ventilation-lantern"), 2)
        self.assertGreaterEqual(role_count(specs, "conservatory-interior-stair"), 14)
        self.assertGreaterEqual(role_count(specs, "conservatory-interior-water"), 1)
        self.assertGreaterEqual(role_count(specs, "lush-canal-water"), 4)
        self.assertGreaterEqual(role_count(specs, "canal-bridge-deck"), 18)
        self.assertGreaterEqual(role_count(specs, "layered-civic-wing"), 24)
        self.assertGreaterEqual(role_count(specs, "civic-ground-arcade-arch-rib"), 150)
        self.assertGreaterEqual(role_count(specs, "mature-tree-trunk"), 32)
        self.assertGreaterEqual(role_count(specs, "garden-flower"), 40)
        self.assertGreaterEqual(role_count(specs, "garden-bench-seat"), 8)
        self.assertGreaterEqual(role_count(specs, "garden-lantern-light"), 8)
        self.assertGreaterEqual(role_count(specs, "foreground-arcade-arch-rib"), 70)
        self.assertEqual(role_count(specs, "stepped-garden-terrace"), 12)
        self.assertEqual(role_count(specs, "stepped-garden-rill"), 4)
        self.assertGreaterEqual(role_count(specs, "avenue-tier-planter"), 12)
        self.assertGreaterEqual(role_count(specs, "conservatory-dense-planting"), 30)
        self.assertGreaterEqual(role_count(specs, "conservatory-botanical-plant"), 24)
        self.assertEqual(role_count(specs, "conservatory-central-promenade"), 1)
        self.assertEqual(role_count(specs, "conservatory-rear-upper-walk"), 0)
        self.assertEqual(role_count(specs, "reference-forecourt-terrace"), 3)
        self.assertEqual(role_count(specs, "reference-forecourt-water"), 1)

    def test_r11_fixed_camera_keeps_both_heroes_near_forty_percent_height(self):
        camera = NAKANIWA.REFERENCE_DUAL_CAMERA
        self.assertEqual(camera["location"][1], 1.65)
        self.assertEqual(camera["targetFrameHeightRatio"], 0.40)
        metrics = NAKANIWA.reference_camera_frame_metrics(0)
        self.assertTrue(metrics["passed"], metrics)
        ratios = [hero["visibleFrameHeightRatio"] for hero in metrics["heroes"]]
        self.assertGreaterEqual(min(ratios), 0.33)
        self.assertLessEqual(max(ratios), 0.52)
        self.assertLessEqual(max(abs(ratio - 0.40) for ratio in ratios), 0.07)

    def test_threshold_and_interior_cameras_are_player_height_and_strict(self):
        for camera in (
            NAKANIWA.CONSERVATORY_THRESHOLD_CAMERA,
            NAKANIWA.CONSERVATORY_INTERIOR_CAMERA,
        ):
            self.assertEqual(camera["location"][1], NAKANIWA.PLAYER_EYE_M)
            self.assertEqual(camera["maxOpaqueObstructionRatio"], 0.10)
        self.assertEqual(NAKANIWA.CONSERVATORY_THRESHOLD_CAMERA["openingWidthM"], 8.0)
        self.assertEqual(NAKANIWA.CONSERVATORY_INTERIOR_CAMERA["clearViewWidthM"], 6.4)

    def test_conservatory_has_exact_eight_metre_opening_and_continuous_walk(self):
        specs = NAKANIWA.build_specs(0)
        portals = [spec for spec in specs if spec["role"] in {
            "conservatory-portal-left", "conservatory-portal-right",
        }]
        self.assertEqual(len(portals), 2)
        left, right = sorted(portals, key=lambda spec: spec["x"])
        gap = (right["x"] - right["w"] / 2) - (left["x"] + left["w"] / 2)
        self.assertAlmostEqual(gap, 8.0)
        rear_foundations = [
            spec for spec in specs
            if spec["role"] == "conservatory-perimeter-foundation"
            and abs(spec["z"] - 93.3) < 0.01
        ]
        self.assertEqual(len(rear_foundations), 2)
        rear_left, rear_right = sorted(rear_foundations, key=lambda spec: spec["x"])
        rear_gap = (
            rear_right["x"] - rear_right["w"] / 2
            - (rear_left["x"] + rear_left["w"] / 2)
        )
        self.assertAlmostEqual(rear_gap, 12.0)
        promenade = [spec for spec in specs if spec["role"] == "conservatory-central-promenade"]
        self.assertEqual(len(promenade), 1)
        self.assertEqual(promenade[0]["w"], 8.0)
        self.assertGreaterEqual(promenade[0]["d"], 58.0)
        self.assertGreaterEqual(role_count(specs, "conservatory-interior-stair"), 28)

    def test_lod_policy_reduces_cost_without_erasing_identity(self):
        lod0, lod1, lod2 = (NAKANIWA.build_specs(lod) for lod in range(3))
        self.assertGreater(len(lod0), len(lod1))
        self.assertGreater(len(lod1), len(lod2))
        for specs in (lod0, lod1, lod2):
            self.assertGreaterEqual(role_count(specs, "palace-crown-spire"), 5)
            self.assertGreaterEqual(role_count(specs, "conservatory-vault-rib"), 45)
            self.assertEqual(role_count(specs, "lush-canal-water"), 4)
            self.assertEqual(role_count(specs, "canal-bridge-deck"), 18)
            self.assertGreaterEqual(role_count(specs, "layered-civic-wing"), 14)
            self.assertGreaterEqual(role_count(specs, "mature-tree-trunk"), 10)
        self.assertGreaterEqual(role_count(lod1, "conservatory-curved-glass-panel"), 120)
        self.assertGreaterEqual(role_count(lod2, "conservatory-curved-glass-panel"), 30)

    def test_every_lod_stays_in_canonical_plan_bounds_and_height_envelopes(self):
        for lod in range(3):
            with self.subTest(lod=lod):
                bounds = [NAKANIWA.spec_bounds(spec) for spec in NAKANIWA.build_specs(lod)]
                self.assertGreaterEqual(min(item[0] for item in bounds), -160.001)
                self.assertLessEqual(max(item[3] for item in bounds), 160.001)
                self.assertGreaterEqual(min(item[2] for item in bounds), -160.001)
                self.assertLessEqual(max(item[5] for item in bounds), 160.001)
                self.assertGreaterEqual(min(item[1] for item in bounds), -0.61)
                self.assertLessEqual(max(item[4] for item in bounds), 50.0)

    def test_blocking_visuals_leave_both_approach_corridors_and_los_open(self):
        for lod in range(3):
            specs = NAKANIWA.build_specs(lod)
            blockers = [spec for spec in specs if spec["blocksGameplay"]]
            for landmark in NAKANIWA.LANDMARKS:
                approach = landmark["approach"]
                half = approach["width"] / 2
                min_x = min(approach["start"][0], approach["end"][0]) - half
                max_x = max(approach["start"][0], approach["end"][0]) + half
                min_z = min(approach["start"][1], approach["end"][1]) - half
                max_z = max(approach["start"][1], approach["end"][1]) + half
                intrusions = [spec["role"] for spec in blockers
                              if plan_intersects(NAKANIWA.spec_bounds(spec), min_x, max_x, min_z, max_z)]
                self.assertEqual(intrusions, [], f"LOD{lod} {landmark['id']} approach blockers")

    def test_mature_trees_do_not_clip_any_canonical_player_spawn(self):
        for lod in range(3):
            trunks = [spec for spec in NAKANIWA.build_specs(lod)
                      if spec["role"] == "mature-tree-trunk"]
            for spawn_x, _, spawn_z in NAKANIWA.CANONICAL_PLAYER_SPAWNS:
                nearest = min(
                    math.hypot(spec["x"] - spawn_x, spec["z"] - spawn_z)
                    for spec in trunks
                )
                self.assertGreaterEqual(
                    nearest, 8.0,
                    f"LOD{lod} mature tree clips spawn {(spawn_x, spawn_z)}",
                )

    def test_material_library_is_shared_and_pbr_role_complete(self):
        self.assertLessEqual(len(NAKANIWA.MATERIALS), 12)
        self.assertEqual(set(NAKANIWA.MATERIALS), set(NAKANIWA.DEFAULT_INTEGRATION_MATERIAL_MAP))
        for required in ("wet_stone", "white_marble", "verdigris_bronze", "glass", "water",
                         "brass", "foliage_dark", "foliage_light", "flower"):
            self.assertIn(required, NAKANIWA.MATERIALS)
        self.assertGreater(NAKANIWA.MATERIALS["glass"]["transmission"], 0.75)
        self.assertLess(NAKANIWA.MATERIALS["glass"]["roughness"], 0.12)
        self.assertLess(NAKANIWA.MATERIALS["water"]["roughness"], 0.15)
        self.assertGreater(NAKANIWA.MATERIALS["verdigris_bronze"]["metallic"], 0.7)

    def test_independent_v8_scorecard_remains_a_no_ship_baseline(self):
        self.assertEqual(len(NAKANIWA.REFERENCE_SCORE_ITEMS), 10)
        scores = [item["score"] for item in NAKANIWA.REFERENCE_SCORE_ITEMS]
        self.assertEqual(min(scores), 3.5)
        self.assertAlmostEqual(sum(scores) / len(scores), 4.86)
        self.assertEqual(len({item["category"] for item in NAKANIWA.REFERENCE_SCORE_ITEMS}), 10)

    def test_meshbuilder_compatible_emitter_covers_every_spec(self):
        builder = RecordingBuilder()
        specs = NAKANIWA.emit_to_builder(builder, 2)
        self.assertEqual(len(builder.calls), len(specs))
        self.assertEqual(
            sorted(kind for kind, _ in builder.calls),
            sorted(spec["kind"] for spec in specs),
        )
        self.assertTrue(any(call[0] == "panel" for call in builder.calls))
        self.assertTrue(any(call[0] == "beam" for call in builder.calls))

    def test_subset_emitter_preserves_landmark_batch_ownership(self):
        specs = NAKANIWA.build_specs(2)
        landmark_id = NAKANIWA.LANDMARKS[0]["id"]
        subset = [spec for spec in specs if spec["group"] == landmark_id]
        builder = RecordingBuilder()
        emitted = NAKANIWA.emit_specs_to_builder(builder, subset)
        self.assertEqual(emitted, subset)
        self.assertEqual(len(builder.calls), len(subset))

    def test_module_is_independent_and_uses_explicit_spanning_geometry(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import build_all_stages", source)
        self.assertNotIn("primitive_cube_add", source)
        self.assertNotIn("primitive_cylinder_add", source)
        self.assertIn("Connection Map", source)
        self.assertIn("add_beam", source)
        self.assertIn("add_sloped_panel", source)
        self.assertNotRegex(source, r"add_image|image_plane|billboard\s*\(")


if __name__ == "__main__":
    unittest.main()
