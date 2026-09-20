# Week 16 Supplementary Program — W16-01 to W16-09

**Purpose:** turn the nine tools named in the Week 16 safe visual-tool optimization ideas into a disciplined implementation sequence. Each sprint studies one tool pattern, defines the useful input boundary, implements one reviewable adapter or workflow, and records evidence without treating external output as authoritative geometry.

**Status:** program drafted for execution against the Week 16 intake contract.

## Shared operating rule

Every sprint follows the same path: external tool signal → typed intake → provenance and confidence → candidate or review queue → canonical validation → accepted presentation output. No sprint may silently edit walls, openings, stairs, routes, levels, or code findings. Every accepted edit must retain the model revision, source reference, validation result, and professional-review state.

The implementation surface is the Week 16 contract in scripts/week1516.py, the machine-readable output bar-association-hall/standard/week16-ai-tool-inputs.json, and tests/test_week1516_enrichment.py. Tool-specific API connections are optional future adapters; this program first makes the boundary safe and testable without inventing provider access.

## Delivery sequence

| Sprint | Tool | Primary input | Primary implementation outcome |
|---|---|---|---|
| W16-01 | Maket.ai | text brief and room schedule | typed text-to-plan candidate intake |
| W16-02 | Planner 5D | validated rooms and scaled furniture | furnishing candidate exchange |
| W16-03 | Archistar / Snaptrude | site facts and massing assumptions | site-feasibility evidence package |
| W16-04 | Floorplanner | model revision and object IDs | synchronized 2D/3D view intake |
| W16-05 | Roomstyler / Homestyler | furniture and finish options | clearance-aware presentation options |
| W16-06 | Magicplan | photos, scale, and capture metadata | confidence-based recognition queue |
| W16-07 | ChatGPT / Claude / Grok / Gemini | brief, constraints, and feedback | typed brief/refinement proposals |
| W16-08 | 4Lines.ai | IDs, levels, openings, and dimensions | traceable plan/section exchange |
| W16-09 | Archiagent | dimensioned model and units | live-dimension review evidence |

## W16-01 — Maket.ai: text-to-plan candidate intake

**Potential study:** evaluate how residential text-to-plan and furniture suggestions can accelerate brief exploration while preserving explicit dimensions, room uses, occupancy, adjacency intent, and missing facts.

**Action plan:**
1. Define a normalized input fixture containing a typed brief, room schedule, units, dimensions, furniture intent, and source reference.
2. Compare the tool suggestion against the canonical model for room count, dimensions, adjacency intent, and route assumptions.
3. Record every mismatch as a review finding; never infer missing walls or doors from the visual suggestion.

**Implementation:** add a Maket.ai fixture to ingest_ai_tool_input, expose candidate-only metadata in the Week 16 report, and add passing, missing-units, and conflicting-dimensions tests.

**Evidence and gate:** source brief, units, export/reference ID, extracted facts, and reviewer state. The sprint passes only when a visually attractive suggestion with invalid topology remains review-required.

**Implementation status:** Applied in scripts/week1516.py through validate_maket_input, with fixture tests at tests/fixtures/week16/maket-ai-text-to-plan.json and regression coverage in tests/test_week1516_enrichment.py.

## W16-02 — Planner 5D: furnishing candidate exchange

**Potential study:** assess rapid 2D/3D furnishing and furniture-placement ideas against scaled room geometry, occupancy, route widths, door swings, and clearance envelopes.

**Action plan:**
1. Export or describe a furnishing candidate against a specific canonical model revision.
2. Map each proposed item to a typed asset, dimensions, rotation, service side, occupancy, and clearance envelope.
3. Run the Week 15 placement validator and compare the candidate with the deterministic furnishing baseline.

**Implementation:** add a Planner 5D exchange fixture, asset mapping report, rejected-placement findings, and a deterministic candidate comparison test. Preserve the presentation-only flag on every imported item.

**Evidence and gate:** model revision, asset scale, clearance result, source reference, and rejected conflicts. No candidate may win if the imported furniture blocks a route, stair, service zone, or door swing.

**Implementation status:** Applied in `scripts/week1516.py` through `validate_planner5d_input`, with the exchange fixture at `tests/fixtures/week16/planner5d-furnished-layout.json`, generated evidence at `bar-association-hall/standard/week16-planner5d-exchange-report.json`, and regression coverage in `tests/test_week1516_enrichment.py`.

