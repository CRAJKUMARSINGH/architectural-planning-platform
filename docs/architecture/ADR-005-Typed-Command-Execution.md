# ADR-005 — Typed Commands Are the Only Geometry Mutation Boundary

**Status:** Accepted
**Date:** 2026-09-21

## Decision

Authoritative edits to the `advocate-chambers.project.v2` model enter through
the Python command runner.  A command is validated, checked against the
current base revision, applied to a copy, quick-validated, deterministically
serialized, and then committed as a new immutable revision.

The phase-two runner supports the v2 structures that already have a canonical
schema: levels, spaces, openings, windows, stairs, site orientation, and
program requirements.  Wall splitting and furniture operations return a
structured blocker because project.v2 does not yet define authoritative wall
or furniture collections.  They must not silently mutate a presentation layer.

## Consequences

- Replaying an accepted idempotency key returns the original result.
- Reusing a key with different request parameters is rejected.
- A stale base revision returns `REVISION_CONFLICT`; geometry is never merged
  implicitly.
- Revision hashes are derived from canonical JSON with sorted keys and stable
  numeric normalization.
- Persistence, authorization, and durable job execution remain follow-up
  work from the implementation plan.