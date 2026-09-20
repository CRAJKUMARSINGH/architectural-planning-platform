import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from week1516 import (  # noqa: E402
    ASSET_CATALOG,
    ROOM_TEMPLATES,
    AI_INPUT_VERSION,
    ai_tool_input_manifest,
    candidate_studio,
    design_package,
    edit_placements,
    find_valid_position,
    furnish_model,
    ingest_ai_tool_input,
    validate_maket_input,
    validate_placement,
)


def model_fixture():
    return {
        "project": {"id": "fixture", "revision": 8},
        "levels": [{"id": "GF", "elevation": 0}],
        "spaces": [{"id": "GF-OFFICE", "name": "Office", "roomUse": "office", "geometry": {"rect": [0, 0, 240, 240]}}],
        "openings": [],
        "routes": [{"id": "ROUTE", "spaceId": "GF-OFFICE", "geometry": {"rect": [0, 0, 240, 36]}}],
        "stairs": [],
        "serviceZones": [],
        "adjacencies": [{"satisfied": True}],
        "program": {"spaceChecks": [{"status": "pass"}]},
    }


class Week1516EnrichmentTests(unittest.TestCase):
    def test_w1601_maket_fixture_matches_canonical_model(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "maket-ai-text-to-plan.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        result = validate_maket_input(
            model_fixture(),
            payload,
            source_reference=payload["sourceReference"],
            model_revision=8,
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["version"], "week16-01.maket-ai.v1")
        self.assertFalse(result["authoritativeGeometryChanged"])
        self.assertEqual(result["input"]["tool"], "Maket.ai")
        self.assertEqual(result["findings"], [])

    def test_w1601_maket_dimension_conflict_requires_review_without_mutation(self):
        model = model_fixture()
        before = copy.deepcopy(model)
        payload = {
            "units": "inch",
            "rooms": [{"name": "Office", "width": 180, "depth": 240}],
            "furnitureIntent": [],
            "adjacencyIntent": [],
        }
        result = validate_maket_input(model, payload, source_reference="maket-conflict", model_revision=8)
        self.assertEqual(result["status"], "review-required")
        self.assertTrue(any(item["rule"] == "MAKET_DIMENSION_CONFLICT" for item in result["findings"]))
        self.assertEqual(model, before)

    def test_w1601_maket_missing_units_and_dimensions_blocks(self):
        result = validate_maket_input(
            model_fixture(),
            {"rooms": [{"name": "Office"}], "furnitureIntent": [], "adjacencyIntent": []},
            source_reference="maket-invalid",
            model_revision=8,
        )
        rules = {item["rule"] for item in result["findings"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("MAKET_UNITS_REQUIRED", rules)
        self.assertIn("MAKET_ROOM_DIMENSIONS_REQUIRED", rules)

    def test_week16_exposes_tool_inputs_with_review_boundaries(self):
        manifest = ai_tool_input_manifest()
        self.assertEqual(manifest["version"], AI_INPUT_VERSION)
        self.assertEqual(manifest["status"], "review-first")
        tools = {item["tool"] for item in manifest["tools"]}
        self.assertEqual(
            {
                "Maket.ai",
                "Planner 5D",
                "Archistar / Snaptrude",
                "Floorplanner",
                "Roomstyler / Homestyler",
                "Magicplan",
                "ChatGPT / Claude / Grok / Gemini",
                "4Lines.ai",
                "Archiagent",
            },
            tools,
        )
        self.assertTrue(manifest["promotionPolicy"]["rerunValidationAfterAcceptance"])

    def test_week16_tool_input_is_typed_and_non_authoritative(self):
        item = ingest_ai_tool_input(
            "maket-text-to-plan",
            source_input={"rooms": [{"name": "living", "width": 240}]},
            source_reference="maket-export-001",
            model_revision=8,
            validation_status="pending",
        )
        self.assertEqual(item["tool"], "Maket.ai")
        self.assertEqual(item["modelRevision"], 8)
        self.assertFalse(item["authoritative"])
        self.assertEqual(item["promotionStatus"], "review-required")
        with self.assertRaises(ValueError):
            ingest_ai_tool_input(
                "unknown-tool",
                source_input={},
                source_reference="unknown",
                model_revision=8,
            )

    def test_catalog_and_templates_cover_week15_categories(self):
        categories = {item["category"] for item in ASSET_CATALOG.values()}
        self.assertTrue({"furniture", "fixtures", "appliance", "sanitaryware", "seating", "dais", "library", "counter", "vehicle", "industrial-equipment"} & categories)
        self.assertEqual({"residential", "office", "chamber", "hall", "classroom", "library", "healthcare", "retail", "light-industrial"}, set(ROOM_TEMPLATES))
        for spec in ASSET_CATALOG.values():
            self.assertFalse(spec["authoritative"])
            self.assertIn("clearanceEnvelope", spec)
            self.assertIn("rotationRules", spec)

    def test_one_click_furnishing_preserves_authority_and_is_deterministic(self):
        model = model_fixture()
        before = copy.deepcopy(model)
        first = furnish_model(model, seed=1516)
        second = furnish_model(model, seed=1516)
        self.assertEqual(first["determinism"], second["determinism"])
        self.assertTrue(first["authoritativeGeometryUnchanged"])
        self.assertEqual(model, before)
        self.assertTrue(all(item["presentationOnly"] for item in first["placements"]))

    def test_route_and_door_swing_are_blockers(self):
        model = model_fixture()
        placement = {
            "id": "desk-1",
            "assetId": "work-desk",
            "hostSpaceId": "GF-OFFICE",
            "geometry": {"rect": [0, 0, 60, 30]},
        }
        findings = validate_placement(model, placement)
        self.assertTrue(any(item["rule"] == "ASSET_MUST_NOT_BLOCK_ZONE" for item in findings))
        model["openings"] = [{"id": "D-1", "hostSpace": "GF-OFFICE", "geometry": {"rect": [0, 200, 36, 218]}}]
        placement["geometry"]["rect"] = [0, 180, 60, 210]
        self.assertTrue(any(item["rule"] == "ASSET_MUST_NOT_BLOCK_DOOR_SWING" for item in validate_placement(model, placement)))

    def test_edit_operations_and_valid_position(self):
        model = model_fixture()
        placement = find_valid_position(model, "work-desk", "GF-OFFICE")
        self.assertIsNotNone(placement)
        placement["id"] = "desk-1"
        moved = edit_placements(model, [placement], {"type": "duplicate", "targetId": "desk-1", "newId": "desk-2", "dx": 100, "dy": 100})
        self.assertEqual(len(moved["placements"]), 2)
        replaced = edit_placements(model, [placement], {"type": "replace", "targetId": "desk-1", "assetId": "executive-desk"})
        self.assertEqual(replaced["placements"][0]["assetId"], "executive-desk")

    def test_candidate_studio_deterministic_and_blocker_safe(self):
        model = model_fixture()
        first = candidate_studio(model, seeds=(1, 2, 3))
        second = candidate_studio(model, seeds=(1, 2, 3))
        self.assertEqual(first["ranking"], second["ranking"])
        self.assertIsNotNone(first["bestCandidateId"])
        blocked = candidate_studio(model, seeds=(1,), inherited_findings=[{"severity": "BLOCKER", "rule": "TEST"}])
        self.assertIsNone(blocked["bestCandidateId"])

    def test_candidate_studio_carries_external_inputs_without_geometry_authority(self):
        model = model_fixture()
        external = ingest_ai_tool_input(
            "planner5d-furnished-layout",
            source_input={"layoutId": "candidate-01"},
            source_reference="planner5d-export-01",
            model_revision=8,
        )
        result = candidate_studio(model, seeds=(1,), ai_tool_inputs=(external,))
        self.assertEqual(result["aiToolInputCatalogVersion"], AI_INPUT_VERSION)
        self.assertEqual(result["aiToolInputs"][0]["tool"], "Planner 5D")
        self.assertFalse(result["aiToolInputs"][0]["authoritative"])

    def test_design_package_is_revision_traceable_and_non_destructive(self):
        package = design_package(model_fixture(), "C-15-01")
        self.assertFalse(package["authoritativeGeometryChanged"])
        self.assertEqual(package["technicalPlanSideBySide"]["modelRevision"], 8)
        self.assertTrue(all(job["artifactManifest"]["traceableTo"]["candidateId"] == "C-15-01" for job in package["renderJobs"]))


if __name__ == "__main__":
    unittest.main()