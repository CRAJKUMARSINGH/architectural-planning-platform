# Week E10 — Stabilisation & Enterprise Candidate — 📋 PLANNED

**Status:** Planned  
**Depends on:** E09 complete

## Goal

Prove the platform under realistic load, finalise all documentation, and tag
`v1.0.0-enterprise-candidate`. A third-party engineer should be able to understand
the system from docs alone after this week.

## Tasks

### 1. Multi-project load scenario
- [ ] Add load scenario fixture: `tests/fixtures/e10/load_scenario.json`
  - 3 projects: Bar Association Hall + residential + small commercial
  - 10 concurrent users, mix of read/write, 5 min sustained
- [ ] Run `scripts/load_test.py` against staging stack
- [ ] Assert p95 command preview ≤ 3 s; p95 full validation ≤ 10 s
- [ ] Document any deviations from Week 25 performance envelopes

### 2. Concurrent job stress test
- [ ] Simultaneous 5 generation jobs for same project → assert no revision conflict corruption
- [ ] Worker crash mid-job → assert last valid revision intact, job status = `FAILED`
- [ ] Redis unavailability → assert graceful degradation (503 from API, no data loss)

### 3. Soft-delete and data retention
- [ ] Implement `deleted_at` enforcement in project/org/user queries (currently defined, not enforced everywhere)
- [ ] Add retention policy: jobs older than 90 days soft-purged; artifacts older than 365 days flagged
- [ ] `GET /api/v1/projects/` must never return soft-deleted projects

### 4. Final documentation pass
- [ ] Review all 6 ADRs for accuracy against current codebase — update any that have drifted
- [ ] Add ADR-007 covering AI advisory boundary (Phases 14–17)
- [ ] Update `CONTRIBUTING.md` with Phase 18 scope and E09–E10 context
- [ ] Verify all runbooks are accurate (`docs/runbooks/`)
- [ ] Confirm `docs/enterprise/README.md` weeks/ directory is complete

### 5. Enterprise candidate tag
- [ ] All prior acceptance criteria from E01–E09 still hold
- [ ] Performance within established envelopes (or deviations documented)
- [ ] Quality-gate: `REVIEW_REQUIRED` only for legitimate professional architectural sign-off
- [ ] Known-limitations register: `docs/enterprise/known-limitations.md`
- [ ] Tag `v1.0.0-enterprise-candidate` with release assets:
  - quality-gate-report.json
  - adversarial-summary.json
  - performance-report.json
  - SBOM (CycloneDX JSON)
  - known-limitations.md

### 6. Phase 18 kickoff
- [ ] Create spec for Phase 18 — Client Presentation & Export Workflow
- [ ] Define acceptance criteria: PDF export from canvas, client-facing share link, version diff view

## Acceptance Criteria

| Criterion | Done? |
|-----------|-------|
| All prior E01–E09 acceptance criteria still hold | ⬜ |
| Performance within envelopes (or deviations documented) | ⬜ |
| Third-party engineer can understand system from docs alone | ⬜ |
| Quality-gate: `REVIEW_REQUIRED` only for legitimate professional items | ⬜ |
| `v1.0.0-enterprise-candidate` tag pushed with full release assets | ⬜ |
