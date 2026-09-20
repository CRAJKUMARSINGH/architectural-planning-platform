# ADR-003 — Organization-Centric Tenancy

**Status:** Accepted  
**Date:** 2026-09-20

## Context

The platform will be used by architectural firms, bar associations, and individual practitioners. Data isolation and role-based access are required before any multi-user or commercial deployment.

## Decision

- Primary isolation boundary is the **Organization**.
- Users belong to one or more organizations via memberships with roles.
- Projects belong to exactly one organization.
- Roles (minimum): Owner, Editor, Viewer, Reviewer.
- Authorization is enforced at the repository/query layer, not only in the HTTP layer.
- A local development bypass may exist but must be impossible to enable in staging/production configurations.

## Consequences

- Simple mental model for early customers
- Clear audit trail (actor + organization + resource)
- Future fine-grained permissions can be layered on top without rewriting the isolation boundary

## Non-Goals (for now)

- Per-room or per-sheet ACLs
- Cross-organization sharing links (can be added later with explicit design)
