# Release Checklist

## Pre-Release
- [ ] All CI status checks green on the release commit
- [ ] Full adversarial suite passed (30/30 known critical defects detected)
- [ ] Performance suite within agreed envelopes (or deviations documented)
- [ ] Quality-gate report generated and reviewed
- [ ] No software `BLOCKED` states
- [ ] Remaining `REVIEW_REQUIRED` items are only legitimate professional-review items
- [ ] CHANGELOG updated
- [ ] Version number decided (semver)

## Release Artifacts
- [ ] Application version / git SHA
- [ ] Quality-gate report (JSON + short human summary)
- [ ] SBOM
- [ ] Adversarial summary
- [ ] Performance summary
- [ ] Known-limitations register
- [ ] Docker image digests (if applicable)

## Post-Release
- [ ] Staging smoke test completed
- [ ] Monitoring dashboards show healthy baseline
- [ ] Announcement / internal note includes the professional-review disclaimer
- [ ] **Never** mark outputs as automatically issuable — professional review is always required
- [ ] Tag pushed and GitHub Release created with assets attached
