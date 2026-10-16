# Enterprise Enrichment — Due Tasks

<!-- Last reviewed: 2026-10-16 -->
<!-- E01–E08 complete. E09–E10 are the remaining open weeks. -->

## ✅ COMPLETE — E01 through E08

All tasks through E08 (Security Hardening) are complete and merged to `main`.
See `CHANGELOG.md` and `docs/enterprise/checklists/security.md` for details.

Key deliverables landed:
- **E01** — `pyproject.toml`, Ruff, mypy, EditorConfig, `.nvmrc`, `CONTRIBUTING.md`, baseline snapshot at `baselines/2026-09-20/`.
- **E02** — PostgreSQL schema + Alembic migrations, SQLAlchemy ORM, Docker Compose Postgres service.
- **E03** — JWT/OIDC validation, Organization/Membership/Role model, `AUTH_DISABLED` guard, auth fixtures.
- **E04** — Redis + RQ worker, content-addressed artifact storage (SHA-256), job lifecycle.
- **E05** — GitHub Actions CI: lint → typecheck → unit → adversarial → quality-gate → performance smoke; merge gate enforced.
- **E06** — Versioned API (`/api/v1/`), OpenAPI schema, Pydantic ↔ Zod alignment, frontend error states.
- **E07** — Structured JSON logs, Prometheus metrics, readiness/liveness, Grafana dashboard, OTEL integration.
- **E08** — JWT error detail sanitisation, CORS env-var, `/metrics` protection, `:?` mandatory secrets in OIDC compose, `pip-audit` + `npm audit` 0 findings.

---

## E09 — Staging & Release Process

- [ ] Docker images for API, worker, web tested with `docker compose up --build` against staging config.
- [ ] Semantic versioning automated — release tag triggers `release.yml` → quality-gate report + SBOM attached.
- [ ] Request body size limits + rate limiting (IP + user) wired into FastAPI middleware.
- [ ] Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`) added to FastAPI middleware.
- [ ] SBOM auto-generated and attached to every release tag in CI.
- [ ] Staging smoke test documented and automated.
- [ ] Blue/green or canary deployment skeleton for Kubernetes / Cloud Run.

## E10 — Stabilisation & Enterprise Candidate

- [ ] Multi-project load scenario (Bar Association + residential + industrial recipes) run and profiled.
- [ ] Concurrent job stress test passing within established latency envelopes.
- [ ] Soft-delete and retention policy defined and implemented.
- [ ] Final ADRs updated; CONTRIBUTING and runbooks reviewed for accuracy.
- [ ] Tag `v1.0.0-enterprise-candidate` with quality-gate report + SBOM + known-limitations register.
- [ ] Professional-review package readiness confirmed on the software side.

---

## Supplemental Notes

- Archive/LFS policy, project registry, transformation guide, Week 24 blinded pack, and `REVIEW_REQUIRED` safeguards are already represented in the codebase. No duplicate tasks above.
- Phases 16 (AI Version Scoring) and 17 (Proactive Suggestions) are complete. Phase 18 (Client Presentation & Export Workflow) is the next domain phase.
