# Phase 16A Technical Specification: AI Version Scoring Integration

## Overview

**Objective:** Integrate existing AI version scoring backend with frontend workflow to enable architects to score design versions against client briefs using Gemini AI.

**Current State:** 
- Backend AI service fully implemented (`services/ai/ai_service.py`)
- API endpoint available (`POST /api/v1/projects/{id}/ai/score-version`)
- Frontend integration missing

**Target State:**
- Frontend UI for triggering and displaying AI scoring
- Integration with existing revision system
- Score visualization and history
- Version comparison capabilities

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
├─────────────────────────────────────────────────────────────┤
│  VersionScoringPanel.tsx                                     │
│  ├─ Fetch brief analysis                                    │
│  ├─ Trigger scoring for selected revision                   │
│  ├─ Display scores (overall, program-fit, daylight, budget) │
│  ├─ Show AI commentary and zone scores                       │
│  └─ Compare scores across versions                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  POST /api/v1/projects/{id}/ai/score-version                │
│  ├─ Validate request (auth, project access)                 │
│  ├─ Extract version geometry and metadata                  │
│  ├─ Call AI service                                         │
│  ├─ Return scored results with provenance                    │
│  └─ Handle errors gracefully                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI Service (Python)                        │
├─────────────────────────────────────────────────────────────┤
│  AIService.score_version()                                   │
│  ├─ Build scoring prompt with version data + brief          │
│  ├─ Call Gemini API (gemini-2.5-flash)                       │
│  ├─ Parse structured JSON response                          │
│  ├─ Add provenance tracking                                 │
│  └─ Return VersionScoreResult                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Gemini API (External)                        │
├─────────────────────────────────────────────────────────────┤
│  Generate architectural evaluation scores                    │
│  Return structured JSON with scores and commentary          │
└─────────────────────────────────────────────────────────────┘
```

## Data Structures

### API Request Schema

```typescript
interface ScoreVersionRequest {
  projectId: string;
  revisionId: string;
  briefAnalysisId?: string; // Optional: use latest if not provided
  scoringCriteria?: string[]; // Optional: custom criteria
}
```

### API Response Schema

```typescript
interface ScoreVersionResponse {
  success: boolean;
  data?: {
    overallScore: number; // 0-100
    programFit: number; // 0-100
    daylight: number; // 0-100
    budgetFit: number; // 0-100
    commentary: string;
    zoneScores: Array<{
      zoneName: string;
      score: number;
      notes: string;
    }>;
    provenance: {
      model: string;
      timestamp: string;
      versionId: string;
      briefAnalysisId: string;
    };
  };
  error?: string;
}
```

### Frontend State Schema

```typescript
interface ScoringState {
  currentRevision: Revision | null;
  briefAnalysis: BriefAnalysisResult | null;
  scoringResult: VersionScoreResult | null;
  isScoring: boolean;
  error: string | null;
  scoreHistory: Array<{
    revisionId: string;
    timestamp: string;
    scores: VersionScoreResult;
  }>;
}
```

## Component Specifications

### VersionScoringPanel.tsx

**Location:** `apps/web/src/components/VersionScoringPanel.tsx`

**Props:**
```typescript
interface VersionScoringPanelProps {
  projectId: string;
  currentRevision: Revision;
  onScoreComplete?: (result: VersionScoreResult) => void;
}
```

**State Management:**
```typescript
const [briefAnalysis, setBriefAnalysis] = useState<BriefAnalysisResult | null>(null);
const [scoringResult, setScoringResult] = useState<VersionScoreResult | null>(null);
const [isScoring, setIsScoring] = useState(false);
const [error, setError] = useState<string | null>(null);
const [selectedRevision, setSelectedRevision] = useState<Revision>(currentRevision);
```

**Key Functions:**

1. **fetchBriefAnalysis**
```typescript
async function fetchBriefAnalysis(): Promise<void> {
  const response = await fetch(`/api/v1/projects/${projectId}/ai/analyze-brief`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ briefText: currentRevision.briefText })
  });
  const data = await response.json();
  setBriefAnalysis(data.data);
}
```

2. **scoreVersion**
```typescript
async function scoreVersion(revision: Revision): Promise<void> {
  setIsScoring(true);
  setError(null);
  
  try {
    const response = await fetch(`/api/v1/projects/${projectId}/ai/score-version`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        projectId,
        revisionId: revision.id,
        briefAnalysisId: briefAnalysis?.provenance.timestamp
      })
    });
    
    const data = await response.json();
    if (data.success) {
      setScoringResult(data.data);
      onScoreComplete?.(data.data);
    } else {
      setError(data.error || 'Scoring failed');
    }
  } catch (err) {
    setError('Failed to connect to scoring service');
  } finally {
    setIsScoring(false);
  }
}
```

3. **compareScores**
```typescript
function compareScores(version1: VersionScoreResult, version2: VersionScoreResult): ScoreDiff {
  return {
    overall: version2.overallScore - version1.overallScore,
    programFit: version2.programFit - version1.programFit,
    daylight: version2.daylight - version1.daylight,
    budgetFit: version2.budgetFit - version1.budgetFit,
  };
}
```

**UI Structure:**
```tsx
<div className="scoring-panel">
  {/* Revision Selector */}
  <RevisionSelector 
    revisions={revisions}
    selected={selectedRevision}
    onSelect={setSelectedRevision}
  />
  
  {/* Brief Analysis Summary */}
  {briefAnalysis && (
    <BriefAnalysisSummary analysis={briefAnalysis} />
  )}
  
  {/* Score Button */}
  <button 
    onClick={() => scoreVersion(selectedRevision)}
    disabled={isScoring || !briefAnalysis}
  >
    {isScoring ? 'Scoring...' : 'Score This Version'}
  </button>
  
  {/* Scoring Results */}
  {scoringResult && (
    <ScoringResults result={scoringResult} />
  )}
  
  {/* Version Comparison */}
  {scoreHistory.length > 1 && (
    <VersionComparison history={scoreHistory} />
  )}
  
  {/* Error Display */}
  {error && <ErrorMessage message={error} />}
