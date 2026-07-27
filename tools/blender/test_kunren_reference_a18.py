from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.blender.stage_kits.kunren_reference_a18 import (
    COMMAND_ID,
    DEFAULT_LOD_BUDGETS,
    HANGAR_ID,
    KIT_VERSION,
    LODBudget,
    REFERENCE_IMAGE_SHA256,
    emit_kunren_reference_a18_plan,
    load_authoritative_kunren_layout,
    make_kunren_reference_a18_plan,
)


def fixture_stage():
    command = {
        "id": COMMAND_ID,
        "districtKind": "bunker",
        "collisionTemplate": "courtyard",
        "cx": 72.8,
        "cz": 84,
        "rot": 0,
        "width": 88,
        "depth": 56,
        "height": 49,
        "entrance": [28, 84],
        "approach": {"start": [8, 84], "end": [28, 84], "width": 12},
        "grounded": True,
        "combatSpace": True,
    }
    hangar = {
        "id": HANGAR_ID,
        "districtKind": "hangar",
        "collisionTemplate": "hall",
        "cx": -84.8,
        "cz": -100,
        "rot": 0,
        "width": 112,
        "depth": 70,
        "height": 55,
        "entrance": [-28, -100],
        "approach": {"start": [-8, -100], "end": [-28, -100], "width": 12},
        "grounded": True,
        "combatSpace": True,
    }
    boxes = [
        {
            "x": 72.8,
            "y": 0,
            "z": 84,
            "w": 88,
            "h": 0.5,
            "d": 56,
            "landmarkId": COMMAND_ID,
            "landmarkPart": "floor",
            "structural": True,
        },
        {
            "x": -84.8,
            "y": 0,
            "z": -100,
            "w": 112,
            "h": 0.5,
            "d": 70,
            "landmarkId": HANGAR_ID,
            "landmarkPart": "floor",
            "structural": True,
        },
    ]
    return {
        "id": "kunren",
        "size": 310,
        "seed": 11,
        "playerSpawns": [[143, 0, 0], [0, 0, 143], [-143, 0, 0], [97, 0, 0]],
        "botSpawns": [[57, 0, 0], [47, 0, 0], [37, 0, 0], [27, 0, 0]],
        "landmarkPlacements": [command, hangar],
        "districtPlacements": [
            {"kind": "bunker", "cx": 72.8, "cz": 84, "rot": 0, "width": 88, "depth": 56},
            {"kind": "hangar", "cx": -84.8, "cz": -100, "rot": 0, "width": 112, "depth": 70},
            {"kind": "arena", "cx": -32, "cz": -36, "rot": 3, "width": 30, "depth": 44},
            {"kind": "bunker", "cx": -76, "cz": -40, "rot": 0, "width": 40, "depth": 32},
            {"kind": "tower", "cx": 116, "cz": -40, "rot": 0, "width": 22, "depth": 22},
            {"kind": "hangar", "cx": 60, "cz": 36, "rot": 0, "width": 40, "depth": 22},
            {"kind": "arena", "cx": 52, "cz": 136, "rot": 0, "width": 44, "depth": 30},
            {"kind": "bunker", "cx": 52, "cz": -108, "rot": 1, "width": 32, "depth": 40},
            {"kind": "tower", "cx": -28, "cz": 64, "rot": 3, "width": 22, "depth": 22},
            {"kind": "hangar", "cx": 100, "cz": 132, "rot": 0, "width": 40, "depth": 22},
            {"kind": "arena", "cx": -36, "cz": 32, "rot": 0, "width": 44, "depth": 30},
            {"kind": "bunker", "cx": 104, "cz": -80, "rot": 3, "width": 32, "depth": 40},
            {"kind": "tower", "cx": -92, "cz": 92, "rot": 2, "width": 22, "depth": 22},
            {"kind": "hangar", "cx": -124, "cz": -44, "rot": 0, "width": 40, "depth": 22},
        ],
        "propPlacements": [],
        "boxes": boxes,
    }


class RecordingBuilder:
    def __init__(self):
        self.calls = []

    def add_box(self, *args):
        self.calls.append(("box", args))

    def add_oriented_box(self, *args):
        self.calls.append(("oriented_box", args))

    def add_beam(self, *args):
        self.calls.append(("beam", args))

    def add_cylinder(self, *args):
        self.calls.append(("cylinder", args))

    def add_cylinder_between(self, *args):
        self.calls.append(("cylinder_between", args))

    def add_sloped_panel(self, *args):
        self.calls.append(("sloped_panel", args))

    def add_rock(self, *args):
        self.calls.append(("rock", args))


