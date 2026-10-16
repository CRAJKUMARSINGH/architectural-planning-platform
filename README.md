# Architectural Planning Platform

## Implementation Status (October 2026)

| Phase | Name | Status |
|---|---|---|
| 0–3 | Contract, model, commands, revisions | ✅ Done |
| 4 | Auth + OIDC deployment | ✅ Done |
| 5–6 | Versioned API, durable jobs | ✅ Done |
| 7 | 2D editor typed command dispatch | ✅ Done |
| 8–10 | Rendering, import, delivery | ✅ Done |
| 11–13 | Collaboration, testing, observability | ✅ Done |
| 14 | AI Brief Analysis (Gemini 2.5 Flash) | ✅ Done |
| 15 | Concept Canvas | ✅ Done |
| 16 | AI Version Scoring & Tradeoffs | ✅ Done |
| 17 | Proactive Suggestions (heuristic + Gemini) | ✅ Done |
| **18** | **Client Presentation & Export Workflow** | **📋 Next** |
| E01–E08 | Enterprise enrichment (hygiene → security) | ✅ Done |
| E09 | Staging & Release Process | 📋 Planned |
| E10 | Stabilisation & Enterprise Candidate | 📋 Planned |

**Test suite: 718+ passed, 0 failed** · TypeScript: 0 errors · npm audit: 0 vulns · pip-audit: 0 CVEs

See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) for the roadmap.  
See [`docs/FINISHING_GUIDE.md`](docs/FINISHING_GUIDE.md) for setup, verification, and release finishing steps.

---

## AI Endpoints (Phases 14–17)

All endpoints require authentication (`Authorization: Bearer <token>`).

```
POST /api/v1/ai/analyze-brief        # Gemini → structured space program
POST /api/v1/ai/score-version        # Gemini → 0–100 scores vs brief
POST /api/v1/ai/generate-suggestions # Gemini + heuristic fallback → categorised suggestions
GET  /api/v1/ai/health               # SDK + key availability check
```

Set `GEMINI_API_KEY` as an environment secret. All endpoints degrade gracefully to deterministic heuristic fallbacks when the key is absent — no other functionality is affected.

---

## Running

```bash
# Full Python test suite
python -m pytest tests/ -q

# API (dev — local only)
AUTH_DISABLED=true uvicorn services.api.main:app --reload

# Frontend
cd apps/web && npm run dev

# Type check
cd apps/web && npm run typecheck
```

---

## Quick Release

When all checks pass and you are ready to tag a release:

```bash
# Verify everything is green first
make verify
npm run test:week22
npm run test:week23

# Tag and push — triggers the release workflow
git checkout main
git pull
git tag -a v1.0.2 -m "Release v1.0.2"
git push origin v1.0.2
```

The release workflow runs the full quality gate, adversarial suite, and produces signed artifacts.  
See [`docs/FINISHING_GUIDE.md`](docs/FINISHING_GUIDE.md) for the full release checklist.

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

---

## Phase 7 — React Command Dispatch

The `CommandPanel` component renders in the studio right sidebar:
- Operations: `move-opening`, `resize-opening`, `resize-space`, `set-site-orientation`, `add-space`
- **Preview** → dry-run via `usePreviewCommand`, shows findings
- **Commit** → persists revision via `useCommitCommand`, invalidates viewport query cache
- Auto-fills selected object ID from viewport selection

---

## Phase 12 — Testing & Quality Gates

Added comprehensive testing infrastructure:
- **Property-based geometry tests** using Hypothesis for deterministic geometry invariants
- **Playwright DOM/SVG visual regression tests** for architectural viewport rendering
- **Quality gate inventory** covering 12 test categories with signed reports
- All Phase 11–13 regression tests passing

```bash
python -m unittest tests.test_phase12_quality_gate tests.test_phase12_property_based_geometry
npx playwright test
```

---

## Enterprise Enrichment Programme (E01–E08 Complete)

Enterprise enrichment documentation is in [`docs/enterprise/`](docs/enterprise/).

| Week | Theme | Status |
|---|---|---|
| E01 | Foundation & Hygiene | ✅ Done |
| E02 | Persistence Layer | ✅ Done |
| E03 | Auth & Tenancy | ✅ Done |
| E04 | Async Jobs & Storage | ✅ Done |
| E05 | CI/CD & Automated Gates | ✅ Done |
| E06 | API & Frontend Hardening | ✅ Done |
| E07 | Observability | ✅ Done |
| E08 | Security Hardening | ✅ Done |
| E09 | Staging & Release | 📋 Planned |
| E10 | Stabilisation | 📋 Planned |

### Security posture (E08 complete — October 2026)

- JWT/OIDC error responses no longer leak internal exception details
- CORS origins configurable via `CORS_ALLOW_ORIGINS` env-var (locked per environment)
- `/metrics` endpoint guarded by `METRICS_TOKEN`
- `deploy/oidc/docker-compose.oidc.yml` uses `:?` mandatory-variable syntax — no weak password defaults
- `npm audit`: 0 vulnerabilities · `pip-audit`: 0 CVEs
- TypeScript `"strict": true` — 0 errors

---

### Professional Review Boundary

> ⚠️ This software aids architectural planning. It does **not** certify:
> construction readiness, permit/sanction readiness, fire/life-safety compliance,
> structural adequacy, or accessibility (RPwD) final compliance. All outputs
> require independent professional review by licensed architects, engineers,
> and statutory authorities before use in regulated contexts.

---

*Preliminary planning material — not construction, permit, or authority certification.*
