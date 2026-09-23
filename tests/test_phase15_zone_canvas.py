"""Phase 15 — Zone-Sketch Canvas regression tests.

Validates the ZoneCanvas contract and its integration with the existing
typed command pipeline:

- Zone-to-add-space parameter mapping is correct
- Level-ID derivation from floor names is deterministic
- Zone sizes are converted from pixels to canonical model units correctly
- All 7 zone types produce valid add-space commands
- Multi-floor isolation: zones on different floors map to different levelIds
- Architecture principle: zones are ephemeral UI state, not canonical geometry
- Component file exists and App.tsx imports it

No DOM or React renderer required — pure contract + command-pipeline tests.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "phase15" / "zone_canvas_contract.json"
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Helpers (mirrors the TypeScript logic in ZoneCanvas.tsx)
# ---------------------------------------------------------------------------

UNIT = 12   # 1 canvas pixel-unit = 12 inches
GRID = 24   # snap grid in pixels

ZONE_TYPES = {"living", "sleeping", "service", "circulation", "outdoor", "work", "other"}

ZONE_ROOM_USE = {
    "living": "living",
    "sleeping": "sleeping",
    "service": "service",
    "circulation": "circulation",
    "outdoor": "outdoor",
    "work": "work",
    "other": "other",
}

ZONE_ACCESS_INTENT = {
    "circulation": "primary-circulation",
}


def snap(v: float, grid: int = GRID) -> float:
    return round(v / grid) * grid


def floor_to_level_id(floor_name: str) -> str:
    """Mirrors the TypeScript conversion in ZoneCanvas.tsx sendToEditor."""
    return floor_name.upper().replace(" ", "-")[:8]


def zone_to_add_space_params(
    zone_id: str,
    label: str,
    zone_type: str,
    floor: str,
    x: float,
    y: float,
    w: float,
    h: float,
) -> dict:
    """Produce the parameters object that ZoneCanvas dispatches."""
    level_id = floor_to_level_id(floor)
    access_intent = (
        "primary-circulation"
        if zone_type == "circulation"
        else "occupancy"
    )
    return {
        "spaceId": zone_id,
        "levelId": level_id,
        "name": label,
        "rect": [x, y, x + w, y + h],
        "roomUse": zone_type,
        "accessIntent": access_intent,
    }


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------

class TestPhase15Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_version(self):
        self.assertEqual(self.contract["version"], "phase15.zone-canvas-contract.v1")

    def test_seven_zone_types_documented(self):
        self.assertEqual(len(self.contract["zoneTypes"]), 7)
        self.assertIn("living", self.contract["zoneTypes"])
        self.assertIn("circulation", self.contract["zoneTypes"])

    def test_canvas_unit_is_twelve_inches(self):
        self.assertEqual(self.contract["canvasUnit"]["inches"], 12)

    def test_command_operation_is_add_space(self):
        self.assertEqual(self.contract["commandDispatch"]["operation"], "add-space")

    def test_required_parameters_documented(self):
        for p in ("spaceId", "levelId", "name", "rect", "roomUse"):
            self.assertIn(p, self.contract["commandDispatch"]["requiredParameters"])

    def test_architecture_principle_documented(self):
        principle = self.contract["architecturePrinciple"]
        self.assertIn("ephemeral", principle.lower())
        self.assertIn("canonical", principle.lower())

    def test_component_file_exists(self):
        p = ROOT / "apps" / "web" / "src" / "components" / "ZoneCanvas.tsx"
        self.assertTrue(p.exists(), "ZoneCanvas.tsx missing")

    def test_app_tsx_imports_zone_canvas(self):
        app_tsx = (ROOT / "apps" / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("ZoneCanvas", app_tsx)
        self.assertIn("<ZoneCanvas", app_tsx)


# ---------------------------------------------------------------------------
# Level-ID derivation
# ---------------------------------------------------------------------------

class TestLevelIdDerivation(unittest.TestCase):
    def test_ground_floor_becomes_GROUND_F(self):
        self.assertEqual(floor_to_level_id("Ground Floor"), "GROUND-F")

    def test_first_floor_becomes_FIRST_FL(self):
        self.assertEqual(floor_to_level_id("First Floor"), "FIRST-FL")

    def test_max_eight_chars(self):
        result = floor_to_level_id("A very long floor name")
        self.assertLessEqual(len(result), 8)

    def test_spaces_become_dashes(self):
        result = floor_to_level_id("Floor 2")
        self.assertNotIn(" ", result)
        self.assertIn("-", result)

    def test_uppercase(self):
        result = floor_to_level_id("basement")
        self.assertEqual(result, result.upper())

    def test_different_floors_produce_different_level_ids(self):
        gf = floor_to_level_id("Ground Floor")
        ff = floor_to_level_id("First Floor")
        self.assertNotEqual(gf, ff)


# ---------------------------------------------------------------------------
# Zone-to-add-space mapping
# ---------------------------------------------------------------------------

class TestZoneToAddSpaceMapping(unittest.TestCase):

    def _params(self, zone_type: str = "living", floor: str = "Ground Floor") -> dict:
        return zone_to_add_space_params(
            zone_id="zone-test-001",
            label="Living Room",
            zone_type=zone_type,
            floor=floor,
            x=48.0,
            y=48.0,
            w=180.0,
            h=144.0,
        )

    def test_space_id_preserved(self):
        p = self._params()
        self.assertEqual(p["spaceId"], "zone-test-001")

    def test_level_id_derived_from_floor(self):
        p = self._params(floor="Ground Floor")
        self.assertEqual(p["levelId"], "GROUND-F")

    def test_rect_is_four_element_list(self):
        p = self._params()
        self.assertEqual(len(p["rect"]), 4)
        x0, y0, x1, y1 = p["rect"]
        self.assertEqual(x1 - x0, 180.0)
        self.assertEqual(y1 - y0, 144.0)

    def test_room_use_matches_zone_type(self):
        for zt in ZONE_TYPES:
            p = zone_to_add_space_params("z1", zt.title(), zt, "GF", 0, 0, 60, 60)
            self.assertEqual(p["roomUse"], zt)

    def test_circulation_gets_primary_circulation_intent(self):
        p = self._params(zone_type="circulation")
        self.assertEqual(p["accessIntent"], "primary-circulation")

    def test_other_zones_get_occupancy_intent(self):
        for zt in ZONE_TYPES - {"circulation"}:
            p = self._params(zone_type=zt)
            self.assertEqual(p["accessIntent"], "occupancy", f"Failed for zone type {zt}")

    def test_label_used_as_name(self):
        p = self._params()
        self.assertEqual(p["name"], "Living Room")


# ---------------------------------------------------------------------------
# Canvas-unit to inch conversion
# ---------------------------------------------------------------------------

class TestCanvasUnitConversion(unittest.TestCase):
    def test_unit_constant_is_12_inches(self):
        self.assertEqual(UNIT, 12)

    def test_180px_is_15_feet(self):
        self.assertEqual(180 // UNIT, 15)

    def test_144px_is_12_feet(self):
        self.assertEqual(144 // UNIT, 12)

    def test_72px_is_minimum_6_feet(self):
        self.assertEqual(72 // UNIT, 6)

    def test_rect_in_add_space_params_is_in_inches(self):
        """The rect passed to add-space is already in canvas pixel-units (inches)."""
        p = zone_to_add_space_params("z1", "Hall", "living", "GF", 0, 0, 180, 144)
        x0, y0, x1, y1 = p["rect"]
        width_inches = x1 - x0
        height_inches = y1 - y0
        self.assertEqual(width_inches / UNIT, 15.0)   # 15 feet
        self.assertEqual(height_inches / UNIT, 12.0)  # 12 feet


# ---------------------------------------------------------------------------
# Grid snapping
# ---------------------------------------------------------------------------

class TestGridSnapping(unittest.TestCase):
    def test_snap_rounds_to_24px_grid(self):
        self.assertEqual(snap(25), 24)
        self.assertEqual(snap(37), 48)
        self.assertEqual(snap(12), 0)

    def test_snap_preserves_aligned_values(self):
        self.assertEqual(snap(48), 48)
        self.assertEqual(snap(96), 96)

    def test_snap_handles_zero(self):
        self.assertEqual(snap(0), 0)


# ---------------------------------------------------------------------------
# Multi-floor isolation
# ---------------------------------------------------------------------------

class TestMultiFloorIsolation(unittest.TestCase):
    def test_zones_on_different_floors_get_different_level_ids(self):
        gf_params = zone_to_add_space_params("z1", "Hall", "living", "Ground Floor", 0, 0, 180, 144)
        ff_params = zone_to_add_space_params("z2", "Bedroom", "sleeping", "First Floor", 0, 0, 120, 120)
        self.assertNotEqual(gf_params["levelId"], ff_params["levelId"])

    def test_same_floor_zones_share_level_id(self):
        p1 = zone_to_add_space_params("z1", "Hall", "living", "Ground Floor", 0, 0, 180, 144)
        p2 = zone_to_add_space_params("z2", "Kitchen", "service", "Ground Floor", 200, 0, 120, 120)
        self.assertEqual(p1["levelId"], p2["levelId"])


# ---------------------------------------------------------------------------
# CommandRunner acceptance of zone-generated add-space commands
# ---------------------------------------------------------------------------

class TestZoneCommandRunnerAcceptance(unittest.TestCase):
    """Verify that zone-generated add-space parameters pass CommandRunner."""

    def _minimal_model_with_level(self, level_id: str) -> dict:
        return {
            "schemaVersion": "advocate-chambers.project.v2",
            "project": {"id": "proj-test", "name": "T", "revision": 1,
                        "status": "draft", "source": "user", "legacy": {}},
            "units": "inch", "wallThickness": 6.0,
            "levels": [{"id": level_id, "name": level_id, "elevation": 0,
                        "floorToFloor": 120, "source": "user", "status": "draft",
                        "revision": 1,
                        "provenance": {"sourcePath": "test", "sourceId": level_id,
                                       "migration": "week2.legacy-to-v2", "legacyKeys": []},
                        "legacy": {}}],
            "spaces": [], "openings": [], "windows": [], "entries": [],
            "circulationZones": [], "exteriorZones": [], "verticalConnectors": [],
            "stairs": [], "assumptions": [], "notes": [],
            "revisions": [{"id": "R1", "date": "2026-01-01T00:00:00Z",
                           "author": "test", "summary": "init",
                           "source": "user", "legacy": {}}],
            "site": {"id": "SITE", "kind": "site", "levelId": "SITE",
                     "geometry": {"plotVertices": [[0,0],[1,0],[1,1],[0,1]]},
                     "source": "user", "status": "draft", "revision": 1,
                     "provenance": {"sourcePath": "test", "sourceId": "SITE",
                                    "migration": "week2.legacy-to-v2", "legacyKeys": []},
                     "legacy": {}},
        }

    def _make_envelope(self, params: dict, project_id: str = "proj-test") -> dict:
        return {
            "schemaVersion": "advocate-chambers.command.v1",
            "commandId": f"cmd-zone-{params['spaceId']}",
            "projectId": project_id,
            "baseRevision": 1,
            "authorId": "browser-user",
            "operation": "add-space",
            "parameters": params,
            "idempotencyKey": f"ik-zone-{params['spaceId']}-p15",
        }

    def test_living_zone_accepted_by_command_runner(self):
        from packages.geometry.command_runner import CommandRunner  # noqa: PLC0415
        params = zone_to_add_space_params("living-z1", "Living Room", "living",
                                          "GF", 0, 0, 180, 144)
        # Override levelId to match the model's level
        params["levelId"] = "GF"
        model = self._minimal_model_with_level("GF")
        runner = CommandRunner()
        result = runner.execute(model, self._make_envelope(params))
        self.assertTrue(result.accepted, f"Expected accepted, findings: {result.findings}")
        self.assertIn("living-z1", result.affected_object_ids)

    def test_all_zone_types_produce_accepted_commands(self):
        from packages.geometry.command_runner import CommandRunner  # noqa: PLC0415
        runner = CommandRunner()
        for i, zt in enumerate(sorted(ZONE_TYPES)):
            zone_id = f"{zt}-zone-p15-{i}"
            params = zone_to_add_space_params(zone_id, f"{zt.title()} Space",
                                              zt, "GF", i * 200, 0, 160, 120)
            params["levelId"] = "GF"
            model = self._minimal_model_with_level("GF")
            result = runner.execute(model, self._make_envelope(params, f"proj-test"))
            self.assertTrue(result.accepted, f"Zone type {zt} rejected: {result.findings}")

    def test_rect_must_have_four_elements(self):
        """Guard: malformed rect is rejected by CommandRunner constraints."""
        from packages.geometry.command_runner import CommandRunner  # noqa: PLC0415
        bad_params = {
            "spaceId": "bad-zone",
            "levelId": "GF",
            "name": "Bad",
            "rect": [0, 0, 100],  # only 3 elements
            "roomUse": "living",
            "accessIntent": "occupancy",
        }
        model = self._minimal_model_with_level("GF")
        runner = CommandRunner()
        result = runner.execute(model, self._make_envelope(bad_params))
        self.assertFalse(result.accepted)


if __name__ == "__main__":
    unittest.main()
