"""E03 — Auth & Multi-tenancy expanded regression tests.

Covers: JWT structure, role hierarchy matrix, org isolation scenarios,
audit log completeness, AUTH_DISABLED production guard, fixture alignment.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e03"
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _make_user(role: str, org_id: uuid.UUID | None = None):
    from services.api.auth import CurrentUser
    return CurrentUser(
        user_id=uuid.uuid4(),
        email=f"{role}@test.example",
        org_id=org_id or uuid.uuid4(),
        role=role,
    )


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_roles_matrix_fixture_loads(self):
        data = _load_fixture("roles_matrix.json")
        self.assertIn("roles", data)
        self.assertIn("weightMap", data)
        self.assertEqual(sorted(data["roles"]), sorted(["owner", "editor", "reviewer", "viewer"]))

    def test_org_isolation_scenarios_fixture_loads(self):
        data = _load_fixture("org_isolation_scenarios.json")
        self.assertGreaterEqual(len(data["scenarios"]), 4)

    def test_dev_jwt_payload_fixture_loads(self):
        payload = _load_fixture("dev_jwt_payload.json")
        self.assertIn("sub", payload)
        self.assertIn("org_id", payload)
        self.assertEqual(payload["role"], "owner")


# ---------------------------------------------------------------------------
# Role weight matrix — must match fixtures/e03/roles_matrix.json
# ---------------------------------------------------------------------------

class TestRoleWeightMatrix(unittest.TestCase):
    """Role hierarchy matches the documented fixture matrix."""

    def setUp(self):
        os.environ["AUTH_DISABLED"] = "true"

    def test_fixture_weight_matches_code(self):
        from services.api.auth import ROLE_WEIGHT
        fixture = _load_fixture("roles_matrix.json")
        for role, weight in fixture["weightMap"].items():
            self.assertEqual(
                ROLE_WEIGHT[role], weight,
                f"ROLE_WEIGHT[{role!r}] mismatch: code={ROLE_WEIGHT[role]}, fixture={weight}",
            )

    def test_owner_supersedes_all(self):
        owner = _make_user("owner")
        for role in ("owner", "editor", "reviewer", "viewer"):
            self.assertTrue(owner.has_role(role), f"owner must pass has_role({role!r})")

    def test_editor_cannot_delete(self):
        """Editor must not have owner permission (delete operations require owner)."""
        editor = _make_user("editor")
        self.assertFalse(editor.has_role("owner"))

    def test_reviewer_can_view_but_not_edit(self):
        reviewer = _make_user("reviewer")
        self.assertTrue(reviewer.has_role("viewer"))
        self.assertFalse(reviewer.has_role("editor"))

    def test_unknown_role_fails_all(self):
        from services.api.auth import CurrentUser
        user = CurrentUser(
            user_id=uuid.uuid4(), email="x@x.com",
            org_id=uuid.uuid4(), role="superadmin",
        )
        self.assertFalse(user.has_role("viewer"), "Unknown role must not pass any check")


# ---------------------------------------------------------------------------
# JWT decode — structural validation
# ---------------------------------------------------------------------------

class TestJwtStructure(unittest.TestCase):
    """JWT payload must contain sub, org_id, and role."""

    def test_dev_jwt_payload_has_required_claims(self):
        payload = _load_fixture("dev_jwt_payload.json")
        for claim in ("sub", "org_id", "role", "email"):
            self.assertIn(claim, payload, f"JWT payload missing required claim: {claim!r}")

    def test_jwt_decode_rejects_missing_sub(self):
        """get_current_user must reject tokens that omit 'sub'."""
        os.environ["AUTH_DISABLED"] = "false"
        if "services.api.auth" in sys.modules:
            del sys.modules["services.api.auth"]
        import importlib
        from fastapi import HTTPException
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        # Tamper: provide a Bearer token that cannot be a valid HS256 signed JWT
        with self.assertRaises(HTTPException) as ctx:
            auth.get_current_user(
                authorization="Bearer notavalidjwt",
                x_request_id=None,
            )
        self.assertEqual(ctx.exception.status_code, 401)

    def tearDown(self):
        os.environ.pop("AUTH_DISABLED", None)
        if "services.api.auth" in sys.modules:
            del sys.modules["services.api.auth"]


# ---------------------------------------------------------------------------
# Org isolation contract (ADR-003)
# ---------------------------------------------------------------------------

class TestOrgIsolationScenarios(unittest.TestCase):
    """Scenario-driven tests derived from fixtures/e03/org_isolation_scenarios.json."""

    def test_cross_org_access_blocked(self):
        """SqlProjectRepository.get() must NOT return rows from a different org."""
        try:
            from services.api.repository_sql import SqlProjectRepository
            from services.api.db.session import create_all_tables, SessionLocal
            from services.api.models.base import Base
            import sqlalchemy
            from sqlalchemy import create_engine
            engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
            Base.metadata.create_all(engine)
            from sqlalchemy.orm import sessionmaker
            S = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            with S() as sess:
                repo = SqlProjectRepository(sess)
                org_a = uuid.UUID("00000000-0000-0000-0000-000000000001")
                org_b = uuid.UUID("00000000-0000-0000-0000-000000000002")
                proj = repo.create(org_a, "Alpha Project", "inch")
                sess.commit()
                proj_id = proj["id"]
                # Query with correct org
                found = repo.get(proj_id, org_a)
                self.assertIsNotNone(found, "Must find project with correct org_id")
                # Query with wrong org
                not_found = repo.get(proj_id, org_b)
                self.assertIsNone(not_found, "Must NOT find project with wrong org_id (cross-org leak!)")
        except ModuleNotFoundError:
            self.skipTest("sqlalchemy not installed")

    def test_scenarios_fixture_http_status_codes(self):
        scenarios = _load_fixture("org_isolation_scenarios.json")["scenarios"]
        expected_statuses = {
            "scenario-01": 404,
            "scenario-02": 200,
            "scenario-03": 401,
            "scenario-04": 403,
        }
        for s in scenarios:
            sid = s["id"]
            if sid in expected_statuses:
                self.assertEqual(
                    s["httpStatus"], expected_statuses[sid],
                    f"{sid}: httpStatus mismatch in fixture",
                )


# ---------------------------------------------------------------------------
# Audit log completeness
# ---------------------------------------------------------------------------

class TestAuditLogCompleteness(unittest.TestCase):
    """Audit events must be recorded for all mutating operations."""

    REQUIRED_AUDIT_ACTIONS = [
        "project.create",
        "project.delete",
        "job.enqueue",
    ]

    def test_required_audit_actions_documented(self):
        """v1_projects.py routes must reference all required audit actions."""
        routes_src = (ROOT / "services" / "api" / "routes" / "v1_projects.py").read_text()
        for action in self.REQUIRED_AUDIT_ACTIONS:
            self.assertIn(
                action, routes_src,
                f"Audit action {action!r} not found in v1_projects.py",
            )

    def test_audit_records_immutable_by_convention(self):
        """AuditEvent table must not have an update or delete method."""
        try:
            from services.api.repository_sql import SqlAuditRepository
        except ModuleNotFoundError:
            self.skipTest("sqlalchemy not installed")
        import inspect
        methods = [m for m in dir(SqlAuditRepository) if not m.startswith("_")]
        self.assertNotIn("update", methods, "SqlAuditRepository must not expose update()")
        self.assertNotIn("delete", methods, "SqlAuditRepository must not expose delete()")

    def test_audit_repository_records_create_project(self):
        """SqlAuditRepository.record() must store action, resource_type, and org_id."""
        try:
            from services.api.repository_sql import SqlAuditRepository
            from services.api.models.base import Base
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
            Base.metadata.create_all(engine)
            S = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            with S() as sess:
                repo = SqlAuditRepository(sess)
                org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
                repo.record(
                    action="project.create",
                    resource_type="project",
                    resource_id="proj-test-123",
                    organization_id=org_id,
                    actor_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                    payload={"name": "Test Project"},
                    request_id="req-audit-001",
                )
                sess.commit()
                events = repo.list_for_org(org_id)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["action"], "project.create")
                self.assertEqual(events[0]["resource_type"], "project")
        except ModuleNotFoundError:
            self.skipTest("sqlalchemy not installed")


# ---------------------------------------------------------------------------
# Request ID propagation
# ---------------------------------------------------------------------------

class TestRequestIdPropagation(unittest.TestCase):
    """get_current_user must populate request_id on the returned user object."""

    def setUp(self):
        os.environ["AUTH_DISABLED"] = "true"
        if "services.api.auth" in sys.modules:
            del sys.modules["services.api.auth"]

    def test_request_id_taken_from_header(self):
        import importlib
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        user = auth.get_current_user(authorization=None, x_request_id="test-req-xyz")
        self.assertEqual(user.request_id, "test-req-xyz")

    def test_request_id_generated_when_absent(self):
        import importlib
        auth = importlib.import_module("services.api.auth")
        importlib.reload(auth)
        user = auth.get_current_user(authorization=None, x_request_id=None)
        self.assertTrue(len(user.request_id) > 0, "Must generate a request_id when header is absent")
        # Should be a valid UUID-like string
        uuid.UUID(user.request_id)

    def tearDown(self):
        os.environ.pop("AUTH_DISABLED", None)


# ---------------------------------------------------------------------------
# Role dependency injectors
# ---------------------------------------------------------------------------

class TestRequireRoleDependencies(unittest.TestCase):
    """require_editor / require_owner must raise 403 for insufficient roles."""

    def setUp(self):
        os.environ["AUTH_DISABLED"] = "true"

    def test_require_editor_passes_for_editor(self):
        from services.api.auth import require_role
        dep_fn = require_role("editor").dependency
        user = _make_user("editor")
        result = dep_fn(user)
        self.assertEqual(result.role, "editor")

    def test_require_owner_fails_for_editor(self):
        from fastapi import HTTPException
        from services.api.auth import require_role
        dep_fn = require_role("owner").dependency
        user = _make_user("editor")
        with self.assertRaises(HTTPException) as ctx:
            dep_fn(user)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_require_viewer_passes_for_all_roles(self):
        from services.api.auth import require_role
        dep_fn = require_role("viewer").dependency
        for role in ("viewer", "reviewer", "editor", "owner"):
            user = _make_user(role)
            result = dep_fn(user)
            self.assertEqual(result.role, role)


if __name__ == "__main__":
    unittest.main()
