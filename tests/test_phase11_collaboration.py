"""Phase 11 collaboration policy and persistence-contract regressions."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.api.collaboration import (  # noqa: E402
    APPROVAL_STATES,
    hash_review_token,
    sanitize_viewpoint,
    validate_anchor,
    validate_approval_transition,
)


class Phase11CollaborationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture_path = ROOT / "tests/fixtures/phase11/collaboration_policy.json"
        cls.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_fixture_matches_policy_contract(self) -> None:
        self.assertEqual(self.fixture["approvalStates"], list(APPROVAL_STATES))
        self.assertIn("render-viewpoint", self.fixture["anchorTypes"])

    def test_review_token_is_one_way_and_bounded(self) -> None:
        token = "review-secret-token"
        digest = hash_review_token(token)
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, token)
        with self.assertRaises(ValueError):
            hash_review_token("")
        with self.assertRaises(ValueError):
            hash_review_token("x" * 513)

    def test_model_anchor_must_exist_on_pinned_revision(self) -> None:
        model = {"spaces": [{"id": "space-library"}], "openings": [{"id": "door-1"}]}
        self.assertEqual(validate_anchor("room", "space-library", model), ("room", "space-library"))
        self.assertEqual(validate_anchor("opening", "door-1", model), ("opening", "door-1"))
        with self.assertRaises(ValueError):
            validate_anchor("room", "space-missing", model)
        self.assertEqual(
            validate_anchor("render-viewpoint", "camera-east", model),
            ("render-viewpoint", "camera-east"),
        )

    def test_approval_transition_requires_reviewable_path(self) -> None:
        self.assertEqual(
            validate_approval_transition("Review", "Preliminary Coordination"),
            "Preliminary Coordination",
        )
        with self.assertRaises(ValueError):
            validate_approval_transition("Draft", "Client Presentation")
        with self.assertRaises(ValueError):
            validate_approval_transition("Not Issuable", "Client Presentation")

    def test_viewpoint_is_bounded_scalar_json(self) -> None:
        self.assertEqual(
            sanitize_viewpoint({"camera": "axonometric-east-front", "level": "FF"}),
            {"camera": "axonometric-east-front", "level": "FF"},
        )
        with self.assertRaises(ValueError):
            sanitize_viewpoint({"camera": ["not", "scalar"]})
        with self.assertRaises(ValueError):
            sanitize_viewpoint({"camera": "x" * 301})

    def test_phase11_schema_and_migration_are_present(self) -> None:
        orm = (ROOT / "services/api/models/orm.py").read_text(encoding="utf-8")
        migration = (ROOT / "services/api/db/migrations/versions/0004_collaboration_review.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("class ReviewLink", orm)
        self.assertIn("class ReviewComment", orm)
        self.assertIn("class ReviewApproval", orm)
        self.assertIn("down_revision = \"0003_user_disabled_at\"", migration)
        self.assertIn("def downgrade()", migration)


if __name__ == "__main__":
    unittest.main()