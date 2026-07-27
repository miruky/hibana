import unittest

from tools.blender.a23 import orphan
from tools.blender.a23.kit import SpecKit
from tools.blender import a23_bridge


def _box_verts_faces(center, size):
    """Build the same 8-vert / 6-quad-face box ``MeshBuilder.add_box_blender``
    emits, so fixtures exercise the exact topology the real generator
    produces (not a simplified stand-in).
    """
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    verts = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return verts, faces


def _append_box(parts, key, center, size):
    part = parts.setdefault(key, {"verts": [], "faces": []})
    base = len(part["verts"])
    verts, faces = _box_verts_faces(center, size)
    part["verts"].extend(verts)
    part["faces"].extend([tuple(index + base for index in face) for face in faces])


class ContactGapTests(unittest.TestCase):
    def test_flush_boxes_touch_with_zero_gap(self):
        # Two 1m cubes sharing the x=0.5 face exactly.
        a = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        b = (1.0, 0.0, 0.0, 2.0, 1.0, 1.0)
        result = orphan.contact_gap(a, b)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["gap"], 0.0, places=6)
        self.assertEqual(result["normalAxis"], 0)

    def test_separated_boxes_report_the_true_gap(self):
        a = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        b = (2.0, 0.0, 0.0, 3.0, 1.0, 1.0)  # 1m gap on x
        result = orphan.contact_gap(a, b)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["gap"], 1.0, places=6)

    def test_corner_only_touch_is_not_a_contact(self):
        # Share only a single edge/corner region on both tangent axes at once
        # -- overlap on the tangent axes is far below the floor, so no axis
        # should qualify as a real face-to-face contact.
        a = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        b = (0.98, 0.98, 1.0, 1.98, 1.98, 2.0)
        result = orphan.contact_gap(a, b, min_overlap_abs_m=0.05, min_overlap_fraction=0.2)
        self.assertIsNone(result)

    def test_overlapping_embedded_boxes_report_negative_gap(self):
        a = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        b = (0.5, 0.0, 0.0, 1.5, 1.0, 1.0)  # overlaps by 0.5m on x
        result = orphan.contact_gap(a, b)
        self.assertIsNotNone(result)
        self.assertLess(result["gap"], 0.0)


class AsymmetricOverlapRegressionTests(unittest.TestCase):
    """Locks in the fix for a confirmed false negative found while sweeping
    z06's own shipped geometry: a 48 m x 3 m x 0.76 m emissive layout-shell
    beam (add_layout_shell -> choose_box_material's box.get("emissive")
    path) that only overlaps a 2 m-wide pillar at its easternmost end
    (embedding by 2.06 m of its own 3 m depth into the pillar) registered as
    fully "supported" -- 0 orphans -- under the original symmetric
    (smaller-of-both) overlap rule, because 2.06 m already exceeded 20% of
    the 2 m pillar's own width. Visually this is exactly the round's
    "long pink emissive slabs fly across the mid-ground with open sky behind
    them" defect: 46 of the beam's 48 m have nothing beneath or beside them.
    """

    def test_huge_beam_barely_touching_a_narrow_pillar_is_not_supported(self):
        # contact_gap alone still finds a technically-valid axis pairing here
        # (the beam's own long axis can itself serve as the "normal"/embed
        # axis, with the pillar fully engulfing the beam's thin cross-section
        # on the two tangent axes) -- that reading is not wrong on its own
        # for a compact object, but it is exactly how a 48 m beam slipped
        # through as "supported" by a 2 m pillar. find_support layers the
        # major-axis guard on top of contact_gap for this reason; it, not
        # contact_gap in isolation, is the real orphan/support decision.
        beam_bounds = (-50.03, 54.47, 6.17, -1.97, 57.53, 6.93)  # 48.06 x 3.06 x 0.76
        pillar = {"key": "wall_weathered", "bounds": (-4.03, 53.97, -0.03, -1.97, 58.03, 11.03)}  # 2.06 x 4.06 x 11.06
        result = orphan.find_support(beam_bounds, [pillar], touch_tolerance_m=0.06)
        self.assertFalse(result["supported"], "a 2.06 m end-embed must not satisfy a 48 m beam's own overlap floor")

    def test_same_pair_is_an_orphan_end_to_end(self):
        parts: dict = {}
        _append_box(parts, "wall_weathered", (-3.0, 56.0, 5.5), (2.06, 4.06, 11.06))
        _append_box(parts, "emissive", (-26.0, 56.0, 6.55), (48.06, 3.06, 0.76))
        report = orphan.audit_mesh_parts(parts)
        self.assertEqual(report["orphanCount"], 1)

    def test_reversed_case_a_small_prop_against_a_much_larger_wall_still_passes(self):
        # The common case (small orphan, large host) must not regress: using
        # the orphan's own (small) extent as the reference makes the
        # required overlap easy to clear, exactly as before.
        wall_bounds = (-20.0, 0.0, -0.1, 20.0, 10.0, 0.1)
        sign_bounds = (-1.0, 4.0, 0.1, 1.0, 5.0, 0.14)
        result = orphan.contact_gap(sign_bounds, wall_bounds)
        self.assertIsNotNone(result)
        self.assertLessEqual(result["gap"], 0.06)


