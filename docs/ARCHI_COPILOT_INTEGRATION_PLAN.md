# Archi-Copilot Integration Action Plan

## Executive Summary

Integrate all Archi-Copilot AI-native features into Advocate-Chambers with an AI-enhanced editing approach that maintains the geometry-authority principle through proper validation and provenance tracking.

## Strategic Alignment

**Core Principle:** Python remains the sole authority for canonical geometry, but AI can suggest and directly modify geometry when changes pass through the complete validation pipeline with proper provenance tracking.

**Integration Philosophy:** AI features as an enhancement layer over the existing Phase 0-13 foundation, not a replacement for the canonical geometry engine.

## Feature Integration Map

### 1. AI Brief Analysis → Enhanced Week 11-12 Brief Compiler

**Current State:** Week 11-12 has a brief compiler that extracts facts and marks topology gaps.

**Archi-Copilot Enhancement:**
- Replace/enhance current brief compiler with Gemini API integration
- Add structured space program generation (room-by-room with priority and notes)
- Add site/brief constraint analysis
- Add design opportunity identification
- Add open question generation for client clarification

**Integration Points:**
- Extend `scripts/week1112.py` with AI analysis functions
- Add new AI brief analysis schema to `packages/schema/`
- Integrate with existing Week 11-12 enrichment pipeline
- Maintain existing validation and quality gate contracts

### 2. Concept Canvas → Enhanced Phase 7 Frontend Commands

**Current State:** Phase 7 has React command dispatch with typed commands for geometry editing.

**Archi-Copilot Enhancement:**
- Add interactive 2D massing/bubble diagram canvas
- Implement draggable, resizable zone blocks (Living, Sleeping, Service, Circulation, Outdoor, Work, Other)
- Add multi-floor support with floor tabs
- Add snapping and alignment guides
- Add site boundary and north arrow overlay
- Support real floor-plan import as background layer

**Integration Points:**
- Extend existing `apps/web/src/components/Viewport2D.tsx` with canvas capabilities
- Add new canvas command types to `packages/geometry/commands.py`
- Implement canvas-to-canonical-geometry conversion pipeline
- Maintain existing typed command execution through Python
- Add canvas-specific validation rules

### 3. AI Version Scoring → Enhanced Phase 12 Quality Gates

**Current State:** Phase 12 has quality gates with property-based geometry tests and adversarial fixtures.

**Archi-Copilot Enhancement:**
- Add AI-powered version scoring against briefs
- Implement overall, program-fit, daylight, and budget-fit scores (0-100)
- Add written commentary calling out specific zones
- Integrate with existing quality gate framework
- Add version comparison and tradeoff analysis

**Integration Points:**
- Extend `scripts/quality_gate.py` with AI scoring functions
- Add AI scoring schema to `packages/schema/`
- Integrate with existing Week 21-27 validation program
- Maintain existing adversarial test suite
- Add AI-scored quality gate evidence

### 4. Proactive Suggestions → Enhanced Week 16 AI Tool Inputs

**Current State:** Week 16 accepts external AI tool inputs with review boundaries.

**Archi-Copilot Enhancement:**
- Add proactive AI suggestion generation
- Implement categorized suggestions (program, site, daylight, budget, circulation, general)
- Add suggestion acceptance/dismissal tracking
- Integrate with existing Week 16 external tool pipeline
- Add suggestion history and archive view

**Integration Points:**
- Extend `scripts/week16_ai_tool_inputs.py` with suggestion generation
- Add suggestion schema to `packages/schema/`
- Integrate with existing Week 16 review-first input contract
- Maintain existing geometry-authority boundaries
- Add suggestion provenance tracking

## Architecture Enhancements

### New Schema Contracts

