"""Phase 10 export and delivery package regressions."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase10" / "delivery_contract.json"
sys.path.insert(0, str(ROOT))

from packages.geometry.delivery import (
    build_delivery_package,
    create_delivery_package_json,
    generate_dxf_export,
    generate_pdf_export,
    generate_svg_export,
    generate_json_export,
    generate_package_manifest,
    verify_artifact_integrity,
    DeliveryPackage,
    ExportMetadata,
)


class Phase10DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open(encoding="utf-8") as f:
            cls.fixture = json.load(f)

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
        self.assertEqual(self.fixture["version"], "phase10.delivery-contract.v1")
        self.assertIn("requiredArtifacts", self.fixture)
        self.assertIn("requiredManifestFields", self.fixture)
        self.assertTrue(self.fixture["rules"]["blockerExcludesIssuable"])

    def test_export_metadata_structure(self):
        metadata = ExportMetadata(
            artifact_id="test-artifact-1",
            artifact_type="dxf",
            model_sha256="a" * 64,
            rule_pack_version="india-preliminary-review",
            engine_version="traecad-0.1.0",
            project_id="proj-test",
            revision_id="rev-1",
        )
        
        self.assertEqual(metadata.artifact_id, "test-artifact-1")
        self.assertEqual(metadata.artifact_type, "dxf")
        self.assertTrue(metadata.professional_review_required)

    def test_dxf_export_generation(self):
        model = self._sample_model()
        metadata = ExportMetadata(
            artifact_id="test-dxf-1",
            artifact_type="dxf",
            model_sha256="a" * 64,
            rule_pack_version="india-preliminary-review",
            engine_version="traecad-0.1.0",
        )
        
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            result = generate_dxf_export(model, output_path, metadata)
            self.assertTrue(result["success"])
            self.assertIn("layers", result["metadata"])
            self.assertIn("title_block", result["metadata"])
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_pdf_export_generation(self):
        model = self._sample_model()
        metadata = ExportMetadata(
            artifact_id="test-pdf-1",
            artifact_type="pdf",
            model_sha256="a" * 64,
            rule_pack_version="india-preliminary-review",
            engine_version="traecad-0.1.0",
        )
        
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            result = generate_pdf_export(model, output_path, metadata)
            self.assertTrue(result["success"])
            self.assertIn("title_block", result["metadata"])
            self.assertEqual(result["metadata"]["artifact_type"], "pdf")
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_svg_export_generation(self):
        model = self._sample_model()
        metadata = ExportMetadata(
            artifact_id="test-svg-1",
            artifact_type="svg",
            model_sha256="a" * 64,
            rule_pack_version="india-preliminary-review",
            engine_version="traecad-0.1.0",
        )
        
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            result = generate_svg_export(model, output_path, metadata)
            self.assertTrue(result["success"])
            self.assertTrue(result["metadata"]["vector_precision"])
            self.assertEqual(result["metadata"]["artifact_type"], "svg")
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_json_export_generation(self):
        model = self._sample_model()
        metadata = ExportMetadata(
            artifact_id="test-json-1",
            artifact_type="json",
            model_sha256="a" * 64,
            rule_pack_version="india-preliminary-review",
            engine_version="traecad-0.1.0",
        )
        
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "model.json"
            
            result = generate_json_export(model, output_path, metadata)
            self.assertTrue(result["success"])
            self.assertTrue(output_path.exists())
            self.assertEqual(result["metadata"]["artifact_type"], "json")
            
            # Verify JSON is valid
            loaded_model = json.loads(output_path.read_text())
            self.assertEqual(loaded_model["projectId"], "proj-sample-chambers")

    def test_delivery_package_structure(self):
        model = self._sample_model()
        
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            package = build_delivery_package(
                model=model,
                project_id="proj-sample-chambers",
                project_name="Sample Chambers",
                revision_id="rev-1",
                revision_number=1,
                output_dir=output_dir,
            )
            
            self.assertEqual(package.project_id, "proj-sample-chambers")
            self.assertEqual(package.project_name, "Sample Chambers")
            self.assertEqual(package.revision_number, 1)
            self.assertGreater(len(package.artifacts), 0)
            self.assertGreater(len(package.assumptions), 0)
            self.assertIn("disclaimer", package.__dict__)

    def test_package_manifest_generation(self):
        model = self._sample_model()
        
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            package = build_delivery_package(
                model=model,
                project_id="proj-sample-chambers",
                project_name="Sample Chambers",
                revision_id="rev-1",
                revision_number=1,
                output_dir=output_dir,
            )
            
            manifest = generate_package_manifest(package)
            
            # Verify required fields from fixture
            for field_name in self.fixture["requiredManifestFields"]:
                self.assertIn(field_name, manifest)
            
            self.assertEqual(manifest["schemaVersion"], "advocate-chambers.delivery-manifest.v1")
            self.assertTrue(manifest["rules"]["blockerExcludesIssuable"])

    def test_delivery_package_json_creation(self):
        model = self._sample_model()
        
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            package = build_delivery_package(
                model=model,
                project_id="proj-sample-chambers",
                project_name="Sample Chambers",
                revision_id="rev-1",
                revision_number=1,
                output_dir=output_dir,
            )
            
            manifest_path = output_dir / "package-manifest.json"
            result = create_delivery_package_json(package, manifest_path)
            
            self.assertTrue(result["success"])
            self.assertTrue(manifest_path.exists())
            self.assertIn("packageSignature", result)
            self.assertEqual(result["artifact_count"], len(package.artifacts))

    def test_artifact_integrity_verification(self):
        from tempfile import NamedTemporaryFile
        
        # Create a test file with known content
        test_content = b"test artifact content"
        with NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)
            f.write(test_content)
        
        try:
            expected_hash = hashlib.sha256(test_content).hexdigest()
            result = verify_artifact_integrity(test_path, expected_hash)
            
            self.assertTrue(result["valid"])
            self.assertEqual(result["actual_hash"], expected_hash)
            
            # Test with wrong hash
            wrong_hash = "a" * 64
            result_wrong = verify_artifact_integrity(test_path, wrong_hash)
            self.assertFalse(result_wrong["valid"])
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_quality_gate_integration(self):
        model = self._sample_model()
        validation_report = {
            "status": "PASS",
            "findings": [],
            "evidence": {"criticalDefects": 0, "falseNegatives": 0},
        }
        
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            package = build_delivery_package(
                model=model,
                project_id="proj-sample-chambers",
                project_name="Sample Chambers",
                revision_id="rev-1",
                revision_number=1,
                output_dir=output_dir,
                validation_report=validation_report,
            )
            
            self.assertEqual(package.quality_gate_status, "PASS")
            self.assertEqual(package.validation_report["status"], "PASS")

    def test_blocker_prevents_issuable_export(self):
        """Test that BLOCKER status prevents issuable exports."""
        validation_report = {
            "status": "BLOCKED",
            "findings": [{"severity": "BLOCKER", "rule": "critical-structural-issue"}],
        }
        
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            package = build_delivery_package(
                model=self._sample_model(),
                project_id="proj-sample-chambers",
                project_name="Sample Chambers",
                revision_id="rev-1",
                revision_number=1,
                output_dir=output_dir,
                validation_report=validation_report,
            )
            
            manifest = generate_package_manifest(package)
            self.assertEqual(manifest["qualityGateStatus"], "BLOCKED")
            self.assertTrue(manifest["rules"]["blockerExcludesIssuable"])


if __name__ == "__main__":
    unittest.main()