#!/usr/bin/env python3
"""Run and summarize the frozen E01 repository verification baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = ROOT / "baselines" / "2026-09-20"


COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "python-tests",
        (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"),
    ),
    ("adversarial", (sys.executable, "scripts/week23.py", "validate")),
    ("performance-smoke", (sys.executable, "benchmarks/run_benchmark.py", "validate")),
    ("quality-gate", (sys.executable, "scripts/quality_gate.py", "validate")),
)

REPORTS: tuple[tuple[str, str], ...] = (
    ("quality-gate", "quality-gate-report.json"),
    ("adversarial", "week23-adversarial-expansion-report.json"),
    ("performance-smoke", "week25-performance-report.json"),
)


def _run(name: str, command: tuple[str, ...]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    return {
        "name": name,
        "command": list(command),
        "returnCode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "outputTail": output[-2000:],
    }


def _baseline_statuses() -> dict[str, str]:
    status_paths = {
        "adversarial": BASELINE_ROOT / "week23-adversarial-expansion-report.json",
        "performance-smoke": BASELINE_ROOT / "week25-performance-report.json",
        "quality-gate": BASELINE_ROOT / "quality-gate-report.json",
    }
    statuses: dict[str, str] = {}
    for name, path in status_paths.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        statuses[name] = str(data.get("status", "UNKNOWN"))
    return statuses


def _compare_reports() -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    for name, filename in REPORTS:
        live_path = ROOT / "bar-association-hall" / "standard" / filename
        baseline_path = BASELINE_ROOT / filename
        live = json.loads(live_path.read_text(encoding="utf-8"))
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        matches = live == baseline
        comparisons.append(
            {
                "name": name,
                "status": "match" if matches else "changed",
                "warning": None
                if matches
                else "Live report differs from the frozen baseline; review before updating it.",
            }
        )
    return comparisons


def verify() -> dict[str, Any]:
    results = [_run(name, command) for name, command in COMMANDS]
    baseline_statuses = _baseline_statuses()
    return {
        "reportVersion": "enterprise.e01.baseline.v1",
        "baseline": "baselines/2026-09-20",
        "status": "pass" if all(result["status"] == "pass" for result in results) else "fail",
        "baselineStatuses": baseline_statuses,
        "reportComparisons": _compare_reports(),
        "commands": results,
        "notes": [
            "Quality-gate REVIEW_REQUIRED is an expected honest state while professional evidence is pending.",
            "Report differences are warnings only until E01 adopts an explicit update workflow.",
            "This wrapper does not convert REVIEW_REQUIRED into PASS.",
            "No geometry or rule-pack files are modified by verification.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit only the machine-readable report")
    args = parser.parse_args()
    report = verify()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(report, indent=2))
        print(f"\nE01 baseline verification: {report['status'].upper()}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())