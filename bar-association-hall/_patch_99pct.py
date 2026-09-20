"""PATCH: Bring generate_refined_cad.py to 99% 3DHome professional clarity.
Directives:
A1 Relocate main entrance -> WEST longer wall + new porch + windows/vents WEST face
A2 Wall-breaks (host wall gap cut) around EVERY door
A3 D-tag + W-tag opening bubble schedule + IDs on every opening
A4 Room-tag balloons + leader lines (replace inline room text)
A5 Column-grid bubble circles at axes ends
A6 North-arrow compass glyph + N label
A7 Material floor hatching across ALL 15 spaces
A8 Full 4-side perimeter + interior partition dims
A9 Door/Window Schedule table on each sheet
(Regenerate handled separately.)
"""
import sys
from pathlib import Path

FILE = Path(r"e:\Rajkumar\Advocate-Chambers\bar-association-hall\generate_refined_cad.py")
src = FILE.read_text()

# =========================================================
# NEW HELPERS TO INJECT AFTER helpers section (after r_arch_dim_v
# =========================================================
NEW_HELPERS = r'''

# =========================================================
# 99% 3DHOME PROFESSIONAL CLARITY HELPERS (A2..A9 + A1 porch)
# =========================================================
def r_wall_gap(msp, x1, y1, x2, y2, gap_cx, gap_cy, gap_w, direction="h"):
    """Draw 2 wall segments leaving a gap of gap_w centered at (gap_cx,gap_cy).
       direction='h' -> horizontal, gap along x (y held constant at line y=gap_cy)
       direction='v' -> vertical, gap along y (x held constant at col x=gap_cx)
       Used for true 3DHome wall-break around door/window openings."""
    lw = 42 if direction == "h" else 42
    if direction == "h":
        g_half = gap_w / 2.0
        y_line = gap_cy
        if x1 < gap_cx - g_half:
            r_line(msp, x1, y_line, gap_cx - g_half, y_line, layer="A-WALL", lw=lw)
        if gap_cx + g_half < x2:
            r_line(msp, gap_cx + g_half, y_line, x2, y_line, layer="A-WALL", lw=lw)
    else:
        g_half = gap_w / 2.0
        x_line = gap_cx
        if y1 < gap_cy - g_half:
            r_line(msp, x_line, y1, x_line, gap_cy - g_half, layer="A-WALL", lw=lw)
        if gap_cy + g_half < y2:
            r_line(msp, x_line, gap_cy + g_half, x_line, y2, layer="A-WALL", lw=lw)


def r_door_pro(msp, hinge_x, hinge_y, w, swing_dir=1,
               tag=None, tag_cx=None, tag_cy=None,
               host_wall=None, host_gap_cx=None, host_gap_cy=None, gap_w=None):
    """3DHome standard door: wall-break + leaf + arc + bubble-marker tag.
       host_wall direction 'h'|'v' determines gap orientation."""
    if host_wall and host_gap_cx is not None:
        if host_wall == "h":
            # gap_y matches hinge_y, gap_w = w + 4" tolerance
            gw = gap_w or (w + 4*IN)
            r_wall_gap(msp, hinge_x - 2*w, hinge_y, hinge_x + 2*w, hinge_y,
                       host_gap_cx, host_gap_cy, gw, direction="h")
        else:
            gw = gap_w or (w + 4*IN)
            r_wall_gap(msp, hinge_x, hinge_y - 2*w, hinge_x, hinge_y + 2*w,
                       host_gap_cx, host_gap_cy, gw, direction="v")
    r_door_swing(msp, hinge_x, hinge_y, w, swing_dir=swing_dir)
    if tag:
        tcx = tag_cx if tag_cx is not None else (hinge_x + w*0.5)
        tcy = tag_cy if tag_cy is not None else (hinge_y + (-1.8*FT if swing_dir>0 else 1.8*FT))
        r_opening_bubble(msp, tcx, tcy, tag)


def r_opening_bubble(msp, cx, cy, label, diam=3.0*FT):
    """3DHome-style D-xx/W-xx circular opening schedule bubble."""
    r = diam / 2.0
    r_circle(msp, cx, cy, r, layer="A-ANNO-NOTE" if False else "A-TEXT", lw=22)
    r_text(msp, label, cx, cy, h=TX_SMALL*FT, layer="A-DOOR",
           align=TextEntityAlignment.MIDDLE_CENTER)


def r_room_bubble(msp, label_cx, label_cy, anchor_cx, anchor_cy,
                  label, sub_label=None, style="round"):
    """3DHome room-tag balloon bubble with leader to anchor point."""
    diam = 6.5 * FT
    r = diam / 2.0
    if style == "round":
        r_circle(msp, label_cx, label_cy, r, layer="A-TEXT", lw=24)
    else:
        r_rect(msp, label_cx - r, label_cy - r, label_cx + r, label_cy + r,
               layer="A-TEXT", lw=24)
    # Leader line from bubble edge (nearest point toward anchor) to anchor
    dx = anchor_cx - label_cx
    dy = anchor_cy - label_cy
    L = math.hypot(dx, dy) or 1.0
    bx = label_cx + dx * r / L
    by = label_cy + dy * r / L
    r_line(msp, bx, by, anchor_cx, anchor_cy, layer="A-TEXT", lw=16)
    # Dot at leader tail (arrow tail on bubble side)
    r_circle(msp, bx, by, 0.35*FT, layer="A-TEXT", lw=22)
    # Room title (bold, large) + subtitle small
    yy_off = -0.4*FT if sub_label else 0.0
    r_text(msp, label, label_cx, label_cy + yy_off, h=TX_LARGE*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)
    if sub_label:
        r_text(msp, sub_label, label_cx, label_cy - 2.4*FT, h=TX_SMALL*FT, layer="A-TEXT",
               align=TextEntityAlignment.MIDDLE_CENTER)


def r_grid_bubble(msp, cx, cy, label, diam=3.6*FT):
    """AIA standard grid-bubble circle with axis ID at column/row end."""
    r = diam / 2.0
    # Two concentric circles
    r_circle(msp, cx, cy, r, layer="A-GRID", lw=26)
    r_circle(msp, cx, cy, r*0.88, layer="A-GRID", lw=16)
    r_text(msp, label, cx, cy, h=TX_MEDIUM*FT, layer="A-GRID",
           align=TextEntityAlignment.MIDDLE_CENTER)


def r_north_arrow(msp, cx, cy, size=8.0*FT):
    """True north-arrow compass: circle + N-S pointer + N letter bar."""
    outer_r = size / 2.0
    inner_r = outer_r * 0.55
    # Outer circle
    r_circle(msp, cx, cy, outer_r, layer="A-ANNO-NOTE" if False else "A-TEXT-TTL", lw=26)
    # Inner circle thinner
    r_circle(msp, cx, cy, inner_r, layer="A-TEXT-TTL", lw=16)
    # North arrow point (top)
    tip_y = cy + outer_r*0.93
    # Triangle filled-ish outline for north-point
    tip_xl, tip_xr = cx - outer_r*0.38, cx + outer_r*0.38
    base_y = cy + inner_r*0.8
    # North pointer (arrow up): fill triangle hatch + sides
    r_line(msp, tip_xl, base_y, cx, tip_y, layer="A-TEXT-TTL", lw=30)
    r_line(msp, tip_xr, base_y, cx, tip_y, layer="A-TEXT-TTL", lw=30)
    r_line(msp, tip_xl, base_y, tip_xr, base_y, layer="A-TEXT-TTL", lw=22)
    try:
        pts_tri = [(tip_xl, base_y), (tip_xr, base_y), (cx, tip_y)]
        rpts = [rotate_pt(p[0], p[1], ROT_CX, ROT_CY, ROT_DEG) for p in pts_tri]
        h = msp.add_hatch(color=7, dxfattribs={"layer": "A-HATCH"})
        h.set_pattern_fill("SOLID", scale=1.0)
        h.paths.add_polyline_path(rpts, is_closed=True)
    except Exception:
        pass
    # South arrow stub (down) short
    stub_y = cy - outer_r*0.55
    r_line(msp, cx - outer_r*0.18, cy - inner_r*0.2, cx, stub_y, layer="A-TEXT-TTL", lw=22)
    r_line(msp, cx + outer_r*0.18, cy - inner_r*0.2, cx, stub_y, layer="A-TEXT-TTL", lw=22)
    # North letter banner (above compass)
    bx1, bx2 = cx - outer_r*0.55, cx + outer_r*0.55
    by1, by2 = tip_y + 0.8*FT, tip_y + 3.2*FT
    r_rect(msp, bx1, by1, bx2, by2, layer="A-TEXT-TTL", lw=24)
    r_text(msp, "N", cx, (by1+by2)/2, h=TX_XL*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)


def r_floor_hatch(msp, x1, y1, x2, y2, pattern="ANSI34", scale=1.5):
    """Material floor hatching for all 15 space types."""
    r_fill_rect(msp, x1, y1, x2, y2, hatch=pattern, layer="A-HATCH", scale=scale)


def r_schedule_table(msp, ox, oy, title, headers, rows,
                     col_widths=None, row_h=2.8*FT):
    """Draw professional schedule table (A9 door/window/opening)."""
    n_cols = len(headers)
    if col_widths is None:
        col_widths = [max(len(headers[i]), max((len(r[i]) for r in rows), default=8))*1.2*FT
                      for i in range(n_cols)]
    total_w = sum(col_widths)
    total_h = (len(rows) + 1) * row_h
    # Frame
    r_rect(msp, ox, oy - total_h, ox + total_w, oy, layer="A-TEXT", lw=30)
    # Title bar
    r_text(msp, title, ox + total_w/2, oy - row_h/2, h=TX_XL*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)
    # Horizontal dividers
    for r in range(len(rows) + 2):
        y_div = oy - r * row_h
        if r in (1, len(rows) + 1):
            lw = 26
        else:
            lw = 14
        r_line(msp, ox, y_div, ox + total_w, y_div, layer="A-TEXT", lw=lw)
    # Columns + header text
    cx = ox
    for ci, (hdr, w) in enumerate(zip(headers, col_widths)):
        if ci > 0:
            r_line(msp, cx, oy, cx, oy - total_h, layer="A-TEXT", lw=14)
        r_text(msp, hdr, cx + w/2, oy - 1.5*row_h, h=TX_LARGE*FT, layer="A-TEXT-TTL",
               align=TextEntityAlignment.MIDDLE_CENTER)
        # Row cells
        for ri, row in enumerate(rows):
            yc = oy - (ri + 2) * row_h + row_h/2
            r_text(msp, row[ci], cx + w/2, yc, h=TX_SMALL*FT, layer="A-TEXT",
                   align=TextEntityAlignment.MIDDLE_CENTER)
        cx += w
    r_line(msp, ox + total_w, oy, ox + total_w, oy - total_h, layer="A-TEXT", lw=14)


def draw_west_porch(msp):
    """A1 Main entry porch on LONGER WEST WALL (X=0 face, 88' longer side).
       8' deep x 30' wide porch, 6 columns, entry at mid-vestibule into building."""
    # Porch extents: project 8' west of X=0 line, span Y=28..58 (30' wide, centered on 88' total 5..93)
    depth = 8 * FT
    span_y0, span_y1 = 28.0, 58.0
    px1 = X(0) - depth
    px2 = X(0)
    py1 = Y(span_y0) - 1*FT
    py2 = Y(span_y1) + 1*FT
    r_rect(msp, px1, py1, px2, py2, layer="A-SITE", lw=32)
    r_fill_rect(msp, px1, py1, px2, py2, hatch="GRATE", layer="A-BAY")
    # Columns along porch (6 evenly spaced)
    n_cols = 6
    for c in range(n_cols):
        frac = (c + 0.5) / n_cols
        cy_ = py1 + frac * (py2 - py1)
        cbx = px1 + depth*0.55 - 6*IN
        cby = cy_ - 6*IN
        r_fill_rect(msp, cbx, cby, cbx + 12*IN, cby + 12*IN, hatch="SOLID", layer="A-COLUMN")
        r_rect(msp, cbx, cby, cbx + 12*IN, cby + 12*IN, layer="A-COLUMN", lw=28)
    # Title + D-tag bubble
    r_text(msp, "WEST / MAIN ENTRY PORCH 30\' x 8\'", (px1+px2)/2, (py1+py2)/2, h=TX_LARGE*FT,
           layer="A-TEXT-TTL", align=TextEntityAlignment.MIDDLE_CENTER, rot=90.0)
    # Return entry door wall gap + double doors on WEST envelope
    # Double leaf main entry into WEST wall -> opens directly into Main Hall west side
    # Centered on porch span
    entry_cy = (Y(span_y0) + Y(span_y1)) / 2.0
    leaf = 4*FT
    hinge_y_bot = entry_cy - leaf
    hinge_y_top = entry_cy
    # Wall-break vertical col WEST (gap 2*leaf + 4")
    gw = 2*leaf + 4*IN
    r_wall_gap(msp, X(0), Y(span_y0) - 3*FT, X(0), Y(span_y1) + 3*FT,
               X(0), entry_cy, gw, direction="v")
    # Bottom leaf swings south, top leaf swings north (double swing into hall)
    r_door_swing(msp, X(0), hinge_y_bot, leaf, swing_dir=1)
    r_door_swing(msp, X(0), hinge_y_top, leaf, swing_dir=-1)
    r_opening_bubble(msp, X(0) - 2.0*FT, entry_cy, "D-MAIN 8\'-0\"")
    r_text(msp, "PRIMARY / MAIN ENTRY\nWEST FACE",
           X(0) - 5*FT, entry_cy, h=TX_XL*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER, rot=90.0)
    # Also open a corridor vestibule: insert an entry narthex on the inside
    # connecting west main entry through an interior pair of double doors into E-W corridor
    # Narthex/vestibule X=0..10, Y=40..56 (10x16)
    vx1, vx2 = X(0) + OWT, X(10) - IWT/2
    vy1, vy2 = Y(40) + IWT/2, Y(56) - IWT/2
    r_rect(msp, vx1, vy1, vx2, vy2, layer="A-WALL", lw=32)
    r_fill_rect(msp, vx1, vy1, vx2, vy2, hatch="AR-CONC", layer="A-HATCH")
    r_room_bubble(msp, vx1 + 6*FT, (vy1+vy2)/2 - 2*FT, (vx1+vx2)/2, (vy1+vy2)/2,
                  "ENTRY VESTIBULE", sub_label="10\' x 16\'", style="round")
    # Interior double doors from vestibule EAST into corridor (Y corridor 21.5..25.5
    # actually at X(10), Y(48) -> corridor from 21.5..25.5 runs horiz so vestibule
    # opens into corridor E wall via X(10) line at Y(23) area - let's do:
    # Interior door south wall of vestibule -> lobby corridor (not E-W corridor)
    # Interior double doors on EAST wall of vestibule -> opens into Main Hall
    int_cy = (vy1 + vy2) / 2.0
    # South door (vestibule -> south lobby through the wall Y=40)
    r_wall_gap(msp, vx1, vy1 - IWT/2, vx2, vy1 - IWT/2,
               (vx1+vx2)/2, vy1 - IWT/2, 6*FT+4*IN, direction="h")
    r_door_swing(msp, (vx1+vx2)/2 - 3*FT, vy1 - IWT/2, 3*FT, swing_dir=1)
    r_door_swing(msp, (vx1+vx2)/2,           vy1 - IWT/2, 3*FT, swing_dir=-1)
    r_opening_bubble(msp, (vx1+vx2)/2, vy1 - 4*FT, "D-VEST 2x3\'-0\"")
    # East door (vestibule -> Main Hall single 4')
    r_wall_gap(msp, vx2, vy1, vx2, vy2,
               vx2, int_cy, 4*FT+4*IN, direction="v")
    r_door_swing(msp, vx2, int_cy - 2*FT, 4*FT, swing_dir=1)
    r_opening_bubble(msp, vx2 + 2.0*FT, int_cy, "D-HALL 4\'-0\"")


def draw_full_perimeter_dims(msp):
    """A8 Full 4-side perimeter dimension strings + interior partitions 3 strings each side."""
    # SOUTH: Y=5 overall plus sub-dims South wing (0..30, 30..55) + overall 55
    r_arch_dim_h(msp, X(0), Y(5), X(30), "30\'-0\"", offset=-1.5*FT)
    r_arch_dim_h(msp, X(0), Y(5), X(55), "55\'-0\" OVERALL", offset=-3.3*FT)
    r_arch_dim_h(msp, X(30), Y(5), X(55), "25\'-0\"", offset=-1.5*FT)
    # Interior south-wing dims
    r_arch_dim_h(msp, X(0), Y(5), X(15), "15\'-0\"", offset=-5.1*FT)
    r_arch_dim_h(msp, X(15), Y(5), X(30), "15\'-0\"", offset=-5.1*FT)
    # NORTH side: Y=93
    r_arch_dim_h(msp, X(0), Y(93), X(15), "15\'-0\"", offset=+1.5*FT)
    r_arch_dim_h(msp, X(15), Y(93), X(30), "15\'-0\"", offset=+1.5*FT)
    r_arch_dim_h(msp, X(31), Y(93), X(46), "15\'-0\"", offset=+1.5*FT)
    r_arch_dim_h(msp, X(46), Y(93), X(55), "9\'-0\"", offset=+1.5*FT)
    r_arch_dim_h(msp, X(0), Y(93), X(55), "55\'-0\" OVERALL", offset=+3.3*FT)
    # WEST side: X(0) from 5..93 LONGER 88'-0" wall
    r_arch_dim_v(msp, X(0), Y(5), Y(21.5), "16\'-6\"", offset=-1.5*FT)
    r_arch_dim_v(msp, X(0), Y(21.5), Y(93), "71\'-6\"", offset=-1.5*FT)
    r_arch_dim_v(msp, X(0), Y(5), Y(93), "88\'-0\" OVERALL LONG WALL", offset=-3.3*FT)
    # Interior vertical dims WEST side zones
    r_arch_dim_v(msp, X(0), Y(5), Y(13), "8\'-0\"", offset=-5.1*FT)
    r_arch_dim_v(msp, X(0), Y(13), Y(21.5), "8\'-6\"", offset=-5.1*FT)
    r_arch_dim_v(msp, X(0), Y(21.5), Y(25.5), "4\'-0\"", offset=-5.1*FT)
    r_arch_dim_v(msp, X(0), Y(25.5), Y(75), "49\'-6\"", offset=-5.1*FT)
    r_arch_dim_v(msp, X(0), Y(75), Y(93), "18\'-0\"", offset=-5.1*FT)
    # EAST side X=55
    r_arch_dim_v(msp, X(55), Y(21.5), Y(54.5), "33\'-0\"", offset=+1.5*FT)
    r_arch_dim_v(msp, X(55), Y(54.5), Y(93), "38\'-6\"", offset=+1.5*FT)
    r_arch_dim_v(msp, X(55), Y(5), Y(93), "88\'-0\" OVERALL LONG WALL", offset=+3.3*FT)
    # Additional interior dims: corridor Y=21.5..25.5 horizontally
    r_arch_dim_h(msp, X(0), Y(21.5), X(55), "55\'-0\" CORRIDOR RUN", offset=+1.5*FT)


def draw_west_wall_windows_vents(msp, level="GF"):
    """A1: Add windows and vents along LONGER WEST wall (X=0, all 4 sides now have glazing)."""
    # WEST wall Y segments: 5..21.5 south wing, then 21.5..93 main block.
    # BUT we just added MAIN ENTRY at Y=28..58 on WEST face - skip windows there.
    # Also the entry vestibule occupies Y=40..56. Skip for doors.
    y_positions = [
        # (y_ft, size_ft, label_type)
        (8,   5,  "W"),
        (17,  5,  "W"),
        (35,  5,  "W"),   # below entry
        (62,  5,  "W"),   # above entry (after Y=58 porch end)
        (70,  6,  "W"),
        (80,  6,  "W"),
        (88,  5,  "W"),
    ]
    for idx, (yf, wf, _lt) in enumerate(y_positions):
        tag = f"W-{level}-{idx+11:02d}"
        r_window(msp, X(0) + OWT/2, Y(yf), wf*FT, direction="w")
        # Bubble for west window
        r_opening_bubble(msp, X(0) - 4.5*FT, Y(yf), tag)
    # Vents WEST (3 total: pantry/bar-off, service, toilet areas)
    vent_ys = [11, 23, 86]
    for idx, vy in enumerate(vent_ys):
        vl = f"V-{level}-W{idx+1}"
        r_ventilator(msp, X(0) + OWT/2, Y(vy), size=2.5*FT, direction="w", label=vl)


# =========================================================
# GENERIC ROOM BUBBLE INVENTORY - SHARED
# =========================================================
ROOM_BUBBLES_GF = [
    ("lx1+6*FT", "(ly1+ly2)/2", "(lx1+lx2)/2", "(ly1+ly2)/2", "ENTRY LOBBY", "SOUTH - SECONDARY", "X(0)+OWT", "X(30)-IWT/2", "Y(5)+OWT", "Y(13)-IWT/2", "GRATE"),
    ("bo_x1+5*FT", "bo_y1+6*FT", "(bo_x1+bo_x2)/2", "(bo_y1+bo_y2)/2", "BAR OFFICE", "15\' x 8.5\'", "X(0)+OWT", "X(15)-IWT/2", "Y(13)+IWT/2", "Y(21.5)-OWT", "ANSI34"),
    ("(mx1+mx2)/2-4*FT", "(my1+my2)/2 if False else ct_y2-2.5*FT", "(mx1+mx2)/2", "ct_y1+3*FT", "MALE TOILET", "5 U + 2 WC", "X(15)+IWT/2", "X(22.5)-IWT/2", "Y(13)+IWT/2", "Y(21.5)-OWT", "DOLMIT"),
    ("(fx1+fx2)/2+4*FT", "ct_y2-2.5*FT", "(fx1+fx2)/2", "ct_y1+3*FT", "FEMALE TOILET", "3 WC", "X(22.5)+IWT/2", "X(30)-OWT", "Y(13)+IWT/2", "Y(21.5)-OWT", "DOLMIT"),
    ("(awc_x1+awc_x2)/2", "(awc_y1+awc_y2)/2+4*FT", "(awc_x1+awc_x2)/2", "(awc_y1+awc_y2)/2", "RPwD AWC", "5\' TURN", "X(0)+OWT", "X(8)-IWT/2", "Y(25.5)+IWT/2", "Y(32)-IWT/2", "AR-CONC"),
    ("(mhx1+mhx2)/2", "mhy1+18*FT", "(mhx1+mhx2)/2", "mhy2-4*FT", "MAIN HALL", "AUDIENCE HALL", "X(0)+OWT", "X(46)-IWT/2", "Y(25.5)+IWT/2", "Y(75)-IWT/2", "NET"),
    ("(rdx1+rdx2)/2", "rdy1+2*FT", "(rdx1+rdx2)/2", "(rdy1+rdy2)/2", "DAIS / ROSTRUM", "15\' x 18\'", "X(31)+IWT/2", "X(46)-IWT/2", "Y(75)+IWT/2", "Y(93)-OWT", "ANSI32"),
    ("stair_ox+4.5*FT", "stair_oy+8*FT", "stair_ox+4.5*FT", "stair_oy+16.5*FT", "PUBLIC STAIR", "ST-01 9\' W", "X(46)+IWT/2", "X(55)-OWT", "Y(21.5)+IWT/2", "Y(54.5)-IWT/2", "ANSI37"),
]

'''

