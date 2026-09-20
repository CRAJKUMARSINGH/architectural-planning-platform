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
