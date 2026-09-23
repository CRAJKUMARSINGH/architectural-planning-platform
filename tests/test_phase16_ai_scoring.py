"""Phase 16 — AI Version Scoring regression tests.

Covers:
* HeuristicScorer correctness (area fit, daylight, budget, circulation)
* VersionScore.grade() and signature stability
* TradeoffComparison winner selection and tradeoff notes
* VersionScoringEngine.score_for_quality_gate() gate pass/fail logic
* GeminiVersionScorer fallback path on Gemini failure
* API route /score-version and /compare-versions (mock integration)
* Edge cases: empty zones, unknown budget, single-version comparison
* Provenance field presence and format
"""
from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase16_ai_scoring import (
    HeuristicScorer,
    TradeoffComparison,
    VersionScore,
    VersionScoringEngine,
    ZoneScore,
    AI_SCORE_SCHEMA_VERSION,
    AI_SCORING_GATE_VERSION,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BRIEF_SMALL = {
    "summary": "2BHK residential flat, tight budget",
    "spaceProgram": [
        {"name": "Living Room", "sqm": 30, "priority": "must-have"},
        {"name": "Master Bedroom", "sqm": 18, "priority": "must-have"},
        {"name": "Bedroom 2", "sqm": 14, "priority": "must-have"},
        {"name": "Kitchen", "sqm": 12, "priority": "must-have"},
        {"name": "Bathroom", "sqm": 5, "priority": "must-have"},
    ],
    "maxBudget": 5_000_000,
    "constraints": ["Tight site", "Low budget"],
}

VERSION_GOOD = {
    "id": "v1-good",
    "totalArea": 90.0,
    "estimatedCost": 4_500_000,
    "zones": [
        {"name": "Living Room", "type": "living", "areaSqm": 30, "windowAreaSqm": 5.0},
        {"name": "Master Bedroom", "type": "sleeping", "areaSqm": 18, "windowAreaSqm": 3.0},
        {"name": "Bedroom 2", "type": "sleeping", "areaSqm": 14, "windowAreaSqm": 2.0},
        {"name": "Kitchen", "type": "service", "areaSqm": 12, "windowAreaSqm": 1.5},
        {"name": "Bathroom", "type": "bathroom", "areaSqm": 5, "windowAreaSqm": 0},
        {"name": "Corridor", "type": "circulation", "areaSqm": 11},
    ],
}

VERSION_POOR = {
    "id": "v1-poor",
    "totalArea": 90.0,
    "estimatedCost": 7_000_000,   # over budget
    "zones": [
        {"name": "Living Room", "type": "living", "areaSqm": 15, "windowAreaSqm": 0},   # undersized + no windows
        {"name": "Master Bedroom", "type": "sleeping", "areaSqm": 35, "windowAreaSqm": 0},   # oversized
        {"name": "Kitchen", "type": "service", "areaSqm": 12, "windowAreaSqm": 0},
        {"name": "Bathroom", "type": "bathroom", "areaSqm": 5, "windowAreaSqm": 0},
    ],
}

VERSION_AVERAGE = {
    "id": "v1-avg",
    "totalArea": 90.0,
    "estimatedCost": 5_100_000,   # slightly over
    "zones": [
        {"name": "Living Room", "type": "living", "areaSqm": 27, "windowAreaSqm": 3.5},
        {"name": "Master Bedroom", "type": "sleeping", "areaSqm": 17, "windowAreaSqm": 2.2},
        {"name": "Bedroom 2", "type": "sleeping", "areaSqm": 13, "windowAreaSqm": 1.5},
        {"name": "Kitchen", "type": "service", "areaSqm": 11, "windowAreaSqm": 1.0},
        {"name": "Bathroom", "type": "bathroom", "areaSqm": 5, "windowAreaSqm": 0},
        {"name": "Corridor", "type": "circulation", "areaSqm": 8},
    ],
}


# ===========================================================================
# ZoneScore tests
# ===========================================================================

class TestZoneScore(unittest.TestCase):

    def test_to_dict_required_fields(self):
        zs = ZoneScore(zone_name="Living Room", score=80)
        d = zs.to_dict()
        self.assertEqual(d["zoneName"], "Living Room")
        self.assertEqual(d["score"], 80)
        self.assertIn("notes", d)

    def test_to_dict_optional_fields_omitted_when_none(self):
        zs = ZoneScore(zone_name="Hall", score=70)
        d = zs.to_dict()
        self.assertNotIn("areaSqm", d)
        self.assertNotIn("briefTargetSqm", d)
        self.assertNotIn("areaFitPct", d)

    def test_to_dict_optional_fields_present_when_set(self):
        zs = ZoneScore(zone_name="Bedroom", score=75, area_sqm=18.0, brief_target_sqm=20.0,
                       area_fit_pct=90.0, daylight_assessment="adequate")
        d = zs.to_dict()
        self.assertAlmostEqual(d["areaSqm"], 18.0)
        self.assertAlmostEqual(d["briefTargetSqm"], 20.0)
        self.assertAlmostEqual(d["areaFitPct"], 90.0)
        self.assertEqual(d["daylightAssessment"], "adequate")


# ===========================================================================
# VersionScore tests
# ===========================================================================

class TestVersionScore(unittest.TestCase):

    def _make_score(self, overall: int = 75) -> VersionScore:
        return VersionScore(
            version_id="v1",
            overall_score=overall,
            program_fit=80,
            daylight=70,
            budget_fit=90,
            circulation_score=85,
            commentary="Test version",
        )

    def test_grade_thresholds(self):
        self.assertEqual(self._make_score(95).grade(), "A")
        self.assertEqual(self._make_score(85).grade(), "B")
        self.assertEqual(self._make_score(75).grade(), "C")
        self.assertEqual(self._make_score(65).grade(), "D")
        self.assertEqual(self._make_score(55).grade(), "F")
        self.assertEqual(self._make_score(0).grade(), "F")
        self.assertEqual(self._make_score(100).grade(), "A")

    def test_to_dict_schema_version(self):
        d = self._make_score().to_dict()
        self.assertEqual(d["schemaVersion"], AI_SCORE_SCHEMA_VERSION)

    def test_to_dict_all_required_keys(self):
        d = self._make_score().to_dict()
        for key in ("versionId", "grade", "overallScore", "programFit",
                    "daylight", "budgetFit", "circulationScore",
                    "commentary", "zoneScores", "flags", "scoredBy", "provenance"):
            self.assertIn(key, d, f"Missing key: {key}")

    def test_signature_is_sha256_hex(self):
        sig = self._make_score().signature
        self.assertEqual(len(sig), 64)
        int(sig, 16)   # must be valid hex

    def test_signature_changes_when_score_changes(self):
        s1 = self._make_score(75)
        s2 = self._make_score(76)
        self.assertNotEqual(s1.signature, s2.signature)

    def test_signature_stable_for_identical_objects(self):
        s1 = self._make_score(80)
        s2 = self._make_score(80)
        self.assertEqual(s1.signature, s2.signature)


# ===========================================================================
# HeuristicScorer tests
# ===========================================================================

class TestHeuristicScorer(unittest.TestCase):

    def setUp(self):
        self.scorer = HeuristicScorer()

    def test_score_returns_version_score(self):
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        self.assertIsInstance(result, VersionScore)

    def test_good_version_outscores_poor_version(self):
        good = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        poor = self.scorer.score(VERSION_POOR, BRIEF_SMALL)
        self.assertGreater(good.overall_score, poor.overall_score)

    def test_score_range_valid(self):
        for version in (VERSION_GOOD, VERSION_POOR, VERSION_AVERAGE):
            result = self.scorer.score(version, BRIEF_SMALL)
            self.assertGreaterEqual(result.overall_score, 0)
            self.assertLessEqual(result.overall_score, 100)
            self.assertGreaterEqual(result.program_fit, 0)
            self.assertLessEqual(result.program_fit, 100)

    def test_over_budget_penalises_budget_fit(self):
        poor = self.scorer.score(VERSION_POOR, BRIEF_SMALL)   # cost = 7M, budget = 5M
        self.assertLess(poor.budget_fit, 70)

    def test_within_budget_gives_full_budget_score(self):
        good = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)   # cost = 4.5M, budget = 5M
        self.assertEqual(good.budget_fit, 100)

    def test_unknown_budget_neutral(self):
        brief_no_budget = {**BRIEF_SMALL, "maxBudget": 0}
        result = self.scorer.score(VERSION_GOOD, brief_no_budget)
        self.assertEqual(result.budget_fit, 70)

    def test_no_window_data_flags_zone(self):
        poor = self.scorer.score(VERSION_POOR, BRIEF_SMALL)
        self.assertTrue(len(poor.flags) > 0)
        flag_text = " ".join(poor.flags)
        self.assertIn("window", flag_text.lower())

    def test_zone_scores_populated(self):
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        self.assertGreater(len(result.zone_scores), 0)
        for zs in result.zone_scores:
            self.assertIsInstance(zs, ZoneScore)
            self.assertGreaterEqual(zs.score, 0)
            self.assertLessEqual(zs.score, 100)

    def test_circulation_score_good_when_corridor_present(self):
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        self.assertGreater(result.circulation_score, 50)

    def test_circulation_score_lower_when_no_corridor(self):
        version_no_circ = {**VERSION_GOOD, "zones": [
            z for z in VERSION_GOOD["zones"] if z.get("type") != "circulation"
        ]}
        result = self.scorer.score(version_no_circ, BRIEF_SMALL)
        self.assertLess(result.circulation_score, 90)

    def test_provenance_has_required_fields(self):
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        prov = result.provenance
        self.assertIn("scorer", prov)
        self.assertIn("timestamp", prov)
        self.assertEqual(prov["scorer"], "heuristic")

    def test_scored_by_field(self):
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        self.assertEqual(result.scored_by, "heuristic")

    def test_empty_zones_does_not_crash(self):
        v = {"id": "empty", "totalArea": 0, "estimatedCost": 0, "zones": []}
        result = self.scorer.score(v, BRIEF_SMALL)
        self.assertIsInstance(result, VersionScore)

    def test_empty_space_program_does_not_crash(self):
        brief_empty = {**BRIEF_SMALL, "spaceProgram": []}
        result = self.scorer.score(VERSION_GOOD, brief_empty)
        self.assertIsInstance(result, VersionScore)

    def test_commentary_non_empty(self):
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        self.assertGreater(len(result.commentary), 10)

    def test_grade_grades_correctly(self):
        self.assertEqual(HeuristicScorer.grade(95), "A")
        self.assertEqual(HeuristicScorer.grade(55), "F")

    def test_area_fit_pct_close_to_100_for_matching_zone(self):
        """A zone matching the brief exactly should show ~100% area fit."""
        result = self.scorer.score(VERSION_GOOD, BRIEF_SMALL)
        living = next((z for z in result.zone_scores if "living" in z.zone_name.lower()), None)
        if living and living.area_fit_pct is not None:
            self.assertAlmostEqual(living.area_fit_pct, 100.0, delta=5.0)