# =========================================================
# INJECT NEW HELPERS
# Locate insertion point: after "def r_arch_dim_v(...):" block ends
# =========================================================
ANCHOR1 = "align=TextEntityAlignment.BOTTOM_CENTER if offset >= 0 else TextEntityAlignment.TOP_CENTER)\n\n\n"
if ANCHOR1 not in src:
    print("FAIL ANCHOR1 (helpers inject) - r_arch_dim_v end not found")
    sys.exit(2)
src = src.replace(ANCHOR1, ANCHOR1 + NEW_HELPERS, 1)

# =========================================================
# A6: Update draw_directions() to reference LONG WEST wall as primary entry direction
# =========================================================
OLD_DIR = '''def draw_directions(msp):
    r_text(msp, "SOUTH - PUBLIC ENTRY", X(27.5), Y(5) - 4*FT, h=TX_XL*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_text(msp, "NORTH", X(27.5), Y(93) + 1.5*FT, h=TX_LARGE*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_text(msp, "WEST", X(0) - 4*FT, Y(49), h=TX_LARGE*FT, layer="A-TEXT-TTL", rot=90.0,
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_text(msp, "EAST - VIP PORTICO", X(55) + 4*FT, Y(49), h=TX_XL*FT, layer="A-TEXT-TTL", rot=90.0,
           align=TextEntityAlignment.MIDDLE_CENTER)
'''
NEW_DIR = '''def draw_directions(msp):
    r_text(msp, "SOUTH - SECONDARY / PUBLIC", X(27.5), Y(5) - 4*FT, h=TX_LARGE*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_text(msp, "NORTH", X(27.5), Y(93) + 1.5*FT, h=TX_LARGE*FT, layer="A-TEXT-TTL",
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_text(msp, "WEST - MAIN ENTRY << LONGER 88\' WALL >>", X(0) - 4*FT, Y(49), h=TX_XL*FT, layer="A-TEXT-TTL", rot=90.0,
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_text(msp, "EAST - VIP PORTICO", X(55) + 4*FT, Y(49), h=TX_LARGE*FT, layer="A-TEXT-TTL", rot=90.0,
           align=TextEntityAlignment.MIDDLE_CENTER)
'''
if OLD_DIR not in src:
    print("FAIL ANCHOR2 (draw_directions) not found")
    sys.exit(3)
