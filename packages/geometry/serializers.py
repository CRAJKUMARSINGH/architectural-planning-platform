"""Deterministic canonical serialization and content hashing."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .tolerances import quantize_number


def normalize(value: Any) -> Any:
    """Normalize JSON-compatible data recursively before hashing or writing."""

    if isinstance(value, dict):
        return {str(key): normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, tuple):
        return [normalize(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON cannot contain NaN or infinity")
        return quantize_number(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported value for canonical JSON: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def clone_json(value: Any) -> Any:
    """Clone only through the same JSON boundary used by revisions."""

    return json.loads(canonical_json(value))


def serialize_model(model: Any) -> str:
    """Serialize a canonical model dict to a deterministic JSON string."""
    return canonical_json(model)


def deserialize_model(raw: str) -> Any:
    """Deserialize a canonical model from a JSON string."""
    return json.loads(raw)
