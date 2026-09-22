"""Phase 13 correlation and observability regressions."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.api.middleware.correlation import (  # noqa: E402
    build_correlation_context,
    response_correlation_headers,
)


class Phase13ObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = ROOT / "tests/fixtures/phase13/observability_contract.json"
        cls.fixture = json.loads(path.read_text(encoding="utf-8"))

    def test_contract_covers_all_plan_measurements(self) -> None:
        self.assertEqual(self.fixture["version"], "phase13.observability-contract.v1")
        self.assertEqual(len(self.fixture["measuredStages"]), 10)
        self.assertIn("revision_creation", self.fixture["measuredStages"])

    def test_context_propagates_safe_ids(self) -> None:
        context = build_correlation_context(
            {
                "x-request-id": "req-123",
                "x-trace-id": "trace-456",
                "x-job-id": "job-7",
                "x-revision-id": "rev-8",
                "x-org-id": "org-9",
            }
        )
        self.assertEqual(context["request_id"], "req-123")
        self.assertEqual(context["trace_id"], "trace-456")
        self.assertEqual(context["revision_id"], "rev-8")
        self.assertEqual(response_correlation_headers(context), {
            "x-request-id": "req-123",
            "x-trace-id": "trace-456",
        })

    def test_invalid_ids_are_replaced_or_dropped(self) -> None:
        context = build_correlation_context(
            {
                "x-request-id": "bad id\\nwith newline",
                "x-trace-id": "bad id",
                "x-job-id": "job-ok",
                "authorization": "Bearer must-not-be-propagated",
                "cookie": "session=secret",
            }
        )
        self.assertRegex(context["request_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(context["trace_id"], context["request_id"])
        self.assertEqual(context["job_id"], "job-ok")
        self.assertNotIn("authorization", context)
        self.assertNotIn("cookie", context)

    def test_security_rules_are_documented(self) -> None:
        self.assertIn(
            "logs do not include authorization or cookie headers",
            self.fixture["securityRules"],
        )


if __name__ == "__main__":
    unittest.main()