```json
{
  "ai_brief_analysis": {
    "version": "ai-brief-analysis.v1",
    "spaceProgram": [{"name": "...", "sqm": "...", "priority": "...", "notes": "..."}],
    "constraints": [...],
    "opportunities": [...],
    "openQuestions": [...]
  },
  "canvas_zones": {
    "version": "canvas-zones.v1",
    "zones": [{"id": "...", "type": "...", "floor": "...", "geometry": "..."}],
    "snapGuides": [...],
    "siteBoundary": {...}
  },
  "ai_version_score": {
    "version": "ai-version-score.v1",
    "overall": 85,
    "programFit": 90,
    "daylight": 75,
    "budgetFit": 80,
    "commentary": "...",
    "zoneScores": [...]
  },
  "ai_suggestions": {
    "version": "ai-suggestions.v1",
    "suggestions": [{"category": "...", "text": "...", "accepted": false}],
    "categories": ["program", "site", "daylight", "budget", "circulation", "general"]
  }
}
```

### Enhanced Command Types

```python
# New canvas commands
class CreateCanvasZone(TypedCommand):
    zone_type: str  # Living, Sleeping, Service, etc.
    floor: str
    geometry: dict

class ResizeCanvasZone(TypedCommand):
    zone_id: str
    new_geometry: dict

class ApplyAISuggestion(TypedCommand):
    suggestion_id: str
    target_zone_id: str | None
    parameters: dict

class ScoreCanvasVersion(TypedCommand):
    version_id: str
    brief_analysis_id: str
    scoring_criteria: list[str]
```

### AI Service Integration

**New Service:** `services/ai/ai_service.py`
- Gemini API client with proper error handling
- Brief analysis generation
- Version scoring against briefs
- Suggestion generation
- Provenance tracking for all AI operations

**New Routes:** `services/api/routes/v1_ai.py`
- `POST /api/v1/projects/{id}/ai/analyze-brief`
- `POST /api/v1/projects/{id}/ai/score-version`
- `POST /api/v1/projects/{id}/ai/generate-suggestions`
- `POST /api/v1/projects/{id}/ai/apply-suggestion`

## Implementation Phases

### Phase 14 — AI Brief Analysis Integration (4-6 weeks)

**Complexity:** High

**Deliverables:**
1. AI service integration with Gemini API
2. Enhanced brief analysis schema and validation
3. Integration with Week 11-12 brief compiler
4. Quality gate integration for AI-generated analysis
5. Regression tests for AI brief analysis pipeline

**Exit Criteria:**
- AI brief analysis generates structured space programs
- Analysis integrates with existing Week 11-12 pipeline
- Quality gates validate AI-generated content
- All existing tests pass
- New AI analysis regression tests pass

### Phase 15 — Concept Canvas Integration (6-8 weeks)

**Complexity:** Very High

**Deliverables:**
1. Interactive 2D canvas component in React
2. Canvas zone types and geometry handling
3. Multi-floor support with floor tabs
4. Snapping and alignment guides
5. Site boundary and north arrow overlay
6. Canvas-to-canonical-geometry conversion
7. New canvas command types in Python
8. Canvas-specific validation rules
9. Regression tests for canvas operations

**Exit Criteria:**
- Canvas allows creating, moving, resizing zones
- Canvas operations convert to canonical geometry
- Multi-floor support works correctly
- All canvas operations pass validation
- Existing geometry tests still pass
- New canvas regression tests pass

### Phase 16 — AI Version Scoring Integration (4-6 weeks)

**Complexity:** High

**Deliverables:**
1. AI version scoring service integration
2. Scoring schema and validation
3. Integration with Phase 12 quality gates
4. Version comparison and tradeoff analysis
5. Scoring provenance tracking
6. Regression tests for AI scoring

**Exit Criteria:**
- AI scores versions against briefs accurately
- Scoring integrates with quality gate framework
- Version comparison provides useful insights
- All existing quality gate tests pass
- New AI scoring regression tests pass

### Phase 17 — Proactive Suggestions Integration (4-6 weeks)

**Complexity:** High

**Deliverables:**
1. AI suggestion generation service
2. Suggestion schema and validation
3. Integration with Week 16 external tool pipeline
4. Suggestion acceptance/dismissal tracking
5. Suggestion history and archive
6. Regression tests for suggestion pipeline

**Exit Criteria:**
- AI generates relevant categorized suggestions
- Suggestions integrate with existing workflow
- Acceptance/dismissal tracking works correctly
- All existing Week 16 tests pass
- New suggestion regression tests pass

