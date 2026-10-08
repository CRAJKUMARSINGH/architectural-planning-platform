#!/usr/bin/env python3
"""
Bar Association Hall — Complete 10-Sheet PDF Package
Rev P03: First Floor Corrected (Balcony + Ladies Advocate Room)
Source: ATTACHED-ASSETS/BAR HAAL  |  Date: 2026-10-08

Sheets produced:
  A-00  Cover / Title Sheet with Project Summary
  A-01  Site Plan
  A-02  Ground Floor Plan
  A-03  First Floor Plan (Rev P03 — Balcony + Ladies Room)
  A-04  Front Elevation
  A-05  Section A-A (through stair and Ladies Room)
  A-06  Door & Window Schedule + Balcony Detail
  A-07  Sanitary Ware Schedule
  A-08  Specifications & Materials
  A-09  Area Statement

Output: exports/pdf/BAR_ASSOCIATION_COMPLETE.pdf
"""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A1, A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

# ── Mixed paper sizes by sheet type ──────────────────────────────────────────
# Drawing sheets (A-00 to A-05) use A1 landscape — full-size plotter output.
# Schedule / spec sheets (A-06 to A-09) use A3/A4 — desk-printer friendly.
SHEET_CONFIG = {
    'A-00': ('cover',     A1),   # Cover / project summary
    'A-01': ('site',      A1),   # Site plan
    'A-02': ('plan',      A1),   # Ground floor plan
    'A-03': ('plan',      A1),   # First floor plan (Rev P03)
    'A-04': ('elevation', A1),   # Front elevation
    'A-05': ('section',   A1),   # Section A-A
    'A-06': ('schedule',  A3),   # Door & window schedule + balcony detail
    'A-07': ('schedule',  A3),   # Sanitary ware schedule
    'A-08': ('specs',     A4),   # Specifications & materials
    'A-09': ('schedule',  A3),   # Area statement
}

# ── Output path ──────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).resolve().parent / "pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PDF = OUT_DIR / "BAR_ASSOCIATION_COMPLETE.pdf"

# ── Page geometry helpers (recalculated per sheet) ────────────────────────────
MARGIN  = 18 * mm
TITLE_H = 70 * mm   # bottom title block height

def _page_geom(pagesize: tuple) -> dict:
    """Return draw-zone metrics for a given landscape pagesize."""
    pw, ph = landscape(pagesize)
    return {
        "PW": pw, "PH": ph,
        "DRAW_X": MARGIN,
        "DRAW_Y": MARGIN + TITLE_H,
        "DRAW_W": pw - 2 * MARGIN,
        "DRAW_H": ph - 2 * MARGIN - TITLE_H,
    }

# Default geometry (A1 landscape) — used by drawing sheets
_A1 = _page_geom(A1)
PW     = _A1["PW"]
PH     = _A1["PH"]
DRAW_X = _A1["DRAW_X"]
DRAW_Y = _A1["DRAW_Y"]
DRAW_W = _A1["DRAW_W"]
DRAW_H = _A1["DRAW_H"]

# ── Colour palette ────────────────────────────────────────────────────────────
C_BLACK   = colors.HexColor("#0f172a")
C_DARK    = colors.HexColor("#334155")
C_GRAY    = colors.HexColor("#64748b")
C_LGRAY   = colors.HexColor("#cbd5e1")
C_PALE    = colors.HexColor("#f1f5f9")
C_ACCENT  = colors.HexColor("#0284c7")
C_RED     = colors.HexColor("#b91c1c")
C_AMBER   = colors.HexColor("#d97706")
C_GREEN   = colors.HexColor("#047857")
C_LADIES  = colors.HexColor("#e879f9")   # magenta highlight for ladies room
C_BALCONY = colors.HexColor("#f97316")   # orange for balcony

PROJECT_NAME  = "BAR ASSOCIATION HALL"
PROJECT_SUB   = "District Court Complex, Banswara, Rajasthan, India"
REV           = "Rev P03"
DOC_DATE      = "2026-10-08"
SCALE_NOTE    = "Scale: As noted (A1 sheet)"
STATUS        = "PRELIMINARY REVIEW ONLY — NOT FOR CONSTRUCTION"


# ── Shared drawing primitives ─────────────────────────────────────────────────

def _border(c: canvas.Canvas, pw: float = None, ph: float = None) -> None:
    """Outer and inner ISO border lines."""
    pw = pw or PW
    ph = ph or PH
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(2.5)
    c.rect(MARGIN, MARGIN, pw - 2 * MARGIN, ph - 2 * MARGIN)
    c.setLineWidth(0.5)
    c.rect(MARGIN + 3, MARGIN + 3, pw - 2 * MARGIN - 6, ph - 2 * MARGIN - 6)


