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
FLOORPLANNER_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "floorplanner-synchronized-view.json"
FLOORPLANNER_REPORT_PATH = REPORT_ROOT / "week16-floorplanner-synchronized-view-report.json"
ROOMSTYLER_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "roomstyler-presentation-options.json"
ROOMSTYLER_REPORT_PATH = REPORT_ROOT / "week16-roomstyler-presentation-report.json"
MAGICPLAN_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "magicplan-recognition-queue.json"
MAGICPLAN_REPORT_PATH = REPORT_ROOT / "week16-magicplan-recognition-report.json"
LLM_BRIEF_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "llm-brief-refinement.json"
LLM_BRIEF_REPORT_PATH = REPORT_ROOT / "week16-llm-brief-refinement-report.json"
FOURLINES_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "week16" / "4lines-plan-section-exchange.json"
FOURLINES_REPORT_PATH = REPORT_ROOT / "week16-4lines-plan-section-exchange-report.json"
MANIFEST_PATH = REPORT_ROOT / "week1516-enrichment-manifest.json"
CHANGELOG_PATH = REPORT_ROOT / "week1516-changelog.md"

WEEK15_VERSION = "week15.parametric-assets.v1"
WEEK16_VERSION = "week16.candidate-studio.v1"
RENDER_VERSION = "week16.render-pipeline.v1"
AI_INPUT_VERSION = "week16.ai-tool-inputs.v1"
MAKET_INPUT_VERSION = "week16-01.maket-ai.v1"
PLANNER5D_INPUT_VERSION = "week16-02.planner5d.v1"
ARCHISTAR_INPUT_VERSION = "week16-03.archistar-snaptrude.v1"
FLOORPLANNER_INPUT_VERSION = "week16-04.floorplanner.v1"
ROOMSTYLER_INPUT_VERSION = "week16-05.roomstyler-homestyler.v1"
MAGICPLAN_INPUT_VERSION = "week16-06.magicplan.v1"
LLM_BRIEF_INPUT_VERSION = "week16-07.llm-brief-refinement.v1"
FOURLINES_INPUT_VERSION = "week16-08.4lines-plan-section.v1"


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
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/floorplanner-synchronized-view.json",
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
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/roomstyler-presentation-options.json",
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
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/magicplan-recognition-queue.json",
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
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/llm-brief-refinement.json",
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
        "implementationStatus": "applied",
        "implementationFixture": "tests/fixtures/week16/4lines-plan-section-exchange.json",
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