## W16-03 — Archistar / Snaptrude: site-feasibility evidence

**Potential study:** use site and building-scale modelling patterns for north, frontage, setbacks, levels, public access, staff access, service access, and massing assumptions.

**Action plan:**
1. Define a site evidence package with source, coordinate/unit assumptions, orientation, access points, setbacks, and confidence.
2. Compare imported site facts with the Week 6 recipe and Week 7 rule-pack inputs.
3. Separate measurable findings from assumptions requiring survey or professional confirmation.

**Implementation:** add a site-model adapter fixture that writes explicit assumptions into the review report, links them to rule-pack findings, and tests that a missing frontage or service-access fact remains a warning rather than a hidden pass.

**Evidence and gate:** site source, assumption status, rule-pack version, confidence, and professional-review state. Product output cannot be labeled permit, code, or construction approval.

**Implementation status:** Applied in `scripts/week1516.py` through
`validate_archistar_snaptrude_input`, with fixture tests at
`tests/fixtures/week16/archistar-snaptrude-site-model.json`, generated evidence at
`bar-association-hall/standard/week16-archistar-snaptrude-site-report.json`, and
regression coverage in `tests/test_week1516_enrichment.py`.

## W16-04 — Floorplanner: synchronized 2D/3D view intake

**Potential study:** evaluate fast 2D/3D planning views as a presentation and comparison surface tied to one model revision and one object-ID map.

**Action plan:**
1. Export a view candidate with level, object IDs, room boundaries, openings, and model revision.
2. Check that visible rooms, doors, stairs, and dimensions resolve to canonical objects.
3. Re-run validation after any accepted edit and record stale-view conflicts.

**Implementation:** add a synchronized-view fixture and stale-revision test to the Week 14/16 view contract. A view with unknown IDs or an older revision must be marked stale, not silently accepted.

**Evidence and gate:** object-ID map, view/export reference, level visibility, revision match, and validation signature. The sprint passes only when 2D and 3D views agree with the same validated revision.

**Implementation status:** Applied in `scripts/week1516.py` through
`validate_floorplanner_input`, with fixture tests at
`tests/fixtures/week16/floorplanner-synchronized-view.json`, generated evidence
at `bar-association-hall/standard/week16-floorplanner-synchronized-view-report.json`,
and regression coverage in `tests/test_week1516_enrichment.py`.

## W16-05 — Roomstyler / Homestyler: clearance-aware presentation

**Potential study:** test furniture-heavy visual exploration, materials, finishes, and colour options without allowing styling to hide a technical blocker.

**Action plan:**
1. Convert proposed furniture and finish options into typed non-authoritative presentation objects.
2. Check scale, occupancy, route clearance, door approach, and service-side requirements.
3. Compare the styled candidate beside the technical plan and validation markers.

**Implementation:** add a presentation-option fixture and ensure the render package carries the same model revision, candidate ID, and AI-input provenance as the technical plan.

**Evidence and gate:** asset dimensions, clearance findings, source reference, render traceability, and review state. A polished render cannot suppress a blocker or change authoritative geometry.

**Implementation status:** Applied in `scripts/week1516.py` through
`validate_roomstyler_homestyler_input`, with the presentation-options fixture at
`tests/fixtures/week16/roomstyler-presentation-options.json`, generated evidence
at `bar-association-hall/standard/week16-roomstyler-presentation-report.json`,
and regression coverage in `tests/test_week1516_enrichment.py`.

## W16-06 — Magicplan: photo-assisted recognition queue

**Potential study:** evaluate phone/photo-assisted capture for existing spaces and plans, with explicit scale evidence and human confirmation before promotion.

**Action plan:**
1. Store source images, capture metadata, known dimensions, scale evidence, and recognition confidence.
2. Place uncertain rooms, openings, and walls in a review queue with proposed object links.
3. Promote only manually confirmed objects into an editable model revision, then rerun topology and clearance checks.

**Implementation:** add a recognition-queue fixture covering accepted, uncertain, and rejected objects. Test that an image-only result cannot become issue-ready geometry and that provenance survives export.

**Evidence and gate:** source image, scale evidence, confidence, manual confirmation, object provenance, and validation result. No silent image-to-geometry promotion is allowed.