src = src.replace(OLD_DIR, NEW_DIR, 1)

# =========================================================
# A5: Upgrade draw_column_grid() with grid bubbles at ends
# =========================================================
OLD_GRID = '''def draw_column_grid(msp):
    col_x = [0, 15, 30, 45, 55]
    col_y = [5, 11.5, 30, 50, 70, 93]
    for cx in col_x:
        if cx <= 30:
            y1, y2 = 5, 93
        else:
            y1, y2 = 21.5, 93
        r_line(msp, X(cx), Y(y1), X(cx), Y(y2), layer="A-GRID", lw=13)
        r_text(msp, f"C-{cx}\'", X(cx), Y(93) + 1.5*FT, h=TX_MEDIUM*FT, layer="A-GRID",
               align=TextEntityAlignment.MIDDLE_CENTER)
    for cy in col_y:
        if cy <= 5 or cy > 21.5:
            x2 = 55
        else:
            x2 = 30
        r_line(msp, X(0), Y(cy), X(x2), Y(cy), layer="A-GRID", lw=13)
        r_text(msp, f"R-{cy}\'", X(0) - 1.5*FT, Y(cy), h=TX_MEDIUM*FT, layer="A-GRID", rot=90.0,
               align=TextEntityAlignment.MIDDLE_CENTER)
    col_sz = 12 * IN
    for cx in col_x:
        for cy in col_y:
            if cx > 30 and cy < 21.5:
                continue
            bx = X(cx) - col_sz/2
            by = Y(cy) - col_sz/2
            r_fill_rect(msp, bx, by, bx + col_sz, by + col_sz, hatch="SOLID", layer="A-COLUMN")
            r_rect(msp, bx, by, bx + col_sz, by + col_sz, layer="A-COLUMN", lw=30)
'''
NEW_GRID = '''def draw_column_grid(msp):
    col_x = [0, 15, 30, 45, 55]
    col_x_ids = ["1", "2", "3", "4", "5"]
    col_y = [5, 11.5, 30, 50, 70, 93]
    col_y_ids = ["A", "B", "C", "D", "E", "F"]
    for cx, gid in zip(col_x, col_x_ids):
        if cx <= 30:
            y1, y2 = 5, 93
        else:
            y1, y2 = 21.5, 93
        r_line(msp, X(cx), Y(y1), X(cx), Y(y2), layer="A-GRID", lw=13)
        r_grid_bubble(msp, X(cx), Y(93) + 4.0*FT, gid)
        r_grid_bubble(msp, X(cx), Y(5)  - 6.5*FT, gid)
    for cy, gid in zip(col_y, col_y_ids):
        if cy <= 5 or cy > 21.5:
            x2 = 55
        else:
            x2 = 30
        r_line(msp, X(0), Y(cy), X(x2), Y(cy), layer="A-GRID", lw=13)
        r_grid_bubble(msp, X(0)  - 6.5*FT, Y(cy), gid)
        r_grid_bubble(msp, X(55) + 4.0*FT, Y(cy), gid)
    col_sz = 12 * IN
    for cx in col_x:
        for cy in col_y:
            if cx > 30 and cy < 21.5:
                continue
            bx = X(cx) - col_sz/2
            by = Y(cy) - col_sz/2
            r_fill_rect(msp, bx, by, bx + col_sz, by + col_sz, hatch="SOLID", layer="A-COLUMN")
            r_rect(msp, bx, by, bx + col_sz, by + col_sz, layer="A-COLUMN", lw=30)
'''
if OLD_GRID not in src:
    print("FAIL ANCHOR3 (draw_column_grid) not found")
    sys.exit(4)
src = src.replace(OLD_GRID, NEW_GRID, 1)

FILE.write_text(src)
print("INJECT PASS 1 (helpers + directions + grid bubbles) OK")

# =========================================================
# NOW: Fully REWRITE draw_ground_floor() with all A1..A9 directives
# Read file again after changes
# =========================================================
src = FILE.read_text()

# Locate draw_ground_floor() start -> end
# Use delimiter: "def draw_ground_floor():" -> "def draw_first_floor():"
idx_start = src.index("def draw_ground_floor():")
idx_end   = src.index("def draw_first_floor():")