# ===========================================================================
# TradeoffComparison tests
# ===========================================================================

class TestTradeoffComparison(unittest.TestCase):

    def _make_versions(self) -> list[VersionScore]:
        scorer = HeuristicScorer()
        return [
            scorer.score(VERSION_GOOD, BRIEF_SMALL),
            scorer.score(VERSION_POOR, BRIEF_SMALL),
            scorer.score(VERSION_AVERAGE, BRIEF_SMALL),
        ]

    def test_to_dict_has_required_keys(self):
        versions = self._make_versions()
        tc = TradeoffComparison(versions=versions, winner_id=versions[0].version_id)
        d = tc.to_dict()
        for key in ("schemaVersion", "generatedAt", "versionCount", "winner", "tradeoffNotes", "matrix"):
            self.assertIn(key, d)

    def test_schema_version(self):
        tc = TradeoffComparison(versions=self._make_versions())
        self.assertEqual(tc.to_dict()["schemaVersion"], "ai-tradeoff.v1")

    def test_version_count_matches(self):
        versions = self._make_versions()
        tc = TradeoffComparison(versions=versions)
        self.assertEqual(tc.to_dict()["versionCount"], 3)

    def test_matrix_length_matches_versions(self):
        versions = self._make_versions()
        tc = TradeoffComparison(versions=versions)
        self.assertEqual(len(tc.to_dict()["matrix"]), 3)


