# Week 15–16 enrichment changelog

## Week 15 — Parametric assets and clearance-aware furnishing

- Added a typed catalog covering furniture, fixtures, appliances, sanitaryware,
  seating rows, dais, library tables, counters, vehicles, and industrial
  equipment.
- Added dimensions, rotation rules, wall relationships, service sides,
  occupancy, clearance envelopes, room templates, and typed edit operations.
- One-click placement rejects door swings, routes, stairs, service zones,
  room-boundary violations, and overlapping clearance envelopes.
- Presentation objects remain non-authoritative and retain the canonical model
  revision for audit.

## Week 16 — Candidate studio and presentation pipeline

- Added deterministic candidate seeds and comparison metrics for area,
  adjacency, routes, daylight/ventilation, vertical coordination, furniture
  fit, and visual quality.
- A candidate with a BLOCKER or ERROR cannot win.
- Added moodboards, materials, lighting presets, non-destructive design layers,
  and traceable render, panorama, and presentation-sheet job manifests.
- Technical plan and presentation output carry the same model revision and
  candidate identifier.
- Added explicit review-first intake adapters for Maket.ai, Planner 5D,
  Archistar/Snaptrude, Floorplanner, Roomstyler/Homestyler, Magicplan,
  ChatGPT/Claude/Grok/Gemini, 4Lines.ai, and Archiagent.
- Each accepted tool signal retains its source reference, model revision,
  validation status, and review state; no external tool can silently mutate
  authoritative geometry or bypass a validation rerun.

### W16-01 implementation status — Maket.ai

- Added a text-to-plan fixture with units, room schedule, dimensions,
  furniture intent, and adjacency intent.
- Added dimension, unit, room-match, and input-shape checks through
  `validate_maket_input`.
- Conflicting dimensions become `review-required`; missing units or dimensions
  become blockers; the canonical model is never mutated.

### W16-02 implementation status — Planner 5D

- Added a furnishing exchange fixture with explicit model revision, units,
  source asset mappings, scaled dimensions, occupancy intent, and placements.
- Added canonical asset mapping and clearance validation through
  `validate_planner5d_input`; route, door-swing, room-fit, and overlapping
  clearance conflicts are retained as rejected-placement findings.
- Added a deterministic comparison with the Week 15 furnishing baseline.
  Imported items remain presentation-only and a rejected item cannot make the
  Planner 5D candidate eligible.

### W16-03 implementation status — Archistar / Snaptrude

- Added a site-model evidence fixture with coordinate and unit assumptions,
  orientation, access points, setbacks, levels, massing assumptions, confidence,
  and professional-review state.
- Added `validate_archistar_snaptrude_input`, which compares imported facts with
  the Week 6 orientation/program contract and links the canonical Week 7
  rule-pack findings without mutating geometry.
- Missing frontage or service access remains an explicit warning; imported
  massing remains review evidence and cannot become permit, code, or construction
  approval.

### W16-04 implementation status — Floorplanner

- Added a synchronized 2D/3D view fixture with level visibility, room and
  opening IDs, stair references, export provenance, model revision, and
  validation evidence.
- Added `validate_floorplanner_input`, which reuses the Week 14 canonical view
  contract and rejects unknown IDs, incomplete level coverage, stale revisions,
  and missing validation signatures from silent acceptance.
- Accepted view edits require a post-edit model revision and validation rerun
  signature; view data remains presentation-only and cannot mutate geometry.
