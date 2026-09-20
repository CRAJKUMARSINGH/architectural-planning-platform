# Changelog

All notable changes to **Advocate-Chambers** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — Enterprise Enrichment in Progress

Enterprise E01–E10 programme underway. See `docs/enterprise/ENTERPRISE_ROADMAP.md`.

### Added (2026-09-20) — E03–E10 Fixture & Regression Test Expansion

Comprehensive fixtures and expanded regression tests for all enterprise weeks.
All 258 enterprise regression tests pass; 34 skip pending SQLAlchemy install.

#### Fixture files
- `tests/fixtures/e03/` — roles_matrix.json, org_isolation_scenarios.json, dev_jwt_payload.json
- `tests/fixtures/e04/` — job_payloads.json (state machine transitions), artifact_samples.json
- `tests/fixtures/e05/` — quality_gate_passing.json, quality_gate_blocked.json, quality_gate_adversarial_regression.json
- `tests/fixtures/e06/` — openapi_required_paths.json
- `tests/fixtures/e07/` — structured_log_sample.json
- `tests/fixtures/e08/` — security_headers_required.json
- `tests/fixtures/e09/` — release_manifest_sample.json
- `tests/fixtures/e10/` — load_scenario.json

#### Expanded test files
- `tests/test_e03_auth_expanded.py` — role weight matrix alignment, cross-org isolation, JWT decode, audit immutability, request-ID propagation
- `tests/test_e04_jobs_expanded.py` — job state machine, SHA-256 deduplication, path-traversal containment, concurrent store writes
- `tests/test_e05_quality_gate_expanded.py` — fixture-driven gate enforcement, ERROR/BLOCKER regression, adversarial count regression, SBOM artefact checks
- `tests/test_e06_api.py` — versioned route structure, Pydantic constraints, auth wiring, OpenAPI schema, ADR-001 geometry boundary
- `tests/test_e07_observability_expanded.py` — full JSON log field contract, Grafana dashboard, health endpoint, correlation ID round-trip
- `tests/test_e08_security_expanded.py` — header completeness, rate-limit eviction, tamper detection, OWASP checklist, CORS, staging guards
- `tests/test_e09_staging_expanded.py` — docker compose service completeness, Dockerfile presence, release workflow, checklist disclaimer
- `tests/test_e10_stabilization.py` — concurrent job safety, load scenario fixture, ADR completeness, runbook coverage, enterprise candidate readiness

#### Infrastructure fixes (driven by new tests)
- `scripts/enterprise/check_quality_gate.py` — now fails on `ERROR` severity findings and missing `adversarialSuite` key
- `.github/workflows/ci.yml` — explicitly calls `check_quality_gate.py` in the quality gate step
- `docs/enterprise/checklists/release.md` — added "Never mark outputs as automatically issuable" disclaimer
- `Makefile` — added `docker-build`, `docker-up`, `docker-staging`, `docker-down` targets (E09)

---

## [1.0.0-enterprise-baseline] — 2026-09-20

### Summary
Baseline snapshot captured before the 10-week enterprise enrichment programme begins.
Domain enrichment through Week 28 is complete and frozen as the quality baseline.

### Domain Enrichment (Weeks 1–28 — complete)

- **Week 1–2** Parametric model schema v1, manifest validation, round-trip serialisation.
- **Week 3–4** Reachability graphs, semantic opening schedule.
- **Week 5–6** Stair coordination, program area analysis.
- **Week 7–8** NBC/RPwD rule-pack v1 (`india-preliminary-review`), drawing quality checks.
- **Week 9–10** Furniture / clearance presentation layer, candidate QA, release checklist.
- **Week 11–12** Capability matrix, brief compiler v1, changelog.
- **Week 13–14** Visual-tool import recognition (Planner 5D, Magicplan, ArchiStar), synchronised views.
- **Week 15–16** Parametric asset library, 4-line plan/section exchange, AI-tool inputs (read-only).
- **Week 17–18** Site feasibility scoring, delivery package generation.
- **Week 19–20** Archive integrity, revision operations, LFS strategy.
- **Week 21** Quality gate v1 — `PASS` / `REVIEW_REQUIRED` / `BLOCKED` / `INCOMPLETE`.
- **Week 22** Adversarial fixture foundation — 30 known critical defects.
- **Week 23** Adversarial expansion — all 30 fixtures confirmed detected (100% recall).
- **Week 24** Professional review protocol — two-reviewer workflow, anonymised results.
- **Week 25** Performance benchmark suite — latency envelopes established.
- **Week 26** Reproducibility package — SHA-256 signed, deterministic across environments.
- **Week 27** Integrated release v1 — quality-gate report + SBOM + known-limitations register.
- **Week 28** Organisation model — multi-project recipe scaffold.

### Baseline Quality State (2026-09-20)

| Gate | Status |
|------|--------|
| Unit tests (37+) | PASS |
| Adversarial suite | 30/30 detected |
| Quality gate | REVIEW_REQUIRED (professional sign-off pending — by design) |
| Performance | Within established envelopes |
| Reproducibility | Confirmed — SHA-256 signed |

Frozen reports: `baselines/2026-09-20/`

---

## Enterprise Enrichment Weeks (Planned)

| Week | Focus | Target Date |
|------|-------|-------------|
| E01 | Foundation & Hygiene | 2026-09-20 |
| E02 | Persistence Layer | TBD |
| E03 | Auth & Multi-tenancy | TBD |
| E04 | Async Jobs & Storage | TBD |
| E05 | CI/CD & Automated Gates | TBD |
| E06 | API & Frontend Hardening | TBD |
| E07 | Observability | TBD |
| E08 | Security Hardening | TBD |
| E09 | Staging & Release Process | TBD |
| E10 | Stabilisation & Enterprise Candidate | TBD |

---

<!-- Links -->
[Unreleased]: https://github.com/CRAJKUMARSINGH/Advocate-Chambers/compare/v1.0.0-enterprise-baseline...HEAD
[1.0.0-enterprise-baseline]: https://github.com/CRAJKUMARSINGH/Advocate-Chambers/releases/tag/v1.0.0-enterprise-baseline
