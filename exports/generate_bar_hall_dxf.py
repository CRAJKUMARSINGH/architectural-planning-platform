#!/usr/bin/env python3
"""
Bar Association Hall - DXF Export Script
Banswara, Rajasthan — First Floor Corrected Plan (Balcony + Ladies Room)
Generated per BAR HAAL instructions — Rev P03
"""
import ezdxf
from ezdxf import units


def create_first_floor_dxf():
    doc = ezdxf.new('R2010', setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    # Layers per CAD standards
    doc.layers.add("A-WALL-EXT", color=7, lineweight=50)
    doc.layers.add("A-WALL-INT", color=7, lineweight=30)
    doc.layers.add("A-DOOR", color=4)
    doc.layers.add("A-WIND", color=5)
    doc.layers.add("A-FURN", color=2)
    doc.layers.add("A-DIMS", color=3)
    doc.layers.add("A-TEXT", color=1)
    doc.layers.add("A-AREA", color=6)   # Ladies room highlight
    doc.layers.add("A-GRID", color=8)

    # Grid 6m x 6m
    for i, label in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
        x = i * 6.0
        msp.add_line((x, -2), (x, 26), dxfattribs={'layer': 'A-GRID'})
        msp.add_text(label, height=0.2).set_placement((x, -1))
    for j in range(1, 5):
        y = (j - 1) * 6.0
        msp.add_line((-2, y), (32, y), dxfattribs={'layer': 'A-GRID'})
        msp.add_text(str(j), height=0.2).set_placement((-1, y))

    # External walls 230mm
    ext = [(0, 0), (30, 0), (30, 24), (0, 24), (0, 0)]
    msp.add_lwpolyline(ext, close=True, dxfattribs={'layer': 'A-WALL-EXT', 'lineweight': 50})

    # Ladies Advocate Room — highlighted
    ladies = [(24, 20), (27, 20), (27, 24), (24, 24)]
    msp.add_lwpolyline(ladies, close=True, dxfattribs={'layer': 'A-AREA'})

    # Attached toilet
    toilet = [(25, 18), (27, 18), (27, 20), (25, 20)]
    msp.add_lwpolyline(toilet, close=True, dxfattribs={'layer': 'A-WALL-INT'})

    # D4 French door to balcony
    msp.add_arc((24, 21), 1.2, 270, 360, dxfattribs={'layer': 'A-DOOR'})
    msp.add_text("D4\n1200x2400", height=0.12).set_placement((24.3, 20.3))

    # Internal toilet door
    msp.add_arc((26, 20), 0.75, 180, 270, dxfattribs={'layer': 'A-DOOR'})

    # Balcony — 1.5m projection
    msp.add_line((0, -1.5), (30, -1.5), dxfattribs={'layer': 'A-WALL-EXT'})
    msp.add_text("BALCONY 1.5m DEEP", height=0.15).set_placement((12, -1.2))

    # Railing
    msp.add_line((0, -1.5), (0, -2.5), dxfattribs={'layer': 'A-WALL-EXT'})
    msp.add_line((30, -1.5), (30, -2.5), dxfattribs={'layer': 'A-WALL-EXT'})
    msp.add_line((0, -2.5), (30, -2.5), dxfattribs={'layer': 'A-WALL-EXT'})
    msp.add_text("MS RAILING 1.05m HIGH", height=0.12).set_placement((12, -2.2))

    # Room labels
    rooms = [
        ((25.5, 22), "LADIES ADVOCATE ROOM\n12.0 m2"),
        ((26, 19), "TOILET\n4.0 m2"),
        ((15, 22), "LIBRARY\n36.0 m2"),
        ((15, 16), "COMMITTEE ROOM\n30.0 m2"),
        ((7.5, 22), "OFFICE 1\n18.0 m2"),
        ((7.5, 16), "OFFICE 2\n18.0 m2"),
    ]
    for pos, text in rooms:
        msp.add_text(text, height=0.18, dxfattribs={'layer': 'A-TEXT'}).set_placement(pos)

    doc.saveas('exports/dxf/A-03_FIRST_FLOOR_CORRECTED.dxf')
    print("OK  DXF exported: exports/dxf/A-03_FIRST_FLOOR_CORRECTED.dxf")


if __name__ == "__main__":
    create_first_floor_dxf()
