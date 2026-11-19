#!/usr/bin/env python3
"""E09 — Staging smoke test.

Verifies a deployed staging stack is reachable and enforcing auth:

  1. GET  /health                      -> 200
  2. GET  /ready                       -> 200 (reported as DEGRADED on 503)
  3. POST /api/v1/projects/ (no token) -> 401
  4. POST /api/v1/projects/ (token)    -> 201   (only when --token is supplied)

Usage:
    python scripts/enterprise/staging_smoke.py --base-url https://staging.example.com
    python scripts/enterprise/staging_smoke.py --base-url http://localhost:8000 --token "$JWT"

Exit code 0 = all mandatory checks passed, 1 = at least one failed.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

MANDATORY_FAILURES: list[str] = []


def _request(url: str, method: str = "GET", token: str | None = None,
             payload: dict | None = None) -> tuple[int, str]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


def _check(name: str, actual: int, expected: tuple[int, ...], mandatory: bool = True) -> None:
    ok = actual in expected
    status = "PASS" if ok else ("FAIL" if mandatory else "WARN")
    if not ok and mandatory:
        MANDATORY_FAILURES.append(name)
    print(f"[{status}] {name}: got {actual}, expected one of {expected}")


def main() -> int:
    parser = argparse.ArgumentParser(description="E09 staging smoke test")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Staging base URL (no trailing slash)")
    parser.add_argument("--token", default=None, help="Optional JWT for the authenticated checks")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Smoke-testing staging at {base}\n")

    status, _ = _request(f"{base}/health")
    _check("GET /health", status, (200,))

    status, body = _request(f"{base}/ready")
    _check("GET /ready", status, (200,), mandatory=False)
    if status == 503:
        print("        (DEGRADED — Postgres/Redis not green)")

    status, _ = _request(f"{base}/api/v1/projects/", method="POST", payload={"name": "smoke"})
    _check("POST /api/v1/projects/ without token", status, (401,))

    if args.token:
        status, _ = _request(f"{base}/api/v1/projects/", method="POST",
                             payload={"name": "staging-smoke"}, token=args.token)
        _check("POST /api/v1/projects/ with token", status, (201,))
    else:
        print("[SKIP] authenticated project creation (no --token supplied)")

    print()
    if MANDATORY_FAILURES:
        print(f"SMOKE TEST FAILED — {len(MANDATORY_FAILURES)} mandatory check(s) failed: "
              f"{', '.join(MANDATORY_FAILURES)}")
        return 1
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
