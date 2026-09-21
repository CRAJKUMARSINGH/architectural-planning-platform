"""Numerical policy for architectural geometry.

The canonical model is stored in inches.  These tolerances are intentionally
small enough not to hide a design change, but large enough to avoid rejecting
normal floating-point round trips.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import math


@dataclass(frozen=True)
class Tolerances:
    linear: float = 1e-6
    angular: float = 1e-6
    area: float = 1e-4
    serialization_decimals: int = 9


DEFAULT_TOLERANCES = Tolerances()


def is_close(left: float, right: float, tolerance: float = DEFAULT_TOLERANCES.linear) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def is_positive(value: float, tolerance: float = DEFAULT_TOLERANCES.linear) -> bool:
    return value > tolerance


def quantize_number(value: float | int, decimals: int = DEFAULT_TOLERANCES.serialization_decimals) -> int | float:
    """Return a stable JSON-friendly number without binary float noise."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if not math.isfinite(value):
        raise ValueError("geometry numbers must be finite")
    try:
        decimal = Decimal(str(value)).quantize(
            Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("geometry numbers must be finite") from exc
    result = float(decimal)
    if result == 0:
        return 0
    return result