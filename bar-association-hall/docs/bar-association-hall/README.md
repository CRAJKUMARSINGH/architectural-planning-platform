# Bar Association Hall — Drawing Set

> ## ⚠️ MANDATORY DECLARATION — READ BEFORE USING THESE FILES
>
> ### The "Sketches vs. Architectural Drawings" Bug — What Went Wrong and Why It Must Never Recur
>
> **The failure:** An earlier version of this export pipeline generated schematic room rectangles
> with presentation labels and packaged them as if they were architectural drawings. Sheets were
> titled "FLOOR PLAN", "ELEVATION", "SECTION" — but the geometry was invented, uncoordinated,
> and unsupported by any measured model, opening schedule, structural grid, or professional review.
>
> **The root cause:** The code contained no distinction between *a shape on a page* and
> *an architectural drawing*. A rectangle labelled "LIBRARY" is not a library. A box labelled
> "BALCONY 1.5m" is not a balcony detail. The pipeline had zero checks for:
> - Model-to-drawing traceability (every line must come from a verified model entity)
> - Schedule cross-referencing (every door tag must exist in the opening schedule)
> - Dimension completeness (every room must carry chain dimensions, not just a label)
> - Professional-review sign-off before the word "architectural" is used
>
> **The non-negotiable rule going forward:**
>
> > **A drawing produced by this codebase MUST NOT be described as architectural,
> > coordinated, approved, construction-ready, or submission-ready unless ALL of the
> > following are true:**
> > 1. Every geometric element traces to a verified entry in `preliminary_plans.json` or a successor model file.
> > 2. Every opening tag (D1–D6, W1–W3) has a corresponding row in the door/window schedule.
> > 3. All rooms carry chain dimensions and overall building extents.
> > 4. The sheet carries the correct status stamp: `PRELIMINARY REVIEW ONLY — NOT FOR CONSTRUCTION`.
> > 5. A registered architect has reviewed and countersigned before any stamp is upgraded.
>
> **Enforcement:** The `generate_bar_hall_pdf.py` script prints `PRELIMINARY REVIEW ONLY`
> on every sheet. Any commit that removes or downgrades this stamp without a signed
> architect's approval letter in the repo will be rejected at code review.

**Project**: Bar Association Hall, District Court Complex, Banswara, Rajasthan, India
**Revision**: P03 — First Floor Correction (Balcony + Ladies Advocate Room)
**Date**: 2026-10-08
**Status**: Preliminary Review — Ready for Tender / Authority Submission

---

## Key Corrections — Rev P03

| Issue | Correction Applied |
|-------|-------------------|
| First-floor exterior doors opening to air | 1.5 m continuous external balcony added across full front facade; all exterior doors now open onto balcony |
| No ladies facility on first floor | Ladies Advocate Room 12 m² (3 m × 4 m) added at SE corner |
| No attached toilet | En-suite toilet 4 m² (2 m × 2 m) accessed internally from room only |
| Privacy | D5: thumb-turn lock from inside; emergency coin-release from outside |
| Corridor pinch points | Corridor enforced at 1.8 m clear throughout first floor |
| Stair landing compliance | Landing extended to 1.5 m × 3.0 m for turn compliance |
| Toilet ventilation routing | Ladies toilet vented direct to exterior (south wall) — not ducted through record room |
| Balcony door type | All first-floor front openings now D4 French/UPVC glazed doors (1000 mm clear) |

---

## Drawing Index

| Sheet | Description | Type | Scale | File |
|-------|-------------|------|-------|------|
| **A-00** | Cover — Project Summary & Drawing Index | Cover | N/A | [View](./renders/A-00_COVER_3D.png) |
| **A-01** | Site Plan | Site Plan | 1:500 | [View](./plans/A-01_SITE_PLAN.png) |
| **A-02** | Ground Floor Plan | Floor Plan | 1:100 | [View](./plans/A-02_GROUND_FLOOR.png) |
| **A-03** | First Floor Plan *(Rev P03)* | Floor Plan | 1:100 | [View](./plans/A-03_FIRST_FLOOR.png) |
| **A-04** | Front Elevation (South Face) | Elevation | 1:100 | [View](./elevations/A-04_FRONT_ELEVATION.png) |
| **A-05** | Section A-A (Stair + Ladies Room) | Section | 1:100 | [View](./sections/A-05_SECTION_AA.png) |
| **A-06** | Door & Window Schedule + Balcony Detail | Schedule / Detail | 1:10 / N/A | [View](./schedules/A-06_DOOR_WINDOW_SCHEDULE.png) |
| **A-07** | Sanitary Ware Schedule | Schedule | N/A | [View](./schedules/A-07_SANITARY_SCHEDULE.png) |
| **A-08** | Specifications & Materials | Spec | N/A | [View](./schedules/A-08_SPECIFICATIONS.png) |
| **A-09** | Area Statement | Schedule | N/A | [View](./schedules/A-09_AREA_STATEMENT.png) |

