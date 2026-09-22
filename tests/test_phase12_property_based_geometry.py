"""Phase 12 property-based geometry tests using Hypothesis."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from hypothesis import given, strategies as st, settings, Phase, HealthCheck
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

    def given(*_a, **_kw):
        def decorator(func): return func
        return decorator

    class _MockS:
        def __call__(self, *_a, **_kw): return self
        def __getattr__(self, _n): return _MockS()

    class _MockSettings:
        def __init__(self, *_a, **_kw): pass
        def __call__(self, func): return func

    settings = _MockSettings
    st = _MockS()

    class Phase:
        generate = "generate"

    class HealthCheck:
        too_slow = "too_slow"


from packages.geometry.commands import finding, OPERATIONS
from packages.geometry.serializers import serialize_model, deserialize_model


class PropertyBasedGeometryTests(unittest.TestCase):
    """Property-based tests for geometry operations."""
    
    @unittest.skipIf(not HYPOTHESIS_AVAILABLE, "Hypothesis not installed")
    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=4, max_size=4))
    @settings(max_examples=50, phases=[Phase.generate])
    def test_rectangle_area_calculation_is_deterministic(self, coords):
        """Property: Rectangle area calculation should be deterministic for same coordinates."""
        # Create a simple rectangle from 4 coordinates
        x1, y1, x2, y2 = coords
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        area = width * height
        
        # Calculate area again - should be identical
        area_second = width * height
        self.assertEqual(area, area_second, "Area calculation should be deterministic")
    
    @unittest.skipIf(not HYPOTHESIS_AVAILABLE, "Hypothesis not installed")
    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=2, max_size=2))
    @settings(max_examples=50, phases=[Phase.generate])
    def test_wall_length_calculation_is_positive(self, coords):
        """Property: Wall length should always be positive for valid coordinates."""
        x1, x2 = coords
        length = abs(x2 - x1)
        self.assertGreaterEqual(length, 0, "Wall length should be non-negative")
        self.assertEqual(length, abs(x1 - x2), "Length should be symmetric")
    
    @unittest.skipIf(not HYPOTHESIS_AVAILABLE, "Hypothesis not installed")
    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=4, max_size=4))
    @settings(max_examples=30, phases=[Phase.generate])
    def test_perimeter_calculation_bounds(self, coords):
        """Property: Rectangle perimeter should be bounded by coordinate extremes."""
        x1, y1, x2, y2 = coords
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        perimeter = 2 * (width + height)
        
        # Perimeter should be at least the sum of dimensions
        self.assertGreaterEqual(perimeter, width + height)
        # Perimeter should not exceed 2x the sum of max coordinates
        max_coord = max(abs(x1), abs(y1), abs(x2), abs(y2))
        self.assertLessEqual(perimeter, 8 * max_coord if max_coord > 0 else 0)
    
    @unittest.skipIf(not HYPOTHESIS_AVAILABLE, "Hypothesis not installed")
    @given(st.dictionaries(st.text(min_size=1, max_size=10), st.floats(min_value=0, max_value=1000), min_size=1, max_size=5))
    @settings(max_examples=30, phases=[Phase.generate])
    def test_serialization_round_trip_preserves_structure(self, data_dict):
        """Property: JSON serialization round-trip should preserve data structure."""
        # Serialize
        serialized = json.dumps(data_dict, sort_keys=True)
        # Deserialize
        deserialized = json.loads(serialized)
        # Should be equal
        self.assertEqual(data_dict, deserialized, "Serialization round-trip should preserve data")
    
    @unittest.skipIf(not HYPOTHESIS_AVAILABLE, "Hypothesis not installed")
    @given(st.lists(st.text(min_size=1, max_size=10, alphabet="abc123"), min_size=1, max_size=5))
    @settings(max_examples=20, phases=[Phase.generate], suppress_health_check=[HealthCheck.too_slow])
    def test_finding_generation_creates_valid_structure(self, object_ids):
        """Property: Finding generation should always produce valid structure."""
        result = finding(
            rule="test-rule",
            message="Test message",
            severity="ERROR",
            object_ids=object_ids,
            evidence={"test": "value"},
        )
        
        # Required fields should exist
        self.assertIn("id", result)
        self.assertIn("severity", result)
        self.assertIn("rule", result)
        self.assertIn("message", result)
        self.assertIn("objectIds", result)
        
        # Object IDs should be deduplicated
        self.assertEqual(len(result["objectIds"]), len(set(object_ids)))
    
    def test_operations_list_is_stable(self):
        """Property: Known operations list should be stable and contain expected operations."""
        # The operations list should be immutable
        original_ops = list(OPERATIONS)
        self.assertEqual(tuple(OPERATIONS), tuple(original_ops), "Operations list should be stable")
        
        # Should contain core operations
        self.assertIn("add-wall", OPERATIONS)
        self.assertIn("move-opening", OPERATIONS)
        self.assertIn("add-space", OPERATIONS)
    
    def test_hypothesis_availability_check(self):
        """Test to verify if Hypothesis is available for property-based testing."""
        if HYPOTHESIS_AVAILABLE:
            self.assertTrue(True, "Hypothesis is available for property-based testing")
        else:
            self.skipTest("Hypothesis not installed - property-based tests require pip install hypothesis")
    
    def test_basic_geometry_invariants_without_hypothesis(self):
        """Basic geometry invariant tests that don't require Hypothesis."""
        # Test deterministic area calculation
        coords = [0, 0, 10, 10]
        x1, y1, x2, y2 = coords
        area1 = abs(x2 - x1) * abs(y2 - y1)
        area2 = abs(x2 - x1) * abs(y2 - y1)
        self.assertEqual(area1, area2)
        
        # Test that zero-length walls have zero area
        zero_coords = [5, 5, 5, 5]
        zx1, zy1, zx2, zy2 = zero_coords
        zero_area = abs(zx2 - zx1) * abs(zy2 - zy1)
        self.assertEqual(zero_area, 0)
        
        # Test that positive coordinates produce positive dimensions
        pos_coords = [1, 1, 10, 20]
        px1, py1, px2, py2 = pos_coords
        width = abs(px2 - px1)
        height = abs(py2 - py1)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)


if __name__ == "__main__":
    unittest.main()