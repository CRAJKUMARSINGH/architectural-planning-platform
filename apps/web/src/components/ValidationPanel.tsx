import React from 'react';
import { useQuery } from '@tanstack/react-query';

interface Props {
  projectId: string;
  level: 'GF' | 'FF';
}

type Finding = {
  id: string;
  severity: string;
  rule: string;
  message: string;
  suggestedFixes: string[];
};

type Analysis = {
  status: string;
  findingCounts: Record<string, number>;
  findings: Finding[];
  week5?: { status: string; findingCounts: Record<string, number> };
  week6?: { status: string; findingCounts: Record<string, number> };
};

export function ValidationPanel({ projectId, level }: Props): React.JSX.Element {
  const query = useQuery<Analysis>({
    queryKey: ['analysis-validation', projectId, level],
    queryFn: async () => {
      const response = await fetch(`/analysis?level=${level}`);
      if (!response.ok) throw new Error('Analysis API unavailable');
      return (await response.json()) as Analysis;
    },
  });
  const result = query.data;
  const findings = result?.findings ?? [];
  const blockers = findings.filter((f) => f.severity === 'BLOCKER');
  const errors   = findings.filter((f) => f.severity === 'ERROR');
  const warnings = findings.filter((f) => f.severity === 'WARNING');

  /* WCAG 1.4.1: status conveys meaning by text + colour, not colour alone */
  const pillStyle = (ok: boolean): React.CSSProperties => ({
    display: 'inline-block',
    padding: '3px 10px',
    fontSize: 10,
    fontWeight: 700,
    borderRadius: 999,
    background: ok ? '#e4efe6' : '#f3dcd7',
    color: ok ? '#2d5c36' : '#8b3c32',
  });

  const isPass = !query.isError && blockers.length === 0 && errors.length === 0;

  return (
    <section aria-label="Validation panel — Week 3–6 checks">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <h2 style={{ margin: 0, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.2, color: '#65717a' }}>
          Week 3–6 Validation
        </h2>
        {/* WCAG 4.1.2: type="button" required on all buttons */}
        <button
          type="button"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
          aria-busy={query.isFetching}
          style={{
            fontSize: 10,
            padding: '3px 10px',
            border: '1px solid #aebac0',
            background: '#ffffff',
            borderRadius: 999,
            cursor: 'pointer',
          }}
        >
          {query.isFetching ? 'Running…' : 'Re-run'}
        </button>
      </div>

      {/* WCAG 1.4.1: text label carries status meaning, colour is supplemental */}
      <div style={{ marginBottom: 10 }} aria-live="polite" aria-atomic="true">
        <span style={pillStyle(isPass)}>
          {query.isLoading
            ? 'LOADING'
            : blockers.length || errors.length
              ? `${blockers.length + errors.length} BLOCKING`
              : 'PASS'}
        </span>
        {warnings.length > 0 && (
          <span style={{ ...pillStyle(false), marginLeft: 6, background: '#faf0de', color: '#7a5a12' }}>
            {warnings.length} WARNING{warnings.length !== 1 ? 'S' : ''}
          </span>
        )}
      </div>

      {(result?.week5 ?? result?.week6) && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          {result?.week5 && (
            <span style={pillStyle(result.week5.status === 'pass')}>
              W5 {result.week5.status === 'pass' ? 'PASS' : 'REVIEW'}
            </span>
          )}
          {result?.week6 && (
            <span style={pillStyle(result.week6.status === 'pass')}>
              W6 {result.week6.status === 'pass' ? 'PASS' : 'REVIEW'}
            </span>
          )}
        </div>
      )}

      {/* WCAG 3.3.1: errors announced via role="alert" */}
      {query.isError && (
        <div role="alert" style={{ fontSize: 11, color: '#8b3c32', marginBottom: 8 }}>
          The authoritative analysis API could not be reached.
        </div>
      )}

      {findings.slice(0, 8).map((finding) => (
        <div
          key={finding.id}
          style={{
            fontSize: 11,
            color: finding.severity === 'WARNING' ? '#7a5a12' : '#8b3c32',
            padding: '4px 0',
            lineHeight: 1.35,
          }}
        >
          <strong>{finding.severity}</strong> · {finding.message}
          {finding.suggestedFixes[0] && (
            <div style={{ color: '#65717a', paddingLeft: 10 }}>
              ↳ {finding.suggestedFixes[0]}
            </div>
          )}
        </div>
      ))}
      {findings.length > 8 && (
        <div style={{ fontSize: 10, color: '#65717a' }}>
          Showing 8 of {findings.length} findings for {level}.
        </div>
      )}
      {!query.isLoading && !query.isError && findings.length === 0 && (
        <div style={{ fontSize: 11, color: '#2d5c36' }}>All Week 3–6 gates cleared.</div>
      )}
    </section>
  );
}
