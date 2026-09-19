import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from week24 import (  # noqa: E402
    build_pack,
    build_results,
    validate_pack,
    validate_results,
)
from week23 import signature  # noqa: E402


class Week24ProfessionalReviewTests(unittest.TestCase):
    def test_pack_contains_required_blinded_mix(self):
        pack, answer_key = build_pack()
        self.assertEqual(len(pack["cases"]), 25)
        self.assertEqual(len(answer_key["cases"]), 25)
        self.assertTrue(pack["blinded"])
        self.assertEqual(validate_pack(pack), [])
        self.assertEqual(
            [entry["expectedClass"] for entry in answer_key["cases"]].count("valid"),
            10,
        )
        self.assertEqual(
            [entry["expectedClass"] for entry in answer_key["cases"]].count("defective"),
            10,
        )
        self.assertEqual(
            [entry["expectedClass"] for entry in answer_key["cases"]].count("borderline_or_incomplete"),
            5,
        )

    def test_blinded_cases_do_not_expose_answer_key(self):
        pack, _ = build_pack()
        for case in pack["cases"]:
            self.assertNotIn("expectedClass", case)
            self.assertNotIn("findings", case)
            self.assertIn("model", case)
            self.assertIn("modelSignature", case)

    def test_pending_review_cannot_be_marked_pass(self):
        pack, _ = build_pack()
        results = build_results(pack)
        self.assertEqual(results["status"], "REVIEW_REQUIRED")
        self.assertEqual(results["reviewStatus"], "PENDING_EXTERNAL_REVIEW")
        self.assertEqual(results["completedReviewers"], 0)
        self.assertEqual(validate_results(results, pack), [])

        tampered = copy.deepcopy(results)
        tampered["status"] = "PASS"
        self.assertIn("pending external review cannot be marked PASS", validate_results(tampered, pack))

    def test_pack_and_result_signatures_are_deterministic(self):
        pack_a, _ = build_pack()
        pack_b, _ = build_pack()
        self.assertEqual(pack_a, pack_b)
        self.assertEqual(
            pack_a["packSignature"],
            signature({key: value for key, value in pack_a.items() if key != "packSignature"}),
        )
        result = build_results(pack_a)
        self.assertEqual(
            result["reportSignature"],
            signature({key: value for key, value in result.items() if key != "reportSignature"}),
        )


if __name__ == "__main__":
    unittest.main()