# E08-Security

# Week E08 â€” Security Hardening

**Duration:** 4â€“6 days  
**Risk:** High  
**Depends on:** E03, E05

---

## Objectives

1. Reduce attack surface.
2. Strengthen supply-chain security.
3. Make artifact integrity verifiable.
4. Document the security posture.

---

## Task List

### 1. Request Hardening (1 day)

- [ ] Rate limiting (per IP / per user).
- [ ] Request body size limits.
- [ ] Strict CORS for non-local environments.
- [ ] Security headers (HSTS, X-Content-Type-Options, etc.).

### 2. Dependency & Secret Hygiene (1 day)

- [ ] Pin dependencies.
- [ ] Automated vulnerability scanning in CI.
- [ ] Secret scanning (already partially covered in E05 â€” verify).
- [ ] Remove any hardcoded secrets or local-only credentials from committed files.

### 3. Artifact Integrity (1 day)

- [ ] Ensure every stored artifact has a SHA-256.
- [ ] Verification endpoint or offline verification script.
- [ ] Extend existing quality-gate signature concept to release packages.

### 4. AuthZ Review (1 day)

- [ ] Re-audit every mutating endpoint against the role matrix.
- [ ] Ensure organization isolation is enforced at the repository layer, not only in the API.

### 5. Documentation & Process (1 day)

- [ ] Complete `SECURITY.md` with disclosure process.
- [ ] OWASP Top 10 mapping document (see `checklists/security.md`).
- [ ] Threat model sketch for the planning platform (geometry integrity, tenant isolation, job injection).

---

## Non-Goals

- Full formal certification (SOC 2, ISO 27001) â€” only readiness work.
- Hardware security modules.


---


