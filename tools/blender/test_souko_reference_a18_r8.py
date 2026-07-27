#!/usr/bin/env python3
"""Dedicated tests for the isolated Souko A18 r8 production module."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools/blender/stage_kits/souko_reference_a18_r8.py"
SPEC = importlib.util.spec_from_file_location("souko_reference_a18_r8", MODULE_PATH)
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


class SoukoReferenceA18R8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plans = {lod: souko.build_plan(lod) for lod in (0, 1, 2)}
        cls.metrics = {lod: souko.plan_metrics(cls.plans[lod]) for lod in (0, 1, 2)}

    def specs_for(self, lod: int, role: str):
        return [spec for spec in self.plans[lod].specs if spec["role"] == role]

    def test_canonical_truth_and_reference_hash_are_locked(self) -> None:
        self.assertEqual(souko.STAGE_ID, "souko")
        self.assertEqual(souko.CANONICAL_BOUNDS,
                         {"min_x": -168.0, "max_x": 168.0,
                          "min_z": -168.0, "max_z": 168.0})
        self.assertEqual(souko.CANONICAL_PLAYER_SPAWNS,
                         ((-156.0, 0.0, 0.0), (0.0, 0.0, -156.0),
                          (156.0, 0.0, 0.0), (0.0, 0.0, 156.0)))
        self.assertEqual([landmark["id"] for landmark in souko.LANDMARKS],
                         [souko.STACKHOUSE_ID, souko.CUSTOMS_ID])
        reference = REPO_ROOT / souko.REFERENCE_PATH
        self.assertTrue(reference.is_file())
        self.assertEqual(hashlib.sha256(reference.read_bytes()).hexdigest(),
                         souko.REFERENCE_SHA256)

    def test_lods_are_monotonic_and_within_webgl_budgets(self) -> None:
        counts = [self.metrics[lod]["specCount"] for lod in (0, 1, 2)]
        triangles = [self.metrics[lod]["estimatedTriangles"] for lod in (0, 1, 2)]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(triangles[0], triangles[1])
        self.assertGreater(triangles[1], triangles[2])
        for lod in (0, 1, 2):
            self.assertLessEqual(self.metrics[lod]["specCount"], souko.LOD_API[lod]["maxSpecs"])
            self.assertLessEqual(self.metrics[lod]["estimatedTriangles"],
                                 souko.LOD_API[lod]["maxEstimatedTriangles"])
            self.assertLessEqual(self.metrics[lod]["materialCount"], 16)

    def test_stackhouse_has_four_towers_two_huge_bridges_and_deep_interior(self) -> None:
        plan = self.plans[0]
        self.assertEqual(len(self.specs_for(0, "stackhouse-roof-cap")), 4)
        bridges = self.specs_for(0, "stackhouse-skybridge-floor")
        self.assertEqual(len(bridges), 2)
        self.assertGreater(max(bridge["w"] for bridge in bridges), 48.0)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-rack-upright")), 15)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-rack-depth-tie")), 20)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-internal-cargo-bay")), 35)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-tower-floor")), 25)
        self.assertEqual(len(self.specs_for(0, "stackhouse-occupied-tower-envelope")), 4)
        self.assertEqual(len(self.specs_for(0, "stackhouse-main-bridge-glazed-side")), 2)
        self.assertEqual(len(self.specs_for(0, "stackhouse-main-bridge-safety-chord")), 2)
        self.assertGreaterEqual(len(self.specs_for(0, "stackhouse-visible-rust-streak")), 12)
        stack_specs = [spec for spec in plan.specs if spec["group"] == souko.STACKHOUSE_ID]
        self.assertGreater(max(souko.spec_bounds(spec)[4] for spec in stack_specs), 63.5)

    def test_customs_has_exactly_four_full_depth_teeth_and_multi_storey_mass(self) -> None:
        for lod in (0, 1, 2):
            roofs = self.specs_for(lod, "customs-sawtooth-roof")
            gables = self.specs_for(lod, "customs-sawtooth-triangular-glass-gable")
            self.assertEqual(len(roofs), 4)
            self.assertEqual(len(gables), 4)
            for roof in roofs:
                z_values = [corner[2] for corner in roof["corners"]]
                self.assertGreater(max(z_values) - min(z_values), 55.0)
        self.assertEqual(len(self.specs_for(0, "customs-heavy-lower-wing")), 2)
        self.assertEqual(len(self.specs_for(0, "customs-multistorey-upper-wing")), 2)
        self.assertEqual(len(self.specs_for(0, "customs-control-tower-glazing")), 1)
        self.assertEqual(len(self.specs_for(0, "customs-industrial-chimney")), 2)
        self.assertGreaterEqual(len(self.specs_for(0, "customs-loading-door")), 6)
        self.assertEqual(len(self.specs_for(0, "customs-sawtooth-occupied-bay-volume")), 4)
        self.assertEqual(len(self.specs_for(0, "customs-sawtooth-bay-window-band")), 4)

    def test_city_and_port_have_real_near_mid_far_geometry(self) -> None:
        roles = self.metrics[0]["roles"]
        layers = self.metrics[0]["layers"]
        self.assertGreaterEqual(layers["near"], 250)
        self.assertGreaterEqual(layers["mid"], 400)
        self.assertGreaterEqual(layers["far"], 75)
        for role in ("bonded-warehouse-shell", "cargo-container-shell", "pallet-slat",
                     "forklift-body", "port-crane-huge-boom", "cargo-ship-hull",
                     "real-sea-geometry", "quay-slab", "bonded-yard-cargo-drum",
                     "wet-diagonal-bonded-service-road"):
            self.assertGreater(roles.get(role, 0), 0, role)
        for role in ("port-crane-huge-boom", "cargo-ship-hull", "real-sea-geometry"):
            self.assertTrue(all(spec["outsidePlayable"] for spec in self.specs_for(0, role)))

    def test_materials_encode_wet_rust_stains_and_relief(self) -> None:
        self.assertTrue(souko.MATERIALS["wet_asphalt"]["wetVariation"])
        self.assertLess(souko.MATERIALS["puddle_water"]["roughness"], 0.12)
        self.assertTrue(souko.MATERIALS["weathered_zinc"]["rustMask"])
        self.assertTrue(souko.MATERIALS["structural_steel"]["rustMask"])
        self.assertTrue(souko.MATERIALS["old_concrete"]["stains"])
        self.assertTrue(souko.MATERIALS["red_brick"]["stains"])
        self.assertGreater(souko.MATERIALS["rust"]["noise"], 0.0)
        self.assertEqual(len(souko.MATERIALS), 16)

    def test_all_connections_are_named_and_have_real_overlap(self) -> None:
        for lod, plan in self.plans.items():
            names = {spec["name"] for spec in plan.specs}
            self.assertGreater(len(plan.connections), 90)
            for connection in plan.connections:
                self.assertIn(connection["parent"], names, (lod, connection))
                self.assertIn(connection["child"], names, (lod, connection))
                self.assertGreaterEqual(connection["overlapM"], souko.MIN_CONTACT_OVERLAP_M)

    def test_routes_spawns_and_fixed_player_eye_views_are_clear(self) -> None:
        for plan in self.plans.values():
            self.assertEqual(souko.route_intrusions(plan), [])
            self.assertEqual(souko.spawn_intrusions(plan), [])
        self.assertEqual(len(souko.PRIVATE_VIEWS), 8)
        self.assertEqual(len({view["id"] for view in souko.PRIVATE_VIEWS}), 8)
        for view in souko.PRIVATE_VIEWS:
            self.assertEqual(view["eye"][1], 1.65)
            self.assertGreaterEqual(view["lensMm"], 24.0)
            self.assertLessEqual(view["lensMm"], 34.0)

    def test_fixed_ten_category_scorecard_is_provisional_only(self) -> None:
        scorecard = souko.producer_provisional_scorecard()
        self.assertEqual(tuple(scorecard["fixedCategoryOrder"]), souko.FIXED_SCORE_CATEGORIES)
        self.assertEqual(tuple(item["category"] for item in scorecard["items"]),
                         souko.FIXED_SCORE_CATEGORIES)
        self.assertEqual(len(scorecard["items"]), 10)
        self.assertTrue(scorecard["producerProvisional"])
        self.assertFalse(scorecard["formalReferencePassClaimed"])
        self.assertTrue(scorecard["independentReviewRequired"])
        self.assertFalse(scorecard["formalPassGate"]["currentlyMeetsNumericGate"])

    def test_emitter_covers_every_spec_without_builder_import(self) -> None:
        builder = RecordingBuilder()
        souko.emit_plan(builder, self.plans[2])
        self.assertEqual(len(builder.calls), len(self.plans[2].specs))
        self.assertEqual({payload["name"] for _, payload in builder.calls},
                         {spec["name"] for spec in self.plans[2].specs})
        self.assertTrue(all(payload["material"] in set(souko.DEFAULT_INTEGRATION_MATERIAL_MAP.values())
                            for _, payload in builder.calls))

    def test_explicit_mesh_batches_have_expected_raw_topology(self) -> None:
        batches = souko._build_mesh_batches(self.plans[0])
        self.assertEqual(set(batches), set(self.metrics[0]["materials"]))
        self.assertGreater(sum(len(batch["vertices"]) for batch in batches.values()), 9000)
        self.assertGreater(sum(len(batch["faces"]) for batch in batches.values()), 6500)
        self.assertLess(sum(len(batch["vertices"]) for batch in batches.values()), 100_000)

    def test_module_is_isolated_and_contains_no_shortcut_geometry_calls(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden = (
            "import build_all_stages", "from build_all_stages", "primitive_cube_add",
            "primitive_cylinder_add", "bpy.ops.mesh.", "ShaderNodeTexImage",
            "image_as_planes", "runtime-background-image", "billboard-matte",
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)
        self.assertIn("if not bpy.app.background", source)
        self.assertIn("/private/tmp/hibana-blender/", source)


if __name__ == "__main__":
    unittest.main()
