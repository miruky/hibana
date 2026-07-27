import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.blender.audit_blender_render_set import audit_render_set, inspect_render


class BlenderRenderSetAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def detailed_image(self, path: Path, shift: int = 0) -> None:
        image = Image.new("RGB", (640, 360), (112 + shift, 142, 168))
        draw = ImageDraw.Draw(image)
        for index in range(24):
            x = index * 28 - 8
            height = 90 + (index * 37 + shift) % 180
            draw.rectangle((x, 350 - height, x + 20, 350), fill=(95 + index % 5 * 18, 73, 51))
            draw.line((x, 350 - height, x + 20, 350 - height), fill=(230, 200, 150), width=3)
        for y in range(170, 360, 16):
            draw.line((0, y, 640, y + shift % 7), fill=(55, 45, 40), width=2)
        image.save(path)

    def test_uniform_wall_frame_is_rejected(self):
        path = self.root / "wall.png"
        Image.new("RGB", (640, 360), (76, 87, 94)).save(path)
        report = inspect_render(path)
        self.assertFalse(report["ok"])
        self.assertIn("probable-camera-inside-or-facing-wall", report["findings"])

    def test_large_black_lower_void_is_rejected(self):
        path = self.root / "black-void.png"
        self.detailed_image(path)
        image = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 270, 639, 359), fill=(0, 0, 0))
        image.save(path)
        report = inspect_render(path)
        self.assertFalse(report["ok"])
        self.assertIn("large-border-connected-black-void", report["findings"])
        self.assertGreater(
            report["metrics"]["borderConnectedNearBlackVoidRatio"],
            0.10,
        )

    def test_large_white_lower_void_is_rejected(self):
        path = self.root / "white-void.png"
        self.detailed_image(path)
        image = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 250, 639, 359), fill=(255, 255, 255))
        image.save(path)
        report = inspect_render(path)
        self.assertFalse(report["ok"])
        self.assertIn("large-border-connected-white-void", report["findings"])
        self.assertGreater(
            report["metrics"]["borderConnectedNearWhiteVoidRatio"],
            0.15,
        )

    def test_repeated_near_black_facade_grid_is_rejected(self):
        path = self.root / "window-grid.png"
        self.detailed_image(path)
        image = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(image)
        # A mid-value facade with two copied rows of small black cards. The
        # rest of the frame remains detailed, so blank/wall heuristics alone
        # cannot be responsible for the failure.
        draw.rectangle((64, 35, 575, 245), fill=(132, 126, 116))
        for row in range(2):
            for column in range(7):
                x = 90 + column * 68
                y = 70 + row * 82
                draw.rectangle((x, y, x + 25, y + 31), fill=(3, 4, 4))
        image.save(path)
        report = inspect_render(path)
        self.assertFalse(report["ok"])
        self.assertIn("repeated-near-black-facade-grid", report["findings"])
        self.assertGreaterEqual(report["metrics"]["darkFacadeGrid"]["candidateCount"], 8)

    def test_complete_unique_eight_view_set_passes_technical_gate(self):
        for index in range(8):
            label = "eye165" if index < 4 else "aerial"
            self.detailed_image(self.root / f"{index:02d}-{label}.png", shift=index)
        report = audit_render_set(self.root)
        self.assertTrue(report["ok"], report)

    def test_missing_eye_height_and_duplicate_frames_fail(self):
        source = self.root / "00-aerial.png"
        self.detailed_image(source)
        payload = source.read_bytes()
        for index in range(1, 8):
            (self.root / f"{index:02d}-aerial.png").write_bytes(payload)
        report = audit_render_set(self.root)
        self.assertFalse(report["ok"])
        self.assertIn("duplicate-render-frame", report["setFindings"])
        self.assertIn("insufficient-eye-height-views:0:4", report["setFindings"])


if __name__ == "__main__":
    unittest.main()
