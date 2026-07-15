from __future__ import annotations

import json
import unittest
from pathlib import Path


CONTRACT = Path(__file__).parents[1] / "fixtures" / "five-view-generation-contract.json"


class FiveViewGenerationContractTests(unittest.TestCase):
    def test_contract_contains_required_views_and_visual_rules(self) -> None:
        data = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(data["views"], ["front", "back", "left", "right", "top"])
        self.assertEqual(data["background"]["target_rgb"], [72, 76, 82])
        self.assertIn("realistic colored façade textures", data["appearance"]["facade_materials"])
        self.assertIn("white clay render", data["appearance"]["forbidden_subject_styles"])

    def test_prompt_repeats_mandatory_texture_and_background_constraints(self) -> None:
        prompt = json.loads(CONTRACT.read_text(encoding="utf-8"))["prompt_template"].lower()
        self.assertIn("realistic colored façade textures", prompt)
        self.assertIn("dark neutral-gray studio background", prompt)
        self.assertIn("do not produce a white", prompt)


if __name__ == "__main__":
    unittest.main()
