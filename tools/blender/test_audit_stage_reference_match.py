import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.blender.audit_stage_reference_match import (
    HUMAN_CATEGORIES,
    audit_stage,
    diagnostic_findings,
    image_metrics,
)


class StageReferenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def image(self, name: str, detailed: bool) -> Path:
        path = self.root / name
        image = Image.new("RGB", (640, 360), (126, 151, 174))
        draw = ImageDraw.Draw(image)
        if detailed:
            for index in range(18):
                x = 10 + index * 34
                height = 80 + (index % 5) * 35
                draw.rectangle((x, 350 - height, x + 25, 350), fill=(130 + index % 3 * 15, 91, 52))
                draw.rectangle((x + 4, 330 - height, x + 20, 340 - height), fill=(210, 170, 105))
            for y in range(200, 350, 18):
                draw.line((0, y, 640, y), fill=(76, 56, 42), width=2)
        else:
            draw.rectangle((180, 170, 460, 350), fill=(86, 72, 61))
        image.save(path)
        return path

    def scorecard(self, path: Path, stage_id: str, reference: Path, render: Path, score: float = 8.0):
        import hashlib

        def sha(item: Path) -> str:
            return hashlib.sha256(item.read_bytes()).hexdigest()

        path.write_text(json.dumps({
            "stageId": stage_id,
            "referenceSha256": sha(reference),
            "renderSha256": sha(render),
            "reviewer": "visual-qa",
            "notes": "Compared at first-person height from the approved camera.",
            "verdict": "SHIP",
            "scores": {category: score for category in HUMAN_CATEGORIES},
        }), encoding="utf-8")

    def test_identical_detailed_images_have_no_diagnostic_findings(self):
        reference = self.image("reference.png", True)
        metrics = image_metrics(reference)
        self.assertEqual([], diagnostic_findings(metrics, metrics))

    def test_empty_blockout_is_flagged_against_detailed_reference(self):
        reference = self.image("reference.png", True)
        render = self.image("render.png", False)
        findings = diagnostic_findings(image_metrics(reference), image_metrics(render))
        self.assertIn("low-full-frame-structural-density", findings)
        self.assertIn("low-play-space-structural-density", findings)

    def test_missing_human_scorecard_never_passes(self):
        reference = self.image("reference.png", True)
        render = self.image("render.png", True)
        result = audit_stage("kairou", reference, render, self.root / "missing.json")
        self.assertFalse(result["ok"])
        self.assertIn("missing-human-scorecard", result["humanReview"]["errors"])

    def test_human_category_below_seven_fails_even_if_average_is_high(self):
        reference = self.image("reference.png", True)
        render = self.image("render.png", True)
        card = self.root / "kairou.json"
        self.scorecard(card, "kairou", reference, render, 9.0)
        raw = json.loads(card.read_text())
        raw["scores"]["humanScale"] = 6.9
        card.write_text(json.dumps(raw), encoding="utf-8")
        result = audit_stage("kairou", reference, render, card)
        self.assertFalse(result["ok"])
        self.assertIn("below-category-gate:humanScale", result["humanReview"]["errors"])

    def test_hash_bound_scorecard_and_identical_render_pass(self):
        reference = self.image("reference.png", True)
        render = self.root / "render.png"
        render.write_bytes(reference.read_bytes())
        card = self.root / "kairou.json"
        self.scorecard(card, "kairou", reference, render, 8.0)
        result = audit_stage("kairou", reference, render, card)
        self.assertTrue(result["ok"])
        self.assertEqual(8.0, result["humanReview"]["average"])

    def test_repository_scorecard_template_matches_required_categories(self):
        template = json.loads(
            Path("tools/blender/stage-reference-scorecard.template.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(HUMAN_CATEGORIES), set(template["scores"]))
        self.assertEqual("NO-SHIP", template["verdict"])


if __name__ == "__main__":
    unittest.main()
