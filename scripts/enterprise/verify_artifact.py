"""E08 — Offline artifact integrity verifier.

Usage:
    python scripts/enterprise/verify_artifact.py <file_path> [--expected-sha256 <hash>]

Verifies the SHA-256 hash of a file against its stored value or a provided hash.
Exits 0 if OK, 1 if mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify artifact SHA-256 integrity")
    parser.add_argument("file", type=Path, help="Path to artifact file")
    parser.add_argument("--expected-sha256", help="Expected SHA-256 hex digest")
    parser.add_argument("--manifest", type=Path, help="JSON manifest with sha256 fields")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    actual = sha256_file(args.file)

    if args.expected_sha256:
        expected = args.expected_sha256.lower()
        if actual != expected:
            print(f"FAIL: SHA-256 mismatch for {args.file.name}", file=sys.stderr)
            print(f"  Expected: {expected}", file=sys.stderr)
            print(f"  Actual:   {actual}", file=sys.stderr)
            sys.exit(1)
        print(f"OK {args.file.name}: {actual}")
        return

    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        fname = args.file.name
        entries = manifest.get("artifacts", manifest.get("files", []))
        found = next((e for e in entries if Path(e.get("path", "")).name == fname), None)
        if not found:
            print(f"WARNING: {fname} not found in manifest", file=sys.stderr)
        else:
            expected_m = found.get("sha256", "")
            if actual != expected_m:
                print(f"FAIL: SHA-256 mismatch (manifest)", file=sys.stderr)
                print(f"  Manifest: {expected_m}", file=sys.stderr)
                print(f"  Actual:   {actual}", file=sys.stderr)
                sys.exit(1)
            print(f"OK {fname} matches manifest: {actual}")
        return

    # No expected hash -- just print
    print(f"sha256:{actual}  {args.file}")


if __name__ == "__main__":
    main()
