# Advocate-Chambers Implementation Plan

## 1. Product objective

Build a trustworthy architectural planning platform that converts a brief or
imported source drawing into:

1. a canonical, editable geometry model;
2. explainable validation findings;
3. synchronized 2D, 3D, section, and elevation views;
4. presentation-quality visualizations;
5. reviewable DXF, PDF, SVG, image, and evidence packages.

The governing principle is:

> **Create a structurally correct plan first, then render it beautifully.**

The supplied residential floor-plan images define the presentation-quality
target. They are visual references only. They are not construction, permit,
code, structural, MEP, survey, or authority certification.

## 2. Non-negotiable architecture

- Python remains the sole authority for walls, openings, stairs, levels, routes,
  site geometry, rule-pack evaluation, validation, and deterministic exports.
- React is a client and interaction layer; it must never become the source of
  truth for constructive geometry.
- FastAPI is a typed gateway and coordinator; long work runs in workers.
- Postgres stores metadata, revisions, jobs, memberships, and audit events.
- Object storage stores content-addressed geometry, reports, and exports.
- Redis/RQ delivers jobs; it contains no business logic.
- Presentation objects may add furniture, materials, plants, lighting, and
  decorative content, but cannot mutate canonical geometry.
- Missing evidence never becomes `PASS`.
- Every artifact must identify its model revision, rule-pack version, engine
  version, and content hash.
- Every output remains preliminary planning material until reviewed by the
  appointed professionals and authorities.

## 3. Target system flow

```text
Brief / source drawing
        |
        v
React editor
        | HTTPS + JWT
        v
FastAPI gateway
        |
        +--> typed command preview
        +--> revision commit
        +--> validation request
        +--> render/export job
        |
        v
Python geometry authority
        |
        +--> canonical model
        +--> quick validation
        +--> deterministic hash
        |
        v
Postgres + object storage
        |
        v
Redis/RQ workers
        |
        +--> full validation
        +--> technical drawings
        +--> presentation scene
        +--> render/export artifacts
        |
        v
Review links, findings, downloads, delivery package
```

## 4. Delivery sequence

### Phase 0 — Freeze the product contract

**Complexity: Medium**

Define five explicit product modes:

- **Brief:** requirements, constraints, assumptions, and missing information.
- **Model:** canonical geometry and typed edits.
- **Validate:** deterministic findings and quality gates.
- **Present:** non-authoritative furniture, materials, and render views.
- **Deliver:** exports, manifests, assumptions, and review evidence.

Define explicit states:

```text
DRAFT
VALIDATED
REVIEW_REQUIRED
BLOCKED
INCOMPLETE
NOT_ISSUABLE
```

Do not use a single `isValid` flag.

Exit criteria:

- product modes documented;
- states represented in schemas;
- professional-review boundary visible in the UI and exports;
- existing weekly/adversarial tests remain unchanged and passing.

### Phase 1 — Stabilize the canonical model

**Complexity: High**

Keep `packages/schema/project-v2.schema.json` as the compatibility base. Add
the contracts that surround it:

- `packages/schema/command.schema.json`;
- `packages/schema/finding.schema.json`;
- `packages/schema/revision.schema.json`;
- `packages/schema/render-manifest.schema.json`;
- `packages/schema/artifact-manifest.schema.json`.

Every drawable object must have:

```text
id
kind
levelId
source
status
revision
provenance
```

Define measurement policy:

- preserve the current external unit contract;
- convert units only at API/display boundaries;
- define linear, angular, area, and topology tolerances;
- define display rounding separately from geometry precision;
- add round-trip tests for inch, feet-inch, millimetre, and metre input.

Exit criteria:

- schema validation rejects malformed objects;
- model serialization is deterministic;
- model hash is stable for equivalent input;
- unit conversions do not alter intended geometry.

### Phase 2 — Add typed command execution

**Complexity: Very High**

Create a Python command layer, for example:

```text
packages/geometry/
  commands.py
  command_runner.py
  topology.py
  constraints.py
  tolerances.py
  revisions.py
  serializers.py
```

Initial commands:

- `create-project`;
- `add-level`;
- `add-space`;
- `resize-space`;
- `add-wall`;
- `split-wall`;
- `move-opening`;
- `resize-opening`;
- `add-window`;
- `add-stair`;
- `set-site-orientation`;
- `set-program-requirement`;
- `apply-furniture-operation`.