**Implementation status:** Applied in `scripts/week1516.py` through
`validate_magicplan_input`, with the recognition-queue fixture at
`tests/fixtures/week16/magicplan-recognition-queue.json`, generated evidence at
`bar-association-hall/standard/week16-magicplan-recognition-report.json`, and
regression coverage in `tests/test_week1516_enrichment.py`. Only the manually
confirmed, scale-backed object with a topology/clearance rerun is promoted;
uncertain and rejected recognition remains in the review queue.

## W16-07 — ChatGPT / Claude / Grok / Gemini: typed brief refinement

**Potential study:** compare conversational brief extraction, clarification questions, assumptions, and candidate feedback while keeping every accepted change typed and revisioned.

**Action plan:**
1. Feed a natural-language brief containing units, levels, floor-to-floor heights, room schedule, occupancy, adjacencies, access intent, style, and requested outputs.
2. Extract facts, assumptions, missing topology inputs, and proposed revisions into the Week 12 compiler shape.
3. Require an explicit accept-revision operation before any typed model change and block incomplete upper-floor access.

**Implementation:** add provider-neutral conversation fixtures, ambiguity cases, and typed revision tests. Store provider/model metadata only as provenance; do not treat generated prose as geometry.

**Evidence and gate:** source text, extracted facts, assumptions, clarification state, accepted revision, and validation report. Missing facts must produce a clarification or blocker before rendering.

**Implementation status:** Applied in `scripts/week1516.py` through
`validate_llm_brief_input`, with the provider-neutral fixture at
`tests/fixtures/week16/llm-brief-refinement.json`, generated evidence at
`bar-association-hall/standard/week16-llm-brief-refinement-report.json`, and
regression coverage in `tests/test_week1516_enrichment.py`. Typed revisions
require explicit acceptance and a validation rerun; incomplete upper-floor
access remains blocked.

## W16-08 — 4Lines.ai: traceable plan/section exchange

**Potential study:** assess architectural plan, section, elevation, and model-exchange workflows where semantic IDs and levels must remain synchronized.

**Action plan:**
1. Prepare an exchange package containing object IDs, levels, openings, dimensions, section/elevation references, and validation provenance.
2. Compare returned views against the canonical model for missing, duplicated, or disconnected objects.
3. Reject any view that cannot trace to the validated model revision.

**Implementation:** add a plan-section exchange fixture and cross-view identity test to the synchronized-view contract. Record import/export signatures and invalidation reasons.

**Evidence and gate:** model revision, object-ID map, view type, exchange reference, validation signature, and invalidation state. A disconnected section or elevation remains rejected even if visually complete.

**Implementation status:** Applied in `scripts/week1516.py` through
`validate_4lines_input`, with the exchange fixture at
`tests/fixtures/week16/4lines-plan-section-exchange.json`, generated evidence at
`bar-association-hall/standard/week16-4lines-plan-section-exchange-report.json`,
and cross-view identity regression coverage in
`tests/test_week1516_enrichment.py`.

## W16-09 — Archiagent: live-dimension review

**Potential study:** use scaled floor-plan and live-dimension workflows as an explainable review aid, not as evidence of jurisdictional compliance.

**Action plan:**
1. Normalize dimension values and units against the canonical model and identify the source object for every displayed dimension.
2. Compare changed dimensions against wall spans, openings, room areas, clearances, stairs, and route findings.
3. Rerun topology, clearance, and rule-pack validation after accepted dimension edits.

**Implementation:** add a dimension-review fixture with valid, stale, and conflicting measurements. Preserve the original source reference and record the rerun validation signature.

**Evidence and gate:** units, dimension source, model revision, changed-object list, rerun result, and professional-review state. Millimetre-accuracy claims never replace local-code or professional checks.

## Supplementary program definition of done

- All nine tool IDs map to the Week 16 machine-readable intake manifest.
- Each sprint has a fixture, a failing or review-required case, and a valid case.
- Every accepted signal retains source, revision, confidence or validation status, and review state.
- Presentation and technical outputs remain traceable to the same validated model revision.
- No external tool can override canonical geometry, suppress a blocker, or imply professional approval.
- README and the main Week 01–16 program link to this supplementary sequence.
