# Week E05 — CI/CD & Automated Quality Gates

**Duration:** 3–5 days  
**Risk:** Low–Medium  
**Depends on:** E01  
**Can run in parallel with E02–E04 after E01**

---

## Objectives

1. Make the existing rich test and quality-gate machinery enforce itself automatically.
2. Prevent regressions of adversarial detection and performance envelopes from reaching `main`.
3. Produce SBOMs and quality-gate summaries on release tags.

---

## Task List

### 1. Workflow Skeleton (1 day)

- [ ] Create `.github/workflows/ci.yml`.
- [ ] Jobs:
  1. lint (Python + Node)
  2. typecheck
  3. unit tests
  4. domain validation (selected `npm run validate:*`)
  5. adversarial suite
  6. performance smoke
  7. quality-gate check
- [ ] Cache npm and pip dependencies.

### 2. Quality-Gate Enforcement (1 day)

- [ ] Script that runs `scripts/quality_gate.py` (or equivalent) and fails the job if status is `BLOCKED` or critical false-negatives appear.
- [ ] Optional: compare against baseline and fail on unexpected new REVIEW_REQUIRED reasons that indicate software regression.

### 3. Supply Chain (1 day)

- [ ] Enable Dependabot or equivalent.
- [ ] Add secret scanning.
- [ ] Generate SBOM (Syft or similar) on tags.
- [ ] Upload SBOM as release asset.

### 4. Branch Protection (0.5 day)

- [ ] Require status checks for merge to `main`.
- [ ] Require at least one review (even if single-owner initially).

### 5. Documentation (0.5 day)

- [ ] Document how CI maps to the weekly enrichment commands.
- [ ] Document how to interpret a failed quality-gate job.

---

## Sample Workflow

See `samples/github-actions/ci.yml` for a concrete starting point.