def _title_block(c: canvas.Canvas, sheet_no: str, sheet_title: str,
                 sheet_type: str, scale: str = "1:100",
                 pw: float = None, ph: float = None) -> None:
    """ISO 7200-style title block at page bottom."""
    pw = pw or PW
    ph = ph or PH
    bx = MARGIN
    by = MARGIN
    bw = pw - 2 * MARGIN
    bh = TITLE_H

    # Background
    c.setFillColor(C_PALE)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(1)
    c.rect(bx, by, bw, bh, fill=1, stroke=1)

    # Vertical dividers
    div1 = bx + 230 * mm
    div2 = pw - MARGIN - 70 * mm
    c.line(div1, by, div1, by + bh)
    c.line(div2, by, div2, by + bh)

    # --- Project block ---
    c.setFillColor(C_BLACK)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(bx + 8 * mm, by + bh - 18 * mm, PROJECT_NAME)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_ACCENT)
    c.drawString(bx + 8 * mm, by + bh - 27 * mm, PROJECT_SUB)
    c.setFont("Helvetica", 8)
    c.setFillColor(C_DARK)
    c.drawString(bx + 8 * mm, by + bh - 36 * mm, f"Revision: {REV}   |   Date: {DOC_DATE}")
    c.drawString(bx + 8 * mm, by + bh - 45 * mm, "Structural Grid: A–F / 1–4  |  6 m bays")
    c.drawString(bx + 8 * mm, by + bh - 54 * mm, "Stair: Dog-leg RCC  |  18 risers  |  10'-0\" FTF")
    c.setFillColor(C_RED)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(bx + 8 * mm, by + 5 * mm, STATUS)

    # --- Drawing title block ---
    c.setFillColor(C_BLACK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(div1 + 8 * mm, by + bh - 18 * mm, sheet_title.upper())
    c.setFont("Helvetica-Bold", 9)
    if sheet_type in ("FLOOR PLAN", "SITE PLAN"):
        c.setFillColor(C_GREEN)
    elif sheet_type == "SCHEDULE":
        c.setFillColor(C_DARK)
    else:
        c.setFillColor(C_ACCENT)
    c.drawString(div1 + 8 * mm, by + bh - 30 * mm, sheet_type.upper())
    c.setFillColor(C_DARK)
    c.setFont("Helvetica", 8)
    c.drawString(div1 + 8 * mm, by + bh - 40 * mm, f"Scale: {scale}   |   Format: A1 ISO 5457")
    c.drawString(div1 + 8 * mm, by + bh - 50 * mm, "Main Entry: East Long Wall | 4-Sided Fenestration")
    c.setFillColor(C_RED)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(div1 + 8 * mm, by + 5 * mm, "VERIFY SURVEY, CODE & ENGINEERING BEFORE CONSTRUCTION")

    # --- Sheet number block ---
    c.setFillColor(C_BLACK)
    c.rect(div2, by, bw - (div2 - bx), bh, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString((div2 + pw - MARGIN) / 2, by + bh - 24 * mm, sheet_no)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString((div2 + pw - MARGIN) / 2, by + bh - 32 * mm, "SHEET NO.")
    c.setFont("Helvetica", 8)
    c.setFillColor(C_DARK)
    c.drawCentredString((div2 + pw - MARGIN) / 2, by + 12 * mm, f"{REV}  (APPROVED)")
    c.drawCentredString((div2 + pw - MARGIN) / 2, by + 6 * mm, DOC_DATE)


def _section_heading(c: canvas.Canvas, x: float, y: float,
                     text: str, width: float = 120 * mm) -> None:
    c.setFillColor(C_BLACK)
    c.rect(x, y, width, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 3 * mm, y + 2 * mm, text)
    c.setFillColor(C_BLACK)


def _table(c: canvas.Canvas, x: float, y: float,
           headers: list[str], rows: list[list[str]],
           col_widths: list[float]) -> float:
    """Draw a simple table, returns the bottom Y of the table."""
    row_h = 6.5 * mm
    total_w = sum(col_widths)
    total_h = row_h * (len(rows) + 1)

    # Header row
    c.setFillColor(C_BLACK)
    c.rect(x, y - row_h, total_w, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.5)
    cx = x
    for header, cw in zip(headers, col_widths):
        c.drawString(cx + 2 * mm, y - row_h + 2 * mm, header)
        cx += cw

    # Data rows
    for ri, row in enumerate(rows):
        ry = y - row_h * (ri + 2)
        c.setFillColor(C_PALE if ri % 2 == 0 else colors.white)
        c.setStrokeColor(C_LGRAY)
        c.rect(x, ry, total_w, row_h, fill=1, stroke=1)
        c.setFillColor(C_BLACK)
        c.setFont("Helvetica", 7)
        cx = x
        for cell, cw in zip(row, col_widths):
            c.drawString(cx + 2 * mm, ry + 2 * mm, str(cell))
            cx += cw

    return y - total_h


# ── Sheet generators ─────────────────────────────────────────────────────────

def _sheet_a00_cover(c: canvas.Canvas) -> None:
    """A-00: Cover sheet with project summary."""
    _border(c)
    _title_block(c, "A-00", "Cover — Project Summary", "COVER SHEET", scale="N/A")

    cy = DRAW_Y + DRAW_H - 10 * mm
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(C_BLACK)
    c.drawCentredString(PW / 2, cy, PROJECT_NAME)

    cy -= 14 * mm
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(C_ACCENT)
    c.drawCentredString(PW / 2, cy, PROJECT_SUB)

    cy -= 10 * mm
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(C_RED)
    c.drawCentredString(PW / 2, cy, f"Revision {REV} — Balcony Correction + Ladies Advocate Room")

    # Horizontal rule
    cy -= 8 * mm
    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(2)
    c.line(DRAW_X + 20 * mm, cy, DRAW_X + DRAW_W - 20 * mm, cy)
    cy -= 12 * mm

    # Two-column summary
    col1_x = DRAW_X + 20 * mm
    col2_x = DRAW_X + DRAW_W / 2 + 10 * mm
    col_w  = DRAW_W / 2 - 30 * mm

    _section_heading(c, col1_x, cy, "KEY CORRECTIONS — Rev P03", col_w)
    cy -= 8 * mm
    corrections = [
        "1. BALCONY ADDED — 1.5 m continuous external balcony on first-floor",
        "   front facade; all exterior doors now open onto balcony (not air).",
        "2. LADIES ADVOCATE ROOM — 12 m² (3.0 m × 4.0 m) added at SE corner,",
        "   first floor. Quiet zone, natural light, balcony access via D4.",
        "3. EN-SUITE TOILET — 4 m² (2.0 m × 2.0 m) accessed internally only.",
        "   Direct external vent W3; WC1 wall-hung, WB1 wall-hung basin.",
        "4. PRIVACY LOCK — D5: thumb-turn from inside,",
        "   emergency coin-release from outside. Corridor access only.",
        "5. CORRIDOR — enforced 1.8 m clear throughout first floor.",
        "6. STAIR LANDING — extended to 1.5 m × 3.0 m (turn compliance).",
        "7. TOILET VENT — ladies toilet vented direct to exterior.",
        "8. FRENCH DOORS — D4 UPVC glazed, 1000 mm clear, on all",
        "   first-floor front openings to balcony.",
    ]
    c.setFont("Helvetica", 8.5)
    c.setFillColor(C_DARK)
    for line in corrections:
        c.drawString(col1_x, cy, line)
        cy -= 5.5 * mm

    # Reset cy for column 2
    cy2 = DRAW_Y + DRAW_H - 10 * mm - 14 * mm - 10 * mm - 8 * mm - 12 * mm - 8 * mm

    _section_heading(c, col2_x, cy2, "BUILDING STATISTICS", col_w)
    cy2 -= 8 * mm
    stats = [
        ("Building Footprint",    "30.0 m × 24.0 m"),
        ("Ground Floor Area",     "398.0 m²  (4,283 sq ft)"),
        ("First Floor Area",      "414.0 m²  (4,455 sq ft)"),
        ("Balcony Area",          "45.0 m²   (484 sq ft)"),
        ("Total Built-up Area",   "857.0 m²  (9,223 sq ft)"),
        ("Carpet Area (90%)",     "771.3 m²  (8,301 sq ft)"),
        ("Bar Hall Inner Height", "3.96 m  (13'-0\")"),
        ("Balcony Depth",         "1.50 m continuous"),
        ("Corridor Width",        "1.80 m clear"),
        ("Ladies Room",           "12.0 m²  (3.0 × 4.0 m)"),
        ("Ladies Toilet",         "4.0 m²   (2.0 × 2.0 m)"),
        ("Stair",                 "Dog-leg RCC, 18 risers, 10'-0\" FTF"),
    ]
    c.setFont("Helvetica", 8.5)
    for label, value in stats:
        c.setFillColor(C_DARK)
        c.drawString(col2_x, cy2, f"  {label}:")
        c.setFillColor(C_BLACK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(col2_x + 55 * mm, cy2, value)
        c.setFont("Helvetica", 8.5)
        cy2 -= 5.5 * mm

    cy2 -= 8 * mm
    _section_heading(c, col2_x, cy2, "CODE COMPLIANCE", col_w)
    cy2 -= 8 * mm
    codes = [
        "NBC 2016 — natural light, ventilation, 1.8 m corridor",
        "RPwD Act — 900 mm doors, lever handles, accessible route",
        "Fire — enclosed stair, balcony = horizontal escape route",
        "IS 456:2000 — RCC columns / beams, M25 concrete",
        "IS 1893:2016 — seismic zone III provisions",
        "IS 875:2015 — wind and imposed loads",
    ]
    c.setFont("Helvetica", 8.5)
    c.setFillColor(C_DARK)
    for line in codes:
        c.drawString(col2_x + 3 * mm, cy2, f"✓  {line}")
        cy2 -= 5.5 * mm

    # Drawing index table at bottom
    idx_y = DRAW_Y + 50 * mm
    _section_heading(c, DRAW_X + 20 * mm, idx_y, "DRAWING INDEX", DRAW_W - 40 * mm)
    idx_y -= 2 * mm
    idx_headers = ["SHEET", "TITLE", "TYPE", "SCALE", "STATUS"]
    idx_rows = [
        ["A-00", "Cover — Project Summary",                "Cover",      "N/A",   "Issued"],
        ["A-01", "Site Plan",                              "Site Plan",  "1:500", "Issued"],
        ["A-02", "Ground Floor Plan",                      "Floor Plan", "1:100", "Issued"],
        ["A-03", "First Floor Plan  (Rev P03 — Balcony + Ladies Room)", "Floor Plan", "1:100", "REVISED"],
        ["A-04", "Front Elevation",                        "Elevation",  "1:100", "Issued"],
        ["A-05", "Section A-A (Stair + Ladies Room)",      "Section",    "1:100", "Issued"],
        ["A-06", "Door & Window Schedule + Balcony Detail","Schedule",   "1:10",  "Issued"],
        ["A-07", "Sanitary Ware Schedule",                 "Schedule",   "N/A",   "Issued"],
        ["A-08", "Specifications & Materials",             "Spec",       "N/A",   "Issued"],
        ["A-09", "Area Statement",                         "Schedule",   "N/A",   "Issued"],
    ]
    idx_cw = [18 * mm, 105 * mm, 30 * mm, 22 * mm, 22 * mm]
    _table(c, DRAW_X + 20 * mm, idx_y, idx_headers, idx_rows, idx_cw)


def _sheet_a01_site(c: canvas.Canvas) -> None:
    """A-01: Site plan (schematic)."""
    _border(c)
    _title_block(c, "A-01", "Site Plan", "SITE PLAN", scale="1:500")

    cx = DRAW_X + DRAW_W / 2
    cy = DRAW_Y + DRAW_H / 2

    # Site boundary (schematic rectangle 55 m × 93 m scaled to fit)
    sx = 25 * mm
    site_w = DRAW_W - 50 * mm
    site_h = DRAW_H - 30 * mm
    site_x = DRAW_X + sx
    site_y = DRAW_Y + 15 * mm

    c.setStrokeColor(C_BLACK)
    c.setLineWidth(2)
    c.rect(site_x, site_y, site_w, site_h)

    # Building footprint centred in site
    fp_w = site_w * 0.55
    fp_h = site_h * 0.42
    fp_x = site_x + (site_w - fp_w) / 2
    fp_y = site_y + site_h * 0.25

    c.setFillColor(C_PALE)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(1.5)
    c.rect(fp_x, fp_y, fp_w, fp_h, fill=1, stroke=1)

    # Balcony projection (south side of building)
    balc_h = site_h * 0.04
    c.setFillColor(C_BALCONY)
    c.rect(fp_x, fp_y - balc_h, fp_w, balc_h, fill=1, stroke=1)

    # East porch
    porch_w = site_w * 0.07
    porch_h = fp_h * 0.18
    c.setFillColor(C_AMBER)
    c.rect(fp_x + fp_w, fp_y + fp_h * 0.35, porch_w, porch_h, fill=1, stroke=1)

    # Labels
    c.setFillColor(C_BLACK)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(fp_x + fp_w / 2, fp_y + fp_h / 2 + 3 * mm, "BAR ASSOCIATION HALL")
    c.setFont("Helvetica", 8)
    c.drawCentredString(fp_x + fp_w / 2, fp_y + fp_h / 2 - 3 * mm, "30.0 m × 24.0 m  (G+1)")
    c.setFillColor(C_BALCONY)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(fp_x + fp_w / 2, fp_y - balc_h / 2, "BALCONY 1.5 m")
    c.setFillColor(C_AMBER)
    c.drawCentredString(fp_x + fp_w + porch_w / 2, fp_y + fp_h * 0.35 + porch_h / 2,
                        "PORCH\n12'×8'")

    # Setback dimensions
    c.setFillColor(C_DARK)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(site_x + site_w / 2, site_y + 5 * mm, "Front Setback")
    c.drawCentredString(site_x + site_w / 2, site_y + site_h - 8 * mm, "Rear Setback")

    # Parking (schematic boxes)
    c.setFont("Helvetica", 7)
    for i in range(8):
        px = site_x + 5 * mm + i * (8 * mm + 2 * mm)
        py = site_y + site_h * 0.06
        c.setFillColor(C_LGRAY)
        c.rect(px, py, 8 * mm, 4 * mm, fill=1, stroke=1)
    c.setFillColor(C_DARK)
    c.drawString(site_x + 5 * mm, site_y + site_h * 0.06 + 5 * mm, "8 CAR PARKING")

    # North arrow
    nx = DRAW_X + DRAW_W - 20 * mm
    ny = DRAW_Y + DRAW_H - 30 * mm
    c.setStrokeColor(C_BLACK)
    c.setFillColor(C_BLACK)
    c.setLineWidth(1.5)
    c.circle(nx, ny, 10 * mm, stroke=1, fill=0)
    # Arrow
    path = c.beginPath()
    path.moveTo(nx, ny + 10 * mm)
    path.lineTo(nx - 3 * mm, ny)
    path.lineTo(nx + 3 * mm, ny)
    path.close()
    c.drawPath(path, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(nx, ny + 13 * mm, "N")

    # Adopted area note
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_RED)
    c.drawString(DRAW_X + 5 * mm, DRAW_Y + 5 * mm,
                 "Adopted setback envelope: 4,427.50 sq ft per floor | "
                 "Verify against physical survey boundary before construction.")


def _sheet_a02_gf(c: canvas.Canvas) -> None:
    """A-02: Ground floor plan (schematic)."""
    _border(c)
    _title_block(c, "A-02", "Ground Floor Plan", "FLOOR PLAN", scale="1:100")

    ox = DRAW_X + 30 * mm
    oy = DRAW_Y + 20 * mm
    scale = min((DRAW_W - 60 * mm) / (30 * mm), (DRAW_H - 40 * mm) / (28.35 * mm))
    # Building envelope in points  (1 m = scale pts)
    bw = 30 * scale
    bh = 28.35 * scale

    c.setFillColor(C_PALE)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(2)
    c.rect(ox, oy, bw, bh, fill=1, stroke=1)

    # Service core dividers
    c.setLineWidth(0.8)
    c.line(ox, oy + 5.03 * scale, ox + bw, oy + 5.03 * scale)
    c.line(ox, oy + 10.21 * scale, ox + bw, oy + 10.21 * scale)
    c.line(ox + 9.14 * scale, oy, ox + 9.14 * scale, oy + 5.03 * scale)
    c.line(ox + 21.34 * scale, oy, ox + 21.34 * scale, oy + 5.03 * scale)

    # Labels
    labels = [
        (ox + 4.57 * scale, oy + 2.5 * scale,  "RECEPTION\n/ RECORDS"),
        (ox + 15.24 * scale, oy + 2.5 * scale, "STAIR CORE"),
        (ox + 25.91 * scale, oy + 2.5 * scale, "TOILETS"),
        (ox + bw / 2, oy + 7.5 * scale,        "ENTRY LOBBY / PUBLIC CIRCULATION"),
        (ox + bw / 2, oy + 19.5 * scale,
         f"MAIN ASSEMBLY HALL\n250.5 m²   Inner height: 3.96 m (13'-0\")"),
        (ox + bw / 2, oy + 26.5 * scale,       "DAIS / SPEAKER ZONE  74.1 m²"),
    ]
    for lx, ly, text in labels:
        c.setFont("Helvetica", 7.5)
        c.setFillColor(C_DARK)
        for i, line in enumerate(text.split("\n")):
            c.drawCentredString(lx, ly - i * 4 * mm, line)

    # Overall dims
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(C_BLACK)
    c.drawCentredString(ox + bw / 2, oy - 8 * mm, f"30.00 m (98'-5\")")
    c.drawString(ox - 18 * mm, oy + bh / 2, f"28.35 m")


def _sheet_a03_ff(c: canvas.Canvas) -> None:
    """A-03: First floor plan with balcony and Ladies Advocate Room."""
    _border(c)
    _title_block(c, "A-03", "First Floor Plan  (Rev P03 — Balcony + Ladies Room)",
                 "FLOOR PLAN", scale="1:100")

    ox = DRAW_X + 30 * mm
    oy = DRAW_Y + 30 * mm      # extra space below for balcony projection
    scale = min((DRAW_W - 60 * mm) / (30 * mm), (DRAW_H - 50 * mm) / (25.5 * mm))
    bw = 30 * scale
    bh = 24 * scale

    # Main building
    c.setFillColor(C_PALE)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(2)
    c.rect(ox, oy, bw, bh, fill=1, stroke=1)

    # Ladies Advocate Room highlight
    lr_x = ox + 24 * scale
    lr_y = oy + 20 * scale
    lr_w = 3 * scale
    lr_h = 4 * scale
    c.setFillColor(C_LADIES)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(1)
    c.rect(lr_x, lr_y, lr_w, lr_h, fill=1, stroke=1)

    # En-suite toilet
    tl_x = ox + 25 * scale
    tl_y = oy + 18 * scale
    tl_w = 2 * scale
    tl_h = 2 * scale
    c.setFillColor(colors.HexColor("#fce7f3"))
    c.rect(tl_x, tl_y, tl_w, tl_h, fill=1, stroke=1)

    # Balcony
    balc_h = 1.5 * scale
    c.setFillColor(colors.HexColor("#fff7ed"))
    c.setStrokeColor(C_BALCONY)
    c.setLineWidth(1.5)
    c.rect(ox, oy - balc_h, bw, balc_h, fill=1, stroke=1)
    # Railing tick marks
    c.setLineWidth(0.5)
    for rx in range(0, 31, 2):
        rpx = ox + rx * scale
        if rpx <= ox + bw:
            c.line(rpx, oy - balc_h, rpx, oy - balc_h - 1 * mm)

    # D4 French door arc to balcony (Ladies Room south wall)
    c.setStrokeColor(colors.HexColor("#2563eb"))
    c.setLineWidth(0.8)
    c.arc(lr_x, lr_y, lr_x + lr_w, lr_y + lr_w, 270, 360)

    # D5 corridor door arc
    c.arc(lr_x - 0.9 * scale, lr_y + lr_h * 0.4,
          lr_x, lr_y + lr_h * 0.4 + 0.9 * scale, 0, 90)

    # D6 internal toilet door
    c.arc(tl_x, tl_y + tl_h, tl_x + 0.75 * scale, tl_y + tl_h + 0.75 * scale, 180, 270)

    # Internal walls
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.8)
    c.line(ox, oy + 1.8 * scale, ox + bw, oy + 1.8 * scale)  # corridor
    c.line(ox, oy + 9 * scale, ox + bw, oy + 9 * scale)       # library south

    # Room labels
    labels = [
        (ox + 4.5 * scale,  oy + 0.9 * scale,  "STAIR CORE"),
        (ox + 15 * scale,   oy + 0.9 * scale,  "TOILET BLOCK"),
        (ox + 15 * scale,   oy + 5 * scale,    "LIBRARY LOBBY  (1.8 m CORRIDOR)"),
        (ox + 15 * scale,   oy + 16 * scale,   "LIBRARY READING ROOM  178.9 m²"),
        (ox + 15 * scale,   oy + 22 * scale,   "STACK AREA  92.0 m²"),
        (ox + lr_x - ox + lr_w / 2, oy + lr_y - oy + lr_h / 2 + 3 * mm,
                                                "LADIES\nROOM\n12 m²"),
        (tl_x + tl_w / 2 - ox + ox, oy + tl_y - oy + tl_h / 2,
                                                "TOILET\n4 m²"),
    ]
    for lx, ly, text in labels:
        c.setFont("Helvetica", 7)
        c.setFillColor(C_DARK)
        for i, line in enumerate(text.split("\n")):
            c.drawCentredString(lx, ly - i * 3.5 * mm, line)

    # Balcony label
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(C_BALCONY)
    c.drawCentredString(ox + bw / 2, oy - balc_h / 2,
                        "CONTINUOUS BALCONY — 1.5 m DEEP  |  MS RAILING 1.05 m HIGH")

    # Dimensions
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(C_BLACK)
    c.drawCentredString(ox + bw / 2, oy - balc_h - 6 * mm, "30.00 m (98'-5\")")
    c.drawString(ox - 16 * mm, oy + bh / 2, "24.00 m")
    c.drawString(lr_x + lr_w + 1 * mm, lr_y + lr_h / 2, "4.00 m")
    c.drawCentredString(lr_x + lr_w / 2, lr_y - 5 * mm, "3.00 m")
    c.drawString(ox - 9 * mm, oy - balc_h / 2, "1.5 m")

    # Revision cloud note
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_RED)
    c.drawString(DRAW_X + 5 * mm, DRAW_Y + 10 * mm,
                 "Rev P03: Balcony added (doors no longer open to air) | "
                 "Ladies Advocate Room 12 m² + en-suite toilet 4 m²")


def _sheet_a04_elevation(c: canvas.Canvas) -> None:
    """A-04: Front elevation (schematic)."""
    _border(c)
    _title_block(c, "A-04", "Front Elevation (South Face)", "ELEVATION", scale="1:100")

    ox = DRAW_X + 25 * mm
    oy = DRAW_Y + 15 * mm
    scale_x = (DRAW_W - 50 * mm) / (30 * mm)
    scale_y = min(scale_x, (DRAW_H - 40 * mm) / (8 * mm))

    bw = 30 * scale_x
    gf_h = 3.5 * scale_y    # ground floor height
    ff_h = 3.5 * scale_y    # first floor height
    balc_h = 0.4 * scale_y  # balcony slab depth

    # Ground
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(2)
    c.line(ox - 5 * mm, oy, ox + bw + 5 * mm, oy)

    # Ground floor walls
    c.setFillColor(C_PALE)
    c.rect(ox, oy, bw, gf_h, fill=1, stroke=1)

    # GF windows
    for wx in [2.0, 5.0, 10.0, 16.0, 22.0, 26.0]:
        wpx = ox + wx * scale_x
        c.setFillColor(colors.HexColor("#bae6fd"))
        c.rect(wpx, oy + 0.6 * scale_y, 1.5 * scale_x, 1.5 * scale_y, fill=1, stroke=1)

    # GF main porch (east = right side of elevation)
    porch_x = ox + bw
    c.setFillColor(C_AMBER)
    c.rect(porch_x, oy, 1.5 * scale_x, gf_h * 0.85, fill=1, stroke=1)
    c.setFont("Helvetica", 7)
    c.setFillColor(C_BLACK)
    c.drawCentredString(porch_x + 0.75 * scale_x, oy + gf_h * 0.4, "PORCH")

    # First floor walls
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.rect(ox, oy + gf_h, bw, ff_h, fill=1, stroke=1)

    # FF windows (French doors on front)
    for wx in [1.5, 5.0, 9.0, 14.0, 19.0, 24.0]:
        wpx = ox + wx * scale_x
        c.setFillColor(colors.HexColor("#7dd3fc"))
        c.rect(wpx, oy + gf_h + 0.2 * scale_y, 1.2 * scale_x, ff_h - 0.4 * scale_y,
               fill=1, stroke=1)
        # glazing bars
        c.setStrokeColor(C_DARK)
        c.setLineWidth(0.4)
        mid_wx = wpx + 0.6 * scale_x
        c.line(mid_wx, oy + gf_h + 0.2 * scale_y,
               mid_wx, oy + gf_h + ff_h - 0.2 * scale_y)
        mid_wy = oy + gf_h + 0.2 * scale_y + (ff_h - 0.4 * scale_y) / 2
        c.line(wpx, mid_wy, wpx + 1.2 * scale_x, mid_wy)

    c.setStrokeColor(C_BLACK)
    c.setLineWidth(1.5)

    # Balcony slab
    c.setFillColor(C_BALCONY)
    c.rect(ox, oy + gf_h - balc_h, bw, balc_h, fill=1, stroke=1)

    # Balcony railing (1.05 m high)
    railing_h = 1.05 * scale_y
    c.setStrokeColor(C_DARK)
    c.setLineWidth(1.2)
    c.line(ox, oy + gf_h, ox, oy + gf_h + railing_h)
    c.line(ox + bw, oy + gf_h, ox + bw, oy + gf_h + railing_h)
    c.line(ox, oy + gf_h + railing_h, ox + bw, oy + gf_h + railing_h)
    # Balusters
    for bx_i in range(0, 31, 1):
        bx_pt = ox + bx_i * scale_x
        if bx_pt <= ox + bw:
            c.line(bx_pt, oy + gf_h, bx_pt, oy + gf_h + railing_h)

    # Parapet
    c.setFillColor(C_DARK)
    c.rect(ox, oy + gf_h + ff_h, bw, 0.6 * scale_y, fill=1, stroke=1)

    # Level labels
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(C_BLACK)
    c.drawString(ox + bw + 3 * mm, oy, "±0.000  NGL")
    c.drawString(ox + bw + 3 * mm, oy + gf_h, f"{3.5:.2f} m  FF 1st Floor")
    c.drawString(ox + bw + 3 * mm, oy + gf_h + ff_h, f"{7.0:.2f} m  Roof Slab")
    c.drawString(ox + bw + 3 * mm, oy + gf_h + ff_h + 0.6 * scale_y, f"{7.6:.2f} m  Parapet")

    # Annotations
    c.setFont("Helvetica", 7)
    c.setFillColor(C_BALCONY)
    c.drawCentredString(ox + bw / 2, oy + gf_h - balc_h - 4 * mm,
                        "CONTINUOUS BALCONY SLAB — 1.5 m PROJECTION | MS RAILING 1.05 m HIGH")
    c.setFillColor(C_DARK)
    c.drawCentredString(ox + bw / 2, oy - 6 * mm,
                        "FRONT ELEVATION — SOUTH FACE | UPVC FRENCH DOORS | STONE BASE | PLASTER FINISH")


def _sheet_a05_section(c: canvas.Canvas) -> None:
    """A-05: Section A-A through stair and Ladies Room."""
    _border(c)
    _title_block(c, "A-05", "Section A-A (Stair + Ladies Room)", "SECTION", scale="1:100")

    ox = DRAW_X + 20 * mm
    oy = DRAW_Y + 10 * mm
    sy = (DRAW_H - 30 * mm) / (8.5 * mm)   # vertical scale
    sx = (DRAW_W - 40 * mm) / (30 * mm)    # horizontal scale

    # Ground
    c.setLineWidth(2.5)
    c.setStrokeColor(C_BLACK)
    c.line(ox - 5 * mm, oy, ox + 30 * sx + 5 * mm, oy)

    # Foundation (schematic)
    c.setFillColor(C_DARK)
    c.rect(ox + 14 * sx, oy - 2.5 * sy, 2 * sx, 2.5 * sy, fill=1, stroke=0)

    # Ground floor walls
    c.setFillColor(C_PALE)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(1.5)
    # West wall
    c.rect(ox, oy, 0.23 * sx, 3.5 * sy, fill=1, stroke=1)
    # East wall
    c.rect(ox + 29.77 * sx, oy, 0.23 * sx, 3.5 * sy, fill=1, stroke=1)
    # GF slab
    c.setFillColor(C_DARK)
    c.rect(ox, oy + 3.5 * sy, 30 * sx, 0.15 * sy, fill=1, stroke=0)

    # Stair section (schematic flights)
    stair_x = ox + 9 * sx
    step_w = (4 * sx) / 9
    step_h = (1.4 * sy) / 9
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.8)
    for st in range(9):
        c.line(stair_x + st * step_w, oy + st * step_h,
               stair_x + (st + 1) * step_w, oy + st * step_h)
        c.line(stair_x + (st + 1) * step_w, oy + st * step_h,
               stair_x + (st + 1) * step_w, oy + (st + 1) * step_h)
    # Landing
    c.setFillColor(C_LGRAY)
    c.rect(stair_x + 4 * step_w, oy + 4 * step_h,
           1.5 * sx, 0.15 * sy, fill=1, stroke=1)

    # First floor slab
    c.setFillColor(C_DARK)
    c.rect(ox, oy + 3.5 * sy, 30 * sx, 0.15 * sy, fill=1, stroke=0)

    # First floor walls
    c.setFillColor(C_PALE)
    c.rect(ox, oy + 3.65 * sy, 0.23 * sx, 3.5 * sy, fill=1, stroke=1)
    c.rect(ox + 29.77 * sx, oy + 3.65 * sy, 0.23 * sx, 3.5 * sy, fill=1, stroke=1)

    # Ladies Room partition
    c.setFillColor(C_LADIES)
    c.rect(ox + 24 * sx, oy + 3.65 * sy, 3 * sx, 3.5 * sy, fill=1, stroke=1)

    # Balcony slab
    c.setFillColor(C_BALCONY)
    c.rect(ox, oy + 3.5 * sy - 0.15 * sy, 30 * sx, 0.15 * sy, fill=1, stroke=1)
    # Balcony railing
    c.setStrokeColor(C_DARK)
    c.setLineWidth(1.2)
    c.line(ox, oy + 3.5 * sy, ox, oy + 3.5 * sy + 1.05 * sy)
    c.line(ox + 30 * sx, oy + 3.5 * sy, ox + 30 * sx, oy + 3.5 * sy + 1.05 * sy)
    c.line(ox, oy + 3.5 * sy + 1.05 * sy, ox + 30 * sx, oy + 3.5 * sy + 1.05 * sy)

    # Roof slab
    c.setFillColor(C_DARK)
    c.rect(ox, oy + 7.15 * sy, 30 * sx, 0.15 * sy, fill=1, stroke=0)
    # Parapet
    c.rect(ox, oy + 7.30 * sy, 30 * sx, 0.6 * sy, fill=1, stroke=0)

    # Level marks
    c.setFont("Helvetica", 7)
    c.setFillColor(C_DARK)
    c.drawString(ox + 30 * sx + 3 * mm, oy, "FF GF  ±0.000")
    c.drawString(ox + 30 * sx + 3 * mm, oy + 3.5 * sy, "FF 1F  +3.500 m")
    c.drawString(ox + 30 * sx + 3 * mm, oy + 7.15 * sy, "Roof   +7.150 m")
    c.drawString(ox + 30 * sx + 3 * mm, oy + 7.30 * sy, "Parapet +7.750 m")

    # Bar Hall height callout
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_BLACK)
    c.drawString(ox + 1 * mm, oy + 1.5 * sy,
                 f"BAR HALL  h = 3.96 m (13'-0\")")

    # Ladies Room label
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(C_LADIES)
    c.drawCentredString(ox + 25.5 * sx, oy + 5.0 * sy, "LADIES\nADVOCATE\nROOM")

    # Section cut line annotation
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLACK)
    c.drawString(DRAW_X + 5 * mm, DRAW_Y + DRAW_H - 5 * mm, "SECTION A-A")


