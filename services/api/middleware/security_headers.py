"""Security headers + CORS hardening middleware — E08 Security Hardening."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

ENV: str = os.environ.get("ENV", "development")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

if ENV not in ("development", "test"):
    # Only add HSTS in non-dev environments
    SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers[k] = v
        # Never leak internal details in error responses
        response.headers.pop("server", None)
        return response
