// Workflow domain types — mirrors /api/workflow/* response shapes
// IDs are strings (UUID) matching the Platform's project IDs

export type ZoneType = 'living' | 'sleeping' | 'service' | 'circulation' | 'outdoor' | 'work' | 'other';

export interface CanvasBlock {
  id: string;
  label: string;
  zoneType: ZoneType;
  floor: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SpaceProgramItem {
  name: string;
  sqm: number;
  priority: 'must_have' | 'nice_to_have';
  notes?: string | null;
}

export interface BriefAnalysis {
  id: string;
  projectId: string;
  summary: string;
  spaceProgram: SpaceProgramItem[];
  constraints: string[];
  opportunities: string[];
  openQuestions: string[];
  createdAt: string;
}

export interface ConceptVersion {
  id: string;
  projectId: string;
  briefAnalysisId: string | null;
  name: string;
  floors: string[];
  blocks: CanvasBlock[];
  overallScore: number | null;
  programFitScore: number | null;
  daylightScore: number | null;
  budgetFitScore: number | null;
  aiCommentary: string | null;
  promotedRevisionId: string | null;
  createdAt: string;
}

export interface Suggestion {
  id: string;
  projectId: string;
  category: string;
  text: string;
  priority: string;
  status: 'new' | 'accepted' | 'dismissed';
  createdAt: string;
}

export interface ProjectExport {
  projectId: string;
  briefAnalysis: BriefAnalysis | null;
  bestVersion: ConceptVersion | null;
  generatedAt: string;
  markdown: string;
}

export interface AnalyzeBriefBody {
  clientBrief: string;
  siteAddress?: string;
  siteSizeSqm?: number;
  budget?: number;
  stylePreferences?: string;
}

export interface CreateVersionBody {
  name: string;
  floors: string[];
  blocks: CanvasBlock[];
}
