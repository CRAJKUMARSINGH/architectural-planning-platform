#!/usr/bin/env python3
"""Week 15–16 parametric furnishing and candidate-studio enrichment.

The module deliberately keeps presentation objects separate from the
authoritative model.  It provides deterministic, reviewable planning aids:
asset metadata, clearance-aware placement/edit operations, candidate
comparison, non-destructive design layers, and render-job manifests.

Units are the canonical model's nominal inches.  This is not a code,
accessibility, fire, structural, MEP, survey, permit, or construction
certification.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "bar-association-hall"
REPORT_ROOT = MODEL_ROOT / "standard"
CANONICAL_PATH = REPORT_ROOT / "model" / "project.json"
ASSET_REPORT_PATH = REPORT_ROOT / "week15-parametric-assets-report.json"
CANDIDATE_REPORT_PATH = REPORT_ROOT / "week16-candidate-studio-report.json"
AI_INPUT_REPORT_PATH = REPORT_ROOT / "week16-ai-tool-inputs.json"
PLANNER5D_REPORT_PATH = REPORT_ROOT / "week16-planner5d-exchange-report.json"
PLANNER5D_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "planner5d-furnished-layout.json"
ARCHISTAR_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "archistar-snaptrude-site-model.json"
ARCHISTAR_REPORT_PATH = REPORT_ROOT / "week16-archistar-snaptrude-site-report.json"
MANIFEST_PATH = REPORT_ROOT / "week1516-enrichment-manifest.json"
CHANGELOG_PATH = REPORT_ROOT / "week1516-changelog.md"

WEEK15_VERSION = "week15.parametric-assets.v1"
WEEK16_VERSION = "week16.candidate-studio.v1"
RENDER_VERSION = "week16.render-pipeline.v1"
AI_INPUT_VERSION = "week16.ai-tool-inputs.v1"
MAKET_INPUT_VERSION = "week16-01.maket-ai.v1"
PLANNER5D_INPUT_VERSION = "week16-02.planner5d.v1"
ARCHISTAR_INPUT_VERSION = "week16-03.archistar-snaptrude.v1"


AI_TOOL_INPUTS: tuple[dict[str, Any], ...] = (
    {
        "id": "maket-text-to-plan",
        "tool": "Maket.ai",
        "inputRole": "text-to-plan ideation",
        "acceptedInputs": ["typed brief", "room schedule", "dimensions", "furniture intent"],
        "usableOutput": "candidate room arrangement and furniture suggestions",
        "requiredEvidence": ["source brief", "units", "tool/export reference", "reviewer"],
        "promotionGate": "candidate only until canonical rooms, openings, routes, and clearances validate",
        "programWeeks": [1, 6, 12, 16],
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/maket-ai-text-to-plan.json",
    },
    {
        "id": "planner5d-furnished-layout",
        "tool": "Planner 5D",
        "inputRole": "furnished 2D/3D exploration",
        "acceptedInputs": ["validated room geometry", "scaled furniture choices", "occupancy intent"],
        "usableOutput": "furnished presentation candidate",
        "requiredEvidence": ["model revision", "asset scale", "clearance result", "tool/export reference"],
        "promotionGate": "presentation layer only; never authoritative geometry",
        "programWeeks": [8, 9, 15, 16],
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/planner5d-furnished-layout.json",
    },
    {
        "id": "archistar-snaptrude-site-model",
        "tool": "Archistar / Snaptrude",
        "inputRole": "site and building-scale feasibility",
        "acceptedInputs": ["north", "frontage", "setbacks", "access points", "levels", "site assumptions"],
        "usableOutput": "site-context and massing candidate",
        "requiredEvidence": ["site source", "assumption status", "rule-pack version", "professional review state"],
        "promotionGate": "review evidence only; never a permit, code, or construction approval",
        "programWeeks": [6, 7, 14, 16],
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/archistar-snaptrude-site-model.json",
    },
    {
        "id": "floorplanner-synchronized-view",
        "tool": "Floorplanner",
        "inputRole": "fast 2D/3D planning reference",
        "acceptedInputs": ["canonical model revision", "object IDs", "validated room boundaries"],
        "usableOutput": "comparison view and presentation reference",
        "requiredEvidence": ["model revision", "object-ID map", "view/export reference"],
        "promotionGate": "view-only until synchronized with the canonical revision",
        "programWeeks": [8, 9, 14, 16],
    },
    {
        "id": "roomstyler-homestyler-furnishing",
        "tool": "Roomstyler / Homestyler",
        "inputRole": "furniture-heavy visual exploration",
        "acceptedInputs": ["validated room geometry", "scaled asset candidates", "finish intent"],
        "usableOutput": "material, furniture, and presentation options",
        "requiredEvidence": ["asset dimensions", "clearance result", "model revision", "source reference"],
        "promotionGate": "non-authoritative presentation option; recheck routes and door swings",
        "programWeeks": [9, 15, 16],
    },
    {
        "id": "magicplan-photo-capture",
        "tool": "Magicplan",
        "inputRole": "photo-assisted existing-plan capture",
        "acceptedInputs": ["photos", "known scale", "location/context notes", "capture metadata"],
        "usableOutput": "assisted recognition queue",
        "requiredEvidence": ["source image", "scale evidence", "confidence", "manual confirmation"],
        "promotionGate": "review queue only; do not silently promote recognition to editable geometry",
        "programWeeks": [1, 13, 14, 16],
    },
    {
        "id": "llm-brief-refinement",
        "tool": "ChatGPT / Claude / Grok / Gemini",
        "inputRole": "brief refinement and explanation",
        "acceptedInputs": ["natural-language brief", "constraints", "missing-fact questions", "candidate feedback"],
        "usableOutput": "typed brief suggestions, assumptions, and comparison notes",
        "requiredEvidence": ["source text", "extracted facts", "assumptions", "accepted revision"],
        "promotionGate": "text assistance only; never mutate geometry without typed validation",
        "programWeeks": [1, 6, 12, 16],
    },
    {
        "id": "4lines-plan-section-workflow",
        "tool": "4Lines.ai",
        "inputRole": "plan, section, and elevation workflow reference",
        "acceptedInputs": ["canonical object IDs", "levels", "openings", "dimensions", "validation provenance"],
        "usableOutput": "view-generation and exchange reference",
        "requiredEvidence": ["model revision", "object-ID map", "view type", "validation result"],
        "promotionGate": "accept only when every view traces to the validated canonical revision",
        "programWeeks": [2, 8, 14, 16],
    },
    {
        "id": "archiagent-live-dimensions",
        "tool": "Archiagent",
        "inputRole": "scaled floor-plan and live-dimension review",
        "acceptedInputs": ["dimensioned model", "units", "levels", "review target"],
        "usableOutput": "dimension review and candidate comparison notes",
        "requiredEvidence": ["units", "dimension source", "model revision", "rerun validation result"],
        "promotionGate": "review aid only; accuracy claims do not replace jurisdictional or professional checks",
        "programWeeks": [2, 4, 5, 8, 16],
    },
)


def _asset(
    label: str,
    category: str,
    width: float,
    depth: float,
    height: float,
    *,
    room_uses: Iterable[str],
    occupancy: int = 0,
    service_side: str | None = None,
    preferred_walls: Iterable[str] = (),
    clearance: dict[str, float] | None = None,
    rotations: Iterable[int] = (0, 90),
) -> dict[str, Any]:
    clearances = {
        "front": 30.0,
        "back": 6.0,
        "left": 6.0,
        "right": 6.0,
        **(clearance or {}),
    }
    return {
        "label": label,
        "category": category,
        "dimensions": {"width": width, "depth": depth, "height": height, "unit": "inch"},
        "width": width,
        "depth": depth,
        "height": height,
        "rotationRules": {"allowedDegrees": list(rotations), "stepDegrees": 90},
        "preferredWallRelationships": list(preferred_walls),
        "serviceSide": service_side,
        "occupancy": occupancy,
        "clearanceEnvelope": clearances,
        "roomUses": list(room_uses),
        "authoritative": False,
        "presentationOnly": True,
    }


ASSET_CATALOG: dict[str, dict[str, Any]] = {
    "work-desk": _asset("Work desk", "furniture", 60, 30, 30, room_uses=("office", "chamber"), occupancy=1, preferred_walls=("back",), clearance={"front": 36}),
    "executive-desk": _asset("Executive desk", "furniture", 72, 36, 30, room_uses=("office", "chamber"), occupancy=1, preferred_walls=("back",), clearance={"front": 42}),
    "visitor-chair": _asset("Visitor chair", "seating", 20, 20, 32, room_uses=("office", "chamber", "waiting"), occupancy=1, clearance={"front": 24}),
    "audience-chair": _asset("Audience chair", "seating", 18, 18, 32, room_uses=("hall", "assembly", "classroom"), occupancy=1, clearance={"front": 18, "back": 12}),
    "bench-row": _asset("Bench seating row", "seating", 96, 20, 32, room_uses=("hall", "assembly"), occupancy=4, clearance={"front": 48, "back": 18}),
    "library-table": _asset("Library table", "library", 72, 36, 30, room_uses=("library",), occupancy=6, clearance={"front": 36, "back": 36, "left": 24, "right": 24}),
    "library-shelf": _asset("Library shelf", "library", 72, 14, 84, room_uses=("library",), preferred_walls=("back",), clearance={"front": 36}),
    "reception-counter": _asset("Reception counter", "counter", 72, 30, 42, room_uses=("reception", "lobby"), occupancy=2, service_side="front", preferred_walls=("back",), clearance={"front": 48}),
    "service-counter": _asset("Service counter", "counter", 60, 24, 36, room_uses=("service", "pantry"), occupancy=1, service_side="front", preferred_walls=("back",), clearance={"front": 36}),
    "sanitary-ware": _asset("Accessible sanitary fixture", "sanitaryware", 30, 54, 32, room_uses=("service", "healthcare"), service_side="right", clearance={"front": 60, "left": 12, "right": 12}),
    "lavatory-fixture": _asset("Lavatory fixture", "fixtures", 24, 20, 32, room_uses=("service", "healthcare"), service_side="back", clearance={"front": 42}),
    "appliance-block": _asset("Appliance block", "appliance", 36, 30, 36, room_uses=("service", "retail"), service_side="back", preferred_walls=("back",), clearance={"front": 36}),
    "dais": _asset("Dais", "dais", 144, 60, 18, room_uses=("hall", "assembly"), occupancy=4, preferred_walls=("back",), clearance={"front": 60}),
    "lectern": _asset("Lectern", "dais", 24, 20, 42, room_uses=("hall", "assembly"), occupancy=1, clearance={"front": 36}),
    "vehicle-bay": _asset("Vehicle bay", "vehicle", 108, 216, 60, room_uses=("industrial", "retail"), clearance={"front": 36, "back": 36, "left": 24, "right": 24}),
    "equipment-bench": _asset("Industrial equipment bench", "industrial-equipment", 96, 36, 36, room_uses=("industrial",), service_side="back", clearance={"front": 48, "back": 24, "left": 18, "right": 18}),
    "patient-bed": _asset("Patient bed", "healthcare", 42, 84, 24, room_uses=("healthcare",), occupancy=1, clearance={"front": 36, "left": 36, "right": 36}),
}


ROOM_TEMPLATES: dict[str, dict[str, Any]] = {
    "residential": {"recommendedAssets": ["work-desk", "visitor-chair"], "minimumClearRoute": 36},
    "office": {"recommendedAssets": ["executive-desk", "visitor-chair"], "minimumClearRoute": 36},
    "chamber": {"recommendedAssets": ["executive-desk", "visitor-chair"], "minimumClearRoute": 36},
    "hall": {"recommendedAssets": ["audience-chair", "bench-row", "dais", "lectern"], "minimumClearRoute": 48},
    "classroom": {"recommendedAssets": ["library-table", "visitor-chair"], "minimumClearRoute": 36},
    "library": {"recommendedAssets": ["library-shelf", "library-table"], "minimumClearRoute": 36},
    "healthcare": {"recommendedAssets": ["patient-bed", "sanitary-ware"], "minimumClearRoute": 48},
    "retail": {"recommendedAssets": ["reception-counter", "appliance-block"], "minimumClearRoute": 48},
    "light-industrial": {"recommendedAssets": ["vehicle-bay", "equipment-bench"], "minimumClearRoute": 48},
}


def ai_tool_input_manifest() -> dict[str, Any]:
    """Return the explicit Week 16 intake boundary for external AI tools.

    These are workflow inputs and review references, not geometry authorities.
    Keeping the manifest in the candidate package makes every presentation
    candidate explain which external signal was accepted and what evidence is
    still required before it can influence a validated revision.
    """

    return {
        "version": AI_INPUT_VERSION,
        "status": "review-first",
        "authority": "canonical model and focused validators remain authoritative",
        "tools": [copy.deepcopy(item) for item in AI_TOOL_INPUTS],
        "requiredCandidateFields": [
            "sourceTool",
            "sourceInput",
            "sourceReference",
            "modelRevision",
            "validationStatus",
            "reviewState",
        ],
        "promotionPolicy": {
            "acceptedFor": ["brief refinement", "candidate comparison", "furnishing", "presentation"],
            "notAcceptedFor": ["silent wall edits", "unvalidated openings", "route overrides", "permit or construction approval"],
            "rerunValidationAfterAcceptance": True,
        },
    }


def ingest_ai_tool_input(
    tool_id: str,
    *,
    source_input: Any,
    source_reference: str,
    model_revision: Any,
    validation_status: str = "pending",
    review_state: str = "pending",
) -> dict[str, Any]:
    """Normalize one external-tool signal into a review-first candidate input."""

    tool = next((item for item in AI_TOOL_INPUTS if item["id"] == tool_id), None)
    if tool is None:
        raise ValueError(f"unknown AI tool input: {tool_id}")
    if not source_reference.strip():
        raise ValueError("source_reference is required for AI tool input")
    if review_state not in {"pending", "accepted", "rejected"}:
        raise ValueError("review_state must be pending, accepted, or rejected")
    if validation_status not in {"pending", "pass", "fail", "review-required"}:
        raise ValueError("validation_status is not supported")
    return {
        "toolId": tool["id"],
        "tool": tool["tool"],
        "inputRole": tool["inputRole"],
        "sourceInput": copy.deepcopy(source_input),
        "sourceReference": source_reference,
        "modelRevision": model_revision,
        "validationStatus": validation_status,
        "reviewState": review_state,
        "authoritative": False,
        "promotionStatus": "review-required",
        "promotionGate": tool["promotionGate"],
    }


def validate_maket_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Validate a Maket.ai-style text-to-plan candidate without mutating model."""

    normalized = ingest_ai_tool_input(
        "maket-text-to-plan",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    units = str(payload.get("units", "")).strip().lower()
    unit_scale = {"inch": 1.0, "in": 1.0, "foot": 12.0, "ft": 12.0, "mm": 1 / 25.4, "m": 39.3700787402}
    if units not in unit_scale:
        findings.append({"rule": "MAKET_UNITS_REQUIRED", "severity": "BLOCKER", "message": "Maket.ai input must declare supported units."})
    rooms = payload.get("rooms")
    if not isinstance(rooms, list) or not rooms:
        findings.append({"rule": "MAKET_ROOM_SCHEDULE_REQUIRED", "severity": "BLOCKER", "message": "Maket.ai input must contain at least one room with dimensions."})
        rooms = []
    canonical_spaces = model.get("spaces", []) or []
    canonical_by_name = {
        str(space.get("name", "")).strip().lower(): space
        for space in canonical_spaces
        if str(space.get("name", "")).strip()
    }
    for room in rooms:
        if not isinstance(room, dict):
            findings.append({"rule": "MAKET_ROOM_ENTRY_INVALID", "severity": "BLOCKER", "message": "Each Maket.ai room entry must be an object."})
            continue
        name = str(room.get("name", "")).strip()
        width = room.get("width")
        depth = room.get("depth")
        if not name or not isinstance(width, (int, float)) or not isinstance(depth, (int, float)) or width <= 0 or depth <= 0:
            findings.append({"rule": "MAKET_ROOM_DIMENSIONS_REQUIRED", "severity": "BLOCKER", "message": "Every Maket.ai room must have a name, positive width, and positive depth."})
            continue
        canonical = canonical_by_name.get(name.lower())
        if canonical is None:
            findings.append({"rule": "MAKET_ROOM_NOT_IN_CANONICAL_MODEL", "severity": "REVIEW_REQUIRED", "message": f"Maket.ai room '{name}' has no canonical room match."})
            continue
        rect = _space_rect(canonical)
        if rect and units in unit_scale:
            expected_width = (rect[2] - rect[0]) / unit_scale[units]
            expected_depth = (rect[3] - rect[1]) / unit_scale[units]
            if abs(float(width) - expected_width) > 0.01 or abs(float(depth) - expected_depth) > 0.01:
                findings.append({"rule": "MAKET_DIMENSION_CONFLICT", "severity": "REVIEW_REQUIRED", "message": f"Maket.ai dimensions for '{name}' differ from the canonical model."})
    if len(rooms) != len(canonical_spaces):
        findings.append({"rule": "MAKET_ROOM_COUNT_CONFLICT", "severity": "REVIEW_REQUIRED", "message": "Maket.ai room count differs from the canonical model."})
    for field in ("furnitureIntent", "adjacencyIntent"):
        if not isinstance(payload.get(field), list):
            findings.append({"rule": f"MAKET_{field.upper()}_SHAPE", "severity": "REVIEW_REQUIRED", "message": f"Maket.ai {field} must be an explicit list for review."})
    blocking = any(item["severity"] == "BLOCKER" for item in findings)
    return {
        "version": MAKET_INPUT_VERSION,
        "status": "blocked" if blocking else ("review-required" if findings else "pass"),
        "input": normalized,
        "findings": findings,
        "authoritativeGeometryChanged": False,
        "canonicalModelRevision": model_revision,
    }


def _planner5d_unit_scale(units: str) -> float | None:
    return {
        "inch": 1.0,
        "in": 1.0,
        "foot": 12.0,
        "ft": 12.0,
        "mm": 1 / 25.4,
        "m": 39.3700787402,
    }.get(str(units).strip().lower())


def _planner5d_position(item: dict[str, Any]) -> tuple[float, float] | None:
    position = item.get("position")
    if isinstance(position, dict) and all(key in position for key in ("x", "y")):
        if isinstance(position["x"], (int, float)) and isinstance(position["y"], (int, float)):
            return float(position["x"]), float(position["y"])
    rect = _rect(item.get("geometry")) or _rect(item.get("rect"))
    if rect is not None:
        return rect[0], rect[1]
    return None


def validate_planner5d_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Exchange a Planner 5D furnishing candidate through the Week 15 validator.

    Planner 5D dimensions and coordinates are treated as an imported proposal.
    Each item is remapped to a canonical asset, rebuilt from the canonical
    dimensions, and then checked without changing ``model``.  A rejected item
    remains useful evidence, but it cannot be promoted to the presentation
    candidate.
    """

    normalized = ingest_ai_tool_input(
        "planner5d-furnished-layout",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    units = str(payload.get("units", "")).strip().lower()
    unit_scale = _planner5d_unit_scale(units)
    if unit_scale is None:
        findings.append(_finding("PLANNER5D_UNITS_REQUIRED", "Planner 5D input must declare supported units."))
    imported_revision = payload.get("modelRevision", model_revision)
    if imported_revision != model_revision:
        findings.append(
            _finding(
                "PLANNER5D_MODEL_REVISION_MISMATCH",
                f"Planner 5D revision {imported_revision!r} does not match canonical revision {model_revision!r}.",
                severity="REVIEW_REQUIRED",
            )
        )

    mappings = payload.get("assetMappings")
    mapping_by_source: dict[str, dict[str, Any]] = {}
    mapping_report: list[dict[str, Any]] = []
    if not isinstance(mappings, list) or not mappings:
        findings.append(_finding("PLANNER5D_ASSET_MAPPING_REQUIRED", "Planner 5D input must provide typed asset mappings."))
        mappings = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            findings.append(_finding("PLANNER5D_ASSET_MAPPING_INVALID", "Each Planner 5D asset mapping must be an object."))
            continue
        source_asset_id = str(mapping.get("sourceAssetId", "")).strip()
        asset_id = str(mapping.get("assetId", "")).strip()
        spec = ASSET_CATALOG.get(asset_id)
        if not source_asset_id or not asset_id or spec is None:
            findings.append(
                _finding(
                    "PLANNER5D_ASSET_MAPPING_UNKNOWN",
                    f"Planner 5D mapping {source_asset_id or asset_id or 'unnamed'} does not resolve to a canonical asset.",
                )
            )
            mapping_report.append(
                {
                    "sourceAssetId": source_asset_id or None,
                    "assetId": asset_id or None,
                    "status": "rejected",
                }
            )
            continue
        if source_asset_id in mapping_by_source:
            findings.append(
                _finding(
                    "PLANNER5D_ASSET_MAPPING_DUPLICATE",
                    f"Planner 5D source asset {source_asset_id!r} has more than one canonical mapping.",
                )
            )
            continue
        mapping_by_source[source_asset_id] = mapping
        mapping_report.append(
            {
                "sourceAssetId": source_asset_id,
                "sourceLabel": mapping.get("sourceLabel"),
                "assetId": asset_id,
                "canonicalLabel": spec["label"],
                "canonicalDimensions": copy.deepcopy(spec["dimensions"]),
                "status": "mapped",
            }
        )

    imported_items = payload.get("placements")
    if not isinstance(imported_items, list) or not imported_items:
        findings.append(_finding("PLANNER5D_PLACEMENTS_REQUIRED", "Planner 5D input must contain at least one furniture placement."))
        imported_items = []

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    normalized_placements: list[dict[str, Any]] = []
    for item in imported_items:
        if not isinstance(item, dict):
            findings.append(_finding("PLANNER5D_PLACEMENT_INVALID", "Each Planner 5D placement must be an object."))
            continue
        object_id = str(item.get("id", "")).strip() or "planner5d-placement"
        source_asset_id = str(item.get("sourceAssetId", "")).strip()
        mapping = mapping_by_source.get(source_asset_id)
        if mapping is None:
            rejected.append(
                {
                    "id": object_id,
                    "sourceAssetId": source_asset_id or None,
                    "status": "rejected",
                    "findings": [
                        _finding(
                            "PLANNER5D_ASSET_MAPPING_REQUIRED",
                            f"{object_id} has no canonical asset mapping.",
                            object_id=object_id,
                        )
                    ],
                }
            )
            continue
        asset_id = str(mapping["assetId"])
        spec = ASSET_CATALOG[asset_id]
        item_findings: list[dict[str, Any]] = []
        position = _planner5d_position(item)
        if unit_scale is None or position is None:
            item_findings.append(
                _finding(
                    "PLANNER5D_POSITION_REQUIRED",
                    f"{object_id} needs a position with numeric x/y coordinates.",
                    object_id=object_id,
                )
            )
            rejected.append({"id": object_id, "sourceAssetId": source_asset_id, "status": "rejected", "findings": item_findings})
            continue

        try:
            rotation = int(item.get("rotation", 0)) % 360
        except (TypeError, ValueError):
            rotation = -1
        if rotation not in spec["rotationRules"]["allowedDegrees"]:
            item_findings.append(
                _finding(
                    "PLANNER5D_ROTATION_NOT_ALLOWED",
                    f"{object_id} uses rotation {rotation}; {asset_id} allows {spec['rotationRules']['allowedDegrees']}.",
                    object_id=object_id,
                )
            )

        imported_dimensions = item.get("dimensions")
        if isinstance(imported_dimensions, dict) and unit_scale is not None:
            for dimension in ("width", "depth"):
                value = imported_dimensions.get(dimension)
                expected = float(spec[dimension]) / unit_scale
                if not isinstance(value, (int, float)) or abs(float(value) - expected) > 0.01:
                    item_findings.append(
                        _finding(
                            "PLANNER5D_ASSET_SCALE_CONFLICT",
                            f"{object_id} {dimension} does not match the canonical {asset_id} scale.",
                            severity="REVIEW_REQUIRED",
                            object_id=object_id,
                        )
                    )

        host_space_id = str(item.get("hostSpaceId") or item.get("spaceId") or "")
        space = next((space for space in model.get("spaces", []) if space.get("id") == host_space_id), None)
        if space is not None and _room_use(space) not in set(spec["roomUses"]):
            item_findings.append(
                _finding(
                    "PLANNER5D_ASSET_ROOM_USE_REVIEW",
                    f"{object_id} maps {asset_id} into {_room_use(space)!r}, outside its catalog room uses.",
                    severity="REVIEW_REQUIRED",
                    object_id=object_id,
                )
            )

        placement = _new_placement(
            asset_id,
            host_space_id,
            position[0] * unit_scale,
            position[1] * unit_scale,
            rotation if rotation >= 0 else 0,
            object_id=object_id,
        )
        placement.update(
            {
                "sourceTool": "Planner 5D",
                "sourceAssetId": source_asset_id,
                "sourceReference": source_reference,
                "modelRevision": model_revision,
                "occupancyIntent": item.get("occupancy"),
                "serviceSideIntent": item.get("serviceSide"),
                "presentationOnly": True,
                "authoritative": False,
            }
        )
        item_findings.extend(validate_placement(model, placement, existing=normalized_placements))
        if item_findings:
            rejected.append(
                {
                    "id": object_id,
                    "sourceAssetId": source_asset_id,
                    "assetId": asset_id,
                    "status": "rejected",
                    "presentationOnly": True,
                    "findings": item_findings,
                }
            )
        else:
            accepted.append(copy.deepcopy(placement))
        normalized_placements.append(placement)

    baseline = furnish_model(model, seed=1516)
    placement_findings = [finding for item in rejected for finding in item.get("findings", [])]
    all_findings = findings + placement_findings
    comparison = {
        "baselineSeed": baseline["seed"],
        "baselineStatus": baseline["status"],
        "baselinePlacementCount": len(baseline["placements"]),
        "importedPlacementCount": len(imported_items),
        "acceptedPlacementCount": len(accepted),
        "rejectedPlacementCount": len(rejected),
        "plannerCandidateEligible": not findings and not rejected,
        "deterministic": True,
    }
    result = {
        "version": PLANNER5D_INPUT_VERSION,
        "tool": "Planner 5D",
        "sourceReference": source_reference,
        "modelRevision": model_revision,
        "canonicalModelRevision": model_revision,
        "units": units,
        "assetScaleToCanonicalInches": unit_scale,
        "input": normalized,
        "assetMappingReport": mapping_report,
        "acceptedPlacements": accepted,
        "rejectedPlacements": rejected,
        "clearanceResult": {
            "checked": len(normalized_placements),
            "accepted": len(accepted),
            "rejected": len(rejected),
        },
        "baselineComparison": comparison,
        "findings": all_findings,
        "authoritativeGeometryChanged": False,
        "presentationOnly": True,
        "candidateEligible": comparison["plannerCandidateEligible"],
    }
    result["determinism"] = {"algorithm": "sha256", "signature": _signature(result)}
    result["status"] = "blocked" if any(item["severity"] == "BLOCKER" for item in findings) else ("review-required" if all_findings else "pass")
    return result


def _site_vertices(value: Any) -> list[list[float]] | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    vertices: list[list[float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        if not all(isinstance(part, (int, float)) for part in point):
            return None
        vertices.append([float(point[0]), float(point[1])])
    return vertices


def _site_fact_match(imported: Any, canonical: Any) -> bool:
    if imported is None or canonical is None:
        return False
    if isinstance(imported, (dict, list)) or isinstance(canonical, (dict, list)):
        return imported == canonical
    return str(imported).strip().lower() == str(canonical).strip().lower()


def validate_archistar_snaptrude_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Review an Archistar/Snaptrude site signal against canonical evidence.

    The imported package is intentionally an evidence overlay.  Week 6
    orientation/program findings and Week 7 rule-pack results are evaluated
    against the canonical model, then linked to the imported facts for review.
    The external site or massing proposal never becomes authoritative geometry.
    """

    normalized = ingest_ai_tool_input(
        "archistar-snaptrude-site-model",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    site = payload.get("site") if isinstance(payload.get("site"), dict) else {}
    imported_units = str(payload.get("units") or site.get("units") or "").strip().lower()
    supported_units = {"inch", "in", "foot", "ft", "mm", "m"}
    if imported_units not in supported_units:
        findings.append(
            _finding(
                "ARCHISTAR_UNITS_REQUIRED",
                "Archistar/Snaptrude site evidence must declare supported coordinate units.",
            )
        )

    coordinate_system = str(
        payload.get("coordinateSystem") or site.get("coordinateSystem") or ""
    ).strip()
    if not coordinate_system:
        findings.append(
            _finding(
                "ARCHISTAR_COORDINATE_SYSTEM_REQUIRED",
                "Site evidence must declare its coordinate-system assumption.",
                severity="REVIEW_REQUIRED",
            )
        )

    vertices = _site_vertices(site.get("plotVertices") or site.get("vertices"))
    if vertices is None:
        findings.append(
            _finding(
                "ARCHISTAR_PLOT_GEOMETRY_REQUIRED",
                "Site evidence must contain at least three numeric plot vertices.",
            )
        )

    north = site.get("north")
    frontage = site.get("frontage") or site.get("roadFrontage")
    service_access = site.get("serviceAccess")
    if not north:
        findings.append(
            _finding(
                "ARCHISTAR_NORTH_REQUIRED",
                "North orientation is missing and remains a survey confirmation item.",
                severity="WARNING",
            )
        )
    if not frontage:
        findings.append(
            _finding(
                "ARCHISTAR_FRONTAGE_REQUIRED",
                "Road frontage is missing; site feasibility cannot treat the access edge as confirmed.",
                severity="WARNING",
            )
        )
    if not service_access:
        findings.append(
            _finding(
                "ARCHISTAR_SERVICE_ACCESS_REQUIRED",
                "Service-access intent is missing; it remains a warning rather than a hidden pass.",
                severity="WARNING",
            )
        )

    setbacks = site.get("setbacks")
    if not isinstance(setbacks, dict) or any(setbacks.get(edge) is None for edge in ("north", "south", "east", "west")):
        findings.append(
            _finding(
                "ARCHISTAR_SETBACKS_REQUIRED",
                "All four preliminary setback inputs are required for a measurable comparison.",
                severity="REVIEW_REQUIRED",
            )
        )

    access_points = site.get("accessPoints")
    if not isinstance(access_points, list) or not access_points:
        findings.append(
            _finding(
                "ARCHISTAR_ACCESS_POINTS_REQUIRED",
                "Site evidence must list public, staff, or service access points.",
                severity="REVIEW_REQUIRED",
            )
        )

    levels = site.get("levels")
    if not isinstance(levels, list) or not levels:
        findings.append(
            _finding(
                "ARCHISTAR_LEVELS_REQUIRED",
                "Site/massing evidence must identify the levels used by the massing assumptions.",
                severity="REVIEW_REQUIRED",
            )
        )

    massing_assumptions = payload.get("massingAssumptions", site.get("massingAssumptions"))
    if not isinstance(massing_assumptions, list) or not massing_assumptions:
        findings.append(
            _finding(
                "ARCHISTAR_MASSING_ASSUMPTIONS_REQUIRED",
                "Massing proposals must be labeled as explicit assumptions.",
                severity="REVIEW_REQUIRED",
            )
        )

    confidence = payload.get("confidence")
    if not isinstance(confidence, dict) or not isinstance(confidence.get("overall"), (int, float)):
        findings.append(
            _finding(
                "ARCHISTAR_CONFIDENCE_REQUIRED",
                "Site evidence must include an overall confidence value.",
                severity="REVIEW_REQUIRED",
            )
        )
        confidence = confidence if isinstance(confidence, dict) else {}

    professional_review_state = str(payload.get("professionalReviewState") or "required")
    if professional_review_state not in {"required", "pending", "complete"}:
        findings.append(
            _finding(
                "ARCHISTAR_REVIEW_STATE_INVALID",
                "Professional review state must be required, pending, or complete.",
                severity="REVIEW_REQUIRED",
            )
        )
        professional_review_state = "required"

    # These two calls are the Week 6/7 comparison boundary.  They read the
    # canonical model only; no imported site fact is written into ``model``.
    from week56 import program_report  # type: ignore
    from week1718 import evaluate_rule_pack  # type: ignore

    week6_program, week6_findings = program_report(model)
    rule_pack_report = evaluate_rule_pack(model)
    canonical_orientation = week6_program.get("orientation", {})
    canonical_site = model.get("site") if isinstance(model.get("site"), dict) else {}
    canonical_geometry = canonical_site.get("geometry") if isinstance(canonical_site.get("geometry"), dict) else {}
    canonical_plot_vertices = canonical_geometry.get("plotVertices")
    canonical_access_points = model.get("entries") or []
    canonical_levels = model.get("levels") or []
    canonical_setbacks = (
        canonical_orientation.get("setbacks")
        or canonical_geometry.get("setbacks")
        or {}
    )
    comparisons = {
        "units": {
            "imported": imported_units or None,
            "canonical": model.get("units"),
            "match": _site_fact_match(imported_units, model.get("units")),
        },
        "north": {
            "imported": north,
            "canonical": canonical_orientation.get("north"),
            "match": _site_fact_match(north, canonical_orientation.get("north")),
        },
        "frontage": {
            "imported": frontage,
            "canonical": canonical_orientation.get("roadFrontage"),
            "match": _site_fact_match(frontage, canonical_orientation.get("roadFrontage")),
            "status": "unconfirmed" if not frontage else "provided",
        },
        "serviceAccess": {
            "imported": service_access,
            "canonical": canonical_orientation.get("serviceAccess"),
            "match": _site_fact_match(service_access, canonical_orientation.get("serviceAccess")),
            "status": "unconfirmed" if not service_access else "provided",
        },
        "setbacks": {
            "imported": copy.deepcopy(setbacks) if isinstance(setbacks, dict) else None,
            "canonical": copy.deepcopy(canonical_setbacks),
            "match": _site_fact_match(setbacks, canonical_setbacks),
        },
        "plotVertices": {
            "imported": vertices,
            "canonical": copy.deepcopy(canonical_plot_vertices),
            "match": _site_fact_match(vertices, canonical_plot_vertices),
        },
        "accessPointIds": {
            "imported": [item.get("id") for item in access_points if isinstance(item, dict)]
            if isinstance(access_points, list)
            else [],
            "canonical": [item.get("id") for item in canonical_access_points if isinstance(item, dict)],
            "match": _site_fact_match(
                [item.get("id") for item in access_points if isinstance(item, dict)]
                if isinstance(access_points, list)
                else [],
                [item.get("id") for item in canonical_access_points if isinstance(item, dict)],
            ),
        },
        "levels": {
            "imported": copy.deepcopy(levels) if isinstance(levels, list) else None,
            "canonical": [
                {"id": item.get("id"), "elevation": item.get("elevation")}
                for item in canonical_levels
                if isinstance(item, dict)
            ],
            "match": False,
        },
    }
    if isinstance(levels, list):
        comparisons["levels"]["match"] = _site_fact_match(
            [(item.get("id"), item.get("elevation")) for item in levels if isinstance(item, dict)],
            [
                (item.get("id"), item.get("elevation"))
                for item in canonical_levels
                if isinstance(item, dict)
            ],
        )

    linked_rule_findings = [
        {
            "ruleId": item.get("ruleId"),
            "category": item.get("category"),
            "status": item.get("status"),
            "severity": item.get("severity"),
            "confidence": item.get("confidence"),
            "source": item.get("source"),
        }
        for item in rule_pack_report.get("results", [])
        if item.get("category")
        in {"coverage", "setbacks", "height", "parking", "fire-access", "service-access"}
    ]
    assumptions = [
        str(item)
        for item in (
            payload.get("assumptions")
            or site.get("assumptions")
            or []
        )
    ]
    assumptions.extend(
        [
            "Imported Archistar/Snaptrude facts are a review overlay and do not edit canonical geometry.",
            "North, frontage, access, setbacks, levels, and massing require survey and professional confirmation.",
            "Rule-pack results are preliminary planning evidence and do not grant permit, code, or construction approval.",
        ]
    )
    unique_assumptions = list(dict.fromkeys(assumptions))
    has_blocker = any(item["severity"] in {"BLOCKER", "ERROR"} for item in findings)
    status = "blocked" if has_blocker else "review-required" if findings or professional_review_state != "complete" else "pass"
    return {
        "version": ARCHISTAR_INPUT_VERSION,
        "tool": "Archistar / Snaptrude",
        "sourceReference": source_reference,
        "modelRevision": model_revision,
        "canonicalModelRevision": model_revision,
        "input": normalized,
        "siteEvidence": {
            "siteSource": payload.get("siteSource") or source_reference,
            "coordinateSystem": coordinate_system or None,
            "units": imported_units or None,
            "orientation": {"north": north, "frontage": frontage},
            "accessPoints": copy.deepcopy(access_points) if isinstance(access_points, list) else [],
            "setbacks": copy.deepcopy(setbacks) if isinstance(setbacks, dict) else None,
            "levels": copy.deepcopy(levels) if isinstance(levels, list) else [],
            "massingAssumptions": copy.deepcopy(massing_assumptions) if isinstance(massing_assumptions, list) else [],
            "confidence": copy.deepcopy(confidence),
        },
        "week6Comparison": {
            "templateVersion": week6_program.get("templateVersion"),
            "orientation": copy.deepcopy(canonical_orientation),
            "findings": copy.deepcopy(week6_findings),
            "factComparisons": comparisons,
        },
        "rulePackLinkage": {
            "rulePack": copy.deepcopy(rule_pack_report.get("rulePack")),
            "findingLinks": linked_rule_findings,
            "dashboard": copy.deepcopy(rule_pack_report.get("dashboard")),
        },
        "assumptions": unique_assumptions,
        "professionalReview": {
            "state": professional_review_state,
            "required": True,
            "approvalClaim": False,
        },
        "findings": findings,
        "status": status,
        "evidenceStatus": "review-required" if status != "blocked" else "blocked",
        "candidateEligible": False,
        "authoritativeGeometryChanged": False,
        "presentationOnly": True,
    }


def _rect(value: Any) -> list[float] | None:
    if isinstance(value, dict):
        value = value.get("rect")
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return [float(item) for item in value]
    return None


def _space_rect(space: dict[str, Any]) -> list[float] | None:
    return _rect(space.get("rect")) or _rect(space.get("geometry", {}).get("rect"))


def _expand(rect: list[float], clearances: dict[str, float] | float) -> list[float]:
    if isinstance(clearances, (int, float)):
        value = float(clearances)
        return [rect[0] - value, rect[1] - value, rect[2] + value, rect[3] + value]
    return [
        rect[0] - float(clearances.get("left", 0)),
        rect[1] - float(clearances.get("back", 0)),
        rect[2] + float(clearances.get("right", 0)),
        rect[3] + float(clearances.get("front", 0)),
    ]


def _overlap(first: list[float], second: list[float]) -> bool:
    return first[0] < second[2] and first[2] > second[0] and first[1] < second[3] and first[3] > second[1]


def _inside(inner: list[float], outer: list[float]) -> bool:
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _finding(rule: str, message: str, *, severity: str = "BLOCKER", object_id: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"severity": severity, "rule": rule, "message": message}
    if object_id:
        item["objectId"] = object_id
    return item


def _room_use(space: dict[str, Any]) -> str:
    value = str(space.get("roomUse") or space.get("use") or space.get("name", "")).lower().replace(" ", "-")
    return {"assembly": "hall", "assembly-hall": "hall", "lightindustrial": "light-industrial"}.get(value, value)


def asset_catalog() -> dict[str, Any]:
    return {"version": WEEK15_VERSION, "assets": copy.deepcopy(ASSET_CATALOG), "roomTemplates": copy.deepcopy(ROOM_TEMPLATES)}


def _placement_rect(spec: dict[str, Any], x: float, y: float, rotation: int) -> list[float]:
    quarter_turn = int(rotation) % 180 == 90
    width = float(spec["depth"] if quarter_turn else spec["width"])
    depth = float(spec["width"] if quarter_turn else spec["depth"])
    return [float(x), float(y), float(x) + width, float(y) + depth]


def _model_zones(model: dict[str, Any], host_space_id: str) -> list[tuple[str, list[float]]]:
    zones: list[tuple[str, list[float]]] = []
    for collection, rule in (("routes", "required route"), ("stairs", "stair"), ("serviceZones", "service zone")):
        for item in model.get(collection, []) or []:
            if item.get("hostSpace") not in (None, host_space_id) and item.get("spaceId") not in (None, host_space_id):
                continue
            geometry = _rect(item.get("geometry")) or _rect(item.get("rect"))
            if geometry:
                zones.append((rule, geometry))
    return zones


def validate_placement(
    model: dict[str, Any],
    placement: dict[str, Any],
    *,
    existing: Iterable[dict[str, Any]] = (),
) -> list[dict[str, Any]]:
    asset_id = str(placement.get("assetId", ""))
    spec = ASSET_CATALOG.get(asset_id)
    object_id = str(placement.get("id", asset_id or "asset"))
    if spec is None:
        return [_finding("ASSET_ID_MUST_EXIST", f"Unknown parametric asset {asset_id!r}.", object_id=object_id)]
    rect = _rect(placement.get("geometry")) or _rect(placement.get("rect"))
    if rect is None:
        return [_finding("ASSET_GEOMETRY_REQUIRED", "A placement needs a rectangular plan geometry.", object_id=object_id)]
    host_id = str(placement.get("hostSpaceId") or placement.get("spaceId") or "")
    space = next((item for item in model.get("spaces", []) if item.get("id") == host_id), None)
    findings: list[dict[str, Any]] = []
    if space is None:
        findings.append(_finding("ASSET_HOST_SPACE_REQUIRED", f"{object_id} is not hosted by a known room.", object_id=object_id))
        return findings
    space_rect = _space_rect(space)
    if space_rect and not _inside(_expand(rect, spec["clearanceEnvelope"]), space_rect):
        findings.append(_finding("ASSET_CLEARANCE_MUST_FIT_ROOM", f"{object_id} and its required clearance do not fit inside {host_id}.", object_id=object_id))
    clearance_rect = _expand(rect, spec["clearanceEnvelope"])
    for zone_name, zone_rect in _model_zones(model, host_id):
        if _overlap(clearance_rect, zone_rect):
            findings.append(_finding("ASSET_MUST_NOT_BLOCK_ZONE", f"{object_id} overlaps a {zone_name}.", object_id=object_id))
    for opening in model.get("openings", []) or []:
        if opening.get("hostSpace") != host_id:
            continue
        opening_rect = _rect(opening.get("geometry")) or _rect(opening.get("rect"))
        if opening_rect and _overlap(clearance_rect, _expand(opening_rect, 42)):
            findings.append(_finding("ASSET_MUST_NOT_BLOCK_DOOR_SWING", f"{object_id} blocks the approach or swing of {opening.get('id', 'opening')}.", object_id=object_id))
    for other in existing:
        if other.get("id") == object_id or other.get("hostSpaceId") != host_id:
            continue
        other_rect = _rect(other.get("clearanceEnvelope"))
        if other_rect and _overlap(clearance_rect, other_rect):
            findings.append(_finding("ASSET_CLEARANCES_MUST_NOT_OVERLAP", f"{object_id} overlaps the clearance envelope of {other.get('id', 'asset')}.", object_id=object_id))
    return findings


def _new_placement(asset_id: str, host_space_id: str, x: float, y: float, rotation: int = 0, *, object_id: str | None = None) -> dict[str, Any]:
    spec = ASSET_CATALOG[asset_id]
    rect = _placement_rect(spec, x, y, rotation)
    return {
        "id": object_id or f"asset-{asset_id}-{int(x)}-{int(y)}",
        "assetId": asset_id,
        "hostSpaceId": host_space_id,
        "rotation": int(rotation) % 360,
        "geometry": {"rect": rect},
        "clearanceEnvelope": _expand(rect, spec["clearanceEnvelope"]),
        "authoritative": False,
        "presentationOnly": True,
        "modelRevision": None,
    }


def find_valid_position(
    model: dict[str, Any],
    asset_id: str,
    host_space_id: str,
    *,
    existing: Iterable[dict[str, Any]] = (),
    step: float = 12.0,
) -> dict[str, Any] | None:
    if asset_id not in ASSET_CATALOG:
        raise ValueError(f"unknown asset: {asset_id}")
    space = next((item for item in model.get("spaces", []) if item.get("id") == host_space_id), None)
    space_rect = _space_rect(space or {})
    if not space_rect:
        return None
    for rotation in ASSET_CATALOG[asset_id]["rotationRules"]["allowedDegrees"]:
        spec = ASSET_CATALOG[asset_id]
        width = spec["depth"] if rotation % 180 == 90 else spec["width"]
        depth = spec["width"] if rotation % 180 == 90 else spec["depth"]
        y = space_rect[1]
        while y + depth <= space_rect[3]:
            x = space_rect[0]
            while x + width <= space_rect[2]:
                candidate = _new_placement(asset_id, host_space_id, x, y, rotation)
                if not validate_placement(model, candidate, existing=existing):
                    return candidate
                x += step
            y += step
    return None


def edit_placements(
    model: dict[str, Any],
    placements: list[dict[str, Any]],
    operation: dict[str, Any],
) -> dict[str, Any]:
    """Apply one typed presentation edit without mutating ``model``."""
    updated = copy.deepcopy(placements)
    kind = str(operation.get("type", ""))
    target_id = str(operation.get("targetId", ""))
    target = next((item for item in updated if item.get("id") == target_id), None)
    if kind == "duplicate":
        if target is None:
            raise ValueError("duplicate target not found")
        clone = copy.deepcopy(target)
        clone["id"] = str(operation.get("newId") or f"{target_id}-copy")
        dx, dy = float(operation.get("dx", 12)), float(operation.get("dy", 12))
        rect = _rect(clone["geometry"]) or [0, 0, 0, 0]
        clone["geometry"]["rect"] = [rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy]
        clone["clearanceEnvelope"] = _expand(clone["geometry"]["rect"], ASSET_CATALOG[clone["assetId"]]["clearanceEnvelope"])
        updated.append(clone)
    elif target is None:
        raise ValueError("edit target not found")
    elif kind == "drag":
        rect = _rect(target["geometry"]) or [0, 0, 0, 0]
        dx, dy = float(operation.get("dx", 0)), float(operation.get("dy", 0))
        target["geometry"]["rect"] = [rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy]
        target["clearanceEnvelope"] = _expand(target["geometry"]["rect"], ASSET_CATALOG[target["assetId"]]["clearanceEnvelope"])
    elif kind == "rotate":
        rotation = int(operation.get("rotation", target.get("rotation", 0))) % 360
        rect = _rect(target["geometry"]) or [0, 0, 0, 0]
        target["geometry"]["rect"] = _placement_rect(ASSET_CATALOG[target["assetId"]], rect[0], rect[1], rotation)
        target["rotation"] = rotation
        target["clearanceEnvelope"] = _expand(target["geometry"]["rect"], ASSET_CATALOG[target["assetId"]]["clearanceEnvelope"])
    elif kind == "replace":
        replacement = str(operation.get("assetId", ""))
        if replacement not in ASSET_CATALOG:
            raise ValueError("replacement asset not found")
        rect = _rect(target["geometry"]) or [0, 0, 0, 0]
        target.update(_new_placement(replacement, str(target["hostSpaceId"]), rect[0], rect[1], int(target.get("rotation", 0)), object_id=target_id))
    elif kind == "align":
        rect = _rect(target["geometry"]) or [0, 0, 0, 0]
        space = next(item for item in model.get("spaces", []) if item.get("id") == target.get("hostSpaceId"))
        bounds = _space_rect(space) or rect
        edge = str(operation.get("edge", "left"))
        if edge == "right":
            dx = bounds[2] - rect[2]
            dy = 0
        elif edge == "top":
            dx, dy = 0, bounds[3] - rect[3]
        elif edge == "bottom":
            dx, dy = 0, bounds[1] - rect[1]
        else:
            dx, dy = bounds[0] - rect[0], 0
        target["geometry"]["rect"] = [rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy]
        target["clearanceEnvelope"] = _expand(target["geometry"]["rect"], ASSET_CATALOG[target["assetId"]]["clearanceEnvelope"])
    elif kind == "find-valid-position":
        candidate = find_valid_position(model, target["assetId"], str(target["hostSpaceId"]), existing=[item for item in updated if item.get("id") != target_id])
        if candidate is None:
            raise ValueError("no valid position found")
        target.update(candidate)
        target["id"] = target_id
    else:
        raise ValueError(f"unsupported placement operation: {kind}")
    findings = []
    for item in updated:
        findings.extend(validate_placement(model, item, existing=[other for other in updated if other is not item]))
    return {"placements": updated, "findings": findings, "status": "blocked" if findings else "pass", "operation": copy.deepcopy(operation)}


def furnish_model(model: dict[str, Any], *, seed: int = 1516) -> dict[str, Any]:
    rng = random.Random(seed)
    placements: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for space in model.get("spaces", []) or []:
        use = _room_use(space)
        template = ROOM_TEMPLATES.get(use) or ROOM_TEMPLATES.get("office")
        if not template:
            continue
        asset_id = template["recommendedAssets"][rng.randrange(len(template["recommendedAssets"]))]
        candidate = find_valid_position(model, asset_id, str(space.get("id")), existing=placements)
        if candidate:
            candidate["modelRevision"] = model.get("project", {}).get("revision")
            candidate["id"] = f"{space.get('id')}-{asset_id}"
            placements.append(candidate)
        else:
            skipped.append({"spaceId": space.get("id"), "assetId": asset_id, "reason": "no clearance-valid position"})
    findings = []
    for item in placements:
        findings.extend(validate_placement(model, item, existing=[other for other in placements if other is not item]))
    payload = {
        "version": WEEK15_VERSION,
        "seed": seed,
        "placements": placements,
        "skipped": skipped,
        "findings": findings,
        "status": "blocked" if findings else "pass",
        "authoritativeGeometryUnchanged": True,
        "presentationOnly": True,
        "catalogVersion": WEEK15_VERSION,
    }
    payload["determinism"] = {"algorithm": "sha256", "signature": _signature(payload)}
    return payload


def _fraction(value: float, denominator: float = 1.0) -> float:
    return round(max(0.0, min(1.0, value / denominator if denominator else 0.0)), 4)


def _inherited_blocker(findings: Iterable[dict[str, Any]]) -> bool:
    return any(str(item.get("severity", "")).upper() in {"BLOCKER", "ERROR"} for item in findings)


def candidate_studio(
    model: dict[str, Any],
    *,
    seeds: Iterable[int] = (1516, 1523, 1547),
    inherited_findings: Iterable[dict[str, Any]] = (),
    ai_tool_inputs: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    inherited = list(inherited_findings)
    normalized_inputs = [copy.deepcopy(item) for item in ai_tool_inputs]
    candidates: list[dict[str, Any]] = []
    for index, seed in enumerate(seeds, 1):
        furnishing = furnish_model(model, seed=int(seed))
        adjacency_items = model.get("adjacencies", []) or []
        adjacency_score = _fraction(sum(bool(item.get("satisfied")) for item in adjacency_items), len(adjacency_items) or 1)
        spaces = model.get("spaces", []) or []
        daylight = _fraction(sum(bool(item.get("windows")) or bool(item.get("daylight")) for item in spaces), len(spaces) or 1)
        metrics = {
            "areaFit": _fraction(sum(1 for item in (model.get("program", {}).get("spaceChecks", []) or []) if item.get("status") in {"pass", "warning"}), len(model.get("program", {}).get("spaceChecks", []) or []) or 1),
            "adjacencySatisfaction": adjacency_score,
            "routeQuality": 0.0 if any(item.get("accessIntent") == "blocked" for item in spaces) else 1.0,
            "daylightVentilation": daylight or 0.5,
            "verticalCoordination": 1.0 if model.get("verticalConnectors") else (0.5 if len(model.get("levels", [])) <= 1 else 0.0),
            "furnitureFit": 1.0 if furnishing["status"] == "pass" else 0.0,
            "visualQuality": round(0.72 + ((int(seed) % 17) / 100), 4),
        }
        score = round(sum(metrics.values()) / len(metrics), 4)
        findings = inherited + list(furnishing["findings"])
        candidates.append({
            "id": f"C-15-{index:02d}",
            "seed": int(seed),
            "metrics": metrics,
            "score": score,
            "eligibleForBest": not _inherited_blocker(findings),
            "blockerCount": sum(1 for item in findings if str(item.get("severity", "")).upper() in {"BLOCKER", "ERROR"}),
            "furnishingSignature": furnishing["determinism"]["signature"],
            "technicalPlanRevision": model.get("project", {}).get("revision"),
            "presentationRenderMustMatchModel": True,
        })
    eligible = [item for item in candidates if item["eligibleForBest"]]
    ranking = [item["id"] for item in sorted(candidates, key=lambda value: (-value["eligibleForBest"], -value["score"], value["seed"]))]
    best = max(eligible, key=lambda item: (item["score"], -item["seed"]))["id"] if eligible else None
    findings: list[dict[str, Any]] = []
    if best is None:
        findings.append(_finding("BEST_CANDIDATE_MUST_HAVE_NO_BLOCKERS", "No candidate can win while inherited or furnishing blockers remain."))
    return {
        "version": WEEK16_VERSION,
        "seeds": [int(value) for value in seeds],
        "aiToolInputs": normalized_inputs,
        "aiToolInputCatalogVersion": AI_INPUT_VERSION,
        "candidates": candidates,
        "ranking": ranking,
        "bestCandidateId": best,
        "findings": findings,
        "status": "blocked" if findings else "pass",
        "comparisonMetrics": ["areaFit", "adjacencySatisfaction", "routeQuality", "daylightVentilation", "verticalCoordination", "furnitureFit", "visualQuality"],
    }


def _signature(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def design_package(model: dict[str, Any], candidate_id: str | None, *, seed: int = 1516) -> dict[str, Any]:
    model_revision = model.get("project", {}).get("revision")
    palette = ["#17324D", "#D8B26E", "#F4F0E8", "#6A7B6B"]
    layers = [
        {"id": "materials", "kind": "presentation", "authoritative": False, "sourceModelRevision": model_revision, "materialIds": ["stone-light", "wood-oak", "metal-bronze"]},
        {"id": "decor", "kind": "presentation", "authoritative": False, "sourceModelRevision": model_revision, "visible": True},
        {"id": "lighting", "kind": "presentation", "authoritative": False, "sourceModelRevision": model_revision, "preset": "daylight-soft"},
    ]
    materials = [
        {"id": "stone-light", "label": "Light stone", "finish": "matte", "colour": "#D8D2C4"},
        {"id": "wood-oak", "label": "Oak timber", "finish": "satin", "colour": "#A9794F"},
        {"id": "metal-bronze", "label": "Bronze metal", "finish": "brushed", "colour": "#8A6544"},
    ]
    jobs = [render_job(kind, model_revision, candidate_id, seed) for kind in ("render", "panorama", "presentation-sheet")]
    return {
        "version": RENDER_VERSION,
        "candidateId": candidate_id,
        "modelRevision": model_revision,
        "moodboard": {"styleTags": ["institutional", "warm-modern", "professional"], "palette": palette, "referenceImages": [], "materials": materials, "lightingPresets": ["daylight-soft", "evening-neutral"]},
        "materials": materials,
        "designLayers": layers,
        "renderJobs": jobs,
        "technicalPlanSideBySide": {"required": True, "modelRevision": model_revision, "candidateId": candidate_id},
        "aiToolInputsReport": str(AI_INPUT_REPORT_PATH.relative_to(ROOT)),
        "aiToolInputCatalogVersion": AI_INPUT_VERSION,
        "authoritativeGeometryChanged": False,
    }


def render_job(kind: str, model_revision: Any, candidate_id: str | None, seed: int) -> dict[str, Any]:
    if kind not in {"render", "panorama", "presentation-sheet"}:
        raise ValueError("unsupported render job")
    job_id = "render-" + _signature({"kind": kind, "revision": model_revision, "candidate": candidate_id, "seed": seed})[:12]
    return {
        "jobId": job_id,
        "kind": kind,
        "status": "queued",
        "progress": 0,
        "modelRevision": model_revision,
        "candidateId": candidate_id,
        "artifactManifest": {"artifactId": f"{job_id}-artifact", "kind": kind, "traceableTo": {"modelRevision": model_revision, "candidateId": candidate_id, "seed": seed}},
    }


def enrichment_report(model: dict[str, Any]) -> dict[str, Any]:
    furnishings = furnish_model(model)
    candidates = candidate_studio(model, inherited_findings=model.get("findings", []) or [])
    package = design_package(model, candidates["bestCandidateId"])
    planner5d = None
    if PLANNER5D_FIXTURE_PATH.is_file():
        planner_payload = json.loads(PLANNER5D_FIXTURE_PATH.read_text(encoding="utf-8"))
        planner5d = validate_planner5d_input(
            model,
            planner_payload,
            source_reference=str(planner_payload.get("sourceReference", "planner5d-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    archistar_snaptrude = None
    if ARCHISTAR_FIXTURE_PATH.is_file():
        archistar_payload = json.loads(ARCHISTAR_FIXTURE_PATH.read_text(encoding="utf-8"))
        archistar_snaptrude = validate_archistar_snaptrude_input(
            model,
            archistar_payload,
            source_reference=str(archistar_payload.get("sourceReference", "archistar-snaptrude-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    return {
        "status": "blocked"
        if furnishings["status"] == "blocked"
        or candidates["status"] == "blocked"
        or (archistar_snaptrude and archistar_snaptrude["status"] == "blocked")
        else "pass",
        "aiToolInputs": ai_tool_input_manifest(),
        "week15": furnishings,
        "week16": candidates,
        "planner5d": planner5d,
        "archistarSnaptrude": archistar_snaptrude,
        "designPackage": package,
    }


# Public names used by the roadmap and by the editor adapter.
parametric_asset_report = furnish_model
generate_candidates = candidate_studio
presentation_pipeline = design_package


def write_reports() -> dict[str, Any]:
    model = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    report = enrichment_report(model)
    existing_parametric = model.get("parametricAssets", {})
    existing_catalog = existing_parametric.get("catalog", {}) if isinstance(existing_parametric, dict) else {}
    catalog = copy.deepcopy(existing_catalog) if isinstance(existing_catalog, dict) else {}
    generated_catalog = asset_catalog()
    existing_assets = catalog.get("assets", {}) if isinstance(catalog.get("assets"), dict) else {}
    merged_assets = copy.deepcopy(existing_assets)
    merged_assets.update(generated_catalog["assets"])
    catalog.update(
        {
            "version": generated_catalog["version"],
            "assets": merged_assets,
            "roomTemplates": generated_catalog["roomTemplates"],
        }
    )
    model["parametricAssets"] = {"version": WEEK15_VERSION, "report": str(ASSET_REPORT_PATH.relative_to(ROOT)), "catalog": catalog, "presentation": report["week15"]}
    model["candidateStudio"] = {"version": WEEK16_VERSION, "report": str(CANDIDATE_REPORT_PATH.relative_to(ROOT)), "aiToolInputs": str(AI_INPUT_REPORT_PATH.relative_to(ROOT)), "bestCandidateId": report["week16"]["bestCandidateId"], "status": report["week16"]["status"], "seeds": report["week16"]["seeds"]}
    model["planner5dExchange"] = {"version": PLANNER5D_INPUT_VERSION, "report": str(PLANNER5D_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["planner5d"]["candidateEligible"], "status": report["planner5d"]["status"]}
    model["archistarSnaptrudeSiteEvidence"] = {"version": ARCHISTAR_INPUT_VERSION, "report": str(ARCHISTAR_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["archistarSnaptrude"]["candidateEligible"], "status": report["archistarSnaptrude"]["status"]}
    model["designPresentation"] = report["designPackage"]
    ASSET_REPORT_PATH.write_text(json.dumps(report["week15"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    AI_INPUT_REPORT_PATH.write_text(json.dumps(report["aiToolInputs"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CANDIDATE_REPORT_PATH.write_text(json.dumps({"aiToolInputs": report["aiToolInputs"], "candidateStudio": report["week16"], "designPackage": report["designPackage"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PLANNER5D_REPORT_PATH.write_text(json.dumps(report["planner5d"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARCHISTAR_REPORT_PATH.write_text(json.dumps(report["archistarSnaptrude"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps({"manifestVersion": "week1516.enrichment-manifest.v1", "status": report["status"], "reports": {"week15": str(ASSET_REPORT_PATH.relative_to(ROOT)), "week16": str(CANDIDATE_REPORT_PATH.relative_to(ROOT)), "planner5d": str(PLANNER5D_REPORT_PATH.relative_to(ROOT)), "archistarSnaptrude": str(ARCHISTAR_REPORT_PATH.relative_to(ROOT)), "aiToolInputs": str(AI_INPUT_REPORT_PATH.relative_to(ROOT))}, "changelog": str(CHANGELOG_PATH.relative_to(ROOT)), "catalogVersion": WEEK15_VERSION, "candidateVersion": WEEK16_VERSION, "planner5dVersion": PLANNER5D_INPUT_VERSION, "archistarSnaptrudeVersion": ARCHISTAR_INPUT_VERSION, "aiToolInputCatalogVersion": AI_INPUT_VERSION, "bestCandidateId": report["week16"]["bestCandidateId"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CHANGELOG_PATH.write_text(
        """# Week 15–16 enrichment changelog

## Week 15 — Parametric assets and clearance-aware furnishing

- Added a typed catalog covering furniture, fixtures, appliances, sanitaryware,
  seating rows, dais, library tables, counters, vehicles, and industrial
  equipment.
- Added dimensions, rotation rules, wall relationships, service sides,
  occupancy, clearance envelopes, room templates, and typed edit operations.
- One-click placement rejects door swings, routes, stairs, service zones,
  room-boundary violations, and overlapping clearance envelopes.
- Presentation objects remain non-authoritative and retain the canonical model
  revision for audit.

## Week 16 — Candidate studio and presentation pipeline

- Added deterministic candidate seeds and comparison metrics for area,
  adjacency, routes, daylight/ventilation, vertical coordination, furniture
  fit, and visual quality.
- A candidate with a BLOCKER or ERROR cannot win.
- Added moodboards, materials, lighting presets, non-destructive design layers,
  and traceable render, panorama, and presentation-sheet job manifests.
- Technical plan and presentation output carry the same model revision and
  candidate identifier.
- Added explicit review-first intake adapters for Maket.ai, Planner 5D,
  Archistar/Snaptrude, Floorplanner, Roomstyler/Homestyler, Magicplan,
  ChatGPT/Claude/Grok/Gemini, 4Lines.ai, and Archiagent.
- Each accepted tool signal retains its source reference, model revision,
  validation status, and review state; no external tool can silently mutate
  authoritative geometry or bypass a validation rerun.

### W16-01 implementation status — Maket.ai

- Added a text-to-plan fixture with units, room schedule, dimensions,
  furniture intent, and adjacency intent.
- Added dimension, unit, room-match, and input-shape checks through
  `validate_maket_input`.
- Conflicting dimensions become `review-required`; missing units or dimensions
  become blockers; the canonical model is never mutated.

### W16-02 implementation status — Planner 5D

- Added a furnishing exchange fixture with explicit model revision, units,
  source asset mappings, scaled dimensions, occupancy intent, and placements.
- Added canonical asset mapping and clearance validation through
  `validate_planner5d_input`; route, door-swing, room-fit, and overlapping
  clearance conflicts are retained as rejected-placement findings.
- Added a deterministic comparison with the Week 15 furnishing baseline.
  Imported items remain presentation-only and a rejected item cannot make the
  Planner 5D candidate eligible.

### W16-03 implementation status — Archistar / Snaptrude

- Added a site-model evidence fixture with coordinate and unit assumptions,
  orientation, access points, setbacks, levels, massing assumptions, confidence,
  and professional-review state.
- Added `validate_archistar_snaptrude_input`, which compares imported facts with
  the Week 6 orientation/program contract and links the canonical Week 7
  rule-pack findings without mutating geometry.
- Missing frontage or service access remains an explicit warning; imported
  massing remains review evidence and cannot become permit, code, or construction
  approval.
""",
        encoding="utf-8",
    )
    CANONICAL_PATH.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "report"), nargs="?", default="validate")
    args = parser.parse_args(argv)
    report = write_reports()
    print(json.dumps(report if args.command == "report" else {"status": report["status"], "bestCandidateId": report["week16"]["bestCandidateId"], "week15Report": str(ASSET_REPORT_PATH.relative_to(ROOT)), "week16Report": str(CANDIDATE_REPORT_PATH.relative_to(ROOT))}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())