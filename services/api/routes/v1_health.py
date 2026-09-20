"""E07 /health and /ready endpoints — real dependency checks."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Response

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness probe — always returns 200 if process is up."""
    return {
        "status": "ok",
        "service": "advocate-chambers-api",
        "version": "1.0.0-enterprise",
        "authoritativeGeometry": "python",
    }


@router.get("/ready")
def ready(response: Response) -> dict[str, Any]:
    """Readiness probe — checks Postgres and Redis."""
    checks: dict[str, str] = {}
    ok = True

    # Postgres check
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url and "postgresql" in db_url:
        try:
            from services.api.db.session import engine  # noqa: PLC0415
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
            ok = False
    else:
        checks["postgres"] = "sqlite-dev"

    # Redis check
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        try:
            from redis import Redis  # type: ignore[import]
            Redis.from_url(redis_url).ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            ok = False
    else:
        checks["redis"] = "not-configured"

    status = "ready" if ok else "degraded"
    if not ok:
        response.status_code = 503
    return {"status": status, "checks": checks}


@router.get("/metrics")
def metrics(response: Response):
    """Prometheus metrics — protect in production."""
    try:
        from services.api.middleware.metrics import metrics_endpoint  # noqa: PLC0415
        return metrics_endpoint()
    except Exception:
        return {"error": "metrics unavailable"}