# Keep def signature + all locals inside. Build replacement.
NEW_GF = '''def draw_ground_floor():
    doc, msp = setup_doc(sheet_w=SH, sheet_h=SW, config=config)

    draw_directions(msp)
    draw_south_portico(msp)
    draw_east_portico(msp)
    # A1 NEW: West main entry porch on LONGER 88' WEST wall
    draw_west_porch(msp)
    draw_building_envelope(msp)
    draw_column_grid(msp)
    # A6 North arrow compass glyph (top-right corner of sheet)
    r_north_arrow(msp, X(55) + 18*FT, Y(88))

    # ===== SOUTH WING Y=5..21.5 =====
    # Entry Lobby: Y=5..13 (remains as SECONDARY south entry)
    lx1, lx2 = X(0) + OWT, X(30) - OWT
    ly1, ly2 = Y(5) + OWT, Y(13) - IWT/2
    # A7 Floor hatch (GRATE already)
    # Lobby double door (south) from south portico - NOW SECONDARY
    dd_cx = (lx1+lx2)/2
    # A2 Wall-break + bubble for south secondary lobby entry
    r_wall_gap(msp, lx1, ly1 - OWT/2, lx2, ly1 - OWT/2, dd_cx, ly1 - OWT/2, 8*FT+4*IN, direction="h")
    r_door_pro(msp, dd_cx - 4*FT, ly1, 4*FT, swing_dir=1,
               tag="D-S-LBY", host_wall="h", host_gap_cx=dd_cx-2*FT, host_gap_cy=ly1)
    r_door_pro(msp, dd_cx,       ly1, 4*FT, swing_dir=-1,
               tag=None)
    r_opening_bubble(msp, dd_cx, ly1 - 5*FT, "D-SEC 2x4\'-0\" SOUTH")
    # Lobby -> north corridor double door + wall-break
    r_wall_gap(msp, lx1, ly2 - IWT/2, lx2, ly2 - IWT/2, dd_cx, ly2 - IWT/2, 6*FT+4*IN, direction="h")
    r_door_pro(msp, dd_cx - 3*FT, ly2 - IWT/2, 3*FT, swing_dir=1,
               tag="D-LC-1", host_wall="h", host_gap_cx=dd_cx-1.5*FT, host_gap_cy=ly2-IWT/2)
    r_door_pro(msp, dd_cx,       ly2 - IWT/2, 3*FT, swing_dir=-1, tag=None)

    # SOUTH WING: Y=13..21.5 (8.5' deep zone below L-step)
    # Bar Office: X=0..15, Y=13..21.5
    bo_x1, bo_x2 = X(0) + OWT, X(15) - IWT/2
    bo_y1, bo_y2 = Y(13) + IWT/2, Y(21.5) - OWT
    r_rect(msp, bo_x1, bo_y1, bo_x2, bo_y2, layer="A-WALL", lw=32)
    # A7 Office carpet
    r_floor_hatch(msp, bo_x1, bo_y1, bo_x2, bo_y2, pattern="ANSI34", scale=1.5)
    r_rect(msp, bo_x1 + 1*FT, bo_y1 + 1*FT, bo_x2 - 1*FT, bo_y1 + 3*FT, layer="A-FURN", lw=18)
    r_text(msp, "WORK DESK", (bo_x1+bo_x2)/2, bo_y1 + 2*FT, h=TX_SMALL*FT,
           layer="A-FURN", align=TextEntityAlignment.MIDDLE_CENTER)
    # A2 Bar Office door corridor side (south wall Y=13) + wall-break
    r_wall_gap(msp, bo_x1, bo_y1 - IWT/2, bo_x2, bo_y1 - IWT/2, bo_x2 - 1.5*FT, bo_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, bo_x2 - 3*FT, bo_y1, 3*FT, swing_dir=1,
               tag="D-BO", host_wall="h", host_gap_cx=bo_x2 - 1.5*FT, host_gap_cy=bo_y1)
    r_window(msp, (bo_x1+bo_x2)/2, Y(21.5) - OWT/2, 5*FT, direction="n")
    r_opening_bubble(msp, (bo_x1+bo_x2)/2 + 5*FT, Y(21.5) + 2*FT, "W-GF-BO")
    # A4 Room bubble
    r_room_bubble(msp, bo_x1 + 7.5*FT, bo_y1 + 2.5*FT, (bo_x1+bo_x2)/2, (bo_y1+bo_y2)/2,
                  "BAR OFFICE", sub_label="15\' x 8.5\'")

    # Common Toilet (Lawyers): X=15..30, Y=13..21.5
    ct_x1, ct_x2 = X(15) + IWT/2, X(30) - OWT
    ct_y1, ct_y2 = Y(13) + IWT/2, Y(21.5) - OWT
    r_rect(msp, ct_x1, ct_y1, ct_x2, ct_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, ct_x1, ct_y1, ct_x2, ct_y2, pattern="DOLMIT", scale=1.2)
    # Male: X=15..22.5 (7.5' wide), Female: X=22.5..30 (7.5' wide)
    mx1, mx2 = ct_x1, ct_x1 + (ct_x2-ct_x1)*0.5 - IWT/2
    fx1, fx2 = ct_x1 + (ct_x2-ct_x1)*0.5 + IWT/2, ct_x2
    r_line(msp, (mx1+mx2+fx1+fx2)/4 - 1, ct_y1, (mx1+mx2+fx1+fx2)/4 - 1, ct_y2, layer="A-WALL", lw=28)

    # Male Toilet: 5 urinals + 2 WCs
    # 5 Urinals along north wall
    for u in range(5):
        ux = mx1 + 0.6*FT + u * ((mx2-mx1) - 1.2*FT) / 5.0
        r_rect(msp, ux, ct_y2 - 2.2*FT, ux + 1.2*FT, ct_y2 - 0.4*FT, layer="A-FURN", lw=14)
    # 2 WC cubicles along west side (south half)
    wc_w = (mx2 - mx1 - IWT) / 2.0
    for i in range(2):
        wcx1 = mx1 + i * (wc_w + IWT/2)
        wcx2 = wcx1 + wc_w
        r_rect(msp, wcx1, ct_y1, wcx2, ct_y1 + 5*FT, layer="A-WALL", lw=22)
        r_rect(msp, wcx2 - 1.8*FT, ct_y1 + 0.6*FT, wcx2 - 0.5*FT, ct_y1 + 1.8*FT, layer="A-FURN", lw=12)
        # cubicle door + bubble
        r_wall_gap(msp, wcx1, ct_y1, wcx2, ct_y1,
                   wcx2 - 1*FT, ct_y1, 2*FT+3*IN, direction="h")
    # 2 Wash basins
    r_circle(msp, (mx1+mx2)/2, ct_y1 + 6.5*FT, 0.55*FT, layer="A-FURN", lw=14)
    # Entry door male: south wall east side + wall-break
    r_wall_gap(msp, mx1, ct_y1 - IWT/2, mx2, ct_y1 - IWT/2, mx2 - 1.75*FT, ct_y1 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, mx2 - 3*FT - 0.5*FT, ct_y1, 2.75*FT, swing_dir=1,
               tag="D-MT", host_wall="h", host_gap_cx=mx2-1.75*FT, host_gap_cy=ct_y1)
    # Male bubble
    r_room_bubble(msp, (mx1+mx2)/2, ct_y1 + 3*FT, (mx1+mx2)/2, ct_y2 - 2.5*FT,
                  "MALE TOILET", sub_label="5U+2WC")

    # Female Toilet: 3 WCs + 2 basins
    fw = (fx2 - fx1 - IWT) / 3.0
    for i in range(3):
        fcx1 = fx1 + i * (fw + IWT/3)
        fcx2 = fcx1 + fw
        r_rect(msp, fcx1, ct_y1 + 2*FT, fcx2, ct_y2 - 2.5*FT, layer="A-WALL", lw=22)
        r_rect(msp, fcx2 - 1.8*FT, ct_y2 - 4.2*FT, fcx2 - 0.5*FT, ct_y2 - 3*FT, layer="A-FURN", lw=12)
        r_wall_gap(msp, fcx1, ct_y1+2*FT, fcx2, ct_y1+2*FT,
                   fcx2 - 1*FT, ct_y1+2*FT, 2*FT+3*IN, direction="h")
        r_door_pro(msp, fcx2 - 2*FT, ct_y1 + 2*FT, 2*FT, swing_dir=-1, tag=None)
    # 2 Basins south side
    for i in range(2):
        r_circle(msp, fx1 + 1.8*FT + i*(fx2-fx1-3.6*FT), ct_y1 + 1*FT, 0.5*FT, layer="A-FURN", lw=14)
    # Entry door female: south wall west side + wall-break
    r_wall_gap(msp, fx1, ct_y1 - IWT/2, fx2, ct_y1 - IWT/2, fx1 + 1.375*FT, ct_y1 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, fx1 + 0.5*FT, ct_y1, 2.75*FT, swing_dir=-1,
               tag="D-FT", host_wall="h", host_gap_cx=fx1+1.375*FT, host_gap_cy=ct_y1)
    r_room_bubble(msp, (fx1+fx2)/2, ct_y1 + 3*FT, (fx1+fx2)/2, ct_y2 - 2.5*FT,
                  "FEMALE TOILET", sub_label="3WC")

    # =========================================================
    # GF EXTERIOR WINDOWS - SOUTH WALL + A1 NEW WEST WALL + others
    # =========================================================
    for sw in [(5, 5), (12, 5), (18, 5), (24, 5), (28, 5)]:
        r_window(msp, X(sw[0]), Y(5) + OWT/2, 5*FT, direction="s")
    for ew in [(9, "e"), (18, "e")]:
        r_window(msp, X(30) - OWT/2, Y(ew[0]), 5*FT, direction="e")
    # A1 NEW: WEST wall windows/vents (GF)
    draw_west_wall_windows_vents(msp, level="GF")

    # ===== E-W CORRIDOR Y=21.5..25.5 (4' wide) =====
    cx1, cx2 = X(0) + OWT, X(55) - OWT
    cy1, cy2 = Y(21.5) + IWT/2, Y(25.5) - IWT/2
    r_fill_rect(msp, cx1, cy1, cx2, cy2, hatch="GRATE", layer="A-BAY")
    r_text(msp, "CORRIDOR 4\'-0\"", X(27.5), (cy1+cy2)/2, h=TX_XL*FT,
           layer="A-TEXT-TTL", align=TextEntityAlignment.MIDDLE_CENTER)

    # ===== EAST SIDE: VIP DOOR from portico into corridor directly =====
    vx, vy = X(55) - OWT, Y(35)
    r_wall_gap(msp, vx, Y(28), vx, Y(62), vx, vy, 4*FT+4*IN, direction="v")
    r_door_pro(msp, vx, vy - 2*FT, 4*FT, swing_dir=-1,
               tag="D-VIP", host_wall="v", host_gap_cx=vx, host_gap_cy=vy,
               tag_cx=vx + 4.5*FT, tag_cy=vy)

    # ===== STAIR: X=46..55, Y=21.5..54.5 (9'x33') =====
    stair_ox = X(46) + IWT/2
    stair_oy = Y(21.5) + IWT/2
    r_stair_dogleg(msp, stair_ox, stair_oy)
    # Stair entry door from corridor + wall-break
    r_wall_gap(msp, stair_ox, stair_oy - IWT/2, stair_ox + 9*FT, stair_oy - IWT/2,
               stair_ox + 4.5*FT, stair_oy - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, stair_ox + (9*FT)/2 - 1.5*FT, stair_oy, 3*FT, swing_dir=1,
               tag="D-ST-GF", host_wall="h",
               host_gap_cx=stair_ox + 4.5*FT, host_gap_cy=stair_oy,
               tag_cx=stair_ox + 4.5*FT, tag_cy=stair_oy - 5*FT)
    # North exit door from stair to north circulation
    s_ex = stair_ox + 9*FT
    s_ey = stair_oy + 33*FT
    r_wall_gap(msp, stair_ox, s_ey - IWT/2, s_ex, s_ey - IWT/2,
               stair_ox + 4.5*FT, s_ey - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, stair_ox + 4.5*FT - 1.5*FT, s_ey - 3*FT, 3*FT, swing_dir=-1,
               tag="D-ST-EX", tag_cx=stair_ox + 4.5*FT, tag_cy=s_ey + 4*FT)

    # ===== WEST SIDE ROOMS off corridor: RPwD Accessible WC + Storage =====
    # RPwD AWC: X=0..8, Y=25.5..32
    awc_x1, awc_x2 = X(0) + OWT, X(8) - IWT/2
    awc_y1, awc_y2 = Y(25.5) + IWT/2, Y(32) - IWT/2
    r_rect(msp, awc_x1, awc_y1, awc_x2, awc_y2, layer="A-ACC", lw=32)
    r_floor_hatch(msp, awc_x1, awc_y1, awc_x2, awc_y2, pattern="AR-CONC", scale=1.0)
    r_circle(msp, (awc_x1+awc_x2)/2, (awc_y1+awc_y2)/2, 2.5*FT, layer="A-JALI", lw=18)
    r_rect(msp, awc_x2 - 2.4*FT, awc_y1 + 0.8*FT, awc_x2 - 0.8*FT, awc_y1 + 2.2*FT, layer="A-FURN", lw=16)
    r_circle(msp, awc_x1 + 1.8*FT, awc_y2 - 1.6*FT, 0.6*FT, layer="A-FURN", lw=16)
    r_wall_gap(msp, awc_x1, awc_y1 - IWT/2, awc_x2, awc_y1 - IWT/2,
               awc_x2 - 1.5*FT, awc_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, awc_x2 - 3*FT, awc_y1, 3*FT, swing_dir=1,
               tag="D-RPWD", host_wall="h", host_gap_cx=awc_x2 - 1.5*FT, host_gap_cy=awc_y1,
               tag_cx=awc_x2 - 1.5*FT, tag_cy=awc_y1 - 5*FT)
    r_room_bubble(msp, awc_x2 + 3*FT, (awc_y1+awc_y2)/2, (awc_x1+awc_x2)/2, (awc_y1+awc_y2)/2,
                  "RPwD ACCESSIBLE WC", sub_label="5\' TURN")

    # ===== MAIN HALL (Audience chairs only) X=0..46, Y=25.5..75 =====
    mhx1, mhy1 = X(0) + OWT, Y(25.5) + IWT/2
    mhx2, mhy2 = X(46) - IWT/2, Y(75) - IWT/2
    r_rect(msp, mhx1, mhy1, mhx2, mhy2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, mhx1, mhy1, mhx2, mhy2, pattern="NET", scale=2.5)

    # Central 4' Aisle N-S
    aisle_cx = (mhx1 + mhx2) / 2
    aisle_w = 4 * FT
    r_line(msp, aisle_cx - aisle_w/2, mhy1, aisle_cx - aisle_w/2, mhy2, layer="A-BAY", lw=16)
    r_line(msp, aisle_cx + aisle_w/2, mhy1, aisle_cx + aisle_w/2, mhy2, layer="A-BAY", lw=16)
    r_text(msp, "CENTRAL AISLE 4\'", aisle_cx, (mhy1+mhy2)/2, h=TX_LARGE*FT,
           layer="A-TEXT-TTL", rot=90.0, align=TextEntityAlignment.MIDDLE_CENTER)

    # Audience Chairs ONLY - 12 rows
    num_rows = 12
    row_start = mhy1 + 3 * FT
    row_end = mhy2 - 8 * FT
    row_gap = (row_end - row_start) / (num_rows - 1)
    seat_dia = 0.5 * FT
    for r in range(num_rows):
        ry = row_start + r * row_gap
        left_x_start = mhx1 + 1.8 * FT
        left_x_end = aisle_cx - aisle_w/2 - 1.2 * FT
        num_left = int((left_x_end - left_x_start) / (2.2 * FT))
        for c in range(num_left):
            cx_ = left_x_start + c * 2.2 * FT
            r_circle(msp, cx_, ry, seat_dia, layer="A-FURN", lw=14)
        right_x_end = mhx2 - 1.8 * FT
        right_x_start = aisle_cx + aisle_w/2 + 1.2 * FT
        num_right = int((right_x_end - right_x_start) / (2.2 * FT))
        for c in range(num_right):
            cx_ = right_x_start + c * 2.2 * FT
            r_circle(msp, cx_, ry, seat_dia, layer="A-FURN", lw=14)
        r_text(msp, f"R{r+1:02d}", mhx1 + 0.6*FT, ry, h=TX_SMALL*FT, layer="A-BAY")

    # Hall entry doors from corridor (south wall): 2 pairs
    hsw1_h = X(10) + 0.5*FT
    r_wall_gap(msp, mhx1, mhy1 - IWT/2, mhx2, mhy1 - IWT/2,
               hsw1_h + 4*FT, mhy1 - IWT/2, 8*FT+4*IN, direction="h")
    r_door_pro(msp, hsw1_h, mhy1, 4*FT, swing_dir=1,
               tag="D-H-E1", host_wall="h",
               host_gap_cx=hsw1_h + 2*FT, host_gap_cy=mhy1,
               tag_cx=hsw1_h + 4*FT, tag_cy=mhy1 + 5*FT)
    r_door_pro(msp, hsw1_h + 4*FT, mhy1, 4*FT, swing_dir=-1, tag=None)
    r_opening_bubble(msp, hsw1_h + 4*FT, mhy1 + 5*FT, "HALL ENTRY-1")
    hsw2_h = X(32) + 0.5*FT
    r_wall_gap(msp, mhx1, mhy1 - IWT/2, mhx2, mhy1 - IWT/2,
               hsw2_h + 4*FT, mhy1 - IWT/2, 8*FT+4*IN, direction="h")
    r_door_pro(msp, hsw2_h, mhy1, 4*FT, swing_dir=1,
               tag="D-H-E2", host_wall="h",
               host_gap_cx=hsw2_h + 2*FT, host_gap_cy=mhy1)
    r_door_pro(msp, hsw2_h + 4*FT, mhy1, 4*FT, swing_dir=-1, tag=None)
    r_opening_bubble(msp, hsw2_h + 4*FT, mhy1 + 5*FT, "HALL ENTRY-2")

    # Hall exit doors on EAST wall (2 exits)
    egress_w = 4 * FT
    r_wall_gap(msp, mhx2, mhy1, mhx2, mhy2, mhx2, Y(40), egress_w + 4*IN, direction="v")
    r_door_pro(msp, mhx2, Y(40) - egress_w/2, egress_w, swing_dir=1,
               tag="D-EX-1", host_wall="v",
               host_gap_cx=mhx2, host_gap_cy=Y(40),
               tag_cx=mhx2 + 5*FT, tag_cy=Y(40))
    r_wall_gap(msp, mhx2, mhy1, mhx2, mhy2, mhx2, Y(60), egress_w + 4*IN, direction="v")
    r_door_pro(msp, mhx2, Y(60) - egress_w/2, egress_w, swing_dir=1,
               tag="D-EX-2", host_wall="v",
               host_gap_cx=mhx2, host_gap_cy=Y(60),
               tag_cx=mhx2 + 5*FT, tag_cy=Y(60))

    # =========================================================
    # GF EXTERIOR WINDOWS - MAIN EAST WALL + NORTH WALL
    # =========================================================
    for yf in [25, 32, 40, 48, 56, 64, 72, 82, 90]:
        r_window(msp, X(55) - OWT/2, Y(yf), 6*FT, direction="e")
    for xf in [5, 13, 21, 29, 36, 43, 49, 53]:
        r_window(msp, X(xf), Y(93) - OWT/2, 6*FT, direction="n")

    # =========================================================
    # GF VENTILATORS (pantry / toilet / service / west side)
    # =========================================================
    r_ventilator(msp, X(18.75), Y(5) + OWT/2, size=2.5*FT, direction="s", label="V1")
    r_ventilator(msp, X(26.25), Y(5) + OWT/2, size=2.5*FT, direction="s", label="V2")
    r_ventilator(msp, X(4), Y(5) + OWT/2, size=2.5*FT, direction="s", label="V3")
    r_ventilator(msp, X(4.5), Y(93) - OWT/2, size=2.5*FT, direction="n", label="V4")
    r_ventilator(msp, X(26.5), Y(93) - OWT/2, size=2.5*FT, direction="n", label="V5")
    r_ventilator(msp, X(7.5), Y(5) + OWT/2, size=2.5*FT, direction="s", label="V6")
    r_ventilator(msp, X(30) - OWT/2, Y(13), size=2.5*FT, direction="e", label="V7")

    # ===== PRESIDENT CHAMBER (GF NORTH WEST): X=0..16, Y=81..93, Attached toilet X=0..9, Y=75..81 =====
    px1, px2 = X(0) + OWT, X(16) - IWT/2
    py1, py2 = Y(81) + IWT/2, Y(93) - OWT
    r_rect(msp, px1, py1, px2, py2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, px1, py1, px2, py2, pattern="ANSI36", scale=1.5)
    pt_x1, pt_x2 = X(0) + OWT, X(9) - IWT/2
    pt_y1, pt_y2 = Y(75) + IWT/2, Y(81) - IWT/2
    r_rect(msp, pt_x1, pt_y1, pt_x2, pt_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, pt_x1, pt_y1, pt_x2, pt_y2, pattern="DOLMIT", scale=1.2)
    r_rect(msp, pt_x2 - 2.4*FT, pt_y1 + 1*FT, pt_x2 - 0.8*FT, pt_y1 + 2.4*FT, layer="A-FURN", lw=16)
    r_circle(msp, pt_x1 + 1.8*FT, pt_y2 - 1.2*FT, 0.5*FT, layer="A-FURN", lw=16)
    # President chair + table
    r_rect(msp, px1 + 2*FT, py2 - 5*FT, px2 - 2*FT, py2 - 3*FT, layer="A-FURN", lw=22)
    r_circle(msp, (px1+px2)/2, py2 - 5.8*FT, 0.55*FT, layer="A-FURN", lw=20)
    # Guest chairs row
    for gc in range(3):
        r_circle(msp, px1 + 2.5*FT + gc*4*FT, py1 + 2.5*FT, 0.5*FT, layer="A-FURN", lw=16)
    # President entry from access corridor (south wall Y=81) + wall-break
    r_wall_gap(msp, px1, py1 - IWT/2, px2, py1 - IWT/2,
               px2 - 2.5*FT, py1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, px2 - 3*FT - 0.2*FT, py1, 3*FT, swing_dir=1,
               tag="D-PRES", host_wall="h",
               host_gap_cx=px2 - 1.5*FT, host_gap_cy=py1,
               tag_cx=px2 - 1.5*FT, tag_cy=py1 - 5*FT)
    # Interconnecting door from pres chamber -> attached toilet (shared wall Y=81, X=0..9)
    r_wall_gap(msp, pt_x1, pt_y2 - IWT/2, pt_x2, pt_y2 - IWT/2,
               pt_x2 - 1.375*FT, pt_y2 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, pt_x2 - 3*FT - 0.2*FT, pt_y2, 2.75*FT, swing_dir=1, tag="D-P-T")
    # Also corridor access door into president toilet on south
    r_wall_gap(msp, pt_x1, pt_y1 - IWT/2, pt_x2, pt_y1 - IWT/2,
               pt_x1 + 1.375*FT, pt_y1 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, pt_x1 + 0.3*FT, pt_y1, 2.75*FT, swing_dir=-1,
               tag="D-PTC", host_wall="h",
               host_gap_cx=pt_x1 + 1.375*FT, host_gap_cy=pt_y1)
    r_room_bubble(msp, px2 + 4*FT, py2 - 2*FT, (px1+px2)/2, (py1+py2)/2,
                  "PRESIDENT CHAMBER", sub_label="16\' x 12\'")

    # ===== SECRETARY CHAMBER (GF NORTH): X=16..31, Y=81..93, Attached toilet X=22..31, Y=75..81 =====
    sx1, sx2 = X(16) + IWT/2, X(31) - IWT/2
    sy1, sy2 = Y(81) + IWT/2, Y(93) - OWT
    r_rect(msp, sx1, sy1, sx2, sy2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, sx1, sy1, sx2, sy2, pattern="ANSI36", scale=1.5)
    st_x1, st_x2 = X(22) + IWT/2, X(31) - IWT/2
    st_y1, st_y2 = Y(75) + IWT/2, Y(81) - IWT/2
    r_rect(msp, st_x1, st_y1, st_x2, st_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, st_x1, st_y1, st_x2, st_y2, pattern="DOLMIT", scale=1.2)
    r_rect(msp, st_x2 - 2.4*FT, st_y1 + 1*FT, st_x2 - 0.8*FT, st_y1 + 2.4*FT, layer="A-FURN", lw=16)
    r_circle(msp, st_x1 + 1.8*FT, st_y2 - 1.2*FT, 0.5*FT, layer="A-FURN", lw=16)
    # Secretary desk
    r_rect(msp, sx1 + 2*FT, sy2 - 4.5*FT, sx2 - 2*FT, sy2 - 2.8*FT, layer="A-FURN", lw=22)
    r_circle(msp, (sx1+sx2)/2, sy2 - 5.3*FT, 0.55*FT, layer="A-FURN", lw=20)
    # Secy entry from access corridor (south wall Y=81)
    r_wall_gap(msp, sx1, sy1 - IWT/2, sx2, sy1 - IWT/2,
               sx2 - 2.5*FT, sy1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, sx2 - 3*FT - 0.2*FT, sy1, 3*FT, swing_dir=1,
               tag="D-SEC", host_wall="h",
               host_gap_cx=sx2 - 1.5*FT, host_gap_cy=sy1,
               tag_cx=sx2 - 1.5*FT, tag_cy=sy1 - 5*FT)
    # Interconnecting door from secy chamber -> attached toilet
    r_wall_gap(msp, st_x1, st_y2 - IWT/2, st_x2, st_y2 - IWT/2,
               st_x2 - 1.375*FT, st_y2 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, st_x2 - 3*FT - 0.2*FT, st_y2, 2.75*FT, swing_dir=1, tag="D-S-T")
    # Also corridor door into secretary toilet on south
    r_wall_gap(msp, st_x1, st_y1 - IWT/2, st_x2, st_y1 - IWT/2,
               st_x1 + 1.375*FT, st_y1 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, st_x1 + 0.3*FT, st_y1, 2.75*FT, swing_dir=-1,
               tag="D-STC", host_wall="h",
               host_gap_cx=st_x1 + 1.375*FT, host_gap_cy=st_y1)
    r_room_bubble(msp, sx1 + 8*FT, sy1 + 3*FT, (sx1+sx2)/2, (sy1+sy2)/2,
                  "SECRETARY CHAMBER", sub_label="15\' x 12\'")

    # Circulation corridor E-W connecting chambers + hall back corridor
    ac_x1, ac_x2 = X(31) + IWT/2, X(46) - IWT/2
    ac_y1, ac_y2 = Y(75) + IWT/2, Y(81) - IWT/2
    r_fill_rect(msp, ac_x1, ac_y1, ac_x2, ac_y2, hatch="GRATE", layer="A-BAY")
    r_text(msp, "ACCESS CORRIDOR", (ac_x1+ac_x2)/2, (ac_y1+ac_y2)/2, h=TX_LARGE*FT,
           layer="A-TEXT-TTL", align=TextEntityAlignment.MIDDLE_CENTER, rot=90.0)

    # REVISED DAIS: X=31..46, Y=75..93 (15'x18')
    rdx1, rdy1 = X(31) + IWT/2, Y(75) + IWT/2
    rdx2, rdy2 = X(46) - IWT/2, Y(93) - OWT
    r_fill_rect(msp, rdx1, rdy1, rdx2, rdy2, hatch="ANSI32", layer="A-HATCH")
    r_rect(msp, rdx1, rdy1, rdx2, rdy2, layer="A-WALL", lw=35)
    for s in range(3):
        sy_ = rdy1 + (s+1)*0.5*FT
        r_line(msp, rdx1 + 0.5*FT, sy_, rdx2 - 0.5*FT, sy_, layer="A-SECT-CUT", lw=18)
    rdw2, rdd2 = 12*FT, 3*FT
    rx1, ry1 = (rdx1+rdx2)/2 - rdw2/2, rdy2 - 6.5*FT
    rx2, ry2 = rx1 + rdw2, ry1 + rdd2
    r_rect(msp, rx1, ry1, rx2, ry2, layer="A-FURN", lw=26)
    r_text(msp, "ROSTRUM", (rx1+rx2)/2, (ry1+ry2)/2, h=TX_LARGE*FT, layer="A-FURN",
           align=TextEntityAlignment.MIDDLE_CENTER)
    r_circle(msp, (rx1+rx2)/2, ry2 + 1.2*FT, 0.55*FT, layer="A-FURN", lw=18)
    r_wall_gap(msp, rdx1, rdy1 - IWT/2, rdx2, rdy1 - IWT/2,
               rdx1 + 2.5*FT, rdy1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, rdx1 + 1*FT, rdy1, 3*FT, swing_dir=1,
               tag="D-DAIS", host_wall="h",
               host_gap_cx=rdx1 + 2.5*FT, host_gap_cy=rdy1,
               tag_cx=rdx1 + 2.5*FT, tag_cy=rdy1 - 5*FT)
    r_window(msp, (rdx1+rdx2)/2, Y(93) - OWT/2, 5*FT, direction="n")
    r_room_bubble(msp, rdx1 + 7.5*FT, rdy2 - 2*FT, (rdx1+rdx2)/2, (rdy1+rdy2)/2,
                  "DAIS / ROSTRUM", sub_label="15\' x 18\'")

    # A8 Full 4-side perimeter + interior dims
    draw_full_perimeter_dims(msp)

    # Area Schedule GF (CORRECTED values: Pres 246, Secy 234, Total 4244)
    sx, sy = X(55) + 8*FT, Y(75)
    areas = [
        ("President Chamber + Toilet", "246"),
        ("Secretary Chamber + Toilet", "234"),
        ("Bar Office",                "128"),
        ("Common Toilet (5 Urinals)", "128"),
        ("RPwD Accessible WC",         "48"),
        ("Main Hall + Dais",         "2,650"),
        ("Stair + Circulation",        "810"),
        ("TOTAL GF",                 "4,244"),
    ]
    rows_a = [[n, a + " sft"] for n, a in areas]
    r_schedule_table(msp, sx, sy + 2*FT,
                     "AREA SCHEDULE - GROUND FLOOR",
                     ["SPACE", "AREA"], rows_a,
                     col_widths=[28*FT, 14*FT], row_h=2.6*FT)

    # A9 Door/Window Schedule GF (condensed, professional)
    rows_dw = [
        ["D-MAIN",    "WEST FACE",          "8\'-0\"",       "DOUBLE LEAF",  "MAIN ENTRY"],
        ["D-SEC",     "SOUTH LOBBY",        "2x4\'-0\"",     "DOUBLE LEAF",  "SECONDARY"],
        ["D-LC-1",    "LOBBY-CORRIDOR",     "2x3\'-0\"",     "DOUBLE LEAF",  "INTERIOR"],
        ["D-BO",      "BAR OFFICE",         "3\'-0\"",       "SINGLE",       "INTERIOR"],
        ["D-MT",      "MALE TOILET",        "2.75\'-0\"",    "SINGLE",       "ENTRY"],
        ["D-FT",      "FEMALE TOILET",      "2.75\'-0\"",    "SINGLE",       "ENTRY"],
        ["D-VIP",     "EAST FACE",          "4\'-0\"",       "SINGLE",       "VIP"],
        ["D-H-E1",    "HALL ENTRY-1",       "2x4\'-0\"",     "DOUBLE",       "INTERIOR"],
        ["D-H-E2",    "HALL ENTRY-2",       "2x4\'-0\"",     "DOUBLE",       "INTERIOR"],
        ["D-EX-1",    "HALL EXIT EAST",     "4\'-0\"",       "SINGLE",       "EGRESS"],
        ["D-EX-2",    "HALL EXIT EAST",     "4\'-0\"",       "SINGLE",       "EGRESS"],
        ["D-PRES",    "PRESIDENT CHAMBER",  "3\'-0\"",       "SINGLE",       "INTERIOR"],
        ["D-SEC",     "SECRETARY CHAMBER",  "3\'-0\"",       "SINGLE",       "INTERIOR"],
        ["D-ST-GF",   "STAIR ENTRY",        "3\'-0\"",       "SINGLE",       "CIRC"],
        ["D-RPWD",    "ACCESSIBLE WC",      "3\'-0\"",       "SINGLE",       "RPwD"],
        ["W-GF-W11..W17","WEST WALL",       "5/6\'",         "CASEMENT x7",  "VENTILATION"],
    ]
    sx2, sy2 = X(55) + 8*FT, Y(42)
    r_schedule_table(msp, sx2, sy2 + 2*FT,
                     "OPENING SCHEDULE - DOORS & WINDOWS - GF",
                     ["TAG", "LOCATION", "WIDTH", "TYPE", "NOTES"],
                     rows_dw,
                     col_widths=[12*FT, 20*FT, 10*FT, 14*FT, 16*FT], row_h=2.3*FT)

    # Title block
    draw_sheet_frame_and_titleblock(
        msp, SH, SW,
        sheet_no="SHEET 01 OF 02",
        sheet_title="GROUND FLOOR PLAN - 99% 3DHOME STANDARD",
        scale_txt='1/8" = 1\'-0"',
        config=config,
    )

    # Save
    dxf_path = OUT_DXF / f"BA-Refined-Ground-Floor-Plan{SUFFIX}.dxf"
    doc.saveas(str(dxf_path))
    print(f"[OK] GF DXF saved: {dxf_path.name}")
    pdf = export_dxf_to_pdf(dxf_path, config)
    print(f"[OK] GF PDF saved: {pdf}")
    return dxf_path, pdf


'''
# Rebuild file: keep up to idx_start, insert NEW_GF, then keep from idx_end onward
src_new = src[:idx_start] + NEW_GF + src[idx_end:]
FILE.write_text(src_new)
print("GF rewrite PASS 2 OK")

