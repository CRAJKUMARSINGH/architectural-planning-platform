import React, { useState } from 'react';
import { ConceptCanvas } from './ConceptCanvas';
import type { CanvasBlock, ConceptVersion, Suggestion } from '../types';
import {
  useBriefAnalysis, useAnalyzeBrief,
  useVersions, useCreateVersion, useDeleteVersion, useScoreVersion,
  useSuggestions, useGenerateSuggestions, useUpdateSuggestion,
} from '../api/hooks';
import { exportProject } from '../api/client';

// ── Promote-to-Model: POST /api/v1/projects/{id}/jobs type=generate ──────────
async function promoteToModel(projectId: string, blocks: CanvasBlock[], floors: string[]): Promise<{ jobId: string }> {
  const res = await fetch(`/api/v1/projects/${projectId}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_type: 'generate',
      payload: {
        source: 'concept_canvas',
        floors,
        blocks,
        promotedAt: new Date().toISOString(),
      },
    }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Promote failed: ${res.status} ${body}`);
  }
  const job = await res.json();
  return { jobId: job.id };
}

interface Props {
  projectId: string;
  projectName: string;
  initialBrief?: string;
  initialSiteAddress?: string;
  initialBudget?: number;
  initialSiteSizeSqm?: number;
  initialStylePreferences?: string;
}

const pill = (color: string) => ({
  display: 'inline-block', padding: '1px 8px', borderRadius: 99, fontSize: 10,
  fontWeight: 700, background: color, color: '#fff', textTransform: 'uppercase' as const,
  letterSpacing: '0.05em',
});

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2, color: '#64748b' }}>
        <span>{label}</span><span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{Math.round(value)}%</span>
      </div>
      <div style={{ height: 4, background: '#e2e8f0', borderRadius: 2 }}>
        <div style={{ height: '100%', borderRadius: 2, background: value >= 70 ? '#10b981' : value >= 40 ? '#f59e0b' : '#ef4444', width: `${value}%` }} />
      </div>
    </div>
  );
}

