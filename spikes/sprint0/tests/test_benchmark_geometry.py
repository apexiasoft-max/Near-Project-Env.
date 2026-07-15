from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "benchmark_geometry.py"
SPEC = importlib.util.spec_from_file_location("benchmark_geometry", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class GeometryBenchmarkTests(unittest.TestCase):
    def test_bbox_iou_identical(self) -> None:
        self.assertEqual(MODULE.bbox_iou([0, 0, 2, 2], [0, 0, 2, 2]), 1.0)

    def test_bbox_iou_rejects_zero_area(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.bbox_iou([0, 0, 0, 2], [0, 0, 2, 2])

    def test_repository_fixture_has_five_rows_and_two_methods(self) -> None:
        fixture = Path(__file__).parents[1] / "fixtures" / "geometry-baseline-samples.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        result = MODULE.benchmark(data)
        self.assertEqual(result["sample_count"], 5)
        self.assertIn("floor_count", result["summary"]["height"])
        self.assertIn("shadow", result["summary"]["height"])
        self.assertIn("threshold_bbox", result["summary"]["footprint"])
        self.assertIn("edge_bbox", result["summary"]["footprint"])

    def test_repository_samples_have_reviewed_provider_evidence(self) -> None:
        fixture = Path(__file__).parents[1] / "fixtures" / "geometry-baseline-samples.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(
            data["fixture_status"],
            "provider_aerial_human_reviewed_approximate_not_survey_ground_truth",
        )
        for sample in data["samples"]:
            self.assertEqual(sample["review_status"], "human_reviewed_approximate")
            self.assertIn(sample["height_confidence"], {"low", "medium", "high"})
            self.assertTrue(sample["provider_evidence"].endswith(".png"))
            self.assertTrue(sample["height_evidence"])


if __name__ == "__main__":
    unittest.main()
