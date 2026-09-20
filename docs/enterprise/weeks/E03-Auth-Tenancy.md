# E03-Auth-Tenancy

# Week E03 â€” Auth & Multi-tenancy

**Duration:** 5â€“7 days  
**Risk:** High  
**Depends on:** E02  
**Blocks:** Production use of mutating endpoints

---

## Objectives

1. Introduce identity and organization-scoped access control.
2. Protect all mutating and sensitive read endpoints.
3. Record audit events for security-relevant actions.
4. Preserve a simple local â€œdev modeâ€ for single-developer work.

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
| View project              | âœ“     | âœ“      | âœ“      | âœ“        |
| Edit model / brief        | âœ“     | âœ“      |        |          |
| Enqueue generate job      | âœ“     | âœ“      |        |          |
| Accept revision           | âœ“     | âœ“      |        |          |
| Manage members            | âœ“     |        |        |          |
| Mark professional review  | âœ“     |        |        | âœ“        |

---

## Out of Scope

- Fine-grained per-room permissions
- SSO enterprise federation (can come later)
- Full admin portal UI


---

# Week E03 â€” Acceptance Criteria

## Must Pass

1. Unauthenticated calls to protected endpoints return 401.
2. A user cannot read or mutate projects outside their organization(s).
3. Role checks enforce the documented matrix for at least: view, edit, enqueue job, manage members.
4. Audit events are written for project create/update and job enqueue.
5. Local development still works with a documented bypass or seeded user.
6. Frontend can log in and attach credentials to API calls.
7. Existing domain tests and quality gates remain green.


---


