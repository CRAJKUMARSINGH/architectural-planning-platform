# Architectural Planning Platform — Phase 16B + Phase 17 Product Requirements

## Overview
- **Summary**: Complete Phase 16B (AI Version Scoring DB Integration) and implement Phase 17 (Proactive Suggestions). Finish the skipped `score-revision` endpoint test, fix the Depends anti-pattern, add heuristic suggestion fallback, build the SuggestionsPanel frontend, add persistence for suggestion records, wire both tracks into the quality gate, and build comprehensive regression/fixture tests.
- **Purpose**: Deliver the two next-due phases per docs/IMPLEMENTATION_PLAN.md and README.md. Mark Phase 16 ✅ and Phase 17 ✅.
- **Target Users**: Reviewers using VersionScoringPanel + editors viewing Proactive Suggestions; CI consuming the quality-gate aiScoring and suggestionsCoverage tracks.

## Goals
- Unskip and pass the previously skipped Phase 16B scoring endpoint tests
- Properly use FastAPI `Depends(get_session)` for DB connections in AI routes (no manual `next()`)
- Add round-trip ScoringResult persistence tests (create → commit → fetch → verify)
- Add `/compare-versions` API contract test with fixture JSON
- Implement a deterministic HeuristicSuggestionEngine fallback when Gemini is unavailable
- Build `SuggestionsPanel.tsx` React component mirroring VersionScoringPanel architecture
- Add `SuggestionRecord` ORM model + Alembic migration (0006)
- Persist generated suggestions in the scoring route
- Wire `aiScoring` and `suggestionsCoverage` tracks into scripts/quality_gate.py
- Create regression fixture JSONs in tests/fixtures/ for both phases
- Add 100% test coverage of new code with no skipped tests

## Non-Goals
- No changes to Python geometry authority (walls, openings, stairs)
- No Phase 18 Client Presentation workflow (next due after 16B+17)
- No Postgres production deployment (SQLite in-memory testing as per project convention)
- No changes to existing adversarial/weekly-enrichment tests (they must remain green)
- No new AI model versions or Gemini SDK upgrades
- No external SaaS suggestion integrations

## Background & Context
The README currently marks:
- Phase 16 "AI Version Scoring & Tradeoffs" → 📋 Next
- Phase 17 "Proactive Suggestions" → 📋 Planned
- Phase 18 "Client Presentation & Export Workflow" → 📋 Planned

The current partial state:
- Phase 16A files exist: `scripts/phase16_ai_scoring.py`, `services/api/routes/v1_ai.py`, `ScoringResult` ORM, `VersionScoringPanel.tsx`
- One test is SKIPPED (`test_score_revision_endpoint_exists`) with message "score-revision endpoint and get_session not yet implemented" — but the code DOES exist in v1_ai.py (it uses an anti-pattern and lacks tests)
- Phase 17 has `AIService.generate_suggestions()` + route but no frontend, no heuristic fallback, no persistence, no quality gate integration, no tests

Constraints from prior work (project_memory.md):
- SQLite tests MUST use `StaticPool` (services/api/db/session.py)
- `reset_session_singletons()` MUST be called to prevent cross-test engine leakage
- No `os.environ.setdefault` for test config — use explicit snapshot/restore

## Functional Requirements

- **FR-1**: Score Revision endpoint must be accessible via correct path with proper Depends injection
- **FR-2**: ScoringResult creation must persist to DB and be retrievable by revision_id
- **FR-3**: `/compare-versions` endpoint accepts version list + brief and returns tradeoff matrix
- **FR-4**: AIService suggestion generation has a deterministic heuristic fallback when Gemini unavailable
- **FR-5**: Suggestion records have an ORM model + migration with unique(project_id, category, suggestion_hash)
- **FR-6**: `/generate-suggestions` route persists suggestions and returns deduped results
- **FR-7**: Frontend `SuggestionsPanel.tsx` exposes: category tabs, priority chips, provenance badge
- **FR-8**: quality_gate.py exposes `aiScoring` and `suggestionsCoverage` tracks with proper schema versions
- **FR-9**: All Phase 16A previously-skilled tests run without skip decorators and pass
- **FR-10**: Regression fixture JSONs exist in tests/fixtures/phase16 and phase17

