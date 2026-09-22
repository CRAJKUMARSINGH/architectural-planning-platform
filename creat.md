# Advocate-Chambers — Development Gist & Session Log

> **Auto-updated every session push.** This file is the running gist of all
> engineering conversations, decisions, and implementation milestones.
> Last updated: 2026-09-22 (Phase 7 milestone).

---

## 🏛 Project: Advocate-Chambers / Bar Association Hall, Banswara

A hybrid **React 19 + Python** architectural planning platform.

| Layer | Technology |
|---|---|
| Frontend | React 19.3, TypeScript, Vite, TanStack Query v5, Zod |
| API gateway | FastAPI (Python 3.14), Pydantic v2, SQLAlchemy 2 |
| Geometry authority | Python — `packages/geometry/` |
| Persistence | SQLite (dev) / Postgres (prod), Alembic migrations |
| Object store | Filesystem (dev) / S3-compatible (prod) |
| Workers | RQ / Redis (optional) |
| Test runner | pytest (508 passing as of Phase 5 completion) |

---

## 📋 Implementation Plan Summary — `docs/IMPLEMENTATION_PLAN.md`

| Phase | Name | Status | Commit |
|---|---|---|---|
| 0 | Product contract (schemas, modes, states) | ✅ DONE | 5954ee2 |
| 1 | Canonical model stabilization | ✅ DONE | 5954ee2 |
| 2 | Typed command execution (Python) | ✅ DONE | ac42ae0 |
| 3 | Persistent revisions (Postgres/ORM) | ✅ DONE | 73c2fe6 |
| 4 | Auth & tenancy (JWT/HS256, roles) | 🔶 PARTIAL — OIDC/JWKS not yet |
| 5 | Replace prototype API (/v1 routes) | ✅ DONE | b4de163 |
| 6 | Durable jobs (QUEUED→RUNNING→DONE) | ✅ DONE | 73c2fe6 |
| 7 | 2D editor typed command dispatch | ✅ **NOW DONE** | *this session* |
| 8 | Presentation rendering | 🔶 PARTIAL — scripts only |
| 9 | Import (DXF/PDF/raster) | 🔶 PARTIAL — framework only |
| 10 | Exports & delivery packages | 🔶 PARTIAL — scripts only |
| 11 | Collaboration & review | 🔶 PARTIAL — script layer only |
| 12 | Testing & quality gates | ✅ DONE |
| 13 | Performance & observability | 🔶 PARTIAL — Prometheus/benchmarks |

**Next due:** Phase 5 (100% — push to remote), then Phase 8 (presentation rendering).

---

## 🗂 Key Architecture Decisions

- **ADR-001** — Geometry authority: Python is sole source of truth; React never owns geometry.
- **ADR-003** — Organization isolation: every DB query scoped to `org_id`.
- **ADR-004** — Canonical contract versioning: `advocate-chambers.command.v1`.
- **ADR-005** — Typed command execution: envelope → pipeline → revision.
- **ADR-006** — Persistent revisions: content-addressed SHA-256 in object store.

---

## 🚀 Session History

### Session — 2026-09-22 (Current)

**Goal:** Audit plan, implement Phase 5 (complete) + Phase 7 (frontend), push milestones.

**Completed this session:**

#### Phase 5 — Replace Prototype API (100%)
- `services/api/routes/v1_commands.py` — NEW
  - `POST /api/v1/projects/{id}/commands/preview` (dry-run, returns findings)
  - `POST /api/v1/projects/{id}/commands/commit` (persists revision)
  - `Idempotency-Key` header enforced on commit (422 if absent/short)
  - `If-Match: "Rev:N"` header validated on both routes (412 on mismatch)
  - `ETag: "Rev:N"` returned on every response
- `services/api/routes/v1_projects.py` — added typed `RevisionResponse` model + ETag on revisions list
- `services/api/main.py` — v1 routers mounted at `/api` prefix
- `.gitignore` — added `artifacts/`, `output/`, `*.db`
- `tests/test_phase5_commands.py` — 42 passing tests
- `tests/fixtures/phase5/` — 4 fixture files
- Fixed pre-existing: `test_week2_schema.py` encoding (Windows CP-1252 vs UTF-8)
- Fixed pre-existing: `test_week28_organization.py` git timeout guard

#### Phase 7 — Typed 2D Editor Command Dispatch (100%)
- `apps/web/src/components/useCommandDispatch.ts` — NEW
  - `usePreviewCommand()` mutation hook
  - `useCommitCommand()` mutation hook (invalidates `analysis` + `revisions` queries)
  - Zod schemas: `CommandResultSchema`, `FindingSchema`, `RevisionSummarySchema`
  - `CommandDispatchError` typed error class with `status` + `findings`
  - Auto-generates `idempotencyKey` per mutation call
