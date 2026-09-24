# 00 — Executive Overview

## What the Architectural Planning Platform Already Is

A hybrid **parametric CAD + architectural planning intelligence** platform:

- **Python** owns authoritative geometry, NBC/RPwD rule evaluation, deterministic reports, and export (DXF/PDF/SVG).
- **React 19.3 + Vite** provides the interactive editor (brief → model → validate → furnish → present → export).
- **FastAPI** is a thin typed adapter that never becomes the geometry source of truth.
- Extensive weekly enrichment (through ~Week 28) already delivers:
  - Reachability graphs, semantic openings, stair coordination
  - Versioned rule packs (`india-preliminary-review`)
  - Furniture/clearance-aware presentation layer
  - Candidate studio with transparent scorecards
  - Adversarial fixtures (30 known critical defects)
  - Performance benchmarks + reproducibility + quality gates
  - Conservative release classification (`PASS` / `REVIEW_REQUIRED` / `BLOCKED` / `INCOMPLETE`)

This is already unusually mature for a domain-specific planning tool.

## What “Enterprise-Grade” Means Here

| Dimension              | Prototype / Current                  | Enterprise Target                                      |
|------------------------|--------------------------------------|--------------------------------------------------------|
| State                  | In-memory + files                    | Durable DB + content-addressable artifacts             |
| Identity               | None / local                         | Multi-tenant orgs + roles + audit logs                 |
| Jobs                   | Synchronous / in-process             | Async queue + horizontal workers                       |
| Quality                | Manual npm scripts                   | Automated gates on every PR + release                  |
| Observability          | Print / local counters               | Structured logs + metrics + traces                     |
| Security               | Localhost CORS                       | AuthZ, rate limits, signed artifacts, scanned deps     |
| Deployment             | Developer machine                    | Containerized staging → production path                |
| Release                | Ad-hoc                               | Versioned + quality-gate report + SBOM + changelog     |
| Professional boundary  | Explicitly stated                    | Enforced in software + process                         |

## Guiding Principles (Non-Negotiable)

1. **Geometry Authority stays in Python.**  
   The React editor and FastAPI never become the source of truth for walls, openings, stairs, routes, or levels.

2. **Conservative Quality Gates.**  
   Missing evidence never becomes a silent pass. `REVIEW_REQUIRED` is the default honest state until independent professionals sign off.

3. **Presentation is never authoritative.**  
   Furniture, finishes, AI-tool imports, and visual candidates may never mutate the canonical model.

4. **Determinism + Auditability.**  
   Same inputs + same rule-pack version + same commit → same findings and same hashes.

5. **Small, reversible changes.**  
   Prefer wrapping and extending the existing weekly scripts and kernel over rewriting them.

6. **Professional review remains mandatory.**  
   Software can detect known defects and enforce process. It cannot replace the licensed architect, structural engineer, fire consultant, surveyor, or local authority.

## High-Level Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                               │
│  React Editor (Vite)  ·  Future SDKs  ·  Admin UI            │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS + JWT
┌────────────────────────────▼────────────────────────────────┐
│                     FastAPI Gateway                          │
│  Auth · Rate Limit · Validation · Job Enqueue · OpenAPI     │
└───────┬──────────────────────┬───────────────────┬──────────┘
        │                      │                   │
   ┌────▼────┐          ┌──────▼──────┐     ┌──────▼──────┐
   │ Postgres│          │ Redis Queue │     │ Object Store│
   │ Projects│          │ (RQ/Arq)    │     │ (S3/MinIO)  │
   │ Revisions│         │ Workers     │     │ Artifacts   │
   │ Audit   │          │             │     │ (SHA-256)   │
   └─────────┘          └──────┬──────┘     └─────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Python Workers     │
                    │  traecad_engine     │
                    │  drafting_kernel    │
                    │  weekly scripts     │
                    │  quality_gate       │
                    └─────────────────────┘
```

## Success Definition

After the 10-week program:

- A new engineer can bring up a complete local stack (DB + Redis + API + Web + worker) with one command.
- Every PR is automatically gated by unit tests, adversarial suite, and quality-gate contract.
- Projects, revisions, jobs, and artifacts are durable, multi-tenant, and auditable.
- The platform itself reaches a software quality state of “ready for professional architectural review” — never claiming automatic issuability.
- Existing domain regression (37+ tests, 30 adversarial fixtures, performance profiles) remains green.

## Risk Summary

| Risk                              | Mitigation                                      |
|-----------------------------------|-------------------------------------------------|
| Breaking geometry determinism     | Keep Python pipeline pure; wrap only            |
| Over-engineering early            | E01–E02 stay minimal; auth only after data      |
| Scope creep into new CAD features | Explicit freeze on new domain features during E-weeks |
| Professional boundary erosion     | Quality-gate states and README disclaimers enforced in code |
| Team bandwidth                    | Parallelize E01/E05/E07 after foundation        |

---

Proceed to `ENTERPRISE_ROADMAP.md` for the week-by-week plan.
