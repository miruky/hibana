from __future__ import annotations

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.blender.validate_dense_stage_assets import (
    EXPECTED_GENERATOR_SHA,
    EXPECTED_STAGE_IDS,
    GENERATOR_VERSION,
    accessor_bounds,
    expected_landmark_contracts,
    load_glb_document,
    primitive_triangle_count,
    validate_catalog,
    validate_manifest_contract,
    validate_release,
    validate_thumbnail_contract,
)


VALIDATE_GLB_PATH = Path(__file__).with_name("validate-glb.py")
VALIDATE_GLB_SPEC = importlib.util.spec_from_file_location("hibana_validate_glb", VALIDATE_GLB_PATH)
assert VALIDATE_GLB_SPEC is not None and VALIDATE_GLB_SPEC.loader is not None
VALIDATE_GLB_MODULE = importlib.util.module_from_spec(VALIDATE_GLB_SPEC)
VALIDATE_GLB_SPEC.loader.exec_module(VALIDATE_GLB_MODULE)


def make_profiles() -> dict:
    return {
        "version": 2,
        "profiles": {
            stage_id: {
                "cityProfile": {
                    "archetype": f"city-{stage_id}",
                    "targetBuildingCount": [20, 24],
                },
                "megaLandmarks": [
                    {
                        "id": f"{stage_id}-landmark-a",
                        "dimensionsM": {"width": 100, "depth": 80, "height": 60},
                        "placement": f"placement-{stage_id}-0",
                    },
                    {
                        "id": f"{stage_id}-landmark-b",
                        "dimensionsM": {"width": 110, "depth": 85, "height": 65},
                        "placement": f"placement-{stage_id}-1",
                    },
                ],
            }
            for stage_id in EXPECTED_STAGE_IDS
        },
    }


