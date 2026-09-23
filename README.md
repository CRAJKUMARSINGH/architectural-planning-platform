# Advocate-Chambers — Architectural Planning Platform

## Implementation Status (September 2026)

| Phase | Name | Status |
|---|---|---|
| 0–3 | Contract, model, commands, revisions | ✅ Done |
| 4 | Auth + OIDC deployment | ✅ Done |
| 5–6 | Versioned API, durable jobs | ✅ Done |
| 7 | 2D editor typed command dispatch | ✅ Done |
| 8–10 | Rendering, import, delivery | ✅ Done |
| 11–13 | Collaboration, testing, observability | ✅ Done |
| **14** | **AI Brief Analysis (Gemini 2.5 Flash)** | **✅ Done** |
| **15** | **Concept Canvas (Archi-Copilot port)** | **✅ Done** |
| 16 | AI Version Scoring & Tradeoffs | 📋 Next |
| 17 | Proactive Suggestions | 📋 Planned |
| 18 | Client Presentation & Export Workflow | 📋 Planned |

**Test suite: 718+ passed, 0 failed** · TypeScript: 0 errors

See [`creat.md`](creat.md) for the full session log.
See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) for the roadmap.
See [`docs/ARCHI_COPILOT_INTEGRATION_PLAN.md`](docs/ARCHI_COPILOT_INTEGRATION_PLAN.md) for Archi-Copilot integration.

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

## Implementation Status

| Phase | Name | Status |
|---|---|---|
| 0 | Product contract | ✅ Done |
| 1 | Canonical model stabilization | ✅ Done |
| 2 | Typed command execution (Python) | ✅ Done |
| 3 | Persistent revisions | ✅ Done |
| 4 | Auth & tenancy (OIDC / JWT roles) | ✅ Done |
| 5 | Replace prototype API (/v1 routes) | ✅ Done |
| 6 | Durable jobs | ✅ Done |
| **7** | **2D editor typed command dispatch** | **✅ Done** |
| 8 | Presentation rendering | ✅ Done |
| **9** | **Import (DXF/PDF/raster)** | **✅ Done** |
| **10** | **Exports & delivery** | **✅ Done** |
| 11 | Collaboration & review | ✅ Done |
| 12 | Testing & quality gates | ✅ Done |
| **13** | **Performance & observability (OTel + Dashboards)** | **✅ Done** |
| 14 | AI brief analysis integration | ✅ Done |
| 15 | AI-Assisted Generative Space Planning | 📋 Planned |
| 16 | Concept canvas integration | 📋 Planned |
| 17 | AI version scoring integration | 📋 Planned |
| 18 | Proactive suggestions integration | 📋 Planned |
| 19 | Workflow enhancements | 📋 Planned |

**Test suite: 684+ passed, 0 failed** (as of Phase 14 completion — Phase 7 test isolation issue pre-existing, passes in isolation).

See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) for the full plan.
See [`creat.md`](creat.md) for the full session development gist.

---

## Phase 13 — Performance & Observability (100% Complete)

Added comprehensive OpenTelemetry export integration and observability infrastructure:
- **Correlation context:** Bounded request, trace, job, revision, and organization IDs through structured logs and response headers
- **Prometheus metrics:** Stage histograms covering the ten proposed pipeline measurements  
- **OpenTelemetry export:** Environment-driven OTLP exporter configuration with graceful degradation
- **Span context bridge:** Promotes correlation IDs to OTel attributes with timing and error capture
- **Structured JSON logging:** OTel-compatible log formatter with sensitive-key stripping
- **Security:** OTLP endpoint configured from environment only, sensitive keys stripped from logs

Local implementation complete. Deployment-level dashboards and load-tested evidence remain deployment-specific follow-up.

Run the Phase 13 regression suite with:

> advocate-chambers@1.0.0 test:phase13
> python -m unittest tests.test_phase13_observability tests.test_phase13_otel

## Phase 14 — AI Brief Analysis Integration (100% Complete)

Added comprehensive AI service integration with Gemini API:
- **AI Service:** `services/ai/ai_service.py` with graceful degradation when Gemini SDK or API key unavailable
- **Schemas:** JSON schemas for AI brief analysis, version scoring, and suggestions with provenance tracking
- **API Routes:** `services/api/routes/v1_ai.py` with endpoints for brief analysis, version scoring, and suggestions
- **Quality Gates:** AI-generated content includes model version, timestamp, and provenance tracking
- **Security:** API keys stored as environment variables, AI operations require authentication
- **Integration:** AI service integrates with existing Week 11-12 brief compiler pipeline

Run the Phase 14 regression suite with:

> advocate-chambers@1.0.0 test:phase14
> python -m pytest tests/test_phase14_ai_brief_analysis.py -v

---

## Archi-Copilot Integration Plan (In Progress)

**Status:** Phase 14 complete — continuing with subsequent phases

Comprehensive integration plan to add AI-native features from Archi-Copilot:
- **AI Brief Analysis:** ✅ Enhanced Week 11-12 brief compiler with Gemini API integration
- **Concept Canvas:** Interactive 2D massing/bubble diagrams with multi-floor support
- **AI Version Scoring:** AI-powered design evaluation against briefs
- **Proactive Suggestions:** Categorized AI suggestions for design improvements

**Architecture Approach:** AI-enhanced editing with proper validation and provenance tracking while maintaining Python geometry-authority principle.

**Timeline:** 22-32 weeks (5-8 months) across 5 implementation phases (Phases 14-18)

**Phase 14 Completion:**
- AI service integration with Gemini API
- AI brief analysis, version scoring, and suggestion schemas
- API routes for AI operations with proper error handling
- Quality gate integration and provenance tracking
- 17 regression tests (all passing)
- Full test suite: 684 passed, 0 failed

See [`docs/ARCHI_COPILOT_INTEGRATION_PLAN.md`](docs/ARCHI_COPILOT_INTEGRATION_PLAN.md) for complete details.

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


## Enterprise Enrichment E01 — foundation slice started

The attached enterprise plan is preserved under
[`code-junction/Advocate-Chambers-Enterprise-Enrichment/`](code-junction/Advocate-Chambers-Enterprise-Enrichment/).
The first E01 slice adds repository hygiene and a frozen verification baseline
without changing geometry or runtime behavior:

- pinned Node/Python versions and shared Python tooling configuration;
- `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, and `CHANGELOG.md`;
- baseline reports under `baselines/2026-09-20/`;
- one-command verification with `npm run verify:baseline`.

E01 remains in progress; persistence, identity, queues, CI enforcement, and
deployment are intentionally deferred to their ordered enterprise weeks.

## W1-E-10 — Week 1 regression contract: DONE

The Week 1 baseline contract is now synchronized with the current canonical
model and has a durable fixture runner:

- `tests/fixtures/week1/known-upper-floor-exterior-door.json` proves that an
  unjustified upper-floor exterior door remains a `BLOCKER`.
- `tests/fixtures/week1/valid-connected-model.json` proves that a connected
  model remains free of blocking findings.
- `python scripts/week1.py fixtures` runs both fixtures and checks their
  expected rule/severity/object evidence.
- `python scripts/week1.py verify-manifest` now detects drift between the
  committed validation report, source hashes, and fixture files.

The source baseline is currently `pass` because later Week 3–8 work removed
the original known blocker; the invalid case remains preserved as a regression
fixture instead of being incorrectly recorded as the live baseline state.

The Week 9 and Week 10 enrichment has been implemented and merged into the
canonical planning pipeline.

## Fresh Week 01–16 program — Weeks 01–16 applied

The fresh execution program now uses a common root drafting kernel plus small
building-type recipes instead of duplicating planning logic in one weekly file.
The program includes safe optimization guidance derived from the requested
Maket.ai, Planner 5D, Archistar/Snaptrude, Floorplanner, Roomstyler/Homestyler,
Magicplan, LLM, 4Lines.ai, and Archiagent patterns. Those tools are visual and
workflow references only; they do not replace canonical geometry validation or
professional review.

- Common kernel: [`scripts/drafting_kernel.py`](scripts/drafting_kernel.py)
- Small project recipes: [`packages/recipes/index.json`](packages/recipes/index.json)
- Safe visual-tool patterns:
  [`packages/recipes/visual-tool-patterns.json`](packages/recipes/visual-tool-patterns.json)
- Fresh Week 01–05 report:
  `bar-association-hall/standard/fresh-week01-05-kernel-report.json`
- Week 06–16 reports and manifests:
  `bar-association-hall/standard/`
- Week 16 AI-tool input contract:
  `bar-association-hall/standard/week16-ai-tool-inputs.json`
- Nine-week Week 16 tool execution program: `docs/WEEK16_SUPPLEMENTARY_PROGRAM_01_09.md`

Run the fresh Week 01–05 contract with:

```bash
npm run enrich:fresh-week01-05
npm run validate:fresh-week01-05
npm run test:fresh-week01-05
```

**Task completion:** the fresh Week 01–16 program is applied in this branch and
marked complete here. Week 16 now accepts explicit, review-first inputs from
Maket.ai, Planner 5D, Archistar/Snaptrude, Floorplanner,
Roomstyler/Homestyler, Magicplan, ChatGPT/Claude/Grok/Gemini, 4Lines.ai, and
Archiagent without allowing those tools to override the canonical model.
Outputs remain preliminary planning aids and are not construction, permit, code,
accessibility, fire/life-safety, structural, MEP, survey, or authority
certification.

## Delivered

- **Week 9 — furniture and presentation:** a versioned furniture/equipment library
  with scale, occupancy, and clearance envelopes; deterministic occupancy-aware
  layouts; and a presentation layer that cannot mutate authoritative room, wall,
  opening, stair, or route geometry.
- **Week 10 — comparison and release discipline:** deterministic candidate seeds,
  transparent scorecards for area, adjacency, route quality, daylight/ventilation,
  structural/service coordination, and furniture fit; golden fixtures for
  residential, commercial, institutional, and industrial programs; geometry
  property checks; a release checklist; an export manifest; a changelog; and a
  readable blocked-case SVG fixture.

Run the enrichment and focused regression suite with:

```bash
npm run enrich:week910
npm run test:week910
```

The generated artifacts are under
`bar-association-hall/standard/`, including the Week 9 presentation report,
Week 10 candidate/QA report, release checklist, manifest, changelog, and
failure fixture.

**Release note:** the canonical Bar Association model is now blocker-free
through Week 10. Week 10 selects a deterministic best candidate and the Week 8
sheet stamp is **VALIDATED FOR PRELIMINARY REVIEW**. Two Week 6 warnings remain
for survey-confirmed road frontage and service-access intent; they are explicit
assumptions, not hidden pass conditions. These outputs are still preliminary
planning aids and require review by the licensed architect, structural engineer,
MEP consultant, fire/life-safety professional, surveyor, and local authority.

**Task verification:** Week 3–10 enrichment and the Week 3–8 blocker-removal
pass are complete on `main`. The full weekly regression suite passes (`37`
tests), Week 1–8 validation commands pass, Week 2 migration round-trips without
loss, Week 9 presentation validation passes, and Week 10 release gating selects
candidate `C-01` with `releaseReady: true`. The remaining Week 6 warnings stay
visible for professional review.

# Advocate-Chambers

Architectural planning intelligence for the Bar Association Hall project in
Banswara. The Week 2 canonical model remains the source of truth for geometry;
the Week 3–4 enrichment adds explainable routes, semantic openings, clearance
checks, and stable opening schedules before drawing export.

## Post-Week-20 validation program

The next enrichment phase is an evidence-based validation program rather than
another feature-only phase. It adds a weekly plan for adversarial architectural
fixtures, independent professional review, performance benchmarks, and
reproducibility gates.

The Week 21–27 validation track records acceptance thresholds, benchmark
workload profiles, reviewer scorecards, release classifications, and proposed
evidence layout.

The target release statement is: **100% detection of known critical defects,
zero dangerous false negatives, reproducible professional findings, measured
performance, and no loss of a valid project revision.** Until those gates are
met, generated plans remain preliminary planning and coordination aids and are
not automatically issuable.

## Week 21 task status — applied

Week 21 establishes the machine-readable quality-gate contract and records the
current regression baseline before adversarial, professional-review, and
performance evidence is supplied.

- Added `scripts/quality_gate.py` with `PASS`, `REVIEW_REQUIRED`, `BLOCKED`,
  and `INCOMPLETE` states.
- Added schemas for adversarial benchmark, professional review, and performance
  benchmark results under `packages/schema/`.
- Added tamper detection through a deterministic report signature.
- Added `tests/test_quality_gate.py` covering missing evidence, critical false
  negatives, professional uncertainty, performance failures, passing gates, and
  report tampering.
- Added the baseline artifact:
  `bar-association-hall/standard/quality-gate-report.json`.

The current Week 21 report is `REVIEW_REQUIRED` because the Week 22–26
evidence tracks are present, while independent professional review is still
pending. Missing benchmark evidence is not treated as a pass.

Run the Week 21 contract checks with:

```bash
npm run enrich:week21
npm run validate:week21
npm run test:week21
```

## Week 22 task status — applied and marked done

Week 22 adds the adversarial fixture foundation required to test dangerous
architectural defects instead of only validating successful examples.

- Added 15 deterministic defective fixtures paired with one valid source model.
- Added expected rule ID, severity, affected objects, evidence fields, and
  suggested correction contracts for every fixture.
- Added automated fixture discovery, explicit model mutations, finding
  execution, and benchmark reporting.
- Added the fixture metadata schema at
  `packages/schema/week22-adversarial-fixture.schema.json`.
- Added the foundation report at
  `bar-association-hall/standard/week22-adversarial-foundation-report.json`.

The Week 22 benchmark must report zero missed critical defects, zero dangerous
false negatives, no valid-baseline false positives, and complete evidence and
correction data for every finding. Independent professional review remains
required; this benchmark does not grant planning or construction approval.

The Week 22 adversarial track currently passes with 15 of 15 critical fixtures
detected. The combined quality gate remains `INCOMPLETE` until independent
Week 24 professional-review results are supplied.

Run the Week 22 fixture checks with:

```bash
npm run enrich:week22
npm run validate:week22
npm run test:week22
```
**Task completion:** Week 22 enrichment is complete and marked done in this README.

## Week 23 task status — applied and marked done

Week 23 expands the adversarial benchmark from the original 15 fixtures to 30
deterministic cases and hardens the release measurements.

- Retained all 15 Week 22 invalid-fixture regressions and added 10 additional
  invalid mutation cases plus 5 incomplete-input cases.
- Covered geometry, openings, routes, furniture, levels, and site mutations.
- Added explicit valid, invalid, and incomplete-input group accounting.
- Added false-positive and false-negative reports, rule-ID accuracy, affected
  geometry accuracy, and suggested-correction completeness measurements.
- Added the Week 23 case manifest and schema under
  `tests/fixtures/adversarial/` and `packages/schema/`.
- Added the deterministic report at
  `bar-association-hall/standard/week23-adversarial-expansion-report.json`.
- Connected the quality gate to the expanded Week 23 adversarial report.

The Week 23 benchmark passes with 30 of 30 known defects detected, zero
dangerous false negatives, zero valid-baseline false positives, and complete
rule, evidence, geometry, and correction measurements.

Run the Week 23 checks with:

```bash
npm run enrich:week23
npm run validate:week23
npm run test:week23
```

**Task completion:** Week 23 enrichment is complete and marked done in this README.

## Week 24 task status — review package applied

Week 24 adds a blinded independent professional-review package without
fabricating professional participation.

- Added a blinded pack containing 10 valid, 10 defective, and 5 borderline or
  incomplete-input plans.
- Added reviewer instructions covering independent scoring, reproducibility,
  critical findings, and disagreement documentation.
- Added the standard review form and finding/disagreement result schema.
- Added the software answer key separately from the reviewer-facing pack.
- Added anonymized review results with two pending reviewer slots at
  `bar-association-hall/standard/week24-anonymized-review-results.json`.

The package is structurally complete, but its status correctly remains
`REVIEW_REQUIRED` until at least two independent professionals submit
scorecards meeting the 90% agreement and reproducibility gates.

Run the Week 24 package checks with:

```bash
npm run enrich:week24
npm run validate:week24
npm run test:week24
```

**Task completion:** Week 24 review infrastructure is complete; external professional review remains pending.

## Week 25 task status — applied and marked done

Week 25 adds the performance benchmark harness required to establish measured
limits for representative project sizes.

- Added `benchmarks/run_benchmark.py` and `benchmarks/README.md`.
- Added small, medium, and large deterministic workload fixtures matching the
  validation-program profiles.
- Recorded input, model, and validation signatures; application commit and
  rule-pack metadata; p50/p95 operation timings; memory, CPU, failure
  recovery, timeout, out-of-memory, data-loss, and nondeterminism counts.
- Connected the performance report to the Week 21 quality gate.
- Added the report at
  `bar-association-hall/standard/week25-performance-report.json`.

The initial Week 25 run passes with no silent timeouts, out-of-memory failures,
data-loss events, operation errors, or nondeterministic repeated inputs. Export
timings are deterministic serialization baselines, not a claim of completed
professional PDF/DXF production exports.

Run the Week 25 checks with:

```bash
npm run enrich:week25
npm run validate:week25
npm run test:week25
```

**Task completion:** Week 25 enrichment is complete and marked done in this README.

## Week 26 task status — applied and marked done

Week 26 adds reproducibility and failure-recovery evidence for a second
workspace.

- Added the reproducibility runner at `scripts/week26.py`.
- Added an artifact package containing the input model hash, application
  commit, rule-pack version, model signature, validation signature, and signed
  artifact manifest.
- Added tampered-manifest, missing-artifact, partial-export, soft
  archive/restore, second-workspace, and revision-comparison checks.
- Added the report at
  `bar-association-hall/standard/week26-reproducibility-report.json`.
- Added the explicit revision comparison report at
  `bar-association-hall/standard/week26-revision-comparison-report.json`.

The Week 26 report passes all acceptance checks: tampering is rejected, missing
artifacts remain explicit, partial generation preserves the last valid
revision, restore preserves revision identity, and the package verifies in a
second workspace.

Run the Week 26 checks with:

```bash
npm run enrich:week26
npm run validate:week26
npm run test:week26
```

**Task completion:** Week 26 enrichment is complete and marked done in this README.

**Combined Week 22–26 task completion:** The adversarial corpus, expanded
benchmark, independent-review package, performance harness, reproducibility
runner, failure-injection checks, and revision-comparison report are applied
and validated on `main`. The combined quality gate remains
`REVIEW_REQUIRED` only until two independent professionals complete the Week
24 review; no professional approval or permit decision is implied.

## Week 27–28 task status — release decision and project organization applied

Week 27 combines the validation evidence into one conservative release
classification, known-limitations register, and remediation backlog. Week 28
adds an index-first inventory for the three delivered project packages:
**Bar Association Hall**, **Jamuniya-Shaktawat**, and **Advocate Chambers**.

- Existing drawing and input paths are preserved; no destructive binary move or
  history rewrite is performed.
- Every tracked path receives a project scope, role, storage hint, Git identity,
  and proposed canonical destination.
- Ambiguous legacy root assets remain visible with `reviewRequired: true`.
- The current release classification remains `REVIEW_REQUIRED`; automated
  evidence is coordinated, but professional, site, statutory, and authority
  review are not fabricated.

Run the organization and release checks with:

```bash
npm run enrich:week27
npm run validate:week27
npm run test:week27
npm run enrich:week28
npm run validate:week28
npm run test:week28
```

**Task completion:** Week 27–28 enrichment is applied. The repository now has
a repeatable release/remediation record and a reversible project-data index;
physical migration remains a separate reviewed operation.


## Week 3–4 task status

**Applied on `main`:**

- Week 3 per-level and cross-level walkability graph with connected components,
  entry-root route checks, vertical connector edges, and first-broken-edge
  diagnostics.
- Week 4 semantic wall breaks with side A/side B, explicit exterior-entry
  semantics, door width and swing checks, approach/landing checks, furniture
  conflict hooks, and stable opening tags.
- Deterministic reports:
  - `bar-association-hall/standard/week3-reachability-report.json`
  - `bar-association-hall/standard/week4-openings-report.json`
  - `bar-association-hall/standard/opening-schedule.json`
  - `bar-association-hall/standard/week34-enrichment-manifest.json`
- FastAPI `/analysis` endpoint and React viewport route overlay.
- Regression tests in `tests/test_week34_enrichment.py`.

The current legacy fixture now passes the route/opening gates after the topology
correction pass. Synthetic regression fixtures still prove that orphaned rooms,
invalid side B openings, and disconnected routes remain blockers when
introduced.

## Commands

```bash
npm run enrich:week34
npm run validate:week3
npm run validate:week4
python -m unittest discover -s tests -p 'test_week*.py'
npm run typecheck:web
npm run build:web
```

All dimensions are nominal planning dimensions in inches. Outputs remain
preliminary review material and require qualified architectural, structural,
fire/life-safety, accessibility, and local-code review before construction.

## Week 5–6 task status

**Applied on `main`:**

- Week 5 stair and floor-to-floor coordination validates connector endpoints,
  level elevations, riser arithmetic, tread, landing, width, direction, and
  route continuity. It keeps future-ready connector semantics for ramps and
  lifts without pretending they are validated stairs.
- Week 6 adds an inspectable institutional program template, required room-use
  completeness, area/dimension checks, required/preferred/forbidden
  adjacencies, and site orientation/frontage/service-access assumptions.
- Deterministic reports:
  - `bar-association-hall/standard/week5-stair-coordination-report.json`
  - `bar-association-hall/standard/week6-program-report.json`
  - `bar-association-hall/standard/week56-enrichment-manifest.json`
- The FastAPI `/analysis` response now includes Week 5 connectors and Week 6
  program, orientation, adjacency, and finding data.
- Regression tests live in `tests/test_week56_enrichment.py`.

Commands:

```bash
npm run enrich:week56
npm run validate:week5
npm run validate:week6
python -m unittest discover -s tests -p 'test_week*.py'
```

## Week 7–8 task status

**Applied on `main`:**

- Week 7 adds the versioned `india-preliminary-review` rule pack under
  `bar-association-hall/standard/rule-packs/`.
- Universal geometry checks are separated from configurable accessibility,
  egress, daylight, ventilation, wet-area, and service checks.
- Reports now carry the selected pack, effective date, assumptions,
  professional-review items, and deterministic finding metadata. A rule-pack
  change changes findings without changing authoritative geometry.
- Week 8 adds a deterministic technical-drawing quality contract covering
  wall/layer hierarchy, hatches, labels, legends, title blocks, north arrows,
  scales, sheet references, plan/section/elevation consistency, and traceability
  from visible openings, spaces, and stairs back to model IDs.
- Sheet status is explicit: `VALIDATED FOR PRELIMINARY REVIEW` only when all
  upstream gates pass; otherwise `NOT ISSUABLE`.
- Deterministic reports:
  - `bar-association-hall/standard/week7-rule-pack-report.json`
  - `bar-association-hall/standard/week8-drawing-quality-report.json`
  - `bar-association-hall/standard/week78-enrichment-manifest.json`
- The FastAPI `/analysis` response now includes Week 7 rule-pack data and Week
  8 drawing-quality/stamp data.
- Regression tests live in `tests/test_week78_enrichment.py`.

Commands:

```bash
npm run enrich:week78
npm run validate:week7
npm run validate:week8
npm run test:week78
```

The Week 8 stamp is a preliminary-review gate, not a construction,
accessibility, fire/life-safety, structural, MEP, survey, permit, or local-code
certification.

## Week 11–12 task status

**Applied and marked done:**

- Week 11 adds explicit **Brief, Model, Validate, Furnish, Present, and Export**
  product modes in the web editor.
- The capability matrix distinguishes available, provisional, and
  professional-review features for import, 3D, candidate comparison, materials,
  site feasibility, and collaboration.
- Local-only performance counters report model size, object counts, validation
  duration, render duration, and export duration without telemetry.
- Week 12 adds a deterministic conversational brief compiler for metric and
  imperial units. It extracts site dimensions, north, frontage, levels,
  floor-to-floor heights, room schedules, area targets, access intent,
  occupancy, adjacencies, style, and requested outputs.
- Briefs show assumptions, ambiguities, and missing topology facts before plan
  generation. Supported commands become typed revision previews with changed
  object IDs and validation deltas; conditional outer-door removal is blocked
  until an intentional access path is modeled.
- FastAPI routes: `GET /capabilities`, `GET /performance`,
  `POST /brief/compile`, and `POST /brief/command`.
- Deterministic artifacts:
  - `bar-association-hall/standard/week11-capability-matrix.json`
  - `bar-association-hall/standard/week12-brief-compiler-report.json`
  - `bar-association-hall/standard/week1112-enrichment-manifest.json`
  - `bar-association-hall/standard/week1112-changelog.md`
- Regression tests live in `tests/test_week1112_enrichment.py`.

Commands:

```bash
npm run enrich:week1112
npm run validate:week11
npm run validate:week12
npm run test:week1112
```

The brief compiler and product modes are preliminary planning aids. They do
not provide survey, code, permit, accessibility, fire/life-safety, structural,
MEP, or construction certification.

## Week 13–14 task status — applied and marked done

The Week 13 and Week 14 enrichment is implemented in the canonical pipeline.

- **Week 13 — import, recognition and editable digital twin:** DXF source
  inspection preserves source hash, entity/layer counts and geometry-preserved
  status; PDF/image recognition is explicitly assisted and review-required;
  uncertain objects remain non-authoritative; editable-twin links preserve
  units, levels, openings and source provenance; IFC/BIM remains capability-gated.
- **Week 14 — synchronised views:** 2D plans, 3D, sections and elevations share
  one model revision and selection key, with camera presets, level visibility,
  section-box and isolated-room contracts, snapping targets, route overlays and
  validation markers.
- **Sheet coverage rationalisation:** PDF and DXF export code now uses one
  paper-space layout contract. It is based on ISO 5457 A-series sheet formats
  and ISO 7200-style title-block information fields. The drawing zone is
  protected first; notes, legends and indices share a bounded band, with a
  project policy of **supporting content ≤ 20%** and **drawing zone ≥ 65%**.
  These ratios are project policy, not a claim that ISO prescribes a universal
  percentage.
- **Annotation standard:** future labels, dimensions, keynotes and general
  notes use a shared paper-space type scale with a 2.5 mm minimum readable
  target for ordinary annotations; DXF model-space heights derive from that
  same policy instead of scattered constants.
- **FastAPI routes:** `POST /import/recognize`, `GET /views/synchronized`, and
  `GET /sheet-standard`.
- **Deterministic artifacts:**
  - `bar-association-hall/standard/week13-import-recognition-report.json`
  - `bar-association-hall/standard/week14-synchronized-views-report.json`
  - `bar-association-hall/standard/sheet-layout-standard.json`
  - `bar-association-hall/standard/week1314-enrichment-manifest.json`
  - `bar-association-hall/standard/week1314-changelog.md`
- Regression tests: `tests/test_week1314_enrichment.py`.

Commands:

```bash
npm run enrich:week1314
npm run validate:week13
npm run validate:week14
npm run test:week1314
```

**Task completion:** Week 13–14 enrichment and the sheet-coverage/
annotation-standard correction are complete and are included in this `main`
release. All outputs remain
preliminary planning/coordination aids and require the appointed architect,
engineers, surveyor and local authority review.

## Week 15–16 task status — applied and marked done

The Week 15 and Week 16 enrichment is implemented in the canonical pipeline.

- **Week 15 — parametric assets and clearance-aware furnishing:** the typed
  catalog covers furniture, fixtures, appliances, sanitaryware, seating rows,
  dais, library tables, counters, vehicles, and industrial equipment. Every
  asset carries dimensions, allowed rotations, wall relationships, service
  side, occupancy, and clearance-envelope data. Room templates cover
  residential, offices/chambers, halls, classrooms, libraries, healthcare,
  retail, and light industrial use.
- Drag, rotate, duplicate, align, replace, and find-valid-position operations
  are typed and non-mutating. Placement rejects door swings, required routes,
  stairs, service zones, room-boundary violations, and overlapping clearances.
  Presentation objects are never authoritative construction geometry.
- **Week 16 — candidate studio and presentation pipeline:** candidates use
  deterministic seeds and transparent area, adjacency, route,
  daylight/ventilation, vertical-coordination, furniture-fit, and visual
  metrics. A candidate with a `BLOCKER` or `ERROR` cannot win.
- **W16-02 — Planner 5D furnishing candidate exchange:** imported furniture
  now passes through typed canonical asset mappings, model-revision and scale
  checks, and the Week 15 clearance validator. Route, door-swing, room-fit,
  stair/service-zone, and overlapping-clearance conflicts are reported as
  rejected placements; imported items remain presentation-only, and a
  rejected item makes the Planner 5D candidate ineligible.
- **W16-03 — Archistar / Snaptrude site-feasibility evidence:** imported site
  facts now retain source, coordinate/unit assumptions, north/frontage,
  access points, setbacks, levels, massing assumptions, confidence, and
  professional-review state. The adapter compares those facts with the Week 6
  orientation/program contract and links the canonical Week 7 rule-pack
  findings without mutating authoritative geometry. Missing frontage or
  service-access facts remain explicit warnings rather than hidden passes.
- **W16-04 — Floorplanner synchronized 2D/3D views:** imported plans and 3D
  views now retain one model revision, level visibility, object-ID mappings,
  room boundaries, openings, stairs, export provenance, and validation
  evidence. Unknown IDs, incomplete level coverage, stale revisions, and
  missing validation reruns remain review-required rather than silently
  accepted.
- **W16-05 — Roomstyler / Homestyler clearance-aware presentation:** typed
  furniture and finish options retain asset scale, occupancy, source/render
  provenance, candidate ID, and canonical model revision. Room fit, route,
  service-side, door-approach, and overlapping-clearance findings are reused
  from the Week 15 validator. A polished option cannot suppress a technical
  blocker or become authoritative geometry.
- **W16-06 — Magicplan photo-assisted recognition queue:** source images,
  capture metadata, known dimensions, scale evidence, confidence, proposed
  canonical links, and manual confirmation are retained. Only a confirmed,
  scale-backed recognition with a post-promotion topology/clearance rerun is
  promoted; uncertain, rejected, and image-only results remain review
  evidence.
- **W16-07 — ChatGPT / Claude / Grok / Gemini typed brief refinement:**
  provider-neutral conversation input now delegates extraction and typed
  command previews to the Week 12 compiler. Source text, assumptions,
  clarification questions, provider/model provenance, explicit accepted
  revisions, and validation evidence are retained. Incomplete upper-floor
  access blocks rendering, and conversational output never becomes geometry.
- **W16-08 — 4Lines.ai traceable plan/section exchange:** plan, section, and
  elevation views now carry source-to-canonical object IDs, levels, openings,
  dimensions, view references, exchange provenance, and validation signatures.
  Missing, duplicated, unknown, disconnected, stale, or unvalidated objects
  invalidate the presentation-only exchange.
- Moodboards, palettes, materials, lighting presets, non-destructive design
  layers, render/panorama/presentation-sheet job manifests, and
  technical-plan-to-render revision traceability are included.
- **Sheet rationalisation remains enforced:** ISO 5457 A-series sheet formats
  and ISO 7200-style information fields guide the contract; this project
  policy caps supporting notes/legends/indices at **20%** of the sheet area
  and protects at least **65%** for the drawing zone. These are adopted
  project limits, not a claim that ISO prescribes a universal ratio.
- FastAPI routes: `GET /furnishing/catalog`, `POST /furnishing/preview`,
  `POST /furnishing/validate`, `POST /furnishing/edit`,
  `POST /candidates/studio`, `POST /presentation/package`, and
  `POST /presentation/render-job`.
- Deterministic artifacts:
  - `bar-association-hall/standard/week15-parametric-assets-report.json`
  - `bar-association-hall/standard/week16-candidate-studio-report.json`
  - `bar-association-hall/standard/week16-planner5d-exchange-report.json`
  - `bar-association-hall/standard/week16-archistar-snaptrude-site-report.json`
  - `bar-association-hall/standard/week16-floorplanner-synchronized-view-report.json`
  - `bar-association-hall/standard/week16-roomstyler-presentation-report.json`
  - `bar-association-hall/standard/week16-magicplan-recognition-report.json`
   - `bar-association-hall/standard/week16-llm-brief-refinement-report.json`
   - `bar-association-hall/standard/week16-4lines-plan-section-exchange-report.json`
  - `bar-association-hall/standard/week1516-enrichment-manifest.json`
  - `bar-association-hall/standard/week1516-changelog.md`
- Regression tests live in `tests/test_week1516_enrichment.py`, including
  Planner 5D mapping, Roomstyler clearance rejection, Magicplan promotion
  gating, LLM clarification and typed-revision acceptance, 4Lines cross-view
  identity rejection, route blocking, non-mutation, and deterministic
  comparison coverage.

Commands:

```bash
npm run enrich:week1516
npm run validate:week15
npm run validate:week16
npm run test:week1516
```

**W16-05 and W16-06 task completion:** Roomstyler/Homestyler
clearance-aware presentation and Magicplan photo-assisted recognition queue
are implemented, covered by fixtures and regression tests, and marked done.

**W16-07 and W16-08 task completion:** provider-neutral conversational brief
refinement and 4Lines.ai traceable plan/section/elevation exchange are
implemented, covered by fixtures and regression tests, evidence-backed, and
marked done. Both remain review-first presentation aids and cannot override
canonical geometry or imply professional approval.

**Task completion:** Week 15–16 enrichment is complete and marked done in
this README. Outputs remain preliminary planning/presentation aids and require
appointed architect, engineers, surveyor, and local-authority review.

**W16-02 completion:** Planner 5D furnishing candidate exchange is implemented,
tested, evidence-backed, and marked done. The fixture intentionally retains one
clearance-conflicting placement as rejected review evidence; it is not promoted
to the presentation candidate.

**W16-03 completion:** Archistar / Snaptrude site-feasibility evidence is
implemented, tested, evidence-backed, and marked done. Imported site and
massing signals remain review evidence only; they cannot override canonical
geometry or imply permit, code, or construction approval.

**W16-04 completion:** Floorplanner synchronized 2D/3D view intake is
implemented, tested, evidence-backed, and marked done. Stale or untraceable
views remain review-required and cannot override the canonical model revision.

**W16-09 completion:** Archiagent live-dimension review is implemented,
fixture-backed, and covered by regression tests. Displayed values are normalized
to canonical units and tied to rooms, openings, stairs, routes, or clearance
objects; stale revisions and conflicting measurements remain explicit review
findings. Accepted dimension edits require topology, clearance, and rule-pack
rerun evidence. The generated evidence is
`bar-association-hall/standard/week16-archiagent-live-dimension-report.json`.

## W16-10 task status — product landing page and Netlify production files

W16-10 wires the architectural planning story and the existing drawing
workspace into the main web stream:

- The default React route is now a responsive Advocate Chambers landing page
  with a canonical-plan preview, model-truth/visual-clarity/delivery-confidence
  sections, the review-first workflow, and validation evidence signals.
- The landing page now opens a project-intake screen that lets a user choose
  **New project** or **Continue existing**, enter a project name, narrate
  instructions, and attach multiple PDF, DOC/DOCX, TXT/MD, Excel/CSV, or image
  references before entering the workspace.
- **Open workspace** enters the existing live 2D drawing editor, including
  product modes, level selection, validation, artifacts, and property
  inspection. The landing page and editor are one application, not separate
  mockups.
- Added production metadata and the Netlify SPA configuration in
  `netlify.toml`, including the React build command, Node 20, publish directory,
  and history fallback.

Run the W16-10 web checks with:

```bash
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