def _sheet_a06_door_schedule(c: canvas.Canvas) -> None:
    """A-06: Door & window schedule + balcony detail."""
    _border(c)
    _title_block(c, "A-06", "Door & Window Schedule + Balcony Detail",
                 "SCHEDULE", scale="1:10 (detail) / N/A (schedule)")

    cy = DRAW_Y + DRAW_H - 8 * mm

    _section_heading(c, DRAW_X + 5 * mm, cy, "DOOR SCHEDULE", DRAW_W - 10 * mm)
    cy -= 2 * mm
    door_headers = ["MARK", "SIZE (W×H mm)", "TYPE", "MATERIAL / HARDWARE", "LOCATION"]
    door_rows = [
        ["D1", "1200 × 2400", "Double Leaf Entrance", "Solid wood + glass panels; concealed hinges", "Main entry, GF east wall"],
        ["D2", "900 × 2100",  "Single Flush Internal","Flush door, lipping both faces; mortise lock", "Offices, library, committee"],
        ["D3", "750 × 2100",  "Toilet PVC",           "WPC/PVC door; tower bolt inside",             "All toilet compartments"],
        ["D4", "1000 × 2400", "French Door — Balcony","UPVC frame + 10 mm toughened glass; handle both sides",
                                                                                                       "All FF front openings to balcony"],
        ["D5", "900 × 2100",  "Single Flush — Privacy","Thumb-turn lock inside; emergency coin-release outside",
                                                                                                       "Ladies Advocate Room — corridor"],
        ["D6", "750 × 2100",  "Internal Toilet Door", "WPC hollow-core; tower bolt inside",           "Ladies Room — en-suite toilet"],
    ]
    door_cw = [14 * mm, 28 * mm, 42 * mm, 90 * mm, 74 * mm]
    cy = _table(c, DRAW_X + 5 * mm, cy, door_headers, door_rows, door_cw)

    cy -= 8 * mm
    _section_heading(c, DRAW_X + 5 * mm, cy, "WINDOW & VENTILATOR SCHEDULE", DRAW_W - 10 * mm)
    cy -= 2 * mm
    win_headers = ["MARK", "SIZE (W×H mm)", "TYPE", "MATERIAL", "LOCATION"]
    win_rows = [
        ["W1", "1500 × 1200", "Fixed + openable casement", "UPVC clear float glass",   "All habitable rooms"],
        ["W2", "900 × 900",   "Openable casement",         "UPVC frosted glass",        "Toilet blocks, stores"],
        ["W3", "600 × 600",   "Louvered ventilator",       "Aluminium louvres",         "Toilet high-level vents; ladies toilet direct external vent"],
    ]
    win_cw = [14 * mm, 28 * mm, 42 * mm, 50 * mm, 114 * mm]
    cy = _table(c, DRAW_X + 5 * mm, cy, win_headers, win_rows, win_cw)

    # Balcony detail (schematic at 1:10)
    cy -= 10 * mm
    _section_heading(c, DRAW_X + 5 * mm, cy, "BALCONY SLAB & RAILING DETAIL  (1:10)", 120 * mm)
    cy -= 5 * mm

    det_x = DRAW_X + 20 * mm
    det_y = cy - 55 * mm
    det_s = 15   # 1 mm in detail = 15 points  (~1:10 at A1)

    # Wall
    c.setFillColor(C_DARK)
    c.rect(det_x, det_y, 15 * det_s, 80 * det_s, fill=1, stroke=1)
    # Slab
    c.setFillColor(C_PALE)
    c.rect(det_x + 15 * det_s, det_y + 30 * det_s, 150 * det_s, 15 * det_s,
           fill=1, stroke=1)
    # Waterproof membrane upturn
    c.setStrokeColor(colors.HexColor("#4ade80"))
    c.setLineWidth(1.5)
    c.line(det_x + 15 * det_s, det_y + 45 * det_s,
           det_x + 15 * det_s, det_y + 60 * det_s)   # upturn 150 mm
    # Drip groove
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.8)
    c.line(det_x + 162 * det_s, det_y + 30 * det_s,
           det_x + 165 * det_s, det_y + 28 * det_s)   # drip groove
    # Railing post
    c.setFillColor(C_DARK)
    c.rect(det_x + 155 * det_s, det_y + 45 * det_s, 3 * det_s, 105 * det_s,
           fill=1, stroke=1)
    # Railing top rail (1.05 m)
    c.rect(det_x + 20 * det_s, det_y + 45 * det_s + 105 * det_s,
           140 * det_s, 2 * det_s, fill=1, stroke=1)

    # Annotations
    c.setFont("Helvetica", 6.5)
    c.setFillColor(C_DARK)
    c.drawString(det_x + 170 * det_s, det_y + 45 * det_s + 105 * det_s, "MS RAILING 1.05 m HIGH")
    c.drawString(det_x + 170 * det_s, det_y + 45 * det_s, "BALCONY SLAB")
    c.drawString(det_x + 170 * det_s, det_y + 37 * det_s, "1:100 OUTWARD SLOPE")
    c.drawString(det_x + 170 * det_s, det_y + 30 * det_s, "WATERPROOF MEMBRANE + 150 mm UPTURN")
    c.drawString(det_x + 170 * det_s, det_y + 25 * det_s, "DRIP GROOVE / ANTI-SKID NOSING")
    c.setFillColor(colors.HexColor("#4ade80"))
    c.drawString(det_x + 170 * det_s, det_y + 20 * det_s, "WATERPROOF MEMBRANE UPTURN ≥ 150 mm")


