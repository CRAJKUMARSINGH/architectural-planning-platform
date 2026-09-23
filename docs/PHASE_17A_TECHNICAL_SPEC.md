# Phase 17A Technical Specification: Proactive Suggestions Integration

## Overview

**Objective:** Integrate existing AI proactive suggestions backend with frontend workflow to enable architects to receive categorized, actionable design suggestions from Gemini AI.

**Current State:** 
- Backend AI service fully implemented (`services/ai/ai_service.py`)
- API endpoint available (`POST /api/v1/projects/{id}/ai/generate-suggestions`)
- Frontend integration missing

**Target State:**
- Frontend UI for generating and displaying AI suggestions
- Categorized suggestion display (program, site, daylight, budget, circulation, general)
- Accept/dismiss tracking with persistence
- Suggestion history and archive view
- Filtering and search capabilities

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
├─────────────────────────────────────────────────────────────┤
│  SuggestionsPanel.tsx                                        │
│  ├─ Fetch suggestions for current project                   │
│  ├─ Display by category with filters                        │
│  ├─ Accept/dismiss buttons with tracking                     │
│  ├─ Show suggestion history                                  │
│  └─ Filter by category, status, date                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  POST /api/v1/projects/{id}/ai/generate-suggestions         │
│  ├─ Validate request (auth, project access)                 │
│  ├─ Extract project data (brief, version, context)           │
│  ├─ Call AI service with target categories                  │
│  ├─ Return categorized suggestions with provenance           │
│  └─ Handle errors gracefully                                │
│                                                              │
│  PUT /api/v1/projects/{id}/ai/suggestions/{id}/status       │
│  ├─ Update suggestion acceptance status                     │
│  └─ Track user decisions                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI Service (Python)                        │
├─────────────────────────────────────────────────────────────┤
│  AIService.generate_suggestions()                            │
│  ├─ Build suggestions prompt with project data              │
│  ├─ Call Gemini API (gemini-2.5-flash)                       │
│  ├─ Parse structured JSON response                          │
│  ├─ Categorize suggestions                                  │
│  ├─ Add provenance tracking                                 │
│  └─ Return SuggestionResult                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Gemini API (External)                        │
├─────────────────────────────────────────────────────────────┤
│  Generate categorized design suggestions                     │
│  Return structured JSON with suggestions by category        │
└─────────────────────────────────────────────────────────────┘
```

## Data Structures

### API Request Schema

```typescript
interface GenerateSuggestionsRequest {
  projectId: string;
  categories?: string[]; // Optional: specify categories to generate
  revisionId?: string; // Optional: score specific revision
  context?: {
    siteSize?: number;
    budget?: number;
    stylePreferences?: string[];
  };
}
```

### API Response Schema

```typescript
interface GenerateSuggestionsResponse {
  success: boolean;
  data?: {
    suggestions: Array<{
      id: string;
      category: string;
      text: string;
      priority: 'high' | 'medium' | 'low';
      targetZone?: string;
      rationale?: string;
    }>;
    categories: string[];
    provenance: {
      model: string;
      timestamp: string;
      projectId: string;
      categoriesRequested: string[];
    };
  };
  error?: string;
}
```

### Suggestion Status Update Schema

```typescript
interface UpdateSuggestionStatusRequest {
  status: 'accepted' | 'dismissed' | 'pending';
  userId?: string;
  notes?: string;
}
```

### Frontend State Schema

```typescript
interface SuggestionsState {
  suggestions: Suggestion[];
  filteredSuggestions: Suggestion[];
  activeCategories: string[];
  statusFilter: 'all' | 'pending' | 'accepted' | 'dismissed';
  searchQuery: string;
  isGenerating: boolean;
  error: string | null;
  history: SuggestionHistory[];
}

