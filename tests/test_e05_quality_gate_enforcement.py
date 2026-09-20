"""E05 — Quality gate enforcement regression tests.

Tests: check_quality_gate.py script exit codes, baseline comparison,
       adversarial count validation, report parsing.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestCheckQualityGateScript(unittest.TestCase):
    def _run(self, report: dict, baseline: dict | None = None) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "quality-gate-report.json"
            report_path.write_text(json.dumps(report))

            cmd = [
                sys.executable,
                "scripts/enterprise/check_quality_gate.py",
                "--report", str(report_path),
            ]

            if baseline is not None:
                bl_path = Path(tmpdir) / "baseline.json"
                bl_path.write_text(json.dumps(baseline))
                cmd += ["--baseline", str(bl_path)]
            else:
                # Point baseline to a non-existent path (skip comparison)
                cmd += ["--baseline", str(Path(tmpdir) / "no-baseline.json")]

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(ROOT)
            )
            return result.returncode, result.stderr

    def test_pass_status_with_30_detections(self):
        report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [],
        }
        code, _ = self._run(report)
        self.assertEqual(code, 0)

    def test_blocked_status_fails(self):
        report = {
            "status": "BLOCKED",
            "reason": "corridor blocked",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [],
        }
        code, stderr = self._run(report)
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED", stderr)

    def test_adversarial_regression_fails(self):
        report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 28, "total": 30},
            "findings": [],
        }
        code, stderr = self._run(report)
        self.assertEqual(code, 1)
        self.assertIn("28", stderr)

    def test_blocker_finding_fails(self):
        report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [
                {"severity": "BLOCKER", "code": "EGRESS-001", "message": "Blocked egress"}
            ],
        }
        code, stderr = self._run(report)
        self.assertEqual(code, 1)

    def test_baseline_regression_warns(self):
        good_report = {
            "status": "REVIEW_REQUIRED",
            "adversarialSuite": {"detected": 30, "total": 30},
            "findings": [],
        }
        better_baseline = {
            "status": "PASS",
            "adversarialSuite": {"detected": 30, "total": 30},
        }
        code, stderr = self._run(good_report, baseline=better_baseline)
        # Should warn about regression but not fail (warn-only during E-weeks)
        self.assertIn("REGRESSION", stderr)

    def test_missing_report_exits_2(self):
        result = subprocess.run(
            [sys.executable, "scripts/enterprise/check_quality_gate.py",
             "--report", "/nonexistent/path.json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 2)


class TestReleaseCheckScript(unittest.TestCase):
    def test_release_check_script_exists_and_importable(self):
        script = ROOT / "scripts" / "enterprise" / "release_check.py"
        self.assertTrue(script.exists())
        # Syntax check
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
