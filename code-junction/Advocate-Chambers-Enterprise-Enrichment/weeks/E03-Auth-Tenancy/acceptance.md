# Week E03 — Acceptance Criteria

## Must Pass

1. Unauthenticated calls to protected endpoints return 401.
2. A user cannot read or mutate projects outside their organization(s).
3. Role checks enforce the documented matrix for at least: view, edit, enqueue job, manage members.
4. Audit events are written for project create/update and job enqueue.
5. Local development still works with a documented bypass or seeded user.
6. Frontend can log in and attach credentials to API calls.
7. Existing domain tests and quality gates remain green.
