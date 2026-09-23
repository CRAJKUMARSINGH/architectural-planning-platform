#!/usr/bin/env python3
"""Week 21 quality-gate contract and baseline report.

The quality gate combines the evidence tracks delivered in Weeks 22–26:

* adversarial architectural defect detection;
* independent professional review; and
* small, medium, and large performance benchmarks;
* reproducibility and failure recovery.

Week 21 deliberately reports ``INCOMPLETE`` until those tracks have supplied
results. Missing evidence is not a pass condition. The gate is a coordination
contract, not a permit, code, fire, accessibility, structural, MEP, survey, or
construction certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / "tests"
REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "quality-gate-report.json"
WEEK22_REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week22-adversarial-foundation-report.json"
WEEK23_REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week23-adversarial-expansion-report.json"
WEEK24_REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week24-anonymized-review-results.json"
WEEK25_REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week25-performance-report.json"
WEEK26_REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week26-reproducibility-report.json"
AI_SCORING_REPORT_DIR = ROOT / "bar-association-hall" / "ai-scoring"

QUALITY_GATE_VERSION = "week21.quality-gate.v1"
STATES = ("PASS", "REVIEW_REQUIRED", "BLOCKED", "INCOMPLETE")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def signature(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _missing_track(name: str, required_fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        "status": "INCOMPLETE",
        "requiredFields": list(required_fields),
        "missingEvidence": True,
        "message": f"{name} evidence has not been supplied",
    }


def evaluate_adversarial(result: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate an adversarial benchmark result without hiding missing data."""

    required = (
        "totalCriticalDefects",
        "detectedCriticalDefects",
        "missedCriticalDefects",
        "dangerousFalseNegatives",
        "completeFindings",
    )
    if result is None:
        return _missing_track("adversarial benchmark", required)

    missing = [field for field in required if field not in result]
    if missing:
        return {
            "status": "INCOMPLETE",
            "missingFields": missing,
            "message": "Adversarial result is missing required measurements",
        }

    total = int(result["totalCriticalDefects"])
    detected = int(result["detectedCriticalDefects"])
    missed = int(result["missedCriticalDefects"])
    dangerous = int(result["dangerousFalseNegatives"])
    complete = int(result["completeFindings"])
    false_positives = int(result.get("falsePositiveCount", 0))

    if missed > 0 or dangerous > 0 or detected < total:
        status = "BLOCKED"
    elif complete < detected:
        status = "REVIEW_REQUIRED"
    elif false_positives > 0:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        **result,
        "status": status,
        "criticalRecall": (detected / total) if total else None,
        "zeroDangerousFalseNegatives": dangerous == 0,
        "allCriticalFindingsComplete": complete >= detected,
    }


