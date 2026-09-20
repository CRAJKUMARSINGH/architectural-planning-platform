# Runbook: Database Migration Failure

**Symptom:** `alembic upgrade head` fails or API won't start (schema mismatch).

## Diagnosis

```bash
# Check current migration state
alembic current

# Check migration history
alembic history --verbose

# Validate DB connection
psql $DATABASE_URL -c "SELECT version();"
```

## Resolution

1. **Partial migration** — check alembic_version table:
   ```sql
   SELECT * FROM alembic_version;
   ```
   If stuck mid-migration, assess whether to complete or roll back.

2. **Roll back one revision**:
   ```bash
   alembic downgrade -1
   ```
   All migrations have a working `downgrade()` — this is enforced in the PR checklist.

3. **Roll back to baseline** (nuclear option — data loss risk):
   ```bash
   alembic downgrade base
   ```
   Only use if the database has no production data.

4. **Lock contention** — another migration is running:
   ```bash
   SELECT pid, query, state FROM pg_stat_activity WHERE query LIKE '%alembic%';
   # Kill if safe:
   SELECT pg_terminate_backend(<pid>);
   ```

## Prevention

- Always run migrations against staging first.
- All `downgrade()` functions must be implemented (PR checklist).
- Take a DB snapshot before running migrations on production.
