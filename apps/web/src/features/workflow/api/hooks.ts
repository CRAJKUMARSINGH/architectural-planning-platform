import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from './client';
import type { AnalyzeBriefBody, CreateVersionBody } from '../types';

// ── Query keys ────────────────────────────────────────────────────────────────
export const keys = {
  briefAnalysis: (pid: string) => ['workflow', 'brief', pid] as const,
  versions: (pid: string) => ['workflow', 'versions', pid] as const,
  version: (id: string) => ['workflow', 'version', id] as const,
  suggestions: (pid: string) => ['workflow', 'suggestions', pid] as const,
  export: (pid: string) => ['workflow', 'export', pid] as const,
};

// ── Brief ─────────────────────────────────────────────────────────────────────
export function useBriefAnalysis(projectId: string) {
  return useQuery({
    queryKey: keys.briefAnalysis(projectId),
    queryFn: () => api.getBriefAnalysis(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
}

export function useAnalyzeBrief(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AnalyzeBriefBody) => api.analyzeBrief(projectId, body),
    onSuccess: (data) => {
      qc.setQueryData(keys.briefAnalysis(projectId), data);
    },
  });
}

// ── Versions ──────────────────────────────────────────────────────────────────
export function useVersions(projectId: string) {
  return useQuery({
    queryKey: keys.versions(projectId),
    queryFn: () => api.listVersions(projectId),
    enabled: Boolean(projectId),
  });
}

export function useCreateVersion(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateVersionBody) => api.createVersion(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.versions(projectId) }),
  });
}

export function useDeleteVersion(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (versionId: string) => api.deleteVersion(versionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.versions(projectId) }),
  });
}

export function useScoreVersion(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (versionId: string) => api.scoreVersion(versionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.versions(projectId) }),
  });
}

// ── Suggestions ───────────────────────────────────────────────────────────────
export function useSuggestions(projectId: string) {
  return useQuery({
    queryKey: keys.suggestions(projectId),
    queryFn: () => api.listSuggestions(projectId),
    enabled: Boolean(projectId),
  });
}

export function useGenerateSuggestions(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.generateSuggestions(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.suggestions(projectId) }),
  });
}

export function useUpdateSuggestion(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'new' | 'accepted' | 'dismissed' }) =>
      api.updateSuggestion(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.suggestions(projectId) }),
  });
}

// ── Export ────────────────────────────────────────────────────────────────────
export function useProjectExport(projectId: string) {
  return useQuery({
    queryKey: keys.export(projectId),
    queryFn: () => api.exportProject(projectId),
    enabled: false, // manual only
  });
}
