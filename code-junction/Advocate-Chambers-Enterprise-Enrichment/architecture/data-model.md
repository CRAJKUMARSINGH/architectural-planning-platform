# Data Model (Enterprise Target)

## Core Entities

### Organization
- id (uuid)
- name
- slug
- created_at, updated_at, deleted_at

### User
- id (uuid)
- external_auth_id (from IdP)
- email
- display_name
- created_at, updated_at, deleted_at

### Membership
- id
- organization_id
- user_id
- role (owner | editor | viewer | reviewer)
- created_at

### Project
- id (uuid or stable string e.g. `proj-...`)
- organization_id
- name
- units (inch | mm | ...)
- current_revision_id (nullable)
- created_at, updated_at, deleted_at

### Revision
- id
- project_id
- revision_number
- parent_revision_id (nullable)
- model_storage_key / model_sha256
- rule_pack_version
- author_user_id
- reason
- validation_report_sha256 (nullable)
- created_at

### Job
- id
- project_id
- revision_id (nullable)
- type (generate | validate | enrich | quality_gate | ...)
- status (queued | running | succeeded | failed | cancelled)
- progress (0–100)
- payload (jsonb)
- error (text, nullable)
- created_at, started_at, finished_at
- created_by_user_id

### Artifact
- id
- job_id
- kind (dxf | pdf | svg | json-report | ...)
- storage_key
- sha256
- size_bytes
- created_at

### AuditEvent
- id
- organization_id (nullable)
- actor_user_id (nullable)
- action
- resource_type
- resource_id
- payload (jsonb)
- request_id
- created_at

## Geometry Storage Rule

- Authoritative geometry lives in content-addressed blobs (or versioned files) referenced by `Revision.model_sha256` / `model_storage_key`.
- Relational columns hold only metadata and pointers.
- Reports and exports are also content-addressed artifacts.

## Indexes (Minimum)

- projects(organization_id)
- revisions(project_id, revision_number)
- jobs(status, created_at)
- artifacts(job_id)
- audit_events(organization_id, created_at)
- memberships(user_id), memberships(organization_id)