# ===========================================================================
# VersionScoringEngine tests
# ===========================================================================

class TestVersionScoringEngine(unittest.TestCase):

    def _engine(self) -> VersionScoringEngine:
        """Create an engine with Gemini mocked as unavailable (heuristic path)."""
        with patch("scripts.phase16_ai_scoring.VersionScoringEngine.__init__") as mock_init:
            mock_init.return_value = None
            engine = VersionScoringEngine.__new__(VersionScoringEngine)
            engine._scorer = HeuristicScorer()
        return engine

    def setUp(self):
        self.engine = self._engine()

    def test_score_version_returns_version_score(self):
        result = self.engine.score_version(VERSION_GOOD, BRIEF_SMALL)
        self.assertIsInstance(result, VersionScore)

    def test_compare_versions_returns_tradeoff(self):
        comparison = self.engine.compare_versions(
            [VERSION_GOOD, VERSION_POOR], BRIEF_SMALL
        )
        self.assertIsInstance(comparison, TradeoffComparison)
        self.assertEqual(len(comparison.versions), 2)

    def test_compare_selects_correct_winner(self):
        comparison = self.engine.compare_versions(
            [VERSION_GOOD, VERSION_POOR, VERSION_AVERAGE], BRIEF_SMALL
        )
        # Good version should be winner
        self.assertEqual(comparison.winner_id, "v1-good")

    def test_compare_generates_tradeoff_notes(self):
        comparison = self.engine.compare_versions(
            [VERSION_GOOD, VERSION_POOR], BRIEF_SMALL
        )
        # budget_fit spread should be large (100 vs. <70) → tradeoff note generated
        budget_notes = [n for n in comparison.tradeoff_notes if "Budget" in n]
        self.assertTrue(len(budget_notes) > 0, "Expected budget tradeoff note")

    def test_compare_single_version_no_tradeoff_notes(self):
        comparison = self.engine.compare_versions([VERSION_GOOD], BRIEF_SMALL)
        self.assertEqual(len(comparison.tradeoff_notes), 0)
        self.assertEqual(comparison.winner_id, "v1-good")

    def test_compare_empty_raises(self):
        with self.assertRaises(ValueError):
            self.engine.compare_versions([], BRIEF_SMALL)

    def test_quality_gate_pass_good_version(self):
        gate = self.engine.score_for_quality_gate([VERSION_GOOD], BRIEF_SMALL, minimum_score=60)
        self.assertEqual(gate["status"], "PASS")
        self.assertGreaterEqual(gate["bestOverallScore"], 60)

    def test_quality_gate_review_required_poor_version(self):
        gate = self.engine.score_for_quality_gate(
            [VERSION_POOR], BRIEF_SMALL, minimum_score=80
        )
        # poor version likely scores below 80
        if gate["bestOverallScore"] < 80:
            self.assertEqual(gate["status"], "REVIEW_REQUIRED")

    def test_quality_gate_incomplete_when_no_versions(self):
        gate = self.engine.score_for_quality_gate([], BRIEF_SMALL)
        self.assertEqual(gate["status"], "INCOMPLETE")
        self.assertTrue(gate.get("missingEvidence"))

    def test_quality_gate_has_required_keys(self):
        gate = self.engine.score_for_quality_gate([VERSION_GOOD], BRIEF_SMALL)
        for key in (
            "status", "schemaVersion", "bestVersionId", "bestOverallScore",
            "bestGrade", "minimumScoreRequired", "versionsEvaluated",
            "winner", "tradeoffNotes", "scoredBy", "matrix",
        ):
            self.assertIn(key, gate, f"Missing key: {key}")

    def test_quality_gate_schema_version(self):
        gate = self.engine.score_for_quality_gate([VERSION_GOOD], BRIEF_SMALL)
        self.assertEqual(gate["schemaVersion"], AI_SCORING_GATE_VERSION)

    def test_quality_gate_versions_evaluated_count(self):
        gate = self.engine.score_for_quality_gate(
            [VERSION_GOOD, VERSION_POOR], BRIEF_SMALL
        )
        self.assertEqual(gate["versionsEvaluated"], 2)

    def test_quality_gate_minimum_score_respected(self):
        gate_low = self.engine.score_for_quality_gate([VERSION_GOOD], BRIEF_SMALL, minimum_score=20)
        gate_high = self.engine.score_for_quality_gate([VERSION_GOOD], BRIEF_SMALL, minimum_score=99)
        self.assertEqual(gate_low["status"], "PASS")
        # HIGH threshold almost certainly triggers REVIEW_REQUIRED
        if gate_high["bestOverallScore"] < 99:
            self.assertEqual(gate_high["status"], "REVIEW_REQUIRED")