## Non-Functional Requirements

- **NFR-1**: No existing test regressions — full pytest suite must remain green
- **NFR-2**: TypeScript strict mode passes (no TS errors) for SuggestionsPanel
- **NFR-3**: Heuristic scorer must be fully deterministic (same input → same output, no randomness)
- **NFR-4**: All ORM sessions use `Depends(get_session)` in routes; manual `next(get_session())` is removed
- **NFR-5**: Alembic migration downgrade function is implemented and reversibletest

## Constraints

- **Technical**:
  - SQLite in-memory with StaticPool for all tests (per project_memory.md hard constraint)
  - FastAPI TestClient with dependency_overrides cleared between tests
  - SQLAlchemy ORM models must match docs/architecture/data-model.md naming conventions
  - Pydantic v2 for API contracts
  - React 19.3 + TypeScript strict (no JS)
- **Business**:
  - Geometry authority remains in Python only (ADR-001) — suggestions are advisory only
  - Missing evidence never becomes PASS (ADR-002) — suggestions track default is INCOMPLETE when no data
  - Professional review boundary is visible in UI copy (no "approved" / "certified" language)
- **Dependencies**:
  - Existing services/api/db/session.py with lazy engine + reset_session_singletons()
  - Existing services/ai/ai_service.py dataclasses
  - Existing scripts/quality_gate.py build_quality_gate() signature
  - Existing services/api/models/orm.py ScoringResult model

## Assumptions

- Test auth bypass via `dependency_overrides` for `get_current_user` and `require_project_viewer` is acceptable
- Suggestion hashing is SHA-256 of (category + normalized text) for deduplication
- Heuristic suggestion engine uses the same zone-area/budget/daylight feature set as HeuristicScorer
- Frontend SuggestionsPanel is mounted in App.tsx as an optional panel when Phase 17 is enabled
- Alembic migration 0006 will be manually reversible; SQLite-specific restrictions are acceptable

## Acceptance Criteria

### AC-1: No skipped tests in Phase 16 suite
- **Type**: `rule`
- **Given**: Current test_phase16a_version_scoring.py has 1 skipped test
- **When**: `python -m pytest tests/test_phase16a_version_scoring.py tests/test_phase16_ai_scoring.py -v` runs
- **Then**: All tests pass (0 skipped)
- **Pass Condition**: pytest output shows "0 skipped" and exit code 0
- **Evidence**: CI pytest run capture

### AC-2: Score Revision endpoint uses Depends(get_session) correctly
- **Type**: `rule`
- **Given**: Current score_revision uses `next(get_session())` anti-pattern
- **When**: Inspecting v1_ai.py route signature
- **Then**: The route has `db: Session = Depends(get_session)` as a parameter and manual `next()` is removed
- **Pass Condition**: No occurrence of `next(get_session())` in routes; signature follows FastAPI Depends pattern
- **Evidence**: Static code inspection + passing integration test

### AC-3: ScoringResult round-trip persistence via endpoint
- **Type**: `rule`
- **Given**: A test creates a Project + Revision in the DB
- **When**: POST `/api/ai/score-revision/{project_id}` is called with that revision_id
- **Then**: A ScoringResult row is created with correct foreign keys; subsequent GET / fetch by revision_id returns the same scores
- **Pass Condition**: End-to-end test creates project/revision/scoring and verifies persisted values match
- **Evidence**: DB integration test in test_phase16a_version_scoring.py

### AC-4: Compare-versions API contract test
- **Type**: `rule`
- **Given**: A fixture JSON with 2 versions + brief
- **When**: POST `/api/ai/compare-versions` is called with fixture data
- **Then**: Returns schema_version, winner, tradeoff_notes, matrix (length=2), quality_gate_track keys
- **Pass Condition**: Response matches all required keys; winner ID matches the version with higher heuristic score
- **Evidence**: API contract test + fixture file under tests/fixtures/phase16/

