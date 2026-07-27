from __future__ import annotations

import copy
from pathlib import Path
import unittest

from tools.blender.stage_kits.kunren_reference_a18 import COMMAND_ID, HANGAR_ID
from tools.blender.stage_kits.kunren_reference_a19 import (
    A19_LOD_BUDGETS,
    FIXED_SCORE_CATEGORIES,
    KIT_VERSION,
    MAIN_REFERENCE_CAMERA,
    emit_kunren_reference_a19_plan,
    make_kunren_reference_a19_plan,
    producer_provisional_scorecard,
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
    districts = [
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
    ]
    return {
        "id": "kunren",
        "size": 310,
        "seed": 11,
        "playerSpawns": [[143, 0, 0], [0, 0, 143], [-143, 0, 0], [97, 0, 0]],
        "botSpawns": [[57, 0, 0], [47, 0, 0], [37, 0, 0], [27, 0, 0]],
        "landmarkPlacements": [command, hangar],
        "districtPlacements": districts,
        "propPlacements": [],
        "boxes": boxes,
    }


class RecordingBuilder:
    def __init__(self):
        self.calls = []
        self.names = []

    def begin_part(self, spec):
        self.names.append(spec.name)

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


class KunrenReferenceA19Tests(unittest.TestCase):
    def test_reference_camera_is_locked_first_and_frames_both_heroes_at_40_class(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        metadata = plan.metadata
        self.assertEqual(metadata["constructionOrder"][0], "reference-camera-lock")
        self.assertEqual(MAIN_REFERENCE_CAMERA.eye_height_m, 1.65)
        self.assertEqual(MAIN_REFERENCE_CAMERA.location[1], 1.65)
        self.assertEqual(MAIN_REFERENCE_CAMERA.lens_mm, 24.0)

        command = metadata["heroFrameMetrics"][COMMAND_ID]
        hangar = metadata["heroFrameMetrics"][HANGAR_ID]
        self.assertGreaterEqual(command["screenHeight"], 0.35)
        self.assertGreaterEqual(hangar["screenHeight"], 0.40)
        self.assertLess(command["xMax"], hangar["xMin"])
        self.assertGreater(command["visibleHorizontalFraction"], 0.25)
        self.assertGreater(hangar["visibleHorizontalFraction"], 0.25)
        self.assertGreater(command["xMin"], -0.15)
        self.assertLess(hangar["xMax"], 1.15)

    def test_authoritative_placements_approaches_and_spawns_are_preserved(self):
        stage = fixture_stage()
        before = copy.deepcopy(stage)
        plan = make_kunren_reference_a19_plan(stage, 0)
        self.assertEqual(stage, before)
        contracts = plan.metadata["authoritativeContracts"]
        self.assertEqual(contracts["playerSpawns"], before["playerSpawns"])
        self.assertEqual(contracts["botSpawns"], before["botSpawns"])
        self.assertEqual(contracts["approaches"][COMMAND_ID]["start"], (8.0, 84.0))
        self.assertEqual(contracts["approaches"][HANGAR_ID]["end"], (-28.0, -100.0))
        self.assertEqual(plan.metadata["heroEnvelopes"]["command"]["cx"], 72.8)
        self.assertEqual(plan.metadata["heroEnvelopes"]["hangar"]["cz"], -100.0)

    def test_locked_camera_sightline_uses_low_terraces_not_a_floating_bridge(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertFalse(any(name.startswith("city.bridge.south.service") for name in names))
        treatment = plan.metadata["referenceSightlineTreatment"]
        self.assertEqual(treatment["verticalScale"], 0.12)
        self.assertFalse(treatment["horizontalPlacementsChanged"])
        self.assertFalse(treatment["gameplayCollisionChanged"])
        terrace_boxes = [
            spec
            for spec in plan.boxes
            if spec.name.startswith(("city.block.5.", "city.block.9."))
        ]
        self.assertTrue(terrace_boxes)
        self.assertLess(max(spec.y + spec.h / 2.0 for spec in terrace_boxes), 6.0)

    def test_macro_route_contains_all_requested_layering_families(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        names = set(plan.names)
        required = {
            "a19.route.ramp.deck",
            "a19.route.retaining.left.0",
            "a19.route.retaining.right.0",
            "a19.checkpoint.crossbeam",
            "a19.checkpoint.command-sign",
            "a19.route.service-stair.0",
            "a19.logistics.container.0",
            "a19.logistics.ammo-pallet.0",
            "a19.checkpoint.guard-booth.front-window",
            "a19.foreground.service-frame.mass",
            "a19.foreground.service-frame.front-recess",
            "a19.foreground.pipe.0",
        }
        self.assertTrue(required <= names)
        self.assertEqual(plan.metadata["metrics"]["routeViolations"], [])
        self.assertEqual(plan.metadata["metrics"]["spawnViolations"], [])

    def test_hero_facades_have_deep_occupied_weathered_geometry(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        names = set(plan.names)
        required = {
            "a19.cmd.facade.bay.0.recess",
            "a19.cmd.facade.bay.0.frame.header",
            "a19.cmd.battered-buttress.0",
            "a19.cmd.east-operations-stack.0",
            "a19.cmd.west-operations-bay.0.recess",
            "a19.cmd.forward-keep.base",
            "a19.cmd.forward-keep.aperture.0",
            "a19.hall.portal.outer-collar.0",
            "a19.hall.portal.inner-collar.0",
            "a19.hall.portal.shoulder.south.service-recess",
            "a19.hall.operations.deck.0",
            "a19.hall.aerostat.service-band.0",
            "a19.hall.maintenance-cart.0",
        }
        self.assertTrue(required <= names)
        roles = {spec.role for group in (plan.boxes, plan.beams, plan.sloped_panels) for spec in group}
        self.assertIn("occupied-facade-deep-recess", roles)
        self.assertIn("monumental-portal-outer-collar", roles)
        self.assertIn("weathering-drip-hood", roles)

    def test_all_lods_reduce_and_stay_inside_a19_private_proof_budgets(self):
        plans = [make_kunren_reference_a19_plan(fixture_stage(), lod) for lod in range(3)]
        counts = [plan.primitive_count for plan in plans]
        triangles = [plan.metadata["metrics"]["estimatedTriangles"] for plan in plans]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(triangles[0], triangles[1])
        self.assertGreater(triangles[1], triangles[2])
        for lod, plan in enumerate(plans):
            budget = A19_LOD_BUDGETS[lod]
            self.assertLessEqual(plan.primitive_count, budget.max_primitives)
            self.assertLessEqual(plan.metadata["metrics"]["estimatedTriangles"], budget.max_estimated_triangles)
            self.assertLessEqual(len(plan.metadata["metrics"]["materials"]), budget.max_materials)

    def test_connection_map_is_real_and_minimum_overlap_is_explicit(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertGreater(len(plan.connections), 600)
        for connection in plan.connections:
            self.assertIn(connection.parent, names)
            self.assertIn(connection.child, names)
            self.assertGreaterEqual(connection.actual_overlap_m, 0.005)
        self.assertEqual(len(plan.metadata["connectionMap"]), len(plan.connections))

    def test_emitter_uses_reviewed_builder_surface_and_keeps_names(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        builder = RecordingBuilder()
        metadata = emit_kunren_reference_a19_plan(builder, plan)
        self.assertEqual(len(builder.calls), plan.primitive_count)
        self.assertEqual(builder.names, list(plan.names))
        self.assertEqual(metadata["kitVersion"], KIT_VERSION)
        self.assertEqual(
            {kind for kind, _args in builder.calls},
            {"box", "oriented_box", "beam", "cylinder", "cylinder_between", "sloped_panel", "rock"},
        )

    def test_producer_score_is_exact_category_provisional_and_never_self_passes(self):
        scorecard = producer_provisional_scorecard(["/private/tmp/a19/view.png"])
        self.assertEqual(tuple(scorecard["categories"]), FIXED_SCORE_CATEGORIES)
        self.assertEqual(tuple(scorecard["scores"]), FIXED_SCORE_CATEGORIES)
        self.assertTrue(scorecard["producerProvisional"])
        self.assertTrue(scorecard["independentReviewerRequired"])
        self.assertFalse(scorecard["referencePassClaimed"])
        self.assertEqual(scorecard["releaseDecision"], "NO-SHIP_PENDING_INDEPENDENT_REVIEW")

    def test_private_proof_contract_cannot_write_repo_or_claim_build_integration(self):
        plan = make_kunren_reference_a19_plan(fixture_stage(), 0)
        contract = plan.metadata["privateProofContract"]
        self.assertTrue(contract["defaultDirectory"].startswith("/private/tmp/"))
        self.assertFalse(contract["publicAssetWritesAllowed"])
        self.assertFalse(contract["repoBuildIntegrationAllowed"])
        source = Path(__file__).with_name("stage_kits").joinpath("kunren_reference_a19.py").read_text(encoding="utf-8")
        self.assertNotIn("import build_all_stages", source)


if __name__ == "__main__":
    unittest.main()
