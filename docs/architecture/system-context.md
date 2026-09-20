# System Context

## High-Level Context Diagram

```
[Architect / Reviewer]
        │
        ▼
[React Web Editor] ────────────────────────────────────────┐
        │                                                  │
        │ HTTPS + JWT                                      │
        ▼                                                  │
[FastAPI Gateway] ◄──── Auth Provider (OIDC / Clerk)       │
        │                                                  │
        ├──► Postgres   (metadata, revisions, jobs, audit)  │
        ├──► Redis      (job queue)                        │
        ├──► Object Store (artifacts, geometry blobs)      │
        │    (MinIO local / S3/R2 production)              │
        │                                                  │
        └──► [Python Workers]                              │
                 │                                         │
                 ├── traecad_engine                        │
                 ├── drafting_kernel                       │
                 ├── weekly enrichment scripts             │
                 └── quality_gate                          │
                                                           │
[External Visual Tools] ──(read-only import)───────────────┘
 (Planner 5D, Magicplan, ArchiStar — never authoritative)
```

## Trust Boundaries

| Boundary | Trust Level | Enforcement |
|----------|-------------|-------------|
| Browser → API | Untrusted | Auth (JWT), rate limiting, input validation |
| API → Worker | Internal trusted | Job queue with signed payload |
| Worker → Geometry Engine | Pure functions | Immutable rule-pack + deterministic outputs |
| External visual tools | Untrusted | Import-only path; Python re-validation required |
| Presentation layer → Model | Non-authoritative | Explicit schema separation |

## Key Invariants

1. Same model revision + same rule-pack version + same engine commit → same findings.
2. Presentation layers cannot change wall/opening/stair topology.
3. Quality-gate missing evidence ≠ PASS.
4. `AUTH_DISABLED=true` is impossible in `ENV=staging` or `ENV=production`.

## Component Responsibilities

### React Web Editor (`apps/web`)
- Compiles briefs into structured commands
- Displays geometry (read) and triggers jobs (write)
- Shows job status and artifact download links
- Presents quality-gate state — never claims automatic issuability

### FastAPI Gateway (`services/api`)
- Thin typed adapter — coordinates, does not compute geometry
- Authenticates requests, checks organization membership
- Enqueues jobs to Redis
- Returns job IDs and status — never blocks on long computation

### Python Workers (`scripts/`, `services/worker/`)
- Run existing parametric pipeline, weekly enrichment, quality gate
- Produce deterministic, content-addressed artifacts
- Write results to object store and update job/artifact metadata in Postgres

### Postgres
- Holds metadata, revision pointers, job lifecycle, audit events
- Never holds authoritative wall/opening geometry inline

### Object Store (MinIO / S3)
- Holds geometry blobs (by SHA-256 key) and all generated artifacts
- Content-addressed: same hash = same content, forever

### Redis
- Simple job queue (RQ or Arq)
- No business logic; purely a delivery mechanism

## Professional Boundary

This system aids architectural planning. It does not certify:
- Construction readiness
- Permit / sanction readiness
- Fire safety or life-safety compliance
- Structural adequacy
- Accessibility (RPwD) final compliance

All outputs require independent professional review. See
`docs/enterprise/checklists/professional-review.md`.
