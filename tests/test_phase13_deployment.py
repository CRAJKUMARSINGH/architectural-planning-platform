"""Tests for Phase 13 Observability and Performance deployment configuration and tools."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "phase13" / "deployment_contract.json"
DASHBOARD_PATH = ROOT / "deploy" / "observability" / "grafana" / "dashboards" / "architectural-planning-platform.json"
OTEL_CONFIG_PATH = ROOT / "deploy" / "observability" / "otel-collector-config.yaml"
PROMETHEUS_CONFIG_PATH = ROOT / "deploy" / "observability" / "prometheus.yml"
LOAD_TEST_SCRIPT_PATH = ROOT / "scripts" / "load_test.py"


@pytest.fixture(scope="module")
def contract() -> dict:
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def dashboard() -> dict:
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPhase13DeploymentArtifacts:
    def test_all_contract_artifacts_exist(self, contract):
        for artifact_rel_path in contract["deploymentArtifacts"]:
            path = ROOT / artifact_rel_path
            assert path.exists(), f"Missing required deployment artifact: {artifact_rel_path}"
            assert path.stat().st_size > 0, f"Empty artifact: {artifact_rel_path}"

    def test_otel_collector_config_structure(self, contract):
        content = OTEL_CONFIG_PATH.read_text(encoding="utf-8")
        assert "otlp:" in content
        assert "4317" in content
        assert "4318" in content
        assert "8889" in content
        assert "prometheus:" in content
        assert "batch:" in content
        assert "memory_limiter:" in content

    def test_prometheus_scrape_config_targets(self):
        content = PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8")
        assert "architectural-planning-platform-api" in content
        assert "/metrics" in content
        assert "otel-collector" in content

    def test_grafana_dashboard_structure(self, contract, dashboard):
        assert dashboard["uid"] == contract["grafana"]["dashboardUid"]
        panel_titles = [p["title"] for p in dashboard.get("panels", [])]
        for req_title in contract["grafana"]["requiredPanels"]:
            assert req_title in panel_titles, f"Missing required panel: {req_title}"

        # Verify all 10 pipeline stages are referenced in queries
        dashboard_str = json.dumps(dashboard)
        for stage in contract["pipelineStages"]:
            assert "pipeline_stage_duration_seconds" in dashboard_str


class TestPhase13LoadTestingTool:
    def test_load_test_calculate_stats(self):
        from scripts.load_test import calculate_stats

        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = calculate_stats(latencies, errors=[], total_duration_s=1.0)

        assert stats.count == 5
        assert stats.success_count == 5
        assert stats.error_count == 0
        assert stats.min_ms == 10.0
        assert stats.p50_ms == 30.0
        assert stats.max_ms == 50.0
        assert stats.requests_per_second == 5.0

    def test_synthetic_load_test_execution(self):
        from scripts.load_test import run_synthetic_pipeline_load

        report = run_synthetic_pipeline_load(iterations=3, concurrency=1)
        assert "health_check" in report
        assert "metrics_scrape" in report
        assert "command_preview" in report
        assert report["health_check"]["success_count"] == 3
        assert report["metrics_scrape"]["success_count"] == 3
