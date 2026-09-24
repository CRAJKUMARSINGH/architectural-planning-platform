# Contributing to Architectural Planning Platform

**Platform:** Hybrid parametric CAD / architectural planning intelligence  
**Stack:** Python 3.11 (geometry authority) · React 19.3 + Vite (editor) · FastAPI (adapter)

---

## Quick-start

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11 (`cat .python-version`) | pyenv or system install |
| Node | 20 LTS (`cat .nvmrc`) | nvm recommended |
| npm | ≥ 10 | bundled with Node 20 |
| Git | any recent | |

### 1 — Clone & install

```bash
git clone https://github.com/CRAJKUMARSINGH/architectural-planning-platform.git
cd architectural-planning-platform

# Python deps
pip install -e ".[dev]"

# Node deps (workspaces — installs apps/web + packages/* + services/*)
npm install
```

### 2 — Run baseline verification (single command)

```bash
make verify
```

This runs Python lint + mypy, TypeScript typecheck, Python unit tests, and the
quality-gate check. It should pass on a clean clone with no changes.

On Windows without `make`:

```powershell
npm run verify:baseline
```

### 3 — Run the development servers

```bash
# API (terminal 1)
npm run dev:api

# Web editor (terminal 2)
npm run dev:web
```

---

## Repository layout

```
architectural-planning-platform/
├── apps/web/          React 19.3 + Vite editor
├── packages/
│   ├── schema/        Shared Pydantic ↔ Zod schemas
│   └── recipes/       Project recipe definitions
├── services/api/      FastAPI thin adapter
│   └── db/            SQL schema + Alembic migrations
├── scripts/           Python enrichment / validation scripts (week1–28)
├── tests/             Python unittest suite
├── benchmarks/        Performance benchmark suite
├── bar-association-hall/  Domain reference project
├── docs/              Long-form documentation
│   ├── architecture/  ADRs
│   ├── enterprise/    Enterprise enrichment plan
│   └── history/       Weekly enrichment reports
├── baselines/         Frozen quality-gate + adversarial snapshots
│   └── 2026-09-20/
└── .github/workflows/ CI / CD
```

---

## Running tests

```bash
# All Python unit tests
python -m unittest discover -s tests -p 'test_*.py'

# Specific week
python -m unittest discover -s tests -p 'test_week23*.py'

# Quality gate
npm run validate:week21

# Adversarial suite
npm run test:week22
npm run test:week23

# Performance smoke
npm run validate:week25
```

---

## Linting & formatting

```bash
# Python
make lint-py
# or:
ruff check scripts services packages
ruff format --check scripts services packages
mypy scripts services --ignore-missing-imports

# TypeScript / Web
npm run lint:web
npm run typecheck:web
```

Auto-fix Python formatting:

```bash
ruff format scripts services packages
```

---

## Branch naming

| Prefix | Purpose |
|--------|---------|
| `feat/` | New feature or enrichment week |
| `fix/` | Bug fix |
| `e01/`, `e02/`, … | Enterprise enrichment week work |
| `chore/` | Tooling, deps, docs |
| `hotfix/` | Urgent production fix |

---

## Commit messages — Conventional Commits

```
<type>(<scope>): <short summary>

[optional body]
[optional footer]
```

Types: `feat` · `fix` · `chore` · `docs` · `refactor` · `test` · `perf` · `ci`

Examples:
```
feat(week29): add fire-egress corridor reachability check
fix(quality-gate): correct false-negative for blocked corridor
chore(e01): add pyproject.toml + Ruff configuration
```

---

## Pull request expectations

1. All existing Python unit tests pass (`make verify`).
2. No new critical adversarial false-negatives — the 30/30 adversarial detection score must be maintained.
3. Geometry authority stays in Python (see `docs/architecture/ADR-001-Geometry-Authority.md`).
4. Quality-gate classification must not regress — no new `BLOCKED` states without a corresponding fix.
5. Documentation updated if design decisions change.
6. No secrets committed — scan with `git diff --cached` before pushing.

---

## Non-negotiables (do not violate)

- **Geometry authority stays in Python.** React and FastAPI are clients — never sources of truth for walls, openings, stairs, or routes.
- **Conservative quality gates.** Missing evidence = `REVIEW_REQUIRED` or `INCOMPLETE`. Never auto-promote to issuable.
- **Presentation layers are non-authoritative.** Furniture, finishes, and AI-tool imports must not mutate canonical model geometry.
- **Professional review remains mandatory.** Software gates detect known defects. They do not replace licensed architects, engineers, or statutory authorities.

---

## Getting help

Open a GitHub issue or start a Discussion. Tag issues with:
- `domain` — CAD / NBC / RPwD rule questions
- `enterprise` — E01–E10 infrastructure work
- `bug` — confirmed defect
- `question` — general inquiry
