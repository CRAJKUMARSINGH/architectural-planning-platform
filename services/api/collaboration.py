"""Pure collaboration/review policy helpers for Phase 11.

Persistence and HTTP concerns stay in the API/repository layers.  Keeping the
policy here makes review-link security, anchor validation, and approval
transitions deterministic and easy to exercise without a database.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any

REVIEW_VIEWS = frozenset({"technical", "presentation"})
ANCHOR_TYPES = frozenset(
    {
        "room",
        "space",
        "wall",
        "opening",
        "dimension",
        "validation-finding",
        "render-viewpoint",
    }
)
APPROVAL_STATES = (
    "Draft",
    "Review",
    "Client Presentation",
    "Preliminary Coordination",
    "Not Issuable",
)
ALLOWED_APPROVAL_TRANSITIONS = {
    "Draft": frozenset({"Draft", "Review", "Not Issuable"}),
    "Review": frozenset(
        {"Draft", "Review", "Client Presentation", "Preliminary Coordination", "Not Issuable"}
    ),
    "Client Presentation": frozenset(
        {"Review", "Client Presentation", "Preliminary Coordination", "Not Issuable"}
    ),
    "Preliminary Coordination": frozenset(
        {"Review", "Client Presentation", "Preliminary Coordination", "Not Issuable"}
    ),
    "Not Issuable": frozenset({"Review", "Not Issuable"}),
}


def create_review_token() -> tuple[str, str]:
    """Return a one-time-visible raw token and its SHA-256 storage hash."""

    token = secrets.token_urlsafe(32)
    return token, hash_review_token(token)


def hash_review_token(token: str) -> str:
    """Hash a review token without retaining the bearer credential."""

    if not token or len(token) > 512:
        raise ValueError("review token must be non-empty and at most 512 characters")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_review_view(view: str) -> str:
    normalized = view.strip().lower()
    if normalized not in REVIEW_VIEWS:
        raise ValueError(f"view must be one of {sorted(REVIEW_VIEWS)}")
    return normalized


def validate_anchor(
    anchor_type: str,
    anchor_id: str,
    model: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Validate an anchor and, when supplied, require it in the pinned model."""

    normalized_type = anchor_type.strip().lower()
    normalized_id = anchor_id.strip()
    if normalized_type not in ANCHOR_TYPES:
        raise ValueError(f"anchor_type must be one of {sorted(ANCHOR_TYPES)}")
    if not normalized_id or len(normalized_id) > 200:
        raise ValueError("anchor_id must be non-empty and at most 200 characters")
    if normalized_type == "render-viewpoint" or model is None:
        return normalized_type, normalized_id

    collections = {
        "room": ("spaces",),
        "space": ("spaces",),
        "wall": ("walls",),
        "opening": ("openings", "windows"),
        "dimension": ("dimensions",),
        "validation-finding": ("findings",),
    }
    valid_ids = {
        str(item.get("id"))
        for collection in collections[normalized_type]
        for item in model.get(collection, [])
        if isinstance(item, dict) and item.get("id")
    }
    if normalized_id not in valid_ids:
        raise ValueError(f"anchor_id {normalized_id!r} is not present in the pinned model")
    return normalized_type, normalized_id


def validate_approval_transition(previous: str, requested: str) -> str:
    """Reject approval jumps that do not have a reviewable predecessor."""

    if previous not in APPROVAL_STATES:
        raise ValueError(f"unknown current approval state: {previous}")
    if requested not in APPROVAL_STATES:
        raise ValueError(f"unknown requested approval state: {requested}")
    if requested not in ALLOWED_APPROVAL_TRANSITIONS[previous]:
        raise ValueError(f"approval transition {previous!r} -> {requested!r} is not allowed")
    return requested


def sanitize_viewpoint(viewpoint: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep review anchors bounded and JSON-shaped before persistence."""

    if viewpoint is None:
        return None
    if not isinstance(viewpoint, dict) or len(viewpoint) > 12:
        raise ValueError("viewpoint must be an object with at most 12 fields")
    result: dict[str, Any] = {}
    for key, value in viewpoint.items():
        if not isinstance(key, str) or len(key) > 80:
            raise ValueError("viewpoint keys must be short strings")
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 300:
                raise ValueError("viewpoint text values must be at most 300 characters")
            result[key] = value
        else:
            raise ValueError("viewpoint values must be scalar JSON values")
    return result