class FindSupportTests(unittest.TestCase):
    def test_candidate_within_tolerance_supports(self):
        bounds = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        candidates = [{"bounds": (1.02, 0.0, 0.0, 2.0, 1.0, 1.0), "key": "wall"}]
        result = orphan.find_support(bounds, candidates, touch_tolerance_m=0.06)
        self.assertTrue(result["supported"])

    def test_nearest_candidate_reported_even_when_too_far(self):
        bounds = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        candidates = [{"bounds": (5.0, 0.0, 0.0, 6.0, 1.0, 1.0), "key": "wall"}]
        result = orphan.find_support(bounds, candidates, touch_tolerance_m=0.06)
        self.assertFalse(result["supported"])
        self.assertIsNotNone(result["contact"])
        self.assertAlmostEqual(result["contact"]["gap"], 4.0, places=6)

    def test_no_plausible_candidate_returns_supported_false_no_contact(self):
        bounds = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        # Diagonally displaced on all 3 axes -> never 2-axis overlaps.
        candidates = [{"bounds": (5.0, 5.0, 5.0, 6.0, 6.0, 6.0), "key": "wall"}]
        result = orphan.find_support(bounds, candidates)
        self.assertFalse(result["supported"])
        self.assertIsNone(result["contact"])


class ExtractComponentsTests(unittest.TestCase):
    def test_two_disjoint_boxes_are_two_components(self):
        verts, faces = _box_verts_faces((0, 0, 0), (1, 1, 1))
        verts2, faces2 = _box_verts_faces((10, 0, 0), (1, 1, 1))
        base = len(verts)
        all_verts = verts + verts2
        all_faces = faces + [tuple(i + base for i in f) for f in faces2]
        components = orphan.extract_components(all_verts, all_faces)
        self.assertEqual(len(components), 2)

    def test_touching_boxes_sharing_exact_vertices_weld_into_one_component(self):
        verts, faces = _box_verts_faces((0, 0, 0), (1, 1, 1))
        verts2, faces2 = _box_verts_faces((1, 0, 0), (1, 1, 1))  # shares the x=0.5 face's verts
        base = len(verts)
        all_verts = verts + verts2
        all_faces = faces + [tuple(i + base for i in f) for f in faces2]
        components = orphan.extract_components(all_verts, all_faces)
        self.assertEqual(len(components), 1)

    def test_component_bounds_match_the_box(self):
        verts, faces = _box_verts_faces((2.0, 3.0, -1.0), (4.0, 2.0, 6.0))
        components = orphan.extract_components(verts, faces)
        self.assertEqual(len(components), 1)
        bounds = components[0]["bounds"]
        self.assertAlmostEqual(bounds[0], 0.0)
        self.assertAlmostEqual(bounds[3], 4.0)
        self.assertAlmostEqual(bounds[1], 2.0)
        self.assertAlmostEqual(bounds[4], 4.0)


