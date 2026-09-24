# Enterprise Enrichment — Due Tasks After Current Baseline

This file is intentionally limited to work that was not present in the
current `main` checkout when the supplemental archive and review documents
were reconciled on 2026-09-20.

## E01 — Foundation & Hygiene

- [ ] Install and enforce the shared Ruff/mypy and web typecheck entry points
  in clean-clone CI; the repository now exposes the commands, but the
  developer extras are not vendored.
- [ ] Add a real web lint formatter configuration when the frontend moves
  beyond the current TypeScript-only lint equivalent.
- [ ] Capture a clean-clone run of `make verify` and record it beside the
  frozen baseline.

## E02 — Persistence

- [ ] Add the PostgreSQL-backed repository implementation and an automated
  migration runner. The current slice provides the durable SQLite adapter,
  PostgreSQL schema/migration contract, seed path, and regression coverage.
- [ ] Add a database-backed API integration test against PostgreSQL in CI.
- [ ] Add audit-event writes for every project, revision, job, and artifact
  mutation.

## E03 — Identity & Tenancy

- [ ] Add OIDC/JWT verification, organizations, memberships, role checks, and
  tenant-scoped repository queries.
- [ ] Add authorization fixtures covering owner/editor/viewer/reviewer access
  and cross-organization denial.

## E04 — Async Jobs & Storage

- [ ] Move generation and validation execution to a Redis-backed worker.
- [ ] Replace metadata-only artifact completion with real content-addressed
  DXF/PDF/report storage and checksum verification.
- [ ] Add retry, cancellation, dead-letter, and worker-heartbeat fixtures.

## E05 — CI/CD & Automated Quality Gates

- [ ] Add pull-request workflow enforcement for lint, typecheck, unit,
  adversarial, schema, DXF reopen, PDF, and manifest checks.
- [ ] Add coverage and artifact retention policy to CI.

## E06 — API & Frontend Hardening

- [ ] Version the API, publish OpenAPI request/response contracts, and add
  schema validation at the boundary.
- [ ] Add frontend project/revision loading, error states, and persisted job
  polling against the durable API.

## E07 — Observability

- [ ] Add structured request/job logs, metrics, tracing correlation, and
  readiness/liveness endpoints.
- [ ] Add dashboards and alerts for queue latency, worker failures, and
  artifact verification failures.

## E08 — Security

- [ ] Add dependency/SBOM scanning, secret scanning, security headers, rate
  limits, upload limits, and a threat-model regression suite.
- [ ] Run a tenant-isolation and artifact path-traversal security test suite.

## E09 — Staging & Release

- [ ] Add API, worker, and web images plus the complete Postgres/Redis/object
  storage staging stack.
- [ ] Automate semantic releases with quality-gate, SBOM, adversarial,
  performance, and known-limitations artifacts.

## E10 — Stabilization

- [ ] Add concurrent multi-project load and failure-injection tests.
- [ ] Freeze runbooks, architecture decisions, release candidate evidence, and
  a formal enterprise-candidate tag.

## Supplemental-document reconciliation

The archive/LFS policy, project registry/inventory, transformation guide,
Week 24 blinded pack, review form, and `REVIEW_REQUIRED` safeguards are already
represented in the checkout. No duplicate task is listed here for those
features; the remaining items above are the unimplemented platform work that
they constrain.
