import React, { useState, useCallback } from 'react';
import type { CanvasBlock, ZoneType } from '../types';

const GRID = 20;
const snap = (v: number, on: boolean) => on ? Math.round(v / GRID) * GRID : v;

const ZONE_COLORS: Record<ZoneType, { bg: string; border: string; text: string }> = {
  living:      { bg: '#fef3c7', border: '#d97706', text: '#92400e' },
  sleeping:    { bg: '#e0e7ff', border: '#4f46e5', text: '#3730a3' },
  service:     { bg: '#e2e8f0', border: '#64748b', text: '#1e293b' },
  circulation: { bg: '#f5f5f4', border: '#78716c', text: '#44403c' },
  outdoor:     { bg: '#d1fae5', border: '#059669', text: '#065f46' },
  work:        { bg: '#e0f2fe', border: '#0284c7', text: '#0c4a6e' },
  other:       { bg: '#f4f4f5', border: '#71717a', text: '#18181b' },
};

const ZONE_TYPES: ZoneType[] = ['living', 'sleeping', 'service', 'circulation', 'outdoor', 'work', 'other'];

interface Props {
  blocks: CanvasBlock[];
  onChange: (blocks: CanvasBlock[]) => void;
  floors: string[];
  activeFloor: string;
  onFloorsChange: (floors: string[]) => void;
  onActiveFloorChange: (floor: string) => void;
  readonly?: boolean;
}

