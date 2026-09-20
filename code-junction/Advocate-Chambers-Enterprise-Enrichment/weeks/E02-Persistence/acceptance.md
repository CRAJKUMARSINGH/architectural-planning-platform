# Week E02 — Acceptance Criteria

## Must Pass

1. **Schema & Migrations**
   - Alembic (or equivalent) can upgrade and downgrade cleanly.
   - All tables listed in the data model exist with appropriate indexes and foreign keys.

2. **Repository Behaviour**
   - Creating a project and a revision persists and can be re-loaded after process restart.
   - Job records transition through states (`queued` → `running` → `succeeded` / `failed`).
   - Artifact metadata (id, job_id, kind, sha256, storage_key) is durable.

3. **API Compatibility**
   - Existing FastAPI endpoints continue to respond correctly.
   - `/health` reports database connectivity.
   - In-memory dicts are no longer the primary store for jobs/artifacts.

4. **Geometry Authority Unchanged**
   - Validation still uses the existing Python `drawing_model` / weekly scripts.
   - No geometry coordinates are required to live only in the database.

5. **Local Developer Experience**
   - `docker compose up postgres` (or full stack) works.
   - Seed script creates the Banswara project successfully.

## Exit Gate

- PR merged.
- Documentation updated with connection and migration instructions.
- Baseline quality-gate and adversarial suites still green.
