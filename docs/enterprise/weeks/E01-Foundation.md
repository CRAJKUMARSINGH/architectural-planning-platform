# E01-Foundation

# Week E01 â€” Foundation & Hygiene

**Duration:** 3â€“5 days  
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


---

# Week E01 â€” Acceptance Criteria

## Must Pass

1. **Tooling**
   - `ruff check` and `ruff format --check` succeed on the agreed Python scope.
   - `mypy` runs without new errors on the agreed scope (or documented exceptions).
   - `npm run typecheck:web` succeeds.
   - `npm run lint:web` (or equivalent) succeeds.

2. **Baseline Integrity**
   - Full existing Python unittest discovery (`tests/`) passes.
   - Quality-gate report can still be generated and is not worse than the frozen baseline (no new BLOCKED or critical false-negatives).
   - Adversarial suite (Week 22/23 style) still reports 30/30 known defects detected.

3. **Developer Experience**
   - A clean clone + documented install steps allows a new developer to run the baseline verification command successfully.
   - Node and Python versions are pinned and documented.

4. **Documentation**
   - `CONTRIBUTING.md` exists and is accurate.
   - `SECURITY.md` exists (even if short).
   - `CODEOWNERS` exists.

5. **No Behavioural Regression**
   - Existing `npm run enrich:*` and `validate:*` commands produce the same logical outcomes as before E01.
   - No change to canonical geometry or rule-pack findings.

## Nice to Have

- Pre-commit hooks installed via a single command.
- Simple changelog entry for E01 itself.

## Exit Gate

- PR(s) for E01 merged to `main`.
- Baseline folder committed.
- Team agrees the repository is now â€œhygiene-readyâ€ for E02.


---

# Week E01 â€” Implementation Notes

## Suggested Makefile Targets

```makefile
.PHONY: lint-py lint-web typecheck test-baseline verify

lint-py:
	ruff check scripts bar-association-hall services packages
	ruff format --check scripts bar-association-hall services packages
	mypy scripts services --ignore-missing-imports

lint-web:
	npm run lint:web

typecheck:
	npm run typecheck:web

test-baseline:
	python -m unittest discover -s tests -p 'test_*.py'
	npm run validate:week21 || true
	# add other critical validate targets as needed

verify: lint-py typecheck test-baseline
	@echo "Baseline verification complete"
```

## Baseline Directory Layout

```
baselines/
  2026-09-20/
    quality-gate-report.json
    week23-adversarial-expansion-report.json
    week25-performance-report.json
    README.md          # how the baseline was captured
```

## Common Pitfalls

- Running Ruff across generated reports or large CAD output directories â†’ exclude them.
- mypy complaining about dynamic imports in the weekly scripts â†’ use `type: ignore` sparingly and document.
- Changing `package-lock.json` or Python lock files accidentally â†’ review diffs carefully.

## Migration Tip

If the root already has many weekly scripts, do **not** try to reorganize them in E01. Only add tooling around them. Structural moves belong to later weeks or a dedicated â€œrepo organizationâ€ PR after E02.


