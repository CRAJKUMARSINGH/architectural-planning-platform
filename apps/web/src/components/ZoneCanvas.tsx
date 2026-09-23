/**
 * ZoneCanvas — Phase 15 upstream concept sketching.
 *
 * Ported concept from Archi-Copilot.  Lets the architect sketch draggable,
 * resizable zone blocks (Living, Sleeping, Service, Circulation, etc.) on a
 * canvas, then dispatch each zone as an `add-space` command through the
 * existing Phase 7 useCommitCommand hook.
 *
 * Architecture rule (from IMPLEMENTATION_PLAN.md Phase 7 + Archi-Copilot):
 *   Zone blocks are EPHEMERAL UI STATE.
 *   They are never stored as canonical geometry.
 *   Pressing "Send to editor" dispatches typed add-space commands through
 *   Python validation — the canonical model only changes if every command
 *   is accepted.
 */
import React, { useCallback, useId, useRef, useState } from 'react';
import { type CommandEnvelopeInput, useCommitCommand } from './useCommandDispatch';

// ── Types ────────────────────────────────────────────────────────────────────

export type ZoneType =
  | 'living'
  | 'sleeping'
  | 'service'
  | 'circulation'
  | 'outdoor'
  | 'work'
  | 'other';

export interface ZoneBlock {
  id: string;
  label: string;
  zoneType: ZoneType;
  floor: string;
  /** x, y in canvas units (1 unit = 12 inches / 1 foot) */
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Props {
  projectId: string;
  /** Current revision number — passed to add-space commands as baseRevision */
  currentRevision: number;
  authorId?: string;
  onCommandsDispatched?: (count: number) => void;
}

// ── Constants ────────────────────────────────────────────────────────────────

const ZONE_COLORS: Record<ZoneType, { bg: string; border: string; label: string }> = {
  living:      { bg: '#fef3c7', border: '#f59e0b', label: 'Living' },
  sleeping:    { bg: '#dbeafe', border: '#3b82f6', label: 'Sleeping' },
  service:     { bg: '#fce7f3', border: '#ec4899', label: 'Service' },
  circulation: { bg: '#d1fae5', border: '#10b981', label: 'Circulation' },
  outdoor:     { bg: '#ecfdf5', border: '#6ee7b7', label: 'Outdoor' },
  work:        { bg: '#ede9fe', border: '#8b5cf6', label: 'Work' },
  other:       { bg: '#f3f4f6', border: '#9ca3af', label: 'Other' },
};

const UNIT = 12;        // 1 canvas unit = 12 inches (1 foot)
const GRID = 24;        // snap grid in pixels
const MIN_W = 72;       // min width px  (6 ft = 72 in)
const MIN_H = 60;       // min height px (5 ft = 60 in)
const DEFAULT_W = 180;  // 15 ft
const DEFAULT_H = 144;  // 12 ft
const CANVAS_W = 720;
const CANVAS_H = 540;

function snap(v: number): number { return Math.round(v / GRID) * GRID; }
function uid(): string { return `zone-${Date.now()}-${Math.floor(Math.random() * 1e6)}`; }

// ── Component ─────────────────────────────────────────────────────────────────

export function ZoneCanvas({ projectId, currentRevision, authorId = 'browser-user', onCommandsDispatched }: Props): React.JSX.Element {
  const htmlId = useId();
  const [zones, setZones] = useState<ZoneBlock[]>([]);
  const [floors, setFloors] = useState<string[]>(['Ground Floor']);
  const [activeFloor, setActiveFloor] = useState('Ground Floor');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newFloorName, setNewFloorName] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [dragState, setDragState] = useState<{ id: string; ox: number; oy: number } | null>(null);
  const [resizeState, setResizeState] = useState<{ id: string; startX: number; startY: number; startW: number; startH: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const commit = useCommitCommand({
    projectId,
    currentRevision,
    authorId,
    onSuccess: () => {},
    onError: () => {},
  });

  // ── Floor management ───────────────────────────────────────────────────────

  function addFloor() {
    const name = newFloorName.trim() || `Floor ${floors.length + 1}`;
    if (floors.includes(name)) return;
    setFloors(prev => [...prev, name]);
    setActiveFloor(name);
    setNewFloorName('');
  }

  function removeFloor(floor: string) {
    if (floors.length <= 1) return;
    setZones(prev => prev.filter(z => z.floor !== floor));
    setFloors(prev => prev.filter(f => f !== floor));
    if (activeFloor === floor) setActiveFloor(floors.find(f => f !== floor) ?? floors[0]);
  }

  // ── Zone management ────────────────────────────────────────────────────────

  function addZone(type: ZoneType) {
    const z: ZoneBlock = {
      id: uid(),
      label: ZONE_COLORS[type].label,
      zoneType: type,
      floor: activeFloor,
      x: snap(40),
      y: snap(40),
      w: DEFAULT_W,
      h: DEFAULT_H,
    };
    setZones(prev => [...prev, z]);
    setSelectedId(z.id);
  }

  function deleteZone(id: string) {
    setZones(prev => prev.filter(z => z.id !== id));
    if (selectedId === id) setSelectedId(null);
  }

  // ── SVG drag ──────────────────────────────────────────────────────────────

  function svgPoint(e: React.MouseEvent): { x: number; y: number } | null {
    const svg = svgRef.current;
    if (!svg) return null;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const transformed = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    return { x: transformed.x, y: transformed.y };
  }

  const onZoneMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSelectedId(id);
    const zone = zones.find(z => z.id === id);
    if (!zone) return;
    const p = svgPoint(e);
    if (!p) return;
    setDragState({ id, ox: p.x - zone.x, oy: p.y - zone.y });
  }, [zones]);

  const onResizeMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const zone = zones.find(z => z.id === id);
    if (!zone) return;
    const p = svgPoint(e);
    if (!p) return;
    setResizeState({ id, startX: p.x, startY: p.y, startW: zone.w, startH: zone.h });
  }, [zones]);

  function onSvgMouseMove(e: React.MouseEvent) {
    const p = svgPoint(e);
    if (!p) return;
    if (dragState) {
      const nx = Math.max(0, Math.min(CANVAS_W - 10, snap(p.x - dragState.ox)));
      const ny = Math.max(0, Math.min(CANVAS_H - 10, snap(p.y - dragState.oy)));
      setZones(prev => prev.map(z => z.id === dragState.id ? { ...z, x: nx, y: ny } : z));
    }
    if (resizeState) {
      const dx = p.x - resizeState.startX;
      const dy = p.y - resizeState.startY;
      const nw = Math.max(MIN_W, snap(resizeState.startW + dx));
      const nh = Math.max(MIN_H, snap(resizeState.startH + dy));
      setZones(prev => prev.map(z => z.id === resizeState.id ? { ...z, w: nw, h: nh } : z));
    }
  }

  function onSvgMouseUp() {
    setDragState(null);
    setResizeState(null);
  }

  // ── Send to editor ─────────────────────────────────────────────────────────
  // Dispatch each zone on the active floor as an `add-space` command.
  // Zones never directly touch the canonical model — they produce typed
  // commands that go through Python validation first.

  async function sendToEditor() {
    const floorZones = zones.filter(z => z.floor === activeFloor);
    if (floorZones.length === 0) return;
    setDispatching(true);
    setLastResult(null);
    let accepted = 0;
    let rejected = 0;
    for (const z of floorZones) {
      const levelId = activeFloor.toUpperCase().replace(/\s+/g, '-').slice(0, 8);
      const input: CommandEnvelopeInput = {
        operation: 'add-space',
        parameters: {
          spaceId: z.id,
          levelId,
          name: z.label,
          rect: [z.x, z.y, z.x + z.w, z.y + z.h],
          roomUse: z.zoneType,
          accessIntent: z.zoneType === 'circulation' ? 'primary-circulation' : 'occupancy',
        },
        projectId,
        baseRevision: currentRevision,
        authorId,
        reason: `ZoneCanvas: add ${z.zoneType} zone "${z.label}" from ${activeFloor}`,
      };
      try {
        const result = await commit.mutateAsync(input);
        if (result.accepted) { accepted++; } else { rejected++; }
      } catch {
        rejected++;
      }
    }
    setDispatching(false);
    setLastResult(`${accepted} accepted, ${rejected} rejected`);
    onCommandsDispatched?.(accepted);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const visibleZones = zones.filter(z => z.floor === activeFloor);
  const selected = zones.find(z => z.id === selectedId);

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12 }}
             aria-label="Zone Sketch Canvas">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.2, color: '#65717a' }}>
          Zone Canvas
        </h2>
        <span style={{ fontSize: 10, color: '#9ca3af' }}>Phase 15 · upstream sketch</span>
      </div>

      {/* Floor tabs */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        {floors.map(floor => (
          <div key={floor} style={{ display: 'flex', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => setActiveFloor(floor)}
              style={{
                padding: '3px 8px',
                border: `1px solid ${activeFloor === floor ? '#2e5c62' : '#c7d0d4'}`,
                background: activeFloor === floor ? '#2e5c62' : '#fff',
                color: activeFloor === floor ? '#fff' : '#192530',
                borderRadius: '4px 0 0 4px',
                cursor: 'pointer', fontSize: 11,
              }}
            >{floor}</button>
            {floors.length > 1 && (
              <button
                type="button"
                onClick={() => removeFloor(floor)}
                aria-label={`Remove ${floor}`}
                style={{
                  padding: '3px 5px', border: '1px solid #c7d0d4', borderLeft: 'none',
                  background: '#fff', color: '#9ca3af', borderRadius: '0 4px 4px 0',
                  cursor: 'pointer', fontSize: 10,
                }}
              >×</button>
            )}
          </div>
        ))}
        <input
          value={newFloorName}
          onChange={e => setNewFloorName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addFloor()}
          placeholder="New floor…"
          style={{ width: 80, padding: '3px 6px', border: '1px solid #c7d0d4', borderRadius: 4, fontSize: 11 }}
          aria-label="New floor name"
        />
        <button type="button" onClick={addFloor}
          style={{ padding: '3px 8px', border: '1px solid #2e5c62', background: '#fff', color: '#2e5c62', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
          + Floor
        </button>
      </div>

      {/* Zone type palette */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {(Object.keys(ZONE_COLORS) as ZoneType[]).map(type => (
          <button key={type} type="button" onClick={() => addZone(type)}
            aria-label={`Add ${ZONE_COLORS[type].label} zone`}
            style={{
              padding: '3px 7px', fontSize: 10, borderRadius: 4, cursor: 'pointer',
              border: `1px solid ${ZONE_COLORS[type].border}`,
              background: ZONE_COLORS[type].bg, color: '#192530',
            }}>
            + {ZONE_COLORS[type].label}
          </button>
        ))}
      </div>

      {/* Canvas */}
      <div style={{ border: '1px solid #aebac0', borderRadius: 4, overflow: 'hidden', background: '#f9fafb', position: 'relative' }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
          width="100%"
          style={{ display: 'block', cursor: dragState ? 'grabbing' : 'default', userSelect: 'none' }}
          onClick={() => setSelectedId(null)}
          onMouseMove={onSvgMouseMove}
          onMouseUp={onSvgMouseUp}
          onMouseLeave={onSvgMouseUp}
          role="img"
          aria-label={`Zone sketch canvas — ${activeFloor}`}
        >
          {/* Grid */}
          <defs>
            <pattern id={`${htmlId}-grid`} width={GRID} height={GRID} patternUnits="userSpaceOnUse">
              <path d={`M ${GRID} 0 L 0 0 0 ${GRID}`} fill="none" stroke="#e5e7eb" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill={`url(#${htmlId}-grid)`} />

          {visibleZones.map(z => {
            const c = ZONE_COLORS[z.zoneType];
            const isSel = z.id === selectedId;
            return (
              <g key={z.id}>
                <rect
                  x={z.x} y={z.y} width={z.w} height={z.h}
                  fill={c.bg} stroke={isSel ? '#192530' : c.border}
                  strokeWidth={isSel ? 2 : 1} rx={3}
                  style={{ cursor: 'grab' }}
                  onMouseDown={e => onZoneMouseDown(e, z.id)}
                  onClick={e => { e.stopPropagation(); setSelectedId(z.id); }}
                />
                <text x={z.x + z.w / 2} y={z.y + z.h / 2 - 4}
                  textAnchor="middle" fontSize={10} fill="#374151" fontWeight={600}
                  style={{ pointerEvents: 'none' }}>
                  {z.label}
                </text>
                <text x={z.x + z.w / 2} y={z.y + z.h / 2 + 8}
                  textAnchor="middle" fontSize={8} fill="#9ca3af"
                  style={{ pointerEvents: 'none' }}>
                  {Math.round(z.w / UNIT)}′ × {Math.round(z.h / UNIT)}′
                </text>
                {/* Resize handle */}
                {isSel && (
                  <rect
                    x={z.x + z.w - 8} y={z.y + z.h - 8} width={8} height={8}
                    fill={c.border} rx={1} style={{ cursor: 'se-resize' }}
                    onMouseDown={e => onResizeMouseDown(e, z.id)}
                  />
                )}
              </g>
            );
          })}
        </svg>

        {visibleZones.length === 0 && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
            justifyContent: 'center', pointerEvents: 'none', color: '#9ca3af', fontSize: 11,
          }}>
            Click a zone type above to add it here
          </div>
        )}
      </div>

      {/* Selected zone info + delete */}
      {selected && selected.floor === activeFloor && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: '#65717a' }}>
          <span><code>{selected.id}</code> · {ZONE_COLORS[selected.zoneType].label} · {Math.round(selected.w / UNIT)}′×{Math.round(selected.h / UNIT)}′</span>
          <button type="button" onClick={() => deleteZone(selected.id)}
            style={{ padding: '2px 8px', border: '1px solid #fca5a5', background: '#fef2f2', color: '#b91c1c', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
            aria-label="Delete selected zone">
            Delete
          </button>
        </div>
      )}

      {/* Send to editor */}
      <button
        type="button"
        onClick={sendToEditor}
        disabled={dispatching || zones.filter(z => z.floor === activeFloor).length === 0}
        style={{
          padding: '9px 12px',
          border: '1px solid #2e5c62',
          background: dispatching ? '#c7d0d4' : '#2e5c62',
          color: '#fff', borderRadius: 5, fontWeight: 700, fontSize: 12,
          cursor: dispatching ? 'wait' : 'pointer',
        }}
        aria-label="Dispatch all zones on this floor as add-space commands"
      >
        {dispatching ? 'Dispatching…' : `Send ${zones.filter(z => z.floor === activeFloor).length} zone(s) to editor`}
      </button>

      {lastResult && (
        <div style={{ fontSize: 11, padding: '5px 8px', borderRadius: 4, background: '#f0fdf4', border: '1px solid #86efac', color: '#166534' }}>
          {lastResult} — zones dispatched as add-space commands through Python validation
        </div>
      )}

      <div style={{ fontSize: 10, color: '#9ca3af', borderTop: '1px solid #eef4f4', paddingTop: 6 }}>
        Phase 15 · Zones → <code>add-space</code> commands → Python validation → canonical revision
      </div>
    </section>
  );
}
