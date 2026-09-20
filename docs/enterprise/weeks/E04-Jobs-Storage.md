# E04-Jobs-Storage

# Week E04 â€” Async Jobs & Object Storage

**Duration:** 5â€“7 days  
**Risk:** Medium  
**Depends on:** E02 (and preferably E03)  
**Blocks:** Scalable generation

---

## Objectives

1. Move long-running work off the HTTP request path.
2. Store artifacts in content-addressable object storage.
3. Preserve deterministic outputs of the existing Python pipelines.

---

## Task List

### 1. Queue Choice (0.5 day)

- [ ] Choose: Arq (async-native), RQ, or Celery.
- [ ] Add Redis to docker-compose.

### 2. Worker Process (2 days)

- [ ] Create a worker entrypoint that can run:
  - existing generate pipelines
  - validation / enrichment scripts
  - quality-gate report generation
- [ ] Worker updates job status in the database.
- [ ] On success, write artifact records with SHA-256.

### 3. Object Storage (1.5 days)

- [ ] MinIO for local development.
- [ ] Abstract storage backend (local filesystem fallback + S3 interface).
- [ ] Store artifacts under keys derived from content hash where practical.
- [ ] Signed URL or authenticated download endpoint.

### 4. API Changes (1 day)

- [ ] `/generate` (and similar) only enqueue and return `jobId`.
- [ ] `/jobs/{id}` returns status, progress, artifact list.
- [ ] `/artifacts/{id}` or signed download.

### 5. Failure & Idempotency (1 day)

- [ ] Ensure a failed job does not corrupt the last valid revision (align with existing Week 26 philosophy).
- [ ] Support safe retry of failed jobs.
- [ ] Idempotency keys for critical enqueue operations (optional but recommended).

### 6. Local DX (0.5 day)

- [ ] `docker compose up` starts API + worker + Redis + Postgres + MinIO.
- [ ] Document how to run a single job and inspect artifacts.

---

## Design Rules

- The worker must call the **same Python functions** that the old synchronous path used.
- Determinism is preserved by feeding the worker the same model revision + rule-pack version + seed.
- Presentation/furniture layers remain non-authoritative.


---