# =========================================================
# REWRITE draw_first_floor(): similar professional treatment
# =========================================================
src = FILE.read_text()
# Locate def draw_first_floor(): to end of function (before "if __name__")
idx_start = src.index("def draw_first_floor():")
idx_end   = src.index("if __name__ == \"__main__\":")

NEW_FF = '''def draw_first_floor():
    doc, msp = setup_doc(sheet_w=SH, sheet_h=SW, config=config)

    draw_directions(msp)
    draw_building_envelope(msp)
    draw_column_grid(msp)
    r_north_arrow(msp, X(55) + 18*FT, Y(88))

    # SOUTH WING LOBBY
    lx1, lx2 = X(0) + OWT, X(30) - OWT
    ly1, ly2 = Y(5) + OWT, Y(13) - IWT/2
    r_fill_rect(msp, lx1, ly1, lx2, ly2, hatch="GRATE", layer="A-BAY")
    r_room_bubble(msp, (lx1+lx2)/2, ly1 + 2*FT, (lx1+lx2)/2, (ly1+ly2)/2,
                  "FF LOBBY", sub_label="RECEPTION")

    # Lobby door (south) — secondary egress FF
    dd_cx = (lx1+lx2)/2
    r_wall_gap(msp, lx1, ly1 - OWT/2, lx2, ly1 - OWT/2, dd_cx, ly1 - OWT/2, 6*FT+4*IN, direction="h")
    r_door_pro(msp, dd_cx - 3*FT, ly1, 3*FT, swing_dir=1,
               tag="D-FF-L1", host_wall="h",
               host_gap_cx=dd_cx, host_gap_cy=ly1)
    r_door_pro(msp, dd_cx,       ly1, 3*FT, swing_dir=-1, tag=None)
    # Lobby -> corridor double door
    r_wall_gap(msp, lx1, ly2 - IWT/2, lx2, ly2 - IWT/2, dd_cx, ly2 - IWT/2, 6*FT+4*IN, direction="h")
    r_door_pro(msp, dd_cx - 3*FT, ly2 - IWT/2, 3*FT, swing_dir=1,
               tag="D-FF-LC", host_wall="h",
               host_gap_cx=dd_cx, host_gap_cy=ly2 - IWT/2)
    r_door_pro(msp, dd_cx,       ly2 - IWT/2, 3*FT, swing_dir=-1, tag=None)

    # SOUTH WING: Y=13..21.5 - PANTRY + STORE
    pn_x1, pn_x2 = X(0) + OWT, X(15) - IWT/2
    pn_y1, pn_y2 = Y(13) + IWT/2, Y(21.5) - OWT
    r_rect(msp, pn_x1, pn_y1, pn_x2, pn_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, pn_x1, pn_y1, pn_x2, pn_y2, pattern="ANSI34", scale=1.5)
    r_rect(msp, pn_x1 + 0.5*FT, pn_y1 + 0.5*FT, pn_x2 - 0.5*FT, pn_y1 + 2.8*FT, layer="A-FURN", lw=18)
    r_circle(msp, pn_x1 + 4*FT, pn_y1 + 1.6*FT, 0.5*FT, layer="A-FURN", lw=14)
    r_wall_gap(msp, pn_x1, pn_y1 - IWT/2, pn_x2, pn_y1 - IWT/2,
               pn_x2 - 1.5*FT, pn_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, pn_x2 - 3*FT, pn_y1, 3*FT, swing_dir=1,
               tag="D-PAN", host_wall="h",
               host_gap_cx=pn_x2 - 1.5*FT, host_gap_cy=pn_y1)
    r_window(msp, (pn_x1+pn_x2)/2, Y(21.5) - OWT/2, 5*FT, direction="n")
    r_room_bubble(msp, pn_x1 + 7.5*FT, pn_y1 + 2*FT, (pn_x1+pn_x2)/2, (pn_y1+pn_y2)/2,
                  "PANTRY", sub_label="15\' x 8.5\'")

    # STORE
    st_x1, st_x2 = X(15) + IWT/2, X(30) - OWT
    st_y1, st_y2 = Y(13) + IWT/2, Y(21.5) - OWT
    r_rect(msp, st_x1, st_y1, st_x2, st_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, st_x1, st_y1, st_x2, st_y2, pattern="ANSI37", scale=1.5)
    r_rect(msp, st_x1 + 0.5*FT, st_y1 + 0.5*FT, st_x1 + 3*FT, st_y2 - 0.5*FT, layer="A-LOCKER", lw=18)
    r_wall_gap(msp, st_x1, st_y1 - IWT/2, st_x2, st_y1 - IWT/2,
               st_x1 + 2.5*FT, st_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, st_x1 + 1*FT, st_y1, 3*FT, swing_dir=1,
               tag="D-STR", host_wall="h",
               host_gap_cx=st_x1 + 2.5*FT, host_gap_cy=st_y1)
    r_room_bubble(msp, st_x1 + 7.5*FT, st_y1 + 2*FT, (st_x1+st_x2)/2, (st_y1+st_y2)/2,
                  "STORE ROOM", sub_label="15\' x 8.5\'")

    # =========================================================
    # FF EXTERIOR WINDOWS - SOUTH, EAST (south wing), NORTH, MAIN EAST
    # =========================================================
    for sw in [(5, 5), (12, 5), (18, 5), (24, 5), (28, 5)]:
        r_window(msp, X(sw[0]), Y(5) + OWT/2, 5*FT, direction="s")
    for ew in [(9, "e"), (18, "e")]:
        r_window(msp, X(30) - OWT/2, Y(ew[0]), 5*FT, direction="e")
    # A1 NEW: WEST wall windows FF
    draw_west_wall_windows_vents(msp, level="FF")
    for yf in [25, 32, 40, 48, 56, 64, 72, 82, 90]:
        r_window(msp, X(55) - OWT/2, Y(yf), 6*FT, direction="e")
    for xf in [5, 13, 21, 29, 36, 43, 49, 53]:
        r_window(msp, X(xf), Y(93) - OWT/2, 6*FT, direction="n")

    # E-W CORRIDOR
    cx1, cx2 = X(0) + OWT, X(55) - OWT
    cy1, cy2 = Y(21.5) + IWT/2, Y(25.5) - IWT/2
    r_fill_rect(msp, cx1, cy1, cx2, cy2, hatch="GRATE", layer="A-BAY")
    r_text(msp, "CORRIDOR 4\'-0\"", X(27.5), (cy1+cy2)/2, h=TX_XL*FT,
           layer="A-TEXT-TTL", align=TextEntityAlignment.MIDDLE_CENTER)

    # STAIR (STACKED over GF)
    stair_ox = X(46) + IWT/2
    stair_oy = Y(21.5) + IWT/2
    r_stair_dogleg(msp, stair_ox, stair_oy)
    s_ex = stair_ox + 9*FT
    s_ey = stair_oy + 33*FT
    r_wall_gap(msp, stair_ox, stair_oy - IWT/2, s_ex, stair_oy - IWT/2,
               stair_ox + 4.5*FT, stair_oy - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, (stair_ox + s_ex)/2 - 1.5*FT, stair_oy, 3*FT, swing_dir=1,
               tag="D-ST-FF", host_wall="h",
               host_gap_cx=stair_ox + 4.5*FT, host_gap_cy=stair_oy,
               tag_cx=stair_ox + 4.5*FT, tag_cy=stair_oy - 5*FT)
    r_wall_gap(msp, stair_ox, s_ey - IWT/2, s_ex, s_ey - IWT/2,
               stair_ox + 4.5*FT, s_ey - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, (stair_ox + s_ex)/2 - 1.5*FT, s_ey - 3*FT, 3*FT, swing_dir=-1,
               tag="D-ST-FX", tag_cx=stair_ox + 4.5*FT, tag_cy=s_ey + 4*FT)

    # ===== EDP PROCESS CENTRE =====
    edp_x1, edp_x2 = X(0) + OWT, X(15) - IWT/2
    edp_y1, edp_y2 = Y(25.5) + IWT/2, Y(40) - IWT/2
    r_rect(msp, edp_x1, edp_y1, edp_x2, edp_y2, layer="A-WALL", lw=35)
    r_floor_hatch(msp, edp_x1, edp_y1, edp_x2, edp_y2, pattern="ANSI35", scale=1.5)
    # 3 computer desks
    desk_w, desk_d = 4*FT, 2*FT
    for c in range(3):
        cx_ = edp_x1 + 1.5*FT + c * (desk_w + 0.8*FT)
        r_rect(msp, cx_, edp_y1 + 2*FT, cx_ + desk_w, edp_y1 + 2*FT + desk_d, layer="A-FURN", lw=20)
        r_circle(msp, cx_ + desk_w/2, edp_y1 + 2*FT + desk_d + 0.8*FT, 0.45*FT, layer="A-FURN", lw=16)
        r_rect(msp, cx_ + desk_w/2 - 0.7*FT, edp_y1 + 2*FT + 0.3*FT, cx_ + desk_w/2 + 0.7*FT, edp_y1 + 2*FT + 1*FT, layer="A-FURN", lw=14)
        r_text(msp, f"PC-{c+1}", cx_ + desk_w/2, edp_y1 + 2*FT + desk_d/2, h=TX_SMALL*FT,
               layer="A-FURN", align=TextEntityAlignment.MIDDLE_CENTER)
    # Printer table
    r_rect(msp, edp_x1 + 1.5*FT, edp_y2 - 3*FT, edp_x2 - 1.5*FT, edp_y2 - 1*FT, layer="A-FURN", lw=18)
    r_text(msp, "PRINTER / PLOTTER", (edp_x1+edp_x2)/2, edp_y2 - 2*FT, h=TX_SMALL*FT,
           layer="A-FURN", align=TextEntityAlignment.MIDDLE_CENTER)
    # Entry door (south corridor side) + wall-break
    r_wall_gap(msp, edp_x1, edp_y1 - IWT/2, edp_x2, edp_y1 - IWT/2,
               edp_x2 - 2.0*FT, edp_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, edp_x2 - 3*FT - 0.5*FT, edp_y1, 3*FT, swing_dir=1,
               tag="D-FF-01", host_wall="h",
               host_gap_cx=edp_x2 - 2.0*FT, host_gap_cy=edp_y1,
               tag_cx=edp_x2 - 2*FT, tag_cy=edp_y1 - 5*FT)
    r_room_bubble(msp, edp_x1 + 7.5*FT, edp_y1 + 2*FT, (edp_x1+edp_x2)/2, (edp_y1+edp_y2)/2,
                  "EDP PROCESS CENTRE", sub_label="15\' x 14.5\'")

    # ===== LIBRARY READING ROOM =====
    lx1, ly1 = X(15) + IWT/2, Y(25.5) + IWT/2
    lx2, ly2 = X(46) - IWT/2, Y(75) - IWT/2
    r_rect(msp, lx1, ly1, lx2, ly2, layer="A-WALL", lw=35)
    r_floor_hatch(msp, lx1, ly1, lx2, ly2, pattern="NET3", scale=2.0)
    # Central 4' Aisle
    laisle_cx = (lx1 + lx2) / 2
    laisle_w = 4 * FT
    r_line(msp, laisle_cx - laisle_w/2, ly1, laisle_cx - laisle_w/2, ly2, layer="A-BAY", lw=16)
    r_line(msp, laisle_cx + laisle_w/2, ly1, laisle_cx + laisle_w/2, ly2, layer="A-BAY", lw=16)
    r_text(msp, "AISLE 4\'", laisle_cx, (ly1+ly2)/2, h=TX_LARGE*FT,
           layer="A-TEXT-TTL", rot=90.0, align=TextEntityAlignment.MIDDLE_CENTER)
    # Library tables chairs BOTH sides
    tbl_w, tbl_d = 5 * FT, 2.2 * FT
    num_trows = 6
    trow_start = ly1 + 4 * FT
    trow_end = ly2 - 10 * FT
    tgap = (trow_end - trow_start) / (num_trows - 1) if num_trows > 1 else 0
    for tr in range(num_trows):
        ty_ = trow_start + tr * tgap
        for tl in range(2):
            tx_ = lx1 + 1.5*FT + tl * (tbl_w + 1.2*FT)
            r_rect(msp, tx_, ty_, tx_ + tbl_w, ty_ + tbl_d, layer="A-FURN", lw=22)
            for bc in range(3):
                r_circle(msp, tx_ + 1*FT + bc * 1.5*FT, ty_ - 0.8*FT, 0.42*FT, layer="A-FURN", lw=14)
            for tc in range(3):
                r_circle(msp, tx_ + 1*FT + tc * 1.5*FT, ty_ + tbl_d + 0.8*FT, 0.42*FT, layer="A-FURN", lw=14)
        for tr_ in range(2):
            tx_ = laisle_cx + laisle_w/2 + 1.2*FT + tr_ * (tbl_w + 1.2*FT)
            r_rect(msp, tx_, ty_, tx_ + tbl_w, ty_ + tbl_d, layer="A-FURN", lw=22)
            for bc in range(3):
                r_circle(msp, tx_ + 1*FT + bc * 1.5*FT, ty_ - 0.8*FT, 0.42*FT, layer="A-FURN", lw=14)
            for tc in range(3):
                r_circle(msp, tx_ + 1*FT + tc * 1.5*FT, ty_ + tbl_d + 0.8*FT, 0.42*FT, layer="A-FURN", lw=14)
    # Library entry doors from corridor (south wall): 2 pairs
    le1_h = X(20) + 0.5*FT
    r_wall_gap(msp, lx1, ly1 - IWT/2, lx2, ly1 - IWT/2,
               le1_h + 4*FT, ly1 - IWT/2, 8*FT+4*IN, direction="h")
    r_door_pro(msp, le1_h, ly1, 4*FT, swing_dir=1,
               tag="D-LIB-1", host_wall="h",
               host_gap_cx=le1_h + 4*FT, host_gap_cy=ly1,
               tag_cx=le1_h + 4*FT, tag_cy=ly1 - 5*FT)
    r_door_pro(msp, le1_h + 4*FT, ly1, 4*FT, swing_dir=-1, tag=None)
    le2_h = X(38) - 4*FT + 0.5*FT
    r_wall_gap(msp, lx1, ly1 - IWT/2, lx2, ly1 - IWT/2,
               le2_h + 4*FT, ly1 - IWT/2, 8*FT+4*IN, direction="h")
    r_door_pro(msp, le2_h, ly1, 4*FT, swing_dir=1,
               tag="D-LIB-2", host_wall="h",
               host_gap_cx=le2_h + 4*FT, host_gap_cy=ly1)
    r_door_pro(msp, le2_h + 4*FT, ly1, 4*FT, swing_dir=-1, tag=None)
    # Library exit on EAST wall
    egress_w = 4 * FT
    r_wall_gap(msp, lx2, ly1, lx2, ly2, lx2, Y(60), egress_w + 4*IN, direction="v")
    r_door_pro(msp, lx2, Y(60) - egress_w/2, egress_w, swing_dir=1,
               tag="D-LIB-EX", host_wall="v",
               host_gap_cx=lx2, host_gap_cy=Y(60),
               tag_cx=lx2 + 5*FT, tag_cy=Y(60))

    # ===== STACK AREA =====
    sk_x1, sk_y1 = X(15) + IWT/2, Y(75) + IWT/2
    sk_x2, sk_y2 = X(46) - IWT/2, Y(85) - IWT/2
    r_rect(msp, sk_x1, sk_y1, sk_x2, sk_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, sk_x1, sk_y1, sk_x2, sk_y2, pattern="ANSI37", scale=1.5)
    # 5 double-sided shelf rows
    for sr in range(5):
        sy_ = sk_y1 + 1*FT + sr * ((sk_y2 - sk_y1 - 2*FT) / 5.0)
        r_line(msp, sk_x1 + 2*FT, sy_, sk_x2 - 2*FT, sy_, layer="A-LOCKER", lw=20)
        r_line(msp, sk_x1 + 2*FT, sy_ + 2*FT, sk_x2 - 2*FT, sy_ + 2*FT, layer="A-LOCKER", lw=20)
    # Cross aisle
    cross_cx = (sk_x1+sk_x2)/2
    r_line(msp, cross_cx - 1.5*FT, sk_y1, cross_cx - 1.5*FT, sk_y2, layer="A-BAY", lw=16)
    r_line(msp, cross_cx + 1.5*FT, sk_y1, cross_cx + 1.5*FT, sk_y2, layer="A-BAY", lw=16)
    # 2 doors from library into stack (south wall)
    r_wall_gap(msp, sk_x1, sk_y1 - IWT/2, sk_x2, sk_y1 - IWT/2,
               cross_cx - 3.0*FT, sk_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_wall_gap(msp, sk_x1, sk_y1 - IWT/2, sk_x2, sk_y1 - IWT/2,
               cross_cx + 3.0*FT, sk_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, cross_cx - 4.5*FT, sk_y1, 3*FT, swing_dir=1,
               tag="D-STK-1", host_wall="h",
               host_gap_cx=cross_cx - 3.0*FT, host_gap_cy=sk_y1)
    r_door_pro(msp, cross_cx + 1.5*FT, sk_y1, 3*FT, swing_dir=-1,
               tag="D-STK-2", host_wall="h",
               host_gap_cx=cross_cx + 3.0*FT, host_gap_cy=sk_y1)
    r_room_bubble(msp, (sk_x1+sk_x2)/2, sk_y1 + 3*FT, (sk_x1+sk_x2)/2, (sk_y1+sk_y2)/2,
                  "STACK AREA", sub_label="BOOK STORAGE")

    # ===== FF CHAMBERS ROW: LIBRARIAN + ADMIN (WEST STRIP X=0..15, Y=40..75) =====
    # LIBRARIAN CABIN
    lb_x1, lb_x2 = X(0) + OWT, X(15) - IWT/2
    lb_y1, lb_y2 = Y(40) + IWT/2, Y(55) - IWT/2
    r_rect(msp, lb_x1, lb_y1, lb_x2, lb_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, lb_x1, lb_y1, lb_x2, lb_y2, pattern="ANSI36", scale=1.5)
    r_rect(msp, lb_x1 + 1.5*FT, lb_y2 - 4.5*FT, lb_x2 - 1.5*FT, lb_y2 - 1.5*FT, layer="A-FURN", lw=20)
    r_circle(msp, (lb_x1+lb_x2)/2, lb_y2 - 5.2*FT, 0.45*FT, layer="A-FURN", lw=16)
    r_rect(msp, lb_x2 - 2.5*FT, lb_y1 + 2*FT, lb_x2 - 0.5*FT, lb_y2 - 2*FT, layer="A-FURN", lw=20)
    r_text(msp, "ISSUE COUNTER", lb_x2 - 1.5*FT, (lb_y1+lb_y2)/2, h=TX_SMALL*FT,
           layer="A-FURN", align=TextEntityAlignment.MIDDLE_CENTER, rot=90.0)
    # Entry door south corridor side
    r_wall_gap(msp, lb_x1, lb_y1 - IWT/2, lb_x2, lb_y1 - IWT/2,
               lb_x2 - 1.8*FT, lb_y1 - IWT/2, 3*FT+4*IN, direction="h")
    r_door_pro(msp, lb_x2 - 3*FT - 0.3*FT, lb_y1, 3*FT, swing_dir=1,
               tag="D-LIBR", host_wall="h",
               host_gap_cx=lb_x2 - 1.8*FT, host_gap_cy=lb_y1,
               tag_cx=lb_x2 - 1.8*FT, tag_cy=lb_y1 - 5*FT)
    r_room_bubble(msp, lb_x1 + 7.5*FT, lb_y1 + 2.5*FT, (lb_x1+lb_x2)/2, (lb_y1+lb_y2)/2,
                  "LIBRARIAN", sub_label="15\' x 15\'")

    # ADMIN OFFICE
    ao_x1, ao_x2 = X(0) + OWT, X(15) - IWT/2
    ao_y1, ao_y2 = Y(55) + IWT/2, Y(75) - IWT/2
    r_rect(msp, ao_x1, ao_y1, ao_x2, ao_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, ao_x1, ao_y1, ao_x2, ao_y2, pattern="ANSI36", scale=1.5)
    r_rect(msp, ao_x1 + 1*FT, ao_y1 + 1*FT, ao_x2 - 1*FT, ao_y1 + 2.5*FT, layer="A-FURN", lw=20)
    r_text(msp, "WORK DESK 13\'x1.5\'", (ao_x1+ao_x2)/2, ao_y1 + 1.75*FT, h=TX_SMALL*FT,
           layer="A-FURN", align=TextEntityAlignment.MIDDLE_CENTER)
    for w in range(2):
        wx_ = ao_x1 + 2*FT + w * ((ao_x2-ao_x1) - 4*FT)/1.0
        r_rect(msp, wx_, ao_y2 - 7*FT, wx_ + 4*FT, ao_y2 - 3*FT, layer="A-FURN", lw=18)
        r_circle(msp, wx_ + 2*FT, ao_y2 - 8*FT, 0.4*FT, layer="A-FURN", lw=14)
    r_rect(msp, ao_x1 + 0.5*FT, ao_y1 + 4*FT, ao_x1 + 2.5*FT, ao_y1 + 14*FT, layer="A-LOCKER", lw=16)
    # Entry door south corridor side (from corridor Y=25.5 area; actually room is above librarian so door on south? No - use east wall into library main)
    # Admin entry is from library east wall: place door on EAST side into library X=15
    r_wall_gap(msp, ao_x2, ao_y1, ao_x2, ao_y2, ao_x2, (ao_y1+ao_y2)/2, 3*FT+4*IN, direction="v")
    r_door_pro(msp, ao_x2, (ao_y1+ao_y2)/2 - 1.5*FT, 3*FT, swing_dir=-1,
               tag="D-ADM", host_wall="v",
               host_gap_cx=ao_x2, host_gap_cy=(ao_y1+ao_y2)/2,
               tag_cx=ao_x2 + 4.5*FT, tag_cy=(ao_y1+ao_y2)/2)
    r_room_bubble(msp, ao_x1 + 7.5*FT, ao_y1 + 2.5*FT, (ao_x1+ao_x2)/2, (ao_y1+ao_y2)/2,
                  "ADMIN OFFICE", sub_label="15\' x 20\'")

    # FF TOILET (above stair X=46..55, Y=54.5..70)
    ffto_x1, ffto_x2 = X(46) + IWT/2, X(55) - OWT
    ffto_y1, ffto_y2 = Y(54.5) + IWT/2, Y(70) - IWT/2
    r_rect(msp, ffto_x1, ffto_y1, ffto_x2, ffto_y2, layer="A-WALL", lw=32)
    r_floor_hatch(msp, ffto_x1, ffto_y1, ffto_x2, ffto_y2, pattern="DOLMIT", scale=1.2)
    ffmx1, ffmx2 = ffto_x1, ffto_x1 + (ffto_x2-ffto_x1)*0.55 - IWT/2
    fffx1, fffx2 = ffto_x1 + (ffto_x2-ffto_x1)*0.55 + IWT/2, ffto_x2
    r_line(msp, (ffmx2+fffx1)/2, ffto_y1, (ffmx2+fffx1)/2, ffto_y2, layer="A-WALL", lw=28)
    # Male: 3 urinals + 2 WCs
    for u in range(3):
        ux = ffmx1 + 0.5*FT + u * ((ffmx2-ffmx1) - 1*FT) / 3.0
        r_rect(msp, ux, ffto_y2 - 2.2*FT, ux + 1.1*FT, ffto_y2 - 0.4*FT, layer="A-FURN", lw=14)
    mw_w = (ffmx2 - ffmx1 - IWT) / 2.0
    for i in range(2):
        mwcx1 = ffmx1 + i * (mw_w + IWT/2)
        mwcx2 = mwcx1 + mw_w
        r_rect(msp, mwcx1, ffto_y1, mwcx2, ffto_y1 + 4.5*FT, layer="A-WALL", lw=20)
        r_rect(msp, mwcx2 - 1.8*FT, ffto_y1 + 0.6*FT, mwcx2 - 0.5*FT, ffto_y1 + 1.8*FT, layer="A-FURN", lw=12)
    # Male entry door on south + wall-break
    r_wall_gap(msp, ffmx1, ffto_y1 - IWT/2, ffmx2, ffto_y1 - IWT/2,
               ffmx2 - 1.375*FT, ffto_y1 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, ffmx2 - 2.75*FT, ffto_y1, 2.75*FT, swing_dir=1,
               tag="D-FF-M", host_wall="h",
               host_gap_cx=ffmx2 - 1.375*FT, host_gap_cy=ffto_y1,
               tag_cx=ffmx2 - 1.375*FT, tag_cy=ffto_y1 - 5*FT)
    r_room_bubble(msp, (ffmx1+ffmx2)/2, ffto_y1 + 2.5*FT, (ffmx1+ffmx2)/2, ffto_y2 - 2.5*FT,
                  "FF MALE", sub_label="3U+2WC")
    # Female: 3 WCs
    ffw = (fffx2 - fffx1 - IWT) / 3.0
    for i in range(3):
        ffcx1 = fffx1 + i * (ffw + IWT/3)
        ffcx2 = ffcx1 + ffw
        r_rect(msp, ffcx1, ffto_y1 + 2*FT, ffcx2, ffto_y2 - 2.5*FT, layer="A-WALL", lw=20)
        r_rect(msp, ffcx2 - 1.8*FT, ffto_y2 - 4.2*FT, ffcx2 - 0.5*FT, ffto_y2 - 3*FT, layer="A-FURN", lw=12)
        r_wall_gap(msp, ffcx1, ffto_y1+2*FT, ffcx2, ffto_y1+2*FT,
                   ffcx2 - 1*FT, ffto_y1+2*FT, 2*FT+3*IN, direction="h")
        r_door_pro(msp, ffcx2 - 2*FT, ffto_y1 + 2*FT, 2*FT, swing_dir=-1, tag=None)
    # 2 basins
    r_circle(msp, (ffmx1+ffmx2)/2, ffto_y1 + 6.5*FT, 0.5*FT, layer="A-FURN", lw=14)
    r_circle(msp, (fffx1+fffx2)/2, ffto_y1 + 1*FT, 0.5*FT, layer="A-FURN", lw=14)
    # Female entry door south + wall-break
    r_wall_gap(msp, fffx1, ffto_y1 - IWT/2, fffx2, ffto_y1 - IWT/2,
               fffx1 + 1.375*FT, ffto_y1 - IWT/2, 2.75*FT+4*IN, direction="h")
    r_door_pro(msp, fffx1 + 0.2*FT, ffto_y1, 2.75*FT, swing_dir=-1,
               tag="D-FF-F", host_wall="h",
               host_gap_cx=fffx1 + 1.375*FT, host_gap_cy=ffto_y1)
    r_room_bubble(msp, (fffx1+fffx2)/2, ffto_y1 + 2.5*FT, (fffx1+fffx2)/2, ffto_y2 - 2.5*FT,
                  "FF FEMALE", sub_label="3WC")

    # FF TOILET extra window east wall
    r_window(msp, X(55) - OWT/2, Y(62), 6*FT, direction="e")

    # FF VENTILATORS
    r_ventilator(msp, X(7.5), Y(5) + OWT/2, size=2.5*FT, direction="s", label="FV1")
    r_ventilator(msp, X(22.5), Y(5) + OWT/2, size=2.5*FT, direction="s", label="FV2")
    r_ventilator(msp, X(55) - OWT/2, Y(57), size=2.5*FT, direction="e", label="FV3")
    r_ventilator(msp, X(55) - OWT/2, Y(68), size=2.5*FT, direction="e", label="FV4")
    r_ventilator(msp, X(30.5), Y(93) - OWT/2, size=2.5*FT, direction="n", label="FV5")
    r_ventilator(msp, X(30) - OWT/2, Y(20), size=2.5*FT, direction="e", label="FV6")

    # A8 Full 4-side dims
    draw_full_perimeter_dims(msp)

    # A9 Opening schedule FF
    rows_ff = [
        ["D-FF-L1",   "SOUTH LOBBY",        "2x3\'-0\"",     "DOUBLE",       "EGRESS/SEC"],
        ["D-FF-LC",   "LOBBY-CORR",         "2x3\'-0\"",     "DOUBLE",       "INTERNAL"],
        ["D-PAN",     "PANTRY",             "3\'-0\"",       "SINGLE",       "INTERNAL"],
        ["D-STR",     "STORE ROOM",         "3\'-0\"",       "SINGLE",       "INTERNAL"],
        ["D-FF-01",   "EDP PROCESS",        "3\'-0\"",       "SINGLE",       "OFFICE"],
        ["D-ST-FF",   "STAIR FF ENTRY",     "3\'-0\"",       "SINGLE",       "CIRC"],
        ["D-LIB-1",   "LIBRARY S DOOR-1",   "2x4\'-0\"",     "DOUBLE",       "MAIN"],
        ["D-LIB-2",   "LIBRARY S DOOR-2",   "2x4\'-0\"",     "DOUBLE",       "MAIN"],
        ["D-LIB-EX",  "LIBRARY EXIT E",     "4\'-0\"",       "SINGLE",       "EGRESS"],
        ["D-STK-1",   "STACK ACCESS-1",     "3\'-0\"",       "SINGLE",       "CIRC"],
        ["D-STK-2",   "STACK ACCESS-2",     "3\'-0\"",       "SINGLE",       "CIRC"],
        ["D-LIBR",    "LIBRARIAN CABIN",    "3\'-0\"",       "SINGLE",       "OFFICE"],
        ["D-ADM",     "ADMIN OFFICE",       "3\'-0\"",       "SINGLE",       "OFFICE"],
        ["D-FF-M",    "FF MALE TOILET",     "2.75\'-0\"",    "SINGLE",       "ENTRY"],
        ["D-FF-F",    "FF FEMALE TOILET",   "2.75\'-0\"",    "SINGLE",       "ENTRY"],
        ["W-FF-W11..W17","WEST WALL",       "5/6\'",         "CASEMENT x7",  "VENT"],
    ]
    r_schedule_table(msp, X(55) + 8*FT, Y(70) + 2*FT,
                     "OPENING SCHEDULE - DOORS & WINDOWS - FF",
                     ["TAG", "LOCATION", "WIDTH", "TYPE", "NOTES"],
                     rows_ff,
                     col_widths=[12*FT, 20*FT, 10*FT, 14*FT, 16*FT], row_h=2.3*FT)

    # Area summary FF (condensed)
    rows_ffa = [
        ["Library Reading Room",    "1,535"],
        ["Stack Area",               "310"],
        ["Librarian Cabin",          "225"],
        ["Admin Office",             "300"],
        ["EDP Centre",               "218"],
        ["FF Toilet M+F",            "140"],
        ["Pantry + Store",           "255"],
        ["TOTAL FF",               "2,983"],
    ]
    rows_ffa2 = [[n, a + " sft"] for n, a in rows_ffa]
    r_schedule_table(msp, X(55) + 8*FT, Y(20) + 2*FT,
                     "AREA SCHEDULE - FIRST FLOOR",
                     ["SPACE", "AREA"], rows_ffa2,
                     col_widths=[28*FT, 14*FT], row_h=2.6*FT)

    # Title block (FF SHEET 02)
    draw_sheet_frame_and_titleblock(
        msp, SH, SW,
        sheet_no="SHEET 02 OF 02",
        sheet_title="FIRST FLOOR PLAN - 99% 3DHOME STANDARD",
        scale_txt='1/8" = 1\'-0"',
        config=config,
    )

    # Save
    dxf_path = OUT_DXF / f"BA-Refined-First-Floor-Plan{SUFFIX}.dxf"
    doc.saveas(str(dxf_path))
    print(f"[OK] FF DXF saved: {dxf_path.name}")
    pdf = export_dxf_to_pdf(dxf_path, config)
    print(f"[OK] FF PDF saved: {pdf}")
    return dxf_path, pdf


'''

src_new = src[:idx_start] + NEW_FF + src[idx_end:]
FILE.write_text(src_new)
print("FF rewrite PASS 3 OK")

# Update __main__ banner to reflect WEST main entry
src = FILE.read_text()
OLD_BANNER = '''    print("  GF: Pres+Secy Chambers, Bar Off, 5-Urinal Toilet, Hall Chairs Only")
    print("  FF: EDP Centre Corner, Library Tables Chairs Both Sides")
'''
NEW_BANNER = '''    print("  GF: WEST-MAIN ENTRY (LONG 88ft wall), Pres+Secy, Bar Off, 5-U Toilet, Hall")
    print("  FF: Librarian+Admin West Strip, Library Both-Sides Chairs, Stack, EDP, Toilets")
    print("  A2-A9: Wall-breaks, bubbles, grid-bubbles, north-arrow, hatches, 4-dim, schedule")
'''
if OLD_BANNER not in src:
    print("WARNING: banner anchor not found (not fatal)")
else:
    src = src.replace(OLD_BANNER, NEW_BANNER, 1)
    FILE.write_text(src)
    print("Banner update PASS 4 OK")

print("\nALL PATCHES SUCCESSFUL — 99% 3DHOME applied.")
