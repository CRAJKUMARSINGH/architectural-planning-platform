"""Phase 4 authentication and tenancy regression tests.

These tests deliberately exercise the policy boundary without requiring a live
OIDC provider or Postgres.  The real provider is covered by PyJWT's JWKS client
in ``services.api.auth``; membership authority is exercised with a tiny query
double so the role decision remains deterministic.
"""
from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "phase4" / "authentication_policy.json"
sys.path.insert(0, str(ROOT))


class _Result:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _Session:
    def __init__(self, row):
        self.row = row

    def execute(self, _query):
        return _Result(self.row)


def _user(role="owner"):
    from services.api.auth import CurrentUser

    return CurrentUser(
        user_id=uuid.uuid4(),
        email="phase4@example.test",
        org_id=uuid.uuid4(),
        role=role,
    )


class TestPhase4Fixture(unittest.TestCase):
    def test_policy_fixture_covers_required_security_signals(self):
        policy = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(policy["phase"], "phase4-authentication-and-tenancy")
        self.assertIn("key_rotation", policy["requiredTokenValidation"])
        self.assertIn("disabled_user", policy["denyCases"])


class TestTokenPolicy(unittest.TestCase):
    def test_unknown_role_is_rejected_before_authorization(self):
        from fastapi import HTTPException

        from services.api import auth

        with (
            patch.object(auth, "_decode_jwt", return_value={
                "sub": str(uuid.uuid4()),
                "org_id": str(uuid.uuid4()),
                "role": "administrator",
                "exp": 9999999999,
            }),
            self.assertRaises(HTTPException) as context,
        ):
            auth.get_current_user("Bearer token", "request-1")
        self.assertEqual(context.exception.status_code, 401)

    def test_disabled_claim_is_forbidden(self):
        from fastapi import HTTPException

        from services.api import auth

        with (
            patch.object(auth, "_decode_jwt", return_value={
                "sub": str(uuid.uuid4()),
                "org_id": str(uuid.uuid4()),
                "role": "viewer",
                "disabled": True,
                "exp": 9999999999,
            }),
            self.assertRaises(HTTPException) as context,
        ):
            auth.get_current_user("Bearer token", "request-2")
        self.assertEqual(context.exception.status_code, 403)

    def test_production_rejects_development_secret_configuration(self):
        from services.api import auth

        with patch.object(auth, "ENVIRONMENT", "production"), \
                patch.object(auth, "AUTH_DISABLED", False), \
                patch.object(auth, "OIDC_ISSUER", ""), \
                patch.object(auth, "JWT_SECRET", auth.DEFAULT_DEV_SECRET):
            self.assertTrue(auth.auth_configuration_errors())

    def test_startup_guard_raises_for_invalid_configuration(self):
        from services.api import auth

        with (
            patch.object(auth, "ENVIRONMENT", "production"),
            patch.object(auth, "AUTH_DISABLED", True),
            self.assertRaises(RuntimeError),
        ):
            auth.assert_auth_configuration()


class TestMembershipAuthority(unittest.TestCase):
    def test_membership_role_replaces_higher_token_role(self):
        from fastapi import HTTPException

        from services.api.authorization import require_membership_role

        dependency = require_membership_role("editor").dependency
        user = _user("owner")
        with self.assertRaises(HTTPException) as context:
            dependency(user, _Session(("viewer", None, None)))
        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(user.role, "viewer")

    def test_disabled_membership_is_denied(self):
        from fastapi import HTTPException

        from services.api.authorization import require_membership_role

        dependency = require_membership_role("viewer").dependency
        with self.assertRaises(HTTPException) as context:
            dependency(_user("viewer"), _Session(("viewer", object(), None)))
        self.assertEqual(context.exception.status_code, 403)

    def test_missing_membership_is_denied(self):
        from fastapi import HTTPException

        from services.api.authorization import require_membership_role

        dependency = require_membership_role("viewer").dependency
        with self.assertRaises(HTTPException) as context:
            dependency(_user("owner"), _Session(None))
        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