export function WorkflowPanel({ projectId, projectName, initialBrief = '', initialSiteAddress = '', initialBudget, initialSiteSizeSqm, initialStylePreferences = '' }: Props) {
  const [leftTab, setLeftTab] = useState<'brief' | 'analysis'>('brief');
  const [rightTab, setRightTab] = useState<'versions' | 'suggestions'>('versions');
  const [briefText, setBriefText] = useState(initialBrief);
  const [siteAddress, setSiteAddress] = useState(initialSiteAddress);
  const [budget, setBudget] = useState(initialBudget?.toString() ?? '');
  const [siteSizeSqm, setSiteSizeSqm] = useState(initialSiteSizeSqm?.toString() ?? '');
  const [stylePrefs, setStylePrefs] = useState(initialStylePreferences);
  const [blocks, setBlocks] = useState<CanvasBlock[]>([]);
  const [floors, setFloors] = useState<string[]>(['Ground Floor']);
  const [activeFloor, setActiveFloor] = useState('Ground Floor');
  const [activeVersionId, setActiveVersionId] = useState<string | null>(null);
  const [newVersionName, setNewVersionName] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState('');
  const [isPromoting, setIsPromoting] = useState(false);
  const [promoteMsg, setPromoteMsg] = useState('');

  const { data: analysis } = useBriefAnalysis(projectId);
  const { mutate: doAnalyze, isPending: analyzing } = useAnalyzeBrief(projectId);
  const { data: versions } = useVersions(projectId);
  const { mutate: doCreateVersion, isPending: creatingVersion } = useCreateVersion(projectId);
  const { mutate: doDeleteVersion } = useDeleteVersion(projectId);
  const { mutate: doScoreVersion, isPending: scoring } = useScoreVersion(projectId);
  const { data: suggestions } = useSuggestions(projectId);
  const { mutate: doGenerate, isPending: generating } = useGenerateSuggestions(projectId);
  const { mutate: doUpdateSuggestion } = useUpdateSuggestion(projectId);

  const handleAnalyze = () => {
    doAnalyze({ clientBrief: briefText, siteAddress: siteAddress || undefined,
      budget: budget ? parseFloat(budget) : undefined,
      siteSizeSqm: siteSizeSqm ? parseFloat(siteSizeSqm) : undefined,
      stylePreferences: stylePrefs || undefined });
  };

  const handleSaveVersion = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVersionName.trim()) return;
    doCreateVersion({ name: newVersionName, floors, blocks }, {
      onSuccess: (v) => { setNewVersionName(''); setActiveVersionId(v.id); },
    });
  };

  const loadVersion = (v: ConceptVersion) => {
    setActiveVersionId(v.id);
    setBlocks(v.blocks);
    setFloors(v.floors.length ? v.floors : ['Ground Floor']);
    setActiveFloor(v.floors[0] ?? 'Ground Floor');
  };

  const handleExport = async () => {
    setIsExporting(true); setExportMsg('');
    try {
      const result = await exportProject(projectId);
      const blob = new Blob([result.markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${projectName}-concept.md`;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
      setExportMsg('Downloaded!');
    } catch { setExportMsg('Export failed'); }
    finally { setIsExporting(false); }
  };

  const handlePromote = async () => {
    if (!blocks.length) { setPromoteMsg('Add zones to the canvas first.'); return; }
    if (!confirm('Promote this concept canvas to a geometry Job? The architect will review the result before it becomes authoritative.')) return;
    setIsPromoting(true); setPromoteMsg('');
    try {
      const { jobId } = await promoteToModel(projectId, blocks, floors);
      setPromoteMsg(`Job queued: ${jobId.slice(0, 8)}…`);
    } catch (e: unknown) {
      setPromoteMsg(e instanceof Error ? e.message : 'Promote failed');
    } finally { setIsPromoting(false); }
  };

  const newSuggestions = suggestions?.filter((s: Suggestion) => s.status === 'new') ?? [];

  const panelBase: React.CSSProperties = { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: '#fff', borderRight: '1px solid #e2e8f0' };
  const tabBtn = (active: boolean): React.CSSProperties => ({
    flex: 1, padding: '8px 0', fontSize: 11, fontWeight: active ? 700 : 400,
    background: active ? '#f8fafc' : '#fff', border: 'none', borderBottom: active ? '2px solid #3b82f6' : '2px solid transparent',
    cursor: 'pointer', color: active ? '#1e293b' : '#64748b',
  });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 280px', height: '100%', overflow: 'hidden' }}>

      {/* ── LEFT: Brief + Analysis ─────────────────────────────────────── */}
      <div style={panelBase}>
        <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0' }}>
          <button style={tabBtn(leftTab === 'brief')} onClick={() => setLeftTab('brief')}>Brief</button>
          <button style={{ ...tabBtn(leftTab === 'analysis'), position: 'relative' }} onClick={() => setLeftTab('analysis')}>
            Analysis {analysis && <span style={{ ...pill('#10b981'), marginLeft: 4, fontSize: 8 }}>✓</span>}
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
          {leftTab === 'brief' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                { label: 'Client Brief *', val: briefText, set: setBriefText, multi: true },
                { label: 'Site Address', val: siteAddress, set: setSiteAddress, multi: false },
                { label: 'Style Preferences', val: stylePrefs, set: setStylePrefs, multi: false },
              ].map(f => (
                <label key={f.label} style={{ fontSize: 11, fontWeight: 600, color: '#475569' }}>
                  {f.label}
                  {f.multi ? (
                    <textarea value={f.val} onChange={e => f.set(e.target.value)} rows={5}
                      style={{ display: 'block', width: '100%', marginTop: 3, padding: '6px 8px', fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 4, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
                  ) : (
                    <input value={f.val} onChange={e => f.set(e.target.value)}
                      style={{ display: 'block', width: '100%', marginTop: 3, padding: '6px 8px', fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 4, fontFamily: 'inherit', boxSizing: 'border-box' }} />
                  )}
                </label>
              ))}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {[{ label: 'Site SQM', val: siteSizeSqm, set: setSiteSizeSqm }, { label: 'Budget', val: budget, set: setBudget }].map(f => (
                  <label key={f.label} style={{ fontSize: 11, fontWeight: 600, color: '#475569' }}>
                    {f.label}
                    <input type="number" value={f.val} onChange={e => f.set(e.target.value)}
                      style={{ display: 'block', width: '100%', marginTop: 3, padding: '6px 8px', fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 4, fontFamily: 'monospace', boxSizing: 'border-box' }} />
                  </label>
                ))}
              </div>
              <button onClick={handleAnalyze} disabled={analyzing || !briefText.trim()}
                style={{ padding: '9px 0', background: analyzing ? '#94a3b8' : '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: analyzing || !briefText.trim() ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 700, marginTop: 4 }}>
                {analyzing ? '⟳ Analyzing...' : analysis ? '↺ Re-analyze with AI' : '✦ Analyze Brief with AI'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {!analysis ? (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0', fontSize: 12 }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>✦</div>
                  Click "Analyze Brief with AI" on the Brief tab to get started.
                </div>
              ) : (
                <>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Summary</div>
                    <p style={{ fontSize: 12, color: '#374151', lineHeight: 1.6, background: '#f8fafc', padding: '8px 10px', borderRadius: 6, border: '1px solid #e2e8f0', margin: 0 }}>{analysis.summary}</p>
                  </div>
                  {analysis.spaceProgram.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Space Program</div>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                        <thead><tr style={{ background: '#f1f5f9' }}><th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Space</th><th style={{ textAlign: 'right', padding: '4px 6px', fontWeight: 600 }}>SQM</th></tr></thead>
                        <tbody>
                          {analysis.spaceProgram.map((item, i) => (
                            <tr key={i} style={{ borderTop: '1px solid #f1f5f9' }}>
                              <td style={{ padding: '4px 6px' }}>{item.name} {item.priority === 'nice_to_have' && <span style={pill('#94a3b8')}>opt</span>}</td>
                              <td style={{ padding: '4px 6px', textAlign: 'right', fontFamily: 'monospace' }}>{item.sqm}</td>
                            </tr>
                          ))}
                          <tr style={{ borderTop: '2px solid #e2e8f0', fontWeight: 700 }}>
                            <td style={{ padding: '4px 6px', fontSize: 10, color: '#64748b' }}>Total</td>
                            <td style={{ padding: '4px 6px', textAlign: 'right', fontFamily: 'monospace' }}>{analysis.spaceProgram.reduce((s, i) => s + i.sqm, 0)}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}
                  {analysis.constraints.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#ef4444', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>⚠ Constraints</div>
                      {analysis.constraints.map((c, i) => <div key={i} style={{ fontSize: 11, padding: '4px 8px', background: '#fef2f2', borderLeft: '3px solid #fca5a5', marginBottom: 4, color: '#374151' }}>{c}</div>)}
                    </div>
                  )}
                  {analysis.opportunities.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#d97706', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>✦ Opportunities</div>
                      {analysis.opportunities.map((o, i) => <div key={i} style={{ fontSize: 11, padding: '4px 8px', background: '#fffbeb', borderLeft: '3px solid #fcd34d', marginBottom: 4, color: '#374151' }}>{o}</div>)}
                    </div>
                  )}
                  {analysis.openQuestions.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#7c3aed', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>? Open Questions</div>
                      {analysis.openQuestions.map((q, i) => <div key={i} style={{ fontSize: 11, padding: '4px 8px', background: '#f5f3ff', borderLeft: '3px solid #c4b5fd', marginBottom: 4, color: '#374151' }}>{q}</div>)}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── CENTRE: Canvas ──────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: '#f8fafc' }}>
        <div style={{ flex: 1, padding: 8, overflow: 'hidden' }}>
          <ConceptCanvas blocks={blocks} onChange={setBlocks} floors={floors} activeFloor={activeFloor} onFloorsChange={setFloors} onActiveFloorChange={setActiveFloor} />
        </div>
        <div style={{ height: 48, background: '#fff', borderTop: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', padding: '0 12px', gap: 10, flexShrink: 0 }}>
          <span style={{ fontSize: 11, fontFamily: 'monospace', background: '#f1f5f9', padding: '2px 8px', borderRadius: 99, color: '#475569' }}>{blocks.length} zones</span>
          <span style={{ fontSize: 11, color: '#94a3b8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {activeVersionId ? `Editing: ${versions?.find((v: ConceptVersion) => v.id === activeVersionId)?.name ?? ''}` : 'Unsaved concept'}
          </span>
          <form onSubmit={handleSaveVersion} style={{ display: 'flex', gap: 6 }}>
            <input placeholder="Version name…" value={newVersionName} onChange={e => setNewVersionName(e.target.value)}
              style={{ width: 140, padding: '4px 8px', fontSize: 11, border: '1px solid #e2e8f0', borderRadius: 4 }} />
            <button type="submit" disabled={creatingVersion || !newVersionName.trim()}
              style={{ padding: '4px 12px', fontSize: 11, fontWeight: 700, background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
              {creatingVersion ? '…' : '💾 Save'}
            </button>
          </form>
          <button onClick={handleExport} disabled={isExporting}
            style={{ padding: '4px 12px', fontSize: 11, fontWeight: 700, background: '#0f172a', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
            {isExporting ? '…' : '↓ Export'}
          </button>
          {exportMsg && <span style={{ fontSize: 11, color: '#10b981' }}>{exportMsg}</span>}
          <button onClick={handlePromote} disabled={isPromoting || !blocks.length}
            title="Queue a geometry Job from this concept canvas. Requires architect review before becoming authoritative."
            style={{ padding: '4px 12px', fontSize: 11, fontWeight: 700, background: blocks.length ? '#7c3aed' : '#e2e8f0', color: blocks.length ? '#fff' : '#94a3b8', border: 'none', borderRadius: 4, cursor: blocks.length ? 'pointer' : 'not-allowed', marginLeft: 4 }}>
            {isPromoting ? '…' : '⬆ Promote'}
          </button>
          {promoteMsg && <span style={{ fontSize: 11, color: promoteMsg.includes('Job') ? '#7c3aed' : '#ef4444', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{promoteMsg}</span>}
        </div>
      </div>

      {/* ── RIGHT: Versions + Suggestions ──────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: '#fff', borderLeft: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', flexShrink: 0 }}>
          <button style={tabBtn(rightTab === 'versions')} onClick={() => setRightTab('versions')}>Versions</button>
          <button style={{ ...tabBtn(rightTab === 'suggestions'), position: 'relative' }} onClick={() => setRightTab('suggestions')}>
            AI Insights {newSuggestions.length > 0 && <span style={{ ...pill('#3b82f6'), marginLeft: 4, fontSize: 8 }}>{newSuggestions.length}</span>}
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
          {rightTab === 'versions' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {!versions?.length ? (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 8px', fontSize: 12, border: '2px dashed #e2e8f0', borderRadius: 8, marginTop: 8 }}>
                  No saved versions yet.<br />Draft a concept and save it.
                </div>
              ) : versions.map((v: ConceptVersion) => (
                <div key={v.id} style={{ border: `2px solid ${activeVersionId === v.id ? '#3b82f6' : '#e2e8f0'}`, borderRadius: 8, overflow: 'hidden', background: activeVersionId === v.id ? '#eff6ff' : '#fff' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderBottom: '1px solid #f1f5f9', background: '#f8fafc' }}>
                    <div>
                      <div onClick={() => loadVersion(v)} style={{ fontSize: 12, fontWeight: 700, cursor: 'pointer', color: '#1e293b' }}>{v.name}</div>
                      <div style={{ fontSize: 9, color: '#94a3b8', fontFamily: 'monospace', textTransform: 'uppercase' }}>
                        {new Date(v.createdAt).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => loadVersion(v)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#3b82f6', fontSize: 14 }}>⊞</button>
                      <button onClick={() => doDeleteVersion(v.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', fontSize: 14 }}>✕</button>
                    </div>
                  </div>
                  <div style={{ padding: '8px 10px' }}>
                    {v.overallScore === null ? (
                      <button onClick={() => doScoreVersion(v.id)} disabled={scoring}
                        style={{ width: '100%', padding: '6px 0', fontSize: 11, fontWeight: 700, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 4, cursor: 'pointer', color: '#475569' }}>
                        {scoring ? '⟳ Scoring…' : '✦ Score with AI'}
                      </button>
                    ) : (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                          <span style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Overall</span>
                          <span style={{ fontSize: 20, fontWeight: 900, color: '#3b82f6', lineHeight: 1 }}>{Math.round(v.overallScore)}%</span>
                        </div>
                        <ScoreBar label="Program Fit" value={v.programFitScore} />
                        <ScoreBar label="Daylight" value={v.daylightScore} />
                        <ScoreBar label="Budget Fit" value={v.budgetFitScore} />
                        {v.aiCommentary && <p style={{ fontSize: 10, color: '#64748b', fontStyle: 'italic', margin: '8px 0 0', padding: '6px 8px', background: '#f8fafc', borderRadius: 4, border: '1px solid #e2e8f0' }}>"{v.aiCommentary}"</p>}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button onClick={() => doGenerate()} disabled={generating}
                style={{ width: '100%', padding: '9px 0', fontSize: 12, fontWeight: 700, background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: generating ? 'not-allowed' : 'pointer' }}>
                {generating ? '⟳ Generating…' : '✦ Refresh AI Ideas'}
              </button>
              {!suggestions?.length ? (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '32px 8px', fontSize: 12 }}>Click the button above to generate ideas.</div>
              ) : suggestions.map((s: Suggestion) => (
                <div key={s.id} style={{ padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: 6, opacity: s.status !== 'new' ? 0.5 : 1, background: s.status === 'accepted' ? '#f0fdf4' : s.status === 'dismissed' ? '#fafafa' : '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ ...pill(s.category === 'budget' ? '#7c3aed' : s.category === 'daylight' ? '#d97706' : s.category === 'program' ? '#1d4ed8' : '#475569'), fontSize: 9 }}>{s.category}</span>
                    {s.status === 'new' && (
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button onClick={() => doUpdateSuggestion({ id: s.id, status: 'accepted' })}
                          style={{ background: '#d1fae5', border: '1px solid #6ee7b7', borderRadius: 4, cursor: 'pointer', padding: '2px 6px', fontSize: 11, color: '#065f46' }}>✓</button>
                        <button onClick={() => doUpdateSuggestion({ id: s.id, status: 'dismissed' })}
                          style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 4, cursor: 'pointer', padding: '2px 6px', fontSize: 11, color: '#991b1b' }}>✕</button>
                      </div>
                    )}
                  </div>
                  <p style={{ margin: 0, fontSize: 11, color: '#374151', lineHeight: 1.5 }}>{s.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
