#!/usr/bin/env python3
"""Phase 16 — AI Version Scoring & Tradeoff Analysis.

Integrates AI-powered design-version scoring into the Phase 12 quality gate
framework.  Produces:

* Overall, program-fit, daylight, budget-fit scores (0-100)
* Written zone-level commentary calling out specific rooms
* Tradeoff matrix comparing two or more design versions
* AI scoring provenance record for the audit trail
* ``ai_scoring`` track contribution to ``build_quality_gate``

Design invariants
-----------------
* The geometry-authority principle is preserved: the scoring is advisory.
  No geometry mutation occurs in this module.
* ``AIService`` degrades gracefully when the Gemini SDK / key are absent;
  a deterministic heuristic fallback is used instead.
* All scoring outputs validate against ``ai-version-score.v1`` schema.
* The quality-gate contribution only affects the ``aiScoring`` track, never
  the hard ``adversarial`` / ``professionalReview`` tracks.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema / path constants
# ---------------------------------------------------------------------------

AI_SCORE_SCHEMA_VERSION = "ai-version-score.v1"
AI_SCORING_GATE_VERSION = "ai-scoring-gate.v1"

SCORE_REPORT_DIR = ROOT / "bar-association-hall" / "ai-scoring"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ZoneScore:
    """Score and commentary for a single design zone."""
    zone_name: str
    score: int          # 0-100
    area_sqm: float | None = None
    brief_target_sqm: float | None = None
    area_fit_pct: float | None = None   # actual / target * 100
    daylight_assessment: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "zoneName": self.zone_name,
            "score": self.score,
            "notes": self.notes,
        }
        if self.area_sqm is not None:
            d["areaSqm"] = self.area_sqm
        if self.brief_target_sqm is not None:
            d["briefTargetSqm"] = self.brief_target_sqm
        if self.area_fit_pct is not None:
            d["areaFitPct"] = round(self.area_fit_pct, 1)
        if self.daylight_assessment:
            d["daylightAssessment"] = self.daylight_assessment
        return d


@dataclass
class VersionScore:
    """Full AI scoring result for a single design version."""
    version_id: str
    overall_score: int      # 0-100
    program_fit: int        # 0-100
    daylight: int           # 0-100
    budget_fit: int         # 0-100
    circulation_score: int  # 0-100
    commentary: str
    zone_scores: list[ZoneScore] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AI_SCORE_SCHEMA_VERSION
    scored_by: str = "heuristic"  # "gemini" | "heuristic"

    def grade(self) -> str:
        s = self.overall_score
        if s >= 90: return "A"
        if s >= 80: return "B"
        if s >= 70: return "C"
        if s >= 60: return "D"
        return "F"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "versionId": self.version_id,
            "grade": self.grade(),
            "overallScore": self.overall_score,
            "programFit": self.program_fit,
            "daylight": self.daylight,
            "budgetFit": self.budget_fit,
            "circulationScore": self.circulation_score,
            "commentary": self.commentary,
            "zoneScores": [z.to_dict() for z in self.zone_scores],
            "flags": self.flags,
            "scoredBy": self.scored_by,
            "provenance": self.provenance,
        }

    @property
    def signature(self) -> str:
        payload = json.dumps(
            self.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
        return hashlib.sha256(payload).hexdigest()


@dataclass
class TradeoffComparison:
    """Side-by-side tradeoff matrix for two or more versions."""
    versions: list[VersionScore]
    winner_id: str | None = None
    tradeoff_notes: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "ai-tradeoff.v1",
            "generatedAt": self.generated_at,
            "versionCount": len(self.versions),
            "winner": self.winner_id,
            "tradeoffNotes": self.tradeoff_notes,
            "matrix": [v.to_dict() for v in self.versions],
        }


# ---------------------------------------------------------------------------
# Heuristic scorer (geometry-only, no LLM)
# ---------------------------------------------------------------------------


class HeuristicScorer:
    """Deterministic baseline scorer used when Gemini is unavailable."""

    AREA_TOLERANCE = 0.30
    MIN_CIRC_RATIO = 0.10
    TARGET_WFR = 0.15

    def score(self, version_data: dict[str, Any], brief: dict[str, Any]) -> VersionScore:
        version_id = str(version_data.get("id", "unknown"))
        zones: list[dict[str, Any]] = version_data.get("zones", [])
        total_area = float(version_data.get("totalArea", 0))
        estimated_cost = float(version_data.get("estimatedCost", 0))
        max_budget = float(brief.get("maxBudget", 0))
        space_program: list[dict[str, Any]] = brief.get("spaceProgram", [])

        zone_scores, program_fit, daylight, flags = self._score_zones(zones, space_program)
        circulation = self._score_circulation(zones, total_area)
        budget_fit = self._score_budget(estimated_cost, max_budget)

        overall = int(
            0.35 * program_fit
            + 0.25 * daylight
            + 0.25 * budget_fit
            + 0.15 * circulation
        )
        overall = max(0, min(100, overall))
        commentary = self._commentary(overall, program_fit, daylight, budget_fit, circulation, flags)

        return VersionScore(
            version_id=version_id,
            overall_score=overall,
            program_fit=program_fit,
            daylight=daylight,
            budget_fit=budget_fit,
            circulation_score=circulation,
            commentary=commentary,
            zone_scores=zone_scores,
            flags=flags,
            provenance={
                "scorer": "heuristic",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "totalAreaSqm": total_area,
                "zonesEvaluated": len(zones),
            },
            scored_by="heuristic",
        )

    def _score_zones(
        self, zones: list[dict[str, Any]], space_program: list[dict[str, Any]]
    ) -> tuple[list[ZoneScore], int, int, list[str]]:
        program_index: dict[str, float] = {
            str(item.get("name", "")).lower(): float(item.get("sqm", 0) or 0)
            for item in space_program
            if item.get("name") and item.get("sqm")
        }
        zone_scores: list[ZoneScore] = []
        program_scores: list[int] = []
        daylight_scores: list[int] = []
        flags: list[str] = []

        for zone in zones:
            name = str(zone.get("name", "Zone")).lower()
            area = float(zone.get("areaSqm", 0) or 0)
            windows = float(zone.get("windowAreaSqm", 0) or 0)
            zone_type = str(zone.get("type", "")).lower()

            target = program_index.get(name)
            if target and target > 0 and area > 0:
                ratio = area / target
                deviation = abs(ratio - 1.0)
                pfit = int(max(0, 100 - (deviation / self.AREA_TOLERANCE) * 40))
                area_fit_pct: float | None = ratio * 100
            else:
                pfit = 70
                area_fit_pct = None

            if area > 0 and windows > 0:
                wfr = windows / area
                dlight = int(min(100, (wfr / self.TARGET_WFR) * 80))
            elif zone_type in ("service", "storage", "wc", "bathroom", "toilet"):
                dlight = 70
            else:
                dlight = 40
                flags.append(f"No window data for zone '{name}'")

            program_scores.append(pfit)
            daylight_scores.append(dlight)
            zone_scores.append(ZoneScore(
                zone_name=zone.get("name", name),
                score=int((pfit + dlight) / 2),
                area_sqm=area if area > 0 else None,
                brief_target_sqm=program_index.get(name),
                area_fit_pct=area_fit_pct,
                daylight_assessment="adequate" if dlight >= 65 else "poor",
                notes=f"Program fit {pfit}/100, daylight {dlight}/100",
            ))

        pfit_avg = int(sum(program_scores) / len(program_scores)) if program_scores else 50
        dlight_avg = int(sum(daylight_scores) / len(daylight_scores)) if daylight_scores else 50
        return zone_scores, pfit_avg, dlight_avg, flags

    def _score_circulation(self, zones: list[dict[str, Any]], total_area: float) -> int:
        if total_area <= 0:
            return 50
        circ_area = sum(
            float(z.get("areaSqm", 0) or 0) for z in zones
            if str(z.get("type", "")).lower() in ("circulation", "corridor", "hallway", "lobby")
        )
        ratio = circ_area / total_area
        if ratio < self.MIN_CIRC_RATIO:
            return int(max(30, 100 - (self.MIN_CIRC_RATIO - ratio) / self.MIN_CIRC_RATIO * 60))
        if ratio > 0.25:
            return int(max(50, 100 - (ratio - 0.25) / 0.25 * 40))
        return 90

    def _score_budget(self, estimated_cost: float, max_budget: float) -> int:
        if max_budget <= 0 or estimated_cost <= 0:
            return 70
        ratio = estimated_cost / max_budget
        if ratio <= 0.9:
            return 100
        if ratio <= 1.0:
            return int(100 - (ratio - 0.9) * 200)
        return int(max(0, 100 - (ratio - 1.0) * 200))

    def _commentary(
        self, overall: int, pfit: int, daylight: int, budget: int, circulation: int, flags: list[str]
    ) -> str:
        grade = self.grade(overall)
        parts = [f"Overall grade {grade} ({overall}/100)."]
        if pfit < 60:
            parts.append("Program fit is below target — some zones deviate significantly from the brief.")
        elif pfit >= 85:
            parts.append("Space program is well matched to the brief.")
        if daylight < 60:
            parts.append("Daylight provision needs attention — consider enlarging or adding windows.")
        elif daylight >= 85:
            parts.append("Daylighting strategy is strong.")
        if budget < 70:
            parts.append("Design is over or near budget — cost reduction strategies recommended.")
        elif budget == 100:
            parts.append("Design is comfortably within budget.")
        if circulation < 60:
            parts.append("Circulation area may be insufficient for comfortable movement.")
        if flags:
            parts.append("Flags: " + "; ".join(flags[:3]) + ("…" if len(flags) > 3 else "."))
        return " ".join(parts)

    @staticmethod
    def grade(score: int) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"


# ---------------------------------------------------------------------------
# AI scorer (Gemini integration)
# ---------------------------------------------------------------------------


class GeminiVersionScorer:
    """Score a design version against a brief using the Gemini LLM."""

    def __init__(self, ai_service: Any) -> None:
        self._svc = ai_service

    def score(self, version_data: dict[str, Any], brief: dict[str, Any]) -> VersionScore:
        from services.ai.ai_service import BriefAnalysisResult  # local import

        brief_result = BriefAnalysisResult(
            summary=brief.get("summary", ""),
            space_program=brief.get("spaceProgram", []),
            constraints=brief.get("constraints", []),
            opportunities=brief.get("opportunities", []),
            open_questions=[],
        )
        try:
            raw = self._svc.score_version(version_data, brief_result)
            zone_scores = [
                ZoneScore(
                    zone_name=z.get("zoneName", ""),
                    score=int(z.get("score", 50)),
                    notes=z.get("notes", ""),
                )
                for z in raw.zone_scores
            ]
            return VersionScore(
                version_id=str(version_data.get("id", "unknown")),
                overall_score=raw.overall_score,
                program_fit=raw.program_fit,
                daylight=raw.daylight,
                budget_fit=raw.budget_fit,
                circulation_score=70,   # Gemini doesn't return this; use neutral default
                commentary=raw.commentary,
                zone_scores=zone_scores,
                provenance={**raw.provenance, "scorer": "gemini"},
                scored_by="gemini",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini scoring failed (%s) — using heuristic fallback", exc)
            return HeuristicScorer().score(version_data, brief)


# ---------------------------------------------------------------------------
# Scoring engine (public facade)
# ---------------------------------------------------------------------------


class VersionScoringEngine:
    """Selects Gemini or heuristic scoring and orchestrates comparisons."""

    def __init__(self) -> None:
        try:
            from services.ai.ai_service import get_ai_service
            svc = get_ai_service()
            if svc.available:
                self._scorer: HeuristicScorer | GeminiVersionScorer = GeminiVersionScorer(svc)
                logger.info("VersionScoringEngine: using Gemini scorer")
            else:
                self._scorer = HeuristicScorer()
                logger.info("VersionScoringEngine: using heuristic scorer (AI unavailable)")
        except Exception:
            self._scorer = HeuristicScorer()
            logger.info("VersionScoringEngine: using heuristic scorer (AI import failed)")

    def score_version(self, version_data: dict[str, Any], brief: dict[str, Any]) -> VersionScore:
        """Score a single design version against the project brief."""
        return self._scorer.score(version_data, brief)

    def compare_versions(
        self, versions: list[dict[str, Any]], brief: dict[str, Any]
    ) -> TradeoffComparison:
        """Score all versions and return a tradeoff comparison.

        The version with the highest overall_score is declared winner.
        Tradeoff notes highlight dimensions with >= 10-point spread.
        """
        if not versions:
            raise ValueError("At least one version is required for comparison")

        scored = [self.score_version(v, brief) for v in versions]
        winner = max(scored, key=lambda s: s.overall_score)

        notes: list[str] = []
        if len(scored) >= 2:
            for dim, label in [
                ("program_fit", "Program fit"),
                ("daylight", "Daylight"),
                ("budget_fit", "Budget fit"),
                ("circulation_score", "Circulation"),
            ]:
                vals = [(getattr(s, dim), s.version_id) for s in scored]
                best_val, best_id = max(vals, key=lambda x: x[0])
                worst_val, worst_id = min(vals, key=lambda x: x[0])
                if best_val - worst_val >= 10:
                    notes.append(
                        f"{label}: '{best_id}' leads by {best_val - worst_val} pts over '{worst_id}'"
                    )

        return TradeoffComparison(
            versions=scored,
            winner_id=winner.version_id,
            tradeoff_notes=notes,
        )

    def score_for_quality_gate(
        self,
        versions: list[dict[str, Any]],
        brief: dict[str, Any],
        *,
        minimum_score: int = 60,
    ) -> dict[str, Any]:
        """Return an AI-scoring quality gate track dict for build_quality_gate."""
        if not versions:
            return {
                "status": "INCOMPLETE",
                "message": "No versions provided for AI scoring",
                "missingEvidence": True,
            }

        comparison = self.compare_versions(versions, brief)
        best = max(comparison.versions, key=lambda v: v.overall_score)
        status = "PASS" if best.overall_score >= minimum_score else "REVIEW_REQUIRED"

        return {
            "status": status,
            "schemaVersion": AI_SCORING_GATE_VERSION,
            "bestVersionId": best.version_id,
            "bestOverallScore": best.overall_score,
            "bestGrade": best.grade(),
            "minimumScoreRequired": minimum_score,
            "versionsEvaluated": len(versions),
            "winner": comparison.winner_id,
            "tradeoffNotes": comparison.tradeoff_notes,
            "scoredBy": best.scored_by,
            "matrix": [v.to_dict() for v in comparison.versions],
        }


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def save_scoring_report(comparison: TradeoffComparison, project_id: str = "default") -> Path:
    """Write tradeoff report JSON to the standard output directory."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SCORE_REPORT_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tradeoff-{ts}.json"
    out_path.write_text(
        json.dumps(comparison.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info("Saved scoring report to %s", out_path)
    return out_path


def load_scoring_report(path: Path) -> dict[str, Any]:
    """Load a previously saved tradeoff report."""
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    score_p = sub.add_parser("score", help="Score a single version against a brief")
    score_p.add_argument("version_json", help="Path to version JSON file")
    score_p.add_argument("brief_json", help="Path to brief JSON file")

    compare_p = sub.add_parser("compare", help="Compare multiple versions")
    compare_p.add_argument("brief_json", help="Path to brief JSON file")
    compare_p.add_argument("version_jsons", nargs="+", help="Version JSON files")
    compare_p.add_argument("--project-id", default="default")

    args = parser.parse_args(argv)
    engine = VersionScoringEngine()

    if args.command == "score":
        version_data = json.loads(Path(args.version_json).read_text(encoding="utf-8"))
        brief = json.loads(Path(args.brief_json).read_text(encoding="utf-8"))
        result = engine.score_version(version_data, brief)
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.command == "compare":
        versions = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.version_jsons]
        brief = json.loads(Path(args.brief_json).read_text(encoding="utf-8"))
        comparison = engine.compare_versions(versions, brief)
        out = save_scoring_report(comparison, project_id=args.project_id)
        print(json.dumps(comparison.to_dict(), indent=2))
        print(f"\nReport saved to: {out}", file=sys.stderr)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
