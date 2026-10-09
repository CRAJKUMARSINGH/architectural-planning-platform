# Integration Status — Archi Copilot → Architectural Planning Platform

**Completed:** September 2026

All 6 integration steps are done. The two repositories are now one product.

---

## Step 1 — DB migration ✅

**What:** Added workflow tables to the canonical PostgreSQL schema.

**Files changed:**
- `services/api/db/schema.sql` — appended `brief_analyses`, `concept_versions`, `copilot_suggestions`, `scoring_results` tables with indexes
- `services/api/migrations/add_workflow_tables.sql` — standalone migration for existing databases

**To apply to an existing DB:**
```bash
psql $DATABASE_URL < services/api/migrations/add_workflow_tables.sql
```
Docker Compose picks them up automatically via `docker-entrypoint-initdb.d`.

---

## Step 2 — Python API routes ✅

**What:** 12 workflow endpoints added to the FastAPI backend.

**Files created:**
- `services/api/models/workflow_models.py` — `BriefAnalysis`, `ConceptVersion`, `CopilotSuggestion` SQLAlchemy ORM models
- `services/api/routes/v1_workflow.py` — all workflow routes
- `services/api/models/__init__.py` — updated to export new models

**Files changed:**
- `services/api/main.py` — registered `workflow_router` at `/api/workflow`

**All 12 routes verified:**
```
POST   /api/workflow/projects/{id}/analyze-brief
POST   /api/workflow/projects/{id}/analyze-brief-with-text
GET    /api/workflow/projects/{id}/brief-analysis
GET    /api/workflow/projects/{id}/versions
POST   /api/workflow/projects/{id}/versions
GET    /api/workflow/versions/{id}
DELETE /api/workflow/versions/{id}
POST   /api/workflow/versions/{id}/score
GET    /api/workflow/projects/{id}/suggestions
POST   /api/workflow/projects/{id}/suggestions/generate
PATCH  /api/workflow/suggestions/{id}
GET    /api/workflow/projects/{id}/export
```

---

## Step 3 — React components migrated ✅

**What:** All Archi Copilot UI migrated into `apps/web/src/features/workflow/`.
No new npm packages required. Uses only React + @tanstack/react-query (already installed).

**Files created:**
- `apps/web/src/features/workflow/types.ts` — TypeScript domain types
- `apps/web/src/features/workflow/api/client.ts` — fetch-based API client for all 12 routes
- `apps/web/src/features/workflow/api/hooks.ts` — React Query hooks
- `apps/web/src/features/workflow/components/ConceptCanvas.tsx` — drag/resize/snap zone canvas, pure React inline styles
- `apps/web/src/features/workflow/components/WorkflowPanel.tsx` — three-panel workspace (Brief+Analysis | Canvas | Versions+Suggestions)
- `apps/web/src/features/workflow/index.ts` — barrel export

---

## Step 4 — WorkflowPanel wired into StudioView ✅

**What:** Added a Geometry / Workflow tab switcher in the Studio header.

**File changed:** `apps/web/src/App.tsx`

Changes made:
- `import { WorkflowPanel } from './features/workflow'`
- Added `studioTab` state: `'geometry' | 'workflow'`
- Tab switcher buttons in `studio-header`
- Conditional render: `studioTab === 'workflow'` → `<WorkflowPanel>`, else geometry sidebar + viewport

---

## Step 5 — Promote-to-Model ✅

**What:** Canvas → Geometry handoff button added in the WorkflowPanel status bar.

**How it works:**
1. Architect designs concept on canvas
2. Clicks **⬆ Promote** — requires confirmation dialog
3. `POST /api/v1/projects/{id}/jobs` with `job_type=generate` and canvas blocks as payload
4. Returns a Job ID — the worker picks it up and creates a geometry revision
5. Architect reviews the result in the Geometry tab before it's authoritative

**Key constraint:** Canvas blocks are never silently promoted. The architect
always sees the confirmation dialog and the resulting Job ID.

---

## Step 6 — Archi Copilot Node.js server retired ✅

**What:** The standalone Node.js API server is superseded by the Platform's Python backend.

**File created:** `Archi Copilot/artifacts/api-server/RETIRED.md`
— documents the endpoint mapping from old to new.

**Keep:** `Archi Copilot/lib/api-spec/openapi.yaml` — canonical workflow API spec.

**Do not delete:** The `Archi Copilot/` folder — keep it as reference and for the OpenAPI spec.

---

## How to run the unified product

```bash
# 1. Start all services (Postgres, Redis, MinIO, FastAPI, Worker, React)
docker compose up --build

# 2. Set GEMINI_API_KEY for AI features
#    Add to docker-compose.yml → api.environment or a .env file:
GEMINI_API_KEY=your-key-here

# 3. Open in browser
http://localhost:5173

# 4. Click "Open workspace" → choose a project → click "✦ Workflow" tab
```

---

## Architecture summary

```
Browser
  └── apps/web (React 19, @tanstack/react-query, Vite)
        ├── Geometry tab  → existing viewport, commands, validation
        └── ✦ Workflow tab → apps/web/src/features/workflow/
              ├── Brief analysis panel  → POST /api/workflow/projects/:id/analyze-brief-with-text
              ├── Concept canvas        → state in React, saved via POST /api/workflow/projects/:id/versions
              ├── AI scoring panel      → POST /api/workflow/versions/:id/score
              ├── Suggestions panel     → POST /api/workflow/projects/:id/suggestions/generate
              ├── Export                → GET  /api/workflow/projects/:id/export
              └── ⬆ Promote            → POST /api/v1/projects/:id/jobs (type=generate)

FastAPI (services/api/main.py)
  ├── /api/v1/projects/*    existing Platform routes (auth, orgs, revisions, jobs)
  ├── /api/workflow/*       new workflow routes (v1_workflow.py)
  └── /api/ai/*             existing AI routes (v1_ai.py)

AI service (services/ai/ai_service.py)
  └── Gemini 2.5 Flash — brief analysis, version scoring, suggestions
      (heuristic fallback when GEMINI_API_KEY not set)

PostgreSQL
  ├── Core tables       (projects, revisions, jobs, artifacts, audit_events, ...)
  └── Workflow tables   (brief_analyses, concept_versions, copilot_suggestions, scoring_results)
```

---

## What's left for future work

From `Archi Copilot/SUGGESTION.md`:

- Snapping & alignment guides on canvas
- Site boundary + north arrow overlay for daylight scoring
- AI follow-up chat (ask copilot questions about a specific zone)
- Side-by-side version comparison with AI critique
- Client-facing read-only share link
- PDF export (canvas rendered as image)
- Version diffing view
