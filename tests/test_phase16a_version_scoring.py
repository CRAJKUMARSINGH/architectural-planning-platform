"""Unit tests for Phase 16A AI version scoring integration.

Tests the AI health endpoint, ScoringResult ORM model, and AI service
graceful degradation. Also covers Phase 16B integration:
- /api/ai/score-revision endpoint persists ScoringResult to DB
- Idempotent second call returns stored row without duplicate
- /api/ai/compare-versions API contract and winner selection

CRITICAL — Global state isolation (eliminate cross-module ordering bugs):
  1. Explicitly force required env vars BEFORE any services.* import (not setdefault).
  2. Reset db.session singletons (engine + SessionLocal) so engine re-reads the
     just-set DATABASE_URL instead of inheriting whatever value an earlier test
     module may have locked in.
  3. Each test class setUp/tearDown explicitly saves and restores env state.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "phase16"
sys.path.insert(0, str(ROOT))

# ----- ENVIRONMENT ISOLATION -----------------------------------------------
_SAVED_ENV: dict[str, str | None] = {}
for _key in ("AUTH_DISABLED", "DATABASE_URL", "GEMINI_API_KEY", "JWT_SECRET"):
    _SAVED_ENV[_key] = os.environ.get(_key)

os.environ["AUTH_DISABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("GEMINI_API_KEY", None)
os.environ["JWT_SECRET"] = "test-secret-phase16"

try:
    from services.api.db.session import reset_session_singletons
    reset_session_singletons(dispose=True)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Imports after env is set (order matters for singleton wiring)
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.api.main import app
from services.api.auth import DEV_ORG_ID, DEV_USER_ID, CurrentUser
from services.api.db.session import get_engine, get_session, reset_session_singletons as _reset_s
from services.api.models.base import Base
from services.api.models.orm import (
    Organization,
    User,
    Membership,
    Project,
    Revision,
    ScoringResult,
)
from services.ai.ai_service import (
    AIService,
    BriefAnalysisResult,
    SuggestionResult,
    VersionScoreResult,
)


def _restore_module_env() -> None:
    for _k, _v in _SAVED_ENV.items():
        if _v is None:
            os.environ.pop(_k, None)
        else:
            os.environ[_k] = _v
    try:
        _reset_s(dispose=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Named dependency-override functions (no lambdas! — project_memory lesson)
# ---------------------------------------------------------------------------
def _make_override_current_user(user: CurrentUser):
    def _override() -> CurrentUser:
        return user
    return _override


def _build_mock_ai_service() -> MagicMock:
    svc = MagicMock(spec=AIService)
    svc.available = True
    svc.model_name = "test-mock-v1"

    svc.analyze_brief.return_value = BriefAnalysisResult(
        summary="Test project brief analysis",
        space_program=[
            {"name": "Chamber Hall", "sqm": 80, "priority": "must-have", "notes": "Main advocacy space"},
            {"name": "Library", "sqm": 30, "priority": "must-have", "notes": "Legal reference collection"},
        ],
        constraints=["98-foot front wall", "Setback 10 ft", "Max height 3 stories"],
        opportunities=["Corner lot has dual street frontage", "Rear garden can accommodate lightwell"],
        open_questions=["Client elevator requirement?"],
        provenance={"model": "test-mock-v1", "timestamp": "2026-01-15T10:00:00Z",
                    "brief_length": 100, "context_keys": ["projectId", "revisionId"]},
        model_version="test-mock-v1",
    )

    svc.score_version.return_value = VersionScoreResult(
        overall_score=82,
        program_fit=88,
        daylight=76,
        budget_fit=80,
        commentary="Strong program fit with minor daylight gaps on north side.",
        zone_scores=[
            {"zoneName": "Chamber Hall", "score": 92, "notes": "Excellent volume and flow"},
            {"zoneName": "Library", "score": 78, "notes": "Adequate; add clerestory glazing"},
        ],
        provenance={"model": "test-mock-v1", "timestamp": "2026-01-15T10:05:00Z",
                    "version_id": None, "brief_analysis_id": "2026-01-15T10:00:00Z"},
        model_version="test-mock-v1",
    )

    svc.generate_suggestions.return_value = SuggestionResult(
        suggestions=[
            {"category": "daylight", "text": "Add clerestory windows on the north wall.", "priority": "medium"},
            {"category": "circulation", "text": "Relocate stair away from main entrance.", "priority": "high"},
        ],
        categories=["daylight", "circulation"],
        provenance={"model": "test-mock-v1", "timestamp": "2026-01-15T10:10:00Z"},
        model_version="test-mock-v1",
    )

    return svc


# ---------------------------------------------------------------------------
# Helpers for seeding the test hierarchy
# ---------------------------------------------------------------------------
def _seed_hierarchy(db: Session) -> dict[str, Any]:
    """Create Organization → User → Membership → Project → Revision.

    Returns the ids so tests can reference them. Uses DEV_USER_ID / DEV_ORG_ID
    so the get_current_user override matches the DB memberships when auth is
    NOT fully bypassed.
    """
    org = Organization(
        id=DEV_ORG_ID,
        name="Bar Association Banswara Test",
        slug="ba-banswara-test",
    )
    db.add(org)

    user = User(
        id=DEV_USER_ID,
        external_auth_id="dev-auth-id",
        email="dev@local.example",
        display_name="Dev User",
        disabled_at=None,
    )
    db.add(user)

    membership = Membership(
        organization_id=DEV_ORG_ID,
        user_id=DEV_USER_ID,
        role="owner",
    )
    db.add(membership)

    project_id = uuid.uuid4()
    revision_id = uuid.uuid4()
    project = Project(
        id=project_id,
        organization_id=DEV_ORG_ID,
        name="Advocate Chambers — Test Project",
        units="inch",
        current_revision_id=revision_id,
    )
    db.add(project)

    revision = Revision(
        id=revision_id,
        project_id=project_id,
        revision_number=1,
        parent_revision_id=None,
        model_storage_key="obj/test/rev1.binpack",
        model_sha256="a" * 64,
        rule_pack_version="phase2.rule-pack.v1",
        author_user_id=DEV_USER_ID,
        reason="Initial seed revision for scoring test",
        command_id="cmd-create-project-001",
        idempotency_key="idem-create-project-001",
        command_fingerprint="0" * 64,
        engine_version="phase2.command-engine.v1",
        validation_state="VALID",
        created_at=datetime.utcnow(),
    )
    db.add(revision)
    db.flush()

    project.current_revision_id = revision.id
    db.commit()

    return {
        "org_id": str(org.id),
        "user_id": str(user.id),
        "project_id": str(project_id),
        "revision_id": str(revision_id),
    }


# ---------------------------------------------------------------------------
# Base TestCase shared setup pattern
# ---------------------------------------------------------------------------
class _BaseDBTestCase(unittest.TestCase):
    """Base class: setUp/tearDown that rebuilds tables & wires overrides."""

    saved_env: dict[str, str | None]

    def setUp(self) -> None:
        self.saved_env = {k: os.environ.get(k) for k in (
            "AUTH_DISABLED", "DATABASE_URL", "GEMINI_API_KEY"
        )}
        os.environ["AUTH_DISABLED"] = "true"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ.pop("GEMINI_API_KEY", None)

        _reset_s(dispose=True)

        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        self.client = TestClient(app)

        self.test_user = CurrentUser(
            user_id=DEV_USER_ID,
            email="dev@local.example",
            org_id=DEV_ORG_ID,
            role="owner",
            request_id=f"test-req-{uuid.uuid4()}",
        )

        from services.api.auth import get_current_user as _gcu
        app.dependency_overrides[_gcu] = _make_override_current_user(self.test_user)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        try:
            engine = get_engine()
            Base.metadata.drop_all(bind=engine)
        except Exception:
            pass
        _reset_s(dispose=True)
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Task 1 — /score-revision endpoint reachability (was SKIPPED before)
# ---------------------------------------------------------------------------
class TestVersionScoringAPI(_BaseDBTestCase):
    """Test the AI version scoring API endpoints."""

    def test_score_revision_endpoint_exists(self):
        """Test that the scoring endpoint exists and returns 200 on valid input.

        Seeds Project + Revision so the endpoint doesn't 404 on lookups.
        Mocks v1_ai.get_ai_service (patch WHERE USED) so the AI path is deterministic.
        """
        from services.api.routes import v1_ai as _ai_route_mod

        mock_svc = _build_mock_ai_service()
        with patch.object(_ai_route_mod, "get_ai_service", return_value=mock_svc):
            db_sesh = next(get_session())
            try:
                ids = _seed_hierarchy(db_sesh)
            finally:
                db_sesh.close()

            response = self.client.post(
                f"/api/ai/score-revision/{ids['project_id']}",
                json={"revision_id": ids["revision_id"]},
            )

        self.assertEqual(response.status_code, 200,
                         f"Endpoint should return 200 on valid input; got {response.status_code}: {response.content!r}")

    def test_ai_health_endpoint(self):
        """Test that the AI health check endpoint works."""
        response = self.client.get("/api/ai/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("sdk_installed", data)
        self.assertIn("phase16_scoring_engine", data)


# ---------------------------------------------------------------------------
# Task 2 — ScoringResult round-trip integration
# ---------------------------------------------------------------------------
class TestScoringEndpointIntegration(_BaseDBTestCase):
    """Full integration: call endpoint, verify DB persistence + idempotency.

    Uses context-manager patching (same pattern as the passing test) for
    deterministic mock-lifetime semantics.  Also compares ids against UUID
    objects in the DB-verify path to match whatever canonical representation
    the ORM materialises.
    """

    def test_score_revision_persists_result(self):
        """POST /score-revision writes ScoringResult with correct FKs + scores."""
        from services.api.routes import v1_ai as _route_mod

        mock_svc = _build_mock_ai_service()
        with patch.object(_route_mod, "get_ai_service", return_value=mock_svc):
            db = next(get_session())
            try:
                ids = _seed_hierarchy(db)
            finally:
                db.close()

            rid_uuid = uuid.UUID(ids["revision_id"])
            pid_uuid = uuid.UUID(ids["project_id"])

            resp = self.client.post(
                f"/api/ai/score-revision/{ids['project_id']}",
                json={"revision_id": ids["revision_id"]},
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["overall_score"], 82)
        self.assertEqual(body["program_fit"], 88)
        self.assertEqual(body["daylight"], 76)
        self.assertEqual(body["budget_fit"], 80)
        self.assertEqual(body["model_version"], "test-mock-v1")

        verify = next(get_session())
        try:
            rows = (
                verify.query(ScoringResult)
                .filter(ScoringResult.revision_id == rid_uuid)
                .all()
            )
            self.assertEqual(len(rows), 1, "Exactly one ScoringResult row created")
            row = rows[0]
            self.assertEqual(row.project_id, pid_uuid)
            self.assertEqual(row.revision_id, rid_uuid)
            self.assertEqual(row.overall_score, 82)
            self.assertEqual(row.program_fit, 88)
            self.assertEqual(row.daylight_score, 76)
            self.assertEqual(row.budget_fit, 80)
            self.assertEqual(row.created_by_user_id, DEV_USER_ID)
            self.assertIsInstance(row.zone_scores, list)
            self.assertEqual(len(row.zone_scores), 2)
            self.assertIsInstance(row.provenance, dict)
            self.assertEqual(row.model_version, "test-mock-v1")
        finally:
            verify.close()

    def test_score_revision_idempotent_second_call(self):
        """Second POST returns stored row — no duplicate, AI not re-invoked."""
        from services.api.routes import v1_ai as _route_mod

        mock_svc = _build_mock_ai_service()
        with patch.object(_route_mod, "get_ai_service", return_value=mock_svc):
            db = next(get_session())
            try:
                ids = _seed_hierarchy(db)
            finally:
                db.close()

            rid_uuid = uuid.UUID(ids["revision_id"])

            r1 = self.client.post(
                f"/api/ai/score-revision/{ids['project_id']}",
                json={"revision_id": ids["revision_id"]},
            )
            self.assertEqual(r1.status_code, 200, r1.content)
            self.assertEqual(mock_svc.score_version.call_count, 1)

            r2 = self.client.post(
                f"/api/ai/score-revision/{ids['project_id']}",
                json={"revision_id": ids["revision_id"]},
            )
            self.assertEqual(r2.status_code, 200, r2.content)

        self.assertEqual(mock_svc.score_version.call_count, 1,
                         "AI score_version must NOT be called on 2nd (cached) request")
        self.assertEqual(r2.json()["overall_score"], r1.json()["overall_score"])

        verify = next(get_session())
        try:
            count = (
                verify.query(ScoringResult)
                .filter(ScoringResult.revision_id == rid_uuid)
                .count()
            )
            self.assertEqual(count, 1, "Still exactly 1 row after 2 calls (dedupe worked)")
        finally:
            verify.close()


# ---------------------------------------------------------------------------
# Task 3 — /compare-versions API contract & winner correctness
# ---------------------------------------------------------------------------
class TestCompareVersionsAPI(_BaseDBTestCase):
    """Phase 16 multi-version tradeoff comparison API tests."""

    def setUp(self) -> None:
        super().setUp()
        FIXTURES.mkdir(parents=True, exist_ok=True)
        self.fixture_path = FIXTURES / "compare-versions-sample.json"
        if not self.fixture_path.exists():
            self._write_fixture()

    def _write_fixture(self) -> None:
        fixture = {
            "schemaVersion": "phase16.compare-versions.v1",
            "description": "2 versions: good-scoring (vA) vs poor-scoring (vB)",
            "versions": [
                {
                    "id": "ver-a-good",
                    "totalArea": 7800,
                    "estimatedCost": 4200000,
                    "zones": [
                        {"zoneName": "Chamber Hall", "area": 850, "windows": 4, "southExposure": True},
                        {"zoneName": "Library", "area": 420, "windows": 3, "southExposure": True},
                        {"zoneName": "Chambers x 12", "area": 4800, "windows": 24, "southExposure": True},
                        {"zoneName": "Circulation", "area": 900, "windows": 0, "southExposure": False},
                    ],
                    "orientation": "main-entrance-south-98ft",
                },
                {
                    "id": "ver-b-poor",
                    "totalArea": 5200,
                    "estimatedCost": 5100000,
                    "zones": [
                        {"zoneName": "Chamber Hall", "area": 520, "windows": 1, "southExposure": False},
                        {"zoneName": "Library", "area": 200, "windows": 0, "southExposure": False},
                        {"zoneName": "Chambers x 6", "area": 2400, "windows": 6, "southExposure": False},
                        {"zoneName": "Circulation", "area": 1800, "windows": 0, "southExposure": False},
                    ],
                    "orientation": "main-entrance-north",
                },
            ],
            "brief": {
                "spaceProgram": [
                    {"name": "Chamber Hall", "targetArea": 800, "priority": "must-have"},
                    {"name": "Library", "targetArea": 400, "priority": "must-have"},
                    {"name": "Chambers (units)", "targetCount": 12, "priority": "must-have"},
                ],
                "maxBudget": 4500000,
                "constraints": [
                    "Main entrance on 98-ft south wall",
                    "Min 12 advocate chambers",
                    "Total covered area >= 7500 sq ft",
                ],
                "preferences": ["South-facing daylight preferred for all occupied rooms"],
            },
            "minimumScore": 60,
            "expected": {
                "winner": "ver-a-good",
                "qualityGateStatus": "PASS",
                "winnerOverallScoreMinimum": 60,
            },
        }
        self.fixture_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")

    def test_compare_versions_fixture_is_valid_json(self):
        raw = self.fixture_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertIn("versions", data)
        self.assertIn("brief", data)
        self.assertGreaterEqual(len(data["versions"]), 2)

    def test_compare_versions_schema_and_winner(self):
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        resp = self.client.post(
            "/api/ai/compare-versions",
            json={
                "versions": data["versions"],
                "brief": data["brief"],
                "minimum_score": data.get("minimumScore", 60),
            },
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()

        required_keys = {
            "schema_version", "generated_at", "version_count", "winner",
            "tradeoff_notes", "matrix", "quality_gate_track",
        }
        self.assertTrue(required_keys.issubset(body.keys()),
                        f"Missing keys: {required_keys - set(body.keys())}")

        self.assertEqual(body["version_count"], 2)
        self.assertEqual(body["winner"], data["expected"]["winner"],
                         f"Winner mismatch — matrix: {json.dumps(body['matrix'], indent=2)}")

        winner_row = next((r for r in body["matrix"] if r["versionId"] == body["winner"]), None)
        self.assertIsNotNone(winner_row, "Winner must appear in matrix")
        self.assertGreaterEqual(
            winner_row.get("overallScore", 0),
            data["expected"]["winnerOverallScoreMinimum"],
            "Winner overall score must meet minimum fixture threshold",
        )

    def test_compare_versions_quality_gate_track_pass(self):
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        resp = self.client.post(
            "/api/ai/compare-versions",
            json={
                "versions": data["versions"],
                "brief": data["brief"],
                "minimum_score": data.get("minimumScore", 60),
            },
        )
        self.assertEqual(resp.status_code, 200)
        gate = resp.json()["quality_gate_track"]
        self.assertIn("status", gate)
        self.assertEqual(gate["status"], "PASS",
                         f"Fixture is designed for PASS; gate={json.dumps(gate)}")
        self.assertIn("schemaVersion", gate)
        self.assertIn("bestVersionId", gate)
        self.assertIn("bestOverallScore", gate)
        self.assertIn("versionsEvaluated", gate)
        self.assertEqual(gate["versionsEvaluated"], 2)
        self.assertEqual(gate["bestVersionId"], data["expected"]["winner"])


# ---------------------------------------------------------------------------
# ScoringResult ORM unit tests (no DB / no network)
# ---------------------------------------------------------------------------
class TestScoringResultModel(unittest.TestCase):
    """Test the ScoringResult ORM model construction."""

    def test_scoring_result_creation(self):
        scoring_result = ScoringResult(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            revision_id=uuid.uuid4(),
            brief_analysis_id="test-brief-id",
            overall_score=85,
            program_fit=90,
            daylight_score=75,
            budget_fit=80,
            commentary="Test commentary",
            zone_scores=[{"zoneName": "Living Room", "score": 85, "notes": "Good"}],
            provenance={"model": "gemini-2.5-flash", "timestamp": "2024-01-01T00:00:00Z"},
            model_version="gemini-2.5-flash",
            created_by_user_id=uuid.uuid4(),
        )
        self.assertIsNotNone(scoring_result.id)
        self.assertEqual(scoring_result.overall_score, 85)
        self.assertEqual(scoring_result.program_fit, 90)
        self.assertIsInstance(scoring_result.zone_scores, list)

    def test_scoring_result_score_validation(self):
        valid_scoring = ScoringResult(
            project_id=uuid.uuid4(),
            revision_id=uuid.uuid4(),
            overall_score=0,
            program_fit=100,
            daylight_score=50,
            budget_fit=75,
            commentary="Test",
            zone_scores=[],
            provenance={},
            model_version="gemini-2.5-flash",
        )
        self.assertEqual(valid_scoring.overall_score, 0)
        self.assertEqual(valid_scoring.program_fit, 100)


# ---------------------------------------------------------------------------
# AI Service graceful degradation (unit-level, no DB)
# ---------------------------------------------------------------------------
class TestAIServiceIntegration(unittest.TestCase):
    """Test AI service graceful degradation — env snapshot/restore per test."""

    def test_ai_service_initialization_without_key(self):
        saved = os.environ.pop("GEMINI_API_KEY", None)
        try:
            from services.ai.ai_service import AIService
            ai_service = AIService()
            self.assertIsNotNone(ai_service)
            self.assertFalse(ai_service.available)
        finally:
            if saved is not None:
                os.environ["GEMINI_API_KEY"] = saved

    def test_ai_service_initialization_with_key(self):
        saved = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-key"
        try:
            from services.ai.ai_service import AIService
            ai_service = AIService()
            self.assertIsNotNone(ai_service)
        finally:
            if saved is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = saved


if __name__ == "__main__":
    unittest.main()
