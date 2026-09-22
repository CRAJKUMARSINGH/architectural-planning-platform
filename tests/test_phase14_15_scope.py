"""Tests for Phase 14 & 15 scope definitions and contract fixtures."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASE14_CONTRACT_PATH = ROOT / "tests" / "fixtures" / "phase14" / "phase14_contract.json"
PHASE15_CONTRACT_PATH = ROOT / "tests" / "fixtures" / "phase15" / "phase15_contract.json"
PLAN_PATH = ROOT / "docs" / "IMPLEMENTATION_PLAN.md"


@pytest.fixture(scope="module")
def phase14_contract() -> dict:
    with open(PHASE14_CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def phase15_contract() -> dict:
    with open(PHASE15_CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPhase14And15ScopeDefinitions:
    def test_phase14_contract_structure(self, phase14_contract):
        assert phase14_contract["phase"] == "14-regulatory-compliance-and-statutory-submission"
        assert phase14_contract["status"] == "PENDING_PRODUCT_OWNER_SPECIFICATION"
        assert len(phase14_contract["deliverables"]) > 0
        assert len(phase14_contract["exitCriteria"]) > 0

    def test_phase15_contract_structure(self, phase15_contract):
        assert phase15_contract["phase"] == "15-ai-assisted-generative-space-planning"
        assert phase15_contract["status"] == "PENDING_PRODUCT_OWNER_SPECIFICATION"
        assert len(phase15_contract["deliverables"]) > 0
        assert len(phase15_contract["exitCriteria"]) > 0

    def test_implementation_plan_documents_phase14_15_stubs(self):
        plan_content = PLAN_PATH.read_text(encoding="utf-8")
        assert "Phase 14" in plan_content
        assert "Phase 15" in plan_content
