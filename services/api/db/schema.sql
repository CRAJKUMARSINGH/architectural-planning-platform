-- Advocate-Chambers Enterprise — initial database schema
-- Postgres 15+
-- Managed by Alembic (services/api/db/migrations/).
-- This file is for reference and used by docker-compose initdb.
-- Run via Alembic in all other environments.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Organizations (primary tenancy boundary — see ADR-003)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_auth_id TEXT UNIQUE,            -- from IdP (Clerk / Keycloak)
    email            TEXT NOT NULL UNIQUE,
    display_name     TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Memberships (user ↔ organization with role)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'viewer', 'reviewer')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id)
);

-- ---------------------------------------------------------------------------
-- Projects
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    name                 TEXT NOT NULL,
    units                TEXT NOT NULL DEFAULT 'inch'
                             CHECK (units IN ('inch', 'mm', 'm', 'ft')),
    current_revision_id  UUID,               -- FK added below after revisions
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at           TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Revisions (versioned geometry pointers — authoritative geometry in blobs)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS revisions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id                  UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    revision_number             INTEGER NOT NULL,
    parent_revision_id          UUID REFERENCES revisions(id),
    -- Geometry stored in object store — only the pointer lives here (ADR-001)
    model_storage_key           TEXT,
    model_sha256                TEXT,
    rule_pack_version           TEXT,        -- e.g. india-preliminary-review@1.0.0
    author_user_id              UUID REFERENCES users(id),
    reason                      TEXT,
    validation_report_sha256    TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, revision_number)
);

-- Now add deferred FK from projects → revisions
ALTER TABLE projects
    ADD CONSTRAINT projects_current_revision_fk
    FOREIGN KEY (current_revision_id) REFERENCES revisions(id)
    DEFERRABLE INITIALLY DEFERRED;

-- ---------------------------------------------------------------------------
-- Jobs (async work items — E04)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    revision_id         UUID REFERENCES revisions(id),
    type                TEXT NOT NULL
                            CHECK (type IN ('generate', 'validate', 'enrich',
                                            'quality_gate', 'export', 'benchmark')),
    status              TEXT NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued', 'running', 'succeeded',
                                              'failed', 'cancelled')),
    progress            INTEGER NOT NULL DEFAULT 0
                            CHECK (progress >= 0 AND progress <= 100),
    payload             JSONB NOT NULL DEFAULT '{}',
    error               TEXT,
    created_by_user_id  UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Artifacts (content-addressed outputs — DXF, PDF, SVG, JSON reports)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id       UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL
                     CHECK (kind IN ('dxf', 'pdf', 'svg', 'json-report',
                                     'sbom', 'performance-report', 'adversarial-report')),
    storage_key  TEXT NOT NULL,  -- path in object store
    sha256       TEXT NOT NULL,  -- content address (verify integrity offline)
    size_bytes   BIGINT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Audit events (immutable log — do not DELETE or UPDATE rows)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    actor_user_id   UUID REFERENCES users(id),
    action          TEXT NOT NULL,       -- e.g. project.create, revision.create
    resource_type   TEXT NOT NULL,
    resource_id     TEXT,
    payload         JSONB NOT NULL DEFAULT '{}',
    request_id      TEXT,                -- correlation with structured logs (E07)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_projects_org         ON projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_deleted     ON projects(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_revisions_project    ON revisions(project_id);
CREATE INDEX IF NOT EXISTS idx_revisions_proj_num   ON revisions(project_id, revision_number);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created  ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_project         ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_job        ON artifacts(job_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_sha256     ON artifacts(sha256);
CREATE INDEX IF NOT EXISTS idx_audit_org_created    ON audit_events(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor          ON audit_events(actor_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memberships_user     ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_memberships_org      ON memberships(organization_id);

-- ---------------------------------------------------------------------------
-- Dev seed: local single-developer org + user (non-production only)
-- Remove or gate behind ENV check in production migrations.
-- ---------------------------------------------------------------------------
INSERT INTO organizations (id, name, slug)
VALUES ('00000000-0000-0000-0000-000000000001', 'Local Dev Org', 'local-dev')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO users (id, email, display_name)
VALUES ('00000000-0000-0000-0000-000000000002', 'dev@local.example', 'Dev User')
ON CONFLICT (email) DO NOTHING;

INSERT INTO memberships (organization_id, user_id, role)
VALUES ('00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000002', 'owner')
ON CONFLICT (organization_id, user_id) DO NOTHING;