interface Suggestion {
  id: string;
  category: string;
  text: string;
  priority: 'high' | 'medium' | 'low';
  targetZone?: string;
  rationale?: string;
  status: 'pending' | 'accepted' | 'dismissed';
  createdAt: string;
  updatedAt?: string;
  userId?: string;
  notes?: string;
}
```

## Component Specifications

### SuggestionsPanel.tsx

**Location:** `apps/web/src/components/SuggestionsPanel.tsx`

**Props:**
```typescript
interface SuggestionsPanelProps {
  projectId: string;
  currentRevision?: Revision;
  onSuggestionAction?: (suggestion: Suggestion, action: 'accept' | 'dismiss') => void;
}
```

**State Management:**
```typescript
const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
const [filteredSuggestions, setFilteredSuggestions] = useState<Suggestion[]>([]);
const [activeCategories, setActiveCategories] = useState<string[]>([]);
const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'accepted' | 'dismissed'>('all');
const [searchQuery, setSearchQuery] = useState('');
const [isGenerating, setIsGenerating] = useState(false);
const [error, setError] = useState<string | null>(null);
const [showHistory, setShowHistory] = useState(false);
```

**Key Functions:**

1. **generateSuggestions**
```typescript
async function generateSuggestions(categories?: string[]): Promise<void> {
  setIsGenerating(true);
  setError(null);
  
  try {
    const response = await fetch(`/api/v1/projects/${projectId}/ai/generate-suggestions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        projectId,
        categories: categories || ['program', 'site', 'daylight', 'budget', 'circulation', 'general'],
        revisionId: currentRevision?.id,
        context: {
          siteSize: currentRevision?.metadata?.siteSize,
          budget: currentRevision?.metadata?.budget,
          stylePreferences: currentRevision?.metadata?.stylePreferences
        }
      })
    });
    
    const data = await response.json();
    if (data.success) {
      const newSuggestions = data.data.suggestions.map((s: any) => ({
        ...s,
        status: 'pending' as const,
        createdAt: new Date().toISOString()
      }));
      setSuggestions(prev => [...newSuggestions, ...prev]);
      setFilteredSuggestions(newSuggestions);
    } else {
      setError(data.error || 'Failed to generate suggestions');
    }
  } catch (err) {
    setError('Failed to connect to suggestions service');
  } finally {
    setIsGenerating(false);
  }
}
```

2. **updateSuggestionStatus**
```typescript
async function updateSuggestionStatus(
  suggestionId: string, 
  status: 'accepted' | 'dismissed',
  notes?: string
): Promise<void> {
  try {
    const response = await fetch(
      `/api/v1/projects/${projectId}/ai/suggestions/${suggestionId}/status`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, notes })
      }
    );
    
    if (response.ok) {
      setSuggestions(prev => 
        prev.map(s => 
          s.id === suggestionId 
            ? { ...s, status, updatedAt: new Date().toISOString(), notes }
            : s
        )
      );
      onSuggestionAction?.(
        suggestions.find(s => s.id === suggestionId)!, 
        status === 'accepted' ? 'accept' : 'dismiss'
      );
    }
  } catch (err) {
    setError('Failed to update suggestion status');
  }
}
```

3. **filterSuggestions**
```typescript
function filterSuggestions(): void {
  let filtered = suggestions;
  
  // Apply status filter
  if (statusFilter !== 'all') {
    filtered = filtered.filter(s => s.status === statusFilter);
  }
  
  // Apply category filter
  if (activeCategories.length > 0) {
    filtered = filtered.filter(s => activeCategories.includes(s.category));
  }
  
  // Apply search filter
  if (searchQuery) {
    const query = searchQuery.toLowerCase();
    filtered = filtered.filter(s => 
      s.text.toLowerCase().includes(query) ||
      s.category.toLowerCase().includes(query) ||
      s.targetZone?.toLowerCase().includes(query)
    );
  }
  
  setFilteredSuggestions(filtered);
}
```

**UI Structure:**
```tsx
<div className="suggestions-panel">
  {/* Header with Generate Button */}
  <div className="panel-header">
    <h2>AI Suggestions</h2>
    <button 
      onClick={() => generateSuggestions()}
      disabled={isGenerating}
    >
      {isGenerating ? 'Generating...' : 'Generate New Suggestions'}
    </button>
  </div>
  
  {/* Filters */}
  <div className="filters">
    <CategoryFilter 
      categories={ALL_CATEGORIES}
      active={activeCategories}
      onChange={setActiveCategories}
    />
    <StatusFilter 
      value={statusFilter}
      onChange={setStatusFilter}
    />
    <SearchInput 
      value={searchQuery}
      onChange={setSearchQuery}
    />
  </div>
  
  {/* Suggestions List */}
  <div className="suggestions-list">
    {filteredSuggestions.map(suggestion => (
      <SuggestionCard 
        key={suggestion.id}
        suggestion={suggestion}
        onAccept={() => updateSuggestionStatus(suggestion.id, 'accepted')}
        onDismiss={() => updateSuggestionStatus(suggestion.id, 'dismissed')}
      />
    ))}
  </div>
  
  {/* History Toggle */}
  <button onClick={() => setShowHistory(!showHistory)}>
    {showHistory ? 'Hide History' : 'Show History'}
  </button>
  
  {/* History View */}
  {showHistory && <SuggestionHistory history={history} />}
  
  {/* Error Display */}
  {error && <ErrorMessage message={error} />}
</div>
```

### SuggestionCard.tsx (Sub-component)

**Location:** `apps/web/src/components/SuggestionCard.tsx`

**Props:**
```typescript
interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept: () => void;
  onDismiss: () => void;
}
```

**UI Structure:**
```tsx
<div className={`suggestion-card priority-${suggestion.priority} status-${suggestion.status}`}>
  {/* Category Badge */}
  <CategoryBadge category={suggestion.category} />
  
  {/* Priority Indicator */}
  <PriorityIndicator priority={suggestion.priority} />
  
  {/* Suggestion Text */}
  <p className="suggestion-text">{suggestion.text}</p>
  
  {/* Target Zone (if applicable) */}
  {suggestion.targetZone && (
    <div className="target-zone">
      <strong>Target:</strong> {suggestion.targetZone}
    </div>
  )}
  
  {/* Rationale (if provided) */}
  {suggestion.rationale && (
    <div className="rationale">
      <strong>Why:</strong> {suggestion.rationale}
    </div>
  )}
  
  {/* Action Buttons */}
  {suggestion.status === 'pending' && (
    <div className="actions">
      <button onClick={onAccept} className="accept-btn">
        ✓ Accept
      </button>
      <button onClick={onDismiss} className="dismiss-btn">
        ✗ Dismiss
      </button>
    </div>
  )}
  
  {/* Status Display */}
  {suggestion.status !== 'pending' && (
    <div className={`status-badge ${suggestion.status}`}>
      {suggestion.status === 'accepted' ? '✓ Accepted' : '✗ Dismissed'}
    </div>
  )}
  
  {/* Timestamp */}
  <div className="timestamp">
    {formatDate(suggestion.createdAt)}
  </div>
</div>
```

### SuggestionHistory.tsx (Sub-component)

**Location:** `apps/web/src/components/SuggestionHistory.tsx`

**Props:**
```typescript
interface SuggestionHistoryProps {
  history: SuggestionHistory[];
}
```

**UI Structure:**
```tsx
<div className="suggestion-history">
  <h3>Suggestion History</h3>
  
  {/* Analytics Summary */}
  <div className="analytics">
    <StatCard label="Total Generated" value={history.length} />
    <StatCard label="Accepted" value={history.filter(h => h.status === 'accepted').length} />
    <StatCard label="Dismissed" value={history.filter(h => h.status === 'dismissed').length} />
    <StatCard 
      label="Acceptance Rate" 
      value={`${calculateAcceptanceRate(history)}%`} 
    />
  </div>
  
  {/* Category Breakdown */}
  <div className="category-breakdown">
    <h4>By Category</h4>
    {Object.entries(groupByCategory(history)).map(([category, count]) => (
      <CategoryStat key={category} category={category} count={count} />
    ))}
  </div>
  
  {/* Timeline View */}
  <div className="timeline">
    <h4>Timeline</h4>
    {history.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .map(item => (
        <HistoryItem key={item.id} item={item} />
      ))}
  </div>
</div>
```

## API Integration

### Enhanced API Route

**File:** `services/api/routes/v1_ai.py`

**Enhancement:** Add suggestion status tracking and history

```python
@router.post("/projects/{project_id}/ai/generate-suggestions")
async def generate_suggestions(
    project_id: str,
    request: GenerateSuggestionsRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GenerateSuggestionsResponse:
    """Generate proactive design suggestions for a project."""
    
    # Validate project access
    project = get_project_with_access(db, project_id, current_user["id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Extract project data
    project_data = {
        "id": project.id,
        "brief": project.brief_text,
        "metadata": project.metadata,
        "context": request.context or {}
    }
    
    # Add revision data if specified
    if request.revisionId:
        revision = db.query(Revision).filter(
            Revision.id == request.revisionId,
            Revision.project_id == project_id
        ).first()
        if revision:
            project_data["revision"] = {
                "id": revision.id,
                "geometry": revision.geometry,
                "spaces": extract_spaces_from_geometry(revision.geometry)
            }
    
    # Call AI service
    try:
        ai_service = get_ai_service()
        suggestions_result = ai_service.generate_suggestions(
            project_data, 
            request.categories
        )
        
        # Store suggestions with pending status
        stored_suggestions = []
        for suggestion in suggestions_result.suggestions:
            stored = store_suggestion(
                db, 
                project_id, 
                suggestion, 
                current_user["id"],
                suggestions_result.provenance
            )
            stored_suggestions.append(stored)
        
        return GenerateSuggestionsResponse(
            success=True,
            data={
                "suggestions": stored_suggestions,
                "categories": suggestions_result.categories,
                "provenance": suggestions_result.provenance
            }
        )
    except RuntimeError as e:
        return GenerateSuggestionsResponse(
            success=False,
            error=str(e)
        )

@router.put("/projects/{project_id}/ai/suggestions/{suggestion_id}/status")
async def update_suggestion_status(
    project_id: str,
    suggestion_id: str,
    request: UpdateSuggestionStatusRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UpdateSuggestionStatusResponse:
    """Update the acceptance status of a suggestion."""
    
    # Validate project access
    project = get_project_with_access(db, project_id, current_user["id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get suggestion
    suggestion = db.query(Suggestion).filter(
        Suggestion.id == suggestion_id,
        Suggestion.project_id == project_id
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    # Update status
    suggestion.status = request.status
    suggestion.updated_at = datetime.now(timezone.utc)
    suggestion.user_id = request.userId or current_user["id"]
    suggestion.notes = request.notes
    
    db.commit()
    
    return UpdateSuggestionStatusResponse(
        success=True,
        data={
            "id": suggestion.id,
            "status": suggestion.status,
            "updatedAt": suggestion.updated_at.isoformat()
        }
    )
```

## Database Schema

### New Table: suggestions

```sql
CREATE TABLE suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    revision_id UUID REFERENCES revisions(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    target_zone VARCHAR(255),
    rationale TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'dismissed')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    provenance JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_category CHECK (category IN ('program', 'site', 'daylight', 'budget', 'circulation', 'general'))
);

CREATE INDEX idx_suggestions_project ON suggestions(project_id);
CREATE INDEX idx_suggestions_revision ON suggestions(revision_id);
CREATE INDEX idx_suggestions_status ON suggestions(status);
CREATE INDEX idx_suggestions_category ON suggestions(category);
CREATE INDEX idx_suggestions_created ON suggestions(created_at DESC);
CREATE INDEX idx_suggestions_user ON suggestions(user_id);
```

## Testing Strategy

### Unit Tests

**File:** `tests/test_phase17a_suggestions.py`

```python
class TestSuggestionsIntegration(unittest.TestCase):
    def test_suggestions_endpoint_requires_auth(self):
        """Test that suggestions endpoint requires authentication."""
        response = client.post("/api/v1/projects/test/ai/generate-suggestions")
        self.assertEqual(response.status_code, 401)
    
    def test_generate_suggestions_with_valid_project(self):
        """Test generating suggestions for a valid project."""
        project = create_test_project_with_brief()
        
        response = client.post(
            f"/api/v1/projects/{project.id}/ai/generate-suggestions",
            json={"categories": ["program", "site"]},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertGreater(len(response.json()["data"]["suggestions"]), 0)
    
    def test_suggestions_categorized_correctly(self):
        """Test that suggestions are properly categorized."""
        project = create_test_project_with_brief()
        
        response = client.post(
            f"/api/v1/projects/{project.id}/ai/generate-suggestions",
            json={"categories": ["program", "site", "daylight"]},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        suggestions = response.json()["data"]["suggestions"]
        categories = set(s["category"] for s in suggestions)
        
        self.assertTrue(categories.issubset({"program", "site", "daylight"}))
    
    def test_update_suggestion_status(self):
        """Test updating suggestion acceptance status."""
        project = create_test_project_with_brief()
        
        # Generate suggestions
        gen_response = client.post(
            f"/api/v1/projects/{project.id}/ai/generate-suggestions",
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        suggestion_id = gen_response.json()["data"]["suggestions"][0]["id"]
        
        # Update status
        update_response = client.put(
            f"/api/v1/projects/{project.id}/ai/suggestions/{suggestion_id}/status",
            json={"status": "accepted"},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["status"], "accepted")
```

### Integration Tests

**File:** `tests/test_phase17a_suggestion_workflow.py`

```python
class TestSuggestionWorkflow(unittest.TestCase):
    def test_complete_suggestion_lifecycle(self):
        """Test complete lifecycle from generation to acceptance."""
        project = create_test_project_with_brief()
        
        # Generate suggestions
        gen_response = client.post(
            f"/api/v1/projects/{project.id}/ai/generate-suggestions",
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        suggestion_id = gen_response.json()["data"]["suggestions"][0]["id"]
        
        # Verify initial status
        self.assertEqual(
            gen_response.json()["data"]["suggestions"][0]["status"], 
            "pending"
        )
        
        # Accept suggestion
        accept_response = client.put(
            f"/api/v1/projects/{project.id}/ai/suggestions/{suggestion_id}/status",
            json={"status": "accepted", "notes": "Good suggestion"},
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        self.assertEqual(accept_response.json()["data"]["status"], "accepted")
        
        # Verify history tracking
        history_response = client.get(
            f"/api/v1/projects/{project.id}/ai/suggestions/history",
            headers={"Authorization": f"Bearer {get_test_token()}"}
        )
        
        accepted_count = len([
            s for s in history_response.json()["data"] 
            if s["status"] == "accepted"
        ])
        self.assertEqual(accepted_count, 1)
```

### Frontend Tests

**File:** `apps/web/src/components/__tests__/SuggestionsPanel.test.tsx`

```typescript
describe('SuggestionsPanel', () => {
  it('renders generate button', () => {
    render(<SuggestionsPanel projectId="test" />);
    expect(screen.getByText('Generate New Suggestions')).toBeInTheDocument();
  });
  
  it('displays suggestions after generation', async () => {
    render(<SuggestionsPanel projectId="test" />);
    
    const generateButton = screen.getByText('Generate New Suggestions');
    fireEvent.click(generateButton);
    
    await waitFor(() => {
      expect(screen.getByText(/program/i)).toBeInTheDocument();
    });
  });
  
  it('filters suggestions by category', async () => {
    render(<SuggestionsPanel projectId="test" />);
    
    // Generate suggestions
    fireEvent.click(screen.getByText('Generate New Suggestions'));
    await waitFor(() => {
      expect(screen.getByText(/program/i)).toBeInTheDocument();
    });
    
    // Filter by program category
    fireEvent.click(screen.getByLabelText('Program'));
    
    await waitFor(() => {
      const programSuggestions = screen.getAllByText(/program/i);
      expect(programSuggestions.length).toBeGreaterThan(0);
    });
  });
  
  it('updates suggestion status on accept', async () => {
    render(<SuggestionsPanel projectId="test" />);
    
    // Generate suggestions
    fireEvent.click(screen.getByText('Generate New Suggestions'));
    await waitFor(() => {
      expect(screen.getByText(/accept/i)).toBeInTheDocument();
    });
    
    // Accept first suggestion
    const acceptButton = screen.getAllByText('✓ Accept')[0];
    fireEvent.click(acceptButton);
    
    await waitFor(() => {
      expect(screen.getByText(/✓ accepted/i)).toBeInTheDocument();
    });
  });
});
```

## Performance Considerations

### AI API Latency
- **Target:** <3 seconds for typical projects
- **Strategy:**
  - Implement request debouncing
  - Show loading states with category progress
  - Cache suggestions for identical project states
  - Use streaming responses for large suggestion sets

### Frontend Performance
- **Target:** <100ms for UI interactions
- **Strategy:**
  - Virtual scrolling for large suggestion lists
  - Lazy loading for suggestion history
  - Debounced search input
  - Memoized suggestion cards

### Database Performance
- **Target:** <150ms for suggestion queries
- **Strategy:**
  - Proper indexing on project_id, status, category
  - Query optimization for history views
  - Pagination for large history sets
  - Connection pooling

## Security Considerations

### Authentication & Authorization
- All suggestion endpoints require valid authentication
- Project access validation before operations
- Users can only access their own suggestion history
- Audit logging for all suggestion actions

### Data Privacy
- Project data sent to Gemini API for suggestion generation
- Clear disclosure to users about AI processing
- Option to opt-out of AI suggestions
- Data retention policies for suggestion history

### Rate Limiting
- Per-user rate limits on suggestion generation
- Cost monitoring and alerts
- Quota management per organization
- Graceful degradation when limits reached

## Error Handling

### AI Service Unavailable
```typescript
if (!aiService.available) {
  return {
    success: false,
    error: "AI suggestions temporarily unavailable. Please try again later."
  };
}
```

### Invalid Project
```typescript
if (!project) {
  return {
    success: false,
    error: "Project not found or access denied."
  };
}
```

### Suggestion Parse Error
```typescript
try {
  const suggestions = await aiService.generate_suggestions(projectData, categories);
  return { success: true, data: suggestions };
} catch (parseError) {
  logger.error("Failed to parse AI suggestions response", parseError);
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
AI_SUGGESTIONS_ENABLED=true
AI_SUGGESTIONS_RATE_LIMIT=20
```

### Feature Flags
- Enable/disable suggestions per organization
- Category-specific enablement
- Rate limiting per user
- Cost monitoring and alerts

### Monitoring
- AI API call success rate
- Average suggestion generation latency
- Suggestion acceptance rates by category
- User engagement metrics

## Success Criteria

### Functional Requirements
- [ ] Users can generate suggestions for any project
- [ ] Suggestions are properly categorized
- [ ] Users can accept/dismiss suggestions
- [ ] Status changes are tracked and persisted
- [ ] Suggestion history is viewable
- [ ] Filtering works by category, status, and search
- [ ] Analytics show meaningful metrics

### Technical Requirements
- [ ] All existing tests continue to pass
- [ ] New regression tests added (minimum 12 tests)
- [ ] API response time <3 seconds for typical projects
- [ ] Frontend UI response time <100ms
- [ ] Error handling covers all failure modes
- [ ] Security audit passes
- [ ] Performance benchmarks met

### User Experience Requirements
- [ ] Clear indication when generating suggestions
- [ ] Helpful error messages for failures
- [ ] Intuitive filtering and search interface
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
- Monitor usage and acceptance rates
- Collect user feedback on categories
- Iterate on UX improvements

### Phase 3: General Availability (1 week)
- Enable for all users
- Monitor production metrics
- Provide user documentation
- Support and training

## Future Enhancements

### Potential Future Features
- Custom suggestion categories
- Priority weighting by user preferences
- Suggestion chaining (build on previous suggestions)
- Benchmark against industry best practices
- Multi-project batch suggestions
- Export suggestion reports

### Integration Opportunities
- Integrate with Phase 16A version scoring
- Connect to Week 16 external tool pipeline
- Link to collaboration workflow
- Feed into presentation generation
- Suggest based on quality gate failures