export function ConceptCanvas({
  blocks, onChange, floors, activeFloor,
  onFloorsChange, onActiveFloorChange, readonly = false,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState('');
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizingId, setResizingId] = useState<string | null>(null);
  const [resizeHandle, setResizeHandle] = useState('');
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, w: 0, h: 0, bx: 0, by: 0 });
  const [snapOn, setSnapOn] = useState(true);

  const visible = blocks.filter(b => b.floor === activeFloor);

  const addBlock = (zoneType: ZoneType) => {
    if (readonly) return;
    const nb: CanvasBlock = {
      id: Math.random().toString(36).slice(2, 9),
      label: 'New Space', zoneType,
      floor: activeFloor,
      x: snap(60, snapOn), y: snap(60, snapOn),
      width: snap(120, snapOn), height: snap(100, snapOn),
    };
    onChange([...blocks, nb]);
    setSelectedId(nb.id);
  };

  const addFloor = () => {
    if (readonly) return;
    let n = floors.length + 1;
    let name = `Floor ${n}`;
    while (floors.includes(name)) { n++; name = `Floor ${n}`; }
    onFloorsChange([...floors, name]);
    onActiveFloorChange(name);
  };

  const removeFloor = (floor: string) => {
    if (readonly || floors.length <= 1) return;
    if (!confirm(`Remove "${floor}"? Its zones will be deleted.`)) return;
    const rem = floors.filter(f => f !== floor);
    onFloorsChange(rem);
    onChange(blocks.filter(b => b.floor !== floor));
    if (activeFloor === floor) onActiveFloorChange(rem[0]);
  };

  const deleteBlock = (id: string) => {
    if (readonly) return;
    onChange(blocks.filter(b => b.id !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const commitEdit = () => {
    if (!editingId) return;
    const fallback = blocks.find(b => b.id === editingId)?.label ?? '';
    onChange(blocks.map(b => b.id === editingId ? { ...b, label: editingLabel.trim() || fallback } : b));
    setEditingId(null);
  };

  const onPointerDown = (e: React.PointerEvent, block: CanvasBlock, isHandle = false, hType = '') => {
    if (readonly) return;
    e.stopPropagation();
    if (editingId && editingId !== block.id) commitEdit();
    setSelectedId(block.id);
    if (isHandle) {
      setResizingId(block.id); setResizeHandle(hType);
      setResizeStart({ x: e.clientX, y: e.clientY, w: block.width, h: block.height, bx: block.x, by: block.y });
    } else {
      setDraggingId(block.id);
      setDragOffset({ x: e.clientX - block.x, y: e.clientY - block.y });
    }
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (readonly) return;
    if (draggingId) {
      onChange(blocks.map(b => b.id === draggingId
        ? { ...b, x: snap(Math.max(0, e.clientX - dragOffset.x), snapOn), y: snap(Math.max(0, e.clientY - dragOffset.y), snapOn) }
        : b));
    } else if (resizingId) {
      const dx = e.clientX - resizeStart.x, dy = e.clientY - resizeStart.y;
      onChange(blocks.map(b => {
        if (b.id !== resizingId) return b;
        let { w: nw, h: nh, bx: nx, by: ny } = { w: resizeStart.w, h: resizeStart.h, bx: resizeStart.bx, by: resizeStart.by };
        if (resizeHandle.includes('e')) nw = snap(Math.max(GRID * 2, resizeStart.w + dx), snapOn);
        if (resizeHandle.includes('s')) nh = snap(Math.max(GRID * 2, resizeStart.h + dy), snapOn);
        if (resizeHandle.includes('w')) { const pw = resizeStart.w - dx; if (pw > GRID*2) { nw = snap(pw, snapOn); nx = snap(resizeStart.bx + dx, snapOn); } }
        if (resizeHandle.includes('n')) { const ph = resizeStart.h - dy; if (ph > GRID*2) { nh = snap(ph, snapOn); ny = snap(resizeStart.by + dy, snapOn); } }
        return { ...b, x: nx, y: ny, width: nw, height: nh };
      }));
    }
  }, [draggingId, resizingId, resizeHandle, dragOffset, resizeStart, blocks, onChange, readonly, snapOn]);

  const onPointerUp = (e: React.PointerEvent) => {
    if (readonly) return;
    if (draggingId || resizingId) (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setDraggingId(null); setResizingId(null); setResizeHandle('');
  };

  const HANDLES: { dir: string; style: React.CSSProperties }[] = [
    { dir: 'se', style: { right: -6, bottom: -6, cursor: 'se-resize' } },
    { dir: 'sw', style: { left: -6, bottom: -6, cursor: 'sw-resize' } },
    { dir: 'ne', style: { right: -6, top: -6, cursor: 'ne-resize' } },
    { dir: 'nw', style: { left: -6, top: -6, cursor: 'nw-resize' } },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden', userSelect: 'none', background: '#f8fafc' }}>
      {/* Floor tabs */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, padding: '6px 10px 0', background: '#fff', borderBottom: '1px solid #e2e8f0' }}>
        {floors.map(f => (
          <div key={f} onClick={() => onActiveFloorChange(f)}
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 10px', borderRadius: '4px 4px 0 0', cursor: 'pointer', fontSize: 11, fontFamily: 'monospace',
              background: f === activeFloor ? '#f8fafc' : 'transparent',
              border: f === activeFloor ? '1px solid #e2e8f0' : '1px solid transparent',
              borderBottom: 'none', fontWeight: f === activeFloor ? 700 : 400,
            }}>
            {f}
            {!readonly && floors.length > 1 && (
              <button onClick={e => { e.stopPropagation(); removeFloor(f); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 12, padding: 0, lineHeight: 1 }}>×</button>
            )}
          </div>
        ))}
        {!readonly && (
          <button onClick={addFloor}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: '#94a3b8', padding: '3px 8px', fontFamily: 'monospace' }}>
            + Floor
          </button>
        )}
      </div>

      {/* Zone palette */}
      {!readonly && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: '6px 10px', background: '#fff', borderBottom: '1px solid #e2e8f0', alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'monospace', marginRight: 2 }}>Add:</span>
          {ZONE_TYPES.map(zt => (
            <button key={zt} onClick={() => addBlock(zt)}
              style={{ padding: '2px 8px', fontSize: 11, borderRadius: 4, cursor: 'pointer', fontWeight: 600, border: `1px solid ${ZONE_COLORS[zt].border}`, background: ZONE_COLORS[zt].bg, color: ZONE_COLORS[zt].text }}>
              {zt}
            </button>
          ))}
          <div style={{ marginLeft: 'auto' }}>
            <button onClick={() => setSnapOn(s => !s)}
              style={{ padding: '2px 8px', fontSize: 11, borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', border: '1px solid', borderColor: snapOn ? '#3b82f6' : '#e2e8f0', background: snapOn ? '#eff6ff' : 'transparent', color: snapOn ? '#1d4ed8' : '#94a3b8' }}>
              ⊞ Snap {snapOn ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>
      )}

      {/* Canvas */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', backgroundImage: 'radial-gradient(#e2e8f0 1px, transparent 1px)', backgroundSize: '20px 20px' }}
        onPointerDown={() => { if (!readonly) { commitEdit(); setSelectedId(null); } }}
        onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={onPointerUp}>

        {visible.length === 0 && !readonly && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
            <p style={{ fontSize: 13, color: '#94a3b8', fontFamily: 'monospace' }}>Add zones using the palette above</p>
          </div>
        )}

        {visible.map(block => {
          const sel = selectedId === block.id;
          const ed = editingId === block.id;
          const col = ZONE_COLORS[block.zoneType];
          return (
            <div key={block.id}
              style={{ position: 'absolute', left: block.x, top: block.y, width: block.width, height: block.height,
                border: `2px solid ${col.border}`, background: col.bg, color: col.text,
                borderRadius: 4, cursor: readonly ? 'default' : 'move', display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: sel ? `0 0 0 3px rgba(59,130,246,0.5)` : '0 1px 3px rgba(0,0,0,0.1)',
                zIndex: sel ? 10 : 1 }}
              onPointerDown={e => onPointerDown(e, block)}
              onDoubleClick={e => { e.stopPropagation(); if (!readonly) { setEditingId(block.id); setEditingLabel(block.label); } }}>

              {ed ? (
                <input autoFocus value={editingLabel}
                  onChange={e => setEditingLabel(e.target.value)}
                  onBlur={commitEdit}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === 'Escape') commitEdit(); }}
                  onPointerDown={e => e.stopPropagation()}
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', textAlign: 'center', fontSize: 11, fontWeight: 700, background: 'rgba(255,255,255,0.85)', border: 'none', outline: 'none', padding: '0 6px', borderRadius: 4 }} />
              ) : (
                <div style={{ textAlign: 'center', padding: '0 6px', pointerEvents: 'none' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, lineHeight: 1.3 }}>{block.label}</div>
                  {block.width > 80 && block.height > 55 && (
                    <div style={{ fontSize: 9, opacity: 0.6, marginTop: 2, fontFamily: 'monospace' }}>
                      {Math.round(block.width / GRID)}×{Math.round(block.height / GRID)}m
                    </div>
                  )}
                </div>
              )}

              {!readonly && sel && !ed && (
                <>
                  <button onPointerDown={e => { e.stopPropagation(); deleteBlock(block.id); }}
                    style={{ position: 'absolute', top: -12, right: -12, width: 20, height: 20, borderRadius: '50%', background: '#ef4444', border: '2px solid #fff', color: '#fff', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 20 }}>
                    ×
                  </button>
                  {HANDLES.map(h => (
                    <div key={h.dir}
                      style={{ position: 'absolute', width: 12, height: 12, background: '#3b82f6', border: '2px solid #fff', borderRadius: 2, zIndex: 20, ...h.style }}
                      onPointerDown={e => onPointerDown(e, block, true, h.dir)} />
                  ))}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
