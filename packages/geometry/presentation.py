"""Phase 8 — Presentation scene compiler, asset catalog, and render manifest generator.

Governing principle:
  "Create a structurally correct plan first, then render it beautifully."
  Presentation objects may add materials, furniture, plants, lighting, and
  decorative content, but cannot mutate canonical geometry.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from packages.geometry.serializers import canonical_json, sha256

# ---------------------------------------------------------------------------
# Camera Presets & Style Tokens
# ---------------------------------------------------------------------------

CAMERA_PRESETS: dict[str, dict[str, Any]] = {
    "top-down-plan": {
        "preset": "top-down-plan",
        "projection": "orthographic",
        "position": [0.0, 0.0, 5000.0],
        "target": [0.0, 0.0, 0.0],
    },
    "axonometric-east-front": {
        "preset": "axonometric-east-front",
        "projection": "orthographic",
        "position": [4000.0, -4000.0, 3000.0],
        "target": [0.0, 0.0, 0.0],
    },
    "perspective-courtyard": {
        "preset": "perspective-courtyard",
        "projection": "perspective",
        "position": [2000.0, -2500.0, 1600.0],
        "target": [0.0, 0.0, 1200.0],
    },
    "isometric-overview": {
        "preset": "isometric-overview",
        "projection": "orthographic",
        "position": [5000.0, -5000.0, 4000.0],
        "target": [0.0, 0.0, 0.0],
    },
}

STYLE_TOKENS: dict[str, dict[str, Any]] = {
    "presentation-residential-v1": {
        "version": "presentation-residential-v1",
        "wallStroke": "#1A1A1A",
        "wallFill": "#2C3E50",
        "wallStrokeWidth": 3.5,
        "roomPalette": {
            "living": {"fill": "#F9F6F0", "accent": "#D4AF37", "label": "Living Room"},
            "bedroom": {"fill": "#F0F4F8", "accent": "#718096", "label": "Bedroom"},
            "kitchen": {"fill": "#FFFDF7", "accent": "#E2E8F0", "label": "Kitchen"},
            "dining": {"fill": "#F7FAFC", "accent": "#CBD5E0", "label": "Dining Area"},
            "bath": {"fill": "#EDF2F7", "accent": "#A0AEC0", "label": "Bathroom"},
            "chamber": {"fill": "#FAF5FF", "accent": "#805AD5", "label": "Advocate Chamber"},
            "library": {"fill": "#F0FFF4", "accent": "#38A169", "label": "Law Library"},
            "hall": {"fill": "#FFFAF0", "accent": "#DD6B20", "label": "Association Hall"},
            "courtyard": {"fill": "#F0FFF4", "accent": "#48BB78", "label": "Open Courtyard"},
            "corridor": {"fill": "#F7FAFC", "accent": "#E2E8F0", "label": "Corridor / Circulation"},
            "default": {"fill": "#FFFFFF", "accent": "#E2E8F0", "label": "Space"},
        },
        "shadow": {"enabled": True, "blur": 8, "color": "rgba(0,0,0,0.15)", "offsetY": 4},
        "fontFamily": "Inter, Roboto, sans-serif",
    },
    "presentation-commercial-v1": {
        "version": "presentation-commercial-v1",
        "wallStroke": "#0F172A",
        "wallFill": "#1E293B",
        "wallStrokeWidth": 4.0,
        "roomPalette": {
            "chamber": {"fill": "#F8FAFC", "accent": "#3B82F6", "label": "Chamber"},
            "hall": {"fill": "#F1F5F9", "accent": "#6366F1", "label": "Main Bar Hall"},
            "library": {"fill": "#F8FAFC", "accent": "#0D9488", "label": "Reference Library"},
            "conference": {"fill": "#FAF5FF", "accent": "#9333EA", "label": "Conference Room"},
            "corridor": {"fill": "#F8FAFC", "accent": "#CBD5E1", "label": "Passage"},
            "default": {"fill": "#FFFFFF", "accent": "#E2E8F0", "label": "Office Area"},
        },
        "shadow": {"enabled": True, "blur": 10, "color": "rgba(15,23,42,0.12)", "offsetY": 6},
        "fontFamily": "Inter, Outfit, sans-serif",
    },
}

# ---------------------------------------------------------------------------
# Standard Presentation Asset Catalog
# ---------------------------------------------------------------------------

ASSET_CATALOG_VERSION = "assets-v3"

ASSET_CATALOG: dict[str, dict[str, Any]] = {
    "sofa-3seat": {
        "assetId": "sofa-3seat",
        "name": "3-Seat Executive Sofa",
        "category": "seating",
        "dimensions": {"width": 2100, "depth": 900, "height": 850, "unit": "mm"},
        "clearanceEnvelope": {"front": 600, "back": 100, "sides": 150},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 3,
        "presentationOnly": True,
    },
    "sofa-single": {
        "assetId": "sofa-single",
        "name": "Single Armchair",
        "category": "seating",
        "dimensions": {"width": 900, "depth": 850, "height": 850, "unit": "mm"},
        "clearanceEnvelope": {"front": 500, "back": 50, "sides": 100},
        "permittedRotations": [0, 45, 90, 135, 180, 225, 270, 315],
        "occupancy": 1,
        "presentationOnly": True,
    },
    "advocate-desk": {
        "assetId": "advocate-desk",
        "name": "Senior Advocate Executive Desk",
        "category": "desks",
        "dimensions": {"width": 1800, "depth": 900, "height": 750, "unit": "mm"},
        "clearanceEnvelope": {"front": 900, "back": 1000, "sides": 400},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 1,
        "presentationOnly": True,
    },
    "conference-table-8": {
        "assetId": "conference-table-8",
        "name": "8-Person Conference Table",
        "category": "tables",
        "dimensions": {"width": 2800, "depth": 1200, "height": 750, "unit": "mm"},
        "clearanceEnvelope": {"front": 900, "back": 900, "sides": 900},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 8,
        "presentationOnly": True,
    },
    "bookshelf-law-library": {
        "assetId": "bookshelf-law-library",
        "name": "Full-Height Law Journal Shelf",
        "category": "storage",
        "dimensions": {"width": 1200, "depth": 400, "height": 2200, "unit": "mm"},
        "clearanceEnvelope": {"front": 800, "back": 0, "sides": 0},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 0,
        "presentationOnly": True,
    },
    "dining-table-6": {
        "assetId": "dining-table-6",
        "name": "6-Seat Dining Table",
        "category": "tables",
        "dimensions": {"width": 1800, "depth": 900, "height": 750, "unit": "mm"},
        "clearanceEnvelope": {"front": 800, "back": 800, "sides": 600},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 6,
        "presentationOnly": True,
    },
    "bed-king": {
        "assetId": "bed-king",
        "name": "King Bed with Side Tables",
        "category": "beds",
        "dimensions": {"width": 2000, "depth": 2100, "height": 1100, "unit": "mm"},
        "clearanceEnvelope": {"front": 800, "back": 0, "sides": 600},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 2,
        "presentationOnly": True,
    },
    "indoor-plant-planter": {
        "assetId": "indoor-plant-planter",
        "name": "Architectural Ficus Planter",
        "category": "foliage",
        "dimensions": {"width": 500, "depth": 500, "height": 1400, "unit": "mm"},
        "clearanceEnvelope": {"front": 100, "back": 100, "sides": 100},
        "permittedRotations": [0, 90, 180, 270],
        "occupancy": 0,
        "presentationOnly": True,
    },
    "courtyard-stepwell-fountain": {
        "assetId": "courtyard-stepwell-fountain",
        "name": "Courtyard Stepwell Water Feature",
        "category": "landscape",
        "dimensions": {"width": 2400, "depth": 2400, "height": 450, "unit": "mm"},
        "clearanceEnvelope": {"front": 600, "back": 600, "sides": 600},
        "permittedRotations": [0],
        "occupancy": 0,
        "presentationOnly": True,
    },
}

# ---------------------------------------------------------------------------
# Scene Graph Compiler
# ---------------------------------------------------------------------------

def build_render_manifest(
    *,
    model_sha256: str,
    manifest_id: str | None = None,
    style_version: str = "presentation-residential-v1",
    camera_preset: str = "top-down-plan",
    renderer_version: str = "renderer-0.4.0",
    asset_catalog_version: str = ASSET_CATALOG_VERSION,
    seed: int = 1516,
    output_kind: str = "svg",
    width: int = 1920,
    height: int = 1080,
    section_height: float | None = None,
    section_unit: str = "mm",
) -> dict[str, Any]:
    """Generate a valid render manifest matching packages/schema/render-manifest.schema.json."""
    if camera_preset not in CAMERA_PRESETS:
        camera_preset = "top-down-plan"
    cam = copy.deepcopy(CAMERA_PRESETS[camera_preset])

    mime_map = {
        "svg": "image/svg+xml",
        "png": "image/png",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "glb": "model/gltf-binary",
        "pdf": "application/pdf",
    }

    manifest: dict[str, Any] = {
        "schemaVersion": "advocate-chambers.render-manifest.v1",
        "manifestId": manifest_id or f"rm-{uuid.uuid4().hex[:12]}",
        "modelSha256": model_sha256,
        "rendererVersion": renderer_version,
        "styleVersion": style_version,
        "assetCatalogVersion": asset_catalog_version,
        "camera": cam,
        "sectionPlane": (
            {"height": section_height, "unit": section_unit}
            if section_height is not None
            else None
        ),
        "output": {
            "kind": output_kind,
            "width": width,
            "height": height,
            "mimeType": mime_map.get(output_kind, "image/svg+xml"),
        },
        "seed": seed,
        "presentationOnly": True,
    }
    return manifest


def compile_presentation_scene(
    model: dict[str, Any],
    *,
    style_version: str = "presentation-residential-v1",
    camera_preset: str = "top-down-plan",
    seed: int = 1516,
) -> dict[str, Any]:
    """Compile canonical model into separate Technical and Presentation scene graphs."""
    style = STYLE_TOKENS.get(style_version, STYLE_TOKENS["presentation-residential-v1"])
    model_hash = sha256(model)

    spaces = model.get("spaces", []) or model.get("rooms", []) or []
    walls = model.get("walls", []) or []
    openings = model.get("openings", []) or []
    levels = model.get("levels", []) or [{"id": "L0", "name": "Ground Floor", "elevation": 0}]

    # 1. Technical Scene Graph (Authoritative structural elements)
    technical_scene: dict[str, Any] = {
        "kind": "technical-scene",
        "modelSha256": model_hash,
        "units": model.get("units", "inch"),
        "levels": levels,
        "walls": [
            {
                "id": w.get("id", f"w-{i}"),
                "start": w.get("start", [0, 0]),
                "end": w.get("end", [0, 0]),
                "thickness": w.get("thickness", 9.0),
                "levelId": w.get("levelId", levels[0]["id"]),
                "status": "VALIDATED",
            }
            for i, w in enumerate(walls)
        ],
        "openings": [
            {
                "id": o.get("id", f"op-{i}"),
                "kind": o.get("kind", "door"),
                "wallId": o.get("wallId", ""),
                "offset": o.get("offset", 0.0),
                "width": o.get("width", 36.0),
                "levelId": o.get("levelId", levels[0]["id"]),
            }
            for i, o in enumerate(openings)
        ],
        "spaces": [
            {
                "id": s.get("id", f"sp-{i}"),
                "name": s.get("name", f"Space {i+1}"),
                "kind": s.get("kind", s.get("type", "space")),
                "polygon": s.get("polygon", s.get("boundary", [])),
                "area": s.get("area", 0.0),
                "levelId": s.get("levelId", levels[0]["id"]),
            }
            for i, s in enumerate(spaces)
        ],
    }

    # 2. Presentation Scene Graph (Materials, styling, furniture, vegetation)
    presentation_items: list[dict[str, Any]] = []
    palette = style["roomPalette"]

    for i, s in enumerate(spaces):
        sp_id = s.get("id", f"sp-{i}")
        sp_kind = str(s.get("kind", s.get("type", "default"))).lower()
        sp_name = str(s.get("name", "")).lower()

        # Match room style token
        token_key = "default"
        for key in palette:
            if key in sp_kind or key in sp_name:
                token_key = key
                break
        token = palette.get(token_key, palette["default"])

        # Add stylized floor material node
        presentation_items.append({
            "id": f"mat-{sp_id}",
            "type": "material-layer",
            "spaceId": sp_id,
            "fillColor": token["fill"],
            "accentColor": token["accent"],
            "texture": "subtle-parquet" if token_key in ("living", "chamber", "library") else "smooth-screed",
            "presentationOnly": True,
        })

        # Suggest contextual furniture based on room archetype
        suggested_asset = None
        if "chamber" in token_key or "office" in sp_name:
            suggested_asset = "advocate-desk"
        elif "library" in token_key:
            suggested_asset = "bookshelf-law-library"
        elif "hall" in token_key or "conference" in sp_name:
            suggested_asset = "conference-table-8"
        elif "living" in token_key:
            suggested_asset = "sofa-3seat"
        elif "dining" in token_key:
            suggested_asset = "dining-table-6"
        elif "bedroom" in token_key:
            suggested_asset = "bed-king"
        elif "courtyard" in token_key:
            suggested_asset = "courtyard-stepwell-fountain"

        if suggested_asset and suggested_asset in ASSET_CATALOG:
            asset = ASSET_CATALOG[suggested_asset]
            # Center of space boundary if available
            poly = s.get("polygon", s.get("boundary", []))
            cx, cy = 0.0, 0.0
            if poly and len(poly) >= 3:
                xs = [p[0] for p in poly if len(p) >= 2]
                ys = [p[1] for p in poly if len(p) >= 2]
                if xs and ys:
                    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)

            presentation_items.append({
                "id": f"furn-{sp_id}-{asset['assetId']}",
                "type": "asset-instance",
                "assetId": asset["assetId"],
                "name": asset["name"],
                "spaceId": sp_id,
                "position": [cx, cy, 0.0],
                "rotation": 0.0,
                "dimensions": asset["dimensions"],
                "clearanceEnvelope": asset["clearanceEnvelope"],
                "presentationOnly": True,
            })

    presentation_scene: dict[str, Any] = {
        "kind": "presentation-scene",
        "modelSha256": model_hash,
        "styleVersion": style["version"],
        "style": style,
        "assetCatalogVersion": ASSET_CATALOG_VERSION,
        "items": presentation_items,
        "lighting": {
            "ambient": {"color": "#FFFFFF", "intensity": 0.65},
            "sun": {"direction": [0.5, -0.7, 0.9], "color": "#FFF8E7", "intensity": 0.85},
            "shadows": True,
        },
        "disclaimer": "Preliminary Planning Presentation — Non-Authoritative Styling",
        "presentationOnly": True,
    }

    manifest = build_render_manifest(
        model_sha256=model_hash,
        style_version=style["version"],
        camera_preset=camera_preset,
        seed=seed,
    )

    return {
        "schemaVersion": "advocate-chambers.compiled-presentation.v1",
        "modelSha256": model_hash,
        "technicalScene": technical_scene,
        "presentationScene": presentation_scene,
        "renderManifest": manifest,
    }


def render_presentation_svg(compiled_scene: dict[str, Any], *, width: int = 1200, height: int = 800) -> str:
    """Render a deterministic, crisp, high-aesthetic SVG 2D presentation drawing."""
    tech = compiled_scene.get("technicalScene", {})
    pres = compiled_scene.get("presentationScene", {})
    style = pres.get("style", STYLE_TOKENS["presentation-residential-v1"])

    spaces = tech.get("spaces", [])
    walls = tech.get("walls", [])
    openings = tech.get("openings", [])
    items = pres.get("items", [])

    # Calculate bounding box
    all_points: list[tuple[float, float]] = []
    for s in spaces:
        for p in s.get("polygon", []):
            if len(p) >= 2:
                all_points.append((float(p[0]), float(p[1])))
    for w in walls:
        all_points.append((float(w["start"][0]), float(w["start"][1])))
        all_points.append((float(w["end"][0]), float(w["end"][1])))

    if not all_points:
        all_points = [(0, 0), (1000, 800)]

    min_x = min(p[0] for p in all_points) - 50
    max_x = max(p[0] for p in all_points) + 50
    min_y = min(p[1] for p in all_points) - 50
    max_y = max(p[1] for p in all_points) + 50

    vb_w = max_x - min_x
    vb_h = max_y - min_y

    svg_parts: list[str] = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x} {min_y} {vb_w} {vb_h}" '
        f'width="{width}" height="{height}" style="background-color: #FAFAFA; font-family: {style["fontFamily"]}">'
    )

    # Defs: filters, gradients, drop shadows
    svg_parts.append('''
      <defs>
        <filter id="soft-shadow" x="-10%" y="-10%" width="130%" height="130%">
          <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0F172A" flood-opacity="0.12"/>
        </filter>
        <filter id="wall-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="2" dy="3" stdDeviation="3" flood-color="#000000" flood-opacity="0.25"/>
        </filter>
        <pattern id="pat-parquet" width="20" height="20" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="20" y2="0" stroke="#E2E8F0" stroke-width="0.5"/>
          <line x1="0" y1="10" x2="20" y2="10" stroke="#E2E8F0" stroke-width="0.5"/>
        </pattern>
      </defs>
    ''')

    # Layer 1: Spaces / Rooms with presentation materials
    svg_parts.append('<g id="layer-spaces" filter="url(#soft-shadow)">')
    for s in spaces:
        poly = s.get("polygon", [])
        if len(poly) >= 3:
            pts_str = " ".join(f"{p[0]},{p[1]}" for p in poly)
            # Match material fill
            mat_fill = "#FFFFFF"
            for it in items:
                if it.get("spaceId") == s["id"] and it.get("type") == "material-layer":
                    mat_fill = it.get("fillColor", "#FFFFFF")
                    break
            svg_parts.append(f'<polygon points="{pts_str}" fill="{mat_fill}" stroke="#E2E8F0" stroke-width="1.5"/>')
    svg_parts.append('</g>')

    # Layer 2: Furniture and Presentation Assets
    svg_parts.append('<g id="layer-presentation-assets">')
    for it in items:
        if it.get("type") == "asset-instance":
            pos = it.get("position", [0, 0])
            dims = it.get("dimensions", {"width": 800, "depth": 600})
            w = dims.get("width", 800) / 10.0  # Scale to match coordinate scale
            d = dims.get("depth", 600) / 10.0
            x = pos[0] - w / 2
            y = pos[1] - d / 2
            name = it.get("name", "Asset")
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{d}" rx="4" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.2"/>'
            )
            svg_parts.append(
                f'<text x="{pos[0]}" y="{pos[1] + 3}" font-size="8" fill="#475569" text-anchor="middle">{name[:14]}</text>'
            )
    svg_parts.append('</g>')

    # Layer 3: Walls
    svg_parts.append(f'<g id="layer-walls" filter="url(#wall-shadow)">')
    wall_stroke = style.get("wallStroke", "#1E293B")
    wall_w = style.get("wallStrokeWidth", 3.5)
    for w in walls:
        st = w["start"]
        en = w["end"]
        svg_parts.append(
            f'<line x1="{st[0]}" y1="{st[1]}" x2="{en[0]}" y2="{en[1]}" '
            f'stroke="{wall_stroke}" stroke-width="{wall_w}" stroke-linecap="square"/>'
        )
    svg_parts.append('</g>')

    # Layer 4: Openings / Doors / Windows
    svg_parts.append('<g id="layer-openings">')
    for op in openings:
        # Render door swing indicator if wall coordinate available
        kind = op.get("kind", "door")
        width_op = op.get("width", 36.0)
        # Placeholder vector arc
    svg_parts.append('</g>')

    # Layer 5: Room Labels
    svg_parts.append('<g id="layer-labels">')
    for s in spaces:
        poly = s.get("polygon", [])
        if poly and len(poly) >= 3:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            name = s.get("name", "Space")
            area = s.get("area", 0.0)
            svg_parts.append(
                f'<text x="{cx}" y="{cy - 12}" font-size="14" font-weight="600" fill="#0F172A" text-anchor="middle">{name}</text>'
            )
            if area > 0:
                svg_parts.append(
                    f'<text x="{cx}" y="{cy + 12}" font-size="11" fill="#64748B" text-anchor="middle">{area:.1f} sq.ft</text>'
                )
    svg_parts.append('</g>')

    # Header / Title Block & Presentation Disclaimer
    svg_parts.append(f'''
      <g id="presentation-watermark">
        <text x="{min_x + 20}" y="{max_y - 20}" font-size="11" fill="#94A3B8" font-style="italic">
          Advocate-Chambers • Presentation Rendering • {pres.get("disclaimer", "")} • SHA: {compiled_scene.get("modelSha256", "")[:12]}
        </text>
      </g>
    ''')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)
