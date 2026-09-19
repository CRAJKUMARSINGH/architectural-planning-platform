import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from week23 import (  # noqa: E402
    MANIFEST_PATH,
    build_report,
    read_json,
    run_benchmark,
    signature,
    validate_report,
)


class Week23AdversarialTests(unittest.TestCase):
    def test_expanded_corpus_has_thirty_cases_and_three_input_groups(self):
        benchmark = run_benchmark()
        self.assertEqual(benchmark["fixtureCount"], 30)
        self.assertEqual(benchmark["groupCounts"], {"valid": 1, "invalid": 25, "incomplete": 5})
        self.assertEqual(benchmark["mutationCoverage"], {
            "geometry": 1,
            "openings": 5,
            "routes": 2,
            "furniture": 3,
            "levels": 2,
            "site": 4,
        })

    def test_all_cases_have_unique_ids_and_expected_contracts(self):
        manifest = read_json(MANIFEST_PATH)
        ids = [case["fixtureId"] for case in manifest["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 15)
        for case in manifest["cases"]:
            expected = case["expectedFinding"]
            self.assertTrue(expected["ruleId"])
            self.assertTrue(expected["affectedObjects"])
            self.assertTrue(expected["evidenceFields"])
            self.assertTrue(expected["correction"])

    def test_every_known_defect_is_detected_without_false_positives(self):
        benchmark = run_benchmark()
        self.assertEqual(benchmark["detectedDefects"], 30)
        self.assertEqual(benchmark["missedDefects"], 0)
        self.assertEqual(benchmark["falsePositives"], 0)
        self.assertEqual(benchmark["falseNegatives"], 0)
        self.assertEqual(benchmark["dangerousFalseNegatives"], 0)
        self.assertEqual(benchmark["ruleIdAccuracy"], 1)
        self.assertEqual(benchmark["affectedGeometryAccuracy"], 1)
        self.assertEqual(benchmark["suggestedCorrectionCompleteness"], 1)

    def test_report_is_deterministic_and_valid(self):
        first = build_report()
        second = build_report()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(validate_report(first), [])
        self.assertEqual(first["reportSignature"], signature({
            key: value for key, value in first.items() if key != "reportSignature"
        }))

    def test_report_tampering_is_detectable(self):
        report = build_report()
        tampered = copy.deepcopy(report)
        tampered["benchmark"]["missedDefects"] = 1
        self.assertNotEqual(
            tampered["reportSignature"],
            signature({key: value for key, value in tampered.items() if key != "reportSignature"}),
        )


if __name__ == "__main__":
    unittest.main()