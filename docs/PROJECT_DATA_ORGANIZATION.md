# Professional project-data organization

The repository contains delivered material for three project packages:

1. **Bar Association Hall** — the Banswara G+1 planning and coordinated
   drawing package.
2. **Jamuniya-Shaktawat** — the revised floor-plan and reference-image package.
3. **Advocate Chambers** — the 16-drawing CAD/PDF delivery archive.

The current repository grew incrementally, so source models, inputs, CAD, PDFs,
renders, validation evidence, and shared application code are not uniformly
laid out. Week 28 introduces an **index-first migration** rather than moving
files blindly:

- `projects/project-registry.json` declares the three project scopes and the
  canonical future layout.
- `projects/project-inventory.json` inventories every tracked path with its
  project, role, storage hint, Git blob identity, and proposed destination.
- `bar-association-hall/standard/week28-organization-report.json` records the
  organization acceptance checks.
- Existing paths remain unchanged. No binary is deleted, renamed, overwritten,
  or silently deduplicated.

## Future canonical layout

The inventory proposes this structure for an approved later migration:

```text
projects/<project-id>/
  project.json
  01-inputs/
  02-source/
  03-outputs/
    cad/
    pdf/
    renders/
  04-validation/
  05-documentation/
  06-archive/
  current.json
shared/
  apps/
  packages/
  services/
  scripts/
  tests/
```

The actual source path remains the working reference until a migration has a
reviewed manifest and matching checksums. The `proposedCanonicalPath` field is
there to make the next move explicit and reversible.

## Naming and revision rules

- Keep project IDs stable and lowercase: `bar-association-hall`,
  `jamuniya-shaktawat`, and `advocate-chambers`.
- Keep inputs immutable after intake; create a new revision for corrections.
- Keep CAD, PDF, and render outputs under the same revision and manifest.
- Store validation results beside the revision they qualify.
- Never call a drawing `approved`, `issued`, or `for construction` unless the
  appointed professional and authority have explicitly signed that status.
- Keep ambiguous legacy root assets visible with `reviewRequired: true` rather
  than assigning them silently.

## Repeatable commands

```bash
npm run enrich:week27
npm run validate:week27
npm run test:week27
npm run enrich:week28
npm run validate:week28
npm run test:week28
```

This inventory is a coordination aid. It does not itself certify geometry,
ownership, professional approval, statutory compliance, or construction
readiness.