import React, { useId, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

interface Props {
  projectId: string;
  level: 'GF' | 'FF';
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

type Space = {
  id: string;
  levelId: string;
  name: string;
  roomUse?: string;
  rect: [number, number, number, number];
};

type GraphNode  = { id: string; kind: string; rect?: [number, number, number, number] };
type GraphEdge  = { id: string; from: string; to: string; kind: string; openingId?: string };
type Route      = { spaceId: string; reachable: boolean };

type Analysis = {
  status: string;
  spaces: Space[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[]; routes: Route[] };
  openings: { tag: string; openingId: string; connectionType: string }[];
};

const FALLBACK: Analysis = {
  status: 'unavailable',
  spaces: [],
  graph: { nodes: [], edges: [], routes: [] },
  openings: [],
};

export function Viewport2D({ projectId, level, selectedId, onSelect }: Props): React.JSX.Element {
  const titleId = useId();

  const analysis = useQuery<Analysis>({
    queryKey: ['analysis', projectId, level],
    queryFn: async () => {
      const versioned = await fetch(`/api/v1/projects/${projectId}/analysis?level=${level}`);
      if (versioned.ok) return (await versioned.json()) as Analysis;
      const legacy = await fetch(`/analysis?level=${level}`);
      if (!legacy.ok) throw new Error('Analysis API unavailable');
      return (await legacy.json()) as Analysis;
    },
  });

  const data  = analysis.data ?? FALLBACK;
  const nodes = useMemo(() => new Map(data.graph.nodes.map((n) => [n.id, n])), [data.graph.nodes]);
  const reachableIds = useMemo(
    () => new Set(data.graph.routes.filter((r) => r.reachable).map((r) => r.spaceId)),
    [data.graph.routes],
  );

  const center = (nodeId: string): [number, number] => {
    const node = nodes.get(nodeId);
    if (node?.rect) {
      const [x0, y0, x1, y1] = node.rect;
      return [(x0 + x1) / 2, (y0 + y1) / 2];
    }
    const edge = data.graph.edges.find((e) => e.from === nodeId || e.to === nodeId);
    const host = edge ? nodes.get(edge.from === nodeId ? edge.to : edge.from) : undefined;
    if (host?.rect) {
      const [, y0, x1, y1] = host.rect;
      return [x1 + 30, (y0 + y1) / 2];
    }
    return [0, 0];
  };

  return (
    /* WCAG 1.3.1: landmark region needs accessible name */
    <div
      role="region"
      aria-label="2D floor-plan viewport"
      style={{ width: '100%', height: '100%', background: 'radial-gradient(circle at 20% 20%, #ffffff 0%, #eef4f4 100%)', position: 'relative', overflow: 'hidden' }}
      onClick={() => onSelect(null)}
    >
      <div
        style={{ position: 'absolute', top: 12, left: 16, right: 16, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#65717a', pointerEvents: 'none', zIndex: 1 }}
      >
        <div>
          <strong style={{ color: '#192530' }}>2D VIEWPORT</strong>{' '}·{' '}
          <span>Week 3 route graph · Week 4 semantic openings</span>
        </div>
        <div>
          {level} · <code>{projectId}</code>
        </div>
      </div>

      {/* WCAG 1.1.1: SVG diagram needs role="img" + <title> + aria-labelledby */}
      <svg
        viewBox="0 0 760 1180"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-labelledby={titleId}
        style={{ position: 'absolute', inset: 48, width: 'calc(100% - 96px)', height: 'calc(100% - 96px)', border: '1px solid #aebac0', background: '#ffffff' }}
      >
        <title id={titleId}>
          {level} floor-plan — {data.spaces.length} spaces, route graph and semantic openings for {projectId}
        </title>
        <defs>
          <pattern id="vp2d-grid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#eef4f4" strokeWidth="0.8" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#vp2d-grid)" />

        {/* Route graph edges */}
        {data.graph.edges.map((edge) => {
          const [x1, y1] = center(edge.from);
          const [x2, y2] = center(edge.to);
          const vertical  = edge.kind === 'vertical-connector';
          return (
            <g key={edge.id} aria-hidden="true">
              <line x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={vertical ? '#8b3c32' : '#2e5c62'}
                strokeWidth={vertical ? 3 : 2}
                strokeDasharray={vertical ? '6 4' : undefined}
                opacity={0.82}
              />
              {edge.openingId && (
                <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 4} textAnchor="middle" fontSize={8} fill="#2e5c62">
                  {edge.openingId}
                </text>
              )}
            </g>
          );
        })}

        {/* Spaces — WCAG 2.1.1: keyboard accessible via tabIndex + onKeyDown */}
        {data.spaces.map((space) => {
          const [x0, y0, x1, y1] = space.rect;
          const isSelected  = selectedId === space.id;
          const isReachable = reachableIds.has(space.id);
          const label       = `${space.name} (${space.id}) — ${isReachable ? 'route proven' : 'route broken'}`;
          return (
            <g
              key={space.id}
              role="button"
              tabIndex={0}
              aria-label={label}
              aria-pressed={isSelected}
              onClick={(e) => { e.stopPropagation(); onSelect(space.id); }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(isSelected ? null : space.id); }
                if (e.key === 'Escape') onSelect(null);
              }}
              style={{ cursor: 'pointer', outline: 'none' }}
            >
              <rect
                x={x0} y={y0} width={x1 - x0} height={y1 - y0}
                fill={isSelected ? '#f4e9d9' : isReachable ? '#f6f8f8' : '#f8eeee'}
                stroke={isSelected ? '#8b3c32' : isReachable ? '#718087' : '#b66b61'}
                strokeWidth={isSelected ? 2.4 : 1.1}
                rx={2}
              />
              <text x={(x0 + x1) / 2} y={(y0 + y1) / 2} textAnchor="middle" fontSize={11} fontWeight={600} fill="#192530">
                {space.name}
              </text>
              <text x={(x0 + x1) / 2} y={(y0 + y1) / 2 + 14} textAnchor="middle" fontSize={9} fill="#65717a">
                {space.id} · {isReachable ? 'route proven' : 'route broken'}
              </text>
            </g>
          );
        })}

        <text x="16" y="1148" fontSize="9" fill="#65717a" aria-hidden="true">
          Red rooms have no proven route to an intentional entry · blue lines are semantic opening edges
        </text>
      </svg>

      {analysis.isLoading && (
        <div
          aria-live="polite"
          style={{ position: 'absolute', bottom: 18, right: 22, fontSize: 11, color: '#65717a' }}
        >
          Loading authoritative model…
        </div>
      )}
      {analysis.isError && (
        <div
          role="alert"
          style={{ position: 'absolute', bottom: 18, right: 22, fontSize: 11, color: '#8b3c32' }}
        >
          Analysis API unavailable
        </div>
      )}
    </div>
  );
}
