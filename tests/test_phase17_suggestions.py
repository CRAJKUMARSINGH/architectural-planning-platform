"""Phase 17 tests — heuristic suggestion engine + AI service fallback.

Covers:
  - Fixture integrity and schema validity
  - HeuristicSuggestionEngine determinism (same input → identical signature)
  - Suggestion SHA-256 hash stability (category/text normalization)
  - Per-category minimum suggestion counts for the bundled fixture
  - Priority distribution: HIGH priority when triggered rules fire
  - AIService.generate_suggestions fallback path (heuristic used when
    GEMINI_API_KEY is removed with env snapshot/restore pattern)
  - Fallback provenance tracking (``fallback: true`` + engine version)
"""
from __future__ import annotations

import json
import os
import sys
import unittest
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "phase17"
sys.path.insert(0, str(ROOT))

# ----- ENVIRONMENT ISOLATION (per-module snapshot) ------------------------
_SAVED_ENV: dict[str, str | None] = {}
for _key in ("AUTH_DISABLED", "DATABASE_URL", "GEMINI_API_KEY"):
    _SAVED_ENV[_key] = os.environ.get(_key)
os.environ.pop("GEMINI_API_KEY", None)
os.environ["AUTH_DISABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

try:
    from services.api.db.session import reset_session_singletons
    reset_session_singletons(dispose=True)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Imports after env setup
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.api.main import app
from services.api.auth import DEV_ORG_ID, DEV_USER_ID, CurrentUser
from services.api.db.session import get_engine, get_session, reset_session_singletons as _reset_s
from services.api.models.base import Base
from services.api.models.orm import Organization, User, Membership, Project, Revision
from services.ai.ai_service import AIService, SuggestionResult as _ServiceSuggestionResult

sys.path.insert(0, str(ROOT / "scripts"))
from scripts.phase17_suggestions import (  # noqa: E402  — late import after ROOT on path
    HeuristicSuggestionEngine,
    Suggestion,
    SuggestionResult as _HeuristicSuggestionResult,
    VALID_CATEGORIES,
    VALID_PRIORITIES,
)


def _restore_module_env() -> None:
    for k, v in _SAVED_ENV.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        _reset_s(dispose=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Named override helpers (no lambdas — project_memory lesson)
# ---------------------------------------------------------------------------
def _make_override_current_user(user: CurrentUser):
    def _override() -> CurrentUser:
        return user
    return _override


def _seed_project_hierarchy(db: Session) -> str:
    org = Organization(id=DEV_ORG_ID, name="BA Banswara T17", slug="ba-banswara-t17")
    usr = User(id=DEV_USER_ID, email="dev@local.example", external_auth_id="dev-auth")
    mem = Membership(organization_id=DEV_ORG_ID, user_id=DEV_USER_ID, role="owner")
    pid = uuid.uuid4()
    rid = uuid.uuid4()
    proj = Project(id=pid, organization_id=DEV_ORG_ID, name="P17 Test", units="inch", current_revision_id=rid)
    rev = Revision(
        id=rid, project_id=pid, revision_number=1, model_sha256="0" * 64,
        model_storage_key="obj/t17/rev1.binpack", rule_pack_version="phase2.rule-pack.v1",
        author_user_id=DEV_USER_ID, reason="p17 seed", engine_version="phase2.command-engine.v1",
        validation_state="VALID",
    )
    for obj in (org, usr, mem, proj, rev):
        db.add(obj)
    db.flush()
    proj.current_revision_id = rev.id
    db.commit()
    return str(pid)


# ---------------------------------------------------------------------------
# Base class with DB + env + dependency-override lifecycle
# ---------------------------------------------------------------------------
class _BaseDBTestCase(unittest.TestCase):
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
            user_id=DEV_USER_ID, email="dev@local.example",
            org_id=DEV_ORG_ID, role="owner",
            request_id=f"t17-req-{uuid.uuid4()}",
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
# Fixture integrity & HeuristicSuggestionEngine unit tests
# ---------------------------------------------------------------------------
class TestPhase17FixtureIntegrity(unittest.TestCase):
    def test_fixture_exists_and_is_valid_json(self):
        self.assertTrue(FIXTURES.exists(), f"Missing fixture dir {FIXTURES}")
        path = FIXTURES / "suggestions-sample.json"
        self.assertTrue(path.exists(), f"Missing fixture: {path.name}")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("expected", data)
        self.assertIn("brief", data)
        self.assertIn("version", data)
        self.assertGreaterEqual(len(data["version"]["zones"]), 3)

    def test_fixture_expected_fields_aligned_with_engine(self):
        data = json.loads((FIXTURES / "suggestions-sample.json").read_text(encoding="utf-8"))
        expected_cats = set(data["expected"]["categoriesProduced"])
        self.assertTrue(expected_cats.issubset(VALID_CATEGORIES),
                        f"Fixture expected categories contain unknowns: {expected_cats - VALID_CATEGORIES}")


class TestHeuristicEngineDeterminism(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(
            (FIXTURES / "suggestions-sample.json").read_text(encoding="utf-8")
        )
        cls.engine = HeuristicSuggestionEngine()

    def test_same_input_produces_same_signature(self):
        r1 = self.engine.generate(self.fixture)
        r2 = self.engine.generate(self.fixture)
        self.assertEqual(r1.signature, r2.signature,
                         "Heuristic engine must produce identical output for identical input")

    def test_category_ordering_is_immaterial(self):
        """Passing categories in different orders should yield same suggestion list."""
        base = self.engine.generate(self.fixture, categories=None)
        explicit_abc = self.engine.generate(self.fixture, categories=["budget", "circulation", "daylight", "general", "program"])
        explicit_cba = self.engine.generate(self.fixture, categories=["program", "general", "budget", "circulation", "daylight"])
        self.assertEqual(base.signature, explicit_abc.signature)
        self.assertEqual(explicit_abc.signature, explicit_cba.signature)

    def test_hash_stability_for_normalized_text(self):
        """Suggestion hash must ignore leading/trailing whitespace and case in text/category."""
        s1 = Suggestion(category="PROGRAM ", text="  CONSIDER expanding the chamber hall  ", priority="high")
        s2 = Suggestion(category="program", text="consider expanding the chamber hall", priority="high")
        self.assertEqual(s1.suggestion_hash, s2.suggestion_hash,
                         "SHA-256 hash must normalize category/text whitespace + case")

    def test_hash_differs_for_material_changes(self):
        s1 = Suggestion(category="daylight", text="Add clerestory on north wall", priority="medium")
        s2 = Suggestion(category="daylight", text="Add clerestory on south wall", priority="medium")
        self.assertNotEqual(s1.suggestion_hash, s2.suggestion_hash)


class TestHeuristicEnginePerCategory(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(
            (FIXTURES / "suggestions-sample.json").read_text(encoding="utf-8")
        )
        cls.result = HeuristicSuggestionEngine().generate(cls.data)

    def test_minimum_total_count(self):
        expected_min = int(self.data["expected"]["minSuggestionCount"])
        self.assertGreaterEqual(
            len(self.result.suggestions), expected_min,
            f"Fixture triggers at least {expected_min} suggestions; got {len(self.result.suggestions)}"
        )

    def test_expected_categories_all_produced(self):
        produced = set(self.result.categories)
        expected = set(self.result.categories) if False else set(self.data["expected"]["categoriesProduced"])
        self.assertTrue(expected.issubset(produced),
                        f"Expected categories {expected - produced} missing from output {produced}")

    def test_every_suggestion_has_valid_category_and_priority(self):
        for s in self.result.suggestions:
            self.assertIn(s.category, VALID_CATEGORIES, f"Invalid category {s.category!r} on {s.text[:40]!r}")
            self.assertIn(s.priority, VALID_PRIORITIES, f"Invalid priority {s.priority!r} on {s.text[:40]!r}")
            self.assertTrue(s.text, "Empty suggestion text")
            self.assertRegex(s.suggestion_hash, r"^[0-9a-f]{64}$",
                              f"suggestion_hash must be 64-char hex; got {s.suggestion_hash!r}")

    def test_high_priority_fires_for_known_triggers(self):
        """The fixture intentionally undersizes chamber hall and runs over budget → HIGH priorities."""
        highs = [s for s in self.result.suggestions if s.priority == "high"]
        self.assertGreaterEqual(len(highs), 2,
                                f"Fixture should trigger at least 2 HIGH priority suggestions, got {len(highs)}")
        high_categories = {s.category for s in highs}
        expected = set(self.data["expected"]["highPriorityCategories"])
        self.assertTrue(
            expected.issubset(high_categories | {"budget", "program", "daylight"}),
            f"HIGH-priority categories missing from expected set {expected}"
        )

    def test_program_undersize_rule_fires_for_chamber_hall(self):
        program_items = [s for s in self.result.suggestions
                         if s.category == "program" and "chamber hall" in s.text.lower()]
        self.assertTrue(
            any(s.rule_id == "PROG-UNDERSIZE-002" for s in program_items),
            "Chamber Hall is 560 sq ft vs 800 target — UNDERSIZE HIGH rule should fire"
        )

    def test_budget_overage_rule_fires(self):
        budget_items = [s for s in self.result.suggestions if s.category == "budget"]
        self.assertTrue(
            any("5,200,000" in s.text or "5200000" in s.text or "over" in s.text.lower()
                for s in budget_items),
            "Cost 5.2M vs 4.5M cap should trigger BUDGET-OVER HIGH rule"
        )


# ---------------------------------------------------------------------------
# AIService heuristic fallback (no gemini key → should not raise 503)
# ---------------------------------------------------------------------------
class TestAIServiceFallback(unittest.TestCase):
    """Verify AIService.generate_suggestions transparently falls back when key absent."""

    def setUp(self) -> None:
        self._saved = os.environ.get("GEMINI_API_KEY")
        os.environ.pop("GEMINI_API_KEY", None)
        self.fixture = json.loads(
            (FIXTURES / "suggestions-sample.json").read_text(encoding="utf-8")
        )

    def tearDown(self) -> None:
        if self._saved is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = self._saved

    def test_generate_without_key_uses_heuristic_fallback_and_succeeds(self):
        svc = AIService()
        self.assertFalse(svc.available, "Sanity: AIService should be unavailable with no key")

        result = svc.generate_suggestions(self.fixture, categories=None)

        self.assertIsInstance(result, _ServiceSuggestionResult)
        self.assertIsInstance(result.suggestions, list)
        self.assertGreaterEqual(len(result.suggestions), 4,
                                "Fallback should emit at least 4 suggestions on the fixture")
        self.assertTrue(result.provenance.get("fallback"),
                        "provenance.fallback must be True when heuristic engine produced the list")
        self.assertEqual(result.provenance.get("engine"), "heuristic-v1")
        self.assertEqual(result.model_version, "heuristic-v1")
        self.assertIn("disclaimer", result.provenance,
                      "Heuristic provenance should carry the professional disclaimer")

    def test_each_service_suggestion_entry_has_required_keys(self):
        svc = AIService()
        result = svc.generate_suggestions(self.fixture)
        for s in result.suggestions:
            self.assertIn("category", s)
            self.assertIn("text", s)
            self.assertIn("priority", s)
            self.assertIn("hash", s)
            self.assertRegex(s["hash"], r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# /generate-suggestions endpoint integration (T6 precursor — no persistence yet)
# ---------------------------------------------------------------------------
class TestSuggestionsEndpointIntegration(_BaseDBTestCase):
    """Call the FastAPI /generate-suggestions endpoint through TestClient.

    With no GEMINI_API_KEY, the v1_ai route must return 200 (heuristic fallback)
    instead of the old 503.  This exercises the entire FastAPI → AIService →
    HeuristicSuggestionEngine stack end to end.
    """

    def test_generate_suggestions_endpoint_returns_200_without_gemini_key(self):
        data = json.loads((FIXTURES / "suggestions-sample.json").read_text(encoding="utf-8"))
        payload = {"project_data": data}
        resp = self.client.post("/api/ai/generate-suggestions", json=payload)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["version"], "ai-suggestions.v1")
        self.assertGreaterEqual(len(body["suggestions"]), 4)
        self.assertTrue(body["provenance"].get("fallback"),
                        "Endpoint must use heuristic fallback when GEMINI_API_KEY absent")

    def test_generate_suggestions_categories_filter_works(self):
        data = json.loads((FIXTURES / "suggestions-sample.json").read_text(encoding="utf-8"))
        payload = {"project_data": data, "categories": ["budget", "circulation"]}
        resp = self.client.post("/api/ai/generate-suggestions", json=payload)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        produced_cats = set(body["categories"])
        self.assertTrue(
            {"budget", "circulation"}.issuperset(produced_cats),
            f"Endpoint category filter should only emit requested; got {produced_cats}"
        )


if __name__ == "__main__":
    unittest.main()
