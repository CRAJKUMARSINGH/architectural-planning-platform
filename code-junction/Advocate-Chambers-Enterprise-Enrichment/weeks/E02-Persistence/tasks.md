# Week E02 — Persistence Layer

**Duration:** 4–6 days  
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

### 4. Repository Layer (1–1.5 days)

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
Database  →  metadata, revision pointers, job state, audit
Filesystem / future object store  →  authoritative geometry + reports + DXF/PDF
```

Never put the full wall/opening coordinate arrays into relational columns as the primary store.
