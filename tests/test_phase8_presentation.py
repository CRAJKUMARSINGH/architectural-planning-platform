"""Phase 8 presentation scene compiler and render manifest regressions."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase8" / "presentation_contract.json"
SCHEMA_PATH = ROOT / "packages" / "schema" / "render-manifest.schema.json"
sys.path.insert(0, str(ROOT))

from packages.geometry.presentation import (
    ASSET_CATALOG,
    ASSET_CATALOG_VERSION,
    CAMERA_PRESETS,
    STYLE_TOKENS,
    build_render_manifest,
    compile_presentation_scene,
    render_presentation_svg,
)


class Phase8PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open(encoding="utf-8") as f:
            cls.fixture = json.load(f)
        with SCHEMA_PATH.open(encoding="utf-8") as f:
            cls.manifest_schema = json.load(f)

    def _sample_model(self) -> dict:
        return {
            "schemaVersion": "advocate-chambers.project.v2",
            "projectId": "proj-sample-chambers",
            "units": "inch",
            "levels": [
                {"id": "L0", "name": "Ground Floor", "elevation": 0.0}
            ],
            "walls": [
                {"id": "w1", "start": [0, 0], "end": [240, 0], "thickness": 9.0, "levelId": "L0"},
                {"id": "w2", "start": [240, 0], "end": [240, 180], "thickness": 9.0, "levelId": "L0"},
                {"id": "w3", "start": [240, 180], "end": [0, 180], "thickness": 9.0, "levelId": "L0"},
                {"id": "w4", "start": [0, 180], "end": [0, 0], "thickness": 9.0, "levelId": "L0"},
            ],
            "openings": [
                {"id": "op1", "kind": "door", "wallId": "w1", "offset": 36.0, "width": 36.0, "levelId": "L0"}
            ],
            "spaces": [
                {
                    "id": "sp1",
                    "name": "Senior Advocate Chamber",
                    "kind": "chamber",
                    "polygon": [[0, 0], [240, 0], [240, 180], [0, 180]],
                    "area": 300.0,
                    "levelId": "L0",
                }
            ],
        }

    def test_fixture_integrity(self):
        self.assertEqual(self.fixture["version"], "phase8.presentation-contract.v1")
        for preset in self.fixture["cameraPresets"]:
            self.assertIn(preset, CAMERA_PRESETS)
        for style in self.fixture["styleVersions"]:
            self.assertIn(style, STYLE_TOKENS)

    def test_camera_presets_have_valid_structure(self):
        for name, preset in CAMERA_PRESETS.items():
            self.assertEqual(preset["preset"], name)
            self.assertIn(preset["projection"], ("orthographic", "perspective"))
            self.assertEqual(len(preset["position"]), 3)
            self.assertEqual(len(preset["target"]), 3)

    def test_asset_catalog_items_have_clearance_and_presentation_only(self):
        self.assertGreaterEqual(len(ASSET_CATALOG), 6)
        for asset_id, asset in ASSET_CATALOG.items():
            self.assertEqual(asset["assetId"], asset_id)
            self.assertTrue(asset["presentationOnly"])
            self.assertIn("dimensions", asset)
            self.assertIn("clearanceEnvelope", asset)
            self.assertIn("permittedRotations", asset)

    def test_render_manifest_generation_and_validation(self):
        manifest = build_render_manifest(
            model_sha256="a" * 64,
            style_version="presentation-residential-v1",
            camera_preset="axonometric-east-front",
            seed=42,
        )
        # Verify against required fields in fixture
        for field_name in self.fixture["requiredManifestFields"]:
            self.assertIn(field_name, manifest)
        self.assertTrue(manifest["presentationOnly"])
        self.assertEqual(manifest["schemaVersion"], "advocate-chambers.render-manifest.v1")

    def test_compile_presentation_scene_separates_technical_and_presentation(self):
        model = self._sample_model()
        compiled = compile_presentation_scene(model)

        self.assertIn("technicalScene", compiled)
        self.assertIn("presentationScene", compiled)
        self.assertIn("renderManifest", compiled)

        tech = compiled["technicalScene"]
        pres = compiled["presentationScene"]

        # Technical scene retains authoritative structure
        self.assertEqual(len(tech["walls"]), 4)
        self.assertEqual(len(tech["spaces"]), 1)
        self.assertEqual(tech["spaces"][0]["name"], "Senior Advocate Chamber")

        # Presentation scene adds material tokens and contextual assets
        self.assertTrue(pres["presentationOnly"])
        self.assertEqual(pres["styleVersion"], "presentation-residential-v1")
        self.assertTrue(any(it["type"] == "material-layer" for it in pres["items"]))
        # Advocate Chamber gets advocate-desk suggested
        self.assertTrue(any("advocate-desk" in it.get("assetId", "") for it in pres["items"]))

    def test_presentation_does_not_mutate_canonical_geometry(self):
        model = self._sample_model()
        model_before = json.loads(json.dumps(model))
        compile_presentation_scene(model)
        self.assertEqual(model, model_before, "Presentation compilation must never mutate source model")

    def test_render_presentation_svg_produces_valid_vector_drawing(self):
        model = self._sample_model()
        compiled = compile_presentation_scene(model)
        svg = render_presentation_svg(compiled, width=1200, height=800)

        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn('id="layer-spaces"', svg)
        self.assertIn('id="layer-walls"', svg)
        self.assertIn('id="layer-presentation-assets"', svg)
        self.assertIn('id="presentation-watermark"', svg)
        self.assertIn("Senior Advocate Chamber", svg)


if __name__ == "__main__":
    unittest.main()
