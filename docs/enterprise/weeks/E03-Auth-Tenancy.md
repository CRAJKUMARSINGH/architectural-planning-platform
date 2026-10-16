# Week E03 — Auth & Multi-tenancy — ✅ COMPLETE

**Status:** Complete  
**Completed:** 2026-09-22  
**ADR:** `docs/ADR-004-oidc-deployment.md` · `docs/architecture/ADR-003-Tenancy-Model.md`

## Summary

Introduced JWT/OIDC identity, organizations, memberships, and role-based authorization.
Local single-developer mode preserved via `AUTH_DISABLED=true` dev bypass.

## Deliverables Completed

- `services/api/auth.py` — JWT/OIDC validation, JWKS key rotation via PyJWKClient,
  clock-skew tolerance, disabled-user enforcement, `assert_auth_configuration()` startup guard
- `services/api/authorization.py` — project-scoped dependency enforcing org membership
- ORM models: `Organization`, `Membership`, `User` with roles owner/editor/viewer/reviewer
- `AUTH_DISABLED=true` rejected at startup when `ENV=staging` or `ENV=production`
- Keycloak OIDC deployment: `deploy/oidc/` (docker-compose, realm template, `.env.example`)
- `ADR-004-oidc-deployment.md` with reference architecture and operational runbook
- Regression fixtures: `tests/fixtures/e03/` — roles_matrix.json, org_isolation_scenarios.json
- `tests/test_e03_auth_expanded.py` — role weight, cross-org isolation, JWT decode, audit

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Unauthenticated requests return 401 | ✅ Pass |
| User A cannot see User B's project | ✅ Pass |
| Audit log records actor + resource | ✅ Pass |
| `docker compose` works with seeded dev user | ✅ Pass |
| `AUTH_DISABLED` rejected in staging/production | ✅ Pass |
