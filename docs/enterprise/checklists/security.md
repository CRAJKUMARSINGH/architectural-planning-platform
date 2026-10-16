# Security Checklist (Enterprise)

<!-- Last reviewed: 2026-10-16 — E08 complete -->

## Authentication & Authorization
- [x] All mutating endpoints require authentication
- [x] Organization isolation enforced at repository layer
- [x] Role matrix implemented and tested
- [x] Local AUTH_DISABLED flag impossible in staging/production configs
- [x] Tokens have reasonable expiry and refresh strategy

## Input & Transport
- [ ] Request body size limits ← E09 target
- [ ] Rate limiting (IP + user) ← E09 target
- [x] Strict CORS for non-local environments (`CORS_ALLOW_ORIGINS` env-var; `:?` defaults removed)
- [ ] Security headers present ← E09 target
- [x] No stack traces leaked to clients (JWT errors sanitised; 500 details are generic)

## Data & Artifacts
- [x] Artifacts content-addressed (SHA-256)
- [x] Verification path exists (`scripts/enterprise/verify_artifact.py`)
- [ ] Soft-delete and retention policy defined ← E10 target
- [x] Audit events for sensitive actions

## Supply Chain
- [x] Dependencies pinned
- [x] Automated vulnerability scanning in CI (`pip-audit` + `npm audit`)
- [x] Secret scanning enabled (grep-based + trufflehog3 run; 0 findings)
- [ ] SBOM generated on release ← E09 target (scaffolded, not yet CI-automated)

## Operational
- [x] Secrets only via environment / secret manager
- [x] Health endpoints do not expose sensitive data
- [x] Logs do not contain secrets or full geometry dumps by default
- [x] `/metrics` endpoint protected by `METRICS_TOKEN` env-var

## OWASP Top 10 Mapping (High Level)
| Risk                         | Mitigation                                       | Status |
|-----------------------------|--------------------------------------------------|--------|
| Broken Access Control       | Repo-layer org isolation + role checks           | ✅ |
| Cryptographic Failures      | TLS in transit; hashed artifact integrity        | ✅ |
| Injection                   | Parameterized queries; Pydantic validation       | ✅ |
| Insecure Design             | Geometry authority + conservative quality gates  | ✅ |
| Security Misconfiguration   | Hardened defaults; no AUTH_DISABLED in prod; no weak :- defaults | ✅ |
| Vulnerable Components       | Scanning + pinning; 0 CVEs as of 2026-10-16      | ✅ |
| Auth Failures               | Strong IdP; short-lived tokens; error detail sanitised | ✅ |
| Software & Data Integrity   | Signed reports + content hashes                  | ✅ |
| Logging & Monitoring Failures | Structured logs + audit events; /metrics protected | ✅ |
| SSRF                        | Validate any outbound URLs; no open proxies      | ✅ |