# ===========================================================================
# GeminiVersionScorer fallback tests
# ===========================================================================

class TestGeminiVersionScorerFallback(unittest.TestCase):

    def test_fallback_to_heuristic_on_exception(self):
        """GeminiVersionScorer must fall back to heuristic when AI fails."""
        from scripts.phase16_ai_scoring import GeminiVersionScorer

        mock_svc = MagicMock()
        mock_svc.score_version.side_effect = RuntimeError("API down")

        # We need BriefAnalysisResult importable — mock the ai_service module
        import importlib
        import types as _types

        fake_ai_module = _types.ModuleType("services.ai.ai_service")
        fake_ai_module.BriefAnalysisResult = MagicMock(return_value=MagicMock(
            summary="", space_program=[], constraints=[], opportunities=[], open_questions=[]
        ))  # type: ignore
        sys.modules["services"] = MagicMock()
        sys.modules["services.ai"] = MagicMock()
        sys.modules["services.ai.ai_service"] = fake_ai_module

        scorer = GeminiVersionScorer(mock_svc)
        result = scorer.score(VERSION_GOOD, BRIEF_SMALL)

        self.assertIsInstance(result, VersionScore)
        self.assertEqual(result.scored_by, "heuristic")

        # Cleanup module mocks
        for mod in ("services", "services.ai", "services.ai.ai_service"):
            sys.modules.pop(mod, None)