### AC-5: Heuristic suggestion fallback exists and is deterministic
- **Type**: `rule`
- **Given**: GEMINI_API_KEY not set / SDK not importable
- **When**: HeuristicSuggestionEngine.generate(project, categories) called twice with same inputs
- **Then**: Returns identical list of SuggestionResult objects with at least 1 suggestion per requested category
- **Pass Condition**: result1 == result2 (deep equality) when inputs identical
- **Evidence**: Unit test in new test_phase17_suggestions.py

### AC-6: SuggestionRecord ORM + migration exists
- **Type**: `rule`
- **Given**: services/api/db/migrations/versions/ has current latest 0005_scoring_results.py
- **When**: Listing migrations directory + importing ORM
- **Then**: 0006_suggestion_records.py exists with upgrade + downgrade; orm.py exports SuggestionRecord with id, project_id, category, suggestion_hash, text, priority, provenance, created_by_user_id, created_at
- **Pass Condition**: `alembic upgrade head` succeeds; `alembic downgrade -1` succeeds; class import succeeds
- **Evidence**: Migration file exists + ORM import + test run with upgrade/downgrade

### AC-7: Generate-suggestions endpoint persists and dedupes
- **Type**: `rule`
- **Given**: 2 identical POST `/api/ai/generate-suggestions` requests
- **When**: Both requests are processed
- **Then**: Only 1 SuggestionRecord per unique hash is created; second response returns same count
- **Pass Condition**: DB count of suggestion records equals unique hashes; response size matches
- **Evidence**: Integration test in test_phase17_suggestions.py

### AC-8: SuggestionsPanel.tsx frontend component
- **Type**: `rule`
- **Given**: App.tsx render tree
- **When**: VersionScoringPanel renders
- **Then**: Adjacent SuggestionsPanel is importable, renders category tabs, displays priority chips, has a "Generate" button, and fires POST /generate-suggestions (mocked in test)
- **Pass Condition**: SuggestionsPanel.test.tsx mounts without error; category tabs are visible; mocked fetch is called on button click
- **Evidence**: Jest/Vitest snapshot + interaction test pass

### AC-9: Quality gate includes aiScoring + suggestionsCoverage tracks
- **Type**: `rule`
- **Given**: build_quality_gate() called with default inputs
- **When**: Inspecting output dict keys
- **Then**: `aiScoring` track (status + schemaVersion + bestVersionId + bestOverallScore + versionsEvaluated) AND `suggestionsCoverage` track (status + schemaVersion + categoriesCovered + suggestionCount + missingEvidence) are present
- **Pass Condition**: Output dict contains both keys with required sub-keys
- **Evidence**: Unit test in tests/test_quality_gate.py verifying new tracks

### AC-10: Regression fixtures present for both phases
- **Type**: `rule`
- **Given**: tests/fixtures/ directory
- **When**: Listing phase16 and phase17 subdirectories
- **Then**: phase16/compare-versions-sample.json; phase17/suggestions-sample.json both exist and are valid JSON
- **Pass Condition**: Files exist; `json.load()` succeeds; required top-level keys present per schema
- **Evidence**: File existence + schema validation test

### AC-11: Code quality and regression safety
- **Type**: `rubric`
- **Dimension**: Regression safety and fidelity to project conventions
- **Scale**: 0-2
- **Anchors**: 0 = >5 existing tests break; 1 = 0-4 test breaks or minor convention deviation; 2 = All existing tests green; follows StaticPool + reset_session_singletons + snapshot env pattern; no lambda closures in overrides; code style matches neighbors
- **Pass Threshold**: >= 2
- **Evidence**: Full `python -m pytest tests/ -q` exit code 0; manual code review

## Open Questions
- None. All scope is bounded by the IMPLEMENTATION_PLAN.md phases 16+17 deliverables.
