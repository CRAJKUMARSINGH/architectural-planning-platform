/**
 * Unit tests for VersionScoringPanel component (Phase 16A).
 * 
 * Tests the AI version scoring UI component including:
 * - Brief analysis fetching and display
 * - Version scoring functionality
 * - Score visualization
 * - Error handling
 * - Score history tracking
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VersionScoringPanel } from '../VersionScoringPanel';

// Mock fetch for API calls
global.fetch = vi.fn();

describe('VersionScoringPanel', () => {
  let queryClient: QueryClient;
  
  const mockProjectId = 'test-project-123';
  const mockRevision = {
    id: 'revision-123',
    revisionNumber: 1,
    createdAt: '2024-01-01T00:00:00Z',
    briefText: 'Test client brief for a modern residential project',
    metadata: {
      siteSize: 100,
      budget: 50000,
      stylePreferences: ['modern', 'minimalist']
    }
  };

  const mockBriefAnalysis = {
    summary: 'Modern residential project with open plan living',
    spaceProgram: [
      { name: 'Living Room', sqm: 45, priority: 'must-have', notes: 'Primary gathering space' },
      { name: 'Kitchen', sqm: 20, priority: 'must-have', notes: 'Cooking and dining area' },
      { name: 'Master Bedroom', sqm: 25, priority: 'must-have', notes: 'Primary sleeping space' }
    ],
    constraints: ['Site size limited to 100sqm', 'Budget constraint of $50,000'],
    opportunities: ['Good natural light exposure', 'Open plan possible'],
    openQuestions: ['Client preference for outdoor space?', 'Specific room size requirements?'],
    provenance: {
      model: 'gemini-2.5-flash',
      timestamp: '2024-01-01T00:00:00Z',
      briefLength: 150,
      contextKeys: ['siteSize', 'budget']
    },
    modelVersion: 'gemini-2.5-flash'
  };

  const mockScoringResult = {
    overallScore: 85,
    programFit: 90,
    daylight: 75,
    budgetFit: 80,
    commentary: 'Design meets most brief requirements with excellent program fit. Good use of available space with efficient layout. Daylight could be improved with additional windows.',
    zoneScores: [
      { zoneName: 'Living Room', score: 90, notes: 'Excellent size and placement' },
      { zoneName: 'Kitchen', score: 85, notes: 'Good workflow, could improve daylight' },
      { zoneName: 'Master Bedroom', score: 80, notes: 'Adequate size, consider closet space' }
    ],
    provenance: {
      model: 'gemini-2.5-flash',
      timestamp: '2024-01-01T00:01:00Z',
      versionId: 'revision-123',
      briefAnalysisId: '2024-01-01T00:00:00Z'
    },
    modelVersion: 'gemini-2.5-flash'
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('renders the component with header', () => {
    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    expect(screen.getByText('AI Version Scoring')).toBeInTheDocument();
    expect(screen.getByText('Phase 16A')).toBeInTheDocument();
  });

  it('displays brief analysis status when brief text is available', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockBriefAnalysis
    });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });
  });

  it('shows loading state while analyzing brief', () => {
    (global.fetch as any).mockImplementationOnce(() => new Promise(() => {}));

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    expect(screen.getByText('Analyzing brief...')).toBeInTheDocument();
  });

  it('displays brief analysis needed warning when no brief text', () => {
    const revisionWithoutBrief = { ...mockRevision, briefText: '' };

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={revisionWithoutBrief}
      />
    );

    expect(screen.getByText('⚠ Brief analysis needed')).toBeInTheDocument();
  });

  it('displays current revision information', () => {
    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    expect(screen.getByText(/Scoring Revision #1/)).toBeInTheDocument();
    expect(screen.getByText(/Created:/)).toBeInTheDocument();
  });

  it('enables score button when brief analysis is available', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockBriefAnalysis
    });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      const scoreButton = screen.getByText('Score This Version');
      expect(scoreButton).not.toBeDisabled();
    });
  });

  it('disables score button when brief analysis is not available', () => {
    const revisionWithoutBrief = { ...mockRevision, briefText: '' };

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={revisionWithoutBrief}
      />
    );

    const scoreButton = screen.getByText('Score This Version');
    expect(scoreButton).toBeDisabled();
  });

  it('displays scoring results after successful scoring', async () => {
    // Mock brief analysis
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScoringResult
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    // Wait for brief analysis
    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    // Click score button
    const scoreButton = screen.getByText('Score This Version');
    fireEvent.click(scoreButton);

    // Wait for scoring results
    await waitFor(() => {
      expect(screen.getByText('Scoring Results')).toBeInTheDocument();
    });

    // Verify score display
    expect(screen.getByText('85/100')).toBeInTheDocument();
    expect(screen.getByText('90/100')).toBeInTheDocument(); // program fit
    expect(screen.getByText('75/100')).toBeInTheDocument(); // daylight
    expect(screen.getByText('80/100')).toBeInTheDocument(); // budget fit
  });

  it('shows AI commentary in scoring results', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScoringResult
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));

    await waitFor(() => {
      expect(screen.getByText('AI Commentary')).toBeInTheDocument();
      expect(screen.getByText(/Design meets most brief requirements/)).toBeInTheDocument();
    });
  });

  it('displays zone-specific scores', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScoringResult
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));

    await waitFor(() => {
      expect(screen.getByText('Zone Analysis')).toBeInTheDocument();
      expect(screen.getByText('Living Room')).toBeInTheDocument();
      expect(screen.getByText('Kitchen')).toBeInTheDocument();
      expect(screen.getByText('Master Bedroom')).toBeInTheDocument();
    });
  });

  it('shows error message when scoring fails', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'AI service temporarily unavailable' })
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));

    await waitFor(() => {
      expect(screen.getByText(/AI service temporarily unavailable/)).toBeInTheDocument();
    });
  });

  it('shows error when brief analysis fails', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Failed to analyze brief' })
    });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to analyze brief/)).toBeInTheDocument();
    });
  });

  it('displays score history when multiple versions are scored', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScoringResult
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockScoringResult,
          overallScore: 78,
          programFit: 85,
          provenance: { ...mockScoringResult.provenance, timestamp: '2024-01-01T00:02:00Z' }
        })
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    // Score first version
    fireEvent.click(screen.getByText('Score This Version'));
    await waitFor(() => {
      expect(screen.getByText('Scoring Results')).toBeInTheDocument();
    });

    // Score second version (simulate by updating revision)
    const secondRevision = { ...mockRevision, id: 'revision-456', revisionNumber: 2 };
    
    // Re-render with new revision
    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={secondRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));
    
    await waitFor(() => {
      expect(screen.getByText(/Score History/)).toBeInTheDocument();
    });
  });

  it('calls onScoreComplete callback when scoring completes', async () => {
    const onScoreComplete = vi.fn();

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScoringResult
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
        onScoreComplete={onScoreComplete}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));

    await waitFor(() => {
      expect(onScoreComplete).toHaveBeenCalledWith(mockScoringResult);
    });
  });

  it('displays provenance information for scoring results', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScoringResult
      });

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));

    await waitFor(() => {
      expect(screen.getByText(/Scored by gemini-2.5-flash/)).toBeInTheDocument();
    });
  });

  it('shows loading state during scoring', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      });

    let scoringResolve: (value: any) => void;
    const scoringPromise = new Promise(resolve => {
      scoringResolve = resolve;
    });

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockBriefAnalysis
      })
      .mockImplementationOnce(() => scoringPromise);

    renderWithQueryClient(
      <VersionScoringPanel 
        projectId={mockProjectId} 
        currentRevision={mockRevision}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/✓ Brief analyzed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Score This Version'));

    expect(screen.getByText('Scoring...')).toBeInTheDocument();

    // Resolve the promise
    scoringResolve!({
      ok: true,
      json: async () => mockScoringResult
    });
  });
});