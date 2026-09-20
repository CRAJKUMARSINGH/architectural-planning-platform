# Security Checklist (Enterprise)

## Authentication & Authorization
- [ ] All mutating endpoints require authentication
- [ ] Organization isolation enforced at repository layer
- [ ] Role matrix implemented and tested
- [ ] Local AUTH_DISABLED flag impossible in staging/production configs
- [ ] Tokens have reasonable expiry and refresh strategy

## Input & Transport
- [ ] Request body size limits
- [ ] Rate limiting (IP + user)
- [ ] Strict CORS for non-local environments
- [ ] Security headers present
- [ ] No stack traces leaked to clients

## Data & Artifacts
- [ ] Artifacts content-addressed (SHA-256)
- [ ] Verification path exists
- [ ] Soft-delete and retention policy defined
- [ ] Audit events for sensitive actions

## Supply Chain
- [ ] Dependencies pinned
- [ ] Automated vulnerability scanning in CI
- [ ] Secret scanning enabled
- [ ] SBOM generated on release

## Operational
- [ ] Secrets only via environment / secret manager
- [ ] Health endpoints do not expose sensitive data
- [ ] Logs do not contain secrets or full geometry dumps by default

## OWASP Top 10 Mapping (High Level)
| Risk                         | Mitigation                                      |
|-----------------------------|--------------------------------------------------|
| Broken Access Control       | Repo-layer org isolation + role checks           |
| Cryptographic Failures      | TLS in transit; hashed artifact integrity        |
| Injection                   | Parameterized queries; Pydantic validation       |
| Insecure Design             | Geometry authority + conservative quality gates  |
| Security Misconfiguration   | Hardened defaults; no AUTH_DISABLED in prod      |
| Vulnerable Components       | Scanning + pinning                               |
| Auth Failures               | Strong IdP; short-lived tokens                   |
| Software & Data Integrity   | Signed reports + content hashes                  |
| Logging & Monitoring Failures | Structured logs + audit events                 |
| SSRF                        | Validate any outbound URLs; no open proxies      |
