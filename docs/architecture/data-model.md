# Data Model — Enterprise Target

## Core Entities

### Organization
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| name | TEXT | Display name |
| slug | TEXT | URL-safe unique identifier |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | Soft delete |

### User
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| external_auth_id | TEXT | From IdP (Clerk/Keycloak) |
| email | TEXT | Unique |
| display_name | TEXT | |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### Membership
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| organization_id | UUID → Organization | |
| user_id | UUID → User | |
| role | ENUM | `owner` \| `editor` \| `viewer` \| `reviewer` |
| created_at | TIMESTAMPTZ | |

### Project
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| organization_id | UUID → Organization | Isolation boundary |
| name | TEXT | |
| units | TEXT | `inch` \| `mm` |
| current_revision_id | UUID → Revision | Nullable |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | |

### Revision
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| project_id | UUID → Project | |
| revision_number | INTEGER | Sequential, unique per project |
| parent_revision_id | UUID → Revision | Nullable — history chain |
| model_storage_key | TEXT | Object-store path |
| model_sha256 | TEXT | Content address of geometry blob |
| rule_pack_version | TEXT | E.g. `india-preliminary-review@1.0.0` |
| author_user_id | UUID → User | Nullable |
| reason | TEXT | Human-readable change summary |
| validation_report_sha256 | TEXT | Nullable |
| created_at | TIMESTAMPTZ | |

### Job
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| project_id | UUID → Project | |
| revision_id | UUID → Revision | Nullable |
| type | TEXT | `generate` \| `validate` \| `enrich` \| `quality_gate` |
| status | ENUM | `queued` \| `running` \| `succeeded` \| `failed` \| `cancelled` |
| progress | INTEGER | 0–100 |
| payload | JSONB | Job-type-specific input |
| error | TEXT | Nullable |
| created_by_user_id | UUID → User | Nullable |
| created_at / started_at / finished_at | TIMESTAMPTZ | |

### Artifact
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| job_id | UUID → Job | |
| kind | TEXT | `dxf` \| `pdf` \| `svg` \| `json-report` |
| storage_key | TEXT | Object-store path |
| sha256 | TEXT | Content address |
| size_bytes | BIGINT | |
| created_at | TIMESTAMPTZ | |

### AuditEvent
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| organization_id | UUID → Organization | Nullable |
| actor_user_id | UUID → User | Nullable (system actions) |
| action | TEXT | E.g. `project.create`, `revision.create` |
| resource_type | TEXT | |
| resource_id | TEXT | |
| payload | JSONB | |
| request_id | TEXT | For correlation with logs |
| created_at | TIMESTAMPTZ | |

---

## Geometry Storage Rule

> Authoritative geometry lives in **content-addressed blobs** (object store) referenced by
> `Revision.model_sha256` / `model_storage_key`. Relational columns hold only metadata and
> pointers. Reports and exports are also content-addressed artifacts.

This enforces ADR-001: the database never becomes the authority for wall/opening/stair topology.

---

## Required Indexes

```sql
CREATE INDEX idx_projects_org         ON projects(organization_id);
CREATE INDEX idx_revisions_project    ON revisions(project_id, revision_number);
CREATE INDEX idx_jobs_status_created  ON jobs(status, created_at);
CREATE INDEX idx_artifacts_job        ON artifacts(job_id);
CREATE INDEX idx_audit_org_created    ON audit_events(organization_id, created_at);
CREATE INDEX idx_memberships_user     ON memberships(user_id);
CREATE INDEX idx_memberships_org      ON memberships(organization_id);
```

---

## Migration Strategy

- Managed by **Alembic** (`services/api/db/`).
- All migrations are reversible (downgrade path required).
- Schema changes that affect geometry hash or rule-pack version must be versioned alongside
  the rule-pack itself.