</div>
```

### ScoringResults.tsx (Sub-component)

**Location:** `apps/web/src/components/ScoringResults.tsx`

**Props:**
```typescript
interface ScoringResultsProps {
  result: VersionScoreResult;
}
```

**UI Structure:**
```tsx
<div className="scoring-results">
  {/* Overall Score Display */}
  <ScoreGauge value={result.overallScore} label="Overall" />
  
  {/* Category Scores */}
  <div className="category-scores">
    <ScoreBar value={result.programFit} label="Program Fit" />
    <ScoreBar value={result.daylight} label="Daylight" />
    <ScoreBar value={result.budgetFit} label="Budget Fit" />
  </div>
  
  {/* AI Commentary */}
  <div className="commentary">
    <h4>AI Commentary</h4>
    <p>{result.commentary}</p>
  </div>
  
  {/* Zone-Specific Scores */}
  <div className="zone-scores">
    <h4>Zone Analysis</h4>
    {result.zoneScores.map(zone => (
      <ZoneScoreCard key={zone.zoneName} zone={zone} />
    ))}
  </div>
  
  {/* Provenance Info */}
  <div className="provenance">
    <small>
      Scored by {result.provenance.model} at {result.provenance.timestamp}
    </small>
  </div>
</div>
```

## API Integration

### Enhanced API Route

**File:** `services/api/routes/v1_ai.py`

**Enhancement:** Add revision lookup and geometry extraction

```python
@router.post("/projects/{project_id}/ai/score-version")
async def score_version(
    project_id: str,
    request: ScoreVersionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ScoreVersionResponse:
    """Score a design version against the brief analysis."""
    
    # Validate project access
    project = get_project_with_access(db, project_id, current_user["id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get revision with geometry
    revision = db.query(Revision).filter(
        Revision.id == request.revisionId,
        Revision.project_id == project_id
    ).first()
    
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    
    # Get or create brief analysis
    brief_analysis = get_brief_analysis(db, project_id, request.briefAnalysisId)
    
    # Extract version data for AI
    version_data = {
        "id": revision.id,
        "geometry": revision.geometry,
        "metadata": revision.metadata,
        "spaces": extract_spaces_from_geometry(revision.geometry)
    }
    
    # Call AI service
    try:
        ai_service = get_ai_service()
        scoring_result = ai_service.score_version(version_data, brief_analysis)
        
        # Store scoring result
        store_scoring_result(db, project_id, revision.id, scoring_result)
        
        return ScoreVersionResponse(
            success=True,
            data=scoring_result
        )
    except RuntimeError as e:
        return ScoreVersionResponse(
            success=False,
            error=str(e)
        )
```

## Database Schema

### New Table: scoring_results

```sql
CREATE TABLE scoring_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    revision_id UUID NOT NULL REFERENCES revisions(id) ON DELETE CASCADE,
    brief_analysis_id VARCHAR(255),
    overall_score INTEGER NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    program_fit INTEGER NOT NULL CHECK (program_fit >= 0 AND program_fit <= 100),
    daylight_score INTEGER NOT NULL CHECK (daylight_score >= 0 AND daylight_score <= 100),
    budget_fit INTEGER NOT NULL CHECK (budget_fit >= 0 AND budget_fit <= 100),
    commentary TEXT NOT NULL,
    zone_scores JSONB NOT NULL,
    provenance JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(revision_id)
);

CREATE INDEX idx_scoring_results_project ON scoring_results(project_id);
CREATE INDEX idx_scoring_results_revision ON scoring_results(revision_id);
CREATE INDEX idx_scoring_results_created ON scoring_results(created_at DESC);
```

## Testing Strategy

### Unit Tests

**File:** `tests/test_phase16a_version_scoring.py`

```python
class TestVersionScoringIntegration(unittest.TestCase):
    def test_scoring_endpoint_requires_auth(self):
        """Test that scoring endpoint requires authentication."""
        response = client.post("/api/v1/projects/test/ai/score-version")
        self.assertEqual(response.status_code, 401)
    
    def test_scoring_with_valid_revision(self):
        """Test scoring a valid revision."""
        # Create test project and revision
        project = create_test_project()
        revision = create_test_revision(project.id)
        
        # Score the revision
        response = client.post(
            f"/api/v1/projects/{project.id}/ai/score-version",
            json={"revisionId": revision.id},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("overallScore", response.json()["data"])
    
    def test_scoring_with_invalid_revision(self):
        """Test scoring with non-existent revision."""
        response = client.post(
            "/api/v1/projects/test/ai/score-version",
            json={"revisionId": "non-existent"},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_scoring_provenance_tracking(self):
        """Test that scoring results include provenance."""
        project = create_test_project()
        revision = create_test_revision(project.id)
        
        response = client.post(
            f"/api/v1/projects/{project.id}/ai/score-version",
            json={"revisionId": revision.id},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        provenance = response.json()["data"]["provenance"]
        self.assertIn("model", provenance)
        self.assertIn("timestamp", provenance)
        self.assertIn("versionId", provenance)
```

### Integration Tests

**File:** `tests/test_phase16a_frontend_integration.py`

```python
class TestFrontendIntegration(unittest.TestCase):
    def test_brief_analysis_to_scoring_flow(self):
        """Test complete flow from brief analysis to scoring."""
        # Create project with brief
        project = create_test_project_with_brief()
        
        # Analyze brief
        brief_response = client.post(
            f"/api/v1/projects/{project.id}/ai/analyze-brief",
            json={"briefText": project.brief_text},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        brief_analysis_id = brief_response.json()["data"]["provenance"]["timestamp"]
        
        # Create revision
        revision = create_test_revision(project.id)
        
        # Score revision using brief analysis
        score_response = client.post(
            f"/api/v1/projects/{project.id}/ai/score-version",
            json={
                "revisionId": revision.id,
                "briefAnalysisId": brief_analysis_id
            },
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        self.assertEqual(score_response.status_code, 200)
        self.assertTrue(score_response.json()["success"])
```

### Frontend Tests

**File:** `apps/web/src/components/__tests__/VersionScoringPanel.test.tsx`

```typescript
describe('VersionScoringPanel', () => {
  it('renders revision selector', () => {
    render(<VersionScoringPanel projectId="test" currentRevision={mockRevision} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });
  
  it('displays scoring results after successful scoring', async () => {
    render(<VersionScoringPanel projectId="test" currentRevision={mockRevision} />);
    
    const scoreButton = screen.getByText('Score This Version');
    fireEvent.click(scoreButton);
    
    await waitFor(() => {
      expect(screen.getByText('Overall Score')).toBeInTheDocument();
    });
  });
  
  it('shows error message on scoring failure', async () => {
    mockFetch.mockRejectedValueOnce(new Error('API Error'));
    
    render(<VersionScoringPanel projectId="test" currentRevision={mockRevision} />);
    
    const scoreButton = screen.getByText('Score This Version');
    fireEvent.click(scoreButton);
    
    await waitFor(() => {
      expect(screen.getByText(/failed to connect/i)).toBeInTheDocument();
    });
  });
});
```

## Performance Considerations

### AI API Latency
- **Target:** <5 seconds for typical projects
- **Strategy:** 
  - Implement request debouncing
  - Show loading states with progress indicators
  - Cache scoring results for identical revisions
  - Use streaming responses for large projects

### Frontend Performance
- **Target:** <100ms for UI interactions
- **Strategy:**
  - Use React.memo for expensive components
  - Implement virtual scrolling for large revision lists
  - Lazy load score history
  - Optimize re-renders with proper dependency arrays

### Database Performance
- **Target:** <200ms for scoring result queries
- **Strategy:**
  - Proper indexing on project_id and revision_id
  - Query optimization for score history
  - Connection pooling for database access
  - Consider read replicas for scaling

## Security Considerations

### Authentication & Authorization
- All scoring endpoints require valid authentication
- Project access validation before scoring
- User can only score revisions they have access to
- Audit logging for all scoring operations

### API Key Security
- Gemini API key stored as environment variable
- Never exposed in frontend code
- Rotatable without system restart
- Usage monitoring and rate limiting

### Data Privacy
- Brief text and project data sent to Gemini API
- Clear disclosure to users about AI processing
- Option to opt-out of AI features
- Data retention policies for AI results

## Error Handling

### AI Service Unavailable
```typescript
if (!aiService.available) {
  return {
    success: false,
    error: "AI service temporarily unavailable. Please try again later."
  };
}
```

### Invalid Revision
```typescript
if (!revision) {
  return {
    success: false,
    error: "Revision not found or access denied."
  };
}
```

### Brief Analysis Missing
```typescript
if (!briefAnalysis) {
  return {
    success: false,
    error: "Brief analysis required. Please analyze the brief first."
  };
}
```

### Scoring Parse Error
```typescript
try {
  const scoring = await aiService.score_version(versionData, briefAnalysis);
  return { success: true, data: scoring };
} catch (parseError) {
  logger.error("Failed to parse AI scoring response", parseError);
  return {
    success: false,
    error: "Failed to process AI response. Please try again."
  };
}
```

## Deployment Considerations

### Environment Variables
```bash
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
AI_SCORING_ENABLED=true
AI_RATE_LIMIT=10
```

### Feature Flags
- Enable/disable AI scoring per organization
- Rate limiting per user
- Cost monitoring and alerts
- Gradual rollout strategy

### Monitoring
- AI API call success rate
- Average scoring latency
- Error rates by type
- User engagement metrics

## Success Criteria

### Functional Requirements
- [ ] Users can score any revision they have access to
- [ ] Scoring uses the latest brief analysis by default
- [ ] Scores are displayed with clear visualizations
- [ ] AI commentary is shown in readable format
- [ ] Zone-specific scores are available
- [ ] Version comparison shows score differences
- [ ] Scoring history is tracked and viewable

### Technical Requirements
- [ ] All existing tests continue to pass
- [ ] New regression tests added (minimum 10 tests)
- [ ] API response time <5 seconds for typical projects
- [ ] Frontend UI response time <100ms
- [ ] Error handling covers all failure modes
- [ ] Security audit passes
- [ ] Performance benchmarks met

### User Experience Requirements
- [ ] Clear indication when scoring is in progress
- [ ] Helpful error messages for failures
- [ ] Intuitive version comparison interface
- [ ] Mobile-responsive design
- [ ] Accessibility compliance (WCAG 2.1 AA)

## Rollout Plan

### Phase 1: Internal Testing (1 week)
- Deploy to staging environment
- Test with internal projects
- Gather feedback from team
- Fix critical issues

### Phase 2: Beta Testing (2 weeks)
- Enable for select beta users
- Monitor usage and performance
- Collect user feedback
- Iterate on UX improvements

### Phase 3: General Availability (1 week)
- Enable for all users
- Monitor production metrics
- Provide user documentation
- Support and training

## Future Enhancements

### Potential Future Features
- Custom scoring criteria
- Weighted scoring categories
- Historical trend analysis
- Benchmark against industry standards
- Multi-version batch scoring
- Export scoring reports

### Integration Opportunities
- Integrate with Phase 12 quality gates
- Connect to Week 16 external tool pipeline
- Link to collaboration workflow
- Feed into presentation generation