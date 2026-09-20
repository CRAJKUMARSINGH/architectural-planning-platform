# Runbook: Artifact Missing / Download Failure

**Symptom:** A job shows `succeeded` but artifact download returns 404 or the
SHA-256 does not match.

## Diagnosis

```bash
# Check artifact record in DB
psql $DATABASE_URL -c "SELECT id, kind, storage_key, sha256 FROM artifacts WHERE job_id = '<job-id>';"

# Check object store
# MinIO:
mc ls myminio/advocate-artifacts/<storage_key>
# S3:
aws s3 ls s3://advocate-artifacts/<storage_key>
```

## Resolution

1. **Artifact record exists but file missing in store**
   — The worker wrote the DB record but the store upload failed.
   Re-run the job (idempotent if same revision + rule-pack version).
   ```bash
   # Via API:
   POST /v1/projects/<proj-id>/jobs  {"job_type": "quality_gate"}
   ```

2. **SHA-256 mismatch** — possible corruption:
   ```bash
   python scripts/enterprise/verify_artifact.py <path/to/file> --expected-sha256 <hash>
   ```
   If mismatched, the artifact is untrusted. Regenerate.

3. **Object store unreachable**:
   ```bash
   docker compose ps minio
   curl http://localhost:9000/minio/health/live
   ```

## Prevention

- `verify_artifact.py` is run in the release pipeline.
- All artifacts include SHA-256 in the database record.
- Object store health is checked by `/ready` endpoint.
