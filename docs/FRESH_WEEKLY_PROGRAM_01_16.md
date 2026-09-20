# Fresh Weekly Program 01–16

**Repository:** Advocate-Chambers  
**Purpose:** A clean execution program for the first sixteen enrichment weeks.  
**Status:** Weeks 1–16 are applied through the common drafting kernel and focused weekly validators.
The repository README records the delivery and validation status.

This document is an execution contract, not a replacement for the historical
roadmap. It keeps one common drafting kernel at the root and small,
inspectable project recipes beside it. A recipe configures a building type; it
never invents a wall, door, balcony, stair, route, code value, or approval.

## Root architecture

```text
brief
  -> common drafting kernel
       -> canonical project model
            -> project recipe (residential/commercial/institutional/industrial)
                 -> validate geometry, access, openings, and stairs
                      -> explain findings
                           -> render/export only from the validated revision
```

The canonical model remains the only geometry authority:

- `bar-association-hall/standard/model/project.json`
- `packages/recipes/index.json`
- `packages/recipes/visual-tool-patterns.json`
- `scripts/drafting_kernel.py`
- Week-specific validators under `scripts/`

The kernel coordinates existing validators. It does not create a second
geometry implementation or hide findings produced by a focused week.

## Week 01 — Baseline and honest status

Freeze the current source as a golden fixture. Emit a repeatable JSON report,
record artifact hashes, and keep `PRELIMINARY / NOT FOR CONSTRUCTION` visible.
The inaccessible-room, invalid-opening, overlap, and stair arithmetic fixtures
must fail precisely.

**Gate:** a known impossible route is a `BLOCKER`; a valid fixture remains
deterministic.

## Week 02 — Canonical model and migration

Migrate legacy JSON into a stable model containing projects, sites, levels,
spaces, openings, circulation zones, exterior access zones, stairs, provenance,
and revisions. Validate the schema before any drawing generator receives data.

**Gate:** the legacy source round-trips without losing rooms, openings, stairs,
notes, levels, or revisions.

## Week 03 — Reachability graph

Build per-level and cross-level walkable graphs. Resolve named spaces on both
sides of openings, entry roots, vertical connector edges, connected components,
and the first broken edge.

**Gate:** every occupied room has a proven route or an explainable finding.

## Week 04 — Semantic openings and clearances

Replace decorative opening assumptions with real side A/side B semantics.
Validate width, wall span, swing, approach, landing, furniture conflict,
intentional exterior access, and stable opening schedules.

**Gate:** a door cannot make a room accessible unless both sides are valid and
connected.

## Week 05 — Vertical coordination

Treat stairs and future ramps/lifts as graph connectors with departure and
arrival spaces. Validate floor-to-floor height, riser arithmetic, tread,
landing, width, direction, and route continuity.

**Gate:** every upper-floor route reaches a validated connector arrival, and a
stair edit cannot silently disconnect the plan.

### Week 01–05 delivery contract

Run:

```bash
npm run enrich:fresh-week01-05
npm run validate:fresh-week01-05
npm run test:fresh-week01-05
```

The aggregate report is:
`bar-association-hall/standard/fresh-week01-05-kernel-report.json`.
`PASS` means no known Week 1–5 blocker/error was found; `REVIEW_REQUIRED`
remains the correct state for unresolved assumptions. Neither state is a
construction, permit, accessibility, fire/life-safety, structural, MEP,
survey, or local-code certification.

## Week 06 — Project recipes and orientation

Keep the recipes small and data-driven for residential, commercial,
institutional/civic, and industrial/light-industrial work. Capture north,
frontage, setbacks, public/staff/service access, occupancy, required uses,
area/dimension targets, and required/preferred/forbidden adjacencies.

**Gate:** the system explains why spaces are near or away from one another and
flags missing program facts before rendering.

## Week 07 — Versioned rule packs

Separate universal geometry checks from configurable accessibility, egress,
daylight, ventilation, wet-area, service, and jurisdiction-specific checks.
Expose rule-pack version, assumptions, source, confidence, and professional
review state.

**Gate:** changing a rule pack changes findings predictably without changing
geometry code.

## Week 08 — Technical drawing quality

Standardize wall hierarchy, line weights, hatches, labels, dimensions, legends,
title blocks, north arrows, scales, sheet references, and plan/section/elevation
traceability.

**Gate:** a reviewer can read the sheet without the web UI and trace each
visible object to the model.

## Week 09 — Furniture and presentation

Add scaled furniture/equipment blocks, occupancy-aware layouts, clearance
envelopes, and a separate coloured presentation output. Presentation objects
must never mutate authoritative geometry or conceal a blocker.

**Gate:** useful-looking plans retain routes, technical labels, and validation
status.

## Week 10 — Candidate comparison and release discipline

Generate deterministic alternatives and compare area fit, adjacency, route
quality, daylight/ventilation, vertical coordination, furniture fit, and visual
quality. Add golden fixtures and release manifests.

**Gate:** an attractive candidate cannot win when it contains a blocker.

## Week 11 — Product modes and capability honesty

Expose Brief, Model, Validate, Furnish, Present, and Export modes. Label each
capability as available, provisional, or professional-review dependent.

**Gate:** presentation-only objects cannot be mistaken for building geometry.

## Week 12 — Conversational brief compiler

