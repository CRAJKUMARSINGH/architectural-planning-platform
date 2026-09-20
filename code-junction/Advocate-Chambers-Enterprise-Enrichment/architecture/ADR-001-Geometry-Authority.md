# ADR-001 — Geometry Authority Remains in Python

**Status:** Accepted  
**Date:** 2026-09-20  
**Deciders:** Platform + Domain leads

## Context

Advocate-Chambers combines a rich React editor with a sophisticated Python parametric engine and NBC/RPwD rule evaluation. There is a natural temptation to move more logic into the frontend or into a generic “BIM” layer for perceived interactivity gains.

## Decision

**Python remains the sole authority for:**

- Walls, openings, stairs, routes, levels, and site geometry
- Rule-pack evaluation and quality-gate findings
- Deterministic report generation and export (DXF/PDF/SVG)

The React application and FastAPI service are **clients and coordinators**. They may:

- Compile briefs into structured commands
- Preview and display
- Enqueue jobs
- Attach presentation/furniture layers that are explicitly non-authoritative

They may **never**:

- Become the source of truth for constructive geometry
- Silently override rule-pack findings
- Allow imported visual tools (Planner 5D, etc.) to mutate the canonical model without going through the Python validation path

## Consequences

**Positive**
- Determinism and auditability stay high
- Existing weekly enrichment and adversarial suite remain valid
- Professional review boundary stays clear

**Negative**
- Some interactive edits require a round-trip
- Workers must be scaled for heavy generation

**Mitigations**
- Optimistic UI with explicit “pending validation” states
- Fast validation paths for common commands
- Clear capability matrix so the UI never pretends provisional features are authoritative

## Compliance

Any PR that moves authoritative geometry calculation into TypeScript or into an external SaaS without a Python validation step is a violation of this ADR and must be rejected.