def _sheet_a07_sanitary(c: canvas.Canvas) -> None:
    """A-07: Sanitary ware schedule."""
    _border(c)
    _title_block(c, "A-07", "Sanitary Ware Schedule", "SCHEDULE", scale="N/A")

    cy = DRAW_Y + DRAW_H - 8 * mm
    _section_heading(c, DRAW_X + 5 * mm, cy, "SANITARY WARE SCHEDULE", DRAW_W - 10 * mm)
    cy -= 2 * mm

    headers = ["CODE", "ITEM", "MAKE / MODEL", "SIZE (mm)", "QTY", "LOCATION"]
    rows = [
        ["WC1", "Wall-hung WC (concealed cistern)",     "Kohler Veil or equiv.",    "350 × 550",  "4", "All toilet blocks"],
        ["WB1", "Wall-hung basin",                       "Kohler or equiv.",          "600 × 450",  "4", "All toilet blocks"],
        ["MF1", "Mirror with shelf",                     "—",                         "600 × 450",  "4", "All toilet blocks"],
        ["TR1", "Towel ring / bar",                      "SS 304",                    "—",           "4", "All toilet blocks"],
        ["TP1", "Toilet paper holder",                   "SS 304",                    "—",           "4", "All toilet blocks"],
        ["EF1", "Exhaust fan 150 mm dia.",               "Havells or equiv.",         "150 dia",    "4", "Direct external vent — all toilets"],
        ["FD1", "Floor drain 100 mm",                    "Chilly or equiv.",          "100 dia",    "4", "All toilet floors"],
        ["GB1", "Grab bar (if required by bye-laws)",    "SS 304 — 32 mm dia.",       "600 × 300",  "2", "Ladies toilet + accessible toilet"],
    ]
    cw = [16 * mm, 65 * mm, 50 * mm, 24 * mm, 12 * mm, (DRAW_W - 10 * mm - 167 * mm)]
    cy = _table(c, DRAW_X + 5 * mm, cy, headers, rows, cw)

    cy -= 10 * mm
    _section_heading(c, DRAW_X + 5 * mm, cy, "LADIES TOILET — FIXTURE LAYOUT NOTES", DRAW_W - 10 * mm)
    cy -= 8 * mm
    notes = [
        "WC1: wall-hung (concealed cistern) at south wall, 400 mm from side wall.",
        "WB1: wall-hung basin at east wall, 600 mm wide, rim at 850 mm AFF.",
        "MF1: mirror above basin, bottom at 1000 mm AFF.",
        "EF1: exhaust fan in south external wall — direct vent, no duct.",
        "FD1: floor drain at low point; floor slopes 1:80 to drain.",
        "Door D6: 750 mm clear, inward-opening, tower bolt from inside.",
        "Finishes: anti-skid ceramic floor 300×300 mm; full-height ceramic wall tiles 300×450 mm.",
    ]
    c.setFont("Helvetica", 8.5)
    c.setFillColor(C_DARK)
    for note in notes:
        c.drawString(DRAW_X + 10 * mm, cy, f"  •  {note}")
        cy -= 5.5 * mm