Extract units, site, north, levels, floor-to-floor heights, room schedule,
occupancy, adjacencies, access intent, style, and requested outputs. Show
assumptions and missing topology facts before generation. Every accepted edit
becomes a typed revision.

**Gate:** missing upper-floor access produces a clarification or blocker before
rendering.

## Week 13 — Import and editable digital twin

Support assisted PDF/image recognition and geometry-preserving DXF import.
Attach confidence and provenance to recognized objects. Keep uncertain objects
in a review queue; do not promote them silently.

**Gate:** scale, levels, openings, and source provenance survive import and
export.

## Week 14 — Synchronized views

Drive 2D, 3D, sections, elevations, dimensions, schedules, route overlays, and
validation markers from the same model revision. Add snapping, level visibility,
section boxes, and isolated-room review.

**Gate:** every accepted edit updates dependent views and reruns validation.

## Week 15 — Parametric assets and clearance-aware furnishing

Use typed assets for furniture, fixtures, appliances, sanitaryware, seating,
dais, library tables, counters, vehicles, and industrial equipment. Store
dimensions, rotation rules, service side, occupancy, and clearance envelopes.

**Gate:** one-click furnishing never blocks a door swing, required route, stair,
service zone, or minimum clear area.

## Week 16 — Candidate studio and render pipeline

Create deterministic candidates, moodboards, materials, finishes, lighting
presets, presentation sheets, panorama/render job manifests, and technical-plan
to-render traceability.

**Gate:** the render is traceable to a valid model revision and cannot hide a
blocker.


### Week 16 AI-tool inputs

Week 16 accepts external tool output only through a typed, review-first intake boundary. The supported inputs are:

- **Maket.ai** — text-to-plan briefs, dimensions, room schedules, and furniture intent.
- **Planner 5D** — validated room geometry, scaled furniture choices, and occupancy intent.
- **Archistar / Snaptrude** — north, frontage, setbacks, access points, levels, and site assumptions.
- **Floorplanner** — canonical revision, object IDs, and validated room boundaries for synchronized views.
- **Roomstyler / Homestyler** — scaled furniture, finish intent, and presentation options.
- **Magicplan** — photos, scale evidence, capture metadata, and manual-confirmation state.
- **ChatGPT / Claude / Grok / Gemini** — natural-language briefs, constraints, missing-fact questions, and candidate feedback.
- **4Lines.ai** — object IDs, levels, openings, dimensions, and validation provenance for plan/section workflows.
- **Archiagent** — dimensioned model, units, levels, and review targets for live-dimension review.

Every accepted signal records its source reference, model revision, validation status, and review state. It remains non-authoritative until canonical geometry and focused validators pass; it cannot silently edit walls, openings, routes, or stairs, and it cannot provide permit or construction approval.

## Safe visual-tool optimization ideas

The named products are visual and workflow references, not compliance
authority. Use their useful interaction patterns only after the kernel has
validated the model.

| Reference | Useful pattern | Safe Advocate-Chambers use |
|---|---|---|
| [Maket.ai](https://www.maket.ai/) | Text-to-plan ideation and furniture options | Use as a brief/presentation benchmark; keep dimensions, routes, and openings in the canonical model. |
| [Planner 5D](https://planner5d.com/) | Furnishing and 2D/3D layout exploration | Borrow the quick furnishing workflow only after room geometry and clearances pass. |
| Archistar / Snaptrude | Site and professional modelling patterns | Turn site assumptions into explicit inputs and rule-pack findings; never convert marketing output into approval. |
| [Floorplanner](https://floorplanner.com/) | Fast 2D/3D planning and clean furnished views | Keep synchronized views tied to one revision and one object-ID system. |
| Roomstyler / Homestyler | Furniture-heavy visual exploration | Treat imported or suggested furniture as non-authoritative until scale and route checks pass. |
| Magicplan | Phone/photo-assisted plan capture | Put recognition confidence and manual confirmation in the import review queue. |
| ChatGPT / Claude / Grok / Gemini | Iterative brief and prompt refinement | Use for typed brief compilation and explanation, never for unvalidated geometry mutation. |
| [4Lines.ai](https://4lines.ai/) | Architectural modelling and plan/section workflow | Preserve semantic IDs and validation provenance across every import/export step. |
| [Archiagent](https://www.archiagent.ai/) | Scaled floor plans and live dimensions | Use live dimensions as a review aid; keep jurisdictional and professional checks separate. |

The safe optimization rule is simple: use external tools to improve ideation,
layout comparison, furnishing, and presentation speed; use the common drafting
kernel to decide whether a plan is topologically coherent and ready for the
next review stage.

The machine-readable catalog at
`packages/recipes/visual-tool-patterns.json` records each pattern's safe action,
forbidden shortcut, and relevant program weeks. The fresh kernel report exposes
that catalog so downstream UI work can show recommendations without embedding
tool-specific logic in validators.

## Definition of done for every week

- The source, schema, validator, API, UI, and renderer agree on IDs and units.
- A new rule has both a failing fixture and a valid passing fixture.
- Findings include the rule, affected geometry, explanation, and suggested fix.
- Technical and presentation outputs share the same validated revision.
- Assumptions remain visible and are never presented as approval.
- The change is deterministic, documented, reversible, and linked from README.