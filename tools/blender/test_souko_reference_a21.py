#!/usr/bin/env python3
"""Dedicated tests for the isolated Souko A21 production-art candidate."""

from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools/blender/stage_kits/souko_reference_a21.py"
SPEC = importlib.util.spec_from_file_location("souko_reference_a21", MODULE_PATH)
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


class SoukoReferenceA21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plans = {lod: souko.build_plan(lod) for lod in (0, 1, 2)}
        cls.metrics = {lod: souko.plan_metrics(cls.plans[lod]) for lod in (0, 1, 2)}

    def specs_for(self, lod: int, role: str):
        return [spec for spec in self.plans[lod].specs if spec["role"] == role]

    def test_canonical_truth_references_and_two_hero_identity_are_locked(self) -> None:
        self.assertEqual(souko.STAGE_ID, "souko")
        self.assertEqual(
            souko.CANONICAL_BOUNDS,
            {"min_x": -168.0, "max_x": 168.0, "min_z": -168.0, "max_z": 168.0},
        )
        self.assertEqual(
            [landmark["id"] for landmark in souko.LANDMARKS],
            [souko.STACKHOUSE_ID, souko.CUSTOMS_ID],
        )
        self.assertEqual(
            self.metrics[0]["landmarkGroups"],
            sorted((souko.STACKHOUSE_ID, souko.CUSTOMS_ID)),
        )
        reference = REPO_ROOT / souko.REFERENCE_PATH
        self.assertEqual(
            hashlib.sha256(reference.read_bytes()).hexdigest(),
            souko.REFERENCE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(souko.IMAGEGEN_REFERENCE_PATH.read_bytes()).hexdigest(),
            souko.IMAGEGEN_REFERENCE_SHA256,
        )
        self.assertEqual(souko.INDEPENDENT_A20_BASELINE_SCORE, 4.65)
        self.assertIn("a21", souko.REFERENCE_MATCH_VERSION)

    def test_primary_camera_is_compressed_fixed_1_65m_and_reference_ordered(self) -> None:
        camera = souko.PRIMARY_CAMERA
        self.assertIs(camera, souko.PRIVATE_VIEWS[0])
        self.assertEqual(camera["eye"][1], 1.65)
        self.assertEqual(camera["lensMm"], 26.0)
        self.assertEqual(camera["sensorWidthMm"], 36.0)
        self.assertEqual(
            camera["frameOrder"], (souko.STACKHOUSE_ID, souko.CUSTOMS_ID),
        )
        self.assertLessEqual(camera["skyMaxFraction"], 0.20)
        self.assertLessEqual(camera["roadMaxFraction"], 0.24)
        self.assertGreaterEqual(camera["heroHorizontalFillTarget"][0], 0.82)

        eye_x, _, eye_z = camera["eye"]
        target_x, _, target_z = camera["target"]
        dx, dz = target_x - eye_x, target_z - eye_z
        length = math.hypot(dx, dz)
        forward = (dx / length, dz / length)
        right = (forward[1], -forward[0])
        half_fov = math.atan(camera["sensorWidthMm"] / (2.0 * camera["lensMm"]))
        screen_x = {}
        for landmark in souko.LANDMARKS:
            vx, vz = landmark["cx"] - eye_x, landmark["cz"] - eye_z
            lateral = vx * right[0] + vz * right[1]
            depth = vx * forward[0] + vz * forward[1]
            self.assertLess(abs(math.atan2(lateral, depth)), half_fov)
            screen_x[landmark["id"]] = lateral
        self.assertLess(
            screen_x[souko.STACKHOUSE_ID],
            screen_x[souko.CUSTOMS_ID],
        )
        self.assertEqual(len(souko.PRIVATE_VIEWS), 8)
        self.assertEqual(len({view["id"] for view in souko.PRIVATE_VIEWS}), 8)
        self.assertTrue(all(view["eye"][1] == 1.65 for view in souko.PRIVATE_VIEWS))
        for view in souko.PRIVATE_VIEWS:
            self.assertEqual(
                souko.camera_containment_hits(self.plans[0], view),
                [],
                view["id"],
            )

    def test_lods_are_deterministic_monotonic_and_within_webgl_budgets(self) -> None:
        counts = [self.metrics[lod]["specCount"] for lod in (0, 1, 2)]
        triangles = [self.metrics[lod]["estimatedTriangles"] for lod in (0, 1, 2)]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(triangles[0], triangles[1])
        self.assertGreater(triangles[1], triangles[2])
        for lod in (0, 1, 2):
            self.assertLessEqual(
                self.metrics[lod]["specCount"], souko.LOD_API[lod]["maxSpecs"],
            )
            self.assertLessEqual(
                self.metrics[lod]["estimatedTriangles"],
                souko.LOD_API[lod]["maxEstimatedTriangles"],
            )
            self.assertLessEqual(self.metrics[lod]["materialCount"], 16)
            rebuilt = souko.build_plan(lod)
            self.assertEqual(rebuilt.specs, self.plans[lod].specs)
            self.assertEqual(rebuilt.connections, self.plans[lod].connections)

    def test_stackhouse_is_structurally_reauthored_as_unequal_megastructure(self) -> None:
        for lod in (0, 1, 2):
            self.assertEqual(
                len(self.specs_for(lod, "a21-stackhouse-functional-mass")), 4,
            )
            self.assertEqual(
                len(self.specs_for(lod, "stackhouse-completed-tower-envelope")), 0,
            )
        roles = self.metrics[0]["roles"]
        self.assertGreaterEqual(roles["a21-stackhouse-open-machinery-void"], 8)
        self.assertGreaterEqual(roles["a21-stackhouse-machinery-void-x-brace"], 16)
        self.assertGreaterEqual(roles["a21-stackhouse-open-rack-upright"], 15)
        self.assertGreaterEqual(roles["a21-stackhouse-rack-cargo"], 45)
        self.assertEqual(roles["a21-stackhouse-castle-rack-bridge-floor"], 1)
        self.assertEqual(roles["a21-stackhouse-crown-lift-bridge-floor"], 1)
        stack_specs = [
            spec for spec in self.plans[0].specs
            if spec["group"] == souko.STACKHOUSE_ID
        ]
        self.assertGreater(max(souko.spec_bounds(spec)[4] for spec in stack_specs), 125.0)

    def test_customs_has_four_unequal_full_depth_halls_and_offset_tower(self) -> None:
        for role in (
            "a21-customs-full-depth-sawtooth-roof",
            "a21-customs-full-depth-sawtooth-glazing",
            "a21-customs-deep-machine-hall-void",
            "a21-customs-monumental-machine-aperture",
        ):
            self.assertEqual(len(self.specs_for(0, role)), 4, role)
        roofs = self.specs_for(0, "a21-customs-full-depth-sawtooth-roof")
        peak_heights = []
        for roof in roofs:
            z_values = [corner[2] for corner in roof["corners"]]
            self.assertGreaterEqual(max(z_values) - min(z_values), 70.0)
            peak_heights.append(max(corner[1] for corner in roof["corners"]))
        self.assertEqual(len(set(peak_heights)), 4)
        self.assertGreaterEqual(
            len(self.specs_for(0, "a21-customs-sawtooth-internal-truss")), 64,
        )
        self.assertEqual(
            len(self.specs_for(0, "a21-customs-control-tower-watch-room")), 1,
        )
        self.assertEqual(
            len(self.specs_for(0, "a21-customs-weathered-industrial-chimney")), 2,
        )
        customs_specs = [
            spec for spec in self.plans[0].specs
            if spec["group"] == souko.CUSTOMS_ID
        ]
        self.assertGreater(max(souko.spec_bounds(spec)[4] for spec in customs_specs), 110.0)
        self.assertFalse(
            any("occupied-window-band" in spec["role"] for spec in customs_specs),
        )

    def test_operational_near_mid_far_layers_and_ship_quay_evidence_are_real(self) -> None:
        roles = self.metrics[0]["roles"]
        layers = self.metrics[0]["layers"]
        self.assertGreaterEqual(layers["near"], 700)
        self.assertGreaterEqual(layers["mid"], 900)
        self.assertGreaterEqual(layers["far"], 350)
        required = (
            "a21-quay-tactical-cover",
            "a21-wet-quay-oil-track",
            "a21-cargo-ship-hull-plate",
            "a21-cargo-ship-deck-hatch",
            "a21-cargo-ship-mooring-line",
            "a21-quay-rubber-fender",
            "a21-quay-heavy-bollard",
            "a21-reflective-working-quay-puddle",
            "a21-working-quay-cross-drain",
            "a21-working-quay-service-gantry-leg",
            "a21-working-quay-service-gantry-header",
            "a21-working-quay-overhead-utility-pipe",
            "a21-working-quay-gantry-lamp",
            "real-sea-geometry",
            "port-crane-huge-boom",
            "bonded-warehouse-shell",
        )
        for role in required:
            self.assertGreater(roles.get(role, 0), 0, role)
        for role in (
            "a21-cargo-ship-hull-plate",
            "a21-quay-rubber-fender",
            "real-sea-geometry",
        ):
            self.assertTrue(
                all(spec["outsidePlayable"] for spec in self.specs_for(0, role)),
            )

    def test_release_material_strategy_has_roughness_normal_and_water_alpha(self) -> None:
        self.assertLessEqual(len(souko.MATERIALS), 16)
        surface_suffixes = {
            "wall_weathered", "wall_warm", "wall_cool", "wall_alt",
            "obstacle", "natural", "terrain", "floor", "road", "wall",
            "water", "roof", "wood",
        }
        for key, recipe in souko.MATERIALS.items():
            self.assertIn("baseColor", recipe["textureStrategy"])
            self.assertIn("roughness", recipe["textureStrategy"])
            self.assertIn("normal", recipe["textureStrategy"])
            if (
                key in self.metrics[0]["materials"]
                and souko.MATERIAL_EXPORT_SUFFIX[key] in surface_suffixes
            ):
                self.assertIn(key, self.metrics[0]["releaseSurfaceMaterials"])
        for key in ("puddle_water", "sea_water"):
            self.assertLess(souko.MATERIALS[key]["alpha"], 1.0)
            self.assertIn("alphaBlend", souko.MATERIALS[key]["textureStrategy"])

    def test_connections_bounds_routes_and_spawns_are_valid(self) -> None:
        for lod, plan in self.plans.items():
            names = {spec["name"] for spec in plan.specs}
            self.assertGreater(len(plan.connections), 80)
            for connection in plan.connections:
                self.assertIn(connection["parent"], names)
                self.assertIn(connection["child"], names)
                self.assertGreaterEqual(
                    connection["overlapM"], souko.MIN_CONTACT_OVERLAP_M,
                )
            for spec in plan.specs:
                bounds = souko.spec_bounds(spec)
                self.assertTrue(all(math.isfinite(value) for value in bounds))
                self.assertLess(bounds[0], bounds[3])
                self.assertLess(bounds[1], bounds[4])
                self.assertLess(bounds[2], bounds[5])
            self.assertEqual(souko.route_intrusions(plan), [])
            self.assertEqual(souko.spawn_intrusions(plan), [])

    def test_emitter_covers_every_spec_without_importing_blender(self) -> None:
        builder = RecordingBuilder()
        souko.emit_plan(builder, self.plans[2])
        self.assertEqual(len(builder.calls), len(self.plans[2].specs))
        self.assertEqual(
            {payload["name"] for _, payload in builder.calls},
            {spec["name"] for spec in self.plans[2].specs},
        )

    def test_producer_status_is_explicit_no_ship(self) -> None:
        scorecard = souko.producer_provisional_scorecard()
        self.assertEqual(
            tuple(scorecard["fixedCategoryOrder"]), souko.FIXED_SCORE_CATEGORIES,
        )
        self.assertEqual(len(scorecard["items"]), 10)
        self.assertTrue(scorecard["producerProvisional"])
        self.assertEqual(scorecard["verdict"], "NO-SHIP")
        self.assertFalse(scorecard["formalReferencePassClaimed"])
        self.assertTrue(scorecard["independentReviewRequired"])

    def test_module_is_private_and_does_not_touch_runtime_or_forbidden_generators(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        for token in (
            "import build_all_stages",
            "from build_all_stages",
            "import souko_reference_a19",
            "from souko_reference_a19",
            "public/assets",
            "image_as_planes",
            "runtime-background-image",
            "billboard-matte",
        ):
            self.assertNotIn(token, source, token)
        self.assertIn("/private/tmp/hibana-blender/", source)
        self.assertIn("producerProvisional", source)
        self.assertIn('"verdict": "NO-SHIP"', source)


if __name__ == "__main__":
    unittest.main()
