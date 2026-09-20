import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from week28 import (  # noqa: E402
    PROJECTS,
    build_inventory,
    build_registry,
    classify_path,
    proposed_destination,
    role_for_path,
)


class Week28OrganizationTests(unittest.TestCase):
    def test_three_delivered_projects_are_registered(self):
        registry = build_registry()
        self.assertEqual(len(registry["projects"]), 3)
        self.assertEqual(set(PROJECTS), {
            "bar-association-hall",
            "jamuniya-shaktawat",
            "advocate-chambers",
        })
        self.assertTrue(registry["migrationPolicy"]["legacyPathsPreserved"])

    def test_known_paths_are_scoped_and_have_roles(self):
        cases = {
            "bar-association-hall/INPUTS/site.pdf": ("bar-association-hall", "input-reference"),
            "Jamuniya-Shaktawat/PDF/final.pdf": ("jamuniya-shaktawat", "pdf-output"),
            "CAD-Drawings/DXF/01-plan.dxf": ("advocate-chambers", "cad-output"),
            "scripts/week28.py": ("shared-repository", "shared-engineering"),
        }
        for path, expected in cases.items():
            project_id, _, _ = classify_path(path)
            self.assertEqual((project_id, role_for_path(path, project_id)), expected)

    def test_ambiguous_root_asset_remains_visible_for_review(self):
        project_id, confidence, review_required = classify_path("forecast estimate.xlsx")
        role = role_for_path("forecast estimate.xlsx", project_id)
        destination = proposed_destination("forecast estimate.xlsx", project_id, role)
        self.assertEqual(project_id, "advocate-chambers")
        self.assertEqual(confidence, "inferred-root-asset")
        self.assertTrue(review_required)
        self.assertIn("projects/advocate-chambers/", destination)

    def test_inventory_covers_tracked_paths(self):
        inventory = build_inventory()
        tracked = __import__("week28").tracked_paths()
        self.assertEqual(inventory["entryCount"], len(tracked))
        self.assertEqual(len(inventory["entries"]), len(tracked))
        self.assertTrue(all(entry["proposedCanonicalPath"]
                            for entry in inventory["entries"]))


if __name__ == "__main__":
    unittest.main()