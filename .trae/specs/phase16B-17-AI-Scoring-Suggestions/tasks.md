# Architectural Planning Platform — Phase 16B + Phase 17 Implementation Tasks

## Task 1: Fix score_revision Depends anti-pattern + unskip test in Phase 16A
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None (first task in the dependency chain)
- **Description**:
  - Change `score_revision()` signature in `services/api/routes/v1_ai.py` to use `db: Session = Depends(get_session)`
  - Remove `next(get_session())` manual call + manual close/rollback pattern
  - Remove the `@unittest.skip` decorator on `test_score_revision_endpoint_exists`
  - Add proper `dependency_overrides` for `get_current_user` + `require_project_viewer` in test
  - Update CHAT_GIST.md with 5-minute tick
- **Acceptance Criteria Addressed**: AC-1, AC-2
- **Test Requirements**:
  - `rule` TR-1.1: `grep -c "next(get_session())" services/api/routes/v1_ai.py` returns 0
  - `rule` TR-1.2: `python -m pytest tests/test_phase16a_version_scoring.py -v` shows 0 skipped
- **Notes**: Must follow StaticPool + reset_session_singletons pattern per project_memory

## Task 2: Add ScoringResult round-trip DB integration test
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - Add a new test class `TestScoringEndpointIntegration` in test_phase16a_version_scoring.py
  - Seed SQLite-in-memory DB with Organization → User → Membership → Project → Revision
  - Call POST /api/ai/score-revision/{project_id} via TestClient with dependency overrides
  - Assert ScoringResult is persisted with correct FKs
  - Fetch the stored ScoringResult via ORM and verify all score fields match
  - Add tests for idempotency (second call returns existing scoring row)
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `rule` TR-2.1: New test `test_score_revision_persists_result` passes
  - `rule` TR-2.2: New test `test_score_revision_idempotent_second_call` passes
  - `rule` TR-2.3: Test uses `reset_session_singletons()` in setUp / tearDown

## Task 3: Add /compare-versions API contract test + regression fixture
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - Create `tests/fixtures/phase16/compare-versions-sample.json` with 2 versions + brief program
  - Add `TestCompareVersionsAPI` class in test_phase16_ai_scoring.py (or new file)
  - POST to `/api/ai/compare-versions` with mocked auth, verify response schema
  - Assert winner matches the higher heuristic score
  - Assert `quality_gate_track` dict has PASS status when versions score >= 60
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-4, AC-10
- **Test Requirements**:
  - `rule` TR-3.1: Fixture file loads as valid JSON with versions (length 2) and brief keys
  - `rule` TR-3.2: `test_compare_versions_api_response_schema` passes
  - `rule` TR-3.3: `test_compare_versions_winner_selection` passes

## Task 4: Implement HeuristicSuggestionEngine deterministic fallback
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None (parallelizable with Task 2/3)
- **Description**:
  - Create a new module `scripts/phase17_suggestions.py` mirroring phase16 architecture
  - Implement `HeuristicSuggestionEngine` class with:
    - analyze_zone_areas(program, zones) → program-mismatch suggestions
    - analyze_daylight(zones) → daylight-poor suggestions
    - analyze_budget(cost, max_budget) → cost-overrun suggestions
    - analyze_circulation(zones, total_area) → corridor / circulation suggestions
    - generate(project_data, categories) → SuggestionResult dataclass with provenance
  - Suggestion hashing utility: SHA-256 of (category + normalized lowercased text)
  - Update `AIService.generate_suggestions()` to use HeuristicSuggestionEngine fallback when Gemini unavailable
  - Create `tests/fixtures/phase17/suggestions-sample.json` fixture
  - Add `tests/test_phase17_suggestions.py` with deterministic unit tests
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-5, AC-10
- **Test Requirements**:
  - `rule` TR-4.1: `test_heuristic_suggestions_deterministic` — 2 calls deep-equal
  - `rule` TR-4.2: `test_suggestion_hashing_stable` — same input → same hash
  - `rule` TR-4.3: `test_each_category_produces_at_least_one_suggestion` for standard categories
  - `rule` TR-4.4: Fixture file phase17/suggestions-sample.json is valid JSON

## Task 5: SuggestionRecord ORM model + Alembic migration 0006
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None (parallelizable)
- **Description**:
  - Add `SuggestionRecord` class to `services/api/models/orm.py` with:
    id, project_id (FK), category, suggestion_hash (unique within project+category+hash), text, priority, provenance JSON, created_by_user_id FK, created_at
  - Add UniqueConstraint on (project_id, suggestion_hash) for dedupe
  - Add CheckConstraint for priority in ('low','medium','high','critical')
  - Create migration `services/api/db/migrations/versions/0006_suggestion_records.py` with upgrade + downgrade
  - Add model __init__ export in `services/api/models/__init__.py`
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `rule` TR-5.1: Migration upgrade succeeds against SQLite
  - `rule` TR-5.2: Migration downgrade succeeds and drops the table
  - `rule` TR-5.3: ORM import works + SuggestionRecord(**kwargs) creates a valid instance