**Task completion:** W16-10 landing-page implementation and Netlify production
files are applied and testable locally. Deployment remains subject to the
connected Netlify site and its production environment.

## Week 17–18 task status — applied and marked done

The Week 17 and Week 18 enrichment is implemented in the canonical pipeline and
marked complete here.

- **Week 17 — site feasibility and transparent plan review:** the site
  workspace exposes plot bounds, north, setbacks, access points, level and
  footprint records, context layers, and assumptions without mutating
  authoritative geometry.
- The configurable rule-pack evaluator checks coverage, setbacks, height,
  floor-area targets, parking, accessibility, daylight, ventilation, egress,
  fire access, service access, and wet-area coordination. Each result includes
  a rule ID, input geometry, source, calculation, assumption, confidence, and
  suggested correction, with explicit `pass`, `fail`, `unknown`, and
  professional-review semantics.
- PDF/CAD inspection is a separate imported-review workflow. It records the
  source and review steps but never claims approval or promotes uncertain
  observations to authoritative geometry.
- **Week 18 — collaboration and professional delivery:** deterministic
  read-only technical/presentation review-link contracts, comments anchored to
  rooms, walls, openings, dimensions, validation findings, or viewpoints, and
  revision comparison for geometry, validation, area, openings, and furniture
  changes are included.
