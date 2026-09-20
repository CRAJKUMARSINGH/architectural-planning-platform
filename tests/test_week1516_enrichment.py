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
    PLANNER5D_INPUT_VERSION,
    ARCHISTAR_INPUT_VERSION,
    FLOORPLANNER_INPUT_VERSION,
    ROOMSTYLER_INPUT_VERSION,
    MAGICPLAN_INPUT_VERSION,
    LLM_BRIEF_INPUT_VERSION,
    FOURLINES_INPUT_VERSION,
    ARCHIAGENT_INPUT_VERSION,
    ai_tool_input_manifest,
    candidate_studio,
    design_package,
    edit_placements,
    find_valid_position,
    furnish_model,
    ingest_ai_tool_input,
    validate_maket_input,
    validate_planner5d_input,
    validate_archistar_snaptrude_input,
    validate_floorplanner_input,
    validate_roomstyler_homestyler_input,
    validate_magicplan_input,
    validate_llm_brief_input,
    validate_4lines_input,
    validate_archiagent_input,
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


def planner_model_fixture():
    model = model_fixture()
    model["project"]["revision"] = 1
    model["spaces"] = [
        {
            "id": "GF-03",
            "name": "President Chamber",
            "roomUse": "office",
            "geometry": {"rect": [288, 6, 432, 174]},
        }
    ]
    model["routes"] = []
    model["openings"] = []
    return model


