#!/usr/bin/env python3
"""Build the Phase 12 test-category inventory without masking open gaps."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests/fixtures/phase12/quality_gate_contract.json"
REPORT_PATH = ROOT / "bar-association-hall/standard/phase12-quality-gate-report.json"


def _signature(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    if not isinstance(fixture, dict) or not isinstance(fixture.get("categories"), list):
        raise ValueError("Phase 12 fixture must contain a categories list")
    return fixture


def build_report() -> dict[str, Any]:
    fixture = _load_fixture()
    categories: list[dict[str, Any]] = []
    missing_files: list[str] = []
    for category in fixture["categories"]:
        paths = [str(path) for path in category.get("testPaths", [])]
        missing = [path for path in paths if not (ROOT / path).is_file()]
        missing_files.extend(missing)
        categories.append(
            {
                "id": category["id"],
                "status": category["status"],
                "testPaths": paths,
                "missingTestPaths": missing,
            }
        )
    pending = sorted(item["id"] for item in categories if item["status"] == "pending")
    report: dict[str, Any] = {
        "version": "phase12.quality-gate.v1",
        "status": "REVIEW_REQUIRED" if pending else "PASS",
        "mergeBlocker": bool(pending),
        "categories": categories,
        "coveredCategoryCount": sum(item["status"] == "covered" for item in categories),
        "pendingCategories": pending,
        "missingTestPaths": sorted(set(missing_files)),
        "policy": {
            "missingEvidenceIsNotPass": True,
            "pendingCategoriesRequireExplicitFollowUp": True,
            "adversarialSuiteRemainsMergeBlocker": True,
        },
        "reportSignature": None,
    }
    report["reportSignature"] = _signature(
        {key: value for key, value in report.items() if key != "reportSignature"}
    )
    return report


def write_report() -> dict[str, Any]:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = _signature(
        {key: value for key, value in report.items() if key != "reportSignature"}
    )
    if report.get("reportSignature") != expected:
        errors.append("report signature mismatch")
    if report.get("missingTestPaths"):
        errors.append("fixture references missing test paths")
    if report.get("pendingCategories") and report.get("status") != "REVIEW_REQUIRED":
        errors.append("pending categories must keep the gate in REVIEW_REQUIRED")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("report", "validate"), nargs="?", default="validate")
    args = parser.parse_args()
    report = write_report()
    errors = validate_report(report)
    print(json.dumps({"status": report["status"], "errors": errors}, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())