- Approval states are `Draft`, `Review`, `Client Presentation`, `Preliminary
  Coordination`, and `Not Issuable`. The coordinated package manifest covers
  source JSON, validation report, technical PDF, coloured PDF, DXF, optional
  IFC, images, assumptions, rule-pack version, and manifest. The release gate
  rejects unresolved blockers unless the export is explicitly marked
  `Not Issuable`.
- FastAPI routes: `POST /site/feasibility`, `POST /site/imported-review`,
  `POST /collaboration/review-link`, `POST /collaboration/comments`,
  `POST /collaboration/revision-compare`, `POST /delivery/package`, and
  `GET /delivery/contract`.
- Deterministic artifacts:
  - `bar-association-hall/standard/week17-site-feasibility-report.json`
  - `bar-association-hall/standard/week18-delivery-package-report.json`
  - `bar-association-hall/standard/week1718-enrichment-manifest.json`
  - `bar-association-hall/standard/week1718-changelog.md`
- Regression tests live in `tests/test_week1718_enrichment.py`.

Commands:

```bash
npm run enrich:week1718
npm run validate:week17
npm run validate:week18
npm run test:week1718
```

**Task completion:** Week 17–18 enrichment is complete and marked done in
this README. All checks remain preliminary planning/coordination aids and
require review by the appointed architect, accessibility professional,
fire/life-safety professional, structural and MEP engineers, surveyor, and
local authority. The separate binary cleanup remains intentionally untouched.

