# ADR-004: Production OIDC & Identity Provider Deployment Architecture

- **Status:** Approved / Standardized
- **Date:** 2026-09-22
- **Context:** Phase 4 Authentication & Tenancy Hardening

## 1. Context and Problem Statement

The Architectural Planning Platform requires strict multi-tenant isolation, cryptographically verified user identity, and tenant-scoped role enforcement. While local development can use static bearer tokens or test secrets under isolated conditions, staging and production deployments must integrate with standard OpenID Connect (OIDC) identity providers (Keycloak, Auth0, Okta, AWS Cognito).

## 2. Decision

We mandate the following deployment configuration for all staging and production deployments:

1. **OIDC & JWKS Token Validation:**
   - The FastAPI backend validates incoming JWTs using the OIDC Discovery JWKS URL (`OIDC_JWKS_URL`).
   - Signature validation supports asymmetric algorithms (`RS256`, `RS384`, `RS512`, `ES256`, `ES384`, `ES512`).
   - Public keys are automatically refreshed upon key rotation via PyJWKClient.

2. **Claim Structure & Verification:**
   - `sub`: Canonical UUID of the user.
   - `org_id`: UUID of the organization/tenant isolation boundary.
   - `role`: One of `owner`, `editor`, `reviewer`, `viewer`.
   - `aud`: Must match `OIDC_AUDIENCE` (`architectural-planning-platform-api`).
   - `iss`: Must match `OIDC_ISSUER`.
   - `exp` & `nbf`: Standard expiration with configurable clock skew (`AUTH_CLOCK_SKEW_SECONDS`, max 300s).

3. **Disabled & Inactive User Check:**
   - Tokens with `disabled: true` or `is_active: false` claims are immediately rejected with `403 Forbidden`.
   - Revocation at the IdP is reflected immediately upon token expiry.

4. **Fail-Closed Configuration Guard:**
   - In staging/production (`ENV=staging` or `ENV=production`), `AUTH_DISABLED=true` is rejected on startup.
   - Using the default development secret in production triggers a fatal startup error (`RuntimeError`).

## 3. Reference Architecture

```text
+-----------------------+           +-----------------------+
|  React SPA (Frontend) |           |  Keycloak / OIDC IdP  |
+-----------------------+           +-----------------------+
        |                                       |
        | 1. Auth Code Flow + PKCE              |
        +-------------------------------------->|
        | 2. Issues JWT (sub, org_id, role, aud)|
        |<--------------------------------------+
        |
        | 3. Authorization: Bearer <JWT>
        v
+-----------------------+           +-----------------------+
|  FastAPI Backend      | --------> |  OIDC JWKS Endpoint   |
|  (Resource Server)    |   Fetch   |  (Public Key Rotation)|
+-----------------------+   Keys    +-----------------------+
        |
        | 4. Validate Sig, Iss, Aud, Exp
        | 5. Enforce Org Scoping & DB Membership
        v
+-----------------------+
| Postgres (Data Store) |
+-----------------------+
```

## 4. Operational Runbook

To deploy Keycloak locally for testing the OIDC flow:
```powershell
docker-compose -f deploy/oidc/docker-compose.oidc.yml up -d
```
The imported realm will be accessible at `http://localhost:8080/realms/architectural-planning-platform`.