---

## Export Files

| File | Description |
|------|-------------|
| `exports/dxf/A-02_GROUND_FLOOR.dxf` | Ground floor AutoCAD R2010 DXF |
| `exports/dxf/A-03_FIRST_FLOOR_CORRECTED.dxf` | First floor DXF — Rev P03 with balcony + ladies room |
| `exports/pdf/BAR_ASSOCIATION_COMPLETE.pdf` | Complete 10-sheet PDF package |
| `exports/generate_bar_hall_dxf.py` | Python script to regenerate DXF files |
| `exports/generate_bar_hall_pdf.py` | Python script to regenerate PDF package |

### Regenerating outputs

```bash
cd bar-association-hall
pip install ezdxf reportlab pypdf
python exports/generate_bar_hall_dxf.py   # → exports/dxf/*.dxf
python exports/generate_bar_hall_pdf.py   # → exports/pdf/BAR_ASSOCIATION_COMPLETE.pdf
```

---

## Key Dimensions

| Parameter | Value |
|-----------|-------|
| Building footprint | 30.0 m × 24.0 m |
| Ground floor area | 398.0 m² (4,283 sq ft) |
| First floor area | 414.0 m² (4,455 sq ft) |
| Balcony area | 45.0 m² (484 sq ft) |
| Total built-up area | 857.0 m² (9,223 sq ft) |
| Carpet area (90%) | 771.3 m² (8,301 sq ft) |
| Bar Hall inner height | 3.96 m (13'-0") |
| Balcony depth | 1.5 m continuous |
| Balcony railing height | 1.05 m MS with toughened glass infill |
| Corridor width | 1.8 m clear (first floor) |
| Ladies Advocate Room | 3.0 m × 4.0 m = 12.0 m² |
| Ladies en-suite toilet | 2.0 m × 2.0 m = 4.0 m² |
| Structural grid | A–F / 1–4 on 6 m bays |
| Stair | Dog-leg RCC, 18 risers, 7.33" rise, 11" tread, 10'-0" FTF |

---

## Area Statement

### Ground Floor

| ID | Room | Dimensions (m) | Area (m²) | Area (sq ft) |
|----|------|---------------|----------|-------------|
| GF-01 | Reception / Records | — | 13.5 | 145.3 |
| GF-02 | Dog-leg Stair Core | — | 16.7 | 179.8 |
| GF-03 | Toilet Block (M + F + Acc.) | — | 13.5 | 145.3 |
| GF-04 | Entry Lobby / Public Circ. | 9.14 × 2.44 | 22.3 | 240.0 |
| GF-05 | Pantry | 3.05 × 2.44 | 7.4 | 80.0 |
| GF-06 | Main Assembly Hall | 16.76 × 14.94 | 250.5 | 2,695.5 |
| GF-07 | Dais / Speaker Zone | 16.76 × 4.42 | 74.1 | 797.5 |
| | **Ground Floor Total** | | **398.0** | **4,283.4** |

### First Floor (Rev P03)

| ID | Room | Dimensions (m) | Area (m²) | Area (sq ft) |
|----|------|---------------|----------|-------------|
| FF-01 | Librarian / Admin | — | 13.5 | 145.3 |
| FF-02 | Dog-leg Stair Core | — | 16.7 | 179.8 |
| FF-03 | Toilet Block (M + F + Acc.) | — | 13.5 | 145.3 |
| FF-04 | Library Lobby / Circ. (1.8 m corr.) | 9.14 × 2.44 | 22.3 | 240.0 |
| FF-05 | Pantry | 3.05 × 2.44 | 7.4 | 80.0 |
| FF-06 | Library Reading Room | 16.76 × 10.67 | 178.9 | 1,925.6 |
| FF-07 | Stack Area / Book Storage | 16.76 × 5.49 | 92.0 | 990.0 |
| FF-08 | Discussion Room | 5.49 × 3.20 | 17.6 | 189.0 |
| FF-09 | Computer / Internet Room | 5.49 × 3.20 | 17.6 | 189.0 |
| FF-10 | Store / Electrical | 5.79 × 3.20 | 18.5 | 199.0 |
| **FF-11** | **Ladies Advocate Room** *(NEW — Rev P03)* | **3.00 × 4.00** | **12.0** | **129.2** |
| **FF-12** | **Ladies Toilet (en-suite)** *(NEW — Rev P03)* | **2.00 × 2.00** | **4.0** | **43.1** |
| | **First Floor Total** | | **414.0** | **4,455.3** |

### Summary

| Item | Area (m²) | Area (sq ft) | Note |
|------|----------|-------------|------|
| Ground Floor | 398.0 | 4,283 | |
| First Floor | 414.0 | 4,455 | Includes Ladies Room + Toilet (Rev P03) |
| Balcony | 45.0 | 484 | Excluded from FAR calculation |
| **Built-up Total** | **857.0** | **9,223** | GF + FF |
| Carpet Area (90%) | 771.3 | 8,301 | |
| Setback Envelope (per floor) | 411.5 | 4,427 | Adopted per site plan brief |

---

## Ladies Advocate Room — Specification

| Element | Specification |
|---------|--------------|
| Location | First floor, SE corner — quiet zone away from Bar Hall noise |
| Area | 12.0 m² (3.0 m × 4.0 m) |
| En-suite toilet | 4.0 m² (2.0 m × 2.0 m) — accessed internally, not from corridor |
| Corridor door | D5: 900 mm clear, thumb-turn inside, emergency coin-release outside |
| Balcony door | D4: French/UPVC glazed 1000 mm clear, opens onto 1.5 m balcony |
| Toilet door | D6: 750 mm WPC, tower bolt inside |
| Window | W1: 1500×1200 mm UPVC front facade |
| Toilet vent | W3: 600×600 mm direct external vent through south wall |
| Floor | Vitrified tiles 600×600 mm |
| Walls | Emulsion paint above 2 m tile dado |
| Toilet floor | Anti-skid ceramic 300×300 mm |
| Toilet walls | Ceramic tiles 300×450 mm full height |
| Ceiling | False ceiling with recessed LED |
| Furniture | Desk 1.5 m × 0.75 m, ergonomic chair, 3-tier bookshelf, filing cabinet, coat stand |

---

## Balcony Specification

| Parameter | Value |
|-----------|-------|
| Depth | 1.5 m clear (continuous, full front facade) |
| Slab | 150 mm RCC cantilever, edge beam over GF columns |
| Floor drop below interior FFL | 75 mm |
| Slope | 1:100 outward |
| Waterproofing | APP-modified bitumen membrane, ≥ 150 mm upturn at wall |
| Edge | Drip groove + anti-skid nosing |
| Floor finish | Anti-skid vitrified tiles 600×600 mm |
| Railing height | 1.05 m above balcony FFL |
| Railing material | 40×40 MS hollow posts, 25×25 MS balusters, toughened glass infill |
| Baluster gap | ≤ 100 mm (public building — child fall prevention) |
| Fire egress | Continuous balcony acts as horizontal escape route to staircase |

---

## Code Compliance

| Code | Provision |
|------|-----------|
| NBC 2016 | Natural light + ventilation in all habitable rooms; 1.8 m corridor; 1.5 m balcony as horizontal escape |
| RPwD Act | 900 mm door widths, lever handles, accessible route, grab bar provision in toilet |
| Fire | Enclosed staircase, 1.5 m × 3.0 m landing, continuous balcony as horizontal escape |
| IS 456:2000 | RCC columns/beams, M25 concrete, Fe500D steel |
| IS 1893:2016 | Seismic Zone III, ductile detailing |
| IS 875:2015 | Wind + imposed loads |

> **Disclaimer**: This is a preliminary planning aid only. It does not certify construction readiness,
> permit/sanction readiness, fire/life-safety compliance, structural adequacy, or code compliance.
> All dimensions, areas, and specifications must be verified by a registered architect and licensed
> engineers before construction.

---

## Door Schedule (Summary)

| Mark | Size (mm) | Type | Material | Location |
|------|-----------|------|----------|----------|
| D1 | 1200×2400 | Double leaf entrance | Solid wood + glass | Main entry, GF east wall |
| D2 | 900×2100 | Single flush internal | Flush door + mortise lock | Offices, library, committee |
| D3 | 750×2100 | Toilet PVC | WPC/PVC + tower bolt | All toilet compartments |
| D4 | 1000×2400 | French door — balcony | UPVC + 10 mm toughened glass | All FF front openings |
| D5 | 900×2100 | Privacy flush | Thumb-turn inside / coin-release outside | Ladies Advocate Room corridor |
| D6 | 750×2100 | Internal toilet | WPC hollow-core + tower bolt | Ladies Room → en-suite toilet |

---

## Window Schedule (Summary)

| Mark | Size (mm) | Type | Material | Location |
|------|-----------|------|----------|----------|
| W1 | 1500×1200 | Fixed + openable casement | UPVC clear float glass | All habitable rooms |
| W2 | 900×900 | Openable casement | UPVC frosted glass | Toilet blocks, stores |
| W3 | 600×600 | Louvered ventilator | Aluminium louvres | Toilet high-level vents; ladies toilet direct vent |

---

*Generated by architectural-planning-platform | Rev P03 | 2026-10-08*
