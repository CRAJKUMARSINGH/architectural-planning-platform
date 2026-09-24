"""Structured JSON logging middleware — E07 Observability."""
from __future__ import annotations

import json
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from services.api.middleware.correlation import (
    build_correlation_context,
    response_correlation_headers,
)

# Configure root logger for JSON output
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "architectural-planning-platform-api",
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("request_id", "trace_id", "job_id", "user_id", "revision_id", "org_id"):
            if hasattr(record, key):
                log[key] = getattr(record, key)
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log)


def configure_json_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)


logger = logging.getLogger("advocate.api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs each request with timing, status, and request_id propagation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        context = build_correlation_context(request.headers)
        for key, value in context.items():
            setattr(request.state, key, value)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s %d",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                **context,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )
        response_headers = response_correlation_headers(context)
        response.headers["x-request-id"] = response_headers["x-request-id"]
        response.headers["x-trace-id"] = response_headers["x-trace-id"]
        return response
