# Week E01 — Acceptance Criteria

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
- Team agrees the repository is now “hygiene-ready” for E02.
