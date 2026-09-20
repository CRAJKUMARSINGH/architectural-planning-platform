-- Advocate-Chambers Enterprise — initial schema sketch
-- Postgres 15+
-- This is a starting point; adjust types and constraints to match final ORM.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_auth_id TEXT UNIQUE,
    email            TEXT NOT NULL UNIQUE,
    display_name     TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE TABLE memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    role            TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'viewer', 'reviewer')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id)
);

CREATE TABLE projects (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id      UUID NOT NULL REFERENCES organizations(id),
    name                 TEXT NOT NULL,
    units                TEXT NOT NULL DEFAULT 'inch',
    current_revision_id  UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at           TIMESTAMPTZ
);

CREATE TABLE revisions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID NOT NULL REFERENCES projects(id),
    revision_number         INTEGER NOT NULL,
    parent_revision_id      UUID REFERENCES revisions(id),
    model_storage_key       TEXT,
    model_sha256            TEXT,
    rule_pack_version       TEXT,
    author_user_id          UUID REFERENCES users(id),
    reason                  TEXT,
    validation_report_sha256 TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, revision_number)
);

-- Add FK from projects.current_revision_id after revisions exists
ALTER TABLE projects
    ADD CONSTRAINT projects_current_revision_fk
    FOREIGN KEY (current_revision_id) REFERENCES revisions(id);

CREATE TABLE jobs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL REFERENCES projects(id),
    revision_id      UUID REFERENCES revisions(id),
    type             TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    progress         INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    payload          JSONB NOT NULL DEFAULT '{}',
    error            TEXT,
    created_by_user_id UUID REFERENCES users(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ
);

CREATE TABLE artifacts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id       UUID NOT NULL REFERENCES jobs(id),
    kind         TEXT NOT NULL,
    storage_key  TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    size_bytes   BIGINT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    actor_user_id   UUID REFERENCES users(id),
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT,
    payload         JSONB NOT NULL DEFAULT '{}',
    request_id      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_revisions_project ON revisions(project_id);
CREATE INDEX idx_jobs_status_created ON jobs(status, created_at);
CREATE INDEX idx_artifacts_job ON artifacts(job_id);
CREATE INDEX idx_audit_org_created ON audit_events(organization_id, created_at);
CREATE INDEX idx_memberships_user ON memberships(user_id);
