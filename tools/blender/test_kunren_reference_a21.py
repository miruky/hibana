from __future__ import annotations

import copy
from pathlib import Path
import unittest

from tools.blender.stage_kits.kunren_reference_a18 import COMMAND_ID, HANGAR_ID
from tools.blender.stage_kits.kunren_reference_a21 import (
    A21_LOD_BUDGETS,
    COMMAND_HERO_CAMERA,
    IMAGEGEN_REFERENCE_SHA256,
    KIT_VERSION,
    MAIN_REFERENCE_CAMERA,
    PRIVATE_PROOF_DEFAULT,
    emit_kunren_reference_a21_plan,
    make_kunren_reference_a21_plan,
    producer_provisional_scorecard,
)
from tools.blender.test_kunren_reference_a19 import RecordingBuilder, fixture_stage


class KunrenReferenceA21Tests(unittest.TestCase):
    def test_reference_and_fixed_dual_camera_precede_geometry(self):
        plan = make_kunren_reference_a21_plan(fixture_stage(), 0)
        self.assertEqual(
            plan.metadata["constructionOrder"][:2],
            [
                "focused-imagegen-and-repository-reference-lock",
                "fixed-1p65m-dual-camera-lock",
            ],
        )
        self.assertEqual(MAIN_REFERENCE_CAMERA.location[1], 1.65)
        self.assertEqual(MAIN_REFERENCE_CAMERA.eye_height_m, 1.65)
        self.assertEqual(MAIN_REFERENCE_CAMERA.lens_mm, 20.0)
        self.assertEqual(
            (MAIN_REFERENCE_CAMERA.resolution_x, MAIN_REFERENCE_CAMERA.resolution_y),
            (1280, 720),
        )
        self.assertEqual(
            plan.metadata["imageGenReference"]["sha256"],
            IMAGEGEN_REFERENCE_SHA256,
        )
        self.assertTrue(plan.metadata["imageGenReference"]["usedBeforeModeling"])

    def test_dual_landmark_frame_is_wholly_visible_and_separated(self):
        metrics = make_kunren_reference_a21_plan(
            fixture_stage(),
            0,
        ).metadata["heroFrameMetrics"]
        command = metrics[COMMAND_ID]
        hangar = metrics[HANGAR_ID]
        self.assertGreaterEqual(command["xMin"], 0.0)
        self.assertLessEqual(command["xMax"], 1.0)
        self.assertGreaterEqual(hangar["xMin"], 0.0)
        self.assertLessEqual(hangar["xMax"], 1.0)
        self.assertLess(command["xMax"], hangar["xMin"])
        self.assertGreaterEqual(command["screenHeight"], 0.30)
        self.assertGreaterEqual(hangar["screenHeight"], 0.35)

    def test_authoritative_bounds_placements_routes_and_spawns_are_immutable(self):
        stage = fixture_stage()
        before = copy.deepcopy(stage)
        plan = make_kunren_reference_a21_plan(stage, 0)
        self.assertEqual(stage, before)
        contracts = plan.metadata["authoritativeContracts"]
        self.assertEqual(contracts["stageBounds"], {"size": 310, "changed": False})
        self.assertEqual(contracts["playerSpawns"], before["playerSpawns"])
        self.assertEqual(contracts["botSpawns"], before["botSpawns"])
        self.assertEqual(contracts["approaches"][COMMAND_ID]["start"], (8.0, 84.0))
        self.assertEqual(contracts["approaches"][HANGAR_ID]["end"], (-28.0, -100.0))
        self.assertEqual(plan.metadata["metrics"]["routeViolations"], [])
        self.assertEqual(plan.metadata["metrics"]["spawnViolations"], [])

    def test_exactly_two_landmark_identities_remain_contractual(self):
        contract = make_kunren_reference_a21_plan(
            fixture_stage(),
            0,
        ).metadata["landmarkIdentityContract"]
        self.assertEqual(contract["exactCount"], 2)
        self.assertEqual(contract["ids"], [COMMAND_ID, HANGAR_ID])
        self.assertFalse(contract["thirdLandmarkAllowed"])

    def test_both_player_height_review_cameras_are_clear(self):
        clearance = make_kunren_reference_a21_plan(
            fixture_stage(),
            0,
        ).metadata["proofCameraClearance"]
        self.assertEqual(clearance[MAIN_REFERENCE_CAMERA.name], [])
        self.assertEqual(clearance[COMMAND_HERO_CAMERA.name], [])
        self.assertEqual(COMMAND_HERO_CAMERA.eye_height_m, 1.65)

    def test_command_finish_is_structural_occupied_and_not_a_blank_box(self):
        names = set(make_kunren_reference_a21_plan(fixture_stage(), 0).names)
        required = {
            "a21.cmd.south.armour-pier.0",
            "a21.cmd.south.operations-deck.0",
            "a21.cmd.south.operations-deck.0.rail.0",
            "a21.cmd.south.service-bay.0.recess",
            "a21.cmd.south.service-bay.0.frame.header",
            "a21.cmd.south.service-bay.0.louver.0",
            "a21.cmd.south.service-pipe.0",
            "a21.cmd.south.battered-skirt.west",
            "a21.cmd.south.battered-skirt.west.rib.0",
            "a21.cmd.crown.armoured-roof.south",
            "a21.cmd.crown.primary-radar.mast",
            "a21.cmd.crown.primary-radar.array",
            "a21.cmd.crown.primary-radar.array.rung.0",
        }
        self.assertTrue(required <= names)

    def test_hangar_finish_contains_portal_towers_crane_docking_and_equipment(self):
        plan = make_kunren_reference_a21_plan(fixture_stage(), 0)
        names = set(plan.names)
        required = {
            "a21.hall.portal-tower.south.lower",
            "a21.hall.portal-tower.south.upper",
            "a21.hall.portal-tower.south.balcony.0",
            "a21.hall.portal-door-track.0",
            "a21.hall.overhead-crane.rail.0",
            "a21.hall.overhead-crane.bridge",
            "a21.hall.overhead-crane.hoist",
            "a21.hall.aerostat.docking-cable.0",
            "a21.hall.service-equipment.0",
            "a21.hall.service-equipment.0.status-face",
            "a21.hall.dock-tractor.0.body",
            "a21.hall.dock-tractor.0.towbar",
        }
        self.assertTrue(required <= names)
        roles = {
            spec.role
            for group in (
                plan.boxes,
                plan.beams,
                plan.cylinders,
                plan.cylinders_between,
            )
            for spec in group
        }
        self.assertIn("hangar-portal-load-bearing-service-tower", roles)
        self.assertIn("aerostat-tensioned-docking-cable", roles)
        self.assertIn("hangar-working-overhead-crane-bridge", roles)

    def test_connected_district_and_human_scale_story_are_present(self):
        plan = make_kunren_reference_a21_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertTrue(
            {
                "a21.checkpoint.route-cluster.0.booth",
                "a21.checkpoint.route-cluster.0.booth.window",
                "a21.checkpoint.route-cluster.0.barrier.0",
                "a21.checkpoint.route-cluster.0.floodlight",
                "a21.district.service-bridge.0",
                "a21.district.facade-finish.0.deep-bay",
                "a21.district.facade-finish.0.load-fin.0",
                "a21.district.roof-profile.0.shed",
                "a21.district.roof-profile.1.gable.west",
                "a21.story.foreground-vehicle.0.armoured-hood",
                "a21.story.foreground-vehicle.0.recessed-grille",
                "a21.story.foreground-vehicle.0.roof-station",
                "a21.story.route-maintenance.0.pallet",
                "a21.story.route-maintenance.0.crate.0",
                "a21.story.route-maintenance.0.drum.0",
            }
            <= names
        )

    def test_surface_contract_requires_production_response_not_flat_color(self):
        contract = make_kunren_reference_a21_plan(
            fixture_stage(),
            0,
        ).metadata["surfaceResponseContract"]
        self.assertEqual(
            contract["requiredChannels"],
            ["baseColor", "roughness", "normalOrBump"],
        )
        self.assertTrue(contract["flatColorAloneIsBlockout"])
        self.assertTrue(contract["deepOpeningsAreGeometry"])
        self.assertIn("large-scale staining", contract["proceduralVariation"])
        self.assertIn("roughness breakup", contract["proceduralVariation"])
        self.assertEqual(contract["proofMaterialLimit"], 12)

    def test_lods_reduce_and_stay_inside_webgl_limits_without_minimum_count_gate(self):
        plans = [
            make_kunren_reference_a21_plan(fixture_stage(), lod)
            for lod in range(3)
        ]
        counts = [plan.primitive_count for plan in plans]
        triangles = [
            plan.metadata["metrics"]["estimatedTriangles"] for plan in plans
        ]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(triangles[0], triangles[1])
        self.assertGreater(triangles[1], triangles[2])
        for lod, plan in enumerate(plans):
            budget = A21_LOD_BUDGETS[lod]
            self.assertLessEqual(plan.primitive_count, budget.max_primitives)
            self.assertLessEqual(
                plan.metadata["metrics"]["estimatedTriangles"],
                budget.max_estimated_triangles,
            )
            self.assertLessEqual(
                len(plan.metadata["metrics"]["materials"]),
                budget.max_materials,
            )
            self.assertTrue(
                plan.metadata["metrics"]["primitiveCountIsNotAQualityGate"]
            )

    def test_connection_map_is_complete_and_above_five_millimetres(self):
        plan = make_kunren_reference_a21_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertEqual(len(plan.metadata["connectionMap"]), len(plan.connections))
        for connection in plan.connections:
            self.assertIn(connection.parent, names)
            self.assertIn(connection.child, names)
            self.assertGreaterEqual(connection.actual_overlap_m, 0.005)

    def test_emitter_reuses_reviewed_builder_surface(self):
        plan = make_kunren_reference_a21_plan(fixture_stage(), 0)
        builder = RecordingBuilder()
        metadata = emit_kunren_reference_a21_plan(builder, plan)
        self.assertEqual(len(builder.calls), plan.primitive_count)
        self.assertEqual(builder.names, list(plan.names))
        self.assertEqual(metadata["kitVersion"], KIT_VERSION)
        self.assertEqual(
            {kind for kind, _args in builder.calls},
            {
                "box",
                "oriented_box",
                "beam",
                "cylinder",
                "cylinder_between",
                "sloped_panel",
                "rock",
            },
        )

    def test_producer_score_is_always_provisional_no_ship(self):
        scorecard = producer_provisional_scorecard(
            ["/private/tmp/a21/view.png"]
        )
        self.assertTrue(scorecard["producerProvisional"])
        self.assertFalse(scorecard["producerScoreAccepted"])
        self.assertTrue(scorecard["independentReviewerRequired"])
        self.assertFalse(scorecard["referencePassClaimed"])
        self.assertEqual(
            scorecard["releaseDecision"],
            "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        )
        self.assertLess(scorecard["average"], scorecard["minimumAverage"])
        self.assertEqual(
            scorecard["imageGenReference"]["sha256"],
            IMAGEGEN_REFERENCE_SHA256,
        )

    def test_private_proof_isolated_from_public_source_manifest_git_and_ui(self):
        plan = make_kunren_reference_a21_plan(fixture_stage(), 0)
        contract = plan.metadata["privateProofContract"]
        self.assertEqual(
            contract["defaultDirectory"],
            str(PRIVATE_PROOF_DEFAULT),
        )
        self.assertEqual(contract["resolution"], [1280, 720])
        self.assertFalse(contract["publicAssetWritesAllowed"])
        self.assertFalse(contract["repoBuildIntegrationAllowed"])
        self.assertFalse(contract["manifestWritesAllowed"])
        self.assertFalse(contract["sourceWritesAllowed"])
        source = Path(__file__).with_name("stage_kits").joinpath(
            "kunren_reference_a21.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import build_all_stages", source)
        self.assertNotIn("public/assets/", source)
        self.assertNotIn("src/game/", source)
        self.assertNotIn("git ", source)


if __name__ == "__main__":
    unittest.main()
