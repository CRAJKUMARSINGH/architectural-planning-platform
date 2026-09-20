"""Simple sliding-window rate limiter — E08 Security Hardening.

Uses in-memory counters (good for single-process dev/test).
In production, replace backing store with Redis via slowapi or similar.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Requests per window per IP
RATE_LIMIT: int = 120       # requests
WINDOW_SECONDS: int = 60    # per minute

_ip_windows: dict[str, deque] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health / metrics
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _ip_windows[ip]

        # Evict old entries
        while window and window[0] < now - WINDOW_SECONDS:
            window.popleft()

        if len(window) >= RATE_LIMIT:
            return JSONResponse(
                {"error": "rate_limit_exceeded", "message": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )

        window.append(now)
        return await call_next(request)
