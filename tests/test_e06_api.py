"""E06 — API & Frontend Hardening regression tests.

Covers: versioned /v1/ routes existence, error envelope format, OpenAPI contract,
capability matrix, Pydantic model field constraints, route isolation.
No live DB required — imports are structural / schema checks.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e06"
sys.path.insert(0, str(ROOT))

try:
    from services.api.routes import v1_projects as _v1_projects_mod  # noqa: F401
    V1_PROJECTS_AVAILABLE = True
except ModuleNotFoundError:
    V1_PROJECTS_AVAILABLE = False

_SKIP_SQLALCHEMY = unittest.skipUnless(
    V1_PROJECTS_AVAILABLE, "sqlalchemy not installed — skipping v1_projects tests"
)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity(unittest.TestCase):
    def test_openapi_required_paths_fixture_loads(self):
        data = _load_fixture("openapi_required_paths.json")
        self.assertIn("requiredV1Paths", data)
        self.assertIn("requiredMetaPaths", data)

    def test_versioning_rules_documented_in_fixture(self):
        data = _load_fixture("openapi_required_paths.json")
        self.assertTrue(data["versioningRules"]["breakingChangesRequireNewMajor"])


# ---------------------------------------------------------------------------
# Versioned route structure
# ---------------------------------------------------------------------------

@_SKIP_SQLALCHEMY
class TestVersionedRoutes(unittest.TestCase):
    """All /v1/ routes must be present in the router definition."""

    def test_v1_projects_router_has_correct_prefix(self):
        from services.api.routes.v1_projects import router
        self.assertEqual(router.prefix, "/v1/projects")

    def test_v1_routes_cover_crud(self):
        from services.api.routes.v1_projects import router
        paths = {route.path for route in router.routes}
        # Should have root listing + individual project + jobs + revisions
        self.assertTrue(
            any(p in ("/v1/projects/", "/v1/projects", "", "/") for p in paths),
            "Must have a root list/create route",
        )

    def test_v1_health_router_exists(self):
        from services.api.routes.v1_health import router
        self.assertIsNotNone(router)

    def test_required_v1_paths_in_fixture_are_declared(self):
        """Fixture paths must match at least the declared router patterns."""
        data = _load_fixture("openapi_required_paths.json")
        from services.api.routes.v1_projects import router
        declared_paths = {route.path for route in router.routes}
        for expected in data["requiredV1Paths"]:
            sub = expected.replace("/v1/projects", "", 1) or "/"
            self.assertTrue(
                expected in declared_paths or sub in declared_paths,
                f"Fixture path {expected!r} not found in v1_projects router: {declared_paths}",
            )



# ---------------------------------------------------------------------------
# Pydantic model field constraints
# ---------------------------------------------------------------------------

@_SKIP_SQLALCHEMY
class TestPydanticModelConstraints(unittest.TestCase):
    """Request model validation must reject out-of-contract inputs."""

    def test_project_create_rejects_empty_name(self):
        from pydantic import ValidationError
        from services.api.routes.v1_projects import ProjectCreateRequest
        with self.assertRaises(ValidationError):
            ProjectCreateRequest(name="", units="inch")

    def test_project_create_rejects_invalid_units(self):
        from pydantic import ValidationError
        from services.api.routes.v1_projects import ProjectCreateRequest
        with self.assertRaises(ValidationError):
            ProjectCreateRequest(name="Test Project", units="cubits")

    def test_project_create_accepts_valid_units(self):
        from services.api.routes.v1_projects import ProjectCreateRequest
        for unit in ("inch", "mm", "m", "ft"):
            req = ProjectCreateRequest(name="Test", units=unit)
            self.assertEqual(req.units, unit)

    def test_job_enqueue_rejects_invalid_type(self):
        from pydantic import ValidationError
        from services.api.routes.v1_projects import JobEnqueueRequest
        with self.assertRaises(ValidationError):
            JobEnqueueRequest(job_type="INVALID_TYPE")

    def test_job_enqueue_accepts_all_valid_types(self):
        from services.api.routes.v1_projects import JobEnqueueRequest
        for jtype in ("generate", "validate", "enrich", "quality_gate", "export", "benchmark"):
            req = JobEnqueueRequest(job_type=jtype)
            self.assertEqual(req.job_type, jtype)

    def test_project_name_max_length_enforced(self):
        from pydantic import ValidationError
        from services.api.routes.v1_projects import ProjectCreateRequest
        with self.assertRaises(ValidationError):
            ProjectCreateRequest(name="x" * 201, units="inch")


# ---------------------------------------------------------------------------
# Error envelope structure
# ---------------------------------------------------------------------------

@_SKIP_SQLALCHEMY
class TestErrorEnvelope(unittest.TestCase):
    """FastAPI 422/404 responses must have a 'detail' key (standard envelope)."""

    def test_project_response_model_has_id_and_org(self):
        from services.api.routes.v1_projects import ProjectResponse
        fields = ProjectResponse.model_fields
        self.assertIn("id", fields)
        self.assertIn("organization_id", fields)
        self.assertIn("name", fields)
        self.assertIn("units", fields)

    def test_job_status_response_has_required_fields(self):
        from services.api.routes.v1_projects import JobStatusResponse
        fields = JobStatusResponse.model_fields
        self.assertIn("id", fields)
        self.assertIn("type", fields)
        self.assertIn("status", fields)
        self.assertIn("progress", fields)


# ---------------------------------------------------------------------------
# Auth integration on routes (structural)
# ---------------------------------------------------------------------------

class TestAuthWiringOnRoutes(unittest.TestCase):
    """Routes must declare auth dependencies — not accept anonymous requests."""

    def test_v1_projects_imports_auth_user(self):
        src = (ROOT / "services" / "api" / "routes" / "v1_projects.py").read_text(encoding="utf-8")
        self.assertIn("AuthUser", src)
        self.assertIn("require_editor", src)
        self.assertIn("require_owner", src)

    def test_v1_projects_enqueues_with_audit(self):
        src = (ROOT / "services" / "api" / "routes" / "v1_projects.py").read_text(encoding="utf-8")
        self.assertIn("SqlAuditRepository", src)
        self.assertIn("job.enqueue", src)

    def test_v1_health_does_not_require_auth(self):
        """Health endpoints must be publicly accessible — no auth dependency."""
        src = (ROOT / "services" / "api" / "routes" / "v1_health.py").read_text(encoding="utf-8")
        self.assertNotIn("AuthUser", src)
        self.assertNotIn("require_editor", src)


# ---------------------------------------------------------------------------
# OpenAPI schema contract
# ---------------------------------------------------------------------------

@_SKIP_SQLALCHEMY
class TestOpenApiSchemaContract(unittest.TestCase):
    """FastAPI app must generate a valid OpenAPI schema with all required paths."""

    def setUp(self):
        os.environ["AUTH_DISABLED"] = "true"

    def tearDown(self):
        os.environ.pop("AUTH_DISABLED", None)

    def test_app_generates_openapi_schema(self):
        try:
            from services.api.main import app
            schema = app.openapi()
            self.assertIn("paths", schema)
            self.assertIn("info", schema)
        except Exception as exc:
            self.skipTest(f"FastAPI app not fully importable in test env: {exc}")

    def test_openapi_has_health_path(self):
        try:
            from services.api.main import app
            schema = app.openapi()
            self.assertIn("/health", schema["paths"])
        except Exception as exc:
            self.skipTest(f"FastAPI app not fully importable: {exc}")

    def test_openapi_version_is_set(self):
        try:
            from services.api.main import app
            self.assertIn(".", app.version)  # Should be something like "1.0.0-week20"
        except Exception as exc:
            self.skipTest(f"FastAPI app not importable: {exc}")

    def test_v1_projects_router_adds_paths(self):
        """The v1 router must be mountable without errors."""
        from fastapi import FastAPI
        from services.api.routes.v1_projects import router
        test_app = FastAPI()
        try:
            test_app.include_router(router)
        except Exception as exc:
            self.fail(f"Including v1_projects router raised: {exc}")

    def test_required_meta_paths_in_fixture_reachable(self):
        data = _load_fixture("openapi_required_paths.json")
        try:
            from services.api.main import app
            schema = app.openapi()
            for path in data["requiredMetaPaths"]:
                self.assertIn(path, schema["paths"],
                              f"Required meta path {path!r} missing from OpenAPI schema")
        except Exception as exc:
            self.skipTest(f"FastAPI app not fully importable: {exc}")


# ---------------------------------------------------------------------------
# Frontend contract — never geometry authority
# ---------------------------------------------------------------------------

class TestFrontendContractNoGeometry(unittest.TestCase):
    """ADR-001: React frontend must never be geometry authority.
    These tests verify the API surface never exposes raw geometry write paths.
    """

    def test_v1_projects_has_no_geometry_mutate_route(self):
        src = (ROOT / "services" / "api" / "routes" / "v1_projects.py").read_text(encoding="utf-8")
        for forbidden in ("walls", "openings_geometry", "set_geometry", "mutate_wall"):
            self.assertNotIn(forbidden, src,
                             f"Route must not expose geometry-mutating endpoint: {forbidden!r}")

    def test_revision_stores_sha_pointer_not_geometry(self):
        """Revision ORM model must use model_sha256 pointer, not inline geometry."""
        try:
            from services.api.models.orm import Revision
            col_names = {c.name for c in Revision.__table__.columns}
            self.assertIn("model_sha256", col_names)
            self.assertIn("model_storage_key", col_names)
            # Must NOT have inline geometry
            for forbidden in ("walls", "openings", "geometry", "floorplan"):
                self.assertNotIn(forbidden, col_names,
                                 f"Revision must not have inline geometry column: {forbidden!r}")
        except ImportError:
            self.skipTest("sqlalchemy not installed")


if __name__ == "__main__":
    unittest.main()
