"""Small topology helpers shared by command handlers and constraints."""

from __future__ import annotations

from typing import Any

from .tolerances import DEFAULT_TOLERANCES, is_positive


WALLS = {"north", "south", "east", "west"}


def objects(model: dict[str, Any], collection: str) -> list[dict[str, Any]]:
    return [item for item in model.get(collection, []) if isinstance(item, dict)]


def find_object(model: dict[str, Any], collection: str, object_id: str) -> dict[str, Any] | None:
    return next((item for item in objects(model, collection) if item.get("id") == object_id), None)


def find_any(model: dict[str, Any], object_id: str) -> dict[str, Any] | None:
    for collection in (
        "levels",
        "spaces",
        "openings",
        "windows",
        "stairs",
        "verticalConnectors",
    ):
        result = find_object(model, collection, object_id)
        if result is not None:
            return result
    if model.get("site", {}).get("id") == object_id:
        return model["site"]
    if model.get("project", {}).get("id") == object_id:
        return model["project"]
    return None


def level_exists(model: dict[str, Any], level_id: str) -> bool:
    return find_object(model, "levels", level_id) is not None


def space_bounds(space: dict[str, Any]) -> tuple[float, float, float, float] | None:
    rect = space.get("geometry", {}).get("rect")
    if not isinstance(rect, list) or len(rect) != 4:
        return None
    try:
        return tuple(float(value) for value in rect)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def wall_length(space: dict[str, Any], wall: str) -> float | None:
    bounds = space_bounds(space)
    if bounds is None:
        return None
    x0, y0, x1, y1 = bounds
    if wall in {"north", "south"}:
        return x1 - x0
    if wall in {"east", "west"}:
        return y1 - y0
    return None


def opening_span(
    model: dict[str, Any], opening: dict[str, Any], tolerance: float = DEFAULT_TOLERANCES.linear
) -> tuple[float, float] | None:
    host = find_object(model, "spaces", opening.get("hostSpace", ""))
    wall = opening.get("wall")
    geometry = opening.get("geometry", {})
    if host is None or wall not in WALLS:
        return None
    length = wall_length(host, wall)
    try:
        offset = float(geometry["offset"])
        width = float(geometry["width"])
    except (KeyError, TypeError, ValueError):
        return None
    if length is None or not is_positive(width, tolerance) or offset < -tolerance:
        return None
    return offset, offset + width