# Enterprise Enrichment Programme — Documentation

This folder contains the full 10-week enterprise enrichment plan for the
**Architectural Planning Platform**, sourced from the enrichment package at
`code-junction/Architectural-Planning-Platform-Enterprise-Enrichment/`.

## Contents

```
docs/enterprise/
├── README.md                   ← this file
├── 00-OVERVIEW.md              ← executive summary & principles
├── ENTERPRISE_ROADMAP.md       ← full 10-week detailed plan
├── weeks/
│   ├── E01-Foundation.md
│   ├── E02-Persistence.md
│   ├── E03-Auth-Tenancy.md
│   ├── E04-Jobs-Storage.md
│   ├── E05-CICD.md
│   ├── E06-API-Frontend.md
│   ├── E07-Observability.md
│   ├── E08-Security.md
│   ├── E09-Staging-Release.md
│   └── E10-Stabilization.md
├── checklists/
│   ├── code-quality.md
│   ├── professional-review.md
│   ├── release.md
│   └── security.md
└── templates/
    ├── ADR-template.md
    └── weekly-report-template.md
```

## How to Use

1. Read `00-OVERVIEW.md` for guiding principles before touching any enterprise work.
2. Execute one week at a time. Each `weeks/E0X-*.md` contains tasks + acceptance criteria.
3. Record decisions using the ADR template in `docs/architecture/` (not here).
4. Gate every PR with `make verify` and the quality-gate contract.

## Core Non-Negotiables

1. **Geometry authority stays in Python.** React and FastAPI are clients only.
2. **Quality gates stay conservative.** Missing evidence = `REVIEW_REQUIRED`, never silent pass.
3. **Presentation / AI-tool inputs never mutate authoritative geometry.**
4. **Professional architectural, structural, fire, accessibility, and statutory review remain mandatory.**

See `docs/architecture/` for the formal ADRs.
