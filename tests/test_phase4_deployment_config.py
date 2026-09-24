"""Tests for Phase 4 OIDC Identity Provider deployment configuration and templates."""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "phase4" / "oidc_deployment_contract.json"
ENV_EXAMPLE_PATH = ROOT / "deploy" / "oidc" / ".env.example"
COMPOSE_PATH = ROOT / "deploy" / "oidc" / "docker-compose.oidc.yml"
REALM_TEMPLATE_PATH = ROOT / "deploy" / "oidc" / "keycloak-realm-template.json"
ADR_PATH = ROOT / "docs" / "ADR-004-oidc-deployment.md"


@pytest.fixture(scope="module")
def contract() -> dict:
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def realm_template() -> dict:
    with open(REALM_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPhase4DeploymentArtifacts:
    def test_all_contract_artifacts_exist(self, contract):
        for artifact_rel_path in contract["deploymentArtifacts"]:
            path = ROOT / artifact_rel_path
            assert path.exists(), f"Missing required deployment artifact: {artifact_rel_path}"
            assert path.stat().st_size > 0, f"Empty artifact: {artifact_rel_path}"

    def test_env_example_contains_all_required_variables(self, contract):
        env_content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
        for var in contract["requiredEnvVariables"]:
            assert f"{var}=" in env_content, f"Missing env variable in .env.example: {var}"

    def test_keycloak_realm_template_structure(self, contract, realm_template):
        assert realm_template["realm"] == contract["keycloak"]["realmName"]
        assert realm_template["enabled"] is True

        # Verify roles
        realm_roles = [r["name"] for r in realm_template["roles"]["realm"]]
        for role in contract["roles"]:
            assert role in realm_roles, f"Missing realm role: {role}"

        # Verify clients
        clients = {c["clientId"]: c for c in realm_template["clients"]}
        api_client_id = contract["keycloak"]["clientId"]
        spa_client_id = contract["keycloak"]["spaClientId"]

        assert api_client_id in clients, f"Missing API client: {api_client_id}"
        assert spa_client_id in clients, f"Missing SPA client: {spa_client_id}"

        api_client = clients[api_client_id]
        assert api_client["bearerOnly"] is True

        # Verify mappers on API client
        mapper_names = [m["name"] for m in api_client.get("protocolMappers", [])]
        for req_mapper in contract["keycloak"]["requiredMappers"]:
            assert req_mapper in mapper_names, f"Missing protocol mapper: {req_mapper}"

    def test_adr_documents_security_requirements(self, contract):
        adr_text = ADR_PATH.read_text(encoding="utf-8")
        assert "OIDC_JWKS_URL" in adr_text
        assert "AUTH_DISABLED" in adr_text
        assert "architectural-planning-platform-api" in adr_text
        for role in contract["roles"]:
            assert role in adr_text


class TestPhase4AuthConfigurationValidation:
    def test_auth_configuration_errors_detects_staging_violations(self, monkeypatch):
        from services.api.auth import auth_configuration_errors

        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("AUTH_DISABLED", "true")
        monkeypatch.delenv("OIDC_ISSUER", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)

        import services.api.auth as auth_mod
        monkeypatch.setattr(auth_mod, "ENVIRONMENT", "production")
        monkeypatch.setattr(auth_mod, "AUTH_DISABLED", True)
        monkeypatch.setattr(auth_mod, "OIDC_ISSUER", "")
        monkeypatch.setattr(auth_mod, "JWT_SECRET", "")

        errors = auth_configuration_errors()
        assert any("AUTH_DISABLED must be false" in e for e in errors)
        assert any("OIDC_ISSUER or a non-development JWT_SECRET is required" in e for e in errors)

    def test_auth_configuration_validates_oidc_settings(self, monkeypatch):
        import services.api.auth as auth_mod

        monkeypatch.setattr(auth_mod, "ENVIRONMENT", "production")
        monkeypatch.setattr(auth_mod, "AUTH_DISABLED", False)
        monkeypatch.setattr(auth_mod, "OIDC_ISSUER", "https://auth.example.com/realms/architectural-planning-platform")
        monkeypatch.setattr(auth_mod, "OIDC_AUDIENCE", "")
        monkeypatch.setattr(auth_mod, "OIDC_JWKS_URL", "")

        errors = auth_mod.auth_configuration_errors()
        assert any("OIDC_AUDIENCE is required" in e for e in errors)
        assert any("OIDC_JWKS_URL is required" in e for e in errors)