Command envelope:

```json
{
  "commandId": "cmd-unique-id",
  "projectId": "proj-example",
  "baseRevision": 12,
  "authorId": "user-id",
  "operation": "move-opening",
  "parameters": {
    "openingId": "door-main",
    "wall": "south",
    "offset": 148.5
  },
  "idempotencyKey": "client-unique-key"
}
```

Execution pipeline:

```text
schema validation
authorization
object existence check
topology preconditions
geometry operation
constraint propagation
quick validation
affected-object calculation
deterministic serialization
revision candidate
```

The difficult cases are wall joins, wall splits with openings, room-boundary
updates, stair continuity, door swings, curved site boundaries, stable IDs, and
floating-point drift. Use a robust computational-geometry library such as
GEOS/Shapely for geometric primitives where useful, but keep architectural
semantics in the project’s own Python code.

Exit criteria:

- every command has unit tests;
- invalid commands are rejected with structured findings;
- commands can be replayed deterministically;
- every accepted command produces a revision summary and affected-object list.

### Phase 3 — Implement persistent revisions

**Complexity: High**

Use Postgres for:

- organizations, users, memberships;
- projects;
- revisions;
- jobs;
- artifacts;
- audit events;
- comments and review links.

Use MinIO locally and S3/R2-compatible object storage in production for:

```text
orgs/{org}/projects/{project}/revisions/{sha}/model.json
orgs/{org}/projects/{project}/revisions/{sha}/validation.json
orgs/{org}/jobs/{job}/artifacts/{sha}/drawing.pdf
orgs/{org}/jobs/{job}/artifacts/{sha}/drawing.dxf
orgs/{org}/jobs/{job}/artifacts/{sha}/render.png
```

Revision transaction:

1. authenticate the user;
2. confirm organization membership;
3. confirm the base revision is current;
4. load the canonical model;
5. apply the typed command;
6. run quick validation;
7. serialize deterministically;
8. calculate SHA-256;
9. store the model blob;
10. create the revision row;
11. update the project’s current revision with optimistic locking;
12. enqueue full validation if required;
13. record an audit event.

Return `409 REVISION_CONFLICT` instead of silently merging geometry when the
client is stale.

All Alembic migrations require reversible downgrade paths.

### Phase 4 — Complete authentication and tenancy

**Complexity: High**

**Current delivery status:** Phase 4 hardening is implemented in the current
checkpoint. OIDC/JWKS validation, production configuration guards, database
membership authority, disabled-user enforcement, route dependency wiring, and
regression fixtures are complete. The remaining work in this phase is
deployment-specific identity-provider configuration and live integration
verification; it is not represented as a local code default.

Keep organization as the isolation boundary with roles:

```text
owner
editor
viewer
reviewer
```

Production authentication must validate:

- OIDC issuer;
- audience;
- JWKS signatures;
- token expiry;
- clock skew;
- key rotation;
- organization membership;
- role claims;
- disabled-user state.

Do not use a development JWT secret in staging or production.

Required security tests:

- User A cannot read User B’s project or revision.
- Viewer cannot create a revision.
- Reviewer can comment and review but cannot edit geometry.
- Editor cannot modify organization membership.
- Deleted projects remain inaccessible.
- Artifact downloads enforce organization access.

Authorization must be enforced by repository queries as well as HTTP routes.

### Phase 5 — Replace the prototype API

**Complexity: High**

Use versioned FastAPI routes:

```text
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
GET    /api/v1/projects/{id}/revisions
GET    /api/v1/projects/{id}/revisions/{revision}
POST   /api/v1/projects/{id}/commands/preview
POST   /api/v1/projects/{id}/commands/commit
GET    /api/v1/projects/{id}/analysis
POST   /api/v1/projects/{id}/validate
POST   /api/v1/projects/{id}/jobs
GET    /api/v1/jobs/{id}
GET    /api/v1/jobs/{id}/artifacts
POST   /api/v1/projects/{id}/comments
POST   /api/v1/projects/{id}/review-links
```

Every write supports:

