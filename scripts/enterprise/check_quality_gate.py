"""E05 — Quality-gate enforcement script.

Usage:
    python scripts/enterprise/check_quality_gate.py [--fail-on-blocked] [--baseline baselines/2026-09-20]

Exit codes:
    0 — gate passes (PASS or only expected REVIEW_REQUIRED)
    1 — gate BLOCKED or critical false-negatives detected
    2 — report missing or unreadable
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "quality-gate-report.json"
BASELINE_DEFAULT = ROOT / "baselines" / "2026-09-20" / "quality-gate-report.json"

# Known adversarial defects that MUST be detected
REQUIRED_ADVERSARIAL_DETECTIONS = 30


def load_report(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: Report not found: {path}", file=sys.stderr)
        sys.exit(2)
    with path.open() as f:
        return json.load(f)


def check_gate(report: dict, fail_on_blocked: bool = True) -> list[str]:
    failures: list[str] = []
    status = report.get("status", "INCOMPLETE")

    if status == "BLOCKED":
        failures.append(f"Quality gate is BLOCKED: {report.get('reason', 'see report')}")
    elif status == "INCOMPLETE":
        failures.append("Quality gate is INCOMPLETE — required evidence missing")

    # Check adversarial detection count (if present in the report)
    adversarial = report.get("adversarialSuite", {})
    if adversarial:
        detected = adversarial.get("detected", 0)
        total = adversarial.get("total", REQUIRED_ADVERSARIAL_DETECTIONS)
        if detected < REQUIRED_ADVERSARIAL_DETECTIONS:
            failures.append(
                f"Adversarial detection regression: {detected}/{total} detected "
                f"(required: {REQUIRED_ADVERSARIAL_DETECTIONS})"
            )

    # Check for missing adversarialSuite key — treat as a failure
    if not adversarial:
        failures.append("adversarialSuite key missing from report — cannot verify detection count")

    # Check for BLOCKER or ERROR findings
    findings = report.get("findings", [])
    blocking_findings = [f for f in findings if f.get("severity") in ("BLOCKER", "ERROR")]
    if blocking_findings:
        failures.append(f"{len(blocking_findings)} BLOCKER/ERROR finding(s) in report:")
        for b in blocking_findings[:5]:
            failures.append(f"  - [{b.get('severity','?')}] {b.get('code', '?')}: {b.get('message', '?')}")

    return failures


def compare_with_baseline(current: dict, baseline: dict) -> list[str]:
    """Warn if quality gate status is worse than the baseline."""
    warnings: list[str] = []
    STATUS_ORDER = {"PASS": 0, "REVIEW_REQUIRED": 1, "INCOMPLETE": 2, "BLOCKED": 3}
    cur_status = current.get("status", "INCOMPLETE")
    base_status = baseline.get("status", "REVIEW_REQUIRED")

    if STATUS_ORDER.get(cur_status, 2) > STATUS_ORDER.get(base_status, 1):
        warnings.append(
            f"REGRESSION: gate status went from {base_status} → {cur_status}"
        )

    cur_detected = current.get("adversarialSuite", {}).get("detected", 0)
    base_detected = baseline.get("adversarialSuite", {}).get("detected", REQUIRED_ADVERSARIAL_DETECTIONS)
    if cur_detected < base_detected:
        warnings.append(
            f"REGRESSION: adversarial detection dropped {base_detected} → {cur_detected}"
        )
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality gate enforcement check")
    parser.add_argument("--fail-on-blocked", action="store_true", default=True)
    parser.add_argument("--baseline", type=Path, default=BASELINE_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    report = load_report(args.report)
    failures = check_gate(report, fail_on_blocked=args.fail_on_blocked)

    # Baseline comparison (warn-only for now, promote to failure in E10)
    if args.baseline.exists():
        baseline = load_report(args.baseline)
        regressions = compare_with_baseline(report, baseline)
        for r in regressions:
            print(f"WARNING: {r}", file=sys.stderr)
    else:
        print(f"WARNING: baseline not found at {args.baseline}", file=sys.stderr)

    if failures:
        print("\nQUALITY GATE FAILURES:", file=sys.stderr)
        for f in failures:
            print(f"  FAIL: {f}", file=sys.stderr)
        print("\nCannot merge. Fix the above issues before retrying.", file=sys.stderr)
        sys.exit(1)
    else:
        status = report.get("status", "UNKNOWN")
        detected = report.get("adversarialSuite", {}).get("detected", "?")
        print(f"PASS: Quality gate: {status} | Adversarial: {detected}/{REQUIRED_ADVERSARIAL_DETECTIONS}")
        sys.exit(0)


if __name__ == "__main__":
    main()
