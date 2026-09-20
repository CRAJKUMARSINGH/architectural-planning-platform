# Project Archive and LFS Index

This document records the storage policy for completed planning projects in Advocate-Chambers.

## Current project families

| Project family | Current source locations | Archive slug | Migration status |
|---|---|---|---|
| Bar Association Hall | bar-association-hall, code-junction/Bar-Association-Standard-Drawing-Package | bar-association-hall | Week 28 inventory applied; legacy paths retained |
| Jamuniya-Shaktawat | Jamuniya-Shaktawat/CAD, Jamuniya-Shaktawat/PDF, reference images | jamuniya-shaktawat | Week 28 inventory applied; legacy paths retained |
| Advocate Chambers | CAD-Drawings and explicitly named root-level legacy assets | advocate-chambers | Week 28 inventory applied; five ambiguous root assets remain for review |

The complete machine-readable registry is
`projects/project-registry.json`; the path-level inventory is
`projects/project-inventory.json`. Shared application, validation, schema, and
documentation files remain under the `shared-repository` scope rather than
being copied into every project.

## Canonical destination

~~~text
projects/YYYY/project-slug/
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
  revisions/rNNN/
    manifest.json
  current.json
~~~

Large binary artifacts are governed by the repository .gitattributes file and Git LFS. Text models, schemas, manifests, Markdown, Python, and TypeScript remain normal Git files.

## Migration safety

Legacy directories are read-only until every artifact has a destination path and SHA-256 checksum. No files are deleted, overwritten, or renamed solely for organization. Duplicate cleanup requires a separate review and approval.

## Required project metadata

Each project must retain its building type, location, units, north/orientation, levels, source model, assumptions, rule-pack version, revision history, validation report, artifact hashes, and professional-review status.
