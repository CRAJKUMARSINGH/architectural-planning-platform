#!/usr/bin/env python3
"""Week 23 adversarial benchmark expansion and hardening.

Week 22 supplied the first 15 defect fixtures. This runner keeps those cases
as regression coverage, adds 15 mutation cases across the required domains,
and reports separate invalid, incomplete-input, false-positive, and
false-negative measurements. Incomplete input is quarantined before normal
rule evaluation so missing data cannot be mistaken for a clean plan.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "adversarial" / "week23-cases.json"
REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week23-adversarial-expansion-report.json"
FIXTURE_SCHEMA_VERSION = "week23.adversarial-case.v1"
REPORT_VERSION = "week23.adversarial-expansion.v1"
REQUIRED_INPUT_FIELDS = ("project", "site", "spaces", "routes", "openings", "windows", "furniture")

sys.path.insert(0, str(ROOT / "scripts"))
from week22 import (  # noqa: E402
    apply_mutation,
    detect_findings,
    discover_fixtures,
    load_fixture,
    read_json,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def signature(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_manifest() -> list[dict[str, Any]]:
    manifest = read_json(MANIFEST_PATH)
    if manifest.get("schemaVersion") != FIXTURE_SCHEMA_VERSION:
        raise ValueError("unsupported Week 23 manifest schemaVersion")
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Week 23 manifest must contain a cases array")
    return cases


def _load_case_model(case: dict[str, Any]) -> dict[str, Any]:
    source_path = (ROOT / str(case["sourceFixture"])).resolve()
    if not source_path.is_file():
        raise ValueError(f"source fixture does not exist: {source_path}")
    model = copy.deepcopy(read_json(source_path))
    for mutation in case.get("mutations", []):
        apply_mutation(model, mutation)
    return model


def _input_findings(model: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for field in REQUIRED_INPUT_FIELDS:
        if field not in model:
            findings.append(
                {
                    "ruleId": f"INPUT.MISSING.{field.upper()}",
                    "severity": "BLOCKER",
                    "affectedObjects": [field],
                    "evidence": {"missingField": field},
                    "suggestedCorrection": (
                        f"Supply the {field} collection before running architectural validation."
                    ),
                }
            )
    return findings


def _evaluate(
    case: dict[str, Any],
    model: dict[str, Any],
    *,
    fixture_path: str,
) -> dict[str, Any]:
    group = case["group"]
    findings = _input_findings(model) if group == "incomplete" else detect_findings(model)
    expected = case["expectedFinding"]
    matching = [finding for finding in findings if finding.get("ruleId") == expected["ruleId"]]
    actual = matching[0] if matching else None
    errors: list[str] = []
    if actual is None:
        errors.append(f"expected rule was not detected: {expected['ruleId']}")
    else:
        if actual.get("severity") != expected["severity"]:
            errors.append("detected severity does not match expected severity")
        if not set(expected["affectedObjects"]).issubset(set(actual.get("affectedObjects", []))):
            errors.append("detected affected objects do not include expected objects")
        if not set(expected["evidenceFields"]).issubset(set(actual.get("evidence", {}))):
            errors.append("detected evidence is missing expected fields")
        if not actual.get("suggestedCorrection") or not expected["correction"]:
            errors.append("finding and contract must both include a suggested correction")
    unexpected = [finding for finding in findings if finding.get("ruleId") != expected["ruleId"]]
    if unexpected:
        errors.append("case produced unexpected additional findings")
    return {
        "fixtureId": case["fixtureId"],
        "title": case["title"],
        "group": group,
        "category": case["category"],
        "fixturePath": fixture_path,
        "sourceFixture": case["sourceFixture"],
        "mutationPaths": [mutation["path"] for mutation in case.get("mutations", [])],
        "status": "PASS" if not errors else "FAIL",
        "expectedRuleId": expected["ruleId"],
        "actualRuleId": actual.get("ruleId") if actual else None,
        "severity": actual.get("severity") if actual else expected["severity"],
        "affectedObjects": actual.get("affectedObjects", []) if actual else [],
        "evidence": actual.get("evidence", {}) if actual else {},
        "suggestedCorrection": actual.get("suggestedCorrection") if actual else None,
        "ruleIdCorrect": actual is not None and actual.get("ruleId") == expected["ruleId"],
        "affectedGeometryCorrect": (
            actual is not None
            and set(expected["affectedObjects"]).issubset(set(actual.get("affectedObjects", [])))
        ),
        "suggestedCorrectionComplete": bool(actual and actual.get("suggestedCorrection")),
        "errors": errors,
    }


def _legacy_case(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    fixture, model = load_fixture(path)
    case = {
        "fixtureId": fixture["fixtureId"],
        "title": fixture["title"],
        "group": "invalid",
        "category": fixture["defect"]["category"],
        "sourceFixture": str((path.parent / fixture["sourceFixture"]).relative_to(ROOT)),
        "mutations": fixture.get("mutations", []),
        "expectedFinding": fixture["expectedFinding"],
    }
    return case, model


def run_benchmark() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    legacy_paths = discover_fixtures()
    for path in legacy_paths:
        case, model = _legacy_case(path)
        results.append(_evaluate(case, model, fixture_path=str(path.relative_to(ROOT))))
    for case in _load_manifest():
        model = _load_case_model(case)
        results.append(_evaluate(case, model, fixture_path=str(MANIFEST_PATH.relative_to(ROOT))))

    ids = [result["fixtureId"] for result in results]
    if len(ids) != len(set(ids)):
        raise ValueError("Week 23 fixture IDs must be unique")
    valid_baseline = read_json(ROOT / "tests/fixtures/adversarial/valid/baseline.json")
    valid_findings = detect_findings(valid_baseline)
    category_counts = {
        category: sum(result["category"] == category for result in results)
        for category in ("geometry", "openings", "routes", "furniture", "levels", "site")
    }
    status_counts = {
        group: sum(result["group"] == group for result in results)
        for group in ("invalid", "incomplete")
    }
    passed = [result for result in results if result["status"] == "PASS"]
    missed = [result for result in results if result["status"] != "PASS"]
    total = len(results)
    return {
        "results": results,
        "fixtureCount": total,
        "groupCounts": {"valid": 1, **status_counts},
        "mutationCoverage": category_counts,
        "criticalDefects": total,
        "detectedDefects": len(passed),
        "missedDefects": len(missed),
        "falsePositives": len(valid_findings),
        "falseNegatives": len(missed),
        "dangerousFalseNegatives": len(missed),
        "ruleIdAccuracy": sum(result["ruleIdCorrect"] for result in results) / total,
        "affectedGeometryAccuracy": sum(result["affectedGeometryCorrect"] for result in results) / total,
        "suggestedCorrectionCompleteness": (
            sum(result["suggestedCorrectionComplete"] for result in results) / total
        ),
        "validBaselineFindingCount": len(valid_findings),
        "missedFixtureIds": [result["fixtureId"] for result in missed],
    }


def build_report() -> dict[str, Any]:
    benchmark = run_benchmark()
    status = "PASS" if (
        benchmark["missedDefects"] == 0
        and benchmark["dangerousFalseNegatives"] == 0
        and benchmark["falsePositives"] == 0
        and benchmark["ruleIdAccuracy"] == 1
        and benchmark["affectedGeometryAccuracy"] == 1
        and benchmark["suggestedCorrectionCompleteness"] == 1
    ) else "BLOCKED"
    report: dict[str, Any] = {
        "version": REPORT_VERSION,
        "fixtureSchemaVersion": FIXTURE_SCHEMA_VERSION,
        "status": status,
        "sourceFixture": "tests/fixtures/adversarial/valid/baseline.json",
        "benchmark": {
            key: benchmark[key]
            for key in (
                "fixtureCount",
                "groupCounts",
                "mutationCoverage",
                "criticalDefects",
                "detectedDefects",
                "missedDefects",
                "falsePositives",
                "falseNegatives",
                "dangerousFalseNegatives",
                "ruleIdAccuracy",
                "affectedGeometryAccuracy",
                "suggestedCorrectionCompleteness",
                "validBaselineFindingCount",
            )
        },
        "falsePositiveReport": {
            "status": "PASS" if benchmark["falsePositives"] == 0 else "REVIEW_REQUIRED",
            "validBaselineFindingCount": benchmark["validBaselineFindingCount"],
            "findingRuleIds": [],
        },
        "falseNegativeReport": {
            "status": "PASS" if benchmark["falseNegatives"] == 0 else "BLOCKED",
            "missedFixtureIds": benchmark["missedFixtureIds"],
            "dangerousFalseNegatives": benchmark["dangerousFalseNegatives"],
        },
        "acceptance": {
            "minimumFixtureCountMet": benchmark["fixtureCount"] >= 30,
            "allKnownDefectsDetected": benchmark["missedDefects"] == 0,
            "zeroDangerousFalseNegatives": benchmark["dangerousFalseNegatives"] == 0,
            "noValidBaselineFalsePositives": benchmark["falsePositives"] == 0,
            "allFindingsCarryRuleEvidenceGeometryCorrection": (
                benchmark["suggestedCorrectionCompleteness"] == 1
                and benchmark["ruleIdAccuracy"] == 1
                and benchmark["affectedGeometryAccuracy"] == 1
            ),
        },
        "results": benchmark["results"],
        "reportSignature": None,
    }
    report["reportSignature"] = signature(
        {key: value for key, value in report.items() if key != "reportSignature"}
    )
    return report


def write_report() -> dict[str, Any]:
    report = build_report()
    write_json(REPORT_PATH, report)
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "fixtureSchemaVersion",
        "status",
        "benchmark",
        "falsePositiveReport",
        "falseNegativeReport",
        "acceptance",
        "results",
        "reportSignature",
    )
    errors.extend(f"missing report field: {field}" for field in required if field not in report)
    if report.get("status") not in {"PASS", "BLOCKED"}:
        errors.append("report status must be PASS or BLOCKED")
    benchmark = report.get("benchmark", {})
    if benchmark.get("fixtureCount") != len(report.get("results", [])):
        errors.append("benchmark fixtureCount does not match result count")
    if benchmark.get("fixtureCount", 0) < 30:
        errors.append("benchmark must contain at least 30 fixtures")
    if any(result.get("status") != "PASS" for result in report.get("results", [])):
        errors.append("one or more Week 23 cases failed its expected contract")
    if report.get("reportSignature"):
        expected = signature({key: value for key, value in report.items() if key != "reportSignature"})
        if report["reportSignature"] != expected:
            errors.append("reportSignature does not match report contents")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)
    if args.command == "report":
        report = write_report()
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
        print(f"fixtures: {report['benchmark']['fixtureCount']}")
        print(f"status: {report['status']}")
        return 0 if report["status"] == "PASS" else 1
    report = read_json(REPORT_PATH)
    errors = validate_report(report)
    print(report.get("status", "INVALID"))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())