- `Idempotency-Key`;
- `X-Request-ID`;
- `If-Match` or explicit base revision;
- structured error codes;
- audit context;
- trace ID;
- validation state.

Use Pydantic v2 for API contracts and generate TypeScript types from OpenAPI.

### Phase 6 — Make jobs durable

**Complexity: High**

Replace in-memory job and artifact dictionaries with persisted lifecycle data.

Job states:

```text
QUEUED
RUNNING
SUCCEEDED
FAILED
CANCELLED
EXPIRED
```

Each job stores:

- organization ID;
- project ID;
- revision ID;
- creator;
- type;
- payload hash;
- retry count;
- timeout;
- progress;
- error code;
- worker version;
- timestamps.

Workers receive a revision SHA rather than arbitrary user-provided paths.
Workers must enforce CPU, memory, wall-clock, and subprocess limits.

Failed jobs must retain their error report and never destroy the last valid
revision.

### Phase 7 — Build the real 2D editor

**Complexity: Very High**

Keep React 19, TypeScript, Vite, TanStack Query, and Zod. Add a small local
interaction store or reducer for transient UI state.

Viewport layers:

```text
grid
site
walls
spaces
openings
windows
stairs
dimensions
labels
furniture
routes
validation markers
selection overlays
temporary preview geometry
```

Use SVG initially for precise architectural plans. Introduce Canvas/WebGL only
when measured model size requires it.

For an edit:

1. render an optimistic local preview;
2. send a typed command;
3. show `PENDING_VALIDATION`;
4. receive the canonical result;
5. replace the preview with the server revision;
6. display findings on affected objects.

Every selectable visual object exposes:

```text
objectId
objectKind
levelId
revision
source
validationStatus
```

Dimensions need stable anchors, extension lines, unit formatting, collision
avoidance, scale-aware text, export behavior, and links back to object IDs.

### Phase 8 — Implement presentation rendering

**Complexity: Very High**

Use separate scene graphs.

Technical scene:

```text
walls, rooms, openings, stairs, dimensions, labels, north arrow, title block
```

Presentation scene:

```text
materials, furniture, plants, lighting, solar panels, vehicles, camera, shadows
```

Recommended interactive technology:

- Three.js;
- React Three Fiber;
- glTF assets;
- deterministic camera presets;
- fixed lighting profiles;
- versioned material/style tokens.

For high-quality server renders, evaluate Blender headless after the interactive
pipeline is stable. Blender provides better materials and lighting but adds
asset, worker, versioning, and deployment complexity.

Every render receives a manifest:

```json
{
  "modelSha256": "...",
  "styleVersion": "presentation-residential-v1",
  "assetCatalogVersion": "assets-v3",
  "cameraPreset": "axonometric-east-front",
  "sectionPlane": {
    "height": 3000,
    "unit": "mm"
  },
  "seed": 1516,
  "rendererVersion": "renderer-0.4.0"
}
```

Labels and dimensions should be rendered as controlled vector overlays or
generated separately. Generative image models must never be responsible for
final text, dimensions, or authoritative geometry.

Every presentation asset needs dimensions, scale, permitted rotations,
clearance envelope, service side, occupancy, source/license, asset hash, and an
explicit `presentationOnly` flag.

### Phase 9 — Build import safely

**Complexity: Very High**

Implement imports in this order:

1. native project JSON;
2. DXF;
3. vector PDF;
4. raster image;
5. OCR and assisted recognition.

Potential libraries:

- `ezdxf` for DXF;
- PyMuPDF or PDFium for PDF inspection;
- OpenCV for image preprocessing;
- OCR for text only;
- assisted recognition for uncertain geometry.

Every imported object retains:

```text
sourcePath
sourceId
sourceFormat
sourceHash
confidence
provenance
reviewRequired
```

Unknown or low-confidence objects remain uncertain and cannot silently become
authoritative geometry.

### Phase 10 — Build exports and delivery packages

**Complexity: High**

Delivery package:

```text
project-manifest.json
canonical-model.json
validation-report.json
quality-gate-report.json
drawing-set.pdf
drawing-set.dxf
presentation-render.png
assumptions.md
review-checklist.md
artifact-hashes.json
```

Every sheet includes project name, revision, date, units, scale, north arrow,
title block, drawing number, sheet size, source hash, validation state,
assumptions, and professional-review status.

