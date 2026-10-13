import React, { useState, useRef, useId } from 'react';
import { useQuery } from '@tanstack/react-query';

interface Room {
  id: string;
  type: string;
  position: { x: number; y: number };
  dimensions: { width: number; depth: number };
  area: number;
  center: { x: number; y: number };
  level: string;
  bounds: { x_min: number; y_min: number; x_max: number; y_max: number };
  template?: {
    min_area: number;
    preferred_area: number;
    requires_window: boolean;
    requires_ventilation: boolean;
  };
  furniture?: Array<{
    item: string;
    position: { x: number; y: number };
    rotation: number;
  }>;
}

interface FloorplanData {
  building: {
    width: number;
    depth: number;
    area: number;
    wall_thickness: number;
  };
  rooms: Room[];
  levels: string[];
}

interface Props {
  projectId: string;
  level?: string;
  onRoomSelect?: (room: Room | null) => void;
  onRoomMove?: (roomId: string, newPosition: { x: number; y: number }) => void;
  editable?: boolean;
}

const SCALE = 15; // pixels per foot

export function FloorplanEditor({ 
  projectId, 
  level = 'GF', 
  onRoomSelect, 
  onRoomMove,
  editable = false 
}: Props): React.JSX.Element {
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [draggingRoom, setDraggingRoom] = useState<Room | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const titleId = useId();

  const { data: floorplan, isLoading, error } = useQuery<FloorplanData>({
    queryKey: ['floorplan', projectId, level],
    queryFn: async () => {
      const response = await fetch(`/api/v1/floorplan/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          building_width: 25.0,
          building_depth: 50.0,
          required_rooms: [
            'living_room', 'dining_room', 'kitchen', 'master_bedroom',
            'bathroom', 'garage', 'utility', 'pantry', 'staircase',
            'hallway', 'vestibule', 'study', 'open_to_sky'
          ],
          style: 'modern',
          include_furniture: true
        })
      });
      if (!response.ok) throw new Error('Failed to generate floorplan');
      const result = await response.json();
      return result.layout;
    }
  });

  const handleMouseDown = (room: Room, event: React.MouseEvent) => {
    if (!editable) return;
    
    const svg = svgRef.current;
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    setDraggingRoom(room);
    setDragOffset({
      x: mouseX - room.position.x * SCALE,
      y: mouseY - room.position.y * SCALE
    });
    setSelectedRoom(room);
    onRoomSelect?.(room);
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (!draggingRoom || !editable) return;

    const svg = svgRef.current;
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    const newX = (mouseX - dragOffset.x) / SCALE;
    const newY = (mouseY - dragOffset.y) / SCALE;

    // Constrain to building bounds
    const maxX = floorplan?.building.width || 25;
    const maxY = floorplan?.building.depth || 50;

    const constrainedX = Math.max(0, Math.min(newX, maxX - draggingRoom.dimensions.width));
    const constrainedY = Math.max(0, Math.min(newY, maxY - draggingRoom.dimensions.depth));

    onRoomMove?.(draggingRoom.id, { x: constrainedX, y: constrainedY });
  };

  const handleMouseUp = () => {
    if (draggingRoom && onRoomMove) {
      onRoomMove(draggingRoom.id, {
        x: draggingRoom.position.x,
        y: draggingRoom.position.y
      });
    }
    setDraggingRoom(null);
  };

  const getRoomColor = (room: Room): string => {
    const isSelected = selectedRoom?.id === room.id;
    const colors: Record<string, string> = {
      living_room: isSelected ? '#e8d5b7' : '#f5f5dc',
      dining_room: isSelected ? '#d4e8d5' : '#e8f5e9',
      kitchen: isSelected ? '#ffe8d4' : '#fff3e0',
      master_bedroom: isSelected ? '#e8d4e8' : '#f3e5f5',
      bedroom: isSelected ? '#d4d4e8' : '#e8eaf6',
      bathroom: isSelected ? '#d4e8e8' : '#e0f2f1',
      garage: isSelected ? '#e8e8d4' : '#f5f5f5',
      utility: isSelected ? '#e8d4d4' : '#ffebee',
      pantry: isSelected ? '#d4e8d4' : '#e8f5e9',
      staircase: isSelected ? '#e8e8e8' : '#f5f5f5',
      hallway: isSelected ? '#f0f0f0' : '#fafafa',
      vestibule: isSelected ? '#fff8e1' : '#fffde7',
      study: isSelected ? '#e3f2fd' : '#e8eaf6',
      open_to_sky: isSelected ? '#fff9c4' : '#fffde7',
    };
    return colors[room.type] || '#f5f5f5';
  };

  const getRoomLabel = (room: Room): string => {
    const labels: Record<string, string> = {
      living_room: 'LIVING',
      dining_room: 'DINING',
      kitchen: 'KITCHEN',
      master_bedroom: 'MASTER',
      bedroom: 'BEDROOM',
      bathroom: 'BATH',
      garage: 'GARAGE',
      utility: 'UTILITY',
      pantry: 'PANTRY',
      staircase: 'STAIR',
      hallway: 'HALL',
      vestibule: 'ENTRY',
      study: 'STUDY',
      open_to_sky: 'OPEN TO SKY',
    };
    return labels[room.type] || room.type.toUpperCase();
  };

  if (isLoading) {
    return (
      <div role="status" aria-label="Loading floorplan" style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%',
        fontSize: 14,
        color: '#65717a'
      }}>
        Generating floorplan…
      </div>
    );
  }

  if (error || !floorplan) {
    return (
      <div role="alert" style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%',
        fontSize: 14,
        color: '#8b3c32'
      }}>
        Failed to load floorplan
      </div>
    );
  }

  const buildingWidth = floorplan.building.width * SCALE;
  const buildingDepth = floorplan.building.depth * SCALE;

  return (
    /* WCAG 1.3.1: landmark region with accessible name */
    <div role="region" aria-label="Floorplan editor" style={{ width: '100%', height: '100%', position: 'relative', overflow: 'auto' }}>
      <div style={{ 
        position: 'absolute', 
        top: 12, 
        left: 16, 
        right: 16, 
        display: 'flex', 
        justifyContent: 'space-between',
        fontSize: 11,
        color: '#65717a',
        pointerEvents: 'none',
        zIndex: 1
      }}>
        <div>
          <strong style={{ color: '#192530' }}>FLOORPLAN EDITOR</strong> · 
          <span>AI-powered layout generation</span>
        </div>
        <div>
          {floorplan.building.width}' × {floorplan.building.depth}' · {level}
        </div>
      </div>

      {/* WCAG 1.1.1: role="img" + <title> as first child + aria-labelledby */}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${buildingWidth + 40} ${buildingDepth + 40}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-labelledby={titleId}
        style={{
          width: '100%',
          height: '100%',
          background: '#ffffff',
          margin: 20
        }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <title id={titleId}>
          {level} floorplan — {floorplan.building.width}′ × {floorplan.building.depth}′, {floorplan.rooms.length} rooms
        </title>
        <defs>
          <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#eef4f4" strokeWidth="0.8" />
          </pattern>
        </defs>

        {/* Building outline */}
        <rect
          x={20}
          y={20}
          width={buildingWidth}
          height={buildingDepth}
          fill="url(#grid)"
          stroke="#192530"
          strokeWidth={2}
        />

        {/* Rooms */}
        {floorplan.rooms.map((room) => {
          const x = 20 + room.position.x * SCALE;
          const y = 20 + room.position.y * SCALE;
          const width = room.dimensions.width * SCALE;
          const height = room.dimensions.depth * SCALE;

          return (
            /* WCAG 2.1.1: room groups are interactive — need role + keyboard handler */
            <g
              key={room.id}
              role="button"
              tabIndex={0}
              aria-label={`${getRoomLabel(room)}, ${room.dimensions.width}′ × ${room.dimensions.depth}′${selectedRoom?.id === room.id ? ', selected' : ''}`}
              aria-pressed={selectedRoom?.id === room.id}
              onClick={(e) => { e.stopPropagation(); setSelectedRoom(room); onRoomSelect?.(room); }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setSelectedRoom(selectedRoom?.id === room.id ? null : room);
                  onRoomSelect?.(selectedRoom?.id === room.id ? null : room);
                }
              }}
              style={{ outline: 'none' }}
            >
              {/* Room rectangle */}
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={getRoomColor(room)}
                stroke={selectedRoom?.id === room.id ? '#8b3c32' : '#718087'}
                strokeWidth={selectedRoom?.id === room.id ? 2.4 : 1.1}
                rx={2}
                style={{ cursor: editable ? 'move' : 'pointer' }}
                onMouseDown={(e) => handleMouseDown(room, e)}
              />

              {/* Room label */}
              <text
                x={x + width / 2}
                y={y + height / 2}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill="#192530"
                pointerEvents="none"
              >
                {getRoomLabel(room)}
              </text>

              {/* Room dimensions */}
              <text
                x={x + width / 2}
                y={y + height / 2 + 14}
                textAnchor="middle"
                fontSize={9}
                fill="#65717a"
                pointerEvents="none"
              >
                {room.dimensions.width}' × {room.dimensions.depth}'
              </text>

              {/* Furniture */}
              {room.furniture && room.furniture.map((item, idx) => {
                const fx = x + item.position.x * SCALE;
                const fy = y + item.position.y * SCALE;
                return (
                  <circle
                    key={`${room.id}-furniture-${idx}`}
                    cx={fx}
                    cy={fy}
                    r={4}
                    fill="#2e5c62"
                    opacity={0.6}
                    pointerEvents="none"
                  />
                );
              })}
            </g>
          );
        })}

        {/* Dimension labels */}
        <text x={20 + buildingWidth / 2} y={10} textAnchor="middle" fontSize={10} fill="#65717a">
          {floorplan.building.width}' - WEST TO EAST
        </text>
        <text x={10} y={20 + buildingDepth / 2} textAnchor="middle" fontSize={10} fill="#65717a" transform={`rotate(-90 10 ${20 + buildingDepth / 2})`}>
          {floorplan.building.depth}' - SOUTH TO NORTH
        </text>
      </svg>

      {editable && (
        <div style={{ 
          position: 'absolute', 
          bottom: 18, 
          right: 22, 
          fontSize: 11, 
          color: '#65717a' 
        }}>
          Drag rooms to reposition · Click to select
        </div>
      )}
    </div>
  );
}
