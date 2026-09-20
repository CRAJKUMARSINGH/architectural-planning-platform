# ADR-002 — Conservative Quality Gates

**Status:** Accepted  
**Date:** 2026-09-20

## Context

The domain already implements a sophisticated quality-gate system with states:

- `PASS`
- `REVIEW_REQUIRED`
- `BLOCKED`
- `INCOMPLETE`

Missing evidence is deliberately **not** treated as a pass. Adversarial fixtures exist to catch dangerous false negatives.

## Decision

1. Software quality gates may only declare `PASS` when all required evidence is present and no critical defects are detected.
2. Absence of professional review evidence → `REVIEW_REQUIRED` or `INCOMPLETE`.
3. Known critical defects that are not detected → `BLOCKED` (or equivalent hard failure).
4. The platform itself, after the enterprise program, should reach a state where remaining `REVIEW_REQUIRED` items are only those that correctly require human professionals (architect, structural, fire, accessibility, authority).
5. CI must enforce the gate; a PR that introduces a new critical false-negative cannot merge.

## Consequences

- Honest communication with users and regulators
- Slightly slower “green” path (by design)
- Strong alignment with the existing Week 21–27 validation philosophy

## Related

- Existing `scripts/quality_gate.py`
- Week 22–26 adversarial, performance, and reproducibility work
- Professional-review checklist in this package