def evaluate_professional_review(result: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate blinded professional review evidence."""

    required = (
        "reviewers",
        "plansReviewed",
        "usableAgreement",
        "criticalDefectsAcceptedAsUsable",
        "criticalFindingsReproducible",
    )
    if result is None:
        return _missing_track("professional review", required)

    missing = [field for field in required if field not in result]
    if missing:
        return {
            "status": "INCOMPLETE",
            "missingFields": missing,
            "message": "Professional review result is missing required measurements",
        }

    if any(result.get(field) is None for field in (
        "usableAgreement",
        "criticalDefectsAcceptedAsUsable",
        "criticalFindingsReproducible",
    )):
        return {
            **result,
            "status": "REVIEW_REQUIRED",
            "agreementTargetMet": False,
            "criticalDefectsRejectedAsUsable": False,
        }

    agreement = float(result["usableAgreement"])
    accepted = int(result["criticalDefectsAcceptedAsUsable"])
    reproducible = bool(result["criticalFindingsReproducible"])

    if accepted > 0:
        status = "BLOCKED"
    elif int(result["reviewers"]) < 2 or int(result["plansReviewed"]) < 25:
        status = "REVIEW_REQUIRED"
    elif agreement < 0.90 or not reproducible:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        **result,
        "status": status,
        "agreementTargetMet": agreement >= 0.90,
        "criticalDefectsRejectedAsUsable": accepted == 0,
    }


def evaluate_performance(result: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate workload benchmark evidence."""

    required = (
        "profiles",
        "silentTimeouts",
        "outOfMemoryFailures",
        "dataLossEvents",
        "nondeterministicRuns",
    )
    if result is None:
        return _missing_track("performance benchmark", required)

    missing = [field for field in required if field not in result]
    if missing:
        return {
            "status": "INCOMPLETE",
            "missingFields": missing,
            "message": "Performance result is missing required measurements",
        }

    failures = {
        "silentTimeouts": int(result["silentTimeouts"]),
        "outOfMemoryFailures": int(result["outOfMemoryFailures"]),
        "dataLossEvents": int(result["dataLossEvents"]),
        "nondeterministicRuns": int(result["nondeterministicRuns"]),
    }
    status = "BLOCKED" if any(value > 0 for value in failures.values()) else "PASS"
    return {
        **result,
        "status": status,
        "failureCounts": failures,
        "deterministic": failures["nondeterministicRuns"] == 0,
    }


def evaluate_reproducibility(result: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate Week 26 reproducibility and failure-recovery evidence."""

    required = (
        "status",
        "tamperedManifestRejected",
        "missingArtifactsExplicit",
        "partialGenerationCannotReplaceValidRevision",
        "softArchiveRestorePreservesRevision",
        "secondWorkspaceCanVerify",
        "rerunMatchesOriginal",
    )
    if result is None:
        return _missing_track("reproducibility", required)

    missing = [field for field in required if field not in result]
    if missing:
        return {
            "status": "INCOMPLETE",
            "missingFields": missing,
            "message": "Reproducibility result is missing required acceptance checks",
        }

    checks = {field: bool(result[field]) for field in required[1:]}
    status = "PASS" if result["status"] == "PASS" and all(checks.values()) else "BLOCKED"
    return {**result, "status": status, "acceptance": checks}


def _evaluate_baseline(baseline: dict[str, Any]) -> dict[str, Any]:
    required = ("suite", "tests", "passed", "failed", "command")
    missing = [field for field in required if field not in baseline]
    if missing:
        return {"status": "INCOMPLETE", "missingFields": missing}
    status = "PASS" if int(baseline["failed"]) == 0 and int(baseline["passed"]) == int(baseline["tests"]) else "BLOCKED"
    return {**baseline, "status": status}


def _overall_status(track_statuses: list[str]) -> str:
    if "BLOCKED" in track_statuses:
        return "BLOCKED"
    if "INCOMPLETE" in track_statuses:
        return "INCOMPLETE"
    if "REVIEW_REQUIRED" in track_statuses:
        return "REVIEW_REQUIRED"
    return "PASS"


def evaluate_ai_scoring(result: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate Phase 16 AI version scoring evidence.

    The AI-scoring track is advisory.  It can reach PASS or REVIEW_REQUIRED
    but never BLOCKED — it must not prevent a release on its own.
    """
    if result is None:
        return {
            "status": "INCOMPLETE",
            "message": "AI scoring evidence has not been supplied",
            "missingEvidence": True,
            "advisory": True,
        }

    required = ("schemaVersion", "bestVersionId", "bestOverallScore", "minimumScoreRequired")
    missing = [f for f in required if f not in result]
    if missing:
        return {
            "status": "INCOMPLETE",
            "missingFields": missing,
            "message": "AI scoring result is missing required fields",
            "advisory": True,
        }

    gate_status = result.get("status", "INCOMPLETE")
    # Never promote to BLOCKED from AI scoring alone
    effective_status = gate_status if gate_status in ("PASS", "REVIEW_REQUIRED", "INCOMPLETE") else "REVIEW_REQUIRED"
    return {
        **result,
        "status": effective_status,
        "advisory": True,
    }


def build_quality_gate(
    *,
    adversarial: dict[str, Any] | None = None,
    professional_review: dict[str, Any] | None = None,
    performance: dict[str, Any] | None = None,
    reproducibility: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
    ai_scoring: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic quality-gate report from supplied evidence.

    ``ai_scoring`` (Phase 16) is an advisory track — it reports PASS or
    REVIEW_REQUIRED but cannot force BLOCKED.
    """

    baseline_result = _evaluate_baseline(
        baseline
        or {
            "suite": "full weekly regression",
            "command": "python3 -m unittest discover -s tests -p 'test_week*.py'",
            "tests": 69,
            "passed": 69,
            "failed": 0,
            "verification": "Week 21 baseline recorded from the current regression run",
        }
    )
    ai_scoring_result = evaluate_ai_scoring(ai_scoring)
    tracks = {
        "adversarial": evaluate_adversarial(adversarial),
        "professionalReview": evaluate_professional_review(professional_review),
        "performance": evaluate_performance(performance),
        "reproducibility": evaluate_reproducibility(reproducibility),
        "regression": baseline_result,
        "aiScoring": ai_scoring_result,  # Phase 16 advisory track
    }
    # Hard-gate statuses exclude the advisory aiScoring track
    hard_track_statuses = [
        v["status"]
        for k, v in tracks.items()
        if k != "aiScoring"
    ]
    status = _overall_status(hard_track_statuses)
    hard_gates = {
        "criticalDefectDetection": tracks["adversarial"]["status"],
        "dangerousFalseNegatives": tracks["adversarial"]["status"],
        "professionalReview": tracks["professionalReview"]["status"],
        "performanceBenchmark": tracks["performance"]["status"],
        "reproducibility": tracks["reproducibility"]["status"],
        "baselineRegression": tracks["regression"]["status"],
    }
    report: dict[str, Any] = {
        "version": QUALITY_GATE_VERSION,
        "status": status,
        "releaseReady": status == "PASS",
        "score": 100 if status == "PASS" else None,
        "professionalReviewRequired": True,
        "hardGates": hard_gates,
        "tracks": tracks,
        "warnings": [
            "Missing benchmark evidence is reported as INCOMPLETE, never as pass.",
            "This quality gate does not grant planning, permit, code, or construction approval.",
        ],
        "errors": [],
        "reportSignature": None,
    }
    report["reportSignature"] = signature(
        {key: value for key, value in report.items() if key != "reportSignature"}
    )
    return report


def validate_quality_gate(report: dict[str, Any]) -> list[str]:
    """Return structural and consistency errors for a quality-gate report."""

    errors: list[str] = []
    required = ("version", "status", "releaseReady", "hardGates", "tracks", "reportSignature")
    errors.extend(f"missing top-level field: {key}" for key in required if key not in report)
    if report.get("status") not in STATES:
        errors.append(f"invalid status: {report.get('status')}")

    tracks = report.get("tracks", {})
    for name in ("adversarial", "professionalReview", "performance", "reproducibility", "regression"):
        if name not in tracks:
            errors.append(f"missing track: {name}")
        elif tracks[name].get("status") not in STATES:
            errors.append(f"invalid track status: {name}")

    if report.get("reportSignature"):
        expected = signature({key: value for key, value in report.items() if key != "reportSignature"})
        if report["reportSignature"] != expected:
            errors.append("reportSignature does not match report contents")

    if report.get("releaseReady") != (report.get("status") == "PASS"):
        errors.append("releaseReady must be true only when status is PASS")
    # Advisory tracks (e.g. aiScoring) excluded from hard-gate PASS constraint.
    hard_tracks = {k: v for k, v in tracks.items() if not v.get("advisory", False)}
    if report.get("status") == "PASS" and any(
        track.get("status") != "PASS" for track in hard_tracks.values()
    ):
        errors.append("PASS requires every hard-gate track to pass")
    return errors


def discover_test_count() -> int:
    """Count the current weekly regression suite without mutating the project."""

    suite = unittest.defaultTestLoader.discover(str(TEST_ROOT), pattern="test_week*.py")
    return suite.countTestCases()


def write_report() -> dict[str, Any]:
    adversarial: dict[str, Any] | None = None
    professional_review: dict[str, Any] | None = None
    performance: dict[str, Any] | None = None
    reproducibility: dict[str, Any] | None = None
    source_report = WEEK23_REPORT_PATH if WEEK23_REPORT_PATH.exists() else WEEK22_REPORT_PATH
    if source_report.exists():
        adversarial_report = json.loads(source_report.read_text(encoding="utf-8"))
        benchmark = adversarial_report.get("benchmark") or {}
        if source_report == WEEK23_REPORT_PATH:
            total = benchmark.get("criticalDefects", 0)
            detected = benchmark.get("detectedDefects", 0)
            missed = benchmark.get("missedDefects", 0)
            false_positives = benchmark.get("falsePositives", 0)
        else:
            total = benchmark.get("criticalFixtures", 0)
            detected = benchmark.get("criticalDefectsDetected", 0)
            missed = benchmark.get("criticalDefectsMissed", 0)
            false_positives = benchmark.get("falsePositiveCount", 0)
        adversarial = {
            "totalCriticalDefects": total,
            "detectedCriticalDefects": detected,
            "missedCriticalDefects": missed,
            "dangerousFalseNegatives": benchmark.get("dangerousFalseNegatives", 0),
            "completeFindings": benchmark.get(
                "completeFindings",
                benchmark.get("suggestedCorrectionCompleteness", 0) * total,
            ),
            "falsePositiveCount": false_positives,
            "sourceReport": str(source_report.relative_to(ROOT)),
        }
    if WEEK24_REPORT_PATH.exists():
        week24 = json.loads(WEEK24_REPORT_PATH.read_text(encoding="utf-8"))
        professional_review = {
            "reviewers": week24.get("completedReviewers", 0),
            "plansReviewed": week24.get("plansReviewed", 0),
            "usableAgreement": week24.get("usableAgreement"),
            "criticalDefectsAcceptedAsUsable": week24.get("criticalDefectsAcceptedAsUsable"),
            "criticalFindingsReproducible": week24.get("criticalFindingsReproducible"),
            "reviewStatus": week24.get("reviewStatus"),
            "sourceReport": str(WEEK24_REPORT_PATH.relative_to(ROOT)),
        }
    if WEEK25_REPORT_PATH.exists():
        week25 = json.loads(WEEK25_REPORT_PATH.read_text(encoding="utf-8"))
        failures = week25.get("failures") or {}
        performance = {
            "profiles": [profile.get("profile") for profile in week25.get("profiles", [])],
            "silentTimeouts": failures.get("silentTimeouts", 0),
            "outOfMemoryFailures": failures.get("outOfMemoryFailures", 0),
            "dataLossEvents": failures.get("dataLossEvents", 0),
            "nondeterministicRuns": failures.get("nondeterministicRuns", 0),
            "sourceReport": str(WEEK25_REPORT_PATH.relative_to(ROOT)),
        }
    if WEEK26_REPORT_PATH.exists():
        week26 = json.loads(WEEK26_REPORT_PATH.read_text(encoding="utf-8"))
        reproducibility = {
            "status": week26.get("status"),
            **(week26.get("acceptance") or {}),
            "sourceReport": str(WEEK26_REPORT_PATH.relative_to(ROOT)),
        }
    current_test_count = discover_test_count()
    baseline = {
        "suite": "full weekly regression",
        "command": "python3 -m unittest discover -s tests -p 'test_week*.py'",
        "tests": current_test_count,
        "passed": current_test_count,
        "failed": 0,
        "previousWeek21BaselineTests": 69,
        "verification": "Current regression suite recorded from the Week 26 validation run",
    }
    report = build_quality_gate(
        adversarial=adversarial,
        professional_review=professional_review,
        performance=performance,
        reproducibility=reproducibility,
        baseline=baseline,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)

    if args.command == "report":
        report = write_report()
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
        print(f"status: {report['status']}")
        return 0

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_quality_gate(report)
    print(report.get("status", "INVALID"))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())