- `apps/web/src/components/CommandPanel.tsx` — NEW
  - Renders inside StudioView right sidebar
  - Operations: move-opening, resize-opening, resize-space, set-site-orientation, add-space
  - Shows current revision number + validation state from `/api/v1/projects/{id}/revisions`
  - Preview button → dry-run, shows findings
  - Commit button → persists revision, refreshes viewport via query invalidation
  - Auto-fills selected object ID when viewport selection changes
- `apps/web/src/App.tsx` — imports and renders `<CommandPanel>` in StudioView
- `tests/test_phase7_frontend_commands.py` — 25 regression tests
- `tests/fixtures/phase7/` — 3 fixture files

**Test baseline:** 508 passed → **533 passed** (25 new Phase 7 tests), 0 failed.

---

### Session — 2026-09-22 (Earlier)

**Completed:**
- Full audit of all 14 phases against codebase
- Fixed baseline test failure: `test_week2_schema.py` JSON encoding bug
- Phase 5 50% milestone commit `b4de163`
- Confirmed 508 pass / 0 fail on full suite

---

### Sessions — 2026-09-20 to 2026-09-21

**Phase 1–3, Enterprise E01–E10:**
- Canonical model schemas (project-v2, command, finding, revision, render-manifest, artifact-manifest)
- Typed command execution: 13 operations, CommandRunner, RevisionSummary
- Persistent revisions: ORM (Organization/User/Membership/Project/Revision/Job/Artifact/AuditEvent), Alembic migrations, SQLRevision/Project/Job repositories, object store (FilesystemStore + S3Store)
- Durable jobs: QUEUED→RUNNING→SUCCEEDED/FAILED, RQ dispatch with inline fallback
- Auth: JWT HS256, role hierarchy (viewer/reviewer/editor/owner), AUTH_DISABLED dev mode
- 433→508 tests passing across all enterprise enrichment weeks (E01–E10, W01–W28)

---

## 📁 File Structure Highlights

```
Advocate-Chambers/
├── apps/web/src/
│   ├── App.tsx                         — StudioView wires CommandPanel
│   ├── components/
│   │   ├── CommandPanel.tsx            — Phase 7: command dispatch UI ★ NEW
│   │   ├── useCommandDispatch.ts       — Phase 7: TanStack hooks + Zod ★ NEW
│   │   ├── Viewport2D.tsx              — SVG viewport, click-to-select
│   │   ├── PropertyInspector.tsx       — shows selected object properties
│   │   ├── ValidationPanel.tsx
│   │   └── ArtifactPanel.tsx
├── packages/
│   ├── geometry/
│   │   ├── commands.py                 — CommandEnvelope, OPERATIONS
│   │   ├── command_runner.py           — CommandRunner (13 operations)
│   │   ├── persistence.py              — RevisionTransactionCoordinator
│   │   ├── constraints.py / topology.py / tolerances.py / serializers.py
│   │   └── revisions.py
│   └── schema/                         — JSON Schema contracts (v1)
├── services/api/
│   ├── main.py                         — FastAPI app, mounts /api routers
│   ├── auth.py                         — JWT auth, role deps
│   ├── routes/
│   │   ├── v1_commands.py              — Phase 5: /preview + /commit ★
│   │   ├── v1_projects.py              — CRUD + RevisionResponse
│   │   └── v1_health.py
│   ├── repository_sql.py               — SQL repository adapters
│   ├── models/orm.py                   — SQLAlchemy ORM models
│   └── db/session.py + migrations/
├── tests/
│   ├── test_phase5_commands.py         — 42 tests ★
│   ├── test_phase7_frontend_commands.py — 25 tests ★ NEW
│   └── fixtures/phase5/ + phase7/     ★ NEW
└── docs/
    ├── IMPLEMENTATION_PLAN.md          — 14-phase roadmap
    └── architecture/ADR-001 to ADR-006
```

---

## 🔧 Running the project

```bash
# Python tests (full suite)
python -m pytest tests/ -q

# Frontend dev server
cd apps/web && npm run dev

# API server (dev)
AUTH_DISABLED=true uvicorn services.api.main:app --reload

# Type-check frontend
cd apps/web && npm run typecheck
```

---

## ⚠ Known gaps / Next work

| Gap | Phase | Notes |
|---|---|---|
| OIDC/JWKS auth (RS256) | Phase 4 | HS256 only in prod; JWKS endpoint not wired |
| `split-wall` + `apply-furniture-operation` | Phase 2 | Return UNSUPPORTED — needs wall schema |
| Viewport interactions (drag/resize) | Phase 7 | Click-to-select only; no geometry dragging |
| Presentation rendering API | Phase 8 | Scripts exist; no structured render endpoint |
| DXF/PDF import pipeline | Phase 9 | Recognition only; no canonical promotion |
| Delivery export endpoint | Phase 10 | Scripts exist; no HTTP endpoint |
| Collaboration ORM/routes | Phase 11 | Script layer only |
| OpenTelemetry distributed tracing | Phase 13 | Prometheus metrics present |

---

*Content was generated by Kiro AI and Rajkumar C. Singh.*
*This is preliminary planning material — not construction, permit, or authority certification.*
