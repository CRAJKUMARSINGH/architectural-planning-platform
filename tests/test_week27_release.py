import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from week27 import (  # noqa: E402
    build_report,
    release_classification,
    signature,
    validate_report,
)


class Week27ReleaseTests(unittest.TestCase):
    def test_release_classification_is_conservative(self):
        self.assertEqual(release_classification("BLOCKED"), "BLOCKED")
        self.assertEqual(release_classification("REVIEW_REQUIRED"), "REVIEW_REQUIRED")
        self.assertEqual(
            release_classification("PASS"),
            "PRELIMINARY_COORDINATION_READY",
        )

    def test_current_release_keeps_professional_review_visible(self):
        report = build_report()
        self.assertEqual(report["releaseClassification"], "REVIEW_REQUIRED")
        self.assertFalse(report["releaseReady"])
        self.assertFalse(report["issuable"])
        self.assertTrue(report["knownLimitations"])
        self.assertTrue(any(item["category"] == "independent-professional-review"
                            for item in report["knownLimitations"]))
        self.assertEqual(validate_report(report), [])

    def test_report_signature_is_deterministic(self):
        report = build_report()
        self.assertEqual(
            report["reportSignature"],
            signature({key: value for key, value in report.items()
                       if key != "reportSignature"}),
        )

    def test_tampered_report_is_rejected(self):
        report = build_report()
        tampered = copy.deepcopy(report)
        tampered["releaseReady"] = True
        self.assertIn("reportSignature does not match report contents",
                      validate_report(tampered))


if __name__ == "__main__":
    unittest.main()