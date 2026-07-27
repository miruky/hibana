from __future__ import annotations

import copy
from pathlib import Path
import unittest

from tools.blender.stage_kits import kunren_reference_a22 as a22
from tools.blender.stage_kits.kunren_reference_a18 import COMMAND_ID, HANGAR_ID
from tools.blender.stage_kits.kunren_reference_a22 import (
    A22_EVALUATED_TRIANGLE_TARGETS,
    A22_LOD_BUDGETS,
    COMMAND_HERO_CAMERA,
    IMAGEGEN_REFERENCE_SHA256,
    KIT_VERSION,
    MAIN_REFERENCE_CAMERA,
    PRIVATE_PROOF_DEFAULT,
    SUPPRESSED_A21_PREFIXES,
    emit_kunren_reference_a22_plan,
    make_kunren_reference_a22_plan,
    producer_provisional_scorecard,
)
from tools.blender.test_kunren_reference_a19 import RecordingBuilder, fixture_stage


class KunrenReferenceA22Tests(unittest.TestCase):
    def test_a21_is_scorecard_reference_not_a_blind_geometry_clone(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        audit = plan.metadata["inheritedSuppressionAudit"]
        self.assertTrue(plan.metadata["a21IndependentScorecardCanonical"])
        self.assertFalse(plan.metadata["a21GeometryCloned"])
        self.assertFalse(audit["a21GeometryCloned"])
        self.assertEqual(audit["baseGeometryVersion"], "kunren-reference-a20-v1")
        self.assertGreater(audit["removedObjectCount"], 200)
        self.assertFalse(any(name.startswith("a21.") for name in plan.names))

    def test_old_generic_families_are_removed_from_the_final_plan(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertFalse(
            [name for name in names if name.startswith(SUPPRESSED_A21_PREFIXES)]
        )
        self.assertFalse([name for name in names if name.startswith("city.ridge")])
        inherited_black_cards = [
            spec.name
            for group in (
                plan.boxes,
                plan.beams,
                plan.cylinders,
                plan.cylinders_between,
                plan.sloped_panels,
            )
            for spec in group
            if spec.key == "wall_alt" and not spec.name.startswith("a22.")
        ]
        self.assertEqual(inherited_black_cards, [])
        inherited_box_vehicle_roles = {
            spec.role
            for group in (plan.boxes, plan.beams, plan.cylinders)
            for spec in group
            if (
                "parked-hangar-military-vehicle" in spec.role
                or "parked-foreground-military-vehicle" in spec.role
            )
        }
        self.assertEqual(inherited_box_vehicle_roles, set())
        self.assertTrue(
            all(
                spec.name.startswith("a22.skyline.heightfield-source.")
                and spec.role == "a22-eroded-asymmetric-heightfield-source"
                for spec in plan.rocks
            )
        )

    def test_reference_camera_quantifies_both_hero_occupancies(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        self.assertEqual(MAIN_REFERENCE_CAMERA.eye_height_m, 1.65)
        self.assertEqual(
            (
                MAIN_REFERENCE_CAMERA.resolution_x,
                MAIN_REFERENCE_CAMERA.resolution_y,
            ),
            (1280, 720),
        )
        self.assertEqual(MAIN_REFERENCE_CAMERA.lens_mm, 22.0)
        self.assertEqual(
            MAIN_REFERENCE_CAMERA.location,
            (177.4, 1.65, -185.1),
        )
        self.assertEqual(MAIN_REFERENCE_CAMERA.target, (-6.0, 31.0, -8.0))
        self.assertEqual(COMMAND_HERO_CAMERA.eye_height_m, 1.65)
        self.assertEqual(
            plan.metadata["proofCameraClearance"][MAIN_REFERENCE_CAMERA.name],
            [],
        )
        self.assertEqual(
            plan.metadata["proofCameraClearance"][COMMAND_HERO_CAMERA.name],
            [],
        )
        for landmark_id, metric in plan.metadata["heroFrameMetrics"].items():
            target = a22.REFERENCE_HERO_OCCUPANCY_TARGETS[landmark_id]
            self.assertLessEqual(
                abs(metric["screenWidth"] - target["screenWidth"]),
                target["tolerance"],
            )
            self.assertLessEqual(
                abs(metric["screenHeight"] - target["screenHeight"]),
                target["tolerance"],
            )
        self.assertEqual(
            plan.metadata["imageGenReference"]["sha256"],
            IMAGEGEN_REFERENCE_SHA256,
        )

    def test_canonical_bounds_routes_spawns_and_placements_are_immutable(self):
        stage = fixture_stage()
        before = copy.deepcopy(stage)
        plan = make_kunren_reference_a22_plan(stage, 0)
        self.assertEqual(stage, before)
        contracts = plan.metadata["authoritativeContracts"]
        self.assertEqual(contracts["stageBounds"], {"size": 310, "changed": False})
        self.assertEqual(contracts["playerSpawns"], before["playerSpawns"])
        self.assertEqual(contracts["botSpawns"], before["botSpawns"])
        self.assertEqual(contracts["approaches"][COMMAND_ID]["start"], (8.0, 84.0))
        self.assertEqual(contracts["approaches"][HANGAR_ID]["end"], (-28.0, -100.0))
        self.assertEqual(plan.metadata["metrics"]["routeViolations"], [])
        self.assertEqual(plan.metadata["metrics"]["spawnViolations"], [])

    def test_exactly_two_unique_landmark_identities_remain(self):
        contract = make_kunren_reference_a22_plan(
            fixture_stage(),
            0,
        ).metadata["landmarkIdentityContract"]
        self.assertEqual(contract["exactCount"], 2)
        self.assertEqual(contract["ids"], [COMMAND_ID, HANGAR_ID])
        self.assertEqual(
            contract["names"],
            ["Command Bastion", "Aerostat Vault Hangar"],
        )
        self.assertFalse(contract["thirdLandmarkAllowed"])

    def test_command_is_a_tiered_buttressed_occupied_fortress(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertTrue(
            {
                "a22.cmd.glacis.south",
                "a22.cmd.glacis.north",
                "a22.cmd.main-portal.interior-back",
                "a22.cmd.main-portal.south-jamb",
                "a22.cmd.main-portal.floor",
                "a22.cmd.occupied-bay.0.back",
                "a22.cmd.occupied-bay.0.frame.header",
                "a22.cmd.monumental-keep.lower-core",
                "a22.cmd.monumental-keep.middle-operations-tier",
                "a22.cmd.monumental-keep.asymmetric-radar-tower",
                "a22.cmd.monumental-keep.battered-shoulder.south",
                "a22.cmd.monumental-keep.south-buttress.0",
                "a22.cmd.monumental-keep.south-operations-bay.0.back",
                "a22.cmd.monumental-keep.south-panel-seam.horizontal.0",
                "a22.cmd.monumental-keep.south-panel-seam.vertical.0",
                "a22.cmd.monumental-keep.south-intake-vent.back",
                "a22.cmd.monumental-keep.south-intake-vent.louver.0",
                "a22.cmd.monumental-keep.south-service-pipe.west",
                "a22.cmd.monumental-keep.south-identification-band",
                "a22.cmd.monumental-keep.south-operations-tower",
                "a22.cmd.monumental-keep.south-operations-tower.middle-operations-tier",
                "a22.cmd.monumental-keep.south-operations-tower.upper-sensor-cabin",
                "a22.cmd.monumental-keep.south-operations-tower.occupied-bay.0.back",
                "a22.cmd.monumental-keep.south-operations-tower.structural-belt.0",
                "a22.cmd.monumental-keep.south-operations-tower.south-load-fin.0",
                "a22.cmd.monumental-keep.south-operations-tower.staffed-service-balcony",
                "a22.cmd.monumental-keep.south-operations-tower.middle-operations-tier.deep-intake-vent.back",
                "a22.cmd.monumental-keep.south-operations-tower.upper-sensor-cabin.short-range-radar-array.0",
                "a22.cmd.monumental-keep.south-occupied-operations-gallery",
                "a22.cmd.monumental-keep.south-occupied-operations-gallery.armoured-cap",
                "a22.cmd.monumental-keep.south-occupied-operations-gallery.occupied-bay.back",
                "a22.cmd.south-curtain.lower-breastwork",
                "a22.cmd.south-curtain.middle-operations-terrace",
                "a22.cmd.south-curtain.upper-command-terrace",
                "a22.cmd.south-curtain.lower-breastwork.battered-buttress.0",
                "a22.cmd.south-curtain.lower-breastwork.deep-occupied-bay.0.back",
                "a22.cmd.south-curtain.upper-operations-bridge",
                "a22.cmd.south-curtain.upper-operations-bridge.deep-occupied-bay.0.back",
                "a22.cmd.south-curtain.upper-operations-bridge.grounded-service-riser.west",
                "a22.cmd.monumental-gate-tower.south",
                "a22.cmd.monumental-gate-tower.south.upper-tier",
                "a22.cmd.monumental-gate-tower.south.occupied-slit.0.back",
                "a22.cmd.monumental-gate-tower.south.formwork-seam.horizontal.0",
                "a22.cmd.monumental-gate-tower.south.deep-intake-vent.back",
                "a22.cmd.monumental-gate-tower.south.deep-intake-vent.louver.0",
                "a22.cmd.monumental-gate-tower.south.fortress-identification-sign",
                "a22.cmd.monumental-gate-tower.south.balcony-spotlight.0",
                "a22.cmd.monumental-gate-tower.south.grime-runoff-relief.0",
                "a22.cmd.monumental-gate-tower.south.west-service-balcony",
                "a22.cmd.monumental-gate-tower.south.external-stair.step.0",
                "a22.cmd.monumental-gate-tower.south.external-service-pipe",
                "a22.cmd.monumental-gate-tower.north",
                "a22.cmd.monumental-overgate-bridge",
                "a22.cmd.main-portal.occupied-checkpoint.console",
                "a22.cmd.main-portal.occupied-checkpoint.guard-torso",
                "a22.cmd.operations-gallery",
                "a22.cmd.crown.long-range-radar.array",
                "a22.cmd.reference-mass.lower-grand-terrace",
                "a22.cmd.reference-mass.lower-grand-terrace.deep-arcade.0.occupied-back",
                "a22.cmd.reference-mass.lower-grand-terrace.continuous-occupied-balcony",
                "a22.cmd.reference-mass.west-terrace-wing",
                "a22.cmd.reference-mass.upper-fortress-terrace",
                "a22.cmd.reference-mass.upper-fortress-terrace.grounded-service-pipe.west",
                "a22.cmd.reference-mass.upper-fortress-terrace.central-sensor-tower",
                "a22.cmd.reference-mass.upper-fortress-terrace.asymmetric-signals-tower",
            }
            <= names
        )

    def test_hangar_portal_has_staffed_crown_headhouse(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        self.assertTrue(
            {
                "a22.hall.portal-crown-headhouse",
                "a22.hall.portal-crown-headhouse.occupied-control-bay.back",
                "a22.hall.portal-crown-headhouse.portal-integration-pier.south",
                "a22.hall.portal-crown-headhouse.door-drive-pod.south",
                "a22.hall.portal-crown-headhouse.door-drive-pod.south.deep-vent.louver.0",
                "a22.hall.portal-crown-headhouse.communications-mast",
                "a22.hall.interior-machine-catwalk.0.grounded-gantry-post.0",
                "a22.hall.portal-shell-web.segment.0",
                "a22.hall.interior-ceiling-practical.0",
                "a22.hall.interior-floor-lane.0",
                "a22.hall.portal-maintenance-stack.south",
                "a22.hall.portal-maintenance-stack.south.service-platform.0",
                "a22.hall.portal-maintenance-stack.south.occupied-bay.0.back",
                "a22.hall.portal-maintenance-stack.south.grounded-frame-post.0",
            }
            <= set(plan.names)
        )

    def test_foreground_ramp_has_surface_only_route_markings(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        self.assertTrue(
            {
                "a22.story.foreground-ramp.center-dash.0",
                "a22.story.foreground-ramp.center-dash.6",
                "a22.story.foreground-ramp.edge-mark.left.0",
                "a22.story.foreground-cargo.0.pallet",
                "a22.story.foreground-cargo.0.armoured-crate.0",
                "a22.story.foreground-cargo.0.armoured-crate.0.armoured-lid",
                "a22.story.foreground-cargo.0.armoured-crate.0.safety-strap",
                "a22.story.foreground-cargo.0.upper-armoured-crate.0",
                "a22.story.foreground-cargo.0.upper-armoured-crate.0.armoured-lid",
                "a22.story.foreground-cargo.2.pallet",
                "a22.story.foreground-blast-position.0",
                "a22.story.foreground-blast-position.0.stacked-supply-crate",
                "a22.story.central-checkpoint.barricade.0",
                "a22.story.reference-foreground.apc-service-pallet",
                "a22.story.reference-foreground.apc-service-pallet.field-generator",
                "a22.story.reference-foreground.apc-supply-crate.0",
                "a22.story.reference-foreground.armoured-approach-surface",
                "a22.story.reference-foreground.armoured-approach-surface.worn-centre-dash.4",
                "a22.story.reference-foreground.armoured-approach-surface.low-edge-curb.left",
            }
            <= set(plan.names)
        )

    def test_command_gate_is_fixed_to_authoritative_west_approach(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        diagnostic = plan.metadata["commandGateAlignmentDiagnostic"]
        self.assertEqual(diagnostic["authoritativeEntrance"], [28.0, 84.0])
        self.assertEqual(
            diagnostic["authoritativeApproachStart"],
            [8.0, 84.0],
        )
        self.assertEqual(
            diagnostic["authoritativeApproachEnd"],
            [28.0, 84.0],
        )
        self.assertEqual(diagnostic["authoritativeApproachWidthM"], 12.0)
        self.assertTrue(all(diagnostic["westFaceContacts"].values()))
        self.assertGreaterEqual(diagnostic["portalOpeningWidthM"], 12.0)
        self.assertGreaterEqual(diagnostic["towerOpeningWidthM"], 12.0)
        self.assertEqual(diagnostic["legacySouthFacePlacementCount"], 0)
        self.assertFalse(any(diagnostic["legacySouthFaceFlags"].values()))
        self.assertEqual(diagnostic["routeAndCollisionMutationCount"], 0)
        self.assertTrue(diagnostic["pass"])

        boxes = {spec.name: spec for spec in plan.boxes}
        west_face = diagnostic["westFaceX"]
        portal = boxes["a22.cmd.main-portal.interior-back"]
        self.assertAlmostEqual(portal.x, west_face + 9.8)
        self.assertAlmostEqual(portal.z, 84.0)
        self.assertLess(portal.w, portal.d)
        for name, expected_z in (
            ("a22.cmd.monumental-gate-tower.south", 67.0),
            ("a22.cmd.monumental-gate-tower.north", 101.0),
        ):
            tower = boxes[name]
            self.assertAlmostEqual(tower.x, west_face + 5.0)
            self.assertAlmostEqual(tower.z, expected_z)

    def test_command_diagnostic_camera_sees_unoccluded_gate_frame(self):
        diagnostic = make_kunren_reference_a22_plan(
            fixture_stage(),
            0,
        ).metadata["commandGateAlignmentDiagnostic"]
        frame = diagnostic["projectedVisibleGateFrame"]
        self.assertTrue(diagnostic["gateFrameVisible"])
        self.assertEqual(diagnostic["gateSightlineBlockers"], [])
        self.assertGreaterEqual(frame["xMin"], 0.0)
        self.assertLessEqual(frame["xMax"], 1.0)
        self.assertGreaterEqual(frame["yMin"], 0.0)
        self.assertLessEqual(frame["yMax"], 1.0)
        self.assertGreaterEqual(frame["screenWidth"], 0.12)
        self.assertGreaterEqual(frame["screenHeight"], 0.12)

    def test_hangar_is_a_working_double_shell_airship_dock(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertTrue(
            {
                "a22.hall.vault-rib.outer.0",
                "a22.hall.vault-rib.deep.0",
                "a22.hall.portal-armour.segment.0",
                "a22.hall.portal-service-tower.south.base",
                "a22.hall.portal-service-tower.south.balcony.0",
                "a22.hall.portal-door.rail.0",
                "a22.hall.crane.longitudinal-rail.0",
                "a22.hall.crane.bridge.0",
                "a22.hall.crane.bridge.0.hoist",
                "a22.hall.aerostat.docking-arm.0",
                "a22.hall.aerostat.docking-cable.0",
                "a22.hall.deep-maintenance-bay.0.back",
                "a22.hall.interior-machine.0.0",
                "a22.hall.interior-machine.0.0.drive-rotor",
                "a22.hall.interior-machine.0.0.warm-worklight",
                "a22.hall.interior-machine-catwalk.0",
                "a22.hall.reference-volume.outer-side-wall.south",
                "a22.hall.reference-volume.inner-service-wall.south",
                "a22.hall.reference-volume.overhead-gantry.0",
                "a22.hall.reference-volume.ceiling-light-row.0",
                "a22.hall.reference-volume.armoured-maintenance-floor",
                "a22.hall.aerostat.enlarged-envelope.body",
                "a22.hall.aerostat.enlarged-envelope.service-band.0",
                "a22.hall.aerostat.enlarged-envelope.occupied-gondola",
            }
            <= names
        )

    def test_city_checkpoint_vehicles_and_people_use_real_geometry(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertTrue(
            {
                "a22.city.block.0.structural-spine",
                "a22.city.block.0.grounded-fin.0",
                "a22.city.block.0.occupied-opening.back",
                "a22.city.block.0.occupied-opening.frame.left",
                "a22.city.block.1.roof-saw.0",
                "a22.city.elevated-service-bridge.north",
                "a22.checkpoint.0.grounded-slab",
                "a22.checkpoint.0.interior-back",
                "a22.checkpoint.0.armoured-canopy",
                "a22.checkpoint.0.canopy-post.0",
                "a22.checkpoint.0.overhead-identification-sign",
                "a22.checkpoint.0.canopy-warning-light.0",
                "a22.checkpoint.0.roof-defence-mount",
                "a22.checkpoint.0.roof-defence-weapon",
                "a22.checkpoint.0.floodlight-mast",
                "a22.checkpoint.0.armoured-barrier-boom",
                "a22.story.foreground-wall.left.pilaster.0.0",
                "a22.story.central-weapon-position.traverse-mount",
                "a22.story.central-weapon-position.armoured-shield",
                "a22.story.vehicle.0.apc.sloped-hood",
                "a22.story.vehicle.0.apc.sloped-side-armour.0",
                "a22.story.vehicle.0.apc.front-glacis",
                "a22.story.vehicle.0.apc.wheel.0.0",
                "a22.story.vehicle.0.apc.wheel-hub.0.0",
                "a22.story.vehicle.0.apc.armoured-wheel-fender.0.0",
                "a22.story.vehicle.0.apc.crew-side-window.0.back",
                "a22.story.vehicle.0.apc.low-profile-turret",
                "a22.story.vehicle.0.apc.turret-weapon",
                "a22.story.vehicle.1.cargo.sloped-hood",
                "a22.story.vehicle.2.radar.mobile-radar-array",
                "a22.story.crew.0.torso",
                "a22.story.crew.0.high-visibility-vest-band",
                "a22.story.crew.0.leg.0",
                "a22.skyline.vegetation.north-east.grounded-trunk",
                "a22.skyline.vegetation.north-east.layered-canopy",
            }
            <= names
        )
        wheel_roles = {
            spec.role
            for spec in plan.cylinders_between
            if spec.name.startswith("a22.story.vehicle.")
        }
        self.assertIn("military-vehicle-rubber-wheel", wheel_roles)
        self.assertIn("military-vehicle-real-axle", wheel_roles)
        boxes = {spec.name: spec for spec in plan.boxes}
        apc = boxes["a22.story.vehicle.0.apc.chassis"]
        self.assertEqual((apc.x, apc.z), (145.0, -150.0))
        cargo = boxes["a22.story.vehicle.1.cargo.chassis"]
        self.assertEqual((cargo.x, cargo.z), (155.0, -120.0))

    def test_role_specific_profiles_are_baked_before_batching(self):
        contract = make_kunren_reference_a22_plan(
            fixture_stage(),
            0,
        ).metadata["roleSpecificGeometryProfileContract"]
        self.assertEqual(
            contract["commandPlinthPortalButtressM"],
            [0.12, 0.24],
        )
        self.assertEqual(contract["districtFacadeM"], [0.05, 0.10])
        self.assertEqual(
            contract["railsVehiclesEquipmentM"],
            [0.01, 0.03],
        )
        self.assertTrue(contract["bakedBeforeBatching"])
        self.assertTrue(contract["singleGlobalBevelForbidden"])
        self.assertTrue(contract["normalNoiseAloneIsNotStructuralRealism"])

    def test_depth_density_is_quantified_and_not_a_claimed_visual_pass(self):
        metrics = make_kunren_reference_a22_plan(
            fixture_stage(),
            0,
        ).metadata["depthDensityMetrics"]
        self.assertEqual(set(metrics["fractions"]), {"near", "mid", "far"})
        self.assertAlmostEqual(sum(metrics["fractions"].values()), 1.0, places=3)
        self.assertGreater(metrics["primitiveCounts"]["near"], 0)
        self.assertGreater(metrics["primitiveCounts"]["mid"], 0)
        self.assertGreater(metrics["primitiveCounts"]["far"], 0)
        self.assertTrue(metrics["diagnosticOnly"])

    def test_lods_reduce_and_keep_explicit_evaluated_triangle_targets(self):
        plans = [
            make_kunren_reference_a22_plan(fixture_stage(), lod) for lod in range(3)
        ]
        counts = [plan.primitive_count for plan in plans]
        estimates = [plan.metadata["metrics"]["estimatedTriangles"] for plan in plans]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(estimates[0], estimates[1])
        self.assertGreater(estimates[1], estimates[2])
        for lod, plan in enumerate(plans):
            budget = A22_LOD_BUDGETS[lod]
            self.assertLessEqual(plan.primitive_count, budget.max_primitives)
            self.assertLessEqual(
                plan.metadata["metrics"]["estimatedTriangles"],
                budget.max_estimated_triangles,
            )
            self.assertLessEqual(
                len(plan.metadata["metrics"]["materials"]),
                budget.max_materials,
            )
            target = plan.metadata["metrics"]["evaluatedTriangleTarget"]
            self.assertEqual(
                (target["min"], target["max"]),
                A22_EVALUATED_TRIANGLE_TARGETS[lod],
            )
            self.assertTrue(plan.metadata["metrics"]["primitiveCountIsNotAQualityGate"])

    def test_all_connections_reference_retained_parts_and_overlap(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        names = set(plan.names)
        self.assertEqual(len(plan.metadata["connectionMap"]), len(plan.connections))
        for connection in plan.connections:
            self.assertIn(connection.parent, names)
            self.assertIn(connection.child, names)
            self.assertGreaterEqual(connection.actual_overlap_m, 0.005)

    def test_reviewed_builder_emits_every_final_primitive(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        builder = RecordingBuilder()
        metadata = emit_kunren_reference_a22_plan(builder, plan)
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

    def test_primary_and_full_proof_require_original_resolution_evidence(self):
        plan = make_kunren_reference_a22_plan(fixture_stage(), 0)
        contract = plan.metadata["privateProofContract"]
        self.assertEqual(contract["defaultDirectory"], str(PRIVATE_PROOF_DEFAULT))
        self.assertEqual(contract["resolution"], [1280, 720])
        self.assertGreaterEqual(contract["minimumViewCount"], 8)
        self.assertTrue(contract["primarySelfReviewRequired"])
        self.assertEqual(len(a22._a22_proof_views()), 8)
        self.assertEqual(len(a22._a22_orthographic_views()), 6)
        self.assertFalse(contract["publicAssetWritesAllowed"])
        self.assertFalse(contract["sourceWritesAllowed"])
        self.assertFalse(contract["gitWritesAllowed"])
        self.assertFalse(contract["uiOrMcpWritesAllowed"])

    def test_producer_score_is_provisional_and_always_no_ship(self):
        scorecard = producer_provisional_scorecard(["/private/tmp/a22/01.png"])
        self.assertTrue(scorecard["producerProvisional"])
        self.assertFalse(scorecard["producerScoreAccepted"])
        self.assertTrue(scorecard["independentReviewerRequired"])
        self.assertFalse(scorecard["referencePassClaimed"])
        self.assertLess(scorecard["average"], scorecard["minimumAverage"])
        self.assertEqual(
            scorecard["releaseDecision"],
            "NO-SHIP_PENDING_INDEPENDENT_REVIEW",
        )

    def test_script_never_targets_public_source_manifest_git_ui_or_mcp(self):
        source = (
            Path(__file__)
            .with_name("stage_kits")
            .joinpath("kunren_reference_a22.py")
            .read_text(encoding="utf-8")
        )
        self.assertNotIn("import build_all_stages", source)
        self.assertNotIn("public/assets/", source)
        self.assertNotIn("src/game/", source)
        self.assertNotIn("git ", source)
        self.assertNotIn("mcp__", source)


if __name__ == "__main__":
    unittest.main()
