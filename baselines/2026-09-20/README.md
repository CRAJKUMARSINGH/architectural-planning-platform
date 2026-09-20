# E01 Baseline — 2026-09-20

This directory freezes the platform evidence used to detect regressions during
the Enterprise Enrichment program.

Captured reports:

- `quality-gate-report.json` — overall conservative quality classification.
- `week23-adversarial-expansion-report.json` — known-defect detection evidence.
- `week25-performance-report.json` — performance smoke evidence.

The baseline is evidence, not approval. `REVIEW_REQUIRED` remains the honest
quality-gate state while independent professional architectural review is
pending. Refresh this directory only through an explicit, reviewed baseline
update.