# Contributing to Advocate-Chambers

Advocate-Chambers is a deterministic architectural planning platform. Python
owns authoritative geometry, validation findings, and exports. The React
application and FastAPI service are adapters around that model.

## Supported toolchain

- Node.js 20 LTS (`.nvmrc`)
- Python 3.11 (`.python-version`)
- npm 10+

Create a local environment and install the optional development tools:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
npm install
```

## Verification

The E01 baseline command runs the full Python test suite, adversarial
validation, the performance smoke benchmark, and the quality gate:

```bash
npm run verify:baseline
```

Focused commands remain available for local iteration:

```bash
npm run test:week1
npm run test:week1-fixtures
npm run typecheck:web
```

`REVIEW_REQUIRED` from the quality gate is an honest result when external
professional-review evidence is pending. It is not converted into a pass by
the verification wrapper.

## Change expectations

1. Use a feature branch named `feat/<short-name>`, `fix/<short-name>`, or
   `docs/<short-name>`.
2. Preserve geometry authority in Python and do not make presentation objects
   authoritative.
3. Add a failing and passing fixture for each new validation rule.
4. Keep generated CAD/PDF binaries and unrelated legacy assets untouched.
5. Run `npm run verify:baseline` before opening a pull request.
6. Use Conventional Commits, for example:
   `feat(validation): add explicit landing-zone finding`.

Every change remains preliminary planning infrastructure and does not replace
licensed architectural, structural, fire/life-safety, accessibility, MEP,
survey, or authority review.