class AuditMeshPartsTests(unittest.TestCase):
    def test_emissive_card_flush_against_a_wall_is_not_an_orphan(self):
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        # Card sits directly on the wall's +z face (wall spans z -0.1..0.1).
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.02), (1.0, 0.6, 0.04))
        report = orphan.audit_mesh_parts(parts)
        self.assertEqual(report["orphanCount"], 0)
        self.assertEqual(report["emissiveComponentCount"], 1)

    def test_emissive_card_floating_in_open_sky_is_an_orphan(self):
        # Exactly the round's own defect: a bright card with nothing else in
        # the scene anywhere near it.
        parts: dict = {}
        _append_box(parts, "wall", (-50.0, 1.0, -50.0), (4.0, 2.0, 0.2))
        _append_box(parts, "emissive", (0.0, 8.0, 0.0), (4.0, 8.0, 0.1))
        report = orphan.audit_mesh_parts(parts)
        self.assertEqual(report["orphanCount"], 1)
        self.assertEqual(report["orphans"][0]["key"], "emissive")

    def test_two_nearby_emissive_cards_with_nothing_else_are_both_orphans(self):
        # Neither card may use the other as its supporting surface -- a small
        # (well within touch tolerance) gap between two same-material cards
        # with nothing else nearby is the same defect class as one, not a
        # self-supporting pair.
        parts: dict = {}
        _append_box(parts, "emissive", (0.0, 5.0, 0.0), (1.0, 1.0, 0.1))
        _append_box(parts, "emissive", (1.02, 5.0, 0.0), (1.0, 1.0, 0.1))  # 0.02m gap
        report = orphan.audit_mesh_parts(parts)
        self.assertEqual(report["orphanCount"], 2)

    def test_emissive_lamp_resting_on_top_of_a_bracket_is_supported(self):
        # A "resting" contact (normal axis = Y) rather than a "mounted"
        # contact (normal axis = the card's thin depth axis) must also pass.
        parts: dict = {}
        _append_box(parts, "trim", (0.0, 2.0, 0.0), (0.5, 0.1, 0.5))  # bracket top at y=2.05
        _append_box(parts, "emissive", (0.0, 2.05 + 0.15, 0.0), (0.3, 0.3, 0.3))  # sits at y=2.05..2.35
        report = orphan.audit_mesh_parts(parts)
        self.assertEqual(report["orphanCount"], 0)

    def test_gap_just_over_tolerance_is_still_an_orphan(self):
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        # Wall's +z face is at 0.1; leave a 0.10m gap, well past the 0.06m default tolerance.
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.10 + 0.02), (1.0, 0.6, 0.04))
        report = orphan.audit_mesh_parts(parts)
        self.assertEqual(report["orphanCount"], 1)
        self.assertAlmostEqual(report["orphans"][0]["nearestGapM"], 0.10, delta=0.001)


class AssertNoOrphanEmissiveTests(unittest.TestCase):
    def test_raises_with_details_on_violation(self):
        parts: dict = {}
        _append_box(parts, "emissive", (0.0, 8.0, 0.0), (4.0, 8.0, 0.1))
        with self.assertRaises(RuntimeError) as context:
            orphan.assert_no_orphan_emissive(parts, context="HB_test_LOD0")
        self.assertIn("orphan emissive", str(context.exception))
        self.assertIn("HB_test_LOD0", str(context.exception))

    def test_passes_silently_and_returns_a_report_when_clean(self):
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.02), (1.0, 0.6, 0.04))
        report = orphan.assert_no_orphan_emissive(parts)
        self.assertEqual(report["orphanCount"], 0)