def _canonical_view_objects(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    collections = (
        "levels",
        "spaces",
        "openings",
        "windows",
        "stairs",
        "verticalConnectors",
        "entries",
    )
    objects: dict[str, dict[str, Any]] = {}
    for collection in collections:
        for item in model.get(collection, []) or []:
            if isinstance(item, dict) and item.get("id"):
                objects[str(item["id"])] = {
                    "collection": collection,
                    "levelId": item.get("levelId") or item.get("level"),
                }
    return objects


def validate_floorplanner_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Validate a Floorplanner 2D/3D view exchange against one model revision."""

    normalized = ingest_ai_tool_input(
        "floorplanner-synchronized-view",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    canonical_objects = _canonical_view_objects(model)
    canonical_levels = {
        str(item.get("id"))
        for item in model.get("levels", []) or []
        if isinstance(item, dict) and item.get("id")
    }
    imported_revision = payload.get("modelRevision")
    revision_matches = imported_revision == model_revision
    if not revision_matches:
        findings.append(
            _finding(
                "FLOORPLANNER_MODEL_REVISION_STALE",
                f"Floorplanner revision {imported_revision!r} does not match canonical revision {model_revision!r}.",
                severity="REVIEW_REQUIRED",
            )
        )

    export_reference = str(
        payload.get("viewExportReference") or payload.get("exportReference") or ""
    ).strip()
    if not export_reference:
        findings.append(
            _finding(
                "FLOORPLANNER_EXPORT_REFERENCE_REQUIRED",
                "A synchronized view must retain its Floorplanner export/reference ID.",
                severity="REVIEW_REQUIRED",
            )
        )

    object_id_map = payload.get("objectIdMap")
    if not isinstance(object_id_map, list) or not object_id_map:
        findings.append(
            _finding(
                "FLOORPLANNER_OBJECT_ID_MAP_REQUIRED",
                "The view exchange must provide a source-to-canonical object-ID map.",
                severity="REVIEW_REQUIRED",
            )
        )
        object_id_map = []

    mapped_ids: set[str] = set()
    for mapping in object_id_map:
        if not isinstance(mapping, dict):
            findings.append(
                _finding(
                    "FLOORPLANNER_OBJECT_ID_MAP_INVALID",
                    "Every Floorplanner object-ID mapping must be an object.",
                    severity="REVIEW_REQUIRED",
                )
            )
            continue
        source_id = str(mapping.get("sourceObjectId", "")).strip()
        canonical_id = str(mapping.get("canonicalObjectId", "")).strip()
        if not source_id or canonical_id not in canonical_objects:
            findings.append(
                _finding(
                    "FLOORPLANNER_OBJECT_ID_UNKNOWN",
                    f"Floorplanner mapping {source_id or canonical_id or 'unnamed'} does not resolve to a canonical object.",
                    severity="REVIEW_REQUIRED",
                )
            )
            continue
        mapped_ids.add(canonical_id)

    imported_views = payload.get("views")
    if not isinstance(imported_views, list) or not imported_views:
        findings.append(
            _finding(
                "FLOORPLANNER_VIEWS_REQUIRED",
                "Floorplanner exchange must contain at least one 2D/3D view.",
            )
        )
        imported_views = []

    view_summaries: list[dict[str, Any]] = []
    view_kinds: set[tuple[str, str]] = set()
    for view in imported_views:
        if not isinstance(view, dict):
            findings.append(
                _finding(
                    "FLOORPLANNER_VIEW_INVALID",
                    "Each Floorplanner view must be an object.",
                    severity="REVIEW_REQUIRED",
                )
            )
            continue
        view_id = str(view.get("id", "")).strip() or "unnamed-view"
        kind = str(view.get("kind", "")).strip().lower()
        level_id = str(view.get("levelId", "")).strip()
        object_ids = view.get("objectIds")
        if kind not in {"2d-plan", "3d"}:
            findings.append(
                _finding(
                    "FLOORPLANNER_VIEW_KIND_UNSUPPORTED",
                    f"{view_id} must be a 2d-plan or 3d view.",
                    severity="REVIEW_REQUIRED",
                    object_id=view_id,
                )
            )
        if level_id not in canonical_levels:
            findings.append(
                _finding(
                    "FLOORPLANNER_LEVEL_UNKNOWN",
                    f"{view_id} references unknown level {level_id or '<missing>'}.",
                    severity="REVIEW_REQUIRED",
                    object_id=view_id,
                )
            )
        if not isinstance(object_ids, list) or not object_ids:
            findings.append(
                _finding(
                    "FLOORPLANNER_VIEW_OBJECTS_REQUIRED",
                    f"{view_id} must list the canonical objects visible in the view.",
                    severity="REVIEW_REQUIRED",
                    object_id=view_id,
                )
            )
            object_ids = []
        unknown_ids = [
            str(object_id)
            for object_id in object_ids
            if str(object_id) not in canonical_objects
        ]
        for object_id in unknown_ids:
            findings.append(
                _finding(
                    "FLOORPLANNER_UNKNOWN_OBJECT_ID",
                    f"{view_id} references unknown canonical object {object_id}.",
                    severity="REVIEW_REQUIRED",
                    object_id=object_id,
                )
            )
        opening_ids = view.get("openingIds", [])
        if not isinstance(opening_ids, list):
            opening_ids = []
            findings.append(
                _finding(
                    "FLOORPLANNER_OPENING_IDS_INVALID",
                    f"{view_id} openingIds must be a list.",
                    severity="REVIEW_REQUIRED",
                    object_id=view_id,
                )
            )
        for opening_id in opening_ids:
            opening = canonical_objects.get(str(opening_id))
            if not opening or opening["collection"] != "openings":
                findings.append(
                    _finding(
                        "FLOORPLANNER_OPENING_ID_UNKNOWN",
                        f"{view_id} references unknown canonical opening {opening_id}.",
                        severity="REVIEW_REQUIRED",
                        object_id=str(opening_id),
                    )
                )
        stair_ids = view.get("stairIds", [])
        if not isinstance(stair_ids, list):
            stair_ids = []
            findings.append(
                _finding(
                    "FLOORPLANNER_STAIR_IDS_INVALID",
                    f"{view_id} stairIds must be a list.",
                    severity="REVIEW_REQUIRED",
                    object_id=view_id,
                )
            )
        for stair_id in stair_ids:
            stair = canonical_objects.get(str(stair_id))
            if not stair or stair["collection"] not in {"stairs", "verticalConnectors"}:
                findings.append(
                    _finding(
                        "FLOORPLANNER_STAIR_ID_UNKNOWN",
                        f"{view_id} references unknown canonical stair or connector {stair_id}.",
                        severity="REVIEW_REQUIRED",
                        object_id=str(stair_id),
                    )
                )
        for object_id in object_ids:
            canonical = canonical_objects.get(str(object_id))
            if canonical and canonical.get("levelId") and level_id and canonical["levelId"] != level_id:
                findings.append(
                    _finding(
                        "FLOORPLANNER_OBJECT_LEVEL_MISMATCH",
                        f"{view_id} places {object_id} on {level_id}, but the canonical object belongs to {canonical['levelId']}.",
                        severity="REVIEW_REQUIRED",
                        object_id=str(object_id),
                    )
                )
        view_kinds.add((kind, level_id))
        view_summaries.append(
            {
                "id": view_id,
                "kind": kind,
                "levelId": level_id,
                "objectIds": [str(item) for item in object_ids],
                "openingIds": [str(item) for item in opening_ids],
                "stairIds": [str(item) for item in stair_ids],
                "status": "stale" if not revision_matches else "reviewed",
            }
        )

    expected_kinds = {
        (kind, str(level.get("id")))
        for level in model.get("levels", []) or []
        if isinstance(level, dict) and level.get("id")
        for kind in ("2d-plan", "3d")
    }
    missing_view_kinds = sorted(expected_kinds - view_kinds)
    if missing_view_kinds:
        findings.append(
            _finding(
                "FLOORPLANNER_VIEW_COVERAGE_INCOMPLETE",
                f"Floorplanner exchange is missing synchronized views: {missing_view_kinds}.",
                severity="REVIEW_REQUIRED",
            )
        )

    level_visibility = payload.get("levelVisibility")
    visible_levels = (
        [str(item) for item in level_visibility]
        if isinstance(level_visibility, list)
        else []
    )
    if set(visible_levels) - canonical_levels:
        findings.append(
            _finding(
                "FLOORPLANNER_LEVEL_VISIBILITY_UNKNOWN",
                "Level visibility contains an ID outside the canonical level set.",
                severity="REVIEW_REQUIRED",
            )
        )

    validation_status = str(payload.get("validationStatus") or "pending").strip().lower()
    validation_signature = str(payload.get("validationSignature") or "").strip()
    if not validation_signature:
        findings.append(
            _finding(
                "FLOORPLANNER_VALIDATION_SIGNATURE_REQUIRED",
                "The synchronized view must carry the validation signature for its canonical revision.",
                severity="REVIEW_REQUIRED",
            )
        )
    if validation_status != "pass":
        findings.append(
            _finding(
                "FLOORPLANNER_VALIDATION_NOT_PASSED",
                f"Floorplanner view validation status is {validation_status!r}, not pass.",
                severity="REVIEW_REQUIRED",
            )
        )

    accepted_edit = payload.get("acceptedEdit")
    rerun = {
        "requiredAfterAcceptedEdit": True,
        "performed": False,
        "modelRevision": model_revision,
        "validationSignature": validation_signature or None,
    }
    if isinstance(accepted_edit, dict):
        rerun_revision = accepted_edit.get("postEditModelRevision")
        rerun_signature = str(accepted_edit.get("validationRerunSignature") or "").strip()
        rerun["performed"] = bool(rerun_revision is not None and rerun_signature)
        rerun["modelRevision"] = rerun_revision
        rerun["validationSignature"] = rerun_signature or None
        if not rerun["performed"]:
            findings.append(
                _finding(
                    "FLOORPLANNER_VALIDATION_RERUN_REQUIRED",
                    "An accepted view edit must carry a post-edit model revision and validation rerun signature.",
                    severity="REVIEW_REQUIRED",
                )
            )

    # Reuse the Week 14 view contract as the canonical comparison surface.
    from week1314 import build_synchronized_views  # type: ignore

    canonical_views = build_synchronized_views(model)
    canonical_view_keys = {
        (str(view.get("kind")), str(view.get("levelId")))
        for view in canonical_views.get("views", [])
    }
    synchronization_matches = (
        revision_matches
        and not missing_view_kinds
        and canonical_view_keys.issuperset(view_kinds)
    )
    has_blocker = any(item["severity"] in {"BLOCKER", "ERROR"} for item in findings)
    status = "blocked" if has_blocker else "review-required" if findings else "pass"
    return {
        "version": FLOORPLANNER_INPUT_VERSION,
        "tool": "Floorplanner",
        "sourceReference": source_reference,
        "viewExportReference": export_reference or None,
        "modelRevision": model_revision,
        "importedModelRevision": imported_revision,
        "canonicalModelRevision": model_revision,
        "input": normalized,
        "objectIdMap": copy.deepcopy(object_id_map),
        "views": view_summaries,
        "levelVisibility": visible_levels,
        "revisionMatch": revision_matches,
        "synchronizationStatus": "synchronized" if synchronization_matches and not findings else "stale" if not revision_matches else "review-required",
        "canonicalViewContract": {
            "version": canonical_views.get("reportVersion"),
            "synchronizationKey": canonical_views.get("synchronizationKey"),
            "sharedRevisionAcrossViews": canonical_views.get("gate", {}).get("sharedRevisionAcrossViews"),
            "validationRerunsAfterAcceptedEdit": canonical_views.get("gate", {}).get("validationRerunsAfterAcceptedEdit"),
        },
        "validationEvidence": {
            "status": validation_status,
            "signature": validation_signature or None,
            "rerunAfterAcceptedEdit": rerun,
        },
        "findings": findings,
        "status": status,
        "candidateEligible": status == "pass",
        "authoritativeGeometryChanged": False,
        "presentationOnly": True,
    }


validate_floorplanner_view_input = validate_floorplanner_input


def _canonical_object_ids(model: dict[str, Any]) -> set[str]:
    """Return IDs that a photo-recognition result may propose linking to."""

    object_ids: set[str] = set()
    for collection in ("spaces", "openings", "walls", "stairs", "routes", "serviceZones"):
        for item in model.get(collection, []) or []:
            if isinstance(item, dict) and str(item.get("id", "")).strip():
                object_ids.add(str(item["id"]))
    return object_ids


def validate_roomstyler_homestyler_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Validate a Roomstyler/Homestyler presentation option.

    Imported furniture and finishes are rebuilt as typed presentation objects
    from the canonical asset catalog.  The technical plan remains a separate
    traceable surface; styling can expose a blocker but cannot hide or edit it.
    """

    normalized = ingest_ai_tool_input(
        "roomstyler-homestyler-furnishing",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    units = str(payload.get("units", "")).strip().lower()
    unit_scale = _planner5d_unit_scale(units)
    if unit_scale is None:
        findings.append(_finding("ROOMSTYLER_UNITS_REQUIRED", "Roomstyler/Homestyler input must declare supported units."))

    imported_revision = payload.get("modelRevision", model_revision)
    if imported_revision != model_revision:
        findings.append(
            _finding(
                "ROOMSTYLER_MODEL_REVISION_MISMATCH",
                f"Styled option revision {imported_revision!r} does not match canonical revision {model_revision!r}.",
                severity="REVIEW_REQUIRED",
            )
        )

    candidate_id = str(payload.get("candidateId", "")).strip()
    if not candidate_id:
        findings.append(_finding("ROOMSTYLER_CANDIDATE_ID_REQUIRED", "A styled presentation option must identify its candidate."))

    technical_plan = payload.get("technicalPlan")
    if not isinstance(technical_plan, dict):
        findings.append(
            _finding(
                "ROOMSTYLER_TECHNICAL_PLAN_REQUIRED",
                "The styled option must carry a technical-plan trace for side-by-side review.",
                severity="REVIEW_REQUIRED",
            )
        )
        technical_plan = {}
    if technical_plan.get("modelRevision") != model_revision:
        findings.append(
            _finding(
                "ROOMSTYLER_TECHNICAL_PLAN_REVISION_MISMATCH",
                "The technical plan and styled presentation must use the same canonical model revision.",
                severity="REVIEW_REQUIRED",
            )
        )
    if candidate_id and technical_plan.get("candidateId") != candidate_id:
        findings.append(
            _finding(
                "ROOMSTYLER_TECHNICAL_PLAN_CANDIDATE_MISMATCH",
                "The technical plan and styled presentation must use the same candidate ID.",
                severity="REVIEW_REQUIRED",
            )
        )
    if not str(technical_plan.get("validationSignature", "")).strip():
        findings.append(
            _finding(
                "ROOMSTYLER_TECHNICAL_VALIDATION_REQUIRED",
                "Side-by-side presentation requires the technical plan validation signature.",
                severity="REVIEW_REQUIRED",
            )
        )
    render_reference = str(payload.get("renderReference", "")).strip()
    if not render_reference:
        findings.append(
            _finding(
                "ROOMSTYLER_RENDER_REFERENCE_REQUIRED",
                "A styled presentation must retain its source render/export reference.",
                severity="REVIEW_REQUIRED",
            )
        )

    mappings = payload.get("assetMappings")
    mapping_by_source: dict[str, str] = {}
    mapping_report: list[dict[str, Any]] = []
    if not isinstance(mappings, list) or not mappings:
        findings.append(_finding("ROOMSTYLER_ASSET_MAPPING_REQUIRED", "Styled furniture must use typed canonical asset mappings."))
        mappings = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            findings.append(_finding("ROOMSTYLER_ASSET_MAPPING_INVALID", "Each styled asset mapping must be an object."))
            continue
        source_asset_id = str(mapping.get("sourceAssetId", "")).strip()
        asset_id = str(mapping.get("assetId", "")).strip()
        if not source_asset_id or asset_id not in ASSET_CATALOG:
            findings.append(
                _finding(
                    "ROOMSTYLER_ASSET_MAPPING_UNKNOWN",
                    f"Styled asset mapping {source_asset_id or asset_id or 'unnamed'} does not resolve to a canonical asset.",
                )
            )
            mapping_report.append({"sourceAssetId": source_asset_id or None, "assetId": asset_id or None, "status": "rejected"})
            continue
        mapping_by_source[source_asset_id] = asset_id
        mapping_report.append({"sourceAssetId": source_asset_id, "assetId": asset_id, "status": "mapped"})

    options = payload.get("options")
    if not isinstance(options, list) or not options:
        findings.append(_finding("ROOMSTYLER_OPTIONS_REQUIRED", "At least one typed presentation option is required."))
        options = []

    accepted_options: list[dict[str, Any]] = []
    rejected_options: list[dict[str, Any]] = []
    option_summaries: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict):
            findings.append(_finding("ROOMSTYLER_OPTION_INVALID", "Each presentation option must be an object."))
            continue
        option_id = str(option.get("id", "")).strip()
        option_findings: list[dict[str, Any]] = []
        if not option_id:
            option_findings.append(_finding("ROOMSTYLER_OPTION_ID_REQUIRED", "Each presentation option must have an ID."))
        placements: list[dict[str, Any]] = []
        furniture = option.get("furniture")
        if not isinstance(furniture, list):
            option_findings.append(_finding("ROOMSTYLER_FURNITURE_REQUIRED", f"{option_id or 'option'} must contain a furniture list."))
            furniture = []

        for item in furniture:
            if not isinstance(item, dict):
                option_findings.append(_finding("ROOMSTYLER_FURNITURE_INVALID", f"{option_id or 'option'} contains a non-object furniture item."))
                continue
            object_id = str(item.get("id", "")).strip()
            source_asset_id = str(item.get("sourceAssetId", "")).strip()
            asset_id = str(item.get("assetId") or mapping_by_source.get(source_asset_id, "")).strip()
            spec = ASSET_CATALOG.get(asset_id)
            item_findings: list[dict[str, Any]] = []
            if not object_id:
                item_findings.append(_finding("ROOMSTYLER_FURNITURE_ID_REQUIRED", "Every styled furniture item must have an ID."))
            if spec is None:
                item_findings.append(_finding("ROOMSTYLER_ASSET_UNKNOWN", f"{object_id or 'furniture'} does not resolve to a canonical asset.", object_id=object_id))
                option_findings.extend(item_findings)
                continue
            position = _planner5d_position(item)
            if position is None or unit_scale is None:
                item_findings.append(
                    _finding(
                        "ROOMSTYLER_FURNITURE_POSITION_REQUIRED",
                        f"{object_id or asset_id} needs a numeric position in supported units.",
                        object_id=object_id,
                    )
                )
                option_findings.extend(item_findings)
                continue
            rotation = int(item.get("rotation", 0) or 0)
            placement = _new_placement(
                asset_id,
                str(item.get("hostSpaceId") or item.get("spaceId") or ""),
                position[0] * unit_scale,
                position[1] * unit_scale,
                rotation,
                object_id=object_id or None,
            )
            dimensions = item.get("dimensions")
            if isinstance(dimensions, dict):
                expected_width = spec["depth"] if rotation % 180 == 90 else spec["width"]
                expected_depth = spec["width"] if rotation % 180 == 90 else spec["depth"]
                for dimension, expected in (("width", expected_width), ("depth", expected_depth)):
                    value = dimensions.get(dimension)
                    if not isinstance(value, (int, float)) or abs(float(value) * unit_scale - expected) > 0.01:
                        item_findings.append(
                            _finding(
                                "ROOMSTYLER_ASSET_SCALE_CONFLICT",
                                f"{object_id or asset_id} {dimension} does not match the canonical {asset_id} scale.",
                                severity="REVIEW_REQUIRED",
                                object_id=object_id,
                            )
                        )
            host_space = next(
                (space for space in model.get("spaces", []) if space.get("id") == placement["hostSpaceId"]),
                None,
            )
            if host_space is not None and _room_use(host_space) not in set(spec["roomUses"]):
                item_findings.append(
                    _finding(
                        "ROOMSTYLER_ASSET_ROOM_USE_REVIEW",
                        f"{object_id or asset_id} maps {asset_id} into {_room_use(host_space)!r}, outside its catalog room uses.",
                        severity="REVIEW_REQUIRED",
                        object_id=object_id,
                    )
                )
            item_findings.extend(validate_placement(model, placement, existing=placements))
            placement.update(
                {
                    "sourceTool": "Roomstyler / Homestyler",
                    "sourceAssetId": source_asset_id or None,
                    "sourceReference": source_reference,
                    "candidateId": candidate_id or None,
                    "modelRevision": model_revision,
                    "occupancyIntent": item.get("occupancy"),
                    "serviceSideIntent": item.get("serviceSide"),
                    "presentationOnly": True,
                    "authoritative": False,
                }
            )
            placements.append(placement)
            option_findings.extend(item_findings)

        finish_options = option.get("finishes")
        normalized_finishes: list[dict[str, Any]] = []
        if not isinstance(finish_options, list):
            option_findings.append(_finding("ROOMSTYLER_FINISHES_REQUIRED", f"{option_id or 'option'} must contain typed finish options."))
            finish_options = []
        for finish in finish_options:
            if not isinstance(finish, dict):
                option_findings.append(_finding("ROOMSTYLER_FINISH_INVALID", f"{option_id or 'option'} contains a non-object finish."))
                continue
            finish_id = str(finish.get("id", "")).strip()
            host_space_id = str(finish.get("hostSpaceId", "")).strip()
            if not finish_id or not host_space_id or not str(finish.get("material", "")).strip():
                option_findings.append(
                    _finding(
                        "ROOMSTYLER_FINISH_TYPED_FIELDS_REQUIRED",
                        f"{finish_id or 'finish'} requires an ID, host space, and material.",
                        severity="REVIEW_REQUIRED",
                    )
                )
                continue
            if not any(space.get("id") == host_space_id for space in model.get("spaces", [])):
                option_findings.append(
                    _finding(
                        "ROOMSTYLER_FINISH_HOST_SPACE_UNKNOWN",
                        f"{finish_id} references an unknown canonical host space.",
                        severity="REVIEW_REQUIRED",
                    )
                )
            normalized_finishes.append(
                {
                    "id": finish_id,
                    "hostSpaceId": host_space_id,
                    "material": str(finish["material"]),
                    "finish": str(finish.get("finish", "")),
                    "sourceReference": source_reference,
                    "candidateId": candidate_id or None,
                    "modelRevision": model_revision,
                    "presentationOnly": True,
                    "authoritative": False,
                }
            )

        option_result = {
            "id": option_id or None,
            "label": str(option.get("label", "")),
            "furniture": placements,
            "finishes": normalized_finishes,
            "findings": option_findings,
            "status": "review-required" if option_findings else "pass",
            "presentationOnly": True,
            "authoritativeGeometryChanged": False,
        }
        option_summaries.append(
            {
                "id": option_result["id"],
                "label": option_result["label"],
                "furnitureCount": len(placements),
                "finishCount": len(normalized_finishes),
                "status": option_result["status"],
            }
        )
        if option_findings:
            rejected_options.append(option_result)
        else:
            accepted_options.append(option_result)

    all_findings = findings + [finding for option in rejected_options for finding in option["findings"]]
    # A rejected styled option may contain a technical BLOCKER, but it is
    # isolated from the accepted presentation options.  Preserve that finding
    # and make the candidate ineligible without blocking the report itself.
    has_blocker = any(item["severity"] in {"BLOCKER", "ERROR"} for item in findings)
    status = "blocked" if has_blocker else "review-required" if all_findings else "pass"
    result = {
        "version": ROOMSTYLER_INPUT_VERSION,
        "tool": "Roomstyler / Homestyler",
        "sourceReference": source_reference,
        "renderReference": render_reference or None,
        "candidateId": candidate_id or None,
        "modelRevision": model_revision,
        "canonicalModelRevision": model_revision,
        "importedModelRevision": imported_revision,
        "units": units,
        "assetScaleToCanonicalInches": unit_scale,
        "input": normalized,
        "assetMappingReport": mapping_report,
        "options": option_summaries,
        "acceptedOptions": accepted_options,
        "rejectedOptions": rejected_options,
        "technicalPlanSideBySide": {
            "reference": technical_plan.get("reference"),
            "candidateId": technical_plan.get("candidateId"),
            "modelRevision": technical_plan.get("modelRevision"),
            "validationSignature": technical_plan.get("validationSignature"),
            "validationMarkersRetained": True,
        },
        "findings": all_findings,
        "status": status,
        "candidateEligible": status == "pass" and not rejected_options,
        "presentationOnly": True,
        "authoritativeGeometryChanged": False,
    }
    result["determinism"] = {"algorithm": "sha256", "signature": _signature(result)}
    return result


def validate_magicplan_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Validate Magicplan photo recognition as a confidence-based queue."""

    normalized = ingest_ai_tool_input(
        "magicplan-photo-capture",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    photos = payload.get("photos")
    if not isinstance(photos, list) or not photos:
        findings.append(_finding("MAGICPLAN_SOURCE_IMAGE_REQUIRED", "Magicplan capture must include at least one source image."))
        photos = []
    normalized_photos: list[dict[str, Any]] = []
    for photo in photos:
        if not isinstance(photo, dict) or not str(photo.get("id", "")).strip() or not str(photo.get("sourceImage", "")).strip():
            findings.append(_finding("MAGICPLAN_SOURCE_IMAGE_INVALID", "Each Magicplan photo needs an ID and source image reference."))
            continue
        normalized_photos.append(
            {
                "id": str(photo["id"]),
                "sourceImage": str(photo["sourceImage"]),
                "capturedAt": photo.get("capturedAt"),
                "captureMetadata": copy.deepcopy(photo.get("captureMetadata", {})),
            }
        )

    capture_metadata = payload.get("captureMetadata")
    if not isinstance(capture_metadata, dict) or not str(capture_metadata.get("device", "")).strip():
        findings.append(
            _finding(
                "MAGICPLAN_CAPTURE_METADATA_REQUIRED",
                "Capture metadata must identify the capture device or method.",
                severity="REVIEW_REQUIRED",
            )
        )

    known_dimensions = payload.get("knownDimensions")
    if not isinstance(known_dimensions, list) or not known_dimensions:
        findings.append(_finding("MAGICPLAN_KNOWN_SCALE_REQUIRED", "Magicplan capture must include at least one known dimension."))
        known_dimensions = []
    for dimension in known_dimensions:
        if (
            not isinstance(dimension, dict)
            or not str(dimension.get("id", "")).strip()
            or not isinstance(dimension.get("value"), (int, float))
            or dimension.get("value", 0) <= 0
            or str(dimension.get("units", "")).strip().lower() not in {"inch", "in", "foot", "ft", "mm", "m"}
        ):
            findings.append(
                _finding(
                    "MAGICPLAN_KNOWN_DIMENSION_INVALID",
                    "Known dimensions require a positive value and supported units.",
                )
            )

    scale_evidence = payload.get("scaleEvidence")
    if not isinstance(scale_evidence, list) or not scale_evidence:
        findings.append(_finding("MAGICPLAN_SCALE_EVIDENCE_REQUIRED", "Recognition requires explicit scale evidence tied to a source image."))
        scale_evidence = []
    normalized_scale_evidence = []
    for evidence in scale_evidence:
        if not isinstance(evidence, dict) or not str(evidence.get("photoId", "")).strip() or not str(evidence.get("dimensionId", "")).strip():
            findings.append(
                _finding(
                    "MAGICPLAN_SCALE_EVIDENCE_INVALID",
                    "Each scale-evidence item must link a photo to a known dimension.",
                )
            )
            continue
        normalized_scale_evidence.append(copy.deepcopy(evidence))

    objects = payload.get("recognizedObjects")
    if not isinstance(objects, list) or not objects:
        findings.append(_finding("MAGICPLAN_RECOGNIZED_OBJECTS_REQUIRED", "Magicplan capture must include recognized objects for review."))
        objects = []
    canonical_ids = _canonical_object_ids(model)
    accepted: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    promoted: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    for recognized in objects:
        if not isinstance(recognized, dict):
            findings.append(_finding("MAGICPLAN_OBJECT_INVALID", "Each recognized object must be an object."))
            continue
        object_id = str(recognized.get("id", "")).strip()
        kind = str(recognized.get("kind", "")).strip().lower()
        queue_status = str(recognized.get("queueStatus", "")).strip().lower()
        confidence = recognized.get("confidence")
        proposed_object_id = str(recognized.get("proposedObjectId", "")).strip()
        manual_confirmation = recognized.get("manualConfirmation") is True
        item_findings: list[dict[str, Any]] = []
        if not object_id or kind not in {"room", "opening", "wall"}:
            item_findings.append(_finding("MAGICPLAN_OBJECT_TYPE_REQUIRED", f"{object_id or 'recognized object'} needs an ID and supported kind.", object_id=object_id))
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            item_findings.append(_finding("MAGICPLAN_CONFIDENCE_REQUIRED", f"{object_id or 'recognized object'} needs confidence from 0 to 1.", object_id=object_id))
            numeric_confidence = 0.0
        else:
            numeric_confidence = float(confidence)
        if queue_status not in {"accepted", "uncertain", "rejected"}:
            item_findings.append(_finding("MAGICPLAN_QUEUE_STATUS_REQUIRED", f"{object_id or 'recognized object'} needs accepted, uncertain, or rejected status.", object_id=object_id))
            queue_status = "uncertain"
        if proposed_object_id and proposed_object_id not in canonical_ids:
            item_findings.append(
                _finding(
                    "MAGICPLAN_PROPOSED_LINK_UNKNOWN",
                    f"{object_id or 'recognized object'} proposes an unknown canonical object link.",
                    severity="REVIEW_REQUIRED",
                    object_id=object_id,
                )
            )
        item_result = {
            "id": object_id or None,
            "kind": kind or None,
            "confidence": numeric_confidence,
            "proposedObjectId": proposed_object_id or None,
            "queueStatus": queue_status,
            "manualConfirmation": manual_confirmation,
            "findings": item_findings,
            "sourceImageId": recognized.get("sourceImageId"),
            "authoritative": False,
            "editableGeometry": False,
        }
        if queue_status == "accepted":
            if not manual_confirmation:
                item_findings.append(
                    _finding(
                        "MAGICPLAN_MANUAL_CONFIRMATION_REQUIRED",
                        f"{object_id or 'recognized object'} cannot be promoted without manual confirmation.",
                        severity="REVIEW_REQUIRED",
                        object_id=object_id,
                    )
                )
            if numeric_confidence < 0.85:
                item_findings.append(
                    _finding(
                        "MAGICPLAN_CONFIDENCE_REVIEW_REQUIRED",
                        f"{object_id or 'recognized object'} confidence is below the promotion threshold.",
                        severity="REVIEW_REQUIRED",
                        object_id=object_id,
                    )
                )
            if not normalized_scale_evidence:
                item_findings.append(
                    _finding(
                        "MAGICPLAN_SCALE_REQUIRED_FOR_PROMOTION",
                        f"{object_id or 'recognized object'} has no usable scale evidence.",
                        severity="REVIEW_REQUIRED",
                        object_id=object_id,
                    )
                )
            if not proposed_object_id or proposed_object_id not in canonical_ids:
                item_findings.append(
                    _finding(
                        "MAGICPLAN_CANONICAL_LINK_REQUIRED",
                        f"{object_id or 'recognized object'} needs a known canonical object link before promotion.",
                        severity="REVIEW_REQUIRED",
                        object_id=object_id,
                    )
                )
            promotion = recognized.get("promotion")
            if not isinstance(promotion, dict) or promotion.get("postPromotionModelRevision") is None or not str(promotion.get("validationRerunSignature", "")).strip():
                item_findings.append(
                    _finding(
                        "MAGICPLAN_VALIDATION_RERUN_REQUIRED",
                        f"{object_id or 'recognized object'} needs a post-promotion revision and topology/clearance rerun signature.",
                        severity="REVIEW_REQUIRED",
                        object_id=object_id,
                    )
                )
            if not item_findings:
                item_result["editableGeometry"] = True
                item_result["promotion"] = copy.deepcopy(promotion)
                promoted.append(copy.deepcopy(item_result))
            accepted.append(item_result)
        elif queue_status == "rejected":
            rejected.append(item_result)
            review_queue.append(item_result)
        else:
            uncertain.append(item_result)
            review_queue.append(item_result)
        if item_findings:
            findings.extend(item_findings)

    # Uncertain and rejected recognition is intentionally visible even when it
    # does not block report generation.
    queue_requires_review = bool(uncertain or rejected)
    all_findings = findings
    has_blocker = any(item["severity"] in {"BLOCKER", "ERROR"} for item in all_findings)
    status = "blocked" if has_blocker else "review-required" if all_findings or queue_requires_review else "pass"
    return {
        "version": MAGICPLAN_INPUT_VERSION,
        "tool": "Magicplan",
        "sourceReference": source_reference,
        "modelRevision": model_revision,
        "canonicalModelRevision": model_revision,
        "input": normalized,
        "photos": normalized_photos,
        "captureMetadata": copy.deepcopy(capture_metadata) if isinstance(capture_metadata, dict) else {},
        "knownDimensions": copy.deepcopy(known_dimensions),
        "scaleEvidence": normalized_scale_evidence,
        "acceptedObjects": accepted,
        "uncertainObjects": uncertain,
        "rejectedObjects": rejected,
        "promotedObjects": promoted,
        "reviewQueue": review_queue,
        "recognitionSummary": {
            "recognized": len(objects),
            "accepted": len(accepted),
            "uncertain": len(uncertain),
            "rejected": len(rejected),
            "promoted": len(promoted),
            "imageOnlyPromotionBlocked": not bool(promoted) and bool(objects),
        },
        "findings": all_findings,
        "status": status,
        "candidateEligible": status == "pass",
        "authoritativeGeometryChanged": False,
        "promotionPolicy": "only manually confirmed, scale-backed objects with a validation rerun may become editable in a later revision",
        "determinism": {"algorithm": "sha256", "signature": _signature({
            "sourceReference": source_reference,
            "modelRevision": model_revision,
            "recognizedObjects": objects,
            "scaleEvidence": normalized_scale_evidence,
        })},
    }


def _brief_revision_preview(model: dict[str, Any], command_text: str, *, timestamp: str) -> dict[str, Any]:
    """Build a compact Week 12 typed revision preview for an LLM proposal."""

    from week1112 import command_preview

    preview = command_preview(
        model,
        command_text,
        author="week16-llm-brief-refinement",
        timestamp=timestamp,
    )
    preview["targetObjects"] = [
        {"collection": item["collection"], "id": item["object"].get("id")}
        for item in preview.get("targetObjects", [])
    ]
    return preview


def validate_llm_brief_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Validate provider-neutral conversational brief refinement.

    The LLM output is treated as text evidence and typed revision proposals.
    Week 12 remains responsible for parsing the brief and previewing commands;
    this adapter adds provenance, clarification state, explicit acceptance, and
    the upper-floor access gate needed before a proposal can reach presentation.
    """

    from week1112 import accept_revision, compile_brief

    normalized = ingest_ai_tool_input(
        "llm-brief-refinement",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    brief_text = str(payload.get("briefText") or payload.get("sourceText") or "").strip()
    if not brief_text:
        findings.append(
            _finding(
                "LLM_BRIEF_TEXT_REQUIRED",
                "Conversational refinement must retain the source brief text.",
            )
        )

    provider = str(payload.get("provider") or "provider-neutral").strip()
    if provider not in {"provider-neutral", "ChatGPT", "Claude", "Grok", "Gemini"}:
        findings.append(
            _finding(
                "LLM_PROVIDER_UNSUPPORTED",
                f"Provider {provider!r} is not in the provider-neutral Week 16 boundary.",
                severity="REVIEW_REQUIRED",
            )
        )

    default_units = str(payload.get("defaultUnits") or "inch")
    compiler_shape = compile_brief(brief_text, default_units=default_units)
    compiler_shape["facts"]["constraints"] = copy.deepcopy(payload.get("constraints") or [])
    compiler_shape["facts"]["candidateFeedback"] = copy.deepcopy(payload.get("candidateFeedback") or [])

    vertical_access = payload.get("verticalAccess")
    if not isinstance(vertical_access, list):
        vertical_access = []
    compiler_shape["facts"]["verticalAccess"] = copy.deepcopy(vertical_access)

    brief_level_count = compiler_shape.get("facts", {}).get("levels")
    canonical_levels = [
        str(item.get("id"))
        for item in model.get("levels", []) or []
        if isinstance(item, dict) and item.get("id")
    ]
    required_upper_levels = set(canonical_levels[1:])
    if isinstance(brief_level_count, (int, float)) and brief_level_count > 1 and not required_upper_levels:
        required_upper_levels = {"upper-level"}
    canonical_connector_ids = {
        str(item.get("id"))
        for collection in ("stairs", "verticalConnectors")
        for item in model.get(collection, []) or []
        if isinstance(item, dict) and item.get("id")
    }
    connected_upper_levels: set[str] = set()
    for connection in vertical_access:
        if not isinstance(connection, dict):
            findings.append(
                _finding(
                    "LLM_VERTICAL_ACCESS_ENTRY_INVALID",
                    "Every vertical-access proposal must be a typed object.",
                )
            )
            continue
        from_level = str(connection.get("fromLevel") or connection.get("fromLevelId") or "").strip()
        to_level = str(connection.get("toLevel") or connection.get("toLevelId") or "").strip()
        object_id = str(connection.get("objectId") or connection.get("connectorId") or "").strip()
        if not from_level or not to_level or not object_id:
            findings.append(
                _finding(
                    "LLM_VERTICAL_ACCESS_FIELDS_REQUIRED",
                    "A vertical-access proposal needs fromLevel, toLevel, and objectId.",
                    severity="BLOCKER",
                )
            )
            continue
        if object_id not in canonical_connector_ids:
            findings.append(
                _finding(
                    "LLM_VERTICAL_ACCESS_CONNECTOR_UNKNOWN",
                    f"Vertical-access proposal references unknown canonical connector {object_id}.",
                    severity="REVIEW_REQUIRED",
                    object_id=object_id,
                )
            )
        if to_level in required_upper_levels:
            connected_upper_levels.add(to_level)

    if brief_level_count and brief_level_count > 1:
        missing_upper_levels = sorted(required_upper_levels - connected_upper_levels)
        if missing_upper_levels:
            findings.append(
                _finding(
                    "LLM_UPPER_FLOOR_ACCESS_REQUIRED",
                    "Upper-floor access must identify a canonical stair, lift, or ramp before rendering.",
                    severity="BLOCKER",
                )
            )
            compiler_shape["missingTopologyFacts"].append(
                "Identify a typed stair, lift, or ramp for every upper level before rendering."
            )
        else:
            compiler_shape["missingTopologyFacts"] = [
                item
                for item in compiler_shape.get("missingTopologyFacts", [])
                if "which stair, lift, or ramp" not in item
            ]
    compiler_shape["missingTopologyFacts"] = list(dict.fromkeys(compiler_shape["missingTopologyFacts"]))
    compiler_shape["readyForGeneration"] = not compiler_shape["missingTopologyFacts"]
    compiler_shape["status"] = "ready" if compiler_shape["readyForGeneration"] else "needs-review"

    proposals = payload.get("proposedRevisions")
    if not isinstance(proposals, list):
        proposals = []
    revision_previews: list[dict[str, Any]] = []
    accepted_revision: dict[str, Any] | None = None
    accepted_model: dict[str, Any] | None = None
    for proposal in proposals:
        if isinstance(proposal, str):
            command_text = proposal.strip()
            accept_requested = False
            timestamp = "2026-09-20T00:00:00+05:30"
        elif isinstance(proposal, dict):
            command_text = str(proposal.get("commandText") or proposal.get("text") or proposal.get("command") or "").strip()
            accept_requested = proposal.get("accept") is True
            timestamp = str(proposal.get("timestamp") or "2026-09-20T00:00:00+05:30")
        else:
            command_text = ""
            accept_requested = False
            timestamp = "2026-09-20T00:00:00+05:30"
        if not command_text:
            findings.append(
                _finding(
                    "LLM_REVISION_COMMAND_REQUIRED",
                    "Each proposed revision must contain supported command text.",
                    severity="REVIEW_REQUIRED",
                )
            )
            continue
        preview = _brief_revision_preview(model, command_text, timestamp=timestamp)
        preview["acceptanceRequested"] = accept_requested
        revision_previews.append(preview)
        if accept_requested:
            if accepted_revision is not None:
                findings.append(
                    _finding(
                        "LLM_SINGLE_ACCEPT_OPERATION_REQUIRED",
                        "Accept one typed revision at a time so each accepted revision can be validated.",
                        severity="REVIEW_REQUIRED",
                    )
                )
                continue
            if preview.get("status") != "ready":
                findings.append(
                    _finding(
                        "LLM_REVISION_REQUIRES_REVIEW",
                        "A revision with unresolved command findings cannot be accepted for rendering.",
                        severity="BLOCKER",
                    )
                )
                continue
            accepted = accept_revision(model, preview)
            accepted_model = accepted["model"]
            accepted_revision = accepted["revision"]

    if revision_previews and accepted_revision is None:
        findings.append(
            _finding(
                "LLM_ACCEPT_REVISION_REQUIRED",
                "Typed model changes require an explicit accept operation before they can be applied.",
                severity="REVIEW_REQUIRED",
            )
        )

    validation_report = payload.get("validationReport")
    if not isinstance(validation_report, dict):
        validation_report = {}
        findings.append(
            _finding(
                "LLM_VALIDATION_REPORT_REQUIRED",
                "Brief refinement must retain a validation report before presentation output.",
                severity="REVIEW_REQUIRED",
            )
        )
    validation_status = str(validation_report.get("status") or "").strip()
    if validation_status not in {"pass", "review-required", "blocked"}:
        findings.append(
            _finding(
                "LLM_VALIDATION_STATUS_REQUIRED",
                "Validation evidence must declare pass, review-required, or blocked.",
                severity="REVIEW_REQUIRED",
            )
        )
    if not str(validation_report.get("signature") or "").strip():
        findings.append(
            _finding(
                "LLM_VALIDATION_SIGNATURE_REQUIRED",
                "Validation evidence must retain a deterministic validation signature.",
                severity="REVIEW_REQUIRED",
            )
        )
    if accepted_revision is not None:
        accepted_revision_number = accepted_revision.get("afterRevision")
        if validation_report.get("modelRevision") != accepted_revision_number:
            findings.append(
                _finding(
                    "LLM_VALIDATION_RERUN_REQUIRED",
                    "Accepted typed revisions require validation evidence for the resulting model revision.",
                    severity="BLOCKER",
                )
            )
        if validation_status != "pass":
            findings.append(
                _finding(
                    "LLM_VALIDATION_MUST_PASS_BEFORE_RENDER",
                    "A typed revision cannot reach presentation while its validation report is not pass.",
                    severity="BLOCKER",
                )
            )

    clarification_questions = list(compiler_shape.get("missingTopologyFacts") or [])
    clarification_state = {
        "status": "blocked" if any(item["severity"] in {"BLOCKER", "ERROR"} for item in findings) else (
            "required" if clarification_questions else "resolved"
        ),
        "questions": clarification_questions,
        "source": "week12-brief-compiler",
    }
    has_blocker = any(item["severity"] in {"BLOCKER", "ERROR"} for item in findings)
    status = "blocked" if has_blocker else (
        "review-required"
        if findings or clarification_questions or compiler_shape.get("status") != "ready"
        else "pass"
    )
    return {
        "version": LLM_BRIEF_INPUT_VERSION,
        "tool": "ChatGPT / Claude / Grok / Gemini",
        "provider": provider,
        "model": payload.get("model"),
        "sourceReference": source_reference,
        "modelRevision": model_revision,
        "canonicalModelRevision": model_revision,
        "input": normalized,
        "sourceText": brief_text,
        "compilerShape": compiler_shape,
        "assumptions": list(dict.fromkeys(
            list(compiler_shape.get("assumptions") or [])
            + [str(item) for item in payload.get("assumptions") or []]
        )),
        "clarificationState": clarification_state,
        "proposedRevisions": revision_previews,
        "acceptedRevision": accepted_revision,
        "acceptedModelRevision": accepted_model.get("project", {}).get("revision") if accepted_model else None,
        "validationReport": copy.deepcopy(validation_report),
        "findings": findings,
        "status": status,
        "candidateEligible": status == "pass",
        "authoritativeGeometryChanged": False,
        "promotionPolicy": "explicit typed revision acceptance plus validation rerun is required before presentation",
        "determinism": {"algorithm": "sha256", "signature": _signature({
            "sourceText": brief_text,
            "compilerShape": compiler_shape,
            "proposedRevisions": revision_previews,
            "validationReport": validation_report,
        })},
    }


def validate_4lines_input(
    model: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_reference: str,
    model_revision: Any,
) -> dict[str, Any]:
    """Validate a traceable 4Lines.ai plan/section/elevation exchange."""

    normalized = ingest_ai_tool_input(
        "4lines-plan-section-workflow",
        source_input=payload,
        source_reference=source_reference,
        model_revision=model_revision,
    )
    findings: list[dict[str, Any]] = []
    canonical_objects = _canonical_view_objects(model)
    canonical_levels = {
        str(item.get("id"))
        for item in model.get("levels", []) or []
        if isinstance(item, dict) and item.get("id")
    }
    imported_revision = payload.get("modelRevision")
    if imported_revision != model_revision:
        findings.append(
            _finding(
                "FOURLINES_MODEL_REVISION_STALE",
                f"4Lines.ai exchange revision {imported_revision!r} does not match canonical revision {model_revision!r}.",
                severity="BLOCKER",
            )
        )
    exchange_reference = str(payload.get("exchangeReference") or payload.get("exportReference") or "").strip()
    if not exchange_reference:
        findings.append(
            _finding(
                "FOURLINES_EXCHANGE_REFERENCE_REQUIRED",
                "The 4Lines.ai exchange must retain an import/export reference.",
                severity="BLOCKER",
            )
        )

    provenance = payload.get("validationProvenance")
    if not isinstance(provenance, dict):
        provenance = {}
        findings.append(
            _finding(
                "FOURLINES_VALIDATION_PROVENANCE_REQUIRED",
                "Every exchange must retain validation provenance from the canonical model.",
                severity="BLOCKER",
            )
        )
    if provenance.get("status") != "pass":
        findings.append(
            _finding(
                "FOURLINES_VALIDATED_REVISION_REQUIRED",
                "4Lines.ai views cannot be accepted without pass validation provenance.",
                severity="BLOCKER",
            )
        )
    if provenance.get("modelRevision") != model_revision:
        findings.append(
            _finding(
                "FOURLINES_VALIDATION_REVISION_MISMATCH",
                "Validation provenance must reference the same canonical model revision.",
                severity="BLOCKER",
            )
        )
    if not str(provenance.get("signature") or "").strip():
        findings.append(
            _finding(
                "FOURLINES_VALIDATION_SIGNATURE_REQUIRED",
                "Validation provenance must include a validation signature.",
                severity="BLOCKER",
            )
        )

    object_id_map = payload.get("objectIdMap")
    if not isinstance(object_id_map, list) or not object_id_map:
        object_id_map = []
        findings.append(
            _finding(
                "FOURLINES_OBJECT_ID_MAP_REQUIRED",
                "The exchange must provide source-to-canonical object identity mappings.",
                severity="BLOCKER",
            )
        )
    mapped_canonical_ids: list[str] = []
    source_ids: set[str] = set()
    for mapping in object_id_map:
        if not isinstance(mapping, dict):
            findings.append(
                _finding(
                    "FOURLINES_OBJECT_ID_MAP_INVALID",
                    "Every 4Lines.ai object mapping must be an object.",
                    severity="REVIEW_REQUIRED",
                )
            )
            continue
        source_id = str(mapping.get("sourceObjectId") or "").strip()
        canonical_id = str(mapping.get("canonicalObjectId") or "").strip()
        if not source_id or not canonical_id:
            findings.append(
                _finding(
                    "FOURLINES_OBJECT_ID_FIELDS_REQUIRED",
                    "Every object mapping needs sourceObjectId and canonicalObjectId.",
                    severity="REVIEW_REQUIRED",
                )
            )
            continue
        if source_id in source_ids or canonical_id in mapped_canonical_ids:
            findings.append(
                _finding(
                    "FOURLINES_DUPLICATE_OBJECT_MAPPING",
                    f"Object identity mapping for {canonical_id or source_id} is duplicated.",
                    severity="BLOCKER",
                    object_id=canonical_id or source_id,
                )
            )
        source_ids.add(source_id)
        mapped_canonical_ids.append(canonical_id)
        if canonical_id not in canonical_objects:
            findings.append(
                _finding(
                    "FOURLINES_UNKNOWN_OBJECT_ID",
                    f"4Lines.ai mapping references unknown canonical object {canonical_id}.",
                    severity="BLOCKER",
                    object_id=canonical_id,
                )
            )

    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        dimensions = []
        findings.append(
            _finding(
                "FOURLINES_DIMENSIONS_REQUIRED",
                "The exchange must include dimension evidence tied to canonical objects.",
                severity="REVIEW_REQUIRED",
            )
        )
    dimension_ids: set[str] = set()
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            findings.append(_finding("FOURLINES_DIMENSION_INVALID", "Each dimension must be an object.", severity="REVIEW_REQUIRED"))
            continue
        dimension_id = str(dimension.get("id") or "").strip()
        source_object_id = str(dimension.get("sourceObjectId") or dimension.get("objectId") or "").strip()
        units = str(dimension.get("units") or dimension.get("unit") or "").strip().lower()
        value = dimension.get("value")
        if dimension_id in dimension_ids:
            findings.append(_finding("FOURLINES_DUPLICATE_DIMENSION_ID", f"Dimension {dimension_id} is duplicated.", severity="BLOCKER"))
        dimension_ids.add(dimension_id)
        if (
            not dimension_id
            or not source_object_id
            or not isinstance(value, (int, float))
            or value <= 0
            or units not in {"inch", "in", "foot", "ft", "mm", "cm", "m"}
        ):
            findings.append(
                _finding(
                    "FOURLINES_DIMENSION_FIELDS_REQUIRED",
                    "Dimensions need a unique ID, positive value, supported units, and a canonical source object.",
                    severity="REVIEW_REQUIRED",
                )
            )
        elif source_object_id not in canonical_objects:
            findings.append(
                _finding(
                    "FOURLINES_DIMENSION_SOURCE_UNKNOWN",
                    f"Dimension {dimension_id} references unknown object {source_object_id}.",
                    severity="BLOCKER",
                    object_id=source_object_id,
                )
            )

    views = payload.get("views")
    if not isinstance(views, list) or not views:
        views = []
        findings.append(
            _finding(
                "FOURLINES_VIEWS_REQUIRED",
                "The exchange must contain plan, section, or elevation views.",
                severity="BLOCKER",
            )
        )
    view_summaries: list[dict[str, Any]] = []
    returned_ids: set[str] = set()
    seen_view_ids: set[str] = set()
    required_kinds = {"plan", "2d-plan", "section", "elevation"}
    for view in views:
        if not isinstance(view, dict):
            findings.append(_finding("FOURLINES_VIEW_INVALID", "Every returned view must be an object.", severity="BLOCKER"))
            continue
        view_id = str(view.get("id") or "").strip()
        kind = str(view.get("kind") or view.get("viewType") or "").strip().lower()
        if not view_id or view_id in seen_view_ids:
            findings.append(_finding("FOURLINES_DUPLICATE_VIEW_ID", f"View ID {view_id or '<missing>'} is duplicated.", severity="BLOCKER"))
        seen_view_ids.add(view_id)
        if kind not in required_kinds:
            findings.append(
                _finding(
                    "FOURLINES_VIEW_KIND_UNSUPPORTED",
                    f"{view_id or 'unnamed view'} must be a plan, section, or elevation.",
                    severity="BLOCKER",
                )
            )
        level_values = view.get("levelIds")
        if not isinstance(level_values, list):
            level_values = [view.get("levelId")] if view.get("levelId") else []
        level_ids = [str(item).strip() for item in level_values if str(item).strip()]
        if not level_ids and kind in {"section", "elevation"}:
            findings.append(
                _finding(
                    "FOURLINES_VIEW_LEVELS_REQUIRED",
                    f"{view_id or 'unnamed view'} must declare its referenced levels.",
                    severity="BLOCKER",
                )
            )
        for level_id in level_ids:
            if level_id not in canonical_levels:
                findings.append(
                    _finding(
                        "FOURLINES_LEVEL_UNKNOWN",
                        f"{view_id or 'unnamed view'} references unknown level {level_id}.",
                        severity="BLOCKER",
                    )
                )
        if kind in {"section", "elevation"} and not str(view.get("referenceId") or view.get("reference") or "").strip():
            findings.append(
                _finding(
                    "FOURLINES_VIEW_REFERENCE_REQUIRED",
                    f"{view_id or 'unnamed view'} must retain a section/elevation reference.",
                    severity="REVIEW_REQUIRED",
                )
            )
        object_ids = view.get("objectIds")
        if not isinstance(object_ids, list) or not object_ids:
            object_ids = []
            findings.append(
                _finding(
                    "FOURLINES_VIEW_OBJECTS_REQUIRED",
                    f"{view_id or 'unnamed view'} must list its canonical object IDs.",
                    severity="BLOCKER",
                )
            )
        local_ids: set[str] = set()
        for object_id_value in object_ids:
            object_id = str(object_id_value)
            if object_id in local_ids:
                findings.append(
                    _finding(
                        "FOURLINES_DUPLICATE_OBJECT_ID",
                        f"{view_id or 'unnamed view'} repeats object {object_id}.",
                        severity="BLOCKER",
                        object_id=object_id,
                    )
                )
            local_ids.add(object_id)
            returned_ids.add(object_id)
            canonical = canonical_objects.get(object_id)
            if canonical is None:
                findings.append(
                    _finding(
                        "FOURLINES_UNKNOWN_OBJECT_ID",
                        f"{view_id or 'unnamed view'} references unknown canonical object {object_id}.",
                        severity="BLOCKER",
                        object_id=object_id,
                    )
                )
            elif level_ids and canonical.get("levelId") and canonical["levelId"] not in level_ids:
                findings.append(
                    _finding(
                        "FOURLINES_DISCONNECTED_OBJECT",
                        f"{view_id or 'unnamed view'} places {object_id} outside its declared level set.",
                        severity="BLOCKER",
                        object_id=object_id,
                    )
                )
        for ref_key in ("openingIds", "stairIds"):
            refs = view.get(ref_key, [])
            if not isinstance(refs, list):
                refs = []
                findings.append(
                    _finding(
                        "FOURLINES_VIEW_REFERENCES_INVALID",
                        f"{view_id or 'unnamed view'} {ref_key} must be a list.",
                        severity="REVIEW_REQUIRED",
                    )
                )
            for ref_id_value in refs:
                ref_id = str(ref_id_value)
                returned_ids.add(ref_id)
                if ref_id not in canonical_objects:
                    findings.append(
                        _finding(
                            "FOURLINES_UNKNOWN_OBJECT_ID",
                            f"{view_id or 'unnamed view'} references unknown canonical object {ref_id}.",
                            severity="BLOCKER",
                            object_id=ref_id,
                        )
                    )
        for dimension_ref in view.get("dimensionRefs", []) or []:
            if str(dimension_ref) not in dimension_ids:
                findings.append(
                    _finding(
                        "FOURLINES_DIMENSION_REFERENCE_UNKNOWN",
                        f"{view_id or 'unnamed view'} references unknown dimension {dimension_ref}.",
                        severity="REVIEW_REQUIRED",
                    )
                )
        view_summaries.append(
            {
                "id": view_id,
                "kind": kind,
                "levelIds": level_ids,
                "objectIds": [str(item) for item in object_ids],
                "referenceId": view.get("referenceId") or view.get("reference"),
                "status": "reviewed",
            }
        )

    expected_ids = payload.get("expectedObjectIds")
    if not isinstance(expected_ids, list) or not expected_ids:
        expected_ids = list(dict.fromkeys(mapped_canonical_ids))
    missing_ids = sorted({str(item) for item in expected_ids} - returned_ids)
    for object_id in missing_ids:
        findings.append(
            _finding(
                "FOURLINES_OBJECT_MISSING",
                f"Expected canonical object {object_id} is absent from returned views.",
                severity="BLOCKER",
                object_id=object_id,
            )
        )
    kinds_present = {item["kind"] for item in view_summaries}
    for required_kind in ("plan", "section", "elevation"):
        if required_kind not in kinds_present and not (required_kind == "plan" and "2d-plan" in kinds_present):
            findings.append(
                _finding(
                    "FOURLINES_REQUIRED_VIEW_MISSING",
                    f"The exchange must include a {required_kind} view.",
                    severity="REVIEW_REQUIRED",
                )
            )

    invalidation_reasons = sorted({item["rule"] for item in findings})
    has_blocker = any(item["severity"] in {"BLOCKER", "ERROR"} for item in findings)
    status = "blocked" if has_blocker else "review-required" if findings else "pass"
    return {
        "version": FOURLINES_INPUT_VERSION,
        "tool": "4Lines.ai",
        "sourceReference": source_reference,
        "modelRevision": model_revision,
        "canonicalModelRevision": model_revision,
        "importedModelRevision": imported_revision,
        "input": normalized,
        "exchangeReference": exchange_reference,
        "validationProvenance": copy.deepcopy(provenance),
        "objectIdMap": copy.deepcopy(object_id_map),
        "dimensions": copy.deepcopy(dimensions),
        "views": view_summaries,
        "expectedObjectIds": [str(item) for item in expected_ids],
        "missingObjectIds": missing_ids,
        "invalidation": {
            "invalidated": bool(invalidation_reasons),
            "reasons": invalidation_reasons,
        },
        "findings": findings,
        "status": status,
        "candidateEligible": status == "pass",
        "presentationOnly": True,
        "authoritativeGeometryChanged": False,
        "determinism": {"algorithm": "sha256", "signature": _signature({
            "sourceReference": source_reference,
            "modelRevision": model_revision,
            "objectIdMap": object_id_map,
            "dimensions": dimensions,
            "views": views,
            "validationProvenance": provenance,
        })},
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
    floorplanner = None
    if FLOORPLANNER_FIXTURE_PATH.is_file():
        floorplanner_payload = json.loads(FLOORPLANNER_FIXTURE_PATH.read_text(encoding="utf-8"))
        floorplanner = validate_floorplanner_input(
            model,
            floorplanner_payload,
            source_reference=str(floorplanner_payload.get("sourceReference", "floorplanner-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    roomstyler = None
    if ROOMSTYLER_FIXTURE_PATH.is_file():
        roomstyler_payload = json.loads(ROOMSTYLER_FIXTURE_PATH.read_text(encoding="utf-8"))
        roomstyler = validate_roomstyler_homestyler_input(
            model,
            roomstyler_payload,
            source_reference=str(roomstyler_payload.get("sourceReference", "roomstyler-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    magicplan = None
    if MAGICPLAN_FIXTURE_PATH.is_file():
        magicplan_payload = json.loads(MAGICPLAN_FIXTURE_PATH.read_text(encoding="utf-8"))
        magicplan = validate_magicplan_input(
            model,
            magicplan_payload,
            source_reference=str(magicplan_payload.get("sourceReference", "magicplan-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    llm_brief = None
    if LLM_BRIEF_FIXTURE_PATH.is_file():
        llm_brief_payload = json.loads(LLM_BRIEF_FIXTURE_PATH.read_text(encoding="utf-8"))
        llm_brief = validate_llm_brief_input(
            model,
            llm_brief_payload,
            source_reference=str(llm_brief_payload.get("sourceReference", "llm-brief-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    fourlines = None
    if FOURLINES_FIXTURE_PATH.is_file():
        fourlines_payload = json.loads(FOURLINES_FIXTURE_PATH.read_text(encoding="utf-8"))
        fourlines = validate_4lines_input(
            model,
            fourlines_payload,
            source_reference=str(fourlines_payload.get("sourceReference", "4lines-fixture")),
            model_revision=model.get("project", {}).get("revision"),
        )
    return {
        "status": "blocked"
        if furnishings["status"] == "blocked"
        or candidates["status"] == "blocked"
        or (archistar_snaptrude and archistar_snaptrude["status"] == "blocked")
        or (floorplanner and floorplanner["status"] == "blocked")
        or (roomstyler and roomstyler["status"] == "blocked")
        or (magicplan and magicplan["status"] == "blocked")
        or (llm_brief and llm_brief["status"] == "blocked")
        or (fourlines and fourlines["status"] == "blocked")
        else "pass",
        "aiToolInputs": ai_tool_input_manifest(),
        "week15": furnishings,
        "week16": candidates,
        "planner5d": planner5d,
        "archistarSnaptrude": archistar_snaptrude,
        "floorplanner": floorplanner,
        "roomstyler": roomstyler,
        "magicplan": magicplan,
        "llmBrief": llm_brief,
        "fourlines": fourlines,
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
    model["floorplannerSynchronizedView"] = {"version": FLOORPLANNER_INPUT_VERSION, "report": str(FLOORPLANNER_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["floorplanner"]["candidateEligible"], "status": report["floorplanner"]["status"], "synchronizationStatus": report["floorplanner"]["synchronizationStatus"]}
    model["roomstylerPresentation"] = {"version": ROOMSTYLER_INPUT_VERSION, "report": str(ROOMSTYLER_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["roomstyler"]["candidateEligible"], "status": report["roomstyler"]["status"]}
    model["magicplanRecognitionQueue"] = {"version": MAGICPLAN_INPUT_VERSION, "report": str(MAGICPLAN_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["magicplan"]["candidateEligible"], "status": report["magicplan"]["status"], "promotedObjectCount": len(report["magicplan"]["promotedObjects"])}
    model["llmBriefRefinement"] = {"version": LLM_BRIEF_INPUT_VERSION, "report": str(LLM_BRIEF_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["llmBrief"]["candidateEligible"], "status": report["llmBrief"]["status"], "acceptedRevisionId": (report["llmBrief"].get("acceptedRevision") or {}).get("id")}
    model["fourlinesPlanSectionExchange"] = {"version": FOURLINES_INPUT_VERSION, "report": str(FOURLINES_REPORT_PATH.relative_to(ROOT)), "candidateEligible": report["fourlines"]["candidateEligible"], "status": report["fourlines"]["status"], "invalidation": report["fourlines"]["invalidation"]}
    model["designPresentation"] = report["designPackage"]
    ASSET_REPORT_PATH.write_text(json.dumps(report["week15"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    AI_INPUT_REPORT_PATH.write_text(json.dumps(report["aiToolInputs"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CANDIDATE_REPORT_PATH.write_text(json.dumps({"aiToolInputs": report["aiToolInputs"], "candidateStudio": report["week16"], "designPackage": report["designPackage"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PLANNER5D_REPORT_PATH.write_text(json.dumps(report["planner5d"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARCHISTAR_REPORT_PATH.write_text(json.dumps(report["archistarSnaptrude"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    FLOORPLANNER_REPORT_PATH.write_text(json.dumps(report["floorplanner"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ROOMSTYLER_REPORT_PATH.write_text(json.dumps(report["roomstyler"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MAGICPLAN_REPORT_PATH.write_text(json.dumps(report["magicplan"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    LLM_BRIEF_REPORT_PATH.write_text(json.dumps(report["llmBrief"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    FOURLINES_REPORT_PATH.write_text(json.dumps(report["fourlines"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps({"manifestVersion": "week1516.enrichment-manifest.v1", "status": report["status"], "reports": {"week15": str(ASSET_REPORT_PATH.relative_to(ROOT)), "week16": str(CANDIDATE_REPORT_PATH.relative_to(ROOT)), "planner5d": str(PLANNER5D_REPORT_PATH.relative_to(ROOT)), "archistarSnaptrude": str(ARCHISTAR_REPORT_PATH.relative_to(ROOT)), "floorplanner": str(FLOORPLANNER_REPORT_PATH.relative_to(ROOT)), "roomstyler": str(ROOMSTYLER_REPORT_PATH.relative_to(ROOT)), "magicplan": str(MAGICPLAN_REPORT_PATH.relative_to(ROOT)), "llmBrief": str(LLM_BRIEF_REPORT_PATH.relative_to(ROOT)), "fourlines": str(FOURLINES_REPORT_PATH.relative_to(ROOT)), "aiToolInputs": str(AI_INPUT_REPORT_PATH.relative_to(ROOT))}, "changelog": str(CHANGELOG_PATH.relative_to(ROOT)), "catalogVersion": WEEK15_VERSION, "candidateVersion": WEEK16_VERSION, "planner5dVersion": PLANNER5D_INPUT_VERSION, "archistarSnaptrudeVersion": ARCHISTAR_INPUT_VERSION, "floorplannerVersion": FLOORPLANNER_INPUT_VERSION, "roomstylerVersion": ROOMSTYLER_INPUT_VERSION, "magicplanVersion": MAGICPLAN_INPUT_VERSION, "llmBriefVersion": LLM_BRIEF_INPUT_VERSION, "fourlinesVersion": FOURLINES_INPUT_VERSION, "aiToolInputCatalogVersion": AI_INPUT_VERSION, "bestCandidateId": report["week16"]["bestCandidateId"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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

### W16-04 implementation status — Floorplanner

- Added a synchronized 2D/3D view fixture with level visibility, room and
  opening IDs, stair references, export provenance, model revision, and
  validation evidence.
- Added `validate_floorplanner_input`, which reuses the Week 14 canonical view
  contract and rejects unknown IDs, incomplete level coverage, stale revisions,
  and missing validation signatures from silent acceptance.
- Accepted view edits require a post-edit model revision and validation rerun
  signature; view data remains presentation-only and cannot mutate geometry.

### W16-07 implementation status — ChatGPT / Claude / Grok / Gemini

- Added a provider-neutral conversation fixture containing a natural-language
  brief, constraints, candidate feedback, typed vertical access, and a
  validation report.
- Added `validate_llm_brief_input`, which delegates extraction and command
  previews to the Week 12 compiler, preserves assumptions and clarification
  questions, and records provider/model metadata only as provenance.
- Typed revisions require an explicit `accept` operation and a validation rerun
  for the resulting revision; incomplete upper-floor access is a blocker before
  rendering, and the canonical input model remains unchanged.

### W16-08 implementation status — 4Lines.ai

- Added a plan/section/elevation exchange fixture with source-to-canonical
  object IDs, levels, openings, dimensions, section references, and validation
  provenance.
- Added `validate_4lines_input`, which detects stale revisions, missing or
  duplicated object identity, unknown/disconnected objects, missing dimensions,
  and absent view references.
- Returned views are invalidated unless they trace to the validated canonical
  model revision; the exchange remains presentation-only.
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