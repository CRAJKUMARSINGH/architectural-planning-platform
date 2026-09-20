# E02-Persistence

# Week E02 â€” Persistence Layer

**Duration:** 4â€“6 days  
**Risk:** Medium  
**Depends on:** E01  
**Blocks:** E03, E04, E06

---

## Objectives

1. Introduce durable storage for projects, revisions, jobs, and artifacts.
2. Keep the existing file-based canonical geometry model as the source of truth.
3. Make FastAPI use repositories instead of in-memory dicts.

---

## Task List

### 1. Database Choice & Local Dev (0.5 day)

- [ ] Choose Postgres 15/16.
- [ ] Add Postgres service to a new or existing `docker-compose.yml`.
- [ ] Document connection string via environment variables.

### 2. Schema Design (1 day)

- [ ] Design tables (see `samples/db/schema.sql` and `architecture/data-model.md`):
  - `organizations` (stub for E03)
  - `users` (stub)
  - `projects`
  - `revisions`
  - `jobs`
  - `artifacts`
  - `audit_events`
- [ ] Decide soft-delete strategy (`deleted_at`).
- [ ] Decide how geometry blobs are referenced (path or content hash).

### 3. ORM / Models (1 day)

- [ ] Introduce SQLAlchemy 2.0 or SQLModel.
- [ ] Create model classes matching the schema.
- [ ] Add Alembic and initial migration.

### 4. Repository Layer (1â€“1.5 days)

- [ ] Define repository interfaces (or simple classes) for:
  - ProjectRepository
  - RevisionRepository
  - JobRepository
  - ArtifactRepository
- [ ] Implement Postgres versions.
- [ ] Keep a thin in-memory implementation only for unit tests if useful.

### 5. FastAPI Integration (1 day)

- [ ] Replace `JOBS` and `ARTIFACTS` dicts with repository calls.
- [ ] Add dependency injection for DB session.
- [ ] Ensure existing endpoints (`/health`, `/validate`, `/generate`, etc.) still work.
- [ ] Store job status and artifact metadata in DB; geometry files remain on disk or in object storage (object storage proper comes in E04).

### 6. Seed & Migration Path (0.5 day)

- [ ] Seed script that creates the known project `proj-banswara-bar-association`.
- [ ] Document how existing file-based models are linked to the first revision record.

---

## Out of Scope

- Real authentication (E03)
- Redis / async workers (E04)
- S3 (E04)
- Changing any geometry validation logic

---

## Key Design Rule

```
Database  â†’  metadata, revision pointers, job state, audit
Filesystem / future object store  â†’  authoritative geometry + reports + DXF/PDF
```

Never put the full wall/opening coordinate arrays into relational columns as the primary store.


---

# Week E02 â€” Acceptance Criteria

## Must Pass

1. **Schema & Migrations**
   - Alembic (or equivalent) can upgrade and downgrade cleanly.
   - All tables listed in the data model exist with appropriate indexes and foreign keys.

2. **Repository Behaviour**
   - Creating a project and a revision persists and can be re-loaded after process restart.
   - Job records transition through states (`queued` â†’ `running` â†’ `succeeded` / `failed`).
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


---

# Week E02 â€” Notes

## Migration Strategy for Existing File Models

1. Create an Organization and Project record for the known Banswara case.
2. Create Revision 1 that points at the current canonical model files via `model_storage_key` / `model_sha256`.
3. Do **not** attempt to bulk-import every historical report into the DB in E02; treat them as artifacts that can be linked later.

## Soft Delete

Prefer `deleted_at` over hard deletes for projects and revisions so audit and recovery remain possible.

## Testing Tip

Keep a small set of pure unit tests that use an in-memory or SQLite stand-in if full Postgres in CI is too heavy at first; move to real Postgres in CI during E05.


