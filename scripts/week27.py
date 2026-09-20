#!/usr/bin/env python3
"""Build the Week 27 integrated release decision and remediation register.

Week 27 combines the evidence already produced by Weeks 22–26.  It does not
turn preliminary planning material into an approval or construction issue set.
The release classification is deliberately conservative:

* BLOCKED when a hard gate fails;
* REVIEW_REQUIRED while professional, site, statutory, or authority evidence
  remains incomplete;
* PRELIMINARY_COORDINATION_READY only after the automated gates and independent
  professional review pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STANDARD_ROOT = ROOT / "bar-association-hall" / "standard"
QUALITY_GATE_PATH = STANDARD_ROOT / "quality-gate-report.json"
REPORT_PATH = STANDARD_ROOT / "week27-integrated-release-report.json"
LIMITATIONS_PATH = STANDARD_ROOT / "week27-known-limitations.json"
BACKLOG_PATH = STANDARD_ROOT / "week27-remediation-backlog.json"
CHANGELOG_PATH = STANDARD_ROOT / "week27-changelog.md"
REPORT_VERSION = "week27.integrated-release.v1"


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def signature(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def git_commit() -> str:
    configured = os.environ.get("GIT_COMMIT")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def release_classification(quality_status: str) -> str:
    if quality_status == "BLOCKED":
        return "BLOCKED"
    if quality_status == "PASS":
        return "PRELIMINARY_COORDINATION_READY"
    return "REVIEW_REQUIRED"


def evidence_summary(quality_gate: dict[str, Any]) -> dict[str, Any]:
    tracks = quality_gate.get("tracks", {})
    names = (
        "adversarial",
        "professionalReview",
        "performance",
        "reproducibility",
        "regression",
    )
    return {
        name: {
            "status": tracks.get(name, {}).get("status", "INCOMPLETE"),
            "sourceReport": tracks.get(name, {}).get("sourceReport"),
        }
        for name in names
    }


def build_limitations(quality_gate: dict[str, Any]) -> list[dict[str, Any]]:
    professional = quality_gate.get("tracks", {}).get("professionalReview", {})
    return [
        {
            "id": "LIM-027-001",
            "category": "independent-professional-review",
            "severity": "REVIEW_REQUIRED",
            "status": "OPEN",
            "statement": (
                "Two independent professional reviews, usable/not-usable "
                "agreement, and finding reproducibility are still pending."
            ),
            "evidence": {
                "qualityGateStatus": professional.get("status", "INCOMPLETE"),
                "sourceReport": professional.get("sourceReport"),
            },
            "exitCriteria": [
                "Two independent reviewers submit signed scorecards.",
                "Usable/not-usable agreement is at least 90%.",
                "No critical defect is accepted as usable by both reviewers.",
                "Critical software findings are reproducible from model and rule evidence.",
            ],
        },
        {
            "id": "LIM-027-002",
            "category": "statutory-and-site-verification",
            "severity": "REVIEW_REQUIRED",
            "status": "OPEN",
            "statement": (
                "Survey, jurisdictional code, fire/life-safety, accessibility, "
                "structural, MEP, and authority sign-off remain outside automated "
                "release evidence."
            ),
            "evidence": {
                "source": "Validation program scope and project review notes",
                "automaticApproval": False,
            },
            "exitCriteria": [
                "Appointed professionals verify the current site and governing requirements.",
                "Authority-specific corrections are recorded against a project revision.",
                "A signed issue decision is stored with the delivered package.",
            ],
        },
        {
            "id": "LIM-027-003",
            "category": "drawing-status",
            "severity": "REVIEW_REQUIRED",
            "status": "OPEN",
            "statement": (
                "Repository drawing packages remain preliminary planning and "
                "coordination aids, not construction or permit drawings."
            ),
            "evidence": {
                "releaseClassification": release_classification(
                    quality_gate.get("status", "INCOMPLETE")
                ),
                "automaticIssuance": False,
            },
            "exitCriteria": [
                "Professional review is complete.",
                "Site and authority evidence is complete.",
                "A separately approved issue package is generated and archived.",
            ],
        },
    ]


def build_backlog(quality_gate: dict[str, Any]) -> list[dict[str, Any]]:
    limitations = build_limitations(quality_gate)
    return [
        {
            "id": "REM-027-001",
            "priority": "HIGH",
            "status": "OPEN",
            "owner": "appointed independent reviewers",
            "linkedLimitation": limitations[0]["id"],
            "action": "Complete the Week 24 blinded professional review package.",
            "acceptance": limitations[0]["exitCriteria"],
        },
        {
            "id": "REM-027-002",
            "priority": "HIGH",
            "status": "OPEN",
            "owner": "appointed architect, engineers, surveyor, and authority",
            "linkedLimitation": limitations[1]["id"],
            "action": "Verify site, statutory, fire, accessibility, structural, and MEP assumptions.",
            "acceptance": limitations[1]["exitCriteria"],
        },
        {
            "id": "REM-027-003",
            "priority": "MEDIUM",
            "status": "IN_PROGRESS",
            "owner": "repository maintainer",
            "linkedLimitation": "W28-DATA-001",
            "action": (
                "Keep the multi-project inventory and proposed canonical paths "
                "updated for every future delivery."
            ),
            "acceptance": [
                "Every tracked project artifact has a project, role, source path, and review state.",
                "Legacy paths remain unchanged until a separately approved migration.",
                "Each delivered revision has a manifest and validation status.",
            ],
        },
    ]


def build_report() -> dict[str, Any]:
    quality_gate = read_json(QUALITY_GATE_PATH)
    limitations = build_limitations(quality_gate)
    backlog = build_backlog(quality_gate)
    classification = release_classification(quality_gate.get("status", "INCOMPLETE"))
    acceptance = {
        "noUnresolvedDangerousFalseNegative": (
            quality_gate.get("hardGates", {}).get("dangerousFalseNegatives") == "PASS"
        ),
        "allUnknownsVisible": bool(limitations),
        "reviewerDisagreementsRecorded": (
            quality_gate.get("tracks", {}).get("professionalReview", {}).get("status")
            in {"PASS", "REVIEW_REQUIRED"}
        ),
        "performanceResultsReproducible": (
            quality_gate.get("hardGates", {}).get("performanceBenchmark") == "PASS"
        ),
        "archiveAndRevisionVerificationPass": (
            quality_gate.get("hardGates", {}).get("reproducibility") == "PASS"
        ),
    }
    report = {
        "version": REPORT_VERSION,
        "applicationCommit": git_commit(),
        "qualityGateStatus": quality_gate.get("status", "INCOMPLETE"),
        "releaseClassification": classification,
        "releaseReady": classification == "PRELIMINARY_COORDINATION_READY",
        "issuable": False,
        "decision": (
            "Automated validation evidence is coordinated, but the package "
            "requires independent professional and authority review before issue."
            if classification == "REVIEW_REQUIRED"
            else "See the hard-gate findings and remediation register before issue."
        ),
        "evidence": evidence_summary(quality_gate),
        "acceptance": acceptance,
        "knownLimitations": limitations,
        "remediationBacklog": backlog,
        "sourceQualityGate": str(QUALITY_GATE_PATH.relative_to(ROOT)),
        "reportSignature": None,
    }
    report["reportSignature"] = signature(
        {key: value for key, value in report.items() if key != "reportSignature"}
    )
    return report


def write_report() -> dict[str, Any]:
    report = build_report()
    limitations = {
        "version": "week27.known-limitations.v1",
        "releaseClassification": report["releaseClassification"],
        "limitations": report["knownLimitations"],
        "sourceReport": str(REPORT_PATH.relative_to(ROOT)),
        "reportSignature": report["reportSignature"],
    }
    backlog = {
        "version": "week27.remediation-backlog.v1",
        "items": report["remediationBacklog"],
        "sourceReport": str(REPORT_PATH.relative_to(ROOT)),
        "reportSignature": report["reportSignature"],
    }
    write_json(REPORT_PATH, report)
    write_json(LIMITATIONS_PATH, limitations)
    write_json(BACKLOG_PATH, backlog)
    CHANGELOG_PATH.write_text(
        "# Week 27 integrated release decision\n\n"
        f"- Release classification: **{report['releaseClassification']}**\n"
        f"- Quality-gate status: **{report['qualityGateStatus']}**\n"
        "- Automated evidence is coordinated without converting preliminary "
        "drawings into an issuable package.\n"
        "- Open limitations and remediation actions are recorded in the paired "
        "JSON registers.\n",
        encoding="utf-8",
    )
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "version",
        "applicationCommit",
        "qualityGateStatus",
        "releaseClassification",
        "evidence",
        "acceptance",
        "knownLimitations",
        "remediationBacklog",
        "reportSignature",
    )
    errors.extend(f"missing report field: {field}" for field in required if field not in report)
    if report.get("version") != REPORT_VERSION:
        errors.append("unsupported Week 27 report version")
    if report.get("releaseClassification") not in {
        "BLOCKED",
        "REVIEW_REQUIRED",
        "PRELIMINARY_COORDINATION_READY",
    }:
        errors.append("invalid Week 27 release classification")
    if report.get("issuable") is not False:
        errors.append("Week 27 must never mark the package issuable automatically")
    if report.get("reportSignature"):
        expected = signature(
            {key: value for key, value in report.items() if key != "reportSignature"}
        )
        if report["reportSignature"] != expected:
            errors.append("reportSignature does not match report contents")
    if report.get("releaseClassification") == "PRELIMINARY_COORDINATION_READY":
        if not all((report.get("acceptance") or {}).values()):
            errors.append("coordination-ready report contains a failed acceptance check")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)
    if args.command == "report":
        report = write_report()
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
        print(f"release classification: {report['releaseClassification']}")
        return 0
    report = read_json(REPORT_PATH)
    errors = validate_report(report)
    print(report.get("releaseClassification", "INVALID"))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())