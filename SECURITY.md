# Security Policy

## Supported baseline

Security fixes are addressed on the `main` branch and the latest tagged
release. Do not include secrets, credentials, private project data, or
production artifacts in an issue or pull request.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the repository owner
through GitHub's private vulnerability reporting flow. Include:

- affected commit, route, script, or package;
- reproducible steps or a minimal fixture;
- security impact and any suggested mitigation.

Do not publicly disclose an exploitable issue until a fix or mitigation is
available.

## Security expectations

- Never commit API keys, tokens, passwords, or connection strings.
- Treat uploaded drawings and imported model data as untrusted input.
- Keep generated artifacts content-addressed and verify hashes before use.
- Do not weaken tenant, audit, or quality-gate boundaries to make a local
  workflow appear successful.