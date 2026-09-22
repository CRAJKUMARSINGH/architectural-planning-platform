/**
 * useCommandDispatch — Phase 7 typed command dispatch hook.
 *
 * Wires the React editor to /api/v1/projects/{id}/commands/preview
 * and /api/v1/projects/{id}/commands/commit via TanStack Query mutations.
 *
 * Design rules (from IMPLEMENTATION_PLAN.md Phase 7):
 *  - Preview is a dry-run; it never persists.
 *  - Commit requires Idempotency-Key and If-Match headers.
 *  - On accepted commit, the analysis query is invalidated so the
 *    viewport re-fetches the updated canonical model.
 *  - On revision conflict (409) the caller receives a structured error
 *    so the UI can prompt the user to re-fetch before retrying.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

// ── Zod schemas ──────────────────────────────────────────────────────────────

const FindingSchema = z.object({
  rule: z.string(),
  severity: z.enum(['BLOCKER', 'ERROR', 'WARNING', 'INFO']),
  message: z.string(),
  objectIds: z.array(z.string()).default([]),
  evidence: z.record(z.unknown()).default({}),
  professionalReviewRequired: z.boolean().default(false),
});

const RevisionSummarySchema = z.object({
  revisionNumber: z.number(),
  revisionId: z.string(),
  projectId: z.string(),
  commandId: z.string(),
  operation: z.string(),
  modelSha256: z.string(),
  reason: z.string(),
});

export const CommandResultSchema = z.object({
  accepted: z.boolean(),
  replayed: z.boolean(),
  findings: z.array(FindingSchema),
  affectedObjectIds: z.array(z.string()),
  summary: RevisionSummarySchema.nullable().optional(),
  revisionId: z.string().uuid().nullable().optional(),
  modelSha256: z.string().nullable().optional(),
  validationState: z.string().nullable().optional(),
  previewOnly: z.boolean(),
});

export type CommandResult = z.infer<typeof CommandResultSchema>;
export type Finding = z.infer<typeof FindingSchema>;

// ── Command envelope builder ──────────────────────────────────────────────────

/** Canonical advocate-chambers.command.v1 envelope. */
export interface CommandEnvelopeInput {
  operation: string;
  parameters: Record<string, unknown>;
  baseRevision: number;
  projectId: string;
  authorId: string;
  reason?: string;
}

let _cmdCounter = 0;

function buildEnvelope(input: CommandEnvelopeInput) {
  _cmdCounter += 1;
  return {
    schemaVersion: 'advocate-chambers.command.v1',
    commandId: `cmd-browser-${Date.now()}-${_cmdCounter}`,
    projectId: input.projectId,
    baseRevision: input.baseRevision,
    authorId: input.authorId,
    operation: input.operation,
    parameters: input.parameters,
    idempotencyKey: `ik-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    reason: input.reason ?? `Browser: ${input.operation}`,
    source: 'user',
    clientTimestamp: new Date().toISOString(),
  };
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function postCommand(
  path: string,
  envelope: ReturnType<typeof buildEnvelope>,
  extraHeaders?: Record<string, string>,
): Promise<CommandResult> {
  const resp = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
    body: JSON.stringify({ command: envelope }),
  });

  if (resp.status === 404) throw new CommandDispatchError('Project not found', 404, []);
  if (resp.status === 401) throw new CommandDispatchError('Unauthenticated', 401, []);
  if (resp.status === 403) throw new CommandDispatchError('Insufficient role', 403, []);
  if (resp.status === 412) {
    throw new CommandDispatchError('Revision stale — please refresh before retrying', 412, []);
  }
  if (resp.status === 409) {
    const data = await resp.json().catch(() => ({}));
    throw new CommandDispatchError(
      data.detail ?? 'Revision conflict',
      409,
      [],
    );
  }

  const raw = await resp.json();
  return CommandResultSchema.parse(raw);
}

// ── Error type ────────────────────────────────────────────────────────────────

export class CommandDispatchError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly findings: Finding[],
  ) {
    super(message);
    this.name = 'CommandDispatchError';
  }
}

// ── Preview hook ──────────────────────────────────────────────────────────────

interface UsePreviewCommandOptions {
  projectId: string;
  currentRevision: number;
  authorId?: string;
  onSuccess?: (result: CommandResult) => void;
  onError?: (err: CommandDispatchError) => void;
}

/**
 * Dry-run mutation — calls /api/v1/projects/{id}/commands/preview.
 * Never persists anything. Returns findings + preview summary.
 */
export function usePreviewCommand({
  projectId,
  currentRevision,
  authorId = 'browser-user',
  onSuccess,
  onError,
}: UsePreviewCommandOptions) {
  return useMutation<CommandResult, CommandDispatchError, CommandEnvelopeInput>({
    mutationFn: async (input) => {
      const envelope = buildEnvelope({ ...input, projectId, baseRevision: currentRevision, authorId });
      return postCommand(
        `/api/v1/projects/${projectId}/commands/preview`,
        envelope,
        { 'If-Match': `"Rev:${currentRevision}"` },
      );
    },
    onSuccess,
    onError,
  });
}

// ── Commit hook ───────────────────────────────────────────────────────────────

interface UseCommitCommandOptions {
  projectId: string;
  currentRevision: number;
  authorId?: string;
  onSuccess?: (result: CommandResult) => void;
  onError?: (err: CommandDispatchError) => void;
}

/**
 * Persist mutation — calls /api/v1/projects/{id}/commands/commit.
 * On success, invalidates the analysis + revisions queries so the
 * viewport re-fetches the updated canonical model automatically.
 */
export function useCommitCommand({
  projectId,
  currentRevision,
  authorId = 'browser-user',
  onSuccess,
  onError,
}: UseCommitCommandOptions) {
  const qc = useQueryClient();

  return useMutation<CommandResult, CommandDispatchError, CommandEnvelopeInput>({
    mutationFn: async (input) => {
      const envelope = buildEnvelope({ ...input, projectId, baseRevision: currentRevision, authorId });
      return postCommand(
        `/api/v1/projects/${projectId}/commands/commit`,
        envelope,
        {
          'Idempotency-Key': envelope.idempotencyKey,
          'If-Match': `"Rev:${currentRevision}"`,
        },
      );
    },
    onSuccess: (result, _vars, _ctx) => {
      // Invalidate so viewport and revision list re-fetch
      void qc.invalidateQueries({ queryKey: ['analysis', projectId] });
      void qc.invalidateQueries({ queryKey: ['revisions', projectId] });
      onSuccess?.(result);
    },
    onError,
  });
}
