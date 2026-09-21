# ADR-004 — Canonical Contract Versioning and Measurement Policy

**Status:** Accepted  
**Date:** 2026-09-21  
**Deciders:** Platform + Domain leads

## Context

The platform has a canonical project schema and a growing set of commands,
findings, revisions, render manifests, and delivery artifacts. These contracts
will be used by the Python geometry authority, FastAPI, React, workers, and
external import/export adapters. Uncontrolled shape changes would make
revisions non-replayable and could silently change geometry or release status.

## Decision

1. Every cross-boundary object carries an explicit `schemaVersion`.
2. Existing `advocate-chambers.project.v2` remains compatible while the new
   command, finding, revision, render, and artifact contracts begin at `v1`.
3. A breaking change creates a new schema version and an explicit migration.
4. Additive optional fields are permitted within a version only when old
   consumers can safely ignore them.
5. Authoritative geometry is serialized deterministically before hashing.
6. Model hashes use lowercase SHA-256 hexadecimal.
7. Presentation manifests must declare `presentationOnly: true`.
8. A render, export, or report is never allowed to change canonical geometry.

## Measurement policy

- The current project schema's external unit contract remains inch-based until
  a versioned migration is approved.
- Unit conversion happens at input and display boundaries.
- Geometry comparisons use named tolerances rather than ad-hoc constants.
- Display rounding must never be reused as geometry precision.
- Every future unit conversion must include round-trip tests.

The first implementation should centralize the tolerance policy in Python and
make it available to validators, command execution, and export code.

## Consequences

**Positive**

- Commands can be replayed and audited.
- Reports and artifacts can be traced to one revision.
- Presentation quality can improve without weakening geometry authority.
- API and frontend contracts can evolve deliberately.

**Negative**

- Schema migrations require explicit work.
- Compatibility tests must be maintained.
- Deterministic serialization constrains implementation shortcuts.

## Enforcement

- Contract files live under `packages/schema/`.
- CI checks schema JSON parsing and required contract metadata.
- Any command that changes geometry must include a base revision.
- Any artifact without a model revision, generator version, and hash is invalid.
- A breaking contract change requires an ADR and migration fixture.