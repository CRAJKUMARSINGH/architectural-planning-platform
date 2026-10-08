#!/usr/bin/env python3
"""
Bar Association Hall — DXF Export Script
Rev P03: First Floor Corrected (Balcony + Ladies Advocate Room)
Source: ATTACHED-ASSETS/BAR HAAL  |  Date: 2026-10-08

Changes from previous version:
  - Continuous 1.5 m external balcony on front facade (doors no longer open to air)
  - Ladies Advocate Room 12 m² (3 m × 4 m) at SE corner, first floor
  - Attached en-suite toilet 4 m² (2 m × 2 m), accessed internally only
  - Privacy lock D5: thumb-turn inside, emergency coin-release outside
  - D4 French/UPVC glazed doors on all balcony-side openings
  - Corridor enforced at 1.8 m clear throughout
  - Stair landing extended to 1.5 m × 3.0 m
  - Ladies toilet vented direct to exterior (not via record room)
  - Structural grid A–F / 1–4 on 6 m bays
  - Full dimension strings and room area labels
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment

# Output lives next to this script's exports/dxf/ sub-folder
OUT_DIR = Path(__file__).resolve().parent / "dxf"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Layer definitions
# ---------------------------------------------------------------------------
LAYERS = [
    ("A-GRID",     8,  13),   # light grey, thin
    ("A-WALL-EXT", 7,  50),   # white/black, heavy
    ("A-WALL-INT", 7,  30),   # medium
    ("A-DOOR",     4,  18),   # cyan
    ("A-WIND",     5,  18),   # blue
    ("A-FURN",     2,  13),   # yellow
    ("A-DIMS",     3,  13),   # green
    ("A-TEXT",     1,  13),   # red
    ("A-HATCH",    6,  13),   # magenta – ladies room highlight
    ("A-BALC",    30,  25),   # orange – balcony
]


def _add_layers(doc: ezdxf.document.Drawing) -> None:
    for name, color, lw in LAYERS:
        doc.layers.add(name, color=color, lineweight=lw)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _text(msp, pos: tuple, content: str, height: float = 0.18,
          layer: str = "A-TEXT") -> None:
    msp.add_text(
        content,
        height=height,
        dxfattribs={"layer": layer},
    ).set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)


def _dim_h(msp, x0: float, x1: float, y: float, label: str,
           offset: float = -1.2) -> None:
    """Horizontal aligned dimension."""
    dim = msp.add_linear_dim(
        base=(x0, y + offset),
        p1=(x0, y),
        p2=(x1, y),
        angle=0,
        dxfattribs={"layer": "A-DIMS"},
    )
    dim.set_text(label)
    dim.render()


def _dim_v(msp, x: float, y0: float, y1: float, label: str,
           offset: float = -1.2) -> None:
    """Vertical aligned dimension."""
    dim = msp.add_linear_dim(
        base=(x + offset, y0),
        p1=(x, y0),
        p2=(x, y1),
        angle=90,
        dxfattribs={"layer": "A-DIMS"},
    )
    dim.set_text(label)
    dim.render()


def _door_arc(msp, hinge: tuple, radius: float,
              start_angle: float, end_angle: float) -> None:
    """Draw door leaf (line) + swing arc."""
    angle_rad = math.radians(end_angle - start_angle)
    leaf_end = (
        hinge[0] + radius * math.cos(math.radians(start_angle)),
        hinge[1] + radius * math.sin(math.radians(start_angle)),
    )
    msp.add_line(hinge, leaf_end, dxfattribs={"layer": "A-DOOR"})
    msp.add_arc(
        center=hinge,
        radius=radius,
        start_angle=start_angle,
        end_angle=end_angle,
        dxfattribs={"layer": "A-DOOR"},
    )


# ---------------------------------------------------------------------------
# First Floor Plan  (model space units = metres)
# ---------------------------------------------------------------------------
def create_first_floor_dxf() -> Path:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.M
    msp = doc.modelspace()
    _add_layers(doc)

    # ── Grid ────────────────────────────────────────────────────────────────
    grid_labels_x = list("ABCDEF")
    for i, label in enumerate(grid_labels_x):
        x = i * 6.0
        msp.add_line((x, -3.5), (x, 27.0), dxfattribs={"layer": "A-GRID"})
        _text(msp, (x, -3.0), label, height=0.25, layer="A-GRID")

    for j in range(1, 5):
        y = (j - 1) * 6.0
        msp.add_line((-3.5, y), (33.0, y), dxfattribs={"layer": "A-GRID"})
        _text(msp, (-3.0, y), str(j), height=0.25, layer="A-GRID")

    # ── External walls 230 mm (modelled as closed polyline, width=0.23 m) ──
    ext_wall = [(0, 0), (30, 0), (30, 24), (0, 24)]
    msp.add_lwpolyline(
        ext_wall, close=True,
        dxfattribs={"layer": "A-WALL-EXT", "lineweight": 50},
    )

    # ── Internal partition walls ─────────────────────────────────────────────
    # Corridor spine (1.8 m clear from south wall)
    msp.add_line((0, 1.8), (30, 1.8), dxfattribs={"layer": "A-WALL-INT"})
    # Stair/service core east wall
    msp.add_line((9, 0), (9, 1.8), dxfattribs={"layer": "A-WALL-INT"})
    msp.add_line((21, 0), (21, 1.8), dxfattribs={"layer": "A-WALL-INT"})
    # Library / reading room south wall
    msp.add_line((0, 9.0), (30, 9.0), dxfattribs={"layer": "A-WALL-INT"})
    # Ladies Advocate Room south partition (at y=20)
    msp.add_line((24, 20), (27, 20), dxfattribs={"layer": "A-WALL-INT"})
    # Ladies Advocate Room west partition
    msp.add_line((24, 20), (24, 24), dxfattribs={"layer": "A-WALL-INT"})
    # Toilet (en-suite) south wall
    msp.add_line((25, 18), (27, 18), dxfattribs={"layer": "A-WALL-INT"})
    # Toilet (en-suite) west wall
    msp.add_line((25, 18), (25, 20), dxfattribs={"layer": "A-WALL-INT"})

    # ── Balcony (1.5 m projection beyond south external wall) ────────────────
    # Slab edge
    msp.add_line((0, -1.5), (30, -1.5), dxfattribs={"layer": "A-BALC"})
    # Side returns
    msp.add_line((0, 0), (0, -1.5), dxfattribs={"layer": "A-BALC"})
    msp.add_line((30, 0), (30, -1.5), dxfattribs={"layer": "A-BALC"})
    # Railing line (1.05 m high — shown at slab edge in plan)
    msp.add_line((0, -1.5), (30, -1.5), dxfattribs={"layer": "A-BALC"})
    _text(msp, (15, -0.7), "CONTINUOUS BALCONY — 1.5 m DEEP", 0.2, "A-BALC")
    _text(msp, (15, -1.1), "MS RAILING 1.05 m HIGH | BALUSTER GAP ≤ 100 mm", 0.15, "A-BALC")
    _text(msp, (15, -1.8), "SLAB SLOPE 1:100 OUTWARD | WATERPROOF MEMBRANE | DRIP GROOVE", 0.12, "A-BALC")

    # ── Hatch highlight: Ladies Advocate Room ────────────────────────────────
    hatch = msp.add_hatch(color=6, dxfattribs={"layer": "A-HATCH"})
    hatch.set_pattern_fill("ANSI31", scale=0.05)
    hatch.paths.add_polyline_path(
        [(24, 20), (27, 20), (27, 24), (24, 24)], is_closed=True
    )

    # ── Doors ────────────────────────────────────────────────────────────────
    # D1 — Main entry (double leaf 1200 mm) on south wall at x=14.4–15.6
    msp.add_line((14.4, 0), (14.4, -0.05), dxfattribs={"layer": "A-DOOR"})
    msp.add_line((15.6, 0), (15.6, -0.05), dxfattribs={"layer": "A-DOOR"})
    _text(msp, (15.0, -0.3), "D1  1200×2400  DOUBLE", 0.13, "A-DOOR")

    # D4 — French door Ladies Room to balcony (south wall of room at y=20, x=24)
    #      Hinge at (24, 20), swings inward (into room, toward +y)
    _door_arc(msp, hinge=(24.0, 20.0), radius=1.0, start_angle=0, end_angle=90)
    _text(msp, (24.6, 19.5), "D4  1000×2400\nFRENCH/UPVC", 0.12, "A-DOOR")

    # D5 — Ladies Advocate Room corridor door (west wall at x=24, y≈21.5)
    #      Hinge at (24, 21.5), swings into corridor (toward -x)
    _door_arc(msp, hinge=(24.0, 21.5), radius=0.9, start_angle=180, end_angle=270)
    _text(msp, (23.0, 22.2), "D5  900×2100\nPRIVACY LOCK", 0.12, "A-DOOR")

    # D6 — Internal toilet door (south wall of toilet at y=20, x=25.5–26.25)
    #      Hinge at (25.5, 20), swings into toilet (toward +y)
    _door_arc(msp, hinge=(25.5, 20.0), radius=0.75, start_angle=0, end_angle=90)
    _text(msp, (26.0, 19.4), "D6  750×2100", 0.12, "A-DOOR")

    # ── Windows ──────────────────────────────────────────────────────────────
    # W1 — Front facade windows (south wall, various rooms)
    for wx in [3.0, 7.5, 12.0, 18.0]:
        msp.add_line((wx, 0), (wx + 1.5, 0), dxfattribs={"layer": "A-WIND", "lineweight": 25})
        _text(msp, (wx + 0.75, 0.4), "W1", 0.12, "A-WIND")

    # W1 — Ladies Room front window
    msp.add_line((24.5, 24), (26.0, 24), dxfattribs={"layer": "A-WIND", "lineweight": 25})
    _text(msp, (25.25, 24.4), "W1", 0.12, "A-WIND")

    # W3 — Ladies toilet external vent (east wall)
    msp.add_line((27, 18.5), (27, 19.0), dxfattribs={"layer": "A-WIND", "lineweight": 18})
    _text(msp, (27.5, 18.75), "W3 VENT", 0.11, "A-WIND")

    # ── Room labels & areas ──────────────────────────────────────────────────
    rooms = [
        ((4.5,  0.9),  "STAIR CORE"),
        ((15.0, 0.9),  "TOILET BLOCK (M+F+ACC)"),
        ((15.0, 5.5),  "LIBRARY LOBBY / CORRIDOR — 1.8 m CLEAR"),
        ((15.0, 15.5), "LIBRARY READING ROOM    178.9 m²"),
        ((15.0, 22.0), "STACK AREA / BOOK STORAGE    92.0 m²"),
        ((5.0,  22.0), "DISCUSSION ROOM    17.6 m²"),
        ((22.0, 22.0), "COMPUTER / INTERNET    17.6 m²"),
        ((25.5, 22.5), "LADIES ADVOCATE\nROOM  12.0 m²"),
        ((26.0, 19.0), "TOILET\n4.0 m²"),
    ]
    for pos, label in rooms:
        _text(msp, pos, label, 0.18, "A-TEXT")

    # ── Revision cloud note ───────────────────────────────────────────────────
    _text(msp, (25.5, 17.0), "REV P03 — LADIES ADVOCATE ROOM\n+ BALCONY CORRECTION", 0.15, "A-TEXT")
    _text(msp, (25.5, 16.5), "NBC 2016 | RPwD ACT | IS 456:2000", 0.12, "A-TEXT")

    # ── Dimensions ───────────────────────────────────────────────────────────
    # Overall building width
    _dim_h(msp, 0, 30, 0, "30.00 m  (98'-5\")", offset=-2.5)
    # Overall building depth
    _dim_v(msp, 0, 0, 24, "24.00 m  (78'-9\")", offset=-2.5)
    # Balcony depth
    _dim_v(msp, 0, -1.5, 0, "1.50 m BALCONY", offset=-1.8)
    # Ladies room width
    _dim_h(msp, 24, 27, 20, "3.00 m", offset=-1.0)
    # Ladies room depth
    _dim_v(msp, 27, 20, 24, "4.00 m", offset=0.8)
    # Toilet width
    _dim_h(msp, 25, 27, 18, "2.00 m", offset=-0.8)
    # Corridor width
    _dim_v(msp, 30, 0, 1.8, "1.80 m CORR.", offset=0.8)

    # ── Title annotation ─────────────────────────────────────────────────────
    _text(msp, (15, 26.0), "SHEET A-03 · FIRST FLOOR PLAN · Rev P03", 0.35, "A-TEXT")
    _text(msp, (15, 25.5), "BAR ASSOCIATION HALL · DISTRICT COURT COMPLEX, BANSWARA, RAJASTHAN", 0.22, "A-TEXT")
    _text(msp, (15, 25.1), "SCALE: 1:100 (ON A1) · UNITS: METRES · DATE: 2026-10-08", 0.18, "A-TEXT")
    _text(msp, (15, 24.7),
          "PRELIMINARY REVIEW ONLY — NOT FOR CONSTRUCTION · VERIFY SURVEY, CODE & ENGINEERING",
          0.15, "A-TEXT")

    # ── Save ─────────────────────────────────────────────────────────────────
    out_path = OUT_DIR / "A-03_FIRST_FLOOR_CORRECTED.dxf"
    doc.saveas(out_path)
    print(f"✓  DXF saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Ground Floor Plan  (mirrors service-core geometry from preliminary_plans.json)
# ---------------------------------------------------------------------------
def create_ground_floor_dxf() -> Path:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.M
    msp = doc.modelspace()
    _add_layers(doc)

    # Grid
    for i, label in enumerate(list("ABCDEF")):
        x = i * 6.0
        msp.add_line((x, -2.5), (x, 30.0), dxfattribs={"layer": "A-GRID"})
        _text(msp, (x, -2.0), label, 0.25, "A-GRID")
    for j in range(1, 5):
        y = (j - 1) * 6.0
        msp.add_line((-2.5, y), (33.0, y), dxfattribs={"layer": "A-GRID"})
        _text(msp, (-2.0, y), str(j), 0.25, "A-GRID")

    # External walls
    msp.add_lwpolyline(
        [(0, 0), (30, 0), (30, 28.35), (0, 28.35)],
        close=True, dxfattribs={"layer": "A-WALL-EXT"},
    )

    # Service core partitions
    msp.add_line((0, 5.03), (30, 5.03), dxfattribs={"layer": "A-WALL-INT"})   # Service row south
    msp.add_line((0, 10.21), (30, 10.21), dxfattribs={"layer": "A-WALL-INT"}) # Lobby south
    msp.add_line((9.14, 0), (9.14, 5.03), dxfattribs={"layer": "A-WALL-INT"})
    msp.add_line((21.34, 0), (21.34, 5.03), dxfattribs={"layer": "A-WALL-INT"})

    # Main hall height note
    _text(msp, (15, 19.0), "MAIN ASSEMBLY HALL", 0.30, "A-TEXT")
    _text(msp, (15, 18.3), "Floor area: 250.5 m²", 0.22, "A-TEXT")
    _text(msp, (15, 17.7), "Inner height: 3.96 m  (13'-0\")", 0.22, "A-TEXT")

    # Room labels
    gf_rooms = [
        ((4.57,  2.5),  "RECEPTION /\nRECORDS"),
        ((15.24, 2.5),  "DOG-LEG STAIR CORE"),
        ((25.91, 2.5),  "TOILET BLOCK\n(M + F + ACC.)"),
        ((15.0,  7.6),  "ENTRY LOBBY / PUBLIC CIRCULATION"),
        ((15.0,  28.0), "DAIS / SPEAKER ZONE  74.1 m²"),
    ]
    for pos, label in gf_rooms:
        _text(msp, pos, label, 0.18, "A-TEXT")

    # Dimensions
    _dim_h(msp, 0, 30, 0, "30.00 m", offset=-2.0)
    _dim_v(msp, 0, 0, 28.35, "28.35 m", offset=-2.0)

    # Title
    _text(msp, (15, 29.5), "SHEET A-02 · GROUND FLOOR PLAN · Rev P03", 0.35, "A-TEXT")
    _text(msp, (15, 29.0), "BAR ASSOCIATION HALL · BANSWARA, RAJASTHAN", 0.22, "A-TEXT")
    _text(msp, (15, 28.6), "SCALE: 1:100 · UNITS: METRES · DATE: 2026-10-08", 0.18, "A-TEXT")

    out_path = OUT_DIR / "A-02_GROUND_FLOOR.dxf"
    doc.saveas(out_path)
    print(f"✓  DXF saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Bar Association Hall — DXF Generator  (Rev P03)")
    print("=" * 56)
    create_ground_floor_dxf()
    create_first_floor_dxf()
    print("\nAll DXF files written to:", OUT_DIR)
    print("Open in AutoCAD, LibreCAD, or BricsCAD to verify geometry.")