## Task 6: Wire /generate-suggestions endpoint persistence + dedupe
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 4, Task 5
- **Description**:
  - Modify `/generate-suggestions` route in v1_ai.py to:
    - Accept db: Session via Depends(get_session)
    - Run heuristic fallback when AI unavailable
    - Compute suggestion_hash per result
    - INSERT SuggestionRecord rows with ignore-on-conflict for existing hashes
    - Audit event creation (optional but per tenancy model)
  - Add integration tests in test_phase17_suggestions.py:
    - test_suggestions_endpoint_persists
    - test_suggestions_endpoint_dedupes_identical
    - test_suggestions_endpoint_fallback_when_ai_unavailable
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `rule` TR-6.1: `test_suggestions_endpoint_persists` passes (DB count > 0 after call)
  - `rule` TR-6.2: `test_suggestions_endpoint_dedupes` passes (second call doesn't increase count by same number as first)
  - `rule` TR-6.3: `test_suggestions_endpoint_fallback` passes with mocked unavailability

## Task 7: Build SuggestionsPanel.tsx frontend component + test
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 4 (defines suggestion dataclass shape)
- **Description**:
  - Create `apps/web/src/components/SuggestionsPanel.tsx` mirroring VersionScoringPanel
  - Interface types: `SuggestionItem { id, category, text, priority, provenance }`
  - UI: Header, category tab chips (all/program/site/daylight/budget/circulation), suggestion cards with priority color chips, "Generate Suggestions" CTA button
  - useMutation + fetch to POST /api/ai/generate-suggestions
  - Display provenance (heuristic vs gemini badge) per suggestion
  - Add professional-review copy disclaimer ("Suggestions are advisory — not authoritative geometry")
  - Create `apps/web/src/components/__tests__/SuggestionsPanel.test.tsx` with:
    - Mount test (no crash)
    - Generate button click triggers fetch (mocked)
    - Category tab filtering works
  - (Optional but recommended) Import SuggestionsPanel in App.tsx in the right panel
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `rule` TR-7.1: SuggestionsPanel.test.tsx passes all assertions
  - `rule` TR-7.2: `cd apps/web && npm run typecheck` passes (0 TS errors)
  - `rubric` TR-7.3: UI consistency with VersionScoringPanel; scale 1-3; anchors 1=inconsistent style, 2=similar structure minor gaps, 3=identical structure, spacing, typography, color palette; threshold >= 2; evidence: visual diff of components side-by-side

## Task 8: Wire aiScoring + suggestionsCoverage into quality_gate.py
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 3 (scoring track), Task 4 (suggestions track)
- **Description**:
  - Modify `scripts/quality_gate.py` build_quality_gate() function:
    - Import VersionScoringEngine (phase16) and HeuristicSuggestionEngine (phase17)
    - Build `aiScoring` track using existing heuristic method if project data present; default INCOMPLETE (missingEvidence=True) otherwise
    - Build `suggestionsCoverage` track: status (PASS if suggestions_count >= categories_requested * 0.8 else REVIEW_REQUIRED), schemaVersion, categoriesCovered, suggestionCount, missingEvidence bool
  - Add 2 tests to tests/test_quality_gate.py:
    - test_quality_gate_ai_scoring_track_present
    - test_quality_gate_suggestions_coverage_present
  - Update CHAT_GIST.md
- **Acceptance Criteria Addressed**: AC-9
- **Test Requirements**:
  - `rule` TR-8.1: `test_quality_gate_ai_scoring_track_present` passes (keys: status, schemaVersion, bestVersionId, bestOverallScore, versionsEvaluated)
  - `rule` TR-8.2: `test_quality_gate_suggestions_coverage_present` passes (keys: status, schemaVersion, categoriesCovered, suggestionCount, missingEvidence)
  - `rule` TR-8.3: Empty-input default has status=INCOMPLETE and missingEvidence=True for both tracks

## Task 9: Full regression suite green + README update + CHAT_GIST finalize
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Tasks 1-8 (all)
- **Description**:
  - Run `python -m pytest tests/ -q` — ensure 0 failures
  - Run `cd apps/web && npm run typecheck` — ensure 0 TS errors
  - Update README.md status table: Phase 16 → ✅ Done; Phase 17 → ✅ Done; Phase 18 → 📋 Next
  - Add a short Phase 16/17 summary section in README below the Phase 14 section
  - Update CHAT_GIST.md with final checklist marks + commit log
  - Ensure docs/enterprise/checklists/professional-review.md "never claim" items are referenced in the new SuggestionsPanel disclaimer copy
- **Acceptance Criteria Addressed**: AC-11 (rubric), AC-1 through AC-10 (all evidence collected)
- **Test Requirements**:
  - `rule` TR-9.1: Full pytest suite passes 0 failures
  - `rule` TR-9.2: TypeScript typecheck passes 0 errors
  - `rule` TR-9.3: README status table updated correctly
  - `rubric` TR-9.4: Regression safety dimension (AC-11 scale 0-2); evidence: full suite run output; threshold >= 2
  - `rubric` TR-9.5: Conventions fidelity (StaticPool, no lambda closures, no setdefault env); scale 0-2; threshold >= 2; evidence: code review of all changed files
- **Notes**: This is the final task before 50%, 100%, green-test milestone commits + push
