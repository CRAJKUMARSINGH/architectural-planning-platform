"""Unit tests for Phase 16A AI version scoring integration.

Tests the AI health endpoint, ScoringResult ORM model, and AI service
graceful degradation.

NOTE: Tests that depend on the /api/v1/ai/score-revision endpoint and
``get_session`` are skipped until that endpoint and its DB layer are
implemented (Phase 16B work item).
"""
import os
import unittest
import uuid
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

# Import the components we're testing
from services.api.main import app
from services.api.models.orm import ScoringResult, Revision, Project, User
from services.ai.ai_service import AIService, BriefAnalysisResult, VersionScoreResult

_SCORE_REVISION_ENDPOINT_TODO = (
    "score-revision endpoint and get_session not yet implemented in v1_ai.py (Phase 16B)"
)


class TestVersionScoringAPI(unittest.TestCase):
    """Test the AI version scoring API endpoints."""

    def setUp(self):
        """Set up test client and fixtures."""
        self.client = TestClient(app)
        self.test_project_id = str(uuid.uuid4())
        self.test_revision_id = str(uuid.uuid4())
        self.test_user_id = str(uuid.uuid4())

    @unittest.skip(_SCORE_REVISION_ENDPOINT_TODO)
    def test_score_revision_endpoint_exists(self):
        """Test that the scoring endpoint exists and is accessible."""
        response = self.client.post(
            f"/api/ai/score-revision/{self.test_project_id}",
            json={"revisionId": self.test_revision_id},
        )
        # The endpoint should exist (may return auth error, but not 404)
        self.assertNotEqual(response.status_code, 404)

    def test_ai_health_endpoint(self):
        """Test that the AI health check endpoint works.

        The AI router is mounted at /api (not /api/v1), so health is at /api/ai/health.
        """
        response = self.client.get("/api/ai/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("sdk_installed", data)


class TestScoringResultModel(unittest.TestCase):
    """Test the ScoringResult ORM model."""

    def test_scoring_result_creation(self):
        """Test creating a ScoringResult instance."""
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
        """Test that scores span the full 0-100 range without error."""
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


class TestAIServiceIntegration(unittest.TestCase):
    """Test AI service graceful degradation."""

    def test_ai_service_initialization_without_key(self):
        """AI service degrades gracefully when API key is absent."""
        saved = os.environ.pop("GEMINI_API_KEY", None)
        try:
            ai_service = AIService()
            self.assertIsNotNone(ai_service)
            self.assertFalse(ai_service.available)
        finally:
            if saved is not None:
                os.environ["GEMINI_API_KEY"] = saved

    def test_ai_service_initialization_with_key(self):
        """AI service is always a valid object even with a fake key."""
        os.environ["GEMINI_API_KEY"] = "test-key"
        try:
            ai_service = AIService()
            self.assertIsNotNone(ai_service)
        finally:
            os.environ.pop("GEMINI_API_KEY", None)


if __name__ == "__main__":
    unittest.main()