No export with an unresolved `BLOCKER` may be presented as issue-ready.

### Phase 11 — Collaboration and review

**Complexity: High**

Implement:

- immutable review links;
- technical and presentation views;
- comments anchored to model objects;
- comments anchored to render viewpoints;
- revision comparison;
- reviewer identity;
- approval state;
- audit trail.

Example comment anchor:

```json
{
  "revision": 18,
  "anchorType": "space",
  "anchorId": "space-library",
  "viewpoint": {
    "camera": "axonometric-east-front",
    "level": "FF"
  },
  "body": "Increase daylight opening on the south wall."
}
```

### Phase 12 — Testing and quality gates

**Complexity: Very High**

Test categories:

- command unit tests;
- topology tests;
- wall/opening intersection tests;
- stair arithmetic;
- route connectivity;
- room adjacency;
- area calculations;
- unit conversion;
- serialization round trips;
- revision replay;
- property-based geometry tests;
- API contract tests;
- cross-tenant security tests;
- worker retry and crash recovery;
- artifact hash verification;
- migration upgrade/downgrade;
- object-store and Redis outage behavior;
- stale revision conflict;
- malicious upload and path traversal;
- Playwright visual regression.

Maintain golden fixtures for residential, chambers/offices, institutional,
parking, irregular sites, multi-floor stairs, incomplete briefs, DXF imports,
PDF imports, and presentation scenes.

The existing adversarial quality suite remains a merge blocker. A visual
comparison must be supplemented by DOM/SVG-level checks for labels and
dimensions.

### Phase 13 — Performance and observability

**Complexity: High**

Measure:

```text
brief compilation
quick validation
full validation
revision creation
2D render
3D scene load
server render
DXF export
PDF export
artifact upload
```

Initial proposed targets:

- quick validation under two seconds for a small residential model;
- command preview p95 under three seconds;
- interactive 2D view near 60 FPS for ordinary projects;
- full validation and rendering asynchronous;
- no silent timeouts;
- no data loss on worker failure.

Use:

- OpenTelemetry;
- structured JSON logs;
- Prometheus;
- Grafana;
- request, job, revision, and organization correlation IDs;
- error tracking with sensitive-data filtering.

## 5. Release sequence

| Release | Result | Complexity |
|---|---|---:|
| R0 | Contracts, invariants, fixtures, baseline | Medium |
| R1 | Postgres, object storage, real revisions | High |
| R2 | Typed commands, optimistic locking, validation deltas | Very high |
| R3 | Functional 2D editor with server round-trip | Very high |
| R4 | Durable jobs and DXF/PDF/SVG artifacts | High |
| R5 | Deterministic presentation scene and asset catalog | Very high |
| R6 | Sample-quality 3D renders and presentation sheets | Very high |
| R7 | DXF/PDF/image import with provenance | Very high |
| R8 | Collaboration, review links, comments, approvals | High |
| R9 | Enterprise security, performance, observability, deployment | Very high |

## 6. First vertical slice

The first complete implementation should be intentionally narrow:

1. Open one residential multi-floor project.
2. Select one door in the 2D editor.
3. Move the door using a typed command.
4. Validate the revised geometry.
5. Save an immutable revision.
6. Display the updated canonical plan.
7. Generate one deterministic axonometric presentation view.
8. Export a review package containing the model, findings, image, and hashes.

Do not start with a large photorealistic renderer. Prove this vertical slice
first. It establishes the core trust relationship between the model, the
validation system, the UI, and the final presentation.

## 7. Immediate engineering tickets

1. Add command and finding schemas.
2. Add typed Python command models.
3. Add deterministic command replay tests.
4. Replace static project lookup with Postgres queries.
5. Add revision creation with optimistic locking.
6. Move geometry and reports to object storage.
7. Replace in-memory jobs with persisted jobs.
8. Add authenticated project-scoped API dependencies.
9. Connect the React viewport to `/analysis`.
10. Add command preview to the property inspector.
11. Implement and test `move-opening`.
12. Render the canonical result in 2D.
13. Run full validation after commit.
14. Store the validation report against the revision.
15. Add one deterministic sample-style render.
16. Add visual regression against the supplied reference set.
17. Add the delivery manifest and review disclaimer.
