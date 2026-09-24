# Architectural Planning Platform Finishing Guide

Planned future repository name: `architectural-planning-platform`

This guide is for taking the repository from a fresh clone to a reviewable, reproducible, release-ready state.

It is written against the current repository structure and scripts in `README.md`, `CONTRIBUTING.md`, `Makefile`, `package.json`, `.github/workflows/ci.yml`, and `.github/workflows/release.yml`.

The current GitHub repository is still named `Advocate-Chambers`, but the preferred future functional name is `architectural-planning-platform`. This guide now includes both names so maintainers can transition without confusion.

> Preliminary planning material only. Nothing in this repository should be treated as construction-ready, permit-ready, structural certification, fire approval, accessibility certification, or statutory authority approval without independent professional review.

## 1. What this repository contains

This repository is not only a web app. It combines:

- a Python geometry and validation authority in `packages/geometry`, `scripts`, and `services`
- a FastAPI API in `services/api`
- a React + Vite editor in `apps/web`
- a worker service in `services/worker`
- architectural reference assets and generated outputs in `bar-association-hall`, `CAD-Drawings`, and related folders
- baselines, benchmarks, CI rules, and release scaffolding for validating delivery quality

The key rule of the repository is simple:

> Python remains the authority for geometry, rules, validation, revisions, and deterministic exports.

## 2. Recommended finishing outcome

A "finished" state for this repository should mean all of the following are true:

1. The repo installs cleanly on Python 3.11 and Node 20.
2. Baseline verification passes on a clean checkout.
3. The API and web editor both start locally.
4. Domain validation and quality-gate reports can be reproduced.
5. The `bar-association-hall/standard` outputs remain available as the reference package.
6. CI can run without surprise local-only steps.
7. Release tagging can produce a reviewable package and GitHub release artifacts.
8. Documentation clearly tells a contributor how to run, validate, and ship the project.

## 3. Planned repository rename

The selected future repo name is:

```text
architectural-planning-platform
```

When you apply the rename on GitHub, update these items together:

1. repository name on GitHub
2. local clone folder name
3. README title and opening description
4. any badges, URLs, screenshots, or docs that still say `Advocate-Chambers`
5. release notes and any downstream scripts that assume the old folder name

Recommended transition rule:

- keep product and domain wording such as "Advocate Chambers" and "Bar Association Hall" where they refer to the project content
- use `architectural-planning-platform` when referring to the repository as software

Example rename flow:

```bash
# after renaming the GitHub repository
git remote set-url origin https://github.com/CRAJKUMARSINGH/architectural-planning-platform.git
```

If you want local folder naming to match the new repo:

```bash
cd ..
mv Advocate-Chambers architectural-planning-platform
cd architectural-planning-platform
```

## 4. Prerequisites

Install these first:

- Python `3.11`
- Node `20 LTS`
- npm `>= 10`
- Git
- Docker Desktop or Docker Engine with Compose, if you want the full stack

Check the versions:

```bash
python --version
node --version
npm --version
git --version
docker --version
docker compose version
```

## 5. Fresh clone setup

From a new machine:

```bash
# current repository name
git clone https://github.com/CRAJKUMARSINGH/Advocate-Chambers.git
cd Advocate-Chambers

# Python dependencies
pip install -e ".[dev]"

# Node workspace dependencies
npm install
```

After the repository is renamed, the equivalent future clone flow should become:

```bash
git clone https://github.com/CRAJKUMARSINGH/architectural-planning-platform.git
cd architectural-planning-platform

pip install -e ".[dev]"
npm install
```

If you use a virtual environment, activate it before `pip install`.

## 6. Environment configuration

Copy the template:

```bash
cp .env.example .env
```

Review and adjust at least these values in `.env`:

- `ENV=development`
- `DATABASE_URL`
- `REDIS_URL`
- `AUTH_DISABLED`
- `JWT_SECRET`
- `OIDC_ISSUER`
- `OIDC_AUDIENCE`
- `OIDC_JWKS_URL`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `GEMINI_API_KEY`

