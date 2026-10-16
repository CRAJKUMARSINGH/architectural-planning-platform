# Week E04 — Async Jobs & Object Storage — ✅ COMPLETE

**Status:** Complete  
**Completed:** 2026-09-23

## Summary

Moved long-running generate/validate/render work off the request path.
Redis + RQ workers now process jobs; MinIO provides local S3-compatible content-addressed storage.

## Deliverables Completed

- Redis 7 + RQ worker queue integrated into Docker Compose stack
- `services/worker/` — worker process running existing Python pipelines
- `services/worker/tasks.py` — deterministic artifact production with SHA-256 signing
- `services/worker/queue.py` — job dispatch and heartbeat
- MinIO S3-compatible object store: local dev via Docker Compose
- Content-addressed artifact storage: `orgs/{org}/projects/{proj}/revisions/{sha}/`
- Job status API: `GET /api/v1/jobs/{id}` + artifact download via controlled proxy
- `Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.web` added
- Regression fixtures: `tests/fixtures/e04/` — job_payloads.json, artifact_samples.json
- `tests/test_e04_jobs_expanded.py` — state machine, SHA-256 dedupe, path-traversal containment

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| `/generate` returns job ID immediately | ✅ Pass |
| Worker produces same deterministic artifacts as old synchronous path | ✅ Pass |
| Failure cases leave last valid revision intact | ✅ Pass |
| Artifact download via signed URL / controlled proxy | ✅ Pass |
