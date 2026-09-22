"""Phase 8 — Vector overlay labels and dimensions for presentation renders.

This module provides precise architectural annotation overlays that can be
rendered as vector graphics (SVG) or composited onto 3D renders. These overlays
maintain architectural accuracy while enhancing presentation quality.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class DimensionLine:
    """Architectural dimension line with extension lines and text."""
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    offset: float = 20.0  # Distance from measured element
    text: str = ""
    units: str = "inch"
    arrow_size: float = 6.0


@dataclass
class LabelOverlay:
    """Text label positioned relative to architectural elements."""
    text: str
    position: tuple[float, float]
    anchor: str = "middle"  # start, middle, end
    font_size: float = 12.0
    font_weight: str = "normal"
    color: str = "#0F172A"
    background: str | None = None


@dataclass
class LeaderLine:
    """Leader line pointing from label to architectural element."""
    label_position: tuple[float, float]
    target_position: tuple[float, float]
    style: str = "solid"  # solid, dashed
    arrow: bool = True


def calculate_wall_dimensions(
    walls: list[dict[str, Any]],
    scale: float = 1.0,
    units: str = "inch",
) -> list[DimensionLine]:
    """Generate dimension lines for all walls in the technical scene."""
    dimensions: list[DimensionLine] = []
    
    for wall in walls:
        start = wall.get("start", [0, 0])
        end = wall.get("end", [0, 0])
        
        # Calculate wall length
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx * dx + dy * dy) * scale
        
        # Determine offset direction (perpendicular to wall)
        if abs(dx) > abs(dy):
            # Horizontal wall, offset vertically
            offset_sign = 1 if dy > 0 else -1
            offset_vector = (0, offset_sign * 20.0)
        else:
            # Vertical wall, offset horizontally
            offset_sign = 1 if dx > 0 else -1
            offset_vector = (offset_sign * 20.0, 0)
        
        # Calculate dimension line position
        dim_start = (start[0] + offset_vector[0], start[1] + offset_vector[1])
        dim_end = (end[0] + offset_vector[0], end[1] + offset_vector[1])
        
        dimension_text = f"{length:.1f} {units}"
        
        dimensions.append(DimensionLine(
            start_point=dim_start,
            end_point=dim_end,
            offset=20.0,
            text=dimension_text,
            units=units,
        ))
    
    return dimensions


def calculate_room_labels(
    spaces: list[dict[str, Any]],
    show_area: bool = True,
    show_dimensions: bool = False,
) -> list[LabelOverlay]:
    """Generate text labels for all rooms/spaces."""
    labels: list[LabelOverlay] = []
    
    for space in spaces:
        polygon = space.get("polygon", space.get("boundary", []))
        if not polygon or len(polygon) < 3:
            continue
        
        # Calculate centroid
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # Primary label: room name
        name = space.get("name", "Space")
        labels.append(LabelOverlay(
            text=name,
            position=(cx, cy - 15),
            anchor="middle",
            font_size=14.0,
            font_weight="600",
            color="#0F172A",
        ))
        
        # Secondary label: area
        if show_area:
            area = space.get("area", 0.0)
            labels.append(LabelOverlay(
                text=f"{area:.1f} sq.ft",
                position=(cx, cy + 15),
                anchor="middle",
                font_size=11.0,
                font_weight="normal",
                color="#64748B",
            ))
        
        # Tertiary label: dimensions if requested
        if show_dimensions:
            width = max(xs) - min(xs)
            depth = max(ys) - min(ys)
            labels.append(LabelOverlay(
                text=f"{width:.0f} × {depth:.0f}",
                position=(cx, cy + 30),
                anchor="middle",
                font_size=10.0,
                font_weight="normal",
                color="#94A3B8",
            ))
    
    return labels


def generate_dimension_svg_elements(
    dimensions: list[DimensionLine],
    stroke_color: str = "#475569",
    text_color: str = "#0F172A",
) -> str:
    """Generate SVG elements for dimension lines."""
    svg_parts: list[str] = []
    
    for dim in dimensions:
        x1, y1 = dim.start_point
        x2, y2 = dim.end_point
        
        # Main dimension line
        svg_parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke_color}" stroke-width="1" marker-end="url(#arrow)" marker-start="url(#arrow-rev)"/>'
        )
        
        # Extension lines (perpendicular to dimension line)
        ext_length = 8.0
        svg_parts.append(
            f'<line x1="{x1}" y1="{y1 - ext_length}" x2="{x1}" y2="{y1 + ext_length}" '
            f'stroke="{stroke_color}" stroke-width="0.8"/>'
        )
        svg_parts.append(
            f'<line x1="{x2}" y1="{y2 - ext_length}" x2="{x2}" y2="{y2 + ext_length}" '
            f'stroke="{stroke_color}" stroke-width="0.8"/>'
        )
        
        # Dimension text
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        svg_parts.append(
            f'<text x="{cx}" y="{cy - 4}" font-size="10" fill="{text_color}" '
            f'text-anchor="middle" font-family="Inter, sans-serif">{dim.text}</text>'
        )
    
    return "\n".join(svg_parts)


def generate_label_svg_elements(
    labels: list[LabelOverlay],
) -> str:
    """Generate SVG elements for text labels."""
    svg_parts: list[str] = []
    
    for label in labels:
        x, y = label.position
        font_family = "Inter, sans-serif"
        
        # Background for readability if specified
        if label.background:
            svg_parts.append(
                f'<rect x="{x - 50}" y="{y - 10}" width="100" height="20" '
                f'fill="{label.background}" rx="2" opacity="0.9"/>'
            )
        
        svg_parts.append(
            f'<text x="{x}" y="{y}" font-size="{label.font_size}" '
            f'font-weight="{label.font_weight}" fill="{label.color}" '
            f'text-anchor="{label.anchor}" font-family="{font_family}">{label.text}</text>'
        )
    
    return "\n".join(svg_parts)


def add_vector_overlays_to_svg(
    base_svg: str,
    dimensions: list[DimensionLine] | None = None,
    labels: list[LabelOverlay] | None = None,
) -> str:
    """Add vector overlays (dimensions, labels) to an existing SVG."""
    if not dimensions and not labels:
        return base_svg
    
    overlay_parts: list[str] = []
    
    # Add arrow markers definition if dimensions exist
    if dimensions:
        overlay_parts.append('''
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L9,3 z" fill="#475569" />
        </marker>
        <marker id="arrow-rev" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M9,0 L9,6 L0,3 z" fill="#475569" />
        </marker>
      </defs>
    ''')
    
    # Add dimension layer
    if dimensions:
        overlay_parts.append('<g id="layer-dimensions">')
        overlay_parts.append(generate_dimension_svg_elements(dimensions))
        overlay_parts.append('</g>')
    
    # Add label layer
    if labels:
        overlay_parts.append('<g id="layer-labels">')
        overlay_parts.append(generate_label_svg_elements(labels))
        overlay_parts.append('</g>')
    
    # Insert overlays before closing SVG tag
    svg_close = '</svg>'
    if svg_close in base_svg:
        return base_svg.replace(svg_close, "\n".join(overlay_parts) + "\n" + svg_close)
    else:
        return base_svg + "\n".join(overlay_parts) + "\n</svg>"


def calculate_scale_indicator(
    bounds: tuple[float, float, float, float],  # min_x, min_y, max_x, max_y
    target_pixels: float = 100.0,
    real_world_units: float = 120.0,  # 10 feet in inches
    units: str = "inch",
) -> dict[str, Any]:
    """Calculate a scale bar for the drawing."""
    min_x, min_y, max_x, max_y = bounds
    drawing_width = max_x - min_x
    
    # Calculate pixels per unit
    if drawing_width > 0:
        pixels_per_unit = target_pixels / real_world_units
    else:
        pixels_per_unit = 1.0
    
    scale_text = f"1:{real_world_units/target_pixels:.0f}" if target_pixels > 0 else "1:100"
    
    return {
        "position": (min_x + 20, max_y - 40),
        "width_pixels": target_pixels,
        "real_world_units": real_world_units,
        "units": units,
        "scale_text": scale_text,
        "pixels_per_unit": pixels_per_unit,
    }