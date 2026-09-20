# Baseline Snapshot — 2026-09-20

Frozen before the Enterprise Enrichment programme (E01–E10) begins.

## Contents

| File | Description |
|------|-------------|
| `quality-gate-report.json` | Full quality-gate output — domain enrichment through Week 28 |
| `week22-adversarial-foundation-report.json` | Adversarial fixture foundation — 30 known critical defects |
| `week23-adversarial-expansion-report.json` | Adversarial expansion — 30/30 detected (100% recall) |
| `week25-performance-report.json` | Performance benchmark — latency envelopes |
| `week26-reproducibility-report.json` | Reproducibility package — SHA-256 signed |
| `week27-integrated-release-report.json` | Integrated release v1 report |

## How This Baseline Was Captured

Reports were copied directly from `bar-association-hall/standard/` at commit state
representing the end of domain enrichment Week 28.

## How to Diff Against a New Run

```bash
# Regenerate quality gate
npm run validate:week21

# Compare JSON (PowerShell)
Compare-Object (Get-Content bar-association-hall/standard/quality-gate-report.json) `
              (Get-Content baselines/2026-09-20/quality-gate-report.json)

# Or use jq + diff on Linux/macOS
diff <(jq --sort-keys . baselines/2026-09-20/quality-gate-report.json) \
     <(jq --sort-keys . bar-association-hall/standard/quality-gate-report.json)
```

## Acceptance Threshold

Any PR that makes the quality-gate report **worse** than this baseline
(new `BLOCKED` state, reduction in adversarial detection below 30/30,
or new performance regressions outside established envelopes) must be
fixed before merge. See `CONTRIBUTING.md` for the full PR checklist.
