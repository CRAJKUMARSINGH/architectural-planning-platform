# ADR-006 — Revision Commit Ordering and Optimistic Persistence

**Status:** Accepted
**Date:** 2026-09-21

## Decision

Revision commits use one transaction boundary around metadata and the
project's current-revision pointer:

1. Load the project through an organization-scoped repository.
2. Compare the requested base revision with the current revision.
3. Serialize the canonical model and write it to content-addressed storage.
4. Insert revision metadata with its parent, command fingerprint, and storage key.
5. Compare-and-swap the project's current revision pointer.
6. Record the audit event.

The database transaction is owned by the SQL adapter/caller.  A failed
compare-and-swap raises `RevisionConflict` and must roll back the revision
row.  The object-store write may remain as a harmless content-addressed
orphan and can be garbage-collected later.

Idempotency keys are persisted on revisions.  Replaying the same key and
fingerprint returns the original revision; reusing a key with a different
fingerprint is rejected.

Canonical model and validation bytes never live in Postgres.  Postgres stores
metadata and SHA-256 pointers, while filesystem/MinIO/S3-compatible storage
holds the bytes.