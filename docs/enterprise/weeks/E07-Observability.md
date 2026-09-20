# E07-Observability

# Week E07 â€” Observability

**Duration:** 3â€“4 days  
**Risk:** Low  
**Depends on:** E04, E05

---

## Objectives

1. Make the running system diagnosable by an operator.
2. Correlate jobs, requests, and quality-gate runs.

---

## Task List

### 1. Structured Logging (1 day)

- [ ] JSON logs with: timestamp, level, service, request_id, job_id, user_id (if present), message, extra.
- [ ] Propagate request_id from gateway to worker.

### 2. Metrics (1 day)

- [ ] Prometheus metrics:
  - HTTP request latency & count
  - Job queue depth
  - Job duration by type
  - Validation duration
  - Error rates
- [ ] Expose `/metrics` (protect in production).

### 3. Health Endpoints (0.5 day)

- [ ] `/health` â€” liveness
- [ ] `/ready` â€” checks Postgres + Redis + (optional) object storage
- [ ] Fail ready when critical dependencies are down.

### 4. Basic Dashboard (0.5 day)

- [ ] Provide a Grafana dashboard JSON or equivalent that shows the above metrics.
- [ ] Document how to import it.

### 5. Correlation with Quality Gates (0.5 day)

- [ ] When a quality-gate report is generated, log the application version / git SHA and rule-pack version.
- [ ] Store these identifiers on the report artifact metadata.


---


