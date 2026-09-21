"""Dependency-free tests for the typed phase-two command slice."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from packages.geometry.command_runner import CommandRunner
from packages.geometry.commands import CommandEnvelope, CommandValidationError
from packages.geometry.serializers import canonical_json, sha256
from packages.geometry.tolerances import is_close


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "bar-association-hall" / "standard" / "model" / "project.json"


def command(operation: str, key: str, base: int = 1, **parameters: object) -> dict[str, object]:
    return {
        "schemaVersion": "advocate-chambers.command.v1",
        "commandId": f"cmd-{key}",
        "projectId": "proj-bar-association-hall",
        "baseRevision": base,
        "authorId": "tester",
        "operation": operation,
        "parameters": parameters,
        "idempotencyKey": f"idem-{key}-01",
        "clientTimestamp": "2026-09-21T00:00:00+00:00",
    }


class Phase2CommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))

    def test_canonical_serialization_is_order_independent(self) -> None:
        left = {"b": 2, "a": [1.0000000000001, -0.0]}
        right = {"a": [1.0, 0], "b": 2}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(sha256(left), sha256(right))

    def test_tolerance_is_absolute_for_model_units(self) -> None:
        self.assertTrue(is_close(12.0, 12.0000005))
        self.assertFalse(is_close(12.0, 12.01))

    def test_command_envelope_rejects_missing_fields(self) -> None:
        with self.assertRaises(CommandValidationError):
            CommandEnvelope.from_mapping({"operation": "move-opening"})

    def test_create_project_builds_minimal_canonical_model(self) -> None:
        runner = CommandRunner()
        result = runner.execute(
            None,
            command("create-project", "create", name="Small Chambers", location="Banswara"),
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.model["schemaVersion"], "advocate-chambers.project.v2")
        self.assertEqual(result.model["project"]["revision"], 1)
        self.assertEqual(result.model["levels"][0]["id"], "GF")

    def test_create_project_rejects_existing_model(self) -> None:
        runner = CommandRunner()
        result = runner.execute(
            self.model,
            command("create-project", "create-existing", name="Should Not Replace"),
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.findings[0]["rule"], "PROJECT_EXISTS")

    def test_move_opening_creates_revision_and_summary(self) -> None:
        runner = CommandRunner()
        result = runner.execute(self.model, command("move-opening", "move", openingId="D-GF-01", wall="east", offset=80))
        self.assertTrue(result.accepted)
        self.assertEqual(result.summary.revision_number, 2)
        self.assertEqual(result.summary.changed_object_ids, ("D-GF-01",))
        self.assertEqual(result.model["project"]["revision"], 2)
        self.assertEqual(result.model["openings"][0]["geometry"]["offset"], 80)
        self.assertEqual(len(result.summary.model_sha256), 64)

    def test_replay_returns_identical_result_without_second_revision(self) -> None:
        runner = CommandRunner()
        request = command("move-opening", "replay", openingId="D-GF-01", wall="east", offset=80)
        first = runner.execute(self.model, request)
        second = runner.execute(self.model, request)
        self.assertTrue(first.accepted)
        self.assertTrue(second.replayed)
        self.assertEqual(first.to_mapping()["summary"], second.to_mapping()["summary"])
        self.assertEqual(first.model, second.model)

    def test_idempotency_key_collision_is_rejected(self) -> None:
        runner = CommandRunner()
        request = command("move-opening", "collision", openingId="D-GF-01", wall="east", offset=80)
        runner.execute(self.model, request)
        changed = copy.deepcopy(request)
        changed["parameters"] = {"openingId": "D-GF-01", "wall": "east", "offset": 90}
        result = runner.execute(self.model, changed)
        self.assertFalse(result.accepted)
        self.assertEqual(result.findings[0]["rule"], "IDEMPOTENCY_KEY_REUSE")

    def test_stale_revision_is_rejected_without_mutation(self) -> None:
        runner = CommandRunner()
        result = runner.execute(self.model, command("move-opening", "stale", base=99, openingId="D-GF-01", offset=80))
        self.assertFalse(result.accepted)
        self.assertEqual(result.findings[0]["rule"], "REVISION_CONFLICT")
        self.assertEqual(result.model, self.model)

    def test_opening_cannot_extend_past_host_wall(self) -> None:
        runner = CommandRunner()
        result = runner.execute(self.model, command("resize-opening", "span", openingId="D-GF-01", offset=150, width=100))
        self.assertFalse(result.accepted)
        self.assertEqual(result.findings[0]["rule"], "OPENING_WITHIN_HOST_WALL")

    def test_resize_opening_updates_width(self) -> None:
        runner = CommandRunner()
        result = runner.execute(
            self.model,
            command("resize-opening", "resize", openingId="D-GF-01", wall="east", offset=60, width=42),
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.model["openings"][0]["geometry"]["width"], 42)

    def test_add_level_and_space(self) -> None:
        runner = CommandRunner()
        level = runner.execute(self.model, command("add-level", "level", levelId="TF", name="Terrace", elevation=360, floorToFloor=120))
        self.assertTrue(level.accepted)
        updated = level.model
        space = runner.execute(updated, command("add-space", "space", base=2, spaceId="TF-01", levelId="TF", name="Terrace", finish="public", rect=[0, 0, 120, 120]))
        self.assertTrue(space.accepted)
        self.assertEqual(space.model["spaces"][-1]["id"], "TF-01")
        self.assertEqual(space.model["project"]["revision"], 3)

    def test_duplicate_space_id_is_rejected(self) -> None:
        runner = CommandRunner()
        result = runner.execute(
            self.model,
            command("add-space", "duplicate", spaceId="GF-01", levelId="GF", rect=[0, 0, 120, 120]),
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.findings[0]["rule"], "OBJECT_ID_UNIQUE")

    def test_add_window_and_stair_are_schema_shaped(self) -> None:
        runner = CommandRunner()
        window = runner.execute(self.model, command("add-window", "window", windowId="W-NEW", levelId="GF", hostSpace="GF-01", wall="south", offset=10, width=30))
        self.assertTrue(window.accepted)
        stair = runner.execute(self.model, command("add-stair", "stair", levelFrom="GF", levelTo="FF", stairId="STAIR-NEW", configuration="straight", geometry={"width": 42}))
        self.assertTrue(stair.accepted)
        self.assertEqual(stair.model["verticalConnectors"][-1]["stairId"], "STAIR-NEW")

    def test_orientation_and_program_requirement_are_revisioned(self) -> None:
        runner = CommandRunner()
        oriented = runner.execute(self.model, command("set-site-orientation", "orientation", orientation={"north": "right", "roadFrontage": "south"}))
        self.assertTrue(oriented.accepted)
        requirement = runner.execute(self.model, command("set-program-requirement", "program", requirement={"id": "library", "roomUse": "library", "minCount": 1}))
        self.assertTrue(requirement.accepted)
        self.assertEqual(requirement.model["program"]["requiredUses"][-1]["id"], "library")

    def test_unsupported_geometry_is_a_structured_blocker(self) -> None:
        runner = CommandRunner()
        result = runner.execute(self.model, command("split-wall", "wall", wallId="W-01"))
        self.assertFalse(result.accepted)
        self.assertEqual(result.findings[0]["rule"], "CANONICAL_GEOMETRY_UNSUPPORTED")
        self.assertIsNone(result.summary)

    def test_failed_operation_does_not_mutate_input(self) -> None:
        runner = CommandRunner()
        original = copy.deepcopy(self.model)
        runner.execute(self.model, command("resize-space", "bad", spaceId="GF-01", rect=[0, 0, 0, 100]))
        self.assertEqual(self.model, original)


if __name__ == "__main__":
    unittest.main()