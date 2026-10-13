import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

interface PresetLayout {
  id: string;
  name: string;
  description: string;
  dimensions: { width: number; depth: number };
  rooms: string[];
}

interface Props {
  projectId: string;
  onGenerate?: (layout: any) => void;
}

export function FloorplanGeneratorPanel({ projectId: _projectId, onGenerate }: Props): React.JSX.Element {
  const [buildingWidth, setBuildingWidth] = useState(25.0);
  const [buildingDepth, setBuildingDepth] = useState(50.0);
  const [selectedRooms, setSelectedRooms] = useState<Set<string>>(new Set([
    'living_room', 'dining_room', 'kitchen', 'master_bedroom',
    'bathroom', 'garage', 'utility', 'pantry', 'staircase',
    'hallway', 'vestibule', 'study', 'open_to_sky'
  ]));
  const [style, setStyle] = useState('modern');
  const [includeFurniture, setIncludeFurniture] = useState(true);
  const [layoutVersion, setLayoutVersion] = useState('v1');

  const { data: presets } = useQuery<{ presets: PresetLayout[] }>({
    queryKey: ['floorplan-presets'],
    queryFn: async () => {
      const response = await fetch('/api/v1/floorplan/presets');
      if (!response.ok) throw new Error('Failed to fetch presets');
      return response.json();
    }
  });

  const generateMutation = useMutation({
    mutationFn: async (requestData: any) => {
      const response = await fetch('/api/v1/floorplan/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });
      if (!response.ok) throw new Error('Failed to generate floorplan');
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success && data.layout) {
        onGenerate?.(data.layout);
      }
    }
  });

  const handleGenerate = () => {
    generateMutation.mutate({
      building_width: buildingWidth,
      building_depth: buildingDepth,
      required_rooms: Array.from(selectedRooms),
      constraints: { version: layoutVersion },
      style,
      include_furniture: includeFurniture
    });
  };

  const handlePresetSelect = (preset: PresetLayout) => {
    setBuildingWidth(preset.dimensions.width);
    setBuildingDepth(preset.dimensions.depth);
    setSelectedRooms(new Set(preset.rooms));
  };

  const toggleRoom = (roomType: string) => {
    const newSelected = new Set(selectedRooms);
    if (newSelected.has(roomType)) {
      newSelected.delete(roomType);
    } else {
      newSelected.add(roomType);
    }
    setSelectedRooms(newSelected);
  };

  const roomTypes = [
    { id: 'living_room', label: 'Living Room' },
    { id: 'dining_room', label: 'Dining Room' },
    { id: 'kitchen', label: 'Kitchen' },
    { id: 'master_bedroom', label: 'Master Bedroom' },
    { id: 'bedroom', label: 'Bedroom' },
    { id: 'bathroom', label: 'Bathroom' },
    { id: 'powder_room', label: 'Powder Room' },
    { id: 'garage', label: 'Garage' },
    { id: 'study', label: 'Study' },
    { id: 'utility', label: 'Utility' },
    { id: 'pantry', label: 'Pantry' },
    { id: 'staircase', label: 'Staircase' },
    { id: 'hallway', label: 'Hallway' },
    { id: 'vestibule', label: 'Vestibule' },
    { id: 'open_to_sky', label: 'Open to Sky' },
  ];

  return (
    <div className="panel panel--floorplan">
      <div className="panel__header">
        <span className="panel__title">Floorplan Generator</span>
        <span className="panel__subtitle">AI-powered layout design</span>
      </div>

      <div className="panel__body">
        {/* Preset Layouts */}
        <div className="panel-section">
          <label className="field-label">Preset Layouts</label>
          <div className="preset-grid">
            {presets?.presets.map((preset) => (
              <button
                key={preset.id}
                className="preset-card"
                type="button"
                onClick={() => handlePresetSelect(preset)}
              >
                <strong>{preset.name}</strong>
                <small>{preset.dimensions.width}' × {preset.dimensions.depth}'</small>
                <small>{preset.description}</small>
              </button>
            ))}
          </div>
        </div>

        {/* Building Dimensions */}
        <div className="panel-section">
          <label className="field-label">Building Dimensions (feet)</label>
          <div className="dimension-inputs">
            <label className="field-label--small">
              Width
              <input
                type="number"
                step="0.5"
                min="10"
                max="100"
                value={buildingWidth}
                onChange={(e) => setBuildingWidth(parseFloat(e.target.value) || 0)}
                className="input input--small"
              />
            </label>
            <label className="field-label--small">
              Depth
              <input
                type="number"
                step="0.5"
                min="10"
                max="100"
                value={buildingDepth}
                onChange={(e) => setBuildingDepth(parseFloat(e.target.value) || 0)}
                className="input input--small"
              />
            </label>
          </div>
          <div className="field-hint">
            Total area: {(buildingWidth * buildingDepth).toFixed(0)} sq ft
          </div>
        </div>

        {/* Room Selection */}
        <div className="panel-section">
          <label className="field-label">Required Rooms</label>
          <div className="room-grid">
            {roomTypes.map((room) => (
              <button
                key={room.id}
                className={`room-chip ${selectedRooms.has(room.id) ? 'room-chip--selected' : ''}`}
                type="button"
                onClick={() => toggleRoom(room.id)}
              >
                {room.label}
              </button>
            ))}
          </div>
          <div className="field-hint">
            {selectedRooms.size} rooms selected
          </div>
        </div>

        {/* Style Options */}
        <div className="panel-section">
          <label className="field-label">Style</label>
          <select
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="select"
          >
            <option value="modern">Modern</option>
            <option value="traditional">Traditional</option>
            <option value="minimalist">Minimalist</option>
            <option value="industrial">Industrial</option>
          </select>
        </div>

        {/* Layout Version */}
        <div className="panel-section">
          <label className="field-label">Layout Version</label>
          <select
            value={layoutVersion}
            onChange={(e) => setLayoutVersion(e.target.value)}
            className="select"
          >
            <option value="v2">Version 2 (Kitchen SE)</option>
            <option value="v3">Version 3 (Kitchen SE)</option>
            <option value="v4">Version 4 (Constructed - Kitchen SE)</option>
            <option value="v5">Version 5 (Constructed - Kitchen SE)</option>
          </select>
          <div className="field-hint">
            All versions: Kitchen in South East corner
          </div>
        </div>

        {/* Options */}
        <div className="panel-section">
          <label className="field-label">
            <input
              type="checkbox"
              checked={includeFurniture}
              onChange={(e) => setIncludeFurniture(e.target.checked)}
            />
            Include furniture placement
          </label>
        </div>

        {/* Generate Button */}
        <button
          className="button button--primary button--full"
          type="button"
          onClick={handleGenerate}
          disabled={generateMutation.isPending || selectedRooms.size === 0}
        >
          {generateMutation.isPending ? 'Generating...' : 'Generate Floorplan'}
        </button>

        {/* Errors */}
        {generateMutation.error && (
          <div className="error-message">
            Failed to generate floorplan. Please try again.
          </div>
        )}

        {/* Generated Metadata */}
        {generateMutation.data?.metadata && (
          <div className="panel-section panel-section--info">
            <label className="field-label">Generated Layout</label>
            <div className="metadata-grid">
              <div>
                <small>Dimensions</small>
                <strong>{generateMutation.data.metadata.building_dimensions}</strong>
              </div>
              <div>
                <small>Total Rooms</small>
                <strong>{generateMutation.data.metadata.total_rooms}</strong>
              </div>
              <div>
                <small>Total Area</small>
                <strong>{generateMutation.data.metadata.total_area} sq ft</strong>
              </div>
              <div>
                <small>Validation</small>
                <strong className={generateMutation.data.metadata.validation === 'passed' ? 'text--success' : 'text--error'}>
                  {generateMutation.data.metadata.validation}
                </strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