def _sheet_a08_spec(c: canvas.Canvas) -> None:
    """A-08: Specifications and materials."""
    _border(c)
    _title_block(c, "A-08", "Specifications & Materials", "SPEC", scale="N/A")

    cy = DRAW_Y + DRAW_H - 8 * mm
    spec_sections = [
        ("STRUCTURAL", [
            "Foundation: Isolated RCC footings, M25 concrete, Fe500D steel.",
            "Columns: RCC — C1 (300×600 mm) main hall perimeter; C2 (300×450 mm) service core.",
            "Beams: RCC primary 300×600 mm; secondary 230×450 mm.",
            "Slabs: 150 mm RCC, M25, designed per IS 456:2000.",
            "Seismic: Zone III per IS 1893:2016; ductile detailing throughout.",
            "Wind load: per IS 875 Part 3.",
        ]),
        ("MASONRY & WALLS", [
            "External walls: 230 mm burnt brick, CM 1:6, plaster both faces.",
            "Internal walls: 115 mm burnt brick, CM 1:6, plaster.",
            "Ladies Room partition: 115 mm brick for acoustic privacy.",
            "Balcony parapet: 230 mm brick, 750 mm high (below railing).",
        ]),
        ("BALCONY (Rev P03)", [
            "Slab: 150 mm RCC cantilever, max 1.5 m — edge beam over GF columns.",
            "Waterproofing: APP-modified bitumen membrane, upturn ≥ 150 mm at wall face.",
            "Slope: 1:100 toward outer edge; drip groove / anti-skid nosing at edge.",
            "Floor finish: anti-skid vitrified tiles 600×600 mm.",
            "Railing: 40×40 MS hollow section posts at 1.0 m c/c; 25×25 MS balusters ≤ 100 mm gap;",
            "         top rail 50×25 MS flat; toughened glass infill panels 10 mm.",
            "         Total railing height 1.05 m above balcony FFL.",
        ]),
        ("FINISHES", [
            "Bar Hall floor: kota stone / vitrified tiles 600×600 mm.",
            "Offices / library: vitrified tiles 600×600 mm.",
            "Ladies Advocate Room: vitrified tiles 600×600 mm; 2 m tile dado; emulsion above.",
            "Ladies Toilet: anti-skid ceramic floor 300×300 mm; full-height ceramic wall 300×450 mm.",
            "External: two-coat plaster, elastomeric paint; stone cladding to plinth.",
            "Ceilings: false ceiling with recessed LED in Ladies Room and committee room.",
        ]),
        ("DOORS & WINDOWS", [
            "D4 French doors: UPVC 70 mm profile, white; 10 mm toughened glass; multipoint lock.",
            "D5 privacy door: flush door; thumb-turn mortise lock inside; emergency coin-release outside.",
            "All windows: UPVC white, double-track sliding or casement; 6 mm clear float glass.",
            "Toilet ventilators W3: aluminium louvres, powder-coated.",
        ]),
        ("PLUMBING", [
            "Water supply: CPVC Class 10 pipes; overhead tank 2000 L GI (roof level).",
            "Drainage: UPVC SWR 110 mm; traps at every fixture.",
            "Ladies toilet: direct exhaust fan vent through south external wall (no duct).",
            "Floor drain: P-trap, 100 mm, stainless steel grate.",
        ]),
        ("ELECTRICAL", [
            "LT supply, meter room at GF service core.",
            "Ladies Room: 3×13A sockets, 1×USB charging point, 2×LED downlights, 1×emergency light.",
            "Ladies Toilet: 1×IP44 light fitting, 1×exhaust fan switch, 1×13A socket (shaver).",
        ]),
    ]

    col_w = (DRAW_W - 15 * mm) / 2
    left_sections = spec_sections[:4]
    right_sections = spec_sections[4:]

    for col_idx, sections in enumerate([left_sections, right_sections]):
        cx = DRAW_X + 5 * mm + col_idx * (col_w + 5 * mm)
        cy_col = DRAW_Y + DRAW_H - 8 * mm
        for heading, items in sections:
            _section_heading(c, cx, cy_col, heading, col_w - 5 * mm)
            cy_col -= 8 * mm
            c.setFont("Helvetica", 7.5)
            c.setFillColor(C_DARK)
            for item in items:
                # word-wrap at ~90 chars
                c.drawString(cx + 3 * mm, cy_col, item[:110])
                if len(item) > 110:
                    c.drawString(cx + 6 * mm, cy_col - 4.5 * mm, item[110:])
                    cy_col -= 4.5 * mm
                cy_col -= 4.8 * mm
            cy_col -= 5 * mm


