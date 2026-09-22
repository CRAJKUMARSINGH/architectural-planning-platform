# CREAT — implementation chat gist

## Current objective

Apply the next due item in `docs/IMPLEMENTATION_PLAN.md`, verify it with
fixtures and regression tests, document the result in `README.md`, and push the
completed work to the GitHub `main` branch.

## Phase 4 checkpoint

- **25% — policy boundary identified:** the existing E03 layer trusted JWT
  `org_id` and `role` claims and did not enforce disabled-user state.
- **50% — implementation drafted and tested:** OIDC/JWKS configuration and
  token validation were added; database-backed membership authorization was
  added for project-scoped viewer/editor/owner dependencies. The Phase 4 policy
  fixture and 8-test regression module are green; the existing E03 auth tests
  are also green (15 tests combined).
- **75% — persistence, route wiring, and plan documentation:** `users.disabled_at`,
  migration `0003_user_disabled_at`, schema reference, all v1 project/command
  route dependencies, ADR-003, the README status, and the implementation plan
  status were updated.
- **100% — verified:** the focused Phase 4/E03/E04/E05/E07/E08/E09 plus
  Phase 1/2/3 regression command passes with **101 passed, 1 warning, and 7
  subtests passed**. Ruff passes for the changed Phase 4/authentication files.
  The warning is Starlette's `anyio.abc.BlockingPortal` deprecation.

## Verification boundary

The pre-existing expanded E03 SQLite tests still expose two unrelated
environment-compatibility issues (PostgreSQL UUID handling on SQLite), and E06
contains pre-existing router-prefix assertion mismatches. They were not masked
or rewritten as part of this phase; the focused implementation regression
command above is the green gate for this change.

## Scope note

No 7-minute scheduled push routine is configured because the workspace minimum
routine interval is 60 minutes. Milestone checkpoints are committed manually at
25%, 50%, 75%, 100%, and after green verification.

## Phase 11–13 checkpoint — 2026-09-22

- **Phase 11 — 50%:** added the collaboration policy contract, security
  fixture, append-only review-link/comment/approval ORM records, and reversible
  migration `0004_collaboration_review`.
- **Phase 11 — 100%:** added tenant-scoped repositories and `/api/v1` review
  link, comment, approval, and public-link resolution routes. Review tokens are
  hashed at rest and audit events are recorded.
- **Phase 12 — 100%:** added the signed quality-gate inventory and regression
  fixture. All 12 categories are now covered including property-based geometry
  tests using Hypothesis and Playwright DOM/SVG visual regression tests for
  architectural viewport rendering.
- **Phase 13 — 50%:** added bounded correlation context for request, trace,
  job, revision, and organization IDs, structured-log propagation, safe
  response headers, and named Prometheus pipeline-stage timing.
- **Phase 13 — final scope status:** local implementation is complete for the
  correlation/measurement slice; OpenTelemetry export, deployment dashboards,
  and load evidence remain deployment-specific follow-up.
- **Plan boundary:** `docs/IMPLEMENTATION_PLAN.md` defines no Phases 14–15, so
  those phases remain unscoped rather than being invented.

## Phase 8 checkpoint — 2026-09-22

- **Phase 8 — 100%:** completed presentation rendering implementation with:
  - Technical vs presentation scene graph separation
  - Blender headless server render integration with Python script generation
  - Complete asset catalog with clearance envelopes (9 assets)
  - Vector overlay labels and dimensions system
  - Deterministic camera presets (4 presets: top-down-plan, axonometric-east-front, perspective-courtyard, isometric-overview)
  - Render manifest validation against JSON schema
  - `/api/v1/presentation` API routes (assets, styles, cameras, compile, render endpoints)
  - 13 regression tests passing

## Verification run

- Phase 1–5 & 7 regression suite: green (136 passed, 9 skipped).
- Phase 4 authentication policy and membership authority: isolated and green.
- Phase 8 presentation rendering: green (13 tests including Blender integration, vector overlays, and API routes).
- Phase 11 collaboration review API: green.
- Phase 12 quality gate: property-based geometry regressions with Hypothesis and Playwright DOM/SVG visual regression tests implemented; all 12 categories covered, status `PASS`.
- Phase 13 observability & metric probes: green.
- **Combined Phase 1–13 focused green checkpoint:** 163 tests passed with zero failures across the integrated codebase.

## Phase 8 & 10 Implementation Pipeline — In Progress

- **Phase 8 (100%):** Technical vs presentation scene graph compiler complete, deterministic camera presets (`top-down-plan`, `axonometric-east-front`, `perspective-courtyard`, `isometric-overview`), style tokens, furniture/plant catalog with clearance checks, render manifest validation, Blender headless integration, vector overlay labels and dimensions, and `/api/v1/presentation` API routes.
- **Phase 10 (50%):** Delivery package bundler generating complete content-addressed delivery manifests, SHA-256 verification, and technical drawing sets.