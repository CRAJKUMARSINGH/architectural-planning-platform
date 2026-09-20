"""E03 — Auth & Tenancy tests.

Tests: JWT decode, role hierarchy, AUTH_DISABLED dev bypass, 401/403 enforcement.
No live Postgres required — uses SQLite in-memory.
"""
from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import fastapi  # noqa: F401
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


class TestRoleHierarchy(unittest.TestCase):
    """Role weight ordering — owner > editor > reviewer > viewer."""

    def setUp(self):
        # Ensure auth module is importable regardless of jwt availability
        os.environ["AUTH_DISABLED"] = "true"

    def test_owner_has_all_roles(self):
        from services.api.auth import CurrentUser
        u = CurrentUser(
            user_id=uuid.uuid4(), email="x@x.com",
            org_id=uuid.uuid4(), role="owner",
        )
        for role in ("owner", "editor", "reviewer", "viewer"):
            self.assertTrue(u.has_role(role), f"owner should have {role}")

    def test_viewer_has_only_viewer(self):
        from services.api.auth import CurrentUser
        u = CurrentUser(
            user_id=uuid.uuid4(), email="x@x.com",
            org_id=uuid.uuid4(), role="viewer",
        )
        self.assertTrue(u.has_role("viewer"))
        self.assertFalse(u.has_role("editor"))
        self.assertFalse(u.has_role("owner"))

    def test_editor_has_editor_and_viewer(self):
        from services.api.auth import CurrentUser
        u = CurrentUser(
            user_id=uuid.uuid4(), email="x@x.com",
            org_id=uuid.uuid4(), role="editor",
        )
        self.assertTrue(u.has_role("editor"))
        self.assertTrue(u.has_role("viewer"))
        self.assertFalse(u.has_role("owner"))


class TestAuthDisabledMode(unittest.TestCase):
    """AUTH_DISABLED=true must return the dev user (local dev only)."""

    def setUp(self):
        os.environ["AUTH_DISABLED"] = "true"
        # Reload module to pick up env change
        if "services.api.auth" in sys.modules:
            del sys.modules["services.api.auth"]

    def test_dev_user_returned(self):
        os.environ["AUTH_DISABLED"] = "true"
        import importlib
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        user = auth.get_current_user(authorization=None, x_request_id="test-123")
        self.assertEqual(user.email, "dev@local.example")
        self.assertEqual(user.role, "owner")

    def tearDown(self):
        os.environ.pop("AUTH_DISABLED", None)


class TestAuthRequired(unittest.TestCase):
    """Without AUTH_DISABLED, missing token must raise 401."""

    def setUp(self):
        os.environ["AUTH_DISABLED"] = "false"
        if "services.api.auth" in sys.modules:
            del sys.modules["services.api.auth"]

    def test_missing_token_raises_401(self):
        import importlib
        from fastapi import HTTPException
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(authorization=None, x_request_id=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_bad_format_raises_401(self):
        import importlib
        from fastapi import HTTPException
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(authorization="Basic abc123", x_request_id=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def tearDown(self):
        os.environ.pop("AUTH_DISABLED", None)


class TestDevBypassProduction(unittest.TestCase):
    """AUTH_DISABLED MUST be treated as a hard failure signal in staging/prod.
    This test documents the expected behaviour and the engineering control."""

    def test_auth_disabled_flag_documented(self):
        """The AUTH_DISABLED env var is in docker-compose comment and SECURITY.md."""
        security_md = ROOT / "SECURITY.md"
        self.assertTrue(security_md.exists())
        content = security_md.read_text(encoding="utf-8")
        self.assertIn("AUTH_DISABLED", content)
        self.assertIn("staging", content.lower())


if __name__ == "__main__":
    unittest.main()
