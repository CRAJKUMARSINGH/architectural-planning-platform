# Enterprise Roadmap — 10-Week Detailed Plan

**Baseline:** Current `main` of Advocate-Chambers (domain enrichment through ~Week 28 complete).  
**Goal:** Production-ready platform foundation without diluting the conservative review-first philosophy.

---

## Phase Overview

| Phase | Weeks | Theme                          | Outcome                                      |
|-------|-------|--------------------------------|----------------------------------------------|
| 0     | —     | Principles & Inventory         | Clear non-negotiables + current-state map    |
| 1     | E01   | Foundation & Hygiene           | Clean monorepo, tooling, baselines           |
| 2     | E02   | Persistence                    | Durable projects/revisions/jobs              |
| 3     | E03   | Identity & Tenancy             | Auth + orgs + roles + audit                  |
| 4     | E04   | Async Execution                | Queue + workers + content-addressed storage  |
| 5     | E05   | Automated Quality              | CI that enforces existing gates              |
| 6     | E06   | Product Surface Hardening      | Mature API + frontend contracts              |
| 7     | E07   | Observability                  | Logs, metrics, health                        |
| 8     | E08   | Security                       | Hardened surface + supply chain              |
| 9     | E09   | Staging & Release              | Reproducible deploy + release process        |
| 10    | E10   | Stabilization                  | Load, docs, final candidate tag              |

---

## Week E01 — Foundation & Hygiene

**Goal:** Make the repository and developer experience enterprise-ready without changing runtime behaviour.

### Deliverables
- Unified tooling (Python + Node)
- Shared configs (ESLint, Prettier, Ruff, mypy, EditorConfig)
- Proper monorepo package boundaries
- Baseline documentation (CONTRIBUTING, SECURITY, CODEOWNERS)
- Frozen baseline of current quality-gate + test reports

### Key Tasks
1. Introduce `pyproject.toml` + Ruff + mypy for all Python packages/scripts.
2. Align TypeScript strictness across `apps/web` and future packages.
3. Add `.editorconfig`, `.nvmrc`, `.python-version`.
4. Create `docs/` skeleton and move long-form reports out of root where sensible.
5. Capture current `quality-gate-report.json` + adversarial reports as `baselines/2026-09-20/`.
6. Add conventional-commit lint (commitlint or simple script).
7. Ensure `npm run typecheck:web` + full Python unittest suite are one-command runnable.

### Acceptance
- `make lint` (or equivalent) passes.
- Full existing test + quality-gate suite still green.
- New contributor can run the baseline in < 10 minutes after clone + install.

**Details:** See `weeks/E01-Foundation/`

---

## Week E02 — Persistence Layer

**Goal:** Replace in-memory JOBS/ARTIFACTS and ephemeral project state with durable storage while keeping geometry files authoritative.

### Deliverables
- Postgres schema (projects, revisions, jobs, artifacts, audit_events)
- SQLAlchemy/SQLModel (or equivalent) models + Alembic migrations
- Repository interfaces used by FastAPI
- Local Docker Compose service for Postgres

### Key Decisions
- Geometry (walls, openings, stairs, routes) remains in versioned JSON/files or content-addressed blobs.
- Database holds metadata, revision pointers, job state, and audit.
- Soft-delete + retention policy hooks from day one.

### Acceptance
- Create project → create revision → enqueue job → store artifact metadata works end-to-end against Postgres.
- Existing validation endpoints continue to function against file-backed canonical models.
- Migration is reversible.

**Details:** See `weeks/E02-Persistence/` and `samples/db/`

---

## Week E03 — Auth & Multi-tenancy

**Goal:** Introduce identity, organizations, and basic authorization without blocking local development.

### Deliverables
- JWT / OIDC integration (Clerk, Auth.js, or Keycloak)
- Organization + membership + role model (Owner / Editor / Viewer / Reviewer)
- Protected routes on all mutating endpoints
- Audit log entries for auth and model-changing actions
- Local “dev user” bypass for single-developer mode

### Acceptance
- Unauthenticated requests to protected routes return 401.
- A user can only see/modify projects belonging to their organization(s).
- Audit log records who changed what and when.
- Local docker-compose still works with a seeded dev user.

**Details:** See `weeks/E03-Auth-Tenancy/` and `architecture/ADR-003-Tenancy-Model.md`

---

## Week E04 — Async Jobs & Object Storage

**Goal:** Move long-running generate/validate/render work off the request path.

### Deliverables
- Redis + job queue (RQ, Arq, or Celery)
- Worker process that runs existing Python pipelines
- S3-compatible storage (MinIO local, real S3/R2 in staging)
- Content-addressable artifact storage (SHA-256)
- Job status API + simple progress reporting

### Acceptance
- `/generate` returns a job ID immediately.
- Worker produces the same deterministic artifacts as the old synchronous path.
- Artifact download is served via signed URL or controlled proxy.
- Failure cases leave the last valid revision intact (already required by Week 26 philosophy).