class KunrenReferenceA18Tests(unittest.TestCase):
    def test_authoritative_loader_selects_one_kunren_and_preserves_source_metadata(self):
        stage = fixture_stage()
        payload = {
            "version": 6,
            "placementSource": "canonical-solver-v2-authoring",
            "placementSolverSha256": "solver-sha",
            "stageWorldCatalogSha256": "catalog-sha",
            "stages": [stage, *({"id": f"dummy-{index}"} for index in range(30))],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canonical-stage-layouts.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_authoritative_kunren_layout(path)

        self.assertEqual(loaded.stage_count, 31)
        self.assertEqual(loaded.version, 6)
        self.assertEqual(loaded.placement_solver_sha256, "solver-sha")
        self.assertEqual(loaded.stage_world_catalog_sha256, "catalog-sha")
        self.assertEqual(loaded.stage["id"], "kunren")
        self.assertIsNot(loaded.stage, stage)

    def test_all_lods_are_valid_and_monotonically_reduce(self):
        plans = [make_kunren_reference_a18_plan(fixture_stage(), lod) for lod in range(3)]
        primitive_counts = [plan.primitive_count for plan in plans]
        triangle_counts = [plan.metadata["metrics"]["estimatedTriangles"] for plan in plans]

        self.assertGreater(primitive_counts[0], primitive_counts[1])
        self.assertGreater(primitive_counts[1], primitive_counts[2])
        self.assertGreater(triangle_counts[0], triangle_counts[1])
        self.assertGreater(triangle_counts[1], triangle_counts[2])
        for lod, plan in enumerate(plans):
            budget = DEFAULT_LOD_BUDGETS[lod]
            self.assertLessEqual(plan.primitive_count, budget.max_primitives)
            self.assertLessEqual(plan.metadata["metrics"]["estimatedTriangles"], budget.max_estimated_triangles)
            self.assertLessEqual(len(plan.metadata["metrics"]["materials"]), budget.max_materials)
            self.assertEqual(plan.metadata["metrics"]["routeViolations"], [])
            self.assertEqual(plan.metadata["metrics"]["spawnViolations"], [])

    def test_command_bastion_has_castle_scale_tiers_bridge_and_radar(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        names = set(plan.names)
        for required in (
            "cmd.plinth",
            "cmd.lower.south",
            "cmd.mid.north",
            "cmd.core",
            "cmd.upper.keep",
            "cmd.crown",
            "cmd.bridge.deck",
            "cmd.radar.mast",
            "cmd.radar.ring.0",
            "cmd.tower.north.front",
        ):
            self.assertIn(required, names)

        command_boxes = [spec for spec in plan.boxes if spec.name.startswith("cmd.")]
        command_beams = [spec for spec in plan.beams if spec.name.startswith("cmd.")]
        maximum_y = max(
            [spec.y + spec.h / 2 for spec in command_boxes]
            + [max(spec.start[1], spec.end[1]) + spec.depth for spec in command_beams]
        )
        self.assertGreaterEqual(maximum_y, 48.0)
        self.assertLessEqual(maximum_y, 49.5)

    def test_hangar_is_a_deep_open_ribbed_vault_at_every_lod(self):
        expected_ribs = {0: 10, 1: 7, 2: 4}
        for lod, expected in expected_ribs.items():
            with self.subTest(lod=lod):
                plan = make_kunren_reference_a18_plan(fixture_stage(), lod)
                rib_station_names = {
                    spec.name.split(".")[2]
                    for spec in plan.beams
                    if spec.name.startswith("hall.rib.")
                }
                self.assertEqual(len(rib_station_names), expected)
                arch_beams = [spec for spec in plan.beams if spec.name.startswith("hall.rib.")]
                self.assertGreaterEqual(max(max(spec.start[1], spec.end[1]) for spec in arch_beams), 52.0)
                self.assertLessEqual(min(min(spec.start[2], spec.end[2]) for spec in arch_beams), -130.0)
                self.assertGreaterEqual(max(max(spec.start[2], spec.end[2]) for spec in arch_beams), -70.0)
                self.assertIn("hall.backwall", plan.names)
                self.assertIn("hall.aerostat.body", plan.names)
                self.assertGreaterEqual(len(plan.sloped_panels), 4 if lod == 2 else 8)

    def test_connection_map_references_real_parts_and_all_contacts_overlap(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertGreaterEqual(len(plan.connections), 180)
        for connection in plan.connections:
            self.assertIn(connection.parent, names)
            self.assertIn(connection.child, names)
            self.assertGreaterEqual(connection.actual_overlap_m, connection.min_overlap_m)
        self.assertEqual(len(plan.metadata["connectionMap"]), len(plan.connections))

    def test_collision_floor_boxes_are_used_as_geometry_anchors(self):
        stage = fixture_stage()
        stage["boxes"][0]["x"] = 74.0
        stage["boxes"][0]["w"] = 90.0
        plan = make_kunren_reference_a18_plan(stage, 2)
        plinth = next(spec for spec in plan.boxes if spec.name == "cmd.plinth")

        self.assertAlmostEqual(plinth.x, 76.0)
        self.assertAlmostEqual(plinth.w, 86.0)
        self.assertEqual(plan.metadata["collisionSource"], "canonical-boxes")
        self.assertEqual(plan.metadata["heroEnvelopes"]["command"]["collision_anchor"], "canonical-landmark-floor")

    def test_nonempty_collision_input_without_a_hero_floor_is_rejected(self):
        stage = fixture_stage()
        with self.assertRaisesRegex(ValueError, "one floor anchor"):
            make_kunren_reference_a18_plan(stage, 0, collision_boxes=[stage["boxes"][0]])

    def test_empty_collision_input_uses_reviewable_landmark_fallback(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 2, collision_boxes=[])
        self.assertEqual(plan.metadata["collisionSource"], "deferred-no-boxes")
        self.assertEqual(plan.metadata["collisionBoxCount"], 0)
        self.assertEqual(plan.metadata["heroEnvelopes"]["hangar"]["collision_anchor"], "landmark-envelope-fallback")

    def test_entrance_approach_and_budget_overrides_are_explicit_inputs(self):
        stage = fixture_stage()
        plan = make_kunren_reference_a18_plan(
            stage,
            2,
            entrance_overrides={COMMAND_ID: [28.5, 84]},
            approach_overrides={
                COMMAND_ID: {"start": [8, 84], "end": [28, 84], "width": 10, "inwardClearance": 7},
            },
            lod_budget=LODBudget(250, 5_000, 9),
        )
        self.assertEqual(plan.metadata["heroEnvelopes"]["command"]["entrance"], (28.5, 84.0))
        self.assertEqual(plan.metadata["approachContracts"][COMMAND_ID]["width"], 10.0)
        self.assertEqual(plan.metadata["lodBudget"]["max_primitives"], 250)

        with self.assertRaisesRegex(ValueError, "primitive budget exceeded"):
            make_kunren_reference_a18_plan(stage, 0, lod_budget=LODBudget(40, 50_000, 12))

    def test_route_validator_rejects_an_override_through_solid_mass(self):
        with self.assertRaisesRegex(ValueError, "blocks authoritative approaches"):
            make_kunren_reference_a18_plan(
                fixture_stage(),
                0,
                approach_overrides={
                    COMMAND_ID: {"start": [8, 68.5], "end": [36, 68.5], "width": 12},
                },
            )

    def test_planning_does_not_mutate_authoritative_stage(self):
        stage = fixture_stage()
        before = copy.deepcopy(stage)
        make_kunren_reference_a18_plan(stage, 0)
        self.assertEqual(stage, before)

    def test_all_names_dimensions_and_materials_are_release_safe(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        self.assertEqual(len(plan.names), len(set(plan.names)))
        for spec in plan.boxes:
            self.assertGreater(min(spec.w, spec.h, spec.d), 0)
        for spec in plan.beams:
            self.assertGreater(min(spec.width, spec.depth), 0)
            self.assertNotEqual(spec.start, spec.end)
        for spec in plan.cylinders:
            self.assertGreater(min(spec.radius, spec.height), 0)
        for spec in plan.sloped_panels:
            edge_a = tuple(spec.corners[1][index] - spec.corners[0][index] for index in range(3))
            edge_b = tuple(spec.corners[2][index] - spec.corners[0][index] for index in range(3))
            projected_normal_y = edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2]
            self.assertGreater(abs(projected_normal_y), 1e-8)
        self.assertNotIn("glass", plan.metadata["metrics"]["materials"])
        self.assertEqual(plan.metadata["kitVersion"], KIT_VERSION)

    def test_emitter_uses_only_existing_meshbuilder_helper_surface(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        builder = RecordingBuilder()
        metadata = emit_kunren_reference_a18_plan(builder, plan)

        self.assertEqual(len(builder.calls), plan.primitive_count)
        self.assertEqual(metadata["kitVersion"], KIT_VERSION)
        call_kinds = {kind for kind, _args in builder.calls}
        self.assertEqual(
            call_kinds,
            {"box", "oriented_box", "beam", "cylinder", "cylinder_between", "sloped_panel", "rock"},
        )

    def test_four_district_families_have_distinct_mass_and_facade_markers(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        names = set(plan.names)
        expected = {
            "city.block.0.operations.spine",
            "city.block.0.operations.deck",
            "city.block.1.blast.band.0",
            "city.block.1.blast.band.1",
            "city.block.2.signal.fin.south",
            "city.block.2.signal.crown.deck",
            "city.block.3.monitor.body",
            "city.block.3.monitor.cap",
        }
        self.assertTrue(expected <= names)
        for index in range(4):
            self.assertIn(f"city.block.{index}.door.recess", names)
            self.assertIn(f"city.block.{index}.roof.hvac", names)

    def test_human_scale_near_mid_far_and_formal_gate_contracts_are_measurable(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        metadata = plan.metadata
        layers = metadata["metrics"]["layerCounts"]
        self.assertGreaterEqual(layers["nearHumanScaleAndStory"], 200)
        self.assertGreaterEqual(layers["midPlayableArchitecture"], 650)
        self.assertGreaterEqual(layers["farPhysicalHorizon"], 70)
        self.assertEqual(metadata["humanScaleContract"]["eyeHeightM"], 1.65)
        self.assertEqual(metadata["humanScaleContract"]["serviceDoorHeightM"], 2.5)
        self.assertFalse(metadata["nearMidFarContract"]["rasterMatteAllowed"])
        gate = metadata["formalReferenceGate"]
        self.assertEqual(len(gate["categories"]), 10)
        self.assertEqual(gate["minimumPerCategory"], 7.0)
        self.assertEqual(gate["minimumAverage"], 8.0)
        self.assertGreaterEqual(gate["requiredPerspectiveViewsAt1p65m"], 10)

    def test_selected_portal_ladder_stair_and_door_contacts_physically_overlap(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        boxes = {spec.name: spec for spec in plan.boxes}
        beams = {spec.name: spec for spec in plan.beams}

        lintel = boxes["cmd.gate.lintel"]
        pier = boxes["cmd.portal.frame.south"]
        lintel_bottom = lintel.y - lintel.h / 2
        pier_top = pier.y + pier.h / 2
        self.assertAlmostEqual(pier_top - lintel_bottom, 0.10, places=6)

        tower = boxes["cmd.tower.south.front"]
        ladder = beams["cmd.ladder.south.rail.0"]
        tower_min_x = tower.x - tower.w / 2
        ladder_max_x = max(ladder.start[0], ladder.end[0]) + ladder.width
        self.assertGreaterEqual(ladder_max_x - tower_min_x, 0.005)

        top_step = boxes["hall.stair.south.step.9"]
        catwalk = boxes["hall.catwalk.south"]
        self.assertAlmostEqual(
            top_step.y + top_step.h / 2 - (catwalk.y - catwalk.h / 2),
            0.35,
            places=6,
        )

        jamb = boxes["hall.portal.jamb.south"]
        door = boxes["hall.portal.service-door.south.recess"]
        jamb_max_x = jamb.x + jamb.w / 2
        door_min_x = door.x - door.w / 2
        self.assertAlmostEqual(jamb_max_x - door_min_x, 0.08, places=6)

    def test_reference_surface_license_and_no_raster_horizon_contracts_are_explicit(self):
        plan = make_kunren_reference_a18_plan(fixture_stage(), 0)
        metadata = plan.metadata
        self.assertEqual(metadata["referenceSource"]["sha256"], REFERENCE_IMAGE_SHA256)
        self.assertEqual(
            metadata["surfaceResponseContract"]["requiredChannels"],
            ["baseColor", "roughness", "normalOrBump"],
        )
        forbidden = metadata["textureAtlasContract"]["forbidden"]
        self.assertIn("unknown-license embedded textures", forbidden)
        self.assertIn("raster skyline", forbidden)
        self.assertIn("cylindrical picture wall", forbidden)

    def test_command_radar_array_and_road_checkpoint_survive_lod1(self):
        for lod in (0, 1):
            with self.subTest(lod=lod):
                names = set(make_kunren_reference_a18_plan(fixture_stage(), lod).names)
                self.assertIn("cmd.radar.array.bottom", names)
                self.assertIn("cmd.radar.array.top", names)
                self.assertIn("story.checkpoint.post.south", names)
                self.assertIn("story.checkpoint.crossbeam", names)


if __name__ == "__main__":
    unittest.main()
