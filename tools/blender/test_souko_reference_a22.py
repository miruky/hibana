#!/usr/bin/env python3
"""Private production gates for the independent Souko A22 rebuild."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parent / "stage_kits/souko_reference_a22.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


A22 = _load_module("hibana_test_souko_a22", MODULE_PATH)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestSoukoA22ProductionPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plans = {lod: A22.build_plan(lod) for lod in (0, 1, 2)}
        cls.metrics = {
            lod: A22.plan_metrics(plan) for lod, plan in cls.plans.items()
        }

    def test_reference_and_controlling_reviews_are_hash_locked(self) -> None:
        self.assertEqual(
            _sha256(A22.IMAGEGEN_REFERENCE_PATH),
            A22.IMAGEGEN_REFERENCE_SHA256,
        )
        self.assertEqual(
            _sha256(A22.A21_SCORECARD_PATH),
            A22.A21_INDEPENDENT_SCORECARD_SHA256,
        )
        scorecard = json.loads(
            A22.A21_SCORECARD_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(scorecard["verdict"], "NO-SHIP")
        self.assertLess(float(scorecard["arithmeticMean"]), 7.0)
        self.assertEqual(
            _sha256(A22.A22_CONTROLLING_SCORECARD_PATH),
            A22.A22_CONTROLLING_SCORECARD_SHA256,
        )
        controlling = json.loads(
            A22.A22_CONTROLLING_SCORECARD_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(controlling["verdict"], "PASS")
        self.assertFalse(controlling["genericBlockout"])
        self.assertEqual(
            controlling["evidence"]["candidate"]["sha256"],
            "0d8d5e497936e2476f5cf73b78c4d5eb79a3ed7a944b769d48318a63a5ca2f3e",
        )
        self.assertEqual(float(controlling["arithmetic"]["average"]), 8.0)
        self.assertEqual(float(controlling["arithmetic"]["minimum"]), 7.2)

    def test_canonical_layout_and_two_landmark_identities_are_unchanged(self) -> None:
        self.assertEqual(A22.CANONICAL_BOUNDS, {
            "min_x": -168.0, "max_x": 168.0,
            "min_z": -168.0, "max_z": 168.0,
        })
        self.assertEqual(A22.CANONICAL_PLAYER_SPAWNS, (
            (-156.0, 0.0, 0.0),
            (0.0, 0.0, -156.0),
            (156.0, 0.0, 0.0),
            (0.0, 0.0, 156.0),
        ))
        self.assertEqual(
            [item["id"] for item in A22.LANDMARKS],
            [A22.STACKHOUSE_ID, A22.CUSTOMS_ID],
        )
        self.assertEqual(A22.LANDMARKS[0]["entrance"], (28.0, 96.0))
        self.assertEqual(A22.LANDMARKS[1]["entrance"], (-68.0, -28.0))
        for metrics in self.metrics.values():
            self.assertEqual(
                metrics["landmarkGroups"],
                sorted((A22.STACKHOUSE_ID, A22.CUSTOMS_ID)),
            )

    def test_three_lods_hit_real_evaluated_triangle_bands(self) -> None:
        counts = []
        for lod in (0, 1, 2):
            target = A22.LOD_TARGETS[lod]
            triangle_count = self.metrics[lod]["estimatedTriangles"]
            counts.append(triangle_count)
            self.assertGreaterEqual(triangle_count, target["minTriangles"])
            self.assertLessEqual(triangle_count, target["maxTriangles"])
            self.assertEqual(
                A22.GLB_BUDGETS[lod]["minTriangles"],
                target["minTriangles"],
            )
            self.assertEqual(
                A22.GLB_BUDGETS[lod]["maxTriangles"],
                target["maxTriangles"],
            )
        self.assertGreater(counts[0], counts[1] * 2.4)
        self.assertGreater(counts[1], counts[2] * 3.0)

    def test_plan_is_deterministic(self) -> None:
        plan = A22.build_plan(2)
        serial = json.dumps(
            {"specs": plan.specs, "connections": plan.connections},
            sort_keys=True,
        )
        baseline = json.dumps(
            {
                "specs": self.plans[2].specs,
                "connections": self.plans[2].connections,
            },
            sort_keys=True,
        )
        self.assertEqual(
            hashlib.sha256(serial.encode()).hexdigest(),
            hashlib.sha256(baseline.encode()).hexdigest(),
        )

    def test_material_budget_is_twelve_and_has_restrained_safety_yellow(self) -> None:
        self.assertEqual(len(A22.MATERIALS), 12)
        for metrics in self.metrics.values():
            self.assertEqual(metrics["materialCount"], 12)
        safety = A22.MATERIALS["safety_orange"]["color"]
        self.assertLess(safety[0] - safety[1], 0.12)
        self.assertGreater(safety[1], safety[2] * 4.0)
        for recipe in A22.MATERIALS.values():
            self.assertIn("roughness", recipe)
            self.assertIn("metallic", recipe)
            self.assertIn("textureScaleM", recipe)
        asphalt_wear_fraction = sum(
            A22._wet_asphalt_edge_wear(x, y)
            for y in range(128) for x in range(128)
        ) / (128 * 128)
        self.assertGreater(asphalt_wear_fraction, 0.045)
        self.assertLess(asphalt_wear_fraction, 0.055)

    def test_role_specific_profiles_are_baked_not_modifier_claims(self) -> None:
        for plan in self.plans.values():
            for spec in plan.specs:
                if spec["kind"] == "chamfer_box":
                    low, high = A22.CHAMFER_BANDS_M[spec["chamferBand"]]
                    self.assertTrue(low <= spec["bevelM"] <= high)
                    self.assertTrue(spec["bakedProfile"])
                if spec["kind"] == "pipe":
                    low, high = A22.CHAMFER_BANDS_M["equipment"]
                    self.assertTrue(low <= spec["radius"] <= high)
                    self.assertTrue(spec["bakedProfile"])
            for band in ("hero", "secondary", "equipment"):
                self.assertGreater(
                    A22.plan_metrics(plan)["profileBands"].get(band, 0), 0,
                )
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(".modifiers.new(", source)
        self.assertNotIn("bevel.width = 0.045", source)
        self.assertNotIn("souko_reference_a21.py", source)

    def test_baked_chamfer_mesh_is_44_triangles_and_outward(self) -> None:
        plan = A22.SpecPlan(0)
        plan.chamfer_box(
            "test-hero-pier", "old_concrete", "test",
            2.0, 3.0, 5.0, 4.0, 6.0, 8.0, 0.18,
            band="hero",
        )
        batch = {"vertices": [], "faces": []}
        A22._append_chamfer_box_mesh(batch, plan.specs[0])
        self.assertEqual(len(batch["vertices"]), 24)
        self.assertEqual(len(batch["faces"]), 26)
        self.assertEqual(
            sum(max(0, len(face) - 2) for face in batch["faces"]), 44,
        )
        centre = A22._runtime_to_blender((2.0, 3.0, 5.0))
        for face in batch["faces"]:
            a, b, c = (batch["vertices"][index] for index in face[:3])
            normal = (
                (b[1] - a[1]) * (c[2] - a[2])
                - (b[2] - a[2]) * (c[1] - a[1]),
                (b[2] - a[2]) * (c[0] - a[0])
                - (b[0] - a[0]) * (c[2] - a[2]),
                (b[0] - a[0]) * (c[1] - a[1])
                - (b[1] - a[1]) * (c[0] - a[0]),
            )
            face_centre = tuple(
                sum(batch["vertices"][index][axis] for index in face) / len(face)
                for axis in range(3)
            )
            outward = sum(
                normal[axis] * (face_centre[axis] - centre[axis])
                for axis in range(3)
            )
            self.assertGreater(outward, 0.0)

    def test_endpoint_pipe_has_round_exported_profile(self) -> None:
        plan = A22.SpecPlan(0)
        plan.pipe(
            "test-rail", "safety_orange", "test",
            (0.0, 1.0, 0.0), (8.0, 5.0, 3.0), 0.025, 8,
        )
        batch = {"vertices": [], "faces": []}
        A22._append_pipe_mesh(batch, plan.specs[0])
        self.assertEqual(len(batch["vertices"]), 16)
        self.assertEqual(A22.estimated_triangles(plan.specs[0]), 28)
        self.assertEqual(
            sum(max(0, len(face) - 2) for face in batch["faces"]), 28,
        )
        start, end = plan.specs[0]["start"], plan.specs[0]["end"]
        self.assertGreater(math.dist(start, end), 9.0)

    def test_stackhouse_is_broad_multilevel_loaded_rack_fortress(self) -> None:
        plan = self.plans[0]
        roles = A22.plan_metrics(plan)["roles"]
        self.assertEqual(roles["a22-stackhouse-unequal-process-core"], 4)
        self.assertEqual(roles["a22-stackhouse-transfer-bridge-floor"], 2)
        self.assertGreaterEqual(roles["a22-stackhouse-hero-pier"], 14)
        self.assertGreaterEqual(roles["a22-stackhouse-rack-deck-edge"], 12)
        self.assertGreaterEqual(roles["a22-stackhouse-loaded-rack-cargo"], 300)
        self.assertGreaterEqual(roles["a22-stackhouse-deep-cross-deck"], 90)
        bounds = [
            A22.spec_bounds(spec) for spec in plan.specs
            if spec["group"] == A22.STACKHOUSE_ID
        ]
        self.assertGreater(max(item[3] for item in bounds) - min(item[0] for item in bounds), 100)
        self.assertGreater(max(item[4] for item in bounds), 120)

    def test_customs_is_long_sawtooth_hall_with_real_interior_and_tower(self) -> None:
        roles = self.metrics[0]["roles"]
        self.assertEqual(
            roles["a22-i29c-customs-full-depth-sawtooth-glazing"], 4,
        )
        self.assertEqual(
            roles["a22-i29c-customs-full-depth-sawtooth-roof"], 8,
        )
        self.assertEqual(
            roles["a22-i29c-customs-deep-bay-frame-leg"], 30,
        )
        self.assertEqual(
            roles["a22-i29c-customs-sawtooth-frame-rafter"], 24,
        )
        self.assertEqual(
            roles["a22-i29c-customs-deep-machine-line"], 8,
        )
        self.assertEqual(
            roles["a22-i29c-customs-deep-conveyor-bed"], 4,
        )
        self.assertEqual(
            roles["a22-i29c-customs-integrated-control-core"], 1,
        )
        self.assertEqual(
            roles["a22-i29c-customs-integrated-control-cab"], 1,
        )
        customs_bounds = [
            A22.spec_bounds(spec)
            for spec in self.plans[0].specs
            if spec["group"] == A22.CUSTOMS_ID
        ]
        self.assertGreater(
            max(bounds[3] for bounds in customs_bounds)
            - min(bounds[0] for bounds in customs_bounds),
            105.0,
        )
        self.assertGreater(
            max(bounds[5] for bounds in customs_bounds)
            - min(bounds[2] for bounds in customs_bounds),
            110.0,
        )
        self.assertGreater(max(bounds[4] for bounds in customs_bounds), 90.0)

    def test_checkpoint_port_city_ship_and_maintenance_are_occupied(self) -> None:
        roles = self.metrics[0]["roles"]
        required = {
            "a22-checkpoint-occupied-booth": 2,
            "a22-checkpoint-worker-body": 8,
            "a22-port-city-tall-building": 40,
            "a22-harbour-crane-boom": 3,
            "a22-operational-forklift-body": 6,
            "a22-operational-maintenance-truck": 4,
            "a22-quay-maintenance-equipment": 24,
            "a22-ship-loaded-container": 20,
            "a22-route-worker-body": 12,
            "a22-route-wet-reflection-puddle": 10,
        }
        for role, minimum in required.items():
            self.assertGreaterEqual(roles[role], minimum, role)

    def test_foreground_relief_is_nonblocking_and_lod_reduced(self) -> None:
        expected = {
            0: {
                "a22-route-foreground-loading-bay-long-line": 4,
                "a22-route-foreground-loading-bay-divider": 22,
                "a22-route-foreground-faded-hazard-hatch": 22,
                "a22-route-foreground-slab-expansion-joint": 5,
                "a22-route-foreground-broken-slab-crack": 16,
                "a22-route-foreground-readable-lane-edge": 2,
                "a22-route-forklift-readable-exclusion-box-long": 4,
                "a22-route-forklift-readable-exclusion-box-short": 4,
                "a22-route-near-camera-segmented-drain-line": 40,
            },
            1: {
                "a22-route-foreground-loading-bay-long-line": 4,
                "a22-route-foreground-loading-bay-divider": 8,
                "a22-route-foreground-faded-hazard-hatch": 8,
                "a22-route-foreground-slab-expansion-joint": 3,
                "a22-route-foreground-broken-slab-crack": 8,
                "a22-route-foreground-readable-lane-edge": 0,
                "a22-route-forklift-readable-exclusion-box-long": 0,
                "a22-route-forklift-readable-exclusion-box-short": 0,
                "a22-route-near-camera-segmented-drain-line": 0,
            },
            2: {
                "a22-route-foreground-loading-bay-long-line": 0,
                "a22-route-foreground-loading-bay-divider": 0,
                "a22-route-foreground-faded-hazard-hatch": 0,
                "a22-route-foreground-slab-expansion-joint": 0,
                "a22-route-foreground-broken-slab-crack": 0,
                "a22-route-foreground-readable-lane-edge": 0,
                "a22-route-forklift-readable-exclusion-box-long": 0,
                "a22-route-forklift-readable-exclusion-box-short": 0,
                "a22-route-near-camera-segmented-drain-line": 0,
            },
        }
        relief_roles = set(expected[0])
        for lod, plan in self.plans.items():
            roles = self.metrics[lod]["roles"]
            for role, count in expected[lod].items():
                self.assertEqual(roles.get(role, 0), count, (lod, role))
            for spec in plan.specs:
                if spec["role"] in relief_roles:
                    self.assertFalse(spec["blocksGameplay"], spec["name"])
                    if (
                        spec["role"]
                        == "a22-route-foreground-broken-slab-crack"
                    ):
                        self.assertLessEqual(spec["radius"], 0.020)

    def test_human_vehicle_and_far_occupation_p0_is_present(self) -> None:
        roles = self.metrics[0]["roles"]
        expected = {
            "a22-route-worker-gloved-hand": 6,
            "a22-route-worker-carried-inspection-case": 1,
            "a22-route-worker-carried-service-tool": 2,
            "a22-route-worker-reflective-vest-back": 14,
            "a22-forklift-readable-control-console": 9,
            "a22-forklift-readable-steering-column": 9,
            "a22-forklift-readable-steering-grip": 9,
            "a22-forklift-seated-operator-torso": 3,
            "a22-forklift-seated-operator-head": 3,
            "a22-forklift-seated-operator-helmet": 3,
            "a22-forklift-seated-operator-vest": 3,
            "a22-forklift-seated-operator-control-arm": 6,
            "a22-far-district-occupied-light-strip": 8,
            "a22-far-district-readable-bay-sign": 4,
            "a22-central-skyline-occupied-control-light": 5,
        }
        for role, count in expected.items():
            self.assertEqual(roles.get(role, 0), count, role)
        p0_roles = set(expected)
        for spec in self.plans[0].specs:
            if spec["role"] in p0_roles:
                self.assertFalse(spec["blocksGameplay"], spec["name"])

    def test_independent_p0_mass_ship_and_depth_rebuild_is_structural(self) -> None:
        roles = self.metrics[0]["roles"]
        expected = {
            "a22-p0-stackhouse-monumental-bastion": 2,
            "a22-p0-stackhouse-bastion-crown-house": 2,
            "a22-i29c-customs-continuous-hall-foundation": 1,
            "a22-i29c-customs-continuous-side-shoulder": 2,
            "a22-i29c-customs-integrated-control-core": 1,
            "a22-p0-primary-camera-quay-water": 1,
            "a22-p0-primary-camera-heavy-quay-wall": 1,
            "a22-p0-primary-camera-ship-near-hull": 1,
            "a22-p0-primary-camera-ship-far-hull": 1,
            "a22-p0-primary-camera-ship-bow": 1,
            "a22-p0-central-layered-port-mass": 4,
            "a22-route-p0-grounded-jersey-barrier": 8,
            "a22-route-p0-grounded-cargo-pallet": 4,
            "a22-route-p0-staged-loaded-crate": 4,
        }
        for role, count in expected.items():
            self.assertEqual(roles[role], count, role)
        structural_kinds = {
            "beam", "box", "chamfer_box", "cylinder", "panel", "pipe",
            "round_member",
        }
        for spec in self.plans[0].specs:
            if spec["role"] in expected:
                self.assertIn(spec["kind"], structural_kinds)
                self.assertFalse(spec["blocksGameplay"], spec["name"])

    def test_iteration23_fixed_camera_keeps_quay_ship_and_heroes_safe(self) -> None:
        projected = {
            key: A22.camera_horizontal_ndc(A22.PRIMARY_CAMERA, point)
            for key, point in A22.PRIMARY_CAMERA_PROJECTION_POINTS.items()
        }
        self.assertLess(projected["stackhouseCentre"], -0.35)
        self.assertTrue(0.10 <= projected["customsCentre"] <= 0.55)
        self.assertLessEqual(abs(projected["shipHull"]), 0.75)
        self.assertLessEqual(abs(projected["quayWater"]), 0.75)
        self.assertLess(
            projected["stackhouseCentre"],
            projected["customsCentre"],
        )
        self.assertLess(projected["customsCentre"], projected["shipHull"])
        self.assertLess(projected["quayWater"], projected["shipHull"])
        ship_region = [
            A22.camera_ndc(A22.PRIMARY_CAMERA, point)
            for point in A22.PRIMARY_CAMERA_SCREEN_REGIONS["shipHull"]
        ]
        ship_x = [
            max(-1.0, min(1.0, point[0]))
            for point in ship_region
        ]
        self.assertGreaterEqual(min(ship_x), 0.50)
        self.assertGreaterEqual(max(ship_x) - min(ship_x), 0.30)
        self.assertLessEqual(max(ship_x) - min(ship_x), 0.50)
        water_region = [
            A22.camera_ndc(A22.PRIMARY_CAMERA, point)
            for point in A22.PRIMARY_CAMERA_SCREEN_REGIONS["quayWater"]
        ]
        clipped_water_x = [
            max(-1.0, min(1.0, point[0]))
            for point in water_region
        ]
        self.assertGreaterEqual(
            max(clipped_water_x) - min(clipped_water_x),
            0.40,
        )
        water_y = [point[1] for point in water_region]
        self.assertGreaterEqual(max(water_y) - min(water_y), 0.10)
        self.assertLessEqual(max(water_y) - min(water_y), 0.25)
        self.assertEqual(A22.PRIMARY_CAMERA["lensMm"], 21.0)
        self.assertEqual(A22.PRIMARY_CAMERA["eye"][1], A22.PLAYER_EYE_M)

    def test_visual_water_and_shore_aabbs_never_enter_canonical_roads(
        self,
    ) -> None:
        clearance_m = 2.0
        for lod, plan in self.plans.items():
            self.assertEqual(
                A22.shore_route_intrusions(plan),
                [],
                f"LOD{lod}",
            )
            shore_specs = [
                spec
                for spec in plan.specs
                if spec["role"] in A22.PRIMARY_SHORE_ROLES
            ]
            self.assertGreater(len(shore_specs), 0)
            for spec in shore_specs:
                bounds = A22.spec_bounds(spec)
                for road_record in A22.CANONICAL_ROADS:
                    road = road_record["bounds"]
                    overlaps = (
                        bounds[0] < road["maxX"] + clearance_m
                        and bounds[3] > road["minX"] - clearance_m
                        and bounds[2] < road["maxZ"] + clearance_m
                        and bounds[5] > road["minZ"] - clearance_m
                    )
                    self.assertFalse(
                        overlaps,
                        f"{spec['name']} -> {road_record['id']}",
                    )

    def test_iteration29c_replaces_only_customs_with_connected_macro_hall(
        self,
    ) -> None:
        plan = self.plans[0]
        roles = self.metrics[0]["roles"]
        expected = {
            "a22-i23-stackhouse-supported-void-pylon": 4,
            "a22-i23-stackhouse-occupied-partial-floor": 4,
            "a22-i23-stackhouse-heavy-rack-bridge-floor": 1,
            "a22-i23-stackhouse-rack-bridge-web": 16,
            "a22-i23-stackhouse-readable-stair-tread": 14,
            "a22-i23-quay-crane-grounded-foot": 4,
            "a22-i23-quay-crane-heavy-tower-leg": 4,
            "a22-i23-quay-crane-boom-web": 8,
            "a22-i23-ship-camera-side-hull-rub-rail": 3,
            "a22-i23-ship-readable-forward-deckhouse": 1,
            "a22-i23-ship-readable-forward-bridge": 1,
            "a22-i23-ship-readable-forward-mast": 1,
            "a22-i23-ship-readable-cargo-boom": 1,
            "a22-i23-foreground-loading-slab": 1,
            "a22-i23-foreground-grounded-pallet": 4,
            "a22-i23-foreground-loaded-cargo": 4,
            "a22-i23-far-port-warehouse-mass": 6,
            "a22-i23-far-port-service-stack": 3,
            "a22-i28-stackhouse-mechanical-cap-seated-plinth": 1,
            "a22-i28-far-port-supported-process-neck": 2,
            "a22-i28-stackhouse-occupied-task-strip": 2,
            "a22-i28-quay-tidal-contact-band": 1,
            "a22-i28-quay-readable-coiled-mooring-rope": 16,
            "a22-i28-quay-edge-grounded-pallet": 1,
            "a22-i28-quay-edge-loaded-service-crate": 2,
            "a22-i28-quay-edge-grounded-service-barrel": 3,
            "a22-i28-ship-camera-side-waterline-contact": 1,
            "a22-i28-ship-camera-side-upper-sheer-band": 1,
            "a22-i28-ship-camera-side-rust-runoff": 3,
            "a22-i28-ship-camera-side-deck-attachment-shadow": 1,
            "a22-p0-quay-grounded-cargo-pallet": 4,
            "a22-p0-quay-staged-maintenance-crate": 8,
            "a22-p0-quay-grounded-service-barrel": 3,
            "a22-i29c-customs-continuous-hall-foundation": 1,
            "a22-i29c-customs-continuous-side-shoulder": 2,
            "a22-i29c-customs-continuous-front-spine": 1,
            "a22-i29c-customs-continuous-rear-spine": 1,
            "a22-i29c-customs-monumental-front-gable": 4,
            "a22-i29c-customs-deep-bay-portal": 4,
            "a22-i29c-customs-integrated-control-core": 1,
            "a22-i29c-customs-tower-hall-transfer-deck": 1,
            "a22-i29c-customs-interhero-bridge-abutment": 1,
        }
        for role, count in expected.items():
            self.assertEqual(roles.get(role, 0), count, role)
        self.assertEqual(roles.get("a22-stackhouse-cargo-band", 0), 0)
        orange_count = self.metrics[0]["materials"]["safety_orange"]
        self.assertLess(orange_count / self.metrics[0]["specCount"], 0.09)
        for spec in plan.specs:
            if spec["role"] == "a22-rounded-guardrail":
                self.assertEqual(spec["material"], "weathered_zinc")
            if spec["role"].startswith("a22-i29c-customs-"):
                self.assertFalse(spec["blocksGameplay"], spec["name"])

        # The active candidate begins from Iteration-28 and changes no
        # non-Customs spec.  This also proves that the rejected 29-B loading
        # box and quay tank/coil massing did not leak into 29-C.
        baseline = A22._build_iteration28_baseline(0)
        baseline_frozen = [
            spec for spec in baseline.specs
            if spec["group"] != A22.CUSTOMS_ID
        ]
        candidate_frozen = [
            spec for spec in plan.specs
            if spec["group"] != A22.CUSTOMS_ID
        ]
        self.assertEqual(candidate_frozen, baseline_frozen)
        self.assertFalse(
            any(
                spec["role"].startswith(("a22-i29a-", "a22-i29b-"))
                for spec in plan.specs
            ),
        )
        for lod in (1, 2):
            self.assertFalse(
                any(
                    spec["role"].startswith(("a22-i29a-", "a22-i29b-"))
                    for spec in self.plans[lod].specs
                ),
                f"LOD{lod}",
            )

        screen_x = {
            key: (
                A22.camera_ndc(A22.PRIMARY_CAMERA, point)[0] + 1.0
            ) * 0.5
            for key, point in A22.ITERATION29C_CUSTOMS_SCREEN_POINTS.items()
        }
        self.assertTrue(0.54 <= screen_x["nearInner"] <= 0.57)
        self.assertTrue(0.88 <= screen_x["farOuter"] <= 0.91)

        by_name = {spec["name"]: spec for spec in plan.specs}
        connection_count = 0
        for connection in plan.connections:
            if not connection["note"].startswith("Iteration29-C:"):
                continue
            connection_count += 1
            parent_bounds = A22.spec_bounds(by_name[connection["parent"]])
            child_bounds = A22.spec_bounds(by_name[connection["child"]])
            for axis in range(3):
                actual_overlap = (
                    min(parent_bounds[axis + 3], child_bounds[axis + 3])
                    - max(parent_bounds[axis], child_bounds[axis])
                )
                self.assertGreaterEqual(
                    actual_overlap,
                    A22.MIN_CONTACT_OVERLAP_M,
                    connection,
                )
        self.assertGreaterEqual(connection_count, 100)

        near_hull = next(
            spec for spec in plan.specs
            if spec["role"] == "a22-p0-primary-camera-ship-near-hull"
        )
        self.assertEqual(near_hull["material"], "structural_steel")
        connected_children = {
            connection["child"] for connection in plan.connections
        }
        for spec in plan.specs:
            if spec["role"].endswith("supported-rain-hood"):
                self.assertIn(spec["name"], connected_children)

    def test_glass_is_deep_and_no_black_window_cards_exist(self) -> None:
        for plan in self.plans.values():
            roles = [spec["role"] for spec in plan.specs]
            self.assertFalse(any("black-window" in role for role in roles))
            self.assertFalse(any("window-card" in role for role in roles))
        hero_specs = [
            spec for spec in self.plans[0].specs
            if spec["group"] in {A22.STACKHOUSE_ID, A22.CUSTOMS_ID}
        ]
        glass_count = sum(
            spec["material"] == "dirty_glass" for spec in hero_specs
        )
        warm_count = sum(
            spec["material"] == "warm_glass" for spec in hero_specs
        )
        self.assertGreater(glass_count, 8)
        self.assertGreaterEqual(warm_count, glass_count)

    def test_routes_spawns_and_proof_cameras_are_clear(self) -> None:
        for plan in self.plans.values():
            self.assertEqual(A22.spawn_intrusions(plan), [])
            self.assertEqual(A22.route_intrusions(plan), [])
        self.assertEqual(len(A22.PRIVATE_VIEWS), 9)
        self.assertEqual(len({view["id"] for view in A22.PRIVATE_VIEWS}), 9)
        for view in A22.PRIVATE_VIEWS:
            self.assertEqual(A22.camera_containment_hits(self.plans[0], view), [])
        for view in A22.PRIVATE_VIEWS[:-1]:
            self.assertEqual(view["eye"][1], A22.PLAYER_EYE_M)
        self.assertEqual(A22.PRIMARY_CAMERA["frameOrder"], (
            A22.STACKHOUSE_ID, A22.CUSTOMS_ID,
        ))

    def test_private_only_no_public_or_runtime_paths(self) -> None:
        root = str(A22.PRIVATE_OUTPUT_ROOT)
        self.assertTrue(root.startswith("/private/tmp/hibana-blender/"))
        self.assertIn("a22-souko-production-art", root)
        self.assertNotIn("/public/", root)
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("public/assets/aaa/stages", source)
        self.assertNotIn("src/game/", source)
        self.assertIn("background-only", source)

    def test_producer_status_stays_no_ship(self) -> None:
        scorecard = A22.producer_provisional_scorecard()
        self.assertEqual(scorecard["verdict"], "NO-SHIP")
        self.assertTrue(scorecard["independentReviewRequired"])
        self.assertFalse(scorecard["formalReferencePassClaimed"])
        self.assertFalse(
            scorecard["formalPassGate"]["currentlyMeetsNumericGate"],
        )
        self.assertGreaterEqual(len(A22.SELF_REVIEW_HISTORY), 2)
        self.assertGreaterEqual(
            sum(
                item["verdict"] == "REJECTED"
                for item in A22.SELF_REVIEW_HISTORY
            ),
            5,
        )
        self.assertEqual(
            A22.SELF_REVIEW_HISTORY[-1]["verdict"],
            "REJECTED_GENERIC_BLOCKOUT",
        )
        controlling = scorecard["controllingIndependentReview"]
        self.assertTrue(controlling["lowerIndependentScoreControls"])
        self.assertFalse(controlling["appliesToCurrentCandidate"])
        self.assertEqual(controlling["verdict"], "PASS")
        self.assertFalse(controlling["genericBlockout"])
        self.assertEqual(
            controlling["candidateSha256"],
            "0d8d5e497936e2476f5cf73b78c4d5eb79a3ed7a944b769d48318a63a5ca2f3e",
        )
        self.assertEqual(controlling["mean"], 8.0)
        self.assertEqual(controlling["minimum"], 7.2)


if __name__ == "__main__":
    unittest.main()
