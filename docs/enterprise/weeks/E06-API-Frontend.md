# E06-API-Frontend

# Week E06 â€” API & Frontend Hardening

**Duration:** 5â€“7 days  
**Risk:** Medium  
**Depends on:** E02â€“E04

---

## Objectives

1. Stabilize the public (and internal) API contract.
2. Align frontend types with backend schemas.
3. Improve resilience and clarity of the React editor.

---

## Task List

### 1. API Versioning & OpenAPI (1.5 days)

- [ ] Move routes under `/v1/`.
- [ ] Complete OpenAPI metadata, examples, and error schemas.
- [ ] Publish OpenAPI JSON as a build artifact.

### 2. Shared Schema Package (1.5 days)

- [ ] Create `packages/schema` (or expand existing) that can generate or share types between Python and TypeScript.
- [ ] Align critical request/response models (Project, Revision, Job, Validate, Brief, etc.).
- [ ] Use Zod on the frontend for runtime validation of API responses where valuable.

### 3. Error Contract (0.5 day)

- [ ] Standard error envelope: `code`, `message`, `details`, `requestId`.
- [ ] Map domain validation errors cleanly (do not leak stack traces).

### 4. Frontend Hardening (2 days)

- [ ] Global error boundary.
- [ ] Consistent loading and empty states.
- [ ] Environment-based API base URL.
- [ ] Respect capability matrix (hide or disable provisional features).
- [ ] Never treat furniture/presentation layers as authoritative geometry.

### 5. Capability & Health Surface (0.5 day)

- [ ] Ensure `/v1/capabilities` and `/health` (or `/v1/health`) are accurate.
- [ ] Frontend reads capabilities rather than hard-coding feature flags where possible.

---

## Design Rule

The React application is a **client of the Python geometry authority**.  
It may preview, command, and display; it must not become the source of truth for walls, openings, stairs, or routes.


---


