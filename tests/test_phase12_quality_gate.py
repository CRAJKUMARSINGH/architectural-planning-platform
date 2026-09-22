"""Phase 12 quality-gate inventory regressions."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase12 import build_report, validate_report  # noqa: E402


class Phase12QualityGateTests(unittest.TestCase):
    def test_all_covered_categories_reference_real_tests(self) -> None:
        report = build_report()
        self.assertFalse(report["missingTestPaths"])
        covered = [item for item in report["categories"] if item["status"] == "covered"]
        self.assertGreaterEqual(len(covered), 10)

    def test_open_gaps_are_explicitly_review_required(self) -> None:
        report = build_report()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            report["pendingCategories"],
            ["playwright-dom-svg-visual-regression", "property-based-geometry"],
        )
        self.assertTrue(report["mergeBlocker"])

    def test_report_signature_detects_tampering(self) -> None:
        report = build_report()
        self.assertEqual(validate_report(report), [])
        report["coveredCategoryCount"] += 1
        self.assertIn("report signature mismatch", validate_report(report))

    def test_fixture_is_json_and_versioned(self) -> None:
        fixture = json.loads(
            (ROOT / "tests/fixtures/phase12/quality_gate_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(fixture["version"], "phase12.quality-gate-contract.v1")
        self.assertTrue(any(item["status"] == "pending" for item in fixture["categories"]))


if __name__ == "__main__":
    unittest.main()