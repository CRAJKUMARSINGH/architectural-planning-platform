/**
 * VersionScoringPanel — Phase 16A AI version scoring integration.
 *
 * Provides UI for scoring design versions against client briefs using Gemini AI.
 * Integrates with existing AI service and revision system.
 *
 * Architecture rule (from PHASE_16A_TECHNICAL_SPEC.md):
 *   Scoring results are ephemeral UI state with optional persistence.
 *   All scoring operations go through the AI service with proper validation.
 *   Scores include provenance tracking and integrate with quality gates.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

// ── Types ────────────────────────────────────────────────────────────────────

export interface BriefAnalysisResult {
  summary: string;
  spaceProgram: Array<{
    name: string;
    sqm: number;
    priority: string;
    notes: string;
  }>;
  constraints: string[];
  opportunities: string[];
  openQuestions: string[];
  provenance: {
    model: string;
    timestamp: string;
    briefLength: number;
    contextKeys: string[];
  };
  modelVersion: string;
}

export interface VersionScoreResult {
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
  modelVersion: string;
}

export interface Revision {
  id: string;
  revisionNumber: number;
  createdAt: string;
  briefText?: string;
  metadata?: {
    siteSize?: number;
    budget?: number;
    stylePreferences?: string[];
  };
}

interface Props {
  projectId: string;
  currentRevision: Revision;
  onScoreComplete?: (result: VersionScoreResult) => void;
}

// ── Helper Types ─────────────────────────────────────────────────────────────

interface ScoreDiff {
  overall: number;
  programFit: number;
  daylight: number;
  budgetFit: number;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function VersionScoringPanel({ projectId, currentRevision, onScoreComplete }: Props): React.JSX.Element {
  const qc = useQueryClient();
  
  // State management
  const [briefAnalysis, setBriefAnalysis] = useState<BriefAnalysisResult | null>(null);
  const [scoringResult, setScoringResult] = useState<VersionScoreResult | null>(null);
  const [selectedRevision] = useState<Revision>(currentRevision);
  const [error, setError] = useState<string | null>(null);
  const [scoreHistory, setScoreHistory] = useState<Array<{
    revisionId: string;
    timestamp: string;
    scores: VersionScoreResult;
  }>>([]);

  // Fetch brief analysis on mount
  const { data: briefData, isLoading: briefLoading, error: briefError } = useQuery<BriefAnalysisResult>({
    queryKey: ['brief-analysis', projectId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/ai/analyze-brief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          brief_text: currentRevision.briefText || 'Client brief for project',
          project_context: currentRevision.metadata 
        }),
      });
      if (!response.ok) throw new Error('Failed to analyze brief');
      const data = await response.json();
      return data as BriefAnalysisResult;
    },
    enabled: !!currentRevision.briefText,
  });

  // Update brief analysis when data changes
  useEffect(() => {
    if (briefData) {
      setBriefAnalysis(briefData);
    }
  }, [briefData]);

  // Handle brief analysis errors
  useEffect(() => {
    if (briefError) {
      setError('Failed to analyze brief. Please ensure brief text is available.');
    }
  }, [briefError]);

  // Score version mutation
  const scoreMutation = useMutation({
    mutationFn: async (revision: Revision) => {
      const response = await fetch(`/api/v1/ai/score-revision/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          revisionId: revision.id,
          briefAnalysisId: briefAnalysis?.provenance.timestamp,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to score version');
      }
      const data = await response.json();
      return data as VersionScoreResult;
    },
    onSuccess: (result, revision) => {
      setScoringResult(result);
      setError(null);
      
      // Add to history
      setScoreHistory(prev => [
        ...prev,
        {
          revisionId: revision.id,
          timestamp: new Date().toISOString(),
          scores: result,
        },
      ]);
      
      // Invalidate related queries
      qc.invalidateQueries({ queryKey: ['scoring-results', projectId] });
      
      onScoreComplete?.(result);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to score version');
    },
  });

  // Score the selected version
  const handleScoreVersion = useCallback(() => {
    if (!briefAnalysis) {
      setError('Brief analysis required. Please analyze the brief first.');
      return;
    }
    scoreMutation.mutate(selectedRevision);
  }, [briefAnalysis, selectedRevision, scoreMutation]);

  // Calculate score difference between two versions
  const compareScores = useCallback((version1: VersionScoreResult, version2: VersionScoreResult): ScoreDiff => {
    return {
      overall: version2.overallScore - version1.overallScore,
      programFit: version2.programFit - version1.programFit,
      daylight: version2.daylight - version1.daylight,
      budgetFit: version2.budgetFit - version1.budgetFit,
    };
  }, []);

  // Format timestamp for display
  const formatTimestamp = useCallback((timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  }, []);

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.2, color: '#65717a' }}>
          AI Version Scoring
        </h2>
        <span style={{ fontSize: 10, color: '#9ca3af' }}>Phase 16A</span>
      </div>

      {/* Brief Analysis Status */}
      <div style={{ padding: 8, borderRadius: 4, background: briefAnalysis ? '#f0fdf4' : '#fef9c3', border: `1px solid ${briefAnalysis ? '#86efac' : '#fde047'}` }}>
        <div style={{ fontWeight: 600, marginBottom: 4, color: briefAnalysis ? '#166534' : '#854d0e' }}>
          {briefLoading ? 'Analyzing brief...' : briefAnalysis ? '✓ Brief analyzed' : '⚠ Brief analysis needed'}
        </div>
        {briefAnalysis && (
          <div style={{ fontSize: 11, color: '#166534' }}>
            {briefAnalysis.spaceProgram.length} spaces identified · {briefAnalysis.constraints.length} constraints
          </div>
        )}
      </div>

      {/* Current Revision Info */}
      <div style={{ padding: 8, borderRadius: 4, background: '#f9fafb', border: '1px solid #e5e7eb' }}>
        <div style={{ fontWeight: 600, marginBottom: 4, color: '#374151' }}>
          Scoring Revision #{selectedRevision.revisionNumber}
        </div>
        <div style={{ fontSize: 11, color: '#6b7280' }}>
          Created: {formatTimestamp(selectedRevision.createdAt)}
        </div>
      </div>

      {/* Score Button */}
      <button
        onClick={handleScoreVersion}
        disabled={scoreMutation.isPending || !briefAnalysis}
        style={{
          padding: '10px 16px',
          border: '1px solid #2e5c62',
          background: scoreMutation.isPending ? '#c7d0d4' : '#2e5c62',
          color: '#fff',
          borderRadius: 5,
          fontWeight: 700,
          fontSize: 12,
          cursor: scoreMutation.isPending ? 'wait' : 'pointer',
          opacity: (!briefAnalysis) ? 0.5 : 1,
        }}
      >
        {scoreMutation.isPending ? 'Scoring...' : 'Score This Version'}
      </button>

      {/* Error Display */}
      {error && (
        <div style={{ padding: 8, borderRadius: 4, background: '#fef2f2', border: '1px solid #fca5a5', color: '#b91c1c', fontSize: 11 }}>
          {error}
        </div>
      )}

      {/* Scoring Results */}
      {scoringResult && (
        <div style={{ padding: 12, borderRadius: 4, background: '#f0fdf4', border: '1px solid #86efac' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: 12, fontWeight: 700, color: '#166534' }}>
            Scoring Results
          </h3>
          
          {/* Overall Score */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: '#166534' }}>Overall Score</span>
              <span style={{ fontWeight: 700, fontSize: 18, color: '#166534' }}>
                {scoringResult.overallScore}/100
              </span>
            </div>
            <div style={{ height: 8, background: '#dcfce7', borderRadius: 4, overflow: 'hidden' }}>
              <div 
                style={{ 
                  height: '100%', 
                  width: `${scoringResult.overallScore}%`, 
                  background: scoringResult.overallScore >= 80 ? '#22c55e' : scoringResult.overallScore >= 60 ? '#84cc16' : '#eab308',
                  transition: 'width 0.3s ease',
                }} 
              />
            </div>
          </div>

          {/* Category Scores */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
            <ScoreBar label="Program Fit" value={scoringResult.programFit} />
            <ScoreBar label="Daylight" value={scoringResult.daylight} />
            <ScoreBar label="Budget Fit" value={scoringResult.budgetFit} />
          </div>

          {/* AI Commentary */}
          <div style={{ marginBottom: 12, padding: 8, background: '#fff', borderRadius: 3, border: '1px solid #bbf7d0' }}>
            <div style={{ fontWeight: 600, marginBottom: 4, color: '#166534', fontSize: 11 }}>AI Commentary</div>
            <div style={{ fontSize: 11, color: '#374151', lineHeight: 1.5 }}>
              {scoringResult.commentary}
            </div>
          </div>

          {/* Zone-Specific Scores */}
          {scoringResult.zoneScores.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6, color: '#166534', fontSize: 11 }}>Zone Analysis</div>
              {scoringResult.zoneScores.map((zone, index) => (
                <div 
                  key={index}
                  style={{ 
                    padding: 6, 
                    marginBottom: 4, 
                    background: '#fff', 
                    borderRadius: 3, 
                    border: '1px solid #bbf7d0',
                    fontSize: 11 
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontWeight: 600, color: '#374151' }}>{zone.zoneName}</span>
                    <span style={{ fontWeight: 700, color: '#166534' }}>{zone.score}/100</span>
                  </div>
                  {zone.notes && (
                    <div style={{ color: '#6b7280', fontSize: 10 }}>{zone.notes}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Provenance Info */}
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #bbf7d0', fontSize: 10, color: '#6b7280' }}>
            Scored by {scoringResult.provenance.model} at {formatTimestamp(scoringResult.provenance.timestamp)}
          </div>
        </div>
      )}

      {/* Score History */}
      {scoreHistory.length > 1 && (
        <div style={{ padding: 12, borderRadius: 4, background: '#f9fafb', border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: 12, fontWeight: 700, color: '#374151' }}>
            Score History ({scoreHistory.length} versions)
          </h3>
          {scoreHistory.slice(-3).reverse().map((item, index) => {
            const diff = index > 0 ? compareScores(scoreHistory[scoreHistory.length - 1 - index].scores, item.scores) : null;
            return (
              <div 
                key={item.revisionId}
                style={{ 
                  padding: 6, 
                  marginBottom: 4, 
                  background: '#fff', 
                  borderRadius: 3, 
                  border: '1px solid #e5e7eb',
                  fontSize: 11 
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                  <span style={{ fontWeight: 600, color: '#374151' }}>
                    Revision {item.revisionId.slice(0, 8)}
                  </span>
                  <span style={{ fontWeight: 700, color: '#166534' }}>
                    {item.scores.overallScore}/100
                  </span>
                </div>
                {diff && (
                  <div style={{ fontSize: 10, color: diff.overall >= 0 ? '#166534' : '#b91c1c' }}>
                    {diff.overall >= 0 ? '+' : ''}{diff.overall} overall · 
                    {diff.programFit >= 0 ? '+' : ''}{diff.programFit} program · 
                    {diff.daylight >= 0 ? '+' : ''}{diff.daylight} daylight
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ── Sub-Components ─────────────────────────────────────────────────────────────

interface ScoreBarProps {
  label: string;
  value: number;
}

function ScoreBar({ label, value }: ScoreBarProps): React.JSX.Element {
  const getColor = (v: number) => {
    if (v >= 80) return '#22c55e';
    if (v >= 60) return '#84cc16';
    return '#eab308';
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <span style={{ fontWeight: 600, color: '#374151', fontSize: 10 }}>{label}</span>
        <span style={{ fontWeight: 700, color: '#166534', fontSize: 10 }}>{value}/100</span>
      </div>
      <div style={{ height: 6, background: '#dcfce7', borderRadius: 3, overflow: 'hidden' }}>
        <div 
          style={{ 
            height: '100%', 
            width: `${value}%`, 
            background: getColor(value),
            transition: 'width 0.3s ease',
          }} 
        />
      </div>
    </div>
  );
}