class AuditSpecsTests(unittest.TestCase):
    """Exercises the spec-list front end against a23_bridge's own
    GENERIC_SPEC_KIT -- the same kit ``plan_district_infill`` uses -- so this
    proves the dry-run path a district-infill plan can call before any bpy
    geometry exists.
    """

    KIT: SpecKit = SpecKit(
        box=a23_bridge._box, chamfer_box=a23_bridge._chamfer_box, panel=a23_bridge._panel,
        sweep=a23_bridge._sweep, cylinder=a23_bridge._cylinder, leaf_cluster=a23_bridge._leaf_cluster,
        spec_bounds=a23_bridge.spec_bounds, estimated_triangles=a23_bridge.estimated_triangles,
        project_spec_frame=a23_bridge.project_spec_frame,
    )

    def test_floating_emissive_spec_is_flagged(self):
        specs: list = []
        self.KIT.box(specs, "sign", "wall", "g", -50.0, 1.0, -50.0, 4.0, 2.0, 0.2)
        self.KIT.box(specs, "glow-card", "emissive", "g", 0.0, 8.0, 0.0, 4.0, 8.0, 0.1)
        report = orphan.audit_specs(specs, kit=self.KIT)
        self.assertEqual(report["orphanCount"], 1)
        self.assertEqual(report["orphans"][0]["role"], "glow-card")

    def test_seated_emissive_spec_passes(self):
        specs: list = []
        self.KIT.box(specs, "wall", "wall", "g", 0.0, 1.0, 0.0, 4.0, 2.0, 0.2)
        self.KIT.box(specs, "glow-card", "emissive", "g", 0.0, 1.0, 0.1 + 0.02, 1.0, 0.6, 0.04)
        report = orphan.audit_specs(specs, kit=self.KIT)
        self.assertEqual(report["orphanCount"], 0)


