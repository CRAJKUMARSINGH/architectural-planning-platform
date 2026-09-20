import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from drafting_kernel import (  # noqa: E402
    build_report,
    load_recipe_index,
    load_visual_patterns,
    selected_recipe,
)
from week2 import load_canonical_model  # noqa: E402


class DraftingKernelTests(unittest.TestCase):
    def test_recipe_index_has_four_small_project_recipes(self):
        index = load_recipe_index()
        self.assertEqual(
            {"residential", "commercial", "institutional", "industrial"},
            set(index["recipes"]),
        )
        for recipe in index["recipes"].values():
            self.assertTrue(recipe["requiredFacts"])
            self.assertTrue(recipe["optimizationChecks"])

    def test_current_model_selects_institutional_recipe(self):
        model = load_canonical_model()
        recipe = selected_recipe(model, load_recipe_index())
        self.assertEqual(recipe["id"], "institutional")
        self.assertIn("site.access.public", recipe["requiredFacts"])

    def test_visual_patterns_have_safe_boundaries(self):
        patterns = load_visual_patterns()
        self.assertGreaterEqual(len(patterns), 5)
        self.assertTrue(all(pattern["safeAction"] and pattern["mustNotDo"] for pattern in patterns))

    def test_fresh_kernel_report_keeps_weeks_one_to_five_separate(self):
        report = build_report()
        self.assertEqual(report["reportVersion"], "fresh.week01-05.drafting-kernel.v1")
        self.assertEqual(set(report["weeks"]), {"01", "02", "03-04", "05"})
        self.assertTrue(report["kernel"]["presentationCannotOverrideFindings"])
        self.assertTrue(report["visualOptimization"]["patterns"])
        self.assertEqual(report["policy"]["professionalStatus"], "PRELIMINARY / NOT FOR CONSTRUCTION")

    def test_recipe_file_is_valid_json(self):
        path = ROOT / "packages" / "recipes" / "index.json"
        with path.open(encoding="utf-8") as handle:
            self.assertIsInstance(json.load(handle), dict)


if __name__ == "__main__":
    unittest.main()