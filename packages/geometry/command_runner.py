"""Transactional command execution for the phase-two vertical slice."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .commands import CommandEnvelope, CommandValidationError, command_fingerprint, finding
from .constraints import (
    quick_validate,
    unique_id,
    validate_level_reference,
    validate_opening_position,
    validate_space_geometry,
)
from .revisions import (
    RevisionSummary,
    commit_revision,
    model_revision,
    revision_conflict_finding,
)
from .serializers import clone_json, sha256
from .topology import find_object, level_exists


@dataclass
class CommandResult:
    accepted: bool
    replayed: bool
    model: dict[str, Any] | None
    findings: list[dict[str, Any]]
    summary: RevisionSummary | None
    affected_object_ids: list[str]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "replayed": self.replayed,
            "model": self.model,
            "findings": self.findings,
            "summary": self.summary.to_mapping() if self.summary else None,
            "affectedObjectIds": self.affected_object_ids,
        }


@dataclass(frozen=True)
class _Replay:
    fingerprint: str
    result: CommandResult


class CommandRunner:
    """Run one command atomically and retain accepted idempotent results."""

    def __init__(self, engine_version: str = "phase2.command-engine.v1") -> None:
        self.engine_version = engine_version
        self._idempotency: dict[tuple[str, str], _Replay] = {}

    def execute(
        self, model: dict[str, Any] | None, raw_command: CommandEnvelope | dict[str, Any]
    ) -> CommandResult:
        try:
            command = (
                raw_command
                if isinstance(raw_command, CommandEnvelope)
                else CommandEnvelope.from_mapping(raw_command)
            )
        except CommandValidationError as exc:
            return CommandResult(False, False, deepcopy(model), exc.findings, None, [])

        key = (command.project_id, command.idempotency_key)
        fingerprint = command_fingerprint(command)
        prior = self._idempotency.get(key)
        if prior is not None:
            if prior.fingerprint != fingerprint:
                return CommandResult(
                    False,
                    False,
                    deepcopy(model),
                    [
                        finding(
                            rule="IDEMPOTENCY_KEY_REUSE",
                            message="idempotency key was already used for different parameters",
                            severity="BLOCKER",
                            evidence={"projectId": command.project_id},
                        )
                    ],
                    None,
                    [],
                )
            replay = deepcopy(prior.result)
            replay.replayed = True
            return replay

        if command.operation == "create-project":
            result = self._create_project(command, model)
        else:
            result = self._execute_existing(model, command)
        if result.accepted:
            self._idempotency[key] = _Replay(fingerprint, deepcopy(result))
        return result

    def _execute_existing(
        self, model: dict[str, Any] | None, command: CommandEnvelope
    ) -> CommandResult:
        if model is None:
            return CommandResult(
                False,
                False,
                None,
                [
                    finding(
                        rule="MODEL_REQUIRED",
                        message="a canonical model is required for this operation",
                        severity="BLOCKER",
                    )
                ],
                None,
                [],
            )
        current = model_revision(model)
        if current is None:
            return CommandResult(
                False,
                False,
                deepcopy(model),
                [finding(rule="MODEL_REVISION", message="canonical model has no valid revision", severity="BLOCKER")],
                None,
                [],
            )
        if command.base_revision != current:
            return CommandResult(
                False,
                False,
                deepcopy(model),
                [revision_conflict_finding(command.base_revision, current)],
                None,
                [],
            )
        working = clone_json(model)
        changed: list[str] = []
        findings = self._apply(working, command, changed)
        if findings:
            return CommandResult(False, False, deepcopy(model), findings, None, changed)
        validation = quick_validate(working)
        if validation:
            return CommandResult(False, False, deepcopy(model), validation, None, changed)
        summary = commit_revision(working, command, changed)
        return CommandResult(True, False, working, [], summary, list(summary.changed_object_ids))

    def _create_project(
        self, command: CommandEnvelope, model: dict[str, Any] | None
    ) -> CommandResult:
        if model is not None:
            return CommandResult(
                False,
                False,
                deepcopy(model),
                [finding(rule="PROJECT_EXISTS", message="cannot create a project over an existing model", severity="BLOCKER")],
                None,
                [],
            )
        parameters = command.parameters
        name = parameters.get("name")
        if not isinstance(name, str) or not name.strip():
            return CommandResult(
                False,
                False,
                None,
                [finding(rule="PROJECT_NAME_REQUIRED", message="project name is required", severity="BLOCKER")],
                None,
                [],
            )
        level_id = parameters.get("levelId", "GF")
        model = {
            "schemaVersion": "advocate-chambers.project.v2",
            "project": {
                "id": command.project_id,
                "name": name.strip(),
                "location": parameters.get("location", ""),
                "status": "draft",
                "revision": 1,
                "source": command.source if command.source in {"user", "generator", "import", "survey", "legacy"} else "user",
                "legacy": {},
            },
            "units": "inch",
            "wallThickness": float(parameters.get("wallThickness", 6)),
            "site": {
                "id": "SITE",
                "kind": "site",
                "levelId": "SITE",
                "geometry": {"plotVertices": [[0, 0], [1, 0], [1, 1], [0, 1]]},
                "source": "user",
                "status": "draft",
                "revision": 1,
                "provenance": {"sourcePath": "command", "sourceId": "SITE", "migration": "week2.legacy-to-v2", "legacyKeys": []},
                "legacy": {},
            },
            "levels": [],
            "spaces": [],
            "openings": [],
            "windows": [],
            "entries": [],
            "circulationZones": [],
            "exteriorZones": [],
            "verticalConnectors": [],
            "stairs": [],
            "assumptions": [],
            "notes": [],
            "revisions": [
                {
                    "id": "R1",
                    "date": command.client_timestamp or "1970-01-01T00:00:00+00:00",
                    "author": command.author_id,
                    "summary": command.reason or "Create project",
                    "source": command.source,
                    "legacy": {"commandId": command.command_id},
                }
            ],
        }
        level = self._new_level(level_id, parameters, 1)
        model["levels"].append(level)
        model["program"] = {
            "buildingType": parameters.get("buildingType", "unspecified"),
            "templateVersion": "command.v1",
            "requiredUses": [],
            "adjacencyRules": [],
        }
        model["orientation"] = {"north": "up", "source": "command"}
        return CommandResult(
            True,
            False,
            model,
            [],
            RevisionSummary(
                1,
                "R1",
                command.project_id,
                command.command_id,
                command.operation,
                ("GF" if level_id == "GF" else level_id,),
                sha256(model),
                command.reason or "Create project",
            ),
            [level_id],
        )

    def _apply(
        self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]
    ) -> list[dict[str, Any]]:
        operation = command.operation
        if operation in {"add-wall", "split-wall", "apply-furniture-operation"}:
            return [
                finding(
                    rule="CANONICAL_GEOMETRY_UNSUPPORTED",
                    message=f"{operation} is not supported by project.v2 without an authoritative wall/furniture schema",
                    severity="BLOCKER",
                    professional_review_required=True,
                )
            ]
        handlers: dict[str, Callable[[dict[str, Any], CommandEnvelope, list[str]], list[dict[str, Any]]]] = {
            "add-level": self._add_level,
            "add-space": self._add_space,
            "resize-space": self._resize_space,
            "move-opening": self._move_opening,
            "resize-opening": self._resize_opening,
            "add-window": self._add_window,
            "add-stair": self._add_stair,
            "set-site-orientation": self._set_site_orientation,
            "set-program-requirement": self._set_program_requirement,
        }
        return handlers[operation](model, command, changed)

    @staticmethod
    def _new_base(object_id: str, kind: str, level_id: str) -> dict[str, Any]:
        return {
            "id": object_id,
            "kind": kind,
            "levelId": level_id,
            "source": "user",
            "status": "draft",
            "revision": 1,
            "provenance": {
                "sourcePath": "command",
                "sourceId": object_id,
                "migration": "week2.legacy-to-v2",
                "legacyKeys": [],
            },
            "legacy": {},
        }

    def _new_level(self, level_id: str, p: dict[str, Any], revision: int) -> dict[str, Any]:
        return {
            "id": level_id,
            "name": p.get("name", level_id),
            "elevation": p.get("elevation", 0),
            "floorToFloor": p.get("floorToFloor", 120),
            "source": "user",
            "status": "draft",
            "revision": revision,
            "provenance": {"sourcePath": "command", "sourceId": level_id, "migration": "week2.legacy-to-v2", "legacyKeys": []},
            "legacy": {},
        }

    def _add_level(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        p = command.parameters
        object_id = p.get("levelId", p.get("id"))
        if not isinstance(object_id, str) or not object_id:
            return [finding(rule="LEVEL_ID_REQUIRED", message="levelId is required", severity="BLOCKER")]
        if level_exists(model, object_id):
            return [finding(rule="LEVEL_ID_UNIQUE", message=f"level '{object_id}' already exists", severity="BLOCKER", object_ids=[object_id])]
        try:
            level = self._new_level(object_id, p, model_revision(model) or 1)
        except (TypeError, ValueError):
            return [finding(rule="LEVEL_DIMENSIONS_NUMERIC", message="level elevation and floorToFloor must be numeric", severity="BLOCKER")]
        if float(level["floorToFloor"]) <= 0:
            return [finding(rule="FLOOR_TO_FLOOR_POSITIVE", message="floorToFloor must be positive", severity="BLOCKER", object_ids=[object_id])]
        model.setdefault("levels", []).append(level)
        changed.append(object_id)
        return []

    def _add_space(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        p = command.parameters
        object_id = p.get("spaceId", p.get("id"))
        if not isinstance(object_id, str) or not object_id:
            return [finding(rule="SPACE_ID_REQUIRED", message="spaceId is required", severity="BLOCKER")]
        duplicate = unique_id(model, object_id)
        if duplicate:
            return [duplicate]
        errors = validate_level_reference(model, p.get("levelId"))
        errors += validate_space_geometry(p.get("rect"), object_id)
        if errors:
            return errors
        space = self._new_base(object_id, "space", p["levelId"])
        space.update({"name": p.get("name", object_id), "finish": p.get("finish", "private"), "geometry": {"rect": p["rect"]}})
        for key in ("roomUse", "accessIntent", "stairId"):
            if key in p:
                space[key] = p[key]
        model.setdefault("spaces", []).append(space)
        changed.append(object_id)
        return []

    def _resize_space(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        p = command.parameters
        object_id = p.get("spaceId", p.get("id"))
        space = find_object(model, "spaces", object_id) if isinstance(object_id, str) else None
        if space is None:
            return [finding(rule="SPACE_EXISTS", message="space does not exist", severity="BLOCKER", object_ids=[object_id] if isinstance(object_id, str) else [])]
        errors = validate_space_geometry(p.get("rect"), object_id)
        if errors:
            return errors
        space.setdefault("geometry", {})["rect"] = p["rect"]
        changed.append(object_id)
        return []

    def _opening_update(self, model: dict[str, Any], p: dict[str, Any], changed: list[str], resize: bool) -> list[dict[str, Any]]:
        object_id = p.get("openingId", p.get("id"))
        opening = find_object(model, "openings", object_id) if isinstance(object_id, str) else None
        if opening is None:
            return [finding(rule="OPENING_EXISTS", message="opening does not exist", severity="BLOCKER", object_ids=[object_id] if isinstance(object_id, str) else [])]
        geometry = opening.setdefault("geometry", {})
        wall = p.get("wall", opening.get("wall"))
        offset = p.get("offset", geometry.get("offset"))
        width = p.get("width", geometry.get("width"))
        errors = validate_opening_position(model, host_space_id=opening.get("hostSpace"), wall=wall, offset=offset, width=width, object_id=object_id)
        if errors:
            return errors
        opening["wall"] = wall
        geometry["offset"] = offset
        if resize or "width" in p:
            geometry["width"] = width
        changed.append(object_id)
        return []

    def _move_opening(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        return self._opening_update(model, command.parameters, changed, False)

    def _resize_opening(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        return self._opening_update(model, command.parameters, changed, True)

    def _add_window(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        p = command.parameters
        object_id = p.get("windowId", p.get("id"))
        if not isinstance(object_id, str) or not object_id:
            return [finding(rule="WINDOW_ID_REQUIRED", message="windowId is required", severity="BLOCKER")]
        duplicate = unique_id(model, object_id)
        if duplicate:
            return [duplicate]
        errors = validate_level_reference(model, p.get("levelId"))
        errors += validate_opening_position(model, host_space_id=p.get("hostSpace"), wall=p.get("wall"), offset=p.get("offset"), width=p.get("width"), object_id=object_id)
        if errors:
            return errors
        window = self._new_base(object_id, "window", p["levelId"])
        window.update({"tag": p.get("tag", object_id), "hostSpace": p["hostSpace"], "wall": p["wall"], "geometry": {"offset": p["offset"], "width": p["width"]}})
        if "height" in p:
            window["geometry"]["height"] = p["height"]
        window["accessIntent"] = p.get("accessIntent", "daylight-ventilation")
        model.setdefault("windows", []).append(window)
        changed.append(object_id)
        return []

    def _add_stair(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        p = command.parameters
        object_id = p.get("stairId", p.get("id"))
        if not isinstance(object_id, str) or not object_id:
            return [finding(rule="STAIR_ID_REQUIRED", message="stairId is required", severity="BLOCKER")]
        duplicate = unique_id(model, object_id)
        if duplicate:
            return [duplicate]
        errors = validate_level_reference(model, p.get("levelFrom")) + validate_level_reference(model, p.get("levelTo"))
        if errors:
            return errors
        connector_id = p.get("verticalConnectorId", f"VC-{object_id}")
        stair = self._new_base(object_id, "stair", p["levelFrom"])
        stair.update({
            "levelFrom": p["levelFrom"], "levelTo": p["levelTo"], "verticalConnectorId": connector_id,
            "configuration": p.get("configuration", "straight"), "turnDegrees": p.get("turnDegrees", 0),
            "geometry": p.get("geometry", {}),
        })
        connector = self._new_base(connector_id, "vertical-connector", p["levelFrom"])
        connector.update({
            "fromLevelId": p["levelFrom"], "toLevelId": p["levelTo"], "stairId": object_id,
            "departureSpaceId": p.get("departureSpaceId"), "arrivalSpaceId": p.get("arrivalSpaceId"),
            "accessIntent": "vertical",
        })
        model.setdefault("stairs", []).append(stair)
        model.setdefault("verticalConnectors", []).append(connector)
        changed.extend([object_id, connector_id])
        return []

    def _set_site_orientation(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        orientation = command.parameters.get("orientation", command.parameters)
        if not isinstance(orientation, dict) or not orientation:
            return [finding(rule="ORIENTATION_REQUIRED", message="orientation must be a non-empty object", severity="BLOCKER")]
        model["orientation"] = deepcopy(orientation)
        model["orientation"].setdefault("source", "command")
        changed.append("SITE")
        return []

    def _set_program_requirement(self, model: dict[str, Any], command: CommandEnvelope, changed: list[str]) -> list[dict[str, Any]]:
        p = command.parameters
        requirement = p.get("requirement")
        if not isinstance(requirement, dict) or not requirement:
            return [finding(rule="PROGRAM_REQUIREMENT_REQUIRED", message="requirement must be a non-empty object", severity="BLOCKER")]
        program = model.setdefault("program", {"buildingType": "unspecified", "templateVersion": "command.v1", "requiredUses": [], "adjacencyRules": []})
        requirements = program.setdefault("requiredUses", [])
        requirement_id = p.get("requirementId", requirement.get("id", requirement.get("roomUse")))
        if requirement_id is None:
            return [finding(rule="PROGRAM_REQUIREMENT_ID", message="requirementId or requirement.id/roomUse is required", severity="BLOCKER")]
        for index, existing in enumerate(requirements):
            if existing.get("id", existing.get("roomUse")) == requirement_id:
                requirements[index] = deepcopy(requirement)
                changed.append("PROGRAM")
                return []
        requirements.append(deepcopy(requirement))
        changed.append("PROGRAM")
        return []