/**
 * CommandPanel — Phase 7 typed command dispatch UI.
 *
 * Renders inside the right sidebar next to PropertyInspector.
 * Allows the user to:
 *  1. Preview a command (dry-run, shows findings).
 *  2. Commit a command (persists a new revision, refreshes viewport).
 *
 * Supported operations (subset matching Phase 2 CommandRunner):
 *  - move-opening   (door/window repositioning)
 *  - resize-opening (door/window width change)
 *  - resize-space   (room bounding box edit)
 *  - set-site-orientation (north arrow)
 *  - add-space      (new room)
 *
 * The component uses useRevisions to read the current revision number
 * so it can set a correct If-Match header and baseRevision.
 */
import React, { useCallback, useId, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  type CommandEnvelopeInput,
  type CommandResult,
  type Finding,
  useCommitCommand,
  usePreviewCommand,
} from './useCommandDispatch';

// ── Types ─────────────────────────────────────────────────────────────────────

interface RevisionEntry {
  id: string;
  revision_number: number;
  validation_state?: string;
}

interface Props {
  projectId: string;
  level: 'GF' | 'FF';
  /** The currently selected object id (e.g. a space or opening id). */
  selectedId: string | null;
}

// ── Operation definitions ─────────────────────────────────────────────────────

interface OpField {
  key: string;
  label: string;
  type: 'text' | 'number';
  placeholder?: string;
}

interface OpDef {
  label: string;
  objectKey?: string; // parameter key that holds the selected id
  fields: OpField[];
}

const OPERATIONS: Record<string, OpDef> = {
  'move-opening': {
    label: 'Move Opening',
    objectKey: 'openingId',
    fields: [
      { key: 'openingId', label: 'Opening ID', type: 'text', placeholder: 'e.g. door-main' },
      { key: 'wall', label: 'Wall', type: 'text', placeholder: 'north | south | east | west' },
      { key: 'offset', label: 'Offset (inches)', type: 'number', placeholder: '0' },
    ],
  },
  'resize-opening': {
    label: 'Resize Opening',
    objectKey: 'openingId',
    fields: [
      { key: 'openingId', label: 'Opening ID', type: 'text' },
      { key: 'wall', label: 'Wall', type: 'text', placeholder: 'north | south | east | west' },
      { key: 'offset', label: 'Offset (inches)', type: 'number', placeholder: '0' },
      { key: 'width', label: 'Width (inches)', type: 'number', placeholder: '36' },
    ],
  },
  'resize-space': {
    label: 'Resize Space',
    objectKey: 'spaceId',
    fields: [
      { key: 'spaceId', label: 'Space ID', type: 'text', placeholder: 'e.g. GF-04' },
      { key: 'rect', label: 'Rect [x0,y0,x1,y1] (inches)', type: 'text', placeholder: '0,0,540,720' },
    ],
  },
  'set-site-orientation': {
    label: 'Set Site Orientation',
    fields: [
      { key: 'north', label: 'North direction', type: 'text', placeholder: 'up | down | left | right' },
    ],
  },
  'add-space': {
    label: 'Add Space',
    fields: [
      { key: 'spaceId', label: 'Space ID', type: 'text', placeholder: 'GF-NEW' },
      { key: 'levelId', label: 'Level', type: 'text', placeholder: 'GF' },
      { key: 'name', label: 'Name', type: 'text', placeholder: 'New Room' },
      { key: 'rect', label: 'Rect [x0,y0,x1,y1]', type: 'text', placeholder: '0,0,120,180' },
    ],
  },
};

// ── Styles ─────────────────────────────────────────────────────────────────────