class RemediatePartsTests(unittest.TestCase):
    def test_small_gap_is_seated_flush_and_audit_passes_afterward(self):
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        # Wall's +z face is at 0.1; leave a 0.2m gap (within the 0.5m seat ceiling).
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.2 + 0.02), (1.0, 0.6, 0.04))
        before = orphan.audit_mesh_parts(parts)
        self.assertEqual(before["orphanCount"], 1)

        new_parts, report = orphan.remediate_parts(parts)
        self.assertEqual(report["seatedCount"], 1)
        self.assertEqual(report["bracedCount"], 0)
        after = orphan.audit_mesh_parts(new_parts)
        self.assertEqual(after["orphanCount"], 0)
        # The emissive component must still exist (moved, not dropped).
        self.assertEqual(after["emissiveComponentCount"], 1)

    def test_large_gap_is_braced_never_deleted_and_audit_passes_afterward(self):
        # Deletion is unsafe in general: add_layout_shell renders TypeScript
        # collision boxes 1:1, so removing the visual mesh for an orphan that
        # happens to be collision-authoritative would desync the shipped
        # GLB from the still-active (invisible) collider. Bracing with new
        # support pylons is the universally-safe fallback -- it never
        # deletes or moves the orphan's own geometry.
        parts: dict = {}
        _append_box(parts, "wall", (-50.0, 1.0, -50.0), (4.0, 2.0, 0.2))
        # Blender Z (the third bounds axis) is this codebase's vertical axis
        # (runtime_point maps runtime height -> Blender Z); an elevated,
        # isolated card needs a high Z-centre for _brace_pylon_bounds to have
        # something to bridge.
        _append_box(parts, "emissive", (0.0, 0.0, 8.0), (4.0, 0.1, 1.0))  # nothing nearby, 7.5m off the ground
        before = orphan.audit_mesh_parts(parts)
        self.assertEqual(before["orphanCount"], 1)

        new_parts, report = orphan.remediate_parts(parts)
        self.assertEqual(report["seatedCount"], 0)
        self.assertEqual(report["bracedCount"], 1)
        self.assertGreater(report["bracePylonCount"], 0)
        # The orphan's own geometry is untouched, byte-for-byte.
        self.assertEqual(new_parts["emissive"]["verts"], parts["emissive"]["verts"])
        self.assertEqual(new_parts["emissive"]["faces"], parts["emissive"]["faces"])
        after = orphan.audit_mesh_parts(new_parts)
        self.assertEqual(after["orphanCount"], 0)
        self.assertEqual(after["emissiveComponentCount"], 1)
        # New pylon geometry landed in the configured material ("trim" by default).
        self.assertGreater(len(new_parts["trim"]["verts"]), 0)

    def test_already_seated_component_is_left_untouched(self):
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.02), (1.0, 0.6, 0.04))
        new_parts, report = orphan.remediate_parts(parts)
        self.assertEqual(report["seatedCount"], 0)
        self.assertEqual(report["bracedCount"], 0)
        self.assertEqual(new_parts["emissive"]["verts"], parts["emissive"]["verts"])

    def test_input_parts_are_never_mutated(self):
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.2 + 0.02), (1.0, 0.6, 0.04))
        original_verts = list(parts["emissive"]["verts"])
        orphan.remediate_parts(parts)
        self.assertEqual(parts["emissive"]["verts"], original_verts)

    def test_one_seated_and_one_braced_in_the_same_material_batch(self):
        # Two independent emissive boxes sharing the same "emissive" merged
        # part -- the real MeshBuilder.parts layout. Verifies translating one
        # component does not disturb the other component's own vertices in
        # the same flat per-material list.
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.2 + 0.02), (1.0, 0.6, 0.04))  # seatable
        _append_box(parts, "emissive", (500.0, 500.0, 8.0), (1.0, 0.6, 1.0))  # far away and elevated -> brace

        new_parts, report = orphan.remediate_parts(parts)
        self.assertEqual(report["seatedCount"], 1)
        self.assertEqual(report["bracedCount"], 1)
        after = orphan.audit_mesh_parts(new_parts)
        self.assertEqual(after["orphanCount"], 0)
        self.assertEqual(after["emissiveComponentCount"], 2)
        # Every face index must stay valid (translation never touches faces).
        vertex_count = len(new_parts["emissive"]["verts"])
        for face in new_parts["emissive"]["faces"]:
            for index in face:
                self.assertLess(index, vertex_count)
                self.assertGreaterEqual(index, 0)

    def test_seated_component_keeps_its_own_shape(self):
        # Translation must move all 8 corners together (rigid translation),
        # not distort the box.
        parts: dict = {}
        _append_box(parts, "wall", (0.0, 1.0, 0.0), (4.0, 2.0, 0.2))
        _append_box(parts, "emissive", (0.0, 1.0, 0.1 + 0.2 + 0.02), (1.0, 0.6, 0.04))
        new_parts, _report = orphan.remediate_parts(parts)
        components = orphan.extract_components(new_parts["emissive"]["verts"], new_parts["emissive"]["faces"])
        self.assertEqual(len(components), 1)
        bounds = components[0]["bounds"]
        size = tuple(round(bounds[axis + 3] - bounds[axis], 4) for axis in range(3))
        self.assertEqual(size, (1.0, 0.6, 0.04))

    def test_braced_component_at_grade_already_gets_no_pylons(self):
        # A ground-level orphan (nothing to bridge) must not crash or invent
        # a zero/negative-height pylon; it is simply left un-braced (and, per
        # the module's own note, should not have been an orphan at all if
        # the floor plane were in the candidate pool -- this test only
        # exercises _brace_pylon_bounds' own boundary condition).
        parts: dict = {}
        _append_box(parts, "emissive", (0.0, 0.02, 0.0), (1.0, 1.0, 0.04))  # bottom essentially at grade
        new_parts, report = orphan.remediate_parts(parts)
        self.assertEqual(report["bracedCount"], 1)
        self.assertEqual(report["braced"][0]["bracePylonCount"], 0)
        self.assertNotIn("trim", new_parts)


if __name__ == "__main__":
    unittest.main()