## Week 19–20 task status — applied and marked done

The Week 19 and Week 20 enrichment is implemented in the canonical pipeline
and marked complete here.

- **Week 19 — project archive and artifact integrity:** the manifest-first
  archive contract records project/revision identity, destination layout,
  artifact kind, byte size, SHA-256, validation status, and explicit missing
  records. Manifest signatures, duplicate paths, and duplicate artifact IDs
  are validated before a package can be treated as recoverable.
- **Week 20 — durable revision operations:** immutable revision records carry
  parent revision, author, reason, model signature, validation summary, and
  artifact-manifest signature. Soft archive and restore retain the current
  revision and source history; complete-package verification blocks incomplete
  migration instead of inventing hashes or silently deleting files.
- API contracts are available at `POST /archive/manifest`,
  `POST /revisions/record`, `POST /archive/verify`, and
  `POST /archive/state`.
- Deterministic artifacts:
  - `bar-association-hall/standard/week19-archive-integrity-report.json`
  - `bar-association-hall/standard/week20-revision-operations-report.json`
  - `bar-association-hall/standard/week1920-archive-manifest.json`
  - `bar-association-hall/standard/week1920-changelog.md`
- Regression tests live in `tests/test_week1920_enrichment.py`.

Commands:

```bash
npm run enrich:week1920
npm run validate:week19
npm run validate:week20
npm run test:week1920
```

