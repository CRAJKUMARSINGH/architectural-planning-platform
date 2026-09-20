#!/usr/bin/env python3
"""Common Week 1–5 drafting kernel with small project recipes.

The kernel is deliberately an orchestrator, not a second geometry engine.  The
canonical Week 2 model remains authoritative; the existing Week 1, Week 3–4,
and Week 5 validators remain the source of findings.  Recipes configure brief
intent and optimization checks without inventing missing geometry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "bar-association-hall"
CANONICAL_PATH = MODEL_ROOT / "standard" / "model" / "project.json"
RECIPE_PATH = ROOT / "packages" / "recipes" / "index.json"
VISUAL_PATTERN_PATH = ROOT / "packages" / "recipes" / "visual-tool-patterns.json"
REPORT_PATH = MODEL_ROOT / "standard" / "fresh-week01-05-kernel-report.json"

sys.path.insert(0, str(ROOT / "bar-association-hall"))
sys.path.insert(0, str(ROOT / "scripts"))

from drawing_model import validate_model_findings  # noqa: E402
from week1 import validation_report  # noqa: E402
from week2 import canonical_to_legacy, load_canonical_model, validate_canonical  # noqa: E402
from week34 import enrichment_report as week34_report  # noqa: E402
from week56 import validate_stairs  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_recipe_index() -> dict[str, Any]:
    value = read_json(RECIPE_PATH)
    recipes = value.get("recipes")
    if not isinstance(recipes, dict) or not recipes:
        raise ValueError("recipe index must contain at least one recipe")
    for recipe_id, recipe in recipes.items():
        if not isinstance(recipe, dict):
            raise ValueError(f"recipe {recipe_id!r} must be an object")
        for key in ("label", "requiredFacts", "optimizationChecks"):
            if not recipe.get(key):
                raise ValueError(f"recipe {recipe_id!r} is missing {key}")
    return value


def load_visual_patterns() -> list[dict[str, Any]]:
    value = read_json(VISUAL_PATTERN_PATH)
    patterns = value.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("visual pattern catalog must contain at least one pattern")
    required = ("id", "references", "bestFor", "safeAction", "mustNotDo", "programWeeks")
    for pattern in patterns:
        if not isinstance(pattern, dict) or any(not pattern.get(key) for key in required):
            raise ValueError("every visual pattern needs id, references, purpose, safety, and weeks")
    return patterns


def selected_recipe(model: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    program = model.get("program")
    building_type = program.get("buildingType") if isinstance(program, dict) else None
    building_type = str(building_type or "institutional").lower()
    recipes = index["recipes"]
    recipe = recipes.get(building_type)
    if recipe is None:
        raise ValueError(
            f"no recipe for building type {building_type!r}; "
            f"available: {', '.join(sorted(recipes))}"
        )
    return {
        "id": building_type,
        "label": recipe["label"],
        "requiredFacts": list(recipe["requiredFacts"]),
        "preferredAdjacencies": list(recipe.get("preferredAdjacencies", [])),
        "forbiddenAdjacencies": list(recipe.get("forbiddenAdjacencies", [])),
        "optimizationChecks": list(recipe["optimizationChecks"]),
    }


def _status(findings: Iterable[dict[str, Any]], *, schema_errors: list[str] | None = None) -> str:
    if schema_errors or any(
        item.get("severity") in {"BLOCKER", "ERROR"} for item in findings
    ):
        return "BLOCKED"
    if any(item.get("severity") == "WARNING" for item in findings):
        return "REVIEW_REQUIRED"
    return "PASS"


def _counts(findings: Iterable[dict[str, Any]]) -> dict[str, int]:
    values = list(findings)
    return {
        severity: sum(1 for item in values if item.get("severity") == severity)
        for severity in ("BLOCKER", "ERROR", "WARNING", "INFO")
        if any(item.get("severity") == severity for item in values)
    }


def _tagged(findings: Iterable[dict[str, Any]], week: str) -> list[dict[str, Any]]:
    return [{**finding, "week": week} for finding in findings]


def build_report() -> dict[str, Any]:
    model = load_canonical_model(CANONICAL_PATH)
    recipe_index = load_recipe_index()
    visual_patterns = load_visual_patterns()
    recipe = selected_recipe(model, recipe_index)
    site, plans = canonical_to_legacy(model)

    week1 = validation_report()
    week2_errors = validate_canonical(model)
    week34 = week34_report(site, plans)
    week5_findings, stair_schedule = validate_stairs(model, week34["week3"]["graph"])

    findings = _tagged(week1["findings"], "01")
    findings += _tagged(week34["findings"], "03-04")
    findings += _tagged(week5_findings, "05")
    # A single finding can be surfaced by the compatibility validator and the
    # focused report.  Keep the aggregate deterministic and non-redundant.
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding.get("id")),
            str(finding.get("rule")),
            str(finding.get("message")),
        )
        unique.setdefault(key, finding)
    findings = sorted(unique.values(), key=lambda item: (item.get("severity", ""), item.get("id", "")))
    status = _status(findings, schema_errors=week2_errors)

    return {
        "reportVersion": "fresh.week01-05.drafting-kernel.v1",
        "status": status,
        "kernel": {
            "authoritativeModel": "bar-association-hall/standard/model/project.json",
            "recipeIndex": str(RECIPE_PATH.relative_to(ROOT)),
            "visualPatternCatalog": str(VISUAL_PATTERN_PATH.relative_to(ROOT)),
            "principle": "brief -> canonical model -> validate -> explain -> render",
            "presentationCannotOverrideFindings": True,
        },
        "recipe": recipe,
        "visualOptimization": {
            "catalogVersion": read_json(VISUAL_PATTERN_PATH)["catalogVersion"],
            "patterns": visual_patterns,
        },
        "weeks": {
            "01": {
                "status": _status(week1["findings"]),
                "report": "bar-association-hall/standard/week1-validation-report.json",
                "findingCounts": _counts(week1["findings"]),
            },
            "02": {
                "status": "PASS" if not week2_errors else "BLOCKED",
                "schema": "advocate-chambers.project.v2",
                "errors": week2_errors,
            },
            "03-04": {
                "status": _status(week34["findings"]),
                "findingCounts": _counts(week34["findings"]),
                "graph": week34["week3"]["graph"],
                "openingSchedule": week34["week4"]["schedule"],
            },
            "05": {
                "status": _status(week5_findings),
                "findingCounts": _counts(week5_findings),
                "connectors": stair_schedule,
            },
        },
        "findingCounts": _counts(findings),
        "findings": findings,
        "policy": {
            "issueReadyOutputAllowed": status == "PASS",
            "professionalStatus": "PRELIMINARY / NOT FOR CONSTRUCTION",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args()
    report = build_report()
    write_json(REPORT_PATH, report)
    print(json.dumps(report, indent=2))
    if args.command == "validate":
        return 0 if report["status"] == "PASS" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())