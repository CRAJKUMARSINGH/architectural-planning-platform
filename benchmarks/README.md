# Week 25 performance benchmark

`run_benchmark.py` measures the deterministic planning adapters against the
small, medium, and large workload profiles from the validation program.

```bash
npm run enrich:week25
npm run validate:week25
npm run test:week25
```

The harness records:

- input, model, and validation signatures;
- model generation, validation, site feasibility, furniture clearance,
  technical export, coloured presentation export, DXF export, and API
  validation timings;
- p50 and p95 samples;
- machine, Python, application commit, and rule-pack metadata;
- peak memory, CPU time, failure-recovery time, maximum profile sizes, timeout,
  out-of-memory, data-loss, and nondeterminism counts.

The export adapters deliberately serialize deterministic artifact payloads
instead of pretending to generate a professional PDF or DXF deliverable. The
measurements are an engineering baseline for the adapters and are not a
guarantee of production export performance.

The first generated report is stored at
`bar-association-hall/standard/week25-performance-report.json`. Revised targets
must be recorded in the report and explained rather than silently changed.