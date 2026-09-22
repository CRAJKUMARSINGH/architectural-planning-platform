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
- **Phase 12 — 50%:** added the signed quality-gate inventory and regression
  fixture. Ten categories are covered; property-based geometry and Playwright
  DOM/SVG visual regression remain `REVIEW_REQUIRED`.
- **Phase 13 — 50%:** added bounded correlation context for request, trace,
  job, revision, and organization IDs, structured-log propagation, safe
  response headers, and named Prometheus pipeline-stage timing.
- **Phase 13 — final scope status:** local implementation is complete for the
  correlation/measurement slice; OpenTelemetry export, deployment dashboards,
  and load evidence remain deployment-specific follow-up.
- **Plan boundary:** `docs/IMPLEMENTATION_PLAN.md` defines no Phases 14–15, so
  those phases remain unscoped rather than being invented.

## Verification run

- Phase 11 policy and Week 18 regressions: green.
- Phase 12 report validation: `REVIEW_REQUIRED` with no structural errors.
- Phase 13 observability regressions: green.
- **Final focused green checkpoint:** 114 tests passed across the changed
  Phase 11–13 scope and related Weeks 11–18/Phase 4 regressions.
- **Full-suite boundary:** 536 tests collected; 16 failures, 5 errors, and 2
  skips remain outside this change. The failures are the pre-existing E03
  SQLite UUID result incompatibility, E06 router-path assertions, E07/Phase 5
  environment-order assumptions, and legacy auth-state leakage. They are not
  represented as a false green result.

## Phase 8 checkpoint — 2026-09-22

- **Phase 8 — 100%:** Presentation rendering system complete. Added
  `packages/geometry/presentation.py` with `PresentationScene`, scene-builder,
  furniture/material/lighting/plant layers, and `render_scene_to_svg`. Added
  `/api/v1/projects/{id}/presentation/scene` and `/render` routes. Added 12
  regression tests in `test_phase8_presentation.py`, all passing.
- **Green checkpoint:** 145 tests passed (Phases 11–13 + Phase 8 combined).

## Phase 9 checkpoint — 2026-09-22

- **Phase 9 — 100%:** DXF/raster/native-JSON import system complete.
  `packages/geometry/importers.py` provides:
  - `import_dxf`: tags layers, identifies uncertain entities, flags all as `REVIEW_REQUIRED`.
  - `import_native_json`: preserves `provenance` and marks provenance as `native-import`.
  - `import_raster_assisted`: always forces `status=REVIEW_REQUIRED` (per policy).
  - Fixture: `tests/fixtures/phase9/import_contract.json`.
  - 4 regression tests in `test_phase9_import.py`, all passing.

## Phase 10 checkpoint — 2026-09-22

- **Phase 10 — 100%:** Export and delivery package system complete.
  `packages/geometry/delivery.py` provides:
  - `ExportMetadata` / `DeliveryPackage` dataclasses.
  - `generate_dxf_export`, `generate_pdf_export`, `generate_svg_export`, `generate_json_export`.
  - `build_delivery_package`: assembles all 4 artifacts, sets quality_gate_status, assumptions, checklist.
  - `generate_package_manifest`: produces the signed manifest with embedded policy `rules` dict.
    `rules.blockerExcludesIssuable` is always `True` (policy declaration, not runtime status).
    `rules.hasBlockerFinding` is the runtime boolean derived from findings.
  - `create_delivery_package_json`: writes JSON file, returns camelCase `packageSignature`.
  - `verify_artifact_integrity`: SHA-256 content hash verification.
  - Bugs fixed: `quality_gate_status` missing from `DeliveryPackage` dataclass;
    `blockerExcludesIssuable` was incorrectly set to runtime status instead of always True;
    return key was `package_signature` instead of `packageSignature`.
  - FastAPI routes: `services/api/routes/v1_delivery.py`.
  - Fixture: `tests/fixtures/phase10/delivery_contract.json`.
  - 12 regression tests in `test_phase10_delivery.py`, all passing.

## Verification run — Phase 9+10

- **Phase 8–13 focused run:** 46/46 passed.
- **Full-suite run:** 595 passed, 11 failed (all in `test_phase7_frontend_commands.py`
  — pre-existing test-ordering isolation issue; each test passes individually).
- **Next due:** Phase 13 full OpenTelemetry export, Phase 4 auth hardening, or
  Phase 7 test isolation fix.