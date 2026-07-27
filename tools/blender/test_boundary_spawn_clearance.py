import ast
import json
import math
import os
from pathlib import Path
import unittest


GENERATOR_PATH = Path(__file__).with_name("build_all_stages.py")
PROFILE_PATH = Path(__file__).with_name("stage-profiles.json")
CANONICAL_LAYOUT_ENV = "HIBANA_CANONICAL_STAGE_LAYOUT"
FROZEN_SOLVER_SHA = "623a752e946fae943b89d43f9442bd03ecc70e146e620b97f83045fb28f64ac9"
PLAYER_CAPSULE_RADIUS_M = 0.35
# Boss/giant humanoids use the largest authored bot capsule radius.
BOT_CAPSULE_RADIUS_M = 0.63
MIN_CAPSULE_CLEARANCE_M = 4.0
MIN_DETAIL_CAPSULE_CLEARANCE_M = 3.5
MIN_INITIAL_VIEW_CLEARANCE_M = 32.0


def load_boundary_helpers():
    function_names = {
        "stable_unit",
        "boundary_natural_sample_count",
        "boundary_primary_specs",
    }
    constant_names = {
        "BOUNDARY_SAMPLE_COUNT",
        "BOUNDARY_CHIKURIN_SAMPLE_COUNT",
        "BOUNDARY_ROCK_SEGMENTS_BY_LOD",
        "BOUNDARY_ROCK_MAX_RADIAL_STRETCH",
        "BOUNDARY_MAX_INWARD_REACH_M",
    }
    tree = ast.parse(GENERATOR_PATH.read_text(encoding="utf-8"), filename=str(GENERATOR_PATH))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constant_names
            for target in node.targets
        ):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in function_names:
            nodes.append(node)
    namespace = {}
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), str(GENERATOR_PATH), "exec"),
        namespace,
    )
    return namespace


def conservative_plan_clearance(spec, x, z, radius, rock_stretch):
    """Distance from a capsule disc to a conservative primary-boundary bound."""
    if spec["kind"] == "rock":
        return (
            math.hypot(x - spec["x"], z - spec["z"])
            - spec["radius"] * rock_stretch
            - radius
        )
    if spec["kind"] == "arch":
        width, depth = spec["width"], spec["depth"]
    else:
        width, depth = spec["w"], spec["d"]
    dx = max(abs(x - spec["x"]) - width / 2, 0.0)
    dz = max(abs(z - spec["z"]) - depth / 2, 0.0)
    return math.hypot(dx, dz) - radius


def ray_circle_hit_distance(origin, direction, center, radius):
    offset_x = origin[0] - center[0]
    offset_z = origin[1] - center[1]
    projection = offset_x * direction[0] + offset_z * direction[1]
    discriminant = projection * projection - (
        offset_x * offset_x + offset_z * offset_z - radius * radius
    )
    if discriminant < 0:
        return None
    root = math.sqrt(discriminant)
    near = -projection - root
    far = -projection + root
    if far < 0:
        return None
    return max(0.0, near)


def ray_aabb_hit_distance(origin, direction, center, width, depth):
    minimum = (center[0] - width / 2, center[1] - depth / 2)
    maximum = (center[0] + width / 2, center[1] + depth / 2)
    near, far = -math.inf, math.inf
    for axis in range(2):
        if abs(direction[axis]) < 1e-9:
            if origin[axis] < minimum[axis] or origin[axis] > maximum[axis]:
                return None
            continue
        inverse = 1.0 / direction[axis]
        first = (minimum[axis] - origin[axis]) * inverse
        second = (maximum[axis] - origin[axis]) * inverse
        if first > second:
            first, second = second, first
        near = max(near, first)
        far = min(far, second)
        if near > far:
            return None
    if far < 0:
        return None
    return max(0.0, near)


