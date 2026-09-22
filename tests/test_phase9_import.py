"""Phase 9 — Safe import pipeline regression tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase9" / "import_contract.json"
sys.path.insert(0, str(ROOT))

from packages.geometry.importers import ImportProvenanceTracker, ProjectImporter


class Phase9ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open(encoding="utf-8") as f:
            cls.fixture = json.load(f)
        cls.importer = ProjectImporter()

    def test_fixture_integrity(self):
        self.assertEqual(self.fixture["version"], "phase9.import-contract.v1")
        self.assertIn("dxf", self.fixture["supportedFormats"])
        self.assertIn("raster-image", self.fixture["supportedFormats"])

    def test_native_json_import_preserves_provenance(self):
        sample = {
            "projectId": "proj-native-test",
            "units": "inch",
            "walls": [{"id": "w1", "start": [0, 0], "end": [100, 0]}],
            "spaces": [{"id": "sp1", "name": "Chamber"}],
        }
        imported = self.importer.import_native_json(sample, source_path="upload://native.json")

        self.assertEqual(imported["projectId"], "proj-native-test")
        self.assertEqual(len(imported["walls"]), 1)
        w = imported["walls"][0]
        self.assertIn("source", w)
        src = w["source"]
        for req_field in self.fixture["requiredProvenanceFields"]:
            self.assertIn(req_field, src)
        self.assertEqual(src["sourceFormat"], "native-json")
        self.assertEqual(src["confidence"], 1.0)
        self.assertFalse(src["reviewRequired"])

    def test_dxf_import_tags_layers_and_identifies_uncertain_entities(self):
        entities = [
            {"type": "LINE", "layer": "A-WALL-EXTR", "start": [0, 0], "end": [200, 0]},
            {"type": "LINE", "layer": "A-DOOR", "offset": 36, "width": 36},
            {"type": "TEXT", "layer": "UNKNOWN_LAYER_XYZ", "text": "Random Annotation"},
        ]
        imported = self.importer.import_dxf_entities(entities, source_path="upload://plan.dxf")

        self.assertEqual(len(imported["walls"]), 1)
        self.assertEqual(len(imported["openings"]), 1)
        self.assertEqual(len(imported["uncertainEntities"]), 1)

        unc = imported["uncertainEntities"][0]
        self.assertTrue(unc["source"]["reviewRequired"])
        self.assertLess(unc["source"]["confidence"], 0.90)
        self.assertTrue(imported["importSummary"]["requiresReview"])

    def test_raster_assisted_import_always_sets_review_required(self):
        contours = [
            {"x1": 10, "y1": 10, "x2": 150, "y2": 10, "confidence": 0.85},
            {"x1": 150, "y1": 10, "x2": 150, "y2": 120, "confidence": 0.65},
        ]
        imported = self.importer.import_raster_assisted(contours, source_path="upload://sketch.png", scale_ratio=2.5)

        self.assertEqual(len(imported["walls"]), 2)
        # Policy: raster image recognition must ALWAYS require review
        for w in imported["walls"]:
            self.assertTrue(w["source"]["reviewRequired"])
            self.assertEqual(w["source"]["sourceFormat"], "raster-image")
        self.assertTrue(imported["importSummary"]["requiresReview"])


if __name__ == "__main__":
    unittest.main()
