"""E09 — Release checklist runner.

Runs all pre-release gates and produces a summary. Exit 0 = ready, 1 = not ready.

Usage:
    python scripts/enterprise/release_check.py [--version 1.0.0]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str = "") -> None:
        self.name = name
        self.passed = passed
        self.detail = detail

    def __str__(self) -> str:
        icon = "✓" if self.passed else "✗"
        suffix = f" — {self.detail}" if self.detail else ""
        return f"  {icon} {self.name}{suffix}"


def check_quality_gate() -> CheckResult:
    report_path = ROOT / "bar-association-hall" / "standard" / "quality-gate-report.json"
    if not report_path.exists():
        return CheckResult("Quality gate report", False, "report file missing")
    with report_path.open() as f:
        report = json.load(f)
    status = report.get("status", "INCOMPLETE")
    detected = report.get("adversarialSuite", {}).get("detected", 0)
    ok = status in ("PASS", "REVIEW_REQUIRED") and detected >= 30
    return CheckResult(
        "Quality gate",
        ok,
        f"status={status}, adversarial={detected}/30",
    )


def check_adversarial_suite() -> CheckResult:
    report_path = ROOT / "bar-association-hall" / "standard" / "week23-adversarial-expansion-report.json"
    if not report_path.exists():
        return CheckResult("Adversarial suite report", False, "report missing")
    with report_path.open() as f:
        data = json.load(f)
    detected = data.get("totalDetected", data.get("detected", 0))
    return CheckResult("Adversarial suite 30/30", detected >= 30, f"detected={detected}")


def check_performance_report() -> CheckResult:
    report_path = ROOT / "bar-association-hall" / "standard" / "week25-performance-report.json"
    if not report_path.exists():
        return CheckResult("Performance report", False, "report missing")
    return CheckResult("Performance report", True, "exists")


def check_changelog() -> CheckResult:
    cl = ROOT / "CHANGELOG.md"
    return CheckResult("CHANGELOG.md", cl.exists())


def check_security_md() -> CheckResult:
    sec = ROOT / "SECURITY.md"
    return CheckResult("SECURITY.md", sec.exists())


def check_baselines() -> CheckResult:
    bl = ROOT / "baselines" / "2026-09-20"
    ok = bl.exists() and len(list(bl.glob("*.json"))) >= 5
    return CheckResult("Baselines frozen", ok, str(bl))


def run(version: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Release Checklist — Advocate-Chambers v{version}")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    checks = [
        check_quality_gate(),
        check_adversarial_suite(),
        check_performance_report(),
        check_changelog(),
        check_security_md(),
        check_baselines(),
    ]

    passed = sum(1 for c in checks if c.passed)
    total = len(checks)

    for c in checks:
        print(c)

    print(f"\nResult: {passed}/{total} checks passed")

    if passed < total:
        failed = [c.name for c in checks if not c.passed]
        print(f"\nBLOCKED — fix before release: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✓ All checks passed — ready for v{version} release tag")
        print("\nNext steps:")
        print(f"  git tag -a v{version} -m 'Release v{version}'")
        print(f"  git push origin v{version}")
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="1.0.0-enterprise-candidate")
    args = parser.parse_args()
    run(args.version)
