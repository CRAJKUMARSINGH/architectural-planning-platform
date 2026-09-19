#!/usr/bin/env python3
"""Build and validate the Week 24 blinded professional-review package.

The package is ready for independent review but does not invent professional
participation. It contains 10 valid, 10 defective, and 5 borderline models
without classification labels in the reviewer-facing pack. The anonymized
results artifact stays REVIEW_REQUIRED until two real independent reviewers
submit signed scorecards.
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
PACK_PATH = ROOT / "tests" / "fixtures" / "professional-review" / "week24-review-pack.json"
ANSWER_KEY_PATH = ROOT / "bar-association-hall" / "standard" / "week24-software-answer-key.json"
RESULT_PATH = ROOT / "bar-association-hall" / "standard" / "week24-anonymized-review-results.json"
REPORT_VERSION = "week24.professional-review.v1"

sys.path.insert(0, str(ROOT / "scripts"))
from week22 import detect_findings, discover_fixtures, load_fixture, read_json  # noqa: E402
from week23 import _input_findings, _load_case_model, _load_manifest, signature  # noqa: E402


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _valid_models() -> list[dict[str, Any]]:
    baseline = read_json(ROOT / "tests/fixtures/adversarial/valid/baseline.json")
    models = []
    for index in range(1, 11):
        model = copy.deepcopy(baseline)
        model["project"]["reviewPlanId"] = f"VALID-{index:02d}"
        models.append(model)
    return models


def _defective_models() -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
    output = []
    for path in discover_fixtures()[:10]:
        fixture, model = load_fixture(path)
        output.append((fixture["fixtureId"], model, detect_findings(model)))
    return output


def _borderline_models() -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
    output = []
    for case in _load_manifest():
        if case["group"] != "incomplete":
            continue
        model = _load_case_model(case)
        output.append((case["fixtureId"], model, _input_findings(model)))
    return output


def build_pack() -> tuple[dict[str, Any], dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    answer_key: list[dict[str, Any]] = []
    index = 1

    for model in _valid_models():
        blinded_id = f"BLIND-{index:03d}"
        cases.append({
            "blindedCaseId": blinded_id,
            "modelSignature": signature(model),
            "model": model,
        })
        answer_key.append({"blindedCaseId": blinded_id, "expectedClass": "valid", "findings": []})
        index += 1

    for fixture_id, model, findings in _defective_models():
        blinded_id = f"BLIND-{index:03d}"
        cases.append({
            "blindedCaseId": blinded_id,
            "modelSignature": signature(model),
            "model": model,
        })
        answer_key.append({
            "blindedCaseId": blinded_id,
            "sourceFixtureId": fixture_id,
            "expectedClass": "defective",
            "findings": findings,
        })
        index += 1

    for fixture_id, model, findings in _borderline_models():
        blinded_id = f"BLIND-{index:03d}"
        cases.append({
            "blindedCaseId": blinded_id,
            "modelSignature": signature(model),
            "model": model,
        })
        answer_key.append({
            "blindedCaseId": blinded_id,
            "sourceFixtureId": fixture_id,
            "expectedClass": "borderline_or_incomplete",
            "findings": findings,
        })
        index += 1

    pack = {
        "version": "week24.blinded-review-pack.v1",
        "instructions": "docs/WEEK24_PROFESSIONAL_REVIEW_INSTRUCTIONS.md",
        "reviewForm": "docs/WEEK24_REVIEW_FORM.md",
        "blinded": True,
        "cases": cases,
        "packSignature": None,
    }
    pack["packSignature"] = signature({key: value for key, value in pack.items() if key != "packSignature"})
    key = {
        "version": "week24.software-answer-key.v1",
        "packSignature": pack["packSignature"],
        "cases": answer_key,
        "answerKeyNotForReviewerDistribution": True,
    }
    return pack, key


def build_results(pack: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {
        "version": REPORT_VERSION,
        "status": "REVIEW_REQUIRED",
        "reviewStatus": "PENDING_EXTERNAL_REVIEW",
        "packSignature": pack["packSignature"],
        "plansInPack": len(pack["cases"]),
        "requiredPlanMix": {"valid": 10, "defective": 10, "borderlineOrIncomplete": 5},
        "requiredIndependentReviewers": 2,
        "reviewerSlots": [
            {"reviewerId": "REVIEWER-A", "status": "PENDING"},
            {"reviewerId": "REVIEWER-B", "status": "PENDING"},
        ],
        "completedReviewers": 0,
        "plansReviewed": 0,
        "usableAgreement": None,
        "criticalDefectsAcceptedAsUsable": None,
        "criticalFindingsReproducible": None,
        "findings": [],
        "disagreements": [],
        "acceptance": {
            "atLeastTwoIndependentReviewers": False,
            "usableAgreementTargetMet": False,
            "noCriticalDefectAcceptedAsUsable": False,
            "criticalFindingsReproducible": False,
            "allCriticalDisagreementsDocumented": True,
        },
        "notes": [
            "No professional participation is fabricated by this artifact.",
            "Populate anonymized scorecards only after independent review is completed.",
            "This package is not a permit, approval, or construction certification.",
        ],
        "reportSignature": None,
    }
    results["reportSignature"] = signature({
        key: value for key, value in results.items() if key != "reportSignature"
    })
    return results


def write_report() -> dict[str, Any]:
    pack, answer_key = build_pack()
    results = build_results(pack)
    write_json(PACK_PATH, pack)
    write_json(ANSWER_KEY_PATH, answer_key)
    write_json(RESULT_PATH, results)
    return results


def validate_pack(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = pack.get("cases", [])
    if len(cases) != 25:
        errors.append("review pack must contain exactly 25 blinded cases")
    ids = [case.get("blindedCaseId") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("blinded case IDs must be unique")
    if not pack.get("blinded"):
        errors.append("review pack must be marked blinded")
    if any("expectedClass" in case or "findings" in case for case in cases):
        errors.append("review pack must not expose the answer key")
    if pack.get("packSignature"):
        expected = signature({key: value for key, value in pack.items() if key != "packSignature"})
        if pack["packSignature"] != expected:
            errors.append("packSignature does not match pack contents")
    return errors


def validate_results(results: dict[str, Any], pack: dict[str, Any]) -> list[str]:
    errors = validate_pack(pack)
    required = ("version", "status", "reviewStatus", "packSignature", "reviewerSlots", "acceptance")
    errors.extend(f"missing result field: {field}" for field in required if field not in results)
    if results.get("status") not in {"REVIEW_REQUIRED", "PASS", "BLOCKED"}:
        errors.append("invalid professional review status")
    if results.get("status") == "PASS":
        errors.append("pending external review cannot be marked PASS")
    if results.get("packSignature") != pack.get("packSignature"):
        errors.append("result packSignature does not match review pack")
    if results.get("reportSignature"):
        expected = signature({key: value for key, value in results.items() if key != "reportSignature"})
        if results["reportSignature"] != expected:
            errors.append("reportSignature does not match result contents")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)
    if args.command == "report":
        results = write_report()
        print(f"wrote {RESULT_PATH.relative_to(ROOT)}")
        print(f"review status: {results['status']}")
        return 0
    pack = read_json(PACK_PATH)
    results = read_json(RESULT_PATH)
    errors = validate_results(results, pack)
    print(results.get("status", "INVALID"))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())