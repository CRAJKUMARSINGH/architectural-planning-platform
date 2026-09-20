# Database — Schema & Migrations

## Overview

Postgres 15+ managed by **Alembic**.

- `schema.sql` — reference DDL (also used by `docker-compose.yml` initdb).
- `migrations/` — Alembic-managed versioned migrations (added in E02).
- `alembic.ini` — Alembic configuration (added in E02).

## Local setup (via Docker Compose)

```bash
docker compose up postgres
```

The `schema.sql` is automatically applied on first start via the Docker
`initdb` volume mount.

## Alembic (E02 onwards)

```bash
# Create a new revision
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

## Design rules

1. **Geometry is never stored inline.** Walls, openings, stairs, routes live in
   content-addressed object-store blobs. The DB holds only the `model_sha256` pointer.
   See `docs/architecture/ADR-001-Geometry-Authority.md`.

2. **Audit events are immutable.** Never `UPDATE` or `DELETE` rows in `audit_events`.

3. **Organization isolation.** Every query that returns projects or revisions must filter
   by `organization_id`. See `docs/architecture/ADR-003-Tenancy-Model.md`.

4. **Soft deletes.** Use `deleted_at` for projects, organizations, users.
   Hard deletes require an explicit migration and security review.

5. **All migrations must be reversible.** A working `downgrade()` is required.
