# Enterprise Enrichment Programme — Documentation

This folder contains the full 10-week enterprise enrichment plan and completion records
for the **Architectural Planning Platform**.

## Contents

```
docs/enterprise/
├── README.md                        ← this file
├── 00-OVERVIEW.md                   ← executive summary & principles
├── ENTERPRISE_ROADMAP.md            ← full 10-week detailed plan
├── due-tasks.md                     ← open tasks (E09–E10 only; E01–E08 complete)
├── weeks/
│   ├── E01-Foundation.md            ✅ Complete
│   ├── E02-Persistence.md           ✅ Complete
│   ├── E03-Auth-Tenancy.md          ✅ Complete
│   ├── E04-Jobs-Storage.md          ✅ Complete
│   ├── E05-CICD.md                  ✅ Complete
│   ├── E06-API-Frontend.md          ✅ Complete
│   ├── E07-Observability.md         ✅ Complete
│   ├── E08-Security.md              ✅ Complete (2026-10-16)
│   ├── E09-Staging-Release.md       📋 In Progress
│   └── E10-Stabilization.md         📋 Planned
├── checklists/
│   ├── code-quality.md
│   ├── professional-review.md
│   ├── release.md
│   └── security.md                  ← updated 2026-10-16 with E08 completion ticks
└── templates/
    ├── ADR-template.md
    └── weekly-report-template.md
```

## How to Use

1. Read `00-OVERVIEW.md` for guiding principles before touching any enterprise work.
2. E01–E08 are complete — read the corresponding `weeks/E0X-*.md` for what was delivered.
3. For E09–E10, open `weeks/E09-Staging-Release.md` or `weeks/E10-Stabilization.md`
   for the task list and acceptance criteria.
4. Record new decisions using the ADR template in `docs/architecture/` (not here).
5. Gate every PR with `make verify` and the quality-gate contract.

## Current Status

| Week | Theme | Status |
|------|-------|--------|
| E01 | Foundation & Hygiene | ✅ Complete |
| E02 | Persistence Layer | ✅ Complete |
| E03 | Auth & Tenancy | ✅ Complete |
| E04 | Async Jobs & Storage | ✅ Complete |
| E05 | CI/CD & Automated Gates | ✅ Complete |
| E06 | API & Frontend Hardening | ✅ Complete |
| E07 | Observability | ✅ Complete |
| E08 | Security Hardening | ✅ Complete |
| E09 | Staging & Release | 📋 In Progress |
| E10 | Stabilisation | 📋 Planned |

## Core Non-Negotiables

1. **Geometry authority stays in Python.** React and FastAPI are clients only.
2. **Quality gates stay conservative.** Missing evidence = `REVIEW_REQUIRED`, never silent pass.
3. **Presentation / AI-tool inputs never mutate authoritative geometry.**
4. **Professional architectural, structural, fire, accessibility, and statutory review remain mandatory.**

See `docs/architecture/` for the formal ADRs.
