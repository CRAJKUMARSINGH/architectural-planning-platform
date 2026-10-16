# Week E09 — Staging & Release Process — 📋 IN PROGRESS

**Status:** In Progress  
**Target:** Next sprint  
**ADR:** `docs/ADR-004-oidc-deployment.md`

## Goal

Reproducible deployment path and disciplined release process. After E09, a single
`docker compose up` brings up the full staging-like stack, and a release tag produces
versioned artifacts + quality-gate summary + SBOM automatically.

## Tasks

### 1. Docker image hardening
- [ ] Pin all `FROM` base image digests in `Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.web`
- [ ] Add non-root user in each Dockerfile (`RUN adduser --disabled-password appuser`)
- [ ] Add `HEALTHCHECK` instructions to each image
- [ ] Confirm `docker compose up --build` brings up full working stack end-to-end

### 2. Request hardening (deferred from E08)
- [ ] Add request body size limit middleware to FastAPI (`app.add_middleware(...)`)
- [ ] Add IP-level rate limiting (e.g. `slowapi` or nginx upstream limit)
- [ ] Add security response headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains`
  - `Content-Security-Policy` — strict policy for API
  - `Permissions-Policy`

### 3. SBOM in CI
- [ ] Add `syft` or `cyclonedx-bom` to CI release workflow
- [ ] Attach SBOM JSON to every GitHub Release created from a `v*` tag
- [ ] Verify SBOM includes both Python and Node dependency trees

### 4. Semantic release automation
- [ ] Release workflow: auto-bump version in `package.json` + `pyproject.toml` from git tag
- [ ] Auto-generate release notes from `CHANGELOG.md` section matching the tag
- [ ] Attach quality-gate report + adversarial summary + SBOM as release assets

### 5. Staging smoke test
- [ ] Document and script a staging smoke test:
  - `GET /health` → 200
  - `GET /ready` → 200 (Postgres + Redis green)
  - `POST /api/v1/projects/` → 401 (no token)
  - `POST /api/v1/projects/` with valid JWT → 201
  - `POST /api/v1/projects/{id}/commands/preview` → returns findings
- [ ] Add this as a `make staging-smoke` target
- [ ] Run it in CI against the staging Docker stack after deploy

### 6. Environment promotion checklist
- [ ] Document the `development → staging → production` promotion sequence
- [ ] Confirm `AUTH_DISABLED` guard fires in staging before any service starts
- [ ] Confirm `CORS_ALLOW_ORIGINS` and `METRICS_TOKEN` are set in staging env

## Acceptance Criteria

| Criterion | Done? |
|-----------|-------|
| `docker compose up` brings up working multi-service stack | ⬜ |
| Tagged release produces versioned artifacts + quality-gate + SBOM | ⬜ |
| Staging can run full adversarial suite against realistic fixtures | ⬜ |
| Security headers present on all API responses | ⬜ |
| Request size + rate limits enforced | ⬜ |