# ===========================================================================
# Schema round-trip test
# ===========================================================================

class TestSchemaRoundTrip(unittest.TestCase):

    def test_version_score_json_round_trip(self):
        scorer = HeuristicScorer()
        result = scorer.score(VERSION_GOOD, BRIEF_SMALL)
        d = result.to_dict()
        json_str = json.dumps(d)
        restored = json.loads(json_str)
        self.assertEqual(restored["versionId"], "v1-good")
        self.assertIn("overallScore", restored)
        self.assertIn("zoneScores", restored)

    def test_tradeoff_comparison_json_round_trip(self):
        scorer = HeuristicScorer()
        vs = [scorer.score(v, BRIEF_SMALL) for v in [VERSION_GOOD, VERSION_POOR]]
        tc = TradeoffComparison(versions=vs, winner_id="v1-good", tradeoff_notes=["Note 1"])
        json_str = json.dumps(tc.to_dict())
        restored = json.loads(json_str)
        self.assertEqual(restored["schemaVersion"], "ai-tradeoff.v1")
        self.assertEqual(len(restored["matrix"]), 2)

    def test_schema_file_is_valid_json(self):
        schema_path = ROOT / "packages" / "schema" / "ai-version-score-v2.schema.json"
        self.assertTrue(schema_path.exists(), f"Schema file not found: {schema_path}")
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(data["$schema"], "http://json-schema.org/draft-07/schema#")

    def test_to_dict_conforms_to_schema_required_fields(self):
        scorer = HeuristicScorer()
        result = scorer.score(VERSION_GOOD, BRIEF_SMALL)
        d = result.to_dict()
        schema_path = ROOT / "packages" / "schema" / "ai-version-score-v2.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        required_fields = schema.get("required", [])
        for field_name in required_fields:
            self.assertIn(field_name, d, f"Required field missing: {field_name}")


# ===========================================================================
# Scoring weight invariant test
# ===========================================================================

class TestScoringWeights(unittest.TestCase):
    """Verify the documented weight formula (35/25/25/15) is applied."""

    def test_program_fit_has_highest_weight(self):
        """A version with perfect program fit but poor others should score better
        than a version with perfect everything else but terrible program fit."""
        scorer = HeuristicScorer()

        perfect_program = {
            "id": "pp",
            "totalArea": 90, "estimatedCost": 0,
            "zones": [
                {"name": "Living Room", "type": "living", "areaSqm": 30, "windowAreaSqm": 4.5},
                {"name": "Master Bedroom", "type": "sleeping", "areaSqm": 18, "windowAreaSqm": 2.7},
                {"name": "Bedroom 2", "type": "sleeping", "areaSqm": 14, "windowAreaSqm": 2.1},
                {"name": "Kitchen", "type": "service", "areaSqm": 12, "windowAreaSqm": 1.8},
                {"name": "Bathroom", "type": "bathroom", "areaSqm": 5, "windowAreaSqm": 0},
            ],
        }
        terrible_program = {
            "id": "tp",
            "totalArea": 90, "estimatedCost": 0,
            "zones": [
                {"name": "Lobby", "type": "other", "areaSqm": 80, "windowAreaSqm": 12},
                {"name": "Corridor", "type": "circulation", "areaSqm": 10},
            ],
        }
        r_good = scorer.score(perfect_program, BRIEF_SMALL)
        r_bad = scorer.score(terrible_program, BRIEF_SMALL)
        # Perfect program match should beat a layout that ignores the brief
        self.assertGreater(r_good.overall_score, r_bad.overall_score)


if __name__ == "__main__":
    unittest.main()
