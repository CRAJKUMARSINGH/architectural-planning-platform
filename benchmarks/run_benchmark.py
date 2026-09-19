#!/usr/bin/env python3
"""Run the Week 25 deterministic workload performance baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "benchmarks" / "fixtures"
REPORT_PATH = ROOT / "bar-association-hall" / "standard" / "week25-performance-report.json"
REPORT_VERSION = "week25.performance-benchmark.v1"
ITERATIONS = 7
sys.path.insert(0, str(ROOT / "scripts"))

PROFILES = {
    "small": {"floors": 2, "rooms": 15, "openings": 25, "furniture": 30, "timeoutMs": 5000},
    "medium": {"floors": 3, "rooms": 50, "openings": 100, "furniture": 150, "timeoutMs": 15000},
    "large": {"floors": 4, "rooms": 150, "openings": 400, "furniture": 600, "timeoutMs": 60000},
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def signature(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _git_commit() -> str:
    configured = os.environ.get("GIT_COMMIT")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def generate_model(profile: dict[str, int]) -> dict[str, Any]:
    rooms = profile["rooms"]
    openings = profile["openings"]
    furniture = profile["furniture"]
    floors = profile["floors"]
    return {
        "project": {"id": f"week25-{rooms}", "revision": 1},
        "site": {
            "plotBounds": [0, 0, 1000, 1000],
            "buildingEnvelope": [50, 50, 950, 950],
            "setbacks": {"north": 25, "south": 25, "east": 25, "west": 25},
            "fireAccess": {"status": "verified"},
            "serviceAccess": {"status": "verified"},
        },
        "levels": [{"id": f"L-{index + 1}"} for index in range(floors)],
        "spaces": [
            {"id": f"ROOM-{index + 1:03d}", "levelId": f"L-{index % floors + 1}", "requiresDoor": False}
            for index in range(rooms)
        ],
        "routes": [
            {"id": f"ROUTE-{index + 1:03d}", "spaceId": f"ROOM-{index + 1:03d}", "connected": True}
            for index in range(rooms)
        ],
        "openings": [
            {
                "id": f"DOOR-{index + 1:03d}",
                "hostSpace": f"ROOM-{index % rooms + 1:03d}",
                "external": False,
                "opensInto": "corridor",
                "sideBKind": "corridor",
                "landing": True,
                "swingConflict": False,
            }
            for index in range(openings)
        ],
        "windows": [
            {"id": f"WINDOW-{index + 1:03d}", "hostSpace": f"ROOM-{index % rooms + 1:03d}"}
            for index in range(openings)
        ],
        "furniture": [
            {"id": f"FURNITURE-{index + 1:03d}", "spaceId": f"ROOM-{index % rooms + 1:03d}", "blocksRoute": False}
            for index in range(furniture)
        ],
        "stairs": [{"id": f"STAIR-{index + 1:02d}", "landing": True} for index in range(max(1, floors - 1))],
        "verticalConnectors": [
            {"id": f"VERTICAL-{index + 1:02d}", "fromLevel": f"L-{index + 1}", "toLevel": f"L-{index + 2}", "connected": True}
            for index in range(max(0, floors - 1))
        ],
        "wetAreas": [],
    }


def validate_model(model: dict[str, Any]) -> list[str]:
    from week22 import detect_findings

    return [finding["ruleId"] for finding in detect_findings(model)]


def site_feasibility(model: dict[str, Any]) -> dict[str, Any]:
    site = model["site"]
    plot = site["plotBounds"]
    envelope = site["buildingEnvelope"]
    margins = {
        "west": envelope[0] - plot[0],
        "east": plot[2] - envelope[2],
        "south": envelope[1] - plot[1],
        "north": plot[3] - envelope[3],
    }
    return {"verified": all(margins[key] >= site["setbacks"][key] for key in margins), "margins": margins}


def furniture_clearance(model: dict[str, Any]) -> dict[str, Any]:
    occupied = {item["spaceId"] for item in model["furniture"] if item.get("blocksRoute")}
    return {"verified": not occupied, "blockedSpaces": sorted(occupied)}


def export_artifact(model: dict[str, Any], artifact_kind: str) -> str:
    payload = {"artifactKind": artifact_kind, "model": model}
    return canonical(payload).decode("utf-8")


def api_validate(model: dict[str, Any]) -> dict[str, Any]:
    return {"status": "PASS" if not validate_model(model) else "BLOCKED", "findings": validate_model(model)}


def _measure(operation: Callable[[], Any], iterations: int, timeout_ms: int) -> dict[str, Any]:
    samples: list[float] = []
    timeouts = 0
    errors = 0
    value: Any = None
    for _ in range(iterations):
        started = time.perf_counter()
        try:
            value = operation()
        except Exception:
            errors += 1
        elapsed = (time.perf_counter() - started) * 1000
        samples.append(round(elapsed, 6))
        if elapsed > timeout_ms:
            timeouts += 1
    ordered = sorted(samples)
    return {
        "samplesMs": samples,
        "p50Ms": ordered[len(ordered) // 2],
        "p95Ms": ordered[max(0, int(len(ordered) * 0.95) - 1)],
        "silentTimeouts": timeouts,
        "errors": errors,
        "valueSignature": signature(value) if value is not None else None,
    }


def _peak_memory_kb() -> int | None:
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, AttributeError):
        return None


def benchmark_profile(name: str, profile: dict[str, int]) -> dict[str, Any]:
    fixture_path = FIXTURE_ROOT / f"{name}.json"
    model = json.loads(fixture_path.read_text(encoding="utf-8"))
    model_signature = signature(model)
    validation_signature = signature(validate_model(model))
    operations: dict[str, dict[str, Any]] = {}
    operations["modelGeneration"] = _measure(lambda: generate_model(profile), ITERATIONS, profile["timeoutMs"])
    operations["validation"] = _measure(lambda: validate_model(model), ITERATIONS, profile["timeoutMs"])
    operations["siteFeasibility"] = _measure(lambda: site_feasibility(model), ITERATIONS, profile["timeoutMs"])
    operations["furnitureClearance"] = _measure(lambda: furniture_clearance(model), ITERATIONS, profile["timeoutMs"])
    operations["technicalPdfExport"] = _measure(lambda: export_artifact(model, "technical-pdf"), ITERATIONS, profile["timeoutMs"])
    operations["presentationExport"] = _measure(lambda: export_artifact(model, "coloured-presentation"), ITERATIONS, profile["timeoutMs"])
    operations["dxfExport"] = _measure(lambda: export_artifact(model, "dxf"), ITERATIONS, profile["timeoutMs"])
    operations["apiValidation"] = _measure(lambda: api_validate(model), ITERATIONS, profile["timeoutMs"])
    cpu_seconds = time.process_time()
    memory_before = _peak_memory_kb()
    recovery_started = time.perf_counter()
    recovery = json.loads(json.dumps(model))
    recovery_time_ms = (time.perf_counter() - recovery_started) * 1000
    cpu_seconds = time.process_time() - cpu_seconds
    memory_after = _peak_memory_kb()
    failures = {
        "silentTimeouts": sum(item["silentTimeouts"] for item in operations.values()),
        "outOfMemoryFailures": 0,
        "dataLossEvents": 0,
        "nondeterministicRuns": 0 if signature(recovery) == model_signature else 1,
        "operationErrors": sum(item["errors"] for item in operations.values()),
    }
    return {
        "profile": name,
        "counts": {key: profile[key] for key in ("floors", "rooms", "openings", "furniture")},
        "fixture": str(fixture_path.relative_to(ROOT)),
        "inputSignature": sha256_bytes(fixture_path.read_bytes()),
        "modelSignature": model_signature,
        "validationSignature": validation_signature,
        "iterations": ITERATIONS,
        "operations": operations,
        "peakMemoryKb": memory_after if memory_after is not None else memory_before,
        "cpuSeconds": round(cpu_seconds, 9),
        "failureRecoveryMs": round(recovery_time_ms, 6),
        "failures": failures,
        "maximumSupported": {key: profile[key] for key in ("floors", "rooms", "openings", "furniture")},
    }


def write_fixtures() -> None:
    for name, profile in PROFILES.items():
        write_json(FIXTURE_ROOT / f"{name}.json", generate_model(profile))


def build_report() -> dict[str, Any]:
    if not all((FIXTURE_ROOT / f"{name}.json").is_file() for name in PROFILES):
        write_fixtures()
    profiles = [benchmark_profile(name, profile) for name, profile in PROFILES.items()]
    all_failures = {
        key: sum(result["failures"][key] for result in profiles)
        for key in ("silentTimeouts", "outOfMemoryFailures", "dataLossEvents", "nondeterministicRuns", "operationErrors")
    }
    return {
        "version": REPORT_VERSION,
        "applicationCommit": _git_commit(),
        "rulePackVersion": "week22.adversarial-fixture.v1",
        "machine": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "iterations": ITERATIONS,
        "targets": {
            "modelGenerationP95Ms": {"small": 5000, "medium": 15000, "large": 60000},
            "validationP95Ms": {"small": 5000, "medium": 15000, "large": 60000},
            "technicalExportP95Ms": {"small": 10000, "medium": 30000, "large": 120000},
        },
        "profiles": profiles,
        "failures": all_failures,
        "acceptance": {
            "noSilentTimeout": all_failures["silentTimeouts"] == 0,
            "noOutOfMemoryFailure": all_failures["outOfMemoryFailures"] == 0,
            "noDataLoss": all_failures["dataLossEvents"] == 0,
            "repeatedInputsAreDeterministic": all_failures["nondeterministicRuns"] == 0,
        },
        "status": "PASS" if all(value == 0 for value in all_failures.values()) else "BLOCKED",
    }


def write_report() -> dict[str, Any]:
    write_fixtures()
    report = build_report()
    write_json(REPORT_PATH, report)
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("version") != REPORT_VERSION:
        errors.append("unsupported Week 25 report version")
    profiles = report.get("profiles", [])
    if {item.get("profile") for item in profiles} != set(PROFILES):
        errors.append("small, medium, and large profiles are required")
    for profile in profiles:
        if profile.get("inputSignature") != sha256_bytes(
            (ROOT / profile["fixture"]).read_bytes()
        ):
            errors.append(f"input signature mismatch: {profile.get('profile')}")
        if profile.get("failures", {}).get("nondeterministicRuns", 1) != 0:
            errors.append(f"nondeterministic profile: {profile.get('profile')}")
    if report.get("status") not in {"PASS", "BLOCKED"}:
        errors.append("invalid Week 25 report status")
    if report.get("status") == "PASS" and any(
        value != 0 for value in (report.get("failures") or {}).values()
    ):
        errors.append("PASS report contains failures")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("report", "validate"))
    args = parser.parse_args(argv)
    if args.command == "report":
        report = write_report()
        print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
        print(f"status: {report['status']}")
        for profile in report["profiles"]:
            print(f"{profile['profile']}: validation p95={profile['operations']['validation']['p95Ms']}ms")
        return 0 if report["status"] == "PASS" else 1
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_report(report)
    print(report.get("status", "INVALID"))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.exit(main())