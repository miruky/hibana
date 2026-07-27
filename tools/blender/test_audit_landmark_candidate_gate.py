from __future__ import annotations

import unittest

try:
    from .audit_landmark_candidate_gate import (
        GateConfig,
        bounds_height_audit,
        component_support_audit,
        entrance_bounds_audit,
        entrance_visibility_audit,
        support_chain_audit,
    )
except ImportError:  # pragma: no cover - supports direct execution
    from audit_landmark_candidate_gate import (
        GateConfig,
        bounds_height_audit,
        component_support_audit,
        entrance_bounds_audit,
        entrance_visibility_audit,
        support_chain_audit,
    )


CONFIG = GateConfig()


class LandmarkCandidateGateTests(unittest.TestCase):
    def test_height_gate_classifies_under_within_and_over(self) -> None:
        self.assertEqual(bounds_height_audit((-5, 0, -5, 5, 7, 5), 10, CONFIG)["status"], "under")
        self.assertEqual(bounds_height_audit((-5, -0.2, -5, 5, 9, 5), 10, CONFIG)["status"], "within")
        self.assertEqual(bounds_height_audit((-5, 0, -5, 5, 12, 5), 10, CONFIG)["status"], "over")

    def test_support_chain_accepts_grounded_wall_and_seated_roof(self) -> None:
        nodes = [
            {"name": "foundation", "bounds": (-5, -0.1, -5, 5, 5.1, 5)},
            {"name": "wall", "bounds": (-4, 4.9, -4, 4, 9.1, 4)},
            {"name": "roof", "bounds": (-5, 8.9, -5, 5, 10.5, 5)},
        ]
        report = support_chain_audit(nodes, CONFIG)
        self.assertEqual(report["unsupportedNodeCount"], 0, report)
        self.assertEqual(report["supportedNodeCount"], 3)

    def test_support_chain_rejects_large_air_gap(self) -> None:
        nodes = [
            {"name": "foundation", "bounds": (-5, -0.1, -5, 5, 2, 5)},
            {"name": "floating-crown", "bounds": (-4, 5, -4, 4, 8, 4)},
        ]
        report = support_chain_audit(nodes, CONFIG)
        self.assertEqual(report["unsupportedNodeCount"], 1, report)
        self.assertEqual(report["unsupported"][0]["nearestGapM"], 3.0)

    def test_component_island_gate_follows_contact_chain_to_ground(self) -> None:
        components = [
            {"name": "base", "bounds": (-2, -0.1, -2, 2, 2, 2)},
            {"name": "column", "bounds": (-0.5, 1.9, -0.5, 0.5, 6, 0.5)},
            {"name": "crown", "bounds": (-3, 5.9, -3, 3, 7, 3)},
            {"name": "floating-sign", "bounds": (8, 5, 8, 10, 6, 10)},
        ]
        report = component_support_audit(components, CONFIG)
        self.assertEqual(report["supportedComponentCount"], 3, report)
        self.assertEqual(report["unsupportedIslandCount"], 1, report)
        self.assertEqual(report["unsupportedComponentCount"], 1, report)

    def test_entrance_visibility_rejects_centerline_obstacle(self) -> None:
        stage = {
            "boxes": [{"x": 0, "y": 1.5, "z": 5, "w": 3, "h": 3, "d": 2}],
        }
        placement = {
            "entrance": [0, 10],
            "approach": {"start": [0, 0], "end": [0, 10], "width": 8},
        }
        report = entrance_visibility_audit(stage, placement, CONFIG)
        self.assertIn("entrance-centerline-blocked", report["errors"])

    def test_entrance_visibility_accepts_open_canonical_lane(self) -> None:
        stage = {
            "boxes": [
                {"x": -4, "y": 1.5, "z": 5, "w": 2, "h": 3, "d": 2},
                {"x": 4, "y": 1.5, "z": 5, "w": 2, "h": 3, "d": 2},
            ],
        }
        placement = {
            "entrance": [0, 10],
            "approach": {"start": [0, 0], "end": [0, 10], "width": 8},
        }
        report = entrance_visibility_audit(stage, placement, CONFIG)
        self.assertEqual(report["errors"], [], report)
        self.assertGreaterEqual(report["clearRayCount"], 1)

    def test_exported_entrance_must_remain_on_visual_perimeter(self) -> None:
        placement = {"entrance": [0, 0]}
        report = entrance_bounds_audit((-10, 0, -10, 10, 20, 10), placement, CONFIG)
        self.assertIn("entrance-too-deep-inside-visual-bounds", report["errors"])


if __name__ == "__main__":
    unittest.main()
