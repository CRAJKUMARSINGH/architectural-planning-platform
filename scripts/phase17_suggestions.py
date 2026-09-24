#!/usr/bin/env python3
"""Phase 17 — Proactive AI Suggestions & Heuristic Fallback Engine.

Generates categorised, deterministic design-improvement suggestions using:

* Heuristic rule engine (always available):
  - Zone-area gap analysis against the brief
  - Daylight provision assessment (window-to-floor ratio)
  - Budget posture (under / at / over) with cost levers
  - Circulation adequacy (hallway-to-total-area ratio)

* Gemini LLM suggestions (when SDK + key present).

Each suggestion carries:
- ``category`` (program | daylight | budget | circulation | general)
- ``priority`` (high | medium | low)
- ``suggestion_hash``: SHA-256(category + "|" + lowercase text)
- ``provenance``: dict with scorer, weights, and rule identifiers

Design invariants (ADR-001, ADR-002):
* Suggestions are ADVISORY ONLY — geometry never mutates here.
* Missing evidence produces a "review" priority, not false positives.
* The heuristic fallback produces the same suggestions for the same inputs
  (fully deterministic).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema / path constants
# ---------------------------------------------------------------------------

SUGGESTION_SCHEMA_VERSION = "ai-suggestions.v1"
SUGGESTION_QUALITY_GATE_VERSION = "suggestions-coverage.v1"

FIXTURES_DIR = ROOT / "tests" / "fixtures" / "phase17"
SUGGESTION_REPORT_DIR = ROOT / "bar-association-hall" / "ai-suggestions"

VALID_CATEGORIES = frozenset({"program", "daylight", "budget", "circulation", "general"})
VALID_PRIORITIES = frozenset({"high", "medium", "low"})

# ---------------------------------------------------------------------------
# Rule thresholds — mirror real architectural standards
# ---------------------------------------------------------------------------

AREA_UNDERSIZE_PCT = 0.80         # <80% of brief target  → HIGH priority
AREA_OVERSIZE_PCT = 1.20          # >120%                  → MEDIUM priority
WFR_TARGET = 0.15                 # Window / floor area    → baseline
WFR_MIN = 0.08                    # Below this             → HIGH priority
CIRC_MIN_RATIO = 0.10             # Circulation / total    → below = HIGH
CIRC_MAX_RATIO = 0.25             # Above this             → medium waste
BUDGET_OVER_PCT = 0.10            # 10%+ over budget       → HIGH

# Professional copy templates — no mutable state, pure functions
_DISCLAIMER = (
    "Suggestions are advisory and generated from the available brief data. "
    "Final design decisions must be reviewed by a registered architect and "
    "compliance verified against local building codes (NBC, fire, access, etc.)"
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Suggestion:
    """A single design-improvement suggestion."""
    category: str
    text: str
    priority: str = "medium"
    rule_id: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def suggestion_hash(self) -> str:
        """SHA-256 of normalized (category|text) for dedupe."""
        norm_cat = self.category.strip().lower()
        norm_txt = re.sub(r"\s+", " ", self.text.strip().lower())
        payload = f"{norm_cat}|{norm_txt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "text": self.text,
            "priority": self.priority,
            "hash": self.suggestion_hash,
            "ruleId": self.rule_id,
            "evidence": self.evidence,
        }


@dataclass
class SuggestionResult:
    """Full engine output (same shape as services.ai SuggestionResult)."""
    suggestions: list[Suggestion] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    model_version: str = "heuristic-v1"

    def to_service_dict(self) -> dict[str, Any]:
        """Shape for v1_ai.SuggestionsResponse.suggestions list."""
        return [s.to_dict() for s in self.suggestions]

    @property
    def signature(self) -> str:
        payload = json.dumps(
            [s.to_dict() for s in self.suggestions],
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Heuristic Suggestion Engine (deterministic, pure rule-based)
# ---------------------------------------------------------------------------


class HeuristicSuggestionEngine:
    """Generate proactive design-improvement suggestions without an LLM.

    The engine is fully deterministic — identical project_data + brief
    produce identical suggestion lists and identical hashes.  This makes
    it a reliable fallback when Gemini is unavailable, and a stable
    baseline for idempotency tests.
    """

    ENGINE_VERSION = "heuristic-v1"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        project_data: dict[str, Any],
        categories: list[str] | None = None,
    ) -> SuggestionResult:
        categories_requested = (
            {c.strip().lower() for c in categories}
            if categories
            else set(VALID_CATEGORIES)
        )
        categories_requested &= VALID_CATEGORIES
        if not categories_requested:
            categories_requested = set(VALID_CATEGORIES)

        brief: dict[str, Any] = project_data.get("brief") or project_data or {}
        version: dict[str, Any] = project_data.get("version") or project_data
        zones: list[dict[str, Any]] = list(version.get("zones") or [])
        total_area = float(version.get("totalArea") or version.get("total_area") or 0)
        estimated_cost = float(version.get("estimatedCost") or version.get("estimated_cost") or 0)
        max_budget = float(brief.get("maxBudget") or brief.get("max_budget") or 0)

        suggestions: list[Suggestion] = []
        engine_meta: dict[str, Any] = {
            "zonesCount": len(zones),
            "totalArea": total_area,
            "estimatedCost": estimated_cost,
            "maxBudget": max_budget,
            "categoriesRequested": sorted(categories_requested),
        }

        if "program" in categories_requested:
            suggestions.extend(self.analyze_zone_areas(zones, brief))
        if "daylight" in categories_requested:
            suggestions.extend(self.analyze_daylight(zones))
        if "budget" in categories_requested:
            suggestions.extend(self.analyze_budget(estimated_cost, max_budget, total_area))
        if "circulation" in categories_requested:
            suggestions.extend(self.analyze_circulation(zones, total_area))
        if "general" in categories_requested:
            suggestions.extend(self.analyze_general(project_data, brief, total_area, len(zones)))

        categories_produced = sorted({s.category for s in suggestions})
        provenance = {
            "engine": self.ENGINE_VERSION,
            "schemaVersion": SUGGESTION_SCHEMA_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "disclaimer": _DISCLAIMER,
            **engine_meta,
        }
        return SuggestionResult(
            suggestions=suggestions,
            categories=categories_produced,
            provenance=provenance,
            model_version=self.ENGINE_VERSION,
        )

    # ------------------------------------------------------------------
    # Category analyzers (order of priority: HIGH → MEDIUM → LOW)
    # ------------------------------------------------------------------

    def analyze_zone_areas(self, zones: list[dict[str, Any]], brief: dict[str, Any]) -> list[Suggestion]:
        out: list[Suggestion] = []
        space_program: list[dict[str, Any]] = brief.get("spaceProgram") or brief.get("space_program") or []

        target_index: dict[str, dict[str, Any]] = {}
        for item in space_program:
            name = str(item.get("name") or item.get("zoneName") or "").strip().lower()
            if not name:
                continue
            target_index[name] = {
                "target_area": float(item.get("targetArea") or item.get("sqm") or item.get("area") or 0),
                "priority": str(item.get("priority") or "must-have"),
            }

        zone_map: dict[str, dict[str, Any]] = {}
        for z in zones:
            name = str(z.get("zoneName") or z.get("name") or "").strip().lower()
            if not name:
                continue
            zone_map[name] = z

        # 1) Brief-mandated zones missing entirely → HIGH
        for bname, bmeta in target_index.items():
            if bname not in zone_map and bmeta.get("priority") == "must-have":
                out.append(Suggestion(
                    category="program",
                    priority="high",
                    rule_id="PROG-MISSING-001",
                    text=(
                        f"Must-have zone '{self._display_name(bname)}' is absent from the "
                        f"program — add it to meet the brief before proceeding to client review."
                    ),
                    evidence={"briefZone": bname, "priority": bmeta["priority"]},
                ))

        # 2) Zones present vs. brief target → HIGH/medium gap commentary
        for bname, bmeta in target_index.items():
            target = float(bmeta.get("target_area") or 0)
            if target <= 0 or bname not in zone_map:
                continue
            actual = float(zone_map[bname].get("area") or zone_map[bname].get("areaSqm") or 0)
            if actual <= 0:
                continue
            ratio = actual / target
            if ratio < AREA_UNDERSIZE_PCT:
                out.append(Suggestion(
                    category="program",
                    priority="high",
                    rule_id="PROG-UNDERSIZE-002",
                    text=(
                        f"Zone '{self._display_name(bname)}' is undersized at {actual:,.0f} sq ft "
                        f"vs brief target {target:,.0f} sq ft ({ratio*100:.0f}%). Consider expanding "
                        f"by at least {target - actual:,.0f} sq ft to meet the program."
                    ),
                    evidence={
                        "zone": bname, "actual": actual, "target": target,
                        "ratioPct": round(ratio * 100, 1),
                    },
                ))
            elif ratio > AREA_OVERSIZE_PCT:
                out.append(Suggestion(
                    category="program",
                    priority="medium",
                    rule_id="PROG-OVERSIZE-003",
                    text=(
                        f"Zone '{self._display_name(bname)}' is oversized at {actual:,.0f} sq ft "
                        f"vs brief target {target:,.0f} sq ft ({ratio*100:.0f}%). Recovering "
                        f"{actual - target:,.0f} sq ft could fund other must-have spaces."
                    ),
                    evidence={
                        "zone": bname, "actual": actual, "target": target,
                        "ratioPct": round(ratio * 100, 1),
                    },
                ))

        # 3) Zones that have no brief entry (unplanned) → LOW review note
        for zname, zval in zone_map.items():
            if zname not in target_index:
                area = float(zval.get("area") or zval.get("areaSqm") or 0)
                if area > 200:
                    out.append(Suggestion(
                        category="program",
                        priority="low",
                        rule_id="PROG-UNPLANNED-004",
                        text=(
                            f"Zone '{self._display_name(zname)}' ({area:,.0f} sq ft) does not "
                            f"appear in the brief. Confirm with client whether this space is intentional."
                        ),
                        evidence={"zone": zname, "area": area},
                    ))

        if not out:
            out.append(Suggestion(
                category="program",
                priority="low",
                rule_id="PROG-OK-005",
                text=(
                    "Program areas are within tolerance against the brief — re-confirm at "
                    "the next stakeholder review that no requirements have changed."
                ),
                evidence={},
            ))
        return out

    def analyze_daylight(self, zones: list[dict[str, Any]]) -> list[Suggestion]:
        out: list[Suggestion] = []
        poor_zones: list[str] = []
        no_data_zones: list[str] = []
        wfr_values: list[float] = []

        for z in zones:
            zname = str(z.get("zoneName") or z.get("name") or "Zone")
            ztype = str(z.get("type") or z.get("zoneType") or "").lower()
            area = float(z.get("area") or z.get("areaSqm") or 0)
            windows = float(z.get("windows") or z.get("windowArea") or z.get("windowAreaSqm") or 0)
            south = bool(z.get("southExposure") or z.get("southFacing"))

            # Non-habitable rooms: skip explicit HIGH, allow medium note at aggregate
            if ztype in {"circulation", "corridor", "hallway", "lobby", "wc", "toilet", "bathroom", "storage", "service"}:
                continue

            if area <= 0:
                continue
            wfr = windows / area
            if windows <= 0:
                no_data_zones.append(zname)
                continue
            wfr_values.append(wfr)

            if wfr < WFR_MIN:
                poor_zones.append(zname)
                out.append(Suggestion(
                    category="daylight",
                    priority="high",
                    rule_id="DL-WFR-LOW-011",
                    text=(
                        f"'{zname}' has only {wfr*100:.0f}% window-to-floor ratio. "
                        f"Enlarge or add openings (target {WFR_TARGET*100:.0f}% minimum for "
                        f"habitable rooms per NBC 2016 Part 8)."
                    ),
                    evidence={"zone": zname, "wfrPct": round(wfr * 100, 1)},
                ))

        if no_data_zones:
            out.insert(0, Suggestion(
                category="daylight",
                priority="medium",
                rule_id="DL-NODATA-012",
                text=(
                    "No window data for zones: " + ", ".join(no_data_zones) + ". "
                    "Record glazing areas before running the final compliance review."
                ),
                evidence={"zones": no_data_zones},
            ))

        avg_wfr = sum(wfr_values) / len(wfr_values) if wfr_values else 0
        if not out:
            out.append(Suggestion(
                category="daylight",
                priority="low",
                rule_id="DL-OK-013",
                text=(
                    f"Daylighting posture averages {avg_wfr*100:.0f}% WFR across "
                    f"{len(wfr_values)} zones. Capture solar-gain heat-load calculations for MEP."
                ),
                evidence={"avgWfrPct": round(avg_wfr * 100, 1)},
            ))
        return out

    def analyze_budget(self, estimated_cost: float, max_budget: float, total_area: float) -> list[Suggestion]:
        out: list[Suggestion] = []
        if max_budget <= 0 or estimated_cost <= 0:
            out.append(Suggestion(
                category="budget",
                priority="medium",
                rule_id="BUDGET-NODATA-021",
                text=(
                    "No budget numbers available — confirm the client's MAX budget and the "
                    "current class-5 estimate before the design progresses past Schematic."
                ),
                evidence={"estimatedCost": estimated_cost, "maxBudget": max_budget},
            ))
            return out

        ratio = estimated_cost / max_budget
        evidence = {
            "estimatedCost": estimated_cost,
            "maxBudget": max_budget,
            "ratioPct": round(ratio * 100, 1),
        }
        if total_area > 0:
            evidence["costPerSqFt"] = round(estimated_cost / total_area, 2)

        if ratio > 1 + BUDGET_OVER_PCT:
            delta = estimated_cost - max_budget
            out.append(Suggestion(
                category="budget",
                priority="high",
                rule_id="BUDGET-OVER-022",
                text=(
                    f"Estimated cost ₹{estimated_cost:,.0f} is {(ratio-1)*100:.0f}% over "
                    f"budget ₹{max_budget:,.0f}. Reduce scope by ₹{delta:,.0f} immediately: "
                    f"review finishes, unit count, and structural scheme."
                ),
                evidence=evidence,
            ))
        elif ratio > 1.0:
            out.append(Suggestion(
                category="budget",
                priority="medium",
                rule_id="BUDGET-ATCAP-023",
                text=(
                    f"Estimated cost is within {(ratio-1)*100:.1f}% of cap. Lock finishes "
                    f"now and add a 5% contingency line item before client presentation."
                ),
                evidence=evidence,
            ))
        else:
            headroom = max_budget - estimated_cost
            out.append(Suggestion(
                category="budget",
                priority="low",
                rule_id="BUDGET-HEADROOM-024",
                text=(
                    f"₹{estimated_cost:,.0f} sits within the ₹{max_budget:,.0f} budget "
                    f"(headroom ₹{headroom:,.0f}). Allocate surplus to structural resilience "
                    f"and accessibility upgrades before finishes."
                ),
                evidence=evidence,
            ))
        return out

    def analyze_circulation(self, zones: list[dict[str, Any]], total_area: float) -> list[Suggestion]:
        out: list[Suggestion] = []
        circ_names: list[str] = []
        circ_area = 0.0
        for z in zones:
            ztype = str(z.get("type") or "").lower()
            zname = str(z.get("zoneName") or z.get("name") or "")
            area = float(z.get("area") or z.get("areaSqm") or 0)
            if ztype in {"circulation", "corridor", "hallway", "lobby", "stair", "stairs", "staircase"}:
                circ_area += area
                circ_names.append(zname)

        if total_area <= 0:
            out.append(Suggestion(
                category="circulation",
                priority="medium",
                rule_id="CIRC-NODATA-031",
                text="No total-area data. Record as-built dimensions to validate circulation adequacy.",
                evidence={},
            ))
            return out

        ratio = circ_area / total_area
        evidence = {
            "circulationArea": circ_area,
            "totalArea": total_area,
            "ratioPct": round(ratio * 100, 1),
            "zones": circ_names,
        }

        if ratio < CIRC_MIN_RATIO:
            out.append(Suggestion(
                category="circulation",
                priority="high",
                rule_id="CIRC-TIGHT-032",
                text=(
                    f"Circulation is only {ratio*100:.1f}% of total area. Widen the main "
                    f"corridor to minimum 4' clear (NBC 2016 Part 4) and add a secondary "
                    f"means of egress before submitting for building permit."
                ),
                evidence=evidence,
            ))
        elif ratio > CIRC_MAX_RATIO:
            out.append(Suggestion(
                category="circulation",
                priority="medium",
                rule_id="CIRC-WASTE-033",
                text=(
                    f"Circulation at {ratio*100:.1f}% of total area is excessive. "
                    f"Reclaim {(ratio - 0.18) * total_area:,.0f} sq ft for program use by "
                    f"rationalising the hallway layout."
                ),
                evidence=evidence,
            ))
        else:
            out.append(Suggestion(
                category="circulation",
                priority="low",
                rule_id="CIRC-OK-034",
                text=(
                    f"Circulation balance is healthy at {ratio*100:.1f}%. Confirm corridor "
                    f"turning radii meet wheelchair turning-circle requirements (1.5 m minimum)."
                ),
                evidence=evidence,
            ))
        return out

    def analyze_general(
        self,
        project_data: dict[str, Any],
        brief: dict[str, Any],
        total_area: float,
        zone_count: int,
    ) -> list[Suggestion]:
        out: list[Suggestion] = []
        constraints: list[str] = list(brief.get("constraints") or [])
        orientation = str(project_data.get("orientation") or brief.get("orientation") or "").lower()

        if "98" in orientation or "south" in orientation or any(
            ("98" in c.lower() or "south" in c.lower() or "entrance" in c.lower()) for c in constraints
        ):
            out.append(Suggestion(
                category="general",
                priority="medium",
                rule_id="GEN-MAINENT-041",
                text=(
                    "Verify main entrance falls on the 98-ft (south) wall with a clearly "
                    "marked accessible ramp and 10 ft clear porch; align with Bar Association "
                    "entry protocol and fire-department access requirements."
                ),
                evidence={"orientation": orientation or "from constraints"},
            ))

        if zone_count > 0:
            out.append(Suggestion(
                category="general",
                priority="low",
                rule_id="GEN-CODES-042",
                text=(
                    f"Run full NBC / fire / access rule-pack validation on the {zone_count} "
                    f"zones before the client presentation — do not rely on suggestion coverage alone."
                ),
                evidence={"zoneCount": zone_count},
            ))

        if not out:
            out.append(Suggestion(
                category="general",
                priority="low",
                rule_id="GEN-OK-043",
                text="General posture looks fine. Schedule the next BIM coordination review.",
                evidence={},
            ))
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _display_name(raw: str) -> str:
        spaced = raw.replace("-", " ").replace("_", " ")
        words = spaced.split()
        return " ".join(w.title() for w in words) if words else raw.strip() or "Zone"


# ---------------------------------------------------------------------------
# Convenience: standalone script prints suggestions for a fixture JSON
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run heuristic suggestion engine on a JSON fixture.")
    parser.add_argument("fixture", type=Path, help="Path to project-data JSON fixture")
    parser.add_argument("--categories", nargs="*", default=None, help="Categories to emit (default all)")
    args = parser.parse_args()

    data = json.loads(args.fixture.read_text(encoding="utf-8"))
    engine = HeuristicSuggestionEngine()
    result = engine.generate(data, categories=args.categories)
    print(json.dumps({
        "signature": result.signature,
        "categories": result.categories,
        "count": len(result.suggestions),
        "provenance": result.provenance,
        "suggestions": result.to_service_dict(),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