def make_glb(
    path: Path,
    stage_id: str,
    lod: int,
    triangles: int,
    landmark_ids: tuple[str, str] | None = None,
    archetype: str | None = None,
    target: int = 24,
    include_terrain: bool = True,
    include_landmarks: bool = True,
    generator_version: str = GENERATOR_VERSION,
    generator_sha: str = EXPECTED_GENERATOR_SHA,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    landmark_ids = landmark_ids or (
        f"{stage_id}-landmark-a",
        f"{stage_id}-landmark-b",
    )
    reserved = (1 if include_terrain else 0) + (2 if include_landmarks else 0)
    wall_triangles = max(1, triangles - reserved)
    accessors = []
    meshes = []
    nodes = []

    def extras(material: str) -> dict:
        return {
            "hibanaMaterial": material,
            "hibanaExport": True,
            "hibanaStage": stage_id,
            "hibanaLod": lod,
            "hibanaMegaLandmarks": ",".join(landmark_ids),
            "hibanaCityArchetype": archetype or f"city-{stage_id}",
            "hibanaDenseBuildingTarget": target,
            "hibanaGeneratorVersion": generator_version,
            "hibanaGeneratorSha": generator_sha,
        }

    def add_mesh(name: str, triangle_count: int, bounds: list[float], node_extras: dict) -> None:
        accessor_index = len(accessors)
        accessors.append({
            "count": triangle_count * 3,
            "min": bounds[:3],
            "max": bounds[3:],
        })
        mesh_index = len(meshes)
        meshes.append({"primitives": [{"attributes": {"POSITION": accessor_index}, "mode": 4}]})
        nodes.append({"name": name, "mesh": mesh_index, "extras": node_extras})

    add_mesh(
        f"HB_{stage_id}_LOD{lod}_wall",
        wall_triangles,
        [-10, 0, -10, 10, 10, 10],
        extras("wall"),
    )
    if include_terrain:
        add_mesh(
            f"HB_{stage_id}_LOD{lod}_terrain",
            1,
            [-50, -1, -50, 50, 1, 50],
            extras("terrain"),
        )
    if include_landmarks:
        landmark_bounds = (
            [0, 0, 0, 10, 20, 30],
            [40, 0, 0, 55, 25, 35],
        )
        for landmark_index, landmark_id in enumerate(landmark_ids):
            bounds = landmark_bounds[landmark_index]
            landmark_extras = extras("wall")
            landmark_extras.update({
                "hibanaLandmarkId": landmark_id,
                "hibanaLandmarkIndex": landmark_index,
                "hibanaLandmarkStyle": f"test-style-{landmark_index}",
                "hibanaLandmarkBounds": bounds,
                "hibanaLandmarkTargetDimensionsXYZ": [
                    100 + landmark_index * 10,
                    60 + landmark_index * 5,
                    80 + landmark_index * 5,
                ],
                "hibanaLandmarkPlacement": f"placement-{stage_id}-{landmark_index}",
            })
            add_mesh(
                f"HB_{stage_id}_LOD{lod}_LANDMARK_{landmark_index}_wall",
                1,
                bounds,
                landmark_extras,
            )
    document = {
        "asset": {"version": "2.0"},
        "accessors": accessors,
        "meshes": meshes,
        "nodes": nodes,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "scene": 0,
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    total_length = 12 + 8 + len(payload)
    path.write_bytes(
        struct.pack("<III", 0x46546C67, 2, total_length)
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
    )


def write_glb_document(path: Path, document: dict) -> None:
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    total_length = 12 + 8 + len(payload)
    path.write_bytes(
        struct.pack("<III", 0x46546C67, 2, total_length)
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
    )


def mutate_glb(path: Path, mutate) -> None:
    document = load_glb_document(path)
    mutate(document)
    write_glb_document(path, document)


def make_manifest(
    stage_id: str,
    flag_overrides: dict[str, object] | None = None,
    generator_version: str = GENERATOR_VERSION,
    generator_sha: str = EXPECTED_GENERATOR_SHA,
) -> dict:
    assets = []
    for current_stage_id in EXPECTED_STAGE_IDS:
        entry = {
            "id": f"stage-{current_stage_id}",
            "url": f"stages/{current_stage_id}-lod0.glb",
            "stages": [current_stage_id],
            "instances": [{"position": [0, 0, 0]}],
            "replacesDistantMatte": True,
            "replacesProceduralProps": True,
            "replacesProceduralStageShell": True,
            "stageProvenance": {
                "placementSource": "canonical-solver-v2-authoring",
                "placementSolverSha256": "b" * 64,
                "stageWorldCatalogSha256": "c" * 64,
                "stageLayoutSha256": "d" * 64,
            },
            "lods": [
                {"url": f"stages/{current_stage_id}-lod1.glb", "distance": 260},
                {"url": f"stages/{current_stage_id}-lod2.glb", "distance": 460},
            ],
        }
        if current_stage_id == stage_id and flag_overrides:
            entry.update(flag_overrides)
        assets.append(entry)
    return {
        "version": 1,
        "generatorVersion": generator_version,
        "generatorSha": generator_sha,
        "placementSource": "canonical-solver-v2-authoring",
        "placementSolverSha256": "b" * 64,
        "stageWorldCatalogSha256": "c" * 64,
        "assets": assets,
    }


class DenseStageValidatorTests(unittest.TestCase):
    def test_canonical_layout_overrides_legacy_visual_envelope_contract(self) -> None:
        profile = make_profiles()["profiles"]["renshujo"]
        canonical = {
            "placementSource": "canonical-solver-v2-authoring",
            "landmarkPlacements": [
                {
                    "id": "renshujo-landmark-a",
                    "width": 84,
                    "depth": 64,
                    "height": 58,
                },
                {
                    "id": "renshujo-landmark-b",
                    "width": 90,
                    "depth": 64,
                    "height": 62,
                },
            ],
        }
        contracts = expected_landmark_contracts(profile, canonical)
        self.assertEqual(contracts[0]["targetDimensionsXYZ"], (84.0, 58.0, 64.0))
        self.assertEqual(contracts[1]["targetDimensionsXYZ"], (90.0, 62.0, 64.0))
        self.assertTrue(all(
            item["placement"] == "in-bounds-collision-authoritative"
            for item in contracts
        ))

    def test_runtime_release_layout_overrides_legacy_visual_envelope_contract(self) -> None:
        # This is the release-shape counterpart of the canonical-layout test
        # above: a stage whose runtime-release tools/blender/generated/
        # stage-layouts.json carries populated landmarkPlacements (the same
        # file build_all_stages.py itself reads) must be checked against that
        # collision-authoritative footprint, not against the profile's
        # separate, deliberately larger visualEnvelopeM/free-text placement.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profiles_path = root / "stage-profiles.json"
            manifest_path = root / "aaa/manifest.json"
            layouts_path = root / "stage-layouts.json"
            profiles_path.write_text(json.dumps(make_profiles()), encoding="utf-8")
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(make_manifest("renshujo")), encoding="utf-8")
            layouts_path.write_text(json.dumps({
                "placementSource": "runtime-release",
                "stages": [
                    {
                        "id": "renshujo",
                        "placementSource": "runtime-release",
                        "landmarkPlacements": [
                            {"id": "renshujo-landmark-a", "width": 84, "depth": 64, "height": 58},
                            {"id": "renshujo-landmark-b", "width": 90, "depth": 64, "height": 62},
                        ],
                    },
                ],
            }), encoding="utf-8")
            for lod, triangles in enumerate((100, 45, 12)):
                make_glb(manifest_path.parent / f"stages/renshujo-lod{lod}.glb", "renshujo", lod, triangles)

            def remap_to_runtime_footprint(document: dict) -> None:
                for node in document["nodes"]:
                    extras = node.get("extras", {})
                    index = extras.get("hibanaLandmarkIndex")
                    if index == 0:
                        extras["hibanaLandmarkTargetDimensionsXYZ"] = [84, 58, 64]
                    elif index == 1:
                        extras["hibanaLandmarkTargetDimensionsXYZ"] = [90, 62, 64]
                    if isinstance(index, int):
                        extras["hibanaLandmarkPlacement"] = "in-bounds-collision-authoritative"

            for lod in range(3):
                mutate_glb(manifest_path.parent / f"stages/renshujo-lod{lod}.glb", remap_to_runtime_footprint)

            report = validate_release(
                profiles_path, manifest_path, ["renshujo"], runtime_layouts_path=layouts_path,
            )
            self.assertTrue(report["ok"], report)

            # Reverting just one LOD's baked extras back to the profile's
            # legacy visual-envelope numbers must now fail: for a stage with a
            # populated runtime-release layout, that legacy value is no longer
            # the authoritative contract.
            def remap_back_to_profile(document: dict) -> None:
                for node in document["nodes"]:
                    extras = node.get("extras", {})
                    if extras.get("hibanaLandmarkIndex") == 0:
                        extras["hibanaLandmarkTargetDimensionsXYZ"] = [100, 60, 80]

            mutate_glb(manifest_path.parent / "stages/renshujo-lod0.glb", remap_back_to_profile)
            regressed = validate_release(
                profiles_path, manifest_path, ["renshujo"], runtime_layouts_path=layouts_path,
            )
            self.assertFalse(regressed["ok"])
            self.assertTrue(
                any(
                    "target-dimensions-mismatch" in error
                    for error in regressed["stages"][0]["errors"]
                ),
                regressed["stages"][0]["errors"],
            )

    def release_report(self, mutate_lod0=None, **glb_options) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profiles_path = root / "stage-profiles.json"
            manifest_path = root / "aaa/manifest.json"
            profiles_path.write_text(json.dumps(make_profiles()), encoding="utf-8")
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(make_manifest("renshujo")), encoding="utf-8")
            for lod, triangles in enumerate((100, 45, 12)):
                make_glb(
                    manifest_path.parent / f"stages/renshujo-lod{lod}.glb",
                    "renshujo",
                    lod,
                    triangles,
                    **glb_options,
                )
            if mutate_lod0 is not None:
                mutate_glb(manifest_path.parent / "stages/renshujo-lod0.glb", mutate_lod0)
            # Every other test in this file exercises the legacy profile-only
            # landmark contract and must stay decoupled from whatever the real
            # repository's tools/blender/generated/stage-layouts.json happens
            # to contain for "renshujo" at any given time (today it is empty,
            # so this was previously equivalent by accident, not by contract).
            return validate_release(
                profiles_path, manifest_path, ["renshujo"], runtime_layouts_path=None,
            )

    def test_triangle_modes_are_counted_correctly(self) -> None:
        document = {"accessors": [{"count": 12}, {"count": 7}, {"count": 6}]}
        self.assertEqual(primitive_triangle_count(document, {"indices": 0, "mode": 4}), 4)
        self.assertEqual(primitive_triangle_count(document, {"indices": 1, "mode": 5}), 5)
        self.assertEqual(primitive_triangle_count(document, {"indices": 2, "mode": 6}), 4)
        self.assertEqual(primitive_triangle_count(document, {"indices": 0, "mode": 1}), 0)

    def test_quantized_normalized_position_bounds_are_decoded_before_node_trs(self) -> None:
        document = {
            "accessors": [
                {
                    "componentType": 5122,
                    "normalized": True,
                    "count": 8,
                    "min": [-32767, -16384, 0],
                    "max": [32767, 16384, 32767],
                },
                {
                    "componentType": 5121,
                    "normalized": True,
                    "count": 8,
                    "min": [0, 64, 128],
                    "max": [255, 192, 255],
                },
            ],
        }

        signed = accessor_bounds(document, 0)
        unsigned = accessor_bounds(document, 1)

        self.assertIsNotNone(signed)
        self.assertIsNotNone(unsigned)
        assert signed is not None and unsigned is not None
        self.assertEqual(signed[0][0], -1.0)
        self.assertEqual(signed[1][0], 1.0)
        self.assertAlmostEqual(signed[0][1], -16384 / 32767)
        self.assertAlmostEqual(signed[1][2], 1.0)
        self.assertAlmostEqual(unsigned[0][1], 64 / 255)
        self.assertAlmostEqual(unsigned[1][1], 192 / 255)

    def test_glb_parser_rejects_a_false_declared_length(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stage.glb"
            make_glb(path, "renshujo", 0, 100)
            raw = bytearray(path.read_bytes())
            struct.pack_into("<I", raw, 8, len(raw) + 4)
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "declared-length"):
                load_glb_document(path)

    def test_single_stage_release_passes_exact_lod_ratio_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profiles_path = root / "stage-profiles.json"
            manifest_path = root / "aaa/manifest.json"
            profiles_path.write_text(json.dumps(make_profiles()), encoding="utf-8")
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(make_manifest("renshujo")), encoding="utf-8")
            for lod, triangles in enumerate((100, 45, 12)):
                make_glb(manifest_path.parent / f"stages/renshujo-lod{lod}.glb", "renshujo", lod, triangles)

            report = validate_release(
                profiles_path, manifest_path, ["renshujo"], runtime_layouts_path=None,
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["catalog"]["uniqueLandmarkIds"], 62)
            self.assertEqual(report["stages"][0]["lodRatios"], {"lod1": 0.45, "lod2": 0.12})
            self.assertGreater(report["stages"][0]["lods"][0]["terrainTriangles"], 0)

    def test_mismatch_ratios_size_horizon_and_missing_terrain_are_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profiles_path = root / "stage-profiles.json"
            manifest_path = root / "aaa/manifest.json"
            profiles_path.write_text(json.dumps(make_profiles()), encoding="utf-8")
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(make_manifest("renshujo", {"replacesDistantMatte": False})),
                encoding="utf-8",
            )
            make_glb(
                manifest_path.parent / "stages/renshujo-lod0.glb",
                "renshujo",
                0,
                100,
                landmark_ids=("wrong-a", "wrong-b"),
                include_terrain=False,
            )
            make_glb(manifest_path.parent / "stages/renshujo-lod1.glb", "renshujo", 1, 46)
            make_glb(manifest_path.parent / "stages/renshujo-lod2.glb", "renshujo", 2, 13)
            lod0_size = (manifest_path.parent / "stages/renshujo-lod0.glb").stat().st_size

            report = validate_release(
                profiles_path,
                manifest_path,
                ["renshujo"],
                max_bytes=lod0_size - 1,
                runtime_layouts_path=None,
            )
            errors = report["stages"][0]["errors"]

            self.assertFalse(report["ok"])
            self.assertIn("real-mesh-horizon-flag-not-true", errors)
            self.assertTrue(any("lod0:file-size" in error for error in errors), errors)
            self.assertTrue(any("metadata-mismatch" in error for error in errors), errors)
            self.assertIn("lod0:missing-real-mesh-horizon-terrain", errors)
            self.assertTrue(any(error.startswith("lod1-ratio:") for error in errors), errors)
            self.assertTrue(any(error.startswith("lod2-ratio:") for error in errors), errors)

    def test_catalog_rejects_duplicate_landmark_ids(self) -> None:
        profiles = make_profiles()
        profiles["profiles"]["renshujo"]["megaLandmarks"][1]["id"] = "renshujo-landmark-a"

        report = validate_catalog(profiles)

        self.assertEqual(report["landmarkCount"], 62)
        self.assertEqual(report["uniqueLandmarkIds"], 61)
        self.assertIn("unique-landmark-ids:61!=62", report["errors"])

    def test_manifest_requires_all_three_replacement_flags_to_be_literal_true(self) -> None:
        expected_errors = {
            "replacesDistantMatte": "real-mesh-horizon-flag-not-true",
            "replacesProceduralProps": "procedural-prop-replacement-flag-not-true",
            "replacesProceduralStageShell": "procedural-stage-shell-replacement-flag-not-true",
        }
        for field, expected_error in expected_errors.items():
            for invalid in (False, "true", 1):
                with self.subTest(field=field, invalid=invalid):
                    errors = validate_manifest_contract(make_manifest("renshujo", {field: invalid}))
                    self.assertIn(f"renshujo:{expected_error}", errors)

    def test_manifest_replacement_requires_valid_stage_provenance(self) -> None:
        cases = [
            (None, "stage-provenance-missing"),
            ({
                "placementSource": "canonical-solver-v2-authoring",
                "placementSolverSha256": "b" * 64,
                "stageWorldCatalogSha256": "c" * 64,
            }, "stage-provenance-stage-identity-missing"),
        ]
        for provenance, expected_error in cases:
            with self.subTest(provenance=provenance):
                errors = validate_manifest_contract(make_manifest(
                    "renshujo",
                    {"stageProvenance": provenance},
                ))
                self.assertIn(f"renshujo:{expected_error}", errors)

        invalid = make_manifest("renshujo", {
            "stageProvenance": {
                "placementSource": "canonical-solver-v2-authoring",
                "placementSolverSha256": "not-a-sha",
                "stageWorldCatalogSha256": "c" * 64,
                "stageLayoutSha256": "d" * 64,
            },
        })
        errors = validate_manifest_contract(invalid)
        self.assertIn(
            "renshujo:stage-provenance-placementSolverSha256-invalid",
            errors,
        )

    def test_manifest_requires_exact_31_stage_set_and_current_generator(self) -> None:
        manifest = make_manifest(
            "renshujo",
            generator_version="dense-world-v2",
            generator_sha="0" * 64,
        )
        manifest["assets"].pop()

        errors = validate_manifest_contract(manifest)

        self.assertTrue(any(error.startswith("manifest-generator-version:") for error in errors), errors)
        self.assertIn("manifest-generator-sha-mismatch", errors)
        self.assertIn("manifest-asset-count:30!=31", errors)
        self.assertTrue(any(error.startswith("manifest-stage-ids:missing=renshujo") for error in errors), errors)

    def test_thumbnail_set_must_match_authoritative_31_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            thumbnail_dir = Path(temp)
            for stage_id in EXPECTED_STAGE_IDS[:-1]:
                (thumbnail_dir / f"{stage_id}.webp").touch()
            (thumbnail_dir / "unexpected.webp").touch()

            errors = validate_thumbnail_contract(thumbnail_dir)

            self.assertEqual(len(errors), 1)
            self.assertIn("missing=renshujo", errors[0])
            self.assertIn("extra=unexpected", errors[0])

    def test_legacy_comma_landmark_metadata_alone_is_rejected(self) -> None:
        report = self.release_report(include_landmarks=False)
        errors = report["stages"][0]["errors"]

        self.assertFalse(report["ok"])
        self.assertTrue(any("landmark-id-set:missing=" in error for error in errors), errors)
        self.assertTrue(any("triangles-not-positive" in error for error in errors), errors)

    def test_glb_nodes_require_current_generator_version_and_sha(self) -> None:
        report = self.release_report(generator_version="dense-world-v2", generator_sha="f" * 64)
        errors = report["stages"][0]["errors"]

        self.assertFalse(report["ok"])
        self.assertTrue(any("generator-version:" in error for error in errors), errors)
        self.assertTrue(any("generator-sha-mismatch" in error for error in errors), errors)

    def test_foreign_glb_node_cannot_bypass_generator_provenance(self) -> None:
        def mutate(document: dict) -> None:
            document["nodes"].append({
                "name": "foreign-node",
                "mesh": 0,
                "extras": {
                    "hibanaGeneratorVersion": GENERATOR_VERSION,
                    "hibanaGeneratorSha": "0" * 64,
                },
            })

        report = self.release_report(mutate)
        errors = report["stages"][0]["errors"]

        self.assertFalse(report["ok"])
        self.assertIn("lod0:node[4]:generator-sha-mismatch", errors)

    def test_validate_glb_checks_generator_provenance_on_every_node(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "renshujo-lod0.glb"
            make_glb(path, "renshujo", 0, 100)

            def mutate(document: dict) -> None:
                document["nodes"].append({
                    "name": "foreign-node",
                    "mesh": 0,
                    "extras": {
                        "hibanaGeneratorVersion": GENERATOR_VERSION,
                        "hibanaGeneratorSha": "0" * 64,
                    },
                })

            mutate_glb(path, mutate)
            report = VALIDATE_GLB_MODULE.inspect(path)

            self.assertIn("node[4]:generator-sha", report["metadataErrors"])

    def test_landmark_geometry_requires_positive_triangles_and_valid_bounds(self) -> None:
        def mutate(document: dict) -> None:
            node = next(
                item for item in document["nodes"]
                if item.get("extras", {}).get("hibanaLandmarkIndex") == 0
            )
            primitive = document["meshes"][node["mesh"]]["primitives"][0]
            document["accessors"][primitive["attributes"]["POSITION"]]["count"] = 0
            node["extras"]["hibanaLandmarkBounds"] = [0, 0, 0, 0, 20, 30]

        report = self.release_report(mutate)
        errors = report["stages"][0]["errors"]

        self.assertTrue(any("triangles-not-positive" in error for error in errors), errors)
        self.assertTrue(any("invalid-declared-bounds" in error for error in errors), errors)

    def test_landmark_profile_metadata_and_computed_bounds_must_match(self) -> None:
        def mutate(document: dict) -> None:
            node = next(
                item for item in document["nodes"]
                if item.get("extras", {}).get("hibanaLandmarkIndex") == 0
            )
            node["extras"]["hibanaLandmarkIndex"] = 1
            node["extras"]["hibanaLandmarkTargetDimensionsXYZ"] = [1, 2, 3]
            node["extras"]["hibanaLandmarkPlacement"] = "wrong-placement"
            node["extras"]["hibanaLandmarkBounds"] = [1, 0, 0, 11, 20, 30]

        report = self.release_report(mutate)
        errors = report["stages"][0]["errors"]

        for marker in (
            "index-mismatch",
            "target-dimensions-mismatch",
            "placement-mismatch",
            "declared-bounds-mismatch",
        ):
            self.assertTrue(any(marker in error for error in errors), (marker, errors))

    def test_landmark_bounds_and_centroids_must_be_distinct(self) -> None:
        def mutate(document: dict) -> None:
            nodes = [
                item for item in document["nodes"]
                if isinstance(item.get("extras", {}).get("hibanaLandmarkIndex"), int)
            ]
            first_bounds = list(nodes[0]["extras"]["hibanaLandmarkBounds"])
            nodes[1]["extras"]["hibanaLandmarkBounds"] = first_bounds
            primitive = document["meshes"][nodes[1]["mesh"]]["primitives"][0]
            accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            accessor["min"] = first_bounds[:3]
            accessor["max"] = first_bounds[3:]

        report = self.release_report(mutate)
        errors = report["stages"][0]["errors"]

        self.assertTrue(any("landmark-bounds-not-distinct" in error for error in errors), errors)
        self.assertTrue(any("landmark-centroids-not-distinct" in error for error in errors), errors)

    def test_validate_glb_recognises_new_pbr_surface_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "renshujo-lod0.glb"
            make_glb(path, "renshujo", 0, 100)

            def add_materials(document: dict) -> None:
                document["materials"] = [
                    {
                        "name": f"HBMAT_renshujo_{key}",
                        "pbrMetallicRoughness": {"metallicRoughnessTexture": {"index": 0}},
                        "normalTexture": {"index": 0},
                    }
                    for key in ("wall_warm", "wall_cool", "wall_weathered", "roof", "wood")
                ]

            mutate_glb(path, add_materials)
            report = VALIDATE_GLB_MODULE.inspect(path)

            self.assertEqual(
                set(report["surfaceMaterialKeys"]),
                {"wall_warm", "wall_cool", "wall_weathered", "roof", "wood"},
            )
            self.assertEqual(report["pbrErrors"], [])
            self.assertEqual(report["metadataErrors"], [])

    def test_validate_glb_manifest_rejects_shell_and_generator_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = root / "assets/aaa/manifest.json"
            manifest = make_manifest(
                "renshujo",
                {"replacesProceduralStageShell": "true"},
                generator_sha="0" * 64,
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            for entry in manifest["assets"]:
                for url in [entry["url"], *(lod["url"] for lod in entry["lods"])]:
                    target = manifest_path.parent / url
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.touch()
            thumbnail_dir = root / "assets/stage-thumbs"
            thumbnail_dir.mkdir(parents=True)
            for stage_id in EXPECTED_STAGE_IDS:
                (thumbnail_dir / f"{stage_id}.webp").touch()

            report = VALIDATE_GLB_MODULE.validate_manifest(
                manifest_path,
                [manifest_path.parent / "stages/renshujo-lod0.glb"],
                31,
            )

            self.assertIn("generator-sha-mismatch", report["errors"])
            self.assertIn("stage-renshujo:procedural-stage-shell-gate", report["errors"])


if __name__ == "__main__":
    unittest.main()
