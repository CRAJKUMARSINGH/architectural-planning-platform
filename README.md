# Architectural Planning Platform

## Implementation Status (September 2026)

|| Phase | Name | Status |
||---|---|---|
|| 0–3 | Contract, model, commands, revisions | ✅ Done |
|| 4 | Auth + OIDC deployment | ✅ Done |
|| 5–6 | Versioned API, durable jobs | ✅ Done |
|| 7 | 2D editor typed command dispatch | ✅ Done |
|| 8–10 | Rendering, import, delivery | ✅ Done |
|| 11–13 | Collaboration, testing, observability | ✅ Done |
|| **14** | **AI Brief Analysis (Gemini 2.5 Flash)** | **✅ Done** |
|| **15** | **Concept Canvas** | **✅ Done** |
|| 16 | AI Version Scoring & Tradeoffs | 📋 Next |
|| 17 | Proactive Suggestions | 📋 Planned |
|| 18 | Client Presentation & Export Workflow | 📋 Planned |

**Test suite: 718+ passed, 0 failed** · TypeScript: 0 errors

See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) for the roadmap.

See [`docs/FINISHING_GUIDE.md`](docs/FINISHING_GUIDE.md) for setup, verification, and release finishing steps.

---

## Phase 14 — AI Brief Analysis

Endpoints (all require auth):

```
POST /api/v1/ai/analyze-brief        # Gemini → structured space program
POST /api/v1/ai/score-version        # Gemini → 0–100 scores vs brief
POST /api/v1/ai/generate-suggestions # Gemini → categorised suggestions
GET  /api/v1/ai/health               # SDK + key availability check
```

Set `GEMINI_API_KEY` as an environment secret. The service degrades gracefully when absent — all other functionality is unaffected.

---

## Running

```bash
python -m pytest tests/ -q          # full test suite
AUTH_DISABLED=true uvicorn services.api.main:app --reload
cd apps/web && npm run dev
cd apps/web && npm run typecheck
```

---

*Preliminary planning material — not construction, permit, or authority certification.*

## Enterprise Enrichment Programme

Enterprise enrichment documentation is available in the [`docs/enterprise/`](docs/enterprise/) directory.

### Professional Review Boundary

> ⚠️ This software aids architectural planning. It does **not** certify:
> construction readiness, permit/sanction readiness, fire/life-safety compliance,
> structural adequacy, or accessibility (RPwD) final compliance. All outputs
> require independent professional review by licensed architects, engineers,
> and statutory authorities before use in regulated contexts.

---

## Phase 5 — Versioned API (`/api/v1/`)

```
POST /api/v1/projects/{id}/commands/preview   # dry-run, returns findings
POST /api/v1/projects/{id}/commands/commit    # persists revision
GET  /api/v1/projects/{id}/revisions          # typed RevisionResponse list
GET/POST /api/v1/projects/                    # CRUD with org isolation
```

All writes require `Idempotency-Key`. Both command routes support `If-Match: "Rev:N"`
and return `ETag: "Rev:N"` for optimistic concurrency.

## Phase 7 — React Command Dispatch

The `CommandPanel` component renders in the studio right sidebar:
- Operations: `move-opening`, `resize-opening`, `resize-space`, `set-site-orientation`, `add-space`
- **Preview** → dry-run via `usePreviewCommand`, shows findings
- **Commit** → persists revision via `useCommitCommand`, invalidates viewport query cache
- Auto-fills selected object ID from viewport selection

## Phase 12 — Testing & Quality Gates (100% Complete)

Added comprehensive testing infrastructure:
- **Property-based geometry tests** using Hypothesis for deterministic geometry invariants
- **Playwright DOM/SVG visual regression tests** for architectural viewport rendering
- **Quality gate inventory** covering 12 test categories with signed reports
- All 145 Phase 11-13 regression tests passing

Run the full Phase 12 suite with:

> advocate-chambers@1.0.0 test:phase12
> python -m unittest tests.test_phase12_quality_gate tests.test_phase12_property_based_geometry

> advocate-chambers@1.0.0 test:playwright
> npx playwright test

---

## Running

```bash
# Tests
python -m pytest tests/ -q

# API (dev)
AUTH_DISABLED=true uvicorn services.api.main:app --reload

# Frontend
cd apps/web && npm run dev

# Type check
cd apps/web && npm run typecheck
```

---

*Preliminary planning material — not construction, permit, or authority certification.*

## Quick Release

When all checks pass and you're ready to tag a release:

```bash
# Verify everything is green first
make verify
npm run test:week22
npm run test:week23

# Tag and push — triggers the release workflow
git checkout main
git pull
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

The release workflow will run the full quality gate, adversarial suite, and produce signed artifacts. See [`docs/FINISHING_GUIDE.md`](docs/FINISHING_GUIDE.md) for the full release checklist.
