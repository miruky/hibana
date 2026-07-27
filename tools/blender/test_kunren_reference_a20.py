from __future__ import annotations

import copy
from pathlib import Path
import unittest

from tools.blender.stage_kits.kunren_reference_a18 import COMMAND_ID, HANGAR_ID
from tools.blender.stage_kits.kunren_reference_a19 import make_kunren_reference_a19_plan
from tools.blender.stage_kits.kunren_reference_a20 import (
    A20_LOD_BUDGETS,
    A20_SIGHTLINE_TREATMENTS,
    COMMAND_APPROACH_CAMERA,
    IMAGEGEN_REFERENCE_SHA256,
    KIT_VERSION,
    MAIN_REFERENCE_CAMERA,
    camera_solid_hits,
    emit_kunren_reference_a20_plan,
    make_kunren_reference_a20_plan,
    producer_provisional_scorecard,
)
from tools.blender.test_kunren_reference_a19 import RecordingBuilder, fixture_stage


class KunrenReferenceA20Tests(unittest.TestCase):
    def test_imagegen_and_playable_camera_are_locked_before_geometry(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        self.assertEqual(
            plan.metadata["constructionOrder"][:2],
            ["imagegen-reference-lock", "reference-camera-lock"],
        )
        self.assertEqual(MAIN_REFERENCE_CAMERA.eye_height_m, 1.65)
        self.assertEqual(MAIN_REFERENCE_CAMERA.location[1], 1.65)
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

    def test_dual_heroes_are_wholly_visible_left_and_right(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        command = plan.metadata["heroFrameMetrics"][COMMAND_ID]
        hangar = plan.metadata["heroFrameMetrics"][HANGAR_ID]
        self.assertGreaterEqual(command["xMin"], 0.0)
        self.assertLessEqual(command["xMax"], 1.0)
        self.assertGreaterEqual(hangar["xMin"], 0.0)
        self.assertLessEqual(hangar["xMax"], 1.0)
        self.assertLess(command["xMax"], hangar["xMin"])
        self.assertGreaterEqual(command["screenHeight"], 0.30)
        self.assertGreaterEqual(hangar["screenHeight"], 0.35)

    def test_authoritative_bounds_placements_approaches_and_spawns_are_immutable(self):
        stage = fixture_stage()
        before = copy.deepcopy(stage)
        plan = make_kunren_reference_a20_plan(stage, 0)
        self.assertEqual(stage, before)
        contracts = plan.metadata["authoritativeContracts"]
        self.assertEqual(contracts["stageBounds"], {"size": 310, "changed": False})
        self.assertEqual(contracts["playerSpawns"], before["playerSpawns"])
        self.assertEqual(contracts["botSpawns"], before["botSpawns"])
        self.assertEqual(contracts["approaches"][COMMAND_ID]["start"], (8.0, 84.0))
        self.assertEqual(contracts["approaches"][HANGAR_ID]["end"], (-28.0, -100.0))
        self.assertEqual(plan.metadata["heroEnvelopes"]["command"]["cx"], 72.8)
        self.assertEqual(plan.metadata["heroEnvelopes"]["hangar"]["cz"], -100.0)

    def test_primary_and_command_approach_cameras_are_not_inside_geometry(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        self.assertEqual(camera_solid_hits(plan, MAIN_REFERENCE_CAMERA), ())
        self.assertEqual(camera_solid_hits(plan, COMMAND_APPROACH_CAMERA), ())
        self.assertEqual(COMMAND_APPROACH_CAMERA.eye_height_m, 1.65)
        self.assertEqual(COMMAND_APPROACH_CAMERA.location, (80.0, 1.65, -10.0))
        self.assertEqual(
            plan.metadata["proofCameraClearance"][COMMAND_APPROACH_CAMERA.name],
            [],
        )

    def test_exactly_two_landmark_identities_are_contractual(self):
        contract = make_kunren_reference_a20_plan(fixture_stage(), 0).metadata[
            "landmarkIdentityContract"
        ]
        self.assertEqual(contract["exactCount"], 2)
        self.assertEqual(contract["ids"], [COMMAND_ID, HANGAR_ID])
        self.assertFalse(contract["thirdLandmarkAllowed"])

    def test_camera_blockers_become_low_terraces_without_horizontal_drift(self):
        stage = fixture_stage()
        a19_plan = make_kunren_reference_a19_plan(stage, 0)
        a20_plan = make_kunren_reference_a20_plan(stage, 0)
        treatment = next(
            item for item in A20_SIGHTLINE_TREATMENTS if item.prefix == "city.block.2."
        )
        before = next(spec for spec in a19_plan.boxes if spec.name == "city.block.2.lower")
        after = next(spec for spec in a20_plan.boxes if spec.name == "city.block.2.lower")
        self.assertEqual((after.x, after.z, after.w, after.d), (before.x, before.z, before.w, before.d))
        self.assertAlmostEqual(after.y, before.y * treatment.vertical_scale)
        self.assertAlmostEqual(after.h, before.h * treatment.vertical_scale)
        compressed = [
            spec for spec in a20_plan.boxes if spec.name.startswith("city.block.2.")
        ]
        self.assertLess(max(spec.y + spec.h / 2.0 for spec in compressed), 3.0)

    def test_command_bastion_has_tiers_crown_bridge_buttresses_and_deep_apertures(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        names = set(plan.names)
        required = {
            "a20.cmd.tier.lower.south",
            "a20.cmd.tier.mid",
            "a20.cmd.tier.upper",
            "a20.cmd.tier.keep",
            "a20.cmd.crown.south",
            "a20.cmd.crown.central",
            "a20.cmd.crown.operations-bridge",
            "a20.cmd.buttress.south.0",
            "a20.cmd.buttress.east.0",
            "a20.cmd.aperture.south.0.deep-recess",
            "a20.cmd.aperture.south.0.occupied-light",
            "a20.cmd.gallery.east.0",
            "a20.cmd.west-portal.deep-shadow",
            "a20.cmd.crown.antenna.0.mast",
            "a20.cmd.hero-citadel.plinth",
            "a20.cmd.hero-citadel.keep",
            "a20.cmd.hero-citadel.crown",
            "a20.cmd.hero-citadel.battered-south-face",
            "a20.cmd.hero-citadel.battered-east-face",
            "a20.cmd.hero-citadel.aperture.0",
            "a20.cmd.hero-citadel.lower-gate.deep-recess",
            "a20.cmd.hero-citadel.lower-gate.header",
            "a20.route.command-approach-surface",
        }
        self.assertTrue(required <= names)
        roles = {
            spec.role
            for group in (plan.boxes, plan.beams, plan.sloped_panels)
            for spec in group
        }
        self.assertIn("command-bastion-lower-tier", roles)
        self.assertIn("deep-occupied-command-aperture", roles)
        self.assertIn("castle-scale-battered-buttress", roles)

    def test_hangar_is_deep_operational_and_contains_a_large_aerostat(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        names = set(plan.names)
        required = {
            "a20.hall.cavity.back-wall",
            "a20.hall.cavity.floor",
            "a20.hall.rib.portal.0",
            "a20.hall.rib.back.0",
            "a20.hall.aerostat.nose",
            "a20.hall.aerostat.body",
            "a20.hall.aerostat.tail",
            "a20.hall.aerostat.gondola",
            "a20.hall.gantry.0.crossbeam",
            "a20.hall.equipment.0",
            "a20.hall.worklight.0",
            "a20.hall.catwalk.south.deck",
            "a20.hall.catwalk.north.rail.0",
            "a20.hall.overhead-crane.bridge.0",
            "a20.hall.vehicle.0.tow-tractor",
            "a20.hall.service-tank.0",
        }
        self.assertTrue(required <= names)
        body = next(
            spec
            for spec in plan.cylinders_between
            if spec.name == "a20.hall.aerostat.body"
        )
        self.assertGreaterEqual(body.radius, 8.5)
        self.assertGreaterEqual(abs(body.end[0] - body.start[0]), 35.0)
        roles = {
            spec.role
            for group in (
                plan.boxes,
                plan.beams,
                plan.cylinders_between,
                plan.sloped_panels,
            )
            for spec in group
        }
        self.assertIn("hangar-deep-dark-cavity", roles)
        self.assertIn("hangar-maintenance-gantry", roles)
        self.assertIn("huge-maintained-aerostat", roles)
        self.assertIn("occupied-hangar-catwalk-deck", roles)
        self.assertIn("parked-hangar-military-vehicle", roles)

    def test_near_mid_far_world_is_real_geometry_and_story_is_present(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertTrue(
            {
                "a20.terrain.terrace.0",
                "a20.terrain.terrace.0.retaining",
                "a20.district.terrace-building.0",
                "a20.terrain.mountain.0",
                "a20.story.resupply-pallet.0",
                "a20.story.comms-cabinet",
                "a20.district.dense-block.0",
                "a20.district.dense-block.0.crown",
                "a20.district.dense-block.1.variant-pitched-roof.west",
                "a20.checkpoint.hero-road.crossbeam",
                "a20.checkpoint.hero-road.guard-booth",
                "a20.story.foreground-vehicle.0.apc",
            }
            <= names
        )
        self.assertGreaterEqual(
            len([spec for spec in plan.rocks if spec.name.startswith("a20.terrain.mountain.")]),
            8,
        )
        self.assertGreaterEqual(
            len([spec for spec in plan.boxes if spec.name.startswith("a20.district.dense-block.")]),
            100,
        )
        source = Path(__file__).with_name("stage_kits").joinpath(
            "kunren_reference_a20.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ShaderNodeTexImage", source)
        self.assertNotIn("image_as_plane", source)
        self.assertIn("deterministic-jagged-multi-ring-ridge", source)

    def test_all_lods_reduce_and_stay_inside_a20_webgl_budgets(self):
        plans = [make_kunren_reference_a20_plan(fixture_stage(), lod) for lod in range(3)]
        counts = [plan.primitive_count for plan in plans]
        triangles = [plan.metadata["metrics"]["estimatedTriangles"] for plan in plans]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(triangles[0], triangles[1])
        self.assertGreater(triangles[1], triangles[2])
        for lod, plan in enumerate(plans):
            budget = A20_LOD_BUDGETS[lod]
            self.assertLessEqual(plan.primitive_count, budget.max_primitives)
            self.assertLessEqual(
                plan.metadata["metrics"]["estimatedTriangles"],
                budget.max_estimated_triangles,
            )
            self.assertLessEqual(
                len(plan.metadata["metrics"]["materials"]),
                budget.max_materials,
            )
            self.assertTrue(plan.metadata["metrics"]["webglBatchIntent"]["mergeByMaterial"])

    def test_additions_preserve_routes_spawns_and_real_connection_map(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        self.assertEqual(plan.metadata["metrics"]["routeViolations"], [])
        self.assertEqual(plan.metadata["metrics"]["spawnViolations"], [])
        names = set(plan.names)
        self.assertGreater(len(plan.connections), 700)
        for connection in plan.connections:
            self.assertIn(connection.parent, names)
            self.assertIn(connection.child, names)
            self.assertGreaterEqual(connection.actual_overlap_m, 0.005)
        self.assertEqual(len(plan.metadata["connectionMap"]), len(plan.connections))

    def test_emitter_reuses_reviewed_builder_surface_and_keeps_names(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        builder = RecordingBuilder()
        metadata = emit_kunren_reference_a20_plan(builder, plan)
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

    def test_surface_contract_is_pbr_and_material_count_is_bounded(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        contract = plan.metadata["surfaceResponseContract"]
        self.assertEqual(contract["requiredChannels"], ["baseColor", "roughness", "normalOrBump"])
        self.assertTrue(contract["deepOpeningsAreGeometry"])
        self.assertTrue(contract["flatColorAloneIsBlockout"])
        self.assertEqual(contract["proofMaterialLimit"], 12)
        self.assertEqual(len(plan.metadata["metrics"]["materials"]), 12)

    def test_producer_score_is_provisional_and_can_never_self_pass(self):
        scorecard = producer_provisional_scorecard(["/private/tmp/a20/view.png"])
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

    def test_private_proof_contract_has_no_public_source_manifest_or_git_writes(self):
        plan = make_kunren_reference_a20_plan(fixture_stage(), 0)
        contract = plan.metadata["privateProofContract"]
        self.assertTrue(contract["defaultDirectory"].startswith("/private/tmp/"))
        self.assertEqual(contract["resolution"], [1280, 720])
        self.assertFalse(contract["publicAssetWritesAllowed"])
        self.assertFalse(contract["repoBuildIntegrationAllowed"])
        self.assertFalse(contract["manifestWritesAllowed"])
        self.assertFalse(contract["sourceWritesAllowed"])
        source = Path(__file__).with_name("stage_kits").joinpath(
            "kunren_reference_a20.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import build_all_stages", source)
        self.assertNotIn("public/assets/", source)
        self.assertNotIn("src/game/", source)


if __name__ == "__main__":
    unittest.main()