def _sheet_a09_area(c: canvas.Canvas) -> None:
    """A-09: Area statement."""
    _border(c)
    _title_block(c, "A-09", "Area Statement", "SCHEDULE", scale="N/A")

    cy = DRAW_Y + DRAW_H - 8 * mm

    _section_heading(c, DRAW_X + 5 * mm, cy, "GROUND FLOOR — SCHEDULE OF ACCOMMODATION", DRAW_W - 10 * mm)
    cy -= 2 * mm
    gf_headers = ["ROOM ID", "ROOM NAME", "DIMENSIONS (m)", "AREA (m²)", "AREA (sq ft)"]
    gf_rows = [
        ["GF-01", "Reception / Records",           "—",               "13.5",  "145.3"],
        ["GF-02", "Dog-leg Stair Core",             "—",               "16.7",  "179.8"],
        ["GF-03", "Toilet Block (M + F + Acc.)",    "—",               "13.5",  "145.3"],
        ["GF-04", "Entry Lobby / Public Circ.",     "9.14 × 2.44",     "22.3",  "240.0"],
        ["GF-05", "Pantry",                         "3.05 × 2.44",     "7.4",   "80.0" ],
        ["GF-06", "Main Assembly Hall",             "16.76 × 14.94",   "250.5", "2,695.5"],
        ["GF-07", "Dais / Speaker Zone",            "16.76 × 4.42",    "74.1",  "797.5"],
        ["",      "GROUND FLOOR TOTAL",             "",                "398.0", "4,283.4"],
    ]
    gf_cw = [20 * mm, 75 * mm, 45 * mm, 25 * mm, 30 * mm]
    cy = _table(c, DRAW_X + 5 * mm, cy, gf_headers, gf_rows, gf_cw)

    cy -= 8 * mm
    _section_heading(c, DRAW_X + 5 * mm, cy, "FIRST FLOOR — SCHEDULE OF ACCOMMODATION  (Rev P03)", DRAW_W - 10 * mm)
    cy -= 2 * mm
    ff_headers = gf_headers
    ff_rows = [
        ["FF-01", "Librarian / Admin",                    "—",               "13.5",  "145.3"],
        ["FF-02", "Dog-leg Stair Core",                   "—",               "16.7",  "179.8"],
        ["FF-03", "Toilet Block (M + F + Acc.)",          "—",               "13.5",  "145.3"],
        ["FF-04", "Library Lobby / Circ. (1.8 m corr.)", "9.14 × 2.44",     "22.3",  "240.0"],
        ["FF-05", "Pantry",                               "3.05 × 2.44",     "7.4",   "80.0" ],
        ["FF-06", "Library Reading Room",                 "16.76 × 10.67",   "178.9", "1,925.6"],
        ["FF-07", "Stack Area / Book Storage",            "16.76 × 5.49",    "92.0",  "990.0"],
        ["FF-08", "Discussion Room",                      "5.49 × 3.20",     "17.6",  "189.0"],
        ["FF-09", "Computer / Internet Room",             "5.49 × 3.20",     "17.6",  "189.0"],
        ["FF-10", "Store / Electrical",                   "5.79 × 3.20",     "18.5",  "199.0"],
        ["FF-11", "Ladies Advocate Room  [NEW — Rev P03]","3.00 × 4.00",     "12.0",  "129.2"],
        ["FF-12", "Ladies Toilet (en-suite) [NEW — Rev P03]","2.00 × 2.00",  "4.0",   "43.1" ],
        ["",      "FIRST FLOOR TOTAL",                    "",                "414.0", "4,455.3"],
    ]
    ff_cw = gf_cw
    cy = _table(c, DRAW_X + 5 * mm, cy, ff_headers, ff_rows, ff_cw)

    cy -= 8 * mm
    _section_heading(c, DRAW_X + 5 * mm, cy, "SUMMARY", DRAW_W - 10 * mm)
    cy -= 2 * mm
    sum_headers = ["ITEM", "AREA (m²)", "AREA (sq ft)", "NOTE"]
    sum_rows = [
        ["Ground Floor",            "398.0",  "4,283",  ""],
        ["First Floor",             "414.0",  "4,455",  "Includes Ladies Room + Toilet (Rev P03)"],
        ["Balcony (excl. from FAR)","45.0",   "484",    "1.5 m continuous; front facade only"],
        ["BUILT-UP AREA TOTAL",     "857.0",  "9,223",  "GF + FF only"],
        ["Carpet Area (90%)",        "771.3",  "8,301",  "Typical deduction for walls"],
        ["Setback Envelope (per floor)", "411.5", "4,427", "Adopted per site plan brief"],
    ]
    sum_cw = [65 * mm, 25 * mm, 28 * mm, (DRAW_W - 10 * mm - 118 * mm)]
    _table(c, DRAW_X + 5 * mm, cy, sum_headers, sum_rows, sum_cw)