### Phase 18 — Workflow Enhancements (4-6 weeks)

**Complexity:** Medium

**Deliverables:**
1. Client-facing share links
2. PDF export with canvas rendering
3. Comments/annotations on canvas zones
4. Multi-user project support with roles
5. Version diffing view
6. Moodboard attachment support

**Exit Criteria:**
- Share links work correctly with proper access control
- PDF exports include canvas visualization
- Comments system integrates with existing collaboration
- Multi-user support maintains security boundaries
- All existing collaboration tests pass
- New workflow regression tests pass

## Quality Assurance Strategy

### Regression Testing
- All existing 673 tests must continue passing
- Add new regression tests for each AI feature
- Maintain adversarial test suite coverage
- Add property-based tests for AI-generated content

### Quality Gate Integration
- AI-generated content must pass existing quality gates
- Add AI-specific quality checks (hallucination detection, consistency validation)
- Maintain adversarial coverage for AI suggestions
- Track AI operation provenance in audit logs

### Security Considerations
- AI API keys stored as encrypted environment secrets
- AI operations require proper authentication and authorization
- AI suggestions clearly marked as non-authoritative
- AI modifications go through complete validation pipeline
- AI operation logging for audit trails

## Migration Strategy

### Backward Compatibility
- Maintain existing API contracts
- Add new AI features as optional enhancements
- Existing workflows continue without AI features
- Progressive enhancement approach

### Data Migration
- Add new database tables for AI analysis, canvas zones, suggestions
- Migrate existing projects to support new features
- Provide migration rollback path
- Maintain data integrity during migration

### Performance Considerations
- AI operations run asynchronously via job queue
- Cache AI responses where appropriate
- Implement rate limiting for AI API calls
- Monitor AI operation latency and costs

## Success Metrics

### Functional Metrics
- AI brief analysis accuracy (manual validation)
- Canvas operation success rate
- AI scoring correlation with expert assessment
- Suggestion acceptance rate
- User satisfaction with AI features

### Technical Metrics
- All existing tests passing
- New AI feature regression tests passing
- AI operation latency under targets
- AI API cost within budget
- System performance maintained

### Business Metrics
- Time saved in brief analysis
- Improvement in design quality scores
- Client satisfaction with concept reports
- Reduction in revision cycles
- Overall project completion time

## Risk Mitigation

### Technical Risks
- **AI API reliability:** Implement fallback mechanisms and graceful degradation
- **AI hallucination:** Add validation and user confirmation for critical operations
- **Performance impact:** Async operations and caching strategies
- **Integration complexity:** Incremental implementation with thorough testing

### Business Risks
- **User adoption:** Provide training and gradual rollout
- **Cost management:** Monitor AI API usage and implement cost controls
- **Quality assurance:** Maintain existing quality standards with AI features
- **Regulatory compliance:** Ensure AI features don't create liability issues

## Timeline Estimate

**Total Duration:** 22-32 weeks (5-8 months)

**Critical Path:**
1. Phase 14: AI Brief Analysis (4-6 weeks)
2. Phase 15: Concept Canvas (6-8 weeks) 
3. Phase 16: AI Version Scoring (4-6 weeks)
4. Phase 17: Proactive Suggestions (4-6 weeks)
5. Phase 18: Workflow Enhancements (4-6 weeks)

**Parallel Opportunities:**
- Some workflow enhancements can start earlier
- AI service infrastructure can be built once and reused
- Frontend canvas development can overlap with backend AI services

## Next Steps

1. **Review and approve** this integration plan
2. **Set up AI API infrastructure** (Gemini API key management)
3. **Begin Phase 14** with AI brief analysis integration
4. **Establish success metrics** and monitoring
5. **Create detailed technical specifications** for each phase

## Conclusion

This integration plan adds AI-native features to Advocate-Chambers while maintaining the core geometry-authority principle and building on the solid Phase 0-13 foundation. The AI-enhanced editing approach allows AI to directly modify geometry through proper validation and provenance tracking, creating a powerful AI-assisted architectural planning platform.