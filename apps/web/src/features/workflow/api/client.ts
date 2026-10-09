/**
 * Workflow API client — calls /api/workflow/* on the Platform's Python backend.
 * Uses the same base URL as the rest of the app.
 * Auth token is attached via Authorization header from sessionStorage key 'auth_token'.
 */

import type {
  BriefAnalysis, ConceptVersion, Suggestion,
  ProjectExport, AnalyzeBriefBody, CreateVersionBody,
} from '../types';

const BASE = '/api/workflow';

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined'
    ? sessionStorage.getItem('auth_token')
    : null;
  return token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' };
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: authHeaders(),
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Brief analysis
export const analyzeBrief = (projectId: string, body: AnalyzeBriefBody) =>
  req<BriefAnalysis>(`/projects/${projectId}/analyze-brief-with-text`, {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const getBriefAnalysis = (projectId: string) =>
  req<BriefAnalysis | null>(`/projects/${projectId}/brief-analysis`);

// Concept versions
export const listVersions = (projectId: string) =>
  req<ConceptVersion[]>(`/projects/${projectId}/versions`);

export const createVersion = (projectId: string, body: CreateVersionBody) =>
  req<ConceptVersion>(`/projects/${projectId}/versions`, {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const deleteVersion = (versionId: string) =>
  req<void>(`/versions/${versionId}`, { method: 'DELETE' });

export const scoreVersion = (versionId: string) =>
  req<ConceptVersion>(`/versions/${versionId}/score`, { method: 'POST' });

// Suggestions
export const listSuggestions = (projectId: string) =>
  req<Suggestion[]>(`/projects/${projectId}/suggestions`);

export const generateSuggestions = (projectId: string) =>
  req<Suggestion[]>(`/projects/${projectId}/suggestions/generate`, { method: 'POST' });

export const updateSuggestion = (suggestionId: string, status: 'new' | 'accepted' | 'dismissed') =>
  req<Suggestion>(`/suggestions/${suggestionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });

// Export
export const exportProject = (projectId: string) =>
  req<ProjectExport>(`/projects/${projectId}/export`);