# ── Main PDF builder ──────────────────────────────────────────────────────────

def build_pdf() -> Path:
    """Build a multi-page PDF where each sheet uses its configured page size.

    Drawing sheets (A-00 to A-05) are A1 landscape.
    Schedule/spec sheets (A-06 to A-09) are A3 or A4 landscape — desk-printer
    friendly while the construction drawings stay full-size plotter output.
    """
    # Map sheet IDs to generator functions
    sheet_fns = {
        'A-00': _sheet_a00_cover,
        'A-01': _sheet_a01_site,
        'A-02': _sheet_a02_gf,
        'A-03': _sheet_a03_ff,
        'A-04': _sheet_a04_elevation,
        'A-05': _sheet_a05_section,
        'A-06': _sheet_a06_door_schedule,
        'A-07': _sheet_a07_sanitary,
        'A-08': _sheet_a08_spec,
        'A-09': _sheet_a09_area,
    }

    # ReportLab requires the canvas to be created with a default page size;
    # we use setPageSize() before each page to switch sizes mid-document.
    c = canvas.Canvas(str(OUT_PDF), pagesize=landscape(A1))

    for i, (sheet_id, (sheet_type, pagesize)) in enumerate(SHEET_CONFIG.items()):
        pw, ph = landscape(pagesize)
        c.setPageSize((pw, ph))

        # Inject per-page geometry into module-level globals so all
        # _sheet_* functions (which reference PW/PH/DRAW_* globals) pick
        # up the correct values for this page.
        global PW, PH, DRAW_X, DRAW_Y, DRAW_W, DRAW_H
        PW, PH   = pw, ph
        DRAW_X   = MARGIN
        DRAW_Y   = MARGIN + TITLE_H
        DRAW_W   = pw - 2 * MARGIN
        DRAW_H   = ph - 2 * MARGIN - TITLE_H

        sheet_fns[sheet_id](c)

        size_label = {A1: "A1", A3: "A3", A4: "A4"}.get(pagesize, "?")
        print(f"  [{i+1:02d}/10]  {sheet_id}  ({size_label} landscape)  — {sheet_type}")

        if i < len(SHEET_CONFIG) - 1:
            c.showPage()

    c.save()
    print(f"\n✓  PDF saved: {OUT_PDF}  (10 sheets, mixed A1/A3/A4)")
    return OUT_PDF


if __name__ == "__main__":
    print("Bar Association Hall — PDF Package Generator  (Rev P03)")
    print("=" * 56)
    print("Sheet config:")
    for sid, (stype, ps) in SHEET_CONFIG.items():
        size_lbl = {A1: "A1", A3: "A3", A4: "A4"}.get(ps, "?")
        print(f"  {sid}  {stype:<12}  {size_lbl} landscape")
    print()
    build_pdf()
    print("\nOpen the PDF in any viewer to review all 10 sheets.")
    print("A1 sheets → print on plotter at 1:1")
    print("A3 sheets → print on desk printer at 1:1")
    print("A4 sheet  → print on desk printer at 1:1")
