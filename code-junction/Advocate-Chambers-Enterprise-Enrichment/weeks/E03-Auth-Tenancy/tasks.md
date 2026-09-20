# Week E03 — Auth & Multi-tenancy

**Duration:** 5–7 days  
**Risk:** High  
**Depends on:** E02  
**Blocks:** Production use of mutating endpoints

---

## Objectives

1. Introduce identity and organization-scoped access control.
2. Protect all mutating and sensitive read endpoints.
3. Record audit events for security-relevant actions.
4. Preserve a simple local “dev mode” for single-developer work.

---

## Task List

### 1. Identity Provider Choice (0.5 day)

- [ ] Decide on provider:
  - **Recommended for speed:** Clerk or Auth.js
  - **Self-hosted:** Keycloak
  - **Minimal custom:** JWT issued by FastAPI (only for very early stages)
- [ ] Document the choice in an ADR.

### 2. Data Model Extensions (1 day)

- [ ] Flesh out `organizations`, `users`, `memberships`, `roles`.
- [ ] Add `project.organization_id` (or equivalent ownership).
- [ ] Migration.

### 3. Auth Middleware / Dependencies (1.5 days)

- [ ] FastAPI dependency that extracts and validates JWT.
- [ ] Current-user and current-organization context.
- [ ] Role checks: Owner, Editor, Viewer, Reviewer (minimum set).

### 4. Endpoint Protection (1 day)

- [ ] Classify endpoints:
  - Public: `/health`
  - Authenticated: almost everything else
  - Role-gated: project create/update, job enqueue, revision accept, archive
- [ ] Return 401 / 403 consistently.

### 5. Audit Logging (1 day)

- [ ] Write `audit_events` on:
  - login / token use (optional)
  - project create / update / soft-delete
  - revision create / accept
  - job enqueue
  - artifact download (optional)
- [ ] Include actor, action, resource, timestamp, request id.

### 6. Local Dev Bypass (0.5 day)

- [ ] Environment flag `AUTH_DISABLED=true` or seeded dev user that is automatically authenticated in local docker-compose.
- [ ] Clearly document that this must never be enabled in staging/production.

### 7. Frontend Integration (1 day)

- [ ] Login / logout flow in React.
- [ ] Attach Authorization header to API calls.
- [ ] Handle 401 by redirecting to login.

---

## Minimum Role Matrix

| Action                    | Owner | Editor | Viewer | Reviewer |
|---------------------------|-------|--------|--------|----------|
| View project              | ✓     | ✓      | ✓      | ✓        |
| Edit model / brief        | ✓     | ✓      |        |          |
| Enqueue generate job      | ✓     | ✓      |        |          |
| Accept revision           | ✓     | ✓      |        |          |
| Manage members            | ✓     |        |        |          |
| Mark professional review  | ✓     |        |        | ✓        |

---

## Out of Scope

- Fine-grained per-room permissions
- SSO enterprise federation (can come later)
- Full admin portal UI