const S = {
  panel: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 10,
    fontSize: 12,
  },
  heading: {
    margin: 0,
    fontSize: 12,
    textTransform: 'uppercase' as const,
    letterSpacing: 1.2,
    color: '#65717a',
  },
  select: {
    width: '100%',
    padding: '6px 8px',
    border: '1px solid #c7d0d4',
    borderRadius: 4,
    fontSize: 12,
    background: '#fff',
    color: '#192530',
  },
  label: {
    display: 'block' as const,
    marginBottom: 2,
    color: '#65717a',
    fontSize: 11,
  },
  input: {
    width: '100%',
    padding: '5px 8px',
    border: '1px solid #c7d0d4',
    borderRadius: 4,
    fontSize: 12,
    boxSizing: 'border-box' as const,
  },
  row: { display: 'flex', gap: 6 },
  btnPrimary: (disabled: boolean) => ({
    flex: 1,
    padding: '8px 10px',
    border: '1px solid #2e5c62',
    background: disabled ? '#c7d0d4' : '#2e5c62',
    color: '#fff',
    borderRadius: 5,
    fontWeight: 700,
    cursor: disabled ? 'not-allowed' as const : 'pointer' as const,
    fontSize: 12,
  }),
  btnSecondary: (disabled: boolean) => ({
    flex: 1,
    padding: '8px 10px',
    border: '1px solid #2e5c62',
    background: '#fff',
    color: '#2e5c62',
    borderRadius: 5,
    fontWeight: 700,
    cursor: disabled ? 'not-allowed' as const : 'pointer' as const,
    fontSize: 12,
  }),
  findingBox: (severity: string) => ({
    padding: '6px 8px',
    borderRadius: 4,
    background: severity === 'BLOCKER' || severity === 'ERROR' ? '#fef2f2' : '#fff7ed',
    border: `1px solid ${severity === 'BLOCKER' || severity === 'ERROR' ? '#fca5a5' : '#fcd34d'}`,
    fontSize: 11,
    color: '#192530',
  }),
  successBox: {
    padding: '6px 8px',
    borderRadius: 4,
    background: '#f0fdf4',
    border: '1px solid #86efac',
    fontSize: 11,
    color: '#166534',
  },
  revBadge: {
    fontSize: 10,
    color: '#65717a',
    marginLeft: 4,
  },
};

// ── Helper: parse rect string ─────────────────────────────────────────────────

