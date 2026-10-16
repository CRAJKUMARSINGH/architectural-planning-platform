# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch | ✅ Active |
| Enterprise candidate tags | ✅ Active |
| Historical weekly snapshots | ❌ No security fixes |

---

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Report security issues privately:

1. Email the maintainer directly (see `CODEOWNERS` or GitHub profile).
2. Use GitHub's private **Security Advisory** feature:  
   `https://github.com/CRAJKUMARSINGH/architectural-planning-platform/security/advisories/new`
3. Include:
   - Affected component (API, worker, web, Python pipeline)
   - Description of the vulnerability and potential impact
   - Steps to reproduce (if safe to share)
   - Suggested fix (optional)

We aim to acknowledge within **48 hours** and provide a timeline within **7 days**.

---

## Security Model

### Geometry Authority
Authoritative geometry, rule-pack evaluation, and report generation remain exclusively in
Python workers. React and FastAPI act as coordinators. This boundary protects against
injection of malformed geometry through the UI layer.

### Quality-Gate Integrity
Quality-gate findings are content-addressed (SHA-256). Any modification of a report after
signing is detectable. The platform does NOT auto-promote designs to "issuable" status —
`REVIEW_REQUIRED` is the honest default pending professional sign-off.

### Data Isolation
Projects belong to organizations. Authorization is enforced at the repository/query layer,
not only at the HTTP boundary. See `docs/architecture/ADR-003-Tenancy-Model.md`.

### Professional Boundary
This software aids architectural planning. It does **not** certify construction readiness,
permit readiness, fire safety, structural adequacy, or accessibility compliance. All outputs
require independent professional review before use in regulated contexts.

---

## Known Security Properties (E08 complete — October 2026)

- ✅ All mutating API endpoints require authentication (JWT / OIDC).
- ✅ Organization-level data isolation enforced at repository layer.
- ✅ Artifacts are content-addressed (SHA-256) and verifiable offline.
- ✅ CORS restricted to approved origins via `CORS_ALLOW_ORIGINS` env-var; localhost-only default.
- ✅ Rate limiting applied at the API gateway.
- ✅ Dependencies pinned; automated vulnerability scanning in CI (`pip-audit` + `npm audit`).
- ✅ SBOM generated on every release tag.
- ✅ `AUTH_DISABLED=true` flag rejected at startup in staging/production.
- ✅ JWT/OIDC error details never forwarded to clients (logged server-side only).
- ✅ `/metrics` endpoint protected by `METRICS_TOKEN` env-var in non-dev environments.
- ✅ OIDC deployment compose stack requires explicit secrets (`:?` syntax — no weak defaults).
- ✅ TypeScript strict mode — 0 errors. `tsc --noEmit` is a required CI check.

---

## Scope — What Is In Scope for Security Reports

- Authentication / authorization bypass
- Organization data leakage across tenants
- Injection via API inputs (SQL, command, path traversal)
- Artifact integrity bypass (forging SHA-256 validation)
- Secrets exposed in logs, API responses, or repository history
- Supply-chain concerns (dependency confusion, typosquatting)

---

## Out of Scope

- Professional review accuracy (this is a domain/process matter, not a security vulnerability)
- Social engineering
- Physical access