def archistar_model_fixture():
    model = {
        "project": {"id": "site-fixture", "revision": 1},
        "units": "inch",
        "site": {
            "geometry": {
                "north": "up",
                "plotVertices": [[0, 0], [35, 0], [35, 30], [60, 30], [60, 98], [0, 98]],
                "setbacks": {"east": 5, "north": 60, "south": 5, "west": 0},
            }
        },
        "orientation": {
            "north": "up",
            "roadFrontage": "east",
            "serviceAccess": {"side": "west", "status": "assumption"},
            "setbacks": {"east": 5, "north": 60, "south": 5, "west": 0},
        },
        "levels": [
            {"id": "GF", "elevation": 0, "floorToFloor": 178},
            {"id": "FF", "elevation": 178, "floorToFloor": 178},
        ],
        "spaces": [
            {
                "id": "GF-HALL",
                "levelId": "GF",
                "name": "Assembly Hall",
                "roomUse": "assembly",
                "geometry": {"rect": [6, 6, 666, 174]},
            }
        ],
        "entries": [
            {"id": "ENTRY-MAIN", "hostSpace": "GF-HALL", "exteriorZoneId": "EXT-MAIN"},
            {"id": "ENTRY-VIP", "hostSpace": "GF-HALL", "exteriorZoneId": "EXT-VIP"},
        ],
        "openings": [{"id": "D-1", "hostSpace": "GF-HALL", "geometry": {"width": 36}}],
        "windows": [{"id": "W-1", "hostSpace": "GF-HALL", "geometry": {"width": 60}}],
        "circulationZones": [{"id": "ROUTE-1", "geometry": {"width": 48}}],
        "assumptions": ["Fixture site facts are nominal."],
    }
    return model


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

    def test_w1602_planner5d_fixture_maps_assets_and_rejects_clearance_conflict(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "planner5d-furnished-layout.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = planner_model_fixture()
        before = copy.deepcopy(model)

        result = validate_planner5d_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(result["version"], PLANNER5D_INPUT_VERSION)
        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["clearanceResult"], {"checked": 2, "accepted": 1, "rejected": 1})
        self.assertEqual(result["acceptedPlacements"][0]["assetId"], "work-desk")
        self.assertTrue(result["acceptedPlacements"][0]["presentationOnly"])
        self.assertEqual(result["rejectedPlacements"][0]["id"], "planner-chair-01")
        self.assertTrue(
            any(
                finding["rule"] == "ASSET_CLEARANCES_MUST_NOT_OVERLAP"
                for finding in result["rejectedPlacements"][0]["findings"]
            )
        )
        self.assertEqual(
            {item["status"] for item in result["assetMappingReport"]},
            {"mapped"},
        )
        self.assertFalse(result["candidateEligible"])
        self.assertEqual(model, before)

    def test_w1602_planner5d_route_conflict_cannot_be_candidate(self):
        payload = {
            "modelRevision": 8,
            "units": "inch",
            "assetMappings": [{"sourceAssetId": "desk", "assetId": "work-desk"}],
            "placements": [
                {
                    "id": "desk",
                    "sourceAssetId": "desk",
                    "hostSpaceId": "GF-OFFICE",
                    "position": {"x": 0, "y": 0},
                    "rotation": 0,
                    "dimensions": {"width": 60, "depth": 30},
                }
            ],
        }
        result = validate_planner5d_input(
            model_fixture(),
            payload,
            source_reference="planner5d-route-conflict",
            model_revision=8,
        )

        self.assertFalse(result["candidateEligible"])
        self.assertTrue(
            any(
                finding["rule"] == "ASSET_MUST_NOT_BLOCK_ZONE"
                for finding in result["rejectedPlacements"][0]["findings"]
            )
        )

    def test_w1602_planner5d_comparison_is_deterministic(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "planner5d-furnished-layout.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        first = validate_planner5d_input(
            planner_model_fixture(),
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )
        second = validate_planner5d_input(
            planner_model_fixture(),
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(first["baselineComparison"], second["baselineComparison"])
        self.assertEqual(first["determinism"], second["determinism"])
        self.assertTrue(first["baselineComparison"]["deterministic"])

    def test_w1603_archistar_fixture_links_week6_and_week7_evidence(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "archistar-snaptrude-site-model.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        result = validate_archistar_snaptrude_input(
            archistar_model_fixture(),
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(result["version"], ARCHISTAR_INPUT_VERSION)
        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["candidateEligible"])
        self.assertFalse(result["authoritativeGeometryChanged"])
        self.assertEqual(result["week6Comparison"]["templateVersion"], "week6.program-template.v1")
        self.assertEqual(result["week6Comparison"]["factComparisons"]["north"]["match"], True)
        self.assertIn("rulePack", result["rulePackLinkage"])
        self.assertIn(
            "SERVICE-ACCESS",
            {item["ruleId"] for item in result["rulePackLinkage"]["findingLinks"]},
        )
        self.assertFalse(result["professionalReview"]["approvalClaim"])

    def test_w1603_missing_frontage_and_service_access_stays_explicit_warning(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "archistar-snaptrude-site-model.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["site"].pop("frontage")
        payload["site"].pop("serviceAccess")
        before = copy.deepcopy(archistar_model_fixture())

        result = validate_archistar_snaptrude_input(
            archistar_model_fixture(),
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        warnings = {
            item["rule"]
            for item in result["findings"]
            if item["severity"] == "WARNING"
        }
        self.assertIn("ARCHISTAR_FRONTAGE_REQUIRED", warnings)
        self.assertIn("ARCHISTAR_SERVICE_ACCESS_REQUIRED", warnings)
        self.assertEqual(result["status"], "review-required")
        self.assertTrue(
            any(
                item["ruleId"] == "SERVICE-ACCESS" and item["status"] == "unknown"
                for item in result["rulePackLinkage"]["findingLinks"]
            )
        )
        self.assertEqual(archistar_model_fixture(), before)

    def test_w1603_site_evidence_does_not_mutate_canonical_model(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "archistar-snaptrude-site-model.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = archistar_model_fixture()
        before = copy.deepcopy(model)

        validate_archistar_snaptrude_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(model, before)

    def test_w1604_floorplanner_fixture_is_synchronized_to_canonical_revision(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "floorplanner-synchronized-view.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model_path = ROOT / "bar-association-hall" / "standard" / "model" / "project.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        result = validate_floorplanner_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["version"], FLOORPLANNER_INPUT_VERSION)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["synchronizationStatus"], "synchronized")
        self.assertTrue(result["revisionMatch"])
        self.assertTrue(result["candidateEligible"])
        self.assertEqual(len(result["views"]), 4)
        self.assertEqual(
            result["canonicalViewContract"]["version"],
            "week14.synchronized-views.v1",
        )
        self.assertTrue(result["validationEvidence"]["status"] == "pass")

    def test_w1604_stale_floorplanner_revision_is_not_silently_accepted(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "floorplanner-synchronized-view.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )
        payload["modelRevision"] = model["project"]["revision"] - 1

        result = validate_floorplanner_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["synchronizationStatus"], "stale")
        self.assertFalse(result["candidateEligible"])
        self.assertFalse(result["revisionMatch"])
        self.assertIn(
            "FLOORPLANNER_MODEL_REVISION_STALE",
            {item["rule"] for item in result["findings"]},
        )

    def test_w1604_unknown_ids_and_unrerun_accepted_edit_require_review(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "floorplanner-synchronized-view.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )
        payload["views"][0]["objectIds"].append("not-canonical")
        payload["acceptedEdit"] = {"kind": "move-view-object", "objectId": "GF-01"}

        result = validate_floorplanner_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )
        rules = {item["rule"] for item in result["findings"]}

        self.assertEqual(result["status"], "review-required")
        self.assertIn("FLOORPLANNER_UNKNOWN_OBJECT_ID", rules)
        self.assertIn("FLOORPLANNER_VALIDATION_RERUN_REQUIRED", rules)
        self.assertFalse(result["validationEvidence"]["rerunAfterAcceptedEdit"]["performed"])

    def test_w1605_roomstyler_fixture_keeps_valid_option_and_rejects_clearance_conflict(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "roomstyler-presentation-options.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = planner_model_fixture()
        before = copy.deepcopy(model)

        result = validate_roomstyler_homestyler_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(result["version"], ROOMSTYLER_INPUT_VERSION)
        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["candidateId"], "C-15-02")
        self.assertEqual(result["technicalPlanSideBySide"]["modelRevision"], 1)
        self.assertTrue(result["technicalPlanSideBySide"]["validationMarkersRetained"])
        self.assertEqual(len(result["acceptedOptions"]), 1)
        self.assertEqual(len(result["rejectedOptions"]), 1)
        self.assertTrue(result["acceptedOptions"][0]["furniture"][0]["presentationOnly"])
        self.assertTrue(
            any(
                finding["rule"] == "ASSET_CLEARANCES_MUST_NOT_OVERLAP"
                for finding in result["rejectedOptions"][0]["findings"]
            )
        )
        self.assertFalse(result["candidateEligible"])
        self.assertFalse(result["authoritativeGeometryChanged"])
        self.assertEqual(model, before)

    def test_w1605_roomstyler_valid_option_is_traceable_and_non_authoritative(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "roomstyler-presentation-options.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["options"] = payload["options"][:1]

        result = validate_roomstyler_homestyler_input(
            planner_model_fixture(),
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["candidateEligible"])
        self.assertEqual(result["acceptedOptions"][0]["finishes"][0]["hostSpaceId"], "GF-03")
        self.assertEqual(result["acceptedOptions"][0]["furniture"][0]["modelRevision"], 1)

    def test_w1606_magicplan_fixture_only_promotes_confirmed_scaled_object(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "magicplan-recognition-queue.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model_path = ROOT / "bar-association-hall" / "standard" / "model" / "project.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        before = copy.deepcopy(model)

        result = validate_magicplan_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=1,
        )

        self.assertEqual(result["version"], MAGICPLAN_INPUT_VERSION)
        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["recognitionSummary"]["recognized"], 3)
        self.assertEqual(result["recognitionSummary"]["accepted"], 1)
        self.assertEqual(result["recognitionSummary"]["uncertain"], 1)
        self.assertEqual(result["recognitionSummary"]["rejected"], 1)
        self.assertEqual(result["recognitionSummary"]["promoted"], 1)
        self.assertEqual(result["promotedObjects"][0]["proposedObjectId"], "GF-03")
        self.assertTrue(result["promotedObjects"][0]["editableGeometry"])
        self.assertEqual(result["reviewQueue"][0]["queueStatus"], "uncertain")
        self.assertEqual(result["reviewQueue"][1]["queueStatus"], "rejected")
        self.assertFalse(result["authoritativeGeometryChanged"])
        self.assertEqual(model, before)

    def test_w1606_magicplan_image_only_result_cannot_be_promoted(self):
        payload = {
            "photos": [{"id": "photo-1", "sourceImage": "capture.jpg"}],
            "captureMetadata": {"device": "phone-camera"},
            "recognizedObjects": [
                {
                    "id": "room-from-image",
                    "kind": "room",
                    "confidence": 0.99,
                    "proposedObjectId": "GF-OFFICE",
                    "queueStatus": "accepted",
                    "manualConfirmation": True,
                }
            ],
        }
        result = validate_magicplan_input(
            model_fixture(),
            payload,
            source_reference="magicplan-image-only",
            model_revision=8,
        )

        rules = {item["rule"] for item in result["findings"]}
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["promotedObjects"], [])
        self.assertIn("MAGICPLAN_KNOWN_SCALE_REQUIRED", rules)
        self.assertIn("MAGICPLAN_SCALE_EVIDENCE_REQUIRED", rules)
        self.assertIn("MAGICPLAN_VALIDATION_RERUN_REQUIRED", rules)

    def test_w1607_llm_fixture_compiles_brief_and_accepts_typed_revision(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "llm-brief-refinement.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model_path = ROOT / "bar-association-hall" / "standard" / "model" / "project.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        before = copy.deepcopy(model)

        result = validate_llm_brief_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["version"], LLM_BRIEF_INPUT_VERSION)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["candidateEligible"])
        self.assertEqual(result["compilerShape"]["status"], "ready")
        self.assertEqual(result["clarificationState"]["status"], "resolved")
        self.assertEqual(result["acceptedRevision"]["afterRevision"], 2)
        self.assertTrue(result["acceptedRevision"]["accepted"])
        self.assertEqual(result["validationReport"]["status"], "pass")
        self.assertEqual(result["acceptedModelRevision"], 2)
        self.assertFalse(result["authoritativeGeometryChanged"])
        self.assertEqual(model, before)

    def test_w1607_llm_missing_upper_floor_access_blocks_before_rendering(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "llm-brief-refinement.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["verticalAccess"] = []
        payload["proposedRevisions"] = []
        payload.pop("validationReport")
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )

        result = validate_llm_brief_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        rules = {item["rule"] for item in result["findings"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("LLM_UPPER_FLOOR_ACCESS_REQUIRED", rules)
        self.assertEqual(result["acceptedRevision"], None)
        self.assertEqual(result["clarificationState"]["status"], "blocked")

    def test_w1607_llm_proposal_without_explicit_accept_stays_review_required(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "llm-brief-refinement.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["proposedRevisions"][0]["accept"] = False
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )

        result = validate_llm_brief_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["status"], "review-required")
        self.assertIsNone(result["acceptedRevision"])
        self.assertIn("LLM_ACCEPT_REVISION_REQUIRED", {item["rule"] for item in result["findings"]})

    def test_w1608_4lines_fixture_preserves_cross_view_identity(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "4lines-plan-section-exchange.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )

        result = validate_4lines_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["version"], FOURLINES_INPUT_VERSION)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["candidateEligible"])
        self.assertEqual({item["kind"] for item in result["views"]}, {"plan", "section", "elevation"})
        self.assertEqual(result["missingObjectIds"], [])
        self.assertFalse(result["invalidation"]["invalidated"])
        self.assertFalse(result["authoritativeGeometryChanged"])

    def test_w1608_4lines_missing_duplicate_and_disconnected_objects_are_rejected(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "4lines-plan-section-exchange.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["views"][0]["objectIds"].append("GF-06")
        payload["views"][0]["objectIds"].append("FF-06")
        payload["views"][1]["objectIds"].remove("FF-02")
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )

        result = validate_4lines_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        rules = {item["rule"] for item in result["findings"]}
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["candidateEligible"])
        self.assertIn("FOURLINES_DUPLICATE_OBJECT_ID", rules)
        self.assertIn("FOURLINES_DISCONNECTED_OBJECT", rules)
        self.assertIn("FOURLINES_OBJECT_MISSING", rules)

    def test_w1609_archiagent_fixture_normalizes_dimensions_and_retains_review_evidence(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "archiagent-live-dimension-review.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )
        before = copy.deepcopy(model)

        result = validate_archiagent_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        rules = {item["rule"] for item in result["findings"]}
        self.assertEqual(result["version"], ARCHIAGENT_INPUT_VERSION)
        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["canonicalUnits"], "inch")
        self.assertEqual(result["conflictCount"], 1)
        self.assertEqual(result["changedObjects"], ["GF-01", "GF-03"])
        self.assertIn("ARCHIAGENT_DIMENSION_STALE", rules)
        self.assertIn("ARCHIAGENT_DIMENSION_CONFLICT", rules)
        self.assertIn("ARCHIAGENT_PROFESSIONAL_REVIEW_REQUIRED", rules)
        self.assertTrue(result["validationRerun"]["performed"])
        self.assertEqual(result["validationRerun"]["status"], "pass")
        self.assertEqual(
            next(item for item in result["dimensions"] if item["id"] == "DIM-ROOM-WIDTH")["normalizedValue"],
            144.0,
        )
        self.assertFalse(result["authoritativeGeometryChanged"])
        self.assertEqual(model, before)

    def test_w1609_archiagent_valid_dimensions_can_pass_after_review_completion(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "archiagent-live-dimension-review.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["dimensions"] = payload["dimensions"][:5]
        payload["acceptedEdits"] = []
        payload["professionalReview"] = {"state": "complete", "reviewer": "fixture-reviewer"}

        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )
        result = validate_archiagent_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["candidateEligible"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["conflictCount"], 0)
        self.assertEqual(result["changedObjects"], [])

    def test_w1609_archiagent_accepted_edit_requires_complete_validation_rerun(self):
        fixture_path = ROOT / "tests" / "fixtures" / "week16" / "archiagent-live-dimension-review.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        payload["dimensions"] = payload["dimensions"][:1]
        payload.pop("validationRerun")
        payload["professionalReview"] = {"state": "complete"}

        model = json.loads(
            (ROOT / "bar-association-hall" / "standard" / "model" / "project.json").read_text(
                encoding="utf-8"
            )
        )
        result = validate_archiagent_input(
            model,
            payload,
            source_reference=payload["sourceReference"],
            model_revision=model["project"]["revision"],
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("ARCHIAGENT_VALIDATION_RERUN_REQUIRED", {item["rule"] for item in result["findings"]})

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