function parseParam(key: string, raw: string): unknown {
  if (key === 'rect') {
    const parts = raw.split(',').map((s) => parseFloat(s.trim()));
    return parts.length === 4 && parts.every(isFinite) ? parts : raw;
  }
  if (!isNaN(Number(raw)) && raw.trim() !== '') return Number(raw);
  return raw;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CommandPanel({ projectId, level, selectedId }: Props): React.JSX.Element {
  const uid = useId();

  // Current revision from the server
  const { data: revisions } = useQuery<RevisionEntry[]>({
    queryKey: ['revisions', projectId],
    queryFn: async () => {
      const r = await fetch(`/api/v1/projects/${projectId}/revisions`);
      if (!r.ok) return [];
      return r.json() as Promise<RevisionEntry[]>;
    },
    staleTime: 5_000,
  });
  const currentRevision =
    revisions && revisions.length > 0
      ? Math.max(...revisions.map((r) => r.revision_number))
      : 0;
  const validationState =
    revisions && revisions.length > 0
      ? (revisions.at(-1)?.validation_state ?? 'DRAFT')
      : '—';

  // Operation + field state
  const [operation, setOperation] = useState<string>('move-opening');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [lastResult, setLastResult] = useState<CommandResult | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  // Auto-fill selected ID when user picks an operation with an objectKey
  const opDef = OPERATIONS[operation]!;

  // When selected changes, pre-fill the objectKey field
  React.useEffect(() => {
    if (opDef.objectKey && selectedId) {
      setFields((prev) => ({ ...prev, [opDef.objectKey!]: selectedId }));
    }
  }, [selectedId, opDef.objectKey, operation]);

  const buildInput = useCallback((): CommandEnvelopeInput | null => {
    const params: Record<string, unknown> = {};
    for (const f of opDef.fields) {
      const raw = fields[f.key] ?? '';
      if (!raw && f.type !== 'number') {
        setLastError(`${f.label} is required`);
        return null;
      }
      params[f.key] = parseParam(f.key, raw);
    }
    return {
      operation,
      parameters: params,
      projectId,
      baseRevision: currentRevision || 1,
      authorId: 'browser-user',
      reason: `Phase 7 editor: ${operation}`,
    };
  }, [fields, operation, opDef, projectId, currentRevision]);

  // Preview mutation
  const preview = usePreviewCommand({
    projectId,
    currentRevision: currentRevision || 1,
    onSuccess: (r) => { setLastResult(r); setLastError(null); },
    onError: (e) => { setLastError(e.message); setLastResult(null); },
  });

  // Commit mutation
  const commit = useCommitCommand({
    projectId,
    currentRevision: currentRevision || 1,
    onSuccess: (r) => { setLastResult(r); setLastError(null); },
    onError: (e) => { setLastError(e.message); setLastResult(null); },
  });

  const busy = preview.isPending || commit.isPending;

  function handlePreview() {
    setLastError(null);
    setLastResult(null);
    const input = buildInput();
    if (input) preview.mutate(input);
  }

  function handleCommit() {
    setLastError(null);
    setLastResult(null);
    const input = buildInput();
    if (input) commit.mutate(input);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <section style={S.panel} aria-label="Command Panel">
      <h2 style={S.heading}>
        Command Panel
        {currentRevision > 0 && (
          <span style={S.revBadge}>Rev {currentRevision} · {validationState}</span>
        )}
      </h2>

      {/* Operation selector */}
      <div>
        <label htmlFor={`${uid}-op`} style={S.label}>Operation</label>
        <select
          id={`${uid}-op`}
          style={S.select}
          value={operation}
          onChange={(e) => { setOperation(e.target.value); setFields({}); setLastResult(null); setLastError(null); }}
        >
          {Object.entries(OPERATIONS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </div>

      {/* Dynamic fields */}
      {opDef.fields.map((f) => (
        <div key={f.key}>
          <label htmlFor={`${uid}-${f.key}`} style={S.label}>{f.label}</label>
          <input
            id={`${uid}-${f.key}`}
            style={S.input}
            type={f.type === 'number' ? 'number' : 'text'}
            placeholder={f.placeholder ?? ''}
            value={fields[f.key] ?? ''}
            onChange={(e) => setFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
            disabled={busy}
            aria-label={f.label}
          />
        </div>
      ))}

      {/* Action buttons */}
      <div style={S.row}>
        <button
          type="button"
          style={S.btnSecondary(busy)}
          disabled={busy}
          onClick={handlePreview}
          aria-label="Preview command (dry-run)"
        >
          {preview.isPending ? 'Previewing…' : 'Preview'}
        </button>
        <button
          type="button"
          style={S.btnPrimary(busy)}
          disabled={busy}
          onClick={handleCommit}
          aria-label="Commit command (persist revision)"
        >
          {commit.isPending ? 'Committing…' : 'Commit'}
        </button>
      </div>

      {/* Error banner */}
      {lastError && (
        <div
          style={{ padding: '6px 8px', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 4, fontSize: 11, color: '#b91c1c' }}
          role="alert"
        >
          {lastError}
        </div>
      )}

      {/* Result display */}
      {lastResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {lastResult.accepted ? (
            <div style={S.successBox}>
              <strong>{lastResult.previewOnly ? 'Preview accepted' : 'Committed'}</strong>
              {lastResult.summary && (
                <> · Rev {lastResult.summary.revisionNumber} · {lastResult.summary.operation}</>
              )}
              {lastResult.modelSha256 && (
                <div style={{ marginTop: 2, fontFamily: 'monospace', fontSize: 10 }}>
                  sha256: {lastResult.modelSha256.slice(0, 12)}…
                </div>
              )}
            </div>
          ) : (
            <div style={{ ...S.findingBox('ERROR'), fontWeight: 600 }}>
              Rejected — see findings below
            </div>
          )}

          {lastResult.findings.map((f: Finding, i: number) => (
            <div key={i} style={S.findingBox(f.severity)}>
              <strong>[{f.severity}]</strong> {f.rule}: {f.message}
              {f.professionalReviewRequired && (
                <span style={{ marginLeft: 4, color: '#92400e' }}> ⚠ professional review</span>
              )}
            </div>
          ))}

          {lastResult.affectedObjectIds.length > 0 && (
            <div style={{ fontSize: 11, color: '#65717a' }}>
              Affected: {lastResult.affectedObjectIds.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Context: selected object */}
      {selectedId && !busy && (
        <div style={{ fontSize: 10, color: '#9ca3af', marginTop: 2 }}>
          Selected: <code>{selectedId}</code> · {level}
        </div>
      )}

      <div style={{ fontSize: 10, color: '#9ca3af', borderTop: '1px solid #eef4f4', paddingTop: 6 }}>
        Phase 7 · Commands route to /api/v1/projects/{projectId}/commands/
      </div>
    </section>
  );
}
