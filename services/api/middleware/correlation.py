"""Bounded correlation context shared by logs, metrics, and API responses."""
from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
CORRELATION_KEYS = ("request_id", "trace_id", "job_id", "revision_id", "org_id")
HEADER_NAMES = {
    "request_id": "x-request-id",
    "trace_id": "x-trace-id",
    "job_id": "x-job-id",
    "revision_id": "x-revision-id",
    "org_id": "x-org-id",
}


def _safe(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text if _SAFE_ID.fullmatch(text) else None


def build_correlation_context(headers: Mapping[str, str]) -> dict[str, str]:
    """Read safe correlation headers and generate request/trace roots."""

    request_id = _safe(headers.get("x-request-id")) or str(uuid.uuid4())
    trace_id = _safe(headers.get("x-trace-id")) or request_id
    context = {"request_id": request_id, "trace_id": trace_id}
    for key in ("job_id", "revision_id", "org_id"):
        value = _safe(headers.get(HEADER_NAMES[key]))
        if value:
            context[key] = value
    return context


def response_correlation_headers(context: Mapping[str, str]) -> dict[str, str]:
    """Expose only safe identifiers; never echo arbitrary inbound headers."""

    return {
        HEADER_NAMES[key]: context[key]
        for key in ("request_id", "trace_id")
        if context.get(key)
    }