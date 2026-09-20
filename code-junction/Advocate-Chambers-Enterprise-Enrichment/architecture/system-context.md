# System Context

## High-Level Context Diagram (Text)

```
[Architect / Reviewer]
        │
        ▼
[React Web Editor] ──────────────────────────────┐
        │                                        │
        │ HTTPS + JWT                            │
        ▼                                        │
[FastAPI Gateway] ◄──── Auth Provider (OIDC)     │
        │                                        │
        ├──► Postgres (metadata, audit)          │
        ├──► Redis (job queue)                   │
        ├──► Object Store (artifacts, models)    │
        │                                        │
        └──► [Python Workers]                    │
                 │                               │
                 ├── traecad_engine              │
                 ├── drafting_kernel             │
                 ├── weekly enrichment scripts   │
                 └── quality_gate                │
                                                 │
[External Visual Tools] ──(import only)──────────┘
 (Planner 5D, etc. — never authoritative)
```

## Trust Boundaries

1. **Browser → API** — authenticated, rate-limited, validated.
2. **API → Worker** — trusted internal network; jobs carry revision + rule-pack identity.
3. **Worker → Geometry Engine** — pure functions preferred; side effects only through storage abstractions.
4. **External AI / visual tools** — untrusted; all imports go through recognition + validation pipelines and remain non-authoritative until explicitly accepted under professional review.

## Key Invariants

- Same model revision + same rule-pack version + same engine commit → same findings.
- Presentation layers cannot change wall/opening/stair topology.
- Quality-gate missing evidence ≠ PASS.
