import unittest

from tools.blender.a23 import evidence


class BuildCameraIndexTests(unittest.TestCase):
    def test_overrides_take_priority_over_proof_cameras(self):
        proof = ({"name": "CamA", "lensMm": 24.0},)
        overrides = ({"name": "CamA", "lensMm": 50.0},)
        index = evidence.build_camera_index(proof, overrides)
        self.assertEqual(index["CamA"]["lensMm"], 50.0)

    def test_proof_cameras_not_overridden_are_kept(self):
        proof = ({"name": "CamA", "lensMm": 24.0}, {"name": "CamB", "lensMm": 35.0})
        index = evidence.build_camera_index(proof, ({"name": "CamA", "lensMm": 50.0},))
        self.assertEqual(index["CamB"]["lensMm"], 35.0)

    def test_returned_dicts_are_copies(self):
        cam = {"name": "CamA", "lensMm": 24.0}
        index = evidence.build_camera_index((cam,))
        index["CamA"]["lensMm"] = 999.0
        self.assertEqual(cam["lensMm"], 24.0)


class SlugifyCameraNameTests(unittest.TestCase):
    def test_strips_prefix_and_lowercases(self):
        slug = evidence.slugify_camera_name(
            "CAM_Nakaniwa_A21_Eye165_GardenBridge", strip_prefix="CAM_Nakaniwa_A21_"
        )
        self.assertEqual(slug, "eye165_gardenbridge")

    def test_leaves_name_unchanged_if_prefix_does_not_match(self):
        slug = evidence.slugify_camera_name("OtherName", strip_prefix="CAM_Nakaniwa_A21_")
        self.assertEqual(slug, "othername")

    def test_no_prefix_just_lowercases(self):
        self.assertEqual(evidence.slugify_camera_name("SomeCamera"), "somecamera")


class SelectWantedCamerasTests(unittest.TestCase):
    def test_splits_found_and_missing(self):
        index = {"A": {"name": "A"}, "B": {"name": "B"}}
        found, missing = evidence.select_wanted_cameras(["A", "C", "B"], index)
        self.assertEqual([c["name"] for c in found], ["A", "B"])
        self.assertEqual(missing, ["C"])

    def test_empty_wanted_list(self):
        found, missing = evidence.select_wanted_cameras([], {"A": {"name": "A"}})
        self.assertEqual(found, [])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
