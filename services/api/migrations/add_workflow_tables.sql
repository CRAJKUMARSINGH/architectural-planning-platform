-- Migration: add_workflow_tables
-- Adds the three tables that bring the Archi Copilot workflow into the Platform.
-- Run against your existing PostgreSQL database *after* the core schema is in place.
--
-- Tables added:
--   brief_analyses     — AI-structured analysis of client briefs
--   concept_versions   — concept canvas snapshots with optional AI scores
--   copilot_suggestions — proactive AI suggestions per project
--
-- IMPORTANT: concept canvas blocks are stored as JSONB.  They are *not*
-- authoritative geometry.  Promote to geometry only via a queued Job.

BEGIN;

-- -----------------------------------------------------------------------
-- brief_analyses
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS brief_analyses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    brief_text          TEXT NOT NULL,
    summary             TEXT NOT NULL,
    space_program       JSONB NOT NULL DEFAULT '[]'::jsonb,
    constraints         JSONB NOT NULL DEFAULT '[]'::jsonb,
    opportunities       JSONB NOT NULL DEFAULT '[]'::jsonb,
    open_questions      JSONB NOT NULL DEFAULT '[]'::jsonb,
    provenance          JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version       VARCHAR(80) NOT NULL DEFAULT 'gemini-2.5-flash',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id  UUID REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_brief_analyses_project
    ON brief_analyses(project_id, created_at DESC);

-- -----------------------------------------------------------------------
-- concept_versions
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS concept_versions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id            UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    brief_analysis_id     UUID REFERENCES brief_analyses(id) ON DELETE SET NULL,
    name                  TEXT NOT NULL,
    floors                JSONB NOT NULL DEFAULT '["Ground Floor"]'::jsonb,
    blocks                JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall_score         DOUBLE PRECISION,
    program_fit_score     DOUBLE PRECISION,
    daylight_score        DOUBLE PRECISION,
    budget_fit_score      DOUBLE PRECISION,
    ai_commentary         TEXT,
    -- Link to geometry revision if this concept was promoted to the model.
    promoted_revision_id  UUID REFERENCES revisions(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id    UUID REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_concept_versions_project
    ON concept_versions(project_id, created_at DESC);

-- -----------------------------------------------------------------------
-- copilot_suggestions
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS copilot_suggestions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    category            VARCHAR(30) NOT NULL
                            CHECK (category IN ('program','site','daylight','budget','circulation','general')),
    text                TEXT NOT NULL,
    priority            VARCHAR(20) NOT NULL DEFAULT 'medium',
    status              VARCHAR(20) NOT NULL DEFAULT 'new'
                            CHECK (status IN ('new','accepted','dismissed')),
    suggestion_hash     VARCHAR(64),          -- SHA-256 of category+text for dedup
    provenance          JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version       VARCHAR(80) NOT NULL DEFAULT 'gemini-2.5-flash',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_copilot_suggestions_project
    ON copilot_suggestions(project_id, status, created_at DESC);

COMMIT;
