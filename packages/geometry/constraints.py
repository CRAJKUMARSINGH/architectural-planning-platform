"""Structured, explainable constraints for the phase-two command slice."""

from __future__ import annotations

from typing import Any

from .commands import finding
from .tolerances import DEFAULT_TOLERANCES, is_positive
from .topology import WALLS, find_object, level_exists, wall_length


def required_parameter(parameters: dict[str, Any], name: str) -> tuple[Any, dict[str, Any] | None]:
    if name not in parameters:
        return None, finding(
            rule="COMMAND_PARAMETER_REQUIRED",
            message=f"parameter '{name}' is required",
            severity="BLOCKER",
            evidence={"parameter": name},
        )
    return parameters[name], None


def unique_id(model: dict[str, Any], object_id: str) -> dict[str, Any] | None:
    for collection in (
        "levels",
        "spaces",
        "openings",
        "windows",
        "stairs",
        "verticalConnectors",
    ):
        if find_object(model, collection, object_id) is not None:
            return finding(
                rule="OBJECT_ID_UNIQUE",
                message=f"object id '{object_id}' already exists",
                severity="BLOCKER",
                object_ids=[object_id],
            )
    return None


def validate_space_geometry(rect: Any, object_id: str | None = None) -> list[dict[str, Any]]:
    if not isinstance(rect, list) or len(rect) != 4:
        return [
            finding(
                rule="SPACE_RECT_SHAPE",
                message="space rect must be [x0, y0, x1, y1]",
                severity="BLOCKER",
                object_ids=[object_id] if object_id else [],
            )
        ]
    try:
        x0, y0, x1, y1 = (float(value) for value in rect)
    except (TypeError, ValueError):
        return [
            finding(
                rule="SPACE_RECT_NUMERIC",
                message="space rect coordinates must be numeric",
                severity="BLOCKER",
                object_ids=[object_id] if object_id else [],
            )
        ]
    if not is_positive(x1 - x0) or not is_positive(y1 - y0):
        return [
            finding(
                rule="SPACE_POSITIVE_AREA",
                message="space rect must have positive width and depth",
                severity="BLOCKER",
                object_ids=[object_id] if object_id else [],
                evidence={"rect": rect},
            )
        ]
    return []


def validate_level_reference(model: dict[str, Any], level_id: Any) -> list[dict[str, Any]]:
    if not isinstance(level_id, str) or not level_exists(model, level_id):
        return [
            finding(
                rule="LEVEL_REFERENCE_EXISTS",
                message=f"level '{level_id}' does not exist",
                severity="BLOCKER",
                evidence={"levelId": level_id},
            )
        ]
    return []


def validate_opening_position(
    model: dict[str, Any],
    *,
    host_space_id: Any,
    wall: Any,
    offset: Any,
    width: Any,
    object_id: str | None = None,
) -> list[dict[str, Any]]:
    object_ids = [value for value in (object_id, host_space_id) if isinstance(value, str)]
    space = find_object(model, "spaces", host_space_id) if isinstance(host_space_id, str) else None
    if space is None:
        return [
            finding(
                rule="HOST_SPACE_EXISTS",
                message=f"host space '{host_space_id}' does not exist",
                severity="BLOCKER",
                object_ids=object_ids,
            )
        ]
    if wall not in WALLS:
        return [
            finding(
                rule="OPENING_WALL_SIDE",
                message="opening wall must be north, south, east, or west",
                severity="BLOCKER",
                object_ids=object_ids,
            )
        ]
    try:
        numeric_offset = float(offset)
        numeric_width = float(width)
    except (TypeError, ValueError):
        return [
            finding(
                rule="OPENING_DIMENSIONS_NUMERIC",
                message="opening offset and width must be numeric",
                severity="BLOCKER",
                object_ids=object_ids,
            )
        ]
    length = wall_length(space, wall)
    if length is None:
        return [
            finding(
                rule="HOST_SPACE_RECT",
                message="host space does not have measurable rectangular geometry",
                severity="BLOCKER",
                object_ids=object_ids,
            )
        ]
    if not is_positive(numeric_width) or numeric_offset < -DEFAULT_TOLERANCES.linear:
        return [
            finding(
                rule="OPENING_POSITIVE_SPAN",
                message="opening offset must be non-negative and width positive",
                severity="BLOCKER",
                object_ids=object_ids,
            )
        ]
    if numeric_offset + numeric_width > length + DEFAULT_TOLERANCES.linear:
        return [
            finding(
                rule="OPENING_WITHIN_HOST_WALL",
                message="opening span exceeds the selected host wall",
                severity="BLOCKER",
                object_ids=object_ids,
                evidence={"wallLength": length, "offset": numeric_offset, "width": numeric_width},
            )
        ]
    return []


def quick_validate(model: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate only invariants touched by the phase-two command layer."""

    findings: list[dict[str, Any]] = []
    for space in model.get("spaces", []):
        findings.extend(validate_space_geometry(space.get("geometry", {}).get("rect"), space.get("id")))
        findings.extend(validate_level_reference(model, space.get("levelId")))
    for collection in ("openings", "windows"):
        for opening in model.get(collection, []):
            geometry = opening.get("geometry", {})
            findings.extend(
                validate_opening_position(
                    model,
                    host_space_id=opening.get("hostSpace"),
                    wall=opening.get("wall"),
                    offset=geometry.get("offset"),
                    width=geometry.get("width"),
                    object_id=opening.get("id"),
                )
            )
    return findings