def primary_ray_hit_distance(spec, origin, direction, rock_stretch):
    if spec["kind"] == "rock":
        return ray_circle_hit_distance(
            origin,
            direction,
            (spec["x"], spec["z"]),
            spec["radius"] * rock_stretch,
        )
    if spec["kind"] == "arch":
        width, depth = spec["width"], spec["depth"]
    else:
        width, depth = spec["w"], spec["d"]
    return ray_aabb_hit_distance(
        origin,
        direction,
        (spec["x"], spec["z"]),
        width,
        depth,
    )


def tangent_half_extent(spec):
    if spec["kind"] == "rock":
        return spec["radius"]
    if spec["kind"] == "arch":
        return spec["width"] / 2
    return (spec["w"] if spec["side"] < 2 else spec["d"]) / 2


def boundary_lod0_detail_specs(stage, profile, primary_specs, stable_unit):
    """Mirror the LOD0 shoulder rocks and low ramparts added by add_boundary.

    These are deliberately kept in the spawn audit even though the A17 trap
    was caused by a primary LOD1 rock.  Their smaller envelope can sit closer
    to the playable shell than a primary rock, so primary-only checks would
    overstate the true worst-case capsule margin.
    """
    details = []
    for spec in primary_specs:
        if spec["kind"] != "rock":
            continue
        detail_stride = 3 if stage["id"] == "chikurin" else 2
        if spec["index"] % detail_stride == 0:
            shoulder_x = spec["x"] + (
                1.8 + stable_unit(
                    stage["seed"], spec["index"], spec["side"] + 211,
                ) * 2.6
            ) * (1 if spec["side"] in {0, 2} else -1)
            shoulder_z = spec["z"] + (
                stable_unit(
                    stage["seed"], spec["index"], spec["side"] + 212,
                ) - 0.5
            ) * 3.2
            details.append({
                "kind": "rock",
                "side": spec["side"],
                "index": spec["index"],
                "x": shoulder_x,
                "z": shoulder_z,
                "radius": spec["radius"] * 0.72,
            })
        if (
            profile["boundary"] in {
                "hill-ramparts", "range-earthworks", "mountain-base",
            }
            and spec["index"] % 4 == 0
        ):
            details.append({
                "kind": "box",
                "side": spec["side"],
                "index": spec["index"],
                "x": spec["x"],
                "z": spec["z"],
                "w": spec["radius"] * 1.25,
                "d": spec["radius"] * 0.45,
            })
    return details


class BoundarySpawnClearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layout_path = os.environ.get(CANONICAL_LAYOUT_ENV)
        if not layout_path:
            raise unittest.SkipTest(f"{CANONICAL_LAYOUT_ENV} is not set")
        cls.helpers = load_boundary_helpers()
        cls.layout = json.loads(Path(layout_path).read_text(encoding="utf-8"))
        cls.profiles = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))["profiles"]
        cls.stages = cls.layout["stages"]

    def specs(self, stage, lod):
        return self.helpers["boundary_primary_specs"](
            stage,
            lod,
            self.profiles[stage["id"]],
        )

    def obstacle_specs(self, stage, lod):
        primary_specs = self.specs(stage, lod)
        if lod != 0:
            return primary_specs
        return primary_specs + boundary_lod0_detail_specs(
            stage,
            self.profiles[stage["id"]],
            primary_specs,
            self.helpers["stable_unit"],
        )

    def test_frozen_solver_623_covers_all_31_stages(self):
        self.assertEqual(self.layout["placementSource"], "canonical-solver-v2-authoring")
        self.assertEqual(self.layout["placementSolverSha256"], FROZEN_SOLVER_SHA)
        self.assertEqual(len(self.stages), 31)
        self.assertEqual(set(self.profiles), {stage["id"] for stage in self.stages})

    def test_natural_boundary_center_radius_height_are_lod_invariant(self):
        natural_stage_count = 0
        for stage in self.stages:
            lod_specs = [self.specs(stage, lod) for lod in range(3)]
            if not lod_specs[0] or lod_specs[0][0]["kind"] != "rock":
                continue
            natural_stage_count += 1
            self.assertTrue(all(spec["kind"] == "rock" for specs in lod_specs for spec in specs))
            self.assertEqual([len(specs) for specs in lod_specs], [len(lod_specs[0])] * 3)

            def physical_spec(spec):
                return {key: value for key, value in spec.items() if key != "segments"}

            baseline = [physical_spec(spec) for spec in lod_specs[0]]
            self.assertEqual([physical_spec(spec) for spec in lod_specs[1]], baseline, stage["id"])
            self.assertEqual([physical_spec(spec) for spec in lod_specs[2]], baseline, stage["id"])
            self.assertEqual({spec["segments"] for spec in lod_specs[0]}, {10})
            self.assertEqual({spec["segments"] for spec in lod_specs[1]}, {6})
            self.assertEqual({spec["segments"] for spec in lod_specs[2]}, {4})
        self.assertGreaterEqual(natural_stage_count, 10)

        kunren = next(stage for stage in self.stages if stage["id"] == "kunren")
        kunren_lod1 = self.specs(kunren, 1)
        # A17's 24-sample formula produced r=20.994m.  The fixed 42-sample
        # lattice must keep every Kunren primary radius below 13m.
        self.assertLess(max(spec["radius"] for spec in kunren_lod1), 13.0)

    def test_every_player_and_bot_spawn_capsule_and_eye_clear_every_lod(self):
        rock_stretch = self.helpers["BOUNDARY_ROCK_MAX_RADIAL_STRETCH"]
        checked_capsules = 0
        global_primary_minimum = math.inf
        global_obstacle_minimum = math.inf
        for stage in self.stages:
            for lod in range(3):
                primary_specs = self.specs(stage, lod)
                obstacle_specs = self.obstacle_specs(stage, lod)
                for label, radius, spawns in (
                    ("player", PLAYER_CAPSULE_RADIUS_M, stage["playerSpawns"]),
                    ("bot", BOT_CAPSULE_RADIUS_M, stage["botSpawns"]),
                ):
                    for spawn_index, spawn in enumerate(spawns):
                        primary_capsule_clearance = min(
                            conservative_plan_clearance(
                                spec,
                                float(spawn[0]),
                                float(spawn[2]),
                                radius,
                                rock_stretch,
                            )
                            for spec in primary_specs
                        )
                        obstacle_capsule_clearance = min(
                            conservative_plan_clearance(
                                spec,
                                float(spawn[0]),
                                float(spawn[2]),
                                radius,
                                rock_stretch,
                            )
                            for spec in obstacle_specs
                        )
                        eye_clearance = min(
                            conservative_plan_clearance(
                                spec,
                                float(spawn[0]),
                                float(spawn[2]),
                                0.0,
                                rock_stretch,
                            )
                            for spec in obstacle_specs
                        )
                        checked_capsules += 1
                        global_primary_minimum = min(
                            global_primary_minimum,
                            primary_capsule_clearance,
                        )
                        global_obstacle_minimum = min(
                            global_obstacle_minimum,
                            obstacle_capsule_clearance,
                        )
                        self.assertGreaterEqual(
                            primary_capsule_clearance,
                            MIN_CAPSULE_CLEARANCE_M,
                            f"{stage['id']} LOD{lod} {label}[{spawn_index}] primary capsule",
                        )
                        self.assertGreaterEqual(
                            obstacle_capsule_clearance,
                            MIN_DETAIL_CAPSULE_CLEARANCE_M,
                            f"{stage['id']} LOD{lod} {label}[{spawn_index}] complete boundary capsule",
                        )
                        self.assertGreater(
                            eye_clearance,
                            MIN_DETAIL_CAPSULE_CLEARANCE_M,
                            f"{stage['id']} LOD{lod} {label}[{spawn_index}] eye",
                        )
        expected_capsules = sum(
            (len(stage["playerSpawns"]) + len(stage["botSpawns"])) * 3
            for stage in self.stages
        )
        self.assertEqual(checked_capsules, expected_capsules)
        self.assertGreater(checked_capsules, 2400)
        self.assertGreater(global_primary_minimum, 4.3)
        self.assertGreater(global_obstacle_minimum, 3.6)

    def test_every_player_initial_center_view_has_32m_clearance(self):
        rock_stretch = self.helpers["BOUNDARY_ROCK_MAX_RADIAL_STRETCH"]
        checked_rays = 0
        for stage in self.stages:
            for lod in range(3):
                specs = self.obstacle_specs(stage, lod)
                for spawn_index, spawn in enumerate(stage["playerSpawns"]):
                    origin = (float(spawn[0]), float(spawn[2]))
                    length = math.hypot(*origin)
                    self.assertGreater(length, 0.0)
                    direction = (-origin[0] / length, -origin[1] / length)
                    hits = [
                        hit
                        for spec in specs
                        if (hit := primary_ray_hit_distance(
                            spec,
                            origin,
                            direction,
                            rock_stretch,
                        )) is not None
                    ]
                    nearest = min(hits, default=math.inf)
                    checked_rays += 1
                    self.assertGreaterEqual(
                        nearest,
                        MIN_INITIAL_VIEW_CLEARANCE_M,
                        f"{stage['id']} LOD{lod} player[{spawn_index}] initial view",
                    )
        self.assertEqual(checked_rays, 31 * 4 * 3)

        kunren = next(stage for stage in self.stages if stage["id"] == "kunren")
        first = kunren["playerSpawns"][0]
        length = math.hypot(first[0], first[2])
        self.assertEqual((-first[0] / length, -first[2] / length), (-1.0, 0.0))

    def test_boundary_samples_overlap_or_stay_within_authored_micro_gap(self):
        for stage in self.stages:
            for lod in range(3):
                specs = self.specs(stage, lod)
                natural = bool(specs and specs[0]["kind"] == "rock")
                per_side = {
                    side: sorted(
                        (spec for spec in specs if spec["side"] == side),
                        key=lambda spec: spec["index"],
                    )
                    for side in range(4)
                }
                for side, side_specs in per_side.items():
                    for first, second in zip(side_specs, side_specs[1:]):
                        # A missing index on water-facing side 0 is the authored
                        # harbor/lake opening, continuously filled by real water.
                        if second["index"] != first["index"] + 1:
                            self.assertEqual(side, 0)
                            continue
                        tangent_delta = (
                            abs(second["x"] - first["x"])
                            if side < 2
                            else abs(second["z"] - first["z"])
                        )
                        gap = tangent_delta - tangent_half_extent(first) - tangent_half_extent(second)
                        if natural:
                            self.assertLessEqual(gap, 0.0, f"{stage['id']} LOD{lod} side {side}")
                        else:
                            # Masonry boundaries deliberately leave at most an
                            # eight-percent relief joint between solid modules.
                            count = 42 if lod == 0 else 24 if lod == 1 else 14
                            tolerance = float(stage["size"]) / count * 0.081
                            self.assertLessEqual(gap, tolerance + 1e-9)

                if not natural:
                    continue
                # Verify all four natural corners close as overlapping terrain
                # discs. Water openings are mid-side and do not affect corners.
                corners = (
                    (per_side[0][0], per_side[2][0]),
                    (per_side[0][-1], per_side[3][0]),
                    (per_side[1][0], per_side[2][-1]),
                    (per_side[1][-1], per_side[3][-1]),
                )
                for first, second in corners:
                    gap = (
                        math.hypot(first["x"] - second["x"], first["z"] - second["z"])
                        - first["radius"]
                        - second["radius"]
                    )
                    self.assertLessEqual(gap, 0.0, f"{stage['id']} LOD{lod} corner")


if __name__ == "__main__":
    unittest.main()
