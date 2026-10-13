import React, { useCallback, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface BriefAnalysisResult {
  summary: string;
  spaceProgram: Array<{ name: string; sqm: number; priority: string; notes: string }>;
  constraints: string[];
  opportunities: string[];
  openQuestions: string[];
  provenance: { model: string; timestamp: string; briefLength: number; contextKeys: string[] };
  modelVersion: string;
}

export interface VersionScoreResult {
  overallScore: number;
  programFit: number;
  daylight: number;
  budgetFit: number;
  commentary: string;
  zoneScores: Array<{ zoneName: string; score: number; notes: string }>;
  provenance: { model: string; timestamp: string; versionId: string; briefAnalysisId: string };
  modelVersion: string;
}

export interface Revision {
  id: string;
  revisionNumber: number;
  createdAt: string;
  briefText?: string;
  metadata?: { siteSize?: number; budget?: number; stylePreferences?: string[] };
}

interface Props {
  projectId: string;
  currentRevision: Revision;
  onScoreComplete?: (result: VersionScoreResult) => void;
}

interface ScoreDiff {
  overall: number;
  programFit: number;
  daylight: number;
  budgetFit: number;
}

/* ── ScoreBar sub-component ───────────────────────────────────────────────── */
interface ScoreBarProps { label: string; value: number }

function ScoreBar({ label, value }: ScoreBarProps): React.JSX.Element {
  const color = value >= 80 ? '#22c55e' : value >= 60 ? '#84cc16' : '#eab308';
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <span style={{ fontWeight: 600, color: '#374151', fontSize: 10 }}>{label}</span>
        {/* WCAG 1.4.1: value conveyed as text, not colour alone */}
        <span style={{ fontWeight: 700, color: '#166534', fontSize: 10 }}>{value}/100</span>
      </div>
      {/* WCAG 4.1.2: role="progressbar" + aria value attributes */}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${value} out of 100`}
        style={{ height: 6, background: '#dcfce7', borderRadius: 3, overflow: 'hidden' }}
      >
        <div style={{ height: '100%', width: `${value}%`, background: color, transition: 'width 0.3s ease' }} />
      </div>
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────────────────── */
export function VersionScoringPanel({ projectId, currentRevision, onScoreComplete }: Props): React.JSX.Element {
  const qc = useQueryClient();
  const [briefAnalysis, setBriefAnalysis]   = useState<BriefAnalysisResult | null>(null);
  const [scoringResult, setScoringResult]   = useState<VersionScoreResult | null>(null);
  const [selectedRevision]                  = useState<Revision>(currentRevision);
  const [error, setError]                   = useState<string | null>(null);
  const [scoreHistory, setScoreHistory]     = useState<Array<{ revisionId: string; timestamp: string; scores: VersionScoreResult }>>([]);

  const { data: briefData, isLoading: briefLoading, error: briefError } = useQuery<BriefAnalysisResult>({
    queryKey: ['brief-analysis', projectId],
    queryFn: async () => {
      const response = await fetch('/api/v1/ai/analyze-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_text: currentRevision.briefText ?? 'Client brief for project', project_context: currentRevision.metadata }),
      });
      if (!response.ok) throw new Error('Failed to analyze brief');
      return (await response.json()) as BriefAnalysisResult;
    },
    enabled: !!currentRevision.briefText,
  });

  useEffect(() => { if (briefData) setBriefAnalysis(briefData); }, [briefData]);
  useEffect(() => { if (briefError) setError('Failed to analyze brief. Please ensure brief text is available.'); }, [briefError]);

  const scoreMutation = useMutation({
    mutationFn: async (revision: Revision) => {
      const response = await fetch(`/api/v1/ai/score-revision/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ revisionId: revision.id, briefAnalysisId: briefAnalysis?.provenance.timestamp }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(errorData.detail ?? 'Failed to score version');
      }
      return (await response.json()) as VersionScoreResult;
    },
    onSuccess: (result, revision) => {
      setScoringResult(result);
      setError(null);
      setScoreHistory(prev => [...prev, { revisionId: revision.id, timestamp: new Date().toISOString(), scores: result }]);
      qc.invalidateQueries({ queryKey: ['scoring-results', projectId] });
      onScoreComplete?.(result);
    },
    onError: (err: Error) => { setError(err.message ?? 'Failed to score version'); },
  });

  const handleScoreVersion = useCallback(() => {
    if (!briefAnalysis) { setError('Brief analysis required. Please analyze the brief first.'); return; }
    scoreMutation.mutate(selectedRevision);
  }, [briefAnalysis, selectedRevision, scoreMutation]);

  const compareScores = useCallback((v1: VersionScoreResult, v2: VersionScoreResult): ScoreDiff => ({
    overall: v2.overallScore - v1.overallScore,
    programFit: v2.programFit - v1.programFit,
    daylight: v2.daylight - v1.daylight,
    budgetFit: v2.budgetFit - v1.budgetFit,
  }), []);

  const formatTimestamp = useCallback((ts: string) => new Date(ts).toLocaleString(), []);

  const overallColor = scoringResult
    ? scoringResult.overallScore >= 80 ? '#22c55e' : scoringResult.overallScore >= 60 ? '#84cc16' : '#eab308'
    : '#22c55e';

  return (
    /* WCAG 1.3.1: section needs accessible name */
    <section aria-label="AI version scoring" style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 12 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.2, color: '#65717a' }}>
          AI Version Scoring
        </h2>
        <span style={{ fontSize: 10, color: '#6b7280' }} aria-label="Phase 16A">Phase 16A</span>
      </div>

      {/* Brief Analysis Status — WCAG 4.1.2: status conveyed as text */}
      <div
        aria-live="polite"
        style={{ padding: 8, borderRadius: 4, background: briefAnalysis ? '#f0fdf4' : '#fef9c3', border: `1px solid ${briefAnalysis ? '#86efac' : '#fde047'}` }}
      >
        <div style={{ fontWeight: 600, marginBottom: 4, color: briefAnalysis ? '#166534' : '#854d0e' }}>
          {briefLoading ? 'Analyzing brief…' : briefAnalysis ? '✓ Brief analyzed' : '⚠ Brief analysis needed'}
        </div>
        {briefAnalysis && (
          <div style={{ fontSize: 11, color: '#166534' }}>
            {briefAnalysis.spaceProgram.length} spaces identified · {briefAnalysis.constraints.length} constraints
          </div>
        )}
      </div>

      {/* Current Revision */}
      <div style={{ padding: 8, borderRadius: 4, background: '#f9fafb', border: '1px solid #e5e7eb' }}>
        <div style={{ fontWeight: 600, marginBottom: 4, color: '#374151' }}>
          Scoring Revision #{selectedRevision.revisionNumber}
        </div>
        <div style={{ fontSize: 11, color: '#6b7280' }}>
          Created: {formatTimestamp(selectedRevision.createdAt)}
        </div>
      </div>

      {/* Score Button — WCAG 4.1.2: aria-disabled when not ready; aria-busy when loading */}
      <button
        type="button"
        onClick={handleScoreVersion}
        disabled={scoreMutation.isPending || !briefAnalysis}
        aria-disabled={!briefAnalysis}
        aria-busy={scoreMutation.isPending}
        style={{
          padding: '10px 16px',
          border: '1px solid #2e5c62',
          background: scoreMutation.isPending ? '#c7d0d4' : '#2e5c62',
          color: '#fff',
          borderRadius: 5,
          fontWeight: 700,
          fontSize: 12,
          cursor: scoreMutation.isPending ? 'wait' : 'pointer',
          opacity: !briefAnalysis ? 0.5 : 1,
        }}
      >
        {scoreMutation.isPending ? 'Scoring…' : 'Score This Version'}
      </button>

      {/* Error — WCAG 3.3.1: role="alert" announces to screen readers */}
      {error && (
        <div role="alert" style={{ padding: 8, borderRadius: 4, background: '#fef2f2', border: '1px solid #fca5a5', color: '#b91c1c', fontSize: 11 }}>
          {error}
        </div>
      )}

      {/* Scoring Results */}
      {scoringResult && (
        <div style={{ padding: 12, borderRadius: 4, background: '#f0fdf4', border: '1px solid #86efac' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: 12, fontWeight: 700, color: '#166534' }}>
            Scoring Results
          </h3>

          {/* Overall score — WCAG 4.1.2: role="progressbar" */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: '#166534' }}>Overall Score</span>
              <span style={{ fontWeight: 700, fontSize: 18, color: '#166534' }}>
                {scoringResult.overallScore}/100
              </span>
            </div>
            <div
              role="progressbar"
              aria-valuenow={scoringResult.overallScore}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Overall score: ${scoringResult.overallScore} out of 100`}
              style={{ height: 8, background: '#dcfce7', borderRadius: 4, overflow: 'hidden' }}
            >
              <div style={{ height: '100%', width: `${scoringResult.overallScore}%`, background: overallColor, transition: 'width 0.3s ease' }} />
            </div>
          </div>

          {/* Category Scores */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
            <ScoreBar label="Program Fit" value={scoringResult.programFit} />
            <ScoreBar label="Daylight"    value={scoringResult.daylight} />
            <ScoreBar label="Budget Fit"  value={scoringResult.budgetFit} />
          </div>

          {/* AI Commentary */}
          <div style={{ marginBottom: 12, padding: 8, background: '#fff', borderRadius: 3, border: '1px solid #bbf7d0' }}>
            <div style={{ fontWeight: 600, marginBottom: 4, color: '#166534', fontSize: 11 }}>AI Commentary</div>
            <div style={{ fontSize: 11, color: '#374151', lineHeight: 1.5 }}>{scoringResult.commentary}</div>
          </div>

          {/* Zone Scores */}
          {scoringResult.zoneScores.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6, color: '#166534', fontSize: 11 }}>Zone Analysis</div>
              {scoringResult.zoneScores.map((zone, i) => (
                <div key={i} style={{ padding: 6, marginBottom: 4, background: '#fff', borderRadius: 3, border: '1px solid #bbf7d0', fontSize: 11 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontWeight: 600, color: '#374151' }}>{zone.zoneName}</span>
                    <span style={{ fontWeight: 700, color: '#166534' }}>{zone.score}/100</span>
                  </div>
                  {zone.notes && <div style={{ color: '#6b7280', fontSize: 10 }}>{zone.notes}</div>}
                </div>
              ))}
            </div>
          )}

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
            const diff = index > 0
              ? compareScores(scoreHistory[scoreHistory.length - 1 - index].scores, item.scores)
              : null;
            const diffSign = diff && diff.overall >= 0 ? '+' : '';
            return (
              <div key={item.revisionId} style={{ padding: 6, marginBottom: 4, background: '#fff', borderRadius: 3, border: '1px solid #e5e7eb', fontSize: 11 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                  <span style={{ fontWeight: 600, color: '#374151' }}>Revision {item.revisionId.slice(0, 8)}</span>
                  <span style={{ fontWeight: 700, color: '#166534' }}>{item.scores.overallScore}/100</span>
                </div>
                {diff && (
                  <div style={{ fontSize: 10, color: diff.overall >= 0 ? '#166534' : '#b91c1c' }}>
                    {/* WCAG 1.4.1: change conveyed as text with + / − prefix, not colour alone */}
                    {diffSign}{diff.overall} overall · {diff.programFit >= 0 ? '+' : ''}{diff.programFit} program · {diff.daylight >= 0 ? '+' : ''}{diff.daylight} daylight
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
