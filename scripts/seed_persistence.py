#!/usr/bin/env python3
"""Initialize local E02 metadata and seed the known Banswara project."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.api.persistence import DurableStore  # noqa: E402


def main() -> int:
    store = DurableStore(ROOT)
    project = store.seed_banswara(ROOT / "bar-association-hall/standard/model/project.json")
    print(f"Seeded {project['id']} at {store.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