For local development, use these rules:

- set `AUTH_DISABLED=true` only for local development
- do not use development JWT settings in staging or production
- keep `GEMINI_API_KEY` optional unless you are testing AI endpoints

## 7. Baseline verification

The first finishing checkpoint is a clean baseline run:

```bash
make verify
```

On systems without `make`:

```bash
npm run verify:baseline
```

What a good baseline means:

- Python lint runs
- Python formatting checks run
- mypy runs
- TypeScript typecheck runs
- Python tests run
- the quality gate can be generated and checked

If `make verify` fails, do not call the repository finished yet.

## 8. Run the app locally

Start the API:

```bash
npm run dev:api
```

Start the web editor in another terminal:

```bash
npm run dev:web
```

Useful companion commands:

```bash
npm run typecheck:web
npm run build:web
python -m unittest discover -s tests -p 'test_*.py'
```

The API is served by `uvicorn services.api.main:app --reload --port 8000`.

## 9. Full-stack Docker run

To bring up the local stack with the compose files in the repo:

```bash
docker compose build
docker compose up -d
```

Useful helpers from `Makefile`:

```bash
make docker-build
make docker-up
make docker-staging
make docker-down
```

Use Docker when you want a closer approximation to the service stack with API, worker, Redis, database, object storage, and web components.

## 10. Domain and quality validation

This repository has important domain-specific checks. A finished handoff should confirm the critical ones still run.

### Core validation

```bash
npm run validate:week21
npm run test:week22
npm run test:week23
npm run validate:week25
```

### Important domain references

- `bar-association-hall/standard/quality-gate-report.json`
- `bar-association-hall/standard/week23-adversarial-expansion-report.json`
- `bar-association-hall/standard/week25-performance-report.json`
- `baselines/2026-09-20/quality-gate-report.json`

### Why these matter

- Week 21 checks the quality-gate state
- Week 22 and Week 23 exercise adversarial detection
- Week 25 covers performance smoke validation
- the baseline snapshots in `baselines/2026-09-20` act as regression anchors

## 11. Reference project and artifacts

The repo's main reference delivery package lives in `bar-association-hall`.

Before calling the repo finished, confirm these remain understandable and reproducible:

- source JSON inputs such as `site_plan.json` and `preliminary_plans.json`
- generated CAD and PDF outputs in `bar-association-hall/CAD` and `bar-association-hall/PDF`
- reference package outputs in `bar-association-hall/standard`
- validation and delivery scripts in `bar-association-hall/*.py` and `scripts/*.py`

Useful commands:

```bash
npm run draw:refined
npm run draw:standard
npm run validate:standard
python bar-association-hall/validate_plan.py
python bar-association-hall/traecad_engine.py
```

## 12. CI finishing checklist

The repository CI expects this flow:

1. lint and typecheck
2. unit tests and selected domain validation
3. adversarial suite and quality gate checks
4. performance smoke on `main`

Before pushing a finishing branch, confirm:

- `npm install` completes cleanly
- `pip install -e ".[dev]"` completes cleanly
- `make verify` passes
- key validation scripts still generate reports
- no secrets are committed
- generated reports remain in the expected paths used by CI
- any hard-coded repository references are updated if the rename to `architectural-planning-platform` has already happened

## 13. Release finishing checklist

The release workflow triggers on tags matching `v*`.

A release-ready state should include:

1. all tests passing
2. quality gate produced
3. adversarial suite run
4. release check script passing
5. expected report artifacts present
6. version tag prepared

Recommended release sequence:

```bash
git checkout -b docs/finish-guide
git add docs/FINISHING_GUIDE.md
git commit -m "docs(repo): add finishing guide"
git push origin docs/finish-guide
```

If the repository rename has already happened, also check:

- GitHub Actions still run from the renamed repository
- any release body text still describing the old repository name is updated
- release attachments and docs link to the renamed repository path

If you are releasing from `main` with a version tag:

```bash
git checkout main
git pull
git tag v1.0.1
git push origin v1.0.1
```

That should trigger the workflow in `.github/workflows/release.yml`.

## 14. What still counts as unfinished

Even if the repo runs, do not mark it finished if any of these are still true:

- the baseline verification is failing
- the web app starts but the API contract is broken
- the quality gate or adversarial reports no longer generate
- the main reference outputs in `bar-association-hall/standard` are missing or stale
- environment setup is undocumented for a fresh contributor
- release artifacts cannot be reproduced from repository scripts
- the repository has been renamed but the docs and remote URLs still mix old and new naming in a confusing way

## 15. Suggested final handoff standard

The repository can be handed off as "finished enough to use and continue" when:

- setup from a clean clone is documented and repeatable
- local dev works with `npm run dev:api` and `npm run dev:web`
- the baseline, adversarial, and performance validations are reproducible
- the reference planning package remains intact
- CI and release workflows match the actual repo layout
- the professional-review boundary remains explicit in docs and outputs
- the planned repository name `architectural-planning-platform` is either fully adopted or clearly documented as a pending rename

## 16. Minimal maintainer workflow

For day-to-day maintenance, this sequence is the safest short version:

```bash
pip install -e ".[dev]"
npm install
cp .env.example .env
make verify
npm run dev:api
npm run dev:web
```

Before merge:

```bash
make verify
npm run test:week22
npm run test:week23
npm run validate:week25
```

Before release:

```bash
python -m unittest discover -s tests -p 'test_*.py'
npm run validate:week21
npm run test:week22
npm run test:week23
python scripts/enterprise/release_check.py --version vX.Y.Z
```

## 17. Integrated project policy

The following policy applies to all contributors and maintainers:

### No hidden CI failures

All CI steps that enforce correctness must fail closed. The use of `|| true` is reserved for optional dependency installation and cleanup commands only. It must not be applied to:

- type-checking (mypy)
- domain validation (week21, week23, week26, week27)
- adversarial test suites (week22, week23)
- quality-gate contract checks
- performance validation

### Phase 14/15 regression checks

Phases 14 (AI Brief Analysis) and 15 (Concept Canvas) are complete. Any change touching `services/ai`, `packages/geometry`, or `apps/web/src/components/canvas` must not regress the existing 718+ passing tests.

### Gemini secret handling

`GEMINI_API_KEY` must never be committed. It is injected as a GitHub Actions secret for CI runs that test AI endpoints. All other functionality must degrade gracefully when the key is absent.

### AI advisory status

All AI-generated analysis, scoring, and suggestions are advisory. They do not constitute architectural, structural, fire-safety, or accessibility certification. This boundary must remain explicit in API responses and documentation.

### Python geometry authority

Python is the sole authority for geometry, rules, validation, revisions, and deterministic exports. TypeScript/React must not reimplement geometry logic.

### Professional review requirements

All outputs from this platform are preliminary planning material. Construction readiness, permit issuability, structural adequacy, fire/life-safety compliance, and accessibility (RPwD) compliance all require independent review by licensed professionals and statutory authorities.

### Deferred repository rename

The GitHub repository will be renamed to `architectural-planning-platform` when the team is ready. Until then, maintain both names in documentation as documented in section 3 of this guide.

## 18. Recommended next cleanup items

If you want to improve polish after adding this guide, these are the highest-value follow-ups:

1. Rename the GitHub repository to `architectural-planning-platform`.
2. Confirm whether every `week*` script still reflects the current status text in the docs.
3. Add a short "quick release" section to `README.md`.
4. Decide whether large CAD/PDF assets should stay in the main repo or move to a release/archive strategy.
5. Add one documented "golden path" contributor script for Linux and one for Windows.
6. Set up `GEMINI_API_KEY` as a GitHub Actions secret to enable full AI endpoint testing in CI.

---

If you received this repository as a zip package, unpack it, review `docs/FINISHING_GUIDE.md` first, then run the setup and verification steps in order.
