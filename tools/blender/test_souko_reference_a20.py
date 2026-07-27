#!/usr/bin/env python3
"""Dedicated tests for the isolated Souko A20 art rebuild."""

from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools/blender/stage_kits/souko_reference_a20.py"
SPEC = importlib.util.spec_from_file_location("souko_reference_a20", MODULE_PATH)
assert SPEC and SPEC.loader
souko = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(souko)


class RecordingBuilder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __getattr__(self, name: str):
        if not name.startswith("add_"):
            raise AttributeError(name)

        def record(**payload):
            self.calls.append((name, payload))

        return record


class SoukoReferenceA20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plans = {lod: souko.build_plan(lod) for lod in (0, 1, 2)}
        cls.metrics = {lod: souko.plan_metrics(cls.plans[lod]) for lod in (0, 1, 2)}

    def specs_for(self, lod: int, role: str):
        return [spec for spec in self.plans[lod].specs if spec["role"] == role]

    def test_canonical_truth_reference_and_dual_hero_identity_are_locked(self) -> None:
        self.assertEqual(souko.STAGE_ID, "souko")
        self.assertEqual(
            souko.CANONICAL_BOUNDS,
            {"min_x": -168.0, "max_x": 168.0, "min_z": -168.0, "max_z": 168.0},
        )
        self.assertEqual(
            souko.CANONICAL_PLAYER_SPAWNS,
            ((-156.0, 0.0, 0.0), (0.0, 0.0, -156.0),
             (156.0, 0.0, 0.0), (0.0, 0.0, 156.0)),
        )
        self.assertEqual(
            [landmark["id"] for landmark in souko.LANDMARKS],
            [souko.STACKHOUSE_ID, souko.CUSTOMS_ID],
        )
        self.assertEqual(
            [landmark["referenceName"] for landmark in souko.LANDMARKS],
            ["Rack-Bridge Storehouse", "Customs Sawtooth Terminal"],
        )
        reference = REPO_ROOT / souko.REFERENCE_PATH
        self.assertTrue(reference.is_file())
        self.assertEqual(
            hashlib.sha256(reference.read_bytes()).hexdigest(),
            souko.REFERENCE_SHA256,
        )
        self.assertTrue(souko.IMAGEGEN_REFERENCE_PATH.is_file())
        self.assertEqual(
            hashlib.sha256(souko.IMAGEGEN_REFERENCE_PATH.read_bytes()).hexdigest(),
            souko.IMAGEGEN_REFERENCE_SHA256,
        )
        self.assertEqual(souko.INDEPENDENT_A19_BASELINE_SCORE, 4.54)
        self.assertIn("a20", souko.REFERENCE_MATCH_VERSION)

    def test_primary_camera_is_fixed_1_65m_tight_and_reference_ordered(self) -> None:
        camera = souko.PRIMARY_CAMERA
        self.assertIs(camera, souko.PRIVATE_VIEWS[0])
        self.assertEqual(camera["eye"][1], 1.65)
        self.assertEqual(camera["lensMm"], 26.0)
        self.assertEqual(camera["sensorWidthMm"], 36.0)
        self.assertEqual(camera["frameOrder"], (souko.STACKHOUSE_ID, souko.CUSTOMS_ID))
        self.assertLessEqual(camera["skyMaxFraction"], 0.20)
        self.assertLessEqual(camera["roadMaxFraction"], 0.24)
        self.assertGreaterEqual(camera["heroHorizontalFillTarget"][0], 0.80)

        # Project canonical hero centres onto the horizontal camera-right vector.
        eye_x, _, eye_z = camera["eye"]
        target_x, _, target_z = camera["target"]
        dx, dz = target_x - eye_x, target_z - eye_z
        length = math.hypot(dx, dz)
        forward = (dx / length, dz / length)
        right = (forward[1], -forward[0])
        screen_x = {}
        half_fov = math.atan(camera["sensorWidthMm"] / (2.0 * camera["lensMm"]))
        for landmark in souko.LANDMARKS:
            vx, vz = landmark["cx"] - eye_x, landmark["cz"] - eye_z
            screen_x[landmark["id"]] = vx * right[0] + vz * right[1]
            forward_distance = vx * forward[0] + vz * forward[1]
            angle = abs(math.atan2(screen_x[landmark["id"]], forward_distance))
            self.assertLess(angle, half_fov)
        self.assertLess(screen_x[souko.STACKHOUSE_ID], screen_x[souko.CUSTOMS_ID])

        self.assertEqual(len(souko.PRIVATE_VIEWS), 8)
        self.assertEqual(len({view["id"] for view in souko.PRIVATE_VIEWS}), 8)
        for view in souko.PRIVATE_VIEWS:
            self.assertEqual(view["eye"][1], 1.65)
            self.assertGreaterEqual(view["lensMm"], 24.0)
            self.assertLessEqual(view["lensMm"], 32.0)

    def test_lods_are_monotonic_deterministic_and_within_webgl_budgets(self) -> None:
        counts = [self.metrics[lod]["specCount"] for lod in (0, 1, 2)]
        triangles = [self.metrics[lod]["estimatedTriangles"] for lod in (0, 1, 2)]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(triangles[0], triangles[1])
        self.assertGreater(triangles[1], triangles[2])
        for lod in (0, 1, 2):
            self.assertLessEqual(self.metrics[lod]["specCount"], souko.LOD_API[lod]["maxSpecs"])
            self.assertLessEqual(
                self.metrics[lod]["estimatedTriangles"],
                souko.LOD_API[lod]["maxEstimatedTriangles"],
            )
            self.assertLessEqual(self.metrics[lod]["materialCount"], 16)
            rebuilt = souko.build_plan(lod)
            self.assertEqual(rebuilt.specs, self.plans[lod].specs)
            self.assertEqual(rebuilt.connections, self.plans[lod].connections)

    def test_stackhouse_is_completed_occupied_and_has_deep_bridge_interior(self) -> None:
        for lod in (0, 1, 2):
            self.assertEqual(len(self.specs_for(lod, "stackhouse-completed-tower-envelope")), 4)
            self.assertEqual(len(self.specs_for(lod, "stackhouse-roof-cap")), 4)
            expected_bridges = 2 if lod < 2 else 1
            self.assertEqual(
                len(self.specs_for(lod, "stackhouse-deep-transfer-bridge-floor")),
                expected_bridges,
            )
        bridges = self.specs_for(0, "stackhouse-deep-transfer-bridge-floor")
        self.assertGreater(max(bridge["w"] for bridge in bridges), 80.0)
        self.assertGreaterEqual(max(bridge["d"] for bridge in bridges), 10.0)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-open-interior-floor")), 4)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-rack-upright")), 18)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-rack-depth-tie")), 30)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-deep-interior-cargo")), 50)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-occupied-window-band")), 30)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-rust-runoff-streak")), 16)
        self.assertGreaterEqual(
            len(self.specs_for(0, "stackhouse-primary-west-window-recess")), 20,
        )
        self.assertEqual(
            len(self.specs_for(0, "stackhouse-primary-crown-bridge-floor")), 1,
        )
        self.assertGreaterEqual(
            len(self.specs_for(0, "stackhouse-undercroft-container")), 6,
        )
        self.assertGreaterEqual(len(self.specs_for(0, "industrial-stair-tread")), 30)
        stack_specs = [spec for spec in self.plans[0].specs
                       if spec["group"] == souko.STACKHOUSE_ID]
        self.assertGreater(max(souko.spec_bounds(spec)[4] for spec in stack_specs), 95.0)

    def test_a20_stackhouse_has_macro_cavities_connected_galleries_and_crown(self) -> None:
        roles = self.metrics[0]["roles"]
        self.assertEqual(roles["a20-stackhouse-west-rack-cavity"], 3)
        self.assertGreaterEqual(roles["a20-stackhouse-west-rack-floor"], 18)
        self.assertEqual(roles["a20-stackhouse-grounded-shoulder"], 4)
        self.assertEqual(roles["a20-stackhouse-flying-buttress"], 4)
        self.assertEqual(roles["a20-stackhouse-west-maintenance-gallery"], 2)
        self.assertEqual(roles["a20-stackhouse-north-cantilever-control-room"], 4)
        self.assertEqual(roles["a20-stackhouse-crown-process-drum"], 4)
        self.assertEqual(roles["a20-stackhouse-crown-antenna"], 4)
        self.assertEqual(roles["a20-stackhouse-rack-aisle-floor"], 1)
        self.assertEqual(roles["a20-stackhouse-rack-aisle-portal-upright"], 8)
        self.assertEqual(roles["a20-stackhouse-rack-aisle-portal-header"], 4)
        self.assertEqual(roles["a20-stackhouse-rack-aisle-overhead-brace"], 4)
        self.assertEqual(roles["a20-stackhouse-rack-aisle-service-catwalk"], 1)
        self.assertGreaterEqual(roles["a20-stackhouse-rack-aisle-side-shelf"], 18)
        self.assertGreaterEqual(roles["a20-stackhouse-rack-aisle-loaded-cargo"], 12)
        self.assertGreaterEqual(roles["industrial-stair-tread"], 50)

    def test_customs_has_exactly_four_full_depth_glazed_sawteeth(self) -> None:
        roles = (
            "customs-sawtooth-roof",
            "customs-sawtooth-glazed-face",
            "customs-sawtooth-triangular-glass-gable",
            "customs-sawtooth-occupied-bay-volume",
        )
        for lod in (0, 1, 2):
            for role in roles:
                self.assertEqual(len(self.specs_for(lod, role)), 4, (lod, role))
            for role in ("customs-sawtooth-roof", "customs-sawtooth-glazed-face"):
                for panel in self.specs_for(lod, role):
                    z_values = [corner[2] for corner in panel["corners"]]
                    self.assertGreaterEqual(max(z_values) - min(z_values), 70.0)
        self.assertGreaterEqual(len(self.specs_for(0, "customs-sawtooth-internal-truss")), 56)
        self.assertGreaterEqual(len(self.specs_for(0, "customs-sawtooth-long-purlin")), 16)
        self.assertEqual(len(self.specs_for(0, "customs-control-tower-glazing")), 1)
        self.assertEqual(len(self.specs_for(0, "customs-industrial-chimney")), 2)
        self.assertGreaterEqual(len(self.specs_for(0, "customs-loading-door")), 8)
        self.assertEqual(
            len(self.specs_for(0, "customs-primary-rear-sawtooth-gable")), 4,
        )
        self.assertGreaterEqual(
            len(self.specs_for(0, "customs-primary-rear-occupied-window")), 12,
        )
        self.assertEqual(
            len(self.specs_for(0, "customs-primary-rear-maintenance-balcony")), 2,
        )

    def test_a20_customs_loading_face_is_deep_asymmetric_and_operational(self) -> None:
        roles = self.metrics[0]["roles"]
        self.assertEqual(roles["a20-customs-deep-loading-cavity"], 4)
        self.assertEqual(roles["a20-customs-warm-loading-interior"], 4)
        self.assertEqual(roles["a20-customs-projecting-loading-canopy"], 4)
        self.assertEqual(roles["a20-customs-rear-structural-pilaster"], 5)
        self.assertEqual(roles["a20-customs-upper-occupied-window"], 4)
        self.assertEqual(roles["a20-customs-rear-maintenance-catwalk"], 1)
        self.assertEqual(roles["a20-customs-sawtooth-ridge-lantern"], 4)
        self.assertEqual(roles["a20-customs-roof-exhaust"], 4)
        self.assertEqual(roles["a20-customs-monumental-machine-hall-reveal"], 2)
        self.assertEqual(roles["a20-customs-monumental-machine-hall-glass"], 2)
        self.assertEqual(roles["a20-customs-machine-hall-x-truss"], 4)
        self.assertEqual(roles["a20-customs-grounded-process-riser"], 2)
        canopies = self.specs_for(0, "a20-customs-projecting-loading-canopy")
        self.assertGreater(max(spec["d"] for spec in canopies),
                           min(spec["d"] for spec in canopies))

    def test_foreground_and_horizon_form_continuous_real_geometry_depth(self) -> None:
        roles = self.metrics[0]["roles"]
        layers = self.metrics[0]["layers"]
        self.assertGreaterEqual(layers["near"], 450)
        self.assertGreaterEqual(layers["mid"], 750)
        self.assertGreaterEqual(layers["far"], 100)
        required = (
            "foreground-loading-shed-roof", "foreground-loading-bay-door",
            "pallet-slat", "forklift-body", "cargo-container-shell",
            "quay-cargo-rail", "quay-slab", "quay-mooring-bollard",
            "cargo-ship-hull", "port-crane-huge-boom", "real-sea-geometry",
            "bonded-warehouse-shell", "wet-diagonal-bonded-service-road",
            "inter-landmark-transfer-floor", "service-road-retaining-block",
        )
        for role in required:
            self.assertGreater(roles.get(role, 0), 0, role)
        self.assertGreaterEqual(roles["port-crane-huge-boom"], 3)
        for role in ("real-sea-geometry", "cargo-ship-hull", "port-crane-huge-boom"):
            self.assertTrue(all(spec["outsidePlayable"] for spec in self.specs_for(0, role)))

    def test_a20_working_quay_harbor_and_story_clusters_are_dense(self) -> None:
        roles = self.metrics[0]["roles"]
        self.assertEqual(roles["a20-roadside-tactical-cover"], 8)
        self.assertEqual(roles["a20-quay-oil-and-tire-streak"], 14)
        self.assertEqual(roles["a20-quay-hazard-panel"], 7)
        self.assertEqual(roles["a20-quay-rubber-fender"], 8)
        self.assertEqual(roles["a20-quay-heavy-bollard"], 8)
        self.assertEqual(roles["a20-cargo-ship-mooring-line"], 4)
        self.assertEqual(roles["a20-port-crane-hook-block"], 3)
        self.assertEqual(roles["a20-port-crane-hook"], 3)
        self.assertEqual(roles["a20-cargo-ship-deck-vent"], 3)
        self.assertEqual(roles["a20-harbor-horizon-chimney"], 6)
        self.assertGreaterEqual(roles["a20-quay-fuel-service-tank"], 3)
        self.assertEqual(roles["a20-fixed-camera-apron-cover"], 4)
        self.assertGreaterEqual(self.metrics[0]["layers"]["near"], 1000)
        self.assertGreaterEqual(self.metrics[0]["layers"]["far"], 400)

    def test_materials_encode_wet_rust_roughness_and_relief(self) -> None:
        self.assertEqual(len(souko.MATERIALS), 16)
        self.assertTrue(souko.MATERIALS["wet_asphalt"]["wetVariation"])
        self.assertLess(souko.MATERIALS["puddle_water"]["roughness"], 0.10)
        self.assertLess(souko.MATERIALS["sea_water"]["roughness"], 0.16)
        self.assertTrue(souko.MATERIALS["weathered_zinc"]["rustMask"])
        self.assertTrue(souko.MATERIALS["structural_steel"]["rustMask"])
        self.assertTrue(souko.MATERIALS["old_concrete"]["stains"])
        self.assertTrue(souko.MATERIALS["red_brick"]["stains"])
        self.assertGreater(souko.MATERIALS["rust"]["noise"], 0.20)

    def test_connections_bounds_routes_and_spawns_are_valid(self) -> None:
        for lod, plan in self.plans.items():
            names = {spec["name"] for spec in plan.specs}
            self.assertGreater(len(plan.connections), 90)
            for connection in plan.connections:
                self.assertIn(connection["parent"], names, (lod, connection))
                self.assertIn(connection["child"], names, (lod, connection))
                self.assertGreaterEqual(connection["overlapM"], souko.MIN_CONTACT_OVERLAP_M)
            for spec in plan.specs:
                bounds = souko.spec_bounds(spec)
                self.assertTrue(all(math.isfinite(value) for value in bounds))
                self.assertLess(bounds[0], bounds[3])
                self.assertLess(bounds[1], bounds[4])
                self.assertLess(bounds[2], bounds[5])
            self.assertEqual(souko.route_intrusions(plan), [])
            self.assertEqual(souko.spawn_intrusions(plan), [])

    def test_emitter_covers_every_spec_without_blender_import(self) -> None:
        builder = RecordingBuilder()
        souko.emit_plan(builder, self.plans[2])
        self.assertEqual(len(builder.calls), len(self.plans[2].specs))
        self.assertEqual(
            {payload["name"] for _, payload in builder.calls},
            {spec["name"] for spec in self.plans[2].specs},
        )
        integration_materials = set(souko.DEFAULT_INTEGRATION_MATERIAL_MAP.values())
        self.assertTrue(all(payload["material"] in integration_materials
                            for _, payload in builder.calls))

    def test_producer_status_is_explicit_no_ship_pending_independent_review(self) -> None:
        scorecard = souko.producer_provisional_scorecard()
        self.assertEqual(tuple(scorecard["fixedCategoryOrder"]), souko.FIXED_SCORE_CATEGORIES)
        self.assertEqual(
            tuple(item["category"] for item in scorecard["items"]),
            souko.FIXED_SCORE_CATEGORIES,
        )
        self.assertEqual(len(scorecard["items"]), 10)
        self.assertTrue(scorecard["producerProvisional"])
        self.assertEqual(scorecard["verdict"], "NO-SHIP")
        self.assertFalse(scorecard["formalReferencePassClaimed"])
        self.assertTrue(scorecard["independentReviewRequired"])
        self.assertFalse(scorecard["formalPassGate"]["currentlyMeetsNumericGate"])

    def test_module_is_isolated_and_contains_no_shortcut_or_live_blender_calls(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden = (
            "import build_all_stages", "from build_all_stages",
            "import souko_reference_a18_r8", "from souko_reference_a18_r8",
            "import bpy", "primitive_cube_add", "primitive_cylinder_add",
            "bpy.ops.mesh.", "ShaderNodeTexImage", "image_as_planes",
            "runtime-background-image", "billboard-matte",
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)
        self.assertIn("/private/tmp/hibana-blender/", source)
        self.assertNotIn("public/assets", source)
        self.assertNotIn("souko_reference_a19", source)
        self.assertNotIn("a19-souko-macro-v1", source)


if __name__ == "__main__":
    unittest.main()
