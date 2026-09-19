import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from run_benchmark import (  # noqa: E402
    PROFILES,
    build_report,
    generate_model,
    validate_report,
)


class Week25PerformanceTests(unittest.TestCase):
    def test_profiles_match_required_workload_sizes(self):
        report = build_report()
        self.assertEqual({item["profile"] for item in report["profiles"]}, {"small", "medium", "large"})
        for item in report["profiles"]:
            expected = PROFILES[item["profile"]]
            self.assertEqual(item["counts"], {
                key: expected[key] for key in ("floors", "rooms", "openings", "furniture")
            })

    def test_signatures_are_stable_for_identical_inputs(self):
        report = build_report()
        for item in report["profiles"]:
            profile = PROFILES[item["profile"]]
            first = generate_model(profile)
            second = generate_model(profile)
            self.assertEqual(first, second)
            self.assertEqual(item["modelSignature"], __import__("run_benchmark").signature(first))

    def test_no_failures_and_report_validates(self):
        report = build_report()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["acceptance"]["noSilentTimeout"])
        self.assertTrue(report["acceptance"]["noOutOfMemoryFailure"])
        self.assertTrue(report["acceptance"]["noDataLoss"])
        self.assertTrue(report["acceptance"]["repeatedInputsAreDeterministic"])
        self.assertEqual(validate_report(report), [])

    def test_report_does_not_mutate_the_generated_model(self):
        model = generate_model(PROFILES["small"])
        snapshot = copy.deepcopy(model)
        build_report()
        self.assertEqual(model, snapshot)


if __name__ == "__main__":
    unittest.main()