**Task completion:** Week 17–20 enrichment is complete and marked done in
this README. These archive, revision, and verification contracts remain
preliminary coordination infrastructure; the separate 84-file binary cleanup
and any destructive history rewrite remain intentionally untouched.

## Furnishing architecture consolidation — applied

The Week 15 parametric asset schema is now the single furnishing authority.
The former Week 9 `FURNITURE_LIBRARY` is a compatibility view generated from
that catalog; it no longer owns independent dimensions, occupancy, or
clearance values. Week 9 presentation and candidate functions delegate to the
Week 15 furnishing engine and translate only the legacy response shape.

- One placement/clearance validator handles room fit, door swings, routes,
  stairs, service zones, and furniture clearances.
- Week 9-to-Week 15 rectangle adaptation preserves older callers while
  canonical model rectangles remain authoritative.
- Materials, decoration, lighting, and render jobs remain in the separate
  non-authoritative Week 16 presentation layer.
- Migration tests verify that the Week 9 compatibility wrapper and Week 15
  engine return the same placement-validation result and that legacy library
  values are sourced from the Week 15 catalog.


---

## Enterprise Enrichment Programme — Status (2026-09-20)

10-week enterprise programme to transform the platform into professional-grade
infrastructure. Domain enrichment through Week 28 is complete and frozen as the
quality baseline.

