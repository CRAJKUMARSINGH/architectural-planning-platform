"""Phase 1 contract smoke tests.

These tests intentionally use only the Python standard library so a clean
checkout can verify the contract package before optional validator dependencies
are installed.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "packages" / "schema"


class Phase1ContractTests(unittest.TestCase):
    def load_schema(self, name: str) -> dict[str, Any]:
        path = SCHEMA_ROOT / name
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        self.assertIsInstance(value, dict)
        return value

    def test_phase1_schema_files_are_parseable_and_versioned(self) -> None:
        expected = {
            "command.schema.json": "advocate-chambers.command.v1",
            "finding.schema.json": "advocate-chambers.finding.v1",
            "revision.schema.json": "advocate-chambers.revision.v1",
            "render-manifest.schema.json": "advocate-chambers.render-manifest.v1",
            "artifact-manifest.schema.json": "advocate-chambers.artifact-manifest.v1",
        }
        for filename, version in expected.items():
            with self.subTest(filename=filename):
                schema = self.load_schema(filename)
                self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["properties"]["schemaVersion"]["const"], version)
                self.assertTrue(schema["required"])
                self.assertFalse(schema.get("additionalProperties", True))

    def test_command_contract_has_replay_safety_fields(self) -> None:
        schema = self.load_schema("command.schema.json")
        required = set(schema["required"])
        self.assertTrue({"commandId", "projectId", "baseRevision", "parameters"} <= required)
        self.assertIn("idempotencyKey", required)
        self.assertIn("move-opening", schema["properties"]["operation"]["enum"])
        self.assertGreaterEqual(schema["properties"]["baseRevision"]["minimum"], 1)

    def test_finding_contract_carries_explainable_evidence(self) -> None:
        schema = self.load_schema("finding.schema.json")
        required = set(schema["required"])
        self.assertTrue({"severity", "rule", "message", "objectIds", "evidence"} <= required)
        self.assertEqual(
            schema["properties"]["severity"]["enum"],
            ["BLOCKER", "ERROR", "WARNING", "INFO"],
        )
        self.assertIn("professionalReviewRequired", required)

    def test_content_addressed_contracts_require_sha256(self) -> None:
        for filename in ("revision.schema.json", "artifact-manifest.schema.json"):
            with self.subTest(filename=filename):
                schema = self.load_schema(filename)
                properties = schema["properties"]
                if filename == "revision.schema.json":
                    self.assertRegex(properties["modelSha256"]["pattern"], r"64")
                    self.assertIn("modelStorageKey", properties)
                else:
                    self.assertRegex(properties["sha256"]["pattern"], r"64")
                    self.assertIn("sizeBytes", properties)

    def test_render_manifest_cannot_be_authoritative(self) -> None:
        schema = self.load_schema("render-manifest.schema.json")
        self.assertEqual(schema["properties"]["presentationOnly"]["const"], True)
        self.assertEqual(
            schema["properties"]["camera"]["properties"]["projection"]["enum"],
            ["orthographic", "perspective"],
        )

    def test_contract_patterns_match_representative_values(self) -> None:
        command = self.load_schema("command.schema.json")
        project_pattern = command["properties"]["projectId"]["pattern"]
        sha_pattern = self.load_schema("revision.schema.json")["properties"]["modelSha256"][
            "pattern"
        ]
        self.assertRegex("proj-example-house", project_pattern)
        self.assertRegex("a" * 64, sha_pattern)
        self.assertNotRegex("PROJ-EXAMPLE", project_pattern)
        self.assertNotRegex("a" * 63, sha_pattern)


if __name__ == "__main__":
    unittest.main()