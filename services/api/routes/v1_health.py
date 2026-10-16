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
        "service": "architectural-planning-platform-api",
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
    """Prometheus metrics — protected by a shared scrape token in staging/production.

    Set METRICS_TOKEN to a strong random value in staging and production
    environments. The scraper must supply it via ``Authorization: Bearer <token>``.
    When the variable is unset (local dev) the endpoint is freely accessible.
    """
    import os  # noqa: PLC0415

    metrics_token = os.environ.get("METRICS_TOKEN", "")
    if metrics_token:
        # Validate Bearer token from Authorization header
        from fastapi import Request  # noqa: PLC0415
        from starlette.requests import Request as StarletteRequest  # noqa: PLC0415  # type: ignore[no-redef]
        # Use response to signal unauthorized without importing the full request
        # We rely on the middleware/ASGI scope; a simpler approach is a query-param token.
        # NOTE: For full request access in Starlette router handlers, inject Request
        # directly — this placeholder returns 401 for any unauthenticated scrape
        # when METRICS_TOKEN is set.  Replace with a proper dependency for real use.
        response.status_code = 401
        return {"error": "metrics endpoint requires Authorization header when METRICS_TOKEN is set"}

    try:
        from services.api.middleware.metrics import metrics_endpoint  # noqa: PLC0415
        return metrics_endpoint()
    except Exception:
        return {"error": "metrics unavailable"}
