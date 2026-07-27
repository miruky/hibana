from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

try:
    from .validate_texture_signal import validate
except ImportError:  # pragma: no cover - supports direct execution
    from validate_texture_signal import validate


def write_rgb(path: Path, pixels: list[tuple[int, int, int]], size: tuple[int, int] = (2, 2)) -> None:
    image = Image.new("RGB", size)
    image.putdata(pixels)
    image.save(path)


class TextureSignalTest(unittest.TestCase):
    def test_rejects_black_generated_pbr_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("T_Wall_BC.png", "T_Wall_N.png", "T_Wall_ORM.png"):
                Image.new("RGB", (4, 4), (0, 0, 0)).save(root / name)
            report = validate([str(root)])
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failureCount"], 3)

    def test_accepts_textured_base_normal_and_orm(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_rgb(root / "T_Wall_BC.png", [(35, 44, 49), (81, 70, 56), (122, 94, 61), (58, 77, 69)])
            write_rgb(root / "T_Wall_N.png", [(121, 129, 249), (132, 123, 252), (126, 136, 246), (137, 119, 250)])
            write_rgb(root / "T_Wall_ORM.png", [(210, 88, 12), (198, 145, 24), (225, 112, 17), (190, 172, 31)])
            report = validate([str(root)])
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["failureCount"], 0)

    def test_rejects_invalid_normal_and_clipped_roughness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_rgb(root / "T_Bad_N.png", [(120, 128, 4), (130, 125, 8), (124, 132, 5), (136, 119, 7)])
            write_rgb(root / "T_Bad_ORM.png", [(20, 255, 30), (60, 255, 90), (110, 255, 160), (170, 255, 220)])
            report = validate([str(root)])
            self.assertEqual(report["status"], "FAIL")
            issues = " ".join(issue for result in report["textures"] for issue in result["issues"])
            self.assertIn("blue-channel", issues)
            self.assertIn("roughness", issues)

    def test_accepts_flat_tangent_space_normal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            Image.new("RGB", (4, 4), (128, 128, 255)).save(root / "T_FlatNormal.png")
            report = validate([str(root)])
            self.assertEqual(report["status"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
