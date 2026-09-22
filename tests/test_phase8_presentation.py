"""Phase 8 presentation scene compiler and render manifest regressions."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

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
from packages.geometry.vector_overlays import (
    calculate_room_labels,
    calculate_wall_dimensions,
    add_vector_overlays_to_svg,
)
from packages.geometry.blender_render import (
    validate_blender_environment,
    generate_blender_python_script,
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
        
        # Validate against JSON schema if available
        if JSONSCHEMA_AVAILABLE:
            import jsonschema
            jsonschema.validate(instance=manifest, schema=self.manifest_schema)

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


    def test_presentation_api_routes(self):
        import os
        from fastapi.testclient import TestClient
        from services.api.main import app

        orig_auth = os.environ.get("AUTH_DISABLED")
        os.environ["AUTH_DISABLED"] = "true"
        try:
            client = TestClient(app)
            # Catalog endpoints
            r_assets = client.get("/api/v1/presentation/assets")
            self.assertEqual(r_assets.status_code, 200)
            self.assertIn("assets", r_assets.json())

            r_styles = client.get("/api/v1/presentation/styles")
            self.assertEqual(r_styles.status_code, 200)
            self.assertIn("styles", r_styles.json())

            r_cameras = client.get("/api/v1/presentation/cameras")
            self.assertEqual(r_cameras.status_code, 200)
            self.assertIn("presets", r_cameras.json())
            
            # Blender status endpoint
            r_blender = client.get("/api/v1/presentation/blender/status")
            self.assertEqual(r_blender.status_code, 200)
            self.assertIn("blender_available", r_blender.json())
        finally:
            if orig_auth is None:
                os.environ.pop("AUTH_DISABLED", None)
            else:
                os.environ["AUTH_DISABLED"] = orig_auth

    def test_vector_overlays_calculate_dimensions(self):
        model = self._sample_model()
        dimensions = calculate_wall_dimensions(model["walls"], scale=1.0, units="inch")
        
        self.assertGreater(len(dimensions), 0)
        for dim in dimensions:
            self.assertIsInstance(dim.start_point, tuple)
            self.assertIsInstance(dim.end_point, tuple)
            self.assertTrue(len(dim.text) > 0)
            self.assertEqual(dim.units, "inch")

    def test_vector_overlays_calculate_labels(self):
        model = self._sample_model()
        labels = calculate_room_labels(model["spaces"], show_area=True, show_dimensions=False)
        
        self.assertGreater(len(labels), 0)
        # Should have name and area labels for each space
        self.assertTrue(any("Senior Advocate Chamber" in lbl.text for lbl in labels))
        self.assertTrue(any("sq.ft" in lbl.text for lbl in labels))

    def test_vector_overlays_add_to_svg(self):
        model = self._sample_model()
        compiled = compile_presentation_scene(model)
        base_svg = render_presentation_svg(compiled)
        
        dimensions = calculate_wall_dimensions(model["walls"])
        labels = calculate_room_labels(model["spaces"])
        
        enhanced_svg = add_vector_overlays_to_svg(base_svg, dimensions, labels)
        
        self.assertIn("layer-dimensions", enhanced_svg)
        self.assertIn("layer-labels", enhanced_svg)
        self.assertTrue(enhanced_svg.endswith("</svg>"))

    def test_blender_environment_validation(self):
        status = validate_blender_environment()
        
        self.assertIn("blender_available", status)
        self.assertIn("python_supported", status)
        # Blender may not be available in test environment
        # but the validation function should not crash

    def test_blender_script_generation(self):
        model = self._sample_model()
        compiled = compile_presentation_scene(model)
        
        from pathlib import Path
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            script = generate_blender_python_script(compiled, output_path, "PNG")
            
            self.assertIn("import bpy", script)
            self.assertIn("camera_obj", script)
            self.assertIn("bpy.ops.render.render", script)
            self.assertIn(str(output_path), script)
        finally:
            if output_path.exists():
                output_path.unlink()


if __name__ == "__main__":
    unittest.main()
