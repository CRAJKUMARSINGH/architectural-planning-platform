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