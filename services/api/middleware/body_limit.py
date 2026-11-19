"""Request body size limit middleware — E09 Staging & Release hardening.

Rejects oversized requests before they are read into memory.  The limit is
configurable per environment via MAX_REQUEST_BODY_BYTES so staging and
production can tighten it independently of local development.
"""
from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# 5 MiB is ample for the JSON command/brief payloads this API accepts.
MAX_BODY_BYTES: int = int(os.environ.get("MAX_REQUEST_BODY_BYTES", str(5 * 1024 * 1024)))


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > MAX_BODY_BYTES:
                    return JSONResponse(
                        {"error": "payload_too_large", "message": "Request body exceeds limit"},
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse(
                    {"error": "invalid_content_length", "message": "Malformed Content-Length"},
                    status_code=400,
                )
        return await call_next(request)
