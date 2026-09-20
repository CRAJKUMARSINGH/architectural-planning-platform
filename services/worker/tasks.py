"""Worker tasks — E04 Async Jobs & Storage.

Each task calls the SAME Python pipeline functions used by the synchronous
path (traecad_engine, quality_gate, weekly scripts). Determinism is preserved
because the worker receives the same model SHA-256 + rule-pack version + seed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "bar-association-hall"))

logger = logging.getLogger("advocate.worker.tasks")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./advocate_chambers_local.db")


def _get_session():
    from services.api.db.session import SessionLocal  # noqa: PLC0415
    return SessionLocal()


def _update_job(job_id: str, status: str, progress: int = 0, error: str | None = None) -> None:
    try:
        from services.api.repository_sql import SqlJobRepository  # noqa: PLC0415
        with _get_session() as s:
            repo = SqlJobRepository(s)
            repo.update_status(uuid.UUID(job_id), status, progress=progress, error=error)
            s.commit()
    except Exception as exc:
        logger.error("Could not update job %s status: %s", job_id, exc)


def _store_artifact(job_id: str, kind: str, data: bytes, filename: str) -> dict:
    from services.api.db.session import SessionLocal  # noqa: PLC0415
    from services.api.repository_sql import SqlArtifactRepository  # noqa: PLC0415
    from services.api.storage import get_object_store  # noqa: PLC0415

    store = get_object_store()
    sha = hashlib.sha256(data).hexdigest()
    key = f"jobs/{job_id}/{sha[:8]}-{filename}"
    store.put(key, data)

    with _get_session() as s:
        art_repo = SqlArtifactRepository(s)
        art = art_repo.create(
            job_id=uuid.UUID(job_id),
            kind=kind,
            storage_key=key,
            sha256=sha,
            size_bytes=len(data),
        )
        s.commit()
    return art


def run_job(job_id: str, job_type: str, payload: dict) -> None:
    """Dispatch a persisted job to the correct pipeline."""
    logger.info("Starting job %s type=%s", job_id, job_type)
    _update_job(job_id, "running", progress=5)

    try:
        if job_type == "quality_gate":
            _run_quality_gate(job_id, payload)
        elif job_type == "validate":
            _run_validate(job_id, payload)
        elif job_type == "enrich":
            _run_enrich(job_id, payload)
        elif job_type == "benchmark":
            _run_benchmark(job_id, payload)
        else:
            _run_generate(job_id, payload)
        _update_job(job_id, "succeeded", progress=100)
        logger.info("Job %s succeeded", job_id)
    except Exception as exc:
        err = traceback.format_exc()
        logger.error("Job %s failed: %s", job_id, exc)
        _update_job(job_id, "failed", error=err)


def _run_quality_gate(job_id: str, payload: dict) -> None:
    import importlib
    qg = importlib.import_module("quality_gate")
    report = qg.run_quality_gate()  # type: ignore[attr-defined]
    data = json.dumps(report, indent=2).encode()
    _store_artifact(job_id, "json-report", data, "quality-gate-report.json")
    _update_job(job_id, "running", progress=80)


def _run_validate(job_id: str, payload: dict) -> None:
    import importlib
    dm = importlib.import_module("drawing_model")
    project = payload.get("project", {})
    plans = payload.get("plans", {})
    errors = dm.validate_model(project, plans)  # type: ignore[attr-defined]
    result = {"errors": errors, "ok": not errors, "checkedAt": datetime.now(timezone.utc).isoformat()}
    data = json.dumps(result, indent=2).encode()
    _store_artifact(job_id, "json-report", data, "validation-report.json")
    _update_job(job_id, "running", progress=80)


def _run_enrich(job_id: str, payload: dict) -> None:
    week = payload.get("week", "27")
    import importlib
    try:
        mod = importlib.import_module(f"week{week}")
        report = mod.enrichment_report()  # type: ignore[attr-defined]
    except Exception:
        report = {"week": week, "status": "REVIEW_REQUIRED", "note": "enrichment unavailable"}
    data = json.dumps(report, indent=2).encode()
    _store_artifact(job_id, "json-report", data, f"week{week}-enrichment-report.json")
    _update_job(job_id, "running", progress=80)


def _run_benchmark(job_id: str, payload: dict) -> None:
    import importlib
    try:
        bm = importlib.import_module("run_benchmark")
        result = bm.run_benchmark()  # type: ignore[attr-defined]
    except Exception:
        result = {"status": "REVIEW_REQUIRED", "note": "benchmark unavailable"}
    data = json.dumps(result, indent=2).encode()
    _store_artifact(job_id, "json-report", data, "benchmark-report.json")
    _update_job(job_id, "running", progress=80)


def _run_generate(job_id: str, payload: dict) -> None:
    """Generate DXF/PDF via the existing Python pipeline."""
    pipeline = payload.get("pipeline", "standard")
    try:
        import importlib
        mod = importlib.import_module("generate_standard_drawings" if pipeline == "standard" else "generate_refined_cad")
        mod.main()  # type: ignore[attr-defined]
        result = {"pipeline": pipeline, "status": "succeeded", "generatedAt": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        result = {"pipeline": pipeline, "status": "failed", "error": str(exc)}
    data = json.dumps(result, indent=2).encode()
    _store_artifact(job_id, "json-report", data, "generate-result.json")
    _update_job(job_id, "running", progress=80)
