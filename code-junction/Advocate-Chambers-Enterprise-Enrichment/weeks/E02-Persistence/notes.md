# Week E02 — Notes

## Migration Strategy for Existing File Models

1. Create an Organization and Project record for the known Banswara case.
2. Create Revision 1 that points at the current canonical model files via `model_storage_key` / `model_sha256`.
3. Do **not** attempt to bulk-import every historical report into the DB in E02; treat them as artifacts that can be linked later.

## Soft Delete

Prefer `deleted_at` over hard deletes for projects and revisions so audit and recovery remain possible.

## Testing Tip

Keep a small set of pure unit tests that use an in-memory or SQLite stand-in if full Postgres in CI is too heavy at first; move to real Postgres in CI during E05.
