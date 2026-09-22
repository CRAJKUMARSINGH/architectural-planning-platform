# ADR-003 — Organization-Centric Tenancy

**Status:** Accepted
**Date:** 2026-09-20
**Deciders:** Platform + Domain leads

## Context

The platform will be used by architectural firms, bar associations, and individual
practitioners. Data isolation and role-based access are required before any multi-user
or commercial deployment.

## Decision

- Primary isolation boundary is the **Organization**.
- Users belong to one or more organizations via memberships with roles.
- Projects belong to exactly one organization.
- Roles (minimum): Owner, Editor, Viewer, Reviewer.
- Token role and organization claims identify a request but do not grant access;
  the active database membership is authoritative for effective role.
- Disabled or soft-deleted users cannot access project-scoped resources.
- Production authentication validates OIDC issuer, audience, expiry, clock skew,
  and rotating JWKS signatures. A development JWT secret is never valid in
  staging or production.
- Authorization is enforced at the repository/query layer, not only in the HTTP layer.
- A local development bypass (`AUTH_DISABLED=true`) may exist but must be impossible to
  enable in staging/production configurations.

## Consequences

- Simple mental model for early customers
- Clear audit trail (actor + organization + resource)
- Future fine-grained permissions can be layered on top without rewriting the isolation
  boundary

## Non-Goals (for now)

- Per-room or per-sheet ACLs
- Cross-organization sharing links (can be added later with explicit design)

## Compliance / Enforcement

- Repository/query methods must filter by `organization_id` before returning any project
  or revision data.
- Integration tests must include a cross-tenant isolation test that confirms User A cannot
  read User B's project.
- Project-scoped FastAPI dependencies must verify active membership before applying
  viewer/editor/owner permissions.
- `AUTH_DISABLED` must be rejected by the API startup check when `ENV=staging` or
  `ENV=production`.
