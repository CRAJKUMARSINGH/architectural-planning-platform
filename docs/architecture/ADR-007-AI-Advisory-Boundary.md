# ADR-007 — AI Outputs Are Advisory Only

**Status:** Accepted  
**Date:** 2026-10-16  
**Deciders:** Platform + Domain leads  
**Covers:** Phases 14–17 (AI Brief Analysis, Concept Canvas, Version Scoring, Proactive Suggestions)

## Context

Phases 14–17 introduced Gemini-powered brief analysis, version scoring, and proactive
suggestions, plus a heuristic fallback engine. These AI outputs are consumed by the React
editor and surfaced to architects. There is a risk that AI-generated content could be
mistaken for authoritative geometry findings or used to bypass the quality gate.

## Decision

1. **All AI outputs are advisory.** Brief analysis, version scores, and suggestions are
   informational aids. They do not constitute findings in the quality-gate sense.

2. **AI outputs must never mutate canonical geometry.** The `promote-to-model` workflow
   requires an explicit architect confirmation and produces a Job that goes through the
   full Python validation pipeline before any revision is created.

3. **Schema validation at the boundary.** Every AI response is parsed and validated against
   the declared schema before it is persisted or surfaced in the UI. Malformed AI responses
   are logged and returned as parse-failure stubs — they do not propagate raw LLM text.

4. **Provenance always recorded.** Every AI result carries:
   - `model_version` (e.g. `gemini-2.5-flash`)
   - `timestamp`
   - `fallback: true/false` — whether the heuristic engine was used
   - `engine` — `gemini` or `heuristic-v1`

5. **Heuristic fallback for reliability.** `generate_suggestions()` degrades gracefully to
   `HeuristicSuggestionEngine` when the Gemini SDK is absent or the API key is not set.
   No endpoint returns 503 due to missing AI credentials.

6. **No AI certification claims.** API responses and UI copy must never claim that
   AI-generated content represents code compliance, construction readiness, structural
   adequacy, fire safety, or accessibility certification.

7. **`GEMINI_API_KEY` never committed or logged.** It must be supplied via environment
   secret. The AI service initialises with `self.api_key = os.environ.get("GEMINI_API_KEY")`
   and never prints the value.

## Consequences

**Positive**
- Architects benefit from AI suggestions without the platform overstating their authority
- Graceful degradation means all functionality works without an API key
- Clear provenance trail for any AI-assisted decision

**Negative**
- More explicit UX copy required ("AI advisory — requires architect review")
- Parse-failure stubs require frontend handling

## Compliance / Enforcement

- The `presentationOnly` and `fallback` provenance keys are required on all AI result schemas.
- Any PR that removes the heuristic fallback or allows AI output to skip Python validation
  is a violation of ADR-001 and this ADR.
- API responses must include a disclaimer in the `provenance` object that AI outputs do not
  constitute a quality-gate finding.
- The professional-review checklist (`docs/enterprise/checklists/professional-review.md`)
  applies to all AI-generated content.

## Related

- `ADR-001-Geometry-Authority.md` — Python remains geometry authority
- `ADR-002-Quality-Gates.md` — conservative quality gates
- `services/ai/ai_service.py` — implementation
- `docs/enterprise/checklists/professional-review.md`
