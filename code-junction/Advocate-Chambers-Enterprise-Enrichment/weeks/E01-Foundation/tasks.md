# Week E01 — Foundation & Hygiene

**Duration:** 3–5 days  
**Risk:** Low  
**Depends on:** Nothing  
**Blocks:** Everything else

---

## Objectives

1. Make the repository and local developer experience predictable and professional.
2. Freeze a known-good baseline of domain quality so later enterprise work cannot silently regress it.
3. Introduce shared tooling without changing runtime behaviour of the CAD pipeline.

---

## Task List

### 1. Python Tooling (1 day)

- [ ] Add root `pyproject.toml` with:
  - project metadata
  - optional dependency groups (`dev`, `api`, `worker`)
  - Ruff configuration (lint + format)
  - mypy configuration (strict where practical)
- [ ] Add `ruff.toml` or keep config inside `pyproject.toml`.
- [ ] Ensure all existing scripts under `scripts/` and `bar-association-hall/` can be type-checked at least in non-strict mode.
- [ ] Add `make lint-py` / `npm run lint:py` that runs Ruff + mypy.

### 2. Node / TypeScript Tooling (0.5 day)

- [ ] Confirm `apps/web` uses TypeScript strict mode.
- [ ] Add shared ESLint + Prettier config at repo root (or via workspace package).
- [ ] Ensure `npm run typecheck:web` is clean.
- [ ] Add `npm run lint:web`.

### 3. Editor & Runtime Version Pinning (0.5 day)

- [ ] Add `.editorconfig`
- [ ] Add `.nvmrc` (Node 20 or 22 LTS)
- [ ] Add `.python-version` (3.11 or 3.12)
- [ ] Document required versions in README and CONTRIBUTING.

### 4. Documentation Skeleton (1 day)

- [ ] Create `docs/` directory.
- [ ] Move or copy long-form weekly reports that clutter root into `docs/history/` or keep references.
- [ ] Write `CONTRIBUTING.md`:
  - how to run tests
  - how to run quality gate
  - branch naming
  - PR expectations
- [ ] Write `SECURITY.md` (even if minimal).
- [ ] Add `CODEOWNERS` (can be single owner initially).

### 5. Baseline Capture (0.5 day)

- [ ] Create `baselines/2026-09-20/` (or current date).
- [ ] Copy current:
  - `bar-association-hall/standard/quality-gate-report.json`
  - key adversarial reports
  - performance report
- [ ] Add a small script or make target that re-runs the full suite and diffs against baseline (warn-only for now).

### 6. Conventional Commits & Simple Changelog (0.5 day)

- [ ] Add commit message convention (Conventional Commits).
- [ ] Optional: simple `commitlint` or a pre-commit hook.
- [ ] Add a `CHANGELOG.md` starting from current version.

### 7. One-Command Local Verification (0.5 day)

- [ ] Add a top-level `Makefile` or `scripts/verify-baseline.sh` that runs:
  - Python unit tests
  - key `npm run validate:*` / `test:*` targets
  - quality-gate check
- [ ] Document the command in CONTRIBUTING and README.

---

## Out of Scope for E01

- Database
- Authentication
- Docker (beyond what already exists)
- New CAD features
- Changing any geometry or rule-pack behaviour

---

## Notes for Implementer

- Prefer non-destructive changes. Do not move large binary assets or rewrite history.
- Keep the existing `npm run enrich:*` / `validate:*` / `test:*` scripts working exactly as they do today.
- If Ruff or mypy surface many historical issues, start with a gradual adoption (per-file ignores or lower severity) rather than a massive rewrite.