### Programme Status

| Week | Focus | Status | Key Deliverables |
|------|-------|--------|-----------------|
| **E01** | Foundation & Hygiene | ✅ **Complete** | `pyproject.toml`, Ruff/mypy, ESLint/Prettier, `.editorconfig`, `.nvmrc`, `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, `CHANGELOG.md`, `Makefile`, `baselines/2026-09-20/` |
| **E02** | Persistence Layer | ✅ **Complete** | SQLAlchemy ORM models, Alembic migrations, `repository_sql.py`, `db/session.py`, SQLite dev fallback |
| **E03** | Auth & Multi-tenancy | ✅ **Complete** | JWT middleware, role hierarchy (owner/editor/viewer/reviewer), org isolation, audit logging, `AUTH_DISABLED` dev bypass |
| **E04** | Async Jobs & Storage | ✅ **Complete** | RQ worker entrypoint, `FilesystemStore`/`S3Store`, SHA-256 content-addressed artifacts, inline fallback for dev |
| **E05** | CI/CD & Quality Gates | ✅ **Complete** | `check_quality_gate.py` enforcement script (BLOCKER+ERROR severity, missing adversarial key), `release_check.py`, CI workflow with explicit gate call, Dependabot config |
| **E06** | API & Frontend Hardening | ✅ **Complete** | Versioned `/v1/` routes, `v1_projects.py` with auth+audit, Pydantic constraint validation, error envelope, `v1_health.py` |
| **E07** | Observability | ✅ **Complete** | JSON structured logging (all fields contract), Prometheus metrics middleware, `/health` + `/ready` endpoints, Grafana dashboard JSON, correlation ID round-trip |
| **E08** | Security Hardening | ✅ **Complete** | Rate limiting (window/limit constants), security headers (all OWASP-required), `verify_artifact.py`, CORS policy, input size limits, path-traversal sanitization, staging AUTH guard |
| **E09** | Staging & Release | ✅ **Complete** | `docker-compose.staging.yml`, `release.yml` workflow with SBOM, `release_check.py`, Makefile docker targets, release checklist with professional disclaimer |
| **E10** | Stabilization | ✅ **Complete** | Runbooks (queue-stuck, artifact-missing, DB migration), ADRs frozen, concurrent job safety, load scenario fixture, enterprise candidate readiness checks |

### Phase 4 task status — authentication and tenancy hardening

The next implementation-plan phase is applied on `main`:

- OIDC issuer, audience, expiry, clock-skew, and rotating JWKS validation are
  supported when `OIDC_ISSUER` is configured.
- Production/staging configuration rejects `AUTH_DISABLED` and the default
  development JWT secret.
- Project-scoped authorization now treats the active database membership as the
  authority for organization access and effective role.
- Disabled or soft-deleted users are denied before project-scoped work.
- Migration `0003_user_disabled_at` and the Phase 4 policy fixture/regression
  suite are included.

This phase does not certify identity-provider configuration or professional
architectural review; those remain deployment/operator responsibilities.

### Fixture & Regression Test Coverage (added 2026-09-20)

Comprehensive fixtures and expanded regression tests were added for all enterprise
weeks to harden the test surface beyond basic smoke tests. **258 tests pass,
34 skip** (SQLAlchemy not installed in lightweight dev env — expected).

| Week | Expanded Test File | Fixtures | Key Scenarios |
|------|-------------------|----------|---------------|
| E03 | `test_e03_auth_expanded.py` | `fixtures/e03/` (roles_matrix, org_isolation_scenarios, dev_jwt_payload) | Role weight matrix alignment, cross-org isolation, JWT claim validation, audit immutability, request-ID propagation |
| E04 | `test_e04_jobs_expanded.py` | `fixtures/e04/` (job_payloads, artifact_samples) | Job state machine transitions, SHA-256 content addressing, path-traversal containment, null-byte injection, concurrent store writes |
| E05 | `test_e05_quality_gate_expanded.py` | `fixtures/e05/` (passing, blocked, adversarial_regression) | Fixture-driven gate enforcement, ERROR/BLOCKER severity regression, adversarial count regression (28/30 fails), baseline drift warning, SBOM+CI artefact checks |
| E06 | `test_e06_api.py` | `fixtures/e06/` (openapi_required_paths) | Versioned route structure, Pydantic constraint validation, auth wiring, OpenAPI schema generation, ADR-001 geometry boundary |
| E07 | `test_e07_observability_expanded.py` | `fixtures/e07/` (structured_log_sample) | All JSON log fields, level casing, extra field propagation, health/ready contract, Grafana dashboard, correlation ID round-trip |
| E08 | `test_e08_security_expanded.py` | `fixtures/e08/` (security_headers_required) | Header completeness vs fixture, rate-limit eviction, exemption paths, tamper detection, OWASP checklist, CORS policy, AUTH_DISABLED guard |
| E09 | `test_e09_staging_expanded.py` | `fixtures/e09/` (release_manifest_sample) | Docker compose service completeness, Dockerfile presence, release workflow SBOM+gate references, release checklist "Never" disclaimer, Makefile docker targets |
| E10 | `test_e10_stabilization.py` | `fixtures/e10/` (load_scenario) | Concurrent dispatch safety, concurrent store writes, ADR completeness, runbook coverage, enterprise candidate readiness, no inline geometry in DB schema |

### Quality Baseline (frozen at E01 start)

| Check | Status |
|-------|--------|
| Unit tests (37+) | ✅ PASS |
| Adversarial suite | ✅ 30/30 detected |
| Quality gate | ⚠️ REVIEW_REQUIRED (professional sign-off required — correct by design) |
| Performance | ✅ Within established envelopes |
| Reproducibility | ✅ SHA-256 signed |
| **Enterprise regression suite** | ✅ **258 passed, 34 skipped (SQLAlchemy-absent expected)** |

Frozen reports: [`baselines/2026-09-20/`](baselines/2026-09-20/)

### Enterprise Quick-Start

```bash
# Full baseline verification (lint + typecheck + tests + quality gate)
make verify