**Details:** See `weeks/E04-Jobs-Storage/`

---

## Week E05 — CI/CD & Automated Quality Gates

**Goal:** Make the existing rich test and quality-gate machinery enforce itself on every change.

### Deliverables
- GitHub Actions workflow (or equivalent)
- Jobs: lint → typecheck → unit → week enrichment validation → adversarial → performance smoke → quality-gate check
- Dependency and secret scanning
- SBOM generation on release tags
- Status checks required for merge to `main`

### Acceptance
- A PR that breaks an adversarial fixture or quality-gate contract cannot merge.
- Baseline reports are compared for unexpected regressions.
- Release tags produce a machine-readable quality-gate summary + SBOM.

**Details:** See `weeks/E05-CICD/` and `samples/github-actions/`

---

## Week E06 — API & Frontend Hardening

**Goal:** Turn the thin adapter into a stable product surface.

### Deliverables
- Versioned API (`/v1/...`)
- Complete OpenAPI with examples and error schemas
- Shared schema package (Pydantic ↔ Zod alignment)
- Frontend: proper error boundaries, loading/empty states, environment config
- Capability matrix exposed and respected by UI

### Acceptance
- OpenAPI validates against the running server.
- Frontend never assumes geometry authority.
- Breaking API changes require a new major version or explicit deprecation period.

**Details:** See `weeks/E06-API-Frontend/`

---

## Week E07 — Observability

**Goal:** Make the system operable.

### Deliverables
- Structured JSON logging with request/job IDs
- Basic Prometheus metrics (latency, queue depth, validation duration, error rates)
- Health / readiness / liveness endpoints that check real dependencies
- Simple Grafana dashboard JSON or equivalent
- Correlation of quality-gate runs with deploy versions

### Acceptance
- An operator can answer “is the system healthy?” and “why did this job fail?” from logs + metrics alone.
- Health endpoints fail when Postgres or Redis is unreachable.

**Details:** See `weeks/E07-Observability/`

---

## Week E08 — Security Hardening

**Goal:** Reduce attack surface and supply-chain risk.

### Deliverables
- Rate limiting and request size limits
- Dependency pinning + automated vulnerability scanning
- Secret scanning in CI
- Artifact integrity verification (already partially present — extend)
- Security headers, CORS tightening, input sanitization review
- SECURITY.md + vulnerability disclosure process

### Acceptance
- OWASP Top 10 mapping documented with mitigations.
- No high/critical dependency vulnerabilities in the default install.
- Signed artifacts can be verified offline.

**Details:** See `weeks/E08-Security/` and `checklists/security.md`

---

## Week E09 — Staging Environment & Release Process

**Goal:** Reproducible deployment path and disciplined releases.

### Deliverables
- Docker images for API, worker, web
- Docker Compose for local + staging-like stack
- Simple Kubernetes or Cloud Run manifests (optional but preferred)
- Semantic versioning + automated changelog
- Release checklist that includes quality-gate report
- Blue/green or canary skeleton

### Acceptance
- `docker compose up` brings up a working multi-service stack.
- A tagged release produces versioned artifacts + quality-gate summary + SBOM.
- Staging environment can run the full adversarial suite against realistic fixtures.

**Details:** See `weeks/E09-Staging-Release/` and `samples/docker/`

---

## Week E10 — Stabilization & Enterprise Candidate

**Goal:** Prove the platform under realistic load and document it.

### Deliverables
- Multi-project load scenario (Bar Association + residential + industrial recipes)
- Concurrent job stress test
- Final architecture documentation + ADRs
- Updated CONTRIBUTING and runbooks
- Tag `v1.0.0-enterprise-candidate`
- Professional-review package readiness (software side)

### Acceptance
- All prior acceptance criteria still hold.
- Performance remains within previously established envelopes (or documented deviations).
- A third-party engineer can understand the system from docs alone.
- Quality-gate for the platform itself is `REVIEW_REQUIRED` only for external professional architectural sign-off.

**Details:** See `weeks/E10-Stabilization/`

---

## Cross-Cutting Rules for Every Week

1. **No new domain CAD features** during the E-weeks unless required to keep existing tests green.
2. **Every PR** must keep the existing Python regression + adversarial suite green.
3. **Geometry determinism** is sacred — any change that affects findings must be explicitly versioned in the rule-pack or model schema.
4. **Documentation is part of the Definition of Done.**
5. Prefer **feature flags** for risky changes so local single-user mode remains simple.

---

## Resource Guidance (Solo or Small Team)

| Role              | Focus Weeks          |
|-------------------|----------------------|
| Platform / Backend| E02, E03, E04, E07   |
| Frontend          | E06, parts of E03    |
| DevOps / CI       | E01, E05, E09        |
| Security          | E08                  |
| Domain / QA       | Continuous + E10     |

If working solo, execute strictly in order E01 → E10 and keep each week to a thin vertical slice.

---

## Next Step

Open the corresponding `weeks/E0X-.../` folder and begin with its `tasks.md`.
