"""Tests for Phase 14 Brief Compiler AI integration — Week 11/12 + Gemini API."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "packages" / "schema" / "ai-brief-analysis.schema.json"


@pytest.fixture(scope="module")
def brief_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPhase14BriefCompilerIntegration:
    def test_compile_brief_with_ai_fallback_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from scripts.week1112 import compile_brief_with_ai

        brief_text = "Client wants a 2 storey chambers office with 3 bedrooms, 1 living room and 1 library on a 40ft by 60ft plot. North is facing east."
        result = compile_brief_with_ai(brief_text)

        assert "facts" in result
        assert result["facts"]["site"]["width"]["sourceUnit"] == "ft"
        assert result["facts"]["site"]["width"]["value"] == 480.0
        assert "aiEnrichment" in result
        assert result["aiEnrichment"]["available"] is False

    def test_compile_brief_with_ai_mock_enrichment(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-mock-key")
        from scripts.week1112 import compile_brief_with_ai
        from services.ai.ai_service import BriefAnalysisResult

        mock_result = BriefAnalysisResult(
            summary="2-storey judicial chambers with residential suite",
            space_program=[
                {"name": "Advocate Office", "sqm": 25.0, "priority": "high", "notes": "Private client consultation"},
                {"name": "Law Library", "sqm": 20.0, "priority": "high", "notes": "Legal volumes & study"},
                {"name": "Living Room", "sqm": 30.0, "priority": "medium", "notes": "Upper floor"},
            ],
            constraints=["Plot size 40x60 ft", "North-east orientation"],
            opportunities=["Double height lobby", "Daylit library on north side"],
            open_questions=["Is client parking required inside setback?"],
            provenance={
                "is_ai_generated": True,
                "model": "gemini-2.5-flash",
                "timestamp": "2026-09-22T00:00:00Z",
                "confidence": 0.92,
            },
            model_version="gemini-2.5-flash",
        )

        with patch("services.ai.ai_service.AIService.analyze_brief", return_value=mock_result), \
             patch("services.ai.ai_service.AIService.__init__", return_value=None):
            
            with patch("services.ai.ai_service.get_ai_service") as mock_get_service:
                mock_service_instance = MagicMock()
                mock_service_instance.available = True
                mock_service_instance.analyze_brief.return_value = mock_result
                mock_get_service.return_value = mock_service_instance

                brief_text = "Client wants a 2 storey chambers office with 3 bedrooms, 1 living room and 1 library on a 40ft by 60ft plot."
                result = compile_brief_with_ai(brief_text)

                assert "aiEnrichment" in result
                enrichment = result["aiEnrichment"]
                assert enrichment["version"] == "ai-brief-analysis.v1"
                assert len(enrichment["spaceProgram"]) == 3
                assert enrichment["spaceProgram"][0]["name"] == "Advocate Office"
                assert len(enrichment["constraints"]) == 2
                assert len(enrichment["opportunities"]) == 2
                assert len(enrichment["openQuestions"]) == 1
                assert enrichment["provenance"]["is_ai_generated"] is True

    def test_schema_validates_ai_enrichment_structure(self, brief_schema):
        assert brief_schema["title"] == "AI Brief Analysis"
        assert "properties" in brief_schema
        for req_prop in ["version", "summary", "spaceProgram", "constraints", "opportunities", "openQuestions", "provenance", "modelVersion"]:
            assert req_prop in brief_schema["properties"]