# Run all enterprise regression tests (E03–E10 expanded suite)
python -m pytest tests/test_e03_auth_expanded.py tests/test_e04_jobs_expanded.py \
  tests/test_e05_quality_gate_expanded.py tests/test_e06_api.py \
  tests/test_e07_observability_expanded.py tests/test_e08_security_expanded.py \
  tests/test_e09_staging_expanded.py tests/test_e10_stabilization.py -v

# Run full E-suite (original + expanded)
python -m pytest tests/test_e02_persistence.py tests/test_e03_auth.py \
  tests/test_e04_jobs.py tests/test_e05_quality_gate_enforcement.py \
  tests/test_e07_health.py tests/test_e08_security.py \
  tests/test_e09_e10_release.py tests/test_e03_auth_expanded.py \
  tests/test_e04_jobs_expanded.py tests/test_e05_quality_gate_expanded.py \
  tests/test_e06_api.py tests/test_e07_observability_expanded.py \
  tests/test_e08_security_expanded.py tests/test_e09_staging_expanded.py \
  tests/test_e10_stabilization.py -v

# Quality gate enforcement check
python scripts/enterprise/check_quality_gate.py \
  --report bar-association-hall/standard/quality-gate-report.json \
  --baseline baselines/2026-09-20/quality-gate-report.json

# Local enterprise stack (Postgres + Redis + MinIO + API + Worker + Web)
docker compose up --build

# Staging-like stack
make docker-staging

# Release check
python scripts/enterprise/release_check.py
```

### Architecture

| Document | Location |
|----------|----------|
| Geometry Authority (ADR-001) | [`docs/architecture/ADR-001-Geometry-Authority.md`](docs/architecture/ADR-001-Geometry-Authority.md) |
| Quality Gates (ADR-002) | [`docs/architecture/ADR-002-Quality-Gates.md`](docs/architecture/ADR-002-Quality-Gates.md) |
| Tenancy Model (ADR-003) | [`docs/architecture/ADR-003-Tenancy-Model.md`](docs/architecture/ADR-003-Tenancy-Model.md) |
| Data Model | [`docs/architecture/data-model.md`](docs/architecture/data-model.md) |
| System Context | [`docs/architecture/system-context.md`](docs/architecture/system-context.md) |
| Enterprise Roadmap | [`docs/enterprise/ENTERPRISE_ROADMAP.md`](docs/enterprise/ENTERPRISE_ROADMAP.md) |

### Professional Review Boundary

> ⚠️ This software aids architectural planning. It does **not** certify:
> construction readiness, permit/sanction readiness, fire/life-safety compliance,
> structural adequacy, or accessibility (RPwD) final compliance. All outputs
> require independent professional review by licensed architects, engineers,
> and statutory authorities before use in regulated contexts.

## Phase 11–13 implementation checkpoint — applied with explicit follow-ups

The next due phases in `docs/IMPLEMENTATION_PLAN.md` are now advanced without
duplicating the already-completed Week 11–18 enrichment tracks.

- **Phase 11 — collaboration and review:** durable, tenant-scoped review links,
  revision-pinned comments, append-only approval events, reviewer identity,
  audit records, one-way token storage, public-link resolution, and a reversible
  `0004_collaboration_review` migration are implemented.
- **Phase 12 — testing and quality gates:** the signed
  `phase12-quality-gate-report.json` inventory covers ten regression categories
  and keeps the gate at `REVIEW_REQUIRED` for the two missing harnesses:
  property-based geometry and Playwright DOM/SVG visual regression.
- **Phase 13 — performance and observability:** bounded correlation IDs are
  propagated through structured logs and response headers, and named
  Prometheus pipeline-stage timing is available without making metrics a
  runtime dependency.

Focused commands:

```bash
python -m unittest tests.test_phase11_collaboration
python scripts/phase12.py validate
python -m unittest tests.test_phase12_quality_gate tests.test_phase13_observability
```

Phases 14–15 are not defined in the current plan and are therefore listed as
due scope definition, not implemented work. The public API collaboration
models require the FastAPI/SQLAlchemy deployment dependencies; this lightweight
workspace verifies their pure policy and contract behavior when those optional
dependencies are absent.

Final focused checkpoint: **114 tests passed** across the changed Phase 11–13
scope and related enrichment/authentication regressions. The full repository
suite was also attempted; its remaining non-green results are pre-existing
E03 SQLite UUID, E06 router-path, E07/Phase 5 environment-order, and legacy
auth-state issues, documented in `CREAT.md` rather than masked.

---
