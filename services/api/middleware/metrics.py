"""Prometheus metrics middleware — E07 Observability.

Exposes /metrics endpoint. Protect in production (behind auth or network policy).
Requires: pip install prometheus-client
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from prometheus_client import (  # type: ignore[import]
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    JOB_QUEUE_DEPTH = Gauge("job_queue_depth", "Number of jobs in queued state")
    VALIDATION_DURATION = Histogram(
        "validation_duration_seconds",
        "Time spent in Python validation pipeline",
        buckets=[0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    )
    PIPELINE_STAGE_DURATION = Histogram(
        "pipeline_stage_duration_seconds",
        "Time spent in a named planning pipeline stage",
        ["stage"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = request.url.path
        method = request.method
        status = str(response.status_code)

        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        return response


def metrics_endpoint() -> Response:
    """Expose Prometheus metrics — mount at /metrics."""
    if not PROMETHEUS_AVAILABLE:
        return Response(
            content='{"error": "prometheus_client not installed"}',
            media_type="application/json",
            status_code=503,
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def observe_pipeline_stage(stage: str, elapsed_seconds: float) -> None:
    """Record one bounded stage name; unavailable metrics never break work."""

    if not PROMETHEUS_AVAILABLE:
        return
    PIPELINE_STAGE_DURATION.labels(stage=stage).observe(max(0.